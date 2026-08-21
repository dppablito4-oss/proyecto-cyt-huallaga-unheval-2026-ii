"""
Módulo de Rutas de Estado y Salud (Status & Health Routes)
==========================================================

Responsabilidad:
----------------
Proveer endpoints REST para monitorizar el estado operativo general del sistema
y verificar su disponibilidad mediante sondas de salud (health checks).

Endpoints:
----------
- `GET /api/status`: Devuelve el JSON completo del estado del sistema (`SystemState`).
- `GET /api/health`: Endpoint ligero para monitorización de disponibilidad.
"""

from fastapi import APIRouter, Depends
from app.dependencies import get_system_state
from app.state import SystemState

router = APIRouter()


@router.get("/status", summary="Obtener estado operativo del sistema")
def get_system_status(state: SystemState = Depends(get_system_state)):
    """
    Retorna el estado global del sistema:
    - Estado de cámara, FPS, personas detectadas.
    - Estado de eventos activos y último diagnóstico.
    - Modelo de IA configurado y métricas de procesamiento.
    """
    return state.to_dict()


@router.get("/health", summary="Comprobar salud del servicio")
def health_check():
    """
    Sonda básica de disponibilidad HTTP (Health Check).
    Retorna `{ status: 'ok', service: 'Huallaga AI Monitor' }`.
    """
    return {"status": "ok", "service": "Huallaga AI Monitor"}
