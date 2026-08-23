import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.camera.worker import VideoPipelineWorker


def test_camera_switch_source():
    worker = VideoPipelineWorker()
    # Inicialmente la fuente es settings.CAMERA_SOURCE
    initial_source = settings.CAMERA_SOURCE

    # Cambiar a fuente 1
    worker.switch_source("1")
    assert settings.CAMERA_SOURCE == "1"

    # Cambiar a fuente 0
    worker.switch_source("0")
    assert settings.CAMERA_SOURCE == "0"

    # Restaurar
    worker.switch_source(initial_source)
