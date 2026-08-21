import cv2
import base64
from typing import Tuple, Optional, Any
from pathlib import Path

class ImageProcessor:
    """
    Procesador de imágenes para redimensionar, comprimir JPEG y convertir a Base64
    previo al envío a las API de Visión Multimodal.
    """

    def __init__(self, max_width: int = 1280, jpeg_quality: int = 70):
        self.max_width = max_width
        self.jpeg_quality = jpeg_quality

    def resize_if_needed(self, frame: Any) -> Any:
        h, w = frame.shape[:2]
        if w > self.max_width:
            aspect_ratio = h / w
            new_w = self.max_width
            new_h = int(new_w * aspect_ratio)
            return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return frame

    def compress_jpeg(self, frame: Any) -> bytes:
        resized = self.resize_if_needed(frame)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        success, buffer = cv2.imencode('.jpg', resized, encode_param)
        if not success:
            raise ValueError("Error al codificar imagen a formato JPEG")
        return buffer.tobytes()

    def to_base64_data_url(self, frame: Any) -> str:
        jpeg_bytes = self.compress_jpeg(frame)
        base64_str = base64.b64encode(jpeg_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"

    def save_image(self, frame: Any, output_path: str) -> bool:
        try:
            resized = self.resize_if_needed(frame)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            return cv2.imwrite(output_path, resized, encode_param)
        except Exception:
            return False
