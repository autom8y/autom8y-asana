---
type: review
artifact_role: capacity-review
slug: capacity-s4-rebuild-pr285
rite: thermia (co-seated, capacity-engineer)
scope_fold: "capacity-engineer FOLDS the systems-thermodynamicist concurrency-bound lens for this
  review (W4 folding pattern) -- the in-flight ceiling / fleet-bound derivation in §2 is normally
  systems-thermodynamicist's lens; it is produced here under the fold, not by a second dispatch."
date: 2026-07-29
author: capacity-engineer
status: proposed
subject:
  pr: 285
  title: "feat(substrate): build S4 rebuild stage-validate-swap (RC-E)"
  worktree: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s4
  files_reviewed:
    - src/autom8_asana/substrate/rebuild.py (620L, worktree)
    - tests/unit/substrate/test_rebuild.py (700L, worktree)
prod_touch: NONE (this PR; the finding scope reaches into S8's future prod-touching build via the
  named reference pattern this PR cites -- see §1)
consumes:
  - .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md (P10, lines 98-102)
  - .ledge/specs/TDD-substrate-v2.md (§4 Seam 3 lines 392-423; §11 C9/C12/C14 lines 612-702)
  - .ledge/handoffs/STAGED-wave2-dispatch-specs-2026-07-29.md (§S4 lines 120-129)
  - .know/scar-tissue.md
  - .ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md (line 76 -- "DEFECT-seam1 :76")
  - .ledge/reviews/ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13.md
env: "primary .venv (/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.venv) + PYTHONPATH shadow
  pointing at the worktree's src/ -- the worktree's own .venv has no pytest/mypy installed
  (12 entries in .venv/bin, python3.12 only), matching the same pattern S7's QA review recorded
  (QA-s7-harness-pr283-2026-07-29.md: 'worktree .venv is empty')."
verdict: GO-WITH-CONDITIONS
---

# CAPACITY REVIEW — S4 rebuild (PR #285): pacing, concurrency-bound & P10-budget fidelity

## Verdict: GO-WITH-CONDITIONS

The stage-validate-swap mechanism itself (C9/C12/C14, [H9], [H12], RC-E-4) is soundly built,
honestly dark, and verified two-sided (§Verification receipts). **prod_touch:NONE holds** — nothing
in this PR touches production. The GO is conditional because this primitive is chartered as "the
P10-safe channel every later prod-touch (S8/S11/S12) rides" (PR body; STAGED §S4 line 125-126), and
three of the five review questions resolve to **real, evidenced, currently-unaddressed gaps** that
will propagate into S8's live build if not fixed now — including a concrete defect in the *named
reference pattern* this PR's own docstring tells S8 to copy "exactly." None of the five conditions
in §Conditions require reopening PR #285's diff; all are S8-facing (or S4-additive-optional).

---

## Scope & method

Per dispatch, this review folds the systems-thermodynamicist's concurrency-bound lens (§2 is that
lens, produced here rather than via a second dispatch — noted per instruction). I read: `rebuild.py`
+ `test_rebuild.py` (worktree); `transport/adaptive_semaphore.py`, `transport/budget_allocator.py`,
`core/concurrency.py`, `core/retry.py` (primary checkout — the "G6 controllers"); TDD §4 Seam-3 +
§11; CHARTER P10; STAGED-wave2-dispatch-specs §S4; scar-tissue; and, because PR #285's own docstring
names it as the composition template, `tests/harness/substrate_gate/parity.py` (S7, PR #283,
already merged) plus the true v1 production path `transport/asana_http.py::AsanaHttpClient._request`.
I ran the test suite and mypy against the worktree's filled `rebuild.py` using the primary `.venv` +
a `PYTHONPATH` shadow (receipts in §Verification receipts).

---

## 1. Controller composition fidelity

**Fact, verified by direct read of `rebuild.py`'s import block (lines 65-98) and grep**: this PR
contains **zero** G6 controller wiring. `PacedAsanaFetcher` (rebuild.py:172-190) is a bare `Protocol`
with one abstract method; `test_rebuild.py`'s fetchers (`_FakeFetcher`, `_RaisingFetcher`,
`_GatedFetcher`, lines 139-161, 648-662) never import or touch `AsyncAdaptiveSemaphore`,
`BudgetAllocator`, or `RetryOrchestrator`. This is **honestly disclosed**, not a silent gap — the PR
carries the label verbatim: *"production PacedAsanaFetcher composes G6 (admit→AIMD→retry→gather)
against LIVE Asana with REAL section counts \| METHOD: deferred-to-S8-live-parity \| REASON:
prod_touch NONE this wave; creds expired..."*.

**Consequence**: review question 1 ("does the drawn fetcher actually ride AIMD + BudgetAllocator +
retry as v1's proven paths do") **cannot be graded against this PR's code** — the composing code
does not exist here. But the PR's own docstring (rebuild.py:21) and PR body assert a production
impl should compose G6 **"exactly as the S7 parity runner does."** That referent is not aspirational
— it is a concrete, already-merged file: `tests/harness/substrate_gate/parity.py::PacedLiveParitySource`
(PR #283, QA-GO'd 2026-07-29). I inspected it, since it is the de facto spec S8 will copy.

**Finding A (structural skeleton — PASS)**: `PacedLiveParitySource._paced_fetch_one`
(parity.py:174-182) composes the four primitives in the correct relative order: `floor_gate.admit()`
→ `semaphore.acquire()` → `retry.execute_with_retry_async()` → (outer) `gather_with_semaphore`
(parity.py:184-193). This matches [H11]'s mandate (TDD §4 line 414-415) and is a sound template at
the *ordering* level.

**Finding B (signal-blindness defect — BLOCKING for S8, not for this PR)**: within that composition,
`slot.reject()` is **never called** (grep-verified: zero hits for `reject` in the file; the only
AIMD-slot call is `slot.succeed()` at parity.py:181, fired once *after* `execute_with_retry_async`
returns). Compare the actual v1 proven path, `AsanaHttpClient._request` (asana_http.py:609-666): its
`while True:` retry loop re-enters `async with await semaphore.acquire() as slot:` **on every
attempt** (line 610, inside the loop) and explicitly calls `slot.reject()` on a 429 **before**
deciding whether to retry (line 634), so AIMD's multiplicative decrease fires on the actual signal.
`PacedLiveParitySource` instead acquires **one** slot, hands the *whole* multi-attempt retry sequence
to `RetryOrchestrator.execute_with_retry_async` (which classifies retry-ability via
`DefaultRetryPolicy._is_transient`, retry.py:246-273, entirely independent of the `Slot` object), and
only ever signals `succeed()` if the whole sequence eventually succeeds — or signals **nothing** if
it exhausts retries and raises (retry.py:719: `Slot` docstring confirms "if neither reject() nor
succeed() is called, the slot releases silently... no window adjustment occurs"). Net effect: **a
429 observed and retried through this composition is invisible to AIMD.** The window can only grow
(additive +1 per success, gated by grace/interval) and can never shrink in response to the one signal
it exists to react to. This is the precise shape of review question 1's named risk ("retries not
re-admitted... sidesteps admission") — confirmed present in the pattern this PR tells S8 to copy
"exactly," and not previously caught (grep of `QA-s7-harness-pr283-2026-07-29.md` for `reject`/`slot.`
turns up only unrelated RC-A-2 "REJECT-side test case" hits — the AIMD-blindness gap was not in
scope for that review, but this one is).

**Fix (condition, S8-facing — see §Conditions #1)**: either (a) pass the acquired `Slot` into the
retried operation so each internal attempt can call `slot.reject()`/`succeed()` per the actual
per-attempt outcome, or (b) move `semaphore.acquire()` **inside** the retried unit (re-acquire fresh
per attempt, mirroring `_request`'s inline loop) rather than wrapping the whole retry sequence in one
acquire.

---

## 2. Concurrency bounds — the ceiling formula (folded thermodynamicist lens)

`rebuild.py` itself introduces **zero** additional fan-out. `_rebuild_once` (rebuild.py:434-470)
calls `fetch.fetch(aid)` **exactly once** per rebuild attempt (line 442) — not a loop, not a gather.
The CAS-retry loop in `_publish` (`max_cas_retries=8`, line 411/488) never re-invokes `fetch`; it only
re-reads the S3 pointer and retries the swap — an **S3-side** bound, not an Asana-request amplifier.
The only concurrency-shaping device in this PR is [H12] single-flight (`LocalSingleFlight`,
rebuild.py:344-370): it collapses **concurrent same-`ArtifactId`** rebuild calls to one execution
(proven two-sided by `test_single_flight_coalesces_concurrent_rebuilds`, line 665), but "distinct
keys proceed independently" (docstring, line 347) — **zero cross-artifact protection**.

**Per-rebuild ceiling** (worst-case concurrent Asana requests inside ONE `fetch.fetch(aid)` call,
once S8 builds the concrete fetcher on the Finding-A skeleton):

```
ceiling_per_rebuild = min(S_aid, G, C_aimd)
```

- `S_aid` = sections requiring re-fetch for artifact `aid` (a probe-decided, data-dependent count —
  **not** a code constant; explicitly UV-P'd in the PR body as "REAL section counts ride to S8";
  the test corpus uses 1-2 named sections, which is a fixture convenience, not a production estimate).
- `G` = the local `gather_with_semaphore` fan-out width chosen at the (not-yet-built) per-section
  callsite. Module convention default is 10 (`concurrency.py:16`); existing callsites in this repo
  range 4-20 by purpose ("cache warming (20), watermarks (10), deltas (5), init actions (4), project
  enumeration (5)", concurrency.py:29-31) — this is a **design choice S8 makes**, not fixed today.
- `C_aimd` = the shared `AsyncAdaptiveSemaphore` ceiling — e.g. `read_limit` default **12**
  (`config.py:394`, env `ASANA_CONCURRENCY_READ_LIMIT`, lowered from 50 post-ROOT-1a) — **provided**
  the semaphore instance is the process-shared one used by the rest of the process's Asana traffic.

`S_aid` only ever appears as a `min()` operand, never a multiplier: the ceiling is **bounded
independent of section count** — more sections mean more sequential batches (~`S_aid / G`), not a
higher concurrent ceiling. This is a genuinely good property, **conditional** on `G` and `C_aimd`
being fixed values and the AIMD semaphore instance being truly shared across the artifact's internal
section fan-out (this holds for the Finding-A skeleton — `self._semaphore` is one field, constructed
once in `__init__`, reused by every coroutine `gather_with_semaphore` launches).

**Fleet bound** (S8 running K concurrent rebuilds across K distinct `ArtifactId`s — e.g. a sweep):
single-flight offers **zero** protection here (per its own docstring). So:

```
ceiling_fleet = K x min(S_aid, G, C_aimd)   IF each rebuild call gets an INDEPENDENT
                                              PacedAsanaFetcher / AIMD instance
ceiling_fleet =     min(S_aid, G, C_aimd)   IF all K rebuilds share ONE process-singleton
                                              PacedAsanaFetcher / AIMD instance (REQUIRED)
```

This is the exact shape of the already-ratified pythia hard condition PC-1 — *"Unified in-process
singleton limiter... unifying all ~55-57 `AsanaClient(` sites so no ephemeral bypass escapes the
cap"* (`budget_allocator.py:28-34`) — recurring one seam higher, at the `PacedAsanaFetcher`
construction site instead of the `AsanaClient` construction site. `K` itself is governed by S8's
dispatch fan-out (bounded above by tracked-project-count × `EntityType` registry size, currently
~a dozen entity types per project, per `core/types.py:13-38`; the live project count is an S8 input,
not fixed by this PR).

**This is the formula S8's budget must plug into**: S8 must (a) construct exactly **one**
`PacedAsanaFetcher` per process and inject that same instance into every `rebuild()` call regardless
of `K` (so the fleet ceiling stays at `min(S_aid, G, C_aimd)`, not `K x` that), and (b) size whatever
per-day budget it adopts (§3) against the realized per-rebuild ceiling × expected rebuilds/day, not
against `K` alone — `K` shapes the *rate* of budget consumption, not the *hard ceiling*, if (a) holds.

---

## 3. Per-day budget model

**Not parameterized, not consumable, not enforceable anywhere in the codebase today.** Evidence:

- `grep -rl "per_day|per-day|daily_budget|DAILY|requests_per_day" src/` → **zero hits**.
- `BudgetAllocatorConfig` (config.py:832-860) and `WarmerFloorGate` operate on a **60-second** window
  (`floor_window_seconds: int = 60`) — sized for cross-consumer contention within a minute (the F1a
  fleet-sharing problem: 11 principals splitting one 1500/60s bot-PAT budget, per
  `ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13.md:38-40`), not a calendar-day quota.
- `RetryBudget`'s `BudgetConfig.window_seconds` defaults to **60.0** (retry.py:116) — same story, a
  different subsystem (cascade-amplification prevention, not daily quota).
- `BudgetAllocator` is **explicitly, deliberately advisory / fail-open by design**: *"It is ADVISORY:
  it publishes a floor and telemeters overage; it never hard-blocks a request... every failure
  direction is FAIL-OPEN... never fail-closed"* (budget_allocator.py:14-15, 308-315). Even if S8
  repurposes `PublishedFloor`/`WarmerFloorGate` with `window_seconds=86400`, the mechanism would
  **still never refuse** — it would only telemeter overage (`observe_admission`,
  budget_allocator.py:418-458).
- `rebuild()`'s signature (`aid, fetch, validate`) takes **no** budget/cap parameter. The only
  refusal path this PR exposes is `FetchRefused` → `RebuildOutcome.FETCH_REFUSED` (rebuild.py:145-151,
  443-444) — a **refusal-capable hook** (good: rebuild.py correctly surfaces zero-writes on refusal),
  but the *decision* to refuse on daily-budget exhaustion has to be built entirely net-new inside
  whatever `PacedAsanaFetcher` S8 authors, including **cross-invocation persistence** — Lambda
  processes are short-lived, so neither `BudgetAllocator`'s nor `RetryBudget`'s in-process counters
  survive a cold start; a real per-day cap needs an external counter (S3/DynamoDB/Redis), which is
  out of scope for both this PR and the existing G6 stack.
- This is **not a fresh discovery** — it is a **carried, still-undischarged UV-P**. STAGED-wave2's
  own S2 entry-UV-P list already named *"incremental-rebuild API-budget model with real section
  counts"* as an open item at S2's entry gate (STAGED-wave2-dispatch-specs-2026-07-29.md:63-64); it
  is **still open** three sprints later at S4's exit. It should not be silently re-deferred a third
  time without a named owner and deadline (see §Conditions #3).

**429-banking sub-question** ("does a 429 feed AIMD *and* admission, or only one?"): in the
Finding-B composition, a 429 feeds **neither** (masked by retry; `BudgetAllocator.observe_admission`
is called from exactly one call site, `hierarchy_warmer.py:400`, and counts admitted *volume* per
lane, not 429 responses). In the *correct* v1 pattern (`asana_http.py`), a 429 feeds **AIMD only**
(`slot.reject()`) — `observe_admission` is deliberately "C-11-DECOUPLED" from AIMD/429 by design
(budget_allocator.py:240-246) and is not wired to fire on a 429 anywhere in the codebase. So: *at
best, only one of the two mechanisms reacts to a 429 today, and neither decrements a per-day budget.*

*Minor operational footnote*: `BudgetAllocator.warmer_floor_gate()` **constructs a new
`WarmerFloorGate`** on each call (budget_allocator.py:381-397), and the gate's token bucket **starts
empty** (`self._tokens = 0.0`, line 267). If S8's fetcher calls `warmer_floor_gate()` fresh per
rebuild/section rather than constructing it once and holding it, the floor stops modeling a
*sustained* rate and instead pays a full `1/rate` wait on every call — over-conservative, not a
leak, but worth naming so S8 reuses one gate instance for the process lifetime it's meant to guard.

---

## 4. Receipts (P10 evidence)

`RebuildResult = {outcome, version_id, built_from_live_at, detail: str}` (rebuild.py:128-141).
`FetchedSections = {frame, section_instants}` (rebuild.py:154-169). **Neither carries a
request-count, 429-count, retry-count, or budget-consumed field.** No usage receipt is emitted by
this PR consumable by S8's P10-budget evidence chain.

This gap is **in scope for S4, not S8**: the PR body itself states *"`RebuildResult` — filled
`{outcome, version_id, built_from_live_at, detail}` (S6 declined the field surface; `observe` never
referenced it)"* — i.e., this PR held field-surface design authority for `RebuildResult` and did not
add a usage-telemetry field. Given the mission statement for this sprint is explicitly "this
primitive IS the P10-safe channel," a receipt hook belongs here, even if every field in it stays
`None`/zero on the dark-build fake fetcher.

**Minimal receipt shape** (condition — additive, non-breaking; `RebuildOutcome`'s CLOSED 3-member
enum and the frozen `Rebuilder` signature are both untouched by this):

```python
@dataclass(frozen=True, slots=True)
class FetchTelemetry:
    requests_issued: int = 0
    http_429_count: int = 0
    retries_issued: int = 0
    sections_refetched: int = 0
    sections_reused: int = 0
```

threaded as an optional field on `FetchedSections` (populated by a real `PacedAsanaFetcher`, defaults
to zeros on the fakes/tests) and surfaced onto `RebuildResult` (a new optional field, or structured
content in `detail`). Land it now while the field surface is open (S4), or assign it to S8 as a
**named, non-optional** obligation — not left ambient for whichever sprint happens to touch the type
next.

---

## 5. Off-peak scheduling

**Clean — no blocker.** `rebuild()` takes no internal clock-gating beyond the injected `now`
callable, which `DefaultAcceptancePredicates.validate` uses **only** for the proof-well-formedness
checks (tz-aware, not-future, positive SLA — rebuild.py:306-324). There is no hardcoded call-time,
cron expression, or time-of-day branch anywhere in `rebuild.py`. S8 is free to schedule `rebuild()`
invocations off-peak; nothing in this PR constrains *when* it may be called.

---

## Verification receipts (this review)

```
$ PYTHONPATH=.../autom8y-asana-wt-w2-s4/src \
    /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.venv/bin/python -m pytest \
    tests/unit/substrate/test_rebuild.py -q
25 passed in 10.43s
```
(run from the worktree; the primary checkout's own `rebuild.py` is a 79-line frozen stub — collection
against 25 real C9/C12/C14/[H9]/[H12]/RC-E-4 tests would have errored at import if the wrong file had
loaded, so the pass count is a positive control that the worktree source was exercised.)

```
$ PYTHONPATH=.../autom8y-asana-wt-w2-s4/src \
    /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.venv/bin/python -m mypy --strict \
    src/autom8_asana/substrate/rebuild.py
Success: no issues found in 1 source file
```

Grep receipts: zero G6 imports in `rebuild.py`/`test_rebuild.py`; zero `slot.reject(` occurrences in
`tests/harness/substrate_gate/parity.py`; `observe_admission`/`register_client` called from exactly
one non-`budget_allocator.py` site each (`hierarchy_warmer.py:400`, `client.py:79`); zero
`per_day`/`daily`/`DAILY` hits under `src/`.

---

## Policy Decision Records

### PDR-1: Accept the dark-build UV-P deferral of G6 composition; condition the reference pattern
- **Context**: prod_touch:NONE this wave, creds expired, S4 is Protocol-boundary by design (RC-E-4).
- **Decision**: ACCEPT the deferral as structured (honest UV-P, Protocol correctly isolates the seam).
  CONDITION: the named reference pattern (`PacedLiveParitySource`) must have its AIMD signal-blindness
  (§1 Finding B) fixed, or explicitly disclaimed as "ordering-only, not signal-correct," before S8
  treats it as copy-exactly guidance.
- **Theoretical basis**: [H11] paced-fetch delegation (TDD §4 line 414); AIMD congestion-control
  requires the reject signal to reach the window (adaptive_semaphore.py:1-20 module doctrine).
- **Trade-off**: none for this PR; defers the fix cost to S8, where it belongs given prod_touch.

### PDR-2: Require process-singleton `PacedAsanaFetcher` construction at S8
- **Context**: [H12] single-flight only dedupes same-`ArtifactId`; K concurrent distinct-artifact
  rebuilds are otherwise unbounded by anything in this PR (§2).
- **Decision**: S8 MUST construct one `PacedAsanaFetcher` per process and share it across all
  concurrent `rebuild()` calls, extending the already-ratified PC-1 discipline one seam higher.
- **Theoretical basis**: pythia PC-1 (budget_allocator.py:28-34, ratified 2026-07-20).
- **Trade-off**: none identified — this is the same-cost, correct construction; the alternative
  (fresh-per-call) is strictly worse on every axis.

### PDR-3: Require a net-new, cross-invocation-durable per-day budget primitive at S8
- **Context**: charter P10 requires "a per-day API budget"; STAGED §S4 mission requires "per-day
  budget"; no G6 controller implements one (§3); this is a carried UV-P from S2's entry gate.
- **Decision**: S8 must build this net-new (S3/DynamoDB/Redis-backed counter with UTC-day
  granularity), not repurpose `BudgetAllocator` (60s window, advisory/fail-open by construction).
- **Theoretical basis**: CHARTER P10 (lines 98-102); STAGED §S4 (line 124 "per-day budget").
- **Trade-off**: added infra dependency (a durable counter store) vs. an honest daily cap; the
  alternative (advisory-only, as today) does not satisfy P10's "respect a per-day API budget."

### PDR-4: Require a minimal usage receipt (`FetchTelemetry`) landed at S4 or assigned to S8
- **Context**: `RebuildResult`/`FetchedSections` carry zero usage/429/retry counters (§4); S4 held
  field-surface authority for `RebuildResult` in this exact PR.
- **Decision**: add the additive `FetchTelemetry` shape now, or name S8 as the explicit, non-optional
  owner in the S4→S8 handoff — not left as an unassigned gap.
- **Theoretical basis**: R2 receipt-grammar discipline (per-item file:line anchors this review itself
  follows); P10 "leave a receipt."
- **Trade-off**: a small additive schema change now vs. a harder-to-retrofit gap once S8/S6-observe
  consumers exist against the current 4-field shape.

---

## Conditions for GO

1. **[S8, BLOCKING before S8 arms any live PacedAsanaFetcher]** Fix the AIMD signal-blindness in the
   composition pattern (§1 Finding B): thread `slot.reject()`/`succeed()` to the actual per-attempt
   outcome, not to the outcome of the whole retry sequence.
2. **[S8, BLOCKING before any K>1 concurrent-rebuild dispatch]** Construct `PacedAsanaFetcher` as a
   process singleton; inject the same instance into every `rebuild()` call (§2, PDR-2).
3. **[S8, BLOCKING before "respects a per-day API budget" can be claimed]** Build a durable,
   cross-invocation per-day budget counter; wire it to raise `FetchRefused` on exhaustion so
   `rebuild()` correctly surfaces `FETCH_REFUSED` (§3, PDR-3).
4. **[S4-or-S8, non-blocking for this PR, required before S8 closes its own P10 evidence gate]** Add
   `FetchTelemetry` (or equivalent) so a rebuild's request/429/retry counts are observable (§4, PDR-4).
5. **[Advisory, no owner assigned yet]** Confirm which `Lane` (WARMER/FAIR_SHARE/CLIENT_FELT) a
   rebuild-triggered fetch registers under — today's fair-share pool (1390/60s) is shared with ECS's
   normal serving traffic; an unbounded rebuild sweep in that lane could still crowd it out even with
   a correct per-day cap, since the per-day cap and the 60s fair-share pool are orthogonal budgets.

No condition requires reopening PR #285's diff to merge; all are named obligations for the S8 build
that composes the live `PacedAsanaFetcher`, or additive/optional for S4 while its field surface is
still open.
