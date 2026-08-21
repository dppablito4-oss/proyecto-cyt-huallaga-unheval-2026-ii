"""
Módulo de Hiperparámetros de Modelos de IA (Model Configuration)
================================================================

Responsabilidad:
----------------
Centralizar los hiperparámetros de muestreo (temperatura, top_p, max_tokens)
utilizados en las inferencias del modelo de visión multimodal.
"""

from typing import Dict, Any

# Configuración estándar para inferencias deterministas y reproducibles
DEFAULT_VISION_CONFIG: Dict[str, Any] = {
    "temperature": 0.2,  # Temperatura baja para respuestas consistentes y apegadas a las instrucciones
    "max_tokens": 500,    # Límite suficiente para la estructura JSON de AIAnalysisResult
    "top_p": 1.0
}
