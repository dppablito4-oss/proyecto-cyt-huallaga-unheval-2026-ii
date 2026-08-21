"""
Módulo de Procesamiento y Optimización de Imágenes (ImageProcessor)
===================================================================

Responsabilidad:
----------------
Realizar exclusivamente transformaciones visuales y compresión de imágenes:
- Redimensionamiento proporcional (downscaling) si el ancho excede `settings.IMAGE_MAX_WIDTH`.
- Compresión JPEG controlada con factor de calidad configurable (`settings.JPEG_QUALITY`).
- Guardado opcional de fotogramas procesados en disco (`data/frames/`) para auditoría.

Principio de diseño:
--------------------
`ImageProcessor` NO conoce los detalles del transporte o API de OpenAI (no genera Base64).
La serialización y construcción del payload de red corresponde a `VisionAIClient`.
"""

import cv2
from typing import Any
from pathlib import Path


class ImageProcessor:
    """
    Motor de compresión y redimensionamiento de imágenes.
    Desacoplado de los mecanismos de transporte o proveedores de IA.
    """

    def __init__(self, max_width: int = 1280, jpeg_quality: int = 70):
        """
        Args:
            max_width (int): Ancho máximo horizontal en píxeles.
            jpeg_quality (int): Factor de calidad JPEG entre 1 (mínimo) y 100 (máximo).
        """
        self.max_width = max_width
        self.jpeg_quality = jpeg_quality

    def resize_if_needed(self, frame: Any) -> Any:
        """
        Redimensiona la imagen conservando la relación de aspecto únicamente si su ancho supera `max_width`.
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
        Aplica compresión JPEG y retorna los bytes binarios de la imagen procesada.
        """
        resized = self.resize_if_needed(frame)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        success, buffer = cv2.imencode('.jpg', resized, encode_param)
        if not success:
            raise ValueError("Error al codificar la matriz de imagen a formato JPEG.")
        return buffer.tobytes()

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
