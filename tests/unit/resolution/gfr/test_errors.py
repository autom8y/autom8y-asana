"""Tests for the GFR domain error hierarchy (TDD §2 errors.py).

Verifies the closed reason vocabulary (INVARIANT I4), the no-bare-Exception
discipline, and the carried-attribute contracts.
"""

from __future__ import annotations

import pytest

from autom8_asana.resolution.gfr.errors import (
    UNRESOLVED_REASONS,
    AmbiguousCardinalityError,
    GfrError,
    GuardViolationError,
    UnresolvedError,
)


class TestHierarchy:
    def test_all_errors_subclass_gfr_error(self) -> None:
        assert issubclass(UnresolvedError, GfrError)
        assert issubclass(GuardViolationError, GfrError)
        assert issubclass(AmbiguousCardinalityError, GfrError)

    def test_gfr_error_is_exception_not_bare(self) -> None:
        assert issubclass(GfrError, Exception)


class TestUnresolvedError:
    @pytest.mark.parametrize("reason", sorted(UNRESOLVED_REASONS))
    def test_accepts_each_closed_reason(self, reason: str) -> None:
        err = UnresolvedError(fields=["company_id"], reason=reason)
        assert err.reason == reason
        assert err.fields == ["company_id"]

    def test_rejects_out_of_vocabulary_reason(self) -> None:
        with pytest.raises(ValueError, match="closed vocabulary"):
            UnresolvedError(fields=["x"], reason="made-up-reason")

    def test_fields_copied_not_aliased(self) -> None:
        src = ["a", "b"]
        err = UnresolvedError(fields=src, reason="unknown-field")
        src.append("c")
        assert err.fields == ["a", "b"]

    def test_closed_vocabulary_membership(self) -> None:
        assert (
            frozenset(
                {
                    "unknown-field",
                    "empty-frame",
                    "entity-type-undetectable",
                    "no-identity-path",
                    "business-row-not-found",
                }
            )
            == UNRESOLVED_REASONS
        )


class TestAmbiguousCardinalityError:
    def test_carries_row_count(self) -> None:
        err = AmbiguousCardinalityError(row_count=3)
        assert err.row_count == 3
        assert "3" in str(err)


class TestGuardViolationError:
    def test_message_round_trips(self) -> None:
        err = GuardViolationError("identity via phone")
        assert "identity via phone" in str(err)
