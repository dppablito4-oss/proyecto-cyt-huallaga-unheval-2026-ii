"""
Módulo de Text-to-Speech con OpenAI (OpenAISpeechService)
========================================================

Responsabilidad:
----------------
Implementar el servicio de síntesis de voz utilizando el endpoint `/v1/audio/speech` de OpenAI.
Permite generar advertencias verbales claras, naturales y en español a partir del texto
diseñado dinámicamente por la IA multimodal.

Flujo de invocación:
--------------------
- Llamado por el pipeline de alerta ante una decisión `WARN`.
- Guarda el archivo binario resultante en `data/audio/`.
- La ruta generada se pasa a `app.speech.audio_output.LocalSpeakerOutput` para su reproducción.
"""

import logging
from pathlib import Path
from typing import Optional
from app.config import settings
from app.speech.service import SpeechService

logger = logging.getLogger(__name__)


class OpenAISpeechService(SpeechService):
    """
    Servicio de síntesis de voz basado en la API de OpenAI Audio TTS.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, voice: Optional[str] = None):
        """
        Args:
            api_key (str, opcional): Clave de API de OpenAI.
            model (str, opcional): Modelo TTS (ej. 'tts-1', 'tts-1-hd').
            voice (str, opcional): Voz configurada (ej. 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer').
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_TTS_MODEL
        self.voice = voice or settings.OPENAI_TTS_VOICE

    def generate_speech(self, text: str, output_path: str) -> Optional[str]:
        """
        Envía el texto a la API de OpenAI TTS y escribe el stream de audio en disco.
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY no configurada. Omitiendo generación de audio TTS real.")
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            # Asegurar la creación de la carpeta de destino (data/audio/)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Llamada a la API de generación de voz
            response = client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text
            )
            
            # Transmitir el archivo de audio directamente al disco
            response.stream_to_file(output_path)
            logger.info(f"Audio de advertencia generado en: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error al generar audio con OpenAI TTS: {e}")
            return None
