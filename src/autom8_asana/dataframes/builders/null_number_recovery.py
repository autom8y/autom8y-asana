"""Post-build path-canon recovery of stripped numeric custom-field cells (FPC Phase-2).

A field-agnostic, cache-reuse-only pass that re-populates null *numeric*
custom-field cells (``mrr``, ``weekly_ad_spend``, and any other ``cf:`` number
column) by re-reading the per-task cache copy that the hierarchy warm already
fetched. It runs post-build, BEFORE the value-population receipt, so the floor
receipt assesses a HEALED frame.

The defect it cures (FPC Phase-2, path-asymmetry null mechanism)
---------------------------------------------------------------
``BASE_OPT_FIELDS`` includes ``custom_fields.number_value``, so the full-section
fetch carries the number. The null arises on the GID-only warm path
(``parallel_fetch._fetch_section_gids`` lists with ``opt_fields=["gid"]`` then
hydrates from cache): when the section-list frame is built from a reduced-field
view, a populated ``number_value`` that DOES live in the standard-completeness
cache copy of the same task is dropped from the cell. The user's economics
question then gets a silent ``$0`` instead of the populated figure.

The cure re-reads the standard-completeness cache copy of each null-cell task and
backfills ONLY where the cache carries a genuinely non-null ``number_value``. A
cell whose cache copy is ALSO null (operator never entered the value, or the task
was warmed at MINIMAL completeness) stays honest-null -- the pass NEVER fabricates.

The cold-tier (S3) recovery (FPC Phase-2, cache-tier read defect)
-----------------------------------------------------------------
On the steady-state receiver warm the hot store is COLD for the unit gids: the
progressive build is ``resume=True`` and re-fetches 0 tasks, so the just-warmed
hot copy the docstring above assumed does NOT exist. The hot
``store.get_batch_async(IMMEDIATE)`` therefore cache-MISSES every null gid. BUT
the data is durably present in the S3 per-task copies
(``{prefix}/tasks/{gid}/task.json`` carries the populated ``number_value``),
written by the warmer's durable-first path. The hot-store read alone never
consults that tier -- the application store is a bare Redis provider with no S3
cold tier wired in, and even a ``TieredCacheProvider`` would gate the cold read
behind the global ``ASANA_CACHE_S3_ENABLED`` flag (unset on the warmer Lambda and
ECS). So the cure adds a SECOND, durable-tier read: for the gids that miss the
hot store, a bounded-concurrency S3 read of the per-task copies, independent of
warm-mode and the global flag. Hot hits always win; S3 fills only the hot misses.

SCAR-TISSUE (D-1, template-null integrity rests on the durable-WRITE path)
--------------------------------------------------------------------------
This cure is field-agnostic and G-DENOM: it faithfully heals WHATEVER non-null
``number_value`` the durable per-task copy carries, and by design does NOT classify
active vs template tasks. Therefore template-null integrity is NOT enforced here --
it rests entirely on the durable-WRITE path: the warmer MUST NOT persist a number
into a template task's ``task.json``. If a template copy is ever written with a
populated ``number_value``, this cure will dutifully surface it as a healed cell
(it cannot distinguish "operator-entered value" from "warmer-fabricated value" --
both are non-null numbers in the durable copy). The write-side invariant is the
load-bearing guard; the read-side cure is intentionally faithful, not discerning.

Invariants (HARD)
-----------------
1. **Cache-reuse only / zero Asana GETs.** The hot ``store.get_batch_async``
   call uses ``FreshnessIntent.IMMEDIATE`` (``entry.data`` for cache-present gids,
   ZERO freshness round-trips, ZERO Asana GETs). The cold-tier fill is a single
   batched S3 read -- S3 is durable cache, NOT Asana, so the single-worker
   receiver's SlowAPI budget (CR-3) is never charged and the Asana GET count
   stays 0. (PV-7 measured: warmed corpus => 0 GET delta; an N+1-per-null mutant
   => row-count GETs, which the regression guard catches RED.)
2. **IMMEDIATE freshness.** The warmed cache copy (hot or durable-S3) IS the
   post-warm truth-of-record; re-validating it would be both wasteful and a
   network hit. The S3 read uses ``FreshnessIntent.EVENTUAL`` (no source
   round-trip; honors only TTL, which the durable writes set to 7 days).
3. **not-N+1.** ONE hot batch read + at most ONE cold batch read for the missed
   gids -- both bounded by distinct null-row gids, never by (rows x columns).
4. **Never-fabricate.** A null-in-both-tiers-AND-null-source cell stays null.
5. **Additive / never-raises.** Mirrors the population-receipt posture: a
   degraded-but-present warm must still serve; any failure (including any S3
   backend error) logs a structured WARN and returns the frame unchanged.
6. **Warm path untouched.** This is a post-build heal; it does not change
   ``parallel_fetch`` opt_fields or the merge.

Field-agnosticism (G-PROPAGATE)
-------------------------------
The pass iterates every ``ColumnDef`` whose ``source`` is ``cf:<name>`` and whose
dtype is numeric. ``mrr`` and ``weekly_ad_spend`` heal through the SAME loop with
no per-field special-casing; any future numeric cf column heals for free. Columns
sourced via ``cascade:`` (e.g. offer ``mrr`` from an ancestor Unit) are out of
scope -- those re-derive from the healed ancestor, not from the task's own CF.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger
from opentelemetry import trace as _otel_trace

from autom8_asana.cache.models.completeness import CompletenessLevel
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.dataframes.builders.fields import _coerce_value
from autom8_asana.dataframes.views.cf_utils import get_custom_field_value

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

__all__ = [
    "NumericRecoveryReceipt",
    "recover_null_number_cells",
]

logger = get_logger(__name__)

# Polars dtype names that the recovery pass treats as numeric. Mirrors
# TypeCoercer.NUMERIC_DTYPES; kept local so the pass does not depend on the
# coercer's internals beyond the public _coerce_value entrypoint.
_NUMERIC_DTYPES: frozenset[str] = frozenset({"Decimal", "Float64", "Int64", "Int32"})

_CF_PREFIX = "cf:"

# Cold-tier (S3) fan-out concurrency cap. S3 has no true batch GET
# (``S3CacheProvider.get_batch`` loops ``get_versioned`` per key, each a blocking
# ``client.get_object``). A single worker thread reading N keys serially is linear
# in N and unbounded -- on the live unit warm N~3021, ~525s of the 900s Lambda
# budget is already spent, leaving only ~375s of slack, so a sequential cold read
# would risk the timeout-cliff. We instead fan the per-gid reads out across worker
# threads with a Semaphore-bounded in-flight count: latency collapses to roughly
# ceil(N / cap) * per-GET, while the bound caps the boto3 connection-pool pressure
# (default urllib3 pool is 10/host; we cap a little above that and let the pool
# queue the overflow rather than open unbounded sockets). boto3 low-level clients
# are thread-safe for method calls and the S3 backend shares ONE already-built
# client (s3.py:_get_client returns the cached self._client; the only lock is on
# reconnect, not on the GET path), so the fan-out reads the shared client with no
# race and opens no per-call client.
_COLD_CONCURRENCY_DEFAULT = 24
_COLD_CONCURRENCY_MIN = 1
_COLD_CONCURRENCY_MAX = 64
_COLD_CONCURRENCY_ENV = "ASANA_CURE_COLD_CONCURRENCY"


def _cold_concurrency() -> int:
    """Resolve the cold-read fan-out cap, env-overridable and clamped to a sane range.

    Reads ``ASANA_CURE_COLD_CONCURRENCY`` (an int); a missing/blank/garbage value
    falls back to the default. The result is clamped to
    ``[_COLD_CONCURRENCY_MIN, _COLD_CONCURRENCY_MAX]`` so a misconfigured value can
    neither serialize the read (0/negative) nor exhaust the connection pool /
    thread pool with an absurd in-flight count.
    """
    raw = os.environ.get(_COLD_CONCURRENCY_ENV)
    if raw is None or not raw.strip():
        value = _COLD_CONCURRENCY_DEFAULT
    else:
        try:
            value = int(raw.strip())
        except ValueError:
            value = _COLD_CONCURRENCY_DEFAULT
    return max(_COLD_CONCURRENCY_MIN, min(_COLD_CONCURRENCY_MAX, value))


@dataclass(frozen=True)
class NumericRecoveryReceipt:
    """Outcome of the post-build numeric-cell recovery pass.

    Attributes:
        entity_type: Entity type assessed.
        attempted: True if the entity declared at least one numeric ``cf:``
            column AND the frame carried null cells in it (i.e. the pass made a
            cache read). False means a safe no-op (no eligible columns / no null
            cells / no store).
        columns: The numeric ``cf:`` column names considered.
        null_cells_before: Total null cells across the considered columns prior
            to the pass.
        healed_cells: Count of cells backfilled from a non-null cache value.
        residual_null_cells: Null cells remaining after the pass (cache-miss or
            genuinely-null source -- honest-null).
        cache_miss_gids: Number of distinct null-cell gids absent/insufficient in
            BOTH the hot store AND the durable S3 tier (the live-fallback residual
            stratum, which this pass leaves to an explicit, opt-in,
            ASANA-PAT-gated step -- never charged here).
        cold_present_gids: Number of distinct null-cell gids that MISSED the hot
            store but whose durable S3 per-task copy was PRESENT (a task dict came
            back), counted independently of whether that copy's CF was non-null.
            This is the steady-state-warm cure stratum (hot is cold, S3 carries the
            object). NOTE: this counts S3-objects-PRESENT, NOT values-healed -- a
            present copy with a null source contributes here but heals nothing.
            ``healed_cells`` remains the true heal count.
    """

    entity_type: str
    attempted: bool
    columns: tuple[str, ...]
    null_cells_before: int
    healed_cells: int
    residual_null_cells: int
    cache_miss_gids: int
    healed_by_column: dict[str, int] = field(default_factory=dict)
    cold_present_gids: int = 0


def _numeric_cf_columns(schema: DataFrameSchema) -> list[tuple[str, str, str]]:
    """Return ``(column_name, cf_field_name, dtype)`` for numeric ``cf:`` columns.

    A column qualifies when its ``source`` is ``cf:<name>`` and its dtype is in
    ``_NUMERIC_DTYPES``. ``cascade:`` and non-numeric ``cf:`` columns are excluded.
    """
    out: list[tuple[str, str, str]] = []
    for col in schema.columns:
        source = col.source
        if not source or not source.startswith(_CF_PREFIX):
            continue
        if col.dtype not in _NUMERIC_DTYPES:
            continue
        cf_name = source[len(_CF_PREFIX) :].strip()
        if cf_name:
            out.append((col.name, cf_name, col.dtype))
    return out


async def recover_null_number_cells(
    merged_df: pl.DataFrame,
    schema: DataFrameSchema | None,
    store: Any | None,
    entity_type: str,
    project_gid: str,
) -> tuple[pl.DataFrame, NumericRecoveryReceipt]:
    """Backfill null numeric ``cf:`` cells from the warmed cache (cache-reuse only).

    Field-agnostic: heals every numeric ``cf:`` column (``mrr``,
    ``weekly_ad_spend``, ...) through one loop. Makes at most ONE
    ``store.get_batch_async`` call (IMMEDIATE freshness => zero Asana GETs for
    cached gids). Never fabricates; never raises; never changes build status.

    Args:
        merged_df: Final merged DataFrame for the warm.
        schema: Entity schema (selects numeric ``cf:`` columns; None -> no-op).
        store: UnifiedTaskStore exposing ``get_batch_async``; None -> no-op.
        entity_type: Entity type string (log/span context).
        project_gid: Project GID (log/span context).

    Returns:
        ``(healed_df, receipt)``. On any skip/failure, ``healed_df`` is the input
        frame unchanged and ``receipt.attempted`` is False.
    """
    no_op = NumericRecoveryReceipt(
        entity_type=entity_type,
        attempted=False,
        columns=(),
        null_cells_before=0,
        healed_cells=0,
        residual_null_cells=0,
        cache_miss_gids=0,
    )

    if schema is None or store is None or merged_df.is_empty() or "gid" not in merged_df.columns:
        return merged_df, no_op

    try:
        return await _recover_impl(merged_df, schema, store, entity_type, project_gid)
    except Exception as e:  # BROAD-CATCH: recovery is additive  # noqa: BLE001
        logger.warning(
            "null_number_recovery_failed",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return merged_df, no_op


async def _recover_impl(
    merged_df: pl.DataFrame,
    schema: DataFrameSchema,
    store: Any,
    entity_type: str,
    project_gid: str,
) -> tuple[pl.DataFrame, NumericRecoveryReceipt]:
    """Inner recovery body (exceptions handled by the public wrapper)."""
    numeric_cols = _numeric_cf_columns(schema)
    # Only consider columns actually present in the frame.
    present_cols = [
        (name, cf_name, dtype)
        for (name, cf_name, dtype) in numeric_cols
        if name in merged_df.columns
    ]
    if not present_cols:
        return merged_df, NumericRecoveryReceipt(
            entity_type=entity_type,
            attempted=False,
            columns=(),
            null_cells_before=0,
            healed_cells=0,
            residual_null_cells=0,
            cache_miss_gids=0,
        )

    # Collect the union of gids that have a null in ANY considered numeric column.
    # One batch read serves every null cell across every column (a task's single
    # cache copy carries all of its CFs), so the read count is bounded by distinct
    # null-row gids, never by (rows x columns).
    null_any = pl.lit(False)  # noqa: FBT003 -- polars boolean literal seed
    for name, _cf_name, _dtype in present_cols:
        null_any = null_any | pl.col(name).is_null()
    null_rows = merged_df.filter(null_any & pl.col("gid").is_not_null())

    null_cells_before = sum(int(merged_df[name].null_count()) for name, _c, _d in present_cols)

    if null_rows.is_empty():
        return merged_df, NumericRecoveryReceipt(
            entity_type=entity_type,
            attempted=False,
            columns=tuple(name for name, _c, _d in present_cols),
            null_cells_before=null_cells_before,
            healed_cells=0,
            residual_null_cells=null_cells_before,
            cache_miss_gids=0,
        )

    null_gids: list[str] = [g for g in null_rows["gid"].to_list() if g is not None]

    # Tier 1 -- THE single HOT cache read. IMMEDIATE => entry.data for
    # cache-present-and-STANDARD-sufficient gids, ZERO Asana GETs. STANDARD is the
    # level that guarantees custom_fields.number_value is materialized (see
    # completeness.STANDARD_FIELDS) and is the same level the progressive build
    # itself uses. Cache-MISS / sub-STANDARD gids map to None.
    cached: dict[str, dict[str, Any] | None] = await store.get_batch_async(
        null_gids,
        freshness=FreshnessIntent.IMMEDIATE,
        required_level=CompletenessLevel.STANDARD,
    )

    # Tier 2 -- DURABLE S3 fill for the gids that MISSED the hot store. On the
    # steady-state receiver warm (resume=True, 0 re-fetches) the hot store is cold
    # for the unit gids, so this is the stratum that actually heals. ONE batched
    # S3 read of the per-task copies; hot hits always win, S3 fills only the
    # holes. Independent of warm-mode and the global ASANA_CACHE_S3_ENABLED flag
    # (it reads the durable backend directly, not the flag-gated cold tier). Any
    # backend error returns {} -> honest-null residual (never raises here; the
    # outer wrapper also guards).
    hot_miss_gids = [g for g in null_gids if cached.get(g) is None]
    cold_present_gids = 0
    if hot_miss_gids:
        cold = await _cold_read_durable(hot_miss_gids, store)
        for gid, task_data in cold.items():
            if task_data is not None:
                cached[gid] = task_data
                cold_present_gids += 1

    cache_miss_gids = sum(1 for g in null_gids if cached.get(g) is None)

    # Build per-column {gid: healed_value} maps. NEVER fabricate: only when the
    # cached CF carries a non-null number_value (coerced through the SAME merge-
    # path coercer the warm used, so dtype-parity with the existing column holds).
    healed_by_column: dict[str, int] = {}
    replacement_exprs: list[pl.Expr] = []

    for name, cf_name, dtype in present_cols:
        value_by_gid: dict[str, Any] = {}
        for gid in null_gids:
            task_data = cached.get(gid)
            if task_data is None:
                continue
            raw = get_custom_field_value(task_data, cf_name)
            if raw is None:
                continue  # honest-null: cache copy has no value for this CF
            coerced = _coerce_value(raw, dtype)
            if coerced is None:
                continue
            value_by_gid[gid] = coerced

        if not value_by_gid:
            continue

        # Map gid -> healed value across the frame; null where no healed value.
        # Backfill ONLY where the existing cell is null (coalesce semantics):
        # never overwrite an already-populated cell.
        mapped = pl.col("gid").replace_strict(
            old=list(value_by_gid.keys()),
            new=list(value_by_gid.values()),
            default=None,
            return_dtype=merged_df[name].dtype,
        )
        replacement_exprs.append(
            pl.when(pl.col(name).is_null()).then(mapped).otherwise(pl.col(name)).alias(name)
        )
        healed_by_column[name] = len(value_by_gid)

    if not replacement_exprs:
        # Cache carried nothing recoverable -> honest-null residual, no GET spent
        # beyond the single batch (which was free for cached gids).
        return merged_df, _emit(
            entity_type=entity_type,
            project_gid=project_gid,
            columns=tuple(name for name, _c, _d in present_cols),
            null_cells_before=null_cells_before,
            healed_cells=0,
            residual_null_cells=null_cells_before,
            cache_miss_gids=cache_miss_gids,
            healed_by_column={},
            cold_present_gids=cold_present_gids,
        )

    healed_df = merged_df.with_columns(replacement_exprs)

    null_cells_after = sum(int(healed_df[name].null_count()) for name, _c, _d in present_cols)
    healed_cells = null_cells_before - null_cells_after

    return healed_df, _emit(
        entity_type=entity_type,
        project_gid=project_gid,
        columns=tuple(name for name, _c, _d in present_cols),
        null_cells_before=null_cells_before,
        healed_cells=healed_cells,
        residual_null_cells=null_cells_after,
        cache_miss_gids=cache_miss_gids,
        healed_by_column=healed_by_column,
        cold_present_gids=cold_present_gids,
    )


def _unwrap_task_data(data: Any) -> dict[str, Any] | None:
    """Return the task dict from a cached payload, unwrapping a ``{"data": ...}``
    envelope if present.

    The durable per-task copies are stored as ``CacheEntry.data`` (the raw task
    dict); the backend's ``get_versioned``/``get_batch`` already strips the
    storage envelope on deserialize. Some warmer paths persist the API response
    verbatim, which carries a ``{"data": {...}}`` Asana envelope. Unwrap it so the
    downstream ``custom_fields`` lookup sees a top-level task dict either way.
    """
    if not isinstance(data, dict):
        return None
    inner = data.get("data")
    if "custom_fields" not in data and isinstance(inner, dict):
        return inner
    return data


def _resolve_cold_backend(store: Any) -> Any | None:
    """Resolve a durable S3 cache backend for the cold-tier read.

    Resolution order (prefer reusing configured infrastructure):
      1. If ``store.cache`` is a ``TieredCacheProvider`` exposing a cold tier
         (``_cold``), reuse it -- it is the same durable backend the
         write-through path uses (independent of the s3_enabled READ flag).
      2. Otherwise lazily construct an ``S3CacheProvider`` from the canonical
         S3 settings (``get_settings().s3``) -- the SAME bucket/prefix the
         warmer's durable writes use, so the key namespace matches.

    Returns the backend, or ``None`` when no durable tier can be obtained
    (unconfigured bucket, missing boto3, degraded). Never raises.
    """
    # Reuse an already-wired cold tier if the store exposes one.
    cache = getattr(store, "cache", None)
    cold = getattr(cache, "_cold", None)
    if cold is not None:
        return cold

    # Lazily build an S3 backend from the canonical settings.
    try:
        from autom8_asana.cache.backends.s3 import S3CacheProvider
        from autom8_asana.settings import get_settings

        s3 = get_settings().s3
        if not s3.bucket:
            return None
        backend = S3CacheProvider(
            bucket=s3.bucket,
            prefix=s3.prefix,
            region=s3.region,
            endpoint_url=s3.endpoint_url,
        )
    except Exception:  # BROAD-CATCH: backend construction is best-effort  # noqa: BLE001
        return None

    # A backend that could not initialize its client is unusable; skip it so the
    # cure stays a clean no-op rather than spending failing per-key reads.
    if getattr(backend, "_degraded", False):
        return None
    return backend


async def _cold_read_durable(
    gids: list[str], store: Any
) -> dict[str, dict[str, Any] | None]:
    """Bounded-concurrency durable-S3 read of the per-task copies for ``gids``.

    Reads ``EntryType.TASK`` entries (key ``{prefix}/tasks/{gid}/task.json``) via
    the S3 backend and returns ``{gid: task_dict | None}``. S3 has no true batch
    GET -- ``S3CacheProvider.get_batch`` loops ``get_versioned`` per key, each a
    blocking ``client.get_object`` -- so reading N keys with a single worker is
    linear and unbounded in N (timeout-cliff risk on the live unit warm). We
    instead fan the per-gid ``get_versioned`` reads out across worker threads,
    capping the in-flight count with an ``asyncio.Semaphore`` (see
    ``_cold_concurrency``). Each ``get_versioned`` runs in its own
    ``asyncio.to_thread`` so no read blocks the receiver event loop.

    Invariants preserved:
      * **not-N+1 at gid granularity.** EXACTLY one cold ``get_versioned`` per
        distinct hot-miss gid (``len(gids)`` reads total) -- no per-row/per-cell
        amplification. The fan-out parallelizes those reads; it does not multiply
        them.
      * **Zero Asana GETs.** S3 is durable CACHE, not Asana; the receiver's Asana
        GET budget is not charged.
      * **additive / never-raises.** A per-gid read error contributes ``None`` for
        that gid (it heals nothing -> honest-null residual); a total backend
        failure returns ``{}`` and the frame is left UNCHANGED. No exception
        escapes (the outer wrapper also guards).
      * **idempotent re-warm.** A pure read; re-running yields the same map.

    Thread-safety: boto3 low-level clients are thread-safe for method calls and
    the S3 backend shares ONE already-built client (``s3.py`` ``_get_client``
    returns the cached ``self._client``; the only ``Lock`` is on the reconnect
    path, NOT on the GET path), so concurrent ``get_versioned`` calls read the
    shared client with no race and open no per-call client.
    """
    import asyncio

    backend = _resolve_cold_backend(store)
    if backend is None:
        return {}

    cap = _cold_concurrency()
    sem = asyncio.Semaphore(cap)

    async def _one(gid: str) -> tuple[str, dict[str, Any] | None]:
        # One get_versioned per gid, off the event loop, gated by the semaphore so
        # at most ``cap`` boto3 GETs are in flight at once. A per-gid failure is
        # swallowed to None: that gid simply contributes nothing (honest-null).
        async with sem:
            try:
                entry = await asyncio.to_thread(
                    backend.get_versioned, gid, EntryType.TASK
                )
            except Exception as e:  # BROAD-CATCH: per-gid read is additive  # noqa: BLE001
                logger.warning(
                    "null_number_recovery_cold_read_gid_failed",
                    extra={"gid": gid, "error": str(e), "error_type": type(e).__name__},
                )
                return gid, None
        return gid, (_unwrap_task_data(entry.data) if entry is not None else None)

    try:
        pairs = await asyncio.gather(*[_one(g) for g in gids])
    except Exception as e:  # BROAD-CATCH: total cold read is additive  # noqa: BLE001
        logger.warning(
            "null_number_recovery_cold_read_failed",
            extra={"gid_count": len(gids), "error": str(e), "error_type": type(e).__name__},
        )
        return {}

    return dict(pairs)


def _emit(
    *,
    entity_type: str,
    project_gid: str,
    columns: tuple[str, ...],
    null_cells_before: int,
    healed_cells: int,
    residual_null_cells: int,
    cache_miss_gids: int,
    healed_by_column: dict[str, int],
    cold_present_gids: int = 0,
) -> NumericRecoveryReceipt:
    """Emit OTel span attributes + a structured log line and build the receipt."""
    span = _otel_trace.get_current_span()
    span.set_attribute("computation.null_number_recovery.entity_type", entity_type)
    span.set_attribute("computation.null_number_recovery.null_cells_before", null_cells_before)
    span.set_attribute("computation.null_number_recovery.healed_cells", healed_cells)
    span.set_attribute("computation.null_number_recovery.residual_null_cells", residual_null_cells)
    span.set_attribute("computation.null_number_recovery.cache_miss_gids", cache_miss_gids)
    span.set_attribute(
        "computation.null_number_recovery.cold_present_gids", cold_present_gids
    )

    extra = {
        "entity_type": entity_type,
        "project_gid": project_gid,
        "columns": list(columns),
        "null_cells_before": null_cells_before,
        "healed_cells": healed_cells,
        "residual_null_cells": residual_null_cells,
        "cache_miss_gids": cache_miss_gids,
        "cold_present_gids": cold_present_gids,
        "healed_by_column": healed_by_column,
    }

    if healed_cells > 0:
        logger.info("null_number_recovery_healed", extra=extra)
    else:
        # Nothing to heal from cache (all residual is honest-null / cache-miss).
        logger.info("null_number_recovery_no_op", extra=extra)

    return NumericRecoveryReceipt(
        entity_type=entity_type,
        attempted=True,
        columns=columns,
        null_cells_before=null_cells_before,
        healed_cells=healed_cells,
        residual_null_cells=residual_null_cells,
        cache_miss_gids=cache_miss_gids,
        healed_by_column=healed_by_column,
        cold_present_gids=cold_present_gids,
    )
