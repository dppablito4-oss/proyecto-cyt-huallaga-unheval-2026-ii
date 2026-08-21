"""
Módulo de Métricas de Red y Payload (NetworkMetrics)
===================================================

Responsabilidad:
----------------
Calcular el peso en bytes de los datos y cargas útiles transmitidas hacia las APIs externas
(OpenAI Vision).

Flujo de invocación:
--------------------
- Invocado tras la compresión de imágenes para registrar cuántos bytes fueron enviados
  en la petición HTTP. Esta métrica es fundamental para evaluar costos de transmisión en redes celulares 4G/LTE.
"""

from typing import List


class NetworkMetrics:
    """
    Herramientas de cálculo de tráfico de red y consumo de ancho de banda.
    """

    @staticmethod
    def calculate_payload_bytes(data_urls: List[str]) -> int:
        """
        Calcula el tamaño aproximado en bytes a partir de una lista de Data URLs Base64.

        Args:
            data_urls (List[str]): Cadenas 'data:image/jpeg;base64,...'.

        Returns:
            int: Cantidad total de bytes decodificados transferidos.
        """
        total = 0
        for url in data_urls:
            if "," in url:
                b64_part = url.split(",", 1)[1]
                # En Base64 cada 4 caracteres representan aproximadamente 3 bytes
                total += len(b64_part) * 3 // 4
        return total
