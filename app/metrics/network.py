class NetworkMetrics:
    """
    Calculadora de métricas de red y tamaño de payloads transmitidos.
    """

    @staticmethod
    def calculate_payload_bytes(data_urls: list[str]) -> int:
        total = 0
        for url in data_urls:
            # Estimación del tamaño en bytes a partir del string base64
            if "," in url:
                b64_part = url.split(",", 1)[1]
                total += len(b64_part) * 3 // 4
        return total
