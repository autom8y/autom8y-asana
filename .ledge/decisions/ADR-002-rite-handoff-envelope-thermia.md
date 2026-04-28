---
type: decision
artifact_type: ADR
adr_id: ADR-002
initiative_slug: verify-active-mrr-provenance
session_id: session-20260427-154543-c703e121
phase: design
authored_by: principal-architect
authored_on: 2026-04-27
branch: feat/active-mrr-freshness-signal
worktree: .worktrees/active-mrr-freshness/
title: Rite-handoff envelope for thermia cache concerns (10x-dev → thermia, sre fallback)
status: accepted
companion_prd: verify-active-mrr-provenance.prd.md
companion_tdd: handoff-dossier-schema.tdd.md
reconstruction:
  status: RECONSTRUCTED-2026-04-27
  reason: original lost to **/.ledge/* gitignore during predecessor 10x-dev sprint
  reconstructed_by: thermia procession P0 pre-flight (general-purpose dispatch)
  source_evidence:
    - .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md (frontmatter + 8-section body — exemplar)
    - .ledge/handoffs/INDEX.md (exemplar of fleet-level discoverability artifact)
    - .ledge/specs/handoff-dossier-schema.tdd.md (companion TDD)
    - .ledge/specs/verify-active-mrr-provenance.prd.md (PRD §8 rite-handoff scaffold, D8)
    - cross-rite-handoff skill (canonical type contract)
    - external-critique-gate-cross-rite-residency skill (Axiom 1 grounding)
    - conversation memory of architect-phase authoring
---

# ADR-002 — Rite-handoff envelope for thermia cache concerns

## Status

**Accepted** — 2026-04-27. Implemented at T10 commit (handoff dossier
authoring); the surviving artifact at
`.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` is the
exemplar.

## Context

PRD `verify-active-mrr-provenance` §3 places several cache-architecture
concerns out of scope for the 10x-dev rite:

- **D5** — section-coverage telemetry (deferred to thermia per NG5).
- **D7** — env-matrix legacy-cruft + `AUTOM8Y_ENV` cleanup (deferred to
  thermia per NG6).
- **D10** — cache_warmer Lambda schedule + per-section TTL (deferred to
  thermia per NG7).
- **D8** — telos `verified_realized` attestation (deferred to thermia per
  Axiom 1 critic-rite-disjointness; sre fallback iff thermia unregistered).

These concerns require an **attestable handoff envelope** because:

1. **Axiom 1** (`external-critique-gate-cross-rite-residency`): the
   originating rite cannot self-attest the `verified_realized` gate. A
   different rite must discharge.
2. The deferred concerns are **stateful** at handoff time (cache state,
   env-matrix inventory, classifier-vs-parquet diff). Without an
   anchored snapshot, the receiving rite would re-derive state and
   round-trip clarifying questions to the originating rite — wasteful
   and provenance-fragile.
3. The receiving rite (`thermia`) MAY not be registered at the platform
   manifest level at handoff time. A mechanically-verifiable fallback
   predicate is required to prevent indefinite block.

## Decision

The handoff envelope is an **8-section structured dossier** conformant to
the `cross-rite-handoff` type=`implementation` schema defined in
`handoff-dossier-schema.tdd.md`. Specifically:

1. **Artifact path**:
   `.ledge/handoffs/HANDOFF-{originating_rite}-to-{receiving_rite}-{YYYY-MM-DD}.md`.
2. **Frontmatter**: 12 required fields per TDD §1 (type, handoff_type,
   originating_rite, receiving_rite, fallback_rite, originating_session,
   authored_on, authored_by, worktree, branch, prd_anchor,
   attestation_required) plus 9 recommended fields including
   `attestation_chain` and `verification_deadline`.
3. **Body**: 8 mandatory sections per TDD §2 (classifier list, parquet
   list, mtime histogram sidecar, stakeholder affirmation, cache_warmer
   open Q, section-coverage deferral, env-cruft inventory, telos
   handoff with fallback).
4. **Discoverability**: a single-line entry appended to
   `.ledge/handoffs/INDEX.md` at fleet altitude.
5. **Refusal-clause gate**: 11-line checklist per TDD §3 enforcing no
   aspirational tokens, all anchors `file:line`, all open questions
   verifiable predicates.
6. **Fallback predicate**: mechanically verifiable per TDD §5
   (`Read('.claude/agents/{rite}/')` ENOENT OR rite absent from
   `.knossos/KNOSSOS_MANIFEST.yaml` → fallback rite activates).
7. **Attester invocation contract**: per TDD §4 — `## Attester Acceptance`
   appended at engagement; `## Verification Attestation` appended at
   discharge or deadline.

Primary attester for THIS initiative: `thermia.verification-auditor`
(receiving rite has authority to substitute closest pantheon-fit agent —
see Negative consequence §1 below).

Fallback attester: `sre.observability-engineer` OR
`sre.incident-commander`. Per dossier §8.1 latent decision #2,
**observability-engineer** is the recommended fallback for the
SLO-shaped freshness surface (parquet mtime → staleness threshold →
strict-mode promotion); incident-commander is the alternative for
degraded-state response.

## Alternatives considered

### Rejected: Inline handoff section in PRD (artifact-locality violation)

> Embed the deferred-concerns handoff as a `§Handoff` section inside the
> PRD itself, instead of as a separate dossier artifact.

- Violates **artifact-locality**: a PRD is a frame artifact (declares
  intent + acceptance); a handoff is a state-snapshot artifact (records
  evidence at a moment). Conflating them makes the PRD a moving target
  (the dossier accrues acceptance + verification headings post-PRD-merge).
- Breaks frontmatter discipline: the 12-field cross-rite-handoff
  contract cannot live inside a PRD frontmatter without polluting the
  PRD's own contract.
- Loses fleet-level discoverability: a `.ledge/handoffs/INDEX.md` of
  `.ledge/specs/*.prd.md` greps would conflate intent-artifacts with
  state-snapshot-artifacts.

### Rejected: Single attester (no fallback, indefinite block)

> Name only `thermia.verification-auditor` as primary attester; if
> thermia is not registered, the verification simply blocks.

- The thermia rite may not be registered at handoff time — at the time
  of authoring this PRD, thermia's pantheon was a candidate, not a
  declared rite.
- Indefinite block is unacceptable: the `verified_realized` gate has a
  `verification_deadline` (2026-05-27); blocking past it forces a
  reactivation cycle.
- Sre is structurally similar (observability + reliability surface) and
  can discharge an SLO-shaped attestation; making it the codified
  fallback resolves the indefinite-block risk.

### Rejected: Self-attestation by 10x-dev (Axiom 1 violation)

> Allow the originating rite to declare `verified_realized` itself once
> the in-anger-dogfood probes pass.

- **Axiom 1** (rite-disjointness for critique gates): the same rite that
  shipped the work cannot grade its own verification. This is the
  load-bearing reason cross-rite handoff exists.
- 10x-dev's QA-adversary phase (T9) is in-rite QA, not a verification
  attestation — distinct gate.

### Rejected: Free-form prose handoff (no schema)

> Author a free-form markdown note describing what thermia should pick
> up, with no required sections / refusal-clause / INDEX entry.

- No discoverability: future rite agents cannot grep INDEX or rely on
  consistent section headings.
- No discipline: free-form prose admits aspirational tokens
  (`should/will/eventually`) and unanchored claims that load-bear
  decisions downstream.
- Reuse impossible: every future cross-rite handoff would re-invent
  shape; the 8-section schema is fleet-reusable for `{hygiene, sre,
  security, ...}` handoffs.

### Accepted: 8-section structured dossier + INDEX + fallback predicate + 11-line refusal-clause gate

- Artifact-locality preserved (PRD declares intent; dossier records
  state).
- Frontmatter contract enforced (12 required fields).
- Discoverability: `INDEX.md` entries grep-friendly.
- Discipline: refusal-clause + verifiable fallback predicate.
- Reusable: the schema (TDD §1–§7) is fleet-altitude, not initiative-
  specific.

## Consequences

### Positive

- `.ledge/handoffs/INDEX.md` becomes a fleet-level discoverability
  artifact: any agent can `grep "→ thermia"` to find incoming handoffs
  or `grep "status=ATTESTED-PENDING"` to surface in-flight work.
- The 8-section schema is **reusable** for future cross-rite handoffs
  across `{hygiene, sre, security, ...}` rites — the schema lives at
  fleet altitude (TDD §1–§7), the per-initiative dossiers live at
  initiative altitude.
- Fallback predicate eliminates indefinite-block risk: even if thermia
  rite is unregistered at handoff time, sre activates per `§5.1`
  predicate.
- 11-line refusal-clause inherits the
  `external-critique-gate-cross-rite-residency` discipline; cross-rite
  handoffs cannot smuggle aspirational prose past the gate.

### Negative

1. **Sre rite awareness of `cross-rite-handoff` convention is a
   precondition for fallback-path activation** — FLAG. If sre rite
   agents are unaware of the cross-rite-handoff schema (HANDOFF-*
   naming, INDEX.md scanning, `## Fallback Activation Record` heading),
   the fallback path is dormant. **Suggested mitigation**: a
   cross-rite-handoff inheritance note in the sre rite's documentation,
   or a fleet-level discoverability sweep at the next sre-rite
   onboarding event. **Decision holder**: sre rite Potnia at
   activation; not load-bearing for engineer T10 commit.

2. **Pantheon-role disambiguation may be required at acceptance time**.
   The dossier names `thermia.verification-auditor` as primary attester,
   but no agent of that exact name exists in the thermia pantheon (which
   contains: potnia, heat-mapper, systems-thermodynamicist,
   capacity-engineer, thermal-monitor). The receiving rite has authority
   to substitute its closest pantheon-fit agent (per TDD §5.3); for this
   initiative, `thermal-monitor` discharges (charter includes
   "cross-architecture validation"). This is recorded in §Attester
   Acceptance pantheon-role mapping note. **NOT** fallback activation —
   thermia rite IS registered.

3. **Artifact-discipline overhead**: every cross-rite handoff now
   requires authoring the 8-section dossier + INDEX entry + refusal-
   clause checklist. For very small handoffs, this overhead may exceed
   the handoff content. Mitigation: the refusal-clause is fast (11 lines
   to verify), the INDEX entry is one line, the 8 sections are
   structurally short for small handoffs (e.g. an empty §7 inventory is
   perfectly valid — "0 matches" is itself evidence).

### Neutral

- The schema_version: 1 establishes a versioning hook for future
  evolution. Breaking schema changes require an ADR per TDD §6.
- Forward-fork-friendly: thermia may itself produce a downstream
  handoff (e.g. `HANDOFF-thermia-to-hygiene-{date}.md` for D7) using
  the same schema.

## Anchors

- PRD §8 (Rite-Handoff Scaffold)
- PRD §6 D8 (telos primary + fallback)
- PRD US-6 AC-6.1 (8 required dossier sections)
- TDD `handoff-dossier-schema.tdd.md` §1 (frontmatter)
- TDD `handoff-dossier-schema.tdd.md` §2 (8 body sections)
- TDD `handoff-dossier-schema.tdd.md` §3 (11-line refusal-clause)
- TDD `handoff-dossier-schema.tdd.md` §4 (attester invocation contract)
- TDD `handoff-dossier-schema.tdd.md` §5 (fallback predicate)
- TDD `handoff-dossier-schema.tdd.md` §6 (schema versioning)
- `cross-rite-handoff` skill (canonical type contract)
- `external-critique-gate-cross-rite-residency` skill (Axiom 1 + refusal-
  clause heritage)
- `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` (exemplar)
- `.ledge/handoffs/INDEX.md` (exemplar)

---

*Authored by principal-architect, session-20260427-154543-c703e121,
2026-04-27. Reconstructed by thermia procession P0 pre-flight,
session-20260427-185944-cde32d7b, on 2026-04-27.*
