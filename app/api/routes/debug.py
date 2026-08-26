"""
Módulo de Rutas de Diagnóstico y Pruebas Manuales (Debug REST Routes)
=====================================================================

Responsabilidad:
----------------
Proveer endpoints auxiliares para verificar manualmente componentes aislados del sistema,
tales como la síntesis de voz (TTS), la reproducción física de sonido y el análisis
multimodal de imágenes.

Endpoints:
----------
- `POST /api/debug/test-speech`: Genera y reproduce un audio de prueba para verificar la salida de sonido.
- `POST /api/debug/test-analysis`: Prueba el análisis multimodal de visión con fotogramas sintéticos o del buffer.
"""

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from app.speech.openai_tts import OpenAISpeechService
from app.speech.audio_output import LocalSpeakerOutput
from app.vision.image_processor import ImageProcessor
from app.ai.vision_client import VisionAI
from app.events.rules import DecisionEngine
from app.config import settings

router = APIRouter(prefix="/debug")


class SpeechTestRequest(BaseModel):
    """Payload para solicitud de prueba de voz."""
    text: str = Field(
        default="Prueba de advertencia ambiental de SIVARH en el sector Puente Huallaga.",
        description="Texto a ser convertido a voz y reproducido."
    )
    voice: Optional[str] = Field(
        default=None,
        description="Voz TTS a probar. Si se omite, usa OPENAI_TTS_VOICE."
    )


class AnalysisTestRequest(BaseModel):
    """Payload para solicitud de prueba de análisis de visión."""
    use_buffer: bool = Field(
        default=False,
        description="Si es True, usa los fotogramas actuales del buffer. Si es False, genera frames sintéticos."
    )
    num_frames: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Cantidad de frames sintéticos a generar para la prueba."
    )


@router.post("/test-speech", summary="Ejecutar prueba de síntesis y reproducción de voz")
def test_speech(payload: SpeechTestRequest):
    """
    Sintetiza el texto recibido a un archivo de audio con OpenAI TTS
    y solicita su reproducción inmediata a través del altavoz configurado.
    """
    service = OpenAISpeechService(voice=payload.voice)
    output_path = "data/audio/test_speech.wav"

    speaker = LocalSpeakerOutput()
    result = service.generate_and_play_streaming(payload.text, output_path, speaker)

    return {
        "text": payload.text,
        "voice": service.voice,
        "speed": service.speed,
        "audio_generated": result is not None,
        "audio_path": result,
        "played_locally": result is not None
    }


@router.post("/test-analysis", summary="Ejecutar prueba de análisis multimodal de visión")
def test_analysis(payload: AnalysisTestRequest):
    """
    Ejecuta una inferencia de prueba del pipeline de análisis multimodal.
    Puede utilizar fotogramas del buffer activo o generar frames sintéticos.
    """
    processor = ImageProcessor(
        max_width=settings.IMAGE_MAX_WIDTH,
        jpeg_quality=settings.JPEG_QUALITY
    )
    vision = VisionAI()
    vision.initialize()
    decision_engine = DecisionEngine(warning_threshold=settings.AI_WARNING_THRESHOLD)

    jpeg_frames = []

    if payload.use_buffer:
        # Intentar obtener frames del buffer del pipeline activo
        try:
            from app.main import pipeline_worker
            if hasattr(pipeline_worker, '_frame_buffer'):
                frames = pipeline_worker._frame_buffer.get_last_n_frames(payload.num_frames)
                for ts, frame in frames:
                    jpeg_frames.append(processor.compress_jpeg(frame))
        except Exception:
            pass

    # Si no hay frames del buffer, generar frames sintéticos
    if not jpeg_frames:
        for i in range(payload.num_frames):
            fake = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
            jpeg_frames.append(processor.compress_jpeg(fake))

    # Ejecutar análisis con VisionAIClient (maneja Base64 internamente)
    ai_result = vision.analyze_sequence(jpeg_frames)
    decision = decision_engine.evaluate_decision(ai_result)

    return {
        "frames_analyzed": len(jpeg_frames),
        "source": "buffer" if payload.use_buffer and jpeg_frames else "synthetic",
        "model": settings.OPENAI_VISION_MODEL,
        "image_detail": settings.IMAGE_DETAIL,
        "analysis": ai_result.model_dump(),
        "decision": decision
    }
