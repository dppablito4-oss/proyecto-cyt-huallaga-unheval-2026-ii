"""
Módulo de Motor de Decisiones (DecisionEngine)
==============================================

Responsabilidad:
----------------
Determinar la acción ejecutiva del sistema tras recibir el dictamen estructurado de la IA.
Aplica los umbrales de confianza y las políticas de preservación ambiental y no falsos positivos.

Niveles de decisión:
--------------------
1. `IGNORE`: Confianza baja (< 0.50) o evento no relevante (tránsito normal, portar pertenencias).
2. `LOG_ONLY`: Confianza moderada (0.50 <= c < umbral) o evento ambiguo. Se audita sin emitir audio.
3. `WARN`: Confianza alta (>= umbral, ej. >= 0.80) y acción clasificada como `possible_littering`.
   Dispara la síntesis de voz (`app.speech.openai_tts`) y reproducción (`app.speech.audio_output`).

Flujo de invocación:
--------------------
- Recibe el objeto `app.models.analysis.AIAnalysisResult` emitido por `app.ai.vision_client.VisionAI`.
- Retorna el string de decisión que se almacena en `EventModel.decision`.
"""

from app.models.analysis import AIAnalysisResult


class DecisionEngine:
    """
    Motor de reglas de negocio para determinar cuándo activar una advertencia preventiva por altavoz.
    """

    def __init__(self, warning_threshold: float = 0.80):
        """
        Args:
            warning_threshold (float): Umbral mínimo de certeza (ej. 0.80) para autorizar emisión de voz.
        """
        self.warning_threshold = warning_threshold

    def evaluate_decision(self, ai_result: AIAnalysisResult) -> str:
        """
        Evalúa el resultado estructurado de IA y decide la acción a tomar.

        Args:
            ai_result (AIAnalysisResult): Diagnóstico devuelto por el modelo multimodal.

        Returns:
            str: 'IGNORE', 'LOG_ONLY' o 'WARN'.
        """
        # Si la IA no detectó ningún evento relevante
        if not ai_result.event_detected:
            return "IGNORE"

        # Confianza demasiado baja: ignorar para evitar falsas alarmas
        if ai_result.confidence < 0.50:
            return "IGNORE"

        # Confianza intermedia: registrar en base de datos para análisis posterior, pero no advertir
        if 0.50 <= ai_result.confidence < self.warning_threshold:
            return "LOG_ONLY"

        # Confianza alta: verificar que sea una acción explícita de arrojo de residuos
        if ai_result.confidence >= self.warning_threshold:
            if ai_result.event_type == "possible_littering":
                return "WARN"
            return "LOG_ONLY"

        return "IGNORE"
