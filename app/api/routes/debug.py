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

import logging
from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.speech.openai_tts import OpenAISpeechService
from app.speech.audio_output import LocalSpeakerOutput
from app.vision.image_processor import ImageProcessor
from app.ai.vision_client import VisionAI
from app.events.rules import DecisionEngine
from app.config import settings

router = APIRouter(prefix="/debug")
logger = logging.getLogger(__name__)


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
    speed: Optional[float] = Field(
        default=None,
        ge=0.25,
        le=4.0,
        description="Velocidad de reproducción/síntesis, entre 0.25 y 4.0."
    )


class EventSpeechTestRequest(BaseModel):
    """Descripción de un evento para que Luna redacte y reproduzca un guion de prueba."""

    event_description: str = Field(min_length=5, max_length=500)
    voice: Optional[str] = Field(default=None)
    speed: Optional[float] = Field(default=None, ge=0.75, le=1.35)


class GeneratedWarningScript(BaseModel):
    """Respuesta estructurada del generador textual de guiones."""

    script: str = Field(min_length=5, max_length=300)


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
    service = OpenAISpeechService(voice=payload.voice, speed=payload.speed)
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


@router.post("/generate-event-speech", summary="Generar con Luna y reproducir un guion desde un evento descrito")
def generate_event_speech(payload: EventSpeechTestRequest):
    """Convierte una descripción textual de prueba en un guion comunitario y lo envía al TTS."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY no está configurada.")

    prompt_path = settings.PROMPTS_DIR / "warning_script_from_event.txt"
    try:
        from openai import OpenAI

        system_prompt = prompt_path.read_text(encoding="utf-8").strip()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.beta.chat.completions.parse(
            model=settings.OPENAI_VISION_MODEL,
            reasoning_effort=settings.OPENAI_VISION_REASONING_EFFORT,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Evento descrito para la prueba: {payload.event_description}",
                },
            ],
            response_format=GeneratedWarningScript,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None or not parsed.script.strip():
            raise ValueError("Luna no devolvió un guion válido.")
        script = parsed.script.strip()
    except Exception as exc:
        logger.error("Error al generar el guion de prueba con Luna: %s", exc)
        raise HTTPException(status_code=502, detail="Luna no pudo generar el guion de prueba.") from exc

    from app.state import system_state

    system_state.add_log("AI", f"[GUION IA] Luna generó: \"{script}\"")
    service = OpenAISpeechService(voice=payload.voice, speed=payload.speed)
    output_path = f"data/audio/test_event_{datetime.now():%Y%m%d_%H%M%S}.wav"
    result = service.generate_and_play_streaming(script, output_path, LocalSpeakerOutput())
    if result is None:
        raise HTTPException(status_code=502, detail="El guion fue generado, pero el TTS no pudo reproducirlo.")

    system_state.add_log("AUDIO", f"[AUDIO] Guion de prueba reproducido (voz={service.voice}, velocidad={service.speed:.2f}x).")
    return {
        "event_description": payload.event_description,
        "generated_script": script,
        "model": settings.OPENAI_VISION_MODEL,
        "voice": service.voice,
        "speed": service.speed,
        "audio_generated": True,
        "audio_path": result,
        "played_locally": True,
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
