"""
Módulo de Modelos de Estado de Cámara (Camera Status Model)
===========================================================

Responsabilidad:
----------------
Modelar el estado técnico, resolución y conectividad del dispositivo de captura de video.

Flujo de invocación:
--------------------
- Generado por las implementaciones de `app.camera` (`UsbCamera`, `RtspCamera`, `VideoFileCamera`).
- Expuesto al cliente web a través del endpoint REST `GET /api/cameras/status` en `app.api.routes.cameras`.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CameraStatus(BaseModel):
    """
    Representa el estado operativo y las especificaciones técnicas de la cámara.
    """
    camera_id: str = Field("CAM_001", description="Identificador único del dispositivo de captura.")
    source: str = Field("0", description="Ruta, índice numérico de dispositivo USB o URL RTSP configurada.")
    is_connected: bool = Field(False, description="Indica si la cámara está respondiendo y capturando frames activamente.")
    width: int = Field(1280, description="Ancho de resolución en píxeles configurado o detectado.")
    height: int = Field(720, description="Alto de resolución en píxeles configurado o detectado.")
    fps: float = Field(0.0, description="Tasa real de cuadros por segundo leídos por OpenCV.")
    error_message: Optional[str] = Field(None, description="Mensaje de error descriptivo en caso de desconexión o fallo.")
