import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta
from app.vision.frame_selector import EventKeyframeSelector, FrameSelector

def test_frame_selection_uniform():
    selector = FrameSelector(target_frames=5, strategy="uniform")
    # Crear 10 fotogramas ficticios
    frames = [(datetime.now(), f"frame_{i}") for i in range(10)]
    selected = selector.select_frames(frames)
    assert len(selected) == 5
    assert selected[0][1] == "frame_0"
    assert selected[-1][1] == "frame_9"
    print("test_frame_selection_uniform PASSED")


def test_event_keyframes_cover_before_release_and_after():
    released_at = datetime(2026, 9, 10, 12, 0, 0)
    frames = [
        (released_at + timedelta(seconds=offset), f"frame_{offset}")
        for offset in (-2, -1, 0, 1, 2)
    ]
    selector = EventKeyframeSelector(max_frames=3, before_seconds=1, after_seconds=1)

    selected = selector.select_event_frames(frames, release_timestamp=released_at)

    assert [frame for _, frame in selected] == ["frame_-1", "frame_0", "frame_1"]

if __name__ == "__main__":
    test_frame_selection_uniform()
