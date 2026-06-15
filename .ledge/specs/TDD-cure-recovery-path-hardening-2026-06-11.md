---
type: spec
subtype: tdd
status: proposed
title: "Cure-Recovery-Path Hardening — Fail-Closed Write + Quality-Aware Freshness"
slug: cure-recovery-path-hardening
date: 2026-06-11
rite: 10x-dev
phase: architecture
author: architect
evidence_grade: MODERATE  # self-rite authorship ceiling per self-ref-evidence-grade-rule
impact: high  # data-quality / serving-correctness; ship soak-clear-gated
impact_categories: [performance, data-migration]
substrate_head: b48452d  # the CERTIFIED/DEPLOYED head carrying the cure; NOT branch HEAD 3bbb9bc8
related_adr: .ledge/decisions/ADR-cure-recovery-path-hardening-2026-06-11.md
chaos_receipt: .ledge/reviews/SRE-IGNITION-MATRIX-realization-tail-2026-06-11.md
telos: .know/telos/dataframe-resolution-coherence.md
---

# TDD — Cure-Recovery-Path Hardening

## Grandeur Anchor

> We harden the cure the telos rests on so a durable-read OUTAGE degrades to the
> LAST-GOOD frame and AUTO-RE-HEALS — never persisting a freshly nulled frame, never
> freshness-skipping the recovery — driving the rung from *cure-degrades-honestly* to
> *cure-degrades-SAFELY-and-self-heals*.

This is **defense-in-depth**: the durable-read grant (`S3DurableTaskCacheRead`) is HEALTHY
in production now; the trigger is not live. EXP-1 (2026-06-11) was a deliberate chaos
revocation that surfaced two latent gaps. The deploy that makes this hardening live RESETS
the running telos-soak (anchored 2026-06-11T08:41Z, clear ~2026-06-18) → **HELD / soak-clear-gated**.

## §0 PV Ledger (re-derived live against `b48452d`, default-to-REFUTED)

Code is truth. The prompt's anchors are HYPOTHESES; every one below was re-derived by
direct inspection. Two prompt anchors INVERTED.

| Premise | Verdict | Receipt (file:line @ b48452d) |
|---|---|---|
| PV-PATH-1: cure at `dataframes/builders/null_number_recovery.py` | **PARTIAL → relocated-by-branch** | The file exists at `b48452d` but NOT at branch HEAD `3bbb9bc8` (`git diff 3bbb9bc8..b48452d -- src/` shows the file as a +609-line ADD). `b48452d` is NOT an ancestor of HEAD. **All design anchors are against the deployed/certified head `b48452d`, the substrate the chaos drill ran against.** |
| PV-PATH-2: floor at `post_build_population_receipt.py` | **CONFIRMED (at b48452d)** | `dataframes/builders/post_build_population_receipt.py:54` `POPULATION_WARN_THRESHOLD = 0.80`; `:69` `"unit": ("mrr",)`; `:240` `logger.warning("population_receipt_below_floor", ...)` |
| PV-FINDING-1: write is UNCONDITIONAL after recovery no-op | **CONFIRMED** | `dataframes/builders/progressive.py:863-871` — the Step-6 write gate is `if total_rows > 0 or honest_complete_empty:` then `write_final_artifacts_async(...)`. NO quality/heal-success term. The recovery receipt is captured at `:812` as `_recovery_receipt` (underscore = DISCARDED). |
| PV-FINDING-2: freshness predicate is AGE-keyed | **CONFIRMED** | `metrics/freshness.py:173-179` `FreshnessReport.stale` returns `self.max_age_seconds > self.threshold_seconds`. Per-entity ceiling `config.py:219` `FRESHNESS_CONTRACT_MAX_AGE_SECONDS = {"project": 86400.0, "section": 3000.0}`. No data-QUALITY term anywhere in the predicate. |
| PV-QUALITY-SIGNAL: floor receipt is the SSOT | **CONFIRMED** | `post_build_population_receipt.py:219` `below_floor = min_rate < POPULATION_WARN_THRESHOLD`; the receipt is RETURNED (`PopulationReceipt`, `:244`) but its return value is **DISCARDED** at the call site `progressive.py:834` (`post_build_population_receipt(...)` invoked for side-effect only). This is the orphan signal both forks must re-wire. |
| PV-OFFER-INTACT: offer write path live-served, must not regress | **CONFIRMED** | Chaos receipt §4.1: offer frame `1332/4079` (live MRR) untouched during EXP-1. Floor declares offer `("mrr","offer_id")` (`post_build_population_receipt.py:61`); the cure + receipt run on BOTH entities through the SAME field-agnostic loop (`progressive.py:798-850`). Fail-closed must be symmetric and offer-safe. |
| PV-FROZEN: cold fan-out uses `_SANCTIONED_IO_TO_THREAD` + FROZEN-4 guard | **CONFIRMED** | `cache/durable_task_cache.py:41` names THIS module as the SOLE `asyncio.to_thread` offload site (`:301`); `tests/unit/dataframes/test_concurrency_invariants_guard.py` is the regression guard. Design adds NO new `to_thread` site. |
| PV-BUILD-QUALITY: `DataFrameCacheEntry.build_quality` as carrier | **INVERTED → no null-population field exists** | The carrier is `dataframes/builders/build_result.py:265` `class BuildQuality` (frozen, slots). It carries `status` (success/partial/failure from SECTION outcomes), `sections_*`, `failed_section_gids`, `error_summary` — but **NO null-population / degraded field**. THROUGHLINE §5's anchor `cache/integration/dataframe_cache.py:68` is the cache-entry attachment point, not the definition. Design ADDS a `population_degraded` field to `BuildQuality` as the shared seam. |

### PV inversion summary (G-PROVE)

1. **The cure is NOT on branch HEAD.** The active branch `cr3/gate2-receiver-probe-and-durability`
   (HEAD `3bbb9bc8`) predates the FPC Phase-2 cure. The cure, floor, and durable reader all
   live at `b48452d`. This TDD designs against `b48452d`. Implementation must rebase onto / land
   after the cure substrate.
2. **`build_quality` does not yet carry a degraded signal.** It must be EXTENDED, not merely read.
   This is the seam for BOTH forks (composition point §6).

Neither inversion re-scopes the design — both forks remain valid and necessary. The write does
NOT already fail-closed (PV-FINDING-1 CONFIRMED), so the hardening is load-bearing.

## §1 System Context

```
                          warmer / consumer refresh
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │  ProgressiveProjectBuilder.build (progressive.py)      │
        │                                                        │
        │  5.65 recover_null_number_cells ── NumericRecoveryRcpt │  ← cure (cache-reuse)
        │          │ (durable S3 read via DurableTaskCacheReader)│
        │          ▼                                             │
        │  5.7  post_build_population_receipt ── PopulationReceipt│  ← floor (SSOT)
        │          │  below_floor over ACTIVE subset             │
        │          ▼                                             │
        │  6    [WRITE GATE]  write_final_artifacts_async ───────┼──▶ save_dataframe (S3 parquet)
        └──────────────────────────────────────────────────────┘
                                   ▲
                                   │ freshness decides whether build even runs
        ┌──────────────────────────────────────────────────────┐
        │  FreshnessReport.stale = max_age > threshold (AGE-keyed)│  ← FORK-2 target
        └──────────────────────────────────────────────────────┘
```

Under a revoked `S3DurableTaskCacheRead` grant (EXP-1):
- `read_object` (`durable_task_cache.py:221`) `get_object` raises a `ClientError`(`AccessDenied`)
  — not classified as NoSuchKey/404 nor ValueError/OSError → `raise` (`:240`) → `_one`
  (`:296`) maps the gid to `None` + WARN `durable_task_cache_read_gid_failed`. All 3021 unit
  gids → None.
- Cure: `cache_miss_gids=3021`, `healed_cells=0` → emits `null_number_recovery_no_op`
  (`null_number_recovery.py:_emit`, the `else` branch when `healed_cells == 0`).
- Floor: `min_rate(mrr)=0.0 < 0.80` → `below_floor=True` → WARN `population_receipt_below_floor`.
- **Write gate (`progressive.py:863`) fires regardless** → the null-degraded frame is persisted
  (`dataframe.parquet` mrr_nonnull 0/3021). ← GAP-1.
- Post-restore warm: parquet mtime recent (`< threshold`) → `FreshnessReport.stale == False` →
  rebuild skipped; manifest re-stamped (`progressive.py:475` `section_last_verified_stamped`) so
  the frame LOOKS fresh while the dataframe stays degraded. ← GAP-2.

## §2 Non-Functional Requirements (measurable)

| ID | Requirement | Metric | Target | Method | Environment |
|---|---|---|---|---|---|
| NFR-1 | Fail-closed under cure-failure | persisted-frame mrr_nonnull after a forced durable-read outage | NEVER drops below the prior-good count for the same (project, entity); preserve prior-good OR refuse the write | RED→GREEN unit test §7 fixture at boto3 boundary | warmer warm path |
| NFR-2 | Auto-re-heal after grant restore | warms-to-heal a below-floor frame once the grant returns | ≤ 1 warm cycle after restore (no manual force, no staleness-window wait) | quality-aware freshness unit test §7 | warmer warm path |
| NFR-3 | Offer non-regression | offer frame write behavior during a unit-only cure failure | offer write UNCHANGED (live 1332/4079 preserved); fail-closed fires per-entity, never cross-entity | offer-arm assertion in §7 | both entities |
| NFR-4 | No false re-warm storm (G-DENOM) | rebuilds triggered by quality-aware freshness | fire ONLY on a real floor-breach over the ACTIVE subset; ZERO rebuilds for legitimately-sparse / cold-start / inactive-null frames | denominator test §7 | warmer warm path |
| NFR-5 | Concurrency invariant preserved | new `asyncio.to_thread` offload sites | 0 (FROZEN-4 guard stays green) | `test_concurrency_invariants_guard.py` | unit |
| NFR-6 | Never-fabricate preserved | cells written that have no durable-cache backing | 0 (honest-null only; merge-prior-good copies a PRIOR REAL value, never invents) | never-fabricate test (existing) + prior-good provenance test §7 | unit |

## §3 The Two Forks (option-enumeration discipline — exhaustive before recommend)

The forks INTERACT and must be designed as a coherent pair (§6). Each fork is enumerated
exhaustively below; recommendation follows each table.

### FORK-1 — FAIL-CLOSED WRITE

The question: under a cure-failure that drives the active-subset value column below the floor,
what does the Step-6 write gate (`progressive.py:863`) do?

| Option | Mechanism | What the reader serves in the gap | Serve-stale / LKG interaction | Cold-start (no prior-good)? | Verdict |
|---|---|---|---|---|---|
| **1(a) skip-write / preserve-prior-good** | When `below_floor AND cure attempted-but-healed:0 (cold_present_gids:0)`, SKIP `save_dataframe` for the value-bearing frame; leave the prior-good `dataframe.parquet` intact. Manifest stamping also skipped for this entity so freshness does not falsely advance. | The LAST-GOOD frame (prior warm's 723/3021). No null gap. | Reader's existing freshness/LKG path is unchanged; it sees the prior parquet, ages normally, serve-stale/LKG relief still applies. | UNSAFE if there is NO prior-good (first-ever warm, or post-schema-bump wipe): skipping leaves NO parquet → cold-miss → 503 trap (the exact failure honest-empty-200 fixed, `progressive.py:856`). Must fall through to a guarded write. | **RECOMMENDED, gated on prior-good existence** (composes with 1(c) for cold-start) |
| **1(b) write-but-mark-DEGRADED** | Always write, but stamp the frame's `BuildQuality.population_degraded=True` (+ watermark/index metadata). Reader/freshness can then act on the stamp. | The DEGRADED frame (nulls) — same gap as today, but now OBSERVABLE/actionable downstream. | Requires reader to honor the stamp (prefer LKG over a degraded-but-fresh frame) — a reader-side change, larger blast radius, touches the live offer read path (PV-OFFER-INTACT risk). | Safe (always writes) but serves nulls in the gap. | **REJECTED as the sole fix** — serves nulls; reader-side change risks the live offer path. ADOPTED as a SECONDARY signal (it is Fork-2's trigger; see §6). |
| **1(c) merge-prior-good number-columns for un-healable cells** | For cells the cure could not heal (`cache_miss`), coalesce the PRIOR-GOOD frame's value for the SAME gid+column before writing. New frame = healed-from-cache ∪ prior-good-for-the-rest. | A frame that is freshest-where-fresh and last-good-where-unhealable. Best continuity. | Compatible with serve-stale; the written frame is strictly ≥ prior-good in population. | Safe: if no prior-good, the coalesce is a no-op and the frame is whatever the cure produced (honest-null) — degrades to honest-empty-200, no 503 trap. | **RECOMMENDED as the cold-start-safe complement** to 1(a). Provenance: copies a PRIOR REAL value (never fabricates, NFR-6). |
| 1(d) hard-fail the build (status=FAILURE) | Make `below_floor` flip `BuildStatus` to FAILURE so no frame is produced. | Whatever FAILURE serves (LKG / 503). | Heavy: changes build-status semantics the floor explicitly REFUSES today (`post_build_population_receipt.py:17` "NEVER changes build status"). Regresses the "degraded-but-present beats empty" design (62 rows beat empty denominator). | Same 503 trap risk as 1(a) bare. | **REJECTED** — violates the floor's load-bearing WARN-first contract; over-broad blast radius. |

**FORK-1 RECOMMENDATION:** **1(a) preserve-prior-good, with 1(c) merge-prior-good as the
cold-start-safe fallback.** Concretely: a single `fail_closed_write` decision —
*if the floor breached AND the cure healed nothing from cache (`healed_cells==0 and cold_present_gids==0`)
AND a prior-good frame exists with strictly-higher active population, then DO NOT overwrite it
(1a); else if a prior-good exists with SOME higher-population cells, coalesce them in before
writing (1c); else (cold-start, no prior-good) write the honest-null frame (preserving the
honest-empty-200 invariant) and rely on Fork-2 to re-heal.* 1(b)'s DEGRADED stamp is retained
as a SECONDARY observability signal and as Fork-2's trigger, NOT as the primary gap fix.

Rationale: 1(a) gives zero-null serving in the common case (prior-good exists), 1(c) covers the
partial-heal and never strands a cold-start project in the 503 trap, and avoiding 1(d) preserves
the floor's WARN-first contract and the offer live-serve path.

### FORK-2 — QUALITY-AWARE FRESHNESS

The question: after grant restore, the post-restore warm freshness-skips the rebuild because the
degraded parquet is recent (`max_age < threshold`). How does freshness learn the frame is degraded?

| Option | Mechanism | G-DENOM safety (fire only on real floor-breach over ACTIVE subset) | Coupling / blast | Verdict |
|---|---|---|---|---|
| **2(a) floor-breach → not-fresh → rebuild** | Freshness consults the persisted population-floor verdict: a frame whose `below_floor==True` is treated as STALE regardless of age. The rebuild decision becomes `stale_by_age OR degraded_by_quality`. | SAFE by construction: `below_floor` is ALREADY computed over the active-classified subset (`post_build_population_receipt.py:101-126`), with the SAME active filter the `active_mrr` denominator uses. No blanket "any null → rebuild". | Reads the existing floor SSOT; freshness gains one quality term. No new threshold invented. | **RECOMMENDED.** Derives directly from the population-floor SSOT (G-PROPAGATE), honors G-DENOM for free. |
| 2(b) DEGRADED-watermark-flag forces re-warm | Persist Fork-1(b)'s `population_degraded` stamp; freshness keys on the stamp. | Safe IF the stamp is set only on a real below-floor breach (it is, by definition). Functionally identical trigger to 2(a). | Adds a persisted flag the freshness reader must load (an extra read or a manifest field). More moving parts than 2(a) reading the floor verdict directly. | **ADOPTED as the persistence MECHANISM for 2(a)** — 2(a) needs the breach verdict to survive into the next warm; the `population_degraded` stamp IS that persistence. They are the same fix at two layers (§6). |
| 2(c) shorter max-DEGRADED-age ≪ max-fresh-age | A second, tighter age ceiling that applies only to degraded frames (e.g., 5 min vs 6 h). | Weak G-DENOM: still age-keyed, just a shorter clock. A degraded frame younger than the short ceiling STILL skips — does not deterministically re-heal; only shrinks the window. | Adds a second tunable age constant — config sprawl, still probabilistic. | **REJECTED** — does not guarantee re-heal (NFR-2 needs ≤1 cycle), keeps the age-keyed blind spot Fork-2 exists to remove. |
| 2(d) always rebuild (drop freshness skip) | Never skip the dataframe rebuild. | Trivially heals, but rebuilds EVERY warm even when fresh-and-healthy. | Re-introduces the build pressure the freshness skip exists to relieve (single-worker / serve-stale ceiling, telos band). | **REJECTED** — removes a load-bearing relief valve; storms the single-worker warmer. |

**FORK-2 RECOMMENDATION:** **2(a) floor-breach → not-fresh → rebuild, persisted via 2(b)'s
`population_degraded` stamp.** The rebuild predicate becomes
`needs_rebuild = stale_by_age OR (population_degraded AND grant_now_healthy)`. The
`grant_now_healthy` conjunct prevents a re-warm STORM while the grant is still revoked (a
degraded frame whose cause is still active would otherwise rebuild → re-degrade → loop); it
is satisfied implicitly because a healthy durable read produces `cold_present_gids > 0`, which
clears `below_floor` on the next successful warm.

Rationale: keys on the SSOT floor verdict (G-PROPAGATE), fires only on a real active-subset
breach (G-DENOM), guarantees ≤1-cycle re-heal (NFR-2), and preserves the age-based relief valve
for the healthy path (NFR-4).

## §4 Detailed Design

### 4.1 The shared seam: `BuildQuality.population_degraded`

`build_result.py:265 class BuildQuality` gains one field:

```
population_degraded: bool = False   # min active-subset value-column non-null rate < POPULATION_WARN_THRESHOLD
population_min_rate: float = 1.0    # the observed min_rate (forensics / alarm dimension)
```

Populated from the `PopulationReceipt` (currently discarded at `progressive.py:834`). This is
the single carrier consumed by BOTH forks. It rides into `cache/integration/dataframe_cache.py`
on the cache entry (the existing `build_quality` attachment seam) and into the persisted frame
metadata so the NEXT warm's freshness check (Fork-2) can read it.

### 4.2 FORK-1 wiring (write gate, `progressive.py` Step 5.65→6)

1. Capture both receipts: `merged_df, recovery_receipt = await recover_null_number_cells(...)`
   (un-discard `:812`); `population_receipt = post_build_population_receipt(...)` (un-discard `:834`).
2. Compute the fail-closed decision in a NEW pure helper
   `dataframes/builders/fail_closed_write.py::decide_write(population_receipt, recovery_receipt, prior_good_frame) -> WriteDecision`
   where `WriteDecision ∈ {WRITE_AS_IS, PRESERVE_PRIOR_GOOD, WRITE_COALESCED}`.
   - `PRESERVE_PRIOR_GOOD` when `below_floor AND healed_cells==0 AND cold_present_gids==0 AND prior_good has strictly-higher active population`.
   - `WRITE_COALESCED` when `below_floor AND prior_good exists with SOME higher-population value cells` (partial heal / partial prior-good).
   - `WRITE_AS_IS` otherwise (healthy frame, OR cold-start with no prior-good — preserves honest-empty-200).
3. The Step-6 gate honors the decision: `PRESERVE_PRIOR_GOOD` ⇒ skip `write_final_artifacts_async`
   for this entity AND skip the manifest stamp (so freshness does not falsely advance);
   `WRITE_COALESCED` ⇒ merge prior-good value cells (coalesce, never overwrite a populated cell —
   the SAME `pl.when(is_null).then(...).otherwise(...)` semantics the cure already uses at
   `null_number_recovery.py:413`) then write; `WRITE_AS_IS` ⇒ unchanged.
4. **Per-entity, never cross-entity** (NFR-3): the decision is computed inside the per-(project,entity)
   build, so a unit-frame fail-close cannot touch the offer frame.
5. **Prior-good fetch**: read the existing persisted frame via the storage read path the warm already
   has (`section_persistence` / `storage.load_dataframe`); on read failure, degrade to `WRITE_AS_IS`
   (never block a write on a prior-good READ error — additive posture, mirrors the cure's broad-catch).

### 4.3 FORK-2 wiring (freshness predicate)

`FreshnessReport.stale` (`metrics/freshness.py:173`) stays AGE-only (it is a pure mtime signal;
do not overload it). Instead, the REBUILD DECISION — the consumer/warmer gate that decides whether
to skip the dataframe rebuild — gains the quality term:

```
needs_rebuild = freshness_report.stale OR (persisted_build_quality.population_degraded AND not _grant_unhealthy_recently())
```

The `population_degraded` flag is read from the persisted frame metadata written by Fork-1. The
`_grant_unhealthy_recently` guard is the storm-suppressor: if the last warm's durable read failed
wholesale (`cache_miss_gids == total_null_gids AND cold_present_gids == 0`), do NOT rebuild on
quality alone (the cause is still active; rebuilding re-degrades). It clears automatically when a
healthy warm produces `cold_present_gids > 0`.

### 4.4 What is NOT touched

- No new `asyncio.to_thread` site (NFR-5; the cure's read path and FROZEN-4 allowlist unchanged).
- `post_build_population_receipt` internals unchanged — its return value is now CONSUMED, not its
  logic altered (G-PROPAGATE: the floor stays the SSOT; no bespoke per-builder flag).
- `recover_null_number_cells` internals unchanged — the cure stays never-fabricate / never-raise.
- The offer live-serve read path unchanged (no reader-side change; Fork-1(b) DEGRADED stamp is
  consumed only by Fork-2's warm-side rebuild decision, not by the live read).

## §5 Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Prior-good read adds latency/failure mode to the warm | MEDIUM | Read is best-effort; failure ⇒ `WRITE_AS_IS`. The warm already reads the manifest; the frame read is one more S3 GET on the SAME path. |
| Storm: degraded frame rebuilds → re-degrades while grant still revoked | HIGH | `_grant_unhealthy_recently` conjunct (§4.3) suppresses quality-only rebuild while the durable read is wholesale-failing. |
| Cold-start project stranded (no prior-good, skip-write) | HIGH | 1(c)/`WRITE_AS_IS` fallback preserves honest-empty-200 — never skips when no prior-good. |
| Offer regression (PV-OFFER-INTACT) | HIGH | Per-entity decision; offer arm asserted GREEN in §7; no reader-side change. |
| Deploy resets running telos-soak | KNOWN | DESIGN-ONLY; ship soak-clear-gated. Sequenced after soak clear (~2026-06-18) per chaos receipt §2. |
| Reversibility | — | TWO-WAY DOOR. `population_degraded` defaults False; the rebuild term is additive (`OR`); fail-closed degrades to `WRITE_AS_IS` on any uncertainty. Revert = drop the field + the two `OR`/decision terms. No schema migration, no public API change. |

## §6 How the Pair Composes

The forks share ONE seam and form a closed loop:

```
  cure no-ops (healed:0)  ──┐
                            ▼
  floor: below_floor=True  ──▶  BuildQuality.population_degraded = True  ◀── the shared seam
                            │              │
              FORK-1 reads ─┘              └─ FORK-2 reads (persisted into next warm)
                  │                                     │
        PRESERVE_PRIOR_GOOD / WRITE_COALESCED     needs_rebuild |= (degraded AND grant_healthy)
                  │                                     │
                  ▼                                     ▼
        gap serves LAST-GOOD (no nulls)        next healthy warm re-heals (≤1 cycle)
```

Interaction details (per the prompt's three interactions):
1. **Fork-1(b)'s DEGRADED stamp IS Fork-2(b)'s trigger** — they are the same `population_degraded`
   field at two layers. Fork-1 SETS it (write-time); Fork-2 READS it (next-warm-time). We adopt
   1(b) as a secondary signal precisely so Fork-2 has a persisted trigger.
2. **Fork-1(a) preserve-prior-good may MOOT Fork-2 for unit** — when 1(a) fires, the prior-good
   frame (which was NOT below-floor) is what persists, so `population_degraded` is NOT stamped on
   it → Fork-2 does not re-warm-storm; the frame simply ages normally and re-warms on schedule,
   by which time the grant is healthy. Fork-2 only does load-bearing work in the
   `WRITE_COALESCED` / cold-start `WRITE_AS_IS` paths where a degraded-or-partial frame DID persist.
3. They never conflict: Fork-1 governs WHAT is written; Fork-2 governs WHEN the next rebuild
   runs. The shared field is written by one and read by the other across warm boundaries.

**Coherent-pair invariant:** after any durable-read outage, the persisted frame is NEVER strictly
worse in active-subset population than the prior-good frame (Fork-1), AND any frame that IS
below-floor is guaranteed to rebuild on the next healthy warm (Fork-2). Together: degrade SAFELY,
self-heal DETERMINISTICALLY.

## §7 Test Contract (mandatory — @THROUGHLINE-integration-boundary-fidelity)

Per `.ledge/specs/THROUGHLINE-integration-boundary-fidelity-2026-06-10.md`: stub ONLY at the boto3
transport boundary; REAL `DataFrameCacheEntry`/`NumericRecoveryReceipt`/`PopulationReceipt` shapes
at REAL keys; exact-key assertions. NEVER stub above transport.

### 7.1 Fixture: deliberately-revoked-grant at the boto3 boundary

**Test module (new):** `tests/unit/dataframes/builders/test_cure_recovery_fail_closed.py`

Extends the EXISTING boto3-boundary convention at
`tests/unit/dataframes/builders/test_null_number_recovery.py:336` (`_FakeS3Client`,
`get_object(*, Bucket, Key)`) — the design adds a revoked-grant variant, it does NOT introduce a
new stub layer:

```python
class _ClientError(Exception):
    """Mirrors botocore.exceptions.ClientError by class name + response shape.
    The reader classifies by type name + message; AccessDenied is neither NoSuchKey/404
    nor ValueError/OSError, so read_object RAISES it (durable_task_cache.py:240) ->
    _one maps the gid to None + WARN durable_task_cache_read_gid_failed."""
    def __init__(self, op="GetObject"):
        self.response = {"Error": {"Code": "AccessDenied",
                                   "Message": "User is not authorized to perform: s3:GetObject"}}
        super().__init__(f"An error occurred (AccessDenied) when calling the {op} operation")

class _RevokedGrantS3Client:
    """boto3-CLIENT-boundary stub: get_object RAISES AccessDenied for the durable-task
    prefix (asana-cache/tasks/<gid>/task.json). Asserts the EXACT key the cure built
    (key-construction proof) BEFORE raising, so a wrong prefix still fails loudly."""
    def __init__(self, bucket, task_prefix):
        self._bucket, self._prefix = bucket, task_prefix
        self.keys_seen = []
    def get_object(self, *, Bucket, Key):
        self.keys_seen.append(Key)
        assert Bucket == self._bucket
        assert Key.startswith(self._prefix), f"unexpected prefix: {Key!r}"
        raise _ClientError()
```

Installed via the SAME `monkeypatch` idiom as the existing tests (`_install_fake_client` at
`test_null_number_recovery.py:385`: patch `nnr._get_s3_client` to return the fake, patch
`nnr.get_settings` for the bucket — the ONLY stub boundary is the boto3 client). The HOT store is
a real `_ColdHotStore`-shaped stand-in (all-miss), so the durable tier is the one exercised.

### 7.2 RED assertions (guard load-bearing — these FAIL on today's `b48452d` code)

- **RED-1 (Fork-1):** Given a prior-good frame (unit mrr 723/3021) persisted at the REAL key, and
  a warm under the revoked-grant client, assert the persisted frame after the warm is the
  PRIOR-GOOD frame (mrr_nonnull == 723), NOT the degraded frame (mrr_nonnull == 0). On today's
  code this FAILS: the degraded frame (0/3021) is persisted (`progressive.py:863` unconditional write).
- **RED-2 (Fork-2):** Given a persisted below-floor frame (`population_degraded=True`) and a NOW-HEALTHY
  durable client, assert the next warm REBUILDS (does not freshness-skip) and the resulting frame is
  re-healed. On today's code this FAILS: `FreshnessReport.stale==False` (recent mtime) → rebuild skipped.

### 7.3 GREEN assertions (post-fix)

- **GREEN-1:** "prior-good preserved" — persisted frame mrr_nonnull == prior-good count; the
  `_RevokedGrantS3Client.keys_seen` confirms the cure ATTEMPTED the exact durable keys
  `asana-cache/tasks/<gid>/task.json` (so we know the failure was at transport, not a skipped read).
- **GREEN-2:** "quality-aware rebuild fired" — the second warm's build path executed a rebuild and
  the frame's `below_floor` cleared (mrr_nonnull > floor·active_rows).

### 7.4 Companion assertions

- **OFFER-INTACT (NFR-3):** Run the offer arm (offer frame 1332/4079) through the SAME revoked-grant
  warm; assert the offer frame write is UNCHANGED and its `population_degraded` is governed ONLY by
  the offer's own active subset. Mutation proof: flip the fail-closed decision to cross-entity and
  assert this test goes RED.
- **G-DENOM (NFR-4):** A frame with legitimately-sparse INACTIVE rows (null mrr on non-active
  sections) must NOT trip `below_floor` (the active-subset filter excludes them) and must NOT
  trigger a Fork-2 rebuild. Mutation proof: widen the floor denominator to all rows and assert RED.
- **COLD-START (Fork-1 1c fallback):** No prior-good frame + revoked grant ⇒ `WRITE_AS_IS` honest-null
  frame persisted (NOT skipped) ⇒ honest-empty-200 invariant holds, no 503 trap.
- **FROZEN-4 (NFR-5):** `tests/unit/dataframes/test_concurrency_invariants_guard.py` stays green
  (no new `to_thread` site).

### 7.5 Mutation that proves each guard load-bearing

| Guard | Mutation | Expected |
|---|---|---|
| Fork-1 write gate | Revert §4.2 — restore unconditional write at `progressive.py:863` | RED-1 fails (degraded frame persisted) |
| Fork-2 rebuild term | Drop the `OR population_degraded` term from `needs_rebuild` | RED-2 fails (rebuild skipped) |
| Per-entity scope | Make fail-closed decision read a cross-entity frame | OFFER-INTACT goes RED |
| Active-subset denominator | Compute floor over all rows not active subset | G-DENOM goes RED |
| boto3-boundary fidelity | Stub `recover_null_number_cells` instead of the boto3 client | Test no longer exercises `read_object:221` AccessDenied path → key-construction proof vanishes (over-stub detected) |

## §8 Affected-Module List (for D2 / principal-engineer)

All anchors @ `b48452d`; implementation lands AFTER the cure substrate (rebase consideration: the
cure is not on the active branch HEAD).

- `src/autom8_asana/dataframes/builders/build_result.py` — add `population_degraded` + `population_min_rate` to `BuildQuality` (~:265).
- `src/autom8_asana/dataframes/builders/progressive.py` — un-discard both receipts (:812, :834); honor the write decision at Step 6 (:863-871); skip manifest stamp on PRESERVE_PRIOR_GOOD.
- `src/autom8_asana/dataframes/builders/fail_closed_write.py` — NEW pure helper `decide_write(...) -> WriteDecision` + coalesce expr.
- `src/autom8_asana/dataframes/section_persistence.py` — thread the write decision / prior-good read into `write_final_artifacts_async` (:806) OR expose a prior-good read for the caller.
- `metrics/freshness.py` + the warmer/consumer rebuild gate — add the quality term to the rebuild decision (NOT to `FreshnessReport.stale` itself, which stays a pure age signal at :173); read `population_degraded` from persisted metadata.
- `src/autom8_asana/lambda_handlers/cache_warmer.py` — ensure the persisted `population_degraded` survives into the next warm's freshness consult.
- `src/autom8_asana/cache/integration/dataframe_cache.py` — carry `population_degraded` on the cache entry alongside the existing `build_quality` (THROUGHLINE §5 seam).
- TEST (new): `tests/unit/dataframes/builders/test_cure_recovery_fail_closed.py` (§7).
- No edits to: `post_build_population_receipt.py` internals, `null_number_recovery.py` internals, `durable_task_cache.py`, the FROZEN-4 allowlist.

## §9 Handoff Criteria

- [x] TDD covers both forks with exhaustive option enumeration + recommendation
- [x] Population-floor SSOT is the derivation source (G-PROPAGATE; no orphan flag)
- [x] Fail-closed fires on ACTIVE-subset floor-breach (G-DENOM; honest denominator)
- [x] Offer non-regression specified + asserted (PV-OFFER-INTACT)
- [x] FROZEN-4 / `_SANCTIONED_IO_TO_THREAD` untouched (PV-FROZEN)
- [x] Test contract: boto3-boundary fixture, RED/GREEN, mutation proofs
- [x] Reversibility: two-way door, additive
- [ ] Deploy soak-clear-gated (G-RUNG: ceiling = authored; ship after soak clear ~2026-06-18)
- [x] Affected-module list for D2
