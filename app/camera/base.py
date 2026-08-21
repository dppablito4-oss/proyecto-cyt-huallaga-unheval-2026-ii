from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any, Dict

class CameraSource(ABC):
    """
    Interfaz abstracta para fuentes de captura de video.
    Permite abstraer cámaras USB, streams RTSP/IP y archivos de video grabados.
    """

    @abstractmethod
    def open(self) -> bool:
        """Inicializa la fuente de video."""
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[Any]]:
        """
        Lee el siguiente fotograma.
        Retorna (success: bool, frame: np.ndarray | None).
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Libera la fuente de video."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Verifica si la fuente está activa."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Obtiene información sobre la fuente (resolución, FPS, fuente, etc.)."""
        pass
