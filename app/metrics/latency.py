import time

class LatencyTimer:
    """
    Utilidad para medir latencias de ejecución en milisegundos (ms).
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
        if self._start_time is None or self._end_time is None:
            return 0.0
        return (self._end_time - self._start_time) * 1000.0
