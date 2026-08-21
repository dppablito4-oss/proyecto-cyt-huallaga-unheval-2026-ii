from fastapi import APIRouter, Depends
from app.dependencies import get_system_state
from app.state import SystemState

router = APIRouter()

@router.get("/status")
def get_system_status(state: SystemState = Depends(get_system_state)):
    """Retorna el estado general del sistema."""
    return state.to_dict()

@router.get("/health")
def health_check():
    """Endpoint mínimo de salud (health check)."""
    return {"status": "ok", "service": "Huallaga AI Monitor"}
