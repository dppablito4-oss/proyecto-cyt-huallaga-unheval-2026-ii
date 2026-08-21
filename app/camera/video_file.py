import cv2
from typing import Tuple, Optional, Any, Dict
from pathlib import Path
from app.camera.base import CameraSource

class VideoFileCamera(CameraSource):
    """
    Implementación de CameraSource a partir de un archivo de video grabado (.mp4, .avi).
    Fundamental para pruebas repetibles de investigación y benchmarking.
    """

    def __init__(self, file_path: str, loop: bool = True):
        self.file_path = file_path
        self.loop = loop
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        path = Path(self.file_path)
        if not path.exists():
            return False
        self.cap = cv2.VideoCapture(str(path))
        return self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[Any]]:
        if self.cap is None or not self.cap.isOpened():
            return False, None
        
        ret, frame = self.cap.read()
        if not ret and self.loop:
            # Reiniciar al inicio del video si terminó
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            
        return ret, frame

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def get_metadata(self) -> Dict[str, Any]:
        fps = self.cap.get(cv2.CAP_PROP_FPS) if self.is_opened() else 30.0
        width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) if self.is_opened() else 0
        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) if self.is_opened() else 0
        return {
            "type": "file",
            "file_path": self.file_path,
            "width": int(width),
            "height": int(height),
            "fps": float(fps),
            "is_opened": self.is_opened()
        }
