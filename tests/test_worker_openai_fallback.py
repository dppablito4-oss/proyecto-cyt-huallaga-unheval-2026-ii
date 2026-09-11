from datetime import datetime, timedelta

import numpy as np

from app.camera.worker import VideoPipelineWorker
from app.config import settings
from app.models.analysis import AIAnalysisResult
from app.models.event import EventModel
from app.speech.cached_warning import WarningPlaybackResult


class FakeRepository:
    def __init__(self):
        self.saved = []

    def save(self, event):
        self.saved.append(event.model_copy(deep=True))
        return True


class FakeVisionAI:
    available = True
    last_call_used_api = True

    def __init__(self):
        self.calls = []

    def analyze_sequence(self, images, event_metadata=None):
        self.calls.append((list(images), dict(event_metadata or {})))
        return AIAnalysisResult(
            person_detected=True,
            suspected_disposal=True,
            action_completed=False,
            confidence=0.65,
            event_type="SUSPICIOUS_ACTION",
            description="La evidencia visual continúa ambigua.",
        )


class FakeWarningSpeech:
    def __init__(self):
        self.messages = []

    def emit(self, message=None):
        self.messages.append(message)
        return WarningPlaybackResult(True, "local_template", "warning.wav")


def make_event(event_id: str, state: str, score: float, released_at: datetime) -> EventModel:
    return EventModel(
        id=event_id,
        candidate_id=event_id,
        camera_id="CAM_TEST",
        started_at=released_at,
        local_event_state=state,
        local_event_score=score,
        release_detected=True,
        release_timestamp=released_at,
        release_zone="riverbank",
        object_stationary=state == "CONFIRMED",
        person_moving_away=state == "CONFIRMED",
        event_trace={"timestamps": {"released_at": released_at.isoformat()}},
    )


def test_confirmed_local_event_skips_openai(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_FALLBACK_ENABLED", True)
    worker = VideoPipelineWorker()
    vision = FakeVisionAI()
    repository = FakeRepository()
    worker._vision_ai = vision
    worker._repository = repository
    warning_speech = FakeWarningSpeech()
    worker._warning_speech = warning_speech
    event = make_event("confirmed", "CONFIRMED", 0.9, datetime.now())
    try:
        worker._process_event(event)

        assert vision.calls == []
        assert repository.saved[0].openai_used is False
        assert repository.saved[0].decision == "WARN"
        assert repository.saved[0].metrics["audio_source"] == "local_template"
        assert repository.saved[0].metrics["frames_sent"] == 0
        assert repository.saved[0].metrics["payload_bytes"] == 0
        assert repository.saved[0].metrics["openai_fallback_ratio"] == 0.0
        assert worker._metrics.get_recent_metrics(1)[0].decision == "WARN"
        assert warning_speech.messages == [None]
    finally:
        worker.stop()


def test_uncertain_event_sends_metadata_and_three_event_keyframes(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_FALLBACK_ENABLED", True)
    worker = VideoPipelineWorker()
    vision = FakeVisionAI()
    repository = FakeRepository()
    worker._vision_ai = vision
    worker._repository = repository
    worker._warning_speech = FakeWarningSpeech()
    released_at = datetime.now()
    for offset in (-2, -1, 0, 1, 2):
        worker._frame_buffer.add_frame(
            np.zeros((10, 10, 3), dtype=np.uint8),
            timestamp=released_at + timedelta(seconds=offset),
        )
        worker._frame_buffer._last_sample_time = None
    event = make_event("uncertain", "UNCERTAIN", 0.6, released_at)
    try:
        worker._process_event(event)

        images, metadata = vision.calls[0]
        assert len(images) == 3
        assert metadata["candidate_id"] == "uncertain"
        assert metadata["local_event_score"] == 0.6
        assert repository.saved[0].openai_used is True
        assert repository.saved[0].decision == "LOG_ONLY"
        assert repository.saved[0].metrics["frames_sent"] == 3
        assert repository.saved[0].metrics["payload_bytes"] == sum(map(len, images))
        assert repository.saved[0].metrics["openai_fallback_ratio"] == 1.0
        assert worker._metrics.get_recent_metrics(1)[0].ai_latency_ms >= 0.0
    finally:
        worker.stop()
