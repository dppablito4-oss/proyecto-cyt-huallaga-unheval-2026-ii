"""
Módulo de Esquema Estructurado de IA (AI Analysis Result Schema)
================================================================

Responsabilidad:
----------------
Definir el contrato estricto de respuesta JSON que la IA Multimodal (OpenAI Vision)
debe generar al analizar una secuencia cronológica de imágenes.

Flujo de invocación:
--------------------
- Se utiliza como formato de respuesta estructurada en `app.ai.vision_client.VisionAI.analyze_sequence()`
  mediante el método `beta.chat.completions.parse()`.
- El resultado obtenido es evaluado por `app.events.rules.DecisionEngine.evaluate_decision()` para decidir
  si corresponde emitir una advertencia auditiva con `app.speech.openai_tts.OpenAISpeechService`.
- Se almacena dentro de `EventModel.analysis` y se muestra en el frontend dashboard.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class AIAnalysisResult(BaseModel):
    """
    Esquema Pydantic que mapea la respuesta estructurada de la IA Multimodal.
    Diseñado para garantizar tipado estricto y evitar respuestas no deterministas o texto libre no procesable.
    """
    event_detected: bool = Field(
        ...,
        description="True si se observa una acción relevante de manipulación, arrojo o abandono de objetos en la ribera."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza o certidumbre del modelo sobre la acción clasificada (de 0.00 a 1.00)."
    )
    event_type: Literal["none", "carrying", "retrieving", "temporary_placement", "possible_littering"] = Field(
        default="none",
        description=(
            "Categorización de la conducta observada:\n"
            "- none: Tránsito o actividad normal sin interacción con residuos.\n"
            "- carrying: Portando pertenencias personales continuamente.\n"
            "- retrieving: Recogiendo objetos o limpiando la ribera.\n"
            "- temporary_placement: Apoyo temporal de objetos durante descanso o labor.\n"
            "- possible_littering: Arrojo, lanzamiento o abandono indebido de basura/residuos sólidos."
        )
    )
    object: Optional[str] = Field(
        default=None,
        description="Tipo de objeto identificado (ej. 'botella de plástico', 'bolsa negra', 'envoltorio')."
    )
    description: str = Field(
        ...,
        description="Explicación concisa y fáctica de los cambios observados a lo largo de la secuencia cronológica."
    )
    recommended_action: Literal["ignore", "log_only", "warn"] = Field(
        default="ignore",
        description="Recomendación preliminar de la IA: 'ignore' (descartar), 'log_only' (auditar), 'warn' (advertir)."
    )
    warning_message: Optional[str] = Field(
        default=None,
        description=(
            "Mensaje de advertencia respetuoso, directo y preventivo en español para ser sintetizado por TTS "
            "si se determina que ocurrió arrojo de basura con alta confianza."
        )
    )
