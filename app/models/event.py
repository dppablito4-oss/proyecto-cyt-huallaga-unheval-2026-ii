from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class LocalDetection(BaseModel):
    label: str = "person"
    confidence: float
    bbox: Optional[BoundingBox] = None

class LocalDetectionSummary(BaseModel):
    persons: int = 0
    max_confidence: float = 0.0
    detections: List[LocalDetection] = Field(default_factory=list)

class CaptureMetadata(BaseModel):
    total_frames: int = 0
    selected_frames: int = 0
    jpeg_quality: int = 70
    frame_paths: List[str] = Field(default_factory=list)

class EventModel(BaseModel):
    id: str
    camera_id: str = "CAM_001"
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    status: str = "created"  # created, capturing, analyzing, completed, failed
    local_detection: LocalDetectionSummary = Field(default_factory=LocalDetectionSummary)
    capture: CaptureMetadata = Field(default_factory=CaptureMetadata)
    analysis: Optional[Dict[str, Any]] = None
    decision: Optional[str] = None  # IGNORE, LOG_ONLY, WARN
    metrics: Dict[str, Any] = Field(default_factory=dict)
