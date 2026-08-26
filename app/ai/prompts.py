"""
Módulo de Carga de Prompts del Sistema (Prompts Loader)
======================================================

Responsabilidad:
----------------
Cargar dinámicamente las directivas de comportamiento y el prompt del sistema
desde el archivo de texto externo `prompts/environmental_event.txt`.
Evita hardcodear textos extensos o instrucciones dentro del código fuente.

Flujo de invocación:
--------------------
- Llamado por `app.ai.vision_client.VisionAI.analyze_sequence()` para inyectar
  el rol de sistema en las llamadas a la API de OpenAI.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_system_prompt(prompt_path: Optional[Path] = None) -> str:
    """
    Lee el archivo de texto del prompt del sistema para visión multimodal.

    Args:
        prompt_path (Path, opcional): Ruta personalizada al archivo de prompt.

    Returns:
        str: Contenido textual del prompt o un fallback de seguridad si no se encuentra.
    """
    if prompt_path is None:
        prompt_path = Path(__file__).resolve().parent.parent.parent / "prompts" / "environmental_event.txt"

    try:
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Error al leer prompt desde {prompt_path}: {e}")

    # Mensaje de fallback básico
    return (
        "Eres SIVARH, un sistema inteligente de vigilancia ambiental para las riberas del río Huallaga, sector Puente Huallaga – UNHEVAL. "
        "Analiza la secuencia cronológica de fotogramas e identifica posibles conductas de arrojo de residuos."
    )
