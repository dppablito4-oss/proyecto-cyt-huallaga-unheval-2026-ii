"""
Módulo de Captura de Video USB (UsbCamera)
==========================================

Responsabilidad:
----------------
Implementar la interfaz `CameraSource` para cámaras conectadas localmente por USB
utilizando la biblioteca OpenCV (`cv2.VideoCapture`).

Flujo de invocación:
--------------------
- Instanciado por el worker de captura utilizando el índice `settings.CAMERA_SOURCE` (ej. 0 para cámara principal).
- Abre el dispositivo con `open()`, captura fotogramas secuenciales con `read()` y los provee
  en formato NumPy `ndarray` al pipeline de detección y buffer.
"""

import cv2
from typing import Tuple, Optional, Any, Dict
from app.camera.base import CameraSource


class UsbCamera(CameraSource):
    """
    Controlador de captura para cámaras web USB mediante OpenCV.
    Gestiona la configuración de resolución y tasa de fotogramas objetivo.
    """

    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720, fps: int = 30):
        """
        Inicializa los parámetros de la cámara USB.

        Args:
            camera_index (int): Índice numérico del dispositivo (0 para cámara por defecto).
            width (int): Ancho horizontal deseado en píxeles.
            height (int): Alto vertical deseado en píxeles.
            fps (int): Cuadros por segundo deseados.
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = fps
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """
        Abre el dispositivo USB con OpenCV. En Windows intenta usar el backend DirectShow (CAP_DSHOW)
        para acelerar la inicialización y evitar retrasos en el arranque.
        """
        try:
            # En Windows DirectShow suele ser más rápido y confiable para cámaras USB
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if cv2.os.name == 'nt' else cv2.CAP_ANY)
            
            # Fallback en caso de que DirectShow no esté disponible
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index)
            
            if self.cap.isOpened():
                # Solicitar configuración de resolución y FPS al driver de la cámara
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                return True
            return False
        except Exception:
            return False

    def read(self) -> Tuple[bool, Optional[Any]]:
        """
        Lee el siguiente cuadro desde el stream USB.
        Retorna (True, frame) si la lectura fue exitosa, o (False, None) si falló o la cámara se desconectó.
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def close(self) -> None:
        """
        Libera el descriptor del dispositivo de video para permitir que otros procesos lo utilicen.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        """Verifica si el objeto VideoCapture sigue abierto y funcional."""
        return self.cap is not None and self.cap.isOpened()

    def get_metadata(self) -> Dict[str, Any]:
        """
        Consulta y devuelve las propiedades reales negociadas con el hardware de la cámara.
        """
        actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) if self.is_opened() else self.width
        actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) if self.is_opened() else self.height
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS) if self.is_opened() else self.target_fps
        return {
            "type": "usb",
            "camera_index": self.camera_index,
            "width": int(actual_w),
            "height": int(actual_h),
            "fps": float(actual_fps),
            "is_opened": self.is_opened()
        }
