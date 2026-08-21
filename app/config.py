import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseModel):
    # App General
    APP_NAME: str = "Huallaga AI Monitor"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_VISION_MODEL: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
    OPENAI_TTS_MODEL: str = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    OPENAI_TTS_VOICE: str = os.getenv("OPENAI_TTS_VOICE", "alloy")

    # Camera Options
    CAMERA_SOURCE: str = os.getenv("CAMERA_SOURCE", "0")
    CAMERA_FPS: int = int(os.getenv("CAMERA_FPS", "30"))
    CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "1280"))
    CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "720"))

    # YOLO Detector
    YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    YOLO_PERSON_CONFIDENCE: float = float(os.getenv("YOLO_PERSON_CONFIDENCE", "0.50"))

    # Buffer & Event Management
    BUFFER_SECONDS: int = int(os.getenv("BUFFER_SECONDS", "5"))
    EVENT_CAPTURE_SECONDS: int = int(os.getenv("EVENT_CAPTURE_SECONDS", "3"))
    EVENT_COOLDOWN_SECONDS: int = int(os.getenv("EVENT_COOLDOWN_SECONDS", "10"))

    # Frame Processing
    FRAMES_PER_ANALYSIS: int = int(os.getenv("FRAMES_PER_ANALYSIS", "5"))
    IMAGE_MAX_WIDTH: int = int(os.getenv("IMAGE_MAX_WIDTH", "1280"))
    JPEG_QUALITY: int = int(os.getenv("JPEG_QUALITY", "70"))

    # Decision Engine
    AI_WARNING_THRESHOLD: float = float(os.getenv("AI_WARNING_THRESHOLD", "0.80"))

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    FRONTEND_DIR: Path = BASE_DIR / "frontend"

settings = Settings()
