#!/usr/bin/env python3
"""Business Model Demo - Hierarchy Traversal and Navigation.

Read-only demonstration of the SDK's Business Model layer:
- Hierarchy traversal: Business -> Contact -> Unit -> Offer -> Location
- Bidirectional navigation (parent/child)
- Sibling navigation
- Typed field access

Per TDD-SDKDEMO: Business model demo is read-only - no mutations.

Usage:
    python scripts/demo_business_model.py [--verbose] [--gid BUSINESS_GID]

Default Business GID: 1203504488813198
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from autom8_asana.client import AsanaClient
from autom8_asana.models.business import (
    Business,
)

from _demo_utils import DemoLogger


# ---------------------------------------------------------------------------
# Default Test Data
# ---------------------------------------------------------------------------

DEFAULT_BUSINESS_GID = "1203504488813198"


# ---------------------------------------------------------------------------
# Hierarchy Display
# ---------------------------------------------------------------------------


def display_entity_info(entity: Any, indent: int = 0) -> None:
    """Display basic info about an entity.

    Args:
        entity: Business entity to display.
        indent: Number of spaces to indent.
    """
    prefix = " " * indent
    entity_type = type(entity).__name__
    name = getattr(entity, "name", "(no name)")
    gid = getattr(entity, "gid", "(no gid)")
    print(f"{prefix}[{entity_type}] {name} ({gid})")


def display_typed_fields(entity: Any, indent: int = 0) -> None:
    """Display typed field values for an entity.

    Args:
        entity: Business entity with typed fields.
        indent: Number of spaces to indent.
    """
    prefix = " " * indent

    # Common fields to display for different entity types
    field_sets = {
        "Business": ["company_id", "website", "email", "phone"],
        "Contact": ["title", "phone", "email", "is_owner"],
        "Unit": ["vertical", "mrr", "billing_type", "has_card_on_file"],
        "Offer": ["offer_name", "offer_id", "ad_status", "monthly_budget"],
        "Location": ["street", "city", "state", "zip_code"],
    }

    entity_type = type(entity).__name__
    fields = field_sets.get(entity_type, [])

    displayed = []
    for field_name in fields:
        if hasattr(entity, field_name):
            value = getattr(entity, field_name)
            if value is not None:
                displayed.append(f"{field_name}={value}")

    if displayed:
        print(f"{prefix}  Fields: {', '.join(displayed[:4])}")


# ---------------------------------------------------------------------------
# Demo Functions
# ---------------------------------------------------------------------------


async def demo_hierarchy_traversal(
    client: AsanaClient,
    business: Business,
    logger: DemoLogger,
) -> None:
    """Demonstrate traversing the business hierarchy.

    Traverses: Business -> Contacts -> Units -> Offers -> Locations

    Args:
        client: SDK client.
        business: Loaded Business entity.
        logger: Demo logger.
    """
    logger.category_start("Hierarchy Traversal (Downward)")

    print("\n=== BUSINESS ===")
    display_entity_info(business)
    display_typed_fields(business)

    # --- Contacts ---
    print("\n--- Contacts ---")
    contacts = business.contacts or []
    if contacts:
        for contact in contacts:
            display_entity_info(contact, indent=2)
            display_typed_fields(contact, indent=2)
            if hasattr(contact, "is_owner") and contact.is_owner:
                print("      ** PRIMARY CONTACT (Owner) **")
    else:
        print("  (no contacts)")
    logger.info(f"Found {len(contacts)} contacts")

    # --- Units ---
    print("\n--- Units ---")
    units = business.units or []
    if units:
        for unit in units:
            display_entity_info(unit, indent=2)
            display_typed_fields(unit, indent=2)

            # Offers under this unit
            offers = unit.offers or []
            if offers:
                for offer in offers:
                    display_entity_info(offer, indent=4)
                    display_typed_fields(offer, indent=4)

                    # Locations under this offer
                    locations = getattr(offer, "locations", None) or []
                    if locations:
                        for location in locations:
                            display_entity_info(location, indent=6)
                            display_typed_fields(location, indent=6)
    else:
        print("  (no units)")
    logger.info(f"Found {len(units)} units")

    # Count totals
    total_offers = sum(len(u.offers or []) for u in units)
    total_locations = sum(
        len(getattr(o, "locations", None) or [])
        for u in units
        for o in (u.offers or [])
    )
    logger.info(f"Total offers: {total_offers}")
    logger.info(f"Total locations: {total_locations}")

    logger.category_end("Hierarchy Traversal (Downward)", True)


async def demo_bidirectional_navigation(
    client: AsanaClient,
    business: Business,
    logger: DemoLogger,
) -> None:
    """Demonstrate bidirectional parent/child navigation.

    Shows navigating up and down the hierarchy.

    Args:
        client: SDK client.
        business: Loaded Business entity.
        logger: Demo logger.
    """
    logger.category_start("Bidirectional Navigation")

    # Navigate down to find a unit
    units = business.units or []
    if not units:
        logger.warn("No units found - skipping bidirectional demo")
        logger.category_end("Bidirectional Navigation", True)
        return

    first_unit = units[0]
    print(f"\nStarting from Unit: {first_unit.name}")

    # Navigate up: Unit -> Business (via parent reference)
    print("\n--- Navigating UP (child to parent) ---")
    if hasattr(first_unit, "parent") and first_unit.parent:
        parent = first_unit.parent
        parent_type = type(parent).__name__
        parent_name = getattr(parent, "name", "(unknown)")
        print(f"  Unit's parent: [{parent_type}] {parent_name}")

        # If parent has a parent (e.g., UnitHolder -> Business)
        if hasattr(parent, "parent") and parent.parent:
            grandparent = parent.parent
            grandparent_type = type(grandparent).__name__
            grandparent_name = getattr(grandparent, "name", "(unknown)")
            print(f"  Parent's parent: [{grandparent_type}] {grandparent_name}")
    else:
        print("  (parent reference not loaded)")

    # Navigate down: Unit -> Offers
    print("\n--- Navigating DOWN (parent to children) ---")
    offers = first_unit.offers or []
    print(f"  Unit has {len(offers)} offers:")
    for offer in offers[:3]:  # Show first 3
        print(f"    - {offer.name}")
    if len(offers) > 3:
        print(f"    ... and {len(offers) - 3} more")

    # Demonstrate holder pattern
    print("\n--- Holder Pattern ---")
    if hasattr(first_unit, "_offer_holder") and first_unit._offer_holder:
        holder = first_unit._offer_holder
        holder_name = getattr(holder, "name", "(unnamed holder)")
        print(f"  Unit's OfferHolder: {holder_name}")
        print(f"  Holder contains {len(offers)} Offer children")
    else:
        print("  (offer holder not loaded)")

    logger.category_end("Bidirectional Navigation", True)


async def demo_sibling_navigation(
    client: AsanaClient,
    business: Business,
    logger: DemoLogger,
) -> None:
    """Demonstrate sibling navigation within holders.

    Args:
        client: SDK client.
        business: Loaded Business entity.
        logger: Demo logger.
    """
    logger.category_start("Sibling Navigation")

    # Find entities with siblings
    units = business.units or []
    if len(units) < 2:
        logger.warn("Need at least 2 units for sibling demo - skipping")
        logger.category_end("Sibling Navigation", True)
        return

    print(f"\n--- Unit Siblings ({len(units)} total) ---")
    for i, unit in enumerate(units):
        is_first = i == 0
        is_last = i == len(units) - 1

        position = []
        if is_first:
            position.append("FIRST")
        if is_last:
            position.append("LAST")

        pos_str = f" [{', '.join(position)}]" if position else ""
        print(f"  {i + 1}. {unit.name}{pos_str}")

        # Show previous/next if available
        if i > 0:
            print(f"      Previous: {units[i - 1].name}")
        if i < len(units) - 1:
            print(f"      Next: {units[i + 1].name}")

    # Do the same for offers if available
    if units and units[0].offers:
        offers = units[0].offers
        if len(offers) >= 2:
            print(f"\n--- Offer Siblings in first Unit ({len(offers)} total) ---")
            for i, offer in enumerate(offers[:5]):  # Show first 5
                print(f"  {i + 1}. {offer.name}")
            if len(offers) > 5:
                print(f"  ... and {len(offers) - 5} more")

    logger.category_end("Sibling Navigation", True)


async def demo_typed_field_access(
    client: AsanaClient,
    business: Business,
    logger: DemoLogger,
) -> None:
    """Demonstrate typed field access patterns.

    Shows accessing custom fields through typed properties.

    Args:
        client: SDK client.
        business: Loaded Business entity.
        logger: Demo logger.
    """
    logger.category_start("Typed Field Access")

    print("\n--- Business Fields ---")
    business_fields = [
        ("company_id", "Company ID"),
        ("website", "Website"),
        ("email", "Email"),
        ("phone", "Phone"),
        ("billing_name", "Billing Name"),
    ]

    for attr, display_name in business_fields:
        value = getattr(business, attr, None)
        print(f"  {display_name}: {value if value is not None else '(not set)'}")

    # Unit fields
    units = business.units or []
    if units:
        print("\n--- Unit Fields (first unit) ---")
        unit = units[0]
        unit_fields = [
            ("vertical", "Vertical"),
            ("mrr", "MRR"),
            ("billing_type", "Billing Type"),
            ("has_card_on_file", "Has Card on File"),
            ("primary_rep", "Primary Rep"),
        ]

        for attr, display_name in unit_fields:
            value = getattr(unit, attr, None)
            print(f"  {display_name}: {value if value is not None else '(not set)'}")

    # Offer fields
    if units and units[0].offers:
        print("\n--- Offer Fields (first offer) ---")
        offer = units[0].offers[0]
        offer_fields = [
            ("offer_name", "Offer Name"),
            ("offer_id", "Offer ID"),
            ("ad_status", "Ad Status"),
            ("monthly_budget", "Monthly Budget"),
            ("has_active_ads", "Has Active Ads"),
        ]

        for attr, display_name in offer_fields:
            value = getattr(offer, attr, None)
            print(f"  {display_name}: {value if value is not None else '(not set)'}")

    # Location fields (if available)
    if units and units[0].offers:
        for offer in units[0].offers:
            locations = getattr(offer, "locations", None) or []
            if locations:
                print("\n--- Location Fields (first location) ---")
                location = locations[0]
                location_fields = [
                    ("street", "Street"),
                    ("city", "City"),
                    ("state", "State"),
                    ("zip_code", "Zip Code"),
                    ("full_address", "Full Address"),
                ]

                for attr, display_name in location_fields:
                    value = getattr(location, attr, None)
                    print(
                        f"  {display_name}: {value if value is not None else '(not set)'}"
                    )
                break

    logger.category_end("Typed Field Access", True)


async def demo_holder_inspection(
    client: AsanaClient,
    business: Business,
    logger: DemoLogger,
) -> None:
    """Demonstrate inspecting holder tasks.

    Shows the holder pattern: Parent Task -> Holder Task -> Child Tasks

    Args:
        client: SDK client.
        business: Loaded Business entity.
        logger: Demo logger.
    """
    logger.category_start("Holder Pattern Inspection")

    print("\n--- Business Holders ---")
    holder_attrs = [
        ("_contact_holder", "ContactHolder"),
        ("_unit_holder", "UnitHolder"),
        ("_dna_holder", "DNAHolder"),
        ("_reconciliations_holder", "ReconciliationsHolder"),
        ("_asset_edit_holder", "AssetEditHolder"),
        ("_videography_holder", "VideographyHolder"),
        ("_location_holder", "LocationHolder"),
    ]

    for attr, holder_type in holder_attrs:
        holder = getattr(business, attr, None)
        if holder is not None:
            holder_name = getattr(holder, "name", "(unnamed)")
            holder_gid = getattr(holder, "gid", "(no gid)")
            # Count children based on holder type
            if holder_type == "ContactHolder":
                children = business.contacts or []
            elif holder_type == "UnitHolder":
                children = business.units or []
            elif holder_type == "LocationHolder":
                children = getattr(business, "locations", None) or []
            else:
                children = []
            print(
                f"  {holder_type}: {holder_name} ({holder_gid}) - {len(children)} children"
            )
        else:
            print(f"  {holder_type}: (not loaded)")

    # Show Unit holders if available
    units = business.units or []
    if units:
        print("\n--- First Unit's Holders ---")
        unit = units[0]
        unit_holders = [
            ("_offer_holder", "OfferHolder"),
            ("_process_holder", "ProcessHolder"),
            ("_location_holder", "LocationHolder"),
        ]

        for attr, holder_type in unit_holders:
            holder = getattr(unit, attr, None)
            if holder is not None:
                holder_name = getattr(holder, "name", "(unnamed)")
                # Count children
                if holder_type == "OfferHolder":
                    children = unit.offers or []
                elif holder_type == "ProcessHolder":
                    children = getattr(unit, "processes", None) or []
                elif holder_type == "LocationHolder":
                    children = getattr(unit, "locations", None) or []
                else:
                    children = []
                print(f"  {holder_type}: {holder_name} - {len(children)} children")
            else:
                print(f"  {holder_type}: (not loaded)")

    logger.category_end("Holder Pattern Inspection", True)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


async def load_business(
    client: AsanaClient,
    gid: str,
    logger: DemoLogger,
) -> Business | None:
    """Load a Business entity with full hierarchy.

    Args:
        client: SDK client.
        gid: Business task GID.
        logger: Demo logger.

    Returns:
        Business entity or None if load failed.
    """
    logger.info(f"Loading Business {gid} with full hierarchy...")

    try:
        # Load task with full opt_fields for hierarchy
        opt_fields = [
            "name",
            "notes",
            "html_notes",
            "completed",
            "parent",
            "parent.name",
            "custom_fields",
            "memberships",
            "memberships.project",
            "memberships.project.name",
        ]

        task = await client.tasks.get_async(gid, opt_fields=opt_fields)
        logger.info(f"Loaded task: {task.name}")

        # Convert to Business entity
        # Note: In real usage, you'd use the Business model factory
        # For this demo, we'll work with the raw task
        business = Business.from_task(task)
        logger.info(f"Created Business entity: {business.name}")

        # Load holders and children
        # This would typically be done via prefetch_holders=True
        # For demo, we'll show what's available
        logger.info("Loading hierarchy (this may take a moment)...")

        # Load subtasks to populate holders
        subtasks = []
        async for subtask in client.tasks.subtasks_async(gid, opt_fields=opt_fields):
            subtasks.append(subtask)

        logger.info(f"Found {len(subtasks)} direct subtasks (holders)")

        return business

    except Exception as e:
        logger.warn(f"Failed to load business: {e}")
        return None


async def run_demo(
    business_gid: str = DEFAULT_BUSINESS_GID,
    verbose: bool = False,
) -> int:
    """Run the business model demonstration.

    Args:
        business_gid: GID of the Business task to load.
        verbose: Whether to enable verbose logging.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger = DemoLogger(verbose=verbose)

    print("\n" + "=" * 60)
    print("  Business Model Demo")
    print("  Per TDD-SDKDEMO: Read-only hierarchy traversal")
    print("=" * 60)

    # Initialize client
    logger.info("\nInitializing SDK client...")
    try:
        client = AsanaClient()
    except Exception as e:
        logger.warn(f"Failed to initialize client: {e}")
        return 1

    try:
        # Load business
        business = await load_business(client, business_gid, logger)
        if not business:
            logger.warn("Could not load business entity")
            return 1

        # Run demos
        await demo_hierarchy_traversal(client, business, logger)
        await demo_bidirectional_navigation(client, business, logger)
        await demo_sibling_navigation(client, business, logger)
        await demo_typed_field_access(client, business, logger)
        await demo_holder_inspection(client, business, logger)

        # Summary
        print("\n" + "=" * 60)
        print("  Business Model Demo Complete")
        print("=" * 60)
        print("\nKey patterns demonstrated:")
        print("  1. Downward traversal: Business -> Units -> Offers -> Locations")
        print("  2. Upward navigation via parent references")
        print("  3. Sibling iteration within holder collections")
        print("  4. Typed field access (company_id, mrr, vertical, etc.)")
        print("  5. Holder pattern: Parent -> Holder -> Children")
        print("=" * 60)

        return 0

    finally:
        await client.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Business Model Demo - Read-only hierarchy traversal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
This demo loads a Business entity and demonstrates:
  - Hierarchy traversal (Business -> Contact -> Unit -> Offer -> Location)
  - Bidirectional navigation (parent/child references)
  - Sibling navigation within holders
  - Typed field access patterns
  - Holder pattern inspection

Default Business GID: {DEFAULT_BUSINESS_GID}

Examples:
  python demo_business_model.py                         # Use default business
  python demo_business_model.py --gid 1234567890123    # Use specific business
  python demo_business_model.py --verbose              # Enable verbose logging
""",
    )
    parser.add_argument(
        "-g",
        "--gid",
        default=DEFAULT_BUSINESS_GID,
        help=f"Business task GID to load (default: {DEFAULT_BUSINESS_GID})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(
        run_demo(
            business_gid=args.gid,
            verbose=args.verbose,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
