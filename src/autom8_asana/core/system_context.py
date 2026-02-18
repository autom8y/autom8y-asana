"""Centralized singleton lifecycle management.

Per QW-5 (ARCH-REVIEW-1 Section 3.1): Multiple singletons are reset
independently in test fixtures, creating fragile test isolation. This
module provides a single reset_all() entry point.

Singletons managed:
- ProjectTypeRegistry (models/business/registry.py)
- WorkspaceProjectRegistry (models/business/registry.py)
- SchemaRegistry (dataframes/models/registry.py)
- EntityProjectRegistry (services/resolver.py)
- WatermarkRepository (dataframes/watermark.py)
- MetricRegistry (metrics/registry.py)
- Settings (settings.py)
- Bootstrap flag (models/business/_bootstrap.py)

Usage:
    from autom8_asana.core.system_context import SystemContext

    # In test fixtures:
    SystemContext.reset_all()
"""

from __future__ import annotations

from autom8y_log import get_logger

logger = get_logger(__name__)


class SystemContext:
    """Centralized access to all singleton reset operations.

    All methods use deferred imports to avoid circular dependency
    issues at module load time.
    """

    @staticmethod
    def reset_all() -> None:
        """Reset all singletons to pristine state.

        Intended for test fixtures. Resets are ordered to respect
        dependencies: registries first, then caches, then settings.
        """
        # 1. Core registries
        from autom8_asana.models.business.registry import (
            ProjectTypeRegistry,
            WorkspaceProjectRegistry,
        )

        ProjectTypeRegistry.reset()
        WorkspaceProjectRegistry.reset()

        # 2. DataFrame/schema registries
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        SchemaRegistry.reset()

        # 3. Service-layer registries
        from autom8_asana.services.resolver import EntityProjectRegistry

        EntityProjectRegistry.reset()
        # Note: EntityProjectRegistry.reset() already calls
        # _clear_resolvable_cache(), so no separate call needed.

        # 4. Watermark repository
        from autom8_asana.dataframes.watermark import WatermarkRepository

        WatermarkRepository.reset()

        # 5. Metrics registry
        from autom8_asana.metrics.registry import MetricRegistry

        MetricRegistry.reset()

        # 6. Settings singleton
        from autom8_asana.settings import reset_settings

        reset_settings()

        # 7. Bootstrap flag
        from autom8_asana.models.business._bootstrap import reset_bootstrap

        reset_bootstrap()

        logger.debug("system_context_reset_all_complete")
