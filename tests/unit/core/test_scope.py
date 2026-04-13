"""Unit tests for EntityScope dataclass.

Per TDD-ENTITY-SCOPE-001 Section 8.2: Tests for EntityScope construction,
from_event normalization, properties, and serialization.
"""

from __future__ import annotations

import dataclasses

import pytest

from autom8_asana.core.scope import EntityScope


class TestEntityScopeFromEvent:
    """Tests for EntityScope.from_event() factory method."""

    def test_from_event_empty(self) -> None:
        """Empty event produces defaults."""
        scope = EntityScope.from_event({})
        assert scope.entity_ids == ()
        assert scope.section_filter == frozenset()
        assert scope.limit is None
        assert scope.dry_run is False

    def test_from_event_entity_ids(self) -> None:
        """entity_ids list is normalized to tuple."""
        scope = EntityScope.from_event({"entity_ids": ["123", "456"]})
        assert scope.entity_ids == ("123", "456")

    def test_from_event_dry_run(self) -> None:
        """dry_run=True is preserved."""
        scope = EntityScope.from_event({"dry_run": True})
        assert scope.dry_run is True

    def test_from_event_dry_run_false(self) -> None:
        """dry_run defaults to False."""
        scope = EntityScope.from_event({"dry_run": False})
        assert scope.dry_run is False

    def test_from_event_section_filter(self) -> None:
        """section_filter list is normalized to frozenset."""
        scope = EntityScope.from_event({"section_filter": ["Active", "Pending"]})
        assert scope.section_filter == frozenset({"Active", "Pending"})

    def test_from_event_limit(self) -> None:
        """Integer limit is passed through."""
        scope = EntityScope.from_event({"limit": 10})
        assert scope.limit == 10

    def test_from_event_limit_none(self) -> None:
        """None limit is preserved."""
        scope = EntityScope.from_event({"limit": None})
        assert scope.limit is None

    def test_from_event_unknown_keys_ignored(self) -> None:
        """Extra keys do not raise."""
        scope = EntityScope.from_event({"entity_ids": ["123"], "unknown_key": "value", "extra": 42})
        assert scope.entity_ids == ("123",)

    def test_from_event_empty_entity_ids(self) -> None:
        """Empty list produces empty tuple."""
        scope = EntityScope.from_event({"entity_ids": []})
        assert scope.entity_ids == ()

    def test_from_event_empty_section_filter(self) -> None:
        """Empty list produces empty frozenset."""
        scope = EntityScope.from_event({"section_filter": []})
        assert scope.section_filter == frozenset()


class TestEntityScopeProperties:
    """Tests for EntityScope properties."""

    def test_has_entity_ids_true(self) -> None:
        """Non-empty entity_ids returns True."""
        scope = EntityScope(entity_ids=("123",))
        assert scope.has_entity_ids is True

    def test_has_entity_ids_false(self) -> None:
        """Empty entity_ids returns False."""
        scope = EntityScope()
        assert scope.has_entity_ids is False


class TestEntityScopeToParams:
    """Tests for EntityScope.to_params() serialization."""

    def test_to_params_returns_dry_run_false(self) -> None:
        """to_params includes dry_run=False."""
        scope = EntityScope()
        assert scope.to_params() == {"dry_run": False}

    def test_to_params_returns_dry_run_true(self) -> None:
        """to_params includes dry_run=True."""
        scope = EntityScope(dry_run=True)
        assert scope.to_params() == {"dry_run": True}


class TestEntityScopeFrozen:
    """Tests for EntityScope immutability."""

    def test_frozen(self) -> None:
        """Assignment raises FrozenInstanceError."""
        scope = EntityScope()
        with pytest.raises(dataclasses.FrozenInstanceError):
            scope.entity_ids = ("999",)  # type: ignore[misc]
