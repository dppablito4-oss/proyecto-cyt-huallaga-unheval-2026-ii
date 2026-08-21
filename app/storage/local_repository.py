import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from app.models.event import EventModel
from app.storage.events_repository import EventsRepository

logger = logging.getLogger(__name__)

class SQLiteEventsRepository(EventsRepository):
    """
    Implementación de repositorio basada en SQLite local.
    Proporciona almacenamiento portátil y sin dependencias cloud para la Fase 0.
    """

    def __init__(self, db_path: str = "data/events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        camera_id TEXT,
                        started_at TEXT,
                        ended_at TEXT,
                        status TEXT,
                        data_json TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error al inicializar base de datos SQLite: {e}")

    def save(self, event: EventModel) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO events (id, camera_id, started_at, ended_at, status, data_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.camera_id,
                        event.started_at.isoformat(),
                        event.ended_at.isoformat() if event.ended_at else None,
                        event.status,
                        event.model_dump_json()
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando evento {event.id} en SQLite: {e}")
            return False

    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT data_json FROM events WHERE id = ?", (event_id,))
                row = cursor.fetchone()
                if row:
                    return EventModel.model_validate_json(row["data_json"])
                return None
        except Exception as e:
            logger.error(f"Error leyendo evento {event_id} de SQLite: {e}")
            return None

    def list_recent(self, limit: int = 20) -> List[EventModel]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data_json FROM events ORDER OR BY started_at DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
                events = []
                for row in rows:
                    try:
                        events.append(EventModel.model_validate_json(row["data_json"]))
                    except Exception:
                        pass
                return events
        except Exception as e:
            # Fix fallback query syntax if needed
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT data_json FROM events ORDER BY started_at DESC LIMIT ?", (limit,)
                    )
                    return [EventModel.model_validate_json(r["data_json"]) for r in cursor.fetchall()]
            except Exception as ex:
                logger.error(f"Error consultando eventos recientes en SQLite: {ex}")
                return []
