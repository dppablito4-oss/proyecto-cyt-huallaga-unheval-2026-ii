"""Genera offline la plantilla WAV genérica de SIVARH."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_TEXT = (
    "Cuidemos juntos el Huallaga. Por favor, recoge el residuo y deposítalo "
    "en un contenedor."
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "audio"
    / "templates"
    / "warning_default.wav"
)


def _powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate(output: Path, text: str, overwrite: bool = False) -> Path:
    output = output.resolve()
    if output.exists() and not overwrite:
        print(f"La plantilla ya existe: {output}")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$spanish = $voice.GetInstalledVoices() | Where-Object { "
            "$_.VoiceInfo.Culture.Name -like 'es-*' } | Select-Object -First 1; "
            "if ($spanish) { $voice.SelectVoice($spanish.VoiceInfo.Name) }; "
            f"$voice.SetOutputToWaveFile({_powershell_literal(str(output))}); "
            f"$voice.Speak({_powershell_literal(text)}); "
            "$voice.Dispose()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True,
            timeout=60,
        )
    else:
        espeak = shutil.which("espeak")
        if espeak is None:
            raise RuntimeError("Se requiere Windows System.Speech o el comando espeak.")
        subprocess.run([espeak, "-v", "es", "-w", str(output), text], check=True, timeout=60)

    if not output.is_file() or output.stat().st_size < 44:
        raise RuntimeError("No se pudo generar una plantilla WAV válida.")
    print(f"Plantilla local generada: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generate(args.output, args.text, args.overwrite)


if __name__ == "__main__":
    main()
