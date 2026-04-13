"""Tests for CascadingSectionService.

Covers:
- All 3 section types updated (offer, unit, business)
- Missing section config -> skip that entity
- Section not found in project -> log warning, continue
- API failure -> log warning, continue
- Only configured sections are updated (partial config)
- Case-insensitive section name matching
- Entity with no memberships -> warning, continue
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.lifecycle.config import CascadingSectionConfig
from autom8_asana.lifecycle.sections import CascadingSectionService


def _make_section(gid: str, name: str) -> MagicMock:
    """Create a mock section with gid and name."""
    section = MagicMock()
    section.gid = gid
    section.name = name
    return section


def _make_entity(gid: str, project_gid: str = "proj1") -> MagicMock:
    """Create a mock entity with gid and memberships."""
    entity = MagicMock()
    entity.gid = gid
    entity.memberships = [
        {
            "project": {"gid": project_gid, "name": "Test Project"},
            "section": {"gid": "sec_orig", "name": "Original"},
        }
    ]
    return entity


def _setup_sections(
    mock_client: MagicMock, sections_by_project: dict[str, list[MagicMock]]
) -> None:
    """Configure mock client to return specific sections per project.

    Args:
        mock_client: The mock Asana client.
        sections_by_project: Maps project_gid to list of mock sections.
    """

    def _list_for_project(project_gid: str) -> MagicMock:
        result = MagicMock()
        sections = sections_by_project.get(project_gid, [])
        result.collect = AsyncMock(return_value=sections)
        return result

    mock_client.sections.list_for_project_async = MagicMock(side_effect=_list_for_project)


# --- Test: All 3 section types updated ---


@pytest.mark.asyncio
async def test_cascade_all_three_entities(mock_client, mock_resolution_context):
    """When offer, unit, and business sections are configured, all three
    entities are resolved and moved to their target sections."""
    # Set up entities with memberships
    offer = _make_entity("offer1", "offer_proj")
    unit = _make_entity("unit1", "unit_proj")
    business = _make_entity("biz1", "biz_proj")

    mock_resolution_context.offer_async = AsyncMock(return_value=offer)
    mock_resolution_context.unit_async = AsyncMock(return_value=unit)
    mock_resolution_context.business_async = AsyncMock(return_value=business)

    # Set up sections per project
    _setup_sections(
        mock_client,
        {
            "offer_proj": [_make_section("s1", "Sales Process")],
            "unit_proj": [_make_section("s2", "Next Steps")],
            "biz_proj": [_make_section("s3", "OPPORTUNITY")],
        },
    )
    mock_client.sections.add_task_async = AsyncMock()

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(
        offer="Sales Process", unit="Next Steps", business="OPPORTUNITY"
    )

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 3
    assert "offer1" in result.updates
    assert "unit1" in result.updates
    assert "biz1" in result.updates
    assert len(result.warnings) == 0

    # Verify each entity was moved to correct section
    calls = mock_client.sections.add_task_async.call_args_list
    assert len(calls) == 3
    assert calls[0] == (("s1",), {"task": "offer1"})
    assert calls[1] == (("s2",), {"task": "unit1"})
    assert calls[2] == (("s3",), {"task": "biz1"})


# --- Test: Missing section config -> skip entity ---


@pytest.mark.asyncio
async def test_cascade_skips_unconfigured_entities(mock_client, mock_resolution_context):
    """When only some sections are configured, only those entities
    are resolved and updated. Others are skipped entirely."""
    unit = _make_entity("unit1", "unit_proj")
    mock_resolution_context.unit_async = AsyncMock(return_value=unit)

    _setup_sections(
        mock_client,
        {
            "unit_proj": [_make_section("s1", "Onboarding")],
        },
    )
    mock_client.sections.add_task_async = AsyncMock()

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer=None, unit="Onboarding", business=None)

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 1
    assert "unit1" in result.updates
    assert len(result.warnings) == 0

    # offer_async and business_async should never be called
    mock_resolution_context.offer_async.assert_not_awaited()
    mock_resolution_context.business_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_cascade_empty_config_does_nothing(mock_client, mock_resolution_context):
    """When no sections are configured, no entities are resolved."""
    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig()

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 0
    assert len(result.warnings) == 0


# --- Test: Section not found in project -> warning ---


@pytest.mark.asyncio
async def test_cascade_section_not_found_logs_warning(mock_client, mock_resolution_context):
    """When the target section name does not exist in the entity's project,
    a warning is recorded and the entity is not moved."""
    offer = _make_entity("offer1", "offer_proj")
    mock_resolution_context.offer_async = AsyncMock(return_value=offer)

    # Return sections that do NOT match the config
    _setup_sections(
        mock_client,
        {
            "offer_proj": [_make_section("s1", "Other Section")],
        },
    )

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="Sales Process")

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 0
    assert len(result.warnings) == 1
    assert "Sales Process" in result.warnings[0]
    assert "offer" in result.warnings[0]


@pytest.mark.asyncio
async def test_cascade_empty_sections_list(mock_client, mock_resolution_context):
    """When the project has no sections at all, a warning is recorded."""
    offer = _make_entity("offer1", "offer_proj")
    mock_resolution_context.offer_async = AsyncMock(return_value=offer)

    _setup_sections(
        mock_client,
        {
            "offer_proj": [],
        },
    )

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="Sales Process")

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 0
    assert len(result.warnings) == 1


# --- Test: API failure -> warning, continue ---


@pytest.mark.asyncio
async def test_cascade_entity_resolution_error(mock_client, mock_resolution_context):
    """When entity resolution fails, a warning is logged and remaining
    entities are still processed (fail-forward)."""
    # Offer resolution fails
    mock_resolution_context.offer_async = AsyncMock(side_effect=ConnectionError("Entity not found"))

    # Unit resolves successfully
    unit = _make_entity("unit1", "unit_proj")
    mock_resolution_context.unit_async = AsyncMock(return_value=unit)

    _setup_sections(
        mock_client,
        {
            "unit_proj": [_make_section("s1", "Next Steps")],
        },
    )
    mock_client.sections.add_task_async = AsyncMock()

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="Sales Process", unit="Next Steps")

    result = await service.cascade_async(config, mock_resolution_context)

    # Unit should still succeed despite offer failure
    assert len(result.updates) == 1
    assert "unit1" in result.updates
    assert len(result.warnings) == 1
    assert "offer" in result.warnings[0]


@pytest.mark.asyncio
async def test_cascade_add_task_api_error(mock_client, mock_resolution_context):
    """When the Asana add_task API call fails, a warning is recorded
    and remaining entities are processed."""
    offer = _make_entity("offer1", "offer_proj")
    unit = _make_entity("unit1", "unit_proj")
    mock_resolution_context.offer_async = AsyncMock(return_value=offer)
    mock_resolution_context.unit_async = AsyncMock(return_value=unit)

    _setup_sections(
        mock_client,
        {
            "offer_proj": [_make_section("s1", "Sales Process")],
            "unit_proj": [_make_section("s2", "Next Steps")],
        },
    )

    # First add_task call fails, second succeeds
    mock_client.sections.add_task_async = AsyncMock(
        side_effect=[ConnectionError("API error"), None]
    )

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="Sales Process", unit="Next Steps")

    result = await service.cascade_async(config, mock_resolution_context)

    # Offer failed, unit succeeded
    assert len(result.updates) == 1
    assert "unit1" in result.updates
    assert len(result.warnings) == 1
    assert "offer" in result.warnings[0]


# --- Test: Case-insensitive section matching ---


@pytest.mark.asyncio
async def test_cascade_case_insensitive_section_match(mock_client, mock_resolution_context):
    """Section names are matched case-insensitively."""
    business = _make_entity("biz1", "biz_proj")
    mock_resolution_context.business_async = AsyncMock(return_value=business)

    # Section name has different case than config
    _setup_sections(
        mock_client,
        {
            "biz_proj": [_make_section("s1", "opportunity")],
        },
    )
    mock_client.sections.add_task_async = AsyncMock()

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(business="OPPORTUNITY")

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 1
    assert "biz1" in result.updates
    mock_client.sections.add_task_async.assert_awaited_once_with("s1", task="biz1")


# --- Test: Entity with no memberships ---


@pytest.mark.asyncio
async def test_cascade_entity_no_memberships(mock_client, mock_resolution_context):
    """When an entity has no memberships, a warning is recorded."""
    offer = MagicMock()
    offer.gid = "offer1"
    offer.memberships = []
    mock_resolution_context.offer_async = AsyncMock(return_value=offer)

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="Sales Process")

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 0
    assert len(result.warnings) == 1
    assert "offer" in result.warnings[0]


# --- Test: Entity with memberships but no project GID ---


@pytest.mark.asyncio
async def test_cascade_entity_no_project_gid(mock_client, mock_resolution_context):
    """When an entity's memberships have no project GID, a warning is recorded."""
    offer = MagicMock()
    offer.gid = "offer1"
    offer.memberships = [{"project": {}, "section": {"gid": "s1"}}]
    mock_resolution_context.offer_async = AsyncMock(return_value=offer)

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="Sales Process")

    result = await service.cascade_async(config, mock_resolution_context)

    assert len(result.updates) == 0
    assert len(result.warnings) == 1


# --- Test: Onboarding stage section mapping (integration-style) ---


@pytest.mark.asyncio
async def test_cascade_onboarding_stage_sections(mock_client, mock_resolution_context):
    """Verify the correct sections for Onboarding stage per Appendix C:
    Offer=ACTIVATING, Unit=Onboarding, Business=ONBOARDING."""
    offer = _make_entity("offer1", "offer_proj")
    unit = _make_entity("unit1", "unit_proj")
    business = _make_entity("biz1", "biz_proj")

    mock_resolution_context.offer_async = AsyncMock(return_value=offer)
    mock_resolution_context.unit_async = AsyncMock(return_value=unit)
    mock_resolution_context.business_async = AsyncMock(return_value=business)

    _setup_sections(
        mock_client,
        {
            "offer_proj": [_make_section("s1", "ACTIVATING")],
            "unit_proj": [_make_section("s2", "Onboarding")],
            "biz_proj": [_make_section("s3", "ONBOARDING")],
        },
    )
    mock_client.sections.add_task_async = AsyncMock()

    service = CascadingSectionService(mock_client)
    config = CascadingSectionConfig(offer="ACTIVATING", unit="Onboarding", business="ONBOARDING")

    result = await service.cascade_async(config, mock_resolution_context)

    assert result.updates == ["offer1", "unit1", "biz1"]
    assert len(result.warnings) == 0
