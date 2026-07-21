"""Hierarchy warming for the progressive project builder.

Extracted from ProgressiveProjectBuilder to separate hierarchy warming
concern from the build pipeline. Handles:
- Reconstructing hierarchy from resumed parquet data
- Fetching and caching gap tasks missing from the store
- Populating the store with freshly-fetched section tasks
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.errors import S3_TRANSPORT_ERRORS
from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS
from autom8_asana.errors import RateLimitError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    import polars as pl

    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

    # The gap-parent fetch closure: gid -> (task_dict|None, rate_limited). Typed as
    # a Coroutine (not just Awaitable) so the chunk comprehension matches
    # gather_with_limit's ``list[Coroutine[...]]`` parameter.
    _GapFetch = Callable[[str], Coroutine[Any, Any, tuple[dict[str, Any] | None, bool]]]

__all__ = ["HierarchyWarmer"]

logger = get_logger(__name__)

# Gap-warm burst shaping (ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13): the
# fleet shares ONE Asana 1500/60s budget with per-process-only AIMD and no
# cross-consumer arbitration. An unchunked gap warm fires thousands of GETs in
# one gather; under budget contention a single surfaced RateLimitError (the
# transport has already exhausted its Retry-After retries by then) used to
# abort the WHOLE batch and discard every fetched parent (gaps_warmed=0 every
# cycle — the ASR offer-frame starvation). Chunking bounds the burst; the
# saturation abort banks partial progress and yields the budget instead of
# hammering a saturated ceiling.
_GAP_WARM_CHUNK_SIZE = 200
# Abort the remaining chunks when >= this fraction of a chunk rate-limited:
# the shared budget is saturated and further fetches this cycle are wasted
# spend. Progress is banked; the next SWR cycle resumes from the shrunken
# uncached set.
_GAP_WARM_SATURATION_ABORT_FRACTION = 0.5


class HierarchyWarmer:
    """Warms hierarchy index and populates store with parent chain data.

    Extracted from ProgressiveProjectBuilder to separate hierarchy
    warming concern from the build pipeline.
    """

    def __init__(
        self,
        store: Any,
        client: AsanaClient,
        project_gid: str,
        entity_type: str,
        max_concurrent: int,
        task_to_dict: Callable[[Task], dict[str, Any]],
    ) -> None:
        """Initialize HierarchyWarmer.

        Args:
            store: UnifiedStore for cache operations.
            client: AsanaClient for API calls.
            project_gid: Asana project GID.
            entity_type: Entity type string.
            max_concurrent: Max concurrent API fetches.
            task_to_dict: Callback to convert Task model to dict.
        """
        self._store = store
        self._client = client
        self._project_gid = project_gid
        self._entity_type = entity_type
        self._max_concurrent = max_concurrent
        self._task_to_dict = task_to_dict

    def reconstruct_hierarchy_from_dataframe(self, df: pl.DataFrame) -> int:
        """Reconstruct HierarchyIndex from resumed parquet parent_gid column.

        Per TDD-CASCADE-RESUME-FIX: When sections are loaded from S3,
        tasks are not registered in the UnifiedStore's HierarchyIndex.
        This method iterates the merged DataFrame and registers each
        (gid, parent_gid) pair so cascade validation (Step 5.5) can
        resolve parent chains for resumed sections.

        Args:
            df: Merged DataFrame with 'gid' and 'parent_gid' columns.

        Returns:
            Count of hierarchy entries registered.
        """
        if self._store is None:
            return 0

        if "gid" not in df.columns or "parent_gid" not in df.columns:
            return 0

        hierarchy = self._store.get_hierarchy_index()
        registered = 0

        gids = df["gid"].to_list()
        parent_gids = df["parent_gid"].to_list()

        for gid, parent_gid in zip(gids, parent_gids):
            if gid is None:
                continue

            # Skip if already registered (from freshly-fetched sections)
            if hierarchy.contains(str(gid)):
                continue

            # Build minimal task dict for hierarchy registration
            task_dict: dict[str, Any] = {"gid": str(gid)}
            if parent_gid is not None:
                task_dict["parent"] = {"gid": str(parent_gid)}

            hierarchy.register(task_dict)
            registered += 1

        if registered > 0:
            logger.info(
                "hierarchy_reconstructed_from_parquet",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "entries_registered": registered,
                    "total_rows": len(df),
                },
            )

        return registered

    async def warm_hierarchy_gaps_async(self, df: pl.DataFrame) -> int:
        """Warm hierarchy gaps by fetching uncached parent tasks from API.

        Per TDD-CASCADE-RESUME-FIX: After reconstructing unit → unit_holder
        links from parquet parent_gid, the unit_holder → business links are
        still missing because unit_holders were registered only as parents
        (not as tasks with their own parent). This method directly fetches
        uncached parent GIDs from the API — the API response reveals their
        parent (business), which gets registered in the hierarchy, completing
        the chain for cascade resolution.

        Per WS-1-cascade-null-fix: Fetches full task data from the API
        instead of storing GID-only stubs. Stubs lack the ``parent`` field
        needed by ``put_batch_async``'s hierarchy warming to discover the
        next level (e.g., unit_holder → business). Without the parent field,
        ``_fetch_immediate_parents`` finds no parents to fetch, leaving the
        chain incomplete and cascade fields unresolvable.

        Args:
            df: Merged DataFrame with 'parent_gid' column.

        Returns:
            Count of gap tasks fetched and cached.
        """
        if self._store is None or "parent_gid" not in df.columns:
            return 0

        # maintain_order: stable chunk composition across SWR cycles, so the
        # banked-progress resume walks the SAME tail instead of resampling a
        # shuffled set each cycle (monotonic convergence under contention).
        parent_gids = [
            str(g) for g in df["parent_gid"].drop_nulls().unique(maintain_order=True).to_list()
        ]
        if not parent_gids:
            return 0

        # Filter to parent GIDs not already cached as full task data
        from autom8_asana.cache.models.entry import EntryType

        uncached = []
        for gid in parent_gids:
            cached = self._store.cache.get_versioned(gid, EntryType.TASK)
            if cached is None:
                uncached.append(gid)

        if not uncached:
            return 0

        logger.info(
            "hierarchy_gap_fetch_starting",
            extra={
                "project_gid": self._project_gid,
                "entity_type": self._entity_type,
                "total_parent_gids": len(parent_gids),
                "uncached_count": len(uncached),
            },
        )

        # Fetch full task data from the API for each uncached parent.
        # Per WS-1-cascade-null-fix: GID-only stubs lack the ``parent``
        # field, so put_batch_async's _fetch_immediate_parents cannot
        # discover the next ancestor level. Fetching full task data
        # ensures the parent link is present, allowing hierarchy warming
        # to traverse the complete chain (e.g., unit_holder → business).
        #
        # Per ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13: fetches run in
        # bounded chunks, a surfaced RateLimitError tolerates per-fetch (the
        # transport already exhausted its Retry-After retries), and progress
        # is BANKED — a 429 must never discard the parents that did fetch.
        try:
            fetched_task_dicts: list[dict[str, Any]] = []
            rate_limited_total = 0
            aborted_early = False
            chain_warm_completed = True

            async def _fetch_gap_parent(gid: str) -> tuple[dict[str, Any] | None, bool]:
                """Fetch one gap parent. Returns (task_dict|None, rate_limited)."""
                try:
                    task = await self._client.tasks.get_async(gid, opt_fields=BASE_OPT_FIELDS)
                    if task is not None:
                        return self._task_to_dict(task), False
                    return None, False
                except RateLimitError as e:
                    logger.warning(
                        "hierarchy_gap_fetch_rate_limited",
                        extra={
                            "parent_gid": gid,
                            "retry_after": e.retry_after,
                        },
                    )
                    return None, True
                except S3_TRANSPORT_ERRORS as e:
                    logger.warning(
                        "hierarchy_gap_fetch_failed",
                        extra={
                            "parent_gid": gid,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    return None, False

            # F1a warmer floor wiring (ITEM-C / F-C3-01 cure). Resolved ONCE per
            # sweep: ``fetch_one`` routes every gap GET through the process
            # singleton's WarmerFloorGate on the real clock ONLY in the warmer lane
            # with the allocator ARMED; otherwise it IS ``_fetch_gap_parent``
            # unchanged -- byte-identical Asana request path, no per-GET branch, no
            # per-GET env read (the ITEM-D dead-knob discipline hoisted to the sweep
            # seam). ``cure_active`` also gates the AC-4 (b') per-chunk banking
            # cadence below, so the cure (floor pacing + durable per-chunk banking)
            # arms together at the flip -- one lever, two co-required behaviours.
            fetch_one, cure_active = self._floor_paced(_fetch_gap_parent)

            for chunk_start in range(0, len(uncached), _GAP_WARM_CHUNK_SIZE):
                chunk = uncached[chunk_start : chunk_start + _GAP_WARM_CHUNK_SIZE]
                results = await gather_with_limit(
                    [fetch_one(gid) for gid in chunk],
                    max_concurrent=self._max_concurrent,
                )
                chunk_dicts = [d for d, _ in results if d is not None]
                fetched_task_dicts.extend(chunk_dicts)
                chunk_rate_limited = sum(1 for _, limited in results if limited)
                rate_limited_total += chunk_rate_limited

                # AC-4 (b') per-chunk banking: durably bank THIS chunk before
                # continuing, so a 900s Lambda-wall truncation -- which floor pacing
                # GUARANTEES for large gap sets (a 3,291-GET sweep is ~1,795s at
                # 110/60s, well past the 900s wall: the §3.3 inversion) -- loses at
                # most one chunk. Stable ordering (maintain_order) then drops each
                # banked head chunk out of the next tick's uncached set: cumulative
                # convergence in <=2-3 ticks instead of a lose-everything restart.
                # Active ONLY with the cure; OFF => single end-of-sweep banking
                # (byte-identical baseline) below.
                if cure_active and chunk_dicts and not await self._bank_gap_chunk(chunk_dicts):
                    chain_warm_completed = False

                if chunk_rate_limited >= max(
                    1, int(len(chunk) * _GAP_WARM_SATURATION_ABORT_FRACTION)
                ):
                    aborted_early = True
                    break

            if not fetched_task_dicts:
                logger.warning(
                    "hierarchy_gap_no_tasks_fetched",
                    extra={
                        "project_gid": self._project_gid,
                        "entity_type": self._entity_type,
                        "attempted": len(uncached),
                        "rate_limited": rate_limited_total,
                    },
                )
                return 0

            # Baseline single end-of-sweep banking (byte-identical when INERT). The
            # cure already banked per-chunk above, so this runs ONLY when inert.
            # Now that task_dicts carry full parent info, _fetch_immediate_parents
            # discovers and fetches the next ancestor level (e.g., business from
            # unit_holder.parent). put_batch_async stores BEFORE it warms
            # (unified.py), so a 429 from the recursive chain warm must not discard
            # the banked store: the parents ARE cached, and the next SWR cycle
            # resumes from the shrunken uncached set.
            if not cure_active and not await self._bank_gap_chunk(fetched_task_dicts):
                chain_warm_completed = False

            if aborted_early or rate_limited_total or not chain_warm_completed:
                logger.warning(
                    "hierarchy_gap_warming_partial",
                    extra={
                        "project_gid": self._project_gid,
                        "entity_type": self._entity_type,
                        "attempted": len(uncached),
                        "fetched": len(fetched_task_dicts),
                        "rate_limited": rate_limited_total,
                        "aborted_early": aborted_early,
                        "chain_warm_completed": chain_warm_completed,
                    },
                )
            else:
                logger.info(
                    "hierarchy_gap_warming_complete",
                    extra={
                        "project_gid": self._project_gid,
                        "entity_type": self._entity_type,
                        "attempted": len(uncached),
                        "fetched": len(fetched_task_dicts),
                    },
                )

            return len(fetched_task_dicts)
        except Exception as e:  # BROAD-CATCH: enrichment  # noqa: BLE001
            logger.warning(
                "hierarchy_gap_warming_failed",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "parent_gids_count": len(uncached),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0

    def _floor_paced(self, fetch: _GapFetch) -> tuple[_GapFetch, bool]:
        """Wrap the gap-parent fetch with the F1a warmer floor gate when armed (ITEM-C).

        Returns ``(fetch, False)`` UNCHANGED unless BOTH hold: the process is the
        substrate warmer lane (``running_in_warmer_lane`` -- the cache-warmer
        Lambdas only) AND the process-singleton allocator is ARMED (operator flip,
        F-a). In that case returns ``(paced_fetch, True)`` where every gap-warm GET
        is first admitted through the allocator's ``WarmerFloorGate`` on the real
        clock -- the production call path the QA live-leg harness drove by hand
        (QA-live-leg-verdict.md), closing F-C3-01's falsification pathway -- and
        each admitted outbound GET is recorded via ``observe_admission`` (the AC-2
        admitted-vs-outbound denominator the flip custody found unwired).

        The pacing decision is resolved ONCE per sweep: when inert the returned
        callable IS ``fetch`` itself, so the per-GET Asana path is byte-identical to
        the pre-wiring baseline with NO branch and NO env read (the ITEM-D dead-knob
        discipline hoisted to the sweep seam). Fail-OPEN (pythia PC-3 / C-4): any
        allocator-internal fault returns the unpaced fetch and emits
        ``budget_lane_failopen`` -- a warm sweep is NEVER blocked by the limiter
        (fail-closed would worsen the storm the node-4 gate defeated).
        """
        from autom8_asana.transport.budget_allocator import (
            Lane,
            get_budget_allocator,
            running_in_warmer_lane,
        )

        try:
            if not running_in_warmer_lane():
                return fetch, False
            allocator = get_budget_allocator()
            if not allocator.enabled:
                return fetch, False
            gate = allocator.warmer_floor_gate()  # REAL clock + asyncio.sleep
        except Exception as exc:  # noqa: BLE001 -- fail-OPEN (C-4); never fail-closed
            self._note_floor_failopen(exc)
            return fetch, False

        async def _floor_paced_fetch(gid: str) -> tuple[dict[str, Any] | None, bool]:
            try:
                await gate.admit()  # earned-token admission at the static floor rate
            except Exception as exc:  # noqa: BLE001 -- never fail-closed on the gate
                self._note_floor_failopen(exc)
                return await fetch(gid)
            # One admitted gate passage == exactly one outbound gap GET (the fetch
            # issues one GET regardless of outcome). Record it for the AC-2
            # admitted-vs-outbound reconciliation. Warmer admissions are
            # floor-protected, so observe_admission telemeters NO overage for this
            # lane (PC-4 warmer-insulation) -- the call establishes the live
            # production admission-observation site the custody found ABSENT.
            # Advisory only: suppressed so it can never fail-close the sweep (C-4).
            with contextlib.suppress(Exception):
                allocator.observe_admission(Lane.WARMER)
            return await fetch(gid)

        return _floor_paced_fetch, True

    async def _bank_gap_chunk(self, task_dicts: list[dict[str, Any]]) -> bool:
        """Durably bank a batch of fetched gap parents; return chain-warm completion.

        Extracted from the single end-of-sweep banking so the AC-4 (b') fix can
        invoke it PER-CHUNK without changing its semantics. ``put_batch_async``
        stores BEFORE it warms (unified.py), so a ``RateLimitError`` surfaced by the
        recursive chain-warm does NOT discard the just-stored parents -- they are
        durable regardless. Returns ``False`` (and emits
        ``hierarchy_gap_chain_warm_rate_limited``) when the recursive chain-warm was
        rate-limited, matching the pre-existing partial-progress semantics.
        """
        try:
            await self._store.put_batch_async(
                task_dicts,
                opt_fields=BASE_OPT_FIELDS,
                tasks_client=self._client.tasks,
                warm_hierarchy=True,
            )
            return True
        except RateLimitError as e:
            logger.warning(
                "hierarchy_gap_chain_warm_rate_limited",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "stored": len(task_dicts),
                    "retry_after": e.retry_after,
                },
            )
            return False

    def _note_floor_failopen(self, error: BaseException) -> None:
        """Emit ``budget_lane_failopen`` for a warmer-lane gate fault (PC-3 / C-4).

        Best-effort and self-contained: the warm sweep proceeds un-paced regardless
        (fail-OPEN). Mirrors ``client.py._attach_to_budget_allocator``'s guarded
        tripwire -- the emission can never re-raise and fail-close the sweep.
        """
        try:
            from autom8_asana.transport.budget_allocator import Lane, get_budget_allocator

            get_budget_allocator().note_lane_failopen(Lane.WARMER, error)
        except Exception:  # noqa: BLE001 -- never let the tripwire fail-close the sweep
            logger.warning(
                "budget_lane_failopen",
                extra={
                    "lane": "warmer",
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
            )

    async def populate_store_with_tasks(self, tasks: list[Task]) -> None:
        """Populate UnifiedStore with fetched tasks for cascade resolution.

        Per ADR-cascade-field-resolution: Uses put_batch_async with warm_hierarchy=True
        to recursively fetch and cache parent tasks. This ensures fields like
        office_phone and vertical that cascade from Business are properly resolved.

        The hierarchy warming:
        - Fetches immediate parents not already in cache
        - Recursively warms ancestors up to max_depth=5
        - Includes custom_fields for cascade field extraction
        """
        if not tasks or self._store is None:
            return

        try:
            # Convert Task models to dicts for batch storage
            task_dicts = [self._task_to_dict(task) for task in tasks]

            logger.info(
                "store_populate_batch_starting",
                extra={
                    "task_count": len(task_dicts),
                    "entity_type": self._entity_type,
                    "project_gid": self._project_gid,
                    "warm_hierarchy": True,
                },
            )

            # Use put_batch_async with hierarchy warming - same pattern as project.py
            # This recursively fetches and caches parent chains for cascade resolution
            await self._store.put_batch_async(
                task_dicts,
                opt_fields=BASE_OPT_FIELDS,
                tasks_client=self._client.tasks,
                warm_hierarchy=True,
            )

        except Exception as e:  # BROAD-CATCH: enrichment  # noqa: BLE001
            # Don't fail build if store population fails
            logger.warning(
                "store_populate_batch_failed",
                extra={
                    "task_count": len(tasks),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "entity_type": self._entity_type,
                },
            )
