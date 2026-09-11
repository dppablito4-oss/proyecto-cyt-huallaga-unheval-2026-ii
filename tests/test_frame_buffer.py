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


def test_frame_buffer_supports_nearest_range_and_context_queries():
    buffer = FrameBuffer(buffer_seconds=10, fps=100)
    center = datetime.now()
    for second in range(-2, 3):
        buffer.add_frame(f"frame_{second}", timestamp=center + timedelta(seconds=second))
        buffer._last_sample_time = None

    nearest = buffer.get_nearest_frame(center + timedelta(seconds=0.4))
    interval = buffer.get_frames_between(
        center - timedelta(seconds=1),
        center + timedelta(seconds=1),
    )
    context = buffer.get_context(center, before=1, after=1)

    assert nearest[1] == "frame_0"
    assert [frame for _, frame in interval] == ["frame_-1", "frame_0", "frame_1"]
    assert context == interval
    assert buffer.get_nearest_frame(center + timedelta(seconds=10), max_delta_seconds=1) is None
