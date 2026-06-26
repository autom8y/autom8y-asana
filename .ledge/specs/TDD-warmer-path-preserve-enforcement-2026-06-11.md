---
type: spec
status: proposed
name: warmer-path-preserve-enforcement
date: 2026-06-11
initiative: cure-recovery-path-hardening (warmer-path follow-up to #127)
evidence_grade: "[STRUCTURAL | MODERATE]"
extends: ".ledge/specs/TDD-cure-recovery-path-hardening-2026-06-11.md (#127, merged 7973c10a, deployed :509)"
throughline: ".ledge/specs/THROUGHLINE-integration-boundary-fidelity-2026-06-10.md (this gap is its textbook two-writer instance)"
heads:
  substrate_of_record: 7973c10a   # main, #127-deployed; the game-day RED ran against THIS, not branch HEAD
  authored_against: 7973c10a
  branch_head_authored_on: 3bbb9bc8   # cr3/gate2 — does NOT contain #127 (PV note below)
related_adr: ".ledge/decisions/ADR-warmer-path-preserve-enforcement-2026-06-11.md"
---

# TDD: Warmer-Path PRESERVE Enforcement — one gated write primitive, no orphan writer

## GRANDEUR ANCHOR

We close the warmer-path gap the game-day exposed — so a durable-read OUTAGE makes the
cure PRESERVE the last-good frame at **every** write site, not just the one a unit test
happened to cover. #127 proved the *decision* is correct (`decide_write` returns
PRESERVE on a wholesale outage and the builder honors it). This TDD proves the *decision
is enforced everywhere a `dataframe.parquet` can be written* — by converging the two
finalize writers onto **one gated write primitive** that no future sibling writer can
silently bypass.

## PV PREAMBLE — substrate-of-record correction (read first)

**Inversion caught during re-derivation (G-PROVE):** the checked-out branch is
`cr3/gate2-receiver-probe-and-durability` (HEAD `3bbb9bc8`). That branch **does NOT
contain #127** — `git grep -nw decide_write 3bbb9bc8 -- src/` returns NONE; the symbols
`WriteDecision`, `PRESERVE_PRIOR_GOOD`, `recovery_receipt`, `fail_closed_write` are
absent from the working tree. #127 lives on **`main` (`7973c10a`)**, which is the
DEPLOYED `:509` substrate the game-day ran against. The prompt's line numbers (752, 768,
773, 786, 825) match `7973c10a` **exactly** and do not match the working tree. **All
file:line anchors in this TDD are against `7973c10a`** (the deployed truth). The
implementing engineer MUST branch from / rebase onto a base that contains #127 (a
`main` descendant), NOT `cr3/gate2`. This is recorded as Risk R-0 and as the first
implementation pre-condition.

## Context

- **Extends:** #127 (`TDD-cure-recovery-path-hardening`, `ADR-cure-recovery-path-hardening`),
  merged `7973c10a`, deployed `:509`. #127 introduced the pure decision helper
  `fail_closed_write.decide_write(...)` and wired it into the progressive builder's
  Step-6 finalize (`_finalize_artifacts_write_async`). That gate is GREEN — the builder
  honors PRESERVE by skipping its OWN write.
- **The game-day RED (deploy-empirical, 2026-06-11, on `:509`/`7973c10`):** under a
  revoked `S3DurableTaskCacheRead` grant, the cure logged
  `fail_closed_write_preserve_prior_good` (PRESERVE *decided*) at 11:34:47.383Z, yet the
  unit frame was persisted **0/3021** with `index_written:false` at 11:34:47.626Z
  (243 ms later). The decision was made but **NOT enforced at the operative write site**.
  Full case: `.ledge/handoffs/HANDOFF-releaser-to-10x-dev-gameday-RED-warmer-preserve-gap-2026-06-11.md`.
- **The throughline this is a textbook instance of:**
  `THROUGHLINE-integration-boundary-fidelity-2026-06-10.md` §1 — the #127 test stubbed
  *one* finalize path (the builder); the warmer's operative writer was never exercised.
  "Cover BOTH finalize paths, or assert they converge on one gated write." This TDD
  chooses **converge**.

## Root cause (the two-writer split) — re-derived, pasted file:line @ 7973c10a

The system has **two distinct finalize writers** for a `dataframe.parquet`, and #127
gated only the first:

1. **Writer A — builder finalize (GATED, works):**
   `dataframes/builders/progressive.py:650 _finalize_artifacts_write_async` runs the cure
   (`:713 recover_null_number_cells`), the population receipt (`:727
   post_build_population_receipt`), then `:752 decision = decide_write(...)`. On
   `WriteDecision.PRESERVE_PRIOR_GOOD` it logs `:773 fail_closed_write_preserve_prior_good`
   and **early-returns at `:786`**, *skipping its own* `:814 write_final_artifacts_async`.
   This is correct. BUT it still RETURNS the degraded `merged_df` inside `_FinalizeResult`
   (`:790`), and `build_progressive_async` puts that degraded frame onto
   `BuildResult.dataframe` (`:1075 dataframe=merged_df`). **The `WriteDecision` is computed,
   stored on `_FinalizeResult.decision` (`:96`), and then discarded** — `BuildResult`
   (`builders/build_result.py:107`) has NO `decision` / `write_decision` field
   (fields: `status, sections, dataframe, watermark, project_gid, entity_type,
   total_time_ms, fetch_time_ms, sections_probed, sections_delta_updated` — verified
   `build_result.py:136-145`). The decision dies inside the builder.

2. **Writer B — warmer/put_async finalize (UNGATED, the bug):**
   - `cache/dataframe/warmer.py:403` `df, watermark = await build_method(project_gid, client)`
     where `build_method` is `strategy._build_dataframe` (`warmer.py:392`).
   - `strategy._build_dataframe` → `services/universal_strategy.py:1171` → `:1228
     _build_entity_dataframe` → `:1248 result = await builder.build_progressive_async(resume=True)`
     → `:1249 df = result.dataframe`. **It extracts the bare degraded frame and returns
     `(df, watermark)` — the `WriteDecision` is NOT on `result` to extract.**
   - `warmer.py:418` then **unconditionally** `durable = await self.cache.put_async(
     project_gid=..., entity_type=..., dataframe=df, watermark=watermark)` — note it
     passes NO `population_degraded`, NO `population_min_rate`, NO `build_result`,
     despite `integration/dataframe_cache.py:618 put_async` accepting all three.
   - `integration/dataframe_cache.py:706 progressive_tier.put_async(cache_key, entry)`
     → `cache/dataframe/tiers/progressive.py:212 put_async` → `:239
     write_final_artifacts_async(... index_data=None ...)`. **`index_data=None` is the
     exact `index_written:false` signature from the game-day receipt.**
   - `dataframes/section_persistence.py:760 write_final_artifacts_async` →
     `:790 save_dataframe(...)` **UNCONDITIONALLY**. The function contains ZERO
     `WriteDecision` / `decide_write` / PRESERVE references (grep-confirmed).

So: the builder PRESERVES on disk (skips Writer A), hands the degraded frame back, and
the warmer **re-writes it via Writer B**. The gate guards one of two writers.

## Complete write-path map — EVERY parquet-write site, gated/ungated @ 7973c10a

Enumerated by `git grep -n "save_dataframe\|write_final_artifacts_async\|put_async" 7973c10a -- src/`
and tracing each to the physical `save_dataframe` primitive. The bug is "gate guards one
of N writers" — here is all N.

| # | Write site (file:line @7973c10a) | Reaches `save_dataframe` via | Gated by #127? | Notes / blast |
|---|----------------------------------|------------------------------|----------------|---------------|
| W1 | `builders/progressive.py:814 write_final_artifacts_async` (Step-6, inside `_finalize_artifacts_write_async`) | direct → `section_persistence:790` | **YES (GATED)** | The working #127 gate. PRESERVE → early-return `:786` skips this. Do NOT regress. |
| W2 | `builders/progressive.py:661 write_final_artifacts_async` | direct → `section_persistence:790` | partial — this is the *no-sections honest-empty* branch *inside* the gated method's neighborhood | Honest-empty path; population receipt is no-op for 0-row (`assessed=False`) → `decide_write`→`WRITE_AS_IS`. Benign, but funnels through the same primitive under convergence. |
| **W3** | `cache/dataframe/tiers/progressive.py:239 write_final_artifacts_async(index_data=None)` | direct → `section_persistence:790` | **NO (UNGATED) — THE BUG** | The operative WARMER writer. Driven by `warmer.py:418 put_async`. `index_data=None` → `index_written:false`. |
| W4 | `api/preload/legacy.py:283 save_dataframe(updated_df)` | direct → `section_persistence/storage:725` | **NO (UNGATED)** | Receiver legacy preload, INCREMENTAL-delta branch (`was_incremental`). Writes a delta-merge of an *existing good* frame — NOT a cure-recovery rebuild; does not pass through `decide_write`. Lower risk (no wholesale-outage signal in scope) but still an orphan `save_dataframe`. See §Receiver finding. |
| W5 | `api/preload/progressive.py:584 save_dataframe(s3_df)` | direct → `storage:725` | **NO (UNGATED)** | Receiver progressive preload, CASCADE self-heal re-persist (`rows_corrected > 0`). Additive (adds resolved cascade fields to a loaded S3 frame); not a cure-recovery rebuild. Lower risk; orphan `save_dataframe`. See §Receiver finding. |
| W6 | `api/routes/admin.py:330 put_async(df)` (after `:329 build_progressive_async`) | `put_async` → tiers `:239` → `section_persistence:790` | **NO (UNGATED)** | Admin manual rebuild. SAME two-writer pattern as the warmer: extracts `build_result.dataframe` (degraded on PRESERVE) and `put_async`-writes it bare. A second victim of the split. |
| W7 | `cache/dataframe/decorator.py:222 put_async(df)` (@dataframe_cache) | `put_async` → tiers `:239` → `section_persistence:790` | **NO (UNGATED)** | Request-path decorator cache fill. Bare `put_async`. Lower live-frequency for the bulk entities but structurally identical orphan. |
| — | `section_persistence.py:790 save_dataframe` | (the physical write) | — | **The single choke point.** Every W above terminates here (W4/W5 via the storage primitive directly; W1/W2/W3/W6/W7 via `write_final_artifacts_async`). This is where convergence lands. |
| — | `dataframes/storage.py:725 save_dataframe` (S3DataFrameStorage) | physical S3 PUT | — | Lowest primitive; already accepts `population_degraded`/`population_min_rate` (FORK-2 sidecar). `section_persistence.save_dataframe` is the in-process wrapper above it. |
| — | `section_persistence.py:852 save_section` (checkpoint) | mid-fetch section parquet | N/A | NOT a final `dataframe.parquet`; writes per-section checkpoints. Out of scope (not a cure-recovery final artifact). Named for completeness. |

**Count:** 7 final-frame write sites (W1–W7). #127 gated **1** (W1). **W3 is the live
warmer bug; W6 is the admin twin; W7 the decorator twin.** W2 is benign-honest-empty.
W4/W5 are receiver preload orphans NOT on the cure-recovery rebuild path (see below).

### Receiver finding (PV item 3) — W4/W5 are NOT the live cure-recovery face, but ARE ungated

The prompt asked whether the receiver/preload paths (legacy:285, progressive:584) are
also ungated, and to re-scope if so. **They are ungated, but they are NOT the same defect
class as W3:**

- **W4 (legacy:283)** fires only on the `was_incremental` delta-merge branch — it persists
  an incremental delta applied to an *already-good* loaded frame. The full-rebuild branch
  in legacy preload goes through `build_progressive_async` (`legacy.py:504,611`) → Writer A
  (gated). W4 never runs the cure on a wholesale-outage rebuild; there is no `WriteDecision`
  in scope to honor.
- **W5 (progressive:584)** fires only on `cascade_result.rows_corrected > 0` — a cascade
  self-heal that ADDS resolved parent-link fields to a loaded S3 frame. It is additive,
  not a fresh degraded build.

**Disposition:** W4/W5 do not reproduce the game-day RED (no cure / no below-floor
freshly-nulled frame). They are, however, structurally ungated `save_dataframe` callers.
Under the recommended convergence (Option b), W4/W5 inherit the impossible-by-construction
guard (Option c, the typed wrapper) for FREE — any below-floor frame without a recorded
WriteDecision raises. They do NOT require the decision-threading work (Options a/b core);
they require only that they route through the gated primitive. This is the
**re-scope**: W3 (+ W6, W7) are the threading targets; W4/W5 are guard-coverage-only.

## System Design — the converged write primitive

### Architecture (before → after)

```
BEFORE (#127 — gate at Writer A only):
  build_progressive_async
    └─ _finalize_artifacts_write_async
         ├─ decide_write() ──► PRESERVE ──► early-return (skip W1)   [GATED ✓]
         └─ returns _FinalizeResult{ merged_df (DEGRADED), decision } 
              └─ BuildResult{ dataframe = DEGRADED }  ◄── decision DROPPED here
  warmer.put_async(df=DEGRADED)  ──► tiers.put_async ──► W3 save_dataframe  [UNGATED ✗]

AFTER (convergence — gate at the ONE primitive every writer passes):
  build_progressive_async ─┐
  admin rebuild ───────────┤  all carry the WriteDecision (or a below-floor frame
  decorator ───────────────┤  with no decision → guard raises)
  warmer ──────────────────┘
                           ▼
            gated_write_final_artifacts(df, decision|None, population_receipt,
                                        prior_good_loader)  ◄── ONE gate
                           ▼
            section_persistence.save_dataframe   (physical write — reached ONLY
                                                   through the gate)
```

### Components

| Component | Responsibility | Change |
|-----------|----------------|--------|
| `fail_closed_write.decide_write` | Pure PRESERVE/COALESCE/WRITE decision | **UNCHANGED** (do not touch the #127 helper) |
| `WriteDecision` (return-carry) | Thread the decision from builder → caller | **NEW**: add `write_decision` (+ `population_degraded`/`population_min_rate`) to `BuildResult` so the warmer/admin can read what the builder decided |
| `BuildResult` (`build_result.py:107`) | Aggregate build outcome | **EDIT**: add `write_decision: Any = None` field (Any to avoid import cycle, mirroring `_FinalizeResult.decision:96`) |
| `build_progressive_async` (`progressive.py:878`) | Populate `BuildResult.write_decision` from `finalize.decision` | **EDIT**: pass `finalize.decision` into the `BuildResult` factory |
| `universal_strategy._build_entity_dataframe` (`:1228`) | Today returns bare `df` | **EDIT**: return the decision alongside (see Option-b threading) OR funnel its `put_async` through the gate |
| **`SectionPersistence.write_final_artifacts_async`** (`section_persistence.py:760`) | The convergence point | **CORE EDIT**: accept the decision + receipt context; skip `save_dataframe` on PRESERVE; COALESCE on WRITE_COALESCED; **refuse** a below-floor frame with no recorded decision (Option c guard) |
| `tiers/progressive.py:put_async` (`:212`) | Warmer's delegate | **EDIT**: thread `entry`'s population/decision metadata into `write_final_artifacts_async` instead of dropping it (`index_data=None` stays for the index-laziness reason, unrelated) |
| `warmer.py:_warm_entity_type_async` (`:418`) | The orphan caller | **EDIT**: pass the build's decision/population through `put_async` (which already accepts them) |

### The gate's information problem (PV item 4) — what `put_async` has vs needs

`put_async` (and `write_final_artifacts_async`) has: `df`, `entity_type`, `watermark`. It
LACKS the **`recovery_receipt`** — the wholesale-outage signal `decide_write` needs to
distinguish PRESERVE from WRITE_COALESCED. Therefore the primitive **cannot fully
re-decide alone**. Two ways to give it what it needs (the design choice between Options
a/b is exactly this):

- **Thread the decision in** (carry the already-computed `WriteDecision` from the builder
  that DID have the receipt) — chosen. The builder computed it correctly at `:752`; we
  stop discarding it.
- **Re-derive a cheaper signal** in the primitive (e.g. "df active-subset is below floor
  AND a strictly-better prior-good exists on disk") — viable as the *guard* (Option c)
  but cannot distinguish PRESERVE from COALESCE without the heal count. Used only for the
  fail-loud assertion, not for the full re-decision.

## Fix Option Table (exhaustive — @option-enumeration-discipline)

| Opt | Mechanism | Pros | Cons | Verdict |
|-----|-----------|------|------|---------|
| **(a) Propagate the decision to the warmer caller** | Carry `WriteDecision` on `BuildResult` → `_build_entity_dataframe` returns `(df, decision)` → warmer SKIPS `put_async` on PRESERVE, COALESCEs on WRITE_COALESCED | Minimal blast; localized to warmer + 3 return shapes; no primitive change | Leaves TWO writers — gate now at the warmer *caller*, not the primitive. W6/W7 each need the SAME patch. A future sibling caller is silently ungated again. Violates G-PROPAGATE (one gated primitive, no per-path orphan). | Rejected as sole fix — it is the *symptom-local* form #127 already is, just moved one node. |
| **(b) Converge onto ONE gated write primitive** | `write_final_artifacts_async` becomes the single gated funnel: accepts `(df, write_decision, population_receipt, prior_good_loader)`; honors `decide_write` at the ONE place every parquet write passes. Builder, warmer, admin, decorator all route through it. | No future sibling writer can be silently ungated — the gate is at the choke point (`section_persistence:790` is reached ONLY through it). Composes with #127 (the builder still early-returns; the primitive's gate is idempotent w.r.t. that). G-PROPAGATE satisfied. | `put_async` lacks `recovery_receipt` → must thread the decision in (combine with the *carry* half of (a)). Larger surface (5 call-sites touched). | **RECOMMENDED (core).** |
| **(c) Impossible-by-construction guard** | A typed assertion at the primitive: "a below-floor frame (population_receipt.below_floor) arriving with NO recorded WriteDecision" RAISES (or refuses + logs `ungated_below_floor_write_refused`). | Makes an ungated degraded write a LOUD failure, not a silent degrade. Catches W4/W5 + any future writer for free. Cheap. | Alone it only fail-LOUDS; it does not PRESERVE (it would turn the bug into a 503/error rather than serving last-good). Needs (b) to also DO the right thing. | **RECOMMENDED (companion to b).** The guard is the backstop; (b) is the behavior. |
| (d) Move the gate DOWN into `decide_write`'s caller-set by making `decide_write` a decorator on `save_dataframe` | `save_dataframe` itself refuses below-floor writes | Lowest possible choke (storage primitive) | `save_dataframe` is also used for checkpoints (`save_section` is separate, but storage-level coupling risks the cascade self-heal W5 and honest-empty W2 mis-firing); too low — loses the entity/receipt context cleanly available one layer up; couples a pure-ish storage primitive to cure semantics | Rejected — wrong altitude; `section_persistence.write_final_artifacts_async` is the correct choke (it already owns the "final artifact" semantic; checkpoints use a different method). |
| (e) Per-entity sidecar "do-not-overwrite" lock file | Builder writes a PRESERVE marker; writers check it | Decouples writers entirely | Adds durable state + a new failure mode (stale lock strands a project); racy across the single uvicorn worker's concurrent warms; over-engineered | Rejected — introduces more failure surface than it removes. |

### Recommendation: (b) + (c), with the *carry* half of (a) as the threading mechanism

**(b) is the behavior, (c) is the backstop, (a)'s carry is how (b) gets its input.**

Concretely:
1. **(a)-carry:** add `write_decision` (+ `population_degraded`, `population_min_rate`) to
   `BuildResult`; `build_progressive_async` populates it from `finalize.decision` /
   `finalize.population_receipt`. `_build_entity_dataframe` returns the decision context to
   the warmer (today it drops it). This stops the discard.
2. **(b)-converge:** `write_final_artifacts_async` accepts an optional
   `write_decision: WriteDecision | None` and a `prior_good_loader` callback. When
   `write_decision is PRESERVE_PRIOR_GOOD` it SKIPS `save_dataframe` (and returns the
   honest "preserved, not written" boolean per VG-001 semantics — see §Reliability). When
   `WRITE_COALESCED`, it coalesces against the prior-good before writing. Builder Writer A
   *also* routes through this (it can pass `write_decision=WRITE_AS_IS` since it already
   early-returned on PRESERVE — idempotent, no regression). Warmer (W3), admin (W6),
   decorator (W7) all now pass the carried decision.
3. **(c)-guard:** inside `write_final_artifacts_async`, if `population_degraded is True`
   (a below-floor frame) AND `write_decision is None` (no recorded decision threaded),
   the primitive **refuses the parquet save** and logs
   `ungated_below_floor_write_refused` — converting any *future* orphan into a loud,
   last-good-preserving refusal rather than a silent 0/N degrade. W4/W5 inherit this.

## How it composes with #127 WITHOUT regressing the builder path (G-RUNG / non-regression)

- The builder's Step-6 PRESERVE early-return (`progressive.py:786`) **stays**. The builder
  continues to NOT call `write_final_artifacts_async` on PRESERVE. The convergence gate is
  therefore **never even reached** on the builder's PRESERVE path — there is zero behavior
  change for Writer A's PRESERVE case. (Idempotent: the builder gate and the primitive gate
  agree; the primitive gate is a *second* line of defense, not a replacement.)
- For Writer A's WRITE_AS_IS / WRITE_COALESCED cases, the builder already coalesces and
  writes via `:814`; under convergence it passes `write_decision=<the decision it made>`
  to the primitive, which then performs the SAME save it does today (the COALESCE having
  already been applied in the builder for that path — the primitive does NOT double-coalesce;
  it coalesces only when handed a non-coalesced frame + WRITE_COALESCED, which is the
  warmer's case). **Design note:** to avoid double-coalesce, the builder passes
  `write_decision=WRITE_AS_IS` for the frame it ALREADY coalesced (the frame is now
  >= prior-good, so WRITE_AS_IS is honest), OR the primitive's coalesce is null-cell-only
  (idempotent — re-coalescing an already-full frame is a no-op per
  `coalesce_prior_good`'s `pl.when(is_null)` semantics, `fail_closed_write.py:coalesce_prior_good`).
  The latter (idempotent coalesce) is the safer composition and is RECOMMENDED — it makes
  the primitive's behavior independent of which caller fed it.
- The existing #127 test `test_cure_recovery_fail_closed.py` (builder finalize) stays GREEN
  — it exercises Writer A, untouched.

## NFR-3 — offer-path symmetry + safety

`_VALUE_COLUMNS_BY_ENTITY = {"offer": ("mrr", "offer_id"), "unit": ("mrr",)}`
(`post_build_population_receipt.py:60`). The gate is **per-entity** by construction:
`decide_write` consumes THIS entity's `population_receipt` and THIS entity's prior-good
frame; `prior_good_loader` reads `load_dataframe(project_gid, entity_type=<this entity>)`.
A unit-frame PRESERVE can NEVER touch the offer frame (different entity key, different
prior-good read). The convergence primitive preserves this — it receives the entity's own
decision; it does not cross entities. The warmer warms entities in a loop
(`warmer._warm_entity_type_async` per entity_type); each iteration carries its own
decision. **Offer is symmetric and isolated** — when the offer warm hits a wholesale
outage it PRESERVES the offer frame exactly as unit does, and unit's outage cannot
degrade offer. (Game-day receipt confirms: "Offer frame untouched throughout.")

## G-DENOM — honest ACTIVE-subset floor

The floor is computed by `post_build_population_receipt` over the ACTIVE/ACTIVATING subset
(`_active_subset`, `_ACTIVE_ACTIVITY_VALUES = {"active","activating"}`). The convergence
primitive does NOT re-derive a denominator — it CONSUMES the receipt's `below_floor` /
`min_rate` verdict (same as `decide_write` does). No new denominator is introduced; the
honest active-subset floor is preserved end-to-end. `prior_good_active_nonnull`
(`fail_closed_write.py`) re-applies the IDENTICAL `_active_subset` to the prior-good frame
for the apples-to-apples comparison — that parity is unchanged.

## FROZEN / FROZEN-4 — no new `to_thread`

The convergence adds NO new `asyncio.to_thread` site. The prior-good read reuses the
existing `_load_prior_good_frame` (`progressive.py`, which uses
`persistence.storage.load_dataframe` — an existing seam, no new thread). The
`prior_good_loader` passed to the primitive is a thin async callback over that SAME seam.
FROZEN-4 (concurrency regression guard, `test(dataframes)` b4c090e4) is untouched —
the gate is a pure decision + a skipped/redirected write, no new offloaded CPU work.

## Test Contract (mandatory, per THROUGHLINE §1/§4)

### The WARMER-PATH broken-grant fixture (RED on today's `7973c10a`)

**Module:** `tests/integration/cache/test_warmer_preserve_enforcement.py` (NEW —
integration altitude; the existing `tests/unit/dataframes/builders/test_cure_recovery_fail_closed.py`
covered the BUILDER finalize ONLY).

**What it drives (the real warmer store path, NOT a re-implementation):**
`warmer._warm_entity_type_async(entity_type="unit", project_gid=<canonical>, client)`
→ `strategy._build_dataframe` → `build_progressive_async` → `_build_entity_dataframe`
→ `cache.put_async` → `tiers/progressive.put_async` → `write_final_artifacts_async`
→ `save_dataframe`. Every layer is the REAL code path.

**The boundary stub (THROUGHLINE §4 step 1 — stub ONLY the lowest client boundary):**
the `boto3` S3 client's `get_object` raises `ClientError` with
`{"Error": {"Code": "AccessDenied"}}` for the durable per-task cache prefix
`asana-cache/tasks/<gid>/task.json` (the revoked `S3DurableTaskCacheRead` grant — the
EXACT shape and key the game-day revoked). The `dataframe.parquet` prefix
(`asana-cache/dataframes/.../unit/dataframe.parquet`) is readable and SEEDED with a
prior-good frame (mrr non-null for the active subset, e.g. 723/3021 — the game-day
prior-good count). REAL `DataFrameCacheEntry` / `PopulationReceipt` /
`NumericRecoveryReceipt` shapes; REAL keys; exact-key assertions (THROUGHLINE §4 steps 2-3).

**The content assertion (THROUGHLINE lesson — assert by FRAME CONTENT, never the log):**
after the warm under the revoked grant, load the persisted frame via the unit's OWN
read path (`persistence.storage.load_dataframe(project_gid, entity_type="unit")`) and
assert:
- `active-subset count(mrr non-null) == prior_good_count` (e.g. 723), **NOT 0**.
- the persisted frame is byte-identical (or count-identical on the value column) to the
  seeded prior-good — i.e. PRESERVE was *enforced*, the degraded 0/3021 frame was NOT
  written.
- **Explicitly do NOT** assert on the `fail_closed_write_preserve_prior_good` log line —
  the game-day proved that log FIRED while the write degraded. The log is necessary but
  NOT sufficient evidence. Content is the only honest oracle.

**The inline behavioral baseline (proves the test is load-bearing — the mutation proof):**
a sibling `test_BASELINE_warmer_ungated_persists_degraded` that runs the SAME fixture
against the CURRENT (pre-fix) warmer write path and asserts the persisted frame is
**0/3021** (the bug). This baseline is RED-after-fix (it documents what the bug WAS) and
is the mutation proof: revert the gate and the primary test goes RED, the baseline goes
GREEN. Per the #127 test's own `test_BASELINE_*` convention (`test_cure_recovery_fail_closed.py`
docstring RED-1).

**The mutation that proves it load-bearing:** delete the `write_decision is
PRESERVE_PRIOR_GOOD → skip save_dataframe` branch in the convergence primitive (or revert
the warmer's decision-threading so `put_async` is called bare). The primary assertion
(`count(mrr)==723`) MUST flip to `0/3021`. If the test stays GREEN under that mutation,
the test is theater (it is asserting on the log or on a stubbed-above-boundary stand-in).

**Layer-4 (THROUGHLINE §4 step 4 — un-unit-testable):** the runtime-principal grant
assertion (the warmer's IAM role can/cannot read the tasks prefix) is NOT unit-assertable;
it is the **deploy-gate / re-game-day** forcing function owned by the releaser seam
(G-RUNG — this TDD's ceiling is *authored + tested in-process*; the live re-game-day on
the re-deployed substrate earns the `self-heal-game-day-proven` rung).

### Offer-symmetry test (NFR-3)

`test_warmer_preserve_offer_isolated`: revoke the durable grant during an OFFER warm with
a prior-good offer frame; assert the offer frame is PRESERVED (count(mrr) and
count(offer_id) == prior-good) AND that a concurrently-good unit frame is untouched.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| R-0: implementing on `cr3/gate2` (no #127) | H if unguarded | H (builds on absent base) | Pre-condition #1: branch from a `main` descendant containing `7973c10a`; CI grep-asserts `decide_write` present before the fix lands. |
| R-1: double-coalesce (builder coalesces, primitive re-coalesces) | M | M (no data harm — null-cell-only coalesce is idempotent, but wasteful) | Make the primitive's coalesce null-cell-only (idempotent per `coalesce_prior_good`); builder passes WRITE_AS_IS for already-coalesced frames. |
| R-2: PRESERVE-skip changes the VG-001 durability boolean | M | M (a skipped write must not present as a non-durable FAILURE, nor as a false SUCCESS that resets the breaker) | Define a distinct return contract: PRESERVE returns `True` (the last-good frame IS durable — it's on disk) but does NOT stamp freshness/manifest (mirrors #127 builder semantics `:768`). Document in §Reliability. |
| R-3: guard (c) over-fires on honest-empty W2 | L | M (refusing a legit empty write → 503 trap) | Guard predicate gates on `population_degraded is True` specifically; honest-empty has `assessed=False`→`below_floor=False`→`population_degraded` falsy → guard does not fire. |
| R-4: W4/W5 receiver paths regress under guard | L | M | W4/W5 frames are not below-floor (good loaded frames + additive merges) → `population_degraded` falsy → guard passes them through unchanged. Covered by a receiver-preload regression test. |
| R-5: branch HEAD `cr3/gate2` diverges from `main` at these files | M | M | Rebase-onto-main pre-condition; re-derive line anchors post-rebase (they will shift; the SEMANTICS are the contract, not the integers). |

## Affected-module list (for D2 / principal-engineer)

Authored against `7973c10a`; **line numbers will shift after rebase-onto-main — treat the
function/symbol names as the contract, not the integers.**

1. `src/autom8_asana/dataframes/section_persistence.py` — `write_final_artifacts_async`
   (`:760`): accept `write_decision` + `prior_good_loader`; PRESERVE-skip; WRITE_COALESCED;
   guard (c). **CORE.**
2. `src/autom8_asana/dataframes/builders/build_result.py` — `BuildResult` (`:107`): add
   `write_decision` (+ `population_degraded`/`population_min_rate`) fields; update
   `from_section_results`.
3. `src/autom8_asana/dataframes/builders/progressive.py` — `build_progressive_async`
   (`:878`, the `BuildResult` construction ~`:1075`): populate `write_decision` from
   `finalize.decision`. Builder Step-6 early-return (`:786`) UNCHANGED.
4. `src/autom8_asana/services/universal_strategy.py` — `_build_entity_dataframe` (`:1228`):
   return the decision context (not bare `df`); `_build_dataframe` (`:1171`) signature carry.
5. `src/autom8_asana/cache/dataframe/warmer.py` — `_warm_entity_type_async` (`:418`):
   pass the carried `write_decision`/`population_degraded`/`population_min_rate` into
   `cache.put_async` (which already accepts them, `:618`).
6. `src/autom8_asana/cache/dataframe/tiers/progressive.py` — `put_async` (`:212`): thread
   `entry`'s decision/population metadata into `write_final_artifacts_async` (`:239`).
7. `src/autom8_asana/cache/integration/dataframe_cache.py` — `put_async` (`:618`): pass the
   decision through to the tier (it already plumbs `population_degraded` to `BuildQuality`;
   add the `write_decision` pass-through).
8. `src/autom8_asana/api/routes/admin.py` — rebuild path (`:330`): pass the build's decision
   into `put_async` (W6 twin fix).
9. `src/autom8_asana/cache/dataframe/decorator.py` — `:222`: pass decision into `put_async`
   (W7 twin fix) OR rely on guard (c) as the backstop (decorator frames are request-path,
   rarely below-floor; guard-only is acceptable for W7 — engineer's call, documented).
10. `tests/integration/cache/test_warmer_preserve_enforcement.py` — NEW (the test contract).
11. (regression) a receiver-preload pass-through test confirming W4/W5 unchanged.

## ADRs

- `.ledge/decisions/ADR-warmer-path-preserve-enforcement-2026-06-11.md` — the convergence
  decision (Option b + c) and the FROZEN-grammar non-regression contract with #127.

## Open Items (resolved during implementation)

- O-1: idempotent-coalesce vs builder-passes-WRITE_AS_IS (R-1) — RECOMMEND idempotent coalesce.
- O-2: W7 decorator — thread-decision vs guard-only backstop. RECOMMEND guard-only (lower
  blast; decorator frames rarely below-floor) but document the choice.
- O-3: exact VG-001 return value on PRESERVE (R-2) — RECOMMEND `True` + no-freshness-stamp.
