"""
Módulo de Cliente de Visión Multimodal (VisionAI)
=================================================

Responsabilidad:
----------------
Encapsular la comunicación con la API de Visión Multimodal de OpenAI (por defecto `gpt-4o`).
Recibe la lista de imágenes seleccionadas en formato Base64 Data URL, aplica el prompt
del sistema especializado y obtiene una respuesta validada bajo el esquema Pydantic `AIAnalysisResult`.

Flujo de invocación:
--------------------
- Recibe la secuencia procesada por `app.vision.image_processor.ImageProcessor.to_base64_data_url()`.
- Si `settings.OPENAI_API_KEY` está ausente, opera en **modo simulación (mock)** retornando un
  resultado estructurado seguro para permitir el desarrollo y pruebas locales sin costo de tokens.
- Si hay API Key válida, realiza la llamada mediante `client.beta.chat.completions.parse()`.
- Entrega el resultado a `app.events.rules.DecisionEngine`.
"""

import logging
from typing import List, Optional
from app.config import settings
from app.models.analysis import AIAnalysisResult
from app.ai.prompts import load_system_prompt

logger = logging.getLogger(__name__)


class VisionAI:
    """
    Cliente de inferencia multimodal para análisis de secuencias de video.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Args:
            api_key (str, opcional): Clave secreta de la API de OpenAI. Si es None, lee de `settings`.
            model (str, opcional): Nombre del modelo de visión (ej. 'gpt-4o').
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_VISION_MODEL
        self.client = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Instancia el cliente oficial de OpenAI. Si no se configuró una API Key,
        advierte en el log y deja el cliente en modo simulación (mock).
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY no configurada. VisionAI operará en modo placeholder/mock.")
            return False
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            self._initialized = True
            logger.info("Cliente OpenAI Vision inicializado correctamente.")
            return True
        except Exception as e:
            logger.error(f"Error al inicializar el cliente OpenAI: {e}")
            return False

    def analyze_sequence(self, image_data_urls: List[str]) -> AIAnalysisResult:
        """
        Envía la secuencia de imágenes a OpenAI Vision y analiza los cambios temporales.

        Args:
            image_data_urls (List[str]): Lista de strings Data URL Base64 de las imágenes.

        Returns:
            AIAnalysisResult: Objeto Pydantic con la detección, confianza, descripción y recomendación.
        """
        # Modo simulación seguro para arranques sin API Key (Fase 0)
        if not self._initialized or not self.client:
            logger.info("Retornando resultado simulado (mock) de VisionAI por falta de API Key.")
            return AIAnalysisResult(
                event_detected=False,
                confidence=0.0,
                event_type="none",
                object=None,
                description="Simulación Fase 0: El sistema está ejecutándose en modo seguro sin llamadas a API.",
                recommended_action="ignore",
                warning_message=None
            )

        # Cargar el prompt especializado desde prompts/environmental_event.txt
        system_prompt = load_system_prompt()

        # Construir el payload de mensajes con las imágenes
        image_detail = settings.IMAGE_DETAIL  # 'medium' por defecto para GPT-5.6 Luna
        content = [{"type": "text", "text": "Analiza la siguiente secuencia cronológica de fotogramas:"}]
        for idx, url in enumerate(image_data_urls):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": image_detail
                }
            })

        try:
            # Uso de respuestas estructuradas nativas de OpenAI con validación Pydantic
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
            logger.error(f"Error en la llamada a OpenAI Vision API: {e}")
            return AIAnalysisResult(
                event_detected=False,
                confidence=0.0,
                event_type="none",
                object=None,
                description=f"Error durante el análisis de visión: {e}",
                recommended_action="ignore",
                warning_message=None
            )
