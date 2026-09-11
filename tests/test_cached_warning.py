from pathlib import Path

from app.speech.cached_warning import CachedWarningSpeechService


class FakeAudioOutput:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.played = []

    def play(self, path):
        self.played.append(path)
        return self.succeeds


class FakeTTS:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.calls = []

    def generate_and_play_streaming(self, text, output_path, audio_output):
        self.calls.append((text, output_path, audio_output))
        return output_path if self.succeeds else None


def make_service(tmp_path, audio, tts, template_exists=True):
    template = tmp_path / "templates" / "warning.wav"
    if template_exists:
        template.parent.mkdir()
        template.write_bytes(b"RIFF-local")
    return CachedWarningSpeechService(
        template_path=template,
        cache_dir=tmp_path / "cache",
        generic_message="Mensaje genérico",
        audio_output=audio,
        tts_fallback=tts,
    )


def test_local_template_has_priority_over_dynamic_tts(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS()
    service = make_service(tmp_path, audio, tts)

    result = service.emit("Un mensaje dinámico para este caso")

    assert result.emitted is True
    assert result.source == "local_template"
    assert audio.played == [str(service.template_path)]
    assert tts.calls == []


def test_dynamic_message_uses_openai_only_when_local_template_is_unavailable(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS()
    service = make_service(tmp_path, audio, tts, template_exists=False)

    result = service.emit("Mensaje dinámico")

    assert result.emitted is True
    assert result.source == "openai_tts"
    assert len(tts.calls) == 1
    assert Path(tts.calls[0][1]).parent == tmp_path / "cache"


def test_equivalent_dynamic_message_reuses_hash_cache(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS()
    service = make_service(tmp_path, audio, tts, template_exists=False)
    cached = service._cache_path("Mensaje   Dinámico")
    cached.parent.mkdir()
    cached.write_bytes(b"RIFF-cache")

    result = service.emit("  mensaje dinámico ")

    assert result.source == "tts_cache"
    assert audio.played == [str(cached)]
    assert tts.calls == []


def test_audio_failure_returns_none_without_raising(tmp_path):
    audio = FakeAudioOutput(succeeds=False)
    tts = FakeTTS(succeeds=False)
    service = make_service(tmp_path, audio, tts)

    result = service.emit("Mensaje dinámico")

    assert result.emitted is False
    assert result.source == "none"
