"""
Módulo de Rutas de Configuración Dinámica (Config REST Routes)
==============================================================

Responsabilidad:
----------------
Permitir la consulta y modificación en caliente de parámetros operacionales del prototipo
(fotogramas por análisis, calidad JPEG, umbral de advertencia) sin requerir reiniciar el servidor.

Seguridad:
----------
- `GET /api/config` excluye intencionalmente API Keys, contraseñas y datos sensibles.
- `PATCH /api/config` valida los tipos con Pydantic y aplica cambios en memoria.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from app.dependencies import get_settings
from app.config import Settings

router = APIRouter(prefix="/config")


class ConfigUpdateModel(BaseModel):
    """
    Esquema para la actualización parcial de parámetros de configuración.
    """
    frames_per_analysis: Optional[int] = Field(None, ge=1, le=20, description="Cantidad de frames seleccionados por evento.")
    jpeg_quality: Optional[int] = Field(None, ge=10, le=100, description="Calidad de compresión JPEG.")
    ai_warning_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Umbral de confianza para emitir advertencia.")


@router.get("", summary="Consultar configuración no sensible del sistema")
def get_safe_config(settings: Settings = Depends(get_settings)):
    """
    Retorna la configuración activa omitiendo credenciales o llaves de API privadas.
    """
    return {
        "OPENAI_VISION_MODEL": settings.OPENAI_VISION_MODEL,
        "OPENAI_TTS_MODEL": settings.OPENAI_TTS_MODEL,
        "CAMERA_SOURCE": settings.CAMERA_SOURCE,
        "CAMERA_FPS": settings.CAMERA_FPS,
        "YOLO_MODEL": settings.YOLO_MODEL,
        "YOLO_PERSON_CONFIDENCE": settings.YOLO_PERSON_CONFIDENCE,
        "BUFFER_SECONDS": settings.BUFFER_SECONDS,
        "BUFFER_FPS": settings.BUFFER_FPS,
        "EVENT_COOLDOWN_SECONDS": settings.EVENT_COOLDOWN_SECONDS,
        "FRAMES_PER_ANALYSIS": settings.FRAMES_PER_ANALYSIS,
        "JPEG_QUALITY": settings.JPEG_QUALITY,
        "AI_WARNING_THRESHOLD": settings.AI_WARNING_THRESHOLD
    }


@router.patch("", summary="Actualizar parámetros operativos en tiempo de ejecución")
def update_config(update_data: ConfigUpdateModel, settings: Settings = Depends(get_settings)):
    """
    Aplica modificaciones en tiempo real sobre los parámetros permitidos.
    """
    if update_data.frames_per_analysis is not None:
        settings.FRAMES_PER_ANALYSIS = update_data.frames_per_analysis
    if update_data.jpeg_quality is not None:
        settings.JPEG_QUALITY = update_data.jpeg_quality
    if update_data.ai_warning_threshold is not None:
        settings.AI_WARNING_THRESHOLD = update_data.ai_warning_threshold
        
    return {"message": "Configuración actualizada correctamente."}
