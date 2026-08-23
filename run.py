"""
Script lanzador principal para Huallaga AI Monitor
==================================================
Ejecuta el servidor backend FastAPI y sirve el dashboard web.
"""

import sys
from pathlib import Path
import uvicorn

# Asegurar que el directorio raíz esté en sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings

if __name__ == "__main__":
    print(f"Iniciando {settings.APP_NAME} en http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
