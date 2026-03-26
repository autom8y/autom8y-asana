"""Tests for Business model.

Per TDD-BIZMODEL: Tests for Business model with holders and typed fields.
"""

from __future__ import annotations

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.fields import CascadingFieldDef
from autom8_asana.models.task import Task


class TestBusinessConstruction:
    """Tests for Business model construction."""

    def test_business_inherits_from_task(self) -> None:
        """Business inherits from Task and can be constructed."""
        business = Business(gid="123", name="Acme Corp")
        assert business.gid == "123"
        assert business.name == "Acme Corp"

    def test_holder_key_map_has_required_entries(self) -> None:
        """HOLDER_KEY_MAP defines required holder types.

        Per TDD-HARDENING-C Phase 6: reconciliation_holder (renamed from reconciliations_holder).
        """
        # Required holder types that must be present
        required_keys = {
            "contact_holder",
            "unit_holder",
            "location_holder",
            "dna_holder",
            "reconciliation_holder",  # Renamed from reconciliations_holder
            "asset_edit_holder",
            "videography_holder",
        }
        # All required keys must be present (allows adding new holders without breaking test)
        assert required_keys.issubset(set(Business.HOLDER_KEY_MAP.keys()))

    def test_holder_key_map_values(self) -> None:
        """HOLDER_KEY_MAP values are (name, emoji) tuples."""
        for key, value in Business.HOLDER_KEY_MAP.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert isinstance(value[0], str)  # name
            assert isinstance(value[1], str)  # emoji


class TestBusinessHolderProperties:
    """Tests for Business holder properties."""

    def test_contact_holder_property(self) -> None:
        """contact_holder returns cached reference."""
        business = Business(gid="123")
        holder = ContactHolder(gid="456")
        business._contact_holder = holder
        assert business.contact_holder is holder

    def test_contact_holder_none_by_default(self) -> None:
        """contact_holder returns None when not populated."""
        business = Business(gid="123")
        assert business.contact_holder is None

    def test_unit_holder_returns_task(self) -> None:
        """unit_holder returns Task (Phase 2: will be UnitHolder)."""
        business = Business(gid="123")
        task = Task(gid="456")
        business._unit_holder = task
        assert business.unit_holder is task

    def test_stub_holders_return_task(self) -> None:
        """Stub holders return Task or None."""
        business = Business(gid="123")
        task = Task(gid="456")

        business._dna_holder = task
        assert business.dna_holder is task

        assert business.reconciliation_holder is None
        assert business.asset_edit_holder is None
        assert business.videography_holder is None


class TestBusinessConvenienceShortcuts:
    """Tests for Business convenience shortcut properties."""

    def test_contacts_via_holder(self) -> None:
        """contacts returns list via contact_holder."""
        business = Business(gid="123")
        holder = ContactHolder(gid="456")
        holder._contacts = [
            Contact(gid="c1", name="John"),
            Contact(gid="c2", name="Jane"),
        ]
        business._contact_holder = holder

        assert len(business.contacts) == 2
        assert business.contacts[0].name == "John"

    def test_contacts_empty_when_no_holder(self) -> None:
        """contacts returns empty list when holder not populated."""
        business = Business(gid="123")
        assert business.contacts == []

    def test_units_returns_empty_phase1(self) -> None:
        """units returns empty list in Phase 1."""
        business = Business(gid="123")
        assert business.units == []

    def test_address_returns_none_phase1(self) -> None:
        """address returns None in Phase 1."""
        business = Business(gid="123")
        assert business.address is None

    def test_hours_returns_none_phase1(self) -> None:
        """hours returns None in Phase 1."""
        business = Business(gid="123")
        assert business.hours is None


class TestBusinessHolderPopulation:
    """Tests for Business holder population."""

    def test_identify_holder_by_name(self) -> None:
        """_identify_holder identifies holder by task name."""
        business = Business(gid="123")
        task = Task(gid="456", name="Contacts")
        assert business._identify_holder(task) == "contact_holder"

    def test_identify_holder_no_match(self) -> None:
        """_identify_holder returns None for non-holder task."""
        business = Business(gid="123")
        task = Task(gid="456", name="Some Task")
        assert business._identify_holder(task) is None

    def test_matches_holder_pattern_by_name(self) -> None:
        """_matches_holder_pattern returns True for name match.

        Per TDD-SPRINT-1 Phase 2: Extracted to detection.py.
        """
        from autom8_asana.models.business.detection import _matches_holder_pattern

        task = Task(gid="456", name="Contacts")
        assert _matches_holder_pattern(task, "Contacts", "busts_in_silhouette")

    def test_matches_holder_pattern_no_match(self) -> None:
        """_matches_holder_pattern returns False when neither name nor emoji match.

        Per TDD-SPRINT-1 Phase 2: Extracted to detection.py.
        """
        from autom8_asana.models.business.detection import _matches_holder_pattern

        task = Task(gid="456", name="Other")
        assert not _matches_holder_pattern(task, "Contacts", "busts_in_silhouette")

    def test_create_typed_holder_contact(self) -> None:
        """_create_typed_holder creates ContactHolder."""
        business = Business(gid="123")
        task = Task(gid="456", name="Contacts")
        holder = business._create_typed_holder("contact_holder", task)

        assert isinstance(holder, ContactHolder)
        assert holder.gid == "456"
        assert holder._business is business

    def test_create_typed_holder_dna(self) -> None:
        """_create_typed_holder returns typed DNAHolder for DNA."""
        from autom8_asana.models.business.business import DNAHolder

        business = Business(gid="123")
        task = Task(gid="456", name="DNA")
        holder = business._create_typed_holder("dna_holder", task)

        assert isinstance(holder, DNAHolder)
        assert holder.gid == "456"
        assert holder._business is business

    def test_populate_holders(self) -> None:
        """_populate_holders populates holder properties."""
        business = Business(gid="123")
        subtasks = [
            Task(gid="h1", name="Contacts"),
            Task(gid="h2", name="Units"),
            Task(gid="h3", name="DNA"),
        ]
        business._populate_holders(subtasks)

        assert business._contact_holder is not None
        assert isinstance(business._contact_holder, ContactHolder)
        assert business._unit_holder is not None
        assert business._dna_holder is not None


class TestBusinessCascadingFields:
    """Tests for Business cascading field definitions."""

    def test_cascading_fields_class_exists(self) -> None:
        """Business.CascadingFields class exists."""
        assert hasattr(Business, "CascadingFields")

    def test_cascading_fields_all(self) -> None:
        """CascadingFields.all() returns list of definitions."""
        all_fields = Business.CascadingFields.all()
        assert len(all_fields) == 4
        assert all(isinstance(f, CascadingFieldDef) for f in all_fields)

    def test_cascading_fields_get(self) -> None:
        """CascadingFields.get() returns definition by name."""
        field_def = Business.CascadingFields.get("Office Phone")
        assert field_def is not None
        assert field_def.name == "Office Phone"

    def test_cascading_fields_get_not_found(self) -> None:
        """CascadingFields.get() returns None for unknown field."""
        assert Business.CascadingFields.get("Unknown Field") is None

    def test_office_phone_cascade_targets(self) -> None:
        """Office Phone cascades to specific targets."""
        field_def = Business.CascadingFields.OFFICE_PHONE
        assert field_def.target_types == {"Unit", "Offer", "Process", "Contact"}
        assert field_def.allow_override is False

    def test_company_id_cascades_to_all(self) -> None:
        """Company ID cascades to all descendants."""
        field_def = Business.CascadingFields.COMPANY_ID
        assert field_def.target_types is None  # None = all
        assert field_def.allow_override is False

    def test_business_name_uses_source_field(self) -> None:
        """Business Name uses source_field='name'."""
        field_def = Business.CascadingFields.BUSINESS_NAME
        assert field_def.source_field == "name"

    def test_get_cascading_fields_method(self) -> None:
        """get_cascading_fields() returns field definitions."""
        business = Business(gid="123")
        fields = business.get_cascading_fields()
        assert len(fields) == 4


class TestBusinessCustomFields:
    """Tests for Business custom field accessors."""

    def test_company_id_getter(self) -> None:
        """company_id getter returns value."""
        business = Business(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Company ID", "text_value": "ACME-001"}
            ],
        )
        assert business.company_id == "ACME-001"

    def test_company_id_setter(self) -> None:
        """company_id setter updates value."""
        business = Business(gid="123", custom_fields=[])
        business.company_id = "NEW-001"
        assert business.custom_fields_editor().get("Company ID") == "NEW-001"
        assert business.custom_fields_editor().has_changes()

    def test_office_phone_getter_setter(self) -> None:
        """office_phone getter and setter work with E.164 normalization."""
        business = Business(gid="123", custom_fields=[])
        business.office_phone = "(614) 636-2433"
        # PhoneTextField normalizes to E.164 on read
        assert business.office_phone == "+16146362433"

    def test_num_reviews_number_conversion(self) -> None:
        """num_reviews converts to int."""
        business = Business(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Num Reviews", "number_value": 42.0}],
        )
        assert business.num_reviews == 42
        assert isinstance(business.num_reviews, int)

    def test_num_reviews_none(self) -> None:
        """num_reviews returns None when not set."""
        business = Business(gid="123", custom_fields=[])
        assert business.num_reviews is None

    def test_vertical_enum_extraction(self) -> None:
        """vertical extracts name from enum dict."""
        business = Business(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Vertical",
                    "enum_value": {"gid": "v1", "name": "Legal"},
                }
            ],
        )
        assert business.vertical == "Legal"

    def test_booking_type_enum_extraction(self) -> None:
        """booking_type extracts name from enum dict."""
        business = Business(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Booking Type",
                    "enum_value": {"gid": "b1", "name": "Standard"},
                }
            ],
        )
        assert business.booking_type == "Standard"

    def test_rep_people_field(self) -> None:
        """rep returns list of people dicts."""
        business = Business(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Rep",
                    "people_value": [
                        {"gid": "user1", "name": "John Doe"},
                        {"gid": "user2", "name": "Jane Doe"},
                    ],
                }
            ],
        )
        assert len(business.rep) == 2
        assert business.rep[0]["name"] == "John Doe"

    def test_rep_empty_list_when_none(self) -> None:
        """rep returns empty list when not set."""
        business = Business(gid="123", custom_fields=[])
        assert business.rep == []


class TestBusinessFieldsClass:
    """Tests for Business.Fields constants."""

    def test_fields_class_has_constants(self) -> None:
        """Business.Fields has all field constants including those from mixins.

        Per TDD-SPRINT-1/ADR-0119: Business inherits fields from mixins:
        - SharedCascadingFieldsMixin: VERTICAL, REP
        - FinancialFieldsMixin: BOOKING_TYPE, MRR, WEEKLY_AD_SPEND

        Note: MRR and WEEKLY_AD_SPEND are inherited but return None on Business
        since the underlying Asana task doesn't have those custom fields.
        """
        expected_fields = {
            # Entity-specific fields
            "AGGRESSION_LEVEL",
            "COMPANY_ID",
            "FACEBOOK_PAGE_ID",
            "FALLBACK_PAGE_ID",
            "GOOGLE_CAL_ID",
            "NUM_REVIEWS",
            "OFFICE_PHONE",
            "OWNER_NAME",
            "OWNER_NICKNAME",
            "REVIEW_1",
            "REVIEW_2",
            "REVIEWS_LINK",
            "STRIPE_ID",
            "STRIPE_LINK",
            "TWILIO_PHONE_NUM",
            "VCA_STATUS",
            # From SharedCascadingFieldsMixin
            "VERTICAL",
            "REP",
            # From FinancialFieldsMixin
            "BOOKING_TYPE",
            "MRR",
            "WEEKLY_AD_SPEND",
        }
        actual_fields = {
            name
            for name in dir(Business.Fields)
            if not name.startswith("_") and name.isupper()
        }
        assert actual_fields == expected_fields

    def test_field_constants_are_strings(self) -> None:
        """Field constants are string values."""
        assert Business.Fields.COMPANY_ID == "Company ID"
        assert Business.Fields.OFFICE_PHONE == "Office Phone"
        assert Business.Fields.VERTICAL == "Vertical"


class TestBusinessNavigation:
    """Tests for Business bidirectional navigation."""

    def test_contact_can_navigate_to_business(self) -> None:
        """Contact can navigate back to Business."""
        business = Business(gid="b1", name="Acme")
        holder = ContactHolder(gid="h1")
        holder._business = business
        contact = Contact(gid="c1", name="John")
        contact._contact_holder = holder

        assert contact.business is business

    def test_contact_holder_has_business_reference(self) -> None:
        """ContactHolder has reference to Business."""
        business = Business(gid="b1")
        holder = ContactHolder(gid="h1")
        business._contact_holder = holder
        holder._business = business

        assert holder.business is business
