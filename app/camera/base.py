"""
Módulo Base de Captura de Video (CameraSource Interface)
========================================================

Responsabilidad:
----------------
Definir el contrato polimórfico abstracto `CameraSource` para desacoplar completamente
la lógica de negocio y visión por computadora de los detalles técnicos del hardware de cámara.

Flujo de invocación:
--------------------
- Es la clase base implementada por:
  * `app.camera.usb_camera.UsbCamera` (Cámaras web USB)
  * `app.camera.rtsp_camera.RtspCamera` (Cámaras IP / Seguridad mediante RTSP)
  * `app.camera.video_file.VideoFileCamera` (Archivos de video grabados para investigación)
- El bucle de captura principal llama de forma continua a `.read()` y envía cada fotograma
  a `app.vision.detector.LocalDetector` y `app.vision.frame_buffer.FrameBuffer`.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any, Dict


class CameraSource(ABC):
    """
    Clase base abstracta que estandariza las operaciones de adquisición de video.
    Cualquier origen de cuadros (físico, stream o archivo) debe derivar de esta clase.
    """

    @abstractmethod
    def open(self) -> bool:
        """
        Abre o inicializa la conexión con el dispositivo de video o stream.
        
        Returns:
            bool: True si la fuente se abrió correctamente, False en caso contrario.
        """
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[Any]]:
        """
        Captura y recupera el siguiente fotograma del flujo de video.
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: 
                - Primer elemento (bool): Éxito de la lectura del cuadro.
                - Segundo elemento (ndarray | None): El fotograma en formato de matriz OpenCV (BGR) o None.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Libera el recurso de hardware, cierra la conexión del stream o el archivo de video.
        """
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """
        Indica si el recurso de captura se encuentra actualmente abierto y activo.
        
        Returns:
            bool: True si está disponible para lectura, False si está cerrado o desconectado.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Provee metadatos descriptivos sobre la fuente de video (tipo, resolución, FPS, etc.).
        
        Returns:
            Dict[str, Any]: Diccionario con parámetros técnicos del origen de video.
        """
        pass
