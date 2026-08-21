import logging
from typing import List, Optional
from app.config import settings
from app.models.analysis import AIAnalysisResult
from app.ai.prompts import load_system_prompt

logger = logging.getLogger(__name__)

class VisionAI:
    """
    Cliente para interactuar con la API Multimodal de Visión (OpenAI GPT-4o / Vision).
    Recibe la secuencia de fotogramas procesados y retorna el modelo Pydantic AIAnalysisResult.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_VISION_MODEL
        self.client = None
        self._initialized = False

    def initialize(self) -> bool:
        if not self.api_key:
            logger.warning("OPENAI_API_KEY no configurada. VisionAI operará en modo placeholder/mock.")
            return False
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Error al inicializar el cliente OpenAI: {e}")
            return False

    def analyze_sequence(self, image_data_urls: List[str]) -> AIAnalysisResult:
        """
        Envía una secuencia de imágenes (data URLs Base64) al modelo multimodal.
        """
        if not self._initialized or not self.client:
            logger.info("Retornando resultado simulado (mock) de VisionAI por falta de API Key o cliente.")
            return AIAnalysisResult(
                event_detected=False,
                confidence=0.0,
                event_type="none",
                object=None,
                description="Simulación: El sistema está ejecutándose en modo Fase 0 (sin llamadas reales a API de IA).",
                recommended_action="ignore",
                warning_message=None
            )

        system_prompt = load_system_prompt()

        content = [{"type": "text", "text": "Analiza la siguiente secuencia cronológica de fotogramas:"}]
        for idx, url in enumerate(image_data_urls):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": "low"
                }
            })

        try:
            # Uso de respuestas estructuradas Pydantic con OpenAI Beta Parse
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                response_format=AIAnalysisResult,
                temperature=0.2
            )
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Error en la llamada a Vision AI: {e}")
            return AIAnalysisResult(
                event_detected=False,
                confidence=0.0,
                event_type="none",
                object=None,
                description=f"Error durante el análisis de visión: {e}",
                recommended_action="ignore",
                warning_message=None
            )
