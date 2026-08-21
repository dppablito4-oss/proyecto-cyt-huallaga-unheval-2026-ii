import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from datetime import datetime
from app.vision.frame_selector import FrameSelector

def test_frame_selection_uniform():
    selector = FrameSelector(target_frames=5, strategy="uniform")
    # Crear 10 fotogramas ficticios
    frames = [(datetime.now(), f"frame_{i}") for i in range(10)]
    selected = selector.select_frames(frames)
    assert len(selected) == 5
    assert selected[0][1] == "frame_0"
    assert selected[-1][1] == "frame_9"
    print("test_frame_selection_uniform PASSED")

if __name__ == "__main__":
    test_frame_selection_uniform()
