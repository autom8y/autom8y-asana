"""Centralized singleton lifecycle management.

Singletons self-register their reset functions via ``register_reset``.
``SystemContext.reset_all()`` invokes every registered function in
registration order.

Usage:
    # In a singleton module (e.g. dataframes/models/registry.py):
    from autom8_asana.core.system_context import register_reset
    register_reset(SchemaRegistry.reset)

    # In test fixtures:
    from autom8_asana.core.system_context import SystemContext
    SystemContext.reset_all()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

_reset_registry: list[Callable[[], None]] = []


def register_reset(fn: Callable[[], None]) -> None:
    """Register a callable to be invoked by ``SystemContext.reset_all()``.

    Duplicates are silently ignored so re-importing a module is safe.
    """
    if fn not in _reset_registry:
        _reset_registry.append(fn)


class SystemContext:
    """Centralized access to all singleton reset operations."""

    @staticmethod
    def reset_all() -> None:
        """Reset all singletons to pristine state.

        Intended for test fixtures. Resets are ordered to respect
        dependencies: registries first, then caches, then settings.
        """
        # --- Registration-based resets ---
        for fn in _reset_registry:
            fn()

        logger.debug("system_context_reset_all_complete")
