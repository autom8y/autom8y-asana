"""Tests for the GFR planner (TDD §5, §9.3 planner.py row).

The planner is pure/synchronous. These tests verify hop classification
(offer->Business is PARENT_CHAIN, not in-frame; business is LOCAL; unit/contact
are IN_FRAME_PARENT) and the all-or-nothing unknown-field failure (INVARIANT I4).
"""

from __future__ import annotations

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.resolution.gfr.models import HopClass
from autom8_asana.resolution.gfr.planner import (
    IDENTITY_FIELDS,
    _classify_hop,
    _owning_entity,
    plan_resolution,
)

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]


class TestOwningEntity:
    def test_company_id_owned_by_business_only(self) -> None:
        assert _owning_entity("company_id") == "business"

    def test_unknown_field_has_no_owner(self) -> None:
        assert _owning_entity("definitely_not_a_real_field") is None

    def test_identity_fields_constant(self) -> None:
        assert "company_id" in IDENTITY_FIELDS


class TestClassifyHop:
    def test_offer_to_business_is_parent_chain(self) -> None:
        # TDD §5.2: offer's in-frame parent_gid points at OfferHolder, not
        # Business; the only collision-free path is the live parent chain.
        assert _classify_hop(EntityType.OFFER, "business") is HopClass.PARENT_CHAIN

    def test_business_to_business_is_local(self) -> None:
        assert _classify_hop(EntityType.BUSINESS, "business") is HopClass.LOCAL

    def test_unit_to_business_is_in_frame_parent(self) -> None:
        assert _classify_hop(EntityType.UNIT, "business") is HopClass.IN_FRAME_PARENT

    def test_contact_to_business_is_in_frame_parent(self) -> None:
        assert _classify_hop(EntityType.CONTACT, "business") is HopClass.IN_FRAME_PARENT

    def test_asset_edit_to_business_is_in_frame_parent(self) -> None:
        assert _classify_hop(EntityType.ASSET_EDIT, "business") is HopClass.IN_FRAME_PARENT


class TestPlanResolution:
    def test_offer_company_id_plan_is_identity_parent_chain(self) -> None:
        plan = plan_resolution(EntityType.OFFER, ["company_id"])
        assert plan.entry_entity_type == "offer"
        assert len(plan.field_plans) == 1
        fp = plan.field_plans[0]
        assert fp.owner == "business"
        assert fp.fields == ["company_id"]
        assert fp.hop is HopClass.PARENT_CHAIN
        assert fp.is_identity is True
        assert plan.identity_plans == [fp]

    def test_business_company_id_plan_is_local(self) -> None:
        plan = plan_resolution(EntityType.BUSINESS, ["company_id"])
        fp = plan.field_plans[0]
        assert fp.hop is HopClass.LOCAL
        assert fp.is_identity is True

    def test_non_schema_field_routed_to_dynamic(self) -> None:
        """D-T1a: a no-schema-owner field partitions to ``dynamic_fields``.

        The planner no longer raises ``unknown-field`` at plan time for a field with
        no resolvable schema owner — it is manifest-blind and cannot pre-judge
        absence. It routes the field to ``ResolutionPlan.dynamic_fields`` and defers
        the absent/present verdict to the tail (governed-strict, manifest-aware).
        The schema-owned field is still planned normally in the same call.
        """
        plan = plan_resolution(EntityType.OFFER, ["company_id", "not_a_field"])
        # company_id is still planned as an identity field (path untouched).
        assert len(plan.field_plans) == 1
        assert plan.field_plans[0].is_identity is True
        # The no-schema field is partitioned, NOT raised on.
        assert plan.dynamic_fields == ["not_a_field"]

    def test_schema_field_still_planned_normally(self) -> None:
        """A schema field still produces its ``FieldPlan``; ``dynamic_fields`` empty."""
        plan = plan_resolution(EntityType.OFFER, ["company_id"])
        assert len(plan.field_plans) == 1
        assert plan.field_plans[0].fields == ["company_id"]
        assert plan.dynamic_fields == []

    def test_multiple_non_schema_fields_all_routed_to_dynamic(self) -> None:
        """Multiple no-schema fields all partition to ``dynamic_fields`` (D-T1a)."""
        plan = plan_resolution(EntityType.OFFER, ["nope1", "nope2"])
        assert plan.field_plans == []
        assert set(plan.dynamic_fields) == {"nope1", "nope2"}

    def test_plan_dynamic_fields_defaults_empty(self) -> None:
        """``dynamic_fields`` is additive with a default empty list (additivity)."""
        plan = plan_resolution(EntityType.BUSINESS, ["company_id"])
        assert plan.dynamic_fields == []


class TestOptionAEntryScopedOwnership:
    """Option A (ADR-gfr-dynvocab-tail-scope, PT-02): the non-identity owner test
    is narrowed from "owned by ANY resolvable schema" to "owned by the ENTRY
    entity's OWN schema". Foreign-schema ownership (asset_edit owning asset_id) no
    longer suppresses tail routing for an Offer entry. The identity carve-out
    (company_id -> Business, is_identity=True) is unchanged.
    """

    def test_asset_id_for_offer_routes_to_dynamic_tail(self) -> None:
        """asset_id is foreign-owned (asset_edit) but ABSENT from Offer's own schema.

        Under Option A it must route to ``dynamic_fields`` (the tail), NOT to an
        un-executed ``FieldPlan(owner='asset_edit')``. This is the worked-example
        fork the ADR resolves: the old global owner test mis-routed asset_id to a
        foreign schema and it was silently dropped (QA F-2).
        """
        plan = plan_resolution(EntityType.OFFER, ["asset_id"])
        assert plan.dynamic_fields == ["asset_id"]
        # No foreign-schema FieldPlan is produced for asset_id.
        assert plan.field_plans == []
        assert plan.identity_plans == []

    def test_own_schema_non_identity_field_still_schema_routed(self) -> None:
        """office_phone IS on the Offer's own schema -> still schema-routed, NOT the tail.

        A field the entry entity's own schema declares keeps the old routing: it
        produces a non-identity ``FieldPlan`` and does NOT enter ``dynamic_fields``.
        This is what keeps test_engine.py::test_no_identity_path_when_no_identity_
        field_requested GREEN (office_phone -> no-identity-path, unchanged).
        """
        plan = plan_resolution(EntityType.OFFER, ["office_phone"])
        assert plan.dynamic_fields == []
        assert len(plan.field_plans) == 1
        fp = plan.field_plans[0]
        assert fp.owner == "offer"
        assert fp.is_identity is False
        assert "office_phone" in fp.fields

    def test_company_id_identity_carveout_unchanged_for_offer(self) -> None:
        """company_id is Business-owned (NOT Offer-owned) yet MUST stay is_identity.

        The identity carve-out is checked before the entry-scoped fallthrough; the
        Option A narrowing touches only the NON-identity owner branch.
        """
        plan = plan_resolution(EntityType.OFFER, ["company_id"])
        assert plan.dynamic_fields == []
        assert len(plan.field_plans) == 1
        fp = plan.field_plans[0]
        assert fp.owner == "business"
        assert fp.is_identity is True
        assert fp.hop is HopClass.PARENT_CHAIN

    def test_mixed_company_id_and_asset_id_partitions_both(self) -> None:
        """The mixed case (F-2 closed): company_id -> identity plan, asset_id -> tail."""
        plan = plan_resolution(EntityType.OFFER, ["company_id", "asset_id"])
        assert plan.dynamic_fields == ["asset_id"]
        assert len(plan.field_plans) == 1
        assert plan.field_plans[0].is_identity is True
        assert plan.field_plans[0].owner == "business"

    def test_genuine_absence_still_routes_to_tail(self) -> None:
        """A field on NO schema at all still routes to the tail (genuine-absence)."""
        plan = plan_resolution(EntityType.OFFER, ["totally_made_up"])
        assert plan.dynamic_fields == ["totally_made_up"]
        assert plan.field_plans == []

    def test_business_entry_own_field_schema_routed(self) -> None:
        """For a Business entry, a Business-owned non-identity field stays schema-routed.

        Entry-scoped ownership is relative to the ENTRY entity: office_phone is on
        the Business schema, so for a Business entry it is own-schema and not routed
        to the tail (it is a non-identity own-schema field, the residual no-executor
        case the ADR leaves for the Option-D harden-on-touch).
        """
        plan = plan_resolution(EntityType.BUSINESS, ["office_phone"])
        assert plan.dynamic_fields == []
        assert len(plan.field_plans) == 1
        assert plan.field_plans[0].owner == "business"
        assert plan.field_plans[0].is_identity is False
