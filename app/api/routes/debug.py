"""
Módulo de Rutas de Diagnóstico y Pruebas Manuales (Debug REST Routes)
=====================================================================

Responsabilidad:
----------------
Proveer endpoints auxiliares para verificar manualmente componentes aislados del sistema,
tales como la síntesis de voz (TTS) o la reproducción física de sonido.

Endpoints:
----------
- `POST /api/debug/test-speech`: Genera y reproduce un audio de prueba para verificar la salida de sonido.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.speech.openai_tts import OpenAISpeechService
from app.speech.audio_output import LocalSpeakerOutput

router = APIRouter(prefix="/debug")


class SpeechTestRequest(BaseModel):
    """Payload para solicitud de prueba de voz."""
    text: str = Field(
        default="Prueba del sistema de vigilancia ambiental del río Huallaga.",
        description="Texto a ser convertido a voz y reproducido."
    )


@router.post("/test-speech", summary="Ejecutar prueba de síntesis y reproducción de voz")
def test_speech(payload: SpeechTestRequest):
    """
    Sintetiza el texto recibido a un archivo de audio con OpenAI TTS
    y solicita su reproducción inmediata a través del altavoz configurado.
    """
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
