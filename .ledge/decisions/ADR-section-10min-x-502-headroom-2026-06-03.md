---
type: decision
adr_id: ADR-section-10min-x-502-headroom-2026-06-03
title: "SECTION ≤10-min freshness × 502 build-capacity headroom — joint design"
status: draft
decision_state: authored-not-ratified
rite: sre
authors: [chaos-engineer, platform-engineer]
date: 2026-06-03
initiative: cr3-fleet-data-plane-foundation-cutover
evidence_grade: moderate   # self-ref sre rite authored the substrate; MODERATE ceiling.
                           # The ONLY STRONG claims are the two consumer-corroborated PQ-3/OQ corrections (OQ-1 width, OQ-4 cred), cited inline.
reversible_only: true      # DESIGN ONLY — no apply, no deploy, no value bump, no merge. FROZEN=4 holds.
supersedes_consideration: ["#97/#338 held fast-lane (15-min, 2 GIDs) — assessed §B; likely re-scoped, not deployed as-is"]
grounding:
  - .ledge/handoffs/HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md
  - /Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2026-06-03.md   # OQ-1..4 ANSWERED
  - .sos/wip/cr3-verified-findings-2026-06-03.md
  - .sos/wip/cr3-producer-sprint-ledger-2026-06-03.md
  - .claude/agent-memory/platform-engineer/warm-cadence-vs-lkg-ceiling-tension.md
  - .claude/agent-memory/platform-engineer/asana-dataframe-resolver-cred-topology.md
ratification_gates:
  - "SIZING (§A) value bump: human/IC-gated land — max_concurrent_builds raise is INERT and DANGEROUS without the CPU/mem bump landing FIRST."
  - "SECTION lane (§B) deploy: downstream of the §C gated land; the headroom bump precedes the lane deploy."
  - "FINAL ≥99% re-gate (§D): DOWNSTREAM of the §C gated land — MUST NOT run on the current substrate."
---

# ADR — SECTION ≤10-min freshness × 502 build-capacity headroom (joint design)

> **DESIGN ONLY.** Nothing in this doc is applied, deployed, merged, or value-bumped. `max_concurrent_builds`
> stays **FROZEN=4** (`build_coordinator.py:131`, `settings.py:305`) until the §C human/IC-gated land pass.
> Every platform claim carries an SVR `file:line` / aws-resource receipt or is marked **UV-P**. Self-ref
> MODERATE ceiling: this rite authored the substrate, so no PASS/STRONG self-certification — the only STRONG
> claims are the two consumer-corroborated corrections (OQ-1 width, OQ-4 credential), cited at source.

## §0. The tension (restated, source-anchored)

SECTION must serve at **≤10-min freshness** AND is the **502 build-capacity hotspot** — and these are NOT
separable on SECTION the way they are on project/analytics.

- **Consumer freshness contract (OQ-2, ratified from monolith source-of-truth, NOT a strawman):** per-entity
  `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` — **PROJECT=86400s (24h)**, **SECTION=576s** (`0.16×3600`; the literal
  source value — the `~10min`/`600s` shorthand used elsewhere in this doc is the `caching.py:39` comment gloss),
  **ANALYTICS/BACKFILL=86400s (24h)**, VERTICAL-SUMMARY sub-tier=2592000s (720h). **NB (land correction, per
  sprint-ledger Gate 2/6):** of these tiers only **`project` and `section` bind to a receiver `entity_type`**
  (`entity_registry.py:885,925`); `analytics`/`backfill`/`vertical-summary` have NO matching entity and are
  **dead keys** — the calibrated knob (PR #102) is therefore exactly `{"project":86400, "section":576}`. Source:
  `config/thresholds/caching.py:39 SECTION_DF_REFRESH_HOURS: float = 0.16` (comment "~10 minutes. Sections
  change more frequently than projects") and `:33 PROJECT_DF_REFRESH_HOURS: int = 24`
  (consumer return HANDOFF, OQ-2 tier table). [MODERATE → corroborated by rite-disjoint consumer QA that
  each tier traces to a `caching.py:line` + verified consumer cadence]
- **Current receiver ceiling:** `LKG_MAX_STALENESS_MULTIPLIER = 10.0` (`config.py:115`) × project/section
  TTL=300s (`config.py:91 DEFAULT_TTL: int = 300`) = **3000s / 50-min** hard-reject ceiling. Gate:
  `dataframe_cache.py:531-546` (`age > max_age → return None → cache-miss → build → 503`). [STRONG, code-anchored]
- **The asymmetry:** PROJECT and ANALYTICS at 24h ride LKG-serve comfortably (their 502 pressure collapses —
  a frame an hour old is trivially within a 24h contract, so it serves stale and never builds on-miss).
  **SECTION at 600s cannot serve-stale-longer to dodge capacity** — it is the entity that needs the freshest
  data, and the 50-min internal ceiling is *looser* than its 600s contract, so even a within-ceiling frame
  can be contract-stale. The freshness need and the capacity hotspot coincide on exactly one entity.

The load-bearing consequence: tightening SECTION freshness (knob → 600s) makes section frames hard-reject +
rebuild **far sooner** than the old 50-min ceiling did → **more on-demand section builds → more semaphore
pressure → more 502s.** We cannot relax SECTION to relieve capacity; we must (a) give the build path enough
headroom to absorb the warm-miss/cold tail, and (b) install a ≤10-min SECTION warm lane so steady-state
reads hit serve-within-bound and never reach the build path at all.

---

## §A. SIZING — `max_concurrent_builds` target + matched CPU/mem

### A.1 Residual SECTION build-key contention (the number that sizes the lever)

The monolith fans out at `max_workers=10` (`apis/asana_api/objects/project/refresh_frames.py:115`
`with ThreadPoolExecutor(max_workers=10)`) over a ~34-GID warm-set class snapshot
(`refresh_frames.py:92`), each `get_df(sections="ALL")` decomposing into `{project, section}` build-keys →
**~20 concurrent build-keys** contend for `max_concurrent_builds=4`. **[STRONG — OQ-1, rite-disjoint
consumer live-source verification at `refresh_frames.py:115`/`:92`; this is one of the two STRONG corrections
this rite is permitted to assert]**

The receiver coalesces by `(project_gid, entity_type)` (`build_coordinator.py:51,54`), so the pressure is
**breadth of distinct keys, not depth on one key**. Under the serve-stale paradigm (V6, already implemented):

| Scenario | Total in-flight keys | PROJECT arm (24h) | SECTION arm (600s) | **Residual SECTION build-keys** | vs 4 slots |
|----------|----------------------|-------------------|--------------------|-----------------------------------|------------|
| **A — `max_workers=10` (live, unthrottled)** | ~20 (10×{project,section}) | rides LKG-serve, **no build** | builds on warm-miss | **~10** | **~2.5× overshoot** |
| **B — consumer throttle toward `max_workers=4`** | ~8 (4×{project,section}) | rides LKG-serve, **no build** | builds on warm-miss | **~4** | **~1.0× (just fits)** |

The decisive insight: under serve-stale, **PROJECT/ANALYTICS keys do not contend for the build semaphore at
all** (they LKG-serve their loose contract), so only the **SECTION arm** is the real contender. That is why
this is a SECTION problem, and why the headroom only has to cover the SECTION residual + cold tail — NOT all
~20 keys. The consumer OFFERS a client-side `max_workers` throttle toward 4 (OQ-1; "one-line client change,
no receiver relaxation") which alone collapses Scenario A → B. We do not depend on it, but we size for both.

### A.2 Recommended `max_concurrent_builds` target + matched task size

Memory is the binding constraint. Each Polars section build ≈ **~2GB** resident
(`cache_warmer.py:88-89` "single heavy GID … ~30k rows … OOM"; sizing rationale `lifespan.py:232-234`).
Usable RAM after ADOT 256MB sidecar:

| cpu / mem | Usable after ADOT 256 | Safe concurrent ~2GB builds | Verdict for SECTION residual |
|-----------|------------------------|------------------------------|------------------------------|
| **1024 / 2048 (CURRENT)** | ~1792 MB | **~0–1** | Cannot safely run even 2 heavy builds; today's `max_concurrent_builds=4` is **already over-provisioned vs RAM** — the semaphore admits 4 but the box OOMs/thrashes past ~1. This is the latent danger the handoff names. |
| **2048 / 4096** | ~3840 MB | ~1 | Matches a `max_concurrent_builds=2` target under throttle (Scenario B). Minimum viable. |
| **2048 / 8192** | ~7936 MB | **~3** | **RECOMMENDED.** Matches `max_concurrent_builds=4` (keep the value, make it HONEST vs RAM) under throttle; absorbs Scenario-A bursts to ~3 concurrent before backpressure. |
| 4096 / 16384 | ~16128 MB | ~7 | Matches `max_concurrent_builds=6–8` for unthrottled Scenario A with margin; higher cost — defer unless throttle is refused AND warm-miss tail proves wide at re-gate. |

**Recommendation (DESIGN, not applied):**
- **Target `max_concurrent_builds` = 4** (i.e. KEEP the frozen value) **paired with cpu=2048 / mem=8192** —
  this makes the existing semaphore value *truthful* against RAM (~3 safe 2GB builds) rather than a latent
  OOM trap, and gives the SECTION residual (Scenario B ~4, Scenario A burst ~10 over time) real headroom with
  Retry-After backpressure (`errors.py:621-638`, V4 ✓) as the safety valve beyond ~3 concurrent.
- **If the consumer applies the OQ-1 throttle (max_workers→4):** `max_concurrent_builds=2` + cpu=2048/mem=4096
  is sufficient and cheaper; the SECTION residual (~4) is then absorbed by the warm lane (§B) + 2 build slots
  + Retry-After, with project/analytics fully on LKG-serve.
- **Single-worker constraint (no bump implied for SECTION):** the API runs **one uvicorn worker**
  (`entrypoint.py:52-57`, no `workers=` arg; `lifespan.py:232` "conservative for single-worker uvicorn").
  The `BuildCoordinator` semaphore and the `cpu_thread_concurrency=4` `to_thread` cap (`settings.py:276-285`)
  are **in-process** controls that already gate CPU-bound Polars work within the single worker. **A worker bump
  is NOT recommended:** multiple uvicorn workers would each instantiate an independent `BuildCoordinator`
  semaphore (constructed per-event-loop in `lifespan`, `lifespan.py:226-237`), multiplying effective build
  concurrency by the worker count and *defeating* the `max_concurrent_builds` cap — N workers × 4 slots × 2GB
  would OOM any reasonable task. Keep one worker; scale builds via the semaphore value + RAM, not workers.
  `cpu_thread_concurrency` should track `max_concurrent_builds` (the `settings.py:273` comment already binds
  them: "Sizing = max_concurrent_builds").

**FROZEN discipline:** the value-change above is a **DESIGN RECOMMENDATION**. `max_concurrent_builds` stays
**4** and **no `.tf`/task-sizing file is touched** until the §C gated land. The lever is **inert and
dangerous** without the CPU/mem bump landing FIRST (PQ-1 acceptance #5).

---

## §B. SECTION-TIGHT WARM LANE — a ≤10-min cadence so reads serve-within-bound

**Goal:** make the steady-state SECTION read find a frame **<600s old** → serve FRESH/SWR (within bound) →
no on-demand build → no 502. The §A headroom then only has to cover the **warm-miss / cold tail** (a GID the
lane has not yet reached, a cold start, or a freshly-registered GID), not the steady state.

### B.1 Why the current lanes do not meet 600s (source-anchored)

| Lane | Schedule | Coverage | Inter-warm interval | vs 600s SECTION contract |
|------|----------|----------|---------------------|--------------------------|
| offer warmer | `cron(0 */4 * * ? *)` (live: `autom8-asana-cache-warmer-schedule`) | offer domain (NOT project/section) | 4h | irrelevant to section |
| **bulk warmer** | `cron(0,30 * * * ? *)` (live: `autom8-asana-cache-warmer-bulk-schedule`, ENABLED) | 68 keys = 34 GID × {project,section} | **~46 min** for heaviest GID (sweep ~40–50min > 30-min tick) | **MISS — 46min ≫ 600s** |
| held fast-lane #97 (NOT deployed) | 15-min, 2 heaviest GIDs only | 4 keys = 2 GID × {project,section} | ~20.5 min for those 2 GIDs | **MISS — 15min tick & 20.5min interval > 600s; and only 2 of 34 GIDs** |

Live receipts: bulk `cron(0,30 * * * ? *)`, mem=2048, timeout=900, **ReservedConcurrentExecutions=1**,
LastMod 2026-06-03T09:06:11Z (`aws lambda get-function-concurrency / describe-rule`, this session). Fast
warmer = **ResourceNotFound** (`aws lambda get-function-configuration autom8-asana-cache-warmer-fast`) —
confirms #97/#338 NOT deployed. Heaviest-GID timing: BusinessUnits 17 sections, per-section fetch
**38s–326s**, rebuild **~5.5min**, ~46min inter-warm (`warm-cadence-vs-lkg-ceiling-tension.md:10-14`,
CRG-3 gameday 2026-06-03 06:59Z — BusinessUnits SOLE 503 GID, 10/10, frame aged ~2h ≫ 3000s ceiling).
[STRONG, code+aws+gameday-anchored]

**Conclusion: neither existing lane meets 600s, and the held fast-lane is doubly insufficient** (cadence still
>600s AND only 2 of 34 GIDs). The 15-min fast lane was designed against the OLD 50-min ceiling, not the now-
ratified 600s contract — it is **superseded** by this requirement.

### B.2 Shape decision: a SECTION-ONLY lane over the full section warm-set, NOT an extended fast-lane

**Decision: add a third lane — a SECTION-ARM-ONLY warm lane over all 34 GIDs at a ≤10-min cadence** — rather
than extend the 2-GID fast-lane. Rationale:

1. **The contract is per-entity-type, not per-GID.** OQ-2 binds SECTION=600s for *all* sections, not the 2
   heaviest. A 2-GID fast-lane leaves 32 GIDs' sections governed only by the 46-min bulk sweep → 32 contract
   violations. The lane must cover the **section arm of the whole warm-set**.
2. **The machinery already exists and is lane-generic.** `_prematerialize_bulk_set_async`
   (`cache_warmer.py:247-557`) drives bulk AND fast lanes from ONE coroutine; the only differences are the
   `key_source` callable and the `fast_lane` continuation flag (`cache_warmer.py:286-307,344,448-449`). A
   SECTION lane is a **third `key_source`** — `section_only_prematerialization_keys()` yielding
   `[(gid, "section") for gid in consumer_warm_set_gids()]` (34 keys, mirroring
   `bulk_prematerialization_keys` `project_registry.py:294-327` but arm-restricted) — plus a third event flag
   `prematerialize_section_set` and a disjoint checkpoint prefix. **No new build/merge/coverage code.**
3. **Lane isolation is already solved.** Disjoint `CACHE_WARMER_CHECKPOINT_PREFIX` per-Lambda (#96, merged;
   `cache_warmer.py:289-293`) gives each lane its own `latest.json` so checkpoints never contend. The SECTION
   lane gets its own prefix (e.g. `section-fast/`), disjoint from bulk (`bulk/`) and offer.
4. **Backstop invariant preserved.** The section lane is a strict subset of the bulk sweep's section arm, so
   if the section lane stalls, the 30-min bulk still covers every section key (the same structural backstop the
   fast-lane asserts at `project_registry.py:352-359`). Add the analogous module-load assertion.

### B.3 Lambda budget feasibility — the load-bearing constraint

A ≤10-min cadence over 34 section keys is the hard part. Per-link wall-clock at one reserved slot:

- Section sweep cost ≈ Σ section-build time over 34 GIDs. The heaviest single GID (BusinessUnits) alone is
  ~5.5min; a serial 34-key section sweep is **≫ 10min** — it **cannot complete inside a single 10-min tick
  serially.** [STRONG — derived from `warm-cadence-vs-lkg-ceiling-tension.md:10-14` per-GID timings]
- The handler self-continues via checkpoint when it nears timeout/key-budget (`cache_warmer.py:428-463,
  471-486`), but self-continuation **serializes** links under `ReservedConcurrentExecutions=1` (bulk's live
  value) — a 34-key section sweep would chain across many 900s links and blow past 10min end-to-end.

**Two feasible shapes — recommend the first, with the second as the staged fallback:**

- **(B.3.a) RECOMMENDED — section lane with its OWN `reserved_concurrency` ≥ 2–3 + heaviest-first ordering +
  a ≤10-min tick.** Parallel links let the 34-key sweep finish well inside 10min (≥3 links × ~3min each).
  CRITICAL: the section lane MUST have a **dedicated reserved-concurrency pool disjoint from the bulk warmer's
  `ReservedConcurrentExecutions=1`** — sharing would let section links starve the bulk self-continuation chain
  (or vice-versa), and the disjoint-checkpoint-prefix isolation (#96) does NOT cover concurrency-slot
  contention. Account-level Lambda concurrency budget for the 3 lanes (offer=existing, bulk=1, section=2–3)
  must be reserved explicitly in TF; **this is a value the §C land must set, not assume.**
  [UV-P: account-level unreserved-concurrency headroom to carve a disjoint section pool of 2–3 | METHOD:
  deferred-to-section-land-tf-plan | REASON: account concurrency budget is an org-TF fact in the autom8y repo,
  not falsifiable from the receiver subtree; verify via `aws lambda get-account-settings` at land-plan time]
- **(B.3.b) STAGED FALLBACK — heaviest-subset section lane (the 2–4 heaviest GIDs) at ≤10-min on
  `reserved_concurrency=1`, bulk 30-min covering the cheap-section tail.** This re-scopes the held fast-lane
  #97 from `{project,section}`-of-2-GIDs to `section`-of-N-heaviest-GIDs and tightens it from 15→10min. It
  leaves the *light*-section GIDs (which rebuild in seconds and serve within-ceiling LKG anyway) on the bulk
  sweep. Lower cost, partial contract coverage — acceptable only if the re-gate (§D) shows the light-section
  GIDs never breach 600s in practice. This is the **resilience-theater-avoidance fallback**: ship the cheap
  subset, prove coverage, then graduate to (B.3.a) only if light GIDs prove contract-fragile.

### B.4 Interaction with the bulk warmer (already-disjoint)

- **Checkpoint/namespace:** disjoint prefix already exists (#96, `cache_warmer.py:289-293`). Section lane =
  third disjoint prefix. No collision with bulk's checkpoint by construction. ✓
- **Coverage denominator:** section lane reports coverage over its own 34-key (or N-heaviest) denominator
  (`_finish` `cache_warmer.py:397-426`, `WarmerKeysCovered/Enumerated`), not the bulk's 68. ✓
- **Build-path interaction:** the warm lane writes to S3 + memory AHEAD of reads
  (`cache_warmer.py:254-264`), so steady-state SECTION reads hit serve-FRESH and **never enter the
  `BuildCoordinator` semaphore** — the §A headroom is reserved for the warm-miss/cold tail only. This is the
  intended division of labor: §B removes steady-state build pressure; §A absorbs the residual tail.
- **The freshness knob and the lane are complementary, not redundant:** `FRESHNESS_CONTRACT_MAX_AGE_SECONDS`
  (PR #99, ships `{}` = inert until OQ-2 calibration) sets WHEN a section frame hard-rejects (600s). The lane
  sets HOW OFTEN a fresh frame is produced (≤10min). Calibrating the knob to 600s WITHOUT the lane would make
  section reads hard-reject every 10min → a 503/build storm — exactly the danger §0 names. **The lane MUST
  precede or co-deploy with the knob calibration** (deploy-order, §C step 7 before any knob→600s).

---

## §C. GATED-LAND RUNBOOK (human/IC-gated; ordered; irreversible steps flagged)

> Every step below is **STOPPED-AND-REPORTED** for the separate human/IC-gated pass. Nothing here is executed
> by this design. Steps are ordered so the lever is never inert-and-dangerous and the re-gate never runs on an
> uncertified substrate.

1. **Rebase the bundled receiver PRs off origin/main.** `git rebase --onto origin/main sre/cache-warmer-fast-lane`
   for **#100, #99, #101** (they carry the `sre/cache-warmer-fast-lane` fast-lane bundling delta — sprint
   ledger DISCREPANCY NOTE). #343 (autom8y infra-TF) and #98 are already clean. Verify each diff shrinks to
   its logical change (e.g. #100 → src+tests only, no fast-lane files). **Reversible (branch op).**
2. **Merge the OQ-free PRs in dependency order:** #98 (EMF 3-cause disaggregation, no deps) → #100 (C2
   namespace + `max_concurrent_builds` *parameterization*, FROZEN=4, no behavior change) → #99 (serve-stale
   attestation + inert `{}` knob) → #101 (Project-arm canary content-binding). All currently OPEN, base main
   (REST-verified). **IRREVERSIBLE (merge to main).**
3. **`terraform apply` #343** (autom8y infra-TF: cred-IaC adopt-via-import of Secret 1 + both SSM pointers +
   client_id-drift alarm). Secret 2 **stays** (drift alarm, NOT delete — it is actively consumed, NOT
   vestigial: `asana-dataframe-resolver-cred-topology.md:11`, monolith reads it at
   `autom8 config/satellite_config.py:388-392`, `LastAccessedDate=2026-06-03`). No `aws_secretsmanager_secret_version`
   declared (value stays out-of-band). **IRREVERSIBLE (apply); secret-decommission explicitly NOT in scope.**
4. **C1 5-lambda OTLP convergence deploy.** Re-bake the 5 asana lambdas' `OTEL_EXPORTER_OTLP_HEADERS` from
   SSM v10 (currently divergent: SSM v10 @12:59Z vs lambda env @09:06Z, sprint ledger A3(i)). **Assert literal
   `0/0/0` re-plan AFTER convergence** (single-source SSM writer `observability/main.tf:164`; #339 removed the
   oscillating var-chain). **IRREVERSIBLE (deploy).**
5. **CPU/mem + cap apply — THE LEVER, FIRST.** Apply cpu=2048/mem=8192 (§A.2 recommendation) AND raise
   `max_concurrent_builds` 4→target in the SAME apply (or mem first, then cap). **The cap raise is INERT and
   DANGEROUS without the mem bump landing FIRST** (PQ-1 acceptance #5: 4 builds × ~2GB ≫ current 2GB task).
   Verify the running task RAM via `describe-tasks` before proceeding. **IRREVERSIBLE (task-def apply); the
   FROZEN=4 is released ONLY here, under IC sign-off.**
6. **Deploy the §B SECTION warm lane.** New `section_only_prematerialization_keys` + `prematerialize_section_set`
   flag + disjoint checkpoint prefix + dedicated `reserved_concurrency` pool (≥2–3 per B.3.a, or =1 for the
   B.3.b heaviest-subset fallback) + ≤10-min EventBridge schedule. Verify disjoint from bulk's
   `ReservedConcurrentExecutions=1` pool (B.3 UV-P: confirm account concurrency budget at plan time).
   **IRREVERSIBLE (deploy).**
7. **Calibrate `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` to OQ-2 using the PR #102 map `{"project":86400, "section":576}`**
   (NOT a four-tier list — `analytics`/`vertical-summary` are dead keys with no matching `entity_type`; sprint-ledger
   Gate 2/6) and ratify PR #99's ADR. **MUST follow step 6** — calibrating SECTION→576s
   before the lane is live produces a section hard-reject/503 storm (§B.4). **IRREVERSIBLE (config deploy +
   ADR ratification).**
8. **Run ≥2 full SECTION sweeps** and confirm via `WarmerKeysCovered/Enumerated` + `WarmerCheckpointCleared`
   (`cache_warmer.py:410-414`) that the section lane reaches coverage=1.0 inside the ≤10-min cadence on ≥2
   consecutive cycles. **Read/measure — reversible.** Only after this does §D run.

---

## §D. FINAL ≥99% RE-GATE PLAN (rite-disjoint, chaos-engineer-authored, DOWNSTREAM of §C)

> **This re-gate measures the HEADROOM-APPLIED substrate. It MUST NOT run on the current substrate** — doing so
> repeats the INTERIM stale-datum error (the 82% was measured under the test-probe fixture on the dark/pre-bump
> substrate; sprint ledger qa_d labels it INTERIM-NOT-FINAL). The §C land is the precondition for §D.

**Hypothesis (chaos-engineering, hypothesis-driven):** *Given* the §C-applied substrate (cpu=2048/mem=8192,
`max_concurrent_builds`=target, SECTION ≤10-min lane live with ≥2 clean sweeps, `FRESHNESS_CONTRACT_MAX_AGE_SECONDS`
calibrated to OQ-2, EMF 3-cause disaggregated via #98), *When* ≥2 concurrent request streams drive the
confirmed-live fan-out width against BOTH project and section arms, *Then* satellite-serve ≥99% per Source on
both arms with CPU_STARVATION=0 and zero contract-stale section serves.

**Steady-state baseline (define BEFORE injection):** post-warmer section read p99 latency, build-semaphore
queue depth (`builds_started/coalesced` `build_coordinator.py:142-148`), section frame age distribution vs
600s, `/health` latency, ALB target-health.

**Measured at the confirmed live width:** ~20 build-keys (OQ-1 ratified width, `refresh_frames.py:115`/`:92`),
OR throttled ~8 if the consumer applies the `max_workers→4` throttle (state which at run time — do NOT measure
at the 104 test-probe fixture `probe_concurrency_semaphore.py:42`, the paradigm-wrong-datum trap).
**Recommendation: run BOTH** — unthrottled ~20 (worst case, proves §A headroom) AND throttled ~8 (the OQ-1
intended steady state).

**Success criteria (PASS requires ALL; default-to-REFUTED on any unproven):**

| # | Criterion | Signal / receipt |
|---|-----------|------------------|
| 1 | ≥99% satellite-serve per Source on **BOTH** Project AND Section arms, POST-warmer (≥1 full section sweep) | EMF satellite/fallback ratio, disaggregated |
| 2 | **3-cause-EMF disaggregated** (503-cadence / 502-capacity / honest-refusal) — verdict reads CAUSE, not a collapsed counter | PR #98 EMF split (S7-GATE-FIDELITY criterion 1) |
| 3 | **SECTION-10min held** — zero section serves at age >600s during the window (the contract is met, not merely "within the 50-min internal ceiling") | section frame-age distribution vs 600s; `meta.stale_served` (#99) |
| 4 | **CPU_STARVATION = 0** on the 4-signal panel | CPU util, `/health` latency, ALB target-health flaps, 503 CACHE_BUILD_IN_PROGRESS rate (PQ-1 acceptance #2) |
| 5 | **Singleflight proven under bulk** — `builds_coalesced > 0` with ≥1 completed under concurrent same-`(project_gid, section)` load | `build_coordinator.py` stats (NOT the #90 single-gid 2-build artifact) |
| 6 | **≥2 concurrent request streams** at the confirmed live width | load-driver config; state throttled/unthrottled |
| 7 | Canary bound to **CONTENT/cause, not 2xx-liveness** — a 2xx carrying an empty/wrong frame FAILS the gate | #101 Project-arm content-binding; Section arm clears on disaggregated honest-EMF + the PQ-5 guard decision (Section is column-contract-EXEMPT) |

**Abort criteria (defined before start, per chaos-engineering safety):**
- Section serve at age >600s on >1% of reads → ABORT (lane cadence or knob mis-calibrated; do not continue
  measuring a contract-violating substrate).
- CPU util sustained >85% OR `/health` p99 > ALB idle margin OR ALB target-health flap → ABORT (the §A bump
  is undersized; recede to §A.2 4096/16384 option, re-land, re-gate).
- 502 rate exceeds the INTERIM pre-bump baseline → ABORT (the substrate regressed; the lever is mis-applied).
- Max duration: bounded window per arm; if ≥99% not reached within it → FAIL (not ABORT), iterate.

**Disjointness:** authored and run by chaos-engineer, **NOT** the receiver author who wrote the fixes
(self-ref MODERATE ceiling — the re-gate IS the STRONG-lift corroboration event per the handoff §7). The
≥99% figure is a TARGET measured on the applied substrate, not a self-certified PASS.

**Compound-fault graduation (anti-resilience-theater):** the boundary-case calculus — a single section warm-
miss that builds within SLO is "resilient under single-fault." Per the §0 boundary case, schedule a
**compound-fault** follow-up (warm-lane stall + concurrent cold-start burst at unthrottled width) to test
whether §A headroom + the bulk backstop hold when the section lane itself fails. Do NOT re-run an identical
passing scenario 3× (resilience theater); graduate to compound once the single-fault PASS is recorded.

---

## §E. Decision summary + what stays FROZEN

| Lever | Design recommendation | Land step | Status now |
|-------|----------------------|-----------|------------|
| `max_concurrent_builds` | KEEP **4**, paired with cpu=2048/mem=8192 (or **2** + 2048/4096 under OQ-1 throttle) | §C step 5 | **FROZEN=4**, parameterized only (#100), no value change |
| CPU/mem task size | cpu=2048 / **mem=8192** (RECOMMENDED) | §C step 5 (FIRST) | not applied; no `.tf`/task-sizing touched |
| uvicorn workers | **KEEP 1** (multi-worker multiplies the semaphore → defeats the cap) | n/a | unchanged |
| SECTION warm lane | NEW section-arm-only lane, 34 GIDs, ≤10-min, disjoint reserved-concurrency pool (B.3.a); heaviest-subset fallback (B.3.b) | §C step 6 | designed only; fast-lane #97 superseded |
| `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` | calibrate to OQ-2 (SECTION=600s etc.) **after** the lane is live | §C step 7 | ships `{}` (inert, #99); OQ-2-gated |
| Secret 2 | drift alarm, **NOT delete** (consumed) | §C step 3 | not authored for decommission |

**Reversible — nothing landed.** This ADR is `status: draft / authored-not-ratified`. No merge, no terraform
apply, no deploy, no secret op, no `max_concurrent_builds` value change (FROZEN=4 holds), no CPU/mem apply.
Every irreversible step is enumerated in §C for the separate human/IC-gated land pass. Self-ref MODERATE
ceiling held; the only STRONG claims are the two consumer-corroborated corrections (OQ-1 width
`refresh_frames.py:115`; OQ-4 credential `asana-dataframe-resolver-cred-topology.md`).
