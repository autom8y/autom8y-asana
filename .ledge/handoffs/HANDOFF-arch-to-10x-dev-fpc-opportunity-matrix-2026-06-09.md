---
type: handoff
handoff_type: implementation   # arch (opportunity-matrix mapped) → 10x-dev/framing (FPC design + build)
station: rite-switch seam (arch → 10x-dev)
source_rite: arch
target_rite: 10x-dev (framing)
date: 2026-06-09
initiative: field-provenance-&-population-contract (FPC) — generalization of dataframe-resolution-coherence
extends: .know/telos/dataframe-resolution-coherence.md
evidence_grade: STRONG-on-map (first-party live git/S3/DuckDB receipts; arch-adversary PASS post-CH-01-remediation) ; FPC design = NOT STARTED
status: proposed
discipline: >
  arch produced ANALYSIS ONLY — no consumer rebound, no fix landed, no schema edited. Every matrix claim
  carries a live receipt from origin/main 50ebfe33 (benign #113 telemetry bump; dataframes corpus unchanged
  vs e686ba06). The cross-entity coherence invariant fires RED=571 against the live corpus (G-THEATER seal).
  Production levers (merge, re-warm, live Asana probe) stay the operator's.
---

# FPC Topological Opportunity-Matrix — arch → 10x-dev/framing HANDOFF

## Rung statement (G-RUNG — not rounded up)

| Element | Rung | Receipt |
|---|---|---|
| Opportunity matrix | **MAPPED** | `.ledge/reviews/fpc-{topology-inventory,dependency-map,architecture-assessment,architecture-report}-2026-06-09.md` |
| FPC roadmap | **RANKED by leverage** | 5 pillars scored + phased (architecture-report §) |
| Coherence-invariant | **SPEC'd + RED-demonstrated** | DuckDB `offer.mrr==unit.mrr` → gun=571 / coherent=0 (live, re-run 3× across N2/N3/N4 + adversary) |
| FPC design (TDD/ADR) | **NOT STARTED** | arch produces no design; this is the 10x-dev charge |
| unit-MRR cure (cell-0) | **authored, UNMERGED** | worktree `/Users/tomtenuta/Code/a8/repos/seam2-unit-econ` (1355 tests pass; sufficiency = Phase-2 path-canonicalization) |

## The map (what arch found — beyond the unit cell)

- **82 distinct schema cells** (13 BASE × 10 entities + 69 entity-specific); 29 registry descriptors. Modes: **57 Direct / 17 Cascade / 8 Derived / 10 number-typed**.
- **80 of 82 cells carry NO population policy** — only `offer.mrr` + `offer.offer_id` are in `post_build_population_receipt.py:60-61 _VALUE_COLUMNS_BY_ENTITY`. The FM-4 blind spot is **corpus-wide**, not unit-local.
- **TWO coexisting null mechanisms** the FPC must fire on BOTH:
  - **(a) fetch/path-asymmetry** — number cf dropped on the section `list_async` build path while the per-task `get_async` (hierarchy/cascade) path carries it. SDK opt_fields symmetric (`fields.py:69` ∧ `hierarchy_warmer.py:43`) → server-side divergence. 8 number cells have **no GET/cascade backstop** (`unit.{mrr,weekly_ad_spend,discount}`, `offer.cost`, `asset_edit.{offer_id,score,template_id,videos_paid}`).
  - **(b) schema/model type-drift** — drift sweep = **3 cells**: `unit.discount` (Decimal vs EnumField, known) + **2 NEW**: `offer.cost` (Utf8 vs NumberField, `schemas/offer.py:70-73` vs `models/business/offer.py:136`), `asset_edit.score` (Float64 vs Decimal). PLUS `offer_id` **Utf8↔Int64 cross-frame** (`offer` vs `asset_edit`, same `cf:Offer ID`).
- **Blast radius / leverage:** `business.office_phone` = ~26-frame keystone (by-design cohesion, NOT a defect); `unit.mrr` = the economic headline (single Source-cell fix → offer.mrr + offer_holder + monolith consumers all heal). Cascade graph is **acyclic**.
- **FM faces:** FM-2 CLOSED (SEAM-1); **FM-1/3/4 OPEN corpus-wide.** Boundary: entity↔canonical-project + holder/leaf = STRONG (5/5); the **schema↔model** and **value↔fetch-path** boundaries LEAK — the structural argument FOR a single FieldContract source-of-truth.

## Ranked leverage (impact ÷ effort)

1. **Drift eradication — 4.0 QUICK WIN** — reconcile D1/D2/D3 + a **generated schema/model parity test** as the structural seal. *Blocked on UK-2: PRD-0024 owner sets the canonical direction for discount/cost.*
2. **offer_id dtype normalization — 3.0 QUICK WIN (conditional UK-3)** — Utf8↔Int64; becomes blocking-HIGH if a cross-frame join ships.
3. **Population-floor extension (2.5) + path-dependent number recovery (2.5) — STRATEGIC tie** — extend `_VALUE_COLUMNS_BY_ENTITY` to the unguarded number cells (Phase 1); add the null-targeted GET backstop / path-canonicalization (Phase 2, where the 571-gun + cell-0 are cured).

## Phased roadmap (the 5 FPC pillars sequenced)

- **Phase 1 (CR-3-safe, no fetch changes, ~3-5d):** drift reconcile (pillar: *declarative FieldContract* seed) + generated **schema/model parity test** (pillar: *generated verification matrix*, partial) + population-floor extension (pillar: *observatory*, partial) + offer_id normalize. **Eliminates all type-contract failures + seals drift structurally.** Does NOT cure the 571-gun.
- **Phase 2 (cures the 571-gun):** **path-canonicalization** — one maximal-completeness materialization per Source node (the cell-0 cache-reuse generalized; ZERO new API calls, CR-3-safe). **unit-MRR cell-0 lands here.** Pillar: *path-canonicalization*.
- **Phase 3:** the **cross-entity coherence invariant** as a standing CI guard (offer.mrr==unit.mrr per waterfall field) + the full **generated verification matrix** (resolution + coherence + parity, per cell) + the **population/coherence observatory** (per-field SLIs to AMP, policy-aware alarms). Pillars: *coherence invariant* + *observatory*.
- **North-star:** the **dataflow type system for the data plane** — provenance types (Source/Cascade/Aggregate) × population types (Total/ActiveSubset/LegitimatelySparse); schema dtype + resolver fallback + floor set + opt_fields + tests all **DERIVED** from one `FieldContract` per cell. Eliminates the schema/model + value/fetch drift classes *by construction*.

## arch-adversary verdict (G-CRITIC)

**PASS-WITH-CONDITIONS → resolved to PASS** after Potnia remediation of the sole blocking flag:
- **TL-A PASS** — canary RED=571 independently reproduced; GREEN on synthetic coherent pair. G-THEATER real.
- **TL-B CH-01 (was BLOCKING) — REMEDIATED** — the report's negative recovery-grep was mis-scoped (broad pattern hit 6 circuit-breaker `recovery_timeout` lines in `storage.py`). The **correctly-scoped** grep is genuinely EMPTY; `cf_utils.py:49`/`default.py:255` number-branches `return number_value` bare on origin/main → **keystone HOLDS** (no number-cell recovery; cell-0 cure unmerged). Both false receipts corrected in `fpc-architecture-assessment-2026-06-09.md:50,191`.
- **TL-C PASS** — no round-up; G-PROPAGATE (FPC = sole propagation point, no orphans), G-DENOM (per-field ActiveSubset/Total/Sparse) honored; DEFERs correctly held.
- **FLAG-2 (carried into the build):** Phase-2 must register a **structured falsifiable prediction** — post-path-canonicalization deploy, re-run the canary: `coherent: 0 → ≥100` (else the path-canonicalization failed); `falsification_condition` = canary still `coherent=0` post-deploy; expiry ≤180d.

## DEFER / watch-registered (do NOT scope-creep into the FPC design)

- **DEFER-UNIT-MRR-CELL0-LAND** — cure worktree authored/unmerged; lands in Phase 2 (path-canonicalization).
- **DEFER-LIVE-ASANA-PROBE** — qa-A's 6-call list-vs-get diff (`ASANA_PAT`); the A-vs-B discriminator; operator lever. The FPC *dissolves* A-vs-B (canonicalize the path; observe the residual) — but the probe still cheaply confirms.
- **UK-2 (BLOCKS Phase-1 drift direction)** — PRD-0024 owner: is `discount`/`cost` canonically enum-string or numeric? Resolve before drift reconcile locks a direction.
- **UK-3** — is a DataFrame-level `offer_id` join planned? If yes, the Utf8↔Int64 normalization is blocking-HIGH.
- **DEFER-MONOLITH-CONSUMER-EDGES (EM1/EM2)** — cross-repo (autom8); SEAM-2 rebind; `autom8/framing`.
- **DEFER-06-11-SOAK-TAIL · DEFER-AMBER-OBS** — unchanged (sre/IC/operator).
- **Throughline N≥2** — SEAM-1 (entity-identity) + FPC (field-provenance) = the second instance of "data-plane contracts implicit." Promote the throughline at the FPC design gate (was N=1, MODERATE-ceilinged).

## Routing

- **Next `/frame` → 10x-dev/framing** for the FPC: architect TDD + ADR (the 5 pillars + the dataflow-type-system reframe) → `/spike` path-canonicalization on a 2nd Source field for N≥2 evidence → **eunomia rite-disjoint design critique** (STRONG requires it; arch-adversary self-assessment caps at MODERATE) → phased `/sprint` (Phase 1 quick-wins first, gated on UK-2).
- Production-mutating levers (merge, prod re-warm, live Asana probe, schema-direction decision via PRD-0024) stay the operator's.

*arch rite, 2026-06-09. Opportunity matrix MAPPED + roadmap RANKED; FPC NOT designed/built; unit-MRR cell-0 unmerged (Phase-2). Every claim carries a live receipt; the coherence invariant fires RED=571 (G-THEATER); arch-adversary PASS post-CH-01-remediation. The stale local checkout was never trusted. STOP — the build is the next rite's.*
