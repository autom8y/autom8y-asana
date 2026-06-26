"""Tests for GFR result/plan models (TDD §3.2, §9.3 models.py row).

Covers extra="forbid" rejection and the row-set-native .scalar() semantics
(INVARIANT I5).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.resolution.gfr.errors import AmbiguousCardinalityError
from autom8_asana.resolution.gfr.models import (
    FieldPlan,
    FieldStatus,
    FieldWithProvenance,
    HopClass,
    ResolutionPlan,
    ResolvedFields,
    TruthTier,
)


def _fwp(value: object = "G_A") -> FieldWithProvenance:
    return FieldWithProvenance(value=value, status=FieldStatus.FRESH, source=TruthTier.CACHE)


class TestFieldWithProvenance:
    def test_extra_forbid_rejects_unknown_key(self) -> None:
        with pytest.raises(ValidationError):
            FieldWithProvenance(
                value="x",
                status=FieldStatus.FRESH,
                source=TruthTier.CACHE,
                bogus="nope",  # type: ignore[call-arg]
            )

    def test_as_of_optional_defaults_none(self) -> None:
        fwp = _fwp()
        assert fwp.as_of is None
        assert fwp.status is FieldStatus.FRESH
        assert fwp.source is TruthTier.CACHE


class TestResolvedFieldsScalar:
    def test_scalar_returns_single_row(self) -> None:
        rf = ResolvedFields(gid="g1", rows=[{"company_id": _fwp()}], row_count=1)
        row = rf.scalar()
        assert row["company_id"].value == "G_A"

    def test_scalar_raises_on_multiple_rows(self) -> None:
        rf = ResolvedFields(
            gid="g1",
            rows=[{"company_id": _fwp("A")}, {"company_id": _fwp("B")}],
            row_count=2,
        )
        with pytest.raises(AmbiguousCardinalityError) as exc:
            rf.scalar()
        assert exc.value.row_count == 2

    def test_scalar_raises_on_zero_rows(self) -> None:
        rf = ResolvedFields(gid="g1", rows=[], row_count=0)
        with pytest.raises(AmbiguousCardinalityError) as exc:
            rf.scalar()
        assert exc.value.row_count == 0

    def test_extra_forbid_on_resolved_fields(self) -> None:
        with pytest.raises(ValidationError):
            ResolvedFields(gid="g", rows=[], row_count=0, extra="x")  # type: ignore[call-arg]


class TestResolutionPlan:
    def test_identity_plans_filters_identity(self) -> None:
        plan = ResolutionPlan(
            entry_entity_type="offer",
            field_plans=[
                FieldPlan(
                    owner="business",
                    fields=["company_id"],
                    hop=HopClass.PARENT_CHAIN,
                    is_identity=True,
                ),
                FieldPlan(
                    owner="offer",
                    fields=["mrr"],
                    hop=HopClass.LOCAL,
                    is_identity=False,
                ),
            ],
        )
        ident = plan.identity_plans
        assert len(ident) == 1
        assert ident[0].owner == "business"
        assert ident[0].fields == ["company_id"]

    def test_field_plan_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            FieldPlan(owner="business", fields=["x"], hop=HopClass.LOCAL, junk=1)  # type: ignore[call-arg]


class TestEnums:
    def test_field_status_has_no_unresolved_member(self) -> None:
        # INVARIANT I4: unresolved fields raise UnresolvedError, never a status.
        members = {m.value for m in FieldStatus}
        assert members == {"fresh", "stale"}

    def test_truth_tier_values(self) -> None:
        assert TruthTier.CACHE.value == "asana-cache"
        assert TruthTier.VERIFIED.value == "data-verified"

    def test_hop_class_values(self) -> None:
        assert {m.value for m in HopClass} == {"local", "in-frame", "parent-chain"}
