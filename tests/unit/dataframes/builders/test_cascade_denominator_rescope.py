"""Two-sided tests for the parent-mediated cascade denominator rescope.

Structure-evaluator RULING (CONCUR-WITH-CONDITIONS, 2026-08-22) conditions
C1-C5.  The rescope changes what population a cascade null rate is measured
against: rows with a non-null ``parent_gid``, computed in-frame, no join.

Each condition below is tested TWO-SIDED -- the fixture that should pass AND
the fixture that should fail.  A one-sided suite here would be worthless: the
whole failure this rescope corrects is a gate that could not distinguish
"unreachable by construction" from "broken".

The live shape the fixtures model (contact entity, 2026-08-22 production
reading): ~62% of contact rows have NO parent in Asana at all.  Under the
pre-rescope full-frame denominator those orphans counted as cascade faults,
so the 20% threshold sat permanently out of reach of any join or warm fix --
the gate was unclearable, which is a denominator question, never a threshold
one.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders import cascade_validator
from autom8_asana.dataframes.builders.cascade_validator import (
    CASCADE_NULL_ERROR_THRESHOLD,
    CascadeDenominatorCollapsedError,
    audit_cascade_key_nulls,
    check_cascade_health,
    resolve_cascade_denominator,
)
from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA
from autom8_asana.services.dynamic_index import DynamicIndexCache
from autom8_asana.services.errors import CascadeNotReadyError, get_status_for_error
from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

_CASCADE_COLUMNS = [("office_phone", "Office Phone")]
_KEY_COLUMNS = ("office_phone",)


def _make_schema(cascade_columns: list[tuple[str, str]]) -> MagicMock:
    schema = MagicMock()
    schema.get_cascade_columns.return_value = cascade_columns
    return schema


def _frame(
    *,
    orphans: int,
    joinable_populated: int,
    joinable_null: int,
) -> pl.DataFrame:
    """Build a contact-shaped frame with an explicit orphan/joinable split.

    Args:
        orphans: Rows with ``parent_gid`` null -- no parent in Asana.
        joinable_populated: Parented rows whose cascade value arrived.
        joinable_null: Parented rows whose cascade value is missing.  These
            are the only genuine cascade faults.
    """
    parent_gids: list[str | None] = (
        [None] * orphans + ["parent-1"] * joinable_populated + ["parent-2"] * joinable_null
    )
    phones: list[str | None] = (
        [None] * orphans + ["+15551230000"] * joinable_populated + [None] * joinable_null
    )
    total = orphans + joinable_populated + joinable_null
    return pl.DataFrame(
        {
            "gid": [f"t{i}" for i in range(total)],
            "parent_gid": parent_gids,
            "office_phone": phones,
        },
        schema={"gid": pl.Utf8, "parent_gid": pl.Utf8, "office_phone": pl.Utf8},
    )


#: 62% unparented, and every parented row is clean.  This is the shape the
#: live contact frame is in: no cascade fault at all, but the pre-rescope
#: gate read 62% and refused.
ORPHAN_HEAVY = dict(orphans=620, joinable_populated=380, joinable_null=0)

#: Same orphan load, but 25% of the PARENTED rows lost their cascade value.
#: That is a real fault and must still trip the gate.
JOINABLE_DIRTY = dict(orphans=620, joinable_populated=285, joinable_null=95)


# ---------------------------------------------------------------------------
# C1 -- the denominator is parent_gid.is_not_null(), in-frame, no join
# ---------------------------------------------------------------------------


class TestDenominatorIsParentGidInFrame:
    """RULING C1 (BLOCKING)."""

    def test_denominator_counts_only_parented_rows(self) -> None:
        denominator = resolve_cascade_denominator(_frame(**ORPHAN_HEAVY), _CASCADE_COLUMNS)

        assert denominator.total_rows == 1000
        assert denominator.joinable_rows == 380
        assert denominator.orphan_rows == 620
        assert denominator.orphan_rate == pytest.approx(0.62)
        assert denominator.rescoped is True

    def test_orphans_leave_both_numerator_and_denominator(self) -> None:
        """An orphan is not a cascade fault -- it has no ancestor to inherit from."""
        denominator = resolve_cascade_denominator(_frame(**ORPHAN_HEAVY), _CASCADE_COLUMNS)

        assert denominator.frame.height == 380
        assert denominator.frame["office_phone"].null_count() == 0

    def test_a_row_with_an_unresolvable_parent_stays_in_the_numerator(self) -> None:
        """The keystone of C1: the gate gets LOUDER as the join degrades.

        A row that HAS a parent_gid but whose parent the join cannot follow
        keeps its place in the denominator and shows up as a null in the
        numerator.  The refused "resolves to a Business row" definition would
        have migrated exactly these rows OUT of the denominator, shrinking the
        population until the gate read healthy as the data got worse.
        """
        frame = _frame(orphans=0, joinable_populated=90, joinable_null=10)
        denominator = resolve_cascade_denominator(frame, _CASCADE_COLUMNS)

        assert denominator.joinable_rows == 100, "unresolvable parents stay in the denominator"
        assert denominator.frame["office_phone"].null_count() == 10, "and stay in the numerator"

    def test_no_join_is_performed(self) -> None:
        """The rescope reads one column of one frame.

        The frame carries no Business rows and no join key beyond parent_gid;
        if the implementation reached for a second frame this would fail.
        """
        frame = _frame(**ORPHAN_HEAVY)
        assert set(frame.columns) == {"gid", "parent_gid", "office_phone"}

        denominator = resolve_cascade_denominator(frame, _CASCADE_COLUMNS)

        assert denominator.joinable_rows == 380

    def test_gate_passes_on_orphan_heavy_but_joinable_clean(self) -> None:
        result = check_cascade_health(
            df=_frame(**ORPHAN_HEAVY),
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.healthy is True
        assert result.max_null_rate == 0.0
        assert result.degraded_columns == {}

    def test_gate_fails_when_parented_rows_are_dirty(self) -> None:
        result = check_cascade_health(
            df=_frame(**JOINABLE_DIRTY),
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.healthy is False
        assert "office_phone" in result.degraded_columns
        # 95 nulls / 380 parented rows = 25%, over the 20% threshold.
        assert result.degraded_columns["office_phone"] == pytest.approx(0.25)

    def test_the_same_frame_read_two_ways_gives_two_verdicts(self) -> None:
        """The rescope is load-bearing, not cosmetic.

        ORPHAN_HEAVY is 62% null on the full frame and 0% null on the
        parented population.  Full-frame reading refuses; rescoped reading
        passes.  If this assertion ever collapses to one verdict the rescope
        has been silently reverted.
        """
        frame = _frame(**ORPHAN_HEAVY)

        full_frame_rate = frame["office_phone"].null_count() / frame.height
        rescoped = resolve_cascade_denominator(frame, _CASCADE_COLUMNS)
        rescoped_rate = rescoped.frame["office_phone"].null_count() / rescoped.joinable_rows

        assert full_frame_rate > CASCADE_NULL_ERROR_THRESHOLD
        assert rescoped_rate <= CASCADE_NULL_ERROR_THRESHOLD


# ---------------------------------------------------------------------------
# C2 -- denominator fields on the audit log AND the span
# ---------------------------------------------------------------------------


class TestDenominatorFieldsAreEmitted:
    """RULING C2."""

    def test_audit_log_carries_all_four_fields(self) -> None:
        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=_frame(**ORPHAN_HEAVY),
                entity_type="contact",
                project_gid="proj-1",
                schema=_make_schema(_CASCADE_COLUMNS),
                key_columns=_KEY_COLUMNS,
            )

        mock_logger.info.assert_called_once()
        extra = mock_logger.info.call_args[1]["extra"]
        assert extra["total_rows"] == 1000
        assert extra["joinable_rows"] == 380
        assert extra["orphan_rows"] == 620
        assert extra["orphan_rate"] == pytest.approx(0.62)
        assert extra["denominator_rescoped"] is True

    def test_audit_rate_is_joinable_scoped_not_full_frame(self) -> None:
        """Audit and gate must read the same number, or the log lies."""
        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=_frame(**JOINABLE_DIRTY),
                entity_type="contact",
                project_gid="proj-1",
                schema=_make_schema(_CASCADE_COLUMNS),
                key_columns=_KEY_COLUMNS,
            )

        extra = mock_logger.error.call_args[1]["extra"]
        assert extra["severity"] == "error"
        # 95/380 = 25% joinable-scoped, NOT 715/1000 = 71.5% full-frame.
        assert extra["cascade_key_nulls"]["office_phone"]["null_rate"] == pytest.approx(0.25)
        assert extra["cascade_key_nulls"]["office_phone"]["null_count"] == 95

    def test_span_carries_all_four_fields(self) -> None:
        span = MagicMock()
        with (
            patch(
                "autom8_asana.dataframes.builders.cascade_validator._otel_trace.get_current_span",
                return_value=span,
            ),
            patch("autom8_asana.dataframes.builders.cascade_validator.logger"),
        ):
            audit_cascade_key_nulls(
                df=_frame(**ORPHAN_HEAVY),
                entity_type="contact",
                project_gid="proj-1",
                schema=_make_schema(_CASCADE_COLUMNS),
                key_columns=_KEY_COLUMNS,
            )

        emitted = {call.args[0]: call.args[1] for call in span.set_attribute.call_args_list}
        assert emitted["computation.cascade_audit.total_rows"] == 1000
        assert emitted["computation.cascade_audit.joinable_rows"] == 380
        assert emitted["computation.cascade_audit.orphan_rows"] == 620
        assert emitted["computation.cascade_audit.orphan_rate"] == pytest.approx(0.62)
        assert emitted["computation.cascade_audit.denominator_rescoped"] is True

    def test_health_result_carries_the_denominator(self) -> None:
        result = check_cascade_health(
            df=_frame(**ORPHAN_HEAVY),
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.total_rows == 1000
        assert result.joinable_rows == 380
        assert result.orphan_rows == 620
        assert result.orphan_rate == pytest.approx(0.62)
        assert result.denominator_rescoped is True


# ---------------------------------------------------------------------------
# C3 -- fail CLOSED when the denominator collapses
# ---------------------------------------------------------------------------


class TestCollapseFailsClosed:
    """RULING C3."""

    def test_all_orphan_frame_raises(self) -> None:
        frame = _frame(orphans=500, joinable_populated=0, joinable_null=0)

        with pytest.raises(CascadeDenominatorCollapsedError) as excinfo:
            check_cascade_health(
                df=frame,
                entity_type="contact",
                schema=_make_schema(_CASCADE_COLUMNS),
                key_columns=_KEY_COLUMNS,
            )

        assert excinfo.value.total_rows == 500
        assert excinfo.value.orphan_rows == 500
        assert "contact" in str(excinfo.value)

    def test_collapse_does_not_report_healthy(self) -> None:
        """The negative side of C3: the `else 0.0` shortcut must NOT return.

        A guard of the form ``null_count / total if total > 0 else 0.0``
        would hand back max_null_rate=0.0 and healthy=True for a frame in
        which nothing can resolve at all.  That is the fake-health failure
        this condition exists to forbid.
        """
        frame = _frame(orphans=500, joinable_populated=0, joinable_null=0)

        try:
            result = check_cascade_health(
                df=frame,
                entity_type="contact",
                schema=_make_schema(_CASCADE_COLUMNS),
                key_columns=_KEY_COLUMNS,
            )
        except CascadeDenominatorCollapsedError:
            return  # refused, as required

        pytest.fail(f"collapse returned instead of raising: healthy={result.healthy}")

    def test_one_parented_row_is_enough_to_avoid_collapse(self) -> None:
        """Two-sided boundary: N=1 joinable computes, N=0 refuses."""
        frame = _frame(orphans=499, joinable_populated=1, joinable_null=0)

        result = check_cascade_health(
            df=frame,
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.joinable_rows == 1
        assert result.healthy is True

    def test_one_parented_null_row_is_a_full_fault_not_a_collapse(self) -> None:
        frame = _frame(orphans=499, joinable_populated=0, joinable_null=1)

        result = check_cascade_health(
            df=frame,
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.healthy is False
        assert result.max_null_rate == pytest.approx(1.0)

    def test_empty_frame_still_returns_healthy(self) -> None:
        """Collapse is about orphans, not emptiness.  An empty frame is
        handled by the pre-existing is_empty() guard and is unchanged."""
        empty = _frame(orphans=0, joinable_populated=0, joinable_null=0)

        result = check_cascade_health(
            df=empty,
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.healthy is True

    def test_collapse_does_not_fire_on_an_ungated_frame(self) -> None:
        """No cascade key column present -> nothing to refuse about."""
        frame = pl.DataFrame(
            {"gid": ["t1"], "parent_gid": [None]},
            schema={"gid": pl.Utf8, "parent_gid": pl.Utf8},
        )

        result = check_cascade_health(
            df=frame,
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )

        assert result.healthy is True

    def test_audit_reports_none_not_zero_on_collapse(self) -> None:
        """The audit is a log, not a gate -- but it must not fabricate 0.0."""
        frame = _frame(orphans=500, joinable_populated=0, joinable_null=0)

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=frame,
                entity_type="contact",
                project_gid="proj-1",
                schema=_make_schema(_CASCADE_COLUMNS),
                key_columns=_KEY_COLUMNS,
            )

        extra = mock_logger.error.call_args[1]["extra"]
        assert extra["denominator_collapsed"] is True
        assert extra["severity"] == "error"
        assert extra["cascade_key_nulls"]["office_phone"]["null_rate"] is None


# ---------------------------------------------------------------------------
# C4 -- scope fence: root entities are un-gated, read from the schema
# ---------------------------------------------------------------------------


class TestScopeFence:
    """RULING C4."""

    def test_business_declares_no_parent_mediated_cascade(self) -> None:
        """business.py's office_phone `source` is cf:, not cascade:.

        The line that says "cascades from Business" is a DESCRIPTION.  A
        reader who treats it as the source declaration would gate the root
        entity against its own cascade.
        """
        assert BUSINESS_SCHEMA.get_cascade_columns() == []
        assert BUSINESS_SCHEMA.has_cascade_columns() is False

        office_phone = next(c for c in BUSINESS_SCHEMA.columns if c.name == "office_phone")
        assert office_phone.source == "cf:Office Phone"
        assert "cascade" in (office_phone.description or "").lower()

    def test_contact_does_declare_one(self) -> None:
        """The other side of the fence, read from the same source of truth."""
        declared = dict(CONTACT_SCHEMA.get_cascade_columns())
        assert declared["office_phone"] == "Office Phone"
        assert declared["vertical"] == "Vertical"

    def test_root_entity_denominator_is_not_rescoped(self) -> None:
        """A blanket parent_gid filter would zero this and fail OPEN."""
        frame = _frame(orphans=1000, joinable_populated=0, joinable_null=0)

        denominator = resolve_cascade_denominator(frame, BUSINESS_SCHEMA.get_cascade_columns())

        assert denominator.rescoped is False
        assert denominator.joinable_rows == 1000, "root denominator is the full frame"
        assert denominator.orphan_rows == 0

    def test_root_entity_gate_does_not_collapse_on_an_unparented_frame(self) -> None:
        """The two-sided partner of test_all_orphan_frame_raises.

        The identical frame that REFUSES for a parent-mediated entity must
        pass for a root entity -- a root's rows are supposed to be unparented.
        """
        frame = _frame(orphans=500, joinable_populated=0, joinable_null=0)

        result = check_cascade_health(
            df=frame,
            entity_type="business",
            schema=BUSINESS_SCHEMA,
            key_columns=("office_phone",),
        )

        assert result.healthy is True
        assert result.denominator_rescoped is False

    def test_scope_is_read_from_schema_not_an_entity_name_list(self) -> None:
        """Entity name is diagnostic only; the declaration decides.

        Same entity_type string, two schemas, two scoping outcomes.  If the
        implementation ever grows a hardcoded {"contact", "offer", ...} set
        this test fails.
        """
        frame = _frame(**ORPHAN_HEAVY)

        as_declared = resolve_cascade_denominator(frame, CONTACT_SCHEMA.get_cascade_columns())
        as_root = resolve_cascade_denominator(frame, BUSINESS_SCHEMA.get_cascade_columns())

        assert as_declared.rescoped is True
        assert as_root.rescoped is False

    def test_frame_without_parent_gid_falls_back_to_full_frame(self) -> None:
        """Fallback can only make the gate stricter, never laxer."""
        frame = pl.DataFrame(
            {"office_phone": [None] * 30 + ["+15551230000"] * 70},
            schema={"office_phone": pl.Utf8},
        )

        denominator = resolve_cascade_denominator(frame, _CASCADE_COLUMNS)
        assert denominator.rescoped is False
        assert denominator.joinable_rows == 100

        result = check_cascade_health(
            df=frame,
            entity_type="contact",
            schema=_make_schema(_CASCADE_COLUMNS),
            key_columns=_KEY_COLUMNS,
        )
        assert result.healthy is False, "pre-rescope strictness is preserved without parent_gid"


# ---------------------------------------------------------------------------
# C5 -- the 0.20 threshold literal is untouched
# ---------------------------------------------------------------------------


class TestThresholdIsUntouched:
    """RULING C5."""

    def test_error_threshold_is_still_exactly_020(self) -> None:
        assert CASCADE_NULL_ERROR_THRESHOLD == 0.20

    def test_slack_disclosure_is_recorded_in_source(self) -> None:
        """C5 asks for the slack to be disclosed, not re-tuned.

        20% of the observed 8,846-row contact frame tolerates 1,769 rows
        against a projected ~273 true faults.  That note is for
        remediation-planner; this test keeps it from being quietly deleted
        alongside the threshold it qualifies.
        """
        source = Path(cascade_validator.__file__).read_text(encoding="utf-8")
        assert "THRESHOLD SLACK DISCLOSURE" in source
        assert "8,846" in source
        assert "1,769" in source

    def test_threshold_boundary_is_strictly_greater_than(self) -> None:
        """Exactly 20% of the parented rows null passes; just over fails."""
        at_threshold = _frame(orphans=100, joinable_populated=80, joinable_null=20)
        over_threshold = _frame(orphans=100, joinable_populated=79, joinable_null=21)

        schema = _make_schema(_CASCADE_COLUMNS)

        assert (
            check_cascade_health(
                df=at_threshold,
                entity_type="contact",
                schema=schema,
                key_columns=_KEY_COLUMNS,
            ).healthy
            is True
        )
        assert (
            check_cascade_health(
                df=over_threshold,
                entity_type="contact",
                schema=schema,
                key_columns=_KEY_COLUMNS,
            ).healthy
            is False
        )


# ---------------------------------------------------------------------------
# Service boundary -- collapse surfaces as an explicit refusal, not a 500
# ---------------------------------------------------------------------------


class TestCollapseTranslatesAtTheServiceBoundary:
    """C3's consequence at the edge the caller actually sees."""

    def _strategy(self) -> UniversalResolutionStrategy:
        return UniversalResolutionStrategy(
            entity_type="contact",
            index_cache=DynamicIndexCache(),
        )

    def test_collapse_becomes_cascade_not_ready(self) -> None:
        strategy = self._strategy()
        frame = _frame(orphans=500, joinable_populated=0, joinable_null=0)
        desc = MagicMock()
        desc.key_columns = _KEY_COLUMNS

        with (
            patch("autom8_asana.core.entity_registry.get_registry") as mock_reg,
            patch.object(
                strategy, "_get_entity_schema", return_value=_make_schema(_CASCADE_COLUMNS)
            ),
        ):
            mock_reg.return_value.get.return_value = desc

            with pytest.raises(CascadeNotReadyError) as excinfo:
                strategy._check_cascade_health(frame, "proj-1")

        assert isinstance(excinfo.value.__cause__, CascadeDenominatorCollapsedError)
        assert get_status_for_error(excinfo.value) == 503
        # parent_gid IS 100% null here -- the message must stay literally true.
        assert excinfo.value.degraded_columns == {"parent_gid": 1.0}

    def test_orphan_heavy_but_clean_frame_is_not_refused(self) -> None:
        """The other side: the gate must stop refusing the live shape."""
        strategy = self._strategy()
        frame = _frame(**ORPHAN_HEAVY)
        desc = MagicMock()
        desc.key_columns = _KEY_COLUMNS

        with (
            patch("autom8_asana.core.entity_registry.get_registry") as mock_reg,
            patch.object(
                strategy, "_get_entity_schema", return_value=_make_schema(_CASCADE_COLUMNS)
            ),
        ):
            mock_reg.return_value.get.return_value = desc
            strategy._check_cascade_health(frame, "proj-1")

    async def test_index_build_proceeds_on_an_orphan_heavy_frame(self) -> None:
        """End-to-end at the resolution seam: 62% orphaned no longer 503s."""
        strategy = self._strategy()
        frame = _frame(**ORPHAN_HEAVY)
        strategy._get_dataframe = AsyncMock(return_value=frame)
        desc = MagicMock()
        desc.key_columns = _KEY_COLUMNS

        with (
            patch("autom8_asana.core.entity_registry.get_registry") as mock_reg,
            patch.object(
                strategy, "_get_entity_schema", return_value=_make_schema(_CASCADE_COLUMNS)
            ),
        ):
            mock_reg.return_value.get.return_value = desc

            index = await strategy._get_or_build_index(
                project_gid="proj-1",
                key_columns=["office_phone"],
                client=MagicMock(),
            )

        assert index is not None
