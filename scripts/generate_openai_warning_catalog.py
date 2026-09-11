"""Genera el catálogo WAV de advertencias de SIVARH mediante OpenAI TTS."""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.speech.openai_tts import OpenAISpeechService


WARNING_TEXTS = (
    "Por favor, recoge el residuo y deposítalo en un contenedor. Cuidemos el río Huallaga.",
    "El arrojo de residuos ha sido detectado. Recoge la bolsa y utiliza un contenedor, por favor.",
    "Ayúdanos a proteger el Huallaga. Recoge el residuo y deposítalo correctamente.",
    "Mantengamos limpia esta ribera. Por favor, retira el residuo que acabas de dejar.",
)


def _validate_wav(path: Path) -> None:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise RuntimeError(f"Formato WAV inesperado en {path.name}.")
        if audio.getnframes() <= 0:
            raise RuntimeError(f"OpenAI devolvió un WAV vacío en {path.name}.")
        duration = audio.getnframes() / audio.getframerate()
        if duration > 30:
            raise RuntimeError(f"Duración WAV inválida en {path.name}: {duration:.1f} s.")


def generate_catalog(
    output_dir: Path,
    *,
    overwrite: bool = False,
    model: str | None = None,
    voice: str | None = None,
    speed: float | None = None,
) -> list[Path]:
    if not settings.OPENAI_API_KEY.strip():
        raise RuntimeError("OPENAI_API_KEY no está configurada en .env.")

    output_dir = output_dir if output_dir.is_absolute() else ROOT_DIR / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    service = OpenAISpeechService(model=model, voice=voice, speed=speed)
    generated_paths: list[Path] = []

    for index, text in enumerate(WARNING_TEXTS, start=1):
        output = output_dir / f"openai_warning_{index:02d}.wav"
        if output.is_file() and not overwrite:
            _validate_wav(output)
            generated_paths.append(output)
            print(f"Conservado: {output.name}")
            continue

        result = service.generate_speech(text, str(output))
        if result is None:
            raise RuntimeError(f"OpenAI TTS no pudo generar {output.name}.")
        _validate_wav(output)
        generated_paths.append(output)
        print(f"Generado con OpenAI TTS: {output.name}")

    return generated_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.OPENAI_WARNING_CATALOG_DIR,
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--speed", type=float, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    paths = generate_catalog(
        args.output_dir,
        overwrite=args.overwrite,
        model=args.model,
        voice=args.voice,
        speed=args.speed,
    )
    print(
        f"Catálogo listo: {len(paths)} archivos · modelo={args.model or settings.OPENAI_TTS_MODEL} "
        f"· voz={args.voice or settings.OPENAI_TTS_VOICE}"
    )


if __name__ == "__main__":
    main()
