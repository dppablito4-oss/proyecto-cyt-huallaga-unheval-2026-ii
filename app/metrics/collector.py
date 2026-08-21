"""
Módulo de Recolección de Métricas Globales (MetricsCollector)
============================================================

Responsabilidad:
----------------
Acumular y estructurar las métricas de todos los eventos procesados para análisis estadístico,
generación de tablas comparativas y benchmarking en publicaciones académicas.

Flujo de invocación:
--------------------
- Recibe instancias de `app.models.metrics.SystemMetrics` producidas por los eventos.
- Permite consultar el historial reciente para exportación o visualización en el dashboard.
"""

from typing import List
from datetime import datetime
from app.models.metrics import SystemMetrics


class MetricsCollector:
    """
    Colector y agregador de métricas operativas del sistema.
    """

    def __init__(self):
        self.history: List[SystemMetrics] = []

    def record_event_metrics(self, metrics: SystemMetrics) -> None:
        """
        Almacena un registro de métricas de un evento.
        """
        self.history.append(metrics)

    def get_recent_metrics(self, limit: int = 50) -> List[SystemMetrics]:
        """
        Retorna las últimas $limit$ métricas capturadas.
        """
        return self.history[-limit:]
