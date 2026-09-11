"""Consulta del estado espacial estructurado de la cámara activa."""

from fastapi import APIRouter

from app.models.scene import SceneState

router = APIRouter(prefix="/scene")


@router.get("", response_model=SceneState, summary="Consultar el estado espacial actual")
def get_scene_state() -> SceneState:
    from app.main import pipeline_worker

    return pipeline_worker.current_scene
