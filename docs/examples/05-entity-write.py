"""Write custom fields using the entity write API.

This example demonstrates the full entity write pipeline:
- Discovering an existing entity (offer task)
- Writing text, number, enum, and multi-enum fields
- Writing core Asana fields (name, notes)
- Verifying writes with independent re-fetch
- Before/after comparison

Based on the proven spike_write_diagnosis.py pattern, polished for documentation.

Usage:
    export ASANA_PAT=your_token_here
    export TARGET_GID=1234567890123456  # GID of an offer task
    .venv/bin/python docs/examples/05-entity-write.py

Prerequisites:
- Python 3.10+
- autom8_asana installed
- Valid Asana PAT with write access
- TARGET_GID must be a task in the Offers project (1143843662099250)
"""
from __future__ import annotations

import asyncio
import os
import sys


def extract_custom_field_value(field: dict) -> object:
    """Extract display-ready value from a custom field dict.

    Handles different field types (text, number, enum, multi-enum).
    """
    subtype = field.get("resource_subtype", "")

    if subtype == "text":
        return field.get("text_value")
    elif subtype == "number":
        return field.get("number_value")
    elif subtype == "enum":
        enum_val = field.get("enum_value")
        return enum_val.get("name") if isinstance(enum_val, dict) else None
    elif subtype == "multi_enum":
        multi_vals = field.get("multi_enum_values") or []
        return [v.get("name") for v in multi_vals if isinstance(v, dict)]
    else:
        return field.get("display_value")


async def main() -> None:
    """Execute the entity write pipeline."""

    # Step 1: Get credentials and target from environment
    token = os.getenv("ASANA_PAT")
    target_gid = os.getenv("TARGET_GID")

    if not token:
        print("ERROR: ASANA_PAT environment variable not set")
        print("Set it with: export ASANA_PAT=your_token_here")
        sys.exit(1)

    if not target_gid:
        print("ERROR: TARGET_GID environment variable not set")
        print("Set it with: export TARGET_GID=1234567890123456")
        sys.exit(1)

    # Step 2: Create client and initialize write services
    from autom8_asana.client import AsanaClient
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.resolution.write_registry import EntityWriteRegistry
    from autom8_asana.services.field_write_service import FieldWriteService

    client = AsanaClient(token=token)

    # The EntityWriteRegistry auto-discovers writable entity types
    # by introspecting model classes for CustomFieldDescriptor properties
    write_registry = EntityWriteRegistry(get_registry())

    # The FieldWriteService orchestrates the validate->resolve->write pipeline
    field_service = FieldWriteService(client, write_registry)

    # Fields we'll track through the write process
    fields_of_interest = [
        "Asset ID",
        "Campaign ID",
        "Weekly Ad Spend",
        "Language",
        "Platforms",
    ]

    try:
        # Step 3: Fetch baseline state (before write)
        print("=" * 70)
        print("STEP 1: Fetch baseline task state")
        print("=" * 70)

        # Specify fields needed for custom field inspection
        opt_fields = [
            "name",
            "notes",
            "custom_fields",
            "custom_fields.name",
            "custom_fields.resource_subtype",
            "custom_fields.text_value",
            "custom_fields.number_value",
            "custom_fields.enum_value",
            "custom_fields.enum_options",
            "custom_fields.multi_enum_values",
        ]

        baseline = await client.tasks.get_async(
            target_gid,
            raw=True,
            opt_fields=opt_fields,
        )

        print(f"Task: {baseline.get('name')}")
        print(f"Notes: {baseline.get('notes', 'N/A')}")
        print("\nCurrent custom field values:")

        # Extract baseline values
        baseline_fields = {}
        for cf in baseline.get("custom_fields", []):
            field_name = cf.get("name", "")
            if field_name in fields_of_interest:
                value = extract_custom_field_value(cf)
                baseline_fields[field_name] = value
                print(f"  {field_name}: {value!r}")

        # Step 4: Prepare fields to write
        print("\n" + "=" * 70)
        print("STEP 2: Write custom fields via FieldWriteService")
        print("=" * 70)

        # The write API accepts snake_case descriptor names (not display names)
        # Display names like "Asset ID" map to descriptors like "asset_id"
        fields_to_write = {
            # Text fields (string values)
            "asset_id": "DOC-EXAMPLE-001",
            "campaign_id": "CAMP-SDK-DEMO",

            # Number field (float or int)
            "weekly_ad_spend": 2500.00,

            # Enum field (single selection by name)
            # Resolves the name "en" to the appropriate enum option GID
            "language": "en",

            # Multi-enum field (multiple selections by names)
            # Resolves names to GIDs, handles deduplication
            "platforms": ["meta", "facebook"],

            # Core Asana fields (not custom fields)
            "name": "[SDK Example] Entity Write API Demo",
            "notes": "Updated via autom8_asana SDK entity write example",
        }

        print(f"Writing {len(fields_to_write)} fields:")
        for field_name, value in fields_to_write.items():
            print(f"  {field_name}: {value!r}")

        # Step 5: Execute the write
        # The service handles:
        # - Field name resolution (snake_case -> Asana display name)
        # - Enum resolution (option name -> GID)
        # - Type validation
        # - Payload construction
        # - Single PUT request to Asana
        result = await field_service.write_async(
            entity_type="offer",
            gid=target_gid,
            fields=fields_to_write,
            list_mode="replace",  # For multi-enum: replace existing vs append
            include_updated=True,  # Re-fetch to verify writes
        )

        print(f"\nWrite result: {result.fields_written} written, {result.fields_skipped} skipped")

        # Display per-field resolution results
        print("\nPer-field resolution:")
        for rf in result.field_results:
            status_icon = {
                "resolved": "✓",
                "skipped": "⊘",
                "error": "✗",
            }.get(rf.status, "?")

            print(f"  [{status_icon}] {rf.input_name}")
            print(f"      Matched: {rf.matched_name!r}")
            print(f"      Value: {rf.value!r}")

            if rf.error:
                print(f"      Error: {rf.error}")
            if rf.suggestions:
                print(f"      Suggestions: {rf.suggestions}")

        # Step 6: Verify with independent re-fetch
        print("\n" + "=" * 70)
        print("STEP 3: Verify with fresh client")
        print("=" * 70)

        # Create a new client to bypass any potential caching
        verify_client = AsanaClient(token=token)

        updated = await verify_client.tasks.get_async(
            target_gid,
            raw=True,
            opt_fields=opt_fields,
        )

        print(f"Task: {updated.get('name')}")
        print(f"Notes: {updated.get('notes', 'N/A')}")
        print("\nUpdated custom field values:")

        # Extract updated values
        updated_fields = {}
        for cf in updated.get("custom_fields", []):
            field_name = cf.get("name", "")
            if field_name in fields_of_interest:
                value = extract_custom_field_value(cf)
                updated_fields[field_name] = value
                print(f"  {field_name}: {value!r}")

        # Step 7: Display before/after comparison
        print("\n" + "=" * 70)
        print("STEP 4: Before/After comparison")
        print("=" * 70)

        print(f"\n{'Field':<30} {'Before':<30} {'After':<30} Changed")
        print(f"{'-'*30} {'-'*30} {'-'*30} -------")

        for field_name in fields_of_interest:
            before_val = repr(baseline_fields.get(field_name))
            after_val = repr(updated_fields.get(field_name))
            changed = "YES" if baseline_fields.get(field_name) != updated_fields.get(field_name) else ""
            print(f"{field_name:<30} {before_val:<30} {after_val:<30} {changed}")

        # Also compare core fields
        print(f"\nCore field 'name':")
        print(f"  Before: {baseline.get('name')!r}")
        print(f"  After:  {updated.get('name')!r}")

        print(f"\nCore field 'notes':")
        print(f"  Before: {baseline.get('notes', '')!r}")
        print(f"  After:  {updated.get('notes', '')!r}")

        # Step 8: Verdict
        print("\n" + "=" * 70)
        print("VERDICT")
        print("=" * 70)

        if result.fields_written == len(fields_to_write):
            print(f"SUCCESS: All {len(fields_to_write)} fields written successfully")
            print(f"  - Text fields: asset_id, campaign_id")
            print(f"  - Number field: weekly_ad_spend")
            print(f"  - Enum field: language")
            print(f"  - Multi-enum field: platforms")
            print(f"  - Core fields: name, notes")
        else:
            print(f"PARTIAL: {result.fields_written}/{len(fields_to_write)} fields written")
            print(f"  Skipped: {result.fields_skipped}")

        print(f"\nVerify in Asana: https://app.asana.com/0/1143843662099250/{target_gid}")

    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
