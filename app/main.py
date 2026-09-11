"""
Punto de Entrada Principal de la Aplicación FastAPI (Main Application Entry Point)
==================================================================================

Responsabilidad:
----------------
- Inicializar la instancia de `FastAPI`.
- Configurar el sistema de logging estándar.
- Aplicar políticas CORS para permitir comunicación segura con navegadores y clientes remotos.
- Registrar todas las rutas de la API REST (`/api/...`) y WebSockets (`/ws`).
- Servir los archivos estáticos del frontend (`frontend/index.html`, CSS, JS) en la raíz `/`.
- Gestionar el ciclo de vida de la aplicación mediante el gestor `lifespan`.
- Inicializar y detener el `VideoPipelineWorker` de captura continua.

Cómo ejecutar el servidor:
--------------------------
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Asegurar que el directorio raíz del proyecto esté en sys.path al ejecutarse como script directo
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.api.routes import api_router
from app.api.websocket import router as ws_router
from app.camera.worker import VideoPipelineWorker

# Configuración centralizada de logging con timestamps y niveles claros
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("HuallagaAIMonitor")

# Instancia global del worker de video, accesible desde los endpoints de control
pipeline_worker = VideoPipelineWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor de ciclo de vida de la aplicación FastAPI.
    Reemplaza los hooks on_event("startup") y on_event("shutdown") deprecados.
    """
    # ── Startup ──
    logger.info("=" * 60)
    logger.info(f"   {settings.APP_NAME} v{settings.APP_VERSION} INICIADO")
    logger.info(f"   Entorno: {settings.APP_ENV} | Modo Debug: {settings.DEBUG}")
    logger.info(f"   Modelo Visión: {settings.OPENAI_VISION_MODEL} | Detalle: {settings.IMAGE_DETAIL}")
    logger.info(f"   Servidor disponible en: http://{settings.HOST}:{settings.PORT}")
    logger.info("=" * 60)
    # Iniciar el pipeline de captura automáticamente
    pipeline_worker.start()

    yield

    # ── Shutdown ──
    pipeline_worker.stop()
    logger.info("Apagando SIVARH y liberando recursos...")


# Creación de la aplicación FastAPI con metadatos descriptivos
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SIVARH: Sistema Inteligente de Vigilancia Ambiental para las Riberas del Río Huallaga. UNHEVAL - Facultad de Ciencias de la Educación, Escuela Profesional de Matemática y Física. Curso: Ciencias Naturales y del Ambiente (2026-II).",
    lifespan=lifespan,
)

# Habilitar CORS (Cross-Origin Resource Sharing) para facilitar pruebas y desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar los endpoints REST bajo el prefijo /api y los canales WebSocket en /ws
app.include_router(api_router)
app.include_router(ws_router)

# Montar el frontend estático para servir directamente el dashboard HTML/CSS/JS
frontend_dir = settings.FRONTEND_DIR
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    logger.warning(f"Directorio de frontend no encontrado en: {frontend_dir}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
