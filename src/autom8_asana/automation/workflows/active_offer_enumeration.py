"""Shared ACTIVE-offer enumeration (ONE active-set definition; no second classifier).

Per ADR grain-bridge / TDD §2.3: both the insights export workflow and the
grain-bridge leads consumer enumerate the SAME set of ACTIVE Offer tasks. This
module is the single canonical implementation -- it reuses the SAME classifier
(``OFFER_CLASSIFIER`` + ``AccountActivity.ACTIVE``) and section-resolution
primitive, so there is exactly ONE active-set definition fleet-wide (DRY; no
second classifier).

The logic is the section-targeted fetch with a project-level fallback, extracted
verbatim from ``InsightsExportWorkflow`` (which now delegates here). ``logger``
and ``workflow_id`` are parameters so each consumer keeps identical log fidelity.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autom8_asana.models.business.activity import (
    OFFER_CLASSIFIER,
    AccountActivity,
    extract_section_name,
)
from autom8_asana.models.business.offer import Offer

if TYPE_CHECKING:
    from autom8y_log import LoggerProtocol

# Offer project GID (canonical source: Offer.PRIMARY_PROJECT_GID)
OFFER_PROJECT_GID: str = Offer.PRIMARY_PROJECT_GID  # type: ignore[assignment]


async def enumerate_active_offers(
    asana_client: Any,
    *,
    logger: LoggerProtocol,
    workflow_id: str,
) -> list[dict[str, Any]]:
    """List ACTIVE (non-completed) Offer tasks via section-targeted fetch.

    Primary path: resolve ACTIVE section GIDs, fetch tasks per section in
    parallel (Semaphore(5)), merge and dedup by GID. Fallback: project-level
    fetch with client-side ACTIVE classification.

    Args:
        asana_client: the Asana client (exposes ``.sections`` and ``.tasks``).
        logger: structured logger for enumeration observability.
        workflow_id: workflow identifier carried into log events.

    Returns:
        List of offer dicts with ``{gid, name}`` shape.
    """
    from autom8_asana.automation.workflows.section_resolution import (
        resolve_section_gids,
    )

    active_section_names = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)

    # Resolve section GIDs
    try:
        resolved = await resolve_section_gids(
            asana_client.sections,
            OFFER_PROJECT_GID,
            active_section_names,
        )
    except (
        Exception  # noqa: BLE001
    ):  # BROAD-CATCH: boundary -- section resolution failure falls back to full enumeration
        logger.warning(
            "section_resolution_failed_fallback",
            workflow_id=workflow_id,
            project_gid=OFFER_PROJECT_GID,
        )
        return await _enumerate_offers_fallback(asana_client, logger=logger)

    if not resolved:
        logger.warning(
            "section_resolution_empty_fallback",
            workflow_id=workflow_id,
            project_gid=OFFER_PROJECT_GID,
        )
        return await _enumerate_offers_fallback(asana_client, logger=logger)

    # Parallel section fetch with bounded concurrency
    semaphore = asyncio.Semaphore(5)

    async def fetch_section(section_gid: str) -> list[Any]:
        async with semaphore:
            result: list[Any] = await asana_client.tasks.list_async(
                section=section_gid,
                opt_fields=["name", "completed", "parent", "parent.name"],
                completed_since="now",
            ).collect()
            return result

    results = await asyncio.gather(
        *[fetch_section(gid) for gid in resolved.values()],
        return_exceptions=True,
    )

    # If any section fetch failed, fall back entirely
    if any(isinstance(r, Exception) for r in results):
        logger.warning(
            "section_fetch_partial_failure_fallback",
            workflow_id=workflow_id,
            project_gid=OFFER_PROJECT_GID,
            failed_count=sum(1 for r in results if isinstance(r, Exception)),
        )
        return await _enumerate_offers_fallback(asana_client, logger=logger)

    # Flatten, dedup by GID, build offer dicts
    seen_gids: set[str] = set()
    offers: list[dict[str, Any]] = []
    for section_tasks in results:
        assert isinstance(section_tasks, list)  # guarded by early-exit above
        for t in section_tasks:
            if t.completed or t.gid in seen_gids:
                continue
            seen_gids.add(t.gid)
            offers.append(
                {
                    "gid": t.gid,
                    "name": t.name,
                }
            )

    logger.info(
        "insights_section_targeted_enumeration",
        sections_targeted=len(resolved),
        tasks_enumerated=len(offers),
    )

    return offers


async def _enumerate_offers_fallback(
    asana_client: Any,
    *,
    logger: LoggerProtocol,
) -> list[dict[str, Any]]:
    """Fallback: project-level fetch with client-side ACTIVE classification.

    This is the pre-migration enumeration logic, preserved verbatim for
    resilience when section resolution or section-level fetch fails.
    """
    page_iterator = asana_client.tasks.list_async(
        project=OFFER_PROJECT_GID,
        opt_fields=[
            "name",
            "completed",
            "parent",
            "parent.name",
            "memberships.section.name",
        ],
        completed_since="now",
    )
    tasks = await page_iterator.collect()

    # Filter to non-completed tasks first
    non_completed = [t for t in tasks if not t.completed]
    total_before = len(non_completed)

    # Filter to only ACTIVE offers by section classification
    active_offers: list[dict[str, Any]] = []
    for t in non_completed:
        section_name = extract_section_name(t, OFFER_PROJECT_GID)
        if section_name is None:
            continue
        activity = OFFER_CLASSIFIER.classify(section_name)
        if activity != AccountActivity.ACTIVE:
            continue
        active_offers.append(
            {
                "gid": t.gid,
                "name": t.name,
            }
        )

    filtered_count = total_before - len(active_offers)
    if filtered_count > 0:
        logger.info(
            "insights_export_offers_filtered_by_activity",
            total_before=total_before,
            active_count=len(active_offers),
            filtered_count=filtered_count,
        )

    return active_offers
