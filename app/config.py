"""
Módulo de Configuración Global del Sistema (Huallaga AI Monitor)
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
from pydantic import BaseModel
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

    # ==========================================
    # 1. Configuración General de la Aplicación
    # ==========================================
    APP_NAME: str = "Huallaga AI Monitor"
    APP_VERSION: str = "0.5.1"
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

    # ==========================================
    # 3. Adquisición de Video (Cámara / Stream)
    # ==========================================
    # Fuente de captura: número entero "0", "1" (webcam) o URL RTSP "rtsp://..."
    # Utilizado por `app.camera.usb_camera.UsbCamera` y `app.camera.rtsp_camera.RtspCamera`
    CAMERA_SOURCE: str = os.getenv("CAMERA_SOURCE", "0")
    CAMERA_FPS: int = int(os.getenv("CAMERA_FPS", "30"))
    CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "1280"))
    CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "720"))

    # ==========================================
    # 4. Detector Local de Personas (YOLO)
    # ==========================================
    # Utilizado por `app.vision.detector.LocalDetector` como filtro de bajo costo
    YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    YOLO_PERSON_CONFIDENCE: float = float(os.getenv("YOLO_PERSON_CONFIDENCE", "0.50"))

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


# Instancia única (Singleton) para ser consumida por todo el proyecto
settings = Settings()
