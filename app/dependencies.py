"""
Módulo de Inyección de Dependencias de FastAPI
=============================================

Responsabilidad:
----------------
Proveer las dependencias necesarias para los controladores y endpoints de FastAPI
(Settings, SystemState, Repositorios) mediante la inyección de dependencias `Depends(...)`.

Flujo de invocación:
--------------------
- Utilizado en `app.api.routes.status` y `app.api.routes.config` para obtener de forma limpia
  y desacoplada las instancias globales del sistema.
"""

from app.config import settings, Settings
from app.state import system_state, SystemState


def get_settings() -> Settings:
    """
    Inyector de dependencia que provee la instancia única de configuración `Settings`.
    Permite acceder a los parámetros globales en cualquier endpoint REST.
    """
    return settings


def get_system_state() -> SystemState:
    """
    Inyector de dependencia que provee la instancia de estado reactivo `SystemState`.
    Permite a los endpoints consultar o modificar el estado global del sistema.
    """
    return system_state
