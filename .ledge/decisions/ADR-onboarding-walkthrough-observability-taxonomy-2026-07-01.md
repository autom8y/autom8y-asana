---
type: decision
decision_subtype: adr
id: ADR-OBW-OBS-TAXONOMY
artifact_id: ADR-onboarding-walkthrough-observability-taxonomy-2026-07-01
schema_version: "1.0"
status: draft
lifecycle_status: draft
date: "2026-07-01"
rite: 10x-dev
station: N2 (architect)
initiative: "First-Attach Remediation — onboarding-walkthrough attach failure"
deciders: [architect (10x-dev)]
consulted: [principal-engineer (downstream implementer), qa-adversary (broken-fixture RED proof)]
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored design within 10x-dev; caps at MODERATE per self-ref-evidence-grade-rule.
  Exception-class + premise claims are executable/file-read receipts (TDD §0). Fault-NAMING
  is POST-DEPLOY and NOT asserted here (G-RUNG).
related:
  - TDD-onboarding-walkthrough-remediation-2026-07-01
  - .ledge/specs/PRD-onboarding-walkthrough-remediation-2026-07-01.md
supersedes: []
---

# ADR: Fleet-Wide Observability Swallow-Close + autom8_data Fault-Naming Taxonomy

## Status

DRAFT — pending principal-engineer implementation + qa-adversary broken-fixture two-sided RED→GREEN. Terminal rung = **swallow-closed + PR-surfaced**; fault-naming (R1/R2) and any realization are POST-DEPLOY (operator, N5 HANDOFF).

## Context

The shared bridge runner's terminal broad-catch (`bridge_base.py:222-237`) counts a per-entity `failed` outcome with **no log line** (verified: `grep -c 'logger\.'` over the block = 0). The 2026-07-01 Neu-Life failure was therefore invisible. Two narrow excepts let KNOWN autom8_data faults escape into that generic swallow: the resolve leg catches only `DataServiceUnavailableError` (`workflow.py:444`); the anchor ladder catches only the GFR family (`workflow.py:497/512/525`), while the GFR engine (`engine.py`) has NO broad-catch (grep-empty) so a `DataService*`/auth exception from the unwrapped `truth_source.py:68` propagates raw to the swallow. `autom8y_core 4.9.0` exposes a `TransportError`-rooted hierarchy where `DataServiceError` (data) and `TokenAcquisitionError` (auth) are **siblings** (TDD §0 R-1). No bandaid, no bridge rewrite; isolation and INV-1..6 preserved.

## Decisions

### D1 — FR-1 log: structured ERROR via `exc_info`, placed BEFORE the failed return, at the shared runner

Emit `logger.error("bridge_entity_failed", workflow_id=…, task_gid=…, error_type=type(exc).__name__, message=str(exc), exc_info=exc)` immediately before the `return BridgeOutcome(status="failed", …)` inside the existing broad-catch. Authored in `bridge_base.py` (shared) → fleet-wide (G-PROPAGATE). The catch is NOT narrowed (INV-3).

- **Alternatives considered:** (a) Author the log in the onboarding-walkthrough `process_entity` instead — REJECTED: leaves the swallow open for `insights_export`/`conversation_audit`/`payment_reconciliation` (defeats the grandeur anchor). (b) Log at the `execute_async` aggregation (post-`gather`, from `WorkflowResult.errors`) — REJECTED: `WorkflowItemError` carries no traceback and the class name is already flattened to `unexpected_error`; the discriminating frame (SDK raise-site) is lost. (c) Raise/propagate instead of logging — REJECTED: breaks per-entity isolation (INV-3), aborts the sweep.
- **Consequences:** every `failed` outcome from this block now emits exactly one structured line naming the class + full traceback. Additive; two-way door. Benefits the whole fleet.

### D2 — OQ-5: FULL traceback (not truncated)

Use `exc_info=exc` + the configured `structlog.processors.format_exc_info` (`structlog_backend.py:109`) — a full traceback in the `exception` field.

- **Alternatives considered:** (a) Truncated / top-N-frames — REJECTED: could elide the SDK frame (`format_routing_address` / `_fetch_business_envelope`) that discriminates R1 vs R2, re-opening the diagnostic gap this arc closes. (b) No traceback, message only — REJECTED: `str(exc)` alone does not locate the raise-site. (c) `dict_tracebacks` structured frames — deferred (heavier; not in the current processor chain; unnecessary for a rare-path line).
- **Consequences:** the block fires only on the failure path — a healthy sweep emits ZERO lines; volume scales with faults (near-zero by SLO), not throughput. Full traceback renders frames + exception string, NOT locals (NFR-3). A future high-failure-cardinality workflow is a per-sink sampling concern, not a reason to blind the shared runner.

### D3 — FR-2 taxonomy: catch the `DataServiceError` family by name; let the auth family fall to the logged terminal net

Widened resolve/anchor legs catch `DataServiceError` (and its `DataServiceUnavailableError`/`DataServiceValidationError` subclasses) → NAMED `failed` reasons. They do NOT catch `TransportError`/`TokenAcquisitionError`. Since `InvalidServiceKeyError` is NOT a `DataServiceError` (TDD §0 R-1, executable), an auth escape falls through to the now-logged terminal net where its true class name surfaces as an unambiguous **R2** signal.

- **Alternatives considered:** (a) Catch the `TransportError` grand-base in the ladders (one net for all transport faults) — REJECTED: collapses R1 (data) and R2 (auth) into one generic name and destroys the discrimination that is the whole point of naming the fault. (b) Add an explicit `except TokenAcquisitionError → error_type="auth_error"` leg — REJECTED for THIS arc: it pre-commits a name to a fault P6 says is disfavored, and it would move the R2 signal OUT of the terminal net into a workflow-local leg, coupling the onboarding workflow to an S2S concern that belongs to sre/platform; letting it surface at the shared net (with its real class name) is the honest, lower-coupling disposition. Reconsider only if the live log names R2. (c) Reclassify anchor `DataService*` as `skipped` — REJECTED: a transient/data fault would be indistinguishable from the benign no-identity-path skip; `failed` is the honest, alarmed disposition mirroring the resolve leg.
- **Consequences:** the common R1 and R2 cases are self-discriminating on `error_type` alone; only the transient `*_unavailable` class needs `message`/`error_category`/`status_code`. Ladders are sized to verified raise-sites — no dead legs.

### D4 — Widening locus: the workflow anchor ladder, NOT `truth_source.py:68`

Widen the anchor except ladder at `workflow.py:490-538` (the per-entity policy boundary). Do NOT wrap the unwrapped by-guid call at `truth_source.py:68`.

- **Alternatives considered:** wrap `truth_source.py:68` and convert `DataService*` there — REJECTED: `verify_company_id_async` is typed `-> bool`; a wrap could only (i) `return False` — which would re-bury a transient/data/auth fault as a benign `guid_anchor_mismatch`/`anchor_unresolved` skip (the exact anti-pattern), or (ii) re-raise as `GfrError` — which lands in `except GfrError` → `skipped anchor_unresolved`, again masking the fault. Both re-swallow. The DIP-correct boundary is the high-level workflow policy owning disposition; the low-level resolution substrate raises typed exceptions and stays disposition-free.
- **Consequences:** `truth_source.py:68` stays unwrapped (unchanged); the fault propagates to the workflow ladder where it becomes a NAMED per-entity `failed` outcome. Preserves the resolution substrate's single responsibility.

### D5 — FR-6/OQ-4: DEFER enriching the terminal `WorkflowItemError.error_type`

Keep the terminal `WorkflowItemError.error_type = "unexpected_error"` (contract-stable). The escaping class name lives in the FR-1 LOG (`error_type` field + traceback), which is where the operator reads it to name R1/R2.

- **Alternatives considered:** set `error_type = type(exc).__name__` on the terminal `WorkflowItemError` — REJECTED for this arc: this changes the ERROR CONTRACT of the shared runner (any consumer matching `error_type == "unexpected_error"` across the fleet could break) — a wider blast radius that buys nothing, because the naming goal is already fully met by the log field. Reversible; revisit as a separate typed-consumer initiative if a consumer wants the class in the structured error object.
- **Consequences:** KNOWN faults get meaningful `error_type` via FR-2 named legs; only the genuinely-unanticipated residual stays `unexpected_error` in the contract while carrying its real class name in the log. Minimal blast radius; two-way door.

## Consequences (rollup)

- Fleet-wide: no per-entity `failed` outcome is invisible again (FR-1); `insights_export`/`conversation_audit`/`payment_reconciliation` benefit for free.
- Known autom8_data faults become NAMED, alarmed `failed` reasons (FR-2); the terminal net is the last-resort observability floor for residual + auth-family (R2) escapes.
- The R1/R2 discrimination is designed into the class taxonomy (D3) and resolved POST-DEPLOY by the live re-invoke log (TDD §8). This arc does not — and must not — claim the fault is named pre-deploy (G-RUNG).
- INV-1..6 preserved; all changes are two-way doors; no one-way-door sign-off gate.

## Scope-Fence (RESERVED — operator, past the rung)

Image rebuild/redeploy · re-enable · the live production re-invoke · any attach/mint/send · the R2 sre/platform fix · deck-map/selection/denominator changes (G-DENOM). This design terminates at a surfaced PR.
