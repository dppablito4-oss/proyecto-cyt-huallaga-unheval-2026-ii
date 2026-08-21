import cv2
from typing import Tuple, Optional, Any, Dict
from app.camera.base import CameraSource

class UsbCamera(CameraSource):
    """
    Implementación de CameraSource para cámaras USB utilizando OpenCV cv2.VideoCapture.
    """

    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720, fps: int = 30):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = fps
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if cv2.os.name == 'nt' else cv2.CAP_ANY)
            if not self.cap.isOpened():
                # Intentar fallback básico sin backend específico
                self.cap = cv2.VideoCapture(self.camera_index)
            
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                return True
            return False
        except Exception:
            return False

    def read(self) -> Tuple[bool, Optional[Any]]:
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def get_metadata(self) -> Dict[str, Any]:
        actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) if self.is_opened() else self.width
        actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) if self.is_opened() else self.height
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS) if self.is_opened() else self.target_fps
        return {
            "type": "usb",
            "camera_index": self.camera_index,
            "width": int(actual_w),
            "height": int(actual_h),
            "fps": float(actual_fps),
            "is_opened": self.is_opened()
        }
