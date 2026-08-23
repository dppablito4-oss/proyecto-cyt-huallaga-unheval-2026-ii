import sys
import time
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
