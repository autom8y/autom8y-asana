#!/usr/bin/env python3
"""Debug script to check resolver index contents."""

import asyncio
import os
import sys

os.environ["LOG_LEVEL"] = "WARNING"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")


async def main():
    from autom8_asana import AsanaClient
    from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver
    from autom8_asana.models.custom_field import CustomField

    pat = os.environ.get("TF_VAR_asana_pat")
    if not pat:
        print("ERROR: TF_VAR_asana_pat not set")
        return

    project_gid = "1201081073731555"

    client = AsanaClient(token=pat)

    async with client:
        # Get project
        project = await client.projects.get_async(project_gid)
        print(f"Project: {project.name}")

        # Get sections and tasks
        print("\n=== Checking first Unit task's custom_fields ===")
        sections = [
            s async for s in client.sections.list_for_project_async(project_gid)
        ]
        for section in sections:
            if "template" in section.name.lower():
                continue

            print(f"\nSection: {section.name}")
            tasks = [
                t
                async for t in client.tasks.list_for_section_async(
                    section.gid,
                    opt_fields=[
                        "name",
                        "parent.gid",
                        "parent.name",
                        "custom_fields",
                        "custom_fields.name",
                        "custom_fields.gid",
                        "custom_fields.resource_subtype",
                        "custom_fields.display_value",
                        "custom_fields.enum_value",
                        "custom_fields.enum_value.name",
                    ],
                    limit=5,
                )
            ]

            for task in tasks:
                # Only check tasks with parents (Unit tasks have parent = UnitHolder)
                if not task.parent:
                    continue

                print(f"\nTask: {task.name} (parent: {task.parent.name})")

                # Build resolver index
                resolver = DefaultCustomFieldResolver()
                if task.custom_fields:
                    cfs = [
                        CustomField.model_validate(cf) if isinstance(cf, dict) else cf
                        for cf in task.custom_fields
                    ]
                    resolver.build_index(cfs)

                    print(f"  Resolver index has {len(resolver._index)} fields:")
                    for key, gid in sorted(resolver._index.items()):
                        info = resolver._gid_to_info.get(gid, {})
                        original_name = info.get("name", "?")
                        field_type = info.get("type", "?")
                        print(
                            f"    '{key}' -> {gid} (original: '{original_name}', type: {field_type})"
                        )

                    # Try to resolve vertical
                    print("\n  Testing resolution:")
                    for field_name in ["Vertical", "vertical", "cf:Vertical"]:
                        gid = resolver.resolve(field_name)
                        value = resolver.get_value(task, field_name) if gid else None
                        print(f"    {field_name!r} -> gid={gid}, value={value!r}")

                    # Check the actual custom_fields data for vertical
                    print("\n  Raw custom_fields matching 'vertical':")
                    for cf in task.custom_fields:
                        cf_name = (
                            cf.get("name")
                            if isinstance(cf, dict)
                            else getattr(cf, "name", None)
                        )
                        if cf_name and "vertical" in cf_name.lower():
                            print(f"    {cf}")

                    break  # Just check first Unit task
            break  # Just check first section


if __name__ == "__main__":
    asyncio.run(main())
