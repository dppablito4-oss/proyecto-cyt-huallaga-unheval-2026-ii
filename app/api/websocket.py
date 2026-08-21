import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from app.state import system_state

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Cliente WebSocket conectado.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Cliente WebSocket desconectado.")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Enviar estado inicial al conectar
        await websocket.send_json({
            "type": "system_state",
            "data": system_state.to_dict()
        })
        
        while True:
            # Mantener conexión activa enviando latidos periódicos de estado
            await asyncio.sleep(2)
            await websocket.send_json({
                "type": "system_state",
                "data": system_state.to_dict()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error WebSocket: {e}")
        manager.disconnect(websocket)
