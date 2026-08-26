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
import wave
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from app.config import settings
from app.speech.service import SpeechService

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.speech.audio_output import LocalSpeakerOutput


ENVIRONMENTAL_WARNING_INSTRUCTIONS = """
Habla como un sistema público de advertencia ambiental.
Tono firme, serio y autoritativo, pero nunca agresivo.
Debe sonar como una advertencia inmediata, no como una narración ni una lectura.
Pronuncia \"Atención\" con énfasis y realiza una pausa breve inmediatamente después.
Usa un ritmo ligeramente rápido y una dicción muy clara.
La instrucción principal debe sonar directa y urgente.
Evita sonar alegre, conversacional, relajado o excesivamente amable.
""".strip()


class OpenAISpeechService(SpeechService):
    """
    Servicio de síntesis de voz basado en la API de OpenAI Audio TTS.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ):
        """
        Args:
            api_key (str, opcional): Clave de API de OpenAI.
            model (str, opcional): Modelo TTS (ej. 'gpt-4o-mini-tts', 'tts-1', 'tts-1-hd').
            voice (str, opcional): Voz configurada (ej. 'onyx', 'alloy', 'echo').
            speed (float, opcional): Velocidad específica para esta síntesis.
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_TTS_MODEL
        self.voice = voice or settings.OPENAI_TTS_VOICE
        self.speed = speed if speed is not None else settings.OPENAI_TTS_SPEED

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
                    input=text,
                    instructions=ENVIRONMENTAL_WARNING_INSTRUCTIONS,
                    speed=self.speed,
                )
            except Exception as model_err:
                # Si el modelo específico falla, fallback a 'tts-1' estándar
                if self.model != "tts-1":
                    logger.warning(f"Fallo al invocar modelo '{self.model}': {model_err}. Intentando con fallback 'tts-1'...")
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice=self.voice,
                        input=text,
                        speed=self.speed,
                    )
                else:
                    raise model_err

            # Transmitir el archivo de audio directamente al disco
            response.stream_to_file(output_path)
            logger.info(
                f"Audio TTS generado exitosamente (voz={self.voice}, velocidad={self.speed}x) en: {output_path}"
            )
            return output_path
        except Exception as e:
            logger.error(f"Error al generar audio con OpenAI TTS: {e}")
            return None

    def generate_and_play_streaming(
        self, text: str, output_path: str, audio_output: "LocalSpeakerOutput"
    ) -> Optional[str]:
        """Solicita PCM por streaming, lo reproduce por fragmentos y archiva un WAV del evento."""
        if not self.api_key:
            logger.warning("OPENAI_API_KEY no configurada. Omitiendo generación TTS en streaming.")
            return None
        if settings.OPENAI_TTS_RESPONSE_FORMAT != "pcm":
            logger.warning("OPENAI_TTS_RESPONSE_FORMAT debe ser 'pcm' para reproducción en streaming.")
            return self.generate_speech(text, output_path)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            def stream_chunks():
                with client.with_streaming_response.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    instructions=ENVIRONMENTAL_WARNING_INSTRUCTIONS,
                    speed=self.speed,
                    response_format="pcm",
                    stream_format="audio",
                ) as response, wave.open(output_path, "wb") as archive:
                    archive.setnchannels(1)
                    archive.setsampwidth(2)
                    archive.setframerate(24000)
                    for chunk in response.iter_bytes(chunk_size=4096):
                        archive.writeframesraw(chunk)
                        yield chunk

            if not audio_output.play_pcm_stream(stream_chunks()):
                return None
            logger.info(
                f"Audio TTS reproducido en streaming (voz={self.voice}, velocidad={self.speed}x) y archivado en: {output_path}"
            )
            return output_path
        except Exception as e:
            logger.error(f"Error en TTS PCM con streaming: {e}")
            return None
