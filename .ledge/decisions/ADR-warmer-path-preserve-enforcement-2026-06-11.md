---
type: decision
status: proposed
name: warmer-path-preserve-enforcement
date: 2026-06-11
initiative: cure-recovery-path-hardening (warmer-path follow-up to #127)
evidence_grade: "[STRUCTURAL | MODERATE]"
supersedes: none
extends: ".ledge/decisions/ADR-cure-recovery-path-hardening-2026-06-11.md (#127)"
tdd: ".ledge/specs/TDD-warmer-path-preserve-enforcement-2026-06-11.md"
substrate_of_record: 7973c10a
---

# ADR: Converge the two finalize writers onto ONE gated write primitive (warmer-path PRESERVE enforcement)

## Status

Proposed. Design-only (TDD + ADR; no src/tests; no commits). Extends #127. Implementation
gated on a base that CONTAINS #127 (a `main`/`7973c10a` descendant), NOT the current
`cr3/gate2` branch.

## Context

#127 (`ADR-cure-recovery-path-hardening`, deployed `:509`/`7973c10`) added a pure
fail-closed write decision (`fail_closed_write.decide_write`) and wired it into the
progressive builder's Step-6 finalize. That gate is correct: on a wholesale durable-read
outage it returns `PRESERVE_PRIOR_GOOD` and the builder skips its own write.

The 2026-06-11 game-day on the deployed `:509` substrate revoked the
`S3DurableTaskCacheRead` grant and forced a warm. The cure **decided** PRESERVE and
**logged** `fail_closed_write_preserve_prior_good` — yet the unit frame was persisted
**0/3021** with `index_written:false`. The decision was made but NOT enforced at the
operative write site.

Re-derivation against `7973c10a` (code-is-truth, file:line in the TDD) found the structural
cause: **there are two distinct finalize writers for a `dataframe.parquet`, and #127 gated
only one.**

- **Writer A (gated):** the builder's `_finalize_artifacts_write_async` — honors PRESERVE,
  skips its own write, but RETURNS the degraded frame and **discards the `WriteDecision`**
  (`BuildResult` has no decision field).
- **Writer B (ungated):** the warmer (`warmer.py:418 put_async`) takes the builder's
  returned degraded frame and re-writes it via `tiers/progressive.put_async` →
  `section_persistence.write_final_artifacts_async` (`index_data=None` → the
  `index_written:false` tell) → `save_dataframe`, with ZERO `WriteDecision` reference.

Two further ungated victims of the SAME pattern exist: admin manual rebuild
(`admin.py:330`) and the `@dataframe_cache` decorator (`decorator.py:222`). The receiver
preload paths (`legacy.py:283`, `progressive.py:584`) are also ungated `save_dataframe`
callers, but they are NOT on the cure-recovery rebuild path (incremental delta / cascade
self-heal of an already-good frame) — a different, lower-risk class.

This is the textbook instance of `THROUGHLINE-integration-boundary-fidelity` §1: the #127
test stubbed one finalize path; the operative warmer writer was never exercised. The
throughline's directive — "cover BOTH finalize paths, OR assert they converge on one
gated write" — frames this decision.

## Decision

**Converge every final-frame write onto ONE gated primitive
(`SectionPersistence.write_final_artifacts_async`), and stop discarding the
`WriteDecision`.** Specifically:

1. **Carry the decision** (the *carry* half of the propagate option): add
   `write_decision` (+ `population_degraded`/`population_min_rate`) to `BuildResult`;
   `build_progressive_async` populates it from the `_FinalizeResult.decision` it already
   computes; `universal_strategy._build_entity_dataframe` returns the decision context to
   the warmer instead of dropping it.

2. **Gate the one primitive** (the convergence): `write_final_artifacts_async` accepts the
   `write_decision` + a `prior_good_loader`. On `PRESERVE_PRIOR_GOOD` it SKIPS
   `save_dataframe` (and freshness/manifest stamping); on `WRITE_COALESCED` it null-cell
   coalesces against prior-good before writing. The builder (Writer A), warmer (W3), admin
   (W6), and decorator (W7) all route through this primitive. `section_persistence:790
   save_dataframe` is reached ONLY through this gate.

3. **Backstop guard (impossible-by-construction):** the primitive REFUSES to save a
   below-floor frame (`population_degraded is True`) that arrives with NO recorded
   `write_decision`, logging `ungated_below_floor_write_refused`. Any future orphan writer
   — and the receiver preload paths W4/W5 — become loud, last-good-preserving refusals
   rather than silent 0/N degrades.

The #127 builder Step-6 PRESERVE early-return is UNCHANGED — the convergence gate is a
SECOND line of defense at the choke point, idempotent with the builder's existing gate.

## Alternatives Considered

### Option A: Propagate the decision to the warmer caller only
- Pros: minimal blast; localized to the warmer and three return shapes; no primitive change.
- Cons: leaves TWO writers — the gate moves one node (to the warmer caller) but a future
  sibling caller is silently ungated again; admin (W6) and decorator (W7) each need the
  same patch independently. This is the #127 shape moved sideways, not a structural fix.
  Violates G-PROPAGATE (one gated primitive, no per-path orphan).

### Option B: Converge onto ONE gated write primitive (CHOSEN, core)
- Pros: no future sibling writer can be silently ungated — the gate sits at the physical
  choke point every parquet write must pass; composes with #127 idempotently; G-PROPAGATE
  satisfied; W4/W5 inherit the guard for free.
- Cons: the primitive lacks the `recovery_receipt` (cannot fully re-decide alone) → must
  thread the decision in (combine with A's carry half); larger surface (5 call-sites).

### Option C: Impossible-by-construction guard (CHOSEN, companion)
- Pros: turns an ungated degraded write into a LOUD failure; catches W4/W5 and any future
  writer cheaply.
- Cons: alone it only fail-LOUDs (would produce an error/503 instead of serving last-good)
  — needs B to also DO the right thing (PRESERVE).

### Option D: Push the gate into `save_dataframe` itself (storage primitive)
- Pros: lowest possible choke.
- Cons: wrong altitude — `save_dataframe` is shared with the storage layer and loses the
  clean entity/receipt context available one layer up at
  `write_final_artifacts_async`; risks mis-firing on honest-empty and cascade self-heal.

### Option E: Per-entity durable PRESERVE lock file
- Pros: decouples writers entirely.
- Cons: adds durable state + a stale-lock strand failure mode; racy across the single
  uvicorn worker's concurrent warms; over-engineered.

## Rationale

The bug is structural, not local: "the gate guards one of N writers." Options A, D, E each
move or duplicate the gate without making the orphan-writer class *impossible*. Only B puts
the gate at the one place every writer converges (`section_persistence:790` reached solely
through `write_final_artifacts_async`), and only C makes a missing-decision below-floor
write LOUD. Together (B behavior + C backstop, fed by A's carry) they satisfy G-PROPAGATE:
one gated primitive, no per-path orphan, and a future-proofing assertion so the next
sibling writer cannot silently regress. The choice composes with #127 without regressing
the builder path because the builder's PRESERVE early-return stays and the primitive gate
is idempotent with it.

This will "look obviously right in 18 months": a single choke point that physically cannot
be bypassed, with a loud refusal for anything that tries — versus the current state where a
correct decision is computed and silently thrown away by a parallel writer.

## Consequences

### Positive
- PRESERVE is enforced at EVERY final-frame write site (warmer, admin, decorator, builder),
  not just the builder. The game-day RED becomes GREEN: a wholesale-outage warm serves the
  last-good frame (count(mrr)==prior-good), never 0/N.
- Future orphan writers are impossible-by-construction (guard refuses + logs).
- Per-entity / never-cross-entity isolation preserved (NFR-3): unit PRESERVE cannot touch
  the offer frame and vice-versa.
- The honest ACTIVE-subset floor (G-DENOM) is consumed, never re-derived.
- No new `asyncio.to_thread` (FROZEN-4 untouched).

### Negative
- Larger surface than the minimal propagate (5 call-sites + BuildResult shape change).
- Requires a base containing #127 (rebase-onto-main pre-condition; current branch lacks it).
- Coalesce idempotence must be guaranteed to avoid double-coalesce (R-1) — mitigated by
  null-cell-only coalesce.

### Neutral
- The VG-001 durability boolean gets a defined PRESERVE semantic (return `True`, no
  freshness stamp) — a new-but-honest contract documented in the TDD §Reliability.
- The `self-heal-game-day-proven` rung is NOT earned by this design; it is earned by the
  releaser's re-deploy + re-game-day on the re-built substrate (G-RUNG: this artifact's
  ceiling is authored-and-tested-in-process).

## Frozen-grammar / scope fence

- Does NOT modify `fail_closed_write.decide_write` (the #127 pure helper) — only stops
  discarding its output and adds a second enforcement point.
- Does NOT regress the builder Step-6 PRESERVE early-return.
- Does NOT touch FROZEN / FROZEN-4 (no new offloaded CPU work).
- Receiver paths W4/W5 are guard-coverage-only (no decision-threading), not re-scoped into
  the threading work.
