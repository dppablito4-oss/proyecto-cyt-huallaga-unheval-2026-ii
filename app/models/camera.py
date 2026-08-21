from typing import Optional
from pydantic import BaseModel

class CameraStatus(BaseModel):
    camera_id: str = "CAM_001"
    source: str = "0"
    is_connected: bool = False
    width: int = 1280
    height: int = 720
    fps: float = 0.0
    error_message: Optional[str] = None
