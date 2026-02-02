"""MetricRegistry: singleton registry for metric definitions.

Follows the ProjectTypeRegistry pattern (ADR-0093):
- Module-level singleton via __new__
- Lazy initialization of definitions on first access
- Explicit reset() for test isolation
"""

from __future__ import annotations

from typing import ClassVar

from autom8_asana.metrics.metric import Metric


class MetricRegistry:
    """Singleton registry for metric definitions.

    Follows the ProjectTypeRegistry pattern (ADR-0093):
    - Module-level singleton via __new__
    - Lazy initialization of definitions on first access
    - Explicit reset() for test isolation

    The registry does NOT auto-discover metrics at import time. Instead,
    _ensure_initialized() imports definitions/offer.py (and future
    definition modules) on first get_metric() or list_metrics() call.

    Attributes:
        _instance: Class-level singleton reference.
        _metrics: Internal name-to-Metric mapping.
        _initialized: Whether definitions have been loaded.

    Example:
        >>> registry = MetricRegistry()
        >>> metric = registry.get_metric("active_mrr")
        >>> print(metric.description)
        'Total MRR for ACTIVE offers, deduped by phone+vertical'

    Testing:
        >>> MetricRegistry.reset()  # Clears singleton for test isolation
    """

    _instance: ClassVar[MetricRegistry | None] = None

    _metrics: dict[str, Metric]
    _initialized: bool

    def __new__(cls) -> MetricRegistry:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._metrics = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def register(self, metric: Metric) -> None:
        """Register a metric definition.

        Args:
            metric: The Metric to register.

        Raises:
            ValueError: If a metric with the same name is already registered
                with a different definition.
        """
        if metric.name in self._metrics:
            existing = self._metrics[metric.name]
            if existing is not metric:
                raise ValueError(
                    f"Metric '{metric.name}' already registered. "
                    f"Existing: {existing.description}"
                )
            return  # Idempotent

        self._metrics[metric.name] = metric

    def get_metric(self, name: str) -> Metric:
        """Look up a metric by name.

        Triggers lazy initialization on first call.

        Args:
            name: Registry key (e.g., "active_mrr").

        Returns:
            The registered Metric.

        Raises:
            KeyError: If no metric is registered with this name.
        """
        self._ensure_initialized()

        if name not in self._metrics:
            available = ", ".join(sorted(self._metrics.keys()))
            raise KeyError(
                f"Unknown metric '{name}'. Available: {available}"
            )

        return self._metrics[name]

    def list_metrics(self) -> list[str]:
        """List all registered metric names.

        Triggers lazy initialization on first call.

        Returns:
            Sorted list of registered metric names.
        """
        self._ensure_initialized()
        return sorted(self._metrics.keys())

    def _ensure_initialized(self) -> None:
        """Lazy-load definition modules if not already loaded.

        Imports autom8_asana.metrics.definitions which triggers
        auto-registration of all metrics defined in submodules.

        If the definitions package was previously imported (e.g., after a
        reset() in tests), we reload it so module-level registration code
        re-executes against the fresh singleton instance.
        """
        if self._initialized:
            return

        import importlib
        import sys

        pkg_name = "autom8_asana.metrics.definitions"
        if pkg_name in sys.modules:
            # Reload submodules first, then the package, so module-level
            # registration code re-executes against this new instance.
            for mod_name in sorted(sys.modules):
                if mod_name.startswith(pkg_name + "."):
                    importlib.reload(sys.modules[mod_name])
            importlib.reload(sys.modules[pkg_name])
        else:
            import autom8_asana.metrics.definitions  # noqa: F401

        self._initialized = True

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for test isolation.

        Per ADR-0093 pattern: explicit reset clears singleton so
        next access creates a fresh instance.
        """
        cls._instance = None
