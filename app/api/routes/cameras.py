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
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from app.models.camera import CameraStatus
from app.config import settings

router = APIRouter(prefix="/cameras")


class CameraSwitchRequest(BaseModel):
    """Esquema para solicitar el cambio de fuente de cámara."""
    source: str = Field(default="0", description="Índice numérico ('0', '1', '2') o URL RTSP / ruta de archivo")


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


@router.post("/switch", summary="Cambiar la fuente de video en caliente")
def switch_camera(payload: CameraSwitchRequest):
    """
    Cambia la cámara activa del sistema sin reiniciar el servidor.
    """
    from app.main import pipeline_worker
    success = pipeline_worker.switch_source(payload.source)
    return {
        "success": success,
        "source": settings.CAMERA_SOURCE,
        "message": f"Cámara cambiada exitosamente a: {payload.source}" if success else "Error al cambiar la fuente de cámara."
    }


def _generate_mjpeg_frames():
    """
    Generador que produce frames JPEG codificados en formato multipart
    para streaming MJPEG compatible con etiquetas <img> en el navegador.
    """
    from app.main import pipeline_worker

    try:
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
    except (GeneratorExit, Exception):
        pass


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


@router.get("/analysis-preview/{filename}", summary="Ver un fotograma preparado para la IA")
def analysis_preview(filename: str):
    """Entrega un JPEG de la secuencia seleccionada, sin permitir rutas arbitrarias."""
    allowed_prefixes = ("ai-preview-", "manual-preview-")
    if Path(filename).name != filename or not filename.startswith(allowed_prefixes):
        raise HTTPException(status_code=404, detail="Fotograma no encontrado.")

    image_path = settings.DATA_DIR / "frames" / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Fotograma no encontrado.")

    return FileResponse(image_path, media_type="image/jpeg")
