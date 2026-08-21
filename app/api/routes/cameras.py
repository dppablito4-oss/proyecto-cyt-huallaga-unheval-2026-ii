"""
Módulo de Rutas de Cámaras (Cameras REST Routes)
================================================

Responsabilidad:
----------------
Proveer información sobre los dispositivos de captura configurados y su estado de enlace.
Incluye streaming MJPEG en vivo para visualización en el dashboard web.

Endpoints:
----------
- `GET /api/cameras/status`: Retorna la resolución, tasa de cuadros y estado de conexión de la cámara.
- `GET /api/cameras/stream`: Stream MJPEG en vivo del feed de la cámara para el dashboard.
"""

import cv2
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.camera import CameraStatus
from app.config import settings

router = APIRouter(prefix="/cameras")


@router.get("/status", response_model=CameraStatus, summary="Consultar estado técnico de la cámara")
def get_camera_status():
    """
    Retorna los parámetros de configuración y estado de conectividad de la fuente de video.
    """
    from app.main import pipeline_worker

    return CameraStatus(
        camera_id="CAM_001",
        source=settings.CAMERA_SOURCE,
        is_connected=pipeline_worker.is_running,
        width=settings.CAMERA_WIDTH,
        height=settings.CAMERA_HEIGHT,
        fps=float(settings.CAMERA_FPS)
    )


def _generate_mjpeg_frames():
    """
    Generador que produce frames JPEG codificados en formato multipart
    para streaming MJPEG compatible con etiquetas <img> en el navegador.
    """
    import time
    from app.main import pipeline_worker

    while True:
        frame = pipeline_worker.current_frame
        if frame is not None:
            # Codificar frame como JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    buffer.tobytes() +
                    b"\r\n"
                )
        # Limitar a ~15 FPS para el stream web (suficiente para monitoreo visual)
        time.sleep(0.066)


@router.get("/stream", summary="Stream MJPEG en vivo de la cámara")
def camera_stream():
    """
    Retorna un stream MJPEG continuo del feed de la cámara para incrustar
    directamente en una etiqueta `<img src="/api/cameras/stream">` del dashboard.
    """
    return StreamingResponse(
        _generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
