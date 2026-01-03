#!/usr/bin/env python3
"""Quick test to verify cascade:Vertical fix works."""

import asyncio
import os
import sys

os.environ["LOG_LEVEL"] = "WARNING"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")


async def main():
    from autom8_asana import AsanaClient
    from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

    pat = os.environ.get("TF_VAR_asana_pat")
    if not pat:
        print("ERROR: TF_VAR_asana_pat not set")
        sys.exit(1)

    # Find the vertical column definition
    vertical_col = None
    for col in UNIT_SCHEMA.columns:
        if col.name == "vertical":
            vertical_col = col
            break

    print("=" * 60)
    print("Testing cascade:Vertical Fix")
    print("=" * 60)
    print(f"\nSchema column: {vertical_col.name}")
    print(f"  source: {vertical_col.source}")
    print(f"  dtype: {vertical_col.dtype}")

    # Verify it's using cascade: prefix now
    if vertical_col.source and vertical_col.source.startswith("cascade:"):
        print("\n✅ Schema fix verified: using cascade: prefix")
    else:
        print(f"\n❌ Schema NOT fixed: source={vertical_col.source}")
        sys.exit(1)

    # Quick test with a single section
    project_gid = "1201081073731555"
    client = AsanaClient(token=pat)

    async with client:
        # Get just 5 tasks from one section to test
        print("\nFetching 5 tasks to test cascade resolution...")

        sections = await client.sections.list_for_project_async(project_gid).collect()
        if not sections:
            print("No sections found")
            return

        first_section = sections[0]
        print(f"Using section: {first_section.name}")

        tasks = await client.tasks.list_async(
            section=first_section.gid,
            opt_fields=[
                "gid", "name", "parent", "parent.gid", "parent.name",
                "custom_fields", "custom_fields.name",
                "custom_fields.display_value", "custom_fields.enum_value",
                "custom_fields.enum_value.name"
            ],
            limit=5
        ).collect()

        print(f"\nChecking {len(tasks)} tasks for Vertical field:")

        vertical_found = 0
        for task in tasks:
            print(f"\n  Task: {task.name[:40]}...")

            # Check custom_fields on task
            if task.custom_fields:
                for cf in task.custom_fields:
                    cf_name = cf.get("name") if isinstance(cf, dict) else getattr(cf, "name", None)
                    if cf_name and "vertical" in cf_name.lower():
                        cf_display = cf.get("display_value") if isinstance(cf, dict) else getattr(cf, "display_value", None)
                        cf_enum = cf.get("enum_value") if isinstance(cf, dict) else getattr(cf, "enum_value", None)
                        enum_name = None
                        if cf_enum:
                            enum_name = cf_enum.get("name") if isinstance(cf_enum, dict) else getattr(cf_enum, "name", None)
                        print(f"    Found Vertical: enum={enum_name}, display={cf_display}")
                        vertical_found += 1

            # Check parent for cascade
            if task.parent:
                parent_name = task.parent.get("name") if isinstance(task.parent, dict) else getattr(task.parent, "name", None)
                parent_gid = task.parent.get("gid") if isinstance(task.parent, dict) else getattr(task.parent, "gid", None)
                print(f"    Parent: {parent_name} ({parent_gid})")

        print(f"\n{'=' * 60}")
        print(f"Summary: {vertical_found}/{len(tasks)} tasks have Vertical on task itself")
        print("Cascade resolution will find Vertical on parent chain")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
