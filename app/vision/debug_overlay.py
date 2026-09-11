"""Overlay opcional para inspeccionar tracking y zonas sin alterar la evidencia."""

from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

from app.models.scene import SceneState
from app.models.tracking import TrackState
from app.vision.zones import ZoneManager


class VisionDebugOverlay:
    """Dibuja cajas, IDs, zonas y trayectorias sobre una copia del frame."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def annotate(
        self,
        frame: np.ndarray,
        scene: SceneState,
        zone_manager: ZoneManager,
    ) -> np.ndarray:
        if not self.enabled:
            return frame

        import supervision as sv

        annotated = frame.copy()
        tracks = [*scene.persons.values(), *scene.objects.values()]
        for name, polygon in zone_manager.pixel_polygons(frame.shape).items():
            cv2.polylines(annotated, [polygon], isClosed=True, color=(0, 190, 255), thickness=2)
            anchor = tuple(int(value) for value in polygon[0])
            occupancy = scene.zones.get(name)
            count = occupancy.occupancy if occupancy is not None else 0
            cv2.putText(
                annotated,
                f"{name} ({count})",
                (anchor[0] + 4, max(18, anchor[1] + 18)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 190, 255),
                1,
                cv2.LINE_AA,
            )

        if not tracks:
            return annotated

        detections = self._to_detections(tracks)
        box_annotator = sv.BoxAnnotator(color_lookup=sv.ColorLookup.TRACK, thickness=2)
        label_annotator = sv.LabelAnnotator(
            color_lookup=sv.ColorLookup.TRACK,
            text_scale=0.45,
            text_padding=4,
        )
        annotated = box_annotator.annotate(scene=annotated, detections=detections)
        associations_by_object = {
            association.object_track_id: association
            for association in scene.associations
        }
        labels = []
        for track in tracks:
            label = (
                f"{'Persona' if track.label.casefold() == 'person' else track.label} "
                f"#{track.track_id} | {track.current_zone or 'sin zona'}"
            )
            association = associations_by_object.get(track.track_id)
            if association is not None:
                status = "OK" if association.confirmed else "?"
                label += (
                    f" | P#{association.person_track_id} "
                    f"{association.association_score:.2f} {status}"
                )
            object_state = scene.object_states.get(track.track_id)
            if object_state is not None:
                label += f" | {object_state.state.value}"
                if object_state.throw_detected:
                    label += " | LANZAMIENTO"
            labels.append(label)
        annotated = label_annotator.annotate(
            scene=annotated,
            detections=detections,
            labels=labels,
        )
        for association in scene.associations:
            person = scene.persons.get(association.person_track_id)
            obj = scene.objects.get(association.object_track_id)
            if person is None or obj is None:
                continue
            color = (70, 220, 120) if association.confirmed else (0, 190, 255)
            cv2.line(
                annotated,
                (round(person.centroid.x), round(person.centroid.y)),
                (round(obj.centroid.x), round(obj.centroid.y)),
                color,
                2,
                cv2.LINE_AA,
            )
        for person in scene.persons.values():
            if person.pose is not None:
                self._draw_pose(annotated, person)
        for track in tracks:
            points = np.asarray(
                [
                    [round(point.position.x), round(point.position.y)]
                    for point in track.trajectory
                ],
                dtype=np.int32,
            )
            if len(points) >= 2:
                color = sv.ColorPalette.DEFAULT.by_idx(track.track_id).as_bgr()
                cv2.polylines(
                    annotated,
                    [points],
                    isClosed=False,
                    color=color,
                    thickness=2,
                )
        return annotated

    @staticmethod
    def _draw_pose(frame: np.ndarray, person: TrackState) -> None:
        """Dibuja sólo hombros, codos, muñecas y caderas conservados."""
        pose = person.pose
        if pose is None:
            return
        connections = (
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"),
            ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"),
            ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"),
            ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
        )
        for start_name, end_name in connections:
            start = getattr(pose, start_name)
            end = getattr(pose, end_name)
            if start is None or end is None:
                continue
            cv2.line(
                frame,
                (round(start.x), round(start.y)),
                (round(end.x), round(end.y)),
                (255, 120, 40),
                2,
                cv2.LINE_AA,
            )
        for name in (
            "left_shoulder",
            "right_shoulder",
            "left_elbow",
            "right_elbow",
            "left_wrist",
            "right_wrist",
            "left_hip",
            "right_hip",
        ):
            point = getattr(pose, name)
            if point is not None:
                cv2.circle(frame, (round(point.x), round(point.y)), 4, (255, 200, 40), -1)

    @staticmethod
    def _to_detections(tracks: Sequence[TrackState]):
        import supervision as sv

        return sv.Detections(
            xyxy=np.asarray(
                [
                    [track.bbox.x1, track.bbox.y1, track.bbox.x2, track.bbox.y2]
                    for track in tracks
                ],
                dtype=np.float32,
            ),
            confidence=np.asarray([track.confidence for track in tracks], dtype=np.float32),
            class_id=np.asarray([track.class_id for track in tracks], dtype=np.int32),
            tracker_id=np.asarray([track.track_id for track in tracks], dtype=np.int32),
        )
