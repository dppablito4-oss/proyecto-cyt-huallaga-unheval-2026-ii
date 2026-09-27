"""Pruebas unitarias para SQLiteEventsRepository (tabla event_logs, borrado individual y limpieza total)."""

import pytest
from datetime import datetime
from pathlib import Path

from app.models.event import EventModel, CaptureMetadata
from app.storage.local_repository import SQLiteEventsRepository


def test_sqlite_event_logs_and_deletion(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    repo = SQLiteEventsRepository(str(db_file))

    event = EventModel(
        id="evt-sql-test-001",
        camera_id="CAM_001",
        started_at=datetime.now(),
        decision="WARN",
        object_class="plastic_bag",
        metrics={
            "logs": [
                {"time": "10:00:00", "level": "INFO", "message": "Detección inicial"},
                {"time": "10:00:02", "level": "WARN", "message": "Arrojo verificado"},
            ]
        },
    )

    # 1. Guardar evento
    assert repo.save(event) is True

    # 2. Consultar logs directamente desde la tabla SQL
    logs = repo.get_event_logs(event.id)
    assert len(logs) == 2
    assert logs[0]["level"] == "INFO"
    assert logs[0]["message"] == "Detección inicial"
    assert logs[1]["level"] == "WARN"

    # 3. get_by_id recupera los logs hidratados
    fetched = repo.get_by_id(event.id)
    assert fetched is not None
    assert fetched.metrics.get("logs") == logs

    # 4. Eliminar evento individual
    assert repo.delete(event.id) is True
    assert repo.get_by_id(event.id) is None
    assert repo.get_event_logs(event.id) == []


def test_sqlite_clear_all_events(tmp_path: Path):
    db_file = tmp_path / "test_events_clear.db"
    repo = SQLiteEventsRepository(str(db_file))

    for i in range(3):
        ev = EventModel(
            id=f"evt-bulk-{i}",
            started_at=datetime.now(),
            metrics={"logs": [{"time": f"11:0{i}:00", "level": "INFO", "message": f"Log {i}"}]},
        )
        repo.save(ev)

    assert len(repo.list_recent(limit=10)) == 3

    # Limpiar todos los eventos
    deleted_count = repo.clear_all()
    assert deleted_count == 3
    assert len(repo.list_recent(limit=10)) == 0


def test_api_delete_events(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes import events as events_route

    temp_repo = SQLiteEventsRepository(str(tmp_path / "api_test.db"))
    monkeypatch.setattr(events_route, "repo", temp_repo)

    ev = EventModel(
        id="api-event-del-1",
        started_at=datetime.now(),
        metrics={"logs": [{"time": "12:00:00", "level": "INFO", "message": "Test API"}]},
    )
    temp_repo.save(ev)

    client = TestClient(app)

    # 1. Eliminar evento individual existente
    res = client.delete("/api/events/api-event-del-1")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Intentar eliminar inexistente
    res_404 = client.delete("/api/events/non-existent-id")
    assert res_404.status_code == 404

    # 3. Limpiar todos los eventos
    temp_repo.save(EventModel(id="api-ev-2", started_at=datetime.now()))
    res_clear = client.delete("/api/events")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "ok"
    assert res_clear.json()["deleted_count"] == 1

