"""Tests for dataframes.cascade_utils dynamic derivation primitives."""

from __future__ import annotations

import pytest

from autom8_asana.dataframes.cascade_utils import (
    cascade_provider_field_mapping,
    cascade_warm_order,
    cascade_warm_phases,
    is_cascade_provider,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

# ---------------------------------------------------------------------------
# DataFrameSchema.get_cascade_columns()  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestGetCascadeColumns:
    """Tests for the get_cascade_columns() schema method."""

    def test_unit_schema_returns_two_cascade_columns(self) -> None:
        from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

        cols = UNIT_SCHEMA.get_cascade_columns()
        names = {c[0] for c in cols}
        assert "office" in names
        assert "office_phone" in names
        assert len(cols) == 2

    def test_business_schema_returns_empty(self) -> None:
        from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA

        assert BUSINESS_SCHEMA.get_cascade_columns() == []

    def test_offer_schema_returns_five_cascade_columns(self) -> None:
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        cols = OFFER_SCHEMA.get_cascade_columns()
        assert len(cols) == 5
        field_names = {c[1] for c in cols}
        assert field_names == {
            "Business Name",
            "Office Phone",
            "Vertical",
            "MRR",
            "Weekly Ad Spend",
        }

    def test_contact_schema_returns_two_cascade_columns(self) -> None:
        from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA

        cols = CONTACT_SCHEMA.get_cascade_columns()
        assert len(cols) == 2
        field_names = {c[1] for c in cols}
        assert field_names == {"Office Phone", "Vertical"}

    def test_synthetic_schema_parses_prefix(self) -> None:
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef(name="gid", dtype="Utf8"),
                ColumnDef(name="phone", dtype="Utf8", source="cascade:Office Phone"),
                ColumnDef(name="city", dtype="Utf8", source="cf:City"),
            ],
        )
        assert schema.get_cascade_columns() == [("phone", "Office Phone")]

    def test_case_insensitive_prefix(self) -> None:
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef(name="x", dtype="Utf8", source="Cascade:Foo Bar"),
            ],
        )
        assert schema.get_cascade_columns() == [("x", "Foo Bar")]


# ---------------------------------------------------------------------------
# is_cascade_provider()  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestIsCascadeProvider:
    def test_business_is_provider(self) -> None:
        assert is_cascade_provider("business") is True

    def test_unit_is_provider(self) -> None:
        assert is_cascade_provider("unit") is True

    def test_offer_is_not_provider(self) -> None:
        assert is_cascade_provider("offer") is False

    def test_contact_is_not_provider(self) -> None:
        assert is_cascade_provider("contact") is False

    def test_asset_edit_is_not_provider(self) -> None:
        assert is_cascade_provider("asset_edit") is False

    def test_nonexistent_entity_is_not_provider(self) -> None:
        assert is_cascade_provider("nonexistent") is False


# ---------------------------------------------------------------------------
# cascade_provider_field_mapping()  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestCascadeProviderFieldMapping:
    def test_business_mapping_includes_office_phone(self) -> None:
        mapping = cascade_provider_field_mapping("business")
        assert mapping["office_phone"] == "Office Phone"

    def test_business_mapping_includes_company_id(self) -> None:
        mapping = cascade_provider_field_mapping("business")
        assert mapping["company_id"] == "Company ID"

    def test_business_mapping_includes_business_name(self) -> None:
        """Business Name cascades via source_field='name'."""
        mapping = cascade_provider_field_mapping("business")
        assert mapping["name"] == "Business Name"

    def test_unit_mapping_includes_mrr(self) -> None:
        mapping = cascade_provider_field_mapping("unit")
        assert mapping["mrr"] == "MRR"

    def test_unit_mapping_includes_weekly_ad_spend(self) -> None:
        mapping = cascade_provider_field_mapping("unit")
        assert mapping["weekly_ad_spend"] == "Weekly Ad Spend"

    def test_unit_mapping_includes_vertical(self) -> None:
        mapping = cascade_provider_field_mapping("unit")
        assert mapping["vertical"] == "Vertical"

    def test_offer_returns_empty(self) -> None:
        assert cascade_provider_field_mapping("offer") == {}

    def test_nonexistent_returns_empty(self) -> None:
        assert cascade_provider_field_mapping("nonexistent") == {}


# ---------------------------------------------------------------------------
# cascade_warm_phases()  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestCascadeWarmPhases:
    def test_returns_at_least_two_phases(self) -> None:
        phases = cascade_warm_phases()
        assert len(phases) >= 2

    def test_business_in_first_phase(self) -> None:
        phases = cascade_warm_phases()
        assert "business" in phases[0]

    def test_unit_not_in_first_phase(self) -> None:
        """Unit depends on Business, so cannot be in phase 0."""
        phases = cascade_warm_phases()
        assert "unit" not in phases[0]

    def test_unit_before_offer(self) -> None:
        """Offer depends on Unit (MRR, Vertical), so Unit must come first."""
        order = cascade_warm_order()
        assert order.index("unit") < order.index("offer")

    def test_business_before_unit(self) -> None:
        """Unit depends on Business (Office Phone), so Business must come first."""
        order = cascade_warm_order()
        assert order.index("business") < order.index("unit")

    def test_business_before_contact(self) -> None:
        order = cascade_warm_order()
        assert order.index("business") < order.index("contact")

    def test_includes_all_warmable_entities(self) -> None:
        """No warmable entity dropped from the ordering."""
        from autom8_asana.core.entity_registry import get_registry

        warmable = {d.name for d in get_registry().warmable_entities()}
        ordered = set(cascade_warm_order())
        assert warmable == ordered


# ---------------------------------------------------------------------------
# cascade_warm_order()  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestCascadeWarmOrder:
    def test_flat_order_starts_with_business(self) -> None:
        order = cascade_warm_order()
        assert order[0] == "business"

    def test_flat_order_is_consistent(self) -> None:
        """Multiple calls return the same order."""
        assert cascade_warm_order() == cascade_warm_order()
