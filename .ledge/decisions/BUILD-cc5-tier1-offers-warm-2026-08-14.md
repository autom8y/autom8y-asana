---
type: decision
subtype: build-note
artifact_id: BUILD-cc5-tier1-offers-warm-2026-08-14
initiative: chain-of-custody-closure
wave: chain-of-custody-closure (Phase 2)
sprint: CC-5 (RE-1 Tier-1 offers-only warm-path repair)
session: coc-phase-2
author: principal-engineer (10x-dev, co-seated)
date: 2026-08-14
status: draft
sprint_state: BUILT-UNMERGED (no merge word exists; F-4 unlifted)
rung: rung-BUILT (dark, in-worktree; NOT merged, NOT pushed, NOT deployed)
self_assessment_ceiling: MODERATE (single-seat, self-ref; no rite-disjoint second read yet)
opened_by: RULINGS-coc-operator-sitting-2026-08-13.md §R-1 (Tier 1, offers-only, coc lane owns)
bound_by: GATE-coc-phase2-entry-2026-08-14.md §3 (CC-5 block) + §4 (hard walls)
substrate_of_record: origin/main d7560153
worktree: .knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc5a
branch: coc-cc5-tier1-warm
commit: 6b75279fcfb9e71c40766bf6bf5d037ca7766ba6
lever: O-A (targeted offers-only pass), placement corrected to priority-FIRST
tier: 1 ONLY — Tier 2 (fleet warmer redesign, entities 5–16) NOT attempted
---

# BUILD — CC-5 Tier-1 offers-only warm-path repair + per-entity warm receipt

> **Exit rung: `rung-BUILT`.** Code exists on a branch in an isolated worktree.
> It has not been merged, pushed, PR'd, or deployed. No merge word exists
> (F-4 unlifted, `RULINGS…§R-4`). Per entry-gate **Amendment A**, this sprint
> buys a *merge-ready artifact* and can NEVER buy a clean AL-5 regime.

---

## 0. R-9 trap — carried VERBATIM

> *"do not misread a post-deploy AL-5 green as staleness cured — it may be the
> warm fix or the deploy, not the regime"* (`project-offers-false-staleness-alarm-legs`;
> `SLATE-re1-warm-path-options-2026-08-13.md:214-216`).

Restated in this sprint's own terms: **this build MUST NOT be read as having
secured, purchased, or moved toward an AL-5 "clean regime."** That would require
an operator merge word + a merge + a deploy + a warm cycle, none of which exist.
The AL-5 window-open timestamp (~2026-08-15T12:45Z) is carried as:

`[UV-P: AL-5 sample window for asana-AL5-offer-frame-stale-1143843662099250 opens ~2026-08-15T12:45Z | METHOD: read-only CloudWatch describe-alarms inspection | REASON: inherited from the wave briefing via SLATE §5; not re-verified own-hands this sprint, and forward-looking sample-window timing is an estimative claim (SVR trigger-table row 6), not an SVR-bearing platform fact]`

---

## 1. FR-3 anchor repair (duty migrated to CC-5 per entry-gate BR-1) — DISCHARGED

All four anchors re-inspected own-hands against the substrate of record via
`git show origin/main:<path>` (no working-tree reads for the *origin* claims;
MONOREPO TRAP honoured).

| claim | SLATE/PROBE cited | CORRECT anchor (verified) | verification |
|---|---|---|---|
| `emit_metric("StoryWarmSuccess", …)` | `story_warmer.py:159` **(wrong)** | **`story_warmer.py:157`** | `git show origin/main:src/autom8_asana/lambda_handlers/story_warmer.py \| sed -n '154,170p'` → `:157 emit_metric("StoryWarmSuccess", stats["success"])`; `:159` is `emit_metric("StoriesWarmed", …)`. Gate's correction CONFIRMED. |
| `story_warm_complete` emission | `story_warmer.py:166` | event name at **`:164`**, `"success"` field at **`:166`**, guard `if stats["success"] > 0 or stats["failure"] > 0:` at **`:162`** | same probe. The SLATE's `:166` is right *as a field anchor*, wrong as the event anchor. |
| `read_stories_batch` def-site | `stories.py:34/:63` **(ambiguous + partly wrong)** | **`src/autom8_asana/cache/integration/stories.py:63`** | `git show origin/main:…/cache/integration/stories.py \| grep -n "def read_stories_batch"` → `63:`. `:34` falls inside the `DEFAULT_STORY_TYPES` list literal. NOTE: the bare filename `stories.py` is **ambiguous** — `src/autom8_asana/clients/stories.py` also exists; the cache-read claim belongs to `cache/integration/stories.py`. |
| "a miss returns `None`" | `stories.py:30` **(wrong)** | **`:97-98`** (`else:` / `result[gid] = None`), function returns at **`:100`** | same probe. `:30` is inside `DEFAULT_STORY_TYPES`. |

**Substance unchanged.** The SLATE's *claims* survive the anchor repair:
`read_stories_batch` (`:63-:100`) contains no `set_versioned` — the nearest is
`:145`, inside `load_stories_incremental` — so it is a pure read and cannot
bootstrap a cold cache. Only the coordinates were wrong.

---

## 2. Lever selection — O-A, justified against the SLATE DF-4 table

**Chosen: O-A (targeted offers-only warm pass keyed on the offers project GID),
with its placement corrected from "after the cascade" to "priority-FIRST."**

One paragraph, anchored to `SLATE §3` + the `SLATE §5` DF-4 table: O-C
(dedicated invocation) is excluded twice over — it needs a new schedule/Lambda
config, i.e. **Terraform**, which this sprint's write fence forbids, and R-1
scoped CC-5 to **ONE Lambda invocation**, which a dedicated second invocation
violates by construction. O-B and O-F are disfavoured in the DF-4 table for
producing a *fuzzy* regime boundary and "the highest O-7a bookkeeping cost"
(`SLATE §5`, rows O-B/O-F) — intermittent or partial warming means there is no
single before/after to segment, which is precisely the wrong property to buy
while an AL-5 sample window is pending. O-D requires a consumer-demand signal
that does not exist (the endpoint has zero traffic, `SLATE §3 O-D`). O-G is
low-confidence on its own arithmetic and "adds a **confound** — a 429 storm from
raised concurrency could itself spike frame staleness, contaminating AL-5 in the
opposite direction" (`SLATE §5`, row O-G). That leaves **O-A**, the only lever
in the table that is (i) implementable purely in `src/**`, (ii) inside one
invocation, and (iii) gives **one clean deploy boundary** ("O-A … one clean
regime", `SLATE §5` row O-A).

### 2.1 Pragmatic adjustment — the slate's O-A placement is not implementable as worded

`SLATE §3 O-A` specifies: *"**after the cascade**, warm the offer DataFrame's
4,192 GIDs specifically."* **That placement cannot work in one invocation.** The
story-warm budget is TIME-bound, not count-bound: the loop's exit is
`_should_exit_early(context)` (`timeout.py:32-54`, exits at remaining <
`TIMEOUT_BUFFER_MS = 120_000`), consulted once per chunk. A second pass placed
after the cascade inherits an already-exhausted clock and would break on its
very first chunk check — reproducing the exact defect it was meant to repair.

The only placement that satisfies O-A's own stated property — *"independent of
whether entities 1–4 exhausted the budget"* — inside a single invocation is
**before** them. So: same lever, corrected placement. This is a deviation from
the slate's literal wording, recorded here rather than performed silently.

### 2.2 Narrowing — the pass is budget-NEUTRAL (the slate over-priced O-A's cost)

`SLATE §3 O-A` prices O-A as *"recurring Asana API budget for 4,192 story
reads/pass"* plus a re-entry into the 429 surface. **Both are narrowed by the
mechanism:**

1. The story warmer **already ran to its timeout wall every run** — the
   `story_warm_timeout_exit` burst re-derived live in
   `CRITIQUE-re1-slate-2026-08-13.md:229-242` is proof it consumes the whole
   residual budget. Total wall-clock consumption, total request volume ceiling,
   and the `Semaphore(3)` envelope are all **unchanged** by this build. What
   changes is *which* tasks the same budget buys — offer instead of the tail of
   entities 1–4. There is no new 429 pressure because there is no new request
   rate and no new concurrency.
2. Re-warming an already-warm task costs **no API call at all**:
   `cache/integration/stories.py:163-167` short-circuits
   (`if cache_age <= max_cache_age_seconds: return cached_stories, cached_entry, True`)
   before the fetcher at `:170`. The warmer passes
   `max_cache_age_seconds=7200` and no `task_modified_at`, so the
   `is_stale` bypass above it does not engage. **Coverage therefore accrues
   across runs** rather than restarting from zero each pass.

**The honest cost this build DOES incur:** entities 1–4 lose the share of the
budget that offer now takes. Under the pre-CC-5 order they received the full
residual budget; under priority-first they receive it minus offer's pass. That
displacement is real, is the unavoidable Tier-1 trade inside one invocation, and
is now **measured** by the per-entity receipt rather than inferred. It is the
same class of trade `SLATE §3 O-F` names ("dilutes entities 1–4 from *complete*
to *partial*"), taken deliberately and narrowly for one entity.

---

## 3. What was built

**One file changed, one file added. One clean deploy boundary** (a single Lambda
image; no new entry point, no new schedule, no new IAM, no Terraform).

| path | change | lines |
|---|---|---|
| `src/autom8_asana/lambda_handlers/story_warmer.py` | rewritten (priority-first order + per-entity receipt + helper extraction) | +406 / −98 (497 total) |
| `tests/unit/lambda_handlers/test_story_warm_priority_offer.py` | new | 439 |

Anchors below are **post-change, in-worktree** (branch `coc-cc5-tier1-warm` @
`6b75279f`), verified by `grep -n` against the committed file.

### 3.1 Priority-first warm order

- `DEFAULT_STORY_WARM_PRIORITY_ENTITIES: tuple[str, ...] = ("offer",)` —
  `story_warmer.py:68`. **Names an ENTITY, never a project GID.** The GID is
  resolved through the caller's `get_project_gid` (registry-backed,
  `cache_warmer.py:879-880`), so a registry change cannot silently aim the pass
  at a stale project. `1143843662099250` appears nowhere in the diff.
- `STORY_WARM_PRIORITY_ENV_VAR = "ASANA_STORY_WARM_PRIORITY_ENTITIES"` —
  `story_warmer.py:74`. Operator lever, following the existing repo idiom
  (`ASANA_VERTICAL_BACKFILL_ENABLED`, `cache_warmer.py:243-248`). Setting it to
  the **empty string restores the pre-CC-5 pure cascade order** — a revert that
  needs no code change and no different image.
- `_build_warm_order(completed_entities, priority_entities)` —
  `story_warmer.py:115`. Priority entities lead, de-duplicated; the remainder
  keeps its original relative order.
- `_warm_entity_stories(...)` — `story_warmer.py:220`. The per-entity body,
  extracted so it is directly testable and so the loop carries no closure over
  loop variables.

### 3.2 Receipt shape (SLATE §4) — implemented, `src/**` only

- `story_warm_entity_complete` — `story_warmer.py:200`, emitted from
  `_emit_entity_receipt` (`:186`) for **every planned entity on every run,
  including when every counter is zero.** Fields: `entity_type`, `project_gid`,
  `priority`, `position`, `enumerated`, `skip_reason`, `task_count`,
  `processed`, `success`, `failure`, `shared_gids_with_prior`,
  `budget_exhausted`, `total_tasks_at_entry`, `duration_ms`, `invocation_id`.
- **The two negatives are distinguishable**, exactly as `SLATE §4` specifies:
  `enumerated=true, success=0` → budget starvation (today's floor);
  `enumerated=false` + `skip_reason` → never reached.
- CloudWatch series — `story_warmer.py:210-218`:
  `StoryWarmEntityTaskCount` (the **denominator**, emitted first — a success
  count without its population cannot be read as coverage),
  `StoryWarmEntitySuccess`, `StoryWarmEntityFailure`, `StoryWarmEntityReached`,
  all dimensioned `{entity_type}` and all emitted **unconditionally including
  explicit `0`**.
- **Dimensioned metrics are emitted only for PRIORITY entities** (`:204-205`).
  Deliberate: every entity's receipt lands in the *log* (dimension-free, already
  the substrate the PROBE and CRITIQUE queried), while the new CloudWatch series
  stay bounded to Tier-1 scope instead of minting a set per fleet entity. This
  also keeps the change clear of the charter's spend fence.
- `story_warm_complete` is now **unconditional** (`:469`). The pre-CC-5 guard
  `if stats["success"] > 0 or stats["failure"] > 0:` (origin/main `:162`) made
  an all-zero run indistinguishable from a run that never happened — the same
  absent-vs-zero defect NR-4(d) exposed, one altitude up.
- `story_warm_timeout_exit` (`:329`) **preserves** its `tasks_processed` and
  `total_tasks` cumulative semantics — the two fields the PROBE and CRITIQUE
  Logs Insights queries parse — so the 14-day baseline series stays comparable
  across the deploy boundary. Regression-guarded by
  `test_timeout_exit_log_preserves_probe_query_fields`.

### 3.3 Two-sidedness of the receipt (why it cannot read green on a no-op)

`success` still increments only on `result is True` from an awaited
`list_for_task_cached_async` (`story_warmer.py:348-355`). A telemetry-only
deploy leaves `StoryWarmEntitySuccess{entity_type=offer}` at 0 (correctly RED);
only real warming moves it. The test suite demonstrates this directly: on the
two-sided canary the **aggregate** `StoryWarmSuccess` is identical (200) on both
legs, and **only the per-entity receipt moves.**

---

## 4. CF-3 and CF-18 — handled, not assumed away

### CF-18 (warm_priority tie fragility) — NEUTRALIZED for the priority set

Mechanism verified own-hands at `dataframes/cascade_utils.py` (origin/main):
`ready = {e for e in remaining if …}` (`:233`) is a **set**, and
`phase = sorted(ready, key=lambda e: warmable_priority.get(e, 99))` (`:247`) is a
*stable* sort — so entities sharing a `warm_priority` (or both falling to the
`99` default) resolve in **set-iteration order**, which is not stable across
processes. No live tie exists today (`entity_registry.py` assigns 1,2,3,4,5,6,
7,10…18 — verified by `grep -n "warm_priority=" src/`), so CF-18 is a *latent*
fragility, not an active defect. **This build does not depend on it either way:**
the priority pass is keyed on the entity name → project GID, not on the entity's
position in `completed_entities`. Guarded by
`test_offer_warmed_even_when_absent_from_completed_entities` and
`test_priority_leads_regardless_of_cascade_position`.

### CF-3 (offer GID shared with an already-warmed entity) — MEASURED + structurally dissolved for offer

- **Measured**: `shared_gids_with_prior` (`story_warmer.py:296`) counts, per
  entity, how many of its GIDs were already enumerated by an earlier entity this
  run. CF-3 stops being an unprobed null and becomes a number in every receipt.
- **Dissolved for offer**: offer now runs **first**, so it can never inherit a
  prior entity's GIDs — its `shared_gids_with_prior` is 0 by construction, and
  any overlap surfaces on the follower instead. Proven by
  `test_cf3_population_overlap_is_measured_not_assumed`.
- **Residual, carried honestly**: a `success` counts *"the warm call returned
  True"*, which includes the case where the cached entry was younger than
  7200 s and no fetch occurred (`cache/integration/stories.py:163-167`). The
  receipt therefore measures **reached-and-warm**, NOT **cold→warm
  transitions**. `list_for_task_cached_async` does not surface the
  `was_incremental` flag it receives from `load_stories_incremental`
  (`clients/stories.py:412-422`), so distinguishing the two would require
  changing that method's return contract — out of CC-5's scope and not attempted.
  `[UV-P: the fraction of offer "successes" that are fetches rather than cache hits | METHOD: extend list_for_task_cached_async to surface was_incremental, or query the existing per-fetch client metrics by task population | REASON: requires a client-contract change with other callers; deliberately out of Tier-1 scope]`

---

## 5. Test receipts — commands, exit codes, own-hands

Run inside the worktree with `PYTHONPATH=$PWD/src` **exported**. This is
load-bearing: the venv's editable install is a plain `.pth` pointing at the MAIN
tree's `src/`, so a bare `pytest` from a worktree silently imports the main
tree's package and would grade the wrong code. Resolution verified before every
leg: `python -c "import autom8_asana.lambda_handlers.story_warmer as m; print(m.__file__)"`
→ `…/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc5a/src/…/story_warmer.py`.

| # | command | result | exit |
|---|---|---|---|
| 1 | `python -m pytest tests/unit/lambda_handlers/test_story_warm_priority_offer.py tests/unit/lambda_handlers/test_story_warming.py -q` | **30 passed** (22 new + 8 pre-existing, all pre-existing unmodified) | **0** |
| 2 | `python -m pytest tests/unit/lambda_handlers/test_cache_warmer.py tests/unit/lambda_handlers/test_warmer_manifest_clearing.py tests/unit/lambda_handlers/test_cache_warmer_adversarial_qa.py -q` | **62 passed** (the call-site consumers) | **0** |
| 3 | `python -m pytest tests/unit/lambda_handlers/ -q -p no:randomly` | **634 passed**, 34 warnings, 205 s (whole handler package) | **0** |
| 4 | `python -m ruff check src/…/story_warmer.py tests/…/test_story_warm_priority_offer.py` | All checks passed | **0** |
| 5 | `python -m ruff format --check <same two files>` | 2 files already formatted | **0** |
| 6 | `python -m mypy src/autom8_asana/lambda_handlers/story_warmer.py` | Success: no issues found | **0** |

Leg 3 was run on the pre-`ruff format` revision of the test file; the reformat
was whitespace-only and legs 1–2 re-ran green on the committed tree. Everything
above is a leg **I ran and watched**; nothing is UNRUN, and nothing is inherited
green.

### 5.1 The two-sided discriminating canary

`test_offer_starves_under_legacy_order_and_warms_under_priority_order` runs ONE
fixture (3 entities × 200 tasks) and ONE budget (2 timeout-clean chunk checks)
through BOTH orderings:

- **RED leg** — `ASANA_STORY_WARM_PRIORITY_ENTITIES=""` (the pre-CC-5 pure
  cascade order, reached through the real operator lever, **not** through a
  defect injected into production code): `offer.success == 0`,
  `enumerated == True`, `budget_exhausted == True` — the production defect,
  reproduced in miniature.
- **GREEN leg** — default priority set, same fixture, same budget:
  `offer.success == 200`, `position == 0`.
- **Teeth**: `red["success"] == green["success"] == 200` and
  `red["total_tasks"] == green["total_tasks"] == 600`. **The aggregate counter
  cannot tell the two legs apart.** Only the per-entity receipt moves. A test
  asserting only on `stats["success"]` would read GREEN on the broken code —
  which is exactly why the receipt is not optional.

Other teeth worth naming: `test_concurrency_envelope_is_not_raised` asserts
`_STORY_WARM_CONCURRENCY == 3` (an O-G tripwire — raising it would be a decision
needing its own ruling, not a silent edit riding this diff);
`test_non_priority_entities_do_not_mint_dimensioned_series` bounds the new
CloudWatch series to Tier-1 scope; `test_partial_offer_coverage_is_reported_honestly`
proves a too-small budget does not read as done.

---

## 6. Hard walls — attested

| wall | state |
|---|---|
| No merge / push / PR / deploy / auto-merge | **HONOURED.** One local commit on `coc-cc5-tier1-warm` in the isolated worktree. `git push` never invoked. No `gh pr` invoked. |
| No Terraform / no new infra / no new IAM | **HONOURED.** `git diff --stat` on the commit shows exactly two paths, both under `src/**` and `tests/**`. Zero `terraform/**` bytes. The alarm/dashboard that would consume `StoryWarmEntity*` is Terraform and is deliberately NOT authored here. |
| Tier 2 FORBIDDEN | **HONOURED.** The default priority set is `("offer",)` and a test pins it (`test_default_priority_is_offers_only`). Nothing in the diff touches the other eleven starved entity types except by receiving a receipt they did not have before. No fleet-warmer redesign, no fan-out, no multi-invocation topology. |
| No AL-5 "clean regime" claim | **HONOURED** — see §0. The exit rung is `rung-BUILT`; the artifact is merge-READY, not merged. |
| Single-writer per path | **HONOURED.** Only `src/autom8_asana/lambda_handlers/story_warmer.py` and `tests/unit/lambda_handlers/test_story_warm_priority_offer.py` were written; the build note is the only main-tree file authored and no git command was run in the main tree. |
| MODERATE self-cap | **HONOURED.** No STRONG claim anywhere in this note. No rite-disjoint second read has occurred. |
| Substrate of record = origin/main d7560153 | **HONOURED.** Branch based at `d7560153`; every origin-claim probe used `git show origin/main:<path>`. |

---

## 7. UV-Ps carried

1. `[UV-P: AL-5 window-open ~2026-08-15T12:45Z | METHOD: read-only describe-alarms | REASON: inherited from the wave briefing, not re-verified own-hands; forward-looking timing is estimative, not SVR-bearing]` (§0).
2. `[UV-P: cache-hit vs fetch split inside offer's "success" count | METHOD: surface was_incremental through list_for_task_cached_async, or population-scoped query of the existing client fetch metrics | REASON: client-contract change with other callers; out of Tier-1 scope]` (§4).
3. `[UV-P: production offer population is ~4,192 tasks and the residual story-warm budget is ~2,500–7,455 tasks/run | METHOD: CloudWatch Logs Insights over /aws/lambda/autom8-asana-cache-warmer | REASON: inherited from PROBE §1 and CRITIQUE :229-242 live re-derivation; this sprint ran NO AWS call whatsoever. The build's correctness does not depend on the exact figure — priority-first reaches offer at ANY residual budget > 0 — but the claim "one pass covers the full 4,192" DOES depend on it and is therefore not asserted here.]`
4. `[UV-P: post-deploy behaviour of the new receipt in the live log group | METHOD: Logs Insights on story_warm_entity_complete after a deploy that does not exist | REASON: SVR trigger-table row 7 — the emission is real code but its live behaviour is a not-yet-shipped referent]`

**Explicitly NOT claimed:** that offer is now warm in production; that the AL-5
regime is improved, clean, or segmentable; that a full 4,192-task pass completes
in every invocation (§4 UV-P 3 — bad-budget runs will warm offer *partially*,
and the receipt reports that honestly rather than rounding it up).

---

## 8. Carries handed forward

- **A.4 disclosure duty SURVIVES.** The entry gate binds it "until a warm is
  *proven* to reach offer." This build makes the proof *possible* (the receipt)
  but supplies no production observation, so the imputed-payload disclosure
  remains necessary. Untouched here: `section_timeline_service.py:502/:505/:532`
  — 4,192 misses ≫ 50 still takes the no-op branch, so the endpoint still
  writes nothing and still cannot bootstrap itself. Nothing in this build
  changes that; it changes who fills the cache *behind* it.
- **Entities 1–4 displacement** is the accepted Tier-1 cost (§2.2). It is now
  measured per entity. If a consumer of those entities' stories is harmed, the
  receipt will show it, and `ASANA_STORY_WARM_PRIORITY_ENTITIES=""` reverts the
  ordering without a code change.
- **The DF-4 deploy-boundary bookkeeping** (`SLATE §5` row O-A) is unchanged and
  unowned by this sprint: land before the window for one clean regime, else
  O-7a segmentation. That is an operator/merge-word decision, and entry-gate
  BR-4 already surfaces that the prize is likely unpurchasable inside the runway.
- **Suggested next reads for the rite-disjoint critic**: (a) is priority-first
  the right *placement* reading of O-A, or is it O-D/O-F in O-A's clothing?
  (b) is the entities-1–4 displacement acceptable without a named consumer
  analysis? (c) does the metric/log split (dimensioned only for priority
  entities) satisfy SLATE §4's "always-emitted" requirement, given the other
  fifteen entities get logs but no series?

---

## 9. Verification scope

Every source claim about `origin/main` was probed with
`git show origin/main:<path>` / `git grep`. Every claim about the built code was
probed with `grep -n` against the committed worktree file and by running the
tests. **Zero** AWS calls, **zero** Asana calls, **zero** Lambda invokes, **zero**
Redis reads, **zero** Terraform, **zero** credential reads, **zero** git mutation
in the main tree. Population and throughput figures are inherited from the PROBE
and CRITIQUE and labelled as such (§7 UV-P 3); none were re-derived this sprint.
Self-assessment ceiling **MODERATE** (single seat, self-referential, no
rite-disjoint second read).
