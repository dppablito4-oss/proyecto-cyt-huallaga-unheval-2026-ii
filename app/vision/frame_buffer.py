from collections import deque
from typing import List, Tuple, Any, Optional
from datetime import datetime

class FrameBuffer:
    """
    Mantendrás los últimos N segundos de fotogramas en RAM mediante una cola circular (deque).
    Evita guardar video continuamente en disco. Almacena (timestamp, frame_ndarray).
    """

    def __init__(self, buffer_seconds: int = 5, fps: int = 30):
        self.buffer_seconds = buffer_seconds
        self.fps = fps
        self.max_size = max(1, buffer_seconds * fps)
        self.buffer: deque = deque(maxlen=self.max_size)

    def add_frame(self, frame: Any, timestamp: Optional[datetime] = None) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        self.buffer.append((timestamp, frame))

    def get_all_frames(self) -> List[Tuple[datetime, Any]]:
        return list(self.buffer)

    def get_last_n_frames(self, n: int) -> List[Tuple[datetime, Any]]:
        frames = list(self.buffer)
        return frames[-n:] if len(frames) >= n else frames

    def clear(self) -> None:
        self.buffer.clear()

    def __len__(self) -> int:
        return len(self.buffer)
