"""Persistencia pequeña para el vocabulario abierto de YOLOE."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence


def normalize_detection_classes(classes: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(
        dict.fromkeys(
            str(name).strip().casefold()
            for name in classes
            if str(name).strip()
        )
    )
    if "person" not in normalized:
        normalized = ("person", *normalized)
    if len(normalized) < 2:
        raise ValueError("Añade al menos una clase de residuo además de 'person'.")
    if len(normalized) > 40:
        raise ValueError("Se admiten como máximo 40 clases para mantener baja latencia.")
    if any(len(name) > 80 for name in normalized):
        raise ValueError("Cada clase debe tener 80 caracteres o menos.")
    return normalized


def load_detection_classes(path: Path, fallback: Sequence[str]) -> tuple[str, ...]:
    if not path.is_file():
        return normalize_detection_classes(fallback)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return normalize_detection_classes(payload.get("classes", ()))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return normalize_detection_classes(fallback)


def save_detection_classes(path: Path, classes: Sequence[str]) -> tuple[str, ...]:
    normalized = normalize_detection_classes(classes)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps({"classes": list(normalized)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)
    return normalized
