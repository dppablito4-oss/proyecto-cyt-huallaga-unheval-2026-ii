"""
Módulo de Rutas de Cámaras (Cameras REST Routes)
================================================

Responsabilidad:
----------------
Proveer información sobre los dispositivos de captura configurados y su estado de enlace.

Endpoints:
----------
- `GET /api/cameras/status`: Retorna la resolución, tasa de cuadros y estado de conexión de la cámara.
"""

from fastapi import APIRouter
from app.models.camera import CameraStatus
from app.config import settings

router = APIRouter(prefix="/cameras")


@router.get("/status", response_model=CameraStatus, summary="Consultar estado técnico de la cámara")
def get_camera_status():
    """
    Retorna los parámetros de configuración y estado de conectividad de la fuente de video.
    """
    return CameraStatus(
        camera_id="CAM_001",
        source=settings.CAMERA_SOURCE,
        is_connected=False,  # En Fase 0 / Standby permanece en False hasta inicializar worker
        width=settings.CAMERA_WIDTH,
        height=settings.CAMERA_HEIGHT,
        fps=float(settings.CAMERA_FPS)
    )
