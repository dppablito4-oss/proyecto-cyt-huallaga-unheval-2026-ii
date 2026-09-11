from datetime import datetime

from app.events.manager import EventManager
from app.events.rules import DecisionEngine
from app.models.reasoning import EventCandidate, EventCandidateState, EventEvidence
from app.speech.cached_warning import CachedWarningSpeechService


class FakeAudioOutput:
    def __init__(self):
        self.played = []

    def play(self, path):
        self.played.append(path)
        return True


class ForbiddenTTS:
    def generate_and_play_streaming(self, *args, **kwargs):
        raise AssertionError("Una alerta local confirmada no debe depender de OpenAI TTS.")


def test_confirmed_trash_bag_throw_emits_local_warning_without_cloud(tmp_path):
    now = datetime.now()
    candidate = EventCandidate(
        id="trash-bag-throw",
        camera_id="CAM_TEST",
        person_track_id=1,
        object_track_id=8,
        object_class="trash bag",
        event_type="WASTE_DISPOSAL",
        score=0.76,
        state=EventCandidateState.CONFIRMED,
        evidence=EventEvidence(
            person_present=True,
            object_present=True,
            object_was_carried=True,
            release_detected=True,
            release_zone="riverbank",
            throw_detected=True,
            object_stationary=False,
            person_moving_away=False,
            association_peak=0.9,
            carried_duration=1.2,
            timestamps={"released_at": now},
        ),
        started_at=now,
        updated_at=now,
    )
    event = EventManager(cooldown_seconds=0, minimum_context_seconds=2.2).create_event(
        candidate
    )

    decision = DecisionEngine(local_confirm_threshold=0.75).evaluate(event)

    template = tmp_path / "warning.wav"
    template.write_bytes(b"RIFF-local-warning")
    output = FakeAudioOutput()
    playback = CachedWarningSpeechService(
        template_path=template,
        cache_dir=tmp_path / "cache",
        generic_message="Recoge el residuo.",
        audio_output=output,
        tts_fallback=ForbiddenTTS(),
    ).emit()

    assert event.object_class == "trash bag"
    assert event.throw_detected is True
    assert decision == "WARN"
    assert playback.emitted is True
    assert playback.source == "local_template"
    assert output.played == [str(template)]
