from typing import Dict, Any, List

class Tracker:
    """
    Placeholder para seguimiento de objetos/personas (Multi-object tracking).
    Permitirá mantener un ID consistente (person_id) a través de los fotogramas (ej. ByteTrack).
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # En la Fase 0 permanece desactivado
        return detections
