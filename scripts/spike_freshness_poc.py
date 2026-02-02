#!/usr/bin/env python3
"""POC: Validate section freshness probing via GID hash + modified_since.

This spike validates two core assumptions before committing to the full
section-level freshness remediation:

1. **GID hash stability**: Fetching task GIDs from a section with minimal
   opt_fields is fast (~1 lightweight API call), and hashing sorted GIDs
   produces a stable fingerprint that changes when tasks are added/removed.

2. **modified_since accuracy**: The Asana `modified_since` parameter on
   `tasks.list_async(section=...)` correctly returns only tasks modified
   after a given timestamp, enabling content-change detection without
   fetching full task data.

Usage:
    python scripts/spike_freshness_poc.py --entity offer
    python scripts/spike_freshness_poc.py --entity offer --section-index 0

Environment Variables:
    ASANA_PAT or ASANA_BOT_PAT - Asana Personal Access Token (required)
    ASANA_WORKSPACE_GID - Workspace GID (required)
"""

import argparse
import asyncio
import hashlib
import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def compute_gid_hash(gids: list[str]) -> str:
    """SHA-256 hash of sorted GIDs, truncated to 16 hex chars."""
    return hashlib.sha256("|".join(sorted(gids)).encode()).hexdigest()[:16]


async def run_spike(entity_filter: str, section_index: int | None = None) -> int:
    """Run the freshness POC against live Asana data.

    Args:
        entity_filter: Entity type to probe (e.g. "offer").
        section_index: Optional specific section index to probe.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import get_bot_pat
    from autom8_asana.services.discovery import discover_entity_projects_async

    bot_pat = get_bot_pat()
    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID", "")

    # Discover project GID for entity type
    entity_registry = await discover_entity_projects_async()
    config = entity_registry.get_config(entity_filter)
    if not config or not config.project_gid:
        logger.error(f"Entity type '{entity_filter}' not found in registry.")
        return 1

    project_gid = config.project_gid
    logger.info(f"Target project: {project_gid} ({entity_filter})")

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        # ── Step 1: List sections ──
        sections = await client.sections.list_for_project_async(project_gid).collect()
        logger.info(f"Found {len(sections)} sections")

        if section_index is not None:
            sections = [sections[section_index]]
            logger.info(f"Probing single section at index {section_index}")

        # ── Step 2: For each section, run probes ──
        for idx, section in enumerate(sections):
            section_name = getattr(section, "name", "?")
            logger.info(f"\n{'='*60}")
            logger.info(f"Section [{idx}]: {section_name} (GID: {section.gid})")
            logger.info(f"{'='*60}")

            # ── Probe A: GID-only fetch (lightweight) ──
            t0 = time.perf_counter()
            gid_tasks = await client.tasks.list_async(
                section=section.gid,
                opt_fields=["gid"],
            ).collect()
            gid_fetch_ms = (time.perf_counter() - t0) * 1000

            gids = [t.gid for t in gid_tasks if t.gid]
            gid_hash = compute_gid_hash(gids)

            logger.info(
                f"  GID fetch: {len(gids)} tasks, "
                f"hash={gid_hash}, "
                f"time={gid_fetch_ms:.1f}ms"
            )

            # ── Probe A2: Repeat GID fetch to verify hash stability ──
            t0 = time.perf_counter()
            gid_tasks_2 = await client.tasks.list_async(
                section=section.gid,
                opt_fields=["gid"],
            ).collect()
            gid_fetch_2_ms = (time.perf_counter() - t0) * 1000

            gids_2 = [t.gid for t in gid_tasks_2 if t.gid]
            gid_hash_2 = compute_gid_hash(gids_2)

            hash_stable = gid_hash == gid_hash_2
            logger.info(
                f"  GID re-fetch: hash={gid_hash_2}, "
                f"stable={hash_stable}, "
                f"time={gid_fetch_2_ms:.1f}ms"
            )
            if not hash_stable:
                logger.warning("  !! GID hash NOT stable between consecutive fetches")

            # ── Probe B: modified_since with recent watermark ──
            # Use 1 hour ago — should return recently modified tasks (if any)
            watermark_1h = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
            t0 = time.perf_counter()
            modified_1h = await client.tasks.list_async(
                section=section.gid,
                modified_since=watermark_1h,
                opt_fields=["gid", "modified_at"],
            ).collect()
            modified_1h_ms = (time.perf_counter() - t0) * 1000

            logger.info(
                f"  modified_since (1h ago): {len(modified_1h)} tasks returned, "
                f"time={modified_1h_ms:.1f}ms"
            )
            for t in modified_1h[:3]:
                logger.info(f"    - {t.gid} modified_at={t.modified_at}")

            # ── Probe C: modified_since with old watermark (24h) ──
            watermark_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
            t0 = time.perf_counter()
            modified_24h = await client.tasks.list_async(
                section=section.gid,
                modified_since=watermark_24h,
                opt_fields=["gid", "modified_at"],
            ).collect()
            modified_24h_ms = (time.perf_counter() - t0) * 1000

            logger.info(
                f"  modified_since (24h ago): {len(modified_24h)} tasks returned, "
                f"time={modified_24h_ms:.1f}ms"
            )

            # ── Probe D: modified_since with future watermark (should return 0) ──
            watermark_future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
            t0 = time.perf_counter()
            modified_future = await client.tasks.list_async(
                section=section.gid,
                modified_since=watermark_future,
                opt_fields=["gid"],
                limit=1,
            ).collect()
            modified_future_ms = (time.perf_counter() - t0) * 1000

            logger.info(
                f"  modified_since (future): {len(modified_future)} tasks returned, "
                f"time={modified_future_ms:.1f}ms"
            )
            if len(modified_future) > 0:
                logger.warning(
                    "  !! Future watermark returned tasks — "
                    "modified_since may not work as expected"
                )

            # ── Probe E: modified_since with limit=1 for quick staleness check ──
            # This is the pattern we'd use in production: just check if ANY
            # task was modified since watermark, don't fetch all of them
            if gids:
                # Get max modified_at from full fetch to simulate stored watermark
                full_tasks = await client.tasks.list_async(
                    section=section.gid,
                    opt_fields=["gid", "modified_at"],
                ).collect()

                modified_ats = [
                    t.modified_at for t in full_tasks if t.modified_at
                ]
                if modified_ats:
                    max_modified = max(modified_ats)
                    logger.info(f"  Max modified_at in section: {max_modified}")

                    # Use max_modified as watermark — should return 0 if nothing changed
                    t0 = time.perf_counter()
                    check_tasks = await client.tasks.list_async(
                        section=section.gid,
                        modified_since=max_modified,
                        opt_fields=["gid"],
                        limit=1,
                    ).collect()
                    check_ms = (time.perf_counter() - t0) * 1000

                    logger.info(
                        f"  Staleness check (watermark=max_modified_at): "
                        f"{len(check_tasks)} tasks, time={check_ms:.1f}ms"
                    )
                    if len(check_tasks) == 0:
                        logger.info("  -> CLEAN: No modifications since watermark")
                    else:
                        logger.info(
                            f"  -> CONTENT_CHANGED: {len(check_tasks)} task(s) "
                            f"modified since watermark"
                        )

            # ── Summary for this section ──
            logger.info(f"\n  Section summary:")
            logger.info(f"    Tasks:           {len(gids)}")
            logger.info(f"    GID hash:        {gid_hash}")
            logger.info(f"    Hash stable:     {hash_stable}")
            logger.info(f"    GID fetch cost:  {gid_fetch_ms:.0f}ms + {gid_fetch_2_ms:.0f}ms")
            logger.info(f"    mod_since costs: {modified_1h_ms:.0f}ms (1h), {modified_24h_ms:.0f}ms (24h), {modified_future_ms:.0f}ms (future)")

    logger.info(f"\n{'='*60}")
    logger.info("POC COMPLETE")
    logger.info(f"{'='*60}")
    logger.info("Key findings to validate:")
    logger.info("  1. GID hash stable across consecutive fetches?")
    logger.info("  2. modified_since returns 0 for future watermark?")
    logger.info("  3. modified_since returns 0 when watermark == max(modified_at)?")
    logger.info("  4. GID-only fetch is lightweight (< 200ms per section)?")
    logger.info("  5. limit=1 modified_since is fast for quick staleness check?")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="POC: Validate section freshness probing"
    )
    parser.add_argument(
        "--entity",
        type=str,
        default="offer",
        help="Entity type to probe (default: offer)",
    )
    parser.add_argument(
        "--section-index",
        type=int,
        default=None,
        help="Optional: probe only this section index (0-based)",
    )
    args = parser.parse_args()
    return asyncio.run(run_spike(args.entity, args.section_index))


if __name__ == "__main__":
    sys.exit(main())
