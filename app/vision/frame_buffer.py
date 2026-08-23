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
- La cámara ofrece cada cuadro a `.add_frame(frame)`, que conserva solo la frecuencia de muestreo configurada.
- Cuando `app.events.manager.EventManager` detecta un evento relevante, extrae el contexto previo
  con `.get_all_frames()` o `.get_last_n_frames()` y lo entrega a `app.vision.frame_selector.FrameSelector`.
- De esta manera, el análisis de IA puede observar lo que ocurrió *justo antes* de que la persona
  fuera detectada o realizara una acción sospechosa.
"""

from collections import deque
from typing import List, Tuple, Any, Optional
from datetime import datetime
import threading
import time


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
        self._sample_interval = 1.0 / max(1, fps)
        self._last_sample_time: Optional[float] = None
        self._lock = threading.Lock()

    def add_frame(self, frame: Any, timestamp: Optional[datetime] = None) -> bool:
        """
        Inserta un fotograma si ya transcurrió el intervalo de muestreo configurado.
        Si se sobrepasa `max_size`, el elemento más antiguo se descarta automáticamente en $O(1)$.

        Returns:
            bool: True si el frame se almacenó; False si se omitió por muestreo.
        """
        now = time.monotonic()
        with self._lock:
            if (
                self._last_sample_time is not None
                and now - self._last_sample_time < self._sample_interval
            ):
                return False

            if timestamp is None:
                timestamp = datetime.now()
            self.buffer.append((timestamp, frame))
            self._last_sample_time = now
            return True

    def get_all_frames(self) -> List[Tuple[datetime, Any]]:
        """
        Devuelve una lista ordenada cronológicamente de todos los fotogramas acumulados en el buffer.
        """
        with self._lock:
            return list(self.buffer)

    def get_last_n_frames(self, n: int) -> List[Tuple[datetime, Any]]:
        """
        Devuelve los últimos $n$ fotogramas más recientes del buffer.
        """
        with self._lock:
            frames = list(self.buffer)
        return frames[-n:] if len(frames) >= n else frames

    def clear(self) -> None:
        """Vacía todos los cuadros almacenados en el buffer."""
        with self._lock:
            self.buffer.clear()
            self._last_sample_time = None

    def __len__(self) -> int:
        """Retorna la cantidad actual de fotogramas en memoria."""
        with self._lock:
            return len(self.buffer)
