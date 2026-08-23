"""
Módulo de WebSockets para Difusión en Tiempo Real (WebSocket Manager)
=====================================================================

Responsabilidad:
----------------
Mantener conexiones bidireccionales persistentes con los navegadores web clientes
mediante la ruta `/ws`, permitiendo actualizar reactivamente los indicadores del dashboard
(estado de cámara, conteo de personas, eventos en curso, alertas emitidas)
sin recurrir a consultas continuas (polling) por HTTP.

Flujo de invocación:
--------------------
- Al abrir la interfaz web en `frontend/`, el script `frontend/js/websocket.js` abre la conexión WS.
- El servidor acepta la conexión, envía inmediatamente una instantánea del estado actual
  (`system_state.to_dict()`) y emite latidos periódicos de sincronización.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from app.state import system_state

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Administrador de conexiones WebSocket activas. Permite gestionar suscripciones
    y emitir mensajes en difusión (broadcast) a todos los dashboards conectados.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Acepta y registra una nueva conexión de cliente WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Cliente WebSocket conectado. Conexiones activas: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remueve la conexión cuando el cliente cierra la pestaña o pierde red."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Cliente WebSocket desconectado. Conexiones activas: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envía un mensaje JSON a todas las conexiones WebSocket vivas."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Punto de conexión WebSocket para el frontend dashboard.
    Mantiene la sesión viva y transmite el estado del sistema.
    """
    await manager.connect(websocket)
    try:
        # Enviar estado actual inmediatamente tras conectarse
        await websocket.send_json({
            "type": "system_state",
            "data": system_state.to_dict()
        })
        
        while True:
            # Latido periódico de actualización cada 1 segundo
            await asyncio.sleep(1)
            await websocket.send_json({
                "type": "system_state",
                "data": system_state.to_dict()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Excepción en canal WebSocket: {e}")
        manager.disconnect(websocket)
