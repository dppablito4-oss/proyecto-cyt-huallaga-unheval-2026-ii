"""
Módulo de Interfaz de Síntesis de Voz (SpeechService Interface)
==============================================================

Responsabilidad:
----------------
Definir la abstracción base para servicios de conversión de texto a voz (Text-to-Speech).
Mantiene desacoplada la generación de audio respecto al motor de decisiones y a la visión.

Flujo de invocación:
--------------------
- Invocado exclusivamente cuando `app.events.rules.DecisionEngine` determina una decisión `WARN`.
- Recibe el texto de `AIAnalysisResult.warning_message` y retorna la ruta del archivo de audio generado.
"""

from abc import ABC, abstractmethod
from typing import Optional


class SpeechService(ABC):
    """
    Contrato abstracto para generadores de voz artificial.
    """

    @abstractmethod
    def generate_speech(self, text: str, output_path: str) -> Optional[str]:
        """
        Sintetiza audio a partir de una cadena de texto.

        Args:
            text (str): Mensaje de advertencia a verbalizar.
            output_path (str): Ruta de destino para guardar el archivo de audio (.mp3).

        Returns:
            Optional[str]: Ruta del archivo generado si tuvo éxito, o None si falló.
        """
        pass
