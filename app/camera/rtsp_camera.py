"""
Módulo de Captura de Video IP / RTSP (RtspCamera)
=================================================

Responsabilidad:
----------------
Placeholder estructurado para fuentes de video IP profesionales mediante el protocolo RTSP
(Real-Time Streaming Protocol).

Flujo de invocación:
--------------------
- Se utilizará en fases posteriores de despliegue en campo en la ribera del río Huallaga,
  donde cámaras fijas o domos PTZ transmiten video por red (ej. `rtsp://admin:pass@192.168.1.50:554/stream1`).
- Permite sustituir la webcam sin alterar el resto del pipeline gracias a `CameraSource`.
"""

import cv2
from typing import Tuple, Optional, Any, Dict
from app.camera.base import CameraSource


class RtspCamera(CameraSource):
    """
    Controlador para cámaras de seguridad y vigilancia IP vía RTSP.
    En la Fase 0 proporciona la interfaz base preparada para extensión.
    """

    def __init__(self, rtsp_url: str):
        """
        Args:
            rtsp_url (str): Dirección URL RTSP del stream de video de la cámara.
        """
        self.rtsp_url = rtsp_url
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """
        Abre el stream RTSP mediante OpenCV y FFmpeg backend.
        """
        try:
            # En implementaciones futuras se pueden añadir flags de baja latencia como `OPENCV_FFMPEG_CAPTURE_OPTIONS`
            self.cap = cv2.VideoCapture(self.rtsp_url)
            return self.cap.isOpened()
        except Exception:
            return False

    def read(self) -> Tuple[bool, Optional[Any]]:
        """Lee el siguiente cuadro del stream RTSP."""
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def close(self) -> None:
        """Cierra la conexión con el stream RTSP."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        """Verifica si la conexión RTSP está activa."""
        return self.cap is not None and self.cap.isOpened()

    def get_metadata(self) -> Dict[str, Any]:
        """Devuelve metadatos del stream IP."""
        return {
            "type": "rtsp",
            "url": self.rtsp_url,
            "is_opened": self.is_opened()
        }
