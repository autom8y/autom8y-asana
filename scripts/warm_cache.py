#!/usr/bin/env python3
"""Standalone script to warm DataFrame cache by building and persisting to S3.

This script replicates the warm cache logic from api/main.py's _preload_dataframe_cache()
but runs standalone for operational use cases like:
- Scheduled cron jobs to pre-warm cache
- Manual cache warming before deployments
- Testing S3 persistence outside of API startup

Usage:
    python scripts/warm_cache.py

Environment Variables:
    ASANA_PAT - Asana Personal Access Token (required)
    ASANA_CACHE_S3_BUCKET - S3 bucket for persistence (required)
    ASANA_CACHE_S3_REGION - AWS region (default: us-east-1)

Per spike-s3-persistence integration map:
Uses EntityProjectRegistry to discover registered entity types and warms all projects.
"""

import asyncio
import logging
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def warm_all_projects() -> int:
    """Warm cache for all registered projects.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from autom8_asana.dataframes.persistence import DataFramePersistence
    from autom8_asana.services.resolver import EntityProjectRegistry

    start_time = time.perf_counter()

    try:
        # Initialize persistence
        persistence = DataFramePersistence()

        if not persistence.is_available:
            logger.error(
                "S3 persistence not available. "
                "Check ASANA_CACHE_S3_BUCKET environment variable."
            )
            return 1

        logger.info("S3 persistence available, starting cache warm...")

        # Get entity registry
        entity_registry = EntityProjectRegistry()

        if not entity_registry.is_ready():
            logger.error("Entity registry not ready. Cannot discover projects.")
            return 1

        # Get all registered entity types and their projects
        registered_types = entity_registry.get_all_entity_types()
        project_configs: list[tuple[str, str]] = []  # (project_gid, entity_type)

        for entity_type in registered_types:
            config = entity_registry.get_config(entity_type)
            if config and config.project_gid:
                project_configs.append((config.project_gid, entity_type))

        if not project_configs:
            logger.warning("No registered projects found. Nothing to warm.")
            return 0

        logger.info(f"Found {len(project_configs)} projects to warm")

        # Process each project
        success_count = 0
        failure_count = 0

        for project_gid, entity_type in project_configs:
            logger.info(f"Warming cache for {entity_type} (project: {project_gid})...")

            try:
                # Get schema and client
                from autom8_asana.client import get_client
                from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
                from autom8_asana.dataframes.section_persistence import (
                    SectionPersistence,
                )

                client = get_client()

                # Get schema for entity type
                schema = entity_registry.get_schema(entity_type)
                if schema is None:
                    logger.error(f"No schema found for entity type: {entity_type}")
                    failure_count += 1
                    continue

                # Create section persistence for progressive builder
                section_persistence = SectionPersistence()

                # Build DataFrame with progressive builder
                builder = ProgressiveProjectBuilder(
                    client=client,
                    project_gid=project_gid,
                    entity_type=entity_type,
                    schema=schema,
                    persistence=section_persistence,
                )

                # Build DataFrame progressively (will auto-persist sections to S3)
                result = await builder.build_progressive_async()

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
    return asyncio.run(warm_all_projects())


if __name__ == "__main__":
    sys.exit(main())
