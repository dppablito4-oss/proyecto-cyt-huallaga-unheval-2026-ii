from types import SimpleNamespace

from app.ai.vision_client import VisionAIClient
from app.models.analysis import AIAnalysisResult


def test_vision_client_sends_local_metadata_with_keyframes():
    expected = AIAnalysisResult(
        person_detected=True,
        suspected_disposal=True,
        action_completed=False,
        confidence=0.6,
        event_type="SUSPICIOUS_ACTION",
        description="Caso ambiguo.",
    )
    captured = {}

    class FakeCompletions:
        def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(parsed=expected))]
            )

    client = VisionAIClient(api_key="test-key", model="test-model")
    client.client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        )
    )
    client._initialized = True

    result = client.analyze_sequence(
        [b"jpeg"],
        event_metadata={"object_track_id": 8, "local_event_score": 0.6},
    )

    user_content = captured["messages"][1]["content"]
    assert result == expected
    assert '"object_track_id":8' in user_content[0]["text"]
    assert "puede contener errores" in user_content[0]["text"]
    assert user_content[1]["type"] == "image_url"
    assert client.last_call_used_api is True
