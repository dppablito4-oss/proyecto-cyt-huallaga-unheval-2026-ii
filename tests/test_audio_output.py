import sys
from pathlib import Path
from types import SimpleNamespace

from app.config import settings
from app.speech.audio_output import LocalSpeakerOutput
from app.speech.openai_tts import OpenAISpeechService


class ImmediateThread:
    """Sustituto determinista que ejecuta el target al llamar start()."""

    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        self.target(*self.args)


class RecordingAudioOutput:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.played_paths = []

    def play(self, audio_path):
        self.played_paths.append(audio_path)
        return self.succeeds


def test_local_speaker_play_starts_background_player(tmp_path, monkeypatch):
    audio_path = tmp_path / "warning.wav"
    audio_path.write_bytes(b"RIFF-test")
    played_paths = []

    monkeypatch.setattr("app.speech.audio_output.threading.Thread", ImmediateThread)
    monkeypatch.setattr(
        LocalSpeakerOutput,
        "_play_system",
        staticmethod(lambda file_path: played_paths.append(file_path)),
    )

    assert LocalSpeakerOutput().play(str(audio_path)) is True
    assert played_paths == [str(audio_path.resolve())]


def test_local_speaker_play_rejects_missing_file(tmp_path):
    missing_path = tmp_path / "missing.wav"

    assert LocalSpeakerOutput().play(str(missing_path)) is False


def test_non_pcm_fallback_generates_and_plays_file(tmp_path, monkeypatch):
    output_path = tmp_path / "warning.mp3"
    service = OpenAISpeechService(api_key="test-key")
    audio_output = RecordingAudioOutput()

    monkeypatch.setattr(settings, "OPENAI_TTS_RESPONSE_FORMAT", "mp3")
    monkeypatch.setattr(service, "generate_speech", lambda text, path: str(output_path))

    result = service.generate_and_play_streaming("Mensaje de prueba", str(output_path), audio_output)

    assert result == str(output_path)
    assert audio_output.played_paths == [str(output_path)]


def test_non_pcm_fallback_reports_playback_failure(tmp_path, monkeypatch):
    output_path = tmp_path / "warning.mp3"
    service = OpenAISpeechService(api_key="test-key")
    audio_output = RecordingAudioOutput(succeeds=False)

    monkeypatch.setattr(settings, "OPENAI_TTS_RESPONSE_FORMAT", "mp3")
    monkeypatch.setattr(service, "generate_speech", lambda text, path: str(output_path))

    result = service.generate_and_play_streaming("Mensaje de prueba", str(output_path), audio_output)

    assert result is None
    assert audio_output.played_paths == [str(output_path)]


def test_generate_speech_matches_requested_file_extension(tmp_path, monkeypatch):
    output_path = tmp_path / "warning.wav"
    requests = []

    class FakeResponse:
        def stream_to_file(self, path):
            Path(path).write_bytes(b"RIFF-test")

    class FakeSpeech:
        def create(self, **kwargs):
            requests.append(kwargs)
            return FakeResponse()

    fake_client = SimpleNamespace(audio=SimpleNamespace(speech=FakeSpeech()))
    fake_openai = SimpleNamespace(OpenAI=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    service = OpenAISpeechService(api_key="test-key")
    result = service.generate_speech("Mensaje de prueba", str(output_path))

    assert result == str(output_path)
    assert output_path.is_file()
    assert requests[0]["response_format"] == "wav"
