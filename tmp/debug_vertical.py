#!/usr/bin/env python3
"""Debug script to inspect custom fields on Unit tasks."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")


async def main():
    from autom8_asana import AsanaClient

    pat = os.environ.get("TF_VAR_asana_pat")
    if not pat:
        print("ERROR: TF_VAR_asana_pat not set")
        sys.exit(1)

    project_gid = "1201081073731555"

    client = AsanaClient(token=pat)

    async with client:
        # Fetch a few tasks with ALL custom field details
        tasks = await client.tasks.get_tasks_for_project_async(
            project_gid,
            opt_fields=[
                "gid", "name",
                "custom_fields",
                "custom_fields.gid",
                "custom_fields.name",
                "custom_fields.resource_subtype",
                "custom_fields.display_value",
                "custom_fields.enum_value",
                "custom_fields.enum_value.name",
                "custom_fields.enum_value.gid",
            ],
            limit=10
        )

        print("=" * 60)
        print("Custom Fields on Unit Tasks")
        print("=" * 60)

        # Collect all unique custom field names
        all_cf_names = set()
        vertical_found = False

        for task in tasks:
            print(f"\nTask: {task.name} ({task.gid})")

            if not task.custom_fields:
                print("  (no custom_fields)")
                continue

            for cf in task.custom_fields:
                # Handle both dict and object styles
                if isinstance(cf, dict):
                    cf_name = cf.get("name", "?")
                    cf_gid = cf.get("gid", "?")
                    cf_type = cf.get("resource_subtype", "?")
                    cf_display = cf.get("display_value", None)
                    cf_enum = cf.get("enum_value")
                    enum_name = cf_enum.get("name") if isinstance(cf_enum, dict) else None
                else:
                    cf_name = getattr(cf, "name", "?")
                    cf_gid = getattr(cf, "gid", "?")
                    cf_type = getattr(cf, "resource_subtype", "?")
                    cf_display = getattr(cf, "display_value", None)
                    cf_enum = getattr(cf, "enum_value", None)
                    enum_name = cf_enum.name if cf_enum and hasattr(cf_enum, "name") else (
                        cf_enum.get("name") if isinstance(cf_enum, dict) else None
                    )

                all_cf_names.add(cf_name)

                # Check if this is the Vertical field
                if cf_name and "vertical" in cf_name.lower():
                    vertical_found = True
                    print(f"  *** {cf_name} ({cf_type}): enum_name={enum_name}, display={cf_display}")
                else:
                    print(f"  - {cf_name} ({cf_type}): display={cf_display}")

        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total unique custom field names: {len(all_cf_names)}")
        print(f"All names: {sorted(all_cf_names)}")
        print(f"Vertical field found: {vertical_found}")

        # Check for close matches
        print("\nFields containing 'vertical' (case-insensitive):")
        for name in sorted(all_cf_names):
            if "vertical" in name.lower():
                print(f"  - '{name}'")


if __name__ == "__main__":
    asyncio.run(main())
