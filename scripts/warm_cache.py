#!/usr/bin/env python3
"""Standalone script to warm DataFrame cache by building and persisting to S3.

This script replicates the warm cache logic from api/main.py's _preload_dataframe_cache()
but runs standalone for operational use cases like:
- Scheduled cron jobs to pre-warm cache
- Manual cache warming before deployments
- Testing S3 persistence outside of API startup

Usage:
    python scripts/warm_cache.py
    python scripts/warm_cache.py --entity offer

Environment Variables:
    ASANA_PAT or ASANA_BOT_PAT - Asana Personal Access Token (required)
    ASANA_WORKSPACE_GID - Workspace GID (required)
    ASANA_CACHE_S3_BUCKET - S3 bucket for persistence (required)
    ASANA_CACHE_S3_REGION - AWS region (default: us-east-1)

Per spike-s3-persistence integration map:
Uses discover_entity_projects_async to populate EntityProjectRegistry, then warms all projects.
"""

import argparse
import asyncio
import logging
import os
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def warm_all_projects(
    entity_filter: str | None = None,
    force: bool = False,
) -> int:
    """Warm cache for all registered projects.

    Args:
        entity_filter: Optional entity type to filter to (e.g. "offer").
        force: If True, bypass manifest resume and do a full rebuild.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import get_bot_pat
    from autom8_asana.config import S3LocationConfig
    from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.dataframes.storage import (
        S3DataFrameStorage,
        create_s3_retry_orchestrator,
    )
    from autom8_asana.services.discovery import discover_entity_projects_async
    from autom8_asana.services.resolver import to_pascal_case

    start_time = time.perf_counter()

    try:
        # Initialize S3DataFrameStorage
        bucket = os.environ.get("ASANA_CACHE_S3_BUCKET", "")
        if not bucket:
            logger.error(
                "S3 persistence not available. "
                "Check ASANA_CACHE_S3_BUCKET environment variable."
            )
            return 1

        location = S3LocationConfig(
            bucket=bucket,
            region=os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1"),
        )
        retry_orchestrator = create_s3_retry_orchestrator()
        df_storage = S3DataFrameStorage(
            location=location, retry=retry_orchestrator,
        )

        if not await df_storage.is_available():
            logger.error(
                "S3 persistence not available. "
                "Check S3 bucket access and credentials."
            )
            return 1

        logger.info("S3 persistence available, starting cache warm...")

        # Discover entity projects (populates EntityProjectRegistry)
        logger.info("Running entity project discovery...")
        entity_registry = await discover_entity_projects_async()

        if not entity_registry.is_ready():
            logger.error("Entity registry not ready after discovery. Cannot warm cache.")
            return 1

        # Get all registered entity types and their projects
        registered_types = entity_registry.get_all_entity_types()
        project_configs: list[tuple[str, str]] = []  # (project_gid, entity_type)

        for entity_type in registered_types:
            if entity_filter and entity_type != entity_filter:
                continue
            config = entity_registry.get_config(entity_type)
            if config and config.project_gid:
                project_configs.append((config.project_gid, entity_type))

        if not project_configs:
            if entity_filter:
                logger.warning(
                    f"Entity type '{entity_filter}' not found in registry. "
                    f"Available: {registered_types}"
                )
            else:
                logger.warning("No registered projects found. Nothing to warm.")
            return 0

        logger.info(f"Found {len(project_configs)} projects to warm")

        # Get credentials for AsanaClient
        bot_pat = get_bot_pat()
        workspace_gid = os.environ.get("ASANA_WORKSPACE_GID", "")

        # Process each project
        success_count = 0
        failure_count = 0
        schema_registry = SchemaRegistry.get_instance()

        for project_gid, entity_type in project_configs:
            logger.info(f"Warming cache for {entity_type} (project: {project_gid})...")

            try:
                # Get schema for entity type via SchemaRegistry with PascalCase key
                task_type = to_pascal_case(entity_type)
                schema = schema_registry.get_schema(task_type)

                resolver = DefaultCustomFieldResolver()
                section_persistence = SectionPersistence(storage=df_storage)

                async with section_persistence:
                    async with AsanaClient(
                        token=bot_pat, workspace_gid=workspace_gid
                    ) as client:
                        builder = ProgressiveProjectBuilder(
                            client=client,
                            project_gid=project_gid,
                            entity_type=entity_type,
                            schema=schema,
                            persistence=section_persistence,
                            resolver=resolver,
                            store=client.unified_store,
                        )

                        # Build DataFrame progressively (will auto-persist sections to S3)
                        result = await builder.build_progressive_async(
                            resume=not force,
                        )

                logger.info(
                    f"Successfully warmed {entity_type}: {result.total_rows} rows persisted"
                )
                success_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to warm {entity_type} (project: {project_gid}): {e}"
                )
                failure_count += 1

        # Summary
        elapsed = time.perf_counter() - start_time
        logger.info(
            f"Cache warm complete: {success_count} succeeded, "
            f"{failure_count} failed, {elapsed:.2f}s elapsed"
        )

        return 0 if failure_count == 0 else 1

    except Exception as e:
        logger.error(f"Cache warm failed: {e}", exc_info=True)
        return 1


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Warm DataFrame cache to S3")
    parser.add_argument(
        "--entity",
        type=str,
        default=None,
        help="Optional entity type to warm (e.g. 'offer'). Warms all if omitted.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force full rebuild (no resume from manifest, no freshness probing).",
    )
    args = parser.parse_args()
    return asyncio.run(warm_all_projects(entity_filter=args.entity, force=args.force))


if __name__ == "__main__":
    sys.exit(main())
