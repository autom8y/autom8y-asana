"""Entity Write API -- Adversarial Smoke Tests against LIVE Asana.

Exercises the full Entity Write pipeline (FieldWriteService -> Asana API)
against a real Offer entity. Tests registry discovery, field name resolution,
live writes with restore, enum resolution, error paths, and partial success.

Requirements:
    ASANA_PAT: Valid Asana Personal Access Token with write access.

Run with:
    .venv/bin/pytest tests/integration/test_entity_write_smoke.py -v --timeout=120 -x

WARNING: This test writes to a REAL Asana entity. It saves and restores
original values in finally blocks. If a test is interrupted mid-write,
manual restoration may be required for offer GID 1205571482650639.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.resolution.field_resolver import FieldResolver
from autom8_asana.resolution.write_registry import (
    CORE_FIELD_NAMES,
    EntityWriteRegistry,
)
from autom8_asana.services.errors import (
    EntityTypeMismatchError,
    NoValidFieldsError,
    TaskNotFoundError,
)
from autom8_asana.services.field_write_service import FieldWriteService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OFFER_GID = "1205571482650639"
OFFER_PROJECT_GID = "1143843662099250"
PROCESS_GID = "1209719836385072"
NONEXISTENT_GID = "9999999999999999"

# Task opt_fields needed for raw read-back
_READ_OPT_FIELDS = [
    "custom_fields",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.enum_options",
    "custom_fields.text_value",
    "custom_fields.number_value",
    "custom_fields.enum_value",
    "custom_fields.multi_enum_values",
    "memberships.project.gid",
    "name",
    "notes",
]

# ---------------------------------------------------------------------------
# Skip + marker
# ---------------------------------------------------------------------------

ASANA_PAT = os.getenv("ASANA_PAT")

pytestmark = [
    pytest.mark.skipif(not ASANA_PAT, reason="ASANA_PAT not set"),
    pytest.mark.integration,
]

# Module-level cache for offer task data (avoid repeated fetches)
_cached_offer_task_data: dict[str, Any] | None = None

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def write_registry() -> EntityWriteRegistry:
    """Build the EntityWriteRegistry from the live entity registry."""
    return EntityWriteRegistry(get_registry())


@pytest.fixture
async def asana_client():
    """Create a real AsanaClient per-test (avoids event loop binding issues)."""
    from autom8_asana import AsanaClient

    client = AsanaClient(token=ASANA_PAT)
    yield client
    await client.close()


@pytest.fixture
async def offer_task_data(asana_client) -> dict[str, Any]:
    """Fetch the offer task data, caching at module level to reduce API calls."""
    global _cached_offer_task_data
    if _cached_offer_task_data is None:
        _cached_offer_task_data = await asana_client.tasks.get_async(
            OFFER_GID, raw=True, opt_fields=_READ_OPT_FIELDS
        )
    return _cached_offer_task_data


@pytest.fixture
async def write_service(asana_client, write_registry) -> FieldWriteService:
    """Create FieldWriteService wired to real client + registry."""
    return FieldWriteService(asana_client, write_registry)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_custom_field_value(
    task_data: dict[str, Any], display_name: str
) -> Any:
    """Extract a custom field value from raw task data by display name.

    Uses case-insensitive matching to handle descriptor name derivation
    differences (e.g., 'Weekly AD Spend' vs Asana's 'Weekly Ad Spend').
    """
    target = display_name.lower().strip()
    for cf in task_data.get("custom_fields", []):
        if cf.get("name", "").lower().strip() == target:
            subtype = cf.get("resource_subtype", "")
            if subtype == "text":
                return cf.get("text_value")
            elif subtype == "number":
                return cf.get("number_value")
            elif subtype == "enum":
                ev = cf.get("enum_value")
                return ev.get("name") if isinstance(ev, dict) else None
            elif subtype == "multi_enum":
                vals = cf.get("multi_enum_values") or []
                return [v.get("name") for v in vals if isinstance(v, dict)]
            else:
                return cf.get("display_value")
    return None


def _get_custom_field_def(
    task_data: dict[str, Any], display_name: str
) -> dict[str, Any] | None:
    """Get the full custom field definition dict by display name.

    Uses case-insensitive matching.
    """
    target = display_name.lower().strip()
    for cf in task_data.get("custom_fields", []):
        if cf.get("name", "").lower().strip() == target:
            return cf
    return None


async def _refetch_task_fresh(gid: str) -> dict[str, Any]:
    """Re-fetch a task using a FRESH client (bypasses cache).

    The TasksClient.get_async() caches responses. After a write, the cache
    contains stale data. Using a fresh client ensures we read from the API.
    See defect D-EW-001.
    """
    from autom8_asana import AsanaClient

    async with AsanaClient(token=ASANA_PAT) as fresh_client:
        return await fresh_client.tasks.get_async(
            gid, raw=True, opt_fields=_READ_OPT_FIELDS
        )


def _make_resolver(
    offer_task_data: dict[str, Any],
    write_registry: EntityWriteRegistry,
) -> FieldResolver:
    """Build a FieldResolver from real task data."""
    info = write_registry.get("offer")
    assert info is not None
    return FieldResolver(
        custom_fields_data=offer_task_data.get("custom_fields", []),
        descriptor_index=info.descriptor_index,
        core_fields=CORE_FIELD_NAMES,
    )


# =========================================================================
# Category 1: Registry Discovery (sync -- only uses write_registry)
# =========================================================================


class TestRegistryDiscovery:
    """Verify EntityWriteRegistry discovers expected entity types."""

    def test_offer_is_writable(self, write_registry: EntityWriteRegistry) -> None:
        """Offer should be discovered as writable."""
        assert write_registry.is_writable("offer"), (
            "EntityWriteRegistry did not discover 'offer' as writable"
        )

    def test_offer_project_gid_correct(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """Offer info should have the correct project GID."""
        info = write_registry.get("offer")
        assert info is not None
        assert info.project_gid == OFFER_PROJECT_GID

    def test_offer_descriptor_index_contains_expected_fields(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """Offer descriptor_index should contain key fields."""
        info = write_registry.get("offer")
        assert info is not None
        idx = info.descriptor_index

        expected_fields = [
            "asset_id",
            "weekly_ad_spend",
            "platforms",
            "language",
            "specialty",
            "optimize_for",
            "campaign_type",
            "algo_version",
            "cost",
            "ad_id",
        ]
        missing = [f for f in expected_fields if f not in idx]
        assert not missing, f"Missing descriptors in index: {missing}"

    def test_offer_descriptor_index_display_names(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """Descriptor index should map to correct Asana display names."""
        info = write_registry.get("offer")
        assert info is not None
        idx = info.descriptor_index

        assert idx.get("asset_id") == "Asset ID", (
            f"asset_id mapped to {idx.get('asset_id')!r}, expected 'Asset ID'"
        )
        assert idx.get("weekly_ad_spend") == "Weekly AD Spend", (
            f"weekly_ad_spend mapped to {idx.get('weekly_ad_spend')!r}, "
            "expected 'Weekly AD Spend'"
        )

    def test_process_is_not_writable(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """Process has PRIMARY_PROJECT_GID=None, should NOT be writable."""
        assert not write_registry.is_writable("process"), (
            "Process should NOT be writable (PRIMARY_PROJECT_GID is None)"
        )

    def test_is_writable_returns_false_for_nonexistent(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """is_writable should return False for unknown types."""
        assert not write_registry.is_writable("nonexistent_entity_type_xyz")

    def test_writable_types_returns_sorted_list(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """writable_types() should return a sorted list including offer."""
        types = write_registry.writable_types()
        assert isinstance(types, list)
        assert types == sorted(types), "writable_types() not sorted"
        assert "offer" in types

    def test_core_fields_on_offer_info(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """Offer WritableEntityInfo should expose CORE_FIELD_NAMES."""
        info = write_registry.get("offer")
        assert info is not None
        assert info.core_fields == CORE_FIELD_NAMES
        assert "name" in info.core_fields
        assert "notes" in info.core_fields


# =========================================================================
# Category 2: Field Name Resolution (Real Task -- async for offer_task_data)
# =========================================================================


class TestFieldNameResolution:
    """Test FieldResolver with REAL custom_fields data from the offer task."""

    async def test_descriptor_name_resolves(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """Descriptor name 'asset_id' should resolve to 'Asset ID' field."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"asset_id": "test"})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved", f"asset_id failed: {rf.error}"
        assert rf.matched_name == "Asset ID"
        assert rf.gid is not None
        assert not rf.is_core

    async def test_display_name_resolves_case_insensitive(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """Display name 'Weekly AD Spend' should resolve (case-insensitive)."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"Weekly AD Spend": 100})
        rf = results[0]
        assert rf.status == "resolved", f"Exact display name failed: {rf.error}"

    async def test_case_variations_resolve(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """Various case forms of 'ASSET ID' should resolve."""
        resolver = _make_resolver(offer_task_data, write_registry)
        variations = ["ASSET ID", "asset id", "Asset Id", "Asset ID"]
        for variant in variations:
            results = resolver.resolve_fields({variant: "test"})
            rf = results[0]
            assert rf.status == "resolved", (
                f"Case variation {variant!r} failed: {rf.error}"
            )

    async def test_snake_case_descriptor_maps_correctly(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """snake_case 'weekly_ad_spend' should map to 'Weekly AD Spend'."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"weekly_ad_spend": 50.0})
        rf = results[0]
        assert rf.status == "resolved", f"weekly_ad_spend failed: {rf.error}"
        assert rf.matched_name == "Weekly AD Spend"

    async def test_core_fields_resolve(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """Core fields 'name' and 'notes' should resolve."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"name": "test", "notes": "test"})
        for rf in results:
            assert rf.status == "resolved", (
                f"Core field {rf.input_name} failed: {rf.error}"
            )
            assert rf.is_core

    async def test_invalid_field_returns_skipped_with_suggestions(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """Nonexistent field should return 'skipped' with fuzzy suggestions."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"nonexistent_field_xyz": "val"})
        rf = results[0]
        assert rf.status == "skipped"
        assert rf.error is not None
        assert "not found" in rf.error.lower()

    async def test_typo_field_suggests_correct_name(
        self, offer_task_data: dict, write_registry: EntityWriteRegistry
    ) -> None:
        """Typo 'assset_id' (triple-s) should suggest 'Asset ID'."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"assset_id": "val"})
        rf = results[0]
        assert rf.status == "skipped"
        if rf.suggestions:
            suggestion_lower = [s.lower() for s in rf.suggestions]
            assert any(
                "asset" in s for s in suggestion_lower
            ), f"Expected 'Asset ID' in suggestions, got: {rf.suggestions}"


# =========================================================================
# Category 3: Live Writes to Offer (REAL API CALLS)
# =========================================================================


class TestLiveWrites:
    """Live writes to offer with save/restore semantics."""

    async def test_text_field_write(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write asset_id with test value, verify via fresh refetch, restore."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_value = _get_custom_field_value(original_task, "Asset ID")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": "SMOKE-TEST-001"},
                include_updated=True,
            )
            assert result.fields_written >= 1
            assert result.fields_skipped == 0

            # Verify via fresh client (bypasses cache)
            updated_task = await _refetch_task_fresh(OFFER_GID)
            updated_value = _get_custom_field_value(updated_task, "Asset ID")
            assert updated_value == "SMOKE-TEST-001", (
                f"Expected 'SMOKE-TEST-001', got {updated_value!r}"
            )

            # D-EW-001 FIXED: include_updated should return post-write data
            assert result.updated_fields is not None
            assert result.updated_fields.get("asset_id") == "SMOKE-TEST-001", (
                f"D-EW-001 regression: include_updated returned "
                f"{result.updated_fields.get('asset_id')!r}, expected 'SMOKE-TEST-001'"
            )
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": original_value or ""},
            )

    async def test_number_field_write(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write weekly_ad_spend with test value, verify via fresh refetch, restore."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_value = _get_custom_field_value(original_task, "Weekly AD Spend")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"weekly_ad_spend": 999.99},
                include_updated=True,
            )
            assert result.fields_written >= 1

            # Verify via fresh client (bypasses cache)
            updated_task = await _refetch_task_fresh(OFFER_GID)
            updated_value = _get_custom_field_value(updated_task, "Weekly AD Spend")
            assert updated_value is not None
            # Asana may round to integer precision depending on field config
            assert abs(float(updated_value) - 999.99) < 1.0, (
                f"Expected ~999.99 (within rounding), got {updated_value}"
            )

            # D-EW-001 FIXED: include_updated should return post-write data
            assert result.updated_fields is not None
            cached_spend = result.updated_fields.get("weekly_ad_spend")
            assert cached_spend is not None, (
                "D-EW-001 regression: include_updated weekly_ad_spend is None"
            )
            assert abs(float(cached_spend) - 999.99) < 1.0, (
                f"D-EW-001 regression: include_updated returned {cached_spend}, "
                f"expected ~999.99"
            )
        finally:
            restore_val = float(original_value) if original_value is not None else None
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"weekly_ad_spend": restore_val},
            )

    async def test_core_field_write_notes(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write 'notes' (core field), verify, restore."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_notes = original_task.get("notes", "")

        test_notes = "[SMOKE TEST] This is a temporary test note."
        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"notes": test_notes},
                include_updated=True,
            )
            assert result.fields_written >= 1

            updated_task = await _refetch_task_fresh(OFFER_GID)
            assert updated_task.get("notes") == test_notes
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"notes": original_notes},
            )

    async def test_null_clear_text_field(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write asset_id to a value then clear to None, verify, restore.

        NOTE: Originally tested algo_version but discovered D-EW-003:
        algo_version is declared as TextField() in the model but is actually
        an enum field in Asana (options: '1', '2'). Changed to asset_id
        which is a genuine text field.
        """
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_value = _get_custom_field_value(original_task, "Asset ID")

        try:
            # Set to a known value first
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": "NULL-CLEAR-TEST-001"},
            )
            task_after_set = await _refetch_task_fresh(OFFER_GID)
            val_after_set = _get_custom_field_value(task_after_set, "Asset ID")
            assert val_after_set == "NULL-CLEAR-TEST-001", (
                f"Expected 'NULL-CLEAR-TEST-001', got {val_after_set!r}"
            )

            # Now clear with None
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": None},
            )
            assert result.fields_written >= 1

            updated_task = await _refetch_task_fresh(OFFER_GID)
            cleared_value = _get_custom_field_value(updated_task, "Asset ID")
            assert cleared_value is None or cleared_value == "", (
                f"Expected None/empty after clear, got {cleared_value!r}"
            )
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": original_value or ""},
            )

    async def test_mixed_write_multiple_fields(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write asset_id + notes + weekly_ad_spend in ONE call, verify all, restore."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_asset_id = _get_custom_field_value(original_task, "Asset ID")
        original_notes = original_task.get("notes", "")
        original_spend = _get_custom_field_value(original_task, "Weekly AD Spend")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={
                    "asset_id": "MIXED-SMOKE-001",
                    "notes": "[SMOKE TEST] Mixed write test.",
                    "weekly_ad_spend": 777.77,
                },
            )
            assert result.fields_written == 3, (
                f"Expected 3 fields written, got {result.fields_written}"
            )
            assert result.fields_skipped == 0

            # Verify via fresh client (bypasses cache)
            updated_task = await _refetch_task_fresh(OFFER_GID)
            assert _get_custom_field_value(updated_task, "Asset ID") == "MIXED-SMOKE-001"
            assert updated_task.get("notes") == "[SMOKE TEST] Mixed write test."
            spend_val = _get_custom_field_value(updated_task, "Weekly AD Spend")
            # Asana may round to integer precision depending on field config
            assert spend_val is not None, "Weekly AD Spend should have a value after write"
            assert abs(float(spend_val) - 777.77) < 1.0, (
                f"Expected ~777.77 (within rounding), got {spend_val}"
            )
        finally:
            restore_spend = float(original_spend) if original_spend is not None else None
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={
                    "asset_id": original_asset_id or "",
                    "notes": original_notes,
                    "weekly_ad_spend": restore_spend,
                },
            )


# =========================================================================
# Category 4: Enum and Multi-Enum Resolution (Real Data)
# =========================================================================


class TestEnumResolution:
    """Test enum and multi_enum resolution with real Asana data."""

    async def test_enum_options_discoverable(
        self, offer_task_data: dict[str, Any]
    ) -> None:
        """Verify we can inspect enum options on language, specialty, etc."""
        enum_fields = ["Language", "Specialty", "Optimize For", "Campaign Type"]
        for field_name in enum_fields:
            cf = _get_custom_field_def(offer_task_data, field_name)
            if cf is None:
                continue
            options = cf.get("enum_options", [])
            enabled = [
                o.get("name")
                for o in options
                if o.get("enabled", True) and o.get("name")
            ]
            assert len(enabled) > 0, (
                f"No enabled options found for enum field {field_name!r}"
            )

    async def test_enum_write_by_name(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write a valid enum value by NAME to 'language' field, verify, restore."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_value = _get_custom_field_value(original_task, "Language")

        cf = _get_custom_field_def(original_task, "Language")
        if cf is None:
            pytest.skip("Language field not found on this offer")

        options = cf.get("enum_options", [])
        enabled = [
            o for o in options if o.get("enabled", True) and o.get("name")
        ]
        if not enabled:
            pytest.skip("No enabled Language options")

        test_option = None
        for opt in enabled:
            if opt["name"] != original_value:
                test_option = opt["name"]
                break
        if test_option is None:
            test_option = enabled[0]["name"]

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"language": test_option},
                include_updated=True,
            )
            assert result.fields_written >= 1, (
                f"Enum write failed. Results: "
                f"{[(r.input_name, r.status, r.error) for r in result.field_results]}"
            )

            updated = await _refetch_task_fresh(OFFER_GID)
            updated_lang = _get_custom_field_value(updated, "Language")
            assert updated_lang == test_option, (
                f"Expected {test_option!r}, got {updated_lang!r}"
            )
        finally:
            if original_value is not None:
                await write_service.write_async(
                    entity_type="offer",
                    gid=OFFER_GID,
                    fields={"language": original_value},
                )
            else:
                await write_service.write_async(
                    entity_type="offer",
                    gid=OFFER_GID,
                    fields={"language": None},
                )

    async def test_enum_write_case_insensitive(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write an enum value with WRONG CASING, should still resolve."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_value = _get_custom_field_value(original_task, "Language")

        cf = _get_custom_field_def(original_task, "Language")
        if cf is None:
            pytest.skip("Language field not found")

        options = cf.get("enum_options", [])
        enabled = [
            o for o in options if o.get("enabled", True) and o.get("name")
        ]
        if not enabled:
            pytest.skip("No enabled Language options")

        test_option_upper = enabled[0]["name"].upper()

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"language": test_option_upper},
            )
            assert result.fields_written >= 1, (
                f"Case-insensitive enum write failed: "
                f"{[(r.input_name, r.status, r.error) for r in result.field_results]}"
            )
        finally:
            if original_value is not None:
                await write_service.write_async(
                    entity_type="offer",
                    gid=OFFER_GID,
                    fields={"language": original_value},
                )
            else:
                await write_service.write_async(
                    entity_type="offer",
                    gid=OFFER_GID,
                    fields={"language": None},
                )

    async def test_invalid_enum_value_returns_skipped(
        self,
        offer_task_data: dict[str, Any],
        write_registry: EntityWriteRegistry,
    ) -> None:
        """Invalid enum value should produce 'skipped' result with suggestions."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields(
            {"language": "TOTALLY_INVALID_ENUM_VALUE_XYZ"}
        )
        rf = results[0]
        assert rf.status == "skipped", (
            f"Expected 'skipped' for invalid enum, got {rf.status}: {rf.error}"
        )
        assert rf.suggestions is not None and len(rf.suggestions) > 0, (
            "Expected enum suggestions for invalid value"
        )

    async def test_multi_enum_write_list(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Write a list of values to platforms (multi_enum), verify, restore."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_platforms = _get_custom_field_value(original_task, "Platforms")

        cf = _get_custom_field_def(original_task, "Platforms")
        if cf is None:
            pytest.skip("Platforms field not found")

        options = cf.get("enum_options", [])
        enabled = [
            o for o in options if o.get("enabled", True) and o.get("name")
        ]
        if len(enabled) < 2:
            pytest.skip("Need at least 2 Platforms options for multi-enum test")

        test_values = [enabled[0]["name"], enabled[1]["name"]]

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"platforms": test_values},
                include_updated=True,
            )
            assert result.fields_written >= 1, (
                f"Multi-enum write failed: "
                f"{[(r.input_name, r.status, r.error) for r in result.field_results]}"
            )

            updated = await _refetch_task_fresh(OFFER_GID)
            updated_platforms = _get_custom_field_value(updated, "Platforms")
            assert isinstance(updated_platforms, list)
            for val in test_values:
                assert val in updated_platforms, (
                    f"Expected {val!r} in platforms, got {updated_platforms}"
                )
        finally:
            if original_platforms:
                await write_service.write_async(
                    entity_type="offer",
                    gid=OFFER_GID,
                    fields={"platforms": original_platforms},
                )
            else:
                await write_service.write_async(
                    entity_type="offer",
                    gid=OFFER_GID,
                    fields={"platforms": []},
                )


# =========================================================================
# Category 5: Error Paths
# =========================================================================


class TestErrorPaths:
    """Test error handling and edge cases."""

    async def test_wrong_entity_type_raises_mismatch(
        self, write_service: FieldWriteService
    ) -> None:
        """Writing to offer GID as 'business' should raise EntityTypeMismatchError."""
        with pytest.raises(EntityTypeMismatchError) as exc_info:
            await write_service.write_async(
                entity_type="business",
                gid=OFFER_GID,
                fields={"notes": "this should fail"},
            )
        assert OFFER_GID in str(exc_info.value)

    async def test_nonexistent_gid_raises_not_found(
        self, write_service: FieldWriteService
    ) -> None:
        """Using a fake GID should raise TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError):
            await write_service.write_async(
                entity_type="offer",
                gid=NONEXISTENT_GID,
                fields={"asset_id": "should-fail"},
            )

    async def test_all_invalid_fields_raises_no_valid_fields(
        self, write_service: FieldWriteService
    ) -> None:
        """Passing only invalid fields should raise NoValidFieldsError."""
        with pytest.raises(NoValidFieldsError):
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"zzz_fake_field": 1, "xxx_fake_field": 2},
            )

    def test_empty_fields_validation(self) -> None:
        """Pydantic model should reject empty fields dict."""
        from autom8_asana.api.routes.entity_write import EntityWriteRequest

        with pytest.raises(ValueError, match="fields must be non-empty"):
            EntityWriteRequest(fields={})

    async def test_wrong_type_for_number_field(
        self,
        offer_task_data: dict[str, Any],
        write_registry: EntityWriteRegistry,
    ) -> None:
        """Passing a string to a number field should produce type error."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"weekly_ad_spend": "not-a-number"})
        rf = results[0]
        assert rf.status == "error", (
            f"Expected 'error' for string in number field, got {rf.status}"
        )
        assert "number" in rf.error.lower()

    async def test_wrong_type_for_text_field(
        self,
        offer_task_data: dict[str, Any],
        write_registry: EntityWriteRegistry,
    ) -> None:
        """Passing a number to a text field should produce type error."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"asset_id": 12345})
        rf = results[0]
        assert rf.status == "error", (
            f"Expected 'error' for int in text field, got {rf.status}"
        )
        assert "text" in rf.error.lower() or "str" in rf.error.lower()

    async def test_wrong_type_for_enum_field(
        self,
        offer_task_data: dict[str, Any],
        write_registry: EntityWriteRegistry,
    ) -> None:
        """Passing a number to an enum field should produce type error."""
        resolver = _make_resolver(offer_task_data, write_registry)
        results = resolver.resolve_fields({"language": 999})
        rf = results[0]
        assert rf.status == "error", (
            f"Expected 'error' for int in enum field, got {rf.status}"
        )

    async def test_unwritable_entity_type_raises_value_error(
        self, write_service: FieldWriteService
    ) -> None:
        """Passing a non-writable entity type should raise ValueError."""
        with pytest.raises(ValueError, match="not writable"):
            await write_service.write_async(
                entity_type="process",
                gid=PROCESS_GID,
                fields={"notes": "test"},
            )


# =========================================================================
# Category 6: Partial Success Semantics
# =========================================================================


class TestPartialSuccess:
    """Verify partial success behavior when mixing valid and invalid fields."""

    async def test_mixed_valid_and_invalid_fields(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Valid fields should be written even when some fields are invalid."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_asset_id = _get_custom_field_value(original_task, "Asset ID")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={
                    "asset_id": "PARTIAL-SMOKE-001",
                    "nonexistent_field_abc": 123,
                },
                include_updated=True,
            )

            assert result.fields_written >= 1, (
                f"Expected at least 1 field written, got {result.fields_written}"
            )
            assert result.fields_skipped >= 1, (
                f"Expected at least 1 field skipped, got {result.fields_skipped}"
            )

            written_names = [
                r.input_name
                for r in result.field_results
                if r.status == "resolved"
            ]
            skipped_names = [
                r.input_name
                for r in result.field_results
                if r.status == "skipped"
            ]
            assert "asset_id" in written_names
            assert "nonexistent_field_abc" in skipped_names

            updated_task = await _refetch_task_fresh(OFFER_GID)
            assert _get_custom_field_value(updated_task, "Asset ID") == "PARTIAL-SMOKE-001"
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": original_asset_id or ""},
            )

    async def test_partial_with_type_error(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """Valid field + type-error field should still write the valid one."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_notes = original_task.get("notes", "")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={
                    "notes": "[SMOKE TEST] Partial type error test.",
                    "weekly_ad_spend": "invalid-string-for-number",
                },
            )
            assert result.fields_written >= 1
            assert result.fields_skipped >= 1

            updated_task = await _refetch_task_fresh(OFFER_GID)
            assert updated_task.get("notes") == "[SMOKE TEST] Partial type error test."
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"notes": original_notes},
            )


# =========================================================================
# Category 7: Process Entity Edge Case
# =========================================================================


class TestProcessEdgeCase:
    """Verify Process entity behavior in write registry."""

    def test_process_excluded_from_writable(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """Process (PRIMARY_PROJECT_GID=None) is excluded from writable types."""
        assert not write_registry.is_writable("process")
        assert "process" not in write_registry.writable_types()

    def test_process_get_returns_none(
        self, write_registry: EntityWriteRegistry
    ) -> None:
        """get('process') should return None."""
        assert write_registry.get("process") is None

    def test_process_has_descriptors(self) -> None:
        """Verify Process model actually HAS CustomFieldDescriptors.

        Confirms exclusion is due to PRIMARY_PROJECT_GID=None, not missing descriptors.
        """
        from autom8_asana.models.business.descriptors import CustomFieldDescriptor
        from autom8_asana.models.business.process import Process

        descriptors = []
        for attr_name in dir(Process):
            try:
                attr = getattr(Process, attr_name)
            except Exception:
                continue
            if isinstance(attr, CustomFieldDescriptor) and attr.field_name:
                descriptors.append(attr_name)

        assert len(descriptors) > 10, (
            f"Expected Process to have many descriptors, found {len(descriptors)}: "
            f"{descriptors}"
        )


# =========================================================================
# Category 8: WriteFieldsResult Structure
# =========================================================================


class TestResultStructure:
    """Verify the WriteFieldsResult object structure."""

    async def test_result_has_correct_metadata(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """WriteFieldsResult should populate all metadata fields."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_asset_id = _get_custom_field_value(original_task, "Asset ID")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": "STRUCT-SMOKE-001"},
            )
            assert result.gid == OFFER_GID
            assert result.entity_type == "offer"
            assert isinstance(result.field_results, list)
            assert len(result.field_results) == 1
            assert result.fields_written == 1
            assert result.fields_skipped == 0
            assert result.updated_fields is None
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": original_asset_id or ""},
            )

    async def test_resolved_field_has_gid_for_custom(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """ResolvedField for custom fields should carry the Asana field GID."""
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_asset_id = _get_custom_field_value(original_task, "Asset ID")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": "GID-CHECK-001"},
            )
            rf = result.field_results[0]
            assert rf.gid is not None, "Custom field ResolvedField should have a GID"
            assert rf.gid.isdigit(), f"GID should be numeric, got {rf.gid!r}"
            assert not rf.is_core
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": original_asset_id or ""},
            )


# =========================================================================
# Category 9: Discovered Defect Regression Tests
# =========================================================================


class TestDiscoveredDefects:
    """Tests that expose discovered defects for regression tracking.

    These tests document and verify bugs found during adversarial testing.
    They serve as regression tests -- when the bug is fixed, the test
    should be updated to assert correct behavior.
    """

    async def test_d_ew_001_include_updated_returns_fresh_data(
        self, write_service: FieldWriteService, asana_client: Any
    ) -> None:
        """D-EW-001 FIXED: include_updated now returns post-write data.

        Previously, _refetch_updated() read from the same client cache that
        held pre-write data, returning stale values. The fix invalidates
        the task cache entry after the update and before the refetch.

        Regression test: verify include_updated returns the WRITTEN value.
        """
        original_task = await _refetch_task_fresh(OFFER_GID)
        original_value = _get_custom_field_value(original_task, "Asset ID")

        try:
            result = await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": "CACHE-BUG-TEST-001"},
                include_updated=True,
            )
            assert result.fields_written == 1

            # The write SUCCEEDS at the Asana API level
            fresh = await _refetch_task_fresh(OFFER_GID)
            assert _get_custom_field_value(fresh, "Asset ID") == "CACHE-BUG-TEST-001"

            # include_updated should return the WRITTEN value (not stale cache)
            assert result.updated_fields is not None
            updated_value = result.updated_fields.get("asset_id")
            assert updated_value == "CACHE-BUG-TEST-001", (
                f"D-EW-001 regression: include_updated returned {updated_value!r}, "
                f"expected 'CACHE-BUG-TEST-001'"
            )
        finally:
            await write_service.write_async(
                entity_type="offer",
                gid=OFFER_GID,
                fields={"asset_id": original_value or ""},
            )

    async def test_d_ew_002_numeric_enum_name_resolves_to_gid(
        self,
        offer_task_data: dict[str, Any],
        write_registry: EntityWriteRegistry,
    ) -> None:
        """D-EW-002 FIXED: Numeric enum option names now resolve to GIDs.

        Previously, _resolve_single_option() treated any numeric string as
        a GID passthrough via isdigit(). Enum options with numeric names
        like '1', '2' were returned as-is instead of being resolved to
        their actual GID. The fix adds a length check (>= 13 digits) to
        distinguish real Asana GIDs from short numeric option names.

        Regression test: verify '2' resolves to the actual GID.
        """
        from autom8_asana.resolution.field_resolver import (
            _build_enum_lookup,
            _resolve_single_option,
        )

        # Algo Version on Asana has enum options: name='1' (GID 1209059380430446),
        # name='2' (GID 1209059380430447)
        cf = _get_custom_field_def(offer_task_data, "Algo Version")
        if cf is None:
            pytest.skip("Algo Version field not found on this offer")

        enum_options = cf.get("enum_options", [])
        lookup = _build_enum_lookup(enum_options)

        # Resolve '2' -- should return the actual GID, not '2'
        result = _resolve_single_option("2", lookup, enum_options)

        expected_gid = None
        for opt in enum_options:
            if opt.get("name") == "2":
                expected_gid = opt.get("gid")
                break

        assert expected_gid is not None, "Option '2' should exist"
        assert result == expected_gid, (
            f"D-EW-002 regression: numeric enum name '2' resolved to "
            f"{result!r}, expected GID {expected_gid!r}"
        )

    async def test_d_ew_003_algo_version_model_type_mismatch(
        self,
        offer_task_data: dict[str, Any],
        write_registry: EntityWriteRegistry,
    ) -> None:
        """D-EW-003: Offer.algo_version declared as TextField but is enum in Asana.

        The model declares `algo_version = TextField()` which tells the
        system to expect text values. But the actual Asana custom field
        'Algo Version' has resource_subtype='enum' with options ['1', '2'].

        This causes:
        1. Text value writes fail silently (resolver skips with 'not found')
        2. Combined with D-EW-002, restoring the original enum value ('2')
           triggers Asana 400 because '2' is sent as-is instead of the GID.

        Severity: MEDIUM
        Component: Offer model definition (offer.py line 180)
        Fix: Change `algo_version = TextField()` to `algo_version = EnumField()`.
        """
        cf = _get_custom_field_def(offer_task_data, "Algo Version")
        assert cf is not None, "Algo Version should exist on the offer task"

        actual_type = cf.get("resource_subtype")
        assert actual_type == "enum", (
            f"Algo Version is {actual_type!r} in Asana (expected 'enum')"
        )

        # The model declares it as TextField -- verify the mismatch
        from autom8_asana.models.business.descriptors import TextField
        from autom8_asana.models.business.offer import Offer

        descriptor = getattr(Offer, "algo_version", None)
        assert descriptor is not None
        assert isinstance(descriptor, TextField), (
            f"Expected TextField descriptor, got {type(descriptor).__name__}"
        )
        # Mismatch confirmed: model says text, Asana says enum
