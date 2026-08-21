from app.models.analysis import AIAnalysisResult

class DecisionEngine:
    """
    Motor de decisiones local. Combina el resultado del análisis de IA,
    el umbral de confianza configurado y las reglas de negocio para determinar
    la acción a tomar (IGNORE, LOG_ONLY, WARN).
    """

    def __init__(self, warning_threshold: float = 0.80):
        self.warning_threshold = warning_threshold

    def evaluate_decision(self, ai_result: AIAnalysisResult) -> str:
        """
        Evalúa el resultado de IA y retorna la decisión final.
        """
        if not ai_result.event_detected:
            return "IGNORE"

        if ai_result.confidence < 0.50:
            return "IGNORE"

        if 0.50 <= ai_result.confidence < self.warning_threshold:
            return "LOG_ONLY"

        if ai_result.confidence >= self.warning_threshold:
            if ai_result.event_type == "possible_littering":
                return "WARN"
            return "LOG_ONLY"

        return "IGNORE"
