from typing import Optional, Literal
from pydantic import BaseModel, Field

class AIAnalysisResult(BaseModel):
    event_detected: bool = Field(..., description="Determina si ocurrió una posible conducta de arrojo o abandono de residuos.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Nivel de confianza de la inferencia de visión (0.00 a 1.00).")
    event_type: Literal["none", "carrying", "retrieving", "temporary_placement", "possible_littering"] = Field(
        default="none",
        description="Categoría del evento observado."
    )
    object: Optional[str] = Field(default=None, description="Descripción del objeto o residuo involucrado.")
    description: str = Field(..., description="Explicación detallada y objetiva de los cambios observados entre fotogramas.")
    recommended_action: Literal["ignore", "log_only", "warn"] = Field(
        default="ignore",
        description="Acción recomendada por el modelo de IA."
    )
    warning_message: Optional[str] = Field(
        default=None,
        description="Mensaje de advertencia breve y educado en español si corresponde emitir voz."
    )
