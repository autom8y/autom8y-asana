"""Regression tests for the scheduling-posture re-source (OFFER_SCHEMA 1.6.0).

Locks the fix for the degenerate 1.5.0 defect: custom_cal_status + the eight
CASCADE_PRIORITY provider columns were sourced ``cf:`` off the Offer's OWN manifest
with snake_case names -- WRONG LEVEL (the fields live on the office-level UnitHolder
ancestor) AND WRONG NAME (real Asana names are Title Case). Every projected row
resolved null, so the whole-source push was degenerate (all enrolled=true /
stratum='inactive'). 1.6.0 sources them ``cascade:<Real Display Name>`` off the
registered ``UnitHolder.CascadingFields``.

These tests are LEVEL + NAME regression teeth:
  * the schema declares ``cascade:`` (never ``cf:``) for the nine columns;
  * each cascade source resolves to a UnitHolder-owned CascadingFieldDef;
  * the cascade READ actually pulls the value off a UNIT_HOLDER ancestor, skipping a
    present-but-null Unit level (the live-verified topology).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.fields import get_cascading_field
from tests._shared.mocks import MockTask

# Column name (snake, the frame column / dict key) -> real Asana display name (the
# cascade source, verified live on the "…Business Units 🔎" UnitHolder task).
SCHEDULING_COLUMN_TO_DISPLAY: dict[str, str] = {
    "custom_cal_status": "Custom Cal Status",
    "reviewwave_id": "ReviewWave ID",
    "acuity_cal_url": "Acuity Cal URL",
    "calendly_url": "Calendly URL",
    "janeapp_url": "JaneApp URL",
    "ehr_cal_url": "EHR Cal URL",
    "trackstat_id": "TrackStat ID",
    "sked_id": "Sked ID",
    "custom_ghl_id": "Custom GHL ID",
}


class _NameGid:
    """Minimal parent reference (gid-only) for the mocked parent chain."""

    def __init__(self, gid: str) -> None:
        self.gid = gid
        self.name: str | None = None


def _text_cf(name: str, value: Any) -> dict[str, Any]:
    return {
        "gid": f"cf_{name.lower().replace(' ', '_')}",
        "name": name,
        "resource_subtype": "text",
        "text_value": value,
    }


# --- schema shape: cascade sourcing at the real display names (NAME + LEVEL teeth) ---


def _offer_column(name: str) -> Any:
    for col in OFFER_SCHEMA.columns:
        if col.name == name:
            return col
    raise AssertionError(f"offer schema missing column {name!r}")


@pytest.mark.parametrize(("column", "display"), sorted(SCHEDULING_COLUMN_TO_DISPLAY.items()))
def test_scheduling_column_is_cascade_sourced_at_real_display_name(
    column: str, display: str
) -> None:
    """Each scheduling column sources ``cascade:<Real Display Name>`` -- NOT ``cf:``.

    The 1.5.0 defect was ``cf:<snake>`` (wrong level + wrong name). This locks BOTH the
    cascade prefix (ancestor traversal, not the Offer's own manifest) AND the exact
    Title-Case display name the lower()/strip() cascade match requires.
    """
    col = _offer_column(column)
    assert col.source == f"cascade:{display}", (
        f"offer column {column!r} must source 'cascade:{display}' (1.6.0 re-source); "
        f"got {col.source!r}. A regression to 'cf:' or snake_case reintroduces the "
        f"degenerate all-null projection."
    )


def test_no_scheduling_column_reverts_to_cf_source() -> None:
    """Regression teeth: none of the nine scheduling columns may use a ``cf:`` source."""
    offenders = [
        (col.name, col.source)
        for col in OFFER_SCHEMA.columns
        if col.name in SCHEDULING_COLUMN_TO_DISPLAY and (col.source or "").lower().startswith("cf:")
    ]
    assert not offenders, (
        f"scheduling columns reverted to cf: sourcing (the 1.5.0 wrong-level defect): {offenders}"
    )


def test_company_id_still_cascade_company_id() -> None:
    """company_id was correct in 1.5.0 (cascade:Company ID) and must be untouched."""
    assert _offer_column("company_id").source == "cascade:Company ID"


def test_offer_schema_version_bumped_to_invalidate_degenerate_cache() -> None:
    """The re-source bumps the schema version so the stale degenerate S3 frame invalidates."""
    assert OFFER_SCHEMA.version == "1.6.0"


# --- registry: the cascade sources resolve to UnitHolder-owned definitions ----------


@pytest.mark.parametrize(("column", "display"), sorted(SCHEDULING_COLUMN_TO_DISPLAY.items()))
def test_scheduling_cascade_field_owned_by_unit_holder(column: str, display: str) -> None:
    """Every scheduling cascade source resolves to a UnitHolder CascadingFieldDef.

    Owner MUST be UnitHolder (the level where the value is POPULATED live) -- NOT Unit
    (present-but-null there) nor Business (absent there). Registering on the wrong owner
    would re-null the projection while passing the schema-source audit.
    """
    result = get_cascading_field(display)
    assert result is not None, f"cascade source {display!r} not registered"
    owner_class, field_def = result
    assert owner_class.__name__ == "UnitHolder", (
        f"{display!r} must be owned by UnitHolder (populated level); got {owner_class.__name__}"
    )
    assert field_def.name == display


# --- cascade READ: value pulled off UNIT_HOLDER, skipping a present-but-null Unit ----


def _offer_unit_unitholder_chain(
    *, unit_holder_fields: list[dict[str, Any]], unit_fields: list[dict[str, Any]]
) -> tuple[MockTask, MagicMock]:
    """Build the live-verified Offer -> Unit -> UnitHolder parent chain + a mock client."""
    unit_holder = MockTask(gid="uh", name="Acme Business Units", custom_fields=unit_holder_fields)
    unit = MockTask(gid="u", name="Acme — Chiro", parent=_NameGid("uh"), custom_fields=unit_fields)
    offer = MockTask(gid="o", name="Offer", parent=_NameGid("u"), custom_fields=[])
    parents = {"u": unit, "uh": unit_holder}
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock(side_effect=lambda gid, **_k: parents[gid])
    return offer, client


async def test_custom_cal_status_resolves_off_unit_holder_skipping_null_unit() -> None:
    """custom_cal_status resolves to the UnitHolder value, NOT the present-but-null Unit.

    Mirrors the live topology: the field is present-but-null on the Unit (L2) and
    POPULATED on the UnitHolder (L3, 'Enabled'). The resolver must traverse past the
    Unit and return the UnitHolder value.
    """
    offer, client = _offer_unit_unitholder_chain(
        unit_holder_fields=[_text_cf("Custom Cal Status", "Enabled")],
        unit_fields=[_text_cf("Custom Cal Status", None)],  # present-but-null at Unit
    )
    resolver = CascadingFieldResolver(client)
    with patch("autom8_asana.dataframes.resolver.cascading.detect_entity_type") as mock_detect:
        mock_detect.side_effect = [
            MagicMock(entity_type=EntityType.OFFER),
            MagicMock(entity_type=EntityType.UNIT),
            MagicMock(entity_type=EntityType.UNIT_HOLDER),
        ]
        value = await resolver.resolve_async(offer, "Custom Cal Status")  # type: ignore[arg-type]
    assert value == "Enabled"


async def test_provider_resolves_off_unit_holder() -> None:
    """A CASCADE_PRIORITY provider (Calendly URL) resolves off the UnitHolder ancestor."""
    offer, client = _offer_unit_unitholder_chain(
        unit_holder_fields=[_text_cf("Calendly URL", "https://cal/acme")],
        unit_fields=[],
    )
    resolver = CascadingFieldResolver(client)
    with patch("autom8_asana.dataframes.resolver.cascading.detect_entity_type") as mock_detect:
        mock_detect.side_effect = [
            MagicMock(entity_type=EntityType.OFFER),
            MagicMock(entity_type=EntityType.UNIT),
            MagicMock(entity_type=EntityType.UNIT_HOLDER),
        ]
        value = await resolver.resolve_async(offer, "Calendly URL")  # type: ignore[arg-type]
    assert value == "https://cal/acme"


async def test_snake_name_does_not_resolve_the_1_5_0_defect() -> None:
    """Two-sided: the OLD snake name (custom_cal_status) matches NOTHING -> None.

    Demonstrates WHY 1.5.0 was degenerate even had it used cascade:: the lower()/strip()
    name match never folds snake_case to the real 'Custom Cal Status' display name, so a
    snake-named source resolves null off every ancestor. (The field is unregistered under
    the snake name, so the resolver short-circuits to None without traversing.)
    """
    offer, client = _offer_unit_unitholder_chain(
        unit_holder_fields=[_text_cf("Custom Cal Status", "Enabled")],
        unit_fields=[],
    )
    resolver = CascadingFieldResolver(client)
    value = await resolver.resolve_async(offer, "custom_cal_status")  # type: ignore[arg-type]
    assert value is None
    client.tasks.get_async.assert_not_called()
