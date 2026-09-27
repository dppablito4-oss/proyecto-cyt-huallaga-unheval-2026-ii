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
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS event_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL,
                        logged_at TEXT,
                        level TEXT,
                        message TEXT,
                        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_event_id ON event_logs(event_id)")
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
        Inserta o actualiza un registro de evento en la tabla `events` y sus logs en `event_logs`.
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

                # Guardar logs en la tabla SQL relacional event_logs
                logs = (
                    event.metrics.get("logs")
                    or (event.event_trace.get("logs") if isinstance(event.event_trace, dict) else [])
                    or []
                )
                if logs:
                    conn.execute("DELETE FROM event_logs WHERE event_id = ?", (event.id,))
                    for log in logs:
                        conn.execute(
                            """
                            INSERT INTO event_logs (event_id, logged_at, level, message)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                event.id,
                                log.get("time") or datetime.now().isoformat(),
                                log.get("level", "INFO"),
                                log.get("message", "")
                            )
                        )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando evento {event.id} en SQLite: {e}")
            return False

    def get_event_logs(self, event_id: str) -> List[dict]:
        """Recupera los logs asociados a un evento específico desde la base de datos SQL."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT logged_at as time, level, message FROM event_logs WHERE event_id = ? ORDER BY id ASC",
                    (event_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error consultando logs del evento {event_id} en SQLite: {e}")
            return []

    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        """
        Busca un evento por su ID primario, deserializa el JSON a `EventModel`
        e hidrata sus logs desde la tabla `event_logs`.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT data_json FROM events WHERE id = ?", (event_id,))
                row = cursor.fetchone()
                if row:
                    event = self._hydrate_legacy_paths(
                        EventModel.model_validate_json(row["data_json"])
                    )
                    if not event.metrics.get("logs"):
                        sql_logs = self.get_event_logs(event.id)
                        if sql_logs:
                            event.metrics["logs"] = sql_logs
                    return event
                return None
        except Exception as e:
            logger.error(f"Error recuperando evento {event_id} de SQLite: {e}")
            return None

    def list_recent(self, limit: int = 20) -> List[EventModel]:
        """
        Recupera los últimos $limit$ eventos ordenados cronológicamente desde el más reciente
        con sus logs asociados.
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
                        ev = self._hydrate_legacy_paths(
                            EventModel.model_validate_json(row["data_json"])
                        )
                        if not ev.metrics.get("logs"):
                            sql_logs = self.get_event_logs(ev.id)
                            if sql_logs:
                                ev.metrics["logs"] = sql_logs
                        events.append(ev)
                    except Exception:
                        pass
                return events
        except Exception as e:
            logger.error(f"Error consultando eventos recientes en SQLite: {e}")
            return []

    def delete(self, event_id: str) -> bool:
        """
        Elimina un evento registrado, sus logs en SQL y sus fotogramas de evidencia asociados.
        """
        try:
            event = self.get_by_id(event_id)
            with self._get_connection() as conn:
                conn.execute("DELETE FROM event_logs WHERE event_id = ?", (event_id,))
                cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()
                deleted = cursor.rowcount > 0
            if event and event.capture and event.capture.frame_paths:
                for fp in event.capture.frame_paths:
                    try:
                        p = Path(fp)
                        if not p.is_absolute():
                            p = self.db_path.parent.parent / p
                        if p.is_file():
                            p.unlink(missing_ok=True)
                    except Exception:
                        pass
            return deleted
        except Exception as e:
            logger.error(f"Error eliminando evento {event_id} de SQLite: {e}")
            return False

    def clear_all(self) -> int:
        """
        Elimina todos los eventos registrados en la base de datos, sus logs y fotogramas.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM events")
                total = cursor.fetchone()[0]
                conn.execute("DELETE FROM event_logs")
                conn.execute("DELETE FROM events")
                conn.commit()
            frames_dir = self.db_path.parent / "frames"
            if frames_dir.is_dir():
                for frame_file in frames_dir.glob("*.jpg"):
                    try:
                        frame_file.unlink(missing_ok=True)
                    except Exception:
                        pass
            return total
        except Exception as e:
            logger.error(f"Error limpiando eventos en SQLite: {e}")
            return 0

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

