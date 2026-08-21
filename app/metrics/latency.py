"""
Módulo de Medición de Tiempos y Latencia (LatencyTimer)
======================================================

Responsabilidad:
----------------
Proveer un gestor de contexto de alta precisión para cuantificar tiempos de ejecución
en milisegundos ($ms$) mediante `time.perf_counter()`.

Flujo de invocación:
--------------------
- Utilizado para cronometrar:
  * El tiempo de inferencia local de YOLO.
  * La latencia de la llamada de red a OpenAI Vision (`ai_latency_ms`).
  * La latencia de generación de audio TTS (`tts_latency_ms`).
  * El tiempo total transcurrido en el pipeline del evento (`total_latency_ms`).
"""

import time


class LatencyTimer:
    """
    Context manager de benchmarking y medición de tiempos.
    
    Ejemplo de uso:
    ---------------
    with LatencyTimer() as timer:
        # operación crítica
        ...
    duracion = timer.elapsed_ms()
    """

    def __init__(self):
        self._start_time = None
        self._end_time = None

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end_time = time.perf_counter()

    def elapsed_ms(self) -> float:
        """
        Retorna los milisegundos transcurridos entre la entrada y salida del bloque.
        """
        if self._start_time is None or self._end_time is None:
            return 0.0
        return (self._end_time - self._start_time) * 1000.0
