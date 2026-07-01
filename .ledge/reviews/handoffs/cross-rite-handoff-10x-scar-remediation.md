---
type: handoff
from: review
to: 10x-dev
created: 2026-06-24
status: proposed
initiative_slug: asana-coherence
head: f4f924d2
findings: [SCAR-REG-001, SCAR-IDEM-001, H-3-push-seam]
gate_authority: telos-integrity-ref §3 Gate C
---

# Cross-Rite Handoff: review → 10x-dev
## SCAR Remediation — idempotency finalize + push-seam observability

---

## 1. Grandeur Anchor

Pick up the torch on autom8y-asana — the ecosystem's CRM-UI / datastore-frontend / workflow-orchestration layer composing into autom8y-{data,ads,sms,scheduling} flows — by driving the review-rite deep-dive from glint-detected signal to a graded, cross-rite-routed case file, advancing the two production-blockers (SCAR-REG-001; SCAR-IDEM-001) from `authored` toward `proven`; proven ONLY by a live receipt — never by a green dashboard or an optimistic merge. Production-mutating levers stay the user's.

Source: `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md` (Grandeur anchor field, verbatim).

---

## 2. Findings Handed Off

### P1 — SCAR-REG-001: Sequential placeholder GIDs at reconciliation routing boundary (HIGH)

**Location**: `src/autom8y_asana/reconciliation/section_registry.py:94–107` (EXCLUDED_SECTION_GIDS), `:128–150` (UNIT_SECTION_GIDS)

**Defect**: 19 visibly sequential GID constants annotated `VERIFY-BEFORE-PROD (SCAR-REG-001)` have never been verified against the live Asana API. If wrong, reconciliation silently misroutes units — tasks either enter excluded sections (Templates, Account Error) or active processing sections are skipped with no metric surfacing the mismatch.

**G-RUNG at handoff time**: defect `proven` (code-confirmed at `section_registry.py:94–107, :128–150` per PV-PREFLIGHT P1 receipt — `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:31`); live-Asana verification rung = `PENDING`.

**What 10x-dev owns (post-iris receipt)**:
- Replace 19 placeholder entries in `section_registry.py:94–107` (EXCLUDED_SECTION_GIDS) and `:128–150` (UNIT_SECTION_GIDS) with live GIDs from the iris receipt of `GET /projects/1201081073731555/sections`.
- Update test fixtures referencing the placeholder GIDs.
- Remove `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations after replacement is confirmed.

**Blocked on**: iris receipt (live `GET /projects/1201081073731555/sections`). Do not author the replacement without the receipt — G-RUNG forbids rounding up from `PENDING` to `proven`.

**Production-readiness gate**: BLOCKED — reconciliation routing correctness cannot be trusted until the live-Asana GID receipt replaces the placeholders.

---

### P2 — SCAR-IDEM-001: Idempotency `finalize()` swallowed — double-execution risk on S2S retry (HIGH)

**Location**: `src/autom8_asana/api/middleware/idempotency.py:719`

**Defect**: `DynamoDBIdempotencyStore.finalize()` is wrapped in a bare `except Exception` that logs and swallows the exception (`idempotency.py:719` — `except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD … a client retry will re-execute the mutation (double-execution risk)`). On failure, the idempotency key is NOT persisted. A client retry then re-executes the mutation. No CloudWatch error metric is emitted on this path. The inline SCAR comment explicitly identifies double-execution risk for S2S strict-once callers.

**G-RUNG at handoff time**: risk `proven` open (`.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:32` — P2 code receipt verbatim; `.ledge/reviews/asana-coherence-case-file.md:69–72` — H-2 finding block).

**What 10x-dev owns**:
- Promote the swallowed exception to an emitted CloudWatch error metric on the `finalize()` failure path at `idempotency.py:719`.
- Evaluate the 500-propagation path: S2S strict-once callers should receive a non-2xx on finalize failure so they do not silently re-execute.
- Wire the metric name through to the SRE alerting gate (coordinate with `sre` rite for threshold and runbook).

**Production-readiness gate**: BLOCKED for S2S strict-once callers — the system-wide idempotency middleware contract has a correctness gap that affects every POST endpoint covered by the middleware.

---

### P2-adjacent — Push-seam / bridge-fleet dark subsystem (H-3): `StatusPush*` not emitting; no prod bridge-fleet observability (HIGH)

**Location**: `src/autom8_asana/services/gid_push.py:498–504`; `src/autom8_asana/services/push_orchestrator.py:192–198`

**Signal-sifter root-cause** (from `.ledge/reviews/asana-coherence-case-file.md:108–116`):
`push_status_to_data_service()` returns `False` silently when `AUTOM8Y_DATA_URL` is absent from the Lambda env. One `logger.warning` is emitted; no CloudWatch metric. `StatusPushSuccess` and `StatusPushFailure` — emitted at `push_orchestrator.py:192–198` — are structurally unreachable in this configuration. Iris observed zero `StatusPush*` events in the live CloudWatch namespace (PV-PREFLIGHT bonus signal — `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:40–41`); the gate-absence at `gid_push.py:498–504` is the structural explanation. When `AUTOM8Y_DATA_URL` is absent, the entire push-seam goes dark with zero SRE-observable signal.

**This is a warranted fix**: the structural explanation is sound (gate-absence at a proven code path), the live CloudWatch absence of `StatusPush*` events is consistent with the structural cause [UNATTESTED on the env-config state in production — G-DENOM: absence of telemetry is not proof of zero activity; the env-config state must be confirmed before concluding the gate is absent in prod vs. confirming AUTOM8Y_DATA_URL is set].

**G-RUNG at handoff time**: gate logic `proven` (code-confirmed); prod env-config state `UNVERIFIABLE` from code alone; observability rung = `emitting` (warning log only — NOT `alerting`) per `.ledge/reviews/asana-coherence-case-file.md:111`.

**What 10x-dev owns**:
- Add `emit_metric("StatusPushSkipped")` at `gid_push.py:503` (two `emit_metric` calls total — success-branch skip and failure-branch skip at the gate-exit paths in `_push_to_data_service_internal()`).
- This is the lowest-effort / highest-observability-impact action in the entire review: ~30 minutes, no blocked dependencies, no iris receipt required.
- Coordinate with `sre` rite post-merge to add alarm on `StatusPushSkipped > 0` in production.

**Bridge-fleet dark context**: `Autom8y/AsanaBridgeFleet :: LastSuccessTimestamp` last datapoint was `2026-06-18T13:32:06`; no datapoints for 2026-06-19 through 2026-06-24 (~6 days) per PV-PREFLIGHT live receipt at `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:39`. Only `{environment: staging, workflow_id: insights-export}` is dimensioned — no production workflow dimension observed. The push-seam gate-absence is the most probable structural explanation for the dark window, but the bridge-fleet dimension investigation (iris: query `Autom8y/AsanaBridgeFleet` across all dimensions) must close before `StatusPush*` dark is declared the root cause. [UNATTESTED — DEFER-POST-HANDOFF: bridge-fleet namespace investigation is routed to iris + sre, not 10x-dev; this item is noted for context only.]

---

## 3. Suggested Command (surface only — do NOT run)

```
/10x
```

Invoke after iris has delivered the live Asana section-GID receipt (SCAR-REG-001 unblock) and after the push-seam metric task is ready to author. The `/10x` command engages the principal-engineer + qa-adversary pipeline for implementation and adversarial test validation.

---

## 4. Realization Rung

```
authored → emitting → proven (RED fixture) → merged (USER-SOVEREIGN) → live → protecting-prod
```

| Rung | Meaning | Who holds it |
|------|---------|-------------|
| authored | Fix is written; SCAR annotation removed; metric call present in code | 10x-dev |
| emitting | Metric wires to CloudWatch and fires in test/staging | 10x-dev + sre |
| proven (RED fixture) | A deliberately-broken fixture fires RED on the finalize double-execution path; a no-defect variant passes GREEN (two-sided teeth; G-THEATER: never green-run-alone) | qa-adversary |
| merged | PR merged to main | USER-SOVEREIGN |
| live | Deployed to production | USER-SOVEREIGN |
| protecting-prod | Alarm threshold set; on-call runbook live; no SCAR annotation remains VERIFY-BEFORE-PROD | sre + USER-SOVEREIGN |

G-RUNG discipline: rungs are named, never rounded up. `merged` and all rungs above it are USER-SOVEREIGN — no agent advances them.

---

## 5. Acceptance Receipt

**What advances the rung from `proven (RED fixture)` to `merged`:**

### SCAR-IDEM-001 (primary acceptance criterion)

**Two-sided fixture requirement (G-THEATER: never green-run-alone)**:

1. **RED fixture — deliberately-broken path**: A test fixture that simulates `DynamoDBIdempotencyStore.finalize()` raising an exception MUST fire RED (test fails / assertion fails) demonstrating that the double-execution path is exercisable. The fixture must assert the mutation is NOT idempotent when finalize fails — i.e., a second call re-executes rather than returning the cached result. This fixture must be authored to fail before the fix is applied.

2. **GREEN fixture — no-defect variant**: The same scenario with the fix in place (finalize failure promotes to metric, exception propagated to caller for strict-once S2S, or key is persisted on partial success) MUST pass GREEN. The GREEN fixture proves the fix closes the double-execution path.

**Acceptance criterion is NOT met by**:
- A single GREEN fixture on the happy path (green-run-alone is G-THEATER anti-pattern)
- A log assertion that the exception was caught (the SCAR is about silent swallow, not logging)
- A metric assertion without a corresponding caller-propagation check for strict-once S2S paths

### SCAR-REG-001 (acceptance criterion, post-iris receipt)

1. Iris receipt of `GET /projects/1201081073731555/sections` is present as a file:line anchor in the PR description or commit body — the receipt is the denominator proof.
2. All 19 constants in `section_registry.py:94–107, :128–150` match the live API response; sequential placeholders are gone.
3. `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations are removed.
4. Test fixtures updated to reference live GIDs (not the sequential placeholders).

### Push-seam (acceptance criterion)

1. `emit_metric("StatusPushSkipped")` is present at `gid_push.py:503` (or equivalent gate-exit location).
2. The metric emits in the test suite (unit or integration fixture asserting the call fires when `AUTOM8Y_DATA_URL` is absent).
3. SRE has acknowledged the metric name for alarm wiring (or the task is filed as a DEFER-POST-MERGE with a named owner).

---

## 6. Inherited Live Receipts

The following live receipts were produced by iris + PV-PREFLIGHT and underpin the finding gradings in this handoff. They are inherited verbatim — not re-asserted by case-reporter.

### PV-PREFLIGHT attestation receipts

| Finding | Receipt | Source |
|---------|---------|--------|
| SCAR-REG-001 code-confirmed | `section_registry.py:94–99` + `:128–131` two `VERIFY-BEFORE-PROD (SCAR-REG-001)` blocks; `EXCLUDED_SECTION_GIDS={1201081073731600..603}` (`:100-107`), `UNIT_SECTION_GIDS={1201081073731610..624}` (`:132-150`) — visibly sequential | `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:31` |
| SCAR-IDEM-001 code-confirmed | `idempotency.py:719` `except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD … a client retry will re-execute the mutation (double-execution risk)`; only `logger.exception` follows (`:720-728`). No error-metric promotion. | `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:32` |
| Push-seam zero `StatusPush*` events | Iris observed zero `StatusPush*` events; real metric is `StatusPushFailure` via `emit_metric` (`push_orchestrator.py:198`); push-seam health NOT validated | `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:40–41` |
| Bridge-fleet dark window | `Autom8y/AsanaBridgeFleet :: LastSuccessTimestamp` last datapoint `2026-06-18T13:32:06`; no datapoints 2026-06-19…24 (~6 days); only `{environment: staging, workflow_id: insights-export}` dimensioned | `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:39` |
| CI @ HEAD integration tests SKIPPED | `ci / Integration Tests` SKIPPED (non-blocking) at HEAD `f4f924d2` | `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:20–21` |
| AWS creds live | `arn:aws:iam::696318035277:user/tom.tenuta` LIVE at triage time | `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:46` |

### iris attestation note

Iris was summoned by the user but agent file was not active at PV-PREFLIGHT time (`~/.claude/agents/iris.md` MISSING — requires CC restart per `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:45`). All iris-derived metrics above were produced during the PV-PREFLIGHT triage session before iris was fully activated. The live Asana section-GID receipt for SCAR-REG-001 (`GET /projects/1201081073731555/sections`) is PENDING iris dispatch post-restart — it is NOT present in this handoff. [UNATTESTED — DEFER-POST-HANDOFF: iris restart + live GID receipt is the first gate before 10x-dev can author the section_registry constant replacement.]

Evidence confidence: [MODERATE — self-assessed per G-CRITIC discipline; external corroboration PENDING for all HIGH findings per `.ledge/reviews/asana-coherence-case-file.md:235`].

---

## 7. Out-of-Scope / User-Sovereign Levers

The following are explicitly out of scope for this handoff and remain user-sovereign or deferred:

| Item | Status | Reason |
|------|--------|--------|
| Merge to `main` | USER-SOVEREIGN | G-RUNG: `merged` rung is never advanced by an agent |
| Production deployment / rollback | USER-SOVEREIGN | G-RUNG: `live` and `protecting-prod` rungs are never advanced by an agent |
| Live Asana section-GID write (updating live Asana workspace) | USER-SOVEREIGN | Production-mutating lever; no agent touches the live Asana API write path |
| `POST /v1/query/{entity_type}` retire decision | DEFER — iris gate first | Retire requires Logs Insights gate on `deprecated_query_endpoint_used.caller_service` since 2026-06-01; G-DENOM bars retire on absence-of-evidence; routed to iris + `10x-dev` post-receipt (`.ledge/reviews/asana-coherence-case-file.md:150–161`) |
| cache_warmer.py decomposition (H-4) | DEFER — planned sprint | 1437 LOC with proven fault history; not an emergency block; effort is significant (8+ test fixture updates); register as a planned sprint item, not this handoff's scope |
| Bridge-fleet namespace investigation | DEFER — iris + sre | `Autom8y/AsanaBridgeFleet` dimension query is an iris task; alarm wiring is sre; 10x-dev has no action until those gates close (M-4, `.ledge/reviews/asana-coherence-case-file.md:141`) |
| FORK-2: SDK substrate upstream PR | DEFER — trigger 2026-09-29 | Coordinated PR to `autom8y_client_sdk.data`; dispatch-asserted defer watch registered; not in current sprint scope (`.ledge/reviews/asana-coherence-case-file.md:171`) |
| .know/ corpus regeneration (M-2) | DEFER — `/know --all` | One-command fix; route to `know` rite, not 10x-dev |
| Broad-except annotation compliance (M-3) | DEFER — hygiene sprint | 10 unannotated sites in `intake_*`; route to `hygiene` rite |
| G-SCOPE: do not scope-creep into M-4, M-5, or FORK-2 | ACTIVE GUARD | This handoff is scoped to SCAR-IDEM-001 + push-seam metric + SCAR-REG-001 (post-iris). Any expansion of scope requires a new handoff artifact. |

---

*Handoff mode: FULL review → 10x-dev | Authored by review rite (case-reporter) | HEAD: f4f924d2 | 2026-06-24*
*Evidence ceiling: [MODERATE — G-CRITIC self-assessed; external corroboration PENDING for all HIGH findings]*
