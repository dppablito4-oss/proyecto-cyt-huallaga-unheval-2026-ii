from abc import ABC, abstractmethod
from typing import Optional

class SpeechService(ABC):
    """
    Interfaz abstracta para servicios de Text-to-Speech (TTS).
    Separada completamente del módulo VisionAI.
    """

    @abstractmethod
    def generate_speech(self, text: str, output_path: str) -> Optional[str]:
        """
        Recibe un mensaje de texto y genera el archivo de audio.
        Retorna la ruta del archivo generado o None en caso de falla.
        """
        pass
