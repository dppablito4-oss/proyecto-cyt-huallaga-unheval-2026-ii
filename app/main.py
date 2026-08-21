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
- Gestionar los eventos de ciclo de vida de la aplicación (`startup` y `shutdown`).

Cómo ejecutar el servidor:
--------------------------
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
"""

import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.config import settings
from app.api.routes import api_router
from app.api.websocket import router as ws_router

# Configuración centralizada de logging con timestamps y niveles claros
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("HuallagaAIMonitor")

# Creación de la aplicación FastAPI con metadatos descriptivos
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema inteligente de vigilancia ambiental para la detección preventiva del arrojo de residuos sólidos en la ribera del río Huallaga."
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


@app.on_event("startup")
async def startup_event():
    """
    Hook de arranque: Se ejecuta al iniciar el proceso uvicorn.
    Permite inicializar recursos compartidos y registrar logs informativos.
    """
    logger.info("=" * 60)
    logger.info(f"   {settings.APP_NAME} v{settings.APP_VERSION} INICIADO")
    logger.info(f"   Entorno: {settings.APP_ENV} | Modo Debug: {settings.DEBUG}")
    logger.info(f"   Servidor disponible en: http://{settings.HOST}:{settings.PORT}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Hook de apagado: Se ejecuta al detener el servidor limpiamente (Ctrl + C / SIGTERM).
    """
    logger.info("Apagando Huallaga AI Monitor y liberando recursos...")
