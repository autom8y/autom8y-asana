"""Unit tests for explicit application bootstrap.

Per TDD-bootstrap / ADR-0149: Tests for bootstrap() function and
_ensure_bootstrapped() fallback guard on ProjectTypeRegistry.

Test cases:
1. bootstrap() populates registry and is idempotent
2. _ensure_bootstrapped() fallback works without explicit bootstrap()
3. _ensure_bootstrapped() is a no-op when bootstrap is already complete
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.models.business._bootstrap import (
    bootstrap,
    is_bootstrap_complete,
    reset_bootstrap,
)
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    get_registry,
)

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def clean_state() -> Generator[None, None, None]:
    """Reset registry and bootstrap state before and after each test."""
    ProjectTypeRegistry.reset()
    reset_bootstrap()
    yield
    ProjectTypeRegistry.reset()
    reset_bootstrap()


class TestBootstrapFunction:
    """Tests for the bootstrap() public API."""

    def test_bootstrap_populates_registry(self, clean_state: None) -> None:
        """bootstrap() populates ProjectTypeRegistry with entity mappings."""
        assert not is_bootstrap_complete()

        bootstrap()

        assert is_bootstrap_complete()
        registry = get_registry()
        assert registry.lookup("1200653012566782") == EntityType.BUSINESS

    def test_bootstrap_is_idempotent(self, clean_state: None) -> None:
        """bootstrap() can be called multiple times without error or side effects."""
        bootstrap()
        bootstrap()
        bootstrap()

        assert is_bootstrap_complete()
        registry = get_registry()
        assert registry.lookup("1200653012566782") == EntityType.BUSINESS


class TestEnsureBootstrappedFallback:
    """Tests for _ensure_bootstrapped() guard on ProjectTypeRegistry."""

    def test_detection_works_without_explicit_bootstrap(self, clean_state: None) -> None:
        """SC-8: Detection succeeds via _ensure_bootstrapped() fallback.

        When no explicit bootstrap() has been called, the guard on
        ProjectTypeRegistry.lookup() triggers lazy initialization.
        """
        # Verify clean state: no bootstrap has run
        assert not is_bootstrap_complete()

        # Do NOT call bootstrap() -- rely on guard
        registry = ProjectTypeRegistry()
        # This should trigger _ensure_bootstrapped() via lookup()
        result = registry.lookup("1200653012566782")

        # Registry should now be populated
        assert result == EntityType.BUSINESS
        assert is_bootstrap_complete()
        assert registry.get_all_mappings()  # Non-empty

    def test_ensure_bootstrapped_noop_when_complete(self, clean_state: None) -> None:
        """_ensure_bootstrapped() is a no-op when bootstrap is already complete."""
        bootstrap()

        # Subsequent lookups should not re-trigger registration
        registry = get_registry()
        result = registry.lookup("1200653012566782")
        assert result == EntityType.BUSINESS

    def test_get_primary_gid_triggers_guard(self, clean_state: None) -> None:
        """get_primary_gid() triggers _ensure_bootstrapped() on first access."""
        assert not is_bootstrap_complete()

        registry = ProjectTypeRegistry()
        gid = registry.get_primary_gid(EntityType.BUSINESS)

        assert gid == "1200653012566782"
        assert is_bootstrap_complete()

    def test_is_registered_triggers_guard(self, clean_state: None) -> None:
        """is_registered() triggers _ensure_bootstrapped() on first access."""
        assert not is_bootstrap_complete()

        registry = ProjectTypeRegistry()
        result = registry.is_registered("1200653012566782")

        assert result is True
        assert is_bootstrap_complete()

    def test_get_all_mappings_triggers_guard(self, clean_state: None) -> None:
        """get_all_mappings() triggers _ensure_bootstrapped() on first access."""
        assert not is_bootstrap_complete()

        registry = ProjectTypeRegistry()
        mappings = registry.get_all_mappings()

        assert len(mappings) > 0
        assert is_bootstrap_complete()
