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

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.speech.audio_output import LocalSpeakerOutput
from app.speech.openai_tts import OpenAISpeechService
from app.state import system_state

router = APIRouter(prefix="/system")


class ManualAlertRequest(BaseModel):
    """Voz elegida en el dashboard para emitir la advertencia preparada por Luna."""

    voice: Literal["alloy", "ash", "echo", "fable", "nova", "onyx", "sage", "shimmer"] = "onyx"
    speed: float = Field(default=1.1, ge=0.75, le=1.35)


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


@router.post("/clear-logs", summary="Limpiar el historial de logs del sistema")
def clear_system_logs():
    """
    Limpia la cola de logs mostrados en el dashboard.
    """
    from app.state import system_state
    system_state.clear_logs()
    return {"message": "Logs limpiados correctamente."}


@router.post("/manual/start-recognition", summary="Capturar secuencia manual")
def start_manual_recognition():
    """Captura cuatro imágenes, una cada 1.5 segundos, sin consultar a la IA."""
    from app.main import pipeline_worker

    accepted, message = pipeline_worker.start_manual_recognition()
    return {"accepted": accepted, "message": message}


@router.post("/manual/send-images", summary="Enviar secuencia manual a la IA")
def send_manual_images():
    """Envía a la IA la última secuencia manual completa."""
    from app.main import pipeline_worker

    accepted, message = pipeline_worker.analyze_manual_sequence()
    return {"accepted": accepted, "message": message}


@router.post("/manual/emit-alert", summary="Emitir la advertencia preparada por Luna")
def emit_manual_alert(payload: ManualAlertRequest):
    """Reproduce el mensaje de la última decisión WARN con la voz seleccionada."""
    snapshot = system_state.to_dict()
    warning_message = snapshot.get("last_warning_message")
    if not snapshot.get("alert_pending") or not warning_message:
        return {"accepted": False, "message": "No hay una alerta pendiente de emisión."}

    system_state.add_log(
        "AUDIO",
        f"[VOZ] Emisión manual solicitada (voz={payload.voice}, velocidad={payload.speed:.2f}x): \"{warning_message}\""
    )
    service = OpenAISpeechService(voice=payload.voice, speed=payload.speed)
    output_path = f"data/audio/manual_alert_{datetime.now():%Y%m%d_%H%M%S}.wav"
    generated = service.generate_and_play_streaming(warning_message, output_path, LocalSpeakerOutput())
    if not generated:
        system_state.add_log("WARN", "[AUDIO] No se pudo emitir la advertencia manual.")
        return {"accepted": False, "message": "No se pudo generar o reproducir la advertencia."}

    system_state.mark_alert_emitted()
    system_state.add_log("AUDIO", "[AUDIO] Advertencia manual emitida correctamente.")
    from app.main import pipeline_worker

    pipeline_worker.record_manual_alert_audio(generated)
    return {
        "accepted": True,
        "message": "Advertencia emitida correctamente.",
        "voice": payload.voice,
        "speed": payload.speed,
        "warning_message": warning_message,
    }
