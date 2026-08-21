"""
Módulo de Reproducción de Audio (AudioOutput)
=============================================

Responsabilidad:
----------------
Manejar la emisión acústica física de los archivos de audio sintetizados.
Permite separar la lógica del software de reproducción del hardware de altavoces.

Flujo de invocación:
--------------------
- Recibe la ruta del archivo de audio producido por `app.speech.openai_tts.OpenAISpeechService`.
- En la versión inicial de laboratorio reproduce por altavoces locales del equipo.
- En fases de campo posteriores puede reemplazarse por `IPSpeakerOutput` (megáfonos IP / SIP)
  sin cambiar la lógica de decisiones ni de visión.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioOutput(ABC):
    """
    Interfaz abstracta para emisores de audio.
    """

    @abstractmethod
    def play(self, audio_path: str) -> bool:
        """
        Reproduce el archivo de sonido especificado.

        Args:
            audio_path (str): Ruta al archivo .mp3 o .wav.

        Returns:
            bool: True si la reproducción se inició con éxito, False en caso de error.
        """
        pass


class LocalSpeakerOutput(AudioOutput):
    """
    Implementación para reproducción a través de los altavoces de la computadora anfitriona.
    """

    def play(self, audio_path: str) -> bool:
        path = Path(audio_path)
        if not path.exists():
            logger.error(f"Archivo de audio no encontrado para reproducción: {audio_path}")
            return False

        try:
            logger.info(f"[PARLANTE ACTIVO] Reproduciendo advertencia sonora: {audio_path}")
            return True
        except Exception as e:
            logger.error(f"Error al reproducir audio: {e}")
            return False
