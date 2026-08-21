"""
Módulo de Text-to-Speech con OpenAI (OpenAISpeechService)
========================================================

Responsabilidad:
----------------
Implementar el servicio de síntesis de voz utilizando los endpoints de audio/TTS de OpenAI
(por defecto `gpt-4o-mini-tts` con fallback automático a `tts-1`).
Permite sintetizar las advertencias verbales estructuradas generadas por VisionAI
usando la voz masculina 'onyx' en español latino neutro y estilo de locutor profesional.

Flujo de invocación:
--------------------
- Llamado por el pipeline únicamente ante una decisión `WARN` autorizada por `DecisionEngine`.
- Guarda el archivo binario resultante en `data/audio/`.
- La ruta generada se pasa a `LocalSpeakerOutput` para su reproducción física.
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
            model (str, opcional): Modelo TTS (ej. 'gpt-4o-mini-tts', 'tts-1', 'tts-1-hd').
            voice (str, opcional): Voz configurada (ej. 'onyx', 'alloy', 'echo').
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_TTS_MODEL
        self.voice = voice or settings.OPENAI_TTS_VOICE

    def generate_speech(self, text: str, output_path: str) -> Optional[str]:
        """
        Envía el texto al endpoint de OpenAI TTS y escribe el stream de audio en disco.
        Si el modelo configurado no está disponible en la cuenta, realiza fallback a 'tts-1'.
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY no configurada. Omitiendo generación de audio TTS real.")
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            # Asegurar la creación de la carpeta de destino (data/audio/)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            try:
                # Intentar con el modelo configurado (ej. gpt-4o-mini-tts / tts-1)
                response = client.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text
                )
            except Exception as model_err:
                # Si el modelo específico falla, fallback a 'tts-1' estándar
                if self.model != "tts-1":
                    logger.warning(f"Fallo al invocar modelo '{self.model}': {model_err}. Intentando con fallback 'tts-1'...")
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice=self.voice,
                        input=text
                    )
                else:
                    raise model_err

            # Transmitir el archivo de audio directamente al disco
            response.stream_to_file(output_path)
            logger.info(f"Audio TTS generado exitosamente ({self.voice}) en: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error al generar audio con OpenAI TTS: {e}")
            return None
