"""Limitadores temporales simples para frecuencias de percepción."""

from __future__ import annotations

import time


class MonotonicRateLimiter:
    """Autoriza trabajo por tiempo monotónico, sin depender del número de frames."""

    def __init__(self, fps: float):
        if fps <= 0:
            raise ValueError("fps debe ser mayor que cero.")
        self.fps = float(fps)
        self.interval = 1.0 / self.fps
        self._last_run: float | None = None

    def is_due(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else float(now)
        if self._last_run is None or current - self._last_run >= self.interval:
            self._last_run = current
            return True
        return False

    def reset(self) -> None:
        self._last_run = None
