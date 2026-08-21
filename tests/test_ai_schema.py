import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.models.analysis import AIAnalysisResult
from app.events.rules import DecisionEngine


def test_ai_analysis_schema_valid():
    # 1. Caso de arrojo confirmado (debe disparar WARN)
    waste_result = AIAnalysisResult(
        person_detected=True,
        suspected_disposal=True,
        action_completed=True,
        confidence=0.92,
        event_type="WASTE_DISPOSAL",
        description="Una persona abandona una botella en la ribera del río.",
        warning_message="Por favor, evite arrojar residuos en esta zona."
    )
    assert waste_result.person_detected is True
    assert waste_result.action_completed is True
    assert waste_result.confidence == 0.92

    engine = DecisionEngine(warning_threshold=0.80)
    decision = engine.evaluate_decision(waste_result)
    assert decision == "WARN"

    # 2. Caso sospechoso pero no completado (debe ser LOG_ONLY)
    suspicious_result = AIAnalysisResult(
        person_detected=True,
        suspected_disposal=True,
        action_completed=False,
        confidence=0.85,
        event_type="SUSPICIOUS_ACTION",
        description="Persona sosteniendo una bolsa pero no la suelta.",
        warning_message=None
    )
    assert engine.evaluate_decision(suspicious_result) == "LOG_ONLY"

    # 3. Caso persona presente normal (debe ser LOG_ONLY o IGNORE según confianza)
    person_result = AIAnalysisResult(
        person_detected=True,
        suspected_disposal=False,
        action_completed=False,
        confidence=0.75,
        event_type="PERSON_PRESENT",
        description="Persona caminando normalmente.",
        warning_message=None
    )
    assert engine.evaluate_decision(person_result) == "LOG_ONLY"

    # 4. Caso sin personas o baja confianza (debe ser IGNORE)
    no_event = AIAnalysisResult(
        person_detected=False,
        suspected_disposal=False,
        action_completed=False,
        confidence=0.20,
        event_type="NO_EVENT",
        description="Sin actividad.",
        warning_message=None
    )
    assert engine.evaluate_decision(no_event) == "IGNORE"

    print("test_ai_analysis_schema_valid PASSED")


if __name__ == "__main__":
    test_ai_analysis_schema_valid()
