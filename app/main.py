import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.config import settings
from app.api.routes import api_router
from app.api.websocket import router as ws_router

# Configurar logging estándar del sistema
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("HuallagaAIMonitor")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema inteligente de vigilancia ambiental para la ribera del río Huallaga"
)

# Configuración CORS para pruebas frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir API routers y WebSockets
app.include_router(api_router)
app.include_router(ws_router)

# Montar frontend estático si la carpeta existe
frontend_dir = settings.FRONTEND_DIR
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    logger.warning(f"Carpeta frontend no encontrada en {frontend_dir}")

@app.on_event("startup")
async def startup_event():
    logger.info(f"=== {settings.APP_NAME} v{settings.APP_VERSION} iniciado ===")
    logger.info(f"Entorno: {settings.APP_ENV} | Host: {settings.HOST}:{settings.PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=== Apagando Huallaga AI Monitor ===")
