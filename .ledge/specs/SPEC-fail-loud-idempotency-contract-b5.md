---
type: spec
slug: fail-loud-idempotency-contract-b5
status: PROPOSED
date: 2026-07-17
initiative: asana-mcp-v1
sprint: sprint-3 (write-surface groundwork)
rite: rnd
charter: .ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md
slate: .ledge/spikes/SPIKE-mcp-substrate-concepts-2026-07-17.md (B5 :163-174)
posture: SPEC ONLY — interface + telemetry requirements. Explicitly NOT an implementation.
evidence: MODERATE (self-referential authorship; inherits the slate ceiling)
---

# SPEC — Fail-Loud Idempotency Contract (B5)

> The standing gate that any **future NON-idempotent** MCP write verb MUST satisfy
> before it may ship. This is a **contract** (interface + degradation telemetry), not
> an implementation — "deliberately *not* one shared implementation; the four repos'
> needs genuinely differ" (slate B5 :172-174).

## 1. Purpose and Non-Goal

**Purpose.** v1 writes are restricted to naturally-idempotent verbs (W-3), so no
idempotency-store work blocks v1. The moment a verb that is *not* naturally idempotent
is proposed (e.g., a create-without-natural-key, an append, a counter increment), it
must bind to a **fail-loud** idempotency store — one that **refuses loudly** rather than
silently degrading. This spec defines the contract that verb must meet.

**Non-goal (binding).** This document specifies NO implementation. It does not choose a
backend, does not add code to any store, and does not remediate SCAR-IDEM-001. Per W-3,
the v1 chain is defanged by **verb selection**, not by store-fixing (frame §4.3; risk
R4). Shipping any code here would be scope creep against the granted §5.4 groundwork
(DRAFT/spec only).

## 2. Scope

| In scope | Out of scope |
|---|---|
| FUTURE non-idempotent write verbs (none exist in v1) | The v1 composite chain add_tag -> push -> mark_complete (idempotent by W-3/W-4) |
| The interface a non-idempotent verb's idempotency store MUST expose | Choosing/altering a concrete backend (DynamoDB, memory, ...) |
| The fail-loud + fail-closed posture and its telemetry | Fixing SCAR-IDEM-001's existing silent-degrade paths (verb selection defangs v1) |

The v1 write tool relies on this spec as the **standing bar** it points future verbs at
(`src/asana_mcp/tools/composite_write.py` module docstring cross-references this file).

## 3. Motivation — the silent-degradation scar (SVR-6 / SCAR-IDEM-001)

The asana idempotency store silently degrades to a no-op on failure at **two** live
surfaces at HEAD (f3d8eec1):

1. **Config-time degrade** — on store-configuration failure the process logs a warning
   and swaps in `NoopIdempotencyStore()`, then keeps serving (`api/main.py:369-372`,
   marker `"fallback": "noop"`). A no-op store accepts every write as "first execution".
2. **Finalize-time swallow** — a `finalize()` exception is swallowed, leaving a
   double-execution window on retry (`api/middleware/idempotency.py:719`; SCAR-IDEM-001,
   OPEN at HEAD, `scar-tissue.md:92`).

For human-paced traffic a silent no-op is a latent risk. For an **agentic** caller that
retries automatically on any ambiguous response, a silent no-op turns "exactly once" into
"once per retry" with no signal — qualitatively worse (slate B5 :167-168). A non-idempotent
verb on top of a silently-degrading store is the exact hazard this contract forbids.

## 4. The Fail-Loud Contract (interface)

A non-idempotent verb MUST route through a store satisfying this interface. Names mirror
the existing asana store shape (`reserve`/`finalize`) so the contract is bindable, but the
**semantics below are the contract**, not the signatures.

```text
IdempotencyStore  (contract — any conforming implementation)
  reserve(key) -> Reservation
      • Returns a NEW reservation on first sight of `key`.
      • Returns a REPLAY marker if `key` was already finalized.
      • MUST raise IdempotencyUnavailable if the backing store cannot be reached or
        cannot guarantee the reservation. It MUST NOT return a "new" reservation on
        backend failure (that is the forbidden silent no-op).

  finalize(key, outcome) -> None
      • Records terminal outcome for `key`.
      • MUST raise IdempotencyFinalizeFailed on write failure. It MUST NOT swallow the
        exception (the SCAR-IDEM-001 anti-pattern). The caller decides recovery.

  Forbidden: any code path that substitutes a no-op / in-memory / best-effort store for
  the configured durable store WITHOUT raising. Degradation is a fail-CLOSED event, never
  a silent swap.
```

**Fail-loud invariant.** For a non-idempotent verb, "the store might be degraded" and
"the write is safe to attempt" are mutually exclusive. If durability cannot be asserted,
the verb call is REFUSED (see §6), never attempted-and-hoped.

## 5. Degradation-Telemetry Requirements

When a conforming store cannot guarantee its contract it MUST, before raising:

1. Emit a **structured** degradation event distinguishable from normal operation
   (a dedicated event name, not a generic warning), carrying: the key (or a
   non-reversible digest), the backend identity, the concrete error, and the
   verb/tool name.
2. Increment a **degradation counter** metric labelled by verb and backend so a
   silent-drift regression is visible on a dashboard, not only in logs.
3. Surface a caller-visible **honesty flag** (analogous to the C6 `stale_served` /
   `contract_complete` fields, SVR-5) so an LLM caller learns the write did NOT occur —
   never a shape that reads as success.

Telemetry is fail-CLOSED corroboration, not a substitute for raising: emitting the event
and then continuing (the current `main.py:369-372` shape) is explicitly non-conforming.

## 6. Fail-Closed Posture

- A non-idempotent verb whose store raises `IdempotencyUnavailable` MUST refuse the write
  and return a loud, retryable-typed error naming the true cause (never auth-shaped;
  cf. C3 cold-frame discipline). It MUST NOT fall through to an unguarded write.
- The refusal is reported with the same honesty the v1 composite tool already models:
  exactly what did / did not happen, no atomicity claimed beyond what the store guarantees.
- Route curation remains the Phase-1 security boundary (constraint 6): a non-idempotent
  verb is not tool-wrapped until it fails closed on unarmed shapes (slate B5 :169-171).

## 7. Acceptance — how a future verb clears this gate

A future non-idempotent verb PR is contract-conformant iff:

- [ ] It binds to a store satisfying §4 (reserve raises on unavailability; finalize raises
      on write failure; no silent no-op swap).
- [ ] It emits the §5 telemetry triad (structured event + counter + caller honesty flag).
- [ ] It fails closed per §6 (loud refusal, true cause, no unguarded fall-through).
- [ ] It ships WITH the reviewed OpenFGA amendment for its principal class (the DRAFT
      companion, `autom8y` PR `feat/asana-mcp-v1-s3-openfga-draft`) — not designed cold.
- [ ] A two-sided test proves it: the write succeeds when the store is healthy AND is
      REFUSED (not silently no-oped) when the store is unavailable.

## 8. Relationship to the v1 composite tool

The v1 tool is the *positive* exemplar of the posture this contract generalizes: it
already refuses loudly and reports exactly what committed, claiming no atomicity the
backing API cannot give. The difference is scope — v1 needs no idempotency STORE because
its verbs are idempotent by selection (W-3/W-4). This contract is what makes the same
honesty enforceable once a verb can no longer lean on natural idempotence.

## 9. SVR Receipts (re-verified live at HEAD f3d8eec1, sprint-3)

```yaml
SVR-B5-1:
  claim: "the asana idempotency store silently swaps in a no-op backend on config failure and keeps serving — the config-time silent-degrade surface this contract forbids"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/api/main.py"
    line_range: "L369-L372"
    marker_token: '"fallback": "noop"'
    claim: "on store-config failure the code logs idempotency_store_degraded and assigns NoopIdempotencyStore(), then continues — degradation without refusal"
SVR-B5-2:
  claim: "SCAR-IDEM-001 (finalize() exception swallowed -> double-execution on retry) is OPEN at HEAD — the finalize-time surface the fail-loud finalize() clause targets"
  verification_method: file-read
  verification_anchor:
    source: ".know/scar-tissue.md"
    line_range: "L92"
    marker_token: "Idempotency `finalize()` exception silently swallowed — double-execution risk on retry"
    claim: "the scar registry records SCAR-IDEM-001 at api/middleware/idempotency.py:719 as an open double-execution risk"
```

## 10. Deliberate Non-Scope (resist creep)

- No backend chosen; no store code written or changed (spec-only, §1 non-goal).
- SCAR-IDEM-001 is NOT remediated here — v1 is safe by verb selection; remediation is a
  precondition only for the FIRST non-idempotent verb, which is operator-reserved.
- No generalization into a fleet-shared store (slate B5: the four repos' needs differ; the
  shared artifact is this CONTRACT, not an implementation).
