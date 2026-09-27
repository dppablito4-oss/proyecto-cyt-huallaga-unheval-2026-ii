"""Prueba unitaria para la generación de reportes PDF (build_evidence_pdf y build_event_pdf)."""

import pytest
from datetime import datetime
from pathlib import Path

from app.models.event import EventModel, CaptureMetadata
from app.reports.pdf_report import build_evidence_pdf, build_event_pdf


def test_build_evidence_pdf(tmp_path: Path):
    output_pdf = tmp_path / "test_evidence.pdf"
    dummy_state = {
        "ai_model": "gpt-4o-mini",
        "last_decision": "WARN",
        "last_analysis_confidence": 0.95,
        "ai_latency": 1.25,
        "last_diagnosis": "Persona arrojando botella a la orilla del río.",
        "last_warning_message": "¡Por favor no arroje residuos al río Huallaga!",
        "logs": [
            {"time": "12:00:00", "level": "INFO", "message": "Inicio de sesión"},
            {"time": "12:00:05", "level": "WARN", "message": "Detección de arrojo"},
        ],
    }
    result_path = build_evidence_pdf(output_pdf, dummy_state, image_paths=[])
    assert result_path.is_file()
    assert result_path.stat().st_size > 0


def test_build_event_pdf(tmp_path: Path):
    output_pdf = tmp_path / "test_event.pdf"
    event = EventModel(
        id="test-event-uuid-123456789",
        camera_id="CAM_001",
        started_at=datetime.now(),
        decision="WARN",
        object_class="bottle",
        local_event_score=0.88,
        openai_confidence=0.92,
        desistimiento_confirmado=True,
        capture=CaptureMetadata(frame_paths=[]),
        analysis={
            "description": "Se observó lanzamiento de plástico.",
            "warning_message": "Advertencia emitida por altavoz.",
        },
        metrics={
            "ai_model": "gpt-4o-mini",
            "ai_latency_ms": 1100.0,
            "logs": [
                {"time": "12:05:00", "level": "TRACK", "message": "Track persona #1 detectado"},
                {"time": "12:05:03", "level": "NUDGE", "message": "Emitiendo advertencia"},
            ],
        },
    )
    result_path = build_event_pdf(output_pdf, event)
    assert result_path.is_file()
    assert result_path.stat().st_size > 0
