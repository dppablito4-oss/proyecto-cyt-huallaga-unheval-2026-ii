"""
Módulo de Seguimiento de Objetos (Tracker Interface)
===================================================

Responsabilidad:
----------------
Proporcionar una interfaz base para algoritmos de seguimiento de múltiples objetos (MOT)
como ByteTrack o BoT-SORT integrables con Ultralytics YOLO.

Flujo de invocación:
--------------------
- En fases avanzadas permitirá asociar un identificador persistente (`track_id` / `person_id`)
  a una persona a lo largo de múltiples fotogramas para analizar su trayectoria y permanencia.
- En la Fase 0 permanece como interfaz para no añadir complejidad computacional innecesaria.
"""

from typing import Dict, Any, List


class Tracker:
    """
    Controlador de seguimiento de trayectorias.
    """

    def __init__(self, enabled: bool = False):
        """
        Args:
            enabled (bool): Activa o desactiva la ejecución del tracker.
        """
        self.enabled = enabled

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Actualiza el estado de las pistas con las detecciones del cuadro actual.
        """
        if not self.enabled:
            return detections
        # Placeholder para integración de algoritmos de seguimiento
        return detections
