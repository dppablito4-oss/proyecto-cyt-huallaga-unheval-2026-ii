"""
Módulo de Procesamiento y Compresión de Imágenes (ImageProcessor)
=================================================================

Responsabilidad:
----------------
Realizar las transformaciones de imagen necesarias para optimizar el consumo de red
y adecuar las imágenes para las APIs multimodales de visión:
- Redimensionamiento proporcional (downscaling) si el ancho excede `settings.IMAGE_MAX_WIDTH`.
- Compresión JPEG controlada con calidad configurable (`settings.JPEG_QUALITY`).
- Codificación a formato Base64 Data URL (`data:image/jpeg;base64,...`).
- Guardado opcional de fotogramas en disco (`data/frames/`) para auditoría y registro experimental.

Flujo de invocación:
--------------------
- Recibe los fotogramas seleccionados por `app.vision.frame_selector.FrameSelector`.
- Convierte cada matriz OpenCV a Data URL Base64 para ser consumido por `app.ai.vision_client.VisionAI`.
"""

import cv2
import base64
from typing import Tuple, Optional, Any
from pathlib import Path


class ImageProcessor:
    """
    Motor de compresión y codificación de imágenes para transmisión eficiente.
    """

    def __init__(self, max_width: int = 1280, jpeg_quality: int = 70):
        """
        Args:
            max_width (int): Ancho máximo en píxeles. Si la imagen es más grande, se redimensiona.
            jpeg_quality (int): Factor de calidad JPEG entre 1 (muy baja) y 100 (máxima).
        """
        self.max_width = max_width
        self.jpeg_quality = jpeg_quality

    def resize_if_needed(self, frame: Any) -> Any:
        """
        Redimensiona la imagen conservando la relación de aspecto solo si su ancho supera `max_width`.
        """
        h, w = frame.shape[:2]
        if w > self.max_width:
            aspect_ratio = h / w
            new_w = self.max_width
            new_h = int(new_w * aspect_ratio)
            return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return frame

    def compress_jpeg(self, frame: Any) -> bytes:
        """
        Aplica compresión JPEG y retorna los bytes binarios de la imagen.
        """
        resized = self.resize_if_needed(frame)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        success, buffer = cv2.imencode('.jpg', resized, encode_param)
        if not success:
            raise ValueError("Error al codificar la matriz de imagen a formato JPEG.")
        return buffer.tobytes()

    def to_base64_data_url(self, frame: Any) -> str:
        """
        Convierte una matriz OpenCV en un string Base64 compatible con la API de OpenAI Vision.
        Formato: `data:image/jpeg;base64,<payload>`
        """
        jpeg_bytes = self.compress_jpeg(frame)
        base64_str = base64.b64encode(jpeg_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"

    def save_image(self, frame: Any, output_path: str) -> bool:
        """
        Guarda la imagen procesada en disco para trazabilidad y experimentos.
        """
        try:
            resized = self.resize_if_needed(frame)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            return cv2.imwrite(output_path, resized, encode_param)
        except Exception:
            return False
