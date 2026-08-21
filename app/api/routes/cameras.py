from fastapi import APIRouter
from app.models.camera import CameraStatus

router = APIRouter(prefix="/cameras")

@router.get("/status", response_model=CameraStatus)
def get_camera_status():
    """Consulta el estado actual de la cámara."""
    return CameraStatus(
        camera_id="CAM_001",
        source="0",
        is_connected=False,
        width=1280,
        height=720,
        fps=0.0
    )
