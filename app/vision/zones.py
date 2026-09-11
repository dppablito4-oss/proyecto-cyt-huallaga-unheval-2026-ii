"""Zonas ambientales poligonales construidas sobre Supervision."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from app.models.scene import NormalizedPoint, ZoneDefinition, ZoneState
from app.models.tracking import TrackedObject

logger = logging.getLogger(__name__)


class ZoneManager:
    """Carga zonas por cámara, las escala al frame y localiza tracks."""

    def __init__(self, camera_id: str, zones: Sequence[ZoneDefinition]):
        self.camera_id = camera_id
        self.zones = list(zones)
        self._scaled_cache: dict[tuple[int, int], dict[str, np.ndarray]] = {}

    @classmethod
    def from_json(cls, path: Path | str, camera_id: str) -> "ZoneManager":
        config_path = Path(path)
        if not config_path.exists():
            logger.warning("Configuración de zonas no encontrada: %s", config_path)
            return cls(camera_id, [])

        payload = json.loads(config_path.read_text(encoding="utf-8"))
        camera_config = payload.get(camera_id, {})
        raw_zones = camera_config.get("zones", {})
        zones: list[ZoneDefinition] = []
        for name, raw_definition in raw_zones.items():
            if isinstance(raw_definition, list):
                polygon = raw_definition
                priority = 0
            else:
                polygon = raw_definition.get("polygon", [])
                priority = raw_definition.get("priority", 0)
            zones.append(
                ZoneDefinition(
                    name=name,
                    polygon=[
                        NormalizedPoint(x=float(point[0]), y=float(point[1]))
                        for point in polygon
                    ],
                    priority=priority,
                )
            )
        return cls(camera_id, zones)

    def pixel_polygons(self, frame_shape: Sequence[int]) -> dict[str, np.ndarray]:
        height, width = int(frame_shape[0]), int(frame_shape[1])
        if height <= 0 or width <= 0:
            raise ValueError("El frame debe tener dimensiones positivas.")
        cache_key = (width, height)
        if cache_key not in self._scaled_cache:
            self._scaled_cache[cache_key] = {
                zone.name: np.asarray(
                    [
                        [
                            min(width - 1, round(point.x * width)),
                            min(height - 1, round(point.y * height)),
                        ]
                        for point in zone.polygon
                    ],
                    dtype=np.int32,
                )
                for zone in self.zones
            }
        return {
            name: polygon.copy()
            for name, polygon in self._scaled_cache[cache_key].items()
        }

    def locate(
        self,
        tracks: Sequence[TrackedObject],
        frame_shape: Sequence[int],
    ) -> tuple[dict[int, str | None], dict[str, ZoneState]]:
        """Asigna una zona por prioridad usando el ancla inferior central."""
        zone_states = {
            zone.name: ZoneState(name=zone.name)
            for zone in self.zones
        }
        assignments = {track.track_id: None for track in tracks}
        if not tracks or not self.zones:
            return assignments, zone_states

        import supervision as sv

        detections = sv.Detections(
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
        polygons = self.pixel_polygons(frame_shape)
        ordered_zones = sorted(
            enumerate(self.zones),
            key=lambda item: (-item[1].priority, item[0]),
        )
        for _, definition in ordered_zones:
            polygon_zone = sv.PolygonZone(polygon=polygons[definition.name])
            inside = polygon_zone.trigger(detections)
            for index, is_inside in enumerate(inside):
                if not is_inside:
                    continue
                track_id = tracks[index].track_id
                zone_states[definition.name].track_ids.append(track_id)
                if assignments[track_id] is None:
                    assignments[track_id] = definition.name
        return assignments, zone_states
