"""
Módulo de Rutas de Control del Sistema (System Control REST Routes)
===================================================================

Responsabilidad:
----------------
Permitir iniciar y detener el pipeline de captura y procesamiento de video
mediante endpoints REST, sin necesidad de reiniciar el servidor completo.

Endpoints:
----------
- `POST /api/system/start`: Inicia o reanuda el worker de captura continua.
- `POST /api/system/stop`: Detiene o pausa la captura y procesamiento de video.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/system")


@router.post("/start", summary="Iniciar el pipeline de captura y procesamiento de video")
def start_pipeline():
    """
    Arranca el `VideoPipelineWorker` si no está en ejecución.
    Abre la cámara, inicia la detección YOLO y habilita el análisis automático.
    """
    from app.main import pipeline_worker

    if pipeline_worker.is_running:
        return {"message": "El pipeline de video ya está en ejecución.", "running": True}

    started = pipeline_worker.start()
    return {
        "message": "Pipeline de video iniciado correctamente." if started else "Error al iniciar el pipeline.",
        "running": started
    }


@router.post("/stop", summary="Detener el pipeline de captura y procesamiento de video")
def stop_pipeline():
    """
    Detiene el `VideoPipelineWorker`, cierra la cámara y libera recursos.
    El servidor web continúa funcionando normalmente.
    """
    from app.main import pipeline_worker

    if not pipeline_worker.is_running:
        return {"message": "El pipeline de video no está en ejecución.", "running": False}

    pipeline_worker.stop()
    return {"message": "Pipeline de video detenido correctamente.", "running": False}
