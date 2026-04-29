"""Unit tests for ``api/routes/_exports_helpers``.

Covers the pure-DataFrame transformations and predicate helpers used by the
Phase 1 ``/exports`` route. Maps to TDD §13 test categories:

- §13.4 identity_complete + null-key surface (PRD AC-4 / AC-5 / AC-6)
- §13.5 activity-state parameterization (PRD AC-8)
- §13.6 unknown_section_value error envelope (PRD §9.2)
- §13.8 predicate date-operator regression (Sprint 2 additive)

Anti-pattern guards exercised:
- AP-6 identity_complete silent failure: NULL-key fixture asserts the row
  surfaces with ``identity_complete=False`` (NOT silently dropped).
- AP-7 PredicateNode AST drift: date operators stay free-form; no entity-prefix.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from autom8_asana.api.routes._exports_helpers import (
    ACTIVE_SECTIONS,
    VALID_SECTIONS,
    DateTranslationResult,
    InvalidSectionError,
    apply_active_default_section_predicate,
    attach_identity_complete,
    dedupe_by_key,
    filter_incomplete_identity,
    predicate_references_field,
    translate_date_predicates,
    validate_section_values,
)
from autom8_asana.query.models import (
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
)

# ---------------------------------------------------------------------------
# §13.4 — identity_complete + null-key surface
# ---------------------------------------------------------------------------


class TestAttachIdentityComplete:
    """attach_identity_complete is the SINGLE source-of-truth (P1-C-05)."""

    def test_both_columns_present_computes_correct_flag(self) -> None:
        df = pl.DataFrame(
            {
                "office_phone": ["555-1", None, "555-2", None],
                "vertical": ["saas", "retail", None, None],
            }
        )
        out = attach_identity_complete(df)
        assert "identity_complete" in out.columns
        assert out["identity_complete"].to_list() == [True, False, False, False]

    def test_null_key_rows_NOT_silently_dropped(self) -> None:
        """AP-6 guard: null-key rows MUST surface in output, not be dropped."""
        df = pl.DataFrame(
            {
                "office_phone": ["555-1", None],
                "vertical": ["saas", None],
            }
        )
        out = attach_identity_complete(df)
        # Critical: row count preserved; NEVER drop null-key rows here.
        assert out.height == 2
        assert out["identity_complete"].to_list() == [True, False]

    def test_missing_office_phone_column_marks_all_false(self) -> None:
        df = pl.DataFrame({"vertical": ["saas", "retail"]})
        out = attach_identity_complete(df)
        assert out["identity_complete"].to_list() == [False, False]

    def test_missing_vertical_column_marks_all_false(self) -> None:
        df = pl.DataFrame({"office_phone": ["555-1", "555-2"]})
        out = attach_identity_complete(df)
        assert out["identity_complete"].to_list() == [False, False]


class TestFilterIncompleteIdentity:
    """PRD AC-5 default (include=True) vs AC-6 opt-out (include=False)."""

    def test_include_true_preserves_all_rows(self) -> None:
        df = pl.DataFrame(
            {
                "office_phone": ["555-1", None],
                "vertical": ["saas", None],
            }
        )
        df = attach_identity_complete(df)
        out = filter_incomplete_identity(df, include=True)
        assert out.height == 2  # AC-5 transparency

    def test_include_false_drops_incomplete_identity_rows(self) -> None:
        df = pl.DataFrame(
            {
                "office_phone": ["555-1", None, "555-2"],
                "vertical": ["saas", "retail", None],
            }
        )
        df = attach_identity_complete(df)
        out = filter_incomplete_identity(df, include=False)
        assert out.height == 1  # only the True row survives
        assert out["office_phone"].to_list() == ["555-1"]

    def test_missing_identity_column_does_not_silently_drop(self) -> None:
        # Defensive: if attach_identity_complete was skipped (programmer error),
        # do NOT drop rows silently.
        df = pl.DataFrame({"office_phone": ["555-1"]})
        out = filter_incomplete_identity(df, include=False)
        assert out.height == 1


class TestDedupeByKey:
    """Account-grain dedup with most-recent-by-modified_at policy."""

    def test_dedupe_picks_most_recent_modified_at(self) -> None:
        df = pl.DataFrame(
            {
                "office_phone": ["555-1", "555-1", "555-2"],
                "vertical": ["saas", "saas", "retail"],
                "modified_at": ["2026-04-27", "2026-04-28", "2026-04-15"],
                "name": ["old", "new", "other"],
            }
        )
        out = dedupe_by_key(df, keys=["office_phone", "vertical"])
        assert out.height == 2
        # The "new" row wins because modified_at is later.
        names = sorted(out["name"].to_list())
        assert names == ["new", "other"]

    def test_dedupe_without_modified_at_falls_back_to_keep_first(self) -> None:
        df = pl.DataFrame(
            {
                "office_phone": ["555-1", "555-1"],
                "vertical": ["saas", "saas"],
                "name": ["first", "second"],
            }
        )
        out = dedupe_by_key(df, keys=["office_phone", "vertical"])
        assert out.height == 1

    def test_dedupe_no_keys_returns_unchanged(self) -> None:
        df = pl.DataFrame({"a": [1, 2]})
        out = dedupe_by_key(df, keys=[])
        assert out.height == 2


# ---------------------------------------------------------------------------
# §13.5 — activity-state parameterization (PRD AC-8 + TDD §9)
# ---------------------------------------------------------------------------


class TestApplyActiveDefaultSectionPredicate:
    """ACTIVE-only default applies ONLY when caller omits ``section``."""

    def test_caller_omits_section_default_applied(self) -> None:
        result, applied = apply_active_default_section_predicate(None)
        assert applied is True
        assert isinstance(result, Comparison)
        assert result.field == "section"
        assert result.op == Op.IN
        assert set(result.value) == set(ACTIVE_SECTIONS)

    def test_caller_provides_section_default_NOT_applied(self) -> None:
        caller = Comparison(field="section", op=Op.IN, value=["SCHEDULED"])
        result, applied = apply_active_default_section_predicate(caller)
        assert applied is False
        assert result is caller

    def test_caller_provides_other_field_default_applied_AND_merged(self) -> None:
        caller = Comparison(field="completed", op=Op.EQ, value=False)
        result, applied = apply_active_default_section_predicate(caller)
        assert applied is True
        assert isinstance(result, AndGroup)
        # Default ACTIVE section filter is FIRST, caller predicate is SECOND.
        assert isinstance(result.and_[0], Comparison)
        assert result.and_[0].field == "section"
        assert result.and_[1] is caller

    def test_section_in_AND_branch_caller_provides_default_NOT_applied(self) -> None:
        c1 = Comparison(field="section", op=Op.IN, value=["ACTIVE"])
        c2 = Comparison(field="completed", op=Op.EQ, value=False)
        caller = AndGroup(and_=[c1, c2])
        result, applied = apply_active_default_section_predicate(caller)
        assert applied is False
        assert result is caller


class TestPredicateReferencesField:
    def test_simple_comparison(self) -> None:
        c = Comparison(field="section", op=Op.EQ, value="ACTIVE")
        assert predicate_references_field(c, "section") is True
        assert predicate_references_field(c, "vertical") is False

    def test_nested_and_group(self) -> None:
        c1 = Comparison(field="completed", op=Op.EQ, value=False)
        c2 = Comparison(field="section", op=Op.IN, value=["ACTIVE"])
        g = AndGroup(and_=[c1, c2])
        assert predicate_references_field(g, "section") is True

    def test_nested_or_group(self) -> None:
        c1 = Comparison(field="completed", op=Op.EQ, value=False)
        c2 = Comparison(field="section", op=Op.IN, value=["ACTIVE"])
        g = OrGroup(or_=[c1, c2])
        assert predicate_references_field(g, "section") is True

    def test_nested_not_group(self) -> None:
        c = Comparison(field="section", op=Op.EQ, value="INACTIVE")
        n = NotGroup(not_=c)
        assert predicate_references_field(n, "section") is True

    def test_none_returns_false(self) -> None:
        assert predicate_references_field(None, "section") is False


# ---------------------------------------------------------------------------
# §13.6 — unknown_section_value (PRD §9.2)
# ---------------------------------------------------------------------------


class TestValidateSectionValues:
    def test_known_section_passes(self) -> None:
        c = Comparison(field="section", op=Op.IN, value=sorted(ACTIVE_SECTIONS))
        validate_section_values(c)  # no exception

    def test_unknown_section_raises(self) -> None:
        c = Comparison(field="section", op=Op.IN, value=["NONSENSE"])
        with pytest.raises(InvalidSectionError) as exc:
            validate_section_values(c)
        assert exc.value.value == "NONSENSE"

    def test_unknown_section_in_eq_raises(self) -> None:
        c = Comparison(field="section", op=Op.EQ, value="MADE_UP")
        with pytest.raises(InvalidSectionError):
            validate_section_values(c)

    def test_other_field_unaffected(self) -> None:
        c = Comparison(field="vertical", op=Op.EQ, value="anything")
        validate_section_values(c)

    def test_nested_and_unknown_section_raises(self) -> None:
        c1 = Comparison(field="completed", op=Op.EQ, value=False)
        c2 = Comparison(field="section", op=Op.IN, value=["BOGUS_SECTION"])
        g = AndGroup(and_=[c1, c2])
        with pytest.raises(InvalidSectionError):
            validate_section_values(g)


def test_active_sections_subset_of_valid_sections() -> None:
    assert ACTIVE_SECTIONS.issubset(VALID_SECTIONS)


def test_active_sections_contains_canonical_members() -> None:
    # Per activity.py:282 _DEFAULT_PROCESS_SECTIONS["active"]
    expected = {"ACTIVE", "EXECUTING", "BUILDING", "PROCESSING", "OPPORTUNITY", "CONTACTED"}
    assert expected.issubset(ACTIVE_SECTIONS)


# ---------------------------------------------------------------------------
# §13.8 — date-operator translation (ESC-1 resolution; TDD §15.1)
# ---------------------------------------------------------------------------


class TestTranslateDatePredicates:
    def test_no_date_ops_returns_predicate_unchanged(self) -> None:
        c = Comparison(field="completed", op=Op.EQ, value=False)
        result = translate_date_predicates(c)
        assert isinstance(result, DateTranslationResult)
        assert result.cleaned_predicate is c
        assert result.date_filter_expr is None

    def test_none_predicate_returns_none(self) -> None:
        result = translate_date_predicates(None)
        assert result.cleaned_predicate is None
        assert result.date_filter_expr is None

    def test_freestanding_between_extracts(self) -> None:
        c = Comparison(field="due_on", op=Op.BETWEEN, value=["2026-01-01", "2026-04-01"])
        result = translate_date_predicates(c)
        assert result.cleaned_predicate is None  # date-only — nothing left for compiler
        assert result.date_filter_expr is not None

    def test_freestanding_date_gte_extracts(self) -> None:
        c = Comparison(field="due_on", op=Op.DATE_GTE, value="2026-01-01")
        result = translate_date_predicates(c)
        assert result.cleaned_predicate is None
        assert result.date_filter_expr is not None

    def test_freestanding_date_lte_extracts(self) -> None:
        c = Comparison(field="due_on", op=Op.DATE_LTE, value="2026-04-01")
        result = translate_date_predicates(c)
        assert result.cleaned_predicate is None
        assert result.date_filter_expr is not None

    def test_relative_date_string_supported(self) -> None:
        c = Comparison(field="due_on", op=Op.DATE_LTE, value="30d")
        result = translate_date_predicates(c)
        assert result.date_filter_expr is not None  # parsed via temporal helper

    def test_and_group_splits_date_from_non_date(self) -> None:
        c_date = Comparison(field="due_on", op=Op.DATE_GTE, value="2026-01-01")
        c_eq = Comparison(field="completed", op=Op.EQ, value=False)
        g = AndGroup(and_=[c_date, c_eq])
        result = translate_date_predicates(g)
        # Cleaned predicate retains the EQ; date expression is non-None.
        assert result.cleaned_predicate is not None
        assert isinstance(result.cleaned_predicate, Comparison)
        assert result.cleaned_predicate.field == "completed"
        assert result.date_filter_expr is not None

    def test_and_group_with_two_date_ops_combines_via_and(self) -> None:
        c1 = Comparison(field="due_on", op=Op.DATE_GTE, value="2026-01-01")
        c2 = Comparison(field="due_on", op=Op.DATE_LTE, value="2026-04-01")
        g = AndGroup(and_=[c1, c2])
        result = translate_date_predicates(g)
        assert result.cleaned_predicate is None
        assert result.date_filter_expr is not None  # AND-merged

    def test_or_group_with_date_op_raises(self) -> None:
        # Phase 1: OR semantics with date ops are unsupported — ESC-1 only
        # handles AND-merge translations.
        c1 = Comparison(field="due_on", op=Op.DATE_GTE, value="2026-01-01")
        c2 = Comparison(field="completed", op=Op.EQ, value=True)
        g = OrGroup(or_=[c1, c2])
        with pytest.raises(ValueError, match="under an OR group"):
            translate_date_predicates(g)

    def test_not_group_with_date_op_raises(self) -> None:
        c = Comparison(field="due_on", op=Op.DATE_GTE, value="2026-01-01")
        n = NotGroup(not_=c)
        with pytest.raises(ValueError, match="under a NOT group"):
            translate_date_predicates(n)

    def test_between_with_invalid_value_shape_raises(self) -> None:
        c = Comparison(field="due_on", op=Op.BETWEEN, value="not_a_list")
        with pytest.raises(ValueError, match="BETWEEN requires"):
            translate_date_predicates(c)

    def test_date_filter_applies_to_dataframe(self) -> None:
        # End-to-end: translated expression actually filters a fixture frame.
        df = pl.DataFrame(
            {
                "due_on": [date(2026, 1, 15), date(2026, 3, 1), date(2026, 5, 1)],
                "name": ["a", "b", "c"],
            }
        )
        c = Comparison(field="due_on", op=Op.BETWEEN, value=["2026-01-01", "2026-04-01"])
        result = translate_date_predicates(c)
        filtered = df.filter(result.date_filter_expr)
        assert filtered["name"].to_list() == ["a", "b"]
