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

import os
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

# Per-worker registry: keyed by pytest-xdist worker ID so that parallel
# workers each maintain an independent reset-function list.  Outside of
# xdist (serial runs, non-pytest contexts) the key falls back to "main".
# Registration order within each key is preserved (append-on-import).
_reset_registry: dict[str, list[Callable[[], None]]] = {}


def _worker_key() -> str:
    """Return the current worker identifier for registry isolation."""
    return os.environ.get("PYTEST_XDIST_WORKER", "main")


def register_reset(fn: Callable[[], None]) -> None:
    """Register a callable to be invoked by ``SystemContext.reset_all()``.

    Duplicates are silently ignored so re-importing a module is safe.
    Registrations are keyed per xdist worker so parallel workers maintain
    independent reset lists.
    """
    key = _worker_key()
    if key not in _reset_registry:
        _reset_registry[key] = []
    if fn not in _reset_registry[key]:
        _reset_registry[key].append(fn)


class SystemContext:
    """Centralized access to all singleton reset operations."""

    @staticmethod
    def reset_all() -> None:
        """Reset all singletons to pristine state.

        Intended for test fixtures. Resets are ordered to respect
        dependencies: registries first, then caches, then settings.
        Registration order is preserved per-worker (append-on-import
        discipline ensures dependency ordering).
        """
        # --- Registration-based resets (worker-local list) ---
        for fn in _reset_registry.get(_worker_key(), []):
            fn()

        logger.debug("system_context_reset_all_complete")
