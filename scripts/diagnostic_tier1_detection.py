#!/usr/bin/env python3
"""Diagnostic script to investigate why Tier 1 detection isn't being used.

This script:
1. Fetches a Business task and its holder subtasks
2. Checks if holders have project memberships
3. Tests if detect_by_project() works for holders
4. Reports on the integration gap

Run with:
    ASANA_PAT='your_token' python scripts/diagnostic_tier1_detection.py
"""

import asyncio
import os
import sys
import logging

# Enable debug logging for detection
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Check for PAT
    pat = os.environ.get("ASANA_PAT")
    if not pat:
        print("ERROR: Set ASANA_PAT environment variable")
        sys.exit(1)

    # Import SDK components
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.detection import (
        detect_entity_type,
        detect_by_project,
    )
    from autom8_asana.models.business.registry import get_registry

    # Print registry state at import time
    print("\n" + "=" * 70)
    print("SECTION 1: Registry State After Import")
    print("=" * 70)

    registry = get_registry()
    mappings = registry.get_all_mappings()
    print(f"\nRegistry has {len(mappings)} mappings:")
    for gid, entity_type in sorted(mappings.items(), key=lambda x: x[1].name):
        print(f"  {gid} -> {entity_type.name}")

    # Known holder project GIDs from the code
    print("\n" + "=" * 70)
    print("SECTION 2: Expected Holder Project GIDs (from code)")
    print("=" * 70)

    expected_holders = {
        "ContactHolder": "1201500116978260",  # Should detect CONTACT_HOLDER
        "Contact": "1200775689604552",  # Should detect CONTACT
        "DNAHolder": "1167650840134033",
        "ReconciliationHolder": "1203404998225231",
        "AssetEditHolder": "1203992664400125",
        "VideographyHolder": "1207984018149338",
        "Business": "1200653012566782",
    }

    for class_name, gid in expected_holders.items():
        entity_type = registry.lookup(gid)
        status = f"{entity_type.name}" if entity_type else "NOT FOUND"
        print(f"  {class_name} ({gid}): {status}")

    # Test with real Asana data
    print("\n" + "=" * 70)
    print("SECTION 3: Fetching Real Holder Data")
    print("=" * 70)

    # Use Contente workspace
    workspace_gid = "1143843643307416"
    async with AsanaClient(pat, workspace_gid=workspace_gid) as client:
        # Use a known Business GID from the test data
        # This is "Test Business" from fixtures
        business_gid = "1200782721452122"

        print(f"\nFetching Business task {business_gid}...")

        try:
            business_task = await client.tasks.get_async(business_gid)
            print(f"\nFound Business task: {business_task.name} ({business_task.gid})")
            print(f"  Memberships: {business_task.memberships}")

            # Test Tier 1 detection on Business
            result = detect_by_project(business_task)
            if result:
                print(
                    f"  Tier 1 Detection: {result.entity_type.name} (confidence: {result.confidence})"
                )
            else:
                print("  Tier 1 Detection: FAILED (returned None)")

            # Fetch holder subtasks
            print(f"\nFetching subtasks (holders) of Business {business_task.gid}...")
            holders = await client.tasks.subtasks_async(business_task.gid).collect()

            print(f"\nFound {len(holders)} holder subtasks:")
            for holder in holders:
                print(f"\n  Holder: {holder.name} ({holder.gid})")
                print(f"    Memberships: {holder.memberships}")

                # Test Tier 1 detection
                result = detect_by_project(holder)
                if result:
                    print(
                        f"    Tier 1 Detection: {result.entity_type.name} (tier {result.tier_used}, confidence: {result.confidence})"
                    )
                else:
                    print("    Tier 1 Detection: FAILED (returned None)")

                # Test full detection chain
                full_result = detect_entity_type(holder)
                print(
                    f"    Full Detection: {full_result.entity_type.name} (tier {full_result.tier_used}, confidence: {full_result.confidence})"
                )

                # Get children of this holder (e.g., contacts)
                if holder.name and "contacts" in holder.name.lower():
                    print(f"\n    Fetching children of {holder.name}...")
                    children = await client.tasks.subtasks_async(holder.gid).collect()
                    if children:
                        child = children[0]
                        print(f"      First child: {child.name} ({child.gid})")
                        print(f"        Memberships: {child.memberships}")

                        # Test detection on child
                        child_result = detect_by_project(child)
                        if child_result:
                            print(
                                f"        Tier 1 Detection: {child_result.entity_type.name}"
                            )
                        else:
                            print("        Tier 1 Detection: FAILED")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback

            traceback.print_exc()

    # Analysis
    print("\n" + "=" * 70)
    print("SECTION 4: Analysis - The Integration Gap")
    print("=" * 70)

    print("""
KEY FINDING: The hydration system (_fetch_holders_async in business.py)
does NOT call detect_entity_type() or detect_by_project().

Instead, it uses:
  1. _identify_holder() - checks HOLDER_KEY_MAP (name + emoji patterns)
  2. _matches_holder() - exact name match, emoji fallback (not implemented)
  3. _create_typed_holder() - switch statement by holder_key string

The detection.py module exists but is NEVER INVOKED during hydration:
  - _populate_holders() calls _identify_holder() (name-based)
  - _identify_holder() iterates HOLDER_KEY_MAP
  - _matches_holder() does task.name == name_pattern

RECOMMENDATION:
Modify _identify_holder() to call detect_entity_type() first (Tier 1),
then fall back to current name matching (Tier 2+).

Or better: modify _populate_holders() to use detect_entity_type()
directly on each subtask, which would provide the full detection chain.
""")


if __name__ == "__main__":
    asyncio.run(main())
