"""Descarga reproducible del modelo liviano oficial de MediaPipe Pose."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlopen


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
DEFAULT_DESTINATION = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "models"
    / "pose_landmarker_lite.task"
)


def download(destination: Path, overwrite: bool = False) -> Path:
    destination = destination.resolve()
    if destination.exists() and not overwrite:
        print(f"El modelo ya existe: {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        with urlopen(MODEL_URL, timeout=60) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Modelo descargado: {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    download(args.destination, args.overwrite)


if __name__ == "__main__":
    main()
