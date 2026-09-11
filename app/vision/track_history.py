"""Historial temporal acotado para trayectorias de tracking."""

from collections import deque
from datetime import datetime, timedelta
from math import hypot
from threading import RLock
from typing import Deque, Optional

from app.models.tracking import Point, TrajectoryPoint


class TrackHistory:
    """Conserva una ventana temporal y deriva movimiento sin crecer indefinidamente."""

    def __init__(self, track_id: int, window_seconds: float = 15.0):
        if track_id < 0:
            raise ValueError("track_id debe ser no negativo.")
        if window_seconds <= 0:
            raise ValueError("window_seconds debe ser mayor que cero.")
        self.track_id = track_id
        self.window_seconds = float(window_seconds)
        self._trajectory: Deque[TrajectoryPoint] = deque()
        self._lock = RLock()

    def add(self, position: Point, timestamp: datetime, zone: Optional[str] = None) -> None:
        """Agrega una observación cronológica y elimina las que salieron de la ventana."""
        with self._lock:
            if self._trajectory and timestamp < self._trajectory[-1].timestamp:
                raise ValueError("Las observaciones de un track deben ser cronológicas.")
            self._trajectory.append(
                TrajectoryPoint(position=position.model_copy(deep=True), timestamp=timestamp, zone=zone)
            )
            self._prune(timestamp)

    def _prune(self, reference: datetime) -> None:
        cutoff = reference - timedelta(seconds=self.window_seconds)
        while self._trajectory and self._trajectory[0].timestamp < cutoff:
            self._trajectory.popleft()

    def set_latest_zone(self, zone: Optional[str]) -> None:
        """Actualiza la zona de la observación más reciente tras el cálculo espacial."""
        with self._lock:
            if self._trajectory:
                self._trajectory[-1].zone = zone

    @property
    def trajectory(self) -> list[TrajectoryPoint]:
        with self._lock:
            return [point.model_copy(deep=True) for point in self._trajectory]

    @property
    def first_seen(self) -> Optional[datetime]:
        with self._lock:
            return self._trajectory[0].timestamp if self._trajectory else None

    @property
    def last_seen(self) -> Optional[datetime]:
        with self._lock:
            return self._trajectory[-1].timestamp if self._trajectory else None

    @property
    def visible_duration(self) -> float:
        with self._lock:
            if len(self._trajectory) < 2:
                return 0.0
            return max(0.0, (self._trajectory[-1].timestamp - self._trajectory[0].timestamp).total_seconds())

    @property
    def current_zone(self) -> Optional[str]:
        with self._lock:
            return self._trajectory[-1].zone if self._trajectory else None

    @property
    def previous_zone(self) -> Optional[str]:
        with self._lock:
            if len(self._trajectory) < 2:
                return None
            current = self._trajectory[-1].zone
            for point in reversed(list(self._trajectory)[:-1]):
                if point.zone != current:
                    return point.zone
            return None

    @property
    def velocity(self) -> tuple[float, float]:
        """Velocidad entre las dos observaciones más recientes, en píxeles/segundo."""
        with self._lock:
            if len(self._trajectory) < 2:
                return 0.0, 0.0
            previous, current = self._trajectory[-2], self._trajectory[-1]
            elapsed = (current.timestamp - previous.timestamp).total_seconds()
            if elapsed <= 0:
                return 0.0, 0.0
            return (
                (current.position.x - previous.position.x) / elapsed,
                (current.position.y - previous.position.y) / elapsed,
            )

    @property
    def speed(self) -> float:
        velocity_x, velocity_y = self.velocity
        return hypot(velocity_x, velocity_y)

    @property
    def direction(self) -> Point:
        """Vector unitario de dirección; (0, 0) representa reposo."""
        velocity_x, velocity_y = self.velocity
        magnitude = hypot(velocity_x, velocity_y)
        if magnitude == 0:
            return Point(x=0.0, y=0.0)
        return Point(x=velocity_x / magnitude, y=velocity_y / magnitude)

    @property
    def distance_travelled(self) -> float:
        with self._lock:
            points = list(self._trajectory)
        return sum(
            hypot(
                current.position.x - previous.position.x,
                current.position.y - previous.position.y,
            )
            for previous, current in zip(points, points[1:])
        )
