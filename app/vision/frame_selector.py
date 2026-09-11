"""
Módulo de Selección de Fotogramas Clave (FrameSelector)
======================================================

Responsabilidad:
----------------
Reducir una ráfaga amplia de fotogramas acumulados durante un evento (ej. 30 a 150 frames)
a una secuencia representativa compacta (ej. 3, 5 u 8 fotogramas clave).
Es uno de los módulos centrales para la optimización de latencia, costos y precisión en la investigación.

Flujo de invocación:
--------------------
- Recibe los fotogramas temporales entregados por `app.vision.frame_buffer.FrameBuffer`.
- Aplica la estrategia configurada (`uniform`, `motion_based`, `confidence_based`).
- Pasa los fotogramas seleccionados a `app.vision.image_processor.ImageProcessor` para su preparación final.
"""

from typing import List, Tuple, Any
from datetime import datetime, timedelta


class FrameSelector:
    """
    Algoritmo de selección temporal de fotogramas.
    En su versión base implementa muestreo uniforme equidistante en el tiempo.
    """

    def __init__(self, target_frames: int = 5, strategy: str = "uniform"):
        """
        Args:
            target_frames (int): Número deseado de imágenes a enviar a la IA (por defecto 5).
            strategy (str): Nombre de la estrategia ('uniform', 'adaptive').
        """
        self.target_frames = target_frames
        self.strategy = strategy

    def select_frames(self, frames_with_time: List[Tuple[datetime, Any]]) -> List[Tuple[datetime, Any]]:
        """
        Toma una secuencia amplia de fotogramas y selecciona los más representativos.

        Args:
            frames_with_time: Lista de tuplas `(timestamp, frame_ndarray)`.

        Returns:
            List[Tuple[datetime, Any]]: Subconjunto de longitud <= `target_frames`.
        """
        total = len(frames_with_time)
        if total == 0:
            return []
        if total <= self.target_frames:
            return frames_with_time

        if self.strategy == "uniform":
            # Calcular índices equidistantes desde el primer cuadro (t=0) hasta el último (t=fin)
            step = (total - 1) / (self.target_frames - 1)
            selected_indices = [int(round(i * step)) for i in range(self.target_frames)]
            
            # Garantizar índices únicos conservando el orden cronológico
            indices = list(dict.fromkeys(selected_indices))
            return [frames_with_time[idx] for idx in indices]

        # Estrategia de respaldo (tomar los primeros N)
        return frames_with_time[:self.target_frames]


class EventKeyframeSelector:
    """Selecciona evidencia antes, durante y después de una liberación."""

    def __init__(
        self,
        max_frames: int = 3,
        before_seconds: float = 1.0,
        after_seconds: float = 1.0,
    ):
        if not 2 <= max_frames <= 4:
            raise ValueError("max_frames debe estar entre 2 y 4.")
        if before_seconds < 0 or after_seconds < 0:
            raise ValueError("Los intervalos de keyframes no pueden ser negativos.")
        self.max_frames = max_frames
        self.before_seconds = float(before_seconds)
        self.after_seconds = float(after_seconds)
        self._uniform_fallback = FrameSelector(target_frames=max_frames, strategy="uniform")

    def select_event_frames(
        self,
        frames_with_time: List[Tuple[datetime, Any]],
        release_timestamp: datetime | None,
        stationary_timestamp: datetime | None = None,
    ) -> List[Tuple[datetime, Any]]:
        if not frames_with_time:
            return []
        if release_timestamp is None:
            return self._uniform_fallback.select_frames(frames_with_time)

        targets = [
            release_timestamp,
            release_timestamp - timedelta(seconds=self.before_seconds),
            release_timestamp + timedelta(seconds=self.after_seconds),
        ]
        if stationary_timestamp is not None:
            targets.append(stationary_timestamp)

        selected_indexes: list[int] = []
        for target in targets:
            nearest_index = min(
                range(len(frames_with_time)),
                key=lambda index: abs(
                    (frames_with_time[index][0] - target).total_seconds()
                ),
            )
            if nearest_index not in selected_indexes:
                selected_indexes.append(nearest_index)
            if len(selected_indexes) == self.max_frames:
                break

        if len(selected_indexes) < self.max_frames:
            for item in self._uniform_fallback.select_frames(frames_with_time):
                index = next(
                    idx
                    for idx, candidate in enumerate(frames_with_time)
                    if candidate[0] == item[0]
                )
                if index not in selected_indexes:
                    selected_indexes.append(index)
                if len(selected_indexes) == self.max_frames:
                    break
        return [frames_with_time[index] for index in sorted(selected_indexes)]
