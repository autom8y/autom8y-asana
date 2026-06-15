---
artifact_id: HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03
schema_version: "1.0"
source_rite: 10x-dev
target_rite: sre
handoff_type: execution
priority: critical
blocking: true
initiative: cr3-fleet-data-plane-foundation-cutover
created_at: "2026-06-03T15:00:00Z"
# HANDOFF schema (cross-rite-handoff, HANDOFF-009) mandates status: pending for an
# unaccepted handoff. The .ledge/ ledge_status below is the additive discoverability
# field (proposed); it does NOT displace the schema-required status field.
status: pending
type: handoff
ledge_status: proposed
source_artifacts:
  - ".sos/wip/cr3-verified-findings-2026-06-03.md"
  - "/Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-arch-autom8-to-sre-autom8y-asana-cr3-producer-work-queue-2026-06-03.md"
  # NOTE: the prior handoff above has NO §6. The office_phone/vertical content-contract (S7-GATE-FIDELITY
  # criterion #3) and the HTTP-2xx body-blind liveness-masquerade (criterion #2) live in the spike below,
  # which the prior handoff lists in its §4 read-first art.
  - "/Users/tomtenuta/Code/autom8/.sos/wip/SPIKE-cr3-getdf-callsites-gid-reconciliation.md"
  - "src/autom8_asana/cache/dataframe/build_coordinator.py"
  - "src/autom8_asana/cache/dataframe/dataframe_cache.py"
  - "src/autom8_asana/api/routes/query.py"
  - ".claude/agent-memory/platform-engineer/asana-dataframe-resolver-cred-topology.md"
provenance:
  - { source: ".sos/wip/cr3-verified-findings-2026-06-03.md", type: artifact, grade: moderate }
  - { source: "src/autom8_asana/cache/dataframe/build_coordinator.py:130-131", type: code, grade: strong }
  - { source: "src/autom8_asana/cache/dataframe/dataframe_cache.py:496-546", type: code, grade: strong }
  - { source: "src/autom8_asana/query/engine.py:163-165", type: code, grade: strong }
  - { source: "aws lambda get-function autom8-asana-cache-warmer-bulk (deployed 2026-06-03 09:06)", type: artifact, grade: strong }
  - { source: ".claude/agent-memory/platform-engineer/asana-dataframe-resolver-cred-topology.md", type: artifact, grade: moderate }
  - { source: "/Users/tomtenuta/Code/autom8/.sos/wip/SPIKE-cr3-getdf-callsites-gid-reconciliation.md:35,55", type: artifact, grade: moderate }
evidence_grade: moderate
tradeoff_points:
  - attribute: "freshness-precision vs build-pressure relief"
    tradeoff: "serve-stale-within-bound trades guaranteed-fresh reads for fewer over-ceiling cache-miss builds (less semaphore pressure → fewer 502s)"
    rationale: "the real freshness need is UNKNOWN and must be elicited as a data contract from monolith owners; until then the 50-min LKG ceiling is an internal default, not a consumer contract. A looser-but-validated bound is correctness-preserving AND capacity-relieving — these are the same lever."
  - attribute: "self-referential evidence ceiling vs delivery velocity"
    tradeoff: "all PASS/compliance conclusions in this handoff are capped at MODERATE absent rite-disjoint live-under-bulk corroboration"
    rationale: "the re-gate is the corroboration event; the receiver rite authored the fixes, so it cannot self-certify the PASS. STRONG requires the chaos-engineer's rite-disjoint live measurement post-warmer."
items:
  - id: PQ-1
    summary: "BLOCKING. The 502 is build-semaphore starvation (max_concurrent_builds=4 × single worker × cpu_thread=4 under wide cache-miss fan-out → 55s timeout → 503 → ALB 502). REFRAME: the misses were driven by the DARK project/section warm path, now fixed by the 30-min bulk warmer. Re-measure 502 POST-warmer; the 82% is a stale pre-fix datum. Durable fix: raise max_concurrent_builds + the REQUIRED CPU/mem bump."
    priority: critical
    acceptance_criteria:
      - "Re-measured ≥99% satellite per Source on BOTH Project AND Section arms, AFTER the 30-min bulk warmer (autom8-asana-cache-warmer-bulk) has run ≥1 full sweep — NOT against the dark-pre-state 82% datum."
      - "CPU_STARVATION = 0 across a 4-signal panel (CPU util, /health latency, ALB target-health flaps, 503 CACHE_BUILD_IN_PROGRESS rate) for the duration of the re-gate window."
      - "Singleflight coalescing PROVEN under bulk: builds_coalesced > 0 with ≥1 completed under concurrent same-(project_gid,entity_type) load (not the #90 single-gid 2-build artifact)."
      - "Re-gate runs ≥2 concurrent request streams at the confirmed live fan-out width (see OQ-1), with a rite-disjoint SLI authored by chaos-engineer, not the receiver author. BLOCKED until monolith provides the OQ-1 answer (real concurrent fan-out width + max_workers confirmation). Do NOT start chaos-engineer re-gate measurement without this input — measuring at the wrong width (e.g. the 104 test-probe fixture instead of live width) produces a paradigm-wrong datum."
      - "If raising max_concurrent_builds: the CPU/mem bump lands FIRST and is verified (4 builds × ~2GB > current 2GB task) — the lever is inert and DANGEROUS without it."
    notes: >
      V1 root cause [STRONG, code-anchored]: POST /{entity_type}/rows (query.py:419-580) → engine.execute_rows
      → on miss universal_strategy.py:1035 fire-and-forget build → request returns 503 CACHE_BUILD_IN_PROGRESS
      (query.py:543). Coalescing key = (project_gid, entity_type) only (build_coordinator.py:51); different
      (project_gid,'section') keys EACH need a semaphore slot. max_concurrent_builds=4 hardcoded
      (build_coordinator.py:130-131), single uvicorn worker (entrypoint.py:52-57, no workers arg),
      cpu_thread_concurrency=4 (settings.py:276-285), cpu=1024/mem=2048 → 768 units after ADOT 256
      (autom8 …/asana/main.tf:144-159). Mechanism: >4 cache-MISS section keys → semaphore queue exceeds
      default_timeout_seconds=55.0 (lifespan.py:232-234) → 503; CPU saturation (4 Polars builds × 4 threads)
      → /health slow → ALB unhealthy after 3 (main.tf:127-137) → 60s idle → 502.
      THE REFRAME [MODERATE, V1×V2×V6]: the mass misses were caused by the DARK project/section warm path
      (effectively unscheduled pre-2026-06-03 09:06, V2). The 30-min bulk warmer now keeps reads on the
      serve-stale path (V6, dataframe_cache.py:496-546) instead of the 4-slot build path, so the 502 should
      largely dissolve. The 82% (V5: 85 sat/19 fb of 104) was measured under the test probe PRE-bulk-warmer —
      it is a stale datum and MUST be re-measured. DURABLE HEADROOM (beyond warming): max_concurrent_builds=4
      is a latent cap on any cold-start/over-ceiling burst; raising it is the durable PQ-1 fix but REQUIRES the
      CPU/mem bump. Owner: platform-engineer (headroom + CPU/mem) → chaos-engineer (re-gate measurement).
    dependencies: []
  - id: PQ-2
    summary: "RESOLVED. The monolith's 'DAILY' cadence claim is REFUTED — it observed only the ~4h offer warmer because the project/section warm path was dark. The 30-min bulk warmer (cron(0,30 * * * ? *)) deployed 2026-06-03 09:06. Fast-lane PRs #97/#338 are HELD, likely superseded by the serve-stale-bound."
    priority: high
    acceptance_criteria:
      - "Confirm the bulk warmer (autom8-asana-cache-warmer-bulk, prematerialize_bulk_set=true) is sweeping the CONSUMER_WARM_SET_GIDS on the 30-min cadence in prod (live invocation evidence, not TF-defined-only)."
      - "Record the operational implication in obs.md: cadence is no longer a fallback-cause input once the bulk warmer is verified live; DAILY was the dark pre-state, not a design choice."
      - "Keep fast-lane #97/#338 HELD until the serve-stale calibration (see SERVE-STALE-ADR) decides whether a 15-min lane is still needed; do NOT deploy it speculatively."
    notes: >
      V2 [STRONG for the bulk-warmer deploy; MODERATE for the dark-pre-state inference]: live now = offer warmer
      cron(0 */4 * * ? *) + bulk warmer cron(0,30 * * * ? *) deployed 2026-06-03 09:06 (autom8-asana-cache-warmer-bulk).
      Pre-today the project/section warm path was effectively dark/unscheduled, so the monolith saw only the ~4h
      daily offer refresh — hence its "DAILY" claim and the over-ceiling/cold frames that drove the misses behind
      PQ-1. The 15-min fast warmer is TF-defined but NOT deployed (aws lambda get-function
      autom8-asana-cache-warmer-fast → ResourceNotFound). RATIONALE for HOLD: a validated serve-stale bound
      (SERVE-STALE-ADR) likely removes the need for a third cadence tier — adding the fast lane now is premature
      complexity against an unconfirmed need. Owner: platform-engineer.
    dependencies: []
  - id: PQ-3
    summary: "FALSE-ALARM [MODERATE]. The monolith's 200-vs-401 credential divergence is an ENVELOPE-SHAPE mismatch, not a value mismatch — same underlying secret value. Converge on the authoritative Secret 1, decommission the vestigial Secret 2, declare both SSM+SM in IaC (currently out-of-band), add rotation cadence + drift alarm. ALL secret values REDACTED."
    priority: high
    acceptance_criteria:
      - "Declare the authoritative credential (envelope-shape JSON {client_id, client_secret}, named autom8y/asana-dataframe-resolver) AND the SSM oauth-client-id pointer in IaC — both are currently provisioned OUT-OF-BAND."
      - "Decommission the vestigial bare-string secret (autom8y/auth/service-api-keys/asana-dataframe-resolver, the G2-PRE migration-028 artifact) after confirming it is consumed by NEITHER monolith NOR receiver."
      - "Add a rotation cadence + a drift alarm that fires when the SSM client_id pointer and the SM envelope client_id diverge."
      - "Lift the grade to STRONG via a LIVE re-mint against BOTH store paths (the 200 and the 401), comparing minted tokens — NOT a digest comparison alone."
      - "Every artifact REDACTS secret values to prefix+length or digest (e.g. client_id sa_1a95…, len N). NEVER print a raw client_secret or token."
    notes: >
      V3 [MODERATE — digest comparison + agent-memory, NOT a live re-mint by us]: both secrets EXIST and share
      the SAME client_id (sa_1a95…, redacted; SSM /autom8y/platform/asana-dataframe-resolver/oauth-client-id =
      Secret 1's client_id). The divergence is ENVELOPE SHAPE, not value: Secret 1 = JSON {client_id,
      client_secret} (authoritative, autom8y/asana-dataframe-resolver, 2026-06-01; receiver canary consumes via
      hermes SSM→SM); Secret 2 = bare string (autom8y/auth/service-api-keys/asana-dataframe-resolver, 2026-05-26,
      G2-PRE migration-028 artifact). Per platform-engineer/asana-dataframe-resolver-cred-topology.md, the
      envelope client_secret digest == the bare-string raw digest = SAME value. The monolith's 401 is a
      stale-store-path/backend issue (AUTH-TEB-001), not a value mismatch. DISTINCTION: do NOT conflate the
      consumer-identity (asana-dataframe-resolver) with the receiver's-OWN-identity (asana-service,
      main.tf:194-196 / variables.tf:17-20) — different credentials. Owner: platform-engineer.
    dependencies: []
  - id: PQ-5
    summary: "Retry-After ✓ and honest_empty ✓ CONFIRMED. The canary section-arm is a DEGENERATE-UNFILTERED VULNERABILITY: project_gid present + section_gid absent → section filter silently skipped → unfiltered project-wide query. Decision required: receiver adds an explicit guard OR monolith seeds a valid section_gid for the canary."
    priority: high
    acceptance_criteria:
      - "[platform-engineer] DECISION REQUIRED (DUE BEFORE S7-GATE-FIDELITY work): implement an explicit guard (reject section-entity request with section_gid absent) OR ask monolith to seed a valid section_gid into the canary fixture — pick one and implement it before any Section-arm gate measurement. Record the decision in .ledge/decisions/PQ-5-section-guard-choice-2026-06-03.md. This is a GATE on S7-GATE-FIDELITY (which depends on PQ-5): the Section half of the S7 composite CANNOT clear until this decision is recorded and implemented."
      - "Retry-After confirmed live-firing on the 503 under bulk (currently structurally wired only — see notes)."
      - "honest_empty confirmed returning 200 + meta.honest_empty on a genuinely-empty honest-complete project under the re-gate."
    notes: >
      V4 [STRONG, code-anchored for (a)(b); the section-arm vuln is the load-bearing finding]:
      (a) Retry-After SET on the 503 (errors.py:621-638, headers={"Retry-After": str(retry_after_seconds)};
      exception_types.py:136-151). ✓  (b) honest_empty: engine.py:264 honest_empty = honest_contract_complete
      and prefilter_row_count==0 (prefilter count at :135-141); 200 + meta.honest_empty (models.py:419-427). ✓
      (c) CANARY SECTION-ARM = REAL VULNERABILITY: project_gid present + section_gid absent → section filter
      skipped (engine.py:163-165, applied only if section_name_filter is not None) → SILENT unfiltered
      project-wide query. This is the receiver-side analogue of the prior handoff's §2.PQ-5 canary section-arm
      degeneration — a degenerate section query reads green while measuring the wrong thing. (The prior handoff
      has NO §6; the office_phone/vertical content-contract is in its §4 read-first spike
      SPIKE-cr3-getdf-callsites-gid-reconciliation.md:35, where SECTION frames are column-contract-EXEMPT.)
      DECISION REQUIRED (platform-engineer, due before S7-GATE-FIDELITY work), recorded in
      .ledge/decisions/PQ-5-section-guard-choice-2026-06-03.md: guard (reject section request with missing
      section_gid) OR routed back to monolith (seed). This is a GATE on S7-GATE-FIDELITY.
    dependencies: []
  - id: SERVE-STALE-ADR
    summary: "Formalize serve-stale as the ratified paradigm. Add meta.stale_served + a FRESHNESS_CONTRACT_MAX_AGE_SECONDS knob, calibrate the bound to the elicited freshness contract (the linchpin). This is ATTESTATION + a contract-bound knob, NOT new architecture — serve-stale already exists up to the LKG ceiling."
    priority: high
    acceptance_criteria:
      - "ADR ratifies serve-stale-within-bound as the freshness paradigm: 3-state (FRESH / APPROACHING_STALE+SWR / STALE+LKG) with a hard-reject ceiling, citing the existing implementation (V6)."
      - "Add meta.stale_served: bool to RowsMeta (which already carries freshness/data_age_seconds/staleness_ratio)."
      - "Add FRESHNESS_CONTRACT_MAX_AGE_SECONDS config knob (per-entity, overrides the multiplier-derived ceiling) and CALIBRATE it to the freshness contract elicited from monolith owners (OQ-2). BLOCKED until monolith provides the OQ-2 answer (actual freshness tolerance per entity). Do NOT ratify the ADR or deploy meta.stale_served + the knob without the calibrated bound — an uncalibrated bound is an arbitrary internal default masquerading as a consumer contract."
      - "Document the dual lever: a looser-but-validated bound = fewer over-ceiling builds = less semaphore pressure = fewer 502s — i.e. this directly relieves PQ-1."
    notes: >
      V6 [STRONG, code-anchored]: serve-stale is ALREADY IMPLEMENTED. 3-state + ceiling (dataframe_cache.py):
      FRESH (≤ttl) serve; APPROACHING_STALE (ttl<age≤3×ttl) serve + SWR refresh (:496-523); STALE
      (≤ LKG_MAX_STALENESS_MULTIPLIER(10.0)×ttl = max_age) serve LKG + refresh; age>max_age → hard-reject →
      cache-miss → build → 503 (:525-546). RowsMeta already carries freshness, data_age_seconds, staleness_ratio
      (models.py:354-427). So the only NEW work is (a) meta.stale_served bool + (b) the contract-driven bound knob.
      LICENSE TIE-IN: the real freshness need is UNKNOWN; the 50-min default (10.0× ceiling on project/section) is
      a correctable INTERNAL policy, not a consumer contract — calibrate to the elicited contract, do not relax
      it arbitrarily. This is the LINCHPIN that ties freshness AND the 502 together. Owner: platform-engineer +
      observability-engineer (attestation EMF).
    dependencies: ["PQ-1"]
  - id: S7-GATE-FIDELITY
    summary: "Before Stage-B (fallback deletion), DISAGGREGATE the 3 GetDfFallback causes (503-cadence / 502-capacity / honest-refusal) into distinct signals, and bind the canary to CONTENT/cause — not liveness. Three causes currently collapse into ONE EMF signal; a false-green S7 is dangerous because Stage-B removes the fallback."
    priority: critical
    acceptance_criteria:
      - "GetDfFallback EMF disaggregated into 3 distinct causes (503-cadence, 502-capacity, honest-refusal) so the S7 verdict reads cause, not a single collapsed counter."
      - "Canary assertion bound to Contract-B column CONTENT (or the disaggregated honest EMF), defeating the liveness-masquerade — a 2xx carrying an empty/wrong frame MUST fail the gate (liveness-masquerade documented at prior handoff §2.PQ-5 line 90 'HTTP-2xx body-blind', and SPIKE-cr3-getdf-callsites-gid-reconciliation.md:55 'NOT HTTP-2xx — body-blind = the liveness-masquerade trap')."
      - "Section-arm content coverage resolved per PQ-5 (guard or seed) AND per the prior handoff's content-contract decision before the Section half of the S7 composite can clear. CITATION: the prior handoff (HANDOFF-arch-autom8-to-sre-autom8y-asana-cr3-producer-work-queue-2026-06-03.md) has NO §6; the office_phone/vertical content-contract lives in its §4 read-first spike SPIKE-cr3-getdf-callsites-gid-reconciliation.md:35, which states: 'PROJECT frames only: office_phone + vertical — the load-bearing MultiIndex-join contract … SECTION frames are EXEMPT (assert_column_contract=False, SIG-3 getdf_signals.py:233-241).' BLOCKING CONDITION: because the Section arm is column-contract-EXEMPT, a Section 2xx cannot be asserted on office_phone/vertical presence — so the Section half MUST instead be cleared on the disaggregated honest-EMF/cause signal (criterion #2) plus the PQ-5 section_gid guard-or-seed decision, NOT on column content. Resolve that scope decision explicitly before the Section half clears."
      - "This disaggregation lands BEFORE the 7-of-7 daily ≥99% composite window starts on either arm."
    notes: >
      [MODERATE, synthesis + prior-handoff §2.PQ-5 / §4-spike anchors]: per the grounding synthesis (item 4) and the monolith's
      own S7-fidelity risk, three causes — cadence-503, capacity-502, honest-refusal — collapse into one
      GetDfFallback EMF. A false-green S7 is dangerous specifically because Stage-B removes the fallback that
      currently preserves failure-domain independence (partial → full distributed monolith). The canary today is
      2xx-shaped on BOTH sides (deploy-gate at receiver_bulk_fanout_deploy_gate.py:404 + receiver metric at
      api/metrics.py:241/346) — it reads no content/EMF/column signal. Owner: observability-engineer (EMF split)
      + chaos-engineer (canary content binding).
    dependencies: ["PQ-1", "PQ-5"]
  - id: FLEET-DATA-PLANE-RND
    summary: "TRACKED, post-CR-3. The ratified telos is a fleet materialized-data-plane foundation (this receiver = instance #1). Investigate CQRS read/materialize split, Asana CDC/incremental ingestion, a generic ingestion-layer, and reuse of the existing analytics semantic layer (QueryableMetric/CompositeMetric) — but ONLY at genuine architectural-smell/decision points, not as CR-3 scope."
    priority: medium
    acceptance_criteria:
      - "Open an R&D track entry (no CR-3 deliverable) capturing: CQRS read/materialize split, Asana CDC/incremental ingestion, generic ingestion-layer, analytics-semantic-layer (QueryableMetric/CompositeMetric) reuse."
      - "Each item gates on a genuine smell-point or decision-point — NOT speculative lift-and-shift; correctness-first, no hard deadline (per license)."
      - "Explicitly OUT of the CR-3 cutover critical path; CR-3 ships serve-stale-now + headroom, R&D is the foundation evolution."
    notes: >
      LICENSE [ratified, operator interview 2026-06-03]: objective = fleet materialized-data-plane foundation,
      optimize for generality/reuse not lift-and-shift; decision variables = serve-stale NOW, CQRS/CDC/ingestion-layer
      = tracked R&D, receiver self-contained EXCEPT investigate the existing analytics semantic layer reuse at genuine
      smell points. Bounds: correctness-first (no hard deadline), balance simplicity ↔ right-foundation ↔ cost, full
      autonomy + surface forks. Owner: incident-commander to triage into the R&D track post-cutover.
    dependencies: ["PQ-1", "SERVE-STALE-ADR"]
---

# HANDOFF — autom8 (arch / 10x-dev) → autom8y-asana (SRE): CR-3 Producer Work-Queue, INGESTED

> **Direction**: autom8 (arch / 10x-dev) → autom8y-asana (sre). **Class**: execution + validation.
> **This is a REVERSE handoff**: the monolith's PRODUCER WORK-QUEUE is ingested here as the receiver/SRE rite's OWN re-prioritized work queue, reconciled against 6 rite-disjoint verified findings.
> **Decision/verdict first**: PQ-1 (the 502) is the single BLOCKING item, and it is most likely ALREADY LARGELY DISSOLVED by today's 30-min bulk warmer — but that is UNPROVEN until a post-warmer re-gate measures it. Everything else is RESOLVED, FALSE-ALARM, or ALREADY-IMPLEMENTED. **Do not start the S7 clock until PQ-1 is re-measured post-warmer.**
> **Discipline**: every platform claim carries an SVR `file:line` / aws-resource receipt drawn from the grounding doc, or is marked UV-P. Conclusions graded [STRONG/MODERATE/WEAK]. Self-referential PASS claims are capped at MODERATE absent rite-disjoint live-under-bulk corroboration. Secret VALUES are REDACTED to prefix+length/digest. We never ask the consumer to relax — we meet the real need. Done = verified-realized + paradigm-right.

---

## §1. Telos & ratified LICENSE

**Telos**: this receiver is **instance #1 of a fleet materialized-data-plane foundation** — optimize for generality/reuse, not lift-and-shift.

**Done (telos-integrity)** = cutover + retire the in-process `get_df` + **target: ≥99% satellite-serve AND paradigm-right** (verified-realized post re-gate, **not** current state; smells fixed or ADR-tracked). "Done" is *verified-realized*, not *code-landed*: the re-gate measurement is the realization event. The ≥99% figure is a **target**, not a self-certified PASS — it is correctly hedged as PENDING in §6 acceptance criteria and capped at MODERATE per §7 until rite-disjoint corroboration.

**Freshness constraint**: the real need is **UNKNOWN → elicit a data contract from monolith owners**; **serve-stale within a bound** calibrated to it. "Never relax the consumer" means *meet the real need* — the 50-min LKG default is a correctable internal policy, **not** a consumer contract.

**Decision variables**: serve-stale **now**; CQRS / CDC / ingestion-layer = tracked **R&D**; receiver self-contained *except* investigate existing analytics-semantic-layer (QueryableMetric/CompositeMetric) reuse at genuine smell-points.

**Bounds**: correctness-first (no hard deadline); balance simplicity ↔ right-foundation ↔ cost; **full autonomy, surface forks**.

---

## §2. RECONCILIATION — monolith claim vs verified reality

The monolith sent a producer work-queue built from its own vantage (dark warm path, test-probe width, store-path 401). Six rite-disjoint verifiers (workflow `wf_91d1efdc`) reconcile it against the receiver's actual code + live AWS state:

| # | Monolith claimed | Verified reality | Finding | Receipt | Grade |
|---|------------------|------------------|---------|---------|-------|
| 1 | `SatelliteClientError → 502` under bulk = the blocker | TRUE root cause, but it is **build-semaphore STARVATION** (4-slot cap × 1 worker × cpu_thread=4 → 55s timeout → 503 → ALB 502), driven by mass cache-MISSES | **V1** | `build_coordinator.py:130-131`, `query.py:543`, `lifespan.py:232-234`, `settings.py:276-285`, `autom8 …/asana/main.tf:127-159` | STRONG |
| 2 | Cadence is **DAILY** (ADR-004 proposes 4h) | **REFUTED** — DAILY was the *dark pre-state*. The project/section warm path was effectively unscheduled; the 30-min bulk warmer deployed **2026-06-03 09:06** | **V2** | `aws lambda get-function autom8-asana-cache-warmer-bulk` (cron `0,30 * * * ? *`, `prematerialize_bulk_set=true`) | STRONG (deploy); MODERATE (dark-inference) |
| 3 | Credential divergence: `asana-dataframe-resolver`=200 vs `…/service-api-keys/asana-dataframe-resolver`=401 | **FALSE-ALARM** — same `client_id` (`sa_1a95…`), divergence is **ENVELOPE SHAPE** (JSON vs bare string), same underlying value. The 401 is a stale store-path (AUTH-TEB-001), Secret 2 is **vestigial** | **V3** | `platform-engineer/asana-dataframe-resolver-cred-topology.md`; SSM `/autom8y/platform/asana-dataframe-resolver/oauth-client-id` == Secret 1 client_id | MODERATE |
| 4 | ~104 projects, section fan-out, `max_workers=10` | **~104 is the TEST-PROBE FIXTURE**, not confirmed live width. Live `CONSUMER_WARM_SET_GIDS` = **34** distinct; per-section fan-out hypothesis **REFUTED** (build key = `(project_gid, entity_type)`, section post-build) | **V5** | `project_registry.py:271-275` (34); `tests/spikes/probe_concurrency_semaphore.py:42` (`N_PROJECTS=104`); `universal_strategy.py:922` | MODERATE |
| 5 | (implicit) serve-stale is new architecture to build | **ALREADY IMPLEMENTED** up to the LKG ceiling — 3-state FRESH/APPROACHING_STALE+SWR/STALE+LKG with hard-reject ceiling; honest markers already on `RowsMeta` | **V6** | `dataframe_cache.py:496-546`, `models.py:354-427` | STRONG |
| 6 | PQ-5 contracts (Retry-After / honest_empty / canary) need confirming | Retry-After ✓, honest_empty ✓; **canary section-arm = degenerate-unfiltered VULNERABILITY** (section_gid absent → silent project-wide query) | **V4** | `errors.py:621-638`, `engine.py:264` + `:135-141`, `engine.py:163-165` | STRONG |

**Load-bearing reframe**: the 502 (V1) and the dark warm path (V2) and serve-stale (V6) are ONE system. The misses that starved the 4-slot build path came from the dark warm path; the 30-min bulk warmer keeps reads on the serve-stale path instead. **The 82% is a stale pre-fix datum** — re-measure POST-warmer before any verdict.

---

## §3. THE WORK QUEUE (re-prioritized)

> Re-prioritized from the monolith's PQ-1..PQ-5. PQ-4 (FallbackCause tagging) is folded into **S7-GATE-FIDELITY**. The serve-stale ADR and the fleet R&D track are added per the ratified license.

### PQ-1 [BLOCKING] — 502 build-semaphore starvation → re-measure post-warmer, then durable headroom
- **Owner**: platform-engineer (headroom + CPU/mem) → chaos-engineer (re-gate measurement).
- **Root cause [V1, STRONG]**: see frontmatter `PQ-1.notes` for the full chain (`build_coordinator.py:130-131` 4-slot cap, single worker `entrypoint.py:52-57`, `cpu_thread_concurrency=4` `settings.py:276-285`, 55s timeout `lifespan.py:232-234`, ALB flap `main.tf:127-137`).
- **The reframe [V1×V2×V6, MODERATE]**: the misses were driven by the DARK project/section warm path (V2), now fixed by the 30-min bulk warmer; serve-stale (V6) already covers reads up to the LKG ceiling → **re-measure the 502 POST-bulk-warmer**. The 82% (V5) is stale, pre-fix.
- **Durable headroom fix**: raise `max_concurrent_builds` (`build_coordinator.py:130-131`) **AND** the REQUIRED CPU/mem bump — 4 builds × ~2GB frame ≈ 8GB ≫ current 2GB task. The lever is **inert and dangerous** without the bump.
- **[precondition] Substrate-certification gate**: the post-warmer re-gate runs ONLY on a substrate certified cleanly-merged → 0-drift `terraform plan` → QA-smoked via the releaser track (`HANDOFF-sre-to-releaser-cr3-receiver-substrate-certification-2026-06-03.md`). The 30-min bulk warmer + serve-stale + cpu=1024 + IAM landed via out-of-band local applies this session; until releaser certifies zero drift between `main` and prod, "deployed" is assumed not proven — **do not measure the re-gate on an uncertified substrate** (a paradigm-wrong-datum risk equal to the OQ-1 width error).
- **Acceptance** (frontmatter): ≥99% per Source (Project AND Section), re-measured post-bulk-warmer; CPU_STARVATION=0 on a 4-signal panel; singleflight proven under bulk; ≥2 concurrent streams at confirmed live width; rite-disjoint SLI authored by chaos-engineer.

### PQ-2 — cadence RESOLVED
- **Owner**: platform-engineer.
- **Status [V2]**: the 30-min bulk warmer is deployed (`autom8-asana-cache-warmer-bulk`, cron `0,30 * * * ? *`). The monolith's "DAILY" was the dark pre-state (only the ~4h offer warmer ran).
- **Fast-lane #97/#338 HELD** — likely superseded by the serve-stale bound (a validated bound removes the need for a third cadence tier). Do **not** deploy speculatively.
- **Operational implication**: once the bulk warmer is verified live, cadence drops out as a fallback-cause input; record in `obs.md`.

### PQ-3 — credential FALSE-ALARM [MODERATE]
- **Owner**: platform-engineer.
- **Disposition [V3]**: converge on the authoritative **Secret 1** (envelope JSON `{client_id, client_secret}`, `autom8y/asana-dataframe-resolver`); decommission the **vestigial Secret 2** (bare string, `…/auth/service-api-keys/asana-dataframe-resolver`, migration-028 artifact); **declare both SSM + SM in IaC** (currently out-of-band); add a **rotation cadence + drift alarm** (fires when SSM client_id pointer ≠ SM envelope client_id).
- **Confirm via live re-mint** against BOTH paths (the 200 and the 401) to lift MODERATE→STRONG — digest comparison alone is not enough.
- **REDACT all secret values** to prefix+length/digest (`client_id sa_1a95…`); never print a raw `client_secret` or token.
- **Do NOT conflate** consumer-identity (`asana-dataframe-resolver`) with the receiver's-own-identity (`asana-service`, `main.tf:194-196`/`variables.tf:17-20`).

### PQ-5 — contracts: Retry-After ✓ / honest_empty ✓ / canary section-arm VULNERABILITY
- **Owner**: platform-engineer (guard) OR routed to monolith (seed).
- **[V4]** Retry-After ✓ (`errors.py:621-638`), honest_empty ✓ (`engine.py:264`). The **canary section-arm is a degenerate-unfiltered vulnerability**: `project_gid` present + `section_gid` absent → section filter skipped (`engine.py:163-165`) → silent project-wide query.
- **[platform-engineer] DECISION REQUIRED (due BEFORE any S7-GATE-FIDELITY work)**: implement an explicit guard (reject section-entity request with missing `section_gid`) **OR** ask monolith to seed a valid `section_gid` into the canary fixture. Record the choice in `.ledge/decisions/PQ-5-section-guard-choice-2026-06-03.md`. This is a **gate on S7-GATE-FIDELITY** (which `dependencies: [PQ-1, PQ-5]`): the Section half of the S7 composite cannot clear until this decision is recorded and implemented. This is the receiver-side analogue of the prior handoff's §2.PQ-5 canary section-arm degeneration — note the Section arm is column-contract-EXEMPT (prior handoff §4 spike `SPIKE-cr3-getdf-callsites-gid-reconciliation.md:35`), so the guard/seed + honest-EMF signal, not column content, is what clears it.

### SERVE-STALE ADR — formalize the ratified paradigm
- **Owner**: platform-engineer + observability-engineer (attestation EMF).
- **[V6, ALREADY-IMPLEMENTED]** Add `meta.stale_served: bool` + `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` knob (per-entity, overrides the multiplier ceiling); calibrate the bound to the **elicited freshness contract** (OQ-2 — the linchpin). This is **attestation + a contract-bound knob, not new architecture**.
- **Dual lever**: a looser-but-validated bound = fewer over-ceiling builds = less semaphore pressure = **fewer 502s**. The freshness contract ties freshness AND PQ-1 together.

### FLEET-DATA-PLANE R&D track — tracked, post-CR-3
- **Owner**: incident-commander (triage post-cutover).
- CQRS read/materialize split, Asana CDC/incremental ingestion, generic ingestion-layer, analytics-semantic-layer (QueryableMetric/CompositeMetric) reuse — each gated on a **genuine smell-point**, not speculative lift-and-shift. Explicitly OUT of the CR-3 critical path.

---

## §4. S7 GATE-FIDELITY REQUIREMENT (before Stage-B)

The S7 fallback-retirement gate authorizes deleting the legacy-SDK fallback (Stage-B → *full* distributed monolith, activating dormant SPOFs). A false-green here is the highest-consequence failure in this initiative. **Before the 7-of-7 daily ≥99% composite window starts on either arm:**

1. **Disaggregate the 3 `GetDfFallback` causes** — 503-cadence / 502-capacity / honest-refusal — into distinct EMF signals. They currently collapse into ONE counter; the verdict must read *cause*, not a collapsed total. [observability-engineer]
2. **Bind the canary to CONTENT/cause, not liveness.** Today the deploy-gate (`receiver_bulk_fanout_deploy_gate.py:404`) and the receiver metric (`api/metrics.py:241`/`:346`) are both 2xx-shaped — a 2xx carrying an empty/wrong frame counts as success. Bind to Contract-B column CONTENT or the disaggregated honest EMF — the liveness-masquerade trap is documented at prior handoff §2.PQ-5 (`…-cr3-producer-work-queue-2026-06-03.md:90`, "HTTP-2xx body-blind") and the get_df callsite spike `SPIKE-cr3-getdf-callsites-gid-reconciliation.md:55` ("NOT HTTP-2xx — body-blind = the liveness-masquerade trap"). [chaos-engineer]
3. **Resolve section-arm content coverage** per PQ-5 (guard or seed) AND the prior handoff's content-contract decision before the Section half clears. **Citation correction**: the prior handoff (`HANDOFF-arch-autom8-to-sre-autom8y-asana-cr3-producer-work-queue-2026-06-03.md`) has **no §6** — the `office_phone`/`vertical` content-contract is in its §4 read-first spike `SPIKE-cr3-getdf-callsites-gid-reconciliation.md:35`: *"PROJECT frames only: `office_phone` + `vertical` — the load-bearing MultiIndex-join contract … SECTION frames are EXEMPT (`assert_column_contract=False`, SIG-3 `getdf_signals.py:233-241`)."* Because the Section arm is **column-contract-exempt**, its half of the composite cannot be cleared on `office_phone`/`vertical` presence — it MUST clear on the disaggregated honest-EMF/cause signal (criterion #2) + the PQ-5 `section_gid` guard-or-seed decision instead. [PQ-5 decision (`.ledge/decisions/PQ-5-section-guard-choice-2026-06-03.md`) is the prerequisite gate.]

---

## §5. OPEN QUESTIONS — back to the monolith

- **OQ-1 (PQ-1 width) [BLOCKS PQ-1 re-gate]** — what is the **real concurrent fan-out width** in production? The ~104 is our test-probe fixture (`probe_concurrency_semaphore.py:42`); live `CONSUMER_WARM_SET_GIDS`=34 (`project_registry.py:271-275`). And is `max_workers=10` actually set in monolith source (currently UV-P — unverified in monolith code)? The re-gate width and the headroom sizing both depend on this answer. **Until returned (handoff_back item D), PQ-1 acceptance #4 is BLOCKED and the chaos-engineer re-gate measurement MUST NOT start.**
- **OQ-2 (freshness contract) [BLOCKS SERVE-STALE-ADR]** — what is the **actual freshness tolerance** the consumer needs per entity? This is the linchpin that calibrates `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` (SERVE-STALE-ADR) AND bounds the over-ceiling build pressure (PQ-1). The 50-min LKG default is our internal policy, not your contract — tell us the real need. **Until returned (handoff_back item E), SERVE-STALE-ADR is BLOCKED and MUST NOT be ratified/deployed with an uncalibrated bound (§6 #4).**

---

## §6. ACCEPTANCE CRITERIA (handoff-level) + handoff_back

**This handoff is accepted-and-discharged when:**
1. PQ-1 re-gate lands a post-bulk-warmer measurement: ≥99% per Source on BOTH arms, CPU_STARVATION=0, singleflight proven, ≥2 streams, rite-disjoint SLI — recorded as a verdict in `.ledge/decisions/`.
2. PQ-3 credential disposition is recorded (converge + decommission + IaC + rotation/drift), confirmed by a live re-mint.
3. PQ-2 cadence decision is recorded (bulk verified live; #97/#338 hold/deploy decision made post-SERVE-STALE-ADR).
4. SERVE-STALE-ADR is ratified with `meta.stale_served` + the calibrated `FRESHNESS_CONTRACT_MAX_AGE_SECONDS`. **BLOCKED-ON-OQ-2**: this criterion cannot be met until the monolith returns the OQ-2 freshness contract; the ADR MUST NOT be ratified/deployed with an uncalibrated bound.
5. S7-GATE-FIDELITY disaggregation + canary content-binding land BEFORE any S7 clock starts.

**handoff_back to the monolith (`/Users/tomtenuta/Code/autom8`)** — the return contract:
- **(A)** Receiver bulk verdict: **PASS** → Sprints 2-3 + 7d S7 soak + Stage-B; **FAIL** → iterate, no Stage-B. *(Verdict is PENDING the post-warmer re-gate; do not read today's green warmer deploy as a pass.)*
- **(B)** PQ-3 credential disposition (false-alarm; converge on Secret 1, decommission Secret 2).
- **(C)** PQ-2 cadence decision (30-min bulk resolves it; DAILY was the dark pre-state).
- **(D) [REQUIRED INPUT — blocks PQ-1]** OQ-1 answer: the **real concurrent fan-out width** in production + confirmation of whether `max_workers=10` is actually set in monolith source. Until this is returned, PQ-1 acceptance #4 is BLOCKED and the chaos-engineer re-gate MUST NOT start (see PQ-1 acceptance).
- **(E) [REQUIRED INPUT — blocks SERVE-STALE-ADR]** OQ-2 answer: the **actual freshness tolerance per entity** the consumer needs. Until this is returned, SERVE-STALE-ADR is BLOCKED — the `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` bound cannot be calibrated and the ADR MUST NOT be ratified/deployed (see SERVE-STALE-ADR acceptance and §6 #4).

---

## §7. Evidence ceilings & disciplines (held throughout)

- **Self-referential MODERATE ceiling**: the receiver rite authored these fixes; no PASS/compliance conclusion here is graded above MODERATE until a **rite-disjoint live-under-bulk** measurement (the chaos-engineer re-gate) corroborates it. The re-gate IS the STRONG-lift event.
- **SVR receipts**: every platform claim carries a `file:line` / aws-resource receipt from the grounding doc, or is marked **UV-P** (e.g. monolith `max_workers=10` is UV-P — unverified in monolith source).
- **Default-to-REFUTED**: DAILY-cadence, per-section-fan-out, and credential-value-mismatch were all REFUTED on inspection; the ~104 width was downgraded to a test-probe fixture.
- **Secret-value redaction**: client_id shown as `sa_1a95…`; no raw `client_secret`/token printed anywhere.
- **Meet-the-real-need**: the freshness bound is calibrated to an elicited contract (OQ-2), never relaxed arbitrarily.
- **Telos-integrity**: done = verified-realized (post-warmer re-gate) + paradigm-right (serve-stale ADR-ratified, smells fixed or tracked).

*Prepared as a REVERSE ingest of the monolith CR-3 producer work-queue, autom8y-asana SRE rite, 2026-06-03. Grounding: `.sos/wip/cr3-verified-findings-2026-06-03.md` (6 verified findings, wf_91d1efdc). Conclusions MODERATE until rite-disjoint live-under-bulk corroboration.*
