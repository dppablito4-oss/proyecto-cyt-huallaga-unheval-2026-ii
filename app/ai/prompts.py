import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def load_system_prompt(prompt_path: Optional[Path] = None) -> str:
    """Carga el prompt del sistema desde un archivo de texto."""
    if prompt_path is None:
        prompt_path = Path(__file__).resolve().parent.parent.parent / "prompts" / "environmental_event.txt"

    try:
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Error al cargar prompt desde {prompt_path}: {e}")

    # Fallback básico por seguridad
    return "Eres un sistema de vigilancia ambiental. Analiza la secuencia de fotogramas e identifica posibles eventos de contaminación."
