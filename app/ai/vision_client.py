"""
Módulo de Cliente de Visión Multimodal (VisionAIClient)
======================================================

Responsabilidad:
----------------
Encapsular la serialización de transporte (conversión a Base64 Data URL), construcción del
payload y comunicación con la API de Visión Multimodal de OpenAI (por defecto `gpt-5.6-luna`).
Recibe los fotogramas binarios (JPEG bytes) procesados por `ImageProcessor` y obtiene una
respuesta validada bajo el esquema Pydantic `AIAnalysisResult`.

Flujo de invocación:
--------------------
- Recibe la lista de bytes JPEG comprimidos entregados por `ImageProcessor.compress_jpeg()`.
- Convierte cada imagen a Base64 Data URL internamente (`data:image/jpeg;base64,...`).
- Inyecta el prompt del sistema especializado (`prompts/environmental_event.txt`).
- Ejecuta la inferencia estructurada con `client.beta.chat.completions.parse()`.
- Entrega el `AIAnalysisResult` al `DecisionEngine`.
"""

import base64
import logging
from typing import List, Optional, Union
from app.config import settings
from app.models.analysis import AIAnalysisResult
from app.ai.prompts import load_system_prompt

logger = logging.getLogger(__name__)


class VisionAIClient:
    """
    Cliente de transporte e inferencia multimodal para análisis de secuencias de video.
    Maneja la serialización Base64 y la comunicación con OpenAI.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Args:
            api_key (str, opcional): Clave secreta de la API de OpenAI. Si es None, lee de `settings`.
            model (str, opcional): Nombre del modelo de visión (ej. 'gpt-5.6-luna').
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
            logger.warning("OPENAI_API_KEY no configurada. VisionAIClient operará en modo placeholder/mock.")
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

    @staticmethod
    def _bytes_to_data_url(image_bytes: bytes) -> str:
        """Convierte bytes JPEG binarios en string Base64 Data URL."""
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"

    def analyze_sequence(self, images: List[Union[bytes, str]]) -> AIAnalysisResult:
        """
        Serializa las imágenes y envía la secuencia a OpenAI Vision para análisis temporal.

        Args:
            images (List[bytes | str]): Lista de bytes JPEG o strings Data URL Base64.

        Returns:
            AIAnalysisResult: Objeto Pydantic con la clasificación estructurada.
        """
        # Modo simulación seguro para arranques sin API Key (Fase 0)
        if not self._initialized or not self.client:
            logger.info("Retornando resultado simulado (mock) de VisionAIClient por falta de API Key.")
            return AIAnalysisResult(
                person_detected=False,
                suspected_disposal=False,
                action_completed=False,
                confidence=0.0,
                event_type="NO_EVENT",
                description="Simulación: Sistema ejecutándose en modo seguro sin llamadas a API.",
                warning_message=None
            )

        # Cargar el prompt especializado desde prompts/environmental_event.txt
        system_prompt = load_system_prompt()

        # Construir el payload de mensajes convirtiendo a Base64 Data URL si vienen en bytes
        image_detail = settings.IMAGE_DETAIL  # 'low', 'auto' o 'high'
        content = [{"type": "text", "text": "Analiza la siguiente secuencia cronológica de fotogramas:"}]

        for item in images:
            if isinstance(item, bytes):
                url = self._bytes_to_data_url(item)
            else:
                url = str(item)

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": image_detail
                }
            })

        try:
            # Respuestas estructuradas nativas de OpenAI con validación Pydantic
            # (No enviamos temperature fija para compatibilidad con modelos como gpt-5.6-luna que solo aceptan default)
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                reasoning_effort=settings.OPENAI_VISION_REASONING_EFFORT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                response_format=AIAnalysisResult
            )
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Error en la llamada a OpenAI Vision API: {e}")
            return AIAnalysisResult(
                person_detected=False,
                suspected_disposal=False,
                action_completed=False,
                confidence=0.0,
                event_type="UNCERTAIN",
                description=f"Error durante el análisis de visión: {e}",
                warning_message=None
            )


# Alias para mantener compatibilidad con el resto del proyecto
VisionAI = VisionAIClient
