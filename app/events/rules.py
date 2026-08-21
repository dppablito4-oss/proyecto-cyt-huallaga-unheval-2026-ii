"""
Módulo de Motor de Decisiones (DecisionEngine)
==============================================

Responsabilidad:
----------------
Determinar la acción ejecutiva del sistema tras recibir el dictamen estructurado de VisionAI.
Aplica reglas deterministas para evitar falsas alarmas y garantizar que el altavoz
sólo se active ante eventos consumados de arrojo de residuos.

Niveles de decisión:
--------------------
1. `IGNORE`:
   - Confianza global < 0.50, o
   - No se detectó persona (`person_detected == False`), o
   - `event_type == "NO_EVENT"`.

2. `LOG_ONLY`:
   - Confianza >= 0.50 pero NO cumple todas las condiciones para emitir advertencia sonora
     (por ejemplo: `action_completed == False`, persona caminando, manipulación dudosa).
   - Se almacena en la base de datos SQLite para auditoría e investigación académica.

3. `WARN`:
   - `confidence >= 0.80` (o umbral configurado), Y
   - `event_type == "WASTE_DISPOSAL"`, Y
   - `action_completed is True` (evidencia visual de que el residuo fue soltado/abandonado).
   - Dispara la síntesis de voz (`app.speech.openai_tts`) y reproducción (`app.speech.audio_output`).
"""

from app.models.analysis import AIAnalysisResult


class DecisionEngine:
    """
    Motor de reglas deterministas para autorizar o denegar la emisión de advertencias sonoras.
    La IA nunca controla directamente el altavoz; DecisionEngine toma la decisión final.
    """

    def __init__(self, warning_threshold: float = 0.80):
        """
        Args:
            warning_threshold (float): Umbral mínimo de confianza (por defecto 0.80).
        """
        self.warning_threshold = warning_threshold

    def evaluate_decision(self, ai_result: AIAnalysisResult) -> str:
        """
        Evalúa el diagnóstico de VisionAI y determina el nivel de acción ejecutiva.

        Args:
            ai_result (AIAnalysisResult): Diagnóstico estructurado de la IA.

        Returns:
            str: 'IGNORE', 'LOG_ONLY' o 'WARN'.
        """
        # 1. Descartar si la confianza es muy baja, no hay personas o no hay evento
        if ai_result.confidence < 0.50 or not ai_result.person_detected or ai_result.event_type == "NO_EVENT":
            return "IGNORE"

        # 2. Regla de Advertencia Estricta (WARN):
        # Requiere: alta confianza + tipo de evento WASTE_DISPOSAL + acción consumada (action_completed = True)
        should_warn = (
            ai_result.confidence >= self.warning_threshold
            and ai_result.event_type == "WASTE_DISPOSAL"
            and ai_result.action_completed is True
        )

        if should_warn:
            return "WARN"

        # 3. En cualquier otro caso con confianza >= 0.50 (ej. sospechoso pero no confirmado), auditar sin sonido
        return "LOG_ONLY"
