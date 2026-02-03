"""Metrics layer for declarative metric computation.

Public API:
    MetricExpr   - Column aggregation expression
    Metric       - Named, scoped metric definition
    Scope        - Data scope (entity type, section, dedup)
    MetricRegistry - Singleton registry of metric definitions
    compute_metric - Execute a metric against a DataFrame
"""

from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry
from autom8_asana.metrics.resolve import SectionIndex, resolve_metric_scope

__all__ = [
    "MetricExpr",
    "Metric",
    "Scope",
    "MetricRegistry",
    "compute_metric",
    "SectionIndex",
    "resolve_metric_scope",
]
