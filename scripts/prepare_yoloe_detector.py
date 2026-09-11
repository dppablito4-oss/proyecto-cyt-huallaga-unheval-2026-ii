"""Precalcula los prompts del detector abierto SIVARH para uso offline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera el archivo pequeño de embeddings para YOLOE."
    )
    parser.add_argument("--model", default=settings.YOLO_MODEL)
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.YOLO_PROMPT_EMBEDDINGS_PATH,
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT_DIR / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLOE

    model = YOLOE(args.model)
    model.set_classes(list(settings.DETECTION_CLASSES))
    saved = model.save_prompt_embeddings(output)
    print(f"Prompts YOLOE preparados: {saved}")
    print("Clases:", ", ".join(settings.DETECTION_CLASSES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
