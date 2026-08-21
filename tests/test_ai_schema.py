import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.models.analysis import AIAnalysisResult

def test_ai_analysis_schema_valid():
    result = AIAnalysisResult(
        event_detected=True,
        confidence=0.92,
        event_type="possible_littering",
        object="botella de plástico",
        description="Una persona abandona una botella en la ribera del río.",
        recommended_action="warn",
        warning_message="Por favor, recoja sus residuos y cuide el río Huallaga."
    )
    assert result.event_detected is True
    assert result.confidence == 0.92
    print("test_ai_analysis_schema_valid PASSED")

if __name__ == "__main__":
    test_ai_analysis_schema_valid()
