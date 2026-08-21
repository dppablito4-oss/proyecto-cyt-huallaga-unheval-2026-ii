from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.dependencies import get_settings
from app.config import Settings

router = APIRouter(prefix="/config")

class ConfigUpdateModel(BaseModel):
    frames_per_analysis: Optional[int] = None
    jpeg_quality: Optional[int] = None
    ai_warning_threshold: Optional[float] = None

@router.get("")
def get_safe_config(settings: Settings = Depends(get_settings)):
    """Retorna la configuración actual del sistema (excluyendo secretos)."""
    return {
        "OPENAI_VISION_MODEL": settings.OPENAI_VISION_MODEL,
        "OPENAI_TTS_MODEL": settings.OPENAI_TTS_MODEL,
        "CAMERA_SOURCE": settings.CAMERA_SOURCE,
        "CAMERA_FPS": settings.CAMERA_FPS,
        "YOLO_MODEL": settings.YOLO_MODEL,
        "YOLO_PERSON_CONFIDENCE": settings.YOLO_PERSON_CONFIDENCE,
        "BUFFER_SECONDS": settings.BUFFER_SECONDS,
        "EVENT_COOLDOWN_SECONDS": settings.EVENT_COOLDOWN_SECONDS,
        "FRAMES_PER_ANALYSIS": settings.FRAMES_PER_ANALYSIS,
        "JPEG_QUALITY": settings.JPEG_QUALITY,
        "AI_WARNING_THRESHOLD": settings.AI_WARNING_THRESHOLD
    }

@router.patch("")
def update_config(update_data: ConfigUpdateModel, settings: Settings = Depends(get_settings)):
    """Actualiza parámetros dinámicos del sistema."""
    if update_data.frames_per_analysis is not None:
        settings.FRAMES_PER_ANALYSIS = update_data.frames_per_analysis
    if update_data.jpeg_quality is not None:
        settings.JPEG_QUALITY = update_data.jpeg_quality
    if update_data.ai_warning_threshold is not None:
        settings.AI_WARNING_THRESHOLD = update_data.ai_warning_threshold
    return {"message": "Configuración actualizada correctamente"}
