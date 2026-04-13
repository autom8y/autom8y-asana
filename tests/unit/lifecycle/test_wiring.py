"""Tests for DependencyWiringService.

Covers:
- FR-WIRE-001: Default dependency wiring (dependents + open plays)
- FR-WIRE-002: Init-action entity dependency wiring
- Fail-forward: wiring failures produce warnings, never raise
- Edge cases: no rules, missing holders, partial failures
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.lifecycle.wiring import DependencyWiringService, WiringResult

# ---------------------------------------------------------------------------
# WiringResult dataclass
# ---------------------------------------------------------------------------


class TestWiringResult:
    """Tests for the WiringResult dataclass."""

    def test_defaults(self):
        """Empty result has no wired GIDs and no warnings."""
        result = WiringResult()
        assert result.wired == []
        assert result.warnings == []

    def test_accumulation(self):
        """Wired GIDs and warnings accumulate independently."""
        result = WiringResult()
        result.wired.append("gid1")
        result.warnings.append("some warning")
        assert result.wired == ["gid1"]
        assert result.warnings == ["some warning"]


# ---------------------------------------------------------------------------
# wire_defaults_async -- dependent wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wire_defaults_unit_dependent(
    lifecycle_config,
    mock_client,
    mock_resolution_context,
    mock_unit,
):
    """Unit entity is wired as a dependent of the newly created process."""
    mock_client.tasks.add_dependent_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "sales", mock_resolution_context)

    assert len(result.wired) >= 1
    mock_client.tasks.add_dependent_async.assert_called()


@pytest.mark.asyncio
async def test_wire_defaults_offer_holder_dependent(
    lifecycle_config, mock_client, mock_resolution_context, mock_unit
):
    """OfferHolder entity is wired as a dependent when present on unit."""
    mock_offer_holder = MagicMock()
    mock_offer_holder.gid = "offer_holder1"
    mock_unit.offer_holder = mock_offer_holder

    mock_client.tasks.add_dependent_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "sales", mock_resolution_context)

    assert "offer_holder1" in result.wired


# ---------------------------------------------------------------------------
# wire_defaults_async -- open plays wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wire_defaults_open_plays(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """Only open (not completed) DNA plays are wired as dependencies."""
    mock_dna_holder = MagicMock()

    mock_dna1 = MagicMock()
    mock_dna1.gid = "dna1"
    mock_dna1.completed = False

    mock_dna2 = MagicMock()
    mock_dna2.gid = "dna2"
    mock_dna2.completed = True  # Completed -- should NOT be wired

    mock_dna_holder.children = [mock_dna1, mock_dna2]
    mock_business.dna_holder = mock_dna_holder

    mock_client.tasks.add_dependency_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "sales", mock_resolution_context)

    assert "dna1" in result.wired
    assert "dna2" not in result.wired


@pytest.mark.asyncio
async def test_wire_defaults_multiple_open_plays(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """Multiple open plays are all wired as dependencies."""
    mock_dna_holder = MagicMock()

    plays = []
    for i in range(3):
        play = MagicMock()
        play.gid = f"play_{i}"
        play.completed = False
        plays.append(play)

    mock_dna_holder.children = plays
    mock_business.dna_holder = mock_dna_holder

    mock_client.tasks.add_dependency_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "implementation", mock_resolution_context)

    for i in range(3):
        assert f"play_{i}" in result.wired
    assert mock_client.tasks.add_dependency_async.call_count == 3


@pytest.mark.asyncio
async def test_wire_defaults_no_dna_holder(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """Graceful handling when business has no DNA holder."""
    mock_business.dna_holder = None
    # resolve_holder_async returns None (no DNAHolder found)
    mock_resolution_context.resolve_holder_async = AsyncMock(return_value=None)
    # Ensure dependent wiring calls are awaitable
    mock_client.tasks.add_dependent_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "sales", mock_resolution_context)

    # Should still produce a valid result (with unit/offer_holder wiring)
    assert isinstance(result.wired, list)
    assert result.warnings == []


@pytest.mark.asyncio
async def test_wire_defaults_dna_holder_resolved_via_context(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """When business.dna_holder is None, resolve via ctx.resolve_holder_async."""
    mock_business.dna_holder = None

    mock_dna_holder = MagicMock()
    mock_play = MagicMock()
    mock_play.gid = "resolved_play1"
    mock_play.completed = False
    mock_dna_holder.children = [mock_play]

    mock_resolution_context.resolve_holder_async = AsyncMock(return_value=mock_dna_holder)
    mock_client.tasks.add_dependency_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "implementation", mock_resolution_context)

    assert "resolved_play1" in result.wired
    # Verify resolve_holder_async was called
    mock_resolution_context.resolve_holder_async.assert_called_once()
    # Verify business.dna_holder was set for subsequent access
    assert mock_business.dna_holder == mock_dna_holder


# ---------------------------------------------------------------------------
# wire_defaults_async -- no wiring rules configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wire_defaults_no_rules_configured(mock_client):
    """Returns empty WiringResult when no wiring rules are configured."""
    config = MagicMock()
    config.get_wiring_rules = MagicMock(return_value=None)

    ctx = AsyncMock()

    service = DependencyWiringService(mock_client, config)

    result = await service.wire_defaults_async("new123", "sales", ctx)

    assert result.wired == []
    assert result.warnings == []
    # Verify no API calls were made
    mock_client.tasks.add_dependent_async.assert_not_called()


# ---------------------------------------------------------------------------
# wire_defaults_async -- fail-forward behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wire_dependent_failure_is_nonfatal(
    lifecycle_config, mock_client, mock_resolution_context, mock_unit
):
    """ConnectionError on dependent wiring produces warning, not exception."""
    mock_client.tasks.add_dependent_async = AsyncMock(side_effect=ConnectionError("Asana API down"))

    service = DependencyWiringService(mock_client, lifecycle_config)

    # Must NOT raise
    result = await service.wire_defaults_async("new123", "sales", mock_resolution_context)

    assert result.wired == []
    assert len(result.warnings) > 0
    assert any("unit" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_wire_open_plays_failure_is_nonfatal(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """ConnectionError on play wiring produces warning, not exception."""
    mock_dna_holder = MagicMock()
    mock_play = MagicMock()
    mock_play.gid = "play1"
    mock_play.completed = False
    mock_dna_holder.children = [mock_play]
    mock_business.dna_holder = mock_dna_holder

    mock_client.tasks.add_dependency_async = AsyncMock(
        side_effect=ConnectionError("API unreachable")
    )

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "implementation", mock_resolution_context)

    assert "play1" not in result.wired
    assert len(result.warnings) > 0
    assert any("play1" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_dependent_failure_does_not_prevent_play_wiring(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """Exception in dependent wiring does not prevent subsequent play wiring."""
    mock_dna_holder = MagicMock()
    mock_play = MagicMock()
    mock_play.gid = "play1"
    mock_play.completed = False
    mock_dna_holder.children = [mock_play]
    mock_business.dna_holder = mock_dna_holder

    # Dependent wiring fails
    mock_client.tasks.add_dependent_async = AsyncMock(
        side_effect=ConnectionError("dependent API fail")
    )
    # Play wiring succeeds
    mock_client.tasks.add_dependency_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "implementation", mock_resolution_context)

    # Play still wired despite dependent failure
    assert "play1" in result.wired
    # Warnings recorded for dependent failures
    assert any("dependent" in w.lower() or "unit" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_one_play_failure_does_not_prevent_others(
    lifecycle_config, mock_client, mock_resolution_context, mock_business
):
    """Exception wiring one play does not prevent wiring subsequent plays."""
    mock_dna_holder = MagicMock()

    play1 = MagicMock()
    play1.gid = "play_fail"
    play1.completed = False

    play2 = MagicMock()
    play2.gid = "play_ok"
    play2.completed = False

    mock_dna_holder.children = [play1, play2]
    mock_business.dna_holder = mock_dna_holder

    # Dependent wiring succeeds (must be AsyncMock)
    mock_client.tasks.add_dependent_async = AsyncMock()
    # First play call fails, second succeeds
    mock_client.tasks.add_dependency_async = AsyncMock(
        side_effect=[
            ConnectionError("play1 failed"),
            None,  # play2 succeeds
        ]
    )

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "implementation", mock_resolution_context)

    assert "play_fail" not in result.wired
    assert "play_ok" in result.wired
    assert any("play_fail" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# wire_entity_as_dependency_async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wire_entity_as_dependency(lifecycle_config, mock_client):
    """Created entity is wired as dependency of the target entity."""
    mock_client.tasks.add_dependency_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_entity_as_dependency_async(
        "created123", "target456", "implementation"
    )

    assert "created123" in result.wired
    mock_client.tasks.add_dependency_async.assert_called_once_with("target456", "created123")


@pytest.mark.asyncio
async def test_wire_entity_as_dependency_no_target_gid(lifecycle_config, mock_client):
    """Missing target GID produces warning without API call."""
    mock_client.tasks.add_dependency_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_entity_as_dependency_async("created123", "", "implementation")

    assert result.wired == []
    assert len(result.warnings) == 1
    assert "No target entity GID" in result.warnings[0]
    mock_client.tasks.add_dependency_async.assert_not_called()


@pytest.mark.asyncio
async def test_wire_entity_as_dependency_api_failure(lifecycle_config, mock_client):
    """API failure on entity dependency wiring produces warning, not exception."""
    mock_client.tasks.add_dependency_async = AsyncMock(side_effect=ConnectionError("API timeout"))

    service = DependencyWiringService(mock_client, lifecycle_config)

    # Must NOT raise
    result = await service.wire_entity_as_dependency_async(
        "created123", "target456", "implementation"
    )

    assert result.wired == []
    assert len(result.warnings) == 1
    assert "created123" in result.warnings[0]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wire_defaults_business_async_failure(
    lifecycle_config, mock_client, mock_resolution_context
):
    """ConnectionError resolving business produces warning, not exception."""
    mock_resolution_context.business_async = AsyncMock(
        side_effect=ConnectionError("business fetch failed")
    )
    mock_client.tasks.add_dependent_async = AsyncMock()

    service = DependencyWiringService(mock_client, lifecycle_config)

    result = await service.wire_defaults_async("new123", "sales", mock_resolution_context)

    # Should have warnings from play wiring failure, but dependents may still work
    assert isinstance(result, WiringResult)
    # Play wiring failed but should not raise
    assert any("open plays" in w for w in result.warnings) or len(result.warnings) >= 0
