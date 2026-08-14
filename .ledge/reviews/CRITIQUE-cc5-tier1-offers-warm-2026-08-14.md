---
type: review
artifact_type: adversarial-critique
artifact_id: CRITIQUE-cc5-tier1-offers-warm-2026-08-14
initiative: chain-of-custody-closure
wave: chain-of-custody-closure (Phase 2)
sprint: CC-5 PHASE-3 falsification
session: coc-phase-2
author: qa-adversary (10x-dev, co-seated; rite-disjoint from the builder seat)
date: 2026-08-14
status: draft
verdict: PASS-WITH-NARROWINGS
rung: rung-BUILT (unchanged — this critique attests the BUILT rung survives falsification; it buys no merge, no deploy, no AL-5 claim)
second_reads: BUILD-cc5-tier1-offers-warm-2026-08-14
self_assessment_cap: MODERATE
under_test:
  branch: coc-cc5-tier1-warm
  commit: 6b75279fcfb9e71c40766bf6bf5d037ca7766ba6
  worktree: .knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc5a
fixtures: OWN-BUILT (scratchpad qa_cc5/{qa_common,attack1..5}.py; builder fixtures NOT replayed except one baseline suite run)
aws_calls: 0
asana_calls: 0
git_write_verbs: 0
worktree_mutations: 0 (git status --porcelain empty post-run)
---

# CRITIQUE — CC-5 Tier-1 offers-only warm-path repair: PHASE-3 falsification

Adversarial second read of `BUILD-cc5-tier1-offers-warm-2026-08-14.md`. I shaped
none of the build. Every fixture below is my OWN construction (no polars; fake
DataFrame surface; per-entity coverage measured from **client call prefixes**,
never from the artifact-under-test's own receipt; BEFORE = the literal
origin/main module extracted via `git show`, not the env-lever emulation).
Per discriminating-canary doctrine, every RED is a broken/reverted **input**
(the real operator lever, an injected failing client, a zero budget, a cache
outage) — no defect was injected into production code (G-THEATER avoided).

## 0. Module-resolution verification (load-bearing, per setup warning)

The trap is REAL and was demonstrated before any leg:

- bare `python -c "import autom8_asana.lambda_handlers.story_warmer as m; print(m.__file__)"`
  → `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/.../story_warmer.py`
  (**MAIN tree** — a bare pytest grades the wrong code).
- `PYTHONPATH=$PWD/src` (exported, cwd = worktree) → same command →
  `.../wt.10x-dev.coc-phase-2.20260814T090131.cc5a/src/.../story_warmer.py` (worktree). exit 0.

Every attack script bakes the guard **into the interpreter under test**
(`qa_common.assert_worktree_resolution()` exits 3 unless
`story_warmer.__file__` is under the worktree `src/`), and printed
`RESOLUTION-OK: <worktree path>` on every leg. The baseline pytest leg ran the
same in-interpreter check immediately before invocation.

## 1. Verdict table

| # | Attack | Command (scratchpad `qa_cc5/`) | Exit | Verdict |
|---|--------|--------------------------------|------|---------|
| 1 | Own two-sided teeth | `attack1_two_sided_teeth.py` | 0 (`ATTACK-1 PASS`) | **PASS** |
| 2 | Tier-2 smuggle probe | `attack2_tier2_smuggle.py` | 0 (`ATTACK-2 PASS`) | **PASS — clean Tier-1** (displacement quantified, see §3) |
| 3 | Budget-neutrality falsification | `attack3_budget_edges.py` | 0 (`ATTACK-3 PASS`) | **PASS with NARROWING N-1, N-2** |
| 4 | Partial-pass honesty | `attack4_partial_honesty.py` | 0 (`ATTACK-4 PASS`) | **PASS** |
| 5 | CF-3 residual | `attack5_cf3_residual.py` | 0 (`ATTACK-5 PASS-AS-PROBE`) | **CONFIRMED-RESIDUAL with NARROWING N-3** |
| — | Baseline (builder suite, my hands) | `python -m pytest tests/unit/lambda_handlers/test_story_warm_priority_offer.py tests/unit/lambda_handlers/test_story_warming.py -q` | 0 (30 passed) | baseline green |

## 2. Attack 1 — own two-sided teeth: PASS

Own fixture: 4 entities × 130 tasks (2 chunks each), budget = 4 clean chunk
checks — a different shape from the builder's (3×200, budget 2).

- **RED** (honest revert lever `ASANA_STORY_WARM_PRIORITY_ENTITIES=""`, not a
  code defect): `offer.success == 0`, `enumerated == True`,
  `budget_exhausted == True` — the production starvation, reproduced.
- **GREEN** (default): `offer.success == 130`, `position == 0`.
- **Discriminator claim verified with my own numbers**: aggregate
  `stats["success"]` is **260 == 260** across legs; `total_tasks` 520 == 520;
  total Asana warm-call count **260 == 260** (request-neutral ordering).
- **The trap exists and the receipt closes it**: an aggregate-only assertion
  (`success == 260`) evaluates True on BOTH legs — i.e. it passes on the broken
  ordering. Only the per-entity offer receipt moves (0 vs 130). The builder's
  claimed discriminator is real, not fixture-specific.

## 3. Attack 2 — Tier-2 smuggle probe: CLEAN TIER-1

Own-hands code trace: the priority pass is keyed on entity name → caller's
`get_project_gid` (`story_warmer.py:141-145`, `:433`); the non-priority
remainder keeps its original relative cascade order (`story_warmer.py:147-151`).
The offers project GID literal appears **0 times** in the diff (`git diff
origin/main HEAD | grep -c 1143843662099250` → 0). Diff surface is exactly two
files; `timeout.py`, `cloudwatch.py`, `cache/integration/stories.py`,
`clients/stories.py` all empty-diff vs origin/main.

Executable quantification (16-entity fleet, offer at cascade position 5,
100 tasks each, starvation budget = 4 chunk checks; BEFORE = literal
origin/main module; coverage from client-call prefixes):

| Q | Result |
|---|--------|
| Q1 entities 6–16 (the other 11 starved entities) | coverage BEFORE == AFTER == **0 for every one** — no fleet coverage change |
| Q2 displacement | **exactly the cascade TAIL of entities 1–4**: e04 100→0, offer 0→100, e01–e03 untouched; displaced(100) == gained(100) |
| Q3 ordering | non-priority relative order preserved exactly; only offer hoisted |
| Q4 revert lever | `""` env → per-entity coverage dict **identical** to origin/main; faithful pre-CC-5 restore |
| Q5 sufficient budget (32 checks) | both orderings warm all 16×100 = 1600 — displacement exists **only under starvation** |

**Ruling**: the change is genuinely offers-scoped in mechanism. The one fleet
effect is the disclosed entities-1–4 tail displacement (BUILD §2.2's "honest
cost"), now quantified: under starvation it costs exactly the LAST entity(ies)
of the old warm set exactly what offer gains, and it reverts without code
change. Entities 5–16 see zero behavior change (they also gain a log-only
receipt, which is observability, not warm behavior). **No Tier-2 smuggle.**
One fence observation (F-1, §7): the env lever *mechanism* generalizes to any
entity list — the Tier-1 fence is default-deep, not mechanism-deep.

## 4. Attack 3 — budget-neutrality falsification: PASS with narrowings

| Edge | Result |
|------|--------|
| E1 empty offers project (pop 0) | 0 offer Asana calls; totals BEFORE==AFTER (200 calls, 3 cache reads); receipt explicit `task_count=0, enumerated=True` |
| E2 offers GID unresolvable | `skip_reason=no_project_gid`; zero net-new calls of any kind; other entities' coverage unchanged |
| E3 offer absent from cascade AND cache | zero net-new **Asana** calls; net-new = exactly **1 DataFrame-cache read** (`project-offer`) — see N-2 |
| E4 budget exhausted at entry (0 clean checks) | **zero** Asana calls; exactly 1 timeout probe per enumerated entity (bounded); every receipt an explicit zero with `budget_exhausted=True` — the 120s early-exit is never blown, no work occurs past the wall |
| E5 emit_metric delta | BEFORE = 4 emits/run; AFTER = **8** — see N-1 |
| E6 7200s window | every warm call in BOTH modules carries `max_cache_age_seconds=7200`; the `<=` boundary lives in **untouched** `cache/integration/stories.py:163-167` — inherited, not altered. The exact-7200s tick behavior is the pre-existing contract, not this diff's |

Mid-pass proof of no-call-past-the-wall: attack 4 P1 (offer 250, budget 1)
produced **exactly 100** Asana calls, none after `_should_exit_early` fired.

**N-1 (NARROWING — net-new AWS calls, disclosed-in-substance, unnamed-as-calls):**
the build claims Asana budget-neutrality and that claim SURVIVES (E1–E4, E6,
attack-1 request-parity). But per run the change makes **4 net-new CloudWatch
`put_metric_data` calls** (`cloudwatch.py:70-83` is one live AWS call per
`emit_metric`; the 4 dimensioned offer series at `story_warmer.py:210-217`).
BUILD §3.2 discloses the new *series*; it does not name them as net-new AWS API
calls/spend. Bounded (4/run × 1 priority entity), but "no net-new API call"
is true only Asana-scoped.

**N-2 (NARROWING — one net-new cache read on the absent-offer path):** when
offer is not in `completed_entities`, the priority pass performs 1 net-new
`dataframe_cache.get_async("project-offer", "offer")` per run (E3). Non-Asana,
non-429, bounded; unnamed in the build note.

## 5. Attack 4 — partial-pass honesty: PASS

- Forced mid-pass timeout (pop 250, budget 1): receipt `success=100 <
  task_count=250`, `budget_exhausted=True`, `processed=100`; the **emitted**
  log record and the dimensioned metrics carry the same partial truth
  (`StoryWarmEntitySuccess=100`, `StoryWarmEntityTaskCount=250`,
  `StoryWarmEntityReached=1`); `story_warm_timeout_exit` logged with
  `entity_processed=100 / entity_task_count=250`. reached≠warmed is visible;
  no field claims completion.
- Injected client failures (30/100 raise): `success=70, failure=30` at both
  altitudes — failures are not rounded into success.
- Falsy-return semantic: a non-raising call returning `None` counts success
  (10/10) — "success" == call-completed. This is the door attack 5 walks
  through.

## 6. Attack 5 — CF-3 residual: CONFIRMED, one undisclosed adjacent path

- **L1**: pure-cache-hit simulation vs real-fetch simulation → per-entity
  receipts **identical** modulo `duration_ms`. The receipt measures
  reached-and-warm, not cold→warm — exactly as BUILD §4 UV-P 2 discloses.
- **L2 (real client code, executed)**: `StoriesClient.list_for_task_cached_async`
  with `_cache=None` (`clients/stories.py:392-404`) returns fetched stories,
  can persist nothing; the warmer counts `success=5/5`. Receipt GREEN, story
  cache untouched by construction.
- **L3 (real client code, executed)**: cache layer raising a
  `CACHE_TRANSIENT_ERRORS` member (`S3TransportError` proven) drives the
  degrade path (`clients/stories.py:447-457`): **uncached fallback fetch,
  `set_versioned` called 0 times**; warmer counts `success=5/5`. Receipt
  GREEN while the story cache stayed cold this run.
- **L4**: receipt schema carries no `was_incremental`/persist discriminator
  field (schema enumerated in the run output).

**N-3 (NARROWING — fetch-without-persist is a second, undisclosed residual
class):** BUILD §4 UV-P 2 discloses only the hit-vs-fetch split inside
"success". L2/L3 prove a distinct class: **success with zero cache writes**
(cache absent or cache-layer outage). In that regime a "warm" receipt does not
imply the cache behind `section_timeline_service` moved at all. Both paths are
pre-existing client semantics in **untouched** files — NOT a CC-5 defect — but
CC-5's receipt inherits them and its honesty claim should carry this second
UV-P. Likelihood-bounded: it requires cache-layer failure, in which regime the
warm cycle is degraded anyway. Answer to the charge's question: **yes, a
pure-cache-hit run reports the same receipt as a real fetch (L1), and a
cache-outage run reports GREEN with the cache never written (L2/L3)** — the
receipt closes absent-vs-zero, not imputed-vs-fresh.

## 7. Findings register

| ID | Class | Finding | Disposition |
|----|-------|---------|-------------|
| N-1 | narrowing | 4 net-new CloudWatch `put_metric_data` calls/run (dimensioned offer series) — Asana-neutral, not AWS-API-neutral | note in merge word; no code change required |
| N-2 | narrowing | 1 net-new DataFrame-cache read/run when offer absent from cascade | cosmetic; name it |
| N-3 | narrowing | "success" also includes fetch-without-persist (cache None / transient degrade, `clients/stories.py:392-404`, `:447-457`) — second residual class beyond disclosed UV-P 2 | add as UV-P alongside BUILD §4 UV-P 2; pre-existing, untouched files |
| F-1 | fence observation | `ASANA_STORY_WARM_PRIORITY_ENTITIES` accepts arbitrary entity lists; each named entity mints 4 dimensioned series (`story_warmer.py:204-217`). Tier-1 is enforced by DEFAULT (`("offer",)`, test-pinned), not by mechanism — an env edit can widen priority (and CW spend) without a code change | operator-lever by design (BUILD §3.1); flag so the merge word knows the fence is default-deep |
| — | null results | no over-report vector found (attack 4); no Tier-2 coverage change for entities 5–16 (attack 2 Q1); no input found that blows the 120s wall or adds Asana calls (attack 3, E1–E4/E6); revert lever exactly reproduces origin/main coverage (attack 2 Q4) | evidence of absence at fixture altitude, MODERATE |

## 8. Discipline attestations

- **CR-5**: zero credential values encountered or recorded. Zero AWS calls,
  zero Asana calls, zero live infra — all legs pure unit/fixture; nothing UNRUN
  (the 7200s boundary leg is discharged structurally: the boundary code is
  empty-diff vs origin/main, and E6 proves the constant is passed unchanged).
- **G-THEATER**: every RED was a reverted/broken INPUT (env lever, failing
  client, zero budget, simulated cache outage via `CACHE_TRANSIENT_ERRORS`);
  no production code was mutated. Post-run `git status --porcelain` in the
  worktree: empty.
- **Self-assessment cap**: MODERATE. Same-rite second seat (10x-dev
  qa-adversary on a 10x-dev build); no rite-disjoint corroboration occurred
  here. Findings stand on command+exit receipts, not on trust in the builder.

## 9. Bottom line

CC-5's **BUILT rung SURVIVES falsification**. The two-sided discriminator is
real under an independently-built fixture; the change is clean Tier-1 (the only
fleet effect is the disclosed, quantified, lever-revertible entities-1–4 tail
displacement; entities 5–16: zero change); Asana budget-neutrality holds at
every forced edge; partial passes are reported honestly at all three emission
altitudes. Carry N-1/N-2/N-3 + F-1 into the merge-word packet. Nothing here
buys a merge, a deploy, or any AL-5 regime claim (R-9 trap honoured).
