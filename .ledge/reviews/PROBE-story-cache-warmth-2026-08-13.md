---
type: review
status: draft
artifact_id: PROBE-story-cache-warmth-2026-08-13
initiative: asana-native-insight-delivery
date: 2026-08-13
probe_authorization: operator interview 2026-08-13 — "Full — live call permitted"
live_call_made: false
live_call_not_made_because: endpoint requires a caller-supplied Bearer credential (CR-5 STOP)
bears_on:
  - FINDING-option-g-imputation-indistinguishable-2026-08-12 (option (g) cost line)
  - DEFECT-temporal-filter-imputed-false-move-2026-08-12 (ACTIVE vs LATENT)
  - GATE-FORK / PT-02 fork briefing (operator-reserved, free until 2026-08-18)
verdict: COLD
grade: MODERATE (ceiling) — see §6
---

# PROBE — is the Asana story cache warm for the offers project, independent of `section-timelines`?

## 1. VERDICT — **COLD**

**Measured**: **0 of 4,192** offer tasks were reached by the only independent
story-cache warm path, across **59 consecutive warmer runs in 3 days** and
**324 runs in 14 days**. Not once. Not partially.

The cache is cold **because nothing warms it** — a structural, steady-state
condition. This is *not* a cold-cache-first-call artifact: **no live call was
made** (see §2), so no measurement here was contaminated by a first-ever
invocation.

The coldness has a precise, quantified mechanism:

| quantity | value | receipt |
|---|---|---|
| offer DataFrame rows (task GIDs) | **4,192** | `entity_warm_success` log, `row_count=4192`, every cycle |
| tasks the warmer must traverse before reaching the first offer task | **10,616** | business 2,574 + unit_holder 2,086 + unit 3,089 + asset_edit_holder 2,867 |
| offer's slice in the warmer's iteration | cumulative **10,617 – 14,808** | `story_warm_timeout_exit` cumulative sequence |
| **max tasks the warmer ever processed** (59 runs / 3 d) | **7,460** | Logs Insights, §2 probe D |
| **max stories warmed in one run** (14 d, 324 runs) | **8,527** | CloudWatch `StoriesWarmed` daily Maximum |
| shortfall to the *first* offer task | **≥ 2,089 tasks** | 10,616 − 8,527 |
| runs that reached the offer slice | **0 of 59** | §2 probe D |

The warmer exhausts its Lambda time budget inside the first three-to-four
entities every single run and then breaks out of every subsequent entity
immediately. Offer is entity **#5** in the cascade order. It is never reached.

**Derived** (inference, not a direct key count — see §5): because the warmer is
the *only* live writer (§3), the offers story cache holds **no live entries**,
so a `section-timelines` call today would take the `cache_misses` branch for
essentially every offer → **imputed fraction ≈ 100%**.

---

## 2. Method — cheapest first, in order

Every step is read-only. No Asana call, no write of any kind, no Slack, no
Lambda invoke, no terraform, no git mutation. All source read via
`git show origin/main:<path>` (MONOREPO TRAP honoured).

### Probe A — is there an independent warm path at all? (cheapest: source read)

`git grep -n "EntryType.STORIES" origin/main -- src` and
`git grep -n "list_for_task_cached_async" origin/main -- src` →
**exactly three** story-cache write sites exist in the whole service:

| # | site | status |
|---|---|---|
| 1 | `src/autom8_asana/lambda_handlers/story_warmer.py:91` | the piggyback cache-warmer — the only independent path |
| 2 | `src/autom8_asana/services/section_timeline_service.py:334` | inside `build_timeline_for_offer` (`:303`) — **zero callers in `src/`**; dead |
| 3 | `src/autom8_asana/services/section_timeline_service.py:511` | inline backfill *inside the endpoint itself* |

All three funnel through `cache/integration/stories.py:179` (`cache.set_versioned`).
So the question reduces to: **does site #1 reach offer tasks?**

### Probe B — is the warmer firing at all? (cheap: CloudWatch metrics)

Live namespace is `autom8y/cache-warmer` (not the `autom8/lambda` default, whose
`StoryWarm*` series carry 15 samples in 14 days, **all zero**).

```
aws cloudwatch get-metric-statistics --namespace autom8y/cache-warmer \
  --metric-name StoriesWarmed --dimensions Name=environment,Value=staging \
  --start-time 2026-07-30T06:22:51Z --end-time 2026-08-13T06:22:51Z \
  --period 86400 --statistics Sum SampleCount Maximum --region us-east-1
```

14-day result: **23–26 runs/day, 103,433–143,731 stories warmed/day**, and
critically **daily Maximum per run 6,761 – 8,527**. The warmer is healthy and
busy — and its per-run ceiling is ~8.5k.

### Probe C — where does `offer` sit in the warm order? (cheap: Logs Insights)

`/aws/lambda/autom8-asana-cache-warmer`, `filter @message like /entity_warm_success/`,
12h window. The cascade order is stable and identical every cycle:

```
1 business              2,574     cum  2,574
2 unit_holder           2,086     cum  4,660
3 unit                  3,089     cum  7,749
4 asset_edit_holder     2,867     cum 10,616
5 offer                 4,192     cum 14,808   <-- offers project 1143843662099250
6 contact              23,484     cum 38,292
7 asset_edit           14,666     cum 52,958
8..16 process_*          5,320 …   cum 59,278
```

The offers project GID is confirmed from the same log group:
`entity_project_registered_from_model {'entity_type': 'offer',
'project_gid': '1143843662099250', 'project_name': 'business offers'}`.

### Probe D — does the warmer ever get that far? (the decisive probe)

`story_warmer.py:114` checks `_should_exit_early(context)` before each 100-task
chunk (`:111`) and `break`s. `stats["total_tasks"] += len(task_gids)` (`:85`)
runs *before* the chunk loop, so every post-timeout entity still logs a
`story_warm_timeout_exit` carrying the **cumulative** `total_tasks`. That
sequence is a free, exact readout of the iteration order and position.

3-day Logs Insights reconstruction, **59 invocations**:

```
invocation   processed  success  grand_total  cumulative breakpoints
bf4b195d          7160     7116        59273  [7750, 10617, 14809, 38292, 52954, 54437]
426344e3          7060     7060        59274  [7750, 10617, 14809, 38293, 52955, 54438]
9c770017          7460     7455        59279  [7750, 10617, 14809, 38293, 52958, 54441]
...                  (59 rows, identical breakpoint structure)

invocations where tasks_processed exceeded 10,616 (offer reachable): 0 of 59
max tasks_processed observed: 7,460
max success observed:         7,455
```

14-day corroboration (`story_warm_complete`, 324 runs, `recordsMatched: 324`):
daily `max_success` ranges **6,760 – 8,526**; daily `max_total` **57,143 – 59,281**.
**8,526 < 10,616.** Two independent data sources (CloudWatch metrics and Logs
Insights) agree to within one task.

> The offer DataFrame *is* retrieved successfully — the cumulative jump of
> exactly 4,192 at breakpoint #5 proves `dataframe_cache.get_async` returned it
> and its `gid` column was enumerated (`story_warmer.py:84`). This is **not** a
> missing-DataFrame failure. It is pure **ordered budget starvation**: the loop
> enumerates offer's 4,192 GIDs and then breaks on the very first chunk.

### Probe E — could the endpoint itself have warmed it? (independent re-verification)

I did not inherit this premise; I re-ran it.

```
log group : /ecs/autom8y-asana-service        window: 14 days -> 2026-08-13T06:2xZ
filter    : /section-timelines|section_timelines|timeline_computed_on_demand|
             story_cache_gap_above_threshold|inline_story_fetch|timeline_derived|
             timelines_computed/
queryId   : c8947d8d-ff09-4711-b40a-6c8bdee817f5
result    : MATCHED ROWS: 0    recordsScanned: 3,849,973    bytesScanned: 1.72 GB
```

**0 matches out of 3,849,973 scanned records.** The control is built in: 3.85M
records scanned means the group is live, not a dead-group false negative. The
prior finding's claim is **independently reproduced**.

### Probe F — same cache on both sides? (rules out a cross-cache confound)

- Lambda `autom8-asana-cache-warmer` env: `REDIS_HOST = master.autom8y-asana-redis.zckwpk.use1.cache.amazonaws.com`
- ECS task definition `autom8y-asana-service:765` env: **the same** `REDIS_HOST`

Both `AUTOM8Y_ENV = production`. So the warmer's writes *would* be visible to the
endpoint. Coldness is not an artifact of two disjoint caches.

Neither carries `ASANA_CACHE_TTL_DEFAULT`, so `ttl_default = 300` s
(`settings.py:148`) is the resolved default, and `_create_stories_entry`
(`cache/integration/stories.py`) sets no per-entry TTL. Corroborating retention
pressure from `AWS/ElastiCache` on `autom8y-asana-redis-001` (3 d):
`DatabaseMemoryUsagePercentage` peaks **99.92%**, `Evictions` up to **4,870** in a
6 h window, `CurrItems` **56,631 – 89,374 across all entry types combined**
(the task universe alone is 59,278). Nothing here supports a >14-day survival of
story entries written in some earlier era.

### Why I did **not** make the live call

`/api/v1/offers/section-timelines` is mounted on `pat_router`
(`api/routes/section_timelines.py:41`) and the whole `/api/v1/offers/*` tree is
**JWT-excluded** (`api/main.py:434`) precisely because it uses PAT / dual-mode
auth. The dependency raises at `api/dependencies.py:93`:

```
raise ApiAuthError("MISSING_AUTH", "Authorization header required")
```

Calling it therefore requires **either** the bot PAT (extracted from Secrets
Manager via `get_bot_pat()`) **or** a minted S2S JWT from the autom8y auth
service. **HARD CONSTRAINT 5 names exactly this shape as a STOP.** I did not
mint, extract, copy, or log any credential, and none appears in this artifact.

**What the live call would have required**: one of —
(a) read `arn:aws:secretsmanager:...:autom8y/asana/...` bot-PAT secret and place
it in an `Authorization: Bearer` header; or
(b) obtain an S2S JWT from the autom8y auth service with `require_business_scope`
satisfied. Both are credential handling. Operator-only.

**And it was not needed.** The log/metric chain is *stronger* than the call would
have been, for two reasons:
1. The call measures one instant; the metric chain measures 14 days × 324 runs of
   steady state.
2. The call would itself have been the first-ever invocation — the exact
   cold-cache first-impression confound the source FINDING warned about
   (`FINDING-…-2026-08-12` §UV-P-10, consequence 3).

---

## 3. The three consequences

### 3.1 Is option (g) returning real history or imputed placeholders? At what rate?

**Imputed placeholders, at approximately 100%.**

Precise mechanics, verified at `origin/main`:

- `read_stories_batch` returns `None` for a task with no cache entry
  (`cache/integration/stories.py:63`, `:36`).
- `None` → `cache_misses += 1` (`section_timeline_service.py:604`) → a single
  imputed interval at `[created_at, None]` carrying the offer's **current**
  classification (`:608` → `_build_imputed_interval` `:272`), `story_count=0`.
- A cache **hit** can *also* be imputed: `:560` counts the hit, but if the
  filtered `section_changed` set is empty, `:586` imputes anyway and forces
  `story_count = 0`. **So the imputed fraction is ≥ the miss fraction, never below it.**

With no live entries for offer GIDs, `cache_misses ≈ total_tasks`, so the whole
offers payload would be synthetic: *every offer reported as having occupied its
current section since creation.* And per the source FINDING, the caller cannot
tell — `story_count` is dropped at the response boundary
(`models/business/section_timeline.py:158`, seven fields, `extra="forbid"`).

**A new mechanical consequence that changes the disposition: option (g) cannot
bootstrap itself.** Inline self-healing runs only for
`0 < len(misses) <= MAX_INLINE_STORY_FETCHES` where the constant is **50**
(`:502`, `:505`). With ~4,192 misses the `elif len(misses) > MAX_INLINE_STORY_FETCHES`
branch fires (`:532`), logs `story_cache_gap_above_threshold` (`:534`) **and
proceeds**. Nothing is written. **Calling the endpoint repeatedly will never warm
it.** The only writer that could is the starved warmer.

So option (g) today is not "a retrospective source that happens to be a bit
imputed." It is a retrospective source that returns **no retrospect at all** for
this project, in a payload shaped exactly like one that does.

### 3.2 Is the `TemporalFilter` defect ACTIVE or LATENT?

**ACTIVE.** Maximally so.

The defect's stated precondition is: *offers with zero cached stories receive one
imputed interval whose `entered_at` is `created_at` and whose classification is
the offer's current one.* This probe measures that precondition to hold for
**essentially the entire offer population, right now, and continuously for at
least 14 days.**

The defect artifact reasoned that the imputed population is "disproportionately
the newly created population." That reasoning was conservative. The measured
truth is worse: the imputed population is **not a sub-population** — it is the
whole population. A `moved_to` + `since`/`until` query without `moved_from` never
reaches the `idx == 0` guard, so every offer whose `created_at` lands in the
window is returned as having moved. Today that is *every* offer created in the
window, with no observed-history offers to dilute it.

**One honest bound**: I measured that the *defect condition* is satisfied — wrong
answers are produced whenever the surface is exercised. I did **not** measure how
often anyone exercises `query/__main__.py:875/:893/:920`. Exploitation frequency
is undetermined. ACTIVE is a statement about correctness, not about traffic.

The `moved_from` workaround remains sign-inverted, unchanged by this probe:
it drops every offer's genuine first move
(`_build_intervals_from_stories` synthesises no pre-first interval).

### 3.3 What does this do to Mission A's cost line?

The FINDING moved option (g) from *"already paid for"* to *"already built, and
carrying an instance of the defect this crusade just closed."* This probe moves
it one rung further: **"already built, never exercised, and currently sourced from
an empty cache that nothing is filling."**

Concretely, the cost line gains a line item the disclosure remedy does not cover:

1. **Disclosure alone now yields an honestly empty readout.** Surfacing
   `story_count` / `imputed: bool` + the cache-gap counters (the FINDING's
   precondition) is still necessary — but applied today it would render a table
   that is 100% flagged imputed. It makes option (g) *honest*, not *useful*.
   The S1/FINDING synthesis ("sound for duration-shaped questions, unsound for
   occurrence-shaped ones") also degrades: with zero observed history, the
   *duration* readout is likewise pure `now − created_at` for every row.

2. **A story-warm for offers becomes a precondition, not a nicety.** Two shapes:
   - *Fix the starvation.* The story-warm budget is consumed by entities 1–4
     every run; entities 5–16 (offer, contact, asset_edit, all nine `process_*`)
     have received **zero** story warming for at least 14 days. Candidate fixes:
     rotate the iteration start offset across runs; give story warming its own
     invocation rather than piggybacking on the tail of a deadline-bound warmer;
     or order by consumer demand rather than cascade order. This is a
     **fleet-wide** repair — offers are one of twelve starved entities.
   - *Or add an offers-specific warm.* 4,192 tasks at the observed rate
     (~7,000 tasks per ~560–770 s at `asyncio.Semaphore(3)`,
     `story_warmer.py:91`) is roughly **6–8 minutes** of dedicated warming per
     pass. Cheap in absolute terms — but it is **new work that option (g) was
     costed as not needing**, plus recurring Asana API budget.

3. **Then, and only then, is there a measurement to take.** UV-P-10 (how heavily
   does option (g) impute?) still cannot be sized from logs, because the endpoint
   still has zero traffic. But sizing it *before* a warm would only re-measure
   ~100%. The correct order is: warm → then measure → then decide.

**Net for PT-02**: option (g)'s retrospective half is reachable *in principle* and
the endpoint is genuinely built and contracted — none of S4's structural findings
are refuted. What is refuted is the assumption that its data substrate exists.
It does not, today. The fork briefing should carry option (g) with two
preconditions, not one: **(i)** disclose the imputation, **(ii)** warm the story
cache for the offers project — and note that **(ii) is a fleet-wide warmer repair
whose blast radius is twelve entity types, not one.**

*Nothing is ruled here. GATE-FORK remains operator-reserved and free until 2026-08-18.*

---

## 4. ⚠ COLD-CACHE CAVEAT

**No live call was made.** Therefore no result in this artifact is a
first-invocation artifact, and the distinction the operator asked for is clean:

> **The cache is cold because nothing warms it — not because this is the first call.**

The evidence for that distinction is the 14-day, 324-run, two-source measurement
of the *warm path*, not of the *read path*. The warm path is healthy, busy, and
structurally incapable of reaching offers. Its per-run ceiling (8,527) sits
2,089 tasks short of offers' first GID (10,617), every run, for 324 consecutive runs.

**Standing hazard for whoever calls it next**: the first real call to
`GET /api/v1/offers/section-timelines` will return a payload that is
~100% imputed and **visually indistinguishable from a fully-observed one**. It
will read as *"these offers have not moved."* It should be read as
*"we have never observed these offers."* And because 4,192 misses ≫ 50, that call
will **not** improve the next one.

---

## 5. What I could not determine — named gaps

1. **A direct key count of `EntryType.STORIES` entries for the 4,192 offer GIDs.**
   *I could not verify this by direct inspection.* The cache is ElastiCache
   (`autom8y-asana-redis-001`) in a private VPC: `nslookup
   master.autom8y-asana-redis.zckwpk.use1.cache.amazonaws.com` → *"connection timed
   out; no servers could be reached"*, and reading it would additionally require
   the auth token at `arn:aws:secretsmanager:...:autom8y/asana/redis-auth-token-…`
   (CR-5 STOP). **The COLD verdict is therefore an inference** — from "the only
   writer never fires for these keys" + "TTL is 300 s by default" + "Redis is at
   99.9% memory with active evictions" — **not a key enumeration.** A residual
   possibility I cannot exclude from this seat: a small number of offer GIDs that
   are *also* members of another warmed entity's DataFrame (a task appearing in
   both `business offers` and an earlier project) could carry live story entries.
   I saw no mechanism producing that and did not probe it.

2. **Traffic on `query/__main__.py` (the `TemporalFilter` consumer).** Not
   measured. ACTIVE in §3.2 is a correctness claim; how often the wrong answer is
   actually *served* is unknown.

3. **Whether the starvation is a regression or has always held.** The 14-day
   window is uniform (max per-run 6,760–8,526 throughout). I did not look
   further back, so I cannot date the onset.

4. **`StoryWarmFailure` step-change.** Daily failure sums jump from 15–47
   (Jul 30 – Aug 4) to 163–439 (Aug 5 – Aug 12). This is inside the
   business/unit_holder/unit population, not offers, so it does not bear on this
   verdict — but it is unexplained and worth its own look.

5. **Non-enforcement of the story overflow threshold.** `OverflowSettings.stories
   = 100` (`cache/models/settings.py:29`) would exclude high-story tasks from the
   cache — but `git grep -n "should_cache" origin/main -- src` returns **only its
   own definition sites** (`:50`, `:173`, `:183`) and **no call site**. I had
   expected this to be an additional bias source; it is not — it is dead config.
   Recorded so no one else re-derives it as a live finding.

6. **The `autom8/lambda`-namespace `StoryWarm*` series** (15 samples in 14 days,
   all zero) — I did not identify which function emits it. It warms zero stories
   either way, so it does not change the verdict.

---

## 6. Grade

**MODERATE (ceiling)** per `self-ref-evidence-grade-rule` — single-seat
self-attestation, no rite-disjoint corroboration obtained. Stratified:

| claim | strength | why |
|---|---|---|
| "0 of 59 warmer runs reached the offer slice; max processed 7,460 vs offer start 10,617" | strongest tier available to a single seat | deterministic re-runnable probes; N=59 and N=324; **two independent sources** (CloudWatch metrics + Logs Insights) agree to within one task; arithmetic reconciles exactly against `entity_warm_success` row counts |
| "0 `section-timelines` invocations in 14 days" | strongest tier available to a single seat | 0 matched / 3,849,973 scanned, with a live-group control built into the same query; independently reproduces the prior finding rather than inheriting it |
| "the warmer is the only independent writer" | strong | exhaustive source grep at `origin/main` over a closed call graph; the two other sites are dead / inside the never-called endpoint |
| **"the offers story cache holds no live entries → ~100% imputation"** | **MODERATE — this is the ceiling** | **inference**, not a key enumeration; direct Redis inspection was blocked by VPC + CR-5 (§5 gap 1) |

The ceiling is set by the last row. Everything upstream of it is measured;
the imputation *rate* is derived. Upgrade path: one authenticated
`GET /api/v1/offers/section-timelines` call (operator-only, credential-bearing)
would emit `timeline_computed_on_demand` (`section_timeline_service.py:653`) with
exact `cache_hits` / `cache_misses`, and `story_cache_gap_above_threshold`
(`:534`) with an exact `miss_count` — converting the derived rate into a measured
one. Because 4,192 misses ≫ 50, that call writes nothing and is safe to repeat.
It remains, per CR-5, an operator action.

---

## 7. Verification scope

Read-only throughout. Source read exclusively via `git show origin/main:<path>`
(MONOREPO TRAP honoured; no working-tree reads, no reads of
`/Users/tomtenuta/Code/a8/a8/repos/autom8y`). AWS: CloudWatch `list-metrics` /
`get-metric-statistics`, Logs Insights `start-query` / `get-query-results`,
`logs describe-log-groups`, `lambda get-function-configuration`,
`ecs describe-services` / `describe-task-definition`,
`elasticache describe-replication-groups`, `sts get-caller-identity`.
**No HTTP request to any application endpoint. No Asana call of any kind. No
write, no Slack post, no Lambda invoke, no terraform, no git mutation.** The
`autom8y-asr-verdicts` S3 bucket (CR-2, operator-reserved) was **not** read and
was not needed. No credential was minted, extracted, copied, or logged, and none
appears in this artifact.
