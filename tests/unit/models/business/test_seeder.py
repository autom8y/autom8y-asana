"""Unit tests for BusinessSeeder.

Per TDD-PROCESS-PIPELINE Phase 3: Tests for BusinessSeeder factory.
Per ADR-0099: Find-or-create pattern.

Test cases:
1. BusinessData validation
2. ContactData validation
3. ProcessData validation
4. ProcessData defaults
5. SeederResult fields
6. SeederResult default flags
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.models.business.process import ProcessType
from autom8_asana.models.business.seeder import (
    BusinessData,
    BusinessSeeder,
    ContactData,
    ProcessData,
    SeederResult,
)


# --- Test: BusinessData ---


class TestBusinessData:
    """Tests for BusinessData Pydantic model."""

    def test_required_name(self) -> None:
        """BusinessData requires name field."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessData()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_minimal_creation(self) -> None:
        """BusinessData can be created with just name."""
        data = BusinessData(name="Acme Corp")

        assert data.name == "Acme Corp"
        assert data.company_id is None
        assert data.vertical is None
        assert data.business_address_line_1 is None
        assert data.business_city is None
        assert data.business_state is None
        assert data.business_zip is None

    def test_full_creation(self) -> None:
        """BusinessData can be created with all fields."""
        data = BusinessData(
            name="Acme Corp",
            company_id="ACME-001",
            vertical="Technology",
            business_address_line_1="123 Main St",
            business_city="Austin",
            business_state="TX",
            business_zip="78701",
        )

        assert data.name == "Acme Corp"
        assert data.company_id == "ACME-001"
        assert data.vertical == "Technology"
        assert data.business_address_line_1 == "123 Main St"
        assert data.business_city == "Austin"
        assert data.business_state == "TX"
        assert data.business_zip == "78701"


# --- Test: ContactData ---


class TestContactData:
    """Tests for ContactData Pydantic model."""

    def test_required_full_name(self) -> None:
        """ContactData requires full_name field."""
        with pytest.raises(ValidationError) as exc_info:
            ContactData()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("full_name",) for e in errors)

    def test_minimal_creation(self) -> None:
        """ContactData can be created with just full_name."""
        data = ContactData(full_name="John Doe")

        assert data.full_name == "John Doe"
        assert data.contact_email is None
        assert data.contact_phone is None

    def test_full_creation(self) -> None:
        """ContactData can be created with all fields."""
        data = ContactData(
            full_name="John Doe",
            contact_email="john@acme.com",
            contact_phone="+1-555-555-5555",
        )

        assert data.full_name == "John Doe"
        assert data.contact_email == "john@acme.com"
        assert data.contact_phone == "+1-555-555-5555"


# --- Test: ProcessData ---


class TestProcessData:
    """Tests for ProcessData Pydantic model.

    Per ADR-0101: initial_state field removed from ProcessData.
    """

    def test_required_fields(self) -> None:
        """ProcessData requires name and process_type."""
        with pytest.raises(ValidationError) as exc_info:
            ProcessData()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
        assert any(e["loc"] == ("process_type",) for e in errors)

    def test_minimal_creation(self) -> None:
        """ProcessData can be created with required fields only."""
        data = ProcessData(name="Demo Call", process_type=ProcessType.SALES)

        assert data.name == "Demo Call"
        assert data.process_type == ProcessType.SALES
        assert data.assigned_to is None
        assert data.due_date is None
        assert data.notes is None

    def test_full_creation(self) -> None:
        """ProcessData can be created with all fields."""
        data = ProcessData(
            name="Demo Call - Acme",
            process_type=ProcessType.SALES,
            assigned_to="user_gid_123",
            due_date="2024-03-15",
            notes="High priority prospect",
        )

        assert data.name == "Demo Call - Acme"
        assert data.process_type == ProcessType.SALES
        assert data.assigned_to == "user_gid_123"
        assert data.due_date == "2024-03-15"
        assert data.notes == "High priority prospect"

    def test_all_process_types_valid(self) -> None:
        """ProcessData accepts all ProcessType values."""
        for ptype in ProcessType:
            data = ProcessData(name="Test Process", process_type=ptype)
            assert data.process_type == ptype


# --- Test: SeederResult ---


class TestSeederResult:
    """Tests for SeederResult dataclass.

    Per ADR-0101: added_to_pipeline field removed from SeederResult.
    """

    def test_required_fields(self) -> None:
        """SeederResult requires business, unit, and process."""
        # Create minimal mock objects
        from unittest.mock import MagicMock

        business = MagicMock()
        unit = MagicMock()
        process = MagicMock()

        result = SeederResult(
            business=business,
            unit=unit,
            process=process,
        )

        assert result.business is business
        assert result.unit is unit
        assert result.process is process

    def test_default_flags(self) -> None:
        """SeederResult defaults all flags to False."""
        from unittest.mock import MagicMock

        result = SeederResult(
            business=MagicMock(),
            unit=MagicMock(),
            process=MagicMock(),
        )

        assert result.contact is None
        assert result.created_business is False
        assert result.created_unit is False
        assert result.created_contact is False
        assert result.warnings == []

    def test_warnings_default_factory(self) -> None:
        """SeederResult creates new list for each instance."""
        from unittest.mock import MagicMock

        result1 = SeederResult(
            business=MagicMock(),
            unit=MagicMock(),
            process=MagicMock(),
        )
        result2 = SeederResult(
            business=MagicMock(),
            unit=MagicMock(),
            process=MagicMock(),
        )

        # Mutate one list
        result1.warnings.append("test warning")

        # Other list should be unaffected
        assert result1.warnings == ["test warning"]
        assert result2.warnings == []

    def test_full_creation(self) -> None:
        """SeederResult can be created with all fields."""
        from unittest.mock import MagicMock

        business = MagicMock()
        unit = MagicMock()
        process = MagicMock()
        contact = MagicMock()

        result = SeederResult(
            business=business,
            unit=unit,
            process=process,
            contact=contact,
            created_business=True,
            created_unit=True,
            created_contact=True,
            warnings=["Warning 1", "Warning 2"],
        )

        assert result.business is business
        assert result.unit is unit
        assert result.process is process
        assert result.contact is contact
        assert result.created_business is True
        assert result.created_unit is True
        assert result.created_contact is True
        assert result.warnings == ["Warning 1", "Warning 2"]


# --- Test: BusinessSeeder ---


class TestBusinessSeeder:
    """Tests for BusinessSeeder class."""

    def test_init_stores_client(self) -> None:
        """BusinessSeeder stores client reference."""
        from unittest.mock import MagicMock

        client = MagicMock()
        seeder = BusinessSeeder(client)

        assert seeder._client is client

    def test_find_business_async_stub_returns_none(self) -> None:
        """_find_business_async MVP stub returns None."""
        import asyncio
        from unittest.mock import MagicMock

        client = MagicMock()
        seeder = BusinessSeeder(client)

        data = BusinessData(name="Acme Corp", company_id="ACME-001")

        # Run the async method
        result = asyncio.run(seeder._find_business_async(data))

        # MVP stub always returns None
        assert result is None
