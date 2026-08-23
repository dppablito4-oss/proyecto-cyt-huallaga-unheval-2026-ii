import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.vision.frame_buffer import FrameBuffer


def test_frame_buffer_limits_sampling_rate():
    buffer = FrameBuffer(buffer_seconds=1, fps=5)

    assert buffer.add_frame("frame_1") is True
    assert buffer.add_frame("frame_2") is False

    time.sleep(0.21)
    assert buffer.add_frame("frame_3") is True
    assert len(buffer) == 2


def test_frame_buffer_selects_only_frames_after_detection_at_intervals():
    buffer = FrameBuffer(buffer_seconds=10, fps=100)
    start = datetime.now()

    for second in range(-2, 7):
        buffer.add_frame(f"frame_{second}", timestamp=start + timedelta(seconds=second))
        buffer._last_sample_time = None

    selected = buffer.get_frames_at_intervals(start, interval_seconds=1, count=5)

    assert [frame for _, frame in selected] == ["frame_1", "frame_2", "frame_3", "frame_4", "frame_5"]
