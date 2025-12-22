#!/usr/bin/env python3
"""Diagnostic script to trace hydration pipeline data flow.

This script instruments the hydration process to identify exactly where
children data disappears. It logs at each step:
1. API response for subtasks
2. Holder identification/creation
3. _populate_children calls
4. Final children storage

Usage:
    ASANA_PAT='your_token' python scripts/diagnose_hydration.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Suppress httpx noise but keep our module's debug output
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def log_separator(title: str, char: str = "=") -> None:
    """Print a visual separator."""
    width = 80
    print(f"\n{char * width}")
    print(f" {title}")
    print(f"{char * width}\n")


async def diagnose_offer_hydration(offer_gid: str) -> None:
    """Diagnose hydration from an Offer GID with full tracing."""
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

    log_separator("HYDRATION DIAGNOSTIC - Starting from Offer GID", "=")
    print(f"Offer GID: {offer_gid}")

    async with AsanaClient() as client:
        # =================================================================
        # STEP 1: Fetch the entry task (Offer)
        # =================================================================
        log_separator("STEP 1: Fetching Entry Task (Offer)", "-")

        offer_task = await client.tasks.get_async(offer_gid)
        print(f"  Task Name: {offer_task.name}")
        print(f"  Task GID: {offer_task.gid}")
        print(f"  Parent GID: {offer_task.parent.gid if offer_task.parent else 'None'}")
        print(f"  Projects: {[p.gid for p in (offer_task.projects or [])]}")

        # =================================================================
        # STEP 2: Manual upward traversal to Business
        # =================================================================
        log_separator("STEP 2: Manual Upward Traversal", "-")

        # Walk up the parent chain
        current = offer_task
        path: list[Task] = []
        depth = 0

        while current.parent and depth < 10:
            parent_gid = current.parent.gid
            print(f"  Level {depth}: {current.name} (GID: {current.gid})")
            print(f"    -> Parent GID: {parent_gid}")

            parent_task = await client.tasks.get_async(parent_gid)
            path.append(parent_task)
            print(f"    -> Parent Name: {parent_task.name}")
            print(
                f"    -> Parent Projects: {[p.gid for p in (parent_task.projects or [])]}"
            )

            current = parent_task
            depth += 1

        print(f"\n  Traversal complete. Path length: {len(path)}")
        print(f"  Root task: {current.name} (GID: {current.gid})")

        # Identify the Business (root should have no parent)
        business_task = current
        print(f"\n  Business detected: {business_task.name}")

        # =================================================================
        # STEP 3: Fetch Business subtasks (holders) - RAW API RESPONSE
        # =================================================================
        log_separator("STEP 3: Fetch Business Subtasks (Raw API)", "-")

        # Use raw API to see exactly what's returned
        raw_subtasks = await client.tasks.subtasks_async(business_task.gid).collect()
        print(f"  Total subtasks returned: {len(raw_subtasks)}")

        for idx, subtask in enumerate(raw_subtasks):
            print(f"\n  Subtask #{idx + 1}:")
            print(f"    GID: {subtask.gid}")
            print(f"    Name: '{subtask.name}'")
            print(f"    Created: {subtask.created_at}")

        # =================================================================
        # STEP 4: Create typed Business and populate holders
        # =================================================================
        log_separator("STEP 4: Create Business Model and Populate Holders", "-")

        from autom8_asana.models.business.business import Business

        business = Business.model_validate(business_task.model_dump())
        print(f"  Business model created: {business.name}")

        # Manually call _populate_holders with tracing
        print("\n  Calling _populate_holders with subtasks...")

        for subtask in raw_subtasks:
            holder_key = business._identify_holder(subtask)
            print(f"    Subtask '{subtask.name}' -> holder_key: {holder_key}")

        business._populate_holders(raw_subtasks)

        # Check what holders were populated
        print("\n  Holder population results:")
        holders = [
            ("contact_holder", business._contact_holder),
            ("unit_holder", business._unit_holder),
            ("location_holder", business._location_holder),
            ("dna_holder", business._dna_holder),
            ("reconciliation_holder", business._reconciliation_holder),
            ("asset_edit_holder", business._asset_edit_holder),
            ("videography_holder", business._videography_holder),
        ]
        for name, holder in holders:
            if holder:
                print(f"    {name}: GID={holder.gid}, Name='{holder.name}'")
            else:
                print(f"    {name}: None (not found)")

        # =================================================================
        # STEP 5: Deep dive into UnitHolder children
        # =================================================================
        log_separator("STEP 5: UnitHolder Children Fetch", "-")

        if business._unit_holder:
            unit_holder = business._unit_holder
            print(f"  UnitHolder GID: {unit_holder.gid}")
            print(f"  UnitHolder Name: {unit_holder.name}")

            # Fetch unit_holder subtasks (Units)
            unit_subtasks = await client.tasks.subtasks_async(unit_holder.gid).collect()
            print(f"\n  Subtasks of UnitHolder: {len(unit_subtasks)}")

            for idx, unit_task in enumerate(unit_subtasks):
                print(f"\n    Unit #{idx + 1}:")
                print(f"      GID: {unit_task.gid}")
                print(f"      Name: '{unit_task.name}'")
                print(f"      Projects: {[p.gid for p in (unit_task.projects or [])]}")

            # Now call _populate_children and trace
            print("\n  Calling _populate_children on UnitHolder...")
            unit_holder._populate_children(unit_subtasks)

            print(
                f"\n  UnitHolder.units after _populate_children: {len(unit_holder.units)}"
            )
            for unit in unit_holder.units:
                print(f"    - Unit: {unit.name} (GID: {unit.gid})")
                print(f"      _unit_holder ref: {unit._unit_holder is unit_holder}")
                print(
                    f"      _business ref: {unit._business is business if hasattr(unit, '_business') else 'N/A'}"
                )

            # =================================================================
            # STEP 6: Deep dive into first Unit's OfferHolder
            # =================================================================
            log_separator("STEP 6: First Unit's OfferHolder Children", "-")

            if unit_holder.units:
                first_unit = unit_holder.units[0]
                print(f"  First Unit: {first_unit.name} (GID: {first_unit.gid})")

                # Fetch Unit's subtasks (OfferHolder, ProcessHolder)
                unit_subtasks_list = await client.tasks.subtasks_async(
                    first_unit.gid
                ).collect()
                print(f"\n  Subtasks of Unit: {len(unit_subtasks_list)}")

                for idx, subtask in enumerate(unit_subtasks_list):
                    print(f"\n    Subtask #{idx + 1}:")
                    print(f"      GID: {subtask.gid}")
                    print(f"      Name: '{subtask.name}'")

                # Identify and populate holders
                print("\n  Calling _populate_holders on Unit...")
                first_unit._populate_holders(unit_subtasks_list)

                print(f"\n  Unit._offer_holder: {first_unit._offer_holder}")
                print(f"  Unit._process_holder: {first_unit._process_holder}")

                if first_unit._offer_holder:
                    offer_holder = first_unit._offer_holder
                    print(f"\n  OfferHolder GID: {offer_holder.gid}")

                    # Fetch offers
                    offer_subtasks = await client.tasks.subtasks_async(
                        offer_holder.gid
                    ).collect()
                    print(f"  Subtasks of OfferHolder: {len(offer_subtasks)}")

                    for idx, offer_task_item in enumerate(offer_subtasks):
                        print(f"\n    Offer #{idx + 1}:")
                        print(f"      GID: {offer_task_item.gid}")
                        print(f"      Name: '{offer_task_item.name}'")

                    # Populate children
                    print("\n  Calling _populate_children on OfferHolder...")
                    offer_holder._populate_children(offer_subtasks)

                    print(
                        f"\n  OfferHolder.offers after _populate_children: {len(offer_holder.offers)}"
                    )
                    for offer in offer_holder.offers:
                        print(f"    - Offer: {offer.name} (GID: {offer.gid})")
                        is_entry = " <-- ENTRY POINT" if offer.gid == offer_gid else ""
                        print(f"      {is_entry}")

        # =================================================================
        # STEP 7: Full hydration test
        # =================================================================
        log_separator("STEP 7: Full Hydration via hydrate_from_gid_async", "-")

        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        result = await hydrate_from_gid_async(client, offer_gid)

        print(f"  Entry type: {result.entry_type}")
        print(f"  Is complete: {result.is_complete}")
        print(f"  API calls: {result.api_calls}")
        print(f"  Path length: {len(result.path)}")
        print(f"  Succeeded branches: {len(result.succeeded)}")
        print(f"  Failed branches: {len(result.failed)}")

        for branch in result.succeeded:
            print(f"    SUCCESS: {branch.holder_type} - {branch.child_count} children")

        for failure in result.failed:
            print(f"    FAILURE: {failure.holder_type} - {failure.error}")

        # Check hierarchy traversal
        biz = result.business
        print(f"\n  Business: {biz.name}")
        print(f"  Contacts: {len(biz.contacts)}")
        print(f"  Units: {len(biz.units)}")

        for unit in biz.units:
            print(f"\n    Unit: {unit.name}")
            print(f"      Offers: {len(unit.offers)}")
            for offer in unit.offers:
                entry_marker = " <-- ENTRY" if offer.gid == offer_gid else ""
                print(f"        - {offer.name} (GID: {offer.gid}){entry_marker}")

        # =================================================================
        # Summary
        # =================================================================
        log_separator("DIAGNOSTIC COMPLETE", "=")

        print("KEY FINDINGS:")
        print("-" * 40)

        # Check for the specific offer
        found_entry = False
        for unit in biz.units:
            for offer in unit.offers:
                if offer.gid == offer_gid:
                    found_entry = True
                    print(f"  [OK] Entry offer {offer_gid} found in hydrated hierarchy")
                    print(
                        f"       Path: Business -> Unit '{unit.name}' -> Offer '{offer.name}'"
                    )

        if not found_entry:
            print(f"  [FAIL] Entry offer {offer_gid} NOT found in hydrated hierarchy!")
            print("         Possible causes:")
            print("         - Offer might be in a different Unit")
            print("         - OfferHolder population failed")
            print("         - Type detection mismatch")


def main() -> None:
    """CLI entry point."""
    # Default to the known Offer GID
    offer_gid = os.environ.get("OFFER_GID", "1203504352465403")

    if not os.environ.get("ASANA_PAT"):
        print("Error: ASANA_PAT environment variable not set")
        print("Usage: ASANA_PAT='your_token' python scripts/diagnose_hydration.py")
        sys.exit(1)

    asyncio.run(diagnose_offer_hydration(offer_gid))


if __name__ == "__main__":
    main()
