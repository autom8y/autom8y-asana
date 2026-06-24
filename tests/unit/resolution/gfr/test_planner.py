"""Tests for the GFR planner (TDD §5, §9.3 planner.py row).

The planner is pure/synchronous. These tests verify hop classification
(offer->Business is PARENT_CHAIN, not in-frame; business is LOCAL; unit/contact
are IN_FRAME_PARENT) and the all-or-nothing unknown-field failure (INVARIANT I4).
"""

from __future__ import annotations

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.resolution.gfr.errors import UnresolvedError
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

    def test_unknown_field_raises_all_or_nothing(self) -> None:
        with pytest.raises(UnresolvedError) as exc:
            plan_resolution(EntityType.OFFER, ["company_id", "not_a_field"])
        assert exc.value.reason == "unknown-field"
        assert "not_a_field" in exc.value.fields
        # All-or-nothing: the whole call fails even though company_id is valid.

    def test_multiple_unknown_fields_all_reported(self) -> None:
        with pytest.raises(UnresolvedError) as exc:
            plan_resolution(EntityType.OFFER, ["nope1", "nope2"])
        assert set(exc.value.fields) == {"nope1", "nope2"}
