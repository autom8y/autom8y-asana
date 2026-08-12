"""FIX-N-C1 — the preload stamp describes the substrate, not the boot clock.

Micro-packet (FIX-1 form). Crusade ``offers-false-staleness-cure``, wave 2,
Lane C1. Pythia RULED C1 admissible as FIX-N at round 3 under a **binding
default-preserving condition** (card D-5 / COND-6).

The defect: the startup preload's S3 parquet fast path loads a frame together
with the ``s3_watermark`` that describes it, then re-puts it through
``DataFrameCache.put_async``, which stamped ``created_at=datetime.now(UTC)``
unconditionally. Boot wall-clock replaced substrate recency. A worker booting
against a 3-hour-old parquet reported age 0 and then drifted "stale" on its own
uptime -- the task-startup-anchored staleness class (DIAG-S1 F3.1: a 10083.3s
reading whose anchor was a task-startup preload put, i.e. 168 minutes of worker
uptime wearing the badge of data age).

Two-sided, per the design's mandated test shape:

* **RED** -- a preloaded entry's age anchors at the S3 watermark, not at boot.
* **GREEN** -- every OTHER ``put_async`` caller is byte-identical: the parameter
  is keyword-only with ``None`` default, ``None`` still stamps ``now()``, and a
  source census proves exactly one call site opts in.
* **FRESH-TASK** -- a fresh worker's preloaded entry reports substrate-derived
  age, and two independently booted workers over the same object agree.

BINDING CONDITION (D-5): if the parameter were ever made required, or its
default changed, C1 leaves the FIX-N class and returns for re-adjudication.
``test_signature_is_default_preserving`` is the tripwire for that.
"""

from __future__ import annotations

import ast
import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCache,
    _get_schema_version_for_entity,
)
from autom8_asana.cache.models.freshness_unified import FreshnessState
from tests.unit.api.test_preload_parquet_fallback import (
    _build_patch_stack,
    _make_mock_app_and_registry,
)

ENTITY_TYPE = "offer"
PROJECT_GID = "proj_offer"
SUBSTRATE_AGE = timedelta(hours=3)

SRC_ROOT = Path(__file__).resolve().parents[4] / "src" / "autom8_asana"
# The single sanctioned opt-in site. Any other call site passing ``created_at``
# is a new claim that some other bytes carry their own recency -- which must be
# argued, not assumed.
SANCTIONED_CREATED_AT_CALLER = "api/preload/progressive.py"

# Mirrors the env the preload harness installs; the real cache must be built
# under it (see run_preload) so settings memoize with the workspace present.
PRELOAD_ENV = {
    "ASANA_WORKSPACE_GID": "workspace-123",
    "ASANA_BOT_PAT": "test-pat",
    "ASANA_CACHE_S3_BUCKET": "test-bucket",
    "ASANA_CACHE_S3_REGION": "us-east-1",
}


def make_real_cache() -> DataFrameCache:
    """A real DataFrameCache whose durable tier is stubbed as a successful write.

    Real cache, real entry construction, real freshness classifier -- only the
    S3 round-trip is stubbed, so the assertions land on production logic.
    """
    progressive_tier = MagicMock()
    progressive_tier.put_async = AsyncMock(return_value=True)
    progressive_tier.get_async = AsyncMock(return_value=None)
    return DataFrameCache(
        memory_tier=MemoryTier(max_entries=100),
        progressive_tier=progressive_tier,
        coalescer=DataFrameCacheCoalescer(),
        circuit_breaker=CircuitBreaker(),
        schema_version=_get_schema_version_for_entity(ENTITY_TYPE) or "1.0.0",
    )


def make_preload_mocks(s3_watermark: datetime) -> tuple[MagicMock, MagicMock]:
    """Persistence + storage mocks that route the preload down the parquet fast path.

    ``get_manifest_async -> None`` is what selects the fast path in production
    (the Lambda deletes the manifest after a successful warm).
    """
    persistence = MagicMock()
    persistence.is_available = True
    persistence.get_manifest_async = AsyncMock(return_value=None)
    persistence.__aenter__ = AsyncMock(return_value=persistence)
    persistence.__aexit__ = AsyncMock(return_value=None)

    df_storage = MagicMock()
    df_storage.load_dataframe = AsyncMock(
        return_value=(pl.DataFrame({"gid": [str(i) for i in range(10)]}), s3_watermark)
    )
    return persistence, df_storage


async def run_preload(s3_watermark: datetime) -> DataFrameCache:
    """Drive the REAL startup preload down its S3 parquet fast path.

    Returns the real cache the preload wrote into. The cache is constructed
    INSIDE the env patch on purpose: building it touches the entity registry and
    therefore memoizes settings, and a cache built under ambient env would leave
    the preload's own ``get_workspace_gid()`` reading a stale settings object.
    """
    from autom8_asana.api.preload.progressive import (
        _preload_dataframe_cache_progressive,
    )

    with patch.dict("os.environ", PRELOAD_ENV):
        cache = make_real_cache()
        app, _registry = _make_mock_app_and_registry()
        persistence, df_storage = make_preload_mocks(s3_watermark)

        with _build_patch_stack(
            persistence,
            df_storage,
            mock_dataframe_cache=cache,
            mock_watermark_repo=MagicMock(),
        ):
            await _preload_dataframe_cache_progressive(app)

    return cache


class TestPreloadStampAnchorsOnSubstrateRed:
    """RED leg — the preloaded entry must date from the parquet, not from boot."""

    async def test_preloaded_entry_age_anchors_at_the_s3_watermark(self) -> None:
        """A worker booting against a 3h-old parquet reports ~3h, not 0s."""
        s3_watermark = datetime.now(UTC) - SUBSTRATE_AGE
        cache = await run_preload(s3_watermark)

        entry = cache.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        assert entry is not None
        # Pre-fix: created_at was boot wall-clock, i.e. ~now.
        assert entry.created_at == s3_watermark
        age = (datetime.now(UTC) - entry.created_at).total_seconds()
        assert age > SUBSTRATE_AGE.total_seconds() - 60

    async def test_substrate_anchored_entry_classifies_stale_not_fresh(self) -> None:
        """A put carrying a 3h-old substrate anchor classifies STALE, not FRESH.

        Exercised at the ``put_async`` seam rather than through ``run_preload``:
        the preload harness patches ``SchemaRegistry``, so every entry it builds
        classifies ``SCHEMA_INVALID`` and a freshness assertion there would pass
        for the wrong reason. Here the registry is real, so the classifier's
        verdict is load-bearing.
        """
        cache = make_real_cache()
        watermark = datetime.now(UTC) - SUBSTRATE_AGE

        await cache.put_async(
            PROJECT_GID,
            ENTITY_TYPE,
            pl.DataFrame({"gid": ["1"]}),
            watermark,
            created_at=watermark,
        )

        entry = cache.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        assert entry is not None
        # Pre-fix this was FRESH at age ~0 -- the false-fresh half of the
        # bidirectional defect (the false-stale half is the later drift).
        # offer TTL 180s, grace 540s; 3h is far beyond both.
        assert cache._check_freshness(entry, None) is FreshnessState.STALE

    async def test_watermark_and_stamp_are_co_sourced(self) -> None:
        """The stamp describes the same object being put (CONTRACT §1.4)."""
        s3_watermark = datetime.now(UTC) - SUBSTRATE_AGE
        cache = await run_preload(s3_watermark)

        entry = cache.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        assert entry is not None
        assert entry.watermark == s3_watermark
        assert entry.created_at == entry.watermark
        assert entry.row_count == 10


class TestDefaultPreservationGreen:
    """GREEN leg — the D-5 binding condition: every other caller is untouched."""

    def test_signature_is_default_preserving(self) -> None:
        """COND-6 tripwire: keyword-only, ``datetime | None``, default ``None``.

        If this fails, the parameter was made required or its default changed
        -- which takes C1 out of the FIX-N class per card D-5. It is a
        re-adjudication signal, not a test to relax.
        """
        params = inspect.signature(DataFrameCache.put_async).parameters

        created_at = params["created_at"]
        assert created_at.kind is inspect.Parameter.KEYWORD_ONLY
        assert created_at.default is None
        assert created_at.annotation == "datetime | None"

        # The positional surface is unchanged, so every historical positional
        # call site still binds exactly as before.
        positional = [
            name
            for name, p in params.items()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        assert positional == [
            "self",
            "project_gid",
            "entity_type",
            "dataframe",
            "watermark",
            "build_result",
        ]

    async def test_default_path_still_stamps_now(self) -> None:
        """Omitting ``created_at`` stamps wall-clock exactly as before."""
        cache = make_real_cache()
        watermark = datetime.now(UTC) - SUBSTRATE_AGE

        before = datetime.now(UTC)
        durable = await cache.put_async(
            PROJECT_GID,
            ENTITY_TYPE,
            pl.DataFrame({"gid": ["1"]}),
            watermark,
        )
        after = datetime.now(UTC)

        assert durable is True
        entry = cache.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        assert entry is not None
        # Byte-identical to the pre-fix behavior: now(), NOT the watermark.
        assert before <= entry.created_at <= after
        assert entry.created_at != watermark
        assert entry.watermark == watermark

    async def test_explicit_none_is_identical_to_omission(self) -> None:
        """Passing ``created_at=None`` explicitly takes the same branch."""
        cache = make_real_cache()
        watermark = datetime.now(UTC) - SUBSTRATE_AGE

        before = datetime.now(UTC)
        await cache.put_async(
            PROJECT_GID,
            ENTITY_TYPE,
            pl.DataFrame({"gid": ["1"]}),
            watermark,
            created_at=None,
        )
        after = datetime.now(UTC)

        entry = cache.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        assert entry is not None
        assert before <= entry.created_at <= after

    def test_only_the_preload_fast_path_opts_in(self) -> None:
        """Source census: exactly one ``put_async`` call site passes ``created_at``.

        This is the mechanical form of "every OTHER caller (warmer / SWR /
        decorator / admin / legacy preload) is byte-identical" -- it holds by
        construction rather than by inspection, and it fails loudly the moment a
        second site starts claiming its bytes carry their own recency.
        """
        opt_in_sites: list[str] = []
        total_call_sites = 0

        for path in SRC_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute) or func.attr != "put_async":
                    continue
                # Only DataFrameCache receivers -- unified_store.put_async and
                # the tier's own put_async(key, entry) are different surfaces.
                receiver = ast.unparse(func.value)
                if not receiver.endswith("cache"):
                    continue
                total_call_sites += 1
                if any(kw.arg == "created_at" for kw in node.keywords):
                    opt_in_sites.append(str(path.relative_to(SRC_ROOT)))

        # Sanity: the census actually found the caller population it claims to
        # be constraining (a zero-match census would pass vacuously).
        assert total_call_sites >= 5, f"census found only {total_call_sites} call sites"
        assert opt_in_sites == [SANCTIONED_CREATED_AT_CALLER]


class TestFreshTaskAgreement:
    """FRESH-TASK leg — the whole point: new and old workers must agree."""

    async def test_two_workers_booting_on_the_same_parquet_agree(self) -> None:
        """Independently booted workers derive the same age from the same object.

        Pre-fix each worker anchors on ITS OWN boot instant, so the reported
        staleness is a function of which worker answered -- the accident that
        makes "the tick passed" unreadable as evidence (DIAG-S1 F1.8b / F3.1).
        """
        s3_watermark = datetime.now(UTC) - SUBSTRATE_AGE

        worker_a = await run_preload(s3_watermark)
        worker_b = await run_preload(s3_watermark)

        entry_a = worker_a.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        entry_b = worker_b.memory_tier.get(f"{ENTITY_TYPE}:{PROJECT_GID}")
        assert entry_a is not None
        assert entry_b is not None
        assert entry_a.created_at == entry_b.created_at == s3_watermark
