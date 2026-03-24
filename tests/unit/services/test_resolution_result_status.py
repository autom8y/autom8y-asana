"""Unit tests for ResolutionResult status annotation support.

Per TDD-STATUS-AWARE-RESOLUTION / FR-3, FR-4, FR-7, FR-8, FR-9, FR-11:
Tests for status_annotations, total_match_count, from_gids_with_status(),
and updated to_dict() serialization.
"""

from __future__ import annotations

from autom8_asana.services.resolution_result import ResolutionResult


class TestFromGidsWithStatus:
    """Tests for from_gids_with_status() factory method."""

    def test_from_gids_with_status_preserves_parallel_tuple(self) -> None:
        """Verify gids and status_annotations are same length.

        Per FR-3: status_annotations is a parallel tuple.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1", "gid-2", "gid-3"],
            status_annotations=["active", "activating", "inactive"],
        )

        assert result.gids == ("gid-1", "gid-2", "gid-3")
        assert result.status_annotations == ("active", "activating", "inactive")
        assert len(result.gids) == len(result.status_annotations)
        assert result.match_count == 3

    def test_from_gids_with_status_none_annotations(self) -> None:
        """status_annotations=None when no classifier.

        Per FR-7: No classifier -> status_annotations is None.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1", "gid-2"],
            status_annotations=None,
        )

        assert result.gids == ("gid-1", "gid-2")
        assert result.status_annotations is None
        assert result.match_count == 2

    def test_gid_property_returns_first_gid_after_priority_sort(self) -> None:
        """gid returns gids[0] which is ACTIVE after sort.

        Per FR-4: gid returns best match (first after ACTIVITY_PRIORITY sort).
        The caller sorts before constructing the result.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["active-gid", "activating-gid"],
            status_annotations=["active", "activating"],
        )

        assert result.gid == "active-gid"

    def test_gid_property_none_when_all_filtered(self) -> None:
        """Empty gids after filtering -> gid returns None.

        Per EC-1: All filtered out returns NOT_FOUND.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=[],
            status_annotations=None,
        )

        assert result.gid is None
        assert result.error == "NOT_FOUND"
        assert result.match_count == 0

    def test_not_found_has_no_status_annotations(self) -> None:
        """not_found() factory produces None annotations.

        Per FR-9: NOT_FOUND result has no status data.
        """
        result = ResolutionResult.not_found()

        assert result.status_annotations is None
        assert result.total_match_count is None
        assert result.error == "NOT_FOUND"

    def test_from_gids_with_status_empty_list_returns_not_found(self) -> None:
        """Empty GID list -> NOT_FOUND.

        Per EC-8: Empty result after filtering returns NOT_FOUND.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=[],
            status_annotations=[],
        )

        assert result.error == "NOT_FOUND"
        assert result.gids == ()
        assert result.match_count == 0

    def test_from_gids_with_status_with_total_match_count(self) -> None:
        """total_match_count carries through from factory.

        Per FR-11: Pre-filter count for diagnostic metadata.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1"],
            status_annotations=["active"],
            total_match_count=5,
        )

        assert result.total_match_count == 5
        assert result.match_count == 1

    def test_from_gids_with_status_with_context(self) -> None:
        """Context data carries through from factory."""
        context = [{"name": "Entity A"}, {"name": "Entity B"}]
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1", "gid-2"],
            status_annotations=["active", "inactive"],
            context=context,
        )

        assert result.match_context is not None
        assert len(result.match_context) == 2
        assert result.match_context[0]["name"] == "Entity A"


class TestToDictWithStatus:
    """Tests for to_dict() with status annotations."""

    def test_to_dict_includes_status_annotations(self) -> None:
        """Serialization includes status list.

        Per FR-3: status_annotations in dict output.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1", "gid-2"],
            status_annotations=["active", None],
        )

        d = result.to_dict()

        assert "status_annotations" in d
        assert d["status_annotations"] == ["active", None]

    def test_to_dict_includes_total_match_count(self) -> None:
        """Serialization includes pre-filter count.

        Per FR-11: total_match_count in dict output when present.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1"],
            status_annotations=["active"],
            total_match_count=3,
        )

        d = result.to_dict()

        assert d["total_match_count"] == 3

    def test_to_dict_omits_null_total_match_count(self) -> None:
        """None total_match_count omitted from dict.

        Per FR-11: Omit when active_only=False or no classifier.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1", "gid-2"],
            status_annotations=["active", "inactive"],
            total_match_count=None,
        )

        d = result.to_dict()

        assert "total_match_count" not in d

    def test_to_dict_omits_null_status_annotations(self) -> None:
        """None status_annotations omitted from dict (FR-7 degradation)."""
        result = ResolutionResult.from_gids(["gid-1", "gid-2"])

        d = result.to_dict()

        assert "status_annotations" not in d
        assert "total_match_count" not in d

    def test_to_dict_preserves_backwards_compat_fields(self) -> None:
        """Status additions do not remove existing fields."""
        result = ResolutionResult.from_gids_with_status(
            gids=["gid-1"],
            status_annotations=["active"],
            total_match_count=2,
        )

        d = result.to_dict()

        # Existing fields still present
        assert "gids" in d
        assert "match_count" in d
        assert "gid" in d
        assert d["gid"] == "gid-1"
        assert d["gids"] == ["gid-1"]
