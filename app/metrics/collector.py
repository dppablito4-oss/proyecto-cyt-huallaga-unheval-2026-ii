"""Métricas de eventos y rendimiento en tiempo real, thread-safe y acotadas."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from datetime import datetime

import psutil

from app.models.metrics import RuntimeMetricsSnapshot, SystemMetrics


class MetricsCollector:
    """Agrega tasas, latencias, recursos y autonomía del nodo edge."""

    _STAGES = ("capture", "detector", "tracker", "pose", "event_engine")

    def __init__(
        self,
        history_limit: int = 1000,
        rate_window_seconds: float = 10.0,
        process=None,
    ):
        if history_limit < 1 or rate_window_seconds <= 0:
            raise ValueError("history_limit y rate_window_seconds deben ser positivos.")
        self.history: deque[SystemMetrics] = deque(maxlen=history_limit)
        self.rate_window_seconds = float(rate_window_seconds)
        self._stage_times = {stage: deque() for stage in self._STAGES}
        self._latency_ema = {stage: 0.0 for stage in self._STAGES if stage != "capture"}
        self._openai_latency_ms = 0.0
        self._events_created = 0
        self._events_ignored = 0
        self._events_confirmed_local = 0
        self._events_sent_openai = 0
        self._process = process or psutil.Process(os.getpid())
        self._lock = threading.Lock()

    def record_event_metrics(self, metrics: SystemMetrics) -> None:
        with self._lock:
            self.history.append(metrics)

    def get_recent_metrics(self, limit: int = 50) -> list[SystemMetrics]:
        with self._lock:
            return list(self.history)[-limit:]

    def record_stage(
        self,
        stage: str,
        elapsed_ms: float | None = None,
        at: float | None = None,
        count: int = 1,
    ) -> None:
        if stage not in self._stage_times:
            raise ValueError(f"Etapa de métricas desconocida: {stage}")
        if count < 1:
            raise ValueError("count debe ser al menos 1.")
        observed_at = time.monotonic() if at is None else float(at)
        with self._lock:
            times = self._stage_times[stage]
            times.extend([observed_at] * count)
            self._prune(times, observed_at)
            if elapsed_ms is not None and stage in self._latency_ema:
                current = self._latency_ema[stage]
                value = max(0.0, float(elapsed_ms))
                self._latency_ema[stage] = value if current == 0 else current * 0.8 + value * 0.2

    def record_openai_latency(self, elapsed_ms: float) -> None:
        with self._lock:
            value = max(0.0, float(elapsed_ms))
            self._openai_latency_ms = (
                value
                if self._openai_latency_ms == 0
                else self._openai_latency_ms * 0.8 + value * 0.2
            )

    def record_event_outcome(
        self,
        decision: str,
        openai_used: bool,
        local_confirmed: bool,
        autonomous: bool = True,
    ) -> None:
        if not autonomous:
            return
        with self._lock:
            self._events_created += 1
            self._events_ignored += decision == "IGNORE"
            self._events_sent_openai += bool(openai_used)
            self._events_confirmed_local += bool(local_confirmed)

    def snapshot(
        self,
        active_tracks: int = 0,
        active_persons: int = 0,
        active_objects: int = 0,
        pose_active: int = 0,
        suspicious_candidates: int = 0,
        at: float | None = None,
    ) -> RuntimeMetricsSnapshot:
        observed_at = time.monotonic() if at is None else float(at)
        with self._lock:
            for times in self._stage_times.values():
                self._prune(times, observed_at)
            rates = {
                stage: self._rate(times)
                for stage, times in self._stage_times.items()
            }
            events = self._events_created
            openai_ratio = self._events_sent_openai / events if events else 0.0
            local_ratio = (events - self._events_sent_openai) / events if events else 0.0
            latencies = dict(self._latency_ema)
            openai_latency = self._openai_latency_ms
            event_counts = (
                self._events_created,
                self._events_ignored,
                self._events_confirmed_local,
                self._events_sent_openai,
            )
        try:
            cpu_percent = max(0.0, float(self._process.cpu_percent(interval=None)))
            ram_mb = max(0.0, float(self._process.memory_info().rss) / (1024 * 1024))
        except (psutil.Error, AttributeError, OSError):
            cpu_percent = 0.0
            ram_mb = 0.0

        if suspicious_candidates:
            processing_level = "SUSPICIOUS"
        elif active_objects and active_persons:
            processing_level = "OBJECT_INTERACTION"
        elif active_persons:
            processing_level = "PERSON_PRESENT"
        else:
            processing_level = "IDLE"
        return RuntimeMetricsSnapshot(
            timestamp=datetime.now(),
            capture_fps=rates["capture"],
            detector_fps=rates["detector"],
            tracker_fps=rates["tracker"],
            pose_fps=rates["pose"],
            detector_latency_ms=latencies["detector"],
            tracker_latency_ms=latencies["tracker"],
            pose_latency_ms=latencies["pose"],
            event_engine_latency_ms=latencies["event_engine"],
            openai_latency_ms=openai_latency,
            cpu_percent=cpu_percent,
            ram_mb=ram_mb,
            active_tracks=active_tracks,
            active_persons=active_persons,
            active_objects=active_objects,
            pose_active=pose_active,
            events_created=event_counts[0],
            events_ignored=event_counts[1],
            events_confirmed_local=event_counts[2],
            events_sent_openai=event_counts[3],
            openai_percentage=openai_ratio * 100.0,
            openai_fallback_ratio=openai_ratio,
            local_decision_ratio=local_ratio,
            processing_level=processing_level,
        )

    def _prune(self, times: deque[float], observed_at: float) -> None:
        cutoff = observed_at - self.rate_window_seconds
        while times and times[0] < cutoff:
            times.popleft()

    @staticmethod
    def _rate(times: deque[float]) -> float:
        if len(times) < 2:
            return 0.0
        span = times[-1] - times[0]
        return (len(times) - 1) / span if span > 0 else 0.0

    def reset_runtime(self) -> None:
        with self._lock:
            for times in self._stage_times.values():
                times.clear()
            for stage in self._latency_ema:
                self._latency_ema[stage] = 0.0
            self._openai_latency_ms = 0.0
            self._events_created = 0
            self._events_ignored = 0
            self._events_confirmed_local = 0
            self._events_sent_openai = 0
