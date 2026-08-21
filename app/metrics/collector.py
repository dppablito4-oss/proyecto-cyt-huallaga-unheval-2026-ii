from datetime import datetime
from typing import List
from app.models.metrics import SystemMetrics

class MetricsCollector:
    """
    Colector central de métricas del sistema para fines de investigación académica.
    """

    def __init__(self):
        self.history: List[SystemMetrics] = []

    def record_event_metrics(self, metrics: SystemMetrics) -> None:
        self.history.append(metrics)

    def get_recent_metrics(self, limit: int = 50) -> List[SystemMetrics]:
        return self.history[-limit:]
