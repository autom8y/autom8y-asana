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
(``asana-cache/tasks/{gid}/task.json`` carries the populated ``number_value``),
written by the warmer's durable-first path. The hot-store read alone never
consults that tier -- the application store is a bare Redis provider with NO S3
cold tier wired in (the phantom S3 cold tier was retired; see
``StorageNamespaceContract.TASK_CACHE.lifecycle_note``). So the cure adds a SECOND,
durable-tier read via the blessed ``DurableTaskCacheReader``: for the gids that
miss the hot store, a bounded-concurrency RAW S3 GET of the per-task copies. Hot
hits always win; S3 fills only the hot misses.

Why a RAW S3 GET and NOT ``S3CacheProvider`` (the #120 inert-cure correction)
-----------------------------------------------------------------------------
The #120 cure routed the cold read through ``S3CacheProvider.get_versioned``. That
was doubly wrong and healed 0 cells in prod:
  1. **Prefix pollution.** It built the provider with ``prefix=get_settings().s3.prefix``,
     but the ``ASANA_CACHE_S3_PREFIX`` env is OVERLOADED -- prod terraform sets it to
     ``asana-cache/project-frames/`` (the dataframe-storage prefix). The read landed
     on ``asana-cache/project-frames/tasks/{gid}/task.json``, an EMPTY namespace.
  2. **Reader mismatch.** The objects at ``asana-cache/tasks/{gid}/task.json`` are
     RAW Asana task dicts (top-level ``gid``/``custom_fields``/``name``), written by
     the warmer's durable-first path -- NOT ``S3CacheProvider``-serialized envelopes.
     ``S3CacheProvider._deserialize_entry`` expects a storage envelope and reads
     ``data.get("data", {})``; against a raw task dict that yields ``{}`` (empty),
     so even at the RIGHT prefix the provider would surface no custom fields.
This cure therefore reads the objects EXACTLY as the proven live probe does
(``scripts/probe_unit_mrr_provenance.py:read_cache_s3``): a raw ``boto3``
``get_object`` of ``asana-cache/tasks/{gid}/task.json`` (with a ``.gz`` fallback),
``json.loads`` the body, then ``raw.get("data", raw)`` to unwrap an optional Asana
``{"data": {...}}`` envelope before the field lookup. The prefix is a pinned module
constant (decoupled from the polluted setting); only the bucket comes from settings.

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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger
from opentelemetry import trace as _otel_trace

from autom8_asana.cache.durable_task_cache import (
    # The clamp bounds are re-exported (aliased to the cure's historical private
    # names) for back-compat with the cure's existing tests, which read
    # ``nnr._COLD_CONCURRENCY_MIN/MAX/DEFAULT`` to assert the clamp behavior.
    COLD_CONCURRENCY_DEFAULT as _COLD_CONCURRENCY_DEFAULT,  # noqa: F401 -- test-surface re-export
)
from autom8_asana.cache.durable_task_cache import (
    COLD_CONCURRENCY_MAX as _COLD_CONCURRENCY_MAX,  # noqa: F401 -- test-surface re-export
)
from autom8_asana.cache.durable_task_cache import (
    COLD_CONCURRENCY_MIN as _COLD_CONCURRENCY_MIN,  # noqa: F401 -- test-surface re-export
)
from autom8_asana.cache.durable_task_cache import (
    get_durable_task_cache_reader,
    task_cache_key,
    unwrap_task_data,
)
from autom8_asana.cache.models.completeness import CompletenessLevel
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.dataframes.builders.fields import _coerce_value
from autom8_asana.dataframes.views.cf_utils import get_custom_field_value
from autom8_asana.storage_namespace import TASK_CACHE

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

__all__ = [
    "NumericRecoveryReceipt",
    "recover_null_number_cells",
]

logger = get_logger(__name__)

# Canonical task-cache key namespace, DERIVED from the storage namespace registry
# (``StorageNamespaceContract.TASK_CACHE.prefix``) — the single canonical write
# point for every autom8-s3 prefix. This subsumes the previously hand-pinned
# ``"asana-cache"`` literal: the registry is now the SSOT, so the prefix lives in
# exactly ONE place (``src/autom8_asana/storage_namespace.py``) and a wrong-prefix
# read is structurally unaddressable (``tests/arch/test_namespace_contract.py`` t3
# forbids the literal anywhere else in ``src/``).
#
# WHY THE PREFIX IS NOT ``get_settings().s3.prefix``: the ``ASANA_CACHE_S3_PREFIX``
# env var is OVERLOADED in production — prod terraform sets it to
# ``asana-cache/project-frames/`` (the DATAFRAME-STORAGE prefix), so the #120 cure
# read ``{s3.prefix}/tasks/{gid}/task.json`` => an EMPTY namespace. The per-task
# copies live under the UNADORNED ``asana-cache`` prefix regardless of the env
# override; the registry records that as ``TASK_CACHE.prefix``. Only the PREFIX env
# is overloaded; the BUCKET env (``ASANA_CACHE_S3_BUCKET``) is NOT, so the bucket is
# still resolved from ``get_settings().s3.bucket`` inside the reader.
_DURABLE_TASK_CACHE_PREFIX = TASK_CACHE.prefix

# Polars dtype names that the recovery pass treats as numeric. Mirrors
# TypeCoercer.NUMERIC_DTYPES; kept local so the pass does not depend on the
# coercer's internals beyond the public _coerce_value entrypoint.
_NUMERIC_DTYPES: frozenset[str] = frozenset({"Decimal", "Float64", "Int64", "Int32"})

_CF_PREFIX = "cf:"

# Cold-tier (S3) fan-out concurrency cap. The cap + clamp now live with the blessed
# ``DurableTaskCacheReader`` (the bounded-concurrency RAW-S3 read is the reader's
# responsibility); these names are re-exported here for back-compat (the env name
# ``ASANA_CURE_COLD_CONCURRENCY`` is unchanged) so existing patch-targets and the
# concurrency contract are stable. The MIN/MAX/DEFAULT are imported above.
_COLD_CONCURRENCY_ENV = "ASANA_CURE_COLD_CONCURRENCY"


def _cold_concurrency() -> int:
    """Resolve the cold-read fan-out cap (delegates to the reader's clamp).

    Reads ``ASANA_CURE_COLD_CONCURRENCY`` (an int); a missing/blank/garbage value
    falls back to the default. Clamped to ``[_COLD_CONCURRENCY_MIN,
    _COLD_CONCURRENCY_MAX]`` so a misconfigured value can neither serialize the read
    (0/negative) nor exhaust the connection / thread pool.
    """
    from autom8_asana.cache import durable_task_cache as _dtc

    return _dtc._cold_concurrency()


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
    null_any = pl.lit(False)  # polars boolean literal seed
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
    # S3 read of the per-task copies (via the blessed DurableTaskCacheReader); hot
    # hits always win, S3 fills only the holes. The reader reads the durable backend
    # directly (NOT a flag-gated cold tier — the phantom was retired). Any backend
    # error returns {} -> honest-null residual (never raises here; the outer wrapper
    # also guards).
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


# ---------------------------------------------------------------------------
# Cold-tier durable-read shims.
#
# The raw-boto3 read LOGIC is owned by the blessed ``DurableTaskCacheReader``
# (``autom8_asana.cache.durable_task_cache``) — subsumed, not duplicated. The
# functions below are thin delegators that preserve this module's read-path API
# surface (the cure's tests + the live smoke patch ``nnr._get_s3_client`` /
# ``nnr._read_task_cache_object`` and read ``nnr._S3_CLIENT``). The single
# ``asyncio.to_thread`` offload site now lives in the reader, so the FROZEN-4
# concurrency guard's ``_SANCTIONED_IO_TO_THREAD`` allowlist names the reader
# module, not this one.
#
# The module-cached client globals are retained so the existing reset idiom
# (``nnr._S3_CLIENT = None; nnr._S3_CLIENT_BUILD_ATTEMPTED = False``) keeps working
# AND stays coupled to the shared reader singleton's client (resetting the cure's
# globals also resets the reader, so a fresh REAL client is built on next read).
# ---------------------------------------------------------------------------

_S3_CLIENT: Any = None
_S3_CLIENT_BUILD_ATTEMPTED = False


# Re-exported for back-compat: tests/live-smoke call these by name on this module.
_unwrap_task_data = unwrap_task_data


def _cold_task_cache_key(gid: str) -> str:
    """The canonical durable per-task cache key for ``gid`` (registry-derived).

    Delegates to ``DurableTaskCacheReader``'s ``task_cache_key`` so the prefix
    derives from ``TASK_CACHE.prefix`` (the SSOT) — NOT the env-overloaded
    ``get_settings().s3.prefix`` (see ``_DURABLE_TASK_CACHE_PREFIX``).
    """
    return task_cache_key(gid)


def _get_s3_client() -> Any | None:
    """Return the durable-reader's module-cached boto3 S3 client (built lazily once).

    Delegates to the shared ``DurableTaskCacheReader`` singleton so ONE client
    serves every durable read process-wide. The cure's ``_S3_CLIENT`` /
    ``_S3_CLIENT_BUILD_ATTEMPTED`` globals are mirrored from the reader so the
    legacy reset idiom (set both to None/False) still forces a rebuild: when the
    cure's globals are reset to the not-built sentinel, the reader is reset too.

    Never raises: a build failure memoizes ``None`` inside the reader.
    """
    global _S3_CLIENT, _S3_CLIENT_BUILD_ATTEMPTED
    reader = get_durable_task_cache_reader()
    # Honor the legacy reset idiom: if a caller cleared the cure's globals to the
    # not-yet-built sentinel, propagate that reset to the shared reader so the next
    # read rebuilds a fresh client (the live smoke + unit-test fixtures rely on this).
    if not _S3_CLIENT_BUILD_ATTEMPTED and _S3_CLIENT is None:
        reader.reset_client()
    client = reader.get_client()
    _S3_CLIENT = client
    _S3_CLIENT_BUILD_ATTEMPTED = True
    return client


def _read_task_cache_object(client: Any, bucket: str, gid: str) -> dict[str, Any] | None:
    """Raw S3 GET of one per-task copy (delegates to the reader's ``read_object``).

    Preserves the cure's read-path API surface (the live smoke + unit tests call
    ``nnr._read_task_cache_object``). The REAL key construction (registry-derived),
    REAL ``json.loads``, ``.gz`` fallback, and ``{"data": ...}`` unwrap all live in
    ``DurableTaskCacheReader.read_object`` — subsumed, not duplicated. The #120
    defect (``S3CacheProvider`` envelope deserialization + polluted prefix) is gone.
    """
    return get_durable_task_cache_reader().read_object(client, bucket, gid)


async def _cold_read_durable(gids: list[str], store: Any) -> dict[str, dict[str, Any] | None]:
    """Bounded-concurrency RAW-S3 read of the durable per-task copies for ``gids``.

    Delegates the bounded fan-out to ``DurableTaskCacheReader.read_batch_with``
    (the SOLE ``asyncio.to_thread`` offload site), injecting THIS module's
    ``_read_task_cache_object`` as the per-gid reader so a test that patches
    ``nnr._read_task_cache_object`` still takes effect, and resolving the client via
    THIS module's ``_get_s3_client`` so a test that patches ``nnr._get_s3_client``
    still takes effect. The read LOGIC is subsumed in the reader; only the
    client/bucket/read-fn wiring lives here.

    The ``store`` argument is retained for signature stability (the durable copies
    are a parallel write path, not a read tier of the Redis-only application store).

    Invariants preserved (enforced in the reader): not-N+1 at gid granularity, zero
    Asana GETs, never-fabricate, additive/never-raises, idempotent re-warm.
    """
    client = _get_s3_client()
    if client is None:
        return {}

    try:
        from autom8_asana.settings import get_settings

        bucket = get_settings().s3.bucket
    except Exception:  # BROAD-CATCH: settings read is best-effort  # noqa: BLE001
        bucket = ""
    if not bucket:
        return {}

    reader = get_durable_task_cache_reader()
    return await reader.read_batch_with(client, bucket, gids, _read_task_cache_object)


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
    span.set_attribute("computation.null_number_recovery.cold_present_gids", cold_present_gids)

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
