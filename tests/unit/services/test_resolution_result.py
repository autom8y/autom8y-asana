"""Unit tests for ResolutionResult.

Per TDD-DYNAMIC-RESOLVER-001 / FR-004:
Tests multi-match resolution result with backwards-compatible gid property.
"""

import pytest

from autom8_asana.services.resolution_result import ResolutionResult


class TestResolutionResultBasics:
    """Basic tests for ResolutionResult creation and properties."""

    def test_single_match_is_unique(self) -> None:
        """Single match: is_unique=True, gid returns value."""
        result = ResolutionResult(gids=("123",))

        assert result.is_unique is True
        assert result.is_ambiguous is False
        assert result.gid == "123"
        assert result.match_count == 1

    def test_multi_match_is_ambiguous(self) -> None:
        """Multiple matches: is_ambiguous=True, gid returns first."""
        result = ResolutionResult(gids=("123", "456", "789"))

        assert result.is_unique is False
        assert result.is_ambiguous is True
        assert result.gid == "123"  # Returns first
        assert result.gids == ("123", "456", "789")
        assert result.match_count == 3

    def test_no_match_properties(self) -> None:
        """No matches: both is_unique and is_ambiguous are False."""
        result = ResolutionResult(gids=())

        assert result.is_unique is False
        assert result.is_ambiguous is False
        assert result.gid is None
        assert result.match_count == 0

    def test_match_count_auto_computation(self) -> None:
        """match_count computed automatically from gids if not provided."""
        result = ResolutionResult(gids=("a", "b", "c"))

        assert result.match_count == 3

    def test_match_count_explicit(self) -> None:
        """Explicit match_count is respected."""
        result = ResolutionResult(gids=("a", "b"), match_count=2)

        assert result.match_count == 2

    def test_match_count_zero_not_overwritten(self) -> None:
        """match_count=0 with empty gids stays 0."""
        result = ResolutionResult(gids=(), match_count=0)

        assert result.match_count == 0


class TestResolutionResultBackwardsCompatibility:
    """Tests for backwards compatibility with single-GID API."""

    def test_gid_property_returns_first_match(self) -> None:
        """gid property returns first match for multi-match."""
        result = ResolutionResult.from_gids(["first", "second", "third"])

        assert result.gid == "first"

    def test_gid_property_returns_none_when_empty(self) -> None:
        """gid property returns None when no matches."""
        result = ResolutionResult(gids=())

        assert result.gid is None

    def test_gid_property_single_match(self) -> None:
        """gid property works correctly for single match."""
        result = ResolutionResult.from_gids(["only_one"])

        assert result.gid == "only_one"
        assert result.is_unique is True


class TestResolutionResultFactories:
    """Tests for factory methods."""

    def test_not_found_factory(self) -> None:
        """not_found factory creates correct result."""
        result = ResolutionResult.not_found()

        assert result.gids == ()
        assert result.match_count == 0
        assert result.error == "NOT_FOUND"
        assert result.gid is None
        assert result.is_unique is False
        assert result.is_ambiguous is False

    def test_error_result_factory(self) -> None:
        """error_result factory creates result with error."""
        result = ResolutionResult.error_result("INVALID_CRITERIA")

        assert result.gids == ()
        assert result.match_count == 0
        assert result.error == "INVALID_CRITERIA"
        assert result.gid is None

    def test_error_result_custom_error(self) -> None:
        """error_result factory accepts any error string."""
        result = ResolutionResult.error_result("CUSTOM_ERROR_CODE")

        assert result.error == "CUSTOM_ERROR_CODE"

    def test_from_gids_with_matches(self) -> None:
        """from_gids factory with matches creates valid result."""
        result = ResolutionResult.from_gids(["gid1", "gid2"])

        assert result.gids == ("gid1", "gid2")
        assert result.match_count == 2
        assert result.gid == "gid1"
        assert result.error is None

    def test_from_gids_empty_returns_not_found(self) -> None:
        """from_gids with empty list returns NOT_FOUND."""
        result = ResolutionResult.from_gids([])

        assert result.gids == ()
        assert result.match_count == 0
        assert result.error == "NOT_FOUND"

    def test_from_gids_with_context(self) -> None:
        """from_gids factory with context includes context data."""
        context = [
            {"name": "Entity A", "modified_at": "2026-01-08"},
            {"name": "Entity B", "modified_at": "2026-01-07"},
        ]
        result = ResolutionResult.from_gids(
            gids=["gid1", "gid2"],
            context=context,
        )

        assert result.match_context is not None
        assert len(result.match_context) == 2
        assert result.match_context[0]["name"] == "Entity A"
        assert result.match_context[1]["name"] == "Entity B"

    def test_from_gids_without_context(self) -> None:
        """from_gids without context has None match_context."""
        result = ResolutionResult.from_gids(["gid1"])

        assert result.match_context is None


class TestResolutionResultImmutability:
    """Tests for frozen dataclass immutability."""

    def test_frozen_cannot_modify_gids(self) -> None:
        """Cannot modify gids after creation (frozen)."""
        result = ResolutionResult(gids=("123",))

        with pytest.raises(AttributeError):
            result.gids = ("456",)  # type: ignore[misc]

    def test_frozen_cannot_modify_error(self) -> None:
        """Cannot modify error after creation (frozen)."""
        result = ResolutionResult(gids=(), error="NOT_FOUND")

        with pytest.raises(AttributeError):
            result.error = "DIFFERENT"  # type: ignore[misc]

    def test_frozen_cannot_modify_match_count(self) -> None:
        """Cannot modify match_count after creation (frozen)."""
        result = ResolutionResult(gids=("a", "b"))

        with pytest.raises(AttributeError):
            result.match_count = 99  # type: ignore[misc]


class TestResolutionResultToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_basic(self) -> None:
        """to_dict includes required fields."""
        result = ResolutionResult.from_gids(["gid1"])

        d = result.to_dict()

        assert d["gids"] == ["gid1"]
        assert d["match_count"] == 1
        assert d["gid"] == "gid1"
        assert "error" not in d
        assert "context" not in d

    def test_to_dict_with_error(self) -> None:
        """to_dict includes error when present."""
        result = ResolutionResult.error_result("NOT_FOUND")

        d = result.to_dict()

        assert d["error"] == "NOT_FOUND"
        assert d["gids"] == []
        assert d["match_count"] == 0
        assert d["gid"] is None

    def test_to_dict_with_context(self) -> None:
        """to_dict includes context when present."""
        context = [{"name": "Test Entity"}]
        result = ResolutionResult.from_gids(["gid1"], context=context)

        d = result.to_dict()

        assert d["context"] == [{"name": "Test Entity"}]

    def test_to_dict_multi_match(self) -> None:
        """to_dict handles multi-match correctly."""
        result = ResolutionResult.from_gids(["a", "b", "c"])

        d = result.to_dict()

        assert d["gids"] == ["a", "b", "c"]
        assert d["match_count"] == 3
        assert d["gid"] == "a"  # First match

    def test_to_dict_returns_list_not_tuple(self) -> None:
        """to_dict converts tuples to lists for JSON compatibility."""
        result = ResolutionResult(gids=("x", "y"))

        d = result.to_dict()

        assert isinstance(d["gids"], list)
        assert d["gids"] == ["x", "y"]


class TestResolutionResultEdgeCases:
    """Edge case tests."""

    def test_single_empty_string_gid(self) -> None:
        """Handles empty string GID correctly."""
        result = ResolutionResult(gids=("",))

        assert result.gid == ""
        assert result.is_unique is True
        assert result.match_count == 1

    def test_match_context_empty_list(self) -> None:
        """Empty context list becomes None (not stored)."""
        result = ResolutionResult.from_gids(["gid1"], context=[])

        # Empty list is falsy, so becomes None
        assert result.match_context is None

    def test_very_long_gid_list(self) -> None:
        """Handles large number of GIDs."""
        gids = [f"gid-{i}" for i in range(1000)]
        result = ResolutionResult.from_gids(gids)

        assert result.match_count == 1000
        assert result.gid == "gid-0"
        assert result.is_ambiguous is True
        assert len(result.gids) == 1000

    def test_context_with_various_types(self) -> None:
        """Context can contain various value types."""
        context = [
            {
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "none": None,
                "list": [1, 2, 3],
            }
        ]
        result = ResolutionResult.from_gids(["gid1"], context=context)

        assert result.match_context is not None
        assert result.match_context[0]["string"] == "value"
        assert result.match_context[0]["number"] == 42
        assert result.match_context[0]["boolean"] is True
