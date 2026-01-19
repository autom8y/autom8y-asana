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

    def test_find_business_async_no_match_returns_none(self) -> None:
        """_find_business_async returns None when no match found."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        # Mock search service to return no matches
        client.search.find_one_async = AsyncMock(return_value=None)

        seeder = BusinessSeeder(client)

        data = BusinessData(name="Acme Corp", company_id="ACME-001")

        # Run the async method
        result = asyncio.run(seeder._find_business_async(data))

        # Should return None when no match found
        assert result is None


# --- Test: Business Deduplication ---


class TestBusinessDeduplication:
    """Tests for BusinessSeeder deduplication logic.

    Per TDD-entity-creation: Two-tier matching strategy.
    """

    def test_search_by_company_id_returns_hit(self) -> None:
        """_search_by_company_id returns SearchHit when match found."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from autom8_asana.search.models import SearchHit

        # Create mock SearchHit
        mock_hit = SearchHit(
            gid="123456789",
            entity_type="Business",
            name="Test Business",
            matched_fields={"Company ID": "ACME-001"},
        )

        client = MagicMock()
        client.search.find_one_async = AsyncMock(return_value=mock_hit)

        seeder = BusinessSeeder(client)

        # Run the async method
        result = asyncio.run(seeder._search_by_company_id("ACME-001"))

        assert result is not None
        assert result.gid == "123456789"
        assert result.entity_type == "Business"

        # Verify search was called with correct parameters
        client.search.find_one_async.assert_called_once()
        call_args = client.search.find_one_async.call_args
        assert call_args[0][1] == {"Company ID": "ACME-001"}
        assert call_args[1]["entity_type"] == "Business"

    def test_search_by_company_id_returns_none_when_not_found(self) -> None:
        """_search_by_company_id returns None when no match."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        client.search.find_one_async = AsyncMock(return_value=None)

        seeder = BusinessSeeder(client)

        result = asyncio.run(seeder._search_by_company_id("NONEXISTENT"))

        assert result is None

    def test_search_by_company_id_handles_multiple_matches(self) -> None:
        """_search_by_company_id handles ValueError for multiple matches."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from autom8_asana.search.models import SearchHit, SearchResult

        # First call raises ValueError (multiple matches)
        # Second call (find_async) returns first match
        mock_hit = SearchHit(
            gid="123456789",
            entity_type="Business",
            name="First Match",
            matched_fields={"Company ID": "DUP-001"},
        )
        mock_result = SearchResult(
            hits=[mock_hit],
            total_count=1,
            query_time_ms=1.0,
            from_cache=True,
        )

        client = MagicMock()
        client.search.find_one_async = AsyncMock(
            side_effect=ValueError("Multiple matches found")
        )
        client.search.find_async = AsyncMock(return_value=mock_result)

        seeder = BusinessSeeder(client)

        result = asyncio.run(seeder._search_by_company_id("DUP-001"))

        assert result is not None
        assert result.gid == "123456789"

    def test_search_by_company_id_graceful_degradation(self) -> None:
        """_search_by_company_id returns None on unexpected errors."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        client.search.find_one_async = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        seeder = BusinessSeeder(client)

        # Should not raise, returns None
        result = asyncio.run(seeder._search_by_company_id("ERROR-001"))

        assert result is None

    def test_search_by_name_returns_hit(self) -> None:
        """_search_by_name returns SearchHit when match found."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from autom8_asana.search.models import SearchHit

        mock_hit = SearchHit(
            gid="987654321",
            entity_type="Business",
            name="Joe's Pizza",
            matched_fields={"name": "Joe's Pizza"},
        )

        client = MagicMock()
        client.search.find_one_async = AsyncMock(return_value=mock_hit)

        seeder = BusinessSeeder(client)

        result = asyncio.run(seeder._search_by_name("Joe's Pizza"))

        assert result is not None
        assert result.gid == "987654321"
        assert result.name == "Joe's Pizza"

    def test_search_by_name_returns_none_when_not_found(self) -> None:
        """_search_by_name returns None when no match."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        client.search.find_one_async = AsyncMock(return_value=None)

        seeder = BusinessSeeder(client)

        result = asyncio.run(seeder._search_by_name("Nonexistent Business"))

        assert result is None

    def test_search_by_name_handles_multiple_matches(self) -> None:
        """_search_by_name handles ValueError for multiple matches."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from autom8_asana.search.models import SearchHit, SearchResult

        mock_hit = SearchHit(
            gid="111222333",
            entity_type="Business",
            name="Common Name Corp",
            matched_fields={"name": "Common Name Corp"},
        )
        mock_result = SearchResult(
            hits=[mock_hit],
            total_count=1,
            query_time_ms=1.0,
            from_cache=True,
        )

        client = MagicMock()
        client.search.find_one_async = AsyncMock(
            side_effect=ValueError("Multiple matches found")
        )
        client.search.find_async = AsyncMock(return_value=mock_result)

        seeder = BusinessSeeder(client)

        result = asyncio.run(seeder._search_by_name("Common Name Corp"))

        assert result is not None
        assert result.gid == "111222333"

    def test_search_by_name_graceful_degradation(self) -> None:
        """_search_by_name returns None on unexpected errors."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        client.search.find_one_async = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        seeder = BusinessSeeder(client)

        result = asyncio.run(seeder._search_by_name("Error Business"))

        assert result is None

    def test_find_business_prioritizes_company_id_over_name(self) -> None:
        """_find_business_async checks company_id first, then name."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from autom8_asana.search.models import SearchHit

        # Mock a match by company_id
        company_id_hit = SearchHit(
            gid="COMPANY_ID_MATCH",
            entity_type="Business",
            name="Business Found By Company ID",
            matched_fields={"Company ID": "ACME-001"},
        )

        client = MagicMock()
        client.search.find_one_async = AsyncMock(return_value=company_id_hit)

        seeder = BusinessSeeder(client)

        # Mock _load_business to return a mock Business
        mock_business = MagicMock()
        mock_business.gid = "COMPANY_ID_MATCH"

        with patch.object(
            seeder, "_load_business", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = mock_business

            data = BusinessData(name="Some Name", company_id="ACME-001")
            result = asyncio.run(seeder._find_business_async(data))

            assert result is not None
            assert result.gid == "COMPANY_ID_MATCH"

            # Verify _load_business was called with the company_id match GID
            mock_load.assert_called_once_with("COMPANY_ID_MATCH")

    def test_find_business_falls_back_to_composite_match_when_no_company_id_match(
        self,
    ) -> None:
        """_find_business_async falls back to composite matching when company_id not matched.

        Per TDD-BusinessSeeder-v2: Tier 2 is now composite matching.
        """
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from autom8_asana.search.models import SearchHit, SearchResult

        # company_id search returns None
        # find_async returns candidates for composite matching
        candidate_hit = SearchHit(
            gid="COMPOSITE_MATCH",
            entity_type="Business",
            name="Joe's Pizza Palace",
            matched_fields={
                "name": "Joe's Pizza Palace",
                "email": "info@joespizza.com",
            },
        )
        search_result = SearchResult(
            hits=[candidate_hit],
            total_count=1,
            query_time_ms=1.0,
            from_cache=False,
        )

        client = MagicMock()
        # company_id search returns None
        client.search.find_one_async = AsyncMock(return_value=None)
        # find_async returns candidates
        client.search.find_async = AsyncMock(return_value=search_result)

        seeder = BusinessSeeder(client)

        mock_business = MagicMock()
        mock_business.gid = "COMPOSITE_MATCH"

        with patch.object(
            seeder, "_load_business", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = mock_business

            # Provide enough fields for composite matching to find a match
            data = BusinessData(
                name="Joe's Pizza",
                company_id="NOTFOUND-001",
                email="info@joespizza.com",  # Matching email
            )
            result = asyncio.run(seeder._find_business_async(data))

            assert result is not None
            assert result.gid == "COMPOSITE_MATCH"
            mock_load.assert_called_once_with("COMPOSITE_MATCH")

    def test_find_business_uses_composite_match_when_no_company_id(self) -> None:
        """_find_business_async uses composite matching when no company_id provided.

        Per TDD-BusinessSeeder-v2: Uses composite matching with corroborating fields.
        """
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from autom8_asana.search.models import SearchHit, SearchResult

        candidate_hit = SearchHit(
            gid="COMPOSITE_ONLY_MATCH",
            entity_type="Business",
            name="Acme Corporation",
            matched_fields={
                "name": "Acme Corporation",
                "email": "info@acme.com",
                "phone": "+15551234567",
            },
        )
        search_result = SearchResult(
            hits=[candidate_hit],
            total_count=1,
            query_time_ms=1.0,
            from_cache=False,
        )

        client = MagicMock()
        # find_async returns candidates for composite matching
        client.search.find_async = AsyncMock(return_value=search_result)

        seeder = BusinessSeeder(client)

        mock_business = MagicMock()
        mock_business.gid = "COMPOSITE_ONLY_MATCH"

        with patch.object(
            seeder, "_load_business", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = mock_business

            # No company_id provided, but email and phone for composite matching
            data = BusinessData(
                name="Acme Corp",
                email="info@acme.com",
                phone="+15551234567",
            )
            result = asyncio.run(seeder._find_business_async(data))

            assert result is not None
            assert result.gid == "COMPOSITE_ONLY_MATCH"

            # find_one_async should not be called (no company_id)
            # find_async is called for candidate retrieval
            client.search.find_async.assert_called_once()

    def test_find_business_returns_none_when_both_searches_fail(self) -> None:
        """_find_business_async returns None when both tiers find no match."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        client.search.find_one_async = AsyncMock(return_value=None)

        seeder = BusinessSeeder(client)

        data = BusinessData(name="Nonexistent Business", company_id="NOTFOUND-999")
        result = asyncio.run(seeder._find_business_async(data))

        assert result is None

    def test_load_business_calls_from_gid_async(self) -> None:
        """_load_business calls Business.from_gid_async with hydrate=False."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        client = MagicMock()
        seeder = BusinessSeeder(client)

        mock_business = MagicMock()
        mock_business.gid = "123456789"

        # Patch the Business class where it's imported in the seeder module
        with patch(
            "autom8_asana.models.business.business.Business.from_gid_async",
            new_callable=AsyncMock,
        ) as mock_from_gid:
            mock_from_gid.return_value = mock_business

            result = asyncio.run(seeder._load_business("123456789"))

            # Verify from_gid_async was called with hydrate=False
            mock_from_gid.assert_called_once_with(client, "123456789", hydrate=False)
            assert result.gid == "123456789"
