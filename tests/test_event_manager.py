import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.events.manager import EventManager
from app.models.event import LocalDetectionSummary

def test_event_manager_cooldown():
    manager = EventManager(cooldown_seconds=10)
    detection = LocalDetectionSummary(persons=1, max_confidence=0.90)

    # Primer evento debe crearse
    assert manager.should_trigger_event(detection) is True
    event = manager.create_event(detection)
    assert event is not None

    # Durante el cooldown no debe crearse otro evento
    assert manager.should_trigger_event(detection) is False
    print("test_event_manager_cooldown PASSED")

if __name__ == "__main__":
    test_event_manager_cooldown()
