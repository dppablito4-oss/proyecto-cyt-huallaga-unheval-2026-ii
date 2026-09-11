"""Pose corporal selectiva con MediaPipe como dependencia opcional."""

from __future__ import annotations

import logging
from datetime import datetime
from math import hypot
from pathlib import Path
from typing import Protocol, Sequence

import cv2
import numpy as np

from app.models.pose import PosePoint, PoseState
from app.models.scene import SceneState
from app.models.tracking import TrackState

logger = logging.getLogger(__name__)


class PoseAnalyzer(Protocol):
    """Contrato mínimo para enriquecer personas sin acoplar el worker a MediaPipe."""

    @property
    def available(self) -> bool: ...

    def update(
        self,
        frame: np.ndarray,
        scene: SceneState,
        force_track_ids: set[int] | None = None,
    ) -> dict[int, PoseState]: ...

    def reset(self) -> None: ...


class NullPoseAnalyzer:
    """Implementación segura usada cuando pose está desactivada."""

    available = False

    def update(
        self,
        frame: np.ndarray,
        scene: SceneState,
        force_track_ids: set[int] | None = None,
    ) -> dict[int, PoseState]:
        return {}

    def reset(self) -> None:
        return None


class MediaPipePoseAnalyzer:
    """Ejecuta Pose Landmarker sólo sobre personas y momentos relevantes."""

    _LANDMARK_INDEXES = {
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
    }

    def __init__(
        self,
        model_path: Path,
        trigger_zones: Sequence[str],
        fps: float = 7.0,
        min_person_confidence: float = 0.6,
        min_detection_confidence: float = 0.5,
        min_landmark_visibility: float = 0.5,
        max_persons_per_frame: int = 2,
        result_ttl_seconds: float = 0.5,
        crop_padding_ratio: float = 0.15,
        object_proximity_ratio: float = 0.5,
    ):
        if fps <= 0 or result_ttl_seconds <= 0 or object_proximity_ratio <= 0:
            raise ValueError("FPS, TTL y distancia de pose deben ser mayores que cero.")
        if max_persons_per_frame < 1:
            raise ValueError("max_persons_per_frame debe ser al menos 1.")
        self.model_path = Path(model_path)
        self.trigger_zones = {name.casefold() for name in trigger_zones}
        self.fps = float(fps)
        self.min_person_confidence = float(min_person_confidence)
        self.min_detection_confidence = float(min_detection_confidence)
        self.min_landmark_visibility = float(min_landmark_visibility)
        self.max_persons_per_frame = max_persons_per_frame
        self.result_ttl_seconds = float(result_ttl_seconds)
        self.crop_padding_ratio = float(crop_padding_ratio)
        self.object_proximity_ratio = float(object_proximity_ratio)
        self._mediapipe = None
        self._landmarker = None
        self._initialization_attempted = False
        self._last_attempt: dict[int, datetime] = {}
        self._cache: dict[int, PoseState] = {}

    @property
    def available(self) -> bool:
        return self._landmarker is not None

    def update(
        self,
        frame: np.ndarray,
        scene: SceneState,
        force_track_ids: set[int] | None = None,
    ) -> dict[int, PoseState]:
        if frame is None or frame.size == 0:
            return {}

        active_ids = set(scene.persons)
        self._prune(scene.timestamp, active_ids)
        forced = force_track_ids or set()
        eligible = [
            person
            for person in scene.persons.values()
            if person.confidence >= self.min_person_confidence
            and self._activation_reason(person, scene, forced) is not None
        ]
        eligible.sort(
            key=lambda person: (
                person.track_id not in forced,
                person.current_zone is None,
                -person.confidence,
            )
        )

        for person in eligible[: self.max_persons_per_frame]:
            if not self._is_due(person.track_id, scene.timestamp):
                continue
            self._last_attempt[person.track_id] = scene.timestamp
            pose = self._analyze_person(frame, person, scene.timestamp)
            if pose is not None:
                self._cache[person.track_id] = pose

        return {
            track_id: pose.model_copy(deep=True)
            for track_id, pose in self._cache.items()
            if track_id in active_ids
            and self._age_seconds(scene.timestamp, pose.timestamp) <= self.result_ttl_seconds
        }

    def _activation_reason(
        self,
        person: TrackState,
        scene: SceneState,
        forced: set[int],
    ) -> str | None:
        if person.track_id in forced:
            return "event_engine"
        if person.current_zone and person.current_zone.casefold() in self.trigger_zones:
            return "relevant_zone"
        if any(self._object_is_near(person, obj) for obj in scene.objects.values()):
            return "near_object"
        return None

    def _object_is_near(self, person: TrackState, obj: TrackState) -> bool:
        horizontal = max(person.bbox.x1 - obj.centroid.x, 0.0, obj.centroid.x - person.bbox.x2)
        vertical = max(person.bbox.y1 - obj.centroid.y, 0.0, obj.centroid.y - person.bbox.y2)
        distance = hypot(horizontal, vertical)
        diagonal = hypot(
            person.bbox.x2 - person.bbox.x1,
            person.bbox.y2 - person.bbox.y1,
        )
        return distance <= max(1.0, diagonal * self.object_proximity_ratio)

    def _is_due(self, track_id: int, timestamp: datetime) -> bool:
        previous = self._last_attempt.get(track_id)
        return previous is None or self._age_seconds(timestamp, previous) >= 1.0 / self.fps

    @staticmethod
    def _age_seconds(current: datetime, previous: datetime) -> float:
        return max(0.0, (current - previous).total_seconds())

    def _prune(self, timestamp: datetime, active_ids: set[int]) -> None:
        self._cache = {
            track_id: pose
            for track_id, pose in self._cache.items()
            if track_id in active_ids
            and self._age_seconds(timestamp, pose.timestamp) <= self.result_ttl_seconds
        }
        self._last_attempt = {
            track_id: attempted
            for track_id, attempted in self._last_attempt.items()
            if track_id in active_ids
        }

    def _ensure_initialized(self) -> bool:
        if self._landmarker is not None:
            return True
        if self._initialization_attempted:
            return False
        self._initialization_attempted = True
        if not self.model_path.is_file():
            logger.warning(
                "Pose deshabilitada: no existe el modelo MediaPipe en %s.",
                self.model_path,
            )
            return False
        try:
            import mediapipe as mp

            options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=self.min_detection_confidence,
                min_pose_presence_confidence=self.min_detection_confidence,
                output_segmentation_masks=False,
            )
            self._mediapipe = mp
            self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
            logger.info("MediaPipe Pose inicializado en modo selectivo.")
            return True
        except (ImportError, AttributeError, RuntimeError, ValueError) as exc:
            logger.warning("Pose deshabilitada; MediaPipe no pudo inicializarse: %s", exc)
            self._mediapipe = None
            self._landmarker = None
            return False

    def _analyze_person(
        self,
        frame: np.ndarray,
        person: TrackState,
        timestamp: datetime,
    ) -> PoseState | None:
        if not self._ensure_initialized():
            return None
        x1, y1, x2, y2 = self._crop_bounds(frame.shape, person)
        if x2 <= x1 or y2 <= y1:
            return None
        crop = frame[y1:y2, x1:x2]
        try:
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            image = self._mediapipe.Image(
                image_format=self._mediapipe.ImageFormat.SRGB,
                data=np.ascontiguousarray(rgb),
            )
            result = self._landmarker.detect(image)
        except (RuntimeError, ValueError, cv2.error) as exc:
            logger.warning("MediaPipe Pose falló para track #%s: %s", person.track_id, exc)
            return None
        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]
        width = x2 - x1
        height = y2 - y1
        points = {
            name: self._to_point(landmarks[index], x1, y1, width, height, frame.shape)
            for name, index in self._LANDMARK_INDEXES.items()
        }
        useful = [point for point in points.values() if point is not None]
        if not useful:
            return None
        return PoseState(
            track_id=person.track_id,
            timestamp=timestamp,
            confidence=sum(point.visibility for point in useful) / len(useful),
            **points,
        )

    def _crop_bounds(self, frame_shape: tuple[int, ...], person: TrackState) -> tuple[int, int, int, int]:
        frame_height, frame_width = frame_shape[:2]
        box_width = person.bbox.x2 - person.bbox.x1
        box_height = person.bbox.y2 - person.bbox.y1
        pad_x = box_width * self.crop_padding_ratio
        pad_y = box_height * self.crop_padding_ratio
        return (
            max(0, int(person.bbox.x1 - pad_x)),
            max(0, int(person.bbox.y1 - pad_y)),
            min(frame_width, int(person.bbox.x2 + pad_x + 0.999)),
            min(frame_height, int(person.bbox.y2 + pad_y + 0.999)),
        )

    def _to_point(
        self,
        landmark,
        crop_x: int,
        crop_y: int,
        crop_width: int,
        crop_height: int,
        frame_shape: tuple[int, ...],
    ) -> PosePoint | None:
        visibility = float(getattr(landmark, "visibility", 1.0) or 0.0)
        if visibility < self.min_landmark_visibility:
            return None
        frame_height, frame_width = frame_shape[:2]
        x = min(frame_width - 1, max(0.0, crop_x + float(landmark.x) * crop_width))
        y = min(frame_height - 1, max(0.0, crop_y + float(landmark.y) * crop_height))
        return PosePoint(x=x, y=y, visibility=min(1.0, max(0.0, visibility)))

    def reset(self) -> None:
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except RuntimeError as exc:
                logger.warning("MediaPipe Pose no pudo cerrarse limpiamente: %s", exc)
        self._mediapipe = None
        self._landmarker = None
        self._initialization_attempted = False
        self._last_attempt.clear()
        self._cache.clear()


def create_pose_analyzer(enabled: bool, **kwargs) -> PoseAnalyzer:
    """Fábrica que conserva un camino sin MediaPipe ni modelo descargado."""
    if not enabled:
        return NullPoseAnalyzer()
    return MediaPipePoseAnalyzer(**kwargs)
