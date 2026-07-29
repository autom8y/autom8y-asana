"""Substrate-v2 Seam 3 — REBUILD (infra). RC-E.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 3. SEAM-0 landed the
frozen ``RebuildOutcome`` (CLOSED) + the ``Rebuilder`` Protocol signature; **S4
fills the stage-validate-swap body here** (this file) composing the REAL S2
freshness (``substrate.freshness``) + S3 store (``substrate.store``).

The law in one breath (RC-E): a rebuild writes ONLY a staging version, validates
the STAGED bytes, then performs ONE atomic pointer publish LAST — a partial or
failed build leaves the live pointer unmoved (partial ≠ corrupt). Reads route
``SubstrateReader`` (Seam 4), which has no write method; the ``Rebuilder`` has no
serve-read — capability separation is the frozen invariant ([H9]).

Drawn contracts filled by S4 (owner-fill authority; the method surfaces were NAMED
but undrawn in §4):

* ``PacedAsanaFetcher`` — the injected paced live-Asana fetch capability ([H11]).
  Its ONE method returns a fully-materialised frame + per-section content-fetch
  instants. All live Asana I/O routes THIS injected capability; ``substrate.rebuild``
  imports NO ``AsanaClient`` and opens no un-paced path (RC-E-4 — proven by the
  structural import test). A production impl composes v1's G6 controllers exactly
  as the S7 parity runner does — ``BudgetAllocator.warmer_floor_gate().admit()``
  (advisory static floor) → ``AsyncAdaptiveSemaphore.acquire()`` (AIMD concurrency
  slot) → ``RetryOrchestrator`` → ``gather_with_semaphore`` (bounded per-section
  fan-out). Per-section granularity flows from C1; the per-day budget model is
  parameterised at the floor gate (``PublishedFloor``); REAL section counts ride to
  S8 as a labelled UV-P (no prod probe in this dark build).
* ``AcceptancePredicates`` — the injected staged-version validator ([H13]/C9).
  ``validate()`` runs the three checks and, on PASS, mints a ``ValidationReceipt``
  — the un-bypassable key ``_publish`` requires. ``DefaultAcceptancePredicates``
  is the concrete S4 realisation.
* ``RebuildResult`` — the outcome envelope; S4 fills the field surface (S6 declined
  it — ``observe`` never referenced it).

C9/C12/C14 obligation dispositions (encoded + tested here):

* **C9** — swap is gated on a ``ValidationReceipt`` minted ONLY by ``validate()``
  (construction-enforces validate-before-swap: ``_publish`` takes the receipt and
  binds it to the staged version), AND a discriminating swap-before-validate test
  proves a deliberately-miswired ordering is caught (``tests/.../test_rebuild.py``).
* **C12** (architect ruling, encoded VERBATIM) — the rebuilder reads the current
  pointer's ``proof.built_from_live_at`` and swaps its staged version ONLY IF
  ``staged.built_from_live_at >= current`` (a forward/idempotent advance); a staged
  version strictly older than current is DISCARDED, not swapped (a staler build
  that lost a concurrent race must never regress the pointer) — the sole exception
  being an explicit, logged/receipted rollback path. On a CAS (``If-Match``) failure
  the rebuilder RE-READS the current pointer and re-applies this monotonicity check
  before retrying.
* **C14** — when the staged ``version_id`` equals the current pointer's
  ``version_id`` (byte-stable content, idempotent stage), the rebuilder performs the
  pointer-only proof refresh via ``store.refresh_pointer_proof`` (same version,
  fresher proof) — the F1 stale-forever cure. ``StaleProofRefused`` (a concurrent
  fresher win) is accepted as advanced-done; ``ProofDigestMismatch`` is
  unconstructable from this flow (the refreshed proof always describes the SAME
  version's bytes) and is surfaced as a loud invariant failure.

Side effects are EXPLICIT (RC-E): the store is touched ONLY with a COMPLETE,
in-memory-materialised frame — ``stage_version`` (staging, non-pointer) then ONE
pointer publish. There is NO persist-section-k call in this path, so the v1
progressive-builder hazard (a "read-only" recompute that persisted sections
mid-fetch and wrote prod — DEFECT-seam1 :76) is structurally absent: a fetch that
raises mid-way leaves the store byte-identical.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from autom8_asana.substrate.freshness import (
    FreshnessProof,
    canonical_digest,
    fold_built_from_live_at,
    sla_seconds_for,
)
from autom8_asana.substrate.identity import artifact_key
from autom8_asana.substrate.store import (
    CREATE_IF_ABSENT,
    ArtifactMissing,
    CASLost,
    PointerAbsent,
    ProofDigestMismatch,
    StaleProofRefused,
    VersionId,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping
    from datetime import datetime

    import polars as pl

    from autom8_asana.core.types import EntityType
    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.store import PointerState, S3ArtifactStore

# Injected clock — tz-aware UTC. Deterministic in tests; ``datetime.now(UTC)`` in prod.
type NowFn = Callable[[], "datetime"]
# Deterministic frame → stored bytes. version_id = sha256(these bytes), so byte-stable
# logical content MUST mint identical bytes for C3 idempotency / C14 to hold.
type FrameSerializer = Callable[["pl.DataFrame"], bytes]
# (project, entity) → sla_seconds. Default reads the entity registry (S2 C8).
type SlaResolver = Callable[["EntityType"], int]


# --------------------------------------------------------------- outcomes ---
class RebuildOutcome(Enum):
    """CLOSED rebuild outcome taxonomy (frozen §4; no member added).

    * ``SWAPPED`` — the live pointer now serves a fresher truth: a new version was
      CAS-swapped in, OR (C14) the SAME version's proof was refreshed forward. Both
      are "the artifact advanced" from a consumer's view.
    * ``STAGED_REJECTED`` — a version was staged but did NOT become current:
      ``validate`` failed (discard), or C12 monotonicity declined a staler build.
      Live untouched (partial ≠ corrupt).
    * ``FETCH_REFUSED`` — the paced fetch refused before anything was staged (rate
      backpressure / upstream refusal). Zero store writes.
    """

    SWAPPED = "swapped"
    STAGED_REJECTED = "staged_rejected"
    FETCH_REFUSED = "fetch_refused"


@dataclass(frozen=True, slots=True)
class RebuildResult:
    """Envelope returned by ``Rebuilder.rebuild``. Seam 3, FROZEN v1.0 (S4-filled).

    ``version_id`` / ``built_from_live_at`` describe the LIVE artifact after this
    rebuild (present on ``SWAPPED``; ``None`` when nothing was published).
    ``detail`` is a human-readable disposition (the validation-failure reason, the
    monotonicity decline, the fetch refusal) — never a substitute for the outcome.
    """

    outcome: RebuildOutcome
    version_id: VersionId | None = None
    built_from_live_at: datetime | None = None
    detail: str = ""


# --------------------------------------------------------- fetch capability ---
class FetchRefused(Exception):
    """A paced fetch declined to pull live content (rate backpressure / upstream refusal).

    Raised by a ``PacedAsanaFetcher``; the rebuilder maps it to ``FETCH_REFUSED``.
    Because the fetch precedes every store write, a refusal leaves the store
    byte-identical — the RC-E side-effect-free-read guarantee.
    """


@dataclass(frozen=True, slots=True)
class FetchedSections:
    """The paced fetch's output — a fully-materialised frame + its provenance (C1).

    ``frame`` is the WHOLE assembled version (fetched sections ∪ reused sections),
    materialised IN MEMORY — the store never sees a partial. ``section_instants``
    maps ``section_gid -> last content-fetch instant``: a re-fetched section carries
    ``now``; a REUSED (not re-fetched) section carries its PRIOR instant unchanged.
    Only a real content fetch advances an instant; a structural probe decides
    scheduling ONLY and never stamps one (C1). The rebuilder MIN-folds these into
    the artifact's ``built_from_live_at`` via S2's ``fold_built_from_live_at`` — so
    the artifact honestly ages to its stalest constituent section.
    """

    frame: pl.DataFrame
    section_instants: Mapping[str, datetime]


class PacedAsanaFetcher(Protocol):
    """Injected paced live-Asana fetcher ([H11]/RC-E-4). Seam 3 — S4-drawn contract.

    The rebuilder DELEGATES all live Asana I/O to this capability and never
    constructs an ``AsanaClient`` (RC-E-4). A production impl composes v1's G6
    controllers (floor-gate admit → AIMD slot → retry → bounded gather); a test
    injects a fake. S7's parity runner may later reuse this contract.
    """

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        """Paced per-section rebuild-fetch → a complete ``FetchedSections``.

        Probes per-section staleness (a probe DECIDES re-fetch; a section older than
        ``SLA - cadence`` MUST re-fetch), pulls the decided sections' value-rows LIVE
        (paced), reuses the rest, assembles the whole frame IN MEMORY, and reports
        the post-fetch per-section instants. Raises ``FetchRefused`` under rate
        backpressure (no partial is ever persisted).
        """
        ...


# ------------------------------------------------------------- validation ---
@dataclass(frozen=True, slots=True)
class StagedVersion:
    """The staged (not-yet-published) version handed to ``AcceptancePredicates.validate``.

    Carries the materialised ``frame`` (so ``validate`` can re-derive
    ``canonical_digest`` and count populated rows), the stored ``frame_bytes``, the
    ``version_id`` the store minted, and the ``proof`` the rebuilder built.
    """

    version_id: VersionId
    frame: pl.DataFrame
    frame_bytes: bytes
    proof: FreshnessProof


@dataclass(frozen=True, slots=True)
class ValidationReceipt:
    """The C9 swap key — minted ONLY by ``AcceptancePredicates.validate()`` on PASS.

    ``_publish`` REQUIRES a receipt and binds it to the staged version
    (``receipt.version_id == staged.version_id``). There is no other path to a
    receipt, so validate-before-swap is construction-enforced: a rebuilder cannot
    publish a version it did not validate without fabricating this object — which the
    discriminating swap-before-validate test detects.
    """

    version_id: VersionId
    content_digest: str


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    """A validate() rejection — the failed check + a human-readable reason (no receipt)."""

    check: str
    reason: str


# A PASS mints a receipt (the swap key); a FAIL yields a reason and NO receipt.
type ValidationResult = ValidationReceipt | ValidationFailure


class AcceptancePredicates(Protocol):
    """Injected staged-version validator (validate-before-swap; [H13]/C9). Seam 3 — S4-drawn.

    ``validate`` runs the three [H13] checks against the STAGED bytes and returns a
    ``ValidationReceipt`` (PASS — the swap key) or a ``ValidationFailure`` (FAIL —
    discard staging, live untouched).
    """

    def validate(self, staged: StagedVersion, now: datetime) -> ValidationResult:
        """[H13]: population-floor + digest-self-consistency + proof-well-formedness."""
        ...


@dataclass(frozen=True, slots=True)
class DefaultAcceptancePredicates:
    """Concrete [H13] validator (S4 fill authority, O-b ruling).

    Three checks, ALL required for a receipt:

    1. **population-floor** — the frame carries at least ``min_rows`` rows AND every
       registry-declared value column (``canonical_digest``'s pinned set) is non-null
       on the active-classified rows. A degenerate/empty rebuild cannot replace a
       healthy artifact. ``active_predicate`` selects the active rows (default: all
       rows — a frame reaches this seam already active-classified upstream); the
       value-column floor is what ``canonical_digest`` itself pins, re-used here so
       there is ONE value-column source of truth (no drift enum).
    2. **digest-self-consistency** — ``canonical_digest(staged.frame)`` re-derives to
       exactly ``staged.proof.content_digest``. This is the same equality Seam-4's
       ``is_provable`` enforces (mismatch → CORRUPT); catching it pre-swap means a
       proof can never be published against bytes it does not describe.
    3. **proof-well-formedness** — ``built_from_live_at`` is tz-aware (guaranteed by
       ``FreshnessProof.__post_init__`` but re-asserted here) and NOT in the future
       relative to ``now`` (a future instant would serve PROVABLE forever — the
       frozen ``<= sla`` predicate has no negative-age floor); ``sla_seconds > 0``.
    """

    min_rows: int = 1
    active_predicate: Callable[[pl.DataFrame], pl.DataFrame] | None = None

    def validate(self, staged: StagedVersion, now: datetime) -> ValidationResult:
        # (1) population-floor -------------------------------------------------
        active = (
            staged.frame if self.active_predicate is None else self.active_predicate(staged.frame)
        )
        if active.height < self.min_rows:
            return ValidationFailure(
                check="population-floor",
                reason=(
                    f"active row count {active.height} < floor {self.min_rows} — "
                    "refusing to publish a degenerate rebuild over a healthy artifact"
                ),
            )
        null_columns = _value_columns_with_nulls(active)
        if null_columns:
            return ValidationFailure(
                check="population-floor",
                reason=f"null value column(s) {sorted(null_columns)} on active rows",
            )

        # (2) digest-self-consistency -----------------------------------------
        rederived = canonical_digest(staged.frame)
        if rederived != staged.proof.content_digest:
            return ValidationFailure(
                check="digest-self-consistency",
                reason=(
                    f"staged bytes re-derive content_digest {rederived!r} but the proof "
                    f"carries {staged.proof.content_digest!r}"
                ),
            )

        # (3) proof-well-formedness -------------------------------------------
        proof = staged.proof
        if proof.built_from_live_at.tzinfo is None or proof.built_from_live_at.utcoffset() is None:
            return ValidationFailure(
                check="proof-well-formedness", reason="built_from_live_at is not tz-aware"
            )
        if proof.built_from_live_at > now:
            return ValidationFailure(
                check="proof-well-formedness",
                reason=(
                    f"built_from_live_at {proof.built_from_live_at.isoformat()} is in the "
                    f"future relative to now {now.isoformat()}"
                ),
            )
        if proof.sla_seconds <= 0:
            return ValidationFailure(
                check="proof-well-formedness",
                reason=f"non-positive sla_seconds {proof.sla_seconds}",
            )

        return ValidationReceipt(version_id=staged.version_id, content_digest=proof.content_digest)


# ------------------------------------------------------------ single-flight ---
class SingleFlight(Protocol):
    """Per-key single-flight coalescer ([H12]/G7). Injected; default is process-local.

    ``run(key, factory)`` executes ``factory()`` at most once per in-flight ``key``;
    concurrent callers on the same key await the single winner's result. Production
    injects v1's ``DataFrameCacheCoalescer`` (G7); the default here is a lightweight
    process-local registry (the dark build touches no CloudWatch).
    """

    async def run(self, key: str, factory: Callable[[], Awaitable[RebuildResult]]) -> RebuildResult:
        """Coalesce concurrent calls sharing ``key`` onto ONE execution of ``factory``."""
        ...


class LocalSingleFlight:
    """Process-local single-flight ([H12] default) — one in-flight execution per key.

    Concurrent callers on the same key await the first caller's task; distinct keys
    proceed independently. No metrics, no cross-process coordination (that is the
    store's CAS job); prod may inject the G7 coalescer instead.
    """

    def __init__(self) -> None:
        self._inflight: dict[str, asyncio.Task[RebuildResult]] = {}
        self._lock = asyncio.Lock()

    async def run(self, key: str, factory: Callable[[], Awaitable[RebuildResult]]) -> RebuildResult:
        async with self._lock:
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.ensure_future(factory())
                self._inflight[key] = task
                owner = True
            else:
                owner = False
        try:
            return await task
        finally:
            if owner:
                async with self._lock:
                    self._inflight.pop(key, None)


# ----------------------------------------------------------------- rebuilder ---
class Rebuilder(Protocol):
    """Stage-validate-swap rebuilder (RC-E). Seam 3, FROZEN v1.0.

    ``Rebuilder`` and ``SubstrateReader`` are DISTINCT types ([H9]) — the rebuilder
    exposes no serve-read and the reader exposes no write.
    """

    async def rebuild(
        self,
        aid: ArtifactId,
        fetch: PacedAsanaFetcher,
        validate: AcceptancePredicates,
    ) -> RebuildResult:
        """ORDERED, swap LAST (see the module docstring for the C9/C12/C14 encoding)."""
        ...


class SubstrateRebuilder:
    """Concrete stage-validate-swap rebuilder (RC-E). Composes S2 freshness + S3 store.

    Capability-typed ([H9]): exposes ONLY ``rebuild`` — no serve-read, no store
    mutation is re-surfaced. The store, clock, deterministic serializer, sla
    resolver, and single-flight coalescer are injected at construction; the per-call
    ``fetch``/``validate`` match the frozen ``Rebuilder`` signature.

    ``max_cas_retries`` bounds the C12 re-read/re-check retry loop against pathological
    cross-process pointer churn; a staler build converges to a decline on re-read.
    """

    def __init__(
        self,
        store: S3ArtifactStore,
        *,
        now: NowFn | None = None,
        serialize: FrameSerializer | None = None,
        sla_for: SlaResolver | None = None,
        single_flight: SingleFlight | None = None,
        max_cas_retries: int = 8,
    ) -> None:
        self._store = store
        self._now: NowFn = now if now is not None else _utc_now
        self._serialize: FrameSerializer = (
            serialize if serialize is not None else canonical_frame_bytes
        )
        self._sla_for: SlaResolver = sla_for if sla_for is not None else sla_seconds_for
        self._single_flight: SingleFlight = (
            single_flight if single_flight is not None else LocalSingleFlight()
        )
        self._max_cas_retries = max_cas_retries

    async def rebuild(
        self,
        aid: ArtifactId,
        fetch: PacedAsanaFetcher,
        validate: AcceptancePredicates,
    ) -> RebuildResult:
        """Stage-validate-swap for ``aid`` — single-flight-coalesced per ArtifactId ([H12])."""
        key = artifact_key(aid)
        return await self._single_flight.run(key, lambda: self._rebuild_once(aid, fetch, validate))

    async def _rebuild_once(
        self,
        aid: ArtifactId,
        fetch: PacedAsanaFetcher,
        validate: AcceptancePredicates,
    ) -> RebuildResult:
        # 1-3. paced fetch → materialise → freshness (all IN MEMORY; store untouched).
        try:
            fetched = await fetch.fetch(aid)
        except FetchRefused as exc:
            return RebuildResult(outcome=RebuildOutcome.FETCH_REFUSED, detail=str(exc))

        built_from_live_at = fold_built_from_live_at(fetched.section_instants)  # S2 MIN-fold (C1)
        content_digest = canonical_digest(fetched.frame)  # S2 [H1]
        frame_bytes = self._serialize(fetched.frame)  # deterministic (S8 carry)
        proof = FreshnessProof(
            built_from_live_at=built_from_live_at,
            content_digest=content_digest,
            sla_seconds=self._sla_for(aid.entity_type),
        )

        # 4. stage ONLY (never the pointer) — the FIRST and only pre-publish store write.
        staged_version_id = await self._store.stage_version(aid, frame_bytes, proof)
        staged = StagedVersion(
            version_id=staged_version_id, frame=fetched.frame, frame_bytes=frame_bytes, proof=proof
        )

        # 5. validate the STAGED bytes ([H13]). FAIL → discard, live untouched (partial ≠ corrupt).
        result = validate.validate(staged, self._now())
        if isinstance(result, ValidationFailure):
            return RebuildResult(
                outcome=RebuildOutcome.STAGED_REJECTED,
                detail=f"validation failed [{result.check}]: {result.reason}",
            )

        # 6. publish LAST — the single atomic monotonic CAS, gated on the receipt (C9).
        return await self._publish(aid, staged, result)

    async def _publish(
        self, aid: ArtifactId, staged: StagedVersion, receipt: ValidationReceipt
    ) -> RebuildResult:
        """The C9-gated publish: requires a ``ValidationReceipt`` for THIS staged version.

        Encodes the C12 monotonicity ruling + C14 idempotent proof-refresh. Re-reads
        the current pointer at the top of EACH retry and re-branches (first-publish /
        C14 refresh / C12 advance-or-decline) so a lost CAS race re-applies the
        monotonicity check before retrying.
        """
        if receipt.version_id != staged.version_id:
            raise ValueError(
                f"validation receipt is for version {receipt.version_id} but the staged "
                f"version is {staged.version_id} — refusing to publish an unvalidated version (C9)"
            )

        for _attempt in range(self._max_cas_retries):
            current = await self._store.read_pointer(aid)

            # First-ever publish: create the pointer.
            if current is None:
                try:
                    await self._store.swap_pointer(
                        aid, staged.version_id, if_match=CREATE_IF_ABSENT
                    )
                except CASLost:
                    continue  # another writer created it first — re-read + re-branch
                return self._swapped(staged)

            # C14 idempotent stage: byte-stable content → pointer-only proof refresh.
            if current.version_id == staged.version_id:
                # C12 monotonicity: never move built_from_live_at backward for the same version.
                if staged.proof.built_from_live_at < current.proof.built_from_live_at:
                    return self._declined(current, "same version, staged proof older than current")
                try:
                    await self._store.refresh_pointer_proof(
                        aid, staged.proof, if_match=current.etag
                    )
                except (CASLost, PointerAbsent, ArtifactMissing):
                    continue  # concurrent pointer write/delete — re-read + re-branch
                except StaleProofRefused:
                    # A concurrent fresher win advanced the pointer's proof past ours: accept, done.
                    return self._swapped(staged)
                except ProofDigestMismatch:
                    # Unconstructable from this flow: a same-version refresh describes the SAME
                    # bytes → the same canonical digest. If it fires, re-read to disambiguate a
                    # concurrent pointer move (re-branch) from a genuine invariant violation (loud).
                    moved = await self._store.read_pointer(aid)
                    if moved is not None and moved.version_id != staged.version_id:
                        continue
                    raise
                return self._swapped(staged)

            # Byte-changed: C12 advance-or-decline (rollback is a separate receipted path).
            if staged.proof.built_from_live_at < current.proof.built_from_live_at:
                return self._declined(
                    current, "staged build older than current — will not regress the pointer"
                )
            try:
                await self._store.swap_pointer(aid, staged.version_id, if_match=current.etag)
            except (CASLost, PointerAbsent):
                continue  # lost the race / pointer reaped — re-read + re-apply C12 (C12 verbatim)
            return self._swapped(staged)

        # Exhausted the bounded retry budget: re-read once and decline to a staler-or-equal current.
        final = await self._store.read_pointer(aid)
        if final is not None and staged.proof.built_from_live_at <= final.proof.built_from_live_at:
            return self._declined(
                final, "CAS contention: current is at-least-as-fresh after retries"
            )
        raise CASLost(
            f"exhausted {self._max_cas_retries} CAS attempts publishing {aid!r} -> {staged.version_id}"
        )

    @staticmethod
    def _swapped(staged: StagedVersion) -> RebuildResult:
        return RebuildResult(
            outcome=RebuildOutcome.SWAPPED,
            version_id=staged.version_id,
            built_from_live_at=staged.proof.built_from_live_at,
            detail="",
        )

    @staticmethod
    def _declined(current: PointerState, why: str) -> RebuildResult:
        return RebuildResult(
            outcome=RebuildOutcome.STAGED_REJECTED,
            version_id=current.version_id,
            built_from_live_at=current.proof.built_from_live_at,
            detail=f"monotonicity decline: {why}",
        )


# ------------------------------------------------------------- serializers ---
def canonical_frame_bytes(frame: pl.DataFrame) -> bytes:
    """A deterministic, row/column-canonical byte encoding of ``frame`` (dark-build default).

    ``version_id = sha256(these bytes)``; byte-stable LOGICAL content must mint
    identical bytes or C3 idempotency / C14 refresh cannot fire. This default sorts
    columns, canonicalises each record (``sort_keys`` + a stable ``str`` fallback for
    datetimes/Decimals), and sorts the row encodings — so identical logical frames in
    any input row/column order collapse to identical bytes. It is explicitly NOT
    ``write_parquet()`` (whose compression/metadata are non-deterministic — the QA
    two-digest serialization carry). Prod may inject a schema-aware deterministic
    writer; that determinism verification is the S8 gate's job (labelled UV-P).
    """
    import polars as pl_mod

    if not isinstance(frame, pl_mod.DataFrame):  # defensive: the seam contract is pl.DataFrame
        raise TypeError(
            f"canonical_frame_bytes expects a polars DataFrame, got {type(frame).__name__}"
        )
    columns = sorted(frame.columns)
    records = frame.select(columns).to_dicts()
    encoded_rows = sorted(
        json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        for record in records
    )
    payload = "\x1e".join(encoded_rows)
    return payload.encode("utf-8")


# ------------------------------------------------------------------ helpers ---
def _utc_now() -> datetime:
    from datetime import UTC, datetime

    return datetime.now(UTC)


def _value_columns_with_nulls(frame: pl.DataFrame) -> set[str]:
    """The pinned value columns that carry ≥1 null in ``frame`` (population-floor check).

    Re-uses ``canonical_digest``'s pinned value-column set as the single source of
    truth (no drift enum). A value column ABSENT from the frame is a null-equivalent
    for the floor (its absence means the population is not established) — but the
    digest-self-consistency check will already have refused an absent-column frame
    upstream, so here we only inspect present columns.
    """
    from autom8_asana.substrate.freshness import _VALUE_COLUMNS

    offenders: set[str] = set()
    present = set(frame.columns)
    for column in _VALUE_COLUMNS:
        if column not in present:
            offenders.add(column)
            continue
        if frame.get_column(column).null_count() > 0:
            offenders.add(column)
    return offenders
