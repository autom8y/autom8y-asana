---
type: spec
status: proposed
---

# PRD: First-Attach Remediation — Onboarding-Walkthrough Attach Failure (2026-07-01)

> Procession: FIRST-ATTACH REMEDIATION · Station N1 (requirements-analyst)
> Grandeur anchor: remediate the first real onboarding-walkthrough attach failure **to root** — close the fleet-wide observability swallow, NAME the autom8_data fault (R1 vs R2), fix with NO bandaid, proven by a deliberately-broken fixture RED→GREEN **and** a live re-invoke. Denominator stays **1** (Neu Life, GHL, task `1213653428400851`).
> Verification tree: `origin/main` at HEAD `cb4b42017b71f582e7bd09945e96730e6f81ec33` (all file:line anchors below re-verified against THIS SHA this session; dispatch cited `caade003` — a ±1-line drift is noted where it occurs).
> Read-only artifact: this PRD mutates no code. Self-grade ceiling: **MODERATE** (pantheon self-authored; `self-ref-evidence-grade-rule`).

---

## Overview

On 2026-07-01 the onboarding-walkthrough workflow processed exactly one triggering task (Neu Life, GHL) and it **failed fast (0.51s) with `failed:1`** — but the failure emitted **no per-task log line** and was therefore un-diagnosable. Static reading cannot name the escaping exception because the shared bridge runner's terminal broad-catch swallows it without logging. This PRD specifies a no-bandaid remediation: (1) close the fleet-wide observability swallow in the SHARED bridge runner, (2) widen the resolve/anchor excepts so autom8_data faults become NAMED failed reasons instead of escaping to the generic swallow, and (3) NAME the fault (R1 Neu-Life data vs R2 fleet S2S-auth) by evidence — a deliberately-broken fixture RED→GREEN locally **and** the post-deploy live re-invoke whose now-emitted structured log is the non-negotiable functional receipt.

## Impact Assessment
<!-- Required for workflow routing -->
impact: high
impact_categories: [cross_service, security]

Rationale:
- **cross_service** — the observability fix is authored in the SHARED bridge runner (`bridge_base.py`) that ALL asana workflows execute (`insights_export`, `conversation_audit`, `payment_reconciliation`, `onboarding_walkthrough`). Fleet blast radius by construction (G-PROPAGATE).
- **security** — the classification fix widens the except ladder around the W1 tenant-identity anchor (`workflow.py:490-538`) and the by-GUID verifier (`truth_source.py:68`), a cross-tenant-leak fail-closed path. No guard logic changes; the fail-closed invariant is preserved and explicitly re-asserted (INV-2).
- Routes to **Architect** (high-impact routes to Architect regardless of LOC). This PRD is the upstream artifact for the Architecture phase.

## Background

**The failure (inherited runtime ground truth — 2026-07-01; NOT re-litigated).** Neu Life (GHL) was the ONLY triggering task. It failed fast (0.51s) with `failed:1`, swallowed (no per-task log). Customer-clean: 0 walkthrough attachments; the workflow **never emails** — the `@appointments.contenteapp.com` value is a gated *routing address* embedded in the deck, resolved via the SDK phone leg, not an email recipient (corroborated by the workflow docstring's RESOLVE→FREEZE→UPLOAD→DELETE leg list, `workflow.py:1-23` — no email leg).

**P6 (inherited live evidence — NOT re-litigated).** `insights_export` ran `succeeded:67, failed:0`, zero auth errors / 3 days ⇒ fleet S2S auth WORKS ⇒ **R2 (fleet S2S-auth) disfavored, R1 (Neu-Life-specific data / non-canonical value) favored**. P4 (producer bundling) is DISPROVEN as cause — do not chase image bundling.

**Verified structural ground truth (re-inspected this session at `cb4b4201`):**

| # | Anchor | Verified fact | Receipt |
|---|--------|---------------|---------|
| A | `src/autom8_asana/automation/workflows/bridge_base.py:222-237` | Per-entity broad-catch: `try: return await self.process_entity(...)` / `except (Exception) as exc:  # BROAD-CATCH: boundary -- per-entity isolation` returns `BridgeOutcome(status="failed", reason=None, error=WorkflowItemError(error_type="unexpected_error", message=str(exc), recoverable=True))`. **NO `logger.` call in the block** — `grep -c 'logger\.'` over lines 220-238 = `0`. This is the SHARED runner for ALL asana workflows. Dispatch cited `223-237`; on `cb4b4201` the `try` is L222, `except` L224-226, return L227-237 (±1-line SHA drift). | file-read + bash-probe |
| B | `.../onboarding_walkthrough/workflow.py:440-460` | RESOLVE leg wraps the SDK phone resolve in `try:` and catches **ONLY** `except DataServiceUnavailableError as exc:` (L444) → logs `onboarding_walkthrough_resolve_unavailable` + returns `failed`, `error_type="resolve_unavailable"`. `ValueError` / any other `DataService*` **escape** this narrow except → propagate to Anchor A (the silent swallow). | file-read |
| C | `.../onboarding_walkthrough/workflow.py:490-538` | The W1 anchor except ladder catches `GuardViolationError` (L497→skip `guard_violation`), `AmbiguousCardinalityError` (L512→skip `ambiguous_anchor`), `GfrError` (L525→skip `anchor_unresolved`) — **the GFR family only**. `DataService*` are NOT `GfrError` subclasses (`GfrError(Exception)` @ `resolution/gfr/errors.py:41`; `DataService*` are from `autom8y_core.errors`) ⇒ a data-service fault in the by-GUID anchor **escapes** to Anchor A. | file-read |
| D | `src/autom8_asana/resolution/gfr/truth_source.py:68` | `record = await verifier.get_business_by_guid_async(company_id)` is called **UNWRAPPED** inside `verify_company_id_async` — only the `None` (miss) and guid-mismatch cases are handled (both `return False`); an EXCEPTION from the call escapes the function ⇒ up to Anchor A. | file-read |

**Why the fault is not statically nameable (decisive analyst finding).** The dispatch's R1 mechanism "non-canonical GUID → `ValueError`" does NOT ground to a raise-site on this tree:
- `identity_guard.extract_address_guid` (`identity_guard.py:53-68`) is `gated_address.split("@", 1)[0].lower()` — it **cannot** raise `ValueError`; a non-canonical local-part silently becomes a mismatch and is caught as a `guid_anchor_mismatch` **SKIP** (`workflow.py:557`), not a failure.
- The only `raise ValueError` in the resolution path is `gfr/errors.py:68`, a **defensive programming-error guard** (fires only when `UnresolvedError.reason` is outside the closed vocabulary) — not a Neu-Life data path.
⇒ The exact escaping exception was **erased by the swallow**. This is not a gap in analysis; it is the proof that Requirement FR-1 (observability) is load-bearing and that the fault can only be NAMED by the post-fix structured log (FR-3c/3d).

---

## User Stories

- As an **operator triaging a fleet failure**, I want every per-entity `failed` outcome to emit a structured error log carrying `task_gid`, `error_type`, `message`, and `traceback`, so that a production failure is never again invisible (the 2026-07-01 condition).
- As the **onboarding-walkthrough owner**, I want autom8_data faults in the resolve/anchor legs classified as NAMED failed reasons, so that a data fault is distinguishable from the generic `unexpected_error` and from a benign no-identity-path skip.
- As the **incident closer**, I want the Neu-Life fault NAMED as R1 (data) or R2 (auth) by evidence, so that remediation is routed correctly (fix here vs escalate to sre/platform) with no bandaid.

---

## Functional Requirements

### Must Have

#### FR-1 — Observability contract (fleet-wide) · Anchor A `bridge_base.py:222-237`
The per-entity broad-catch in the SHARED bridge runner MUST emit a **structured error-level log on every swallowed failure**, carrying at minimum:
- `task_gid` / `item_id` (from `entity.get("gid", "unknown")`),
- `error_type` = `type(exc).__name__`,
- `message` = `str(exc)`,
- `traceback` (formatted exception traceback).

**Invariant:** no per-entity outcome may be counted `failed` by this block without a corresponding log line. The fix is authored in `bridge_base.py` (the shared runner), NOT in an onboarding-walkthrough orphan (G-PROPAGATE) — it benefits `insights_export` / `conversation_audit` / `payment_reconciliation` by construction. The broad-catch REMAINS as the terminal per-entity isolation net (INV-3); this requirement adds observability, it does not narrow the catch.

**Acceptance (AC-1):**
- (AC-1a, RED→GREEN) A test in `tests/unit/automation/workflows/test_bridge_base.py` defines a `BridgeWorkflowAction` subclass (extend the existing `_TestBridge` pattern, L29-49) whose `process_entity` raises `ValueError("boom")`. Run `execute_async([{gid: "neu-life-fixture"}], {})`. **RED-before** (pre-fix code): outcome is `failed:1` **and NO error log is emitted** (reproduces 2026-07-01). **GREEN-after** (fixed code): outcome is `failed:1` **and** exactly one structured error log is emitted carrying `task_gid="neu-life-fixture"` and `error_type="ValueError"`.
- (AC-1b, two-sided teeth) A sibling `_TestBridge` whose `process_entity` returns `succeeded` (and one returning `skipped`) emits **no** error log and is counted `succeeded`/`skipped` — the log fires ONLY on the fault, not on the clean path.

#### FR-2 — Classification contract · Anchors B (`workflow.py:440-460`) + C (`workflow.py:490-538`)
Resolve/anchor autom8_data faults MUST become NAMED `failed` reasons, not the generic `unexpected_error`. Named FAILED reasons are carried in `WorkflowItemError.error_type` (per precedent `resolve_unavailable` @ `workflow.py:456`); `BridgeOutcome.reason` remains the SKIP field (`bridge_base.py:57,63`). The per-entity ISOLATION contract is preserved: each widened except returns a per-entity `BridgeOutcome` — one task's fault never aborts the `asyncio.gather` sweep (INV-3).

**Taxonomy (proposed error_type strings — testable; Architect may refine names, not semantics):**

| Leg / anchor | Exception (currently escaping) | New disposition | `error_type` | `recoverable` |
|--------------|-------------------------------|-----------------|--------------|---------------|
| RESOLVE (B, L440-460) | `ValueError` (malformed / non-canonical input from resolve or downstream parse) | `failed` | `resolve_invalid_input` | `False` (data-shape fault) — **R1 candidate** |
| RESOLVE (B) | `DataService*` base/sibling (exact class per OQ-1) | `failed` | `resolve_data_error` | per class — R1/R2 candidate |
| ANCHOR (C, L490-538) | `DataServiceUnavailableError` | `failed` | `anchor_unavailable` | `True` (transient infra) — **R2 candidate** |
| ANCHOR (C) | `DataService*` base/sibling (per OQ-1) | `failed` | `anchor_data_error` | per class — R1/R2 candidate |
| TERMINAL (A, L222-237) | anything still uncaught | `failed` + **structured log** (FR-1) | `type(exc).__name__` in the LOG (field MAY stay `unexpected_error`; enrichment is OQ-4) | `True` |

Rationale for symmetry: the ANCHOR DataService* path is classified `failed` (not `skipped`) to MIRROR the existing RESOLVE leg, so a transient data-service fault is counted/alarmed and is never mistaken for the benign "no identity path → skip" case. Fail-closed either way (no attach), but `failed` is the honest, alarmed disposition.

**Acceptance (AC-2):** In `tests/unit/automation/workflows/test_onboarding_walkthrough.py` (extend the existing `DataServiceUnavailableError`-on-resolve stub @ L559-562):
- (AC-2a) resolve stubbed to raise `ValueError` ⇒ outcome `failed`, `error_type="resolve_invalid_input"`, and it does NOT reach the terminal swallow (proves B widened).
- (AC-2b) the by-GUID anchor (via `truth_source.py:68`) stubbed to raise `DataServiceUnavailableError` ⇒ outcome `failed`, `error_type="anchor_unavailable"`, and it does NOT reach the terminal swallow (proves C widened).
- (AC-2c) the GFR-family paths (`GuardViolationError`/`AmbiguousCardinalityError`/`GfrError`/`guid_anchor_mismatch`) are UNCHANGED — their existing skip reasons still fire (regression guard on the ladder ordering, subclasses-before-base).

#### FR-3 — Remediation acceptance (measurable, non-negotiable)
The remediation is accepted only when ALL of:
- (AC-3a) **RED-then-GREEN fixture** — AC-1a holds: the deliberately-broken fixture fires RED (failed, no log) on pre-fix code and GREEN (failed, logged with `task_gid` + `error_type`) on fixed code.
- (AC-3b) **two-sided teeth** — AC-1b holds: the no-defect entity still succeeds/skips cleanly with no error log.
- (AC-3c) **the fault is NAMED (R1 vs R2) by evidence** — the read-only static discriminator is INCONCLUSIVE (see Background: no static raise-site), therefore naming is resolved by the post-fix live re-invoke's structured log `error_type`/`message` (FR-3d). The named `error_type` selects the R1/R2 branch (below).
- (AC-3d) **live re-invoke against the real Lambda is the functional receipt** — a green unit suite is NOT acceptance (this arc's scar: local-green ≠ runtime-correct). NOTE (analyst finding, load-bearing): `just invoke onboarding-walkthrough …` runs LOCALLY in-process (`scripts/invoke_workflow.py` — "Developer CLI for local testing", constructs the workflow and calls `enumerate_async`+`execute_async`); there is NO `aws lambda invoke` recipe in the `justfile`. Local invoke is therefore the exact trap the scar warns against and does NOT satisfy AC-3d. The functional receipt is: the **deployed** Lambda re-invoked for the single Neu-Life task (`1213653428400851`), whose CloudWatch log now carries the FR-1 structured line naming the fault. Because the deployed image must carry the fix for this log to exist, AC-3d is inherently **post-deploy** and is executed by the operator (see Sequencing + Out of Scope). This PRD SPECIFIES the receipt; it does not execute it.

**Sequencing (explicit — resolves the deploy/acceptance tension):**
1. Author FR-1 + FR-2 in code; prove AC-1/AC-2 locally (RED→GREEN, two-sided). ← this arc's "done" (G-RUNG).
2. Operator deploys the fixed shared image (RESERVED).
3. Operator re-invokes the deployed Lambda for Neu-Life (`1213653428400851`); the emitted structured log NAMES the fault → resolves AC-3c and the R1/R2 branch.
4. If R1: apply the Neu-Life data fix (FR-5 SHOULD). If R2: escalate to sre/platform (FR-5 WON'T-here).

#### FR-4 — Invariants preserved (see INV table)
The fix MUST preserve every invariant in the Invariants section. Specifically: customer-clean (no attach/mint/send on a failure — the workflow fails closed BEFORE FREEZE), denominator = 1 (Neu Life, GHL), no blanket-enable, no deck-map widening, no selection change; #725 remains OPEN ⇒ broad rollout BLOCKED.

### Should Have

#### FR-5 — R1 data-fault fix (conditional on naming)
IF AC-3c names an **R1** fault (Neu-Life-specific data — e.g., a malformed/non-canonical address-embedded value, a by-GUID record shape that raises rather than returns `None`, or a data-shape error localized to Neu Life's record), THEN fix the R1 data fault to root within denom=1. The concrete fix is deferred until the live log names the exact `error_type`/field (do not pre-build against an unverified mechanism).

### Could Have

- (FR-6) Enrich `WorkflowItemError.error_type` at the terminal catch from the static `"unexpected_error"` to `type(exc).__name__` (currently OQ-4) — improves downstream typed consumers, wider blast radius; defer unless Architect rules it in-scope.

---

## Non-Functional Requirements

- **NFR-1 (isolation):** per-entity isolation preserved — one task's fault MUST NOT abort the `asyncio.gather` sweep (`bridge_base.py:239`). All widened excepts return per-entity `BridgeOutcome`; the terminal broad-catch stays as the last-resort net.
- **NFR-2 (no blast widening):** zero change to selection/enumeration, `WALKTHROUGH_DECK_MAP`, feature-flag/enable state, or the attach/mint/send legs. Change surface is confined to error-handling + logging in `bridge_base.py` (terminal catch) and `workflow.py` (resolve L440-460 + anchor L490-538 ladders).
- **NFR-3 (log hygiene):** the FR-1 structured log MUST mask/omit PII consistent with existing discipline (guids masked via `identity_guard.mask_guid`, phones via `mask_phone_number`); `str(exc)`/traceback MUST NOT spill a full unmasked guid or office_phone.
- **NFR-4 (no double-log):** a fault already NAMED-and-logged by a widened resolve/anchor except MUST NOT ALSO be re-logged by the terminal catch (it no longer reaches it) — exactly one structured log per failed outcome.

---

## MoSCoW Summary

| Priority | Item | Gate |
|----------|------|------|
| **MUST** | FR-1 close the swallow (structured log in shared `bridge_base.py`) | G-PROPAGATE, G-PROVE |
| **MUST** | FR-2 widen resolve (B) + anchor (C) excepts → NAMED failed reasons | G-PROVE |
| **MUST** | FR-3 name the fault by evidence; live re-invoke is the functional receipt | G-THEATER, G-RUNG |
| **MUST** | FR-4 preserve invariants (customer-clean, denom=1, #725 BLOCKED) | G-DENOM |
| **SHOULD** | FR-5 fix the R1 Neu-Life data fault **iff** named R1 | conditional |
| **COULD** | FR-6 enrich terminal `WorkflowItemError.error_type` to `type(exc).__name__` | OQ-4 |
| **WON'T (here)** | R2 fleet autom8_data S2S-auth fix → escalate to sre/platform (contradicts P6) | escalation |
| **WON'T** | rewrite the bridge; rebuild/redeploy the shared image; re-enable; attach; mint; send; widen deck-map | RESERVED (operator) |

---

## Scope Boundary

**In scope (this arc, code):**
- Structured error log in the terminal broad-catch, `bridge_base.py:222-237` (shared runner).
- Widened resolve except ladder, `workflow.py:440-460`.
- Widened anchor except ladder, `workflow.py:490-538`.
- Unit tests: `test_bridge_base.py` (AC-1), `test_onboarding_walkthrough.py` (AC-2).
- Specification of the live re-invoke receipt (FR-3d) and the R1/R2 branch.

**Out of scope (RESERVED — the operator's, past the G-RUNG rung):**
- Rebuilding / redeploying the shared Lambda image.
- Re-enabling the workflow; any attach / mint / send / deck delivery.
- Executing the live production re-invoke (post-deploy) — SPECIFIED here, executed by operator.
- The R2 fleet S2S-auth fix (route to sre/platform if named — contradicts P6).
- Rewriting the bridge; widening `WALKTHROUGH_DECK_MAP`; changing selection; broad rollout (#725 OPEN).

---

## R1 / R2 Branch (resolved post-deploy by AC-3c)

```
Post-deploy live re-invoke of Neu-Life (1213653428400851) → structured log error_type:
├── error_type ∈ {resolve_invalid_input, resolve_data_error, anchor_data_error, a Neu-Life-local data class}
│      → R1 CONFIRMED (favored by P6). Data fault localized to Neu Life within denom=1.
│      → FR-5 SHOULD: fix the R1 data fault to root. Stay denom=1.
└── error_type ∈ {auth/credential/S2S class} (e.g. anchor_unavailable driven by auth, or a 401/403 data-service class)
       → R2. CONTRADICTS P6 (insights_export succeeded:67 / zero auth / 3d).
       → ESCALATE to sre/platform. WON'T fix here. Re-examine P6 premise as part of escalation.
```
Note: `anchor_unavailable` (transient infra) is R1/R2-ambiguous on its own — the log `message`/underlying cause disambiguates. The branch is selected by the NAMED cause in the live log, not by the coarse `error_type` alone.

---

## Invariants

| ID | Invariant | Enforcement anchor |
|----|-----------|--------------------|
| INV-1 | Customer-clean: no attach / mint / send on a failure — workflow fails closed BEFORE FREEZE | resolve/anchor legs return `failed`/`skipped` prior to FREEZE (`workflow.py` step 5); no producer subprocess runs |
| INV-2 | Fail-closed identity guard unchanged: a data-service fault in the anchor must NOT attach on the phone resolve alone | anchor ladder `workflow.py:490-538` widened for observability/naming only; guard/compare logic (L545-557) untouched |
| INV-3 | Per-entity isolation: one task's fault never aborts the sweep | terminal broad-catch retained `bridge_base.py:224-237`; `asyncio.gather` L239 |
| INV-4 | Denominator = 1 (Neu Life, GHL): no blanket-enable, no deck-map widening, no selection change | positive-necessity GATE `workflow.py:405-425` untouched; `WALKTHROUGH_DECK_MAP` unchanged |
| INV-5 | #725 OPEN ⇒ broad rollout BLOCKED | no enable/rollout in scope |
| INV-6 | The workflow never emails (address is a gated routing value embedded in the deck) | `workflow.py:1-23` leg list has no email leg |

---

## Edge Cases

| Case | Expected behavior |
|------|-------------------|
| `process_entity` raises a non-`DataService*`, non-`ValueError` exception (e.g. `KeyError`) | Terminal catch (A): `failed` + structured log, `error_type="KeyError"`. Never silent. (AC-1 generalizes.) |
| Resolve raises `DataServiceUnavailableError` (pre-existing path) | Unchanged: `failed`, `error_type="resolve_unavailable"`, logged `onboarding_walkthrough_resolve_unavailable` (`workflow.py:444-459`). No regression. |
| Anchor raises `GfrError`/`UnresolvedError` (benign no-identity-path) | Unchanged: `skipped`, reason `anchor_unresolved` (WARNING) (`workflow.py:525-538`). Not reclassified to failed. |
| Non-canonical address local-part that does NOT raise (mismatch) | Unchanged: `skipped`, reason `guid_anchor_mismatch` (`workflow.py:557`). Not a failure — do not reclassify. |
| Two tasks in one sweep, one faults | Faulting task → `failed` + one log; sibling proceeds (isolation, INV-3). No double-log (NFR-4). |
| `str(exc)` / traceback contains a raw guid or phone | Masked/omitted per NFR-3 before logging. |
| `entity` has no `gid` key | Log/`item_id` use `"unknown"` (existing `entity.get("gid", "unknown")` default) — still logged, never silent. |

---

## Success Criteria (testable by QA Adversary)

- [ ] `bridge_base.py:224-237` emits a structured error log with `task_gid`, `error_type=type(exc).__name__`, `message=str(exc)`, `traceback` on every swallowed failure (FR-1).
- [ ] AC-1a: deliberately-broken fixture RED (failed, no log) on pre-fix, GREEN (failed, logged w/ task_gid + error_type) on fixed code.
- [ ] AC-1b: no-defect entity succeeds/skips with no error log (two-sided teeth).
- [ ] AC-2a: resolve `ValueError` ⇒ `failed`, `error_type="resolve_invalid_input"`, not reaching terminal swallow.
- [ ] AC-2b: anchor `DataServiceUnavailableError` ⇒ `failed`, `error_type="anchor_unavailable"`, not reaching terminal swallow.
- [ ] AC-2c: GFR-family + `guid_anchor_mismatch` dispositions unchanged (regression guard).
- [ ] NFR-1..4 hold (isolation; no blast widening; PII masked; exactly-one-log-per-failure).
- [ ] AC-3c/3d SPECIFIED: the post-deploy live re-invoke of `1213653428400851` and its structured-log naming receipt are documented as the functional acceptance; local `just invoke` is explicitly rejected as insufficient.
- [ ] Invariants INV-1..6 preserved (verified by inspection + tests).

---

## Open Questions

- **OQ-1 (blocks FR-2 exact naming):** the ONLY `DataService*` class referenced in-tree is `DataServiceUnavailableError` (`workflow.py:35`; tests L559/775). The dispatch names a distinct `DataServiceError` (malformed); there is **no in-tree receipt** for a bare `DataServiceError` class, and `autom8y_core` is not importable in this sandbox. Architect/Principal MUST confirm the exact `DataService*` base/sibling class name against the installed `autom8y_core.errors` at design time before wiring `resolve_data_error`/`anchor_data_error`. Do not assume the class name.
- **OQ-2:** does the SDK `resolve_routing_address_by_phone_async` (autom8y_core, not in-tree) raise `ValueError` on a malformed value, or only `DataService*`? The `resolve_invalid_input` mapping is contingent on the SDK's real exception surface — confirm at design time.
- **OQ-3 (execution boundary):** the post-deploy live re-invoke (AC-3d) requires the fixed image deployed AND the deployed Lambda invoked for Neu-Life. Both are RESERVED (operator). Confirm operator ownership and the exact re-invoke mechanism (production re-trigger vs `aws lambda invoke` — the repo has no such recipe today).
- **OQ-4 (COULD, FR-6):** enrich terminal `WorkflowItemError.error_type` from static `"unexpected_error"` to `type(exc).__name__`? Wider blast radius on typed consumers — Architect decides in-scope vs deferred.
- **OQ-5:** should the FR-1 traceback be full or truncated (log-volume / cost on the shared fleet runner)? Defaulting to full traceback pending Architect ruling.

---

## Handoff — Verified Anchor Attestation

All anchors re-inspected this session against `origin/main` HEAD `cb4b42017b71f582e7bd09945e96730e6f81ec33` (Read tool + bash-probe). Absolute paths:

| Anchor | Absolute path:line | Claim attested |
|--------|--------------------|----------------|
| A (swallow) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/automation/workflows/bridge_base.py:222-237` | broad-catch returns `failed`, NO logger (grep-0) |
| B (resolve narrow except) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/automation/workflows/onboarding_walkthrough/workflow.py:444` | catches only `DataServiceUnavailableError`; else escapes |
| C (anchor except ladder) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/automation/workflows/onboarding_walkthrough/workflow.py:490-538` | GFR-family only; `DataService*` escapes |
| D (unwrapped by-GUID verifier) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/resolution/gfr/truth_source.py:68` | `get_business_by_guid_async` unwrapped; exception escapes |
| E (test fixture pattern) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/automation/workflows/test_bridge_base.py:29-49` | `_TestBridge` overridable `process_entity` — RED/GREEN substrate |
| F (resolve-fault test precedent) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/automation/workflows/test_onboarding_walkthrough.py:559-562` | `DataServiceUnavailableError`-on-resolve stub — AC-2 substrate |
| G (local-invoke, NOT real Lambda) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/justfile:306-307` → `scripts/invoke_workflow.py` | `just invoke` is local in-process; no `aws lambda invoke` recipe |

**Ready-for-Architecture checklist:** user stories w/ acceptance ✔ · FR MoSCoW-prioritized ✔ · NFR measurable ✔ · edge cases enumerated ✔ · no unresolved stakeholder conflict (open questions deferred, not blocking authoring) ✔ · success criteria QA-testable ✔ · out-of-scope documented ✔ · impact assessment (high; cross_service, security) ✔ · anchors verified via Read/bash ✔ · attestation table w/ absolute paths ✔.

**"Done" (G-RUNG) for THIS arc** = swallow-closed (FR-1) + excepts-widened (FR-2) + fault-naming-mechanism-in-place, proven by AC-1/AC-2 RED→GREEN locally; the fault NAMING and R1/R2 resolution complete at the operator's post-deploy live re-invoke (FR-3d). "Done" is NEVER "realized" (attach/send/deliver) — that is past the reserved deploy.

Self-grade: **MODERATE** (`self-ref-evidence-grade-rule` — pantheon self-authored). Structural anchors A-G are file-read/bash-probe verified at `cb4b4201`; runtime facts (0.51s, P6, customer-clean) are inherited-and-not-re-litigated per dispatch.
