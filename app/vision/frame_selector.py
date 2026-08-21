from typing import List, Tuple, Any
from datetime import datetime

class FrameSelector:
    """
    Selecciona una secuencia reducida de fotogramas (ej. 3, 5 u 8) a partir de una lista
    amplia acumulada durante un evento, aplicando muestreo temporal uniforme o estrategias avanzadas.
    """

    def __init__(self, target_frames: int = 5, strategy: str = "uniform"):
        self.target_frames = target_frames
        self.strategy = strategy

    def select_frames(self, frames_with_time: List[Tuple[datetime, Any]]) -> List[Tuple[datetime, Any]]:
        total = len(frames_with_time)
        if total == 0:
            return []
        if total <= self.target_frames:
            return frames_with_time

        if self.strategy == "uniform":
            # Muestreo uniforme desde el primer hasta el último fotograma
            step = (total - 1) / (self.target_frames - 1)
            selected_indices = [int(round(i * step)) for i in range(self.target_frames)]
            # Eliminar duplicados preservando orden
            indices = list(dict.fromkeys(selected_indices))
            return [frames_with_time[idx] for idx in indices]

        # Estrategia por defecto fallback
        return frames_with_time[:self.target_frames]
