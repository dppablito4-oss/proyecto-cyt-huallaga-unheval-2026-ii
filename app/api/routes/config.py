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
        "OPENAI_TTS_VOICE": settings.OPENAI_TTS_VOICE,
        "OPENAI_TTS_SPEED": settings.OPENAI_TTS_SPEED,
        "USE_LOCAL_WARNING_AUDIO": settings.USE_LOCAL_WARNING_AUDIO,
        "OPENAI_TTS_FALLBACK_ENABLED": settings.OPENAI_TTS_FALLBACK_ENABLED,
        "LOCAL_WARNING_AUDIO_PATH": str(settings.LOCAL_WARNING_AUDIO_PATH),
        "TTS_CACHE_DIR": str(settings.TTS_CACHE_DIR),
        "CAMERA_SOURCE": settings.CAMERA_SOURCE,
        "CAMERA_ID": settings.CAMERA_ID,
        "CAMERA_FPS": settings.CAMERA_FPS,
        "DETECTOR_BACKEND": settings.DETECTOR_BACKEND,
        "YOLO_MODEL": settings.YOLO_MODEL,
        "YOLO_PROMPT_EMBEDDINGS_PATH": str(settings.YOLO_PROMPT_EMBEDDINGS_PATH),
        "YOLO_IMGSZ": settings.YOLO_IMGSZ,
        "DETECTION_FPS": settings.DETECTION_FPS,
        "YOLO_PERSON_CONFIDENCE": settings.YOLO_PERSON_CONFIDENCE,
        "DETECTION_CONFIDENCE": settings.DETECTION_CONFIDENCE,
        "DETECTION_CLASSES": list(settings.DETECTION_CLASSES),
        "TRACKING_ENABLED": settings.TRACKING_ENABLED,
        "TRACKER_TYPE": settings.TRACKER_TYPE,
        "TRACK_HISTORY_SECONDS": settings.TRACK_HISTORY_SECONDS,
        "TRACK_TTL_SECONDS": settings.TRACK_TTL_SECONDS,
        "ZONE_CONFIG_PATH": str(settings.ZONE_CONFIG_PATH),
        "VISION_DEBUG_OVERLAY": settings.VISION_DEBUG_OVERLAY,
        "ASSOCIATION_ENABLED": settings.ASSOCIATION_ENABLED,
        "ASSOCIATION_MIN_SCORE": settings.ASSOCIATION_MIN_SCORE,
        "ASSOCIATION_MIN_DURATION": settings.ASSOCIATION_MIN_DURATION,
        "ASSOCIATION_BBOX_WEIGHT": settings.ASSOCIATION_BBOX_WEIGHT,
        "ASSOCIATION_CENTROID_WEIGHT": settings.ASSOCIATION_CENTROID_WEIGHT,
        "ASSOCIATION_TRAJECTORY_WEIGHT": settings.ASSOCIATION_TRAJECTORY_WEIGHT,
        "ASSOCIATION_TEMPORAL_WEIGHT": settings.ASSOCIATION_TEMPORAL_WEIGHT,
        "ASSOCIATION_HAND_WEIGHT": settings.ASSOCIATION_HAND_WEIGHT,
        "ASSOCIATION_MAX_DISTANCE_RATIO": settings.ASSOCIATION_MAX_DISTANCE_RATIO,
        "ASSOCIATION_HAND_DISTANCE_RATIO": settings.ASSOCIATION_HAND_DISTANCE_RATIO,
        "ASSOCIATION_TRAJECTORY_POINTS": settings.ASSOCIATION_TRAJECTORY_POINTS,
        "POSE_ENABLED": settings.POSE_ENABLED,
        "POSE_MODEL_PATH": str(settings.POSE_MODEL_PATH),
        "POSE_FPS": settings.POSE_FPS,
        "POSE_MIN_PERSON_CONFIDENCE": settings.POSE_MIN_PERSON_CONFIDENCE,
        "POSE_MIN_DETECTION_CONFIDENCE": settings.POSE_MIN_DETECTION_CONFIDENCE,
        "POSE_MIN_LANDMARK_VISIBILITY": settings.POSE_MIN_LANDMARK_VISIBILITY,
        "POSE_TRIGGER_ZONES": list(settings.POSE_TRIGGER_ZONES),
        "POSE_MAX_PERSONS_PER_FRAME": settings.POSE_MAX_PERSONS_PER_FRAME,
        "POSE_RESULT_TTL_SECONDS": settings.POSE_RESULT_TTL_SECONDS,
        "OBJECT_CARRIED_SCORE": settings.OBJECT_CARRIED_SCORE,
        "OBJECT_CARRIED_SECONDS": settings.OBJECT_CARRIED_SECONDS,
        "OBJECT_RELEASE_SCORE": settings.OBJECT_RELEASE_SCORE,
        "OBJECT_RELEASE_GRACE_SECONDS": settings.OBJECT_RELEASE_GRACE_SECONDS,
        "OBJECT_LOST_RELEASE_SECONDS": settings.OBJECT_LOST_RELEASE_SECONDS,
        "OBJECT_STATIONARY_SECONDS": settings.OBJECT_STATIONARY_SECONDS,
        "OBJECT_STATIONARY_MAX_DISTANCE_PX": settings.OBJECT_STATIONARY_MAX_DISTANCE_PX,
        "OBJECT_STATE_TTL_SECONDS": settings.OBJECT_STATE_TTL_SECONDS,
        "PERSON_MOVING_AWAY_SECONDS": settings.PERSON_MOVING_AWAY_SECONDS,
        "PERSON_MOVING_AWAY_MIN_DISTANCE_PX": settings.PERSON_MOVING_AWAY_MIN_DISTANCE_PX,
        "OBJECT_THROW_MIN_SPEED_PX_S": settings.OBJECT_THROW_MIN_SPEED_PX_S,
        "OBJECT_THROW_MIN_DISTANCE_PX": settings.OBJECT_THROW_MIN_DISTANCE_PX,
        "EVENT_RELEVANT_ZONES": list(settings.EVENT_RELEVANT_ZONES),
        "LOCAL_IGNORE_THRESHOLD": settings.LOCAL_IGNORE_THRESHOLD,
        "LOCAL_CONFIRM_THRESHOLD": settings.LOCAL_CONFIRM_THRESHOLD,
        "EVENT_CARRIED_WEIGHT": settings.EVENT_CARRIED_WEIGHT,
        "EVENT_RELEASE_WEIGHT": settings.EVENT_RELEASE_WEIGHT,
        "EVENT_TARGET_ZONE_WEIGHT": settings.EVENT_TARGET_ZONE_WEIGHT,
        "EVENT_STATIONARY_WEIGHT": settings.EVENT_STATIONARY_WEIGHT,
        "EVENT_MOVING_AWAY_WEIGHT": settings.EVENT_MOVING_AWAY_WEIGHT,
        "EVENT_THROW_WEIGHT": settings.EVENT_THROW_WEIGHT,
        "OPENAI_FALLBACK_ENABLED": settings.OPENAI_FALLBACK_ENABLED,
        "OPENAI_MAX_FRAMES": settings.OPENAI_MAX_FRAMES,
        "EVENT_MIN_CONTEXT_SECONDS": settings.EVENT_MIN_CONTEXT_SECONDS,
        "EVENT_KEYFRAME_BEFORE_SECONDS": settings.EVENT_KEYFRAME_BEFORE_SECONDS,
        "EVENT_KEYFRAME_AFTER_SECONDS": settings.EVENT_KEYFRAME_AFTER_SECONDS,
        "METRICS_WINDOW_SECONDS": settings.METRICS_WINDOW_SECONDS,
        "PERFORMANCE_LOG_INTERVAL_SECONDS": settings.PERFORMANCE_LOG_INTERVAL_SECONDS,
        "BUFFER_SECONDS": settings.BUFFER_SECONDS,
        "BUFFER_FPS": settings.BUFFER_FPS,
        "EVENT_CAPTURE_SECONDS": settings.EVENT_CAPTURE_SECONDS,
        "SEQUENCE_FRAME_INTERVAL_SECONDS": settings.SEQUENCE_FRAME_INTERVAL_SECONDS,
        "EVENT_COOLDOWN_SECONDS": settings.EVENT_COOLDOWN_SECONDS,
        "FRAMES_PER_ANALYSIS": settings.FRAMES_PER_ANALYSIS,
        "JPEG_QUALITY": settings.JPEG_QUALITY,
        "AI_WARNING_THRESHOLD": settings.AI_WARNING_THRESHOLD
    }


@router.patch("", summary="Actualizar parámetros operativos en tiempo de ejecución")
def update_config(update_data: ConfigUpdateModel):
    """
    Aplica modificaciones en tiempo real sobre los parámetros permitidos y
    sincroniza los componentes ya construidos del pipeline.
    """
    from app.main import pipeline_worker

    applied = pipeline_worker.apply_runtime_config(
        frames_per_analysis=update_data.frames_per_analysis,
        jpeg_quality=update_data.jpeg_quality,
        ai_warning_threshold=update_data.ai_warning_threshold,
    )
    return {
        "message": "Configuración actualizada correctamente." if applied else "No se enviaron cambios.",
        "updated": applied,
    }
