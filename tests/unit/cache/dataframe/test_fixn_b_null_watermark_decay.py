"""FIX-N-B — a null storage watermark DECAYS; it is never synthesized fresh.

Micro-packet for the synthetic-fresh generator named verbatim in the frozen
offers-freshness CONTRACT §1.3 (``tiers/progressive.py:187-189`` / ``:202-209``
at the pre-fix basis).

The trap: ``ProgressiveTier.get_async`` substituted ``datetime.now(UTC)`` when
storage metadata carried no watermark, then used that substitute as the entry's
``created_at`` -- so a frame of *arbitrary true age* hydrates at age 0 and reads
FRESH. CONTRACT §1.3: "Null -> DECAY. A null content axis means *unprovable*,
and unprovable is **stale**, never fresh."

**Latent, not firing — stated up front so no test here is read as a live-defect
receipt.** The ``DataFrameStorage`` Protocol types the watermark as
``datetime | None`` (``dataframes/storage.py:114-138``), so ``(df, None, meta)``
is admissible at the seam; the sole concrete implementation cannot currently
produce it (``_load_at_keys`` GETs the watermark sidecar first and returns the
whole tuple as ``None`` on a miss, ``storage.py:1043-1052``). Measured
production frequency of the trap tuple is ZERO. These tests therefore feed the
guard a **deliberately-broken input the current storage cannot emit** — a
legitimate discriminating fixture for a latent-class guard, not an injected
defect in working code — and assert the guard rejects it for ANY storage
implementation rather than by accident of one implementation's read ordering.

Two-sided, per the design's mandated test shape:

* **RED**  -- a null-watermark S3 entry whose true age is past the ceiling is
  decayed and reads STALE (pre-fix: FRESH at age 0).
* **GREEN** -- an entry with a real watermark inside SLA still serves FRESH,
  byte-identical to pre-fix behavior.
* **FRESH-TASK** -- a newly started worker hydrating the same null-watermark
  object reports the *same* decayed verdict as a long-lived one: the verdict is
  a pure function of the stored object, not of read time or process age.

Plus the design §3.4 Lane-B co-sourcing note: decaying the S3 entry must not
leave a synthetic-fresh copy alive in the memory tier for the same key.

The serve decision is deliberately NOT changed: a populated/healthy cache-only
frame (offer) is still served as LKG under the availability-first contract. The
defect was the freshness SIGNAL, not the serve.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, get_args, get_type_hints
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import polars as pl

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.dataframe.tiers.progressive import (
    NULL_WATERMARK_DECAY_ANCHOR,
    ProgressiveTier,
)
from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCache,
    _get_schema_version_for_entity,
)
from autom8_asana.cache.models.freshness_unified import FreshnessState
from autom8_asana.config import FRESHNESS_CONTRACT_MAX_AGE_SECONDS
from autom8_asana.dataframes.storage import DataFrameStorage

# The offer entity is the crusade's subject: cache-only (warmed out-of-band),
# TTL 180s, availability ceiling 16200s (config.py FRESHNESS_CONTRACT_MAX_AGE_SECONDS).
ENTITY_TYPE = "offer"
PROJECT_GID = "proj-fixn-b"
CACHE_KEY = f"{ENTITY_TYPE}:{PROJECT_GID}"
OFFER_CEILING_SECONDS = FRESHNESS_CONTRACT_MAX_AGE_SECONDS[ENTITY_TYPE]


def make_frame() -> pl.DataFrame:
    """A populated, healthy frame (row_count > 0 -> LKG-rescuable)."""
    return pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})


class ProtocolStubStorage:
    """A hand-written ``DataFrameStorage`` substitute for the tier's read surface.

    NOT a mock: this is a **Protocol-substitution** fixture. It implements the
    two read members the tier duck-type dispatches on (``hasattr(storage,
    "load_dataframe_with_metadata")``, ``progressive.py:151`` at the pre-fix
    basis) with exactly the return types the Protocol declares
    (``storage.py:1080`` / ``:1103``).

    ``watermark=None`` builds the ``(df, None, meta)`` tuple that the Protocol
    LEGALIZES but ``S3DataFrameStorage`` cannot currently emit: its
    ``_load_dataframe_impl`` holds ``watermark is None <=> df is None`` across
    all four return sites (``storage.py:996``, ``:1008``, ``:1024``, ``:1030``),
    because ``_load_at_keys`` GETs the watermark sidecar first and returns the
    whole tuple as ``None`` on a miss (``storage.py:1043-1052``).

    So this fixture is a deliberately-broken INPUT that a conformant-but-
    different implementation may legally hand the tier -- not an injected defect
    in working production code. The guard under test is what makes the invariant
    hold for ANY implementation rather than by accident of this one's ordering.
    """

    is_available = True

    def __init__(self, watermark: datetime | None) -> None:
        self._watermark = watermark

    async def load_dataframe(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> tuple[pl.DataFrame | None, datetime | None]:
        return make_frame(), self._watermark

    async def load_dataframe_with_metadata(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> tuple[pl.DataFrame | None, datetime | None, dict[str, Any] | None]:
        return (
            make_frame(),
            self._watermark,
            {"schema_version": _get_schema_version_for_entity(ENTITY_TYPE)},
        )


def make_storage(watermark: datetime | None) -> ProtocolStubStorage:
    """Protocol-conformant storage substitute with the given watermark."""
    return ProtocolStubStorage(watermark)


def make_tier(storage: ProtocolStubStorage) -> ProgressiveTier:
    """Real ProgressiveTier over a mocked storage (no S3, no network)."""
    persistence = MagicMock()
    persistence._prefix = "dataframes/"
    type(persistence).storage = PropertyMock(return_value=storage)
    persistence.write_final_artifacts_async = AsyncMock(return_value=True)
    return ProgressiveTier(persistence=persistence)


def make_cache(tier: ProgressiveTier) -> DataFrameCache:
    """A cache whose cold tier is the real ProgressiveTier under test."""
    return DataFrameCache(
        memory_tier=MemoryTier(max_entries=100),
        progressive_tier=tier,
        coalescer=DataFrameCacheCoalescer(),
        circuit_breaker=CircuitBreaker(),
        schema_version=_get_schema_version_for_entity(ENTITY_TYPE) or "1.0.0",
    )


class TestProtocolSubstitution:
    """The load-bearing pair — the guard's real subject is Protocol-conformance.

    Ground G2 (the narrowed, surviving ground for this packet): the trap is
    LEGAL by signature and disarmed only by one implementation's internals. The
    invariant this guard actually adds is *"any conformant DataFrameStorage,
    not just today's, cannot make the tier emit a synthetic-fresh entry."*
    """

    def test_protocol_legalizes_the_null_watermark_tuple(self) -> None:
        """Mechanical receipt for G2 (ii): the declared return type admits (df, None).

        If this ever fails -- because the Protocol narrows the watermark to a
        non-optional ``datetime`` -- the trap stops being type-legal and the
        guard's ground changes. That is a signal, not a nuisance.
        """
        for member in (
            DataFrameStorage.load_dataframe,
            DataFrameStorage.load_dataframe_with_metadata,
        ):
            positions = get_args(get_type_hints(member)["return"])
            watermark_position = positions[1]
            assert type(None) in get_args(watermark_position), (
                f"{member.__name__} no longer legalizes a null watermark"
            )

    async def test_protocol_conformant_null_watermark_is_decayed(self) -> None:
        """RED — a conformant stub returning (df, None) must NOT yield a fresh entry."""
        tier = make_tier(ProtocolStubStorage(watermark=None))
        cache = make_cache(tier)

        entry = await tier.get_async(CACHE_KEY)

        assert entry is not None
        assert entry.created_at == NULL_WATERMARK_DECAY_ANCHOR
        assert cache._check_freshness(entry, None) is not FreshnessState.FRESH
        assert cache._check_freshness(entry, None) is FreshnessState.STALE

    async def test_protocol_conformant_real_watermark_is_a_normal_entry(self) -> None:
        """GREEN — the paired (df, watermark) variant produces an ordinary fresh entry.

        Not vacuous: this asserts the *substrate-derived* stamp, so a guard that
        decayed everything (or that anchored on read time) fails here.
        """
        watermark = datetime.now(UTC) - timedelta(seconds=30)
        tier = make_tier(ProtocolStubStorage(watermark=watermark))
        cache = make_cache(tier)

        entry = await tier.get_async(CACHE_KEY)

        assert entry is not None
        assert entry.created_at == watermark
        assert entry.watermark == watermark
        assert entry.created_at != NULL_WATERMARK_DECAY_ANCHOR
        assert entry.row_count == 2
        assert cache._check_freshness(entry, None) is FreshnessState.FRESH


class TestNullWatermarkDecaysRed:
    """RED leg — a null storage watermark must decay, never read fresh."""

    async def test_null_watermark_entry_is_anchored_at_the_decay_floor(self) -> None:
        """A null storage watermark yields the decay anchor, not now()."""
        tier = make_tier(make_storage(watermark=None))

        entry = await tier.get_async(CACHE_KEY)

        assert entry is not None
        assert entry.created_at == NULL_WATERMARK_DECAY_ANCHOR
        assert entry.watermark == NULL_WATERMARK_DECAY_ANCHOR
        # Pre-fix this entry was stamped at read wall-clock, i.e. ~0s old.
        age = (datetime.now(UTC) - entry.created_at).total_seconds()
        assert age > OFFER_CEILING_SECONDS

    async def test_null_watermark_entry_classifies_stale_not_fresh(self) -> None:
        """The freshness classifier reads the decayed entry as STALE (LKG)."""
        tier = make_tier(make_storage(watermark=None))
        cache = make_cache(tier)

        entry = await tier.get_async(CACHE_KEY)
        assert entry is not None

        # Pre-fix: FRESH (age 0). Post-fix: STALE -- the same state
        # ``_check_freshness`` assigns any past-ceiling entry.
        assert cache._check_freshness(entry, None) is FreshnessState.STALE

    async def test_null_watermark_entry_is_still_served_as_lkg(self) -> None:
        """Availability is preserved: the decayed frame still serves (LKG).

        The defect is the freshness SIGNAL, not the serve. A populated/healthy
        cache-only frame over the ceiling is served as LKG with honest
        staleness telemetry -- unchanged by this packet.
        """
        tier = make_tier(make_storage(watermark=None))
        cache = make_cache(tier)

        with patch("autom8_asana.cache.integration.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async(PROJECT_GID, ENTITY_TYPE)

        assert result is not None
        assert result.row_count == 2

        info = cache.get_freshness_info(PROJECT_GID, ENTITY_TYPE)
        assert info is not None
        assert info.freshness == FreshnessState.STALE.value
        assert info.data_age_seconds > OFFER_CEILING_SECONDS
        assert cache.get_stats()[ENTITY_TYPE]["lkg_serves"] == 1


class TestRealWatermarkUnchangedGreen:
    """GREEN leg — an entry with a real watermark inside SLA is untouched."""

    async def test_real_watermark_within_sla_serves_fresh(self) -> None:
        """A 10s-old real watermark still reads FRESH (offer TTL 180s)."""
        watermark = datetime.now(UTC) - timedelta(seconds=10)
        tier = make_tier(make_storage(watermark=watermark))
        cache = make_cache(tier)

        result = await cache.get_async(PROJECT_GID, ENTITY_TYPE)

        assert result is not None
        assert result.created_at == watermark
        assert result.watermark == watermark

        info = cache.get_freshness_info(PROJECT_GID, ENTITY_TYPE)
        assert info is not None
        assert info.freshness == FreshnessState.FRESH.value
        assert info.data_age_seconds < 60
        assert cache.get_stats()[ENTITY_TYPE]["s3_hits"] == 1

    async def test_real_watermark_past_ceiling_keeps_its_own_age(self) -> None:
        """A genuinely old real watermark decays on its OWN value, not the anchor.

        Guards against the fix over-reaching: only the *underivable* case is
        anchored; a derivable watermark continues to date itself.
        """
        watermark = datetime.now(UTC) - timedelta(seconds=OFFER_CEILING_SECONDS + 600)
        tier = make_tier(make_storage(watermark=watermark))
        cache = make_cache(tier)

        entry = await tier.get_async(CACHE_KEY)
        assert entry is not None
        assert entry.created_at == watermark
        assert entry.created_at != NULL_WATERMARK_DECAY_ANCHOR
        assert cache._check_freshness(entry, None) is FreshnessState.STALE


class TestFreshTaskAgreement:
    """FRESH-TASK leg — the verdict is substrate-derived, not worker-derived."""

    async def test_new_worker_and_long_lived_worker_agree(self) -> None:
        """Two independent processes reading the same object report one verdict.

        Pre-fix these disagree: the long-lived worker's hydrated copy ages on
        wall-clock from ITS read instant while a newly started worker re-reads
        the same object at age 0 / FRESH. Post-fix both derive the same anchor
        from the same bytes.

        The fresh-task case is the acceptance discriminator named at CONTRACT
        §1.6 / DIAG-S1 F3.1. This leg proves it for the latent null-watermark
        class only; the firing instance of worker-anchored age is FIX-N-C1.
        """
        storage = make_storage(watermark=None)

        # Long-lived worker: hydrated earlier in its own process.
        long_lived_cache = make_cache(make_tier(storage))
        with patch("autom8_asana.cache.integration.dataframe_cache.asyncio.create_task"):
            long_lived = await long_lived_cache.get_async(PROJECT_GID, ENTITY_TYPE)

        # Newly started worker: fresh process, fresh tier, same S3 object.
        fresh_cache = make_cache(make_tier(storage))
        with patch("autom8_asana.cache.integration.dataframe_cache.asyncio.create_task"):
            fresh = await fresh_cache.get_async(PROJECT_GID, ENTITY_TYPE)

        assert long_lived is not None
        assert fresh is not None
        assert long_lived.created_at == fresh.created_at == NULL_WATERMARK_DECAY_ANCHOR

        long_lived_info = long_lived_cache.get_freshness_info(PROJECT_GID, ENTITY_TYPE)
        fresh_info = fresh_cache.get_freshness_info(PROJECT_GID, ENTITY_TYPE)
        assert long_lived_info is not None
        assert fresh_info is not None
        assert long_lived_info.freshness == fresh_info.freshness == FreshnessState.STALE.value


class TestMemoryTierCoSourcing:
    """Design §3.4 Lane-B — no synthetic-fresh second answer for the same key."""

    async def test_memory_hydration_carries_the_decayed_verdict(self) -> None:
        """The memory tier is hydrated with the SAME decayed entry object.

        The Lane-B co-sourcing hazard is "decaying an S3 entry while the memory
        tier still holds the synthetic-fresh copy would leave two answers alive
        for the same key". It cannot arise here: ``get_async`` promotes the very
        entry the progressive tier produced, so the hot copy carries the decay
        anchor too. This test pins that structural property.
        """
        tier = make_tier(make_storage(watermark=None))
        cache = make_cache(tier)

        with patch("autom8_asana.cache.integration.dataframe_cache.asyncio.create_task"):
            from_s3 = await cache.get_async(PROJECT_GID, ENTITY_TYPE)

        hot = cache.memory_tier.get(CACHE_KEY)
        assert hot is not None
        assert hot is from_s3
        assert hot.created_at == NULL_WATERMARK_DECAY_ANCHOR

        # Second read is served from memory and reports the same verdict.
        with patch("autom8_asana.cache.integration.dataframe_cache.asyncio.create_task"):
            from_memory = await cache.get_async(PROJECT_GID, ENTITY_TYPE)

        assert from_memory is not None
        assert from_memory.created_at == NULL_WATERMARK_DECAY_ANCHOR
        info = cache.get_freshness_info(PROJECT_GID, ENTITY_TYPE)
        assert info is not None
        assert info.freshness == FreshnessState.STALE.value
