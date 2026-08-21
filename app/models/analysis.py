"""
Módulo de Esquema Estructurado de IA (AI Analysis Result Schema)
================================================================

Responsabilidad:
----------------
Definir el contrato estricto de respuesta JSON que la IA Multimodal (OpenAI Vision)
debe generar al analizar una secuencia cronológica de imágenes.

Campos principales:
-------------------
- `person_detected` (bool): Indica si aparece alguna persona en las imágenes.
- `suspected_disposal` (bool): Indica si existe una acción compatible con arrojar o abandonar residuos.
- `action_completed` (bool): `True` sólo si las imágenes muestran evidencia suficiente de que el objeto fue efectivamente abandonado o arrojado.
- `confidence` (float 0.0 - 1.0): Nivel de certidumbre global del modelo.
- `event_type` (str): NO_EVENT, PERSON_PRESENT, SUSPICIOUS_ACTION, WASTE_DISPOSAL, UNCERTAIN.
- `description` (str): Descripción fáctica de los cambios observados en la secuencia.
- `warning_message` (str | None): Mensaje preventivo corto que el TTS leerá ÚNICAMENTE si DecisionEngine decide WARN.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class AIAnalysisResult(BaseModel):
    """
    Esquema Pydantic que mapea la respuesta estructurada de la IA Multimodal (GPT-5.6 Luna).
    Diseñado para garantizar tipado estricto y evitar respuestas no deterministas.
    """
    person_detected: bool = Field(
        ...,
        description="True si se identifica visualmente la presencia de al menos una persona en los fotogramas."
    )
    suspected_disposal: bool = Field(
        ...,
        description="True si se observa una acción compatible con portar, manipular o arrojar un objeto/residuo."
    )
    action_completed: bool = Field(
        ...,
        description=(
            "True ÚNICAMENTE cuando la secuencia de imágenes demuestra de forma concluyente "
            "que el objeto/residuo fue efectivamente soltado, lanzado o abandonado en la ribera."
        )
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza global sobre la clasificación (de 0.00 a 1.00)."
    )
    event_type: Literal["NO_EVENT", "PERSON_PRESENT", "SUSPICIOUS_ACTION", "WASTE_DISPOSAL", "UNCERTAIN"] = Field(
        default="NO_EVENT",
        description=(
            "Categorización estricta del evento:\n"
            "- NO_EVENT: Escena sin actividad relevante ni personas.\n"
            "- PERSON_PRESENT: Persona transitando o presente sin interacción con residuos.\n"
            "- SUSPICIOUS_ACTION: Persona manipulando objetos pero sin confirmación de abandono.\n"
            "- WASTE_DISPOSAL: Arrojo o abandono efectivo y consumado de residuos sólidos.\n"
            "- UNCERTAIN: Oclusión, baja visibilidad o ambigüedad en la acción."
        )
    )
    description: Optional[str] = Field(
        default="",
        description="Explicación concisa y fáctica de los cambios observados cronológicamente."
    )
    warning_message: Optional[str] = Field(
        default=None,
        description=(
            "Mensaje de advertencia respetuoso y preventivo en español latino neutro "
            "para ser leído por el TTS si corresponde emitir alerta sonora."
        )
    )
