from fastapi import APIRouter
from app.api.routes.status import router as status_router
from app.api.routes.events import router as events_router
from app.api.routes.cameras import router as cameras_router
from app.api.routes.config import router as config_router
from app.api.routes.debug import router as debug_router
from app.api.routes.system import router as system_router

api_router = APIRouter(prefix="/api")
api_router.include_router(status_router, tags=["Status"])
api_router.include_router(events_router, tags=["Events"])
api_router.include_router(cameras_router, tags=["Cameras"])
api_router.include_router(config_router, tags=["Config"])
api_router.include_router(debug_router, tags=["Debug"])
api_router.include_router(system_router, tags=["System"])

