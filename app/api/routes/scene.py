"""Consulta del estado espacial estructurado de la cámara activa."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.scene import SceneState, ZoneDefinition

router = APIRouter(prefix="/scene")


class ZoneCalibrationRequest(BaseModel):
    zones: list[ZoneDefinition] = Field(..., min_length=1, max_length=12)


@router.get("", response_model=SceneState, summary="Consultar el estado espacial actual")
def get_scene_state() -> SceneState:
    from app.main import pipeline_worker

    return pipeline_worker.current_scene


@router.get("/zones", response_model=list[ZoneDefinition], summary="Consultar zonas calibradas")
def get_zones() -> list[ZoneDefinition]:
    from app.main import pipeline_worker

    return pipeline_worker.zone_definitions


@router.put("/zones", response_model=list[ZoneDefinition], summary="Guardar zonas calibradas")
def update_zones(payload: ZoneCalibrationRequest) -> list[ZoneDefinition]:
    from app.main import pipeline_worker

    names = [zone.name.strip().casefold() for zone in payload.zones]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="Los nombres de zona deben ser únicos.")
    if any(not name.replace("_", "").isalnum() for name in names):
        raise HTTPException(
            status_code=422,
            detail="Usa solo letras, números y guion bajo en los nombres de zona.",
        )
    normalized = [
        zone.model_copy(update={"name": name})
        for zone, name in zip(payload.zones, names)
    ]
    try:
        return pipeline_worker.update_zones(normalized)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
