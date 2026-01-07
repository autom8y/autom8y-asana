#!/usr/bin/env python3
"""Export Business Units DataFrame to clipboard using proper materialization tooling."""

import asyncio
import os
import subprocess
import sys

# Fix LOG_LEVEL case sensitivity issue with autom8y_log
if "LOG_LEVEL" in os.environ:
    os.environ["LOG_LEVEL"] = os.environ["LOG_LEVEL"].upper()
else:
    os.environ["LOG_LEVEL"] = "INFO"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")


async def main():
    from autom8_asana import AsanaClient

    pat = os.environ.get("TF_VAR_asana_pat")
    if not pat:
        print("ERROR: TF_VAR_asana_pat not set")
        sys.exit(1)

    project_gid = "1201081073731555"

    print("=" * 60)
    print("Business Units DataFrame Export (Full Materialization)")
    print("=" * 60)

    client = AsanaClient(token=pat)

    async with client:
        # Get the project
        print(f"\n1. Fetching project {project_gid}...")
        project = await client.projects.get_async(project_gid)
        print(f"   Project: {project.name}")

        # Use the proper API with parallel fetch (handles all the caching/refresh)
        print("\n2. Building DataFrame with parallel fetch...")
        print("   (Cold start - fetching all sections in parallel)")

        df = await project.to_dataframe_parallel_async(
            client=client,
            task_type="Unit",  # Uses UNIT_SCHEMA automatically
        )

        print("\n3. DataFrame Stats:")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")

        if "office_phone" in df.columns:
            phone_count = df.filter(df["office_phone"].is_not_null()).height
            print(f"   office_phone NOT NULL: {phone_count}")

        if "vertical" in df.columns:
            vert_count = df.filter(df["vertical"].is_not_null()).height
            print(f"   vertical NOT NULL: {vert_count}")

            # Show sample vertical values
            if vert_count > 0:
                sample_verts = df.filter(df["vertical"].is_not_null())["vertical"].unique().to_list()
                print(f"   vertical values: {sample_verts[:10]}")

        # Export to clipboard
        print("\n4. Exporting to clipboard...")

        # Select key columns for debugging
        export_cols = ["gid", "name", "office_phone", "vertical", "section", "mrr"]
        export_cols = [c for c in export_cols if c in df.columns]

        csv_str = df.select(export_cols).write_csv()
        subprocess.run(["pbcopy"], input=csv_str.encode(), check=True)

        print(f"\n✓ Copied {len(df)} rows to clipboard!")
        print(f"  Columns: {export_cols}")
        print("  Paste into Google Sheets with Cmd+V")


if __name__ == "__main__":
    asyncio.run(main())
