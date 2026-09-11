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


def make_service(tmp_path, audio, tts, template_exists=True, catalog_count=0):
    template = tmp_path / "templates" / "warning.wav"
    if template_exists:
        template.parent.mkdir(exist_ok=True)
        template.write_bytes(b"RIFF-local")
    catalog = []
    for index in range(catalog_count):
        catalog_path = tmp_path / "templates" / f"openai_warning_{index + 1:02d}.wav"
        catalog_path.parent.mkdir(exist_ok=True)
        catalog_path.write_bytes(b"RIFF-openai")
        catalog.append(catalog_path)
    return CachedWarningSpeechService(
        template_path=template,
        cache_dir=tmp_path / "cache",
        generic_message="Mensaje genérico",
        audio_output=audio,
        tts_fallback=tts,
        catalog_paths=catalog,
    )


def test_dynamic_message_uses_openai_before_local_template(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS()
    service = make_service(tmp_path, audio, tts)

    result = service.emit("Un mensaje dinámico para este caso")

    assert result.emitted is True
    assert result.source == "openai_tts"
    assert audio.played == []
    assert len(tts.calls) == 1


def test_dynamic_message_uses_openai_when_local_template_is_unavailable(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS()
    service = make_service(tmp_path, audio, tts, template_exists=False)

    result = service.emit("Mensaje dinámico")

    assert result.emitted is True
    assert result.source == "openai_tts"
    assert len(tts.calls) == 1
    assert Path(tts.calls[0][1]).parent == tmp_path / "cache"


def test_confirmed_local_event_rotates_openai_catalog(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS()
    service = make_service(tmp_path, audio, tts, catalog_count=2)

    first = service.emit()
    second = service.emit()
    third = service.emit()

    assert [first.source, second.source, third.source] == [
        "openai_template",
        "openai_template",
        "openai_template",
    ]
    assert [Path(path).name for path in audio.played] == [
        "openai_warning_01.wav",
        "openai_warning_02.wav",
        "openai_warning_01.wav",
    ]
    assert tts.calls == []


def test_openai_failure_falls_back_to_pre_generated_catalog(tmp_path):
    audio = FakeAudioOutput()
    tts = FakeTTS(succeeds=False)
    service = make_service(tmp_path, audio, tts, catalog_count=1)

    result = service.emit("Mensaje dinámico")

    assert result.emitted is True
    assert result.source == "openai_template"
    assert Path(audio.played[0]).name == "openai_warning_01.wav"


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
    service = make_service(tmp_path, audio, tts, catalog_count=1)

    result = service.emit("Mensaje dinámico")

    assert result.emitted is False
    assert result.source == "none"
