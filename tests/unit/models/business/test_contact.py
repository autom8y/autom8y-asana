"""Tests for Contact and ContactHolder models.

Per TDD-BIZMODEL: Tests for Contact entity with owner detection and typed fields.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.task import Task


class TestContact:
    """Tests for Contact model."""

    def test_contact_inherits_from_task(self) -> None:
        """Contact inherits from Task and can be constructed."""
        contact = Contact(gid="123", name="John Doe")
        assert contact.gid == "123"
        assert contact.name == "John Doe"

    def test_full_name_property(self) -> None:
        """full_name returns Task.name."""
        contact = Contact(gid="123", name="John Doe")
        assert contact.full_name == "John Doe"

    def test_full_name_empty_when_name_none(self) -> None:
        """full_name returns empty string when name is None."""
        contact = Contact(gid="123")
        assert contact.full_name == ""


class TestContactOwnerDetection:
    """Tests for Contact.is_owner detection."""

    @pytest.mark.parametrize(
        "position_value",
        ["Owner", "owner", "OWNER", "CEO", "ceo", "Founder", "President", "Principal"],
    )
    def test_is_owner_true(self, position_value: str) -> None:
        """is_owner returns True for owner positions (case-insensitive)."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Position", "enum_value": {"name": position_value}}
            ],
        )
        assert contact.is_owner is True

    @pytest.mark.parametrize(
        "position_value",
        ["Manager", "Employee", "Director", "VP", "Assistant"],
    )
    def test_is_owner_false_non_owner_position(self, position_value: str) -> None:
        """is_owner returns False for non-owner positions."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Position", "enum_value": {"name": position_value}}
            ],
        )
        assert contact.is_owner is False

    def test_is_owner_false_when_position_none(self) -> None:
        """is_owner returns False when position is None."""
        contact = Contact(gid="123", custom_fields=[])
        assert contact.is_owner is False


class TestContactNameParsing:
    """Tests for Contact name parsing."""

    def test_first_name_parsed(self) -> None:
        """first_name is parsed from full name."""
        contact = Contact(gid="123", name="John Doe")
        assert contact.first_name == "John"

    def test_last_name_parsed(self) -> None:
        """last_name is parsed from full name."""
        contact = Contact(gid="123", name="John Doe")
        assert contact.last_name == "Doe"

    def test_first_name_single_name(self) -> None:
        """first_name works with single name."""
        contact = Contact(gid="123", name="John")
        assert contact.first_name == "John"

    def test_last_name_single_name(self) -> None:
        """last_name returns None for single name."""
        contact = Contact(gid="123", name="John")
        assert contact.last_name is None

    def test_display_name_simple(self) -> None:
        """display_name returns name without prefix/suffix."""
        contact = Contact(gid="123", name="John Doe")
        assert contact.display_name == "John Doe"

    def test_display_name_with_prefix_suffix(self) -> None:
        """display_name includes prefix and suffix."""
        contact = Contact(
            gid="123",
            name="John Doe",
            custom_fields=[
                {"gid": "1", "name": "Prefix", "text_value": "Dr."},
                {"gid": "2", "name": "Suffix", "text_value": "Jr."},
            ],
        )
        assert contact.display_name == "Dr. John Doe Jr."

    def test_preferred_name_uses_nickname(self) -> None:
        """preferred_name returns nickname when set."""
        contact = Contact(
            gid="123",
            name="Jonathan Smith",
            custom_fields=[
                {"gid": "1", "name": "Nickname", "text_value": "Johnny"},
            ],
        )
        assert contact.preferred_name == "Johnny"

    def test_preferred_name_falls_back_to_first_name(self) -> None:
        """preferred_name returns first_name when no nickname."""
        contact = Contact(gid="123", name="Jonathan Smith")
        assert contact.preferred_name == "Jonathan"


class TestContactCustomFields:
    """Tests for Contact custom field accessors."""

    def test_contact_email_getter(self) -> None:
        """contact_email getter returns value."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Contact Email", "text_value": "john@example.com"}
            ],
        )
        assert contact.contact_email == "john@example.com"

    def test_contact_email_setter(self) -> None:
        """contact_email setter updates value."""
        contact = Contact(gid="123", custom_fields=[])
        contact.contact_email = "new@example.com"
        assert contact.get_custom_fields().get("Contact Email") == "new@example.com"
        assert contact.get_custom_fields().has_changes()

    def test_contact_phone_getter(self) -> None:
        """contact_phone getter returns value."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Contact Phone", "text_value": "555-1234"}
            ],
        )
        assert contact.contact_phone == "555-1234"

    def test_position_enum_extraction(self) -> None:
        """position extracts name from enum dict."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Position",
                    "enum_value": {"gid": "ev1", "name": "Manager"},
                }
            ],
        )
        assert contact.position == "Manager"

    def test_position_plain_string(self) -> None:
        """position returns plain string when not dict."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Position", "text_value": "Manager"}
            ],
        )
        assert contact.position == "Manager"

    def test_time_zone_enum_extraction(self) -> None:
        """time_zone extracts name from enum dict."""
        contact = Contact(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Time Zone",
                    "enum_value": {"gid": "tz1", "name": "America/New_York"},
                }
            ],
        )
        assert contact.time_zone == "America/New_York"


class TestContactNavigation:
    """Tests for Contact navigation properties."""

    def test_contact_holder_property(self) -> None:
        """contact_holder returns cached reference."""
        contact = Contact(gid="123")
        holder = ContactHolder(gid="456")
        contact._contact_holder = holder
        assert contact.contact_holder is holder

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        contact = Contact(gid="123")
        holder = ContactHolder(gid="456")
        contact._contact_holder = holder
        contact._invalidate_refs()
        assert contact._contact_holder is None
        assert contact._business is None


class TestContactHolder:
    """Tests for ContactHolder model."""

    def test_contacts_property_empty(self) -> None:
        """contacts returns empty list by default."""
        holder = ContactHolder(gid="123")
        assert holder.contacts == []

    def test_contacts_property_populated(self) -> None:
        """contacts returns populated list."""
        holder = ContactHolder(gid="123")
        holder._contacts = [
            Contact(gid="c1", name="John"),
            Contact(gid="c2", name="Jane"),
        ]
        assert len(holder.contacts) == 2
        assert holder.contacts[0].name == "John"

    def test_owner_property_finds_owner(self) -> None:
        """owner returns contact with is_owner=True."""
        holder = ContactHolder(gid="123")
        owner_contact = Contact(
            gid="c1",
            name="John",
            custom_fields=[
                {"gid": "1", "name": "Position", "enum_value": {"name": "Owner"}}
            ],
        )
        employee_contact = Contact(
            gid="c2",
            name="Jane",
            custom_fields=[
                {"gid": "2", "name": "Position", "enum_value": {"name": "Manager"}}
            ],
        )
        holder._contacts = [employee_contact, owner_contact]
        assert holder.owner is owner_contact

    def test_owner_property_none_when_no_owner(self) -> None:
        """owner returns None when no owner contact."""
        holder = ContactHolder(gid="123")
        holder._contacts = [
            Contact(
                gid="c1",
                custom_fields=[
                    {"gid": "1", "name": "Position", "enum_value": {"name": "Manager"}}
                ],
            )
        ]
        assert holder.owner is None

    def test_populate_children(self) -> None:
        """_populate_children converts Tasks to Contacts."""
        holder = ContactHolder(gid="123")
        subtasks = [
            Task(gid="c1", name="John", created_at="2024-01-01T00:00:00Z"),
            Task(gid="c2", name="Jane", created_at="2024-01-02T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        assert len(holder.contacts) == 2
        assert all(isinstance(c, Contact) for c in holder.contacts)
        # Sorted by created_at
        assert holder.contacts[0].name == "John"
        assert holder.contacts[1].name == "Jane"

    def test_populate_children_sets_back_references(self) -> None:
        """_populate_children sets back references on contacts."""
        holder = ContactHolder(gid="123")
        holder._business = None  # Would be set by Business

        subtasks = [Task(gid="c1", name="John")]
        holder._populate_children(subtasks)

        assert holder.contacts[0]._contact_holder is holder

    def test_invalidate_cache(self) -> None:
        """invalidate_cache clears contacts list."""
        holder = ContactHolder(gid="123")
        holder._contacts = [Contact(gid="c1")]
        holder.invalidate_cache()
        assert holder._contacts == []
