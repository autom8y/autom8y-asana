---
type: review
status: accepted
phase: report
slug: asana-coherence
upstream: asana-coherence-severity-profile.md
preflight: PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md
mode: FULL
head: f4f924d2
date: 2026-06-24
overall_grade: C
---

# Code Review: autom8y-asana — Ecosystem Coherence

**HEAD**: f4f924d2 | **Branch**: chore/bump-core-4.6.0 | **Date**: 2026-06-24

---

## Executive Summary

autom8y-asana is a functionally capable service with a broad test suite and a healthy dependency posture, but it carries two open production-correctness blockers — unverified reconciliation GIDs (SCAR-REG-001) and a swallowed idempotency finalize that enables double-execution on S2S retry (SCAR-IDEM-001) — both explicitly annotated `VERIFY-BEFORE-PROD` in the codebase with verification still pending. Layered across these two blockers is a coherence decay pattern: three subsystems (push-seam, AIMD observability, bridge-fleet health) share the same failure mode — silent non-emission rather than error emission — making the system appear healthy to CloudWatch when it may not be. The deprecated `POST /v1/query/{entity_type}` endpoint has been running past its June 1 sunset with usage unverifiable from metrics alone, and a Logs Insights gate must pass before the retire-vs-extend decision is made. The recommended next action is: (1) unblock iris for the live Asana section-GID receipt on SCAR-REG-001, (2) wire the two missing CloudWatch metrics for the idempotency finalize path and the push-seam gate-exit, and (3) run the Logs Insights query on the deprecated endpoint — three quick-fix actions that together advance all four HIGH findings and close the most critical operational blind spots.

---

## Health Report Card

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Complexity | C | cache_warmer.py at 1437 LOC with three distinct warm paths; active fault zone — two defects traced to this file in recent commits |
| Testing | B | Broad unit/integration/synthetic suite; integration tests SKIPPED at HEAD CI; push-seam skip path is covered (`test_skips_when_no_data_service_url`) |
| Dependencies | B | autom8y-core bumped to 4.6.0 at HEAD; lockfile present; no rot signal; SCAR-LP-001 historical only |
| Structure | C | SCAR-REG-001 (19 unverified sequential GIDs at reconciliation routing boundary); SCAR-IDEM-001 (double-execution risk on S2S retry); lapsed deprecated endpoint (23 days post-sunset) |
| Hygiene | B | 94% broad-except annotation compliance (185/197); `protocols.py:42` ~30% figure overstated; `.know/` corpus 90-commit stale |
| **Overall** | **C** | Median B; weakest-link forces C — two C-graded categories carry four HIGH findings including two production-correctness blockers [PLATFORM-HEURISTIC: the B-vs-C boundary for this configuration] |

**Overall grade calculation trace** (from pattern-profiler, used as-is):
Complexity=C, Testing=B, Dependencies=B, Structure=C, Hygiene=B → median B across five → no F or D cap → 2-of-5 at C does not trigger the 3+ automatic drop rule → but Structure holds two HIGH findings with production-correctness implications and Complexity holds one HIGH with active fault-zone evidence → weakest-link [AV:SRC-007 Kane 2013 STRONG] forces overall = **C**.

---

## Metrics Dashboard

| Metric | Value |
|--------|-------|
| Files scanned | Multiple (5 audit loci + bonus signals per PV-PREFLIGHT) |
| Total findings | 11 (4 HIGH, 5 MEDIUM, 2 LOW) |
| Critical findings | 0 |
| HIGH findings | 4 |
| MEDIUM findings | 5 |
| LOW findings | 2 (1 fixed, 1 refuted — neither open) |
| Production-correctness blockers | 2 (H-1 SCAR-REG-001, H-2 SCAR-IDEM-001) |
| Test coverage signal | Broad (unit + integration + synthetic); integration SKIPPED at HEAD CI |
| Integration tests at HEAD | SKIPPED (non-blocking) |
| Review mode | FULL |
| .know/ corpus age | 90 commits / 49 days stale |

---

## Production-Readiness Verdict

**Two findings are production-correctness blockers. Neither has cleared its verification gate.**

**Blocker 1 — SCAR-REG-001** (`reconciliation/section_registry.py:94–107, :128–150`):
19 sequential placeholder GIDs annotated `VERIFY-BEFORE-PROD` are shipping in production-bound reconciliation routing code. If wrong, units are silently misrouted — tasks either enter excluded sections or active processing sections are silently skipped. The defect is `proven` in code; the live-Asana verification rung is `PENDING`. This finding cannot be cleared without a live API receipt from `GET /projects/1201081073731555/sections`.
**Verdict: BLOCKED — do not rely on reconciliation routing correctness without the live-Asana GID receipt.**
External corroboration: PENDING (critic). [MODERATE confidence per G-CRITIC ceiling — self-assessed]

**Blocker 2 — SCAR-IDEM-001** (`api/middleware/idempotency.py:719`):
`finalize()` exception is silently swallowed; idempotency key not persisted on failure; client retry re-executes the mutation. The inline SCAR comment explicitly names double-execution risk for S2S strict-once callers. No CloudWatch metric on the failure path. The risk is `proven` open in code.
**Verdict: BLOCKED for S2S strict-once callers — the system-wide idempotency middleware contract has a correctness gap that affects every POST endpoint covered by the middleware.**
External corroboration: PENDING (critic). [MODERATE confidence per G-CRITIC ceiling — self-assessed]

---

## Findings by Priority

### HIGH

---

**H-1 — SCAR-REG-001: Sequential placeholder GIDs at reconciliation routing boundary**

- **Location**: `src/autom8y_asana/reconciliation/section_registry.py:94–107` (EXCLUDED_SECTION_GIDS), `:128–150` (UNIT_SECTION_GIDS)
- **G-RUNG**: defect `proven` (in code); live-Asana verification `PENDING` — NOT proven
- **Description**: 19 visibly sequential GID constants (e.g., `1201081073731600..1603`, `1201081073731610..624`) carry `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations. They have never been verified against the live Asana API. If wrong, reconciliation silently misroutes units — either processing excluded sections (Templates, Account Error) or silently skipping active processing sections. No metric surfaces the mismatch.
- **Severity**: HIGH — correctness risk at reconciliation routing boundary; silent failure mode
- **Effort**: Quick fix once live-Asana access available (single API call + 19 constant replacements + test fixture update)
- **Cross-rite routing**: `iris` (live `GET /projects/1201081073731555/sections` receipt) → `10x-dev` (constant replacement post-receipt)
- **Production-readiness gate**: BLOCKED — requires live-Asana receipt before routing can be trusted
- External corroboration: PENDING (critic). [MODERATE confidence per G-CRITIC ceiling]

---

**H-2 — SCAR-IDEM-001: Idempotency finalize() swallowed — double-execution risk on S2S retry**

- **Location**: `src/autom8_asana/api/middleware/idempotency.py:719`
- **G-RUNG**: risk `proven` (defect in code)
- **Description**: `DynamoDBIdempotencyStore.finalize()` is wrapped in a bare `except Exception` that logs and swallows the exception. On failure, the idempotency key is NOT persisted. A client retry then re-executes the mutation. The inline SCAR comment explicitly identifies double-execution risk for S2S strict-once callers. No CloudWatch error metric is emitted on this path.
- **Severity**: HIGH — the middleware is the system-wide idempotency contract; a gap here is not scoped to one endpoint
- **Effort**: Moderate (error metric wire-up + alerting + caller contract review for S2S 500-propagation path)
- **Cross-rite routing**: `sre` (missing CloudWatch error metric + alerting threshold) → `10x-dev` (promote log to metric; add 500 propagation for strict-once S2S callers)
- **Production-readiness gate**: BLOCKED for S2S strict-once callers
- External corroboration: PENDING (critic). [MODERATE confidence per G-CRITIC ceiling]

---

**H-3 — StatusPush* structurally unreachable when AUTOM8Y_DATA_URL absent — operational blind spot**

- **Location**: `src/autom8_asana/services/gid_push.py:498–504`
- **G-RUNG**: gate logic `proven`; prod env-config state `UNVERIFIABLE` from code alone (G-DENOM); observability rung = `emitting` (warning log only — NOT `alerting`)
- **Description**: `push_status_to_data_service()` returns `False` silently when `AUTOM8Y_DATA_URL` is absent from the Lambda env. One `logger.warning` is emitted; no CloudWatch metric. `StatusPushSuccess` and `StatusPushFailure` (emitted at `push_orchestrator.py:192–198`) are structurally unreachable in this configuration. Iris observed zero `StatusPush*` events — this gate is the most probable structural explanation. When absent, the entire push-seam goes dark with zero SRE-observable signal.
- **Severity**: HIGH — observability failure; the push-seam can be entirely non-functional with no alarm, no dashboard signal, no on-call visibility. Structurally identical to the SCAR-005/006 coherence decay pattern.
- **Effort**: Quick fix (two `emit_metric` calls at gate-exit paths in `_push_to_data_service_internal()`)
- **Cross-rite routing**: `sre` (add alarm on `StatusPushSkipped > 0` in production) → `10x-dev` (add `emit_metric("StatusPushSkipped")` at `gid_push.py:503`)
- External corroboration: PENDING (critic). [MODERATE confidence per G-CRITIC ceiling]

---

**H-4 — cache_warmer.py 1437 LOC — three warm paths in a single Lambda handler; active fault zone**

- **Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:1–1437` (three paths at `:1291–1304`)
- **G-RUNG**: `proven` (LOC confirmed by receipt; fault history confirmed via commit log)
- **Description**: The Lambda handler colocates three structurally distinct execution paths (entity-type warm, bulk prematerialization, section prematerialization), AIMD governor logic, WarmResponse dataclass, push side-effects, and checkpoint machinery. Recent commits demonstrate this coupling produces observable defects: C-1 (AIMD dark) and C-2 (warm-cycle semaphore multiply) both traced to this file. The dd8e43ab diff was 702 lines touching this file and 10 others — high merge-conflict and cognitive-load surface.
- **Severity**: HIGH — not cosmetic complexity; the coupling has a proven fault history; active change velocity amplifies the risk
- **Effort**: Significant (decompose into `_warm_entity_type.py`, `_warm_bulk_set.py`, `_warm_section_set.py`, shared `_warm_shared.py`; thin dispatcher; test fixture updates across 8+ test files)
- **Cross-rite routing**: `10x-dev` (decomposition) → `sre` (verify observability stays correct through refactor)
- External corroboration: PENDING (critic). [MODERATE confidence per G-CRITIC ceiling]

---

### MEDIUM / LOW

Medium findings are summarized below. Detail available in the severity profile at `.ledge/reviews/asana-coherence-severity-profile.md`.

| ID | Finding | Location | Key Action | Routing |
|----|---------|----------|------------|---------|
| M-1 | protocols.py `~30%` interop figure overstated; re-quantified at ~14% (2/14 methods) | `protocols.py:42` | Update doc; recover/re-author spike doc | `docs`, `know` |
| M-2 | .know/ corpus 90-commit stale; P5 cache features absent from feat/INDEX.md | `.know/` (all domains) | Run `/know --all`; add staleness check to review pre-flight | `know` |
| M-3 | 10 unannotated broad-except sites (5% non-compliance); clustered in `services/intake_*` | `intake_resolve_service.py:229,316` + 8 others | Add `# noqa: BLE001 — {reason}` to each | `hygiene` |
| M-4 | Bridge-fleet LastSuccessTimestamp dark since 2026-06-18 (~6 days); root cause unresolved | `Autom8y/AsanaBridgeFleet` (CloudWatch) | Dispatch iris to query all namespace dimensions; check staging-only registration | `iris`, `sre` |
| M-5 | /v1/query/{entity_type} sunset lapsed 23 days; usage unverifiable from metrics (log-only signal) | `api/main.py:470`, `routes/query.py:881` | Run Logs Insights on `deprecated_query_endpoint_used`; retire or extend per receipt | `iris`, `10x-dev` |

**LOW findings** (closed — not open actions):
- L-1: C-1 AIMD dark (pre-dd8e43ab) — **fixed** in dd8e43ab (merged 2026-06-19). G-RUNG: fix `merged`.
- L-2: H4 governor-throttle hypothesis — **code-refuted**. `_sample_aimd_engaged()` is read-only; AIMD cannot zero-output the warmer. G-RUNG: refutation `proven`.

---

## Fork Recommendations

### FORK-1: Retire vs. Extend `POST /v1/query/{entity_type}` (Sunset lapsed 2026-06-01)

**Pythia verdict**: Instrument-first, then decide. The only usage signal is a log line (`routes/query.py:885 logger.info("deprecated_query_endpoint_used", extra={caller_service, entity_type})`). There is no `emit_metric` call in this handler. `Autom8y/AsanaWorkflows` publishes 0 metrics. "No usage" is unproven — G-DENOM bars retire on absence-of-evidence.

**Evidence gate (must pass before retire)**:
Run CloudWatch Logs Insights over the asana API log group for the full window since `Sunset: 2026-06-01`, aggregating on `deprecated_query_endpoint_used.caller_service`. Gate PASSES for retire only if: (a) recordsScanned > 0 (denominator real) AND (b) zero distinct `caller_service`. If recordsScanned = 0 (denominator silent), retire remains barred — add `emit_metric` on the event first.

**Ranked options**: (1) Instrument-first via iris Logs Insights query — RECOMMENDED; (2) Re-stamp Sunset + notify callers if usage found; (3) Retire only after gate passes.

**Routing**: `iris` (Logs Insights query — this is the gate) → `10x-dev` (retire or re-stamp based on receipt); optionally `10x-dev` (add `emit_metric` on `deprecated_query_endpoint_used` at `routes/query.py:885` to close the silent-namespace gap permanently).

---

### FORK-2: Interop orphan adapter — SDK substrate vs. per-service (TENSION-006)

**Pythia verdict**: Interop methods (`get_reconciliation_async`, `get_export_csv_async`) belong in the shared SDK substrate (`autom8y_client_sdk.data`), not the per-service orphan adapter. G-PROPAGATE is not refutable — the substrate is already a live external dependency (`bridge_base.py:37`); the orphan reproduces the dual-source-of-truth anti-pattern.

**Recommended**: Option 1 — coordinated upstream PR to the SDK substrate. If a rebind seam is needed before the PR lands, Option 3 is acceptable: a signature-identical local shim in `protocols.py` marked for deletion on substrate landing.

**Status**: DEFER — watch registered, trigger date 2026-09-29 (dispatch-asserted; owner = SDK-repo owner). The dangling `INTEGRATE-ecosystem-dispatch §1.4` phased-plan reference (at `protocols.py:44`, confirmed by `design-constraints.md:321` as absent) is a filed gap (Cassandra complaint `COMPLAINT-20260624-*-pythia.yaml`). The ~14% re-quantification (M-1) does not change the fork conclusion — the interop method count is independent of the coverage ratio decision.

**Routing**: `10x-dev` (SDK upstream PR or local shim authoring when fork becomes active); `know` (recover or re-author the INTEGRATE-ecosystem-dispatch spike doc referenced at `protocols.py:44`)

---

## Cross-Rite Routing Recommendations

| Concern | Recommended Rite | Action | Finding |
|---------|-----------------|--------|---------|
| Live Asana GID verification for SCAR-REG-001 | `iris` | `GET /projects/1201081073731555/sections` — provides the receipt to unblock H-1 | H-1 |
| Section GID constant replacement | `10x-dev` | Replace 19 placeholder entries in `section_registry.py`; update test fixtures. Blocked on iris receipt. | H-1 |
| Idempotency finalize error metric + alerting | `sre` | Add CloudWatch error metric on `finalize()` failure path; set alerting threshold | H-2 |
| Idempotency S2S propagation fix | `10x-dev` | Promote log to error metric; evaluate 500-propagation path for strict-once S2S callers | H-2 |
| Push-seam silent-skip alarm | `sre` | Add alarm on `StatusPushSkipped > 0` in production; wire to on-call runbook | H-3 |
| Push-seam gate-exit metric | `10x-dev` | Add `emit_metric("StatusPushSkipped")` at `gid_push.py:503`; two `emit_metric` calls total | H-3 |
| cache_warmer.py decomposition | `10x-dev` | Decompose into four files; thin dispatcher; update 8+ test fixtures | H-4 |
| Decomposition SRE continuity | `sre` | Verify observability (AIMD, checkpoint, push metrics) remains correct post-refactor | H-4 |
| Deprecated endpoint Logs Insights query | `iris` | Aggregation on `deprecated_query_endpoint_used.caller_service` since 2026-06-01; passes gate for retire | M-5 / FORK-1 |
| Deprecated endpoint retire or re-stamp | `10x-dev` | Post-iris: retire route mount at `api/main.py:470` if gate passes; re-stamp Sunset if callers found | M-5 / FORK-1 |
| Bridge-fleet namespace investigation | `iris` | Query `Autom8y/AsanaBridgeFleet` across all dimensions; check if production workflow is missing | M-4 |
| Bridge-fleet alerting gap | `sre` | Add alarm for `LastSuccessTimestamp` dark > N hours in production | M-4 |
| .know/ corpus regeneration | `know` | Run `/know --all`; add staleness gate to review pre-flight checklist | M-2 |
| Interop overstated figure correction | `docs` | Update `protocols.py:42` from ~30% to ~14% (2/14 public methods) with basis note | M-1 |
| INTEGRATE spike doc recovery | `know` | Recover or re-author the `INTEGRATE-ecosystem-dispatch §1.4` spike doc referenced at `protocols.py:44` | M-1 / FORK-2 |
| Broad-except annotation compliance | `hygiene` | Add `# noqa: BLE001 — {reason}` to 10 sites in `intake_*` and `api/routes/` | M-3 |
| SDK substrate upstream PR (deferred) | `10x-dev` | Coordinated PR to `autom8y_client_sdk.data`; trigger 2026-09-29 | FORK-2 |

---

## Recommended Next Steps

Priority ordered by impact-to-effort ratio:

1. **[Quick / HIGH impact] — H-3: Add push-seam gate-exit metric** (`gid_push.py:503`). Two `emit_metric` calls closes the most operationally dangerous silent blind spot. Effort: 30 minutes. Does not require iris or blocked access. Route: `10x-dev`.

2. **[Quick / HIGH impact] — H-1: Dispatch iris for live Asana GID receipt**. `GET /projects/1201081073731555/sections`. This is the only gate that can close the production-correctness blocker on reconciliation routing. Route: `iris` (requires CC restart to activate iris agent per PV-PREFLIGHT tooling note).

3. **[Quick / HIGH impact] — M-5 / FORK-1: Run Logs Insights gate on deprecated endpoint**. Aggregation on `deprecated_query_endpoint_used.caller_service` since 2026-06-01. Converts the retire-vs-extend fork from undecidable to decidable in one iris query. Route: `iris`.

4. **[Moderate / HIGH impact] — H-2: Wire CloudWatch error metric on idempotency finalize failure**. Promotes the SCAR-IDEM-001 risk from invisible to observable; unblocks the S2S caller contract review. Route: `sre` + `10x-dev`.

5. **[Quick / MEDIUM impact] — M-2: Regenerate .know/ corpus**. `/know --all` — one command; all 90-commit drift resolved. Agents and engineers operating on the stale model are a compounding risk across future reviews and architecture changes. Route: `know`.

6. **[Quick / MEDIUM impact] — M-4: Dispatch iris for bridge-fleet namespace investigation**. Query `Autom8y/AsanaBridgeFleet` across all dimensions to determine if the 6-day gap is a telemetry miss or an operational failure. Gate for the subsequent SRE alerting decision. Route: `iris`.

7. **[Significant / HIGH impact — planned] — H-4: Decompose cache_warmer.py**. 1437 LOC with proven fault history; not an emergency block but a compounding risk with each future AIMD/checkpoint change. Effort: one focused sprint. Route: `10x-dev`.

---

## Coherence Decay — Structural Theme

Four of the nine open findings (H-3, M-4, H-2 in part, plus L-1 now fixed) are instances of a single structural pattern identified by pattern-profiler: **silent non-emission rather than error emission as the failure mode**. When an env-config dependency is absent, a DynamoDB call fails, or a telemetry annotation is missing, the system produces silence rather than an observable error. This is the same pattern as SCAR-005/006 (cache coherence, historical). The 06-18/19 quiescence window (bridge-fleet dark, AIMD dark pre-dd8e43ab fix) is consistent with this pattern cascading across subsystems simultaneously.

This pattern warrants a cross-cutting remediation norm beyond the individual findings: **every gate-exit and failure path in production code should emit a named CloudWatch metric, not just a log line**. The three quick-fix metric additions (H-3, H-2, M-5) each address one instance; an architectural convention enforcing this at the team level would prevent recurrence.

Evidence grade for pattern: [STRUCTURAL | MODERATE] — three structurally independent observations converge; no single conclusive proof; G-DENOM prohibits STRONG without live CloudWatch receipt.

---

## Evidence Discipline

All findings in this report are inherited verbatim from pattern-profiler (`asana-coherence-severity-profile.md`). No severity has been re-graded by case-reporter. G-RUNG rungs are named per the profiler's assessment and never rounded up (`authored < emitting < alerting < proven < merged < live < protecting-prod`). The G-DENOM constraint applies throughout: absence of telemetry signal is not treated as proof of zero activity.

Self-assessed confidence is capped at MODERATE per G-CRITIC discipline. External corroboration is PENDING for all HIGH findings.

---

*Review mode: FULL | Generated by review rite | HEAD: f4f924d2 | 2026-06-24*
