"""
Módulo de Buffer Circular Temporal en Memoria (FrameBuffer)
===========================================================

Responsabilidad:
----------------
Mantener en memoria RAM una ventana deslizante con los fotogramas de los últimos $N$ segundos de video
(por defecto `settings.BUFFER_SECONDS = 5`).
Evita la necesidad de escribir continuamente video al disco duro o saturar el almacenamiento local.

Flujo de invocación:
--------------------
- Cada cuadro capturado por `app.camera` se registra en el buffer mediante `.add_frame(frame)`.
- Cuando `app.events.manager.EventManager` detecta un evento relevante, extrae el contexto previo
  con `.get_all_frames()` o `.get_last_n_frames()` y lo entrega a `app.vision.frame_selector.FrameSelector`.
- De esta manera, el análisis de IA puede observar lo que ocurrió *justo antes* de que la persona
  fuera detectada o realizara una acción sospechosa.
"""

from collections import deque
from typing import List, Tuple, Any, Optional
from datetime import datetime


class FrameBuffer:
    """
    Buffer circular de tamaño acotado (`deque(maxlen=max_size)`).
    Almacena tuplas `(timestamp: datetime, frame: np.ndarray)`.
    """

    def __init__(self, buffer_seconds: int = 5, fps: int = 30):
        """
        Args:
            buffer_seconds (int): Segundos de historia reciente a conservar en RAM.
            fps (int): Tasa estimada o real de cuadros por segundo de la cámara.
        """
        self.buffer_seconds = buffer_seconds
        self.fps = fps
        self.max_size = max(1, buffer_seconds * fps)
        self.buffer: deque = deque(maxlen=self.max_size)

    def add_frame(self, frame: Any, timestamp: Optional[datetime] = None) -> None:
        """
        Inserta un nuevo fotograma en el extremo derecho del buffer.
        Si se sobrepasa `max_size`, el elemento más antiguo se descarta automáticamente en $O(1)$.
        """
        if timestamp is None:
            timestamp = datetime.now()
        self.buffer.append((timestamp, frame))

    def get_all_frames(self) -> List[Tuple[datetime, Any]]:
        """
        Devuelve una lista ordenada cronológicamente de todos los fotogramas acumulados en el buffer.
        """
        return list(self.buffer)

    def get_last_n_frames(self, n: int) -> List[Tuple[datetime, Any]]:
        """
        Devuelve los últimos $n$ fotogramas más recientes del buffer.
        """
        frames = list(self.buffer)
        return frames[-n:] if len(frames) >= n else frames

    def clear(self) -> None:
        """Vacía todos los cuadros almacenados en el buffer."""
        self.buffer.clear()

    def __len__(self) -> int:
        """Retorna la cantidad actual de fotogramas en memoria."""
        return len(self.buffer)
