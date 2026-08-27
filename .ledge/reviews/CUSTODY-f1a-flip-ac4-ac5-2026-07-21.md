---
type: custody
subtype: arch-adversary-flip-custody
artifact_id: CUSTODY-f1a-flip-ac4-ac5-2026-07-21
initiative: F1a — asana cross-consumer rate-limit budget allocator
sprint: C3 — F1a flip-custody (dual-lane-opening-wave, widening-leads lane)
node: "feeds NODE 8 — GO-LIVE (OPERATOR-ONLY). This artifact informs; it never schedules or fires."
challenger_agent: arch-adversary
dispatch: account-status-recon seat, Potnia-ratified deviation (receipt inv-20260721-f802699806f7)
date: 2026-07-21
code_ref: "origin/main @ 2362cd3712173c3d662d9aa4aa2b67a7aafd9ef1 (all code claims; NEVER the dirty working tree)"
targets:
  - .ledge/handoffs/HANDOFF-f1a-to-operator-golive-gate-2026-07-20.md   # working-tree-only, untracked
  - .ledge/handoffs/CHARTER-f1a-budget-allocator-2026-07-20.md          # working-tree-only, untracked
  - .sos/wip/thermia/f1a/ (capacity-specification, ADVERSARY-REPORT-f1a-1, QA verdicts, topology-inventory)
verdicts:
  F-C3-01_wiring: "NEW BLOCKING-CLASS FINDING — the flip as described is registration-only; no production code path pays the floor or the cap. Dominates AC-4/AC-5."
  AC-4: "flip-quality for a warmers-first stage IF wired; ECS half CONDITIONED on the regrowth tripwire; mechanism model CORRECTED (three-factor conjunction, not simple TTL<sweep)"
  AC-5: "NOT flip-blocking; no defensible sizing exists NOW; discharge = two named node-9 measurement windows; allocator telemetry CANNOT discharge it as-built"
evidence_grade_cap: "MODERATE throughout (self-ref-evidence-grade-rule; single-analyst custody, rite-disjoint critic = eunomia verification-auditor @ autom8y-asana per shape :179)"
citations:
  - "[SRC-001 Messick 1989] construct validity — each finding names the construct at risk [MODERATE, self-ref-capped]"
  - "[SRC-010 Cohen 1960] second-rater discipline — every inherited number re-anchored to raw receipt or committed code [MODERATE, self-ref-capped]"
  - "assessment-methodology P-07 — proxy metrics necessary but insufficient (AC-5 log-line proxies)"
fences: "ANALYSIS ONLY. Zero code, zero PR, zero git mutation, zero ari, zero Asana/AWS calls. This file is the sole write."
---

# CUSTODY — F1a flip readiness (AC-4 / AC-5 / node-9 watch) — feeds the SOVEREIGN node-8 decision

## 0. Verdict summary (one screen)

1. **F-C3-01 (NEW, dominates):** on the committed tree, flipping
   `ASANA_BUDGET_ALLOCATOR_ENABLED=true` changes exactly three things in
   production paths: client-registration bookkeeping, the `allocator_boot` log
   line, and the fail-open tripwire scaffold. **No production code path routes
   the warmer's gap-sweep through the 110/60s floor gate, and no code path
   self-caps ECS at 1390.** The go-live handoff's staged-flip semantics
   ("warmer Lambdas first (claims the floor)... then the ECS service (activates
   the yield)", HANDOFF :48) describe a mechanism the merged build does not
   wire. §2 carries the commit-grain receipts and the falsification pathway.
2. **AC-4:** re-derived. The handoff's one-line mechanism ("TTL=300s < ~1795s
   sweep", HANDOFF :54) is REAL but MIS-LOCATED — the regrowth loop is a
   three-factor conjunction (§3.2), and the flip can perversely INVERT a
   today-benign failure mode (bank-on-abort becomes lose-on-timeout, §3.3).
   Option litigation: (a) TTL bump = partial, must be scoped; (b) chunk-ordering
   alone = insufficient, but **per-chunk banking** (its structural sibling) is
   the cheapest kill; (c) floor re-size to 220 = REJECT (triples the shed, zero
   margin). Verdict + the ratified promote-to-blocker tripwire in §3.5.
3. **AC-5:** nothing numeric is defensible today. The C1 zeros for
   `conversation-audit` are window artifacts; the 11:00Z 2-of-4 collision is
   scheduled daily; and as-built there is **no near-zero cap surface at all** —
   a flipped near-zero Lambda inherits the FAIR_SHARE lane with a 1390
   telemetry threshold (§4). Honest boundary: two named measurement windows at
   node-9; not an allocator-telemetry discharge.
4. **Node-9 watch:** the handoff's watch plan (:60-62) is sharpened into a
   staged pre-flip/stage-1/stage-2 checklist with per-stage reverts (§5). One
   correction is load-bearing: `budget_floor_overage` — named "the allocator's
   own ground truth" (:62) — **cannot emit from production traffic as-built**
   (`observe_admission` has zero production call sites); its absence is
   NON-EVIDENCE, not health.

## 1. Ground + method (provenance, per SVR discipline)

- **Documents:** HANDOFF-f1a-to-operator-golive-gate-2026-07-20.md and
  CHARTER-f1a-budget-allocator-2026-07-20.md exist ONLY in the working tree
  (untracked, `??`; not on origin/main). The `.sos/wip/thermia/f1a/` receipts
  are session artifacts (expected untracked). Their content is treated as the
  procession's documentary record; every quantitative claim below re-anchors to
  either those receipts or committed code.
- **Code:** every code claim was read via
  `git show origin/main:<path>` at `2362cd37` (tip, ahead of the QA ref
  `f6a72824`, which IS an ancestor — so the allocator build and anything after
  it through PR #255 is inside my read surface). The dirty working tree was
  never read for code state.
- **Census method (falsifiable):** `git grep` across `origin/main -- src/` for
  the tokens `allocator`, `get_budget_allocator`, `warmer_floor_gate`,
  `published_floor|PublishedFloor`, `observe_admission`,
  `floor_max_requests|fair_share_max`, `ASANA_BUDGET_ALLOCATOR`. Production
  hits: `client.py` (registration seam), `config.py` (config plumbing),
  `transport/budget_allocator.py` (the module itself). Nothing else. Static
  grep cannot see reflection/dynamic dispatch — named as a self-limit in §7.

## 2. F-C3-01 — the flip is registration-only as-built (NEW finding, BLOCKING-class for flip SEMANTICS)

**Claim under challenge:** HANDOFF :42 "Activation is per-process env config,
no code change" + :48 "warmer Lambdas first (claims the floor; lowest risk),
then the ECS service (activates the yield)".

**Receipts (all origin/main @ 2362cd37):**

| # | Fact | Anchor |
|---|------|--------|
| 1 | The attach seam ONLY registers: "register_client ... Advisory bookkeeping only ... **Never touches the client's request path**" | src/autom8_asana/transport/budget_allocator.py:375-385 |
| 2 | Admission counting is advisory AND unwired: "This NEVER blocks (advisory published-floor, not in-path arbiter)" — and `observe_admission` has **zero call sites in src/** outside its own module | src/autom8_asana/transport/budget_allocator.py:392-396; census §1 |
| 3 | `warmer_floor_gate` (the ITEM-C cure primitive) has **zero production call sites**; `hierarchy_warmer.py` contains no floor/allocator/timeout reference at all | src/autom8_asana/transport/budget_allocator.py:355; census §1 |
| 4 | The client's real pacing remains the pre-existing per-client token bucket, built ONLY from `rate_limit.max_requests/window_seconds` — no allocator folding | src/autom8_asana/client.py:205-210; src/autom8_asana/transport/config_translator.py (`to_rate_limiter_config`) |
| 5 | ITEM-C's commit touched ONLY the allocator module + its test file — `hierarchy_warmer.py` was never modified in the allocator PR | `git show --stat 28c4a582` (2 files: transport/budget_allocator.py, tests/unit/transport/test_budget_allocator_warmer_floor.py) |
| 6 | ITEM-B's commit touched ONLY client.py + the census test (construction-seam registration, not per-request consultation) | `git show --stat 4c9ab96e` |
| 7 | The AC-3 "3,291-GET ≤1800s sweep" proof drives the GATE PRIMITIVE with injectable clock — not the production warm loop | tests/unit/transport/test_budget_allocator_warmer_floor.py:8-33,68 |
| 8 | The LIVE-LEG floor pacing was driven by the QA harness calling `allocator.warmer_floor_gate().admit()` itself — a stand-in for a production call path that does not exist | QA-live-leg-verdict.md:30 |

**What this does and does not impugn.** Rung honesty held: LIVE-LEG-PROVEN
truthfully proved the gate primitive against real Asana (QA-live-leg-verdict.md
:28-55), and the census truthfully proved construction-seam unification. The
gap is between the proven rung and the **flip semantics on the operator
surface**: under the advisory design, "enforcement is entirely each
principal's own code honoring its self-cap" (ADJUDICATION-option-slate.md:118-124)
— and the principals' own code (the warm loop; the ECS request path) was never
taught to honor anything. HANDOFF-2 ITEM-C's own scope line ("the warmer lane
claims its static 110/60s floor and completes its gap-sweep under it",
HANDOFF-arch-to-10x :92-95) is discharged by the build only at
primitive-plus-test altitude.

**Consequences for node-8:**
- Stage-1 (warmers-first) cannot claim the floor. The 2026-07-14 disease
  mechanism (AIMD suppression starving the sweep) continues UNCHANGED post-flip.
- Stage-2 (ECS) cannot activate the yield. No 1390 self-cap engages; fleet 429
  dynamics stay as measured.
- The node-9 success criterion ("sawtooth amplitude collapses", HANDOFF :62)
  is UNREACHABLE through this flip; a watch window run against it would
  produce a false-negative verdict on a cure that was never armed.
- Risk symmetry: the flip is therefore also nearly risk-free (byte-identity is
  trivially preserved because almost nothing changes). The danger is not
  activation harm — it is **verdict contamination**: spending the
  storm-equivalent watch window and the operator's flip authority on an inert
  lever, then booking the non-collapse as evidence against the allocator design.

**Falsification pathway (this finding is dogma without one):** produce a
file:line receipt on the deployed ref showing a production call path from the
gap-warm loop (or the transport hot path) into `WarmerFloorGate.admit()` /
an in-path 1390 self-cap — e.g., a commit between `f6a72824` and the deployed
image that wires it, or a dynamic-dispatch site my token census missed. Any
such receipt collapses F-C3-01 to RESOLVED and §5's checklist applies as
written against the wired mechanism.

## 3. AC-4 — TTL-regrowth re-derivation (routed to arch per HANDOFF :54; discharged here)

### 3.1 The charter numbers, re-anchored

| Quantity | Value | Anchor |
|---|---|---|
| Worst-case gap set | 3,291 GETs (one per uncached parent GID; observed regrowth 3291→676→3291 overnight) | capacity-specification.md:102-108, 467-468 |
| Floor | 110/60s = ceil(3,291 / 30 min) | capacity-specification.md:162-166; settings.py:591-597 |
| Floor-paced full sweep | 3,291 ÷ (110/60 s⁻¹) = **1,795.1 s** (~29.9 min) — the handoff's "~1795s" | derived; HANDOFF :54 |
| Chunking | `_GAP_WARM_CHUNK_SIZE = 200` → ceil(3291/200) = 17 chunks; ~109.1 s/chunk at floor pace | hierarchy_warmer.py:42; capacity-specification.md:129 |
| Tick cadence | 30-min EventBridge tick (`cron(0,30 * * * ? *)`); ~46-min inter-warm for the heaviest GID | topology-inventory.md:63; capacity-specification.md:143-146 |
| Lambda link budget | "hard 900 s Lambda timeout" (committed code comment; deployed value = UV-P-1) | lambda_handlers/cache_warmer.py:112-114; capacity-specification.md:183 |
| Per-fetch TTLs (fetch-time cache write) | business 3600 / contact-unit 900 / offer 180 / process 60 / **generic 300** | clients/task_ttl.py:42-48; clients/tasks.py:314-317; config.py:132 |
| Banked batch re-store TTL | `ttl=None` → **NO EXPIRY** (entry-level and both backends) | cache/providers/unified.py:443-498; cache/models/entry.py:105,130-149; backends/memory.py:275-277; backends/redis.py:455-459 |
| Banking cadence | ONE `put_batch_async` after the whole chunk loop (abort path included; timeout path NOT) | hierarchy_warmer.py:240-283 |

### 3.2 Corrected mechanism model — the loop is a three-factor conjunction

The handoff frames AC-4 as "TTL=300s < ~1795s sweep ⇒ early-warmed entries
expire before sweep-end" (HANDOFF :54). The committed code says the loop needs
ALL THREE of:

1. **Single-shot end-of-sweep banking.** Durable (no-expiry) storage happens
   only if the chunk loop RETURNS — `put_batch_async` at hierarchy_warmer.py:278
   runs after the loop (the 50%-saturation abort still reaches it; a process
   death does not).
2. **Link truncation.** At floor pace the full-decay sweep needs 1,795 s; the
   handler's continuation architecture assumes "each link stays well under the
   hard 900 s Lambda timeout" (cache_warmer.py:112-114) — an invariant written
   for un-metered pace. The gap-warm loop itself has ZERO timeout checkpoints
   (census: no `timeout|deadline|should_exit|context` token in
   hierarchy_warmer.py). 900 s at 110/min ≈ 8 chunks ≈ **1,650 GETs**, then the
   invocation dies before the banking line.
3. **Per-fetch evaporation.** Each fetched parent IS cached at fetch time by
   `tasks.get_async` → `_cache_set(..., ttl=resolver)` (tasks.py:314-317) —
   but generic parents get 300 s (and process-typed parents 60 s). 300 s ≪ the
   1,800 s tick interval: everything a truncated invocation fetched has expired
   before the next tick's uncached-check (`get_versioned(gid, EntryType.TASK)`,
   hierarchy_warmer.py:180). Net durable progress per truncated invocation ≈ 0.

Kill any one factor and the loop dies for the completable cases. Note the
handoff's framing is wrong in BOTH directions: banked parents never TTL-expire
(ttl=None), while unbanked parents survive only 300 s — the "TTL bump"
instinct aims at the wrong write path unless scoped to the per-fetch leg.

**Un-pinned residual:** the observed regrowth to the FULL 3,291 after a 676
residual implies previously-BANKED (no-expiry) entries also vanished. TTL
mechanics on the committed code cannot explain that; leading candidates are
Redis eviction under memory pressure and version invalidation → **UV-P-3**.
The capacity spec itself marked the loop a hypothesis
([ASSUMPTION-adjacent, unresolved], capacity-specification.md:474-475); the
build resolved the CONSTANT (300 s) but not the MECHANISM
(budget_allocator.py:121-127).

### 3.3 The perverse inversion (new sub-finding, fires only AFTER wiring)

Today, under storm, AIMD suppression drives fast 429-saturation → the chunk
loop ABORTS early → abort BANKS its partial progress durably
(hierarchy_warmer.py:250-283: `break` then `put_batch_async`). Post-wiring, a
floored lane sees ~zero 429s (QA proved the floor holds under live storm
pressure, QA-live-leg-verdict.md:45-55) → no abort → the sweep runs LONG → the
900 s link timeout strands it with NOTHING banked (factor 2+3). For gap sets
in (~1,650, 3,291], **wiring the floor without fixing the banking cadence
converts a slow-but-durable failure mode into a fast-but-evaporating one.**
The full-decay case the floor was sized FOR is exactly the case the timeout
truncates. Any AC-4 fix class must therefore include banking cadence, not
just TTL.

### 3.4 Option litigation (adversarial, per the dispatch)

| Option | Mechanism | What breaks it | Blast radius | Disposition |
|---|---|---|---|---|
| (a) TTL bump for gap-parents | Raise the PER-FETCH write's TTL for gap-parent context to ≥2× tick (≥3600 s) so truncated progress survives to the next tick → cumulative completion across ~2-3 ticks | (i) does nothing for the banked-entry vanish (already no-expiry; UV-P-3); (ii) a GLOBAL `DEFAULT_TTL` bump leaks staleness to every generic-task consumer incl. client-felt lanes — must be scoped to the gap-parent fetch context; (iii) is a code change → PR + canary, NOT an operator env knob | Cache-freshness only; zero budget-surface coupling; staleness risk LOW for structural parent links (version-guarded via `modified_at`) | VIABLE as composite member, scoped form only |
| (b) Sweep chunk-ordering | Rotate/offset chunk composition per invocation so truncated sweeps cover disjoint segments. NOTE the current code is the OPPOSITE: `maintain_order` = stable composition across cycles (hierarchy_warmer.py:166) — under truncation + 300 s evaporation, every tick re-fetches the SAME head ~1,650 GIDs and never reaches the tail: a deterministic tail-starvation livelock that burns 1,650 floor-calls/tick for zero durable progress (the §2a pay-cost-no-cure conjunction in its purest form, ADVERSARY-REPORT-f1a-1.md:108-112) | Ordering ALONE is insufficient: rotated segments evaporate just the same (300 s covers ~550 GETs of floor-paced work); a full rotation never completes inside any TTL | Warmer-internal only | INSUFFICIENT ALONE; its structural sibling below is the cheapest kill |
| (b′) Per-chunk banking (the load-bearing variant of (b)) | Move `put_batch_async` inside the chunk loop (bank every ~200-GET chunk at ~109 s intervals). Truncation then loses ≤1 chunk; stable ordering starts WORKING FOR the sweep (banked head chunks drop out of the next uncached set); full-decay completes cumulatively in ≤2-3 ticks ≈ well inside the 3600 s freshness bar | Recursive chain-warm cost per banked batch (bounded; `_fetch_immediate_parents` reads cache-first); needs the AC-3 harness extended to a truncation fixture | Warmer-internal; ≤17 batch writes/sweep; hierarchy registration idempotent | **RECOMMENDED PRIMARY (as challenge output — design authority stays with the owning specialist)**; kills factor 1, defuses §3.3, and de-fangs factor 3 without touching the TTL contract |
| (c) Floor re-size | Fit the sweep inside the BINDING constraint. Fit-to-tick already holds (1,795 < 1,800). The binding constraint is the 900 s link: needs 3,291/15 min = **220/min** — precisely capacity-spec §1.6's aggressive bound (:183) | (i) shed TRIPLES: 5,495 calls / 4.69% of the worst 3h window vs 1,808 / 1.54% at 110 (capacity-specification.md:191-195) — re-opens the node-4 REDUCE margin; (ii) ZERO margin: 220×15 min = 3,300 vs 3,291, and live-leg showed 429-retry waits consume pacing wall-clock (QA-live-leg-verdict.md:48-50); (iii) violates the design's own 2× triangulation (capacity-specification.md:136-158); (iv) still loses everything if truncation occurs 1 s early | Fleet-wide: the ECS yield doubles+ | **REJECT as primary.** The 220 double-convergence (sensitivity bound = timeout-fit bound) is surfaced for the record, not endorsed |

### 3.5 AC-4 verdict + the ratified promote-to-blocker tripwire

- **For the flip as-built:** AC-4 is MOOT-BY-DOMINANCE — the floor never
  engages (F-C3-01), so the "floor-paced sweep vs TTL" race never starts. The
  operative blocker is F-C3-01.
- **In the wired counterfactual (and for the remediation PR):** warmers-first
  stage = **flip-quality** — the floor strictly improves admission for every
  gap set ≤ ~1,650 GETs (sweep completes inside one link, banks durably, done),
  and today's behavior is the fallback, EXCEPT for the §3.3 inversion band
  (~1,650–3,291], which the fix class must close. ECS half = **CONDITIONED**:
  the §2a residual (cap lands, floor unclaimed → ECS pays 1.54% for no cure,
  ADVERSARY-REPORT-f1a-1.md:108-112) is REACHABLE through AC-4 alone.
- **PROMOTE-TO-BLOCKER TRIPWIRE (the re-rank trigger, watch-observable):**
  during the warmers-first watch window, IF
  `parent_gids_count` for GID 1143843662099250 regrows to ≥90% of the prior
  full set across ≥2 consecutive 30-min ticks WHILE floored sweep attempts are
  present (allocator active; `hierarchy_gap_warming_failed` /
  `hierarchy_gap_chain_warm_rate_limited` events continuing), OR
  `OfferFrameAgeSeconds{1143843662099250}` raw datapoints sustain >3600 s
  through a storm-equivalent window with the floor engaged —
  THEN **AC-4 = flip-BLOCKER for the ECS half**: do not fire the ECS flip (do
  not start paying the 1.54% shed) until the regrowth loop is closed
  ((b′) ± scoped (a)). Both signals are already-emitting log/metric surfaces
  (capacity-specification.md:102-105; HANDOFF :62) — no new instrumentation is
  needed to arm the tripwire.

## 4. AC-5 — near-zero Lambda cap sizing (HANDOFF :55)

### 4.1 What is defensible NOW from documents

- **Schedules (documented, committed receipts):** `conversation-audit` weekly
  `cron(0 7 ? * SUN *)`; `insights-export` AND `onboarding-walkthrough` BOTH
  daily `cron(0 11 * * ? *)` — a 2-of-4 same-minute collision scheduled DAILY
  inside the diurnal peak that produced the 1,532-call worst minute
  (topology-inventory.md:66-67,70; ADVERSARY-REPORT-f1a-1.md:212-226).
- **The zeros are window artifacts:** no C1 window contained a Sunday 07:00Z
  firing (W1 Wed–Fri; W3 began Sun 11:18Z, 4h18m late) — `conversation-audit`'s
  "measured draw ≈ 0" is placement, not measurement
  (ADVERSARY-REPORT-f1a-1.md:214-219).
- **The design bound is real but unimplemented:** T4 requires near-zero
  self-caps at measured-draw+modest-headroom with Σ(all self-caps) ≤ ~1550
  (ADJUDICATION-option-slate.md:104-107,137-140). As-built, the settings
  surface has exactly FOUR fields — enabled / floor 110 / window 60 /
  fair_share 1390 (settings.py:581-618). **There is no near-zero cap field at
  all.** A flipped near-zero Lambda lands in `Lane.FAIR_SHARE`
  (budget_allocator.py:170-181) with a 1390/60s telemetry threshold — a
  "cap" ~2 orders of magnitude above its draw, and advisory-only besides.
- **Interim exposure bound (documented):** overshoot is bounded by organic
  near-zero demand (low-tens at the 11:00Z collision, itself a log-line PROXY
  — P-07), 429-backstopped server-side, with warmer exposure ~7%/min share
  arithmetic (ADVERSARY-REPORT-f1a-1.md:228-239). Under F-C3-01 the flip
  changes none of this in either direction.

### 4.2 The honest boundary

**No numeric cap proposed here survives its own falsification test.** Any
number would be sized from proxies the record itself impeaches (P-07;
CH-04). Sizing MUST wait for the node-9 watch, and its discharge is:

- **W-A:** ≥1 CWLI measurement window containing a Sunday 07:00Z
  `conversation-audit` firing (first candidates: 2026-07-26, 2026-08-02);
- **W-B:** ≥1 window over the 11:00Z `insights-export` + `onboarding-walkthrough`
  collision inside the 09:00–12:00Z diurnal peak (any weekday);
- output: a measured per-principal burst table (adversary condition-5
  discharge form, ADVERSARY-REPORT-f1a-1.md:282-287), THEN static caps sized
  measured-draw+modest-headroom, THEN a settings surface to carry them (none
  exists — a small follow-up PR is intrinsic to the discharge).

**One boundary correction to the handoff:** :55 says "final sizing =
node-9/operator item" — correct, but note the discharge CANNOT run through
allocator telemetry as-built (`observe_admission` unwired, §2 receipt 2); it
is a CloudWatch-Logs-Insights measurement task, independent of the flip state.

### 4.3 AC-5 verdict

**NOT flip-blocking, either half, wired or not.** The unmeasured principals
cannot claim floor-protected budget (there is none to claim under advisory),
their overshoot band is bounded and backstopped, and the flip does not alter
their behavior. AC-5 stays DEFER with W-A/W-B as the discharge condition and
a recommended deadline of the first watch-window close after 2026-08-02 (two
Sunday candidates deep).

## 5. Node-9 watch consumption → flip-readiness checklist (sharpens HANDOFF :60-62)

The F1a flip is SOVEREIGN (charter F-a, node-8). This checklist informs; the
operator fires or declines.

### 5.0 PRE-FLIP (node-8 gate inputs — resolve before Stage 1)

- [ ] **F-C3-01 disposition (the fork).** Either:
  **(i) accept a registration-only flip** — telemetry scaffold goes live, zero
  cure expectation, and the watch success criterion MUST NOT be sawtooth
  collapse (booking non-collapse against the design would be verdict
  contamination); or
  **(ii) back-route to build** for warm-path floor wiring, folding in the AC-4
  fix class ((b′) per-chunk banking ± scoped (a)) in the same PR — one canary
  cycle closes F-C3-01, AC-4 factor 1, and the §3.3 inversion together, and
  the go-live handoff's staged-flip semantics become true as written.
  Path (ii) is the only path on which node-9 can produce the "cured" rung.
- [ ] **AC-4 tripwire armed** (§3.5 thresholds transcribed into the watch
  owner's runbook — thermal-monitor per charter node 9, CHARTER :78).
- [ ] **SNS gap acknowledged:** AL-5 `Actions=[]`, no topic exists (HANDOFF
  :56); every watch signal below is human-pull, not push — name the watch
  owner and reading cadence explicitly. `protecting-prod` stays unclaimable
  until the operator sanctions notification wiring.
- [ ] **Deployed-provenance check (UV-P-2):** confirm the deployed ECS/Lambda
  images carry the allocator commits (`4fd903ea..f6a72824` ancestors of the
  deployed ref) BEFORE flipping any knob — the fleet scar
  (resolve-deployed-image-provenance-before-certifying) applies verbatim.

### 5.1 STAGE 1 — warmer Lambdas first (`autom8-asana-cache-warmer`, `-bulk`)

Flip: set `ASANA_BUDGET_ALLOCATOR_ENABLED=true` in the two warmer Lambdas'
env. Revert: unset/false (seconds, per-process; byte-identity proven,
HANDOFF :48-50).

| Signal | Threshold / expectation | Reading |
|---|---|---|
| `allocator_boot` state=active in each warmer invocation log | present on every invoke post-flip | flip-realization receipt (per-process-fresh bind, QA-live-leg-verdict.md:28) |
| `OfferFrameAgeSeconds{1143843662099250}` RAW datapoints (never alarm state alone) | sustained <3600 s; 1,301↔25,763 s sawtooth amplitude collapses — ONLY meaningful on path (ii) | capacity-specification.md:458-466; HANDOFF :62 |
| `parent_gids_count` trajectory on gap-warm events | monotone shrink across ticks; **≥90% regrowth over ≥2 consecutive ticks = AC-4 PROMOTE-TO-BLOCKER (§3.5)** | capacity-specification.md:102-108 |
| `aimd_at_minimum` frequency | falls if the floor engages; **unchanged = floor not engaging = F-C3-01 confirmed in the wild** | HANDOFF :62; QA-live-leg-verdict.md:51-55 |
| `hierarchy_gap_warming_failed` / `_rate_limited` rate | at-or-below pre-flip baseline | hierarchy_warmer.py:284-291 |
| `budget_floor_overage` | **as-built emits NOTHING from production traffic (observe_admission unwired). ABSENCE = NON-EVIDENCE.** Becomes ground truth only after wiring | §2 receipt 2; HANDOFF :62 corrected |
| `budget_lane_failopen` | zero; any occurrence = allocator-internal fault, fail-open by design (the one tripwire the flip DOES arm) | client.py:64-96; HANDOFF :57 |

Window: ≥1 storm-equivalent 09:00–12:00Z diurnal peak (HANDOFF :62) AND — for
the AC-4 tripwire — ≥1 observed full-decay gap-fill attempt.

### 5.2 STAGE 2 — ECS `autom8y-asana-service` (the yield side)

GATE: Stage-1 window complete AND the AC-4 tripwire did NOT fire AND (on path
(i)) explicit operator acceptance that this stage is registration-only.

Flip: task-definition env + normal deploy cycle. Revert: env-unset + redeploy
(minutes) or PR revert; keep AL-5 TF commit `31fe9bbf` regardless (HANDOFF :50).

| Signal | Threshold |
|---|---|
| Fleet 429 rate through ≥1 storm window | not worse than baseline (HANDOFF :62) |
| E1 `autom8y-data→/query` LKG stale-serve rate + inbound 5xx | no new hard-starvation on inbound edges (ADVERSARY-REPORT-f1a-1.md:87-106) |
| ECS worst-minute served volume | on path (ii): cap converts 429-retry waste into clean throughput (~1,295 served at the 1,532 worst minute, ADVERSARY-REPORT-f1a-1.md:102-106) |

### 5.3 Close conditions

- `cured` rung claimable ONLY on: sawtooth collapse + fleet-429 not-worse
  through ≥1 storm-equivalent window (CHARTER :78; HANDOFF :21 — currently
  NOT claimed, correctly).
- AC-5 discharge: W-A + W-B measurement windows (§4.2), then the caps PR.
- `protecting-prod`: blocked on SNS wiring (operator carve-out), unchanged.

### 5.4 Checklist delta vs the handoff's open-items surface (HANDOFF §4)

| Handoff item | Status here |
|---|---|
| 1. AC-4 TTL-regrowth | DISCHARGED-as-analysis: mechanism corrected (§3.2), inversion sub-finding added (§3.3), options litigated (§3.4), tripwire made measurable (§3.5) |
| 2. AC-5 sizing | CONFIRMED-DEFER, sharpened: no cap surface exists at all; W-A/W-B named; not an allocator-telemetry discharge (§4) |
| 3. SNS gap | unchanged; folded into §5.0 as watch-owner naming |
| 4. fail-open in-silico only | unchanged; noted the fail-open tripwire is among the few things the flip actually arms |
| 5. capacity-spec escalations ×3 | out of C3 scope; standing (capacity-specification.md:490-526) |
| — | **NEW: F-C3-01** registration-only flip (§2) — dominates the decision surface |
| — | **NEW: §3.3 inversion** — post-wiring fix class must include banking cadence |
| — | **NEW: `budget_floor_overage` non-evidence warning** — the watch plan's named ground truth is inoperative as-built |

## 6. UV-P register (undocumented live-platform state — per structural-verification-receipt frozen syntax)

- [UV-P: deployed warmer-bulk Lambda hard timeout is 900s | METHOD: IaC read in the owning infra repo (only observability_alarms.tf lives in autom8y-asana) or `aws lambda get-function-configuration` | REASON: asserted by committed code comment cache_warmer.py:112-114 and capacity-specification.md:183; the deployed value is not documented in this tree]
- [UV-P: deployed ECS/Lambda images carry origin/main 2362cd37 (or at minimum f6a72824) | METHOD: ECR digest vs task-def/function-config resolution | REASON: all code findings here are origin/main reads; deployed provenance undocumented — fleet scar precedent (IB1 wrong-deployed-repo) makes this a pre-flip check, §5.0]
- [UV-P: ElastiCache/Redis eviction policy + maxmemory for the warmer cache | METHOD: `aws elasticache describe-*` or IaC read | REASON: previously-banked no-expiry entries observably vanished (3291 regrowth after 676 residual, capacity-specification.md:467-468); committed TTL mechanics cannot explain it; eviction is the leading candidate for the un-pinned AC-4 residual (§3.2)]
- [UV-P: zero deployed processes currently set ASANA_BUDGET_ALLOCATOR_ENABLED | METHOD: task-definition + Lambda env audit | REASON: HANDOFF :23 attests it; not independently documented in committed artifacts]
- [UV-P: the deployed warmer's UnifiedStore binds the Redis backend for EntryType.TASK reads/writes | METHOD: runtime config resolution on the deployed image | REASON: topology-inventory.md:63 documents REDIS_HOST presence (C1 receipt); the runtime cache-provider selection path is config-dependent and unverified live]

## 7. Falsification of this artifact (adversary-epistemic-integrity, recursive)

- **F-C3-01 falls** on any production file:line receipt routing warm-loop or
  transport hot-path traffic through `WarmerFloorGate.admit()`/an in-path
  1390 cap on the deployed ref (§2). If it falls, §5 applies as written and
  AC-4 §3.5 becomes the operative custody line.
- **The §3.2 mechanism model falls** if the TASK-entry write path is shown to
  differ live from origin/main (UV-P-2/UV-P-5), or if UV-P-3 resolves to an
  eviction dynamic that dominates TTL entirely (then option (a) is worthless
  and (b′) remains the only kill).
- **The §3.3 inversion falls** if the gap-warm loop is shown to run inside a
  timeout-checkpointed section I could not see statically (the census found
  none in hierarchy_warmer.py; the checkpoint primitives exist one layer up,
  cache_warmer.py:508-552).
- **The AC-5 boundary falls** if a C1-grade measurement of the Sunday/11:00Z
  windows already exists somewhere I did not read — producing it IS the W-A/W-B
  discharge, which revises §4.3 from DEFER to sized.
- **Self-limits:** static token census (method disclosed §1) cannot see
  reflection; all grades MODERATE-capped (self-ref); zero execution, zero live
  probes, single additive artifact; the rite-disjoint check on THIS artifact
  belongs to eunomia verification-auditor @ autom8y-asana
  (dual-lane-opening-wave.shape.md:179).

---
*arch-adversary, C3 flip-custody, 2026-07-21. Read-only against everything but
this file; zero Asana/AWS calls; challenged, not designed. The flip is the
operator's alone — this artifact only tells the truth about what the lever is
connected to.*
