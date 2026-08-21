from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class SystemMetrics(BaseModel):
    event_id: str
    timestamp: datetime
    camera_id: str = "CAM_001"
    frames_captured: int = 0
    frames_sent: int = 0
    image_resolution: str = "1280x720"
    jpeg_quality: int = 70
    payload_bytes: int = 0
    local_detection_confidence: float = 0.0
    ai_confidence: Optional[float] = None
    ai_model: str = "gpt-4o"
    ai_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    decision: str = "IGNORE"
