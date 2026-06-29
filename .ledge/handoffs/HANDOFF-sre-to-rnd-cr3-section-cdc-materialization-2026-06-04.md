---
type: handoff           # .ledge shelf-discoverability field
lifecycle_status: proposed   # .ledge shelf lifecycle (HANDOFF workflow status carried separately in `status:` below)
artifact_id: HANDOFF-sre-to-rnd-cr3-section-cdc-materialization-2026-06-04
schema_version: "1.0"
source_rite: sre
target_rite: rnd
handoff_type: strategic_evaluation
priority: high
blocking: false
initiative: cr3-fleet-data-plane-foundation-cutover
created_at: 2026-06-04T00:00:00Z
status: pending          # HANDOFF v1.0 lifecycle (pending|in_progress|completed|rejected) — distinct from .ledge lifecycle_status above
evidence_grade: strong   # the WALL is empirical gameday/live-attempt data (STRONG); the proposed fix is R&D framing (the rnd track grades feasibility)
source_artifacts:
  - .ledge/decisions/ADR-section-10min-x-502-headroom-2026-06-03.md
  - .ledge/decisions/CR3-FINAL-REGATE-PLAN-2026-06-03.md
  - .ledge/decisions/CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md
  - /Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2-2026-06-03.md   # CQ-5 routing PRE-ACCEPTED
  - .ledge/handoffs/HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md   # FLEET-DATA-PLANE-RND prior routing (item id at :168)
provenance:
  - { source: ".ledge/decisions/ADR-section-10min-x-502-headroom-2026-06-03.md", type: adr, grade: moderate }
  - { source: "src/autom8_asana/config.py:155-161", type: code, grade: strong }
  - { source: ".claude/agent-memory/platform-engineer/warm-cadence-vs-lkg-ceiling-tension.md:10-14", type: artifact, grade: strong }
  - { source: "/Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2-2026-06-03.md:77-79", type: artifact, grade: strong }
tradeoff_points:
  - attribute: "data freshness vs upstream-API budget"
    tradeoff: "Poll-and-rebuild trades simplicity for an API-call cost that scales with (entities × cadence); at the section entity's ≤10-min cadence × 34 GIDs this exceeds the single-resolver-token Asana rate budget by ~8×."
    rationale: "CDC/incremental fetches only CHANGED sections, decoupling API cost from cadence — the only path to ≤10-min section freshness within the rate limit."
  - attribute: "correctness vs delivery deadline"
    tradeoff: "CR-3 ships an INTERIM (serve-stale-section + warm lane + headroom) to hold the deadline; the CDC foundation is deliberately OUT of the critical path (no deadline, correctness-first)."
    rationale: "Consumer (autom8) PRE-ACCEPTED this split at CQ-5 — interim now, foundation evolution on the rnd track."
items:
  - id: RND-CDC-001
    summary: "Investigate incremental / Asana-CDC section materialization (fetch only CHANGED sections via events/webhooks/sync-token or delta polling) to make ≤10-min section freshness feasible within the Asana API rate limit. Poll-and-rebuild has hit its empirical ceiling on the tightest-freshness entity."
    priority: high
    evaluation_criteria:
      - "FEASIBILITY: does an Asana CDC/delta mechanism (events API, webhooks, sync-token, or last-modified delta polling) exist and cover section-change detection at 34-GID scale on a single resolver token, and by what factor does it cut API calls vs full re-warm?"
      - "ACHIEVABLE CADENCE: what section freshness CAN the Asana API sustain at 34-GID scale on a single resolver token? (The forcing question — the ≤10-min target is a consumer contract, not an established-feasible cadence.)"
      - "ARCHITECTURE FIT: does a CQRS read/materialize split + generic ingestion layer subsume this receiver as fleet instance #1 (per FLEET-DATA-PLANE-RND), or is section-CDC a point fix?"
      - "SMELL-GATED: each sub-investigation must gate on a genuine architectural-smell/decision point, not speculative lift-and-shift (consumer constraint, CQ-5 + FLEET-DATA-PLANE-RND acceptance_criteria)."
      - "INTERIM BOUNDARY: confirm CR-3's interim (serve-stale + warm lane + headroom) is NOT regressed or blocked by the R&D track; CDC is foundation evolution, not a CR-3 dependency."
    dependencies: []
    notes: "Procession: inquisition (entry rite rnd, cross-repo R&D campaign) → thermia (cache-arch) for the materialization-cadence design. OUT of the CR-3 critical path. The section lane is ALREADY PAUSED in prod (reserved_concurrency=0 + EventBridge section-schedule DISABLED) — this handoff carries the NEW empirical wall data that justified the pause."
---

# HANDOFF — sre → rnd: section→CDC materialization R&D framing (CR-3)

> **Strategic-evaluation handoff.** R&D → strategy go/no-go framing for the section-freshness
> frontier that CR-3's poll-and-rebuild paradigm cannot cross. This is NOT a build request and
> NOT in the CR-3 critical path. It carries the **empirical forcing data** (the WALL) and frames
> the **real fix to investigate** (CDC/incremental materialization). The rnd track grades feasibility.

## 1. THE WALL — the empirical forcing data

**A ≤10-min full-section-warm of the 34-GID section warm-set is INFEASIBLE against the Asana API
rate limit.** This is not a compute problem and not solvable by raising concurrency — the ceiling
is upstream.

Forcing data (the section-lane live-attempt that triggered the PAUSE, STEP i):

- **5 of 34 GIDs reached in ~12 min** against **896 Asana `rate_limit_429` responses** → full
  34-GID coverage projected at **~80 min**. That is **~8× over the 576s (≤10-min) section
  freshness contract.**
- **Root cause = upstream Asana API rate limit, NOT compute.** Raising `reserved_concurrency`
  WORSENS it — more parallel links generate more concurrent requests against the same
  single-resolver-token rate budget, multiplying 429s.
- The section lane is consequently **PAUSED in prod**: `reserved_concurrency=0` + EventBridge rule
  `autom8-asana-cache-warmer-section-schedule` **DISABLED**. With the lane paused, the LIVE knob
  `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["section"]=576.0` (`config.py:162-164`) now FORCES section
  reads onto the build/502 path (`config.py:155-161`: tightening section to 576s makes section
  frames hard-reject + rebuild far sooner → more build pressure on the `POST /v1/query/section/rows`
  502 hotspot).

Corroborating per-GID timing (independent of the live attempt): the heaviest single GID
(BusinessUnits, 17 sections, per-section fetch 38s–326s, rebuild ~5.5 min) ALONE blows a 10-min
serial budget; a 34-key serial section sweep is ≫ 10 min before any rate-limit even applies
(`warm-cadence-vs-lkg-ceiling-tension.md:10-14`, CRG-3 gameday 2026-06-03 06:59Z). [STRONG —
code + aws + gameday + live-attempt-anchored]

**Bottom line: poll-and-rebuild has hit its hard ceiling on the tightest-freshness entity
(section).** Full re-warm cost scales with (entities × cadence); at section's ≤10-min cadence ×
34 GIDs it exceeds the single-resolver-token Asana rate budget by ~8×. No amount of receiver-side
compute (CPU/mem, concurrency, worker count) moves an upstream rate ceiling.

Cite: `ADR-section-10min-x-502-headroom-2026-06-03.md` (§B.3 documents the ≤10-min-over-34-keys
infeasibility against `reserved_concurrency=1`; this handoff carries the NEW empirical 429/coverage
wall data from the subsequent live attempt). `FLEET-DATA-PLANE-RND` (producer handoff item at
`HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md:168`) ALREADY routed the
fleet-data-plane R&D direction; **this handoff carries the empirical wall that converts that tracked
direction into a forced investigation.**

## 2. THE REAL FIX to investigate (R&D framing — feasibility is rnd's to grade)

**Incremental / Asana-CDC section materialization.** Fetch only the sections that CHANGED rather
than full re-warming all 34 GIDs every cadence. Candidate mechanisms (to be assessed for existence,
coverage, and rate-budget impact by the rnd track):

- **Asana events API / webhooks / sync-token / delta (last-modified) polling** — detect changed
  sections and re-materialize only those, slashing API calls by orders of magnitude. This decouples
  API cost from cadence and is the only identified path that makes ≤10-min section freshness
  feasible within the single-resolver-token rate limit.
- **CQRS read/materialize split** — separate the read model (served frames) from the materialization
  pipeline (change-driven, not poll-driven), so freshness is event-bounded rather than sweep-bounded.
- **The achievable-cadence question (the forcing question):** what section freshness CAN the Asana
  API sustain at 34-GID scale on a single resolver token? The ≤10-min target is a consumer contract
  (OQ-2, `caching.py:39 SECTION_DF_REFRESH_HOURS=0.16`), NOT an established-feasible cadence. The
  rnd track should establish the empirical sustainable-cadence frontier and, if ≤10-min is
  infeasible even under CDC on one token, surface that to the consumer as a contract-renegotiation
  input (e.g. multi-token resolver, or a relaxed section contract).

This subsumes into the broader **fleet materialized-data-plane foundation** (this receiver = instance
#1) already tracked as `FLEET-DATA-PLANE-RND` — CQRS read/materialize split, Asana CDC/incremental
ingestion, generic ingestion layer, reuse of the analytics semantic layer
(QueryableMetric/CompositeMetric).

## 3. Procession + routing (consumer PRE-ACCEPTED)

- **Entry rite: rnd. Procession: inquisition** (cross-repo R&D campaign) **→ thermia (cache-arch)**
  for the materialization-cadence design.
- **The consumer (autom8) PRE-ACCEPTED this routing** at CQ-5 (`consumer return-2`
  `HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2-2026-06-03.md:77-79`): the SECTION-10min (576s)
  × 502 frontier is "OUT of the CR-3 critical path, routed to the FLEET-DATA-PLANE R&D track (rnd
  rite / inquisition procession + thermia cache-arch) for event-driven / CDC materialization.
  Correctness-first; each item gates on a genuine smell-point, not speculative lift-and-shift."

## 4. CR-3 boundary — what ships now vs what this evolves

- **CR-3 ships the INTERIM (correctness-first, holds the deadline):** serve-stale-section +
  the section warm lane (now paused) + build-capacity headroom. This is the interim disposition
  for the section frontier; it does not meet the ≤10-min contract at 34-GID scale but holds
  serve-availability via serve-stale within the 50-min internal ceiling.
- **This R&D track is the foundation evolution (no deadline):** CDC/incremental materialization
  is what MAKES the ≤10-min section contract feasible. It is OUT of the CR-3 critical path and
  must NOT block, gate, or regress the CR-3 land.
- **No reversibility concern:** this handoff is a strategic-evaluation framing artifact. It
  authors no code, touches no config, re-enables no paused lane. The section lane STAYS paused
  (`reserved_concurrency=0`, EventBridge `autom8-asana-cache-warmer-section-schedule` DISABLED).

## 5. Acceptance (for the rnd track)

Accept this handoff into the inquisition procession; produce a feasibility/go-no-go evaluation
against the `RND-CDC-001` evaluation_criteria above. The primary deliverable is the answer to the
achievable-cadence question and a CDC-mechanism feasibility verdict — NOT a production build (that
would be a downstream implementation handoff if/when the rnd track returns a GO).
