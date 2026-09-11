"""
Módulo de Configuración Global de SIVARH
===============================================================

Responsabilidad:
----------------
Centralizar la carga, validación y acceso a todas las variables de entorno
y parámetros operativos del prototipo de vigilancia ambiental.

Flujo de invocación:
--------------------
- Se ejecuta al inicio de la aplicación y es importado por `app.dependencies`, `app.ai.vision_client`,
  `app.speech.openai_tts`, `app.api.routes.config` y el punto de entrada `app.main`.
- Lee las variables desde el archivo `.env` en la raíz del proyecto.
"""

import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator
from dotenv import load_dotenv

# Ruta absoluta al archivo .env ubicado en la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / ".env"

# Cargar las variables de entorno definidas en el archivo .env al entorno de Python
load_dotenv(dotenv_path=env_path)


class Settings(BaseModel):
    """
    Clase contenedora de la configuración global del sistema validada con Pydantic.
    Proporciona valores predeterminados seguros para permitir que el prototipo
    arranque incluso si no se dispone de un archivo .env configurado.
    """

    model_config = ConfigDict(validate_default=True)

    # ==========================================
    # 1. Configuración General de la Aplicación
    # ==========================================
    APP_NAME: str = "SIVARH"
    APP_VERSION: str = "0.10.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ==========================================
    # 2. Configuración de OpenAI (Visión y TTS)
    # ==========================================
    # Utilizado por `app.ai.vision_client.VisionAI` para analizar secuencias de imágenes
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_VISION_MODEL: str = os.getenv("OPENAI_VISION_MODEL", "gpt-5.6-luna")
    # `none` minimiza la latencia para esta clasificación visual estructurada.
    OPENAI_VISION_REASONING_EFFORT: str = os.getenv("OPENAI_VISION_REASONING_EFFORT", "none")
    # `low` reduce los tokens de imagen; evaluar precisión antes de subirlo a `auto`.
    IMAGE_DETAIL: str = os.getenv("IMAGE_DETAIL", "low")

    # Utilizado por `app.speech.openai_tts.OpenAISpeechService` para generar advertencias en audio
    OPENAI_TTS_MODEL: str = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    OPENAI_TTS_VOICE: str = os.getenv("OPENAI_TTS_VOICE", "onyx")
    # Un ritmo levemente superior mantiene la advertencia breve y urgente sin perder dicción.
    OPENAI_TTS_SPEED: float = float(os.getenv("OPENAI_TTS_SPEED", "1.1"))
    # PCM evita decodificar MP3 y permite enviar cada fragmento al altavoz apenas llega.
    OPENAI_TTS_RESPONSE_FORMAT: str = os.getenv("OPENAI_TTS_RESPONSE_FORMAT", "pcm")
    # Pequeño búfer para absorber variaciones de red sin entrecortar la advertencia.
    OPENAI_TTS_STREAM_BUFFER_MS: int = int(os.getenv("OPENAI_TTS_STREAM_BUFFER_MS", "400"))
    USE_LOCAL_WARNING_AUDIO: bool = os.getenv("USE_LOCAL_WARNING_AUDIO", "True").lower() in (
        "true", "1", "yes"
    )
    OPENAI_TTS_FALLBACK_ENABLED: bool = os.getenv(
        "OPENAI_TTS_FALLBACK_ENABLED", "True"
    ).lower() in ("true", "1", "yes")
    LOCAL_WARNING_MESSAGE: str = os.getenv(
        "LOCAL_WARNING_MESSAGE",
        "Cuidemos juntos el Huallaga. Por favor, recoge el residuo y deposítalo en un contenedor.",
    )
    LOCAL_WARNING_AUDIO_PATH: Path = Path(
        os.getenv(
            "LOCAL_WARNING_AUDIO_PATH",
            str(
                Path(__file__).resolve().parent.parent
                / "data"
                / "audio"
                / "templates"
                / "warning_default.wav"
            ),
        )
    )
    TTS_CACHE_DIR: Path = Path(
        os.getenv(
            "TTS_CACHE_DIR",
            str(Path(__file__).resolve().parent.parent / "data" / "audio" / "cache"),
        )
    )

    # ==========================================
    # 3. Adquisición de Video (Cámara / Stream)
    # ==========================================
    # Fuente de captura: número entero "0", "1" (webcam) o URL RTSP "rtsp://..."
    # Utilizado por `app.camera.usb_camera.UsbCamera` y `app.camera.rtsp_camera.RtspCamera`
    CAMERA_SOURCE: str = os.getenv("CAMERA_SOURCE", "0")
    CAMERA_ID: str = os.getenv("CAMERA_ID", "CAM_001")
    CAMERA_FPS: int = int(os.getenv("CAMERA_FPS", "30"))
    CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "1280"))
    CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "720"))

    # ==========================================
    # 4. Detector Local de Personas (YOLO)
    # ==========================================
    # Utilizado por `app.vision.detector.LocalDetector` como filtro de bajo costo
    YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    YOLO_IMGSZ: int = Field(default=int(os.getenv("YOLO_IMGSZ", "640")), ge=160)
    DETECTION_FPS: float = Field(default=float(os.getenv("DETECTION_FPS", "10")), gt=0.0)
    # Alias heredado: se conserva para instalaciones existentes.
    YOLO_PERSON_CONFIDENCE: float = Field(
        default=float(os.getenv("YOLO_PERSON_CONFIDENCE", "0.50")), ge=0.0, le=1.0
    )
    DETECTION_CONFIDENCE: float = Field(
        default=float(
            os.getenv(
                "DETECTION_CONFIDENCE",
                os.getenv("YOLO_PERSON_CONFIDENCE", "0.50"),
            )
        ),
        ge=0.0,
        le=1.0,
    )
    DETECTION_CLASSES: tuple[str, ...] = Field(
        default=tuple(
            dict.fromkeys(
                name.strip().casefold()
                for name in os.getenv(
                    "DETECTION_CLASSES",
                    "person,bottle,cup,backpack,handbag",
                ).split(",")
                if name.strip()
            )
        ),
        min_length=1,
    )

    # ==========================================
    # 4.1. Tracking temporal anónimo (SIVARH v2)
    # ==========================================
    TRACKING_ENABLED: bool = os.getenv("TRACKING_ENABLED", "True").lower() in ("true", "1", "yes")
    TRACKER_TYPE: str = os.getenv("TRACKER_TYPE", "bytetrack")
    TRACK_HISTORY_SECONDS: float = Field(default=float(os.getenv("TRACK_HISTORY_SECONDS", "15")), gt=0)
    TRACK_TTL_SECONDS: float = Field(default=float(os.getenv("TRACK_TTL_SECONDS", "5")), gt=0)
    TRACK_ACTIVATION_THRESHOLD: float = Field(
        default=float(os.getenv("TRACK_ACTIVATION_THRESHOLD", "0.50")), ge=0.0, le=1.0
    )
    TRACK_LOST_BUFFER: int = Field(default=int(os.getenv("TRACK_LOST_BUFFER", "30")), ge=0)
    TRACK_MIN_CONSECUTIVE_FRAMES: int = Field(
        default=int(os.getenv("TRACK_MIN_CONSECUTIVE_FRAMES", "2")), ge=1
    )
    TRACK_MIN_IOU_THRESHOLD: float = Field(
        default=float(os.getenv("TRACK_MIN_IOU_THRESHOLD", "0.10")), ge=0.0, le=1.0
    )

    # ==========================================
    # 4.2. Estado espacial y overlay (SIVARH v2)
    # ==========================================
    ZONE_CONFIG_PATH: Path = Path(
        os.getenv(
            "ZONE_CONFIG_PATH",
            str(Path(__file__).resolve().parent.parent / "config" / "zones.json"),
        )
    )
    VISION_DEBUG_OVERLAY: bool = os.getenv("VISION_DEBUG_OVERLAY", "True").lower() in (
        "true", "1", "yes"
    )

    # ==========================================
    # 4.3. Asociación persona-objeto (SIVARH v2)
    # ==========================================
    ASSOCIATION_ENABLED: bool = os.getenv("ASSOCIATION_ENABLED", "True").lower() in (
        "true", "1", "yes"
    )
    ASSOCIATION_MIN_SCORE: float = Field(
        default=float(os.getenv("ASSOCIATION_MIN_SCORE", "0.65")), ge=0.0, le=1.0
    )
    ASSOCIATION_MIN_DURATION: float = Field(
        default=float(os.getenv("ASSOCIATION_MIN_DURATION", "0.5")), ge=0.0
    )
    ASSOCIATION_BBOX_WEIGHT: float = Field(
        default=float(os.getenv("ASSOCIATION_BBOX_WEIGHT", "0.35")), ge=0.0
    )
    ASSOCIATION_CENTROID_WEIGHT: float = Field(
        default=float(os.getenv("ASSOCIATION_CENTROID_WEIGHT", "0.25")), ge=0.0
    )
    ASSOCIATION_TRAJECTORY_WEIGHT: float = Field(
        default=float(os.getenv("ASSOCIATION_TRAJECTORY_WEIGHT", "0.25")), ge=0.0
    )
    ASSOCIATION_TEMPORAL_WEIGHT: float = Field(
        default=float(os.getenv("ASSOCIATION_TEMPORAL_WEIGHT", "0.15")), ge=0.0
    )
    ASSOCIATION_HAND_WEIGHT: float = Field(
        default=float(os.getenv("ASSOCIATION_HAND_WEIGHT", "0.25")), ge=0.0
    )
    ASSOCIATION_MAX_DISTANCE_RATIO: float = Field(
        default=float(os.getenv("ASSOCIATION_MAX_DISTANCE_RATIO", "1.5")), gt=0.0
    )
    ASSOCIATION_HAND_DISTANCE_RATIO: float = Field(
        default=float(os.getenv("ASSOCIATION_HAND_DISTANCE_RATIO", "0.5")), gt=0.0
    )
    ASSOCIATION_TRAJECTORY_POINTS: int = Field(
        default=int(os.getenv("ASSOCIATION_TRAJECTORY_POINTS", "5")), ge=2
    )

    # ==========================================
    # 4.4. Pose corporal selectiva (SIVARH v2)
    # ==========================================
    # MediaPipe es opcional: si se desactiva, falta el paquete o falta el modelo,
    # las asociaciones continúan con las señales geométricas y temporales.
    POSE_ENABLED: bool = os.getenv("POSE_ENABLED", "False").lower() in (
        "true", "1", "yes"
    )
    POSE_MODEL_PATH: Path = Path(
        os.getenv(
            "POSE_MODEL_PATH",
            str(
                Path(__file__).resolve().parent.parent
                / "data"
                / "models"
                / "pose_landmarker_lite.task"
            ),
        )
    )
    POSE_FPS: float = Field(default=float(os.getenv("POSE_FPS", "7")), gt=0.0)
    POSE_MIN_PERSON_CONFIDENCE: float = Field(
        default=float(os.getenv("POSE_MIN_PERSON_CONFIDENCE", "0.60")), ge=0.0, le=1.0
    )
    POSE_MIN_DETECTION_CONFIDENCE: float = Field(
        default=float(os.getenv("POSE_MIN_DETECTION_CONFIDENCE", "0.50")), ge=0.0, le=1.0
    )
    POSE_MIN_LANDMARK_VISIBILITY: float = Field(
        default=float(os.getenv("POSE_MIN_LANDMARK_VISIBILITY", "0.50")), ge=0.0, le=1.0
    )
    POSE_TRIGGER_ZONES: tuple[str, ...] = tuple(
        dict.fromkeys(
            name.strip().casefold()
            for name in os.getenv(
                "POSE_TRIGGER_ZONES",
                "observation,riverbank,river_edge,water",
            ).split(",")
            if name.strip()
        )
    )
    POSE_MAX_PERSONS_PER_FRAME: int = Field(
        default=int(os.getenv("POSE_MAX_PERSONS_PER_FRAME", "2")), ge=1
    )
    POSE_RESULT_TTL_SECONDS: float = Field(
        default=float(os.getenv("POSE_RESULT_TTL_SECONDS", "0.5")), gt=0.0
    )
    POSE_CROP_PADDING_RATIO: float = Field(
        default=float(os.getenv("POSE_CROP_PADDING_RATIO", "0.15")), ge=0.0, le=1.0
    )
    POSE_OBJECT_PROXIMITY_RATIO: float = Field(
        default=float(os.getenv("POSE_OBJECT_PROXIMITY_RATIO", "0.5")), gt=0.0
    )

    # ==========================================
    # 4.5. Razonamiento temporal local (SIVARH v2)
    # ==========================================
    OBJECT_CARRIED_SCORE: float = Field(
        default=float(os.getenv("OBJECT_CARRIED_SCORE", "0.70")), ge=0.0, le=1.0
    )
    OBJECT_CARRIED_SECONDS: float = Field(
        default=float(os.getenv("OBJECT_CARRIED_SECONDS", "0.5")), ge=0.0
    )
    OBJECT_RELEASE_SCORE: float = Field(
        default=float(os.getenv("OBJECT_RELEASE_SCORE", "0.35")), ge=0.0, le=1.0
    )
    OBJECT_RELEASE_GRACE_SECONDS: float = Field(
        default=float(os.getenv("OBJECT_RELEASE_GRACE_SECONDS", "0.3")), ge=0.0
    )
    OBJECT_STATIONARY_SECONDS: float = Field(
        default=float(os.getenv("OBJECT_STATIONARY_SECONDS", "2.0")), gt=0.0
    )
    OBJECT_STATIONARY_MAX_DISTANCE_PX: float = Field(
        default=float(os.getenv("OBJECT_STATIONARY_MAX_DISTANCE_PX", "12.0")), gt=0.0
    )
    OBJECT_STATE_TTL_SECONDS: float = Field(
        default=float(os.getenv("OBJECT_STATE_TTL_SECONDS", "10.0")), gt=0.0
    )
    PERSON_MOVING_AWAY_SECONDS: float = Field(
        default=float(os.getenv("PERSON_MOVING_AWAY_SECONDS", "1.0")), gt=0.0
    )
    PERSON_MOVING_AWAY_MIN_DISTANCE_PX: float = Field(
        default=float(os.getenv("PERSON_MOVING_AWAY_MIN_DISTANCE_PX", "30.0")), gt=0.0
    )
    EVENT_RELEVANT_ZONES: tuple[str, ...] = tuple(
        dict.fromkeys(
            name.strip().casefold()
            for name in os.getenv(
                "EVENT_RELEVANT_ZONES",
                "riverbank,river_edge,water",
            ).split(",")
            if name.strip()
        )
    )
    LOCAL_IGNORE_THRESHOLD: float = Field(
        default=float(os.getenv("LOCAL_IGNORE_THRESHOLD", "0.35")), ge=0.0, le=1.0
    )
    LOCAL_CONFIRM_THRESHOLD: float = Field(
        default=float(os.getenv("LOCAL_CONFIRM_THRESHOLD", "0.75")), ge=0.0, le=1.0
    )
    EVENT_CARRIED_WEIGHT: float = Field(
        default=float(os.getenv("EVENT_CARRIED_WEIGHT", "0.25")), ge=0.0
    )
    EVENT_RELEASE_WEIGHT: float = Field(
        default=float(os.getenv("EVENT_RELEASE_WEIGHT", "0.25")), ge=0.0
    )
    EVENT_TARGET_ZONE_WEIGHT: float = Field(
        default=float(os.getenv("EVENT_TARGET_ZONE_WEIGHT", "0.20")), ge=0.0
    )
    EVENT_STATIONARY_WEIGHT: float = Field(
        default=float(os.getenv("EVENT_STATIONARY_WEIGHT", "0.15")), ge=0.0
    )
    EVENT_MOVING_AWAY_WEIGHT: float = Field(
        default=float(os.getenv("EVENT_MOVING_AWAY_WEIGHT", "0.15")), ge=0.0
    )

    # ==========================================
    # 4.6. Verificación multimodal como fallback (SIVARH v2)
    # ==========================================
    OPENAI_FALLBACK_ENABLED: bool = os.getenv("OPENAI_FALLBACK_ENABLED", "True").lower() in (
        "true", "1", "yes"
    )
    OPENAI_MAX_FRAMES: int = Field(
        default=int(os.getenv("OPENAI_MAX_FRAMES", "3")), ge=2, le=4
    )
    EVENT_MIN_CONTEXT_SECONDS: float = Field(
        default=float(os.getenv("EVENT_MIN_CONTEXT_SECONDS", "1.0")), ge=0.0
    )
    EVENT_KEYFRAME_BEFORE_SECONDS: float = Field(
        default=float(os.getenv("EVENT_KEYFRAME_BEFORE_SECONDS", "1.0")), ge=0.0
    )
    EVENT_KEYFRAME_AFTER_SECONDS: float = Field(
        default=float(os.getenv("EVENT_KEYFRAME_AFTER_SECONDS", "1.0")), ge=0.0
    )
    METRICS_WINDOW_SECONDS: float = Field(
        default=float(os.getenv("METRICS_WINDOW_SECONDS", "10.0")), gt=0.0
    )
    PERFORMANCE_LOG_INTERVAL_SECONDS: float = Field(
        default=float(os.getenv("PERFORMANCE_LOG_INTERVAL_SECONDS", "10.0")), gt=0.0
    )

    # ==========================================
    # 5. Buffer Circular y Gestión de Eventos
    # ==========================================
    # BUFFER_SECONDS: Tiempo en segundos de video mantenido en RAM por `app.vision.frame_buffer.FrameBuffer`
    BUFFER_SECONDS: int = int(os.getenv("BUFFER_SECONDS", "5"))
    # BUFFER_FPS: Muestras por segundo conservadas en RAM. La cámara puede seguir capturando a mayor FPS.
    BUFFER_FPS: int = int(os.getenv("BUFFER_FPS", "5"))
    # EVENT_CAPTURE_SECONDS: Duracion total de la secuencia posterior a una deteccion
    EVENT_CAPTURE_SECONDS: float = float(os.getenv("EVENT_CAPTURE_SECONDS", "5.6"))
    # SEQUENCE_FRAME_INTERVAL_SECONDS: Separacion temporal entre los fotogramas enviados a la IA
    SEQUENCE_FRAME_INTERVAL_SECONDS: float = float(os.getenv("SEQUENCE_FRAME_INTERVAL_SECONDS", "1"))
    # EVENT_COOLDOWN_SECONDS: Tiempo de espera en `app.events.cooldown.CooldownManager` para evitar llamadas repetidas
    EVENT_COOLDOWN_SECONDS: int = int(os.getenv("EVENT_COOLDOWN_SECONDS", "20"))
    # Modo de reconocimiento manual (desactivado por defecto para monitoreo autónomo).
    MANUAL_RECOGNITION_MODE: bool = os.getenv("MANUAL_RECOGNITION_MODE", "False").lower() in ("true", "1", "yes")
    MANUAL_CAPTURE_FRAMES: int = int(os.getenv("MANUAL_CAPTURE_FRAMES", "4"))
    MANUAL_CAPTURE_INTERVAL_SECONDS: float = float(os.getenv("MANUAL_CAPTURE_INTERVAL_SECONDS", "1.5"))

    # ==========================================
    # 6. Procesamiento y Selección de Imágenes
    # ==========================================
    # FRAMES_PER_ANALYSIS: Cantidad de imágenes que `app.vision.frame_selector.FrameSelector` extraerá
    FRAMES_PER_ANALYSIS: int = int(os.getenv("FRAMES_PER_ANALYSIS", "7"))
    # Dimensiones y calidad de compresión utilizadas por `app.vision.image_processor.ImageProcessor`
    IMAGE_MAX_WIDTH: int = int(os.getenv("IMAGE_MAX_WIDTH", "960"))
    JPEG_QUALITY: int = int(os.getenv("JPEG_QUALITY", "70"))

    # ==========================================
    # 7. Motor de Decisiones (Decision Engine)
    # ==========================================
    # Umbral mínimo de confianza para que `app.events.rules.DecisionEngine` active advertencia por voz
    AI_WARNING_THRESHOLD: float = float(os.getenv("AI_WARNING_THRESHOLD", "0.80"))

    # ==========================================
    # 8. Rutas del Sistema de Archivos
    # ==========================================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    FRONTEND_DIR: Path = BASE_DIR / "frontend"

    @model_validator(mode="after")
    def validate_association_weights(self):
        total = (
            self.ASSOCIATION_BBOX_WEIGHT
            + self.ASSOCIATION_CENTROID_WEIGHT
            + self.ASSOCIATION_TRAJECTORY_WEIGHT
            + self.ASSOCIATION_TEMPORAL_WEIGHT
            + self.ASSOCIATION_HAND_WEIGHT
        )
        if total <= 0:
            raise ValueError("Al menos un peso de asociación debe ser mayor que cero.")
        event_weight_total = (
            self.EVENT_CARRIED_WEIGHT
            + self.EVENT_RELEASE_WEIGHT
            + self.EVENT_TARGET_ZONE_WEIGHT
            + self.EVENT_STATIONARY_WEIGHT
            + self.EVENT_MOVING_AWAY_WEIGHT
        )
        if event_weight_total <= 0:
            raise ValueError("Al menos un peso de evento debe ser mayor que cero.")
        if self.LOCAL_IGNORE_THRESHOLD >= self.LOCAL_CONFIRM_THRESHOLD:
            raise ValueError("LOCAL_IGNORE_THRESHOLD debe ser menor que LOCAL_CONFIRM_THRESHOLD.")
        if self.OBJECT_RELEASE_SCORE >= self.OBJECT_CARRIED_SCORE:
            raise ValueError("OBJECT_RELEASE_SCORE debe ser menor que OBJECT_CARRIED_SCORE.")
        return self


# Instancia única (Singleton) para ser consumida por todo el proyecto
settings = Settings()
