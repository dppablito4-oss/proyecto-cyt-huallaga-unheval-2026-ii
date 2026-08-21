from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SystemStatusModel(BaseModel):
    running: bool = True
    camera_connected: bool = False
    camera_source: str = "0"
    fps: float = 0.0
    persons_detected: int = 0
    active_event: bool = False
    last_event_time: Optional[str] = None
    last_analysis_confidence: Optional[float] = None
    last_warning_message: Optional[str] = None
    ai_model: str = "gpt-4o"
    frames_per_analysis: int = 5

class SystemState:
    def __init__(self):
        self._running = True
        self._camera_connected = False
        self._camera_source = "0"
        self._fps = 0.0
        self._persons_detected = 0
        self._active_event = False
        self._last_event_time: Optional[datetime] = None
        self._last_analysis_confidence: Optional[float] = None
        self._last_warning_message: Optional[str] = None
        self._ai_model = "gpt-4o"
        self._frames_per_analysis = 5
        self._total_events_processed = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "camera_connected": self._camera_connected,
            "camera_source": self._camera_source,
            "fps": self._fps,
            "persons_detected": self._persons_detected,
            "active_event": self._active_event,
            "last_event_time": self._last_event_time.isoformat() if self._last_event_time else None,
            "last_analysis_confidence": self._last_analysis_confidence,
            "last_warning_message": self._last_warning_message,
            "ai_model": self._ai_model,
            "frames_per_analysis": self._frames_per_analysis,
            "total_events_processed": self._total_events_processed
        }

    def set_camera_status(self, connected: bool, source: str = "0", fps: float = 0.0):
        self._camera_connected = connected
        self._camera_source = source
        self._fps = fps

    def set_persons_detected(self, count: int):
        self._persons_detected = count

    def set_active_event(self, active: bool):
        self._active_event = active
        if active:
            self._last_event_time = datetime.now()

    def record_analysis_result(self, confidence: Optional[float], warning_message: Optional[str]):
        self._last_analysis_confidence = confidence
        self._last_warning_message = warning_message
        self._total_events_processed += 1

system_state = SystemState()
