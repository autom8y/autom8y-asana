---
type: decision
subtype: option-slate
artifact_id: SLATE-re1-warm-path-options-2026-08-13
initiative: asana-native-insight-delivery
wave: chain-of-custody-closure
sprint: CC-4 (RE-1 option slate)
author: platform-engineer (sre, co-seated)
date: 2026-08-13
status: draft
wave_terminal_state: AUTHORED-UNMERGED (F-A — terminal state this wave; Q-4 HALT; main thread owns git)
binds: NOTHING (this slate prices F-1; it does not decide it)
self_assessment_ceiling: MODERATE (F-C)
grounds_on:
  - .ledge/reviews/PROBE-story-cache-warmth-2026-08-13.md (VERDICT COLD; mechanism table §1)
fix_locus: src/autom8_asana/lambda_handlers/story_warmer.py:91 (verified git show origin/main)
fork_priced: F-1 (RE-1 ownership) — offers-only vs fleet-wide starved set
critic: remediation-planner (arch), rite-disjoint, second-reads NR-4
---

# SLATE — RE-1 warm-path options (pricing F-1, binding nothing)

> **What this is.** A PAPER sprint, deliberately UPSTREAM of the F-1 fork. It
> converts F-1 (who owns the RE-1 warm path) from a *blind* fork into a *priced*
> one. It enumerates the warm-path options, prices each against the measured
> mechanism table, names the two scope tiers separately, specifies the
> two-sided receipt shape that would replace the inferred zero with a measured
> one, and prices the AL-5 producer-deploy interaction (DF-4) per option.
>
> **What this is NOT.** A recommendation. Nothing here binds F-1. §7 states the
> non-recommendation explicitly and names the decision axes F-1 must weigh. The
> fences forbid building, deploying, widening into a fleet-warmer redesign, or
> treating routed-out as a failure — all honoured.

---

## 0. SVR — mechanism table re-verified own-hands (`git show origin/main:`)

Every load-bearing number and line anchor below was re-inspected at
`origin/main` this sprint (MONOREPO TRAP honoured; no working-tree reads).

| claim | value | own-hands receipt (origin/main) |
|---|---|---|
| fix locus is the warm CALL | `story_warmer.py:91` | `await client.stories.list_for_task_cached_async(` — confirmed at :91 |
| concurrency envelope | `asyncio.Semaphore(3)` | defined at `story_warmer.py:64`, guards the :91 call — **anchor correction:** PROBE §3.3 cites the concurrency as ":91"; the *limit* is at **:64**, the *call* at :91. The value (3) is correct. |
| GID enumeration precedes warming | `stats["total_tasks"] += len(task_gids)` | `story_warmer.py:85` — runs BEFORE the chunk loop, so a timed-out entity still logs its cumulative position |
| per-chunk early-exit | `if _should_exit_early(context): … break` | `story_warmer.py:~114`, chunk_size=100 at :111 |
| success counter (the decisive readout) | `stats["success"] += 1` on `result is True` | `story_warmer.py:136`; emitted as `StoryWarmSuccess` (:159) and `story_warm_complete.success` (:166) |
| exactly THREE story-warm callers exist | 3 | `git grep list_for_task_cached_async origin/main -- src` → `story_warmer.py:91`, `section_timeline_service.py:334`, `section_timeline_service.py:511`. No others. |
| site #2 is dead | 0 callers | `build_timeline_for_offer` (`section_timeline_service.py:303`, contains :334) has **zero callers** in `src/` (grep returns only its own def) |
| inline self-heal is gated ≤50 | `MAX_INLINE_STORY_FETCHES = 50` | `section_timeline_service.py:502`; write-branch `if 0 < len(misses) <= 50` (:505); no-op branch `elif len(misses) > 50` (:532) logs `story_cache_gap_above_threshold` and **proceeds without writing** (:532–539) |
| ordering is stable by construction | `completed_entities: list[str]`, `.append(entity_type)` | `cache_warmer.py:830` + `:948`, driven by `processing_list` (`:907/:914`) — a **list**, not a set; corroborates PROBE's empirical 59/59 |

Mechanism-table quantities inherited from PROBE §1 (log/metric derived, not
re-run this sprint — read-only source SVR was the sprint's scope):

- offer DataFrame rows (task GIDs): **4,192** (`entity_warm_success` row_count, every cycle)
- tasks before the first offer task (entities 1–4): **10,616** (2,574 + 2,086 + 3,089 + 2,867)
- offer's slice: cumulative **10,617 – 14,808**; offer is entity **#5**
- warmer max-ever processed: **7,460** (3d, 59 runs) / **8,527** (14d ceiling, 324 runs)
- shortfall to the *first* offer task: **≥2,089** (vs 14d ceiling) / **≥3,156** (vs 3d max)
- entities **5–16 (twelve types)** have received **zero** story warming ≥14 days
- observed throughput: ~7,000 tasks / ~560–770 s at Semaphore(3) ≈ **~9–12.5 tasks/s**

---

## 1. NR-4 — negative claim, first-sweep with nulls (rite-disjoint critic second-reads)

**Negative claim under test:** *"the warmer's max-ever is 7,460, offer's slice
begins at 10,617, so offer is NEVER reached."*

### NR-4(a) — is there any OTHER path that warms offer stories? — **SWEPT (not asserted)**
`git grep list_for_task_cached_async origin/main -- src` → exactly three write
callers. Disposition of each, verified own-hands:
- `story_warmer.py:91` — the piggyback warmer. **The only live, unconditional path.** Starved (this whole slate).
- `section_timeline_service.py:334` (inside `build_timeline_for_offer` :303) — **dead**: zero callers in `src/`.
- `section_timeline_service.py:511` — the endpoint's inline self-heal, **gated `≤50` misses** (:505). Offers carry ~4,192 misses, so the `>50` branch (:532) fires and **writes nothing**. Confirms PROBE §3.1 "option (g) cannot bootstrap itself."
- Cache-fill-on-read? **No.** `read_stories_batch` (`stories.py:34/:63`) is a pure `cache.get_batch(EntryType.STORIES)` read with no `set_versioned` in its body; a miss returns `None` (`:30`).
- **Conclusion:** exactly one live warm path, and it never reaches offer. The PROBE's "only independent warm path" is **swept, not merely asserted.**
- **Null:** I did not probe whether an offer GID that is *also* a member of an earlier-warmed entity's DataFrame could carry a live entry (PROBE §5 gap 1). I saw no mechanism producing that.

### NR-4(b) — is the 10,616-before-offer ordering STABLE or run-varying? — **STABLE (empirical + structural)**
- Empirical: PROBE §2 probe D — identical breakpoint structure across all 59 runs.
- Structural (this sprint): the warmer's `completed_entities` is a `list[str]` built by `.append()` in `processing_list` completion order (`cache_warmer.py:830/:948/:907`), **not** a set. Order is deterministic by construction. (The `set[str]` at `progressive.py:783` is the API-preload path, a different code path — not the Lambda warmer.)
- **Consequence for the slate:** because order is deterministic, offers are *never* warmed by luck (0/59) — which is why option (b), rotating the start offset, is a genuine lever rather than a no-op.
- **Null:** I did not trace `processing_list`'s root construction to its ultimate source; stability is proven at the list-append altitude, not at the order-seed altitude.

### NR-4(c) — does the `>50` misses branch have a sibling that DOES write? — **YES, but unreachable for offers**
- The sibling write-branch exists: `if 0 < len(misses) <= 50` (`section_timeline_service.py:505`) DOES fetch-and-populate then re-read (:521). But offers' ~4,192 misses take the `elif >50` no-op branch (:532). So a writing sibling exists; it is **gated shut** for any project with >50 cold tasks — i.e., every starved entity. Not a hidden warm path.

### NR-4(d) — is the receipted ZERO a real zero or an UNEMITTED METRIC? — **REAL ZERO. Refuter does NOT invert the slate.** (swept hardest)
This is the refuter that could flip everything, so it was swept hardest.
- The PROBE's decisive readout is **not** an entity-dimensioned metric that could silently drop. It is the aggregate **positive** counter `stats["success"]` (`story_warmer.py:136`), emitted two independent ways: CloudWatch `StoryWarmSuccess` (:159) and `story_warm_complete.success` (:166). For offer to be warmed, this counter would have to **exceed 10,616**. It maxes at **7,455/7,460** (3d) / **8,527** (14d). A live counter that increments to 7,460 every run is the opposite of an absent metric.
- **The two-source cross-check is what defeats the refuter:** the *other* counter, `total_tasks` (`:85`), DOES cross the offer boundary every run (PROBE breakpoints include 10,617 and 14,809). So the instrumentation demonstrably **reaches** offer's enumeration (total_tasks crosses it) while the warming budget demonstrably **does not** (success stalls at 7,460). An unemitted-metric artifact cannot produce that asymmetry: it would zero *both* counters at the offer boundary, not one.
- **Residual caveat (honest):** PROBE §2 probe B's *CloudWatch* query filters `Name=environment,Value=staging`, while the runtime env is `production` (§2 probe F). That dimension quirk affects only the corroborating metric leg; the **decisive** leg (probe D) parses raw `story_warm_timeout_exit` / `story_warm_complete` log messages, which are dimension-free. The verdict does not rest on the staging-dimensioned metric.
- **Conclusion:** the zero is real. **NR-4(d) held; it did not invert the slate.** But it exposes a genuine weakness the slate must carry forward: *today's zero is INFERRED from an aggregate counter, not MEASURED per-entity.* That is exactly what the §4 receipt shape fixes.

---

## 2. Scope tiers — named and priced SEPARATELY (never collapsed)

The two tiers must not be collapsed: **the blast radius is what makes F-1 the
operator's fork.** Offers-only is a bounded repair in this repo; the full
starved set is a fleet-wide warmer redesign the fences explicitly forbid this
sprint from proposing.

| | **Tier 1 — OFFERS-ONLY** | **Tier 2 — FULL STARVED SET (entities 5–16)** |
|---|---|---|
| population | 4,192 tasks (1 entity) | ~48,662 tasks (12 entity types: offer + contact 23,484 + asset_edit 14,666 + 9× process_*) |
| dedicated warm time @ ~9–12.5/s | **~6–8 min/pass** | **~65–90 min/pass** |
| fits one Lambda invocation? | **Yes** (well under the 15-min ceiling) | **No** — exceeds a single invocation's budget by ~4–6×; the warmer already dies at ~7,460 tasks. Structurally requires multi-invocation, parallel fan-out, or a dedicated fleet warmer. |
| blast radius | one project GID (`1143843662099250`) | twelve entity types, each with its own downstream consumers |
| is this repo's to decide? | Plausibly (bounded, in-`src/`) | **This is the fleet-warmer redesign the fences forbid.** F-1 territory. |
| relation to Mission A | closes option (g)'s data substrate for offers only | closes it for offers *and* eleven siblings that were never in scope |

**Load-bearing point for F-1:** every "warm the offers" option below (O-A/B/C/D/F/G)
can be scoped to Tier 1 *or* Tier 2. The **mechanism** (which lever) and the
**scope** (which tier) are orthogonal choices. A Tier-1 offers-only dedicated
warm is a ~6–8 min job; the *same lever* at Tier 2 is a ~65–90 min fleet job
that no single Lambda can hold. Do not let a cheap Tier-1 price smuggle in a
Tier-2 commitment.

---

## 3. OPTION SLATE — enumerated BEFORE recommended, each priced against the mechanism table

> Discipline note (`option-enumeration-discipline`): options are enumerated
> exhaustively first; §7 declines to recommend. Routed-out (O-E) is a
> **first-class** option, not a failure mode.

### O-A — Offers-only dedicated warm (targeted piggyback)
- **Mechanism:** after the cascade, warm the offer DataFrame's 4,192 GIDs specifically (a targeted second pass keyed on the offers project GID), independent of whether entities 1–4 exhausted the budget.
- **Price vs table:** 4,192 tasks / ~9–12.5 tasks/s = **~6–8 min** of dedicated warming; recurring Asana API budget for 4,192 story reads/pass. Closes the ≥2,089-task shortfall for offer only. Scope = Tier 1.
- **Cost the PROBE flags:** this is *new work option (g) was costed as not needing* (PROBE §3.3 item 2).
- **429 hazard:** raising story-read volume re-enters the 429-storm surface (scar tissue: `asana-substrate-freshness` arc). Semaphore(3) is the current throttle; a targeted pass adds ~4,192 reads that were not happening.

### O-B — Rotate the iteration start offset across runs
- **Mechanism:** each run starts the entity cascade at a rotating offset so that, over N runs, every entity (incl. #5) periodically leads and gets budget before timeout.
- **Price vs table:** offers get warmed roughly 1 run in ⌈10,616 / 7,460⌉ ≈ every **2nd–3rd run** if offset lands them first; between those runs offers age. Net: eventual, *intermittent* freshness, not steady-state. Cheapest code change (a start-index change on a deterministic list — NR-4(b)). Scope: naturally Tier 2 (rotation helps all starved entities), but with *intermittent* per-entity coverage.
- **Cost:** whichever entities get pushed past the budget on offset runs age on those runs — it redistributes starvation rather than removing it. No new invocation, no new API budget beyond what already runs.

### O-C — Dedicated invocation decoupled from the deadline-bound cascade
- **Mechanism:** give story warming its own Lambda invocation / schedule, not piggybacked on the tail of the frame warmer's deadline-bound budget (PROBE §3.3: "give story warming its own invocation").
- **Price vs table:** removes the shared-budget starvation entirely — the story warmer gets its own ~15-min budget. At ~9–12.5/s a dedicated invocation covers ~8,000–11,000 tasks/run; Tier 1 (4,192) fits in one; Tier 2 (48,662) still needs ~5–6 invocations or fan-out. New infra (a schedule + Lambda config = Terraform, admissible under the freeze) plus recurring compute + Asana API budget.
- **Cost:** most durable fix; highest new-infra cost; the only option that structurally *guarantees* offer is reached rather than reached-on-average.

### O-D — Consumer-demand ordering
- **Mechanism:** order the cascade by *consumer demand* (warm what gets read) rather than the current cascade/dependency order, so offers — which option (g) reads — warm before low-demand entities.
- **Price vs table:** re-prioritises the existing budget; if offer demand ranks it into the first ~7,460 tasks, it warms every run with **zero new compute**. But it *demotes* whatever currently occupies entities 1–4 (business/unit_holder/unit/asset_edit_holder) — those have their own consumers and their own freshness expectations. Requires a demand signal that does not exist today (would need instrumentation of read traffic per entity — and the endpoint has **zero** traffic today, PROBE §2 probe E, so "demand" for offers is presently unmeasurable).
- **Cost:** cheapest compute, highest *coordination* cost — it trades one entity's freshness for another's, a cross-consumer decision above this slate's pay grade. Chicken-and-egg: demand-ordering needs demand data; the surface has none yet.

### O-E — Routed-out with a named owner (FIRST-CLASS option, not a failure)
- **Mechanism:** F-1 decides the RE-1 warm path — specifically the Tier-2 fleet-warmer redesign — is **owned elsewhere** (a named owner/rite), because its blast radius (twelve entity types, multi-invocation topology) exceeds this repo's 10x-dev lane. This slate hands off a priced problem statement, not a build.
- **Price vs table:** **zero cost in this lane.** No deploy, no `src/` change, no Asana budget, no AL-5 disturbance (see §5). The mechanism-table pricing transfers to the named owner, who inherits Tier-2's ~65–90 min/pass, multi-invocation reality and the DF-4 interaction when *they* deploy.
- **Why first-class:** the PROBE itself frames the durable fix as "a **fleet-wide** repair — offers are one of twelve starved entities" (§3.3). Routing the fleet redesign to its proper owner is the *correct* disposition if F-1 judges the scope fleet-wide — not a punt. The fence "do not widen into a fleet warmer redesign" is precisely why this option exists: this lane should not build Tier 2; it can only route it.
- **Pairs with:** a Tier-1 stopgap (O-A) in this repo while the named owner builds Tier 2 — but that pairing is F-1's call, not this slate's.

### O-F — Reorder / interleave the cascade so starved entities lead (round-robin) — *added*
- **Mechanism:** instead of a rotating *offset* (O-B), interleave entities round-robin (warm N tasks of each entity per cycle) so every entity — including #5 — gets *some* budget every run before any entity is exhausted.
- **Price vs table:** offer gets ~(budget-share) warmed every run — e.g., if the ~7,460-task budget is split 16 ways, offer gets ~460 of its 4,192 tasks/run → full offer coverage in ~9 runs, *partial* coverage every run. Steady partial freshness for all twelve starved entities simultaneously. No new invocation; no new API budget beyond current volume (same total tasks, redistributed).
- **Cost:** dilutes entities 1–4 from *complete* to *partial* per run — they currently finish; under round-robin they would not. Trades depth for breadth across all consumers. A within-warmer scheduling change (in `src/`, under the freeze).

### O-G — Raise the budget / concurrency envelope on the existing cascade — *added*
- **Mechanism:** widen `Semaphore(3)` and/or the Lambda timeout so the single cascade reaches further into the task list (past 10,616 to 14,808).
- **Price vs table:** to reach offer's *end* (14,808) the warmer must roughly **double** its max-ever throughput (7,460 → ≥14,808). Concurrency alone is unlikely to close a ~2× gap within the 15-min Lambda ceiling, and **raising concurrency raises 429 pressure** — the documented storm surface (`asana-substrate-freshness` arc). Cheapest to *try*, least likely to *hold*; a partial raise still leaves entities 6–16 starved.
- **Cost:** highest regression risk (429 storms on entities 1–4 that currently work), lowest confidence of actually reaching offer. Listed for completeness; the shortfall is ordering-structural, not merely budget-structural.

### O-H — Decline to warm; disclosure-only (the null / baseline) — *added*
- **Mechanism:** accept the steady-state cold as a *ruled* condition and pair with the FINDING's disclosure remedy (surface `story_count` / `imputed: bool` + cache-gap counters) so option (g) reads **honestly empty** rather than falsely-observed. No warm, ever, by decision.
- **Price vs table:** zero warm cost; a `src/` change to the *read* payload (endpoint response), which is a deploy but **not a freshness-producer** (see §5 — no AL-5 re-arm). Renders option (g)'s offers table 100%-flagged-imputed but *honest* (PROBE §3.3 item 1: "makes option (g) *honest*, not *useful*").
- **Cost:** Mission A's retrospective half for offers stays empty. Only viable if F-1 judges option (g)'s retrospective half **not needed** for the mission — a product decision, not a platform one.

---

## 4. Two-sided receipt SHAPE — specified in advance, NOT built

**Problem it solves (from NR-4(d)):** today's 0-of-4,192 is **inferred** from an
aggregate counter (`success` < 10,616), not **measured** per-entity. A future
fix could "reach offer" while the aggregate still looks the same, and no metric
would distinguish "warmed offer" from "warmed 460 more of entity #3." The
receipt must make entity #5 a **first-class, always-emitted** dimension so the
floor becomes a measured zero and a fix becomes a visible step.

**Positive receipt — proves entity #5 was processed:**
- Emit, per entity, every run (proposed — NOT built): `story_warm_entity_complete { entity_type, project_gid, enumerated: bool, success: int, total_tasks_at_entry: int }`, and/or a CloudWatch `StoryWarmSuccess` with an `entity_type` dimension.
- **A fix is proven** when `story_warm_entity_complete{entity_type="offer"}.success` steps from **0** to **>0** (up to 4,192) — a positive, emitted value, not a metric that merely appears.

**The honest negative — what today's floor looks like, and what failure looks like:**
- The receipt MUST emit `offer.success = 0` **unconditionally every run** (even when zero), so that "warmed none" is a *measured* datum, not an *absent* one. This is the direct structural fix for NR-4(d): an absent `{entity=offer}` dimension is indistinguishable from `offer.success=0`; an always-emitted explicit `0` is not.
- Two distinguishable negatives, by design:
  - `offer.enumerated = true, offer.success = 0` → **budget starvation** (today's exact state: we reached offer's slice, warmed none). This is the honest negative the floor should show 324/324 runs.
  - `offer.enumerated = false` → **never reached** (a future ordering regression). Distinct from starvation; today this would be `false` at the *success* altitude but `true` at the *enumeration* altitude — which is precisely the asymmetry NR-4(d) leaned on.
- **Baseline to beat:** 0-of-4,192 across 324 runs / 14 d, currently *inferred*. Post-receipt the same floor is *measured* as an explicit `offer.success=0` time series; a working fix is the series leaving zero.
- **Two-sidedness:** the receipt bites only on real warming. A no-op deploy (telemetry only) leaves the series at 0 (correctly RED); a real warm moves it (correctly GREEN). It cannot show green without offer stories actually being written, because `success` increments only on `result is True` at `story_warmer.py:136`.
- **Freeze note:** the emission is a `src/` change (an `emit_metric` / `logger` call in `story_warmer.py`), so it is under the substrate-v2 P6 code freeze even though it warms nothing. The *alarm/dashboard* consuming it is Terraform (admissible). Instrumentation and warm-fix are separable: the receipt can ship first, alone, to convert the inferred floor to a measured one **without** touching freshness (see §5).

---

## 5. DF-4 — AL-5 producer-deploy interaction, priced per option

**The rule (given by the wave):** any WS-C fix is a **PRODUCER DEPLOY** and
moves/re-arms the AL-5 sample window (`asana-AL5-offer-frame-stale-1143843662099250`),
which **opens ~2026-08-15T12:45Z** [UV-P: window-open timestamp is the wave
briefing's figure | METHOD: read-only CloudWatch alarm-state inspection |
REASON: not re-verified own-hands this sprint; forward-looking sample-window
timing], **regardless of when the merge fence lifts.**

**Mechanism (why WS-C moves AL-5):** the story warmer *piggybacks on the same
cache-warmer Lambda invocation* as the frame warmer ("Strategy E", `story_warmer.py:40`).
AL-5 measures offer **frame** staleness; the frame warmer feeds it. Any WS-C
change to how that single shared time budget is spent (adding a ~6–8 min offer
story pass, reordering, raising concurrency) is a producer-of-freshness change
for the frame path too, and the deploy timestamp itself re-anchors the sample.
**R-9 trap (carry verbatim):** *do not misread a post-deploy AL-5 green as
staleness cured* — it may be the warm fix or the deploy, not the regime
(`project-offers-false-staleness-alarm-legs`).

**Clean-deploy windows and O-7a bookkeeping cost, per option:**

| option | is it a freshness-producer deploy? | when it can deploy WITHOUT disturbing the regime | O-7a regime-boundary bookkeeping cost if it can't |
|---|---|---|---|
| **O-A** offers-only warm | **Yes** | land **before 2026-08-15T12:45Z** (window opens on the post-fix regime, one clean regime) **or** after the sample closes | if it lands mid-window: annotate the deploy timestamp, **segment** the AL-5 series at the boundary, never average across it; carry the R-9 "not cured — warmed" caveat on every post-boundary reading |
| **O-B** offset rotation | **Yes** (intermittent) | before window open; **worse mid-window** — intermittent warming makes the boundary *fuzzy* (offers warm some runs, not others), so segmentation isn't a clean cut | O-7a must annotate *which runs* warmed offers, not a single boundary — highest bookkeeping cost of the warming options |
| **O-C** dedicated invocation | **Yes**, and it also changes the *frame* warmer's budget headroom (removes the story tail) | before window open; a dedicated story invocation *decouples* story from frame, which after one clean regime actually *reduces* future AL-5 coupling | mid-window: one clean boundary (invocation split is atomic) but the decoupling itself is a regime change to annotate once |
| **O-D** consumer-demand order | **Yes** | before window open | mid-window: boundary at the reorder deploy; plus the demoted entities' frames also shift — multi-entity boundary bookkeeping |
| **O-E** routed-out | **No deploy in this lane** | **N/A — zero AL-5 disturbance from here.** The named owner inherits the entire DF-4 pricing when *they* deploy. | **zero** in this lane |
| **O-F** round-robin | **Yes** (partial every run) | before window open; like O-B the boundary is fuzzy (partial warming every run shifts the regime gradually, not at a step) | gradual-regime annotation — arguably the hardest to segment cleanly, as there is no single "before/after" |
| **O-G** raise budget/concurrency | **Yes**, and it directly perturbs the frame warmer (shared Lambda) + adds 429 risk to entities 1–4 | before window open | mid-window: boundary plus a **confound** — a 429 storm from raised concurrency could itself spike frame staleness, contaminating AL-5 in the opposite direction |
| **O-H** disclosure-only | **No** (read-payload change, not a freshness producer) | **any time** — it does not touch the warm/frame regime AL-5 measures | **zero** — but it is still a `src/` deploy under the merge freeze |
| **receipt shape (§4)** | **No** (instrumentation only) | **any time** — emits counters, warms nothing, does not move frame freshness | **zero** — this is why the receipt can ship *first*, converting the inferred floor to a measured one on the *pre-fix* regime, cleanly, before AL-5 opens |

**DF-4 headline for F-1:** the cheapest DF-4 posture is to (i) ship the §4
receipt shape and/or choose O-E/O-H, none of which re-arm AL-5, and (ii) if a
warming option is chosen, land it **before 2026-08-15T12:45Z** to buy a single
clean regime — otherwise O-7a segmentation is mandatory and, for the
intermittent options (O-B/O-F), expensive and fuzzy. The merge fence lifting
does **not** relax this: the AL-5 window is on its own clock.

---

## 6. Merge-fence and reversibility notes (context for F-1, binds nothing)

- **Freeze scope:** substrate-v2 P6 fences v1 asana **`src/` code**; Terraform /
  observability is admissible (`project-offers-false-staleness-alarm-legs`). Every
  warming option (O-A/B/C/D/F/G), O-H's disclosure change, and the §4 receipt
  *emission* touch `src/` → under the freeze. Only the alarm/dashboard *consumer*
  side and O-E (no deploy) are freeze-clear.
- **Rollback lever if a warm fix ships:** the cache-warmer is a `PackageType:Image`
  Lambda; rollback = `update-function-code --image-uri <repo>@sha256:<digest>`
  against the pre-fix digest — capture `Code.ResolvedImageUri` **before** merge
  (`rollback-levers`). A pin edit cannot roll it back; the image is the only
  pinning artifact. This is a *note*, not a plan — validation of any rollback is
  Chaos Engineer's, post-implementation.
- **Charter fence:** the governing decision-space charter stops autonomous work
  at irreversibility and at anything touching credentials/spend/external
  commitment — which is why this slate prices and does not deploy.

---

## 7. NON-RECOMMENDATION (F-A / F-C honoured) — the decision axes F-1 must weigh

**This slate recommends NOTHING. It binds NOTHING.** F-1 (RE-1 ownership) remains
the operator's fork. The slate's job is done: the fork is now **priced**, not
blind. The axes F-1 must cross, in order:

1. **Is option (g)'s retrospective half actually NEEDED for Mission A?**
   - If **no** → **O-H** (disclosure-only) or **O-E** (route the fleet warmer out
     and don't build it here). Both are first-class, both ~zero DF-4 cost.
   - If **yes** → continue.
2. **Offers-only (Tier 1) or the full starved set (Tier 2)?** — the blast-radius
   fork. Tier 2 is the fleet-warmer redesign this lane is fenced from building →
   **O-E** (named owner) is the structurally-honest disposition for Tier 2.
   Tier 1 is a bounded in-repo job (O-A/B/C/D/F/G).
3. **If Tier 1: which lever?** — steady-state guarantee (O-C, most infra) vs
   intermittent-cheap (O-B/O-F, budget redistribution) vs targeted-pass
   (O-A, new API budget + 429 risk) vs demand-reorder (O-D, needs a demand
   signal that does not yet exist). O-G is listed but the shortfall is
   ordering-structural, not budget-structural, so a raise alone is low-confidence.
4. **Deploy timing vs AL-5** — whatever is chosen, ship the §4 receipt first
   (clean, no re-arm), and land any warming fix **before 2026-08-15T12:45Z** or
   pay O-7a segmentation.

**Standing hazard to carry to F-1 regardless of choice** (from PROBE §4): the
first authenticated call to `GET /api/v1/offers/section-timelines` returns a
payload ~100% imputed and **visually indistinguishable from a fully-observed
one** — reads as "these offers have not moved," should be read as "we have never
observed these offers." And because 4,192 misses ≫ 50, that call **writes
nothing** and does not improve the next one. Disclosure (the FINDING's remedy)
is necessary under *every* option except a real warm.

---

## 8. Verification scope

Read-only throughout. Source re-verified exclusively via `git show origin/main:<path>`
and `git grep origin/main` (MONOREPO TRAP honoured; no working-tree reads, no
reads of `/Users/tomtenuta/Code/a8/a8/repos/autom8y`). **No** AWS mutation, **no**
Lambda invoke, **no** Asana call, **no** terraform apply, **no** Redis read
(CR-5 STOP on the VPC-private cache — the ~100% imputation rate is carried as
INFERENCE per PROBE §5/§6, never reported as measured). **No** git mutation
(main thread owns git; this agent authored a file only). CR-2 verdicts bucket
untouched. Self-assessment ceiling **MODERATE** (F-C, single-seat, self-ref).
Rite-disjoint critic `remediation-planner` (arch) second-reads §1 NR-4.
