"""
Módulo de Reproducción de Video Pregrabado (VideoFileCamera)
===========================================================

Responsabilidad:
----------------
Permitir la alimentación del pipeline a partir de archivos de video grabados (`.mp4`, `.avi`, `.mkv`).
Es una pieza fundamental para la investigación científica reproducible, permitiendo probar
y comparar modelos de IA, diferentes prompts, estrategias de selección de fotogramas
y algoritmos de compresión exactamente sobre los mismos eventos de prueba.

Flujo de invocación:
--------------------
- Utilizado en entornos de prueba cargando videos desde la carpeta `data/test_videos/`.
- Proporciona fotogramas de forma continua o en bucle infinito (`loop=True`).
"""

import cv2
from typing import Tuple, Optional, Any, Dict
from pathlib import Path
from app.camera.base import CameraSource


class VideoFileCamera(CameraSource):
    """
    Fuente de video basada en archivos locales. Simula una cámara en tiempo real
    a partir de grabaciones de campo.
    """

    def __init__(self, file_path: str, loop: bool = True):
        """
        Args:
            file_path (str): Ruta al archivo de video en el sistema de archivos.
            loop (bool): Si es True, reinicia el video automáticamente al llegar al final.
        """
        self.file_path = file_path
        self.loop = loop
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """Abre el archivo de video especificado."""
        path = Path(self.file_path)
        if not path.exists():
            return False
        self.cap = cv2.VideoCapture(str(path))
        return self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[Any]]:
        """
        Lee el siguiente cuadro del archivo de video.
        Si se alcanza el final del archivo y `loop=True`, rebobina el puntero al fotograma inicial.
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None
        
        ret, frame = self.cap.read()
        if not ret and self.loop:
            # Rebobinar al fotograma 0 para repetir en bucle continuo
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            
        return ret, frame

    def close(self) -> None:
        """Cierra el archivo de video."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        """Verifica si el video está abierto para reproducción."""
        return self.cap is not None and self.cap.isOpened()

    def get_metadata(self) -> Dict[str, Any]:
        """Obtiene la resolución, FPS nativo y duración del archivo."""
        fps = self.cap.get(cv2.CAP_PROP_FPS) if self.is_opened() else 30.0
        width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) if self.is_opened() else 0
        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) if self.is_opened() else 0
        total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) if self.is_opened() else 0
        return {
            "type": "file",
            "file_path": self.file_path,
            "width": int(width),
            "height": int(height),
            "fps": float(fps),
            "total_frames": int(total_frames),
            "is_opened": self.is_opened()
        }
