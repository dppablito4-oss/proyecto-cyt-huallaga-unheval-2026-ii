from types import SimpleNamespace

import pytest

from app.metrics.collector import MetricsCollector
from app.models.metrics import SystemMetrics


class FakeProcess:
    def cpu_percent(self, interval=None):
        assert interval is None
        return 37.5

    def memory_info(self):
        return SimpleNamespace(rss=256 * 1024 * 1024)


def test_collector_measures_rates_latencies_resources_and_autonomy():
    collector = MetricsCollector(rate_window_seconds=2.0, process=FakeProcess())
    collector.record_stage("capture", at=10.0)
    collector.record_stage("capture", at=10.5)
    collector.record_stage("capture", at=11.0)
    collector.record_stage("detector", elapsed_ms=20, at=10.0)
    collector.record_stage("detector", elapsed_ms=40, at=11.0)
    collector.record_stage("tracker", elapsed_ms=5, at=10.0)
    collector.record_stage("tracker", elapsed_ms=15, at=11.0)
    collector.record_stage("pose", elapsed_ms=30, at=10.0, count=2)
    collector.record_stage("pose", elapsed_ms=50, at=11.0, count=2)
    collector.record_stage("event_engine", elapsed_ms=3, at=11.0)
    collector.record_openai_latency(800)
    collector.record_event_outcome("WARN", openai_used=False, local_confirmed=True)
    collector.record_event_outcome("LOG_ONLY", openai_used=True, local_confirmed=False)
    collector.record_event_outcome("IGNORE", openai_used=False, local_confirmed=False)

    snapshot = collector.snapshot(
        active_tracks=3,
        active_persons=1,
        active_objects=2,
        pose_active=1,
        suspicious_candidates=1,
        at=11.0,
    )

    assert snapshot.capture_fps == pytest.approx(2.0)
    assert snapshot.detector_fps == pytest.approx(1.0)
    assert snapshot.tracker_fps == pytest.approx(1.0)
    assert snapshot.pose_fps == pytest.approx(3.0)
    assert snapshot.detector_latency_ms == pytest.approx(24.0)
    assert snapshot.tracker_latency_ms == pytest.approx(7.0)
    assert snapshot.pose_latency_ms == pytest.approx(34.0)
    assert snapshot.event_engine_latency_ms == pytest.approx(3.0)
    assert snapshot.openai_latency_ms == pytest.approx(800.0)
    assert snapshot.cpu_percent == pytest.approx(37.5)
    assert snapshot.ram_mb == pytest.approx(256.0)
    assert snapshot.events_created == 3
    assert snapshot.events_ignored == 1
    assert snapshot.events_confirmed_local == 1
    assert snapshot.events_sent_openai == 1
    assert snapshot.openai_percentage == pytest.approx(100 / 3)
    assert snapshot.openai_fallback_ratio == pytest.approx(1 / 3)
    assert snapshot.local_decision_ratio == pytest.approx(2 / 3)
    assert snapshot.processing_level == "SUSPICIOUS"


def test_collector_bounds_history_ignores_manual_events_and_resets():
    collector = MetricsCollector(history_limit=2, process=FakeProcess())
    for index in range(3):
        collector.record_event_metrics(SystemMetrics(event_id=str(index)))
    collector.record_event_outcome(
        "WARN", openai_used=True, local_confirmed=False, autonomous=False
    )
    collector.record_stage("capture", at=1.0)
    collector.record_stage("capture", at=2.0)

    assert [item.event_id for item in collector.get_recent_metrics()] == ["1", "2"]
    assert collector.snapshot(at=2.0).events_created == 0

    collector.reset_runtime()

    assert collector.snapshot(at=2.0).capture_fps == 0.0


def test_collector_rejects_invalid_stage_and_count():
    collector = MetricsCollector(process=FakeProcess())
    with pytest.raises(ValueError, match="desconocida"):
        collector.record_stage("network")
    with pytest.raises(ValueError, match="al menos 1"):
        collector.record_stage("capture", count=0)
