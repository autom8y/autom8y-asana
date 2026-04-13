"""Tests for Offer and OfferHolder models.

Per TDD-BIZMODEL: Tests for Offer entity with 39 typed fields and ad status.
"""

from __future__ import annotations

from decimal import Decimal

from autom8_asana.models.business.offer import Offer, OfferHolder
from autom8_asana.models.business.unit import Unit, UnitHolder
from autom8_asana.models.task import Task


class TestOffer:
    """Tests for Offer model."""

    def test_offer_inherits_from_task(self) -> None:
        """Offer inherits from Task and can be constructed."""
        offer = Offer(gid="123", name="Summer Promo")
        assert offer.gid == "123"
        assert offer.name == "Summer Promo"


class TestOfferAdStatus:
    """Tests for Offer ad status determination."""

    def test_has_active_ads_true_with_ad_id(self) -> None:
        """has_active_ads returns True when ad_id is set."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Ad ID", "text_value": "ad123"}],
        )
        assert offer.has_active_ads is True

    def test_has_active_ads_true_with_active_ads_url(self) -> None:
        """has_active_ads returns True when active_ads_url is set."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Active Ads URL",
                    "text_value": "https://fb.com/ads/123",
                }
            ],
        )
        assert offer.has_active_ads is True

    def test_has_active_ads_false_when_neither(self) -> None:
        """has_active_ads returns False when no ad markers."""
        offer = Offer(gid="123", custom_fields=[])
        assert offer.has_active_ads is False


class TestOfferNavigation:
    """Tests for Offer navigation properties."""

    def test_offer_holder_property(self) -> None:
        """offer_holder returns cached reference."""
        offer = Offer(gid="123")
        holder = OfferHolder(gid="456")
        offer._offer_holder = holder
        assert offer.offer_holder is holder

    def test_unit_navigation_via_holder(self) -> None:
        """unit property navigates via offer_holder."""
        unit = Unit(gid="u1", name="Test Unit")
        holder = OfferHolder(gid="h1")
        holder._unit = unit

        offer = Offer(gid="o1")
        offer._offer_holder = holder

        assert offer.unit is unit

    def test_business_navigation_via_unit(self) -> None:
        """business property navigates via unit."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="b1", name="Test Business")
        unit_holder = UnitHolder(gid="uh1")
        unit_holder._business = business
        unit = Unit(gid="u1")
        unit._unit_holder = unit_holder

        offer_holder = OfferHolder(gid="oh1")
        offer_holder._unit = unit

        offer = Offer(gid="o1")
        offer._offer_holder = offer_holder

        assert offer.business is business

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        offer = Offer(gid="123")
        offer._business = object()  # type: ignore
        offer._unit = Unit(gid="456")
        offer._offer_holder = OfferHolder(gid="789")

        offer._invalidate_refs()

        assert offer._business is None
        assert offer._unit is None
        assert offer._offer_holder is None


class TestOfferInheritedFields:
    """Tests for Offer inherited field definitions."""

    def test_inherited_fields_all(self) -> None:
        """InheritedFields.all() returns all definitions."""
        all_fields = Offer.InheritedFields.all()
        assert len(all_fields) == 2
        names = [f.name for f in all_fields]
        assert "Vertical" in names
        assert "Platforms" in names

    def test_vertical_inherited_from_unit_business(self) -> None:
        """VERTICAL inherits from Unit and Business."""
        vertical = Offer.InheritedFields.VERTICAL
        assert "Unit" in vertical.inherit_from
        assert "Business" in vertical.inherit_from
        assert vertical.allow_override is True

    def test_platforms_inherited_from_unit(self) -> None:
        """PLATFORMS inherits from Unit."""
        platforms = Offer.InheritedFields.PLATFORMS
        assert "Unit" in platforms.inherit_from
        assert platforms.allow_override is True


class TestOfferCustomFields:
    """Tests for Offer custom field accessors (39 fields)."""

    # --- Financial Fields ---

    def test_mrr_getter(self) -> None:
        """mrr getter returns Decimal value."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "MRR", "number_value": 2500.00}],
        )
        assert offer.mrr == Decimal("2500.00")

    def test_cost(self) -> None:
        """cost getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Cost", "number_value": 100.00}],
        )
        assert offer.cost == Decimal("100.00")

    def test_weekly_ad_spend(self) -> None:
        """weekly_ad_spend getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Weekly Ad Spend", "number_value": 500.00}],
        )
        assert offer.weekly_ad_spend == Decimal("500.00")

    def test_voucher_value(self) -> None:
        """voucher_value getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Voucher Value", "number_value": 50.00}],
        )
        assert offer.voucher_value == Decimal("50.00")

    def test_budget_allocation(self) -> None:
        """budget_allocation getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Budget Allocation", "number_value": 0.25}],
        )
        assert offer.budget_allocation == Decimal("0.25")

    # --- Ad Platform IDs ---

    def test_ad_id(self) -> None:
        """ad_id getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Ad ID", "text_value": "ad123456"}],
        )
        assert offer.ad_id == "ad123456"

    def test_ad_set_id(self) -> None:
        """ad_set_id getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Ad Set ID", "text_value": "adset789"}],
        )
        assert offer.ad_set_id == "adset789"

    def test_campaign_id(self) -> None:
        """campaign_id getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Campaign ID", "text_value": "camp001"}],
        )
        assert offer.campaign_id == "camp001"

    def test_asset_id(self) -> None:
        """asset_id getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Asset ID", "text_value": "asset123"}],
        )
        assert offer.asset_id == "asset123"

    def test_ad_account_url(self) -> None:
        """ad_account_url getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Ad Account URL",
                    "text_value": "https://fb.com/account/123",
                }
            ],
        )
        assert offer.ad_account_url == "https://fb.com/account/123"

    def test_active_ads_url(self) -> None:
        """active_ads_url getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Active Ads URL",
                    "text_value": "https://fb.com/ads",
                }
            ],
        )
        assert offer.active_ads_url == "https://fb.com/ads"

    def test_platforms_multi_enum(self) -> None:
        """platforms returns list from multi-enum field."""
        offer = Offer(gid="123", custom_fields=[])
        offer.custom_fields_editor().set(
            "Platforms",
            [
                {"gid": "e1", "name": "Google"},
                {"gid": "e2", "name": "Meta"},
            ],
        )
        assert offer.platforms == ["Google", "Meta"]

    # --- Content Fields ---

    def test_offer_headline(self) -> None:
        """offer_headline getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Offer Headline", "text_value": "50% Off!"}],
        )
        assert offer.offer_headline == "50% Off!"

    def test_included_items(self) -> None:
        """included_item_1/2/3 getter/setters work."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Included Item 1", "text_value": "Free Shipping"},
                {"gid": "2", "name": "Included Item 2", "text_value": "Gift Card"},
                {"gid": "3", "name": "Included Item 3", "text_value": "Warranty"},
            ],
        )
        assert offer.included_item_1 == "Free Shipping"
        assert offer.included_item_2 == "Gift Card"
        assert offer.included_item_3 == "Warranty"

    def test_landing_page_url(self) -> None:
        """landing_page_url getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Landing Page URL",
                    "text_value": "https://example.com/promo",
                }
            ],
        )
        assert offer.landing_page_url == "https://example.com/promo"

    def test_preview_link(self) -> None:
        """preview_link getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Preview Link",
                    "text_value": "https://preview.com",
                }
            ],
        )
        assert offer.preview_link == "https://preview.com"

    def test_num_ai_copies(self) -> None:
        """num_ai_copies returns integer value."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Num AI Copies", "number_value": 5}],
        )
        assert offer.num_ai_copies == 5

    # --- Configuration Fields ---

    def test_form_id(self) -> None:
        """form_id getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Form ID", "text_value": "form123"}],
        )
        assert offer.form_id == "form123"

    def test_language_enum(self) -> None:
        """language extracts name from enum dict."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Language", "enum_value": {"name": "English"}}],
        )
        assert offer.language == "English"

    def test_specialty_enum(self) -> None:
        """specialty extracts name from enum dict."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Specialty", "enum_value": {"name": "Dental"}}],
        )
        assert offer.specialty == "Dental"

    def test_vertical_enum(self) -> None:
        """vertical extracts name from enum dict."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}],
        )
        assert offer.vertical == "Healthcare"

    def test_campaign_type_enum(self) -> None:
        """campaign_type extracts name from enum dict."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Campaign Type",
                    "enum_value": {"name": "Lead Gen"},
                }
            ],
        )
        assert offer.campaign_type == "Lead Gen"

    def test_optimize_for_enum(self) -> None:
        """optimize_for extracts name from enum dict."""
        offer = Offer(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Optimize For",
                    "enum_value": {"name": "Conversions"},
                }
            ],
        )
        assert offer.optimize_for == "Conversions"

    def test_targeting_strategies_multi_enum(self) -> None:
        """targeting_strategies returns list from multi-enum field."""
        offer = Offer(gid="123", custom_fields=[])
        offer.custom_fields_editor().set(
            "Targeting Strategies",
            [
                {"gid": "t1", "name": "Lookalike"},
                {"gid": "t2", "name": "Interest"},
            ],
        )
        assert offer.targeting_strategies == ["Lookalike", "Interest"]

    def test_office_phone(self) -> None:
        """office_phone getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Office Phone", "text_value": "555-1234"}],
        )
        assert offer.office_phone == "555-1234"

    # --- Scheduling Fields ---

    def test_appt_duration(self) -> None:
        """appt_duration returns integer value."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Appt Duration", "number_value": 30}],
        )
        assert offer.appt_duration == 30

    def test_calendar_duration(self) -> None:
        """calendar_duration returns integer value."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Calendar Duration", "number_value": 60}],
        )
        assert offer.calendar_duration == 60

    def test_custom_cal_url(self) -> None:
        """custom_cal_url getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Custom Cal URL", "text_value": "https://cal.com"}],
        )
        assert offer.custom_cal_url == "https://cal.com"

    # --- Notes Fields ---

    def test_internal_notes(self) -> None:
        """internal_notes getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Internal Notes", "text_value": "Internal memo"}],
        )
        assert offer.internal_notes == "Internal memo"

    def test_external_notes(self) -> None:
        """external_notes getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "External Notes", "text_value": "Client-facing"}],
        )
        assert offer.external_notes == "Client-facing"

    # --- Metadata Fields ---

    def test_offer_id(self) -> None:
        """offer_id getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Offer ID", "text_value": "OFF-001"}],
        )
        assert offer.offer_id == "OFF-001"

    def test_algo_version(self) -> None:
        """algo_version getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Algo Version", "text_value": "v2.5"}],
        )
        assert offer.algo_version == "v2.5"

    def test_triggered_by(self) -> None:
        """triggered_by getter/setter works."""
        offer = Offer(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Triggered By", "text_value": "automation"}],
        )
        assert offer.triggered_by == "automation"

    def test_rep_people_field(self) -> None:
        """rep returns list of people dicts."""
        offer = Offer(gid="123", custom_fields=[])
        offer.custom_fields_editor().set(
            "Rep",
            [
                {"gid": "u1", "name": "John Doe"},
                {"gid": "u2", "name": "Jane Smith"},
            ],
        )
        assert len(offer.rep) == 2
        assert offer.rep[0]["name"] == "John Doe"


class TestOfferHolder:
    """Tests for OfferHolder model."""

    def test_offers_property_empty(self) -> None:
        """offers returns empty list by default."""
        holder = OfferHolder(gid="123")
        assert holder.offers == []

    def test_offers_property_populated(self) -> None:
        """offers returns populated list."""
        holder = OfferHolder(gid="123")
        holder._offers = [
            Offer(gid="o1", name="Offer 1"),
            Offer(gid="o2", name="Offer 2"),
        ]
        assert len(holder.offers) == 2
        assert holder.offers[0].name == "Offer 1"

    def test_active_offers_filters(self) -> None:
        """active_offers returns only offers with active ads."""
        holder = OfferHolder(gid="123")
        active = Offer(
            gid="o1",
            name="Active",
            custom_fields=[{"gid": "1", "name": "Ad ID", "text_value": "ad123"}],
        )
        inactive = Offer(gid="o2", name="Inactive", custom_fields=[])
        holder._offers = [active, inactive]

        active_offers = holder.active_offers
        assert len(active_offers) == 1
        assert active_offers[0].name == "Active"

    def test_unit_property(self) -> None:
        """unit returns cached reference."""
        holder = OfferHolder(gid="123")
        unit = Unit(gid="u1")
        holder._unit = unit
        assert holder.unit is unit

    def test_business_navigation_via_unit(self) -> None:
        """business navigates via unit."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="b1")
        unit_holder = UnitHolder(gid="uh1")
        unit_holder._business = business
        unit = Unit(gid="u1")
        unit._unit_holder = unit_holder

        holder = OfferHolder(gid="oh1")
        holder._unit = unit

        assert holder.business is business

    def test_populate_children(self) -> None:
        """_populate_children converts Tasks to Offers."""
        holder = OfferHolder(gid="123")
        subtasks = [
            Task(gid="o1", name="Offer 1", created_at="2024-01-01T00:00:00Z"),
            Task(gid="o2", name="Offer 2", created_at="2024-01-02T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        assert len(holder.offers) == 2
        assert all(isinstance(o, Offer) for o in holder.offers)
        # Sorted by created_at
        assert holder.offers[0].name == "Offer 1"
        assert holder.offers[1].name == "Offer 2"

    def test_populate_children_sets_back_references(self) -> None:
        """_populate_children sets back references on offers."""
        unit = Unit(gid="u1")
        holder = OfferHolder(gid="123")
        holder._unit = unit

        subtasks = [Task(gid="o1", name="Offer 1")]
        holder._populate_children(subtasks)

        assert holder.offers[0]._offer_holder is holder
        assert holder.offers[0]._unit is unit

    def test_invalidate_cache(self) -> None:
        """invalidate_cache clears offers list."""
        holder = OfferHolder(gid="123")
        holder._offers = [Offer(gid="o1")]
        holder.invalidate_cache()
        assert holder._offers == []
