import logging
from pathlib import Path
from typing import Optional
from app.config import settings
from app.speech.service import SpeechService

logger = logging.getLogger(__name__)

class OpenAISpeechService(SpeechService):
    """
    Implementación del servicio TTS utilizando el endpoint /v1/audio/speech de OpenAI.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, voice: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_TTS_MODEL
        self.voice = voice or settings.OPENAI_TTS_VOICE

    def generate_speech(self, text: str, output_path: str) -> Optional[str]:
        if not self.api_key:
            logger.warning("OPENAI_API_KEY no configurada. Omitiendo generación TTS real.")
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            response = client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text
            )
            
            response.stream_to_file(output_path)
            logger.info(f"Audio TTS generado exitosamente en {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error al generar audio TTS con OpenAI: {e}")
            return None
