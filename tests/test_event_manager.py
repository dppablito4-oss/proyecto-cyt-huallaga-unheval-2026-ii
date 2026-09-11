from datetime import datetime, timedelta

from app.events.manager import EventManager
from app.models.event import LocalDetectionSummary
from app.models.reasoning import EventCandidate, EventCandidateState, EventEvidence


def make_candidate(
    candidate_id: str = "candidate-1",
    state: EventCandidateState = EventCandidateState.UNCERTAIN,
    score: float = 0.6,
) -> EventCandidate:
    now = datetime.now()
    evidence = EventEvidence(
        person_present=True,
        object_present=True,
        object_was_carried=True,
        release_detected=True,
        release_zone="riverbank",
        object_stationary=state is EventCandidateState.CONFIRMED,
        stationary_duration=2.1 if state is EventCandidateState.CONFIRMED else 0,
        person_moving_away=state is EventCandidateState.CONFIRMED,
        association_peak=0.9,
        carried_duration=1.2,
        timestamps={"released_at": now},
    )
    return EventCandidate(
        id=candidate_id,
        camera_id="CAM_TEST",
        person_track_id=1,
        object_track_id=8,
        object_class="bottle",
        event_type="WASTE_DISPOSAL",
        score=score,
        state=state,
        evidence=evidence,
        started_at=now,
        updated_at=now,
    )


def test_event_manager_creates_event_from_candidate_and_maps_local_evidence():
    manager = EventManager(cooldown_seconds=10)
    candidate = make_candidate()
    detection = LocalDetectionSummary(persons=1, max_confidence=0.9)

    assert manager.should_trigger_event(candidate) is True
    event = manager.create_event(candidate, detection)

    assert event.id == candidate.id
    assert event.local_detection == detection
    assert event.person_track_id == 1
    assert event.object_track_id == 8
    assert event.local_event_score == 0.6
    assert event.local_event_state == "UNCERTAIN"
    assert event.release_detected is True
    assert event.release_zone == "riverbank"
    assert event.event_trace["association_peak"] == 0.9
    assert manager.should_trigger_event(candidate) is False


def test_event_manager_deduplicates_candidate_after_completion():
    manager = EventManager(cooldown_seconds=0)
    candidate = make_candidate()
    event = manager.create_event(candidate)
    manager.complete_event(event)

    assert manager.should_trigger_event(candidate) is False
    assert manager.should_trigger_event(make_candidate("candidate-2")) is True


def test_presence_or_ignored_candidate_cannot_trigger_event():
    manager = EventManager(cooldown_seconds=0)
    presence = LocalDetectionSummary(persons=3, max_confidence=0.99)
    ignored = make_candidate(state=EventCandidateState.IGNORE, score=0.2)

    assert manager.should_trigger_event(presence) is False
    assert manager.should_trigger_event(ignored) is False
    assert manager.select_candidate([ignored]) is None


def test_candidate_selection_prioritizes_confirmed_then_score():
    manager = EventManager(cooldown_seconds=0)
    uncertain = make_candidate("uncertain", EventCandidateState.UNCERTAIN, 0.72)
    confirmed = make_candidate("confirmed", EventCandidateState.CONFIRMED, 0.8)

    assert manager.select_candidate([uncertain, confirmed]) == confirmed


def test_candidate_waits_for_configured_post_event_context():
    manager = EventManager(cooldown_seconds=0, minimum_context_seconds=1.0)
    candidate = make_candidate()

    assert manager.should_trigger_event(candidate) is False
    candidate.updated_at = candidate.started_at + timedelta(seconds=1)

    assert manager.should_trigger_event(candidate) is True
