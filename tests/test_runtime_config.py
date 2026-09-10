from app.camera.worker import VideoPipelineWorker
from app.api.routes.config import ConfigUpdateModel, update_config
from app.config import settings
from app.state import system_state


def test_worker_applies_runtime_config_to_live_components(monkeypatch):
    original_frames = settings.FRAMES_PER_ANALYSIS
    original_quality = settings.JPEG_QUALITY
    original_threshold = settings.AI_WARNING_THRESHOLD
    monkeypatch.setattr(settings, "FRAMES_PER_ANALYSIS", original_frames)
    monkeypatch.setattr(settings, "JPEG_QUALITY", original_quality)
    monkeypatch.setattr(settings, "AI_WARNING_THRESHOLD", original_threshold)

    worker = VideoPipelineWorker()
    try:
        applied = worker.apply_runtime_config(
            frames_per_analysis=4,
            jpeg_quality=55,
            ai_warning_threshold=0.91,
        )

        assert applied == {
            "FRAMES_PER_ANALYSIS": 4,
            "JPEG_QUALITY": 55,
            "AI_WARNING_THRESHOLD": 0.91,
        }
        assert settings.FRAMES_PER_ANALYSIS == 4
        assert settings.JPEG_QUALITY == 55
        assert settings.AI_WARNING_THRESHOLD == 0.91
        assert worker._frame_selector.target_frames == 4
        assert worker._image_processor.jpeg_quality == 55
        assert worker._decision_engine.warning_threshold == 0.91
        assert system_state.to_dict()["frames_per_analysis"] == 4
    finally:
        settings.FRAMES_PER_ANALYSIS = original_frames
        settings.JPEG_QUALITY = original_quality
        settings.AI_WARNING_THRESHOLD = original_threshold
        system_state.set_frames_per_analysis(original_frames)


def test_worker_runtime_config_accepts_partial_update(monkeypatch):
    original_frames = settings.FRAMES_PER_ANALYSIS
    original_quality = settings.JPEG_QUALITY
    original_threshold = settings.AI_WARNING_THRESHOLD
    monkeypatch.setattr(settings, "FRAMES_PER_ANALYSIS", original_frames)
    monkeypatch.setattr(settings, "JPEG_QUALITY", original_quality)
    monkeypatch.setattr(settings, "AI_WARNING_THRESHOLD", original_threshold)

    worker = VideoPipelineWorker()
    try:
        applied = worker.apply_runtime_config(ai_warning_threshold=0.87)

        assert applied == {"AI_WARNING_THRESHOLD": 0.87}
        assert worker._frame_selector.target_frames == original_frames
        assert worker._image_processor.jpeg_quality == original_quality
        assert worker._decision_engine.warning_threshold == 0.87
    finally:
        settings.FRAMES_PER_ANALYSIS = original_frames
        settings.JPEG_QUALITY = original_quality
        settings.AI_WARNING_THRESHOLD = original_threshold


def test_config_endpoint_delegates_updates_to_live_worker(monkeypatch):
    calls = []

    class RecordingWorker:
        def apply_runtime_config(self, **kwargs):
            calls.append(kwargs)
            return {"JPEG_QUALITY": kwargs["jpeg_quality"]}

    monkeypatch.setattr("app.main.pipeline_worker", RecordingWorker())

    response = update_config(ConfigUpdateModel(jpeg_quality=62))

    assert calls == [{
        "frames_per_analysis": None,
        "jpeg_quality": 62,
        "ai_warning_threshold": None,
    }]
    assert response == {
        "message": "Configuración actualizada correctamente.",
        "updated": {"JPEG_QUALITY": 62},
    }
