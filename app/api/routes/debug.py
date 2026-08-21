from fastapi import APIRouter
from pydantic import BaseModel
from app.speech.openai_tts import OpenAISpeechService
from app.speech.audio_output import LocalSpeakerOutput

router = APIRouter(prefix="/debug")

class SpeechTestRequest(BaseModel):
    text: str = "Prueba del sistema de vigilancia ambiental del río Huallaga."

@router.post("/test-speech")
def test_speech(payload: SpeechTestRequest):
    """Endpoint para probar manualmente la síntesis de voz (TTS)."""
    service = OpenAISpeechService()
    output_path = "data/audio/test_speech.mp3"
    result = service.generate_speech(payload.text, output_path)
    
    speaker = LocalSpeakerOutput()
    played = speaker.play(output_path) if result else False
    
    return {
        "text": payload.text,
        "audio_generated": result is not None,
        "audio_path": result,
        "played_locally": played
    }
