"""
Script lanzador principal de SIVARH
==================================================
Proyecto de Investigación Aplicada en Ciencia y Tecnología (CyT 2026-II)
Universidad Nacional Hermilio Valdizán (UNHEVAL)
Facultad de Ciencias de la Educación
Carrera Profesional de Matemática y Física
Asignatura: Ciencias Naturales y del Ambiente

Ejecuta el servidor backend FastAPI y sirve el dashboard web en tiempo real.
"""

import sys
import os
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
import uvicorn

# Asegurar que el directorio raíz esté en sys.path
ROOT_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
os.chdir(ROOT_DIR)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.main import app


def _open_dashboard_when_ready() -> None:
    """Abre el panel una vez que Uvicorn ya acepta conexiones."""
    url = f"http://{settings.HOST}:{settings.PORT}"
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1):
                webbrowser.open(url)
                return
        except Exception:
            time.sleep(0.25)

if __name__ == "__main__":
    print(f"Iniciando {settings.APP_NAME} en http://{settings.HOST}:{settings.PORT}")
    frozen = getattr(sys, "frozen", False)
    if frozen:
        threading.Thread(target=_open_dashboard_when_ready, daemon=True).start()
    uvicorn.run(
        app if frozen else "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.DEBUG and not frozen),
    )
