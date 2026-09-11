from app.api.routes import debug
from app.speech.cached_warning import WarningPlaybackResult


def test_local_warning_endpoint_uses_offline_template(monkeypatch):
    monkeypatch.setattr(
        debug.CachedWarningSpeechService,
        "emit",
        lambda self: WarningPlaybackResult(
            emitted=True,
            source="local_template",
            audio_path="warning.wav",
        ),
    )

    response = debug.test_local_warning()

    assert response == {
        "played_locally": True,
        "source": "local_template",
        "audio_path": "warning.wav",
        "uses_openai": False,
    }
