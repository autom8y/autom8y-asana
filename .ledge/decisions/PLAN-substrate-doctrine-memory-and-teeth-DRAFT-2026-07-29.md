---
type: decision
artifact_subtype: plan
artifact_id: PLAN-substrate-doctrine-memory-and-teeth
title: "Companion plan — scar/ADR-memory update + sparse CI-teeth register for the substrate constitution"
created_at: "2026-07-29"
authored_by: structure-evaluator (arch, co-seated 10x-dev) — S9, FOLDING remediation-planner scope per pythia FORK-W4
status: draft
landing_status: "LANDING-HELD-TO-S8-GREEN (with the constitution it serves)"
initiative: substrate-v2-epoch
sprint: S9
rite: arch (authoring) / 10x-dev (landing)
evidence_grade: MODERATE
parent_doctrine: CONSTITUTION-substrate-invariants-DRAFT-2026-07-29
related_artifacts:
  - CONSTITUTION-substrate-invariants-DRAFT-2026-07-29
  - TDD-substrate-v2
  - DP-3-consumer-contracts
  - CHARTER-substrate-v2-epoch-2026-07-27
tags: [substrate-v2, remediation-plan, scar-tissue, ci-teeth, memory-update, DRAFT]
---

# Companion plan — memory update + sparse CI teeth

> **DRAFT — LANDING-HELD-TO-S8-GREEN.** This plan operationalizes the constitution's
> §2 teeth and its memory footprint. Per pythia FORK-W4, this S9 charge folds the
> remediation-planner scope: the doctrine (parent) is the *law*; this companion is the
> *plan to make the law bite in memory and CI*. Both land together, post-S8-green.
> No fix is *executed* in wave-2 — this is the authored plan the landing PR consumes.

## §1 — Scar / ADR memory update plan

The rule (charter P6 + RC-D): **scars stay live-guarding v1 until v1 is deleted (S11).**
The v2 constructions do not *retire* these scars at authoring time — they make the scar's
failure class *unconstructable in v2* while v1 still carries the guard. So each memory
transition below is **staged now, executed at cutover/extinction**, not at this draft's
landing. Each entry names the scar, the RC law that subsumes its class, and the transition.

| Scar / ADR (memory) | Class | Subsumed by | Memory transition (executed at cutover/S11) |
|---------------------|-------|-------------|---------------------------------------------|
| **SCAR-SEAM1-PROBER-001** (the wound: entity-blind prober plane-split; 14-day-stale under false-fresh) | plane-split + false-fresh + guard-drift | **RC-A + RC-B + RC-C** | From "defensive pattern: thread `entity_type` through every S3 writer; call-site guard covers persistence wrappers" → "**unconstructable in v2**: no plane-blind identity constructs (RC-C); no probe advances freshness (RC-B); no second copy exists (RC-A)". Keep the v1 test cluster GREEN until S11; then delete with v1. |
| **SCAR-FRESH-001** (freshness-verification-recency silent-corruption; ADR-006, T11-T16) | freshness stamping | **RC-B** | From "freshness stamping must fail loud on null-name / re-seed edges" → "**no re-stampable freshness field exists in v2**; freshness is content-derived (RC-B); the null-watermark false-CLEAN class is unconstructable". v1 T11-T16 stay green until v1 deletion. |
| **SCAR-DFR-001** (dataframe-cache lineage — the double-write cache location) | multi-copy divergence | **RC-A** | From "the double-write cache location" lineage → "**one artifact per `(project, entity)`; the consolidated-vs-per-section duality is subtracted**". Lineage note only; no live v1 guard to flip. |
| **ADR-006** (freshness = verification-recency) | design paradigm | **RC-B** (content-derived) | Mark the paradigm **superseded by RC-B** at cutover — freshness-as-recency is the disease RC-B cures. Governs v1 until cutover; nothing in v2. |
| **ADR-serve-stale-within-bound** (2026-06-03; 200-with-stale-flag) | serving paradigm | **F5-5 / RC-B fail-loud** | **Already SUPERSEDED-EXECUTED 2026-07-29** (DP-3). No further action; recorded here for lineage completeness. |

**New memory to author at landing (not a v1 scar — a *doctrine* memory):**
- One scar-tissue "defensive-doctrine" entry per RC law, phrased as the *unconstructable
  class* (not a code fix): "In substrate-v2, {failure class} is unconstructable because
  {construction}; the one CI tooth where construction cannot reach is {tooth}." This is the
  reusable form the fleet /frame consumes (charter P12).
- **ADR-memory:** cross-link the constitution from the fork-register ADR
  (`ADR-substrate-v2-fork-register`) so the F1–F6 ruling trail resolves to the standing law.

**Sequencing guard (RC-D, self-applied):** this memory plan itself must not become an
immortal bridge. Its transitions are dated to the cutover/S11 events, not left open.

## §2 — Sparse CI-teeth register

Four teeth, transcribed from the frozen TDD (§3/§4/§11). Each passes the **three-check
false-positive gate** before entering the register (anti-pattern: teeth inflation — do not
add a tooth where construction subtracts the hazard, per P3):

1. **Construction-unreachable?** Can the invariant be made unconstructable instead? If yes → no tooth.
2. **Not a blanket suite?** Is this a targeted tooth on a specific unreachable seam, not a repo-wide guard suite? (P11 forbids blanket suites as the doctrine home.)
3. **Subtract-first honored?** Has the hazard class already been subtracted, with the tooth covering only the residue construction cannot reach?

| # | Tooth | RC served | Construction-unreachable gate | Scope / SUNSET |
|---|-------|-----------|-------------------------------|----------------|
| T1 | **mypy-strict** (repo-wide `strict = true`) | RC-C (required discriminator), RC-E (reader has no write method), RC-B (frozen value types) | PASS — Python has no compile step; the type-level "impossible" is only real when CI runs mypy-strict. Already exists; the doctrine claims it as standing law, not new machinery. | repo-wide (pre-existing); no sunset |
| T2 | **Exhaustiveness** — `typing.assert_never` on every `Provable\|Refused` consumer | RC-C (serving) | PASS — the sum type makes a bare value unobtainable in principle, but a consumer can still skip the `Refused` arm; only mypy exhaustiveness catches the unhandled arm. **Net-new** (zero `assert_never` uses today per PE grep). | substrate serve consumers; no sunset |
| T3 | **Import-forbid** — raw reads (`read_current`/`load_dataframe`) private to `{serve, rebuild}`; core imports no infra | RC-A / RC-C (no gate-bypass) + whole-design dependency legality | PASS — Python has no true module-private or dependency-direction enforcement; only an import-layer lint/mypy tooth forbids the import. | substrate package; no sunset |
| T4 | **`SUNSET_AFTER` expiry** — bounded bridges (e.g. the S7 parity harness) fail CI past their sunset date | RC-D | PASS — **the canonical unreachable case**: time passing is not a code property; only a CI check comparing `now()` to the sunset date makes an immortal bridge fail. | test-scoped bridges only; **each carries a dated SUNSET_AFTER; extension → operator-visible ruling (C11)** |

**Deliberately NOT added (subtraction won — recorded so a future pass does not re-add them):**
- No per-call-site plane guard → subtracted by RC-C construction (the wound's own guard drifted; P5/P6 prove call-site guards drift).
- No query-gated staleness alarm → subtracted by RC-F's query-independent evaluator.
- No result-cache-consistency guard above the gate → subtracted by RC-B/C2 (result-caching above the gate is forbidden by construction).
- No blanket "substrate invariants" guard suite → forbidden by P11 as the doctrine home.

## §3 — Cross-rite observations (noted for the operator / remediation-planner, not converted here)

Per structure-evaluator's cross-rite routing: these touch other domains; I record them as
observations, not as fixes or referrals.

- **F5-5 is cross-repo (fleet-coordination).** The mandated SDK reaches into delegated-fleet
  *consumer* repos — landing it as fleet law implies a coordinated client-library rollout
  beyond autom8y-asana. This intersects the R27 identity-ratchet / R29 identity-gate
  (consumer auth surface) — an operator/fleet-coordination item, not a corridor build.
- **RC-F cutover obligation touches sre/observability.** The "≥1 observed end-to-end FIRED
  alarm" (C10) + the SNS-gap precedent are an observability-engineering concern (alarm-action
  wiring); the cross-repo terraform APPLY limb is Door #4 (DP-4a, operator, parent repo).
- **SLA governance (RC-B, C8) is a product-surface decision.** *Who* may change `sla_seconds`
  and how the "provably ≤ SLA-old, not 'current'" delta is surfaced is governance, not code —
  routed to S2/DP-3 and due to the operator no later than the S8 gate.

## §4 — Grade

MODERATE (self-ref ceiling). This plan is authored, adversary-review pending (arch-adversary,
spanning both this companion and the parent doctrine per the folded scope). Execution of any
memory transition or tooth landing is post-S8-green, by principal-engineer.
