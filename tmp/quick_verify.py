#!/usr/bin/env python3
"""Quick verification that cascade resolution works via the proper API."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")


async def main():
    from autom8_asana import AsanaClient
    from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder, _BASE_OPT_FIELDS
    from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

    pat = os.environ.get("TF_VAR_asana_pat")
    if not pat:
        print("ERROR: TF_VAR_asana_pat not set")
        sys.exit(1)

    project_gid = "1201081073731555"

    print("Quick verify: builder with client for cascade")
    print("=" * 50)

    client = AsanaClient(token=pat)

    async with client:
        # Fetch 30 tasks
        tasks = await client.tasks.list_async(
            project=project_gid, opt_fields=_BASE_OPT_FIELDS
        ).collect()
        tasks = tasks[:30]

        print(f"Fetched {len(tasks)} tasks")

        class MockProject:
            def __init__(self, gid, t):
                self.gid, self._tasks = gid, t
            @property
            def tasks(self):
                return self._tasks

        # Build WITH client (should work)
        print("\n1. Building WITH client (should have cascade data)...")
        builder_with = ProjectDataFrameBuilder(
            project=MockProject(project_gid, tasks),
            task_type="Unit",
            schema=UNIT_SCHEMA,
            client=client,  # <-- This is the key!
        )
        df_with = await builder_with.build_async()
        phone_with = df_with.filter(df_with["office_phone"].is_not_null()).height
        print(f"   office_phone NOT NULL: {phone_with}")

        # Build WITHOUT client (should NOT work - no cascade)
        print("\n2. Building WITHOUT client (no cascade data)...")
        builder_without = ProjectDataFrameBuilder(
            project=MockProject(project_gid, tasks),
            task_type="Unit",
            schema=UNIT_SCHEMA,
            # client NOT passed
        )
        df_without = await builder_without.build_async()
        phone_without = df_without.filter(df_without["office_phone"].is_not_null()).height
        print(f"   office_phone NOT NULL: {phone_without}")

        print(f"\n✓ Cascade resolution working: {phone_with > phone_without}")


if __name__ == "__main__":
    asyncio.run(main())
