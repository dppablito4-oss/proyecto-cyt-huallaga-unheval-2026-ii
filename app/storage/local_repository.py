"""
Módulo de Repositorio Local en SQLite (SQLiteEventsRepository)
==============================================================

Responsabilidad:
----------------
Proveer persistencia local ligera, confiable y sin dependencias de red o servicios en la nube
utilizando SQLite (`data/events.db`).

Flujo de invocación:
--------------------
- Crea automáticamente la tabla `events` en el arranque de la aplicación si no existe.
- Guarda el estado completo de cada evento serializado en formato JSON (`EventModel.model_dump_json()`).
- Es consultado por los endpoints REST `GET /api/events` y `GET /api/events/{id}` en `app.api.routes.events`.
"""

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
    Implementación concreta de persistencia en base de datos SQLite integrada.
    """

    def __init__(self, db_path: str = "data/events.db"):
        """
        Args:
            db_path (str): Ruta al archivo de base de datos local SQLite.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Crea una conexión con row_factory para acceso por nombre de columna."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Crea el esquema de base de datos relacional si aún no está presente."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        camera_id TEXT,
                        started_at TEXT,
                        ended_at TEXT,
                        status TEXT,
                        desistimiento_confirmado INTEGER,
                        post_alert_outcome TEXT,
                        data_json TEXT
                    )
                """)
                columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(events)").fetchall()
                }
                if "desistimiento_confirmado" not in columns:
                    conn.execute(
                        "ALTER TABLE events ADD COLUMN desistimiento_confirmado INTEGER"
                    )
                if "post_alert_outcome" not in columns:
                    conn.execute("ALTER TABLE events ADD COLUMN post_alert_outcome TEXT")
                conn.commit()
        except Exception as e:
            logger.error(f"Error al inicializar base de datos SQLite: {e}")

    def save(self, event: EventModel) -> bool:
        """
        Inserta o actualiza un registro de evento en la tabla `events`.
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO events (
                        id, camera_id, started_at, ended_at, status,
                        desistimiento_confirmado, post_alert_outcome, data_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.camera_id,
                        event.started_at.isoformat(),
                        event.ended_at.isoformat() if event.ended_at else None,
                        event.status,
                        (
                            None
                            if event.desistimiento_confirmado is None
                            else int(event.desistimiento_confirmado)
                        ),
                        event.post_alert_outcome,
                        event.model_dump_json()
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando evento {event.id} en SQLite: {e}")
            return False

    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        """
        Busca un evento por su ID primario y deserializa el JSON a `EventModel`.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT data_json FROM events WHERE id = ?", (event_id,))
                row = cursor.fetchone()
                if row:
                    return self._hydrate_legacy_paths(
                        EventModel.model_validate_json(row["data_json"])
                    )
                return None
        except Exception as e:
            logger.error(f"Error recuperando evento {event_id} de SQLite: {e}")
            return None

    def list_recent(self, limit: int = 20) -> List[EventModel]:
        """
        Recupera los últimos $limit$ eventos ordenados cronológicamente desde el más reciente.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data_json FROM events ORDER BY started_at DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
                events = []
                for row in rows:
                    try:
                        events.append(
                            self._hydrate_legacy_paths(
                                EventModel.model_validate_json(row["data_json"])
                            )
                        )
                    except Exception:
                        pass
                return events
        except Exception as e:
            logger.error(f"Error consultando eventos recientes en SQLite: {e}")
            return []

    def _hydrate_legacy_paths(self, event: EventModel) -> EventModel:
        """Recupera previews antiguos cuyo evento se guardó antes de `frame_paths`."""
        if event.capture.frame_paths:
            return event
        frames_dir = self.db_path.parent / "frames"
        if not frames_dir.is_dir():
            return event
        matches = sorted(frames_dir.glob(f"auto-preview-{event.id[:8]}-*.jpg"))
        if matches:
            event.capture.frame_paths = [str(path.resolve()) for path in matches[:4]]
            event.capture.selected_frames = len(event.capture.frame_paths)
        return event
