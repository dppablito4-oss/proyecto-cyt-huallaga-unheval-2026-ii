from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.routes import cameras
from app.config import settings


def test_automatic_analysis_preview_is_served(tmp_path, monkeypatch):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    image = frames_dir / "auto-preview-event-1.jpg"
    image.write_bytes(b"\xff\xd8\xff\xd9")
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    response = cameras.analysis_preview(image.name)

    assert Path(response.path) == image
    assert response.media_type == "image/jpeg"


def test_analysis_preview_rejects_unknown_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    with pytest.raises(HTTPException) as error:
        cameras.analysis_preview("other-preview.jpg")

    assert error.value.status_code == 404
