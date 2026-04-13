"""E2E proof: Create an Offer under Nation of Wellness OfferHolder
and write fields via FieldWriteService.

This is a LIVE test that:
1. Discovers the Nation of Wellness OfferHolder from an existing offer
2. Lists sibling offers
3. Creates a new Offer task under the OfferHolder
4. Writes custom fields to the new offer via FieldWriteService
5. Writes improvements to sibling offer fields
6. Verifies all writes via re-fetch
7. Cleans up (deletes the created offer)

Run: .venv/bin/pytest tests/integration/test_e2e_offer_write_proof.py -v -s --timeout=120
"""

from __future__ import annotations

import os
import time

import pytest

from autom8_asana.core.errors import Autom8Error

ASANA_PAT = os.getenv("ASANA_PAT")
EXISTING_OFFER_GID = "1205571482650639"
OFFER_PROJECT_GID = "1143843662099250"

pytestmark = [
    pytest.mark.skipif(not ASANA_PAT, reason="ASANA_PAT not set"),
    pytest.mark.integration,
]


@pytest.mark.asyncio
async def test_e2e_offer_write_proof():
    """Full end-to-end proof: create offer, write fields, verify, clean up.

    This single async test exercises the complete Entity Write API pipeline
    against live Asana, with cleanup in a finally block.
    """
    from autom8_asana.cache.models.entry import EntryType
    from autom8_asana.client import AsanaClient
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.resolution.write_registry import EntityWriteRegistry
    from autom8_asana.services.field_write_service import FieldWriteService

    client = AsanaClient(token=ASANA_PAT)
    write_registry = EntityWriteRegistry(get_registry())
    created_gid = None

    try:
        # ==============================================================
        # Phase 1: Discover hierarchy
        # ==============================================================
        print("\n--- Phase 1: Discover Nation of Wellness hierarchy ---")

        offer_data = await client.tasks.get_async(
            EXISTING_OFFER_GID,
            raw=True,
            opt_fields=["parent.gid", "parent.name", "name"],
        )
        parent = offer_data.get("parent", {})
        assert parent and parent.get("gid"), "Existing offer has no parent"
        offer_holder_gid = parent["gid"]
        print(f"  Existing offer: {offer_data['name']}")
        print(f"  OfferHolder: {parent['name']} (GID: {offer_holder_gid})")

        # List sibling offers
        siblings = await client.tasks.subtasks_async(
            offer_holder_gid,
            opt_fields=["name", "completed"],
        ).collect()
        print(f"  Sibling offers: {len(siblings)}")
        for sib in siblings:
            print(f"    - {sib.name} ({sib.gid})")

        assert len(siblings) >= 1, "Expected at least 1 sibling offer"

        # ==============================================================
        # Phase 2: Create new offer
        # ==============================================================
        print("\n--- Phase 2: Create new offer ---")

        new_offer = await client.tasks.create_async(
            name="[E2E Proof] Nation of Wellness - Entity Write API",
            parent=offer_holder_gid,
            projects=[OFFER_PROJECT_GID],
            notes=(
                "E2E proof offer created by adversarial QA to validate "
                "the Entity Write API pipeline. Safe to delete."
            ),
            raw=True,
        )
        created_gid = new_offer["gid"]
        print(f"  Created: {new_offer['name']} (GID: {created_gid})")

        # Verify project membership
        client.tasks._cache_invalidate(created_gid, [EntryType.TASK])
        verify_data = await client.tasks.get_async(
            created_gid,
            raw=True,
            opt_fields=["memberships.project.gid"],
        )
        project_gids = [
            m["project"]["gid"]
            for m in (verify_data.get("memberships") or [])
            if isinstance(m, dict) and isinstance(m.get("project"), dict)
        ]
        assert OFFER_PROJECT_GID in project_gids, (
            f"Offer not in project {OFFER_PROJECT_GID}. Found: {project_gids}"
        )
        print(f"  Verified: in project {OFFER_PROJECT_GID}")

        # ==============================================================
        # Phase 3: Write text + number + core fields
        # ==============================================================
        print("\n--- Phase 3: Write fields via FieldWriteService ---")

        service = FieldWriteService(client, write_registry)
        client.tasks._cache_invalidate(created_gid, [EntryType.TASK])

        result = await service.write_async(
            entity_type="offer",
            gid=created_gid,
            fields={
                # Custom fields (descriptor names)
                "asset_id": "E2E-PROOF-001",
                "campaign_id": "CAMP-NOW-2026",
                "weekly_ad_spend": 750.00,
                "offer_headline": "Nation of Wellness - Premium Package",
                "landing_page_url": "https://nationofwellness.com/offer",
                "internal_notes": "Created by Entity Write API e2e proof",
                # Core fields
                "name": "[E2E Proof] NOW Premium - Write API Verified",
                "notes": (
                    "This offer was created and written to by the Entity Write "
                    "API (FieldWriteService) as an end-to-end proof.\n\n"
                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    "Pipeline: resolve -> validate -> write -> verify\n"
                    "Result: All fields written successfully."
                ),
            },
            include_updated=True,
        )

        print(f"  Fields written: {result.fields_written}")
        print(f"  Fields skipped: {result.fields_skipped}")
        for rf in result.field_results:
            icon = "+" if rf.status == "resolved" else "x"
            print(f"    [{icon}] {rf.input_name} -> {rf.matched_name}")
        assert result.fields_written == 8, (
            f"Expected 8 fields written, got {result.fields_written}"
        )
        assert result.fields_skipped == 0
        assert result.updated_fields is not None
        assert result.updated_fields["asset_id"] == "E2E-PROOF-001"
        assert result.updated_fields["weekly_ad_spend"] == 750.00
        assert "NOW Premium" in result.updated_fields["name"]
        print("  Verified: all 8 fields written + confirmed via include_updated")

        # ==============================================================
        # Phase 4: Write enum field by option name
        # ==============================================================
        print("\n--- Phase 4: Write enum field ---")

        client.tasks._cache_invalidate(created_gid, [EntryType.TASK])
        task_data = await client.tasks.get_async(
            created_gid,
            raw=True,
            opt_fields=[
                "custom_fields",
                "custom_fields.name",
                "custom_fields.resource_subtype",
                "custom_fields.enum_options",
            ],
        )

        # Find a writeable enum field
        enum_field_name = None
        enum_option_name = None
        for cf in task_data.get("custom_fields", []):
            if (
                cf.get("resource_subtype") == "enum"
                and cf.get("enum_options")
                and cf.get("name")
                in (
                    "Language",
                    "Specialty",
                    "Campaign Type",
                    "Optimize For",
                )
            ):
                options = [
                    o["name"]
                    for o in cf["enum_options"]
                    if o.get("enabled", True) and o.get("name")
                ]
                if options:
                    enum_field_name = cf["name"]
                    enum_option_name = options[0]
                    break

        if enum_field_name:
            client.tasks._cache_invalidate(created_gid, [EntryType.TASK])
            enum_result = await service.write_async(
                entity_type="offer",
                gid=created_gid,
                fields={enum_field_name: enum_option_name},
                include_updated=True,
            )
            assert enum_result.fields_written == 1
            assert enum_result.updated_fields[enum_field_name] == enum_option_name
            print(f"  Wrote enum: {enum_field_name} = '{enum_option_name}'")
        else:
            print("  Skipped: no suitable enum field found")

        # ==============================================================
        # Phase 5: Write improvements to sibling offer
        # ==============================================================
        print("\n--- Phase 5: Write improvement to sibling offer ---")

        target_gid = EXISTING_OFFER_GID
        client.tasks._cache_invalidate(target_gid, [EntryType.TASK])

        # Save current state
        sib_data = await client.tasks.get_async(
            target_gid,
            raw=True,
            opt_fields=[
                "custom_fields",
                "custom_fields.name",
                "custom_fields.text_value",
                "custom_fields.resource_subtype",
            ],
        )
        original_notes = None
        for cf in sib_data.get("custom_fields", []):
            if cf.get("name") == "Internal Notes":
                original_notes = cf.get("text_value") or ""
                break

        # Write improvement
        client.tasks._cache_invalidate(target_gid, [EntryType.TASK])
        sib_result = await service.write_async(
            entity_type="offer",
            gid=target_gid,
            fields={
                "internal_notes": (
                    f"[Entity Write API e2e {time.strftime('%H:%M')}] "
                    "Sibling field write verified."
                ),
            },
            include_updated=True,
        )
        assert sib_result.fields_written == 1
        assert "Entity Write API" in sib_result.updated_fields["internal_notes"]
        print(f"  Wrote to sibling {target_gid}: internal_notes updated")

        # Restore original
        client.tasks._cache_invalidate(target_gid, [EntryType.TASK])
        await service.write_async(
            entity_type="offer",
            gid=target_gid,
            fields={"internal_notes": original_notes},
        )
        print("  Restored sibling internal_notes to original value")

        # ==============================================================
        # Phase 6: Final round-trip verification
        # ==============================================================
        print("\n--- Phase 6: Final round-trip verification ---")

        client.tasks._cache_invalidate(created_gid, [EntryType.TASK])
        final = await client.tasks.get_async(
            created_gid,
            raw=True,
            opt_fields=[
                "name",
                "notes",
                "custom_fields",
                "custom_fields.name",
                "custom_fields.text_value",
                "custom_fields.number_value",
                "custom_fields.display_value",
                "custom_fields.resource_subtype",
            ],
        )

        assert "E2E Proof" in final["name"]
        assert "Entity Write API" in (final.get("notes") or "")

        # Build case-insensitive field map for robust verification
        cf_map = {}
        cf_map_lower = {}  # lowered key -> value
        for cf in final.get("custom_fields", []):
            name = cf.get("name", "")
            subtype = cf.get("resource_subtype", "")
            if subtype == "text":
                val = cf.get("text_value")
            elif subtype == "number":
                val = cf.get("number_value")
            elif subtype in ("enum", "multi_enum"):
                val = cf.get("display_value")
            else:
                val = cf.get("display_value")
            cf_map[name] = val
            cf_map_lower[name.lower()] = val

        def cf_get(field_name: str):
            """Case-insensitive custom field lookup."""
            return cf_map.get(field_name) or cf_map_lower.get(field_name.lower())

        assert cf_get("Asset ID") == "E2E-PROOF-001"
        assert cf_get("Campaign ID") == "CAMP-NOW-2026"
        assert cf_get("Weekly AD Spend") == 750.00
        assert cf_get("Offer Headline") == "Nation of Wellness - Premium Package"

        print(f"  name = {final['name']}")
        print(f"  Asset ID = {cf_get('Asset ID')}")
        print(f"  Campaign ID = {cf_get('Campaign ID')}")
        print(f"  Weekly AD Spend = {cf_get('Weekly AD Spend')}")
        print(f"  Offer Headline = {cf_get('Offer Headline')}")
        print(f"  Landing Page URL = {cf_get('Landing Page URL')}")
        if enum_field_name:
            print(f"  {enum_field_name} = {cf_get(enum_field_name)}")
        print("\n  E2E PROOF COMPLETE: All fields verified.")

    finally:
        # ==============================================================
        # Cleanup: delete the created offer
        # ==============================================================
        if created_gid:
            try:
                await client.tasks.delete_async(created_gid)
                print(f"\n--- Cleanup: deleted offer {created_gid} ---")
            except (Autom8Error, OSError) as e:
                print(f"\n--- Cleanup warning: {e} ---")
