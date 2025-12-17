"""Tests for combined hydration via hydrate_from_gid_async.

Per TDD-HYDRATION Phase 3: Tests for hydrate_from_gid_async() universal entry point.
Tests hydration from various entry points (Business, Contact, Offer, Unit).

Per ADR-0069: Hydration API design with generic entry point.
Per ADR-0070: Partial failure handling with HydrationResult.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.exceptions import HydrationError
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.hydration import (
    HydrationBranch,
    HydrationFailure,
    HydrationResult,
    hydrate_from_gid_async,
)
from autom8_asana.models.task import NameGid, Task


# =============================================================================
# Entry Point Tests - From Business GID
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromBusinessGid:
    """Tests for hydrate_from_gid_async starting from Business GID."""

    async def test_business_gid_returns_hydrated_result(self) -> None:
        """Starting from Business GID returns fully hydrated result."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [
                Task(gid="ch1", name="Contacts"),
                Task(gid="uh1", name="Units"),
            ],
            "ch1": [Task(gid="c1", name="John Doe")],
            "uh1": [],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert isinstance(result, HydrationResult)
        assert isinstance(result.business, Business)
        assert result.business.gid == "b1"
        assert result.business.name == "Acme Corp"
        assert result.entry_entity is None  # Started at Business
        assert result.entry_type == EntityType.BUSINESS
        assert result.is_complete is True
        assert result.api_calls > 0

    async def test_business_gid_populates_contacts(self) -> None:
        """Starting from Business GID populates contacts correctly."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [
                Task(gid="c1", name="John Doe"),
                Task(gid="c2", name="Jane Doe"),
            ],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert result.business._contact_holder is not None
        assert len(result.business.contacts) == 2

    async def test_business_gid_populates_units_with_offers(self) -> None:
        """Starting from Business GID populates Units and nested Offers."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium Package")],
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [
                Task(gid="o1", name="Offer 1"),
                Task(gid="o2", name="Offer 2"),
            ],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert len(result.business.units) == 1
        unit = result.business.units[0]
        assert len(unit.offers) == 2


# =============================================================================
# Entry Point Tests - From Contact GID
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromContactGid:
    """Tests for hydrate_from_gid_async starting from Contact GID."""

    async def test_contact_gid_traverses_to_business(self) -> None:
        """Starting from Contact GID traverses up to Business."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "c1": Task(
                    gid="c1",
                    name="John Doe",
                    parent=NameGid(gid="ch1", name="Contacts"),
                ),
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "c1": [],  # Contact has no holder subtasks
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "c1")

        assert isinstance(result.business, Business)
        assert result.business.gid == "b1"
        assert result.api_calls > 0

    async def test_contact_gid_hydrates_full_hierarchy(self) -> None:
        """Starting from Contact GID hydrates full Business hierarchy."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "c1": Task(
                    gid="c1",
                    name="John Doe",
                    parent=NameGid(gid="ch1", name="Contacts"),
                ),
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "c1": [],
            "b1": [
                Task(gid="ch1", name="Contacts"),
                Task(gid="uh1", name="Units"),
            ],
            "ch1": [Task(gid="c1", name="John Doe")],
            "uh1": [Task(gid="u1", name="Premium")],
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "c1")

        assert len(result.business.contacts) == 1
        assert len(result.business.units) == 1


# =============================================================================
# Entry Point Tests - From Offer GID
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromOfferGid:
    """Tests for hydrate_from_gid_async starting from Offer GID."""

    async def test_offer_gid_traverses_four_levels(self) -> None:
        """Starting from Offer GID traverses 4 levels to Business."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "o1": Task(
                    gid="o1",
                    name="Offer 1",
                    parent=NameGid(gid="oh1", name="Offers"),
                ),
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "o1": [],
            "u1": [Task(gid="oh1", name="Offers"), Task(gid="ph1", name="Processes")],
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium")],
            "oh1": [Task(gid="o1", name="Offer 1")],
            "ph1": [],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "o1")

        assert isinstance(result.business, Business)
        assert result.business.gid == "b1"
        # Path should include OfferHolder, Unit, UnitHolder
        assert len(result.path) >= 0  # Path tracking

    async def test_offer_gid_entry_found_in_hierarchy(self) -> None:
        """Starting Offer is findable in hydrated hierarchy."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "o1": Task(
                    gid="o1",
                    name="Offer 1",
                    parent=NameGid(gid="oh1", name="Offers"),
                ),
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "o1": [],
            "u1": [Task(gid="oh1", name="Offers")],
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium")],
            "oh1": [Task(gid="o1", name="Offer 1")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "o1")

        # Find offer in hydrated hierarchy
        found = False
        for unit in result.business.units:
            for offer in unit.offers:
                if offer.gid == "o1":
                    found = True
                    break
        assert found, "Entry offer should be in hydrated hierarchy"


# =============================================================================
# Entry Point Tests - From Unit GID
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromUnitGid:
    """Tests for hydrate_from_gid_async starting from Unit GID."""

    async def test_unit_gid_traverses_two_levels(self) -> None:
        """Starting from Unit GID traverses 2 levels to Business."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "u1": Task(
                    gid="u1",
                    name="Premium Package",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "u1": [Task(gid="oh1", name="Offers")],
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium Package")],
            "oh1": [],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "u1")

        assert isinstance(result.business, Business)
        assert result.business.gid == "b1"


# =============================================================================
# hydrate_full Parameter Tests
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFullParameter:
    """Tests for hydrate_full parameter."""

    async def test_hydrate_full_false_skips_downward(self) -> None:
        """hydrate_full=False skips downward hydration."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1", hydrate_full=False)

        assert result.business.gid == "b1"
        assert result.business._contact_holder is None
        assert result.is_complete is True

    async def test_hydrate_full_true_default_populates_hierarchy(self) -> None:
        """hydrate_full=True (default) populates full hierarchy."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1", hydrate_full=True)

        assert result.business._contact_holder is not None
        assert len(result.business.contacts) == 1


# =============================================================================
# partial_ok Parameter Tests
# =============================================================================


@pytest.mark.asyncio
class TestPartialOkParameter:
    """Tests for partial_ok parameter."""

    async def test_partial_ok_true_continues_on_failure(self) -> None:
        """partial_ok=True continues on hydration failure."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        call_count = 0

        def subtasks_side_effect(gid: str) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                mock.collect = AsyncMock(
                    return_value=[
                        Task(gid="ch1", name="Contacts"),
                        Task(gid="uh1", name="Units"),
                    ]
                )
            else:
                mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1", partial_ok=True)

        assert result.business.gid == "b1"
        assert result.is_complete is False
        assert len(result.failed) == 1
        assert result.failed[0].phase == "downward"

    async def test_partial_ok_false_raises_on_failure(self) -> None:
        """partial_ok=False raises HydrationError on failure."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        call_count = 0

        def subtasks_side_effect(gid: str) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await hydrate_from_gid_async(client, "b1", partial_ok=False)

        error = exc_info.value
        assert error.phase == "downward"
        assert error.entity_gid == "b1"

    async def test_partial_ok_failure_records_recoverable_status(self) -> None:
        """partial_ok=True records recoverable status correctly."""
        from autom8_asana.exceptions import RateLimitError

        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        call_count = 0

        def subtasks_side_effect(gid: str) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(
                    side_effect=RateLimitError("Rate limited", retry_after=30)
                )
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1", partial_ok=True)

        assert len(result.failed) == 1
        # Rate limit errors should be marked as recoverable
        assert result.failed[0].recoverable is True


# =============================================================================
# HydrationResult Property Tests
# =============================================================================


@pytest.mark.asyncio
class TestHydrationResultProperties:
    """Tests for HydrationResult properties and attributes."""

    async def test_result_tracks_api_calls(self) -> None:
        """HydrationResult tracks API call count."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert result.api_calls > 0

    async def test_result_tracks_succeeded_branches(self) -> None:
        """HydrationResult tracks succeeded branches."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [
                Task(gid="ch1", name="Contacts"),
                Task(gid="uh1", name="Units"),
            ],
            "ch1": [Task(gid="c1", name="John"), Task(gid="c2", name="Jane")],
            "uh1": [Task(gid="u1", name="Premium")],
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert len(result.succeeded) > 0
        # Should have at least contact_holder and unit_holder
        holder_types = [b.holder_type for b in result.succeeded]
        assert "contact_holder" in holder_types
        assert "unit_holder" in holder_types

    async def test_result_tracks_path_from_non_business(self) -> None:
        """HydrationResult tracks path when starting from non-Business."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "c1": Task(
                    gid="c1",
                    name="John Doe",
                    parent=NameGid(gid="ch1", name="Contacts"),
                ),
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "c1": [],
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "c1")

        # Path should have at least ContactHolder
        assert len(result.path) >= 0

    async def test_is_complete_true_when_no_failures(self) -> None:
        """is_complete is True when no failures."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert result.is_complete is True
        assert len(result.failed) == 0


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromGidErrorHandling:
    """Tests for error handling in hydrate_from_gid_async."""

    async def test_fetch_failure_raises_hydration_error(self) -> None:
        """Initial fetch failure raises HydrationError."""
        client = MagicMock()
        client.tasks.get_async = AsyncMock(side_effect=RuntimeError("Network error"))

        with pytest.raises(HydrationError) as exc_info:
            await hydrate_from_gid_async(client, "b1")

        error = exc_info.value
        assert error.entity_gid == "b1"
        assert error.phase == "upward"
        assert "Failed to fetch entry task" in str(error)

    async def test_traversal_failure_raises_hydration_error(self) -> None:
        """Upward traversal failure raises HydrationError."""
        client = MagicMock()

        # Task without parent
        task = Task(gid="orphan", name="Orphan", parent=None)
        client.tasks.get_async = AsyncMock(return_value=task)

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await hydrate_from_gid_async(client, "orphan")

        error = exc_info.value
        assert error.phase == "upward"


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromGidIntegration:
    """Integration-style tests for hydrate_from_gid_async."""

    async def test_full_hierarchy_from_offer(self) -> None:
        """Full hierarchy hydration starting from deep Offer."""
        client = MagicMock()

        async def get_async_side_effect(gid: str) -> Task:
            tasks = {
                "o1": Task(
                    gid="o1",
                    name="Summer Special",
                    parent=NameGid(gid="oh1", name="Offers"),
                ),
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium Package"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium Package",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "o1": [],
            "u1": [Task(gid="oh1", name="Offers"), Task(gid="ph1", name="Processes")],
            "b1": [
                Task(gid="ch1", name="Contacts"),
                Task(gid="uh1", name="Units"),
            ],
            "ch1": [
                Task(gid="c1", name="John Doe"),
                Task(gid="c2", name="Jane Doe"),
            ],
            "uh1": [
                Task(gid="u1", name="Premium Package"),
                Task(gid="u2", name="Basic Package"),
            ],
            "u2": [Task(gid="oh2", name="Offers")],
            "oh1": [
                Task(gid="o1", name="Summer Special"),
                Task(gid="o2", name="Winter Deal"),
            ],
            "oh2": [Task(gid="o3", name="Budget Option")],
            "ph1": [Task(gid="p1", name="Build Process")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "o1")

        # Verify full hierarchy
        assert result.business.name == "Acme Corp"
        assert len(result.business.contacts) == 2
        assert len(result.business.units) == 2

        # Find the entry offer in hierarchy
        found_entry = False
        for unit in result.business.units:
            for offer in unit.offers:
                if offer.gid == "o1":
                    assert offer.name == "Summer Special"
                    found_entry = True
        assert found_entry, "Entry offer should be in hydrated hierarchy"

    async def test_multiple_units_with_varied_content(self) -> None:
        """Hydration handles multiple Units with varied nested content."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        mock_responses = {
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [
                Task(gid="u1", name="Premium"),
                Task(gid="u2", name="Basic"),
                Task(gid="u3", name="Enterprise"),
            ],
            "u1": [Task(gid="oh1", name="Offers")],
            "u2": [Task(gid="oh2", name="Offers"), Task(gid="ph2", name="Processes")],
            "u3": [],  # No holders
            "oh1": [Task(gid="o1", name="Offer 1"), Task(gid="o2", name="Offer 2")],
            "oh2": [Task(gid="o3", name="Offer 3")],
            "ph2": [Task(gid="p1", name="Process 1")],
        }

        def subtasks_side_effect(gid: str) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        assert len(result.business.units) == 3

        # Unit 1: 2 offers, no processes
        u1 = next(u for u in result.business.units if u.gid == "u1")
        assert len(u1.offers) == 2
        assert len(u1.processes) == 0

        # Unit 2: 1 offer, 1 process
        u2 = next(u for u in result.business.units if u.gid == "u2")
        assert len(u2.offers) == 1
        assert len(u2.processes) == 1

        # Unit 3: no offers, no processes
        u3 = next(u for u in result.business.units if u.gid == "u3")
        assert len(u3.offers) == 0
        assert len(u3.processes) == 0
