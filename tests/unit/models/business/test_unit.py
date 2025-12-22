"""Tests for Unit and UnitHolder models.

Per TDD-BIZMODEL: Tests for Unit entity with nested holders and 31 typed fields.
"""

from __future__ import annotations

from decimal import Decimal


from autom8_asana.models.business.unit import Unit, UnitHolder
from autom8_asana.models.business.offer import Offer, OfferHolder
from autom8_asana.models.business.process import Process, ProcessHolder
from autom8_asana.models.task import Task


class TestUnit:
    """Tests for Unit model."""

    def test_unit_inherits_from_task(self) -> None:
        """Unit inherits from Task and can be constructed."""
        unit = Unit(gid="123", name="Retail Unit")
        assert unit.gid == "123"
        assert unit.name == "Retail Unit"

    def test_unit_has_holder_key_map(self) -> None:
        """Unit has HOLDER_KEY_MAP for nested holders."""
        assert "offer_holder" in Unit.HOLDER_KEY_MAP
        assert "process_holder" in Unit.HOLDER_KEY_MAP
        assert Unit.HOLDER_KEY_MAP["offer_holder"] == ("Offers", "gift")
        assert Unit.HOLDER_KEY_MAP["process_holder"] == ("Processes", "gear")


class TestUnitNestedHolders:
    """Tests for Unit nested holder properties."""

    def test_offer_holder_property(self) -> None:
        """offer_holder returns cached reference."""
        unit = Unit(gid="123")
        holder = OfferHolder(gid="456")
        unit._offer_holder = holder
        assert unit.offer_holder is holder

    def test_process_holder_property(self) -> None:
        """process_holder returns cached reference."""
        unit = Unit(gid="123")
        holder = ProcessHolder(gid="456")
        unit._process_holder = holder
        assert unit.process_holder is holder

    def test_offers_property_empty(self) -> None:
        """offers returns empty list when holder not populated."""
        unit = Unit(gid="123")
        assert unit.offers == []

    def test_offers_property_populated(self) -> None:
        """offers returns populated list from holder."""
        unit = Unit(gid="123")
        holder = OfferHolder(gid="456")
        holder._offers = [
            Offer(gid="o1", name="Offer 1"),
            Offer(gid="o2", name="Offer 2"),
        ]
        unit._offer_holder = holder
        assert len(unit.offers) == 2
        assert unit.offers[0].name == "Offer 1"

    def test_active_offers_filters_by_has_active_ads(self) -> None:
        """active_offers returns only offers with active ads."""
        unit = Unit(gid="123")
        holder = OfferHolder(gid="456")

        # Active offer (has ad_id)
        active_offer = Offer(
            gid="o1",
            name="Active Offer",
            custom_fields=[{"gid": "1", "name": "Ad ID", "text_value": "123"}],
        )
        # Inactive offer (no ad markers)
        inactive_offer = Offer(gid="o2", name="Inactive Offer", custom_fields=[])

        holder._offers = [active_offer, inactive_offer]
        unit._offer_holder = holder

        active_offers = unit.active_offers
        assert len(active_offers) == 1
        assert active_offers[0].name == "Active Offer"

    def test_processes_property_empty(self) -> None:
        """processes returns empty list when holder not populated."""
        unit = Unit(gid="123")
        assert unit.processes == []

    def test_processes_property_populated(self) -> None:
        """processes returns populated list from holder."""
        unit = Unit(gid="123")
        holder = ProcessHolder(gid="456")
        holder._processes = [
            Process(gid="p1", name="Process 1"),
            Process(gid="p2", name="Process 2"),
        ]
        unit._process_holder = holder
        assert len(unit.processes) == 2


class TestUnitNavigation:
    """Tests for Unit navigation properties."""

    def test_unit_holder_property(self) -> None:
        """unit_holder returns cached reference."""
        unit = Unit(gid="123")
        holder = UnitHolder(gid="456")
        unit._unit_holder = holder
        assert unit.unit_holder is holder

    def test_business_navigation_via_holder(self) -> None:
        """business property navigates via unit_holder."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="b1", name="Test Business")
        holder = UnitHolder(gid="h1")
        holder._business = business

        unit = Unit(gid="u1")
        unit._unit_holder = holder

        assert unit.business is business

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        unit = Unit(gid="123")
        unit._business = object()  # type: ignore
        unit._unit_holder = UnitHolder(gid="456")
        unit._offer_holder = OfferHolder(gid="789")
        unit._process_holder = ProcessHolder(gid="012")

        unit._invalidate_refs()

        assert unit._business is None
        assert unit._unit_holder is None
        assert unit._offer_holder is None
        assert unit._process_holder is None


class TestUnitCascadingFields:
    """Tests for Unit cascading field definitions."""

    def test_cascading_fields_all(self) -> None:
        """CascadingFields.all() returns all definitions."""
        all_fields = Unit.CascadingFields.all()
        assert len(all_fields) == 3
        names = [f.name for f in all_fields]
        assert "Platforms" in names
        assert "Vertical" in names
        assert "Booking Type" in names

    def test_cascading_fields_get(self) -> None:
        """CascadingFields.get() returns field by name."""
        platforms = Unit.CascadingFields.get("Platforms")
        assert platforms is not None
        assert platforms.name == "Platforms"
        assert platforms.allow_override is True

        vertical = Unit.CascadingFields.get("Vertical")
        assert vertical is not None
        assert vertical.allow_override is False  # DEFAULT

    def test_cascading_fields_get_nonexistent(self) -> None:
        """CascadingFields.get() returns None for unknown field."""
        assert Unit.CascadingFields.get("Nonexistent") is None


class TestUnitInheritedFields:
    """Tests for Unit inherited field definitions."""

    def test_inherited_fields_all(self) -> None:
        """InheritedFields.all() returns all definitions."""
        all_fields = Unit.InheritedFields.all()
        assert len(all_fields) == 1
        assert all_fields[0].name == "Default Vertical"

    def test_default_vertical_inherited_from_business(self) -> None:
        """DEFAULT_VERTICAL inherits from Business."""
        default_vertical = Unit.InheritedFields.DEFAULT_VERTICAL
        assert "Business" in default_vertical.inherit_from
        assert default_vertical.allow_override is True
        assert default_vertical.default == "General"


class TestUnitCustomFields:
    """Tests for Unit custom field accessors."""

    # --- Financial Fields ---

    def test_mrr_getter(self) -> None:
        """mrr getter returns Decimal value."""
        unit = Unit(
            gid="123",
            custom_fields=[{"gid": "1", "name": "MRR", "number_value": 5000.50}],
        )
        assert unit.mrr == Decimal("5000.50")

    def test_mrr_setter(self) -> None:
        """mrr setter updates value."""
        unit = Unit(gid="123", custom_fields=[])
        unit.mrr = Decimal("6000")
        assert unit.get_custom_fields().get("MRR") == 6000.0

    def test_mrr_none(self) -> None:
        """mrr returns None when not set."""
        unit = Unit(gid="123", custom_fields=[])
        assert unit.mrr is None

    def test_weekly_ad_spend(self) -> None:
        """weekly_ad_spend getter/setter works."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Weekly Ad Spend", "number_value": 1200.00}
            ],
        )
        assert unit.weekly_ad_spend == Decimal("1200.00")

    def test_discount(self) -> None:
        """discount getter returns enum value per PRD-0024."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Discount", "enum_value": {"name": "10%"}}
            ],
        )
        assert unit.discount == "10%"

    def test_meta_spend(self) -> None:
        """meta_spend getter/setter works."""
        unit = Unit(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Meta Spend", "number_value": 500.00}],
        )
        assert unit.meta_spend == Decimal("500.00")

    def test_tiktok_spend(self) -> None:
        """tiktok_spend getter/setter works."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Tiktok Spend", "number_value": 300.00}
            ],
        )
        assert unit.tiktok_spend == Decimal("300.00")

    # --- Platform Fields ---

    def test_ad_account_id(self) -> None:
        """ad_account_id getter/setter works."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Ad Account ID", "text_value": "ACC123"}
            ],
        )
        assert unit.ad_account_id == "ACC123"

    def test_platforms_multi_enum(self) -> None:
        """platforms returns list from multi-enum field."""
        unit = Unit(gid="123", custom_fields=[])
        # Use set() method to properly add multi-value fields
        unit.get_custom_fields().set(
            "Platforms",
            [
                {"gid": "e1", "name": "Google"},
                {"gid": "e2", "name": "Meta"},
            ],
        )
        assert unit.platforms == ["Google", "Meta"]

    def test_platforms_empty(self) -> None:
        """platforms returns empty list when not set."""
        unit = Unit(gid="123", custom_fields=[])
        assert unit.platforms == []

    # --- Product/Service Fields ---

    def test_vertical_enum(self) -> None:
        """vertical extracts name from enum dict."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Retail"}}
            ],
        )
        assert unit.vertical == "Retail"

    def test_specialty_multi_enum(self) -> None:
        """specialty returns list from multi-enum per PRD-0024."""
        unit = Unit(gid="123", custom_fields=[])
        unit.get_custom_fields().set(
            "Specialty",
            [
                {"gid": "s1", "name": "Dental"},
                {"gid": "s2", "name": "Chiro"},
            ],
        )
        assert unit.specialty == ["Dental", "Chiro"]

    def test_specialty_empty(self) -> None:
        """specialty returns empty list when not set."""
        unit = Unit(gid="123", custom_fields=[])
        assert unit.specialty == []

    def test_products_multi_enum(self) -> None:
        """products returns list from multi-enum field."""
        unit = Unit(gid="123", custom_fields=[])
        unit.get_custom_fields().set(
            "Products",
            [
                {"gid": "p1", "name": "Product A"},
                {"gid": "p2", "name": "Product B"},
            ],
        )
        assert unit.products == ["Product A", "Product B"]

    def test_languages_multi_enum(self) -> None:
        """languages returns list from multi-enum field."""
        unit = Unit(gid="123", custom_fields=[])
        unit.get_custom_fields().set(
            "Languages",
            [
                {"gid": "l1", "name": "English"},
                {"gid": "l2", "name": "Spanish"},
            ],
        )
        assert unit.languages == ["English", "Spanish"]

    # --- Demographics Fields ---

    def test_radius_int(self) -> None:
        """radius returns integer value."""
        unit = Unit(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Radius", "number_value": 25}],
        )
        assert unit.radius == 25

    def test_min_age(self) -> None:
        """min_age returns integer value."""
        unit = Unit(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Min Age", "number_value": 18}],
        )
        assert unit.min_age == 18

    def test_max_age(self) -> None:
        """max_age returns integer value."""
        unit = Unit(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Max Age", "number_value": 65}],
        )
        assert unit.max_age == 65

    def test_gender_multi_enum(self) -> None:
        """gender returns list from multi-enum per PRD-0024."""
        unit = Unit(gid="123", custom_fields=[])
        unit.get_custom_fields().set(
            "Gender",
            [
                {"gid": "g1", "name": "Female"},
                {"gid": "g2", "name": "Male"},
            ],
        )
        assert unit.gender == ["Female", "Male"]

    def test_gender_empty(self) -> None:
        """gender returns empty list when not set."""
        unit = Unit(gid="123", custom_fields=[])
        assert unit.gender == []

    def test_booking_type_enum(self) -> None:
        """booking_type extracts name from enum dict."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Booking Type", "enum_value": {"name": "Calendar"}}
            ],
        )
        assert unit.booking_type == "Calendar"

    # --- Form Settings Fields ---

    def test_form_questions_multi_enum(self) -> None:
        """form_questions returns list from multi-enum per PRD-0024."""
        unit = Unit(gid="123", custom_fields=[])
        unit.get_custom_fields().set(
            "Form Questions",
            [
                {"gid": "q1", "name": "Name"},
                {"gid": "q2", "name": "Email"},
                {"gid": "q3", "name": "Phone"},
            ],
        )
        assert unit.form_questions == ["Name", "Email", "Phone"]

    def test_form_questions_empty(self) -> None:
        """form_questions returns empty list when not set."""
        unit = Unit(gid="123", custom_fields=[])
        assert unit.form_questions == []

    def test_zip_codes_radius_int(self) -> None:
        """zip_codes_radius returns int per PRD-0024."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Zip Codes Radius", "number_value": 25}
            ],
        )
        assert unit.zip_codes_radius == 25

    def test_internal_notes(self) -> None:
        """internal_notes getter works per PRD-0024."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Internal Notes", "text_value": "Some notes here"}
            ],
        )
        assert unit.internal_notes == "Some notes here"

    def test_sms_lead_verification(self) -> None:
        """sms_lead_verification getter/setter works."""
        unit = Unit(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Sms Lead Verification",
                    "enum_value": {"name": "Enabled"},
                }
            ],
        )
        assert unit.sms_lead_verification == "Enabled"


class TestUnitPopulateHolders:
    """Tests for Unit._populate_holders method."""

    def test_populate_holders_identifies_offer_holder(self) -> None:
        """_populate_holders creates OfferHolder from matching subtask."""
        unit = Unit(gid="u1")
        subtasks = [Task(gid="h1", name="Offers")]
        unit._populate_holders(subtasks)

        assert unit._offer_holder is not None
        assert isinstance(unit._offer_holder, OfferHolder)
        assert unit._offer_holder._unit is unit

    def test_populate_holders_identifies_process_holder(self) -> None:
        """_populate_holders creates ProcessHolder from matching subtask."""
        unit = Unit(gid="u1")
        subtasks = [Task(gid="h1", name="Processes")]
        unit._populate_holders(subtasks)

        assert unit._process_holder is not None
        assert isinstance(unit._process_holder, ProcessHolder)
        assert unit._process_holder._unit is unit

    def test_populate_holders_ignores_non_holders(self) -> None:
        """_populate_holders ignores non-holder subtasks."""
        unit = Unit(gid="u1")
        subtasks = [Task(gid="t1", name="Random Task")]
        unit._populate_holders(subtasks)

        assert unit._offer_holder is None
        assert unit._process_holder is None


class TestUnitHolder:
    """Tests for UnitHolder model."""

    def test_units_property_empty(self) -> None:
        """units returns empty list by default."""
        holder = UnitHolder(gid="123")
        assert holder.units == []

    def test_units_property_populated(self) -> None:
        """units returns populated list."""
        holder = UnitHolder(gid="123")
        holder._units = [
            Unit(gid="u1", name="Unit 1"),
            Unit(gid="u2", name="Unit 2"),
        ]
        assert len(holder.units) == 2
        assert holder.units[0].name == "Unit 1"

    def test_business_property(self) -> None:
        """business returns cached reference."""
        from autom8_asana.models.business.business import Business

        holder = UnitHolder(gid="123")
        business = Business(gid="b1")
        holder._business = business
        assert holder.business is business

    def test_populate_children(self) -> None:
        """_populate_children converts Tasks to Units."""
        holder = UnitHolder(gid="123")
        subtasks = [
            Task(gid="u1", name="Unit 1", created_at="2024-01-01T00:00:00Z"),
            Task(gid="u2", name="Unit 2", created_at="2024-01-02T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        assert len(holder.units) == 2
        assert all(isinstance(u, Unit) for u in holder.units)
        # Sorted by created_at
        assert holder.units[0].name == "Unit 1"
        assert holder.units[1].name == "Unit 2"

    def test_populate_children_sets_back_references(self) -> None:
        """_populate_children sets back references on units."""
        from autom8_asana.models.business.business import Business

        holder = UnitHolder(gid="123")
        business = Business(gid="b1")
        holder._business = business

        subtasks = [Task(gid="u1", name="Unit 1")]
        holder._populate_children(subtasks)

        assert holder.units[0]._unit_holder is holder
        assert holder.units[0]._business is business

    def test_invalidate_cache(self) -> None:
        """invalidate_cache clears units list."""
        holder = UnitHolder(gid="123")
        holder._units = [Unit(gid="u1")]
        holder.invalidate_cache()
        assert holder._units == []
