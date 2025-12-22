#!/usr/bin/env python3
"""Comprehensive SDK Demo: autom8_asana Business Hierarchy.

This script demonstrates the full capabilities of the autom8_asana SDK:

1. **Typed Custom Field Descriptors** - Each entity has typed field descriptors
   (TextField, EnumField, NumberField, MultiEnumField, PeopleField) providing
   type-safe access to Asana custom fields.

2. **Bidirectional Navigation** - Parent/child relationships via descriptors
   (ParentRef, HolderRef) enabling traversal up and down the hierarchy.

3. **Entity Hierarchy** - Business -> Holders -> Entities structure with
   nested holders for complex relationships (Unit -> OfferHolder -> Offer).

4. **Detection System** - Automatic type detection via project membership
   or name pattern matching.

Usage:
    export ASANA_PAT='your_personal_access_token'
    python scripts/example_offer_traversal.py

    # Or with a specific GID:
    python scripts/example_offer_traversal.py --gid 1203504352465403
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from autom8_asana.client import AsanaClient
from autom8_asana.models.business import (
    Business,
    Contact,
    Offer,
    Unit,
    hydrate_from_gid_async,
)
from autom8_asana.models.business.location import Location
from autom8_asana.models.business.hours import Hours
from autom8_asana.models.business.process import Process


def format_value(value: Any, default: str = "(not set)") -> str:
    """Format a value for display, handling None and empty values."""
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"${value:,.2f}" if value > 0 else default
        return str(value) if value > 0 else default
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else default
    return str(value)


def print_section(title: str, char: str = "-", width: int = 70) -> None:
    """Print a section header."""
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_field(label: str, value: Any, indent: int = 4) -> None:
    """Print a field with proper indentation and formatting."""
    prefix = " " * indent
    print(f"{prefix}{label}: {format_value(value)}")


async def demo_sdk_capabilities(offer_gid: str) -> int:
    """Demonstrate the full SDK capabilities.

    Args:
        offer_gid: GID of any entity to start traversal from.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    print("\n" + "=" * 70)
    print("  autom8_asana SDK - Comprehensive Demo")
    print("=" * 70)
    print(f"\n  Starting from GID: {offer_gid}")

    async with AsanaClient() as client:
        # =====================================================================
        # SECTION 1: HYDRATION AND TYPE DETECTION
        # =====================================================================
        print_section("1. HYDRATION & TYPE DETECTION", "=")

        print("\n  The SDK can start from ANY entity in the hierarchy and:")
        print("    - Detect its type via project membership or name patterns")
        print("    - Traverse UPWARD to find the Business root")
        print("    - Hydrate DOWNWARD to populate all holders and children")

        print("\n  Hydrating hierarchy...")
        result = await hydrate_from_gid_async(client, offer_gid)

        print("\n  Detection Result:")
        print(
            f"    Entry Type: {result.entry_type.value if result.entry_type else 'Business'}"
        )
        print(f"    API Calls Made: {result.api_calls}")
        print(f"    Hydration Complete: {result.is_complete}")

        if result.succeeded:
            print("\n  Successfully Hydrated Branches:")
            for branch in result.succeeded:
                print(f"    - {branch.holder_type}: {branch.child_count} children")

        if result.failed:
            print("\n  Failed Branches:")
            for failure in result.failed:
                print(f"    - {failure.holder_type}: {failure.error}")

        business: Business = result.business

        # =====================================================================
        # SECTION 2: BUSINESS ROOT - TYPED CUSTOM FIELD DESCRIPTORS
        # =====================================================================
        print_section("2. BUSINESS ROOT - Typed Custom Field Descriptors", "=")

        print(f"\n  Business: {business.name}")
        print(f"  GID: {business.gid}")

        print("\n  Text Fields (TextField descriptors):")
        print_field("Company ID", business.company_id)
        print_field("Office Phone", business.office_phone)
        print_field("Owner Name", business.owner_name)
        print_field("Owner Nickname", business.owner_nickname)
        print_field("Facebook Page ID", business.facebook_page_id)
        print_field("Google Calendar ID", business.google_cal_id)
        print_field("Stripe ID", business.stripe_id)
        print_field("Stripe Link", business.stripe_link)
        print_field("Reviews Link", business.reviews_link)
        print_field("Review 1", business.review_1)
        print_field("Twilio Phone", business.twilio_phone_num)

        print("\n  Number Fields (IntField descriptors):")
        print_field("Num Reviews", business.num_reviews)

        print("\n  Enum Fields (EnumField descriptors):")
        print_field("Aggression Level", business.aggression_level)
        print_field("Booking Type", business.booking_type)
        print_field("VCA Status", business.vca_status)
        print_field("Vertical", business.vertical)

        print("\n  People Fields (PeopleField descriptors):")
        rep = business.rep
        if rep:
            # PeopleField returns list of user references
            print_field(
                "Rep",
                [u.get("name", u.get("gid")) for u in rep]
                if isinstance(rep, list)
                else rep,
            )
        else:
            print_field("Rep", None)

        # =====================================================================
        # SECTION 3: CONTACTS - Navigation and Fields
        # =====================================================================
        print_section("3. CONTACTS - Bidirectional Navigation", "=")

        contacts: list[Contact] = business.contacts
        print(
            f"\n  Contact Holder: {business.contact_holder.name if business.contact_holder else '(none)'}"
        )
        print(f"  Total Contacts: {len(contacts)}")

        for i, contact in enumerate(contacts, 1):
            owner_flag = " ** PRIMARY OWNER **" if contact.is_owner else ""
            print(f"\n  [{i}] {contact.name}{owner_flag}")
            print(f"      GID: {contact.gid}")

            print("\n      Navigation (HolderRef, ParentRef descriptors):")
            print_field(
                "contact.contact_holder",
                contact.contact_holder.name if contact.contact_holder else None,
                6,
            )
            print_field(
                "contact.business",
                contact.business.name if contact.business else None,
                6,
            )

            print("\n      Text Fields:")
            print_field("Email", contact.contact_email, 6)
            print_field("Phone", contact.contact_phone, 6)
            print_field("City", contact.city, 6)
            print_field("Nickname", contact.nickname, 6)
            print_field("Dashboard User", contact.dashboard_user, 6)
            print_field("Contact URL", contact.contact_url, 6)
            print_field("Profile Photo URL", contact.profile_photo_url, 6)
            print_field("Campaign", contact.campaign, 6)
            print_field("Source", contact.source, 6)
            print_field("Medium", contact.medium, 6)

            print("\n      Enum Fields:")
            print_field("Position", contact.position, 6)
            print_field("Time Zone", contact.time_zone, 6)
            print_field("Text Communication", contact.text_communication, 6)

            print("\n      Name Parsing (computed properties):")
            print_field("Full Name", contact.full_name, 6)
            print_field("First Name", contact.first_name, 6)
            print_field("Last Name", contact.last_name, 6)
            print_field("Display Name", contact.display_name, 6)
            print_field("Preferred Name", contact.preferred_name, 6)

            # Limit to first 2 contacts for readability
            if i >= 2 and len(contacts) > 2:
                print(f"\n      ... and {len(contacts) - 2} more contacts")
                break

        # =====================================================================
        # SECTION 4: UNITS AND OFFERS - Nested Hierarchy
        # =====================================================================
        print_section("4. UNITS & OFFERS - Nested Hierarchy", "=")

        units: list[Unit] = business.units
        print(
            f"\n  Unit Holder: {business.unit_holder.name if business.unit_holder else '(none)'}"
        )
        print(f"  Total Units: {len(units)}")

        for i, unit in enumerate(units, 1):
            print(f"\n  [Unit {i}] {unit.name}")
            print(f"      GID: {unit.gid}")

            print("\n      Navigation:")
            print_field(
                "unit.unit_holder",
                unit.unit_holder.name if unit.unit_holder else None,
                6,
            )
            print_field(
                "unit.business", unit.business.name if unit.business else None, 6
            )

            print("\n      Financial Fields (NumberField):")
            print_field("MRR", unit.mrr, 6)
            print_field("Weekly Ad Spend", unit.weekly_ad_spend, 6)
            print_field("Discount", unit.discount, 6)
            print_field("Meta Spend", unit.meta_spend, 6)
            print_field("TikTok Spend", unit.tiktok_spend, 6)

            print("\n      Platform Fields:")
            print_field("Ad Account ID", unit.ad_account_id, 6)
            print_field("Platforms", unit.platforms, 6)
            print_field("TikTok Profile", unit.tiktok_profile, 6)

            print("\n      Product Fields:")
            print_field("Vertical", unit.vertical, 6)
            print_field("Specialty", unit.specialty, 6)
            print_field("Products", unit.products, 6)
            print_field("Languages", unit.languages, 6)
            print_field("Booking Type", unit.booking_type, 6)

            print("\n      Demographics Fields:")
            print_field("Currency", unit.currency, 6)
            print_field("Radius", unit.radius, 6)
            print_field("Min Age", unit.min_age, 6)
            print_field("Max Age", unit.max_age, 6)
            print_field("Gender", unit.gender, 6)

            # Show Offers for this Unit
            offers: list[Offer] = unit.offers
            print(
                f"\n      Offer Holder: {unit.offer_holder.name if unit.offer_holder else '(none)'}"
            )
            print(f"      Total Offers: {len(offers)}")
            print(f"      Active Offers: {len(unit.active_offers)}")

            for j, offer in enumerate(offers, 1):
                entry_marker = " <-- ENTRY POINT" if offer.gid == offer_gid else ""
                active_marker = " [ACTIVE]" if offer.has_active_ads else ""
                print(f"\n      [Offer {j}] {offer.name}{entry_marker}{active_marker}")
                print(f"          GID: {offer.gid}")

                print("\n          Navigation (multi-hop resolution):")
                print_field(
                    "offer.offer_holder",
                    offer.offer_holder.name if offer.offer_holder else None,
                    10,
                )
                print_field("offer.unit", offer.unit.name if offer.unit else None, 10)
                print_field(
                    "offer.business",
                    offer.business.name if offer.business else None,
                    10,
                )

                print("\n          Financial Fields:")
                print_field("MRR", offer.mrr, 10)
                print_field("Cost", offer.cost, 10)
                print_field("Weekly Ad Spend", offer.weekly_ad_spend, 10)
                print_field("Voucher Value", offer.voucher_value, 10)
                print_field("Budget Allocation", offer.budget_allocation, 10)

                print("\n          Ad Platform Fields:")
                print_field("Ad ID", offer.ad_id, 10)
                print_field("Ad Set ID", offer.ad_set_id, 10)
                print_field("Campaign ID", offer.campaign_id, 10)
                print_field("Asset ID", offer.asset_id, 10)
                print_field("Ad Account URL", offer.ad_account_url, 10)
                print_field("Active Ads URL", offer.active_ads_url, 10)
                print_field("Platforms", offer.platforms, 10)

                print("\n          Content Fields:")
                print_field("Offer Headline", offer.offer_headline, 10)
                print_field("Included Item 1", offer.included_item_1, 10)
                print_field("Included Item 2", offer.included_item_2, 10)
                print_field("Included Item 3", offer.included_item_3, 10)
                print_field("Landing Page URL", offer.landing_page_url, 10)
                print_field("Preview Link", offer.preview_link, 10)

                print("\n          Configuration Fields:")
                print_field("Form ID", offer.form_id, 10)
                print_field("Language", offer.language, 10)
                print_field("Specialty", offer.specialty, 10)
                print_field("Vertical", offer.vertical, 10)
                print_field("Targeting", offer.targeting, 10)
                print_field("Campaign Type", offer.campaign_type, 10)
                print_field("Optimize For", offer.optimize_for, 10)

                print("\n          Scheduling Fields:")
                print_field("Appt Duration", offer.appt_duration, 10)
                print_field("Calendar Duration", offer.calendar_duration, 10)
                print_field("Custom Cal URL", offer.custom_cal_url, 10)
                print_field("Schedule Link", offer.offer_schedule_link, 10)

                # Limit offers shown per unit
                if j >= 2 and len(offers) > 2:
                    print(f"\n          ... and {len(offers) - 2} more offers")
                    break

            # Show Processes for this Unit
            processes: list[Process] = unit.processes
            if processes:
                print(
                    f"\n      Process Holder: {unit.process_holder.name if unit.process_holder else '(none)'}"
                )
                print(f"      Total Processes: {len(processes)}")

                for k, process in enumerate(processes[:2], 1):
                    print(f"\n      [Process {k}] {process.name}")
                    print_field("Status", process.status, 10)
                    print_field("Priority", process.priority, 10)
                    print_field("Vertical", process.vertical, 10)
                    print_field("Process Type", process.process_type.value, 10)

                if len(processes) > 2:
                    print(f"\n          ... and {len(processes) - 2} more processes")

            # Limit to first 2 units for readability
            if i >= 2 and len(units) > 2:
                print(f"\n      ... and {len(units) - 2} more units")
                break

        # =====================================================================
        # SECTION 5: LOCATIONS AND HOURS
        # =====================================================================
        print_section("5. LOCATIONS & HOURS", "=")

        locations: list[Location] = business.locations
        print(
            f"\n  Location Holder: {business.location_holder.name if business.location_holder else '(none)'}"
        )
        print(f"  Total Locations: {len(locations)}")

        if locations:
            for i, location in enumerate(locations[:2], 1):
                print(f"\n  [Location {i}] {location.name}")
                print_field("Street", location.street)
                print_field("City", location.city)
                print_field("State", location.state)
                print_field("Zip Code", location.zip_code)
                print_field("Country", location.country)
                print_field("Phone", location.phone)
                print_field("Latitude", location.latitude)
                print_field("Longitude", location.longitude)
                print_field("Full Address", location.full_address)

            if len(locations) > 2:
                print(f"\n      ... and {len(locations) - 2} more locations")

        # Primary address shortcut
        primary_address = business.address
        if primary_address:
            print("\n  Primary Address (business.address shortcut):")
            print_field("Full Address", primary_address.full_address)

        # Hours
        hours: Hours | None = business.hours
        if hours:
            print("\n  Business Hours:")
            print_field("Monday", hours.monday_hours)
            print_field("Tuesday", hours.tuesday_hours)
            print_field("Wednesday", hours.wednesday_hours)
            print_field("Thursday", hours.thursday_hours)
            print_field("Friday", hours.friday_hours)
            print_field("Saturday", hours.saturday_hours)
            print_field("Sunday", hours.sunday_hours)
            print_field("Timezone", hours.timezone)
        else:
            print("\n  Business Hours: (not set)")

        # =====================================================================
        # SECTION 6: BIDIRECTIONAL NAVIGATION DEMO
        # =====================================================================
        print_section("6. BIDIRECTIONAL NAVIGATION DEMO", "=")

        print("\n  The SDK supports full bidirectional navigation:")
        print("    - DOWNWARD: business.units -> unit.offers -> offer.name")
        print("    - UPWARD: offer.unit -> offer.business")

        # Find entry offer for demo
        entry_offer: Offer | None = None
        for unit in units:
            for offer in unit.offers:
                if offer.gid == offer_gid:
                    entry_offer = offer
                    break
            if entry_offer:
                break

        if entry_offer:
            print(f"\n  Starting from Offer: {entry_offer.name}")
            print("\n  Upward Navigation Chain:")
            print(f"    offer.gid            = {entry_offer.gid}")
            if entry_offer.offer_holder:
                print(f"    -> offer_holder.gid  = {entry_offer.offer_holder.gid}")
                print(f"       offer_holder.name = {entry_offer.offer_holder.name}")
            if entry_offer.unit:
                print(f"    -> unit.gid          = {entry_offer.unit.gid}")
                print(f"       unit.name         = {entry_offer.unit.name}")
            if entry_offer.business:
                print(f"    -> business.gid      = {entry_offer.business.gid}")
                print(f"       business.name     = {entry_offer.business.name}")
        else:
            # Demo with first available offer
            if units and units[0].offers:
                first_offer = units[0].offers[0]
                print(f"\n  Demo with first Offer: {first_offer.name}")
                print("\n  Upward Navigation:")
                print(
                    f"    offer -> unit: {first_offer.unit.name if first_offer.unit else '(none)'}"
                )
                print(
                    f"    offer -> business: {first_offer.business.name if first_offer.business else '(none)'}"
                )

        print("\n  Downward Navigation Example:")
        print(f"    business.units: {len(business.units)} units")
        if business.units:
            first_unit = business.units[0]
            print(f"    business.units[0].offers: {len(first_unit.offers)} offers")
            if first_unit.offers:
                print(
                    f"    business.units[0].offers[0].name: {first_unit.offers[0].name}"
                )

        # =====================================================================
        # SECTION 7: SUMMARY STATISTICS
        # =====================================================================
        print_section("7. SUMMARY STATISTICS", "=")

        total_offers = sum(len(u.offers) for u in units)
        active_offers = sum(len(u.active_offers) for u in units)
        total_processes = sum(len(u.processes) for u in units)

        print(f"\n  Hierarchy Summary for: {business.name}")
        print(f"    Business GID: {business.gid}")
        print(f"    Contacts: {len(contacts)}")
        print(f"    Units: {len(units)}")
        print(f"    Total Offers: {total_offers}")
        print(f"    Active Offers: {active_offers}")
        print(f"    Processes: {total_processes}")
        print(f"    Locations: {len(locations)}")
        print(f"    Has Hours: {'Yes' if hours else 'No'}")

        print("\n  API Performance:")
        print(f"    API Calls: {result.api_calls}")
        print(f"    Hydrated Branches: {len(result.succeeded)}")
        print(f"    Failed Branches: {len(result.failed)}")

        # List all holder types present
        holder_types = []
        if business.contact_holder:
            holder_types.append("ContactHolder")
        if business.unit_holder:
            holder_types.append("UnitHolder")
        if business.location_holder:
            holder_types.append("LocationHolder")
        if business.dna_holder:
            holder_types.append("DNAHolder")
        if business.reconciliation_holder:
            holder_types.append("ReconciliationHolder")
        if business.asset_edit_holder:
            holder_types.append("AssetEditHolder")
        if business.videography_holder:
            holder_types.append("VideographyHolder")

        print(f"\n  Populated Holders: {', '.join(holder_types) or '(none)'}")

        print("\n" + "=" * 70)
        print("  Demo Complete!")
        print("=" * 70)

        return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive SDK demo - load any entity and explore the hierarchy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default Offer GID
    python scripts/example_offer_traversal.py

    # Use specific GID (Offer, Unit, Contact, or Business)
    python scripts/example_offer_traversal.py --gid 1203504352465403

SDK Features Demonstrated:
    - Typed Custom Field Descriptors (TextField, EnumField, NumberField, etc.)
    - Bidirectional Navigation (ParentRef, HolderRef descriptors)
    - Entity Hierarchy (Business -> Holders -> Entities)
    - Detection System (type detection via project membership)
    - Hydration (from any GID to full Business hierarchy)

Environment:
    ASANA_PAT: Your Asana Personal Access Token (required)
""",
    )
    parser.add_argument(
        "-g",
        "--gid",
        default="1203504352465403",
        help="Any GID in the hierarchy to start from (default: 1203504352465403)",
    )

    args = parser.parse_args()

    # Check for PAT
    if not os.environ.get("ASANA_PAT"):
        print("Error: ASANA_PAT environment variable not set")
        print("Set it with: export ASANA_PAT='your_token_here'")
        sys.exit(1)

    exit_code = asyncio.run(demo_sdk_capabilities(args.gid))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
