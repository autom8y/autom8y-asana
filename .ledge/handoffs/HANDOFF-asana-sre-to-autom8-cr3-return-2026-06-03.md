---
artifact_id: HANDOFF-asana-sre-to-autom8-cr3-return-2026-06-03
schema_version: "1.0"
source_rite: sre
target_rite: arch
blocking: true
initiative: cr3-receiver-bulk-validation-and-freshness-contract
created_at: "2026-06-03T18:00:00Z"
status: pending
type: handoff
ledge_status: proposed
handoff_type: strategic_input
priority: critical
source_artifacts:
  - ".sos/wip/cr3-verified-findings-2026-06-03.md"
  - "src/autom8_asana/cache/dataframe/build_coordinator.py"
  - "src/autom8_asana/cache/dataframe/dataframe_cache.py"
  - "src/autom8_asana/query/engine.py"
  - "src/autom8_asana/api/errors.py"
  - "tests/spikes/probe_concurrency_semaphore.py"
  - ".claude/agent-memory/platform-engineer/asana-dataframe-resolver-cred-topology.md"
  - "/Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-arch-autom8-to-sre-autom8y-asana-cr3-producer-work-queue-2026-06-03.md"
provenance:
  - { source: ".sos/wip/cr3-verified-findings-2026-06-03.md", type: artifact, grade: moderate }
  - { source: "src/autom8_asana/cache/dataframe/build_coordinator.py:130-131", type: code, grade: strong }
  - { source: "src/autom8_asana/cache/dataframe/dataframe_cache.py:525-546", type: code, grade: strong }
  - { source: "src/autom8_asana/query/engine.py:163-165", type: code, grade: strong }
  - { source: "aws lambda get-function autom8-asana-cache-warmer-bulk (deployed 2026-06-03 09:06)", type: artifact, grade: moderate }
evidence_grade: moderate
tradeoff_points:
  - attribute: "verification completeness vs cycle time"
    tradeoff: "we return BEFORE a clean rite-disjoint >=99% re-gate has landed; the 82% datum we are returning against is a stale pre-fix measurement"
    rationale: "the 30-min bulk warmer + serve-stale ceiling materially changed the read path AFTER the 82% run; returning the interim verdict + the freshness-contract ask now unblocks the monolith's calibration input while we run the re-gate. NO PASS is issued — Stage-B stays blocked."
  - attribute: "self-referential evidence ceiling"
    tradeoff: "all conclusions in this return are capped at MODERATE; no STRONG self-certification"
    rationale: "self-ref evidence-grade rule — we authored both the fix and the verdict; STRONG requires rite-disjoint live-under-bulk corroboration which has not yet landed."
items:
  - id: A-RECV-VERDICT
    summary: "Receiver bulk verdict = INTERIM, NOT-YET->=99%. The 82%/502 is a STALE pre-fix datum. No PASS, no Stage-B until a rite-disjoint >=99% re-gate clears with the 3 GetDfFallback causes disaggregated."
    priority: critical
    data_sources:
      - "build_coordinator.py:130-131 (max_concurrent_builds=4 hardcoded)"
      - "dataframe_cache.py:525-546 (serve-stale ceiling -> hard-reject -> 503)"
      - "tests/spikes/probe_concurrency_semaphore.py:42 (82% measured under N_PROJECTS=104 probe, pre-bulk-warmer)"
      - "aws lambda autom8-asana-cache-warmer-bulk (cron(0,30 * * * ? *), deployed 2026-06-03 09:06)"
    confidence: medium
  - id: B-PQ3-CRED
    summary: "PQ-3 401 is a stale-store-PATH issue (AUTH-TEB-001/migration-028), NOT a value divergence. Converge on authoritative Secret 1 (JSON envelope), decommission vestigial Secret 2."
    priority: high
    data_sources:
      - "platform-engineer/asana-dataframe-resolver-cred-topology.md (envelope client_secret digest == bare-string raw digest)"
      - "SSM /autom8y/platform/asana-dataframe-resolver/oauth-client-id (== Secret 1 client_id)"
    confidence: medium
  - id: C-PQ2-CADENCE
    summary: "Cadence decision: 30-min bulk for project/section (deployed) + 4h offer warmer. The observed 'DAILY' was the pre-today dark project/section state. Serve-stale reframes cadence as a freshness DIAL, not an availability requirement."
    priority: high
    data_sources:
      - "aws lambda autom8-asana-cache-warmer-bulk cron(0,30 * * * ? *) (deployed 2026-06-03 09:06)"
      - "offer warmer cron(0 */4 * * ? *) (live)"
    confidence: medium
  - id: D-PQ5-CONTRACTS
    summary: "Retry-After CONFIRMED; honest_empty CONFIRMED; canary section-arm is a degenerate-unfiltered VULNERABILITY requiring a seeded section_gid or a receiver guard (decision requested)."
    priority: high
    data_sources:
      - "api/errors.py:621-638 (Retry-After header on 503)"
      - "query/engine.py:264 (honest_empty = honest_contract_complete AND prefilter_row_count==0)"
      - "query/engine.py:163-165 (section filter applied only if section_name_filter is not None)"
    confidence: medium
  - id: E-FRESHNESS-CONTRACT
    summary: "LINCHPIN ASK: monolith owners ratify an explicit per-entity freshness data-contract for project/section reads. It calibrates FRESHNESS_CONTRACT_MAX_AGE_SECONDS -> build frequency -> 502 pressure. Single highest-value return we need."
    priority: critical
    data_sources:
      - "dataframe_cache.py:525-546 (LKG ceiling = LKG_MAX_STALENESS_MULTIPLIER(10.0) x ttl)"
      - ".sos/wip/cr3-verified-findings-2026-06-03.md synthesis #3 (freshness contract ties freshness AND 502)"
    confidence: medium
  - id: F-FANOUT-WIDTH
    summary: "OPEN QUESTION: confirm the REAL concurrent fan-out width. The ~104 is OUR test-probe fixture; live distinct warm-set = 34. What is the monolith's true concurrent project count + max_workers?"
    priority: high
    data_sources:
      - "tests/spikes/probe_concurrency_semaphore.py:42 (N_PROJECTS=104, 'S7 gameday width')"
      - "project_registry.py:271-275 (CONSUMER_WARM_SET_GIDS = 34 distinct)"
    confidence: medium
  - id: G-STRATEGIC
    summary: "Strategic direction: the receiver is evolving into the fleet's canonical materialized-data plane; serve-stale-within-bound is the read contract; CQRS/CDC/ingestion are tracked R&D."
    priority: medium
    data_sources:
      - "ratified LICENSE (operator stakeholder interview 2026-06-03)"
    confidence: medium
---

# RETURN — autom8y-asana (SRE) -> autom8 (arch / 10x): CR-3 Return Contract + Freshness-Contract Elicitation

> **Direction**: autom8y-asana(sre) -> autom8(arch/10x). **Class**: validation + strategic_input.
> **Answers**: the monolith's Return Contract (A) receiver bulk verdict, (B) PQ-3 cred disposition,
> (C) PQ-2 cadence decision; plus PQ-5 confirms (D), the **freshness-contract elicitation ask (E)**,
> the fan-out-width open question (F), and strategic direction (G).
> **Discipline**: default-to-REFUTED; every platform claim carries an SVR `file:line`/aws-resource
> receipt or is marked **UV-P**; conclusions graded [STRONG/MODERATE/WEAK]; **self-ref MODERATE ceiling**
> (no PASS self-certification without rite-disjoint live-under-bulk corroboration); **NO production
> secret VALUES printed** (digest/prefix+length only); **never asking you to relax — framing every item
> as meet-the-real-need**.

---

## HEADLINE (decision first)

1. **NO PASS. NO Stage-B.** The receiver bulk verdict is **INTERIM / NOT-YET->=99%** [MODERATE]. The 82%/502 you sent is a **stale pre-fix datum** (measured 2026-06-02, *before the project/section bulk warmer existed*). The dominant 502 is **build-semaphore starvation under mass cache-miss**, and those misses were driven by the **dark project/section warm path**. That path was lit today (30-min bulk warmer deployed **2026-06-03 09:06**). **A rite-disjoint >=99% re-gate is REQUIRED before any PASS** — and it must **disaggregate the 3 GetDfFallback causes** first (S7 false-green guard).
2. **PQ-3 cred = likely FALSE-ALARM** [MODERATE]: the 401 is a stale-store-**PATH**/backend issue, not a value divergence — **same `client_secret` value, envelope-shape difference only**. Converge on authoritative **Secret 1**; decommission vestigial **Secret 2**.
3. **PQ-2 cadence = 30-min bulk (deployed) + 4h offer.** The "DAILY" you observed was the pre-today dark state. Serve-stale reframes cadence as a **freshness DIAL**, not an availability requirement.
4. **The single highest-value thing we need back: ratify an explicit per-entity FRESHNESS DATA-CONTRACT (§E).** It calibrates the serve-stale bound, which sets build frequency, which sets the 502 pressure. It is the linchpin tying freshness AND the 502 together.

---

## A. RECEIVER BULK VERDICT — INTERIM, NOT-YET->=99% [MODERATE]

**Verdict: NO PASS. Stage-B stays BLOCKED. Fallback RETAINED.** Default-to-REFUTED held.

### Why the 82% is a stale, pre-fix datum
- The 82% (85 satellite / 19 fallback of 104) was measured under **our own test probe** at `tests/spikes/probe_concurrency_semaphore.py:42` (`N_PROJECTS=104`, comment "S7 gameday width") — **pre-bulk-warmer**. SVR: `probe_concurrency_semaphore.py:42`. [MODERATE — it is a probe fixture, not a live monolith run]
- The **30-min project/section bulk warmer did not exist** when that run executed. It deployed **2026-06-03 09:06** (`autom8-asana-cache-warmer-bulk`, `cron(0,30 * * * ? *)`, `prematerialize_bulk_set=true`). SVR (aws-resource): `aws lambda get-function autom8-asana-cache-warmer-bulk`. [MODERATE]

### Root cause of the dominant 502 (CONFIRMED mechanism) [STRONG on mechanism, MODERATE on dissolution]
The 502 is **build-semaphore starvation under a mass cache-miss burst**, and the misses were caused by the **dark warm path (V1 × V2)**:
- Miss path: `POST /{entity_type}/rows` (`api/routes/query.py:419-580`) -> on miss fires a fire-and-forget build (`universal_strategy.py:1035`) -> request returns **503 CACHE_BUILD_IN_PROGRESS** (`query.py:543`). SVR: `query.py:419-580,543`; `universal_strategy.py:1035`.
- Coalescing key = `(project_gid, entity_type)` only (`build_coordinator.py:51`); **different `(project_gid,'section')` keys each need a distinct semaphore slot**. SVR: `build_coordinator.py:51,184-238`.
- **`max_concurrent_builds=4` hardcoded** (`build_coordinator.py:130-131`); single uvicorn worker (`entrypoint.py:52-57`); cpu=1024/mem=2048 (768 units after ADOT 256). Wide fan-out of >4 cold section keys queues past `default_timeout_seconds=55.0` (`lifespan.py:232-234`) -> 503; CPU saturation -> `/health` slow -> ALB unhealthy after 3 -> 60s idle -> **502**. SVR: `build_coordinator.py:130-131`; `lifespan.py:232-234`.

**Now addressed by**: (1) the 30-min bulk warmer (warm reads hit serve-stale, not the 4-slot build path), and (2) **serve-stale-up-to-ceiling, already live** (V6) — `dataframe_cache.py` 3-state + ceiling: FRESH serve; APPROACHING_STALE serve + SWR refresh (`:496-523`); STALE serve LKG (`:525-546`). SVR: `dataframe_cache.py:496-546`. [MODERATE]

### Residual headroom work IN PROGRESS (the durable PQ-1 fix beyond warming)
- **`max_concurrent_builds=4` is a latent cap** on any cold-start / over-ceiling burst. Raising it requires a CPU/mem bump (4 builds × ~2GB frame ≈ 8GB vs the 2GB task). SVR: `build_coordinator.py:130-131`. Owner: **autom8y-asana platform-engineer**. This is the durable capacity fix; it is **not yet landed**.
- Measured heavy-GID cadence is **46 min vs 50-min ceiling** (full sweep ~40 min) — tight but inside the current LKG bound; calibrating the freshness contract (§E) will give headroom.

### What MUST happen before any PASS (the S7 false-green guard)
- **(precondition 0) Substrate certification.** The "now addressed" claims above rest on a substrate (30-min bulk warmer + serve-stale + cpu=1024 + IAM trio) that landed via out-of-band local applies + an IAM destroy/restore this session. It is being **independently certified — cleanly-merged → 0-drift `terraform plan` → QA smoke** — via the releaser track `HANDOFF-sre-to-releaser-cr3-receiver-substrate-certification-2026-06-03.md`. **The re-gate runs ON the certified substrate**; until that certification lands, every "deployed" claim in this return is MODERATE/assumed, not proven.
- **Re-measure post-bulk-warmer + post-build-headroom** under a rite-disjoint live-under-bulk re-gate (we authored the fix; we cannot self-certify PASS — self-ref MODERATE ceiling).
- **Disaggregate the 3 GetDfFallback causes** — cadence-503 / capacity-502 / honest-refusal — which currently collapse into ONE EMF signal. A false-green S7 is dangerous **because Stage-B removes the fallback**. The canary must bind to CONTENT/cause, not liveness.

**Acceptance for PASS (return to you when met)**: a landed `.ledge/decisions/` re-gate verdict showing OK-continuous **>=99% on BOTH Project AND Section arms** under the *confirmed* fan-out width (§F), produced by a rite-disjoint verifier, with the 3 fallback causes disaggregated. **Until then: no PASS, no Stage-B; Stage-B remains human/IC-gated.**

---

## B. PQ-3 CREDENTIAL DISPOSITION — converge on Secret 1, decommission Secret 2 [MODERATE]

**Disposition: the 401 is a stale-store-PATH/backend issue (AUTH-TEB-001 / migration-028), NOT a value divergence.** Same `client_secret` value — **envelope-shape difference only**.

| | Authoritative — **Secret 1** | Vestigial — **Secret 2** |
|---|---|---|
| Store path | `autom8y/asana-dataframe-resolver` | `autom8y/auth/service-api-keys/asana-dataframe-resolver` |
| Shape | JSON envelope `{client_id, client_secret}` | bare string |
| Created | 2026-06-01 | 2026-05-26 (G2-PRE migration-028 artifact) |
| Consumed by | **receiver canary** (via hermes SSM->SM) | **neither** monolith nor receiver |

- **Same value**: per `platform-engineer/asana-dataframe-resolver-cred-topology.md`, the envelope `client_secret` **digest == the bare-string raw digest** = SAME value. SVR: agent-memory `asana-dataframe-resolver-cred-topology.md`. [MODERATE — digest comparison + agent-memory, not a live re-mint by us]
- **Same `client_id`** (`sa_1a95…`, redacted to prefix; full value NOT printed) confirmed via SSM `/autom8y/platform/asana-dataframe-resolver/oauth-client-id` == Secret 1's `client_id`. SVR (aws-resource): SSM parameter above. **All secret values redacted to prefix/digest only.**

**Recommendation (meet-the-real-need)**:
1. **Point monolith auth at the authoritative store (Secret 1)** and **confirm via a live re-mint** against both paths — this is the step that would lift our grade from MODERATE to STRONG (we have not re-minted).
2. **Decommission Secret 2** (consumed by neither side) and **declare the authoritative store in IaC** with a defined **rotation cadence**.
3. **Do NOT conflate identities**: consumer-identity = `asana-dataframe-resolver`; receiver's-own-identity = `asana-service` (`main.tf:194-196` / `variables.tf:17-20`). SVR: `main.tf:194-196`.

---

## C. PQ-2 CADENCE DECISION — 30-min bulk (deployed) + 4h offer; serve-stale = freshness DIAL [MODERATE]

**Decision**: project/section served by the **30-min bulk warmer** (`cron(0,30 * * * ? *)`, deployed 2026-06-03 09:06) + the **4h offer warmer** (`cron(0 */4 * * ? *)`, live). SVR (aws-resource): `aws lambda autom8-asana-cache-warmer-bulk`; offer warmer cron.

- The **"DAILY"** you observed was the **pre-today dark project/section state**: that warm path was effectively unscheduled, so you saw only the ~4h/daily offer refresh and over-ceiling/cold project/section frames. SVR: cr3-findings V2. [MODERATE]
- **Reframe**: serve-stale-within-bound makes cadence a **freshness DIAL, not an availability requirement**. A read does not fail because a frame is stale-within-bound; it serves the LKG and refreshes. So "how fresh" is a *contract input* (§E), not a hard warm-interval requirement.

**Operational implications**:
- Warm interval and the serve-stale ceiling are **independent knobs**; the ceiling (not the cron) is what bounds worst-case staleness. Calibrating §E lets us *loosen* the ceiling where the real need allows -> **fewer over-ceiling builds -> less semaphore pressure -> fewer 502s**.
- The **15-min fast-lane warmer is TF-defined but HELD / NOT deployed** (`aws lambda get-function autom8-asana-cache-warmer-fast` -> ResourceNotFound; held PRs #97/#338). SVR (aws-resource): get-function ResourceNotFound. It is likely **superseded by serve-stale calibration**; we hold it pending §E rather than deploy speculatively.

---

## D. PQ-5 CONTRACT CONFIRMATIONS [STRONG on (a)(b), the section-arm is a confirmed VULNERABILITY]

- **(a) Retry-After ✓** — SET on the 503: `headers={"Retry-After": str(retry_after_seconds)}`. SVR: `api/errors.py:621-638`; type at `exception_types.py:136-151`. [STRONG — structural read]
- **(b) honest_empty ✓** — semantics: **200 + `meta.honest_empty`**, gated on `honest_empty = honest_contract_complete AND prefilter_row_count==0` (prefilter count at `:135-141`; meta at `models.py:419-427`). SVR: `query/engine.py:264`; `models.py:419-427`. [STRONG — structural read]
- **(c) canary section-arm = degenerate-unfiltered VULNERABILITY** — when `project_gid` is present but `section_gid` is absent, the section filter is **skipped** (applied only `if section_name_filter is not None`) -> a **silent UNFILTERED project-wide query**. SVR: `query/engine.py:163-165`. [STRONG on the vulnerability]

**ASK (decision requested)**: **monolith seeds a valid `section_gid` for the canary section-arm**, OR we add an explicit receiver-side guard/error that fails closed on a section-arm with no `section_gid`. We default-recommend the guard (fail-closed is safer for a deploy gate), but the seed is cheaper if you own a stable canary `section_gid`. **Your call — please decide.**

---

## E. FRESHNESS-CONTRACT ELICITATION ASK — THE LINCHPIN [the single highest-value return]

**ASK: the monolith owners ratify an explicit, per-entity FRESHNESS DATA-CONTRACT for project/section reads.**

**Why it is load-bearing** (this is the one paragraph that matters most): the real freshness need is **UNKNOWN**. The contract calibrates `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` (a per-entity override of the multiplier-derived LKG ceiling, `LKG_MAX_STALENESS_MULTIPLIER(10.0) × ttl`, SVR `dataframe_cache.py:525-546`) -> which sets how often a build is forced -> which sets the **502 pressure**. A looser-but-validated bound = fewer over-ceiling builds = less semaphore pressure = fewer 502s. **This contract ties freshness AND the 502 together** — it is the single highest-value thing we need back. The current 50-min default is a **correctable internal policy, not a consumer contract**; we are asking you to tell us the *real need* so we can meet it, not to relax anything.

**Evidence-based tiered DRAFT to react to** (these are *strawman* tiers — the real need is yours to ratify, not ours to assume):

| Entity / read | Strawman max-acceptable staleness | Rationale to confirm/correct |
|---|---|---|
| `project` rows (registry/membership) | **<= 4h** | project-level structure changes slowly; tolerant of a 4h bound |
| `section` rows (per-project sections) | **<= 60 min** | section membership drives downstream joins; tighter but not real-time |
| any read feeding a **user-visible** offer-holder decision | **<= 15 min** | if a stale section misroutes an offer, 15-min caps the exposure (would justify the held fast-lane) |
| backfill / analytics-only reads | **<= 24h** | no interactive consumer; cheapest to serve stale |

**What we need from you**: confirm, correct, or replace these tiers with the *real* per-entity bounds (and name any read that is genuinely near-real-time). We will set `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` per entity to the ratified values and attest each served-stale read via `meta.stale_served` (minimal change — V6 already carries `freshness`/`data_age_seconds`/`staleness_ratio` at `models.py:354-427`). SVR: `models.py:354-427`. [MODERATE]

---

## F. OPEN QUESTION — confirm the REAL concurrent fan-out width

**The ~104 is OUR test-probe fixture, not your live concurrency.** SVR: `tests/spikes/probe_concurrency_semaphore.py:42` (`N_PROJECTS=104`, "S7 gameday width"). Our **live distinct warm-set = 34** (`project_registry.py:271-275`, `CONSUMER_WARM_SET_GIDS`). 34 GIDs × {project, section} = 68 max build keys/cycle. The per-section fan-out hypothesis is **REFUTED** (build key is `(project_gid, entity_type)`, section is post-build at `universal_strategy.py:922`). SVR: `project_registry.py:271-275`; `universal_strategy.py:922`. [MODERATE]

**ASK**: what is the monolith's **true concurrent project count** (34 vs 104?) and its **`max_workers`** (you claimed 10; UV-P — unverified in monolith source from our side)? This **sizes the capacity fix** (the `max_concurrent_builds` + CPU/mem decision in §A). We will not over-provision against a 104 that is only our probe, nor under-provision against a real width we cannot see.

---

## G. STRATEGIC INPUT — direction of the receiver [MODERATE]

Framing so you understand where this is going (per the ratified LICENSE, operator interview 2026-06-03):
- The receiver is evolving into the **fleet's canonical materialized-data plane** — this instance (#1) is being built for **generality/reuse**, not lift-and-shift. project/section is the first consumer; more will follow.
- **The read contract is serve-stale-within-bound.** Consumers read a freshness-bounded materialized view; the bound is the contract (§E), not a guarantee of live freshness. "Done" = cutover + retire in-process get_df + **>=99% AND paradigm-right** (smells fixed or ADR-tracked).
- **CQRS / CDC / ingestion-layer are tracked R&D** — not in this cutover. We are deliberately *not* over-building now; serve-stale ships, the deeper ingestion architecture is a forward decision variable.
- Implication for you: design monolith consumers to **read the materialized plane with a declared freshness tier** (§E), and treat the receiver as the source of truth for project/section reads once cutover clears — not as a cache in front of your in-process path.

---

## Acceptance criteria (what closes this return)

1. **§A**: you acknowledge NO PASS / no Stage-B, and that the re-gate (rite-disjoint, >=99% BOTH arms, 3-cause disaggregated, at the confirmed width) is the precondition. Stage-B remains human/IC-gated.
2. **§B**: you point auth at Secret 1 + confirm via a live re-mint (lifts us to STRONG); we decommission Secret 2 and declare the authoritative store + rotation cadence in IaC.
3. **§C**: you accept 30-min bulk + 4h offer as the cadence; the 15-min fast-lane stays held pending §E.
4. **§D**: you decide section-arm = **seed a canary `section_gid`** OR **receiver guard** (fail-closed).
5. **§E (linchpin)**: you ratify per-entity freshness tiers (confirm/correct the strawman) -> we set `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` + attest `meta.stale_served`.
6. **§F**: you confirm true concurrent project count + `max_workers` -> we size the capacity fix.

## Open questions back to the monolith (handoff_back)

- **OQ-1 (blocking §A sizing)**: real concurrent fan-out width + `max_workers`? (UV-P from our side.)
- **OQ-2 (blocking §E)**: ratified per-entity freshness tiers — confirm/correct the strawman.
- **OQ-3 (§D)**: seed a canary `section_gid` or accept a receiver fail-closed guard?
- **OQ-4 (§B)**: confirm the live re-mint against Secret 1 (this is what lifts the cred grade to STRONG).

---

## Disciplines applied

- **Self-ref MODERATE ceiling**: every conclusion here is capped at MODERATE until a rite-disjoint live-under-bulk re-gate corroborates; we authored the fix, so we issue **no PASS self-certification**.
- **No secret VALUES**: all credential material redacted to prefix/digest only (`sa_1a95…`); digests compared, raw values never printed.
- **Meet-the-real-need framing**: no item asks you to relax a contract; §E explicitly asks for the *real* need so we can calibrate to it.
- **SVR receipts**: every platform claim carries a `file:line` or aws-resource receipt; the monolith `max_workers=10` claim is marked **UV-P** (unverified from our side).
- **Telos-integrity**: "done" = verified-realized + paradigm-right; this return is INTERIM precisely because that bar is not yet met.
- **Stage-B gate**: remains **human/IC-gated**; this artifact does not authorize it.

*Prepared by autom8y-asana SRE / Incident Commander, 2026-06-03. Default-to-REFUTED held throughout. Grounding: `.sos/wip/cr3-verified-findings-2026-06-03.md`.*
