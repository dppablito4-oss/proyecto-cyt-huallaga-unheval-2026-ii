import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioOutput(ABC):
    """
    Interfaz abstracta para reproducción de audio generado.
    """

    @abstractmethod
    def play(self, audio_path: str) -> bool:
        """Reproduce el archivo de audio dado."""
        pass

class LocalSpeakerOutput(AudioOutput):
    """
    Implementación para reproducción local a través de los altavoces de la PC.
    """

    def play(self, audio_path: str) -> bool:
        path = Path(audio_path)
        if not path.exists():
            logger.error(f"Archivo de audio no encontrado: {audio_path}")
            return False

        try:
            # En Windows o Linux, reproduce según disponibilidad de librerías
            logger.info(f"[SIMULACIÓN PARLANTE LOCAL] Reproduciendo audio: {audio_path}")
            return True
        except Exception as e:
            logger.error(f"Error reproduciendo audio: {e}")
            return False
