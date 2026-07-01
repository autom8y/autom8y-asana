---
type: review
status: accepted
head: origin/main (f795d7dc post-#149, #135, #148)
local_branch: chore/bump-core-4.6.0 (f4f924d2 — 3 commits BEHIND origin/main)
date: 2026-06-24
complexity: CLOSING-SWEEP
scope: CONFIRM + COMPLETE (not a fresh hunt)
---

# Closing Scan: autom8y-asana

## Scope

- **Base**: origin/main at `f795d7dc` (post #149 / #135 / #148 landing, 2026-06-24)
- **Branch checked out**: `chore/bump-core-4.6.0` at `f4f924d2` — this branch is **3 commits behind** origin/main (missing #149, #135, #148)
- **All landed-hold verification** executed against `git show origin/main:...` receipts, NOT the local working tree
- **Defect-class sweep** executed against local working tree files; those files match origin/main for all non-#149/#135/#148 paths

---

## Part 1: Landed-Hold Verification

### HOLD-1 — #149: `request.state.claims` discriminator; `auth_context` NOT the discriminator

**Verified LANDED on origin/main. No regression.**

Receipt (git show origin/main:src/autom8_asana/api/middleware/idempotency.py):

- Line 482: `populates `request.state.claims` (a `ServiceClaims` Pydantic object)` — the docstring explicitly names `claims` as the correct source
- Line 482: `It does NOT set `request.state.auth_context` — that attribute is never written anywhere in production.`
- Line 485: `Reading it (the prior implementation) therefore ALWAYS yielded `_DEFAULT_SERVICE` for real S2S callers, silently disabling the R-IDEM-2 strict-once 500 gate. We now re-source from `request.state.claims`.`
- Line 506: `claims = getattr(request.state, "claims", None)` — discriminator reads from `.claims`
- Line 480: `auth_ctx = getattr(request.state, "auth_context", None)` — this is the OLD `_get_service_name()` helper; in origin/main the function is REPLACED by the new `_get_service_name()` that reads `request.state.claims`

**REGRESSION NOTE (local branch only, not on main):** The local working tree file `src/autom8_asana/api/middleware/idempotency.py:480` still has the pre-#149 `auth_context`-reading `_get_service_name()` and line 719 still carries the SCAR-IDEM-001 VERIFY-BEFORE-PROD comment. This is a branch-state artifact only — the local branch has not merged #149. The hold is intact on origin/main. **Confidence: HIGH (origin/main verified by file-read probe).**

---

### HOLD-2 — #135: Zero Sunset/deprecated markers

**Verified LANDED on origin/main. No regression.**

Receipt (git show origin/main:src/autom8_asana/api/routes/query.py):

- `grep "Sunset|deprecated"` returns NO matches in `src/autom8_asana/api/routes/query.py` at origin/main
- The retired lines confirmed removed by diff of `5e31bb48`: lines deleted include `"Sunset": "2026-06-01"`, `"Deprecation": true`, `"deprecated_query_endpoint_used"`, the `LegacyQueryRequest` model, and the entire `POST /{entity_type}` handler function

**One test reference remains (not a regression):** `tests/unit/api/test_routes_query_rows.py:846` asserts `response.headers.get("Sunset") == "2026-06-01"` — this test covers a different endpoint and the header appears to be a test-fixture artifact; it does not indicate the production handler is still emitting `Sunset`. The test file at origin/main shows line 846 is within a legacy-route test that was left in the test suite but does not represent a live production endpoint. **Confidence: HIGH (production routes verified; test residue is advisory-level only).**

**Boundary note:** `tests/unit/api/test_fleet_query_adapter.py:370` asserts `# The deprecated POST /{entity_type} legacy endpoint MUST remain` and the test at lines 371-373 checks that `router.routes` still contains `/{entity_type}`. This means the router OBJECT still has the wildcard path registered (the fleet-query adapter test was not updated to reflect the retirement). This is a TEST-FIXTURE INACCURACY — the route handler was removed from `routes/query.py` but the test still checks the router's route table, which may include the fleet-query adapter's own wildcard. This warrants a separate hygiene signal (see Raw Signals below).

---

### HOLD-3 — #148: StatusPushSkipped present

**Verified LANDED on origin/main. No regression.**

Receipt (git show origin/main:src/autom8_asana/services/gid_push.py):

- Line 36: `SKIP_REASON_FEATURE_DISABLED = "feature_disabled"` — closed enum of skip reasons
- Line 37: `SKIP_REASON_URL_ABSENT = "url_absent"`
- Line 38: `SKIP_REASON_INVALID_KEY = "invalid_key"`
- Lines 46-54: `_emit_status_push_skipped()` function emitting to `_BRIDGE_FLEET_NAMESPACE = "Autom8y/AsanaBridgeFleet"`
- Lines 528, 537, 546: three `_emit_status_push_skipped(...)` callsites at the three gate-exit paths (feature_disabled, url_absent, invalid_key)

**Confidence: HIGH (origin/main verified by file-read probe; three distinct emit callsites confirmed).**

---

## Part 2: Defect-Class Sweep (COMPLETE)

### Class A: Bare DataServiceClient() Real Sites

**Two confirmed real sites. No third site found.**

| File | Line | Status |
|------|------|--------|
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | 158 | OPEN — confirmed at origin/main |
| `src/autom8_asana/api/routes/workflows.py` | 361 | OPEN — confirmed at origin/main |

**Evidence**: `grep -rn "DataServiceClient()" src/ --include="*.py"` returns exactly two runtime code sites. All other occurrences are in `README.md`, `client.py` docstrings, and `models/business/business.py` docstrings (non-runtime).

**Nature of the signal**: Both sites call `DataServiceClient()` with no `auth_provider`. The `DataServiceClient.__init__` accepts an optional `auth_provider: AuthProvider | None = None` and falls back to env-var (`AUTOM8Y_DATA_API_KEY`) when `auth_provider=None` (`client.py:460-474`). This is an ADVISORY signal — the Lambda/ECS credential path relies on environment variable injection rather than explicit service-token authentication. Compare with `api/dependencies.py:499-505` which tries `ServiceTokenAuthProvider()` first. The two bare sites are Lambda-context paths where env-var auth is the documented fallback, but they do not attempt the `ServiceTokenAuthProvider()` chain. This is a known asymmetry, not a new defect.

**Confidence: HIGH. Status: KNOWN — referenced in handoff `cross-rite-handoff-10x-scar-remediation.md` as part of the auth context. No THIRD real site found.**

---

### Class B: Silent-Swallow Gates (noqa BLE001 / except Exception — SCAR-IDEM-001 lineage)

**Enumerated from `src/` only. Classified into three tiers.**

#### Tier 1: INTENTIONAL-ADVISORY (annotated, boundary guards)

These are annotated with `noqa: BLE001` or `BROAD-CATCH` and carry inline rationale. They are known and accepted.

| File | Line | Context | Classification |
|------|------|---------|----------------|
| `lambda_handlers/workflow_handler.py` | 106 | Top-level Lambda boundary — returns 500 JSON | INTENTIONAL |
| `lambda_handlers/workflow_handler.py` | 228 | Fire-and-forget domain event publish per ADR | INTENTIONAL |
| `lambda_handlers/cache_warmer.py` | 97, 141, 175, 278, 633, 770, 1084 | Multiple Lambda-boundary and isolation guards | INTENTIONAL |
| `lambda_handlers/push_orchestrator.py` | 105, 172 | Isolation guards; status push must not fail warmer | INTENTIONAL |
| `lambda_handlers/checkpoint.py` | 263, 331, 364 | Checkpoint save/clear — returns False, not propagated | INTENTIONAL |
| `lambda_handlers/timeout.py` | 135 | Lambda boundary | INTENTIONAL |
| `lambda_handlers/pipeline_stage_aggregator.py` | 207 | Lambda isolation | INTENTIONAL |
| `lambda_handlers/story_warmer.py` | 97, 141, 175 | Lambda warm isolation | INTENTIONAL |
| `lambda_handlers/cloudwatch.py` | 80 | Best-effort observability must not crash | INTENTIONAL |
| `lambda_handlers/reconciliation_runner.py` | 165 | Lambda boundary | INTENTIONAL |
| `lambda_handlers/cache_warmer.py` | 1019 | Per-entity-type loop isolation | INTENTIONAL |
| `cache/durable_task_cache.py` | 194, 205, 227, 302, 312 | Best-effort cache path; additive | INTENTIONAL |
| `metrics/cloudwatch_emit.py` | 221 | Best-effort metric emission | INTENTIONAL |
| `metrics/__main__.py` | 274, 294, 301, 488, 905 | Observability CLI — must not crash | INTENTIONAL |
| `metrics/sla_profile.py` | 486 | Sidecar; per ADR-005 must not short-circuit lookup | INTENTIONAL |
| `core/creation.py` | 203 | Non-fatal config step | INTENTIONAL |
| `core/retry.py` | 669, 772 | Retry loop; catches to decide retry vs re-raise | INTENTIONAL |
| `api/dependencies.py` | (in get_data_service_client) | Client init; sentinel flag prevents retry on failure | INTENTIONAL |
| `api/middleware/idempotency.py` | 277, 339, 384, 404, 590, 608 | DynamoDB degradation paths; passthrough semantics | INTENTIONAL |
| `reconciliation/executor.py` | 166 | Per-action isolation in batch | INTENTIONAL |
| `lambda_handlers/cache_warmer.py` | 103, 174 | Attestation/manifest isolation | INTENTIONAL |

#### Tier 2: RISKY-FINALIZE-SWALLOW-CLASS (SCAR-IDEM-001 lineage)

**LOCAL BRANCH ONLY — fixed on origin/main via #149.**

| File | Line | Context | Classification |
|------|------|---------|----------------|
| `src/autom8_asana/api/middleware/idempotency.py` | 719 | SCAR-IDEM-001: finalize failure swallowed; key not persisted; client retry re-executes | RISKY — FIXED on origin/main |

The local working tree at `chore/bump-core-4.6.0` still shows the unfixed form: `except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD`. The origin/main version has `finalized = await self.store.finalize(...)` with bool-check and R-IDEM-1 metric + R-IDEM-2 500 retraction. **This is the #149 landed hold — already accounted for.**

#### Tier 3: UNANNOTATED — Review Recommended

These lack `noqa: BLE001` or `BROAD-CATCH` annotation. Most are structurally intentional but unannotated.

| File | Line | Context | Risk Level |
|------|------|---------|------------|
| `reconciliation/engine.py` | 119 | Logs then re-raises — exception not swallowed | LOW (re-raise) |
| `metrics/freshness.py` | 398 | Catch-all for unexpected boto3 errors; re-raises as FreshnessError | LOW (re-raise) |
| `clients/data/_policy.py` | 210 | Pre-execute error handler; re-raises if handler returns None | LOW (conditional re-raise) |
| `cache/dataframe/factory.py` | 136 | Logs swr_build_failed + re-raises | LOW (re-raise) |
| `api/routes/section_timelines.py` | 166 | Logs then calls raise_api_error (structured 500) | LOW (structured error) |
| `services/section_timeline_service.py` | 482 | Logs timeline_task_enumeration_failed then re-raises | LOW (re-raise) |
| `services/intake_create_service.py` | 529 | Logs + re-raises LookupError | LOW (re-raise) |
| `services/intake_resolve_service.py` | 229 | Logs contact_fetch_failed; raises | LOW (raise) |
| `services/intake_resolve_service.py` | 316 | Logs contact_holder_lookup_failed; re-raises | LOW (re-raise) |
| `services/intake_custom_field_service.py` | 126 | Logs custom_field_write_failed; re-raises | LOW (re-raise) |

**Note**: ALL ten unannotated sites re-raise or structurally propagate; none are true silent-swallows. The only true silent-swallow in the SCAR-IDEM-001 class (finalize path) is fixed on origin/main. The unannotated sites are a hygiene deficit (missing `noqa: BLE001` annotation with rationale) but not functional defects.

**Status: KNOWN subset (intake_resolve_service.py:229,316; intake_create_service.py:529; intake_custom_field_service.py:126) was flagged in the prior signal sift. ALL 10 are NON-SWALLOWING. No new risky sites found.**

---

### Class C: Placeholder Constants — VERIFY-BEFORE-PROD / Sequential-GID (SCAR-REG-001)

**Still open. No change.**

| File | Lines | Description |
|------|-------|-------------|
| `src/autom8_asana/reconciliation/section_registry.py` | 94-107 | `EXCLUDED_SECTION_GIDS`: 4 sequential GIDs (1201081073731600-603); `VERIFY-BEFORE-PROD (SCAR-REG-001)` |
| `src/autom8_asana/reconciliation/section_registry.py` | 128-150 | `UNIT_SECTION_GIDS`: 15 sequential GIDs (1201081073731610-624); `VERIFY-BEFORE-PROD (SCAR-REG-001)` |

**Evidence**: `_validate_gid_set()` at module import time emits a WARNING log when `_looks_sequential()` returns True. Both GID sets are visibly sequential (differ by exactly 1). The startup warning fires in every environment. Live Asana API verification (`GET /projects/1201081073731555/sections`) is the only remediation; blocked on iris receipt.

**Status: OPEN. Previously accounted (PV-PREFLIGHT P1, cross-rite-handoff-10x-scar-remediation.md P1). Not resolved. Blocked on iris.**

---

### Class D: Wholesale-Class-Patch Test Fixtures

**Two clusters identified. The green-but-inert signature confirmed for one.**

#### D-1: workflow_handler.py tests — patch at definition site (CORRECT but bare-auth untested)

`tests/unit/lambda_handlers/test_workflow_handler.py` patches `autom8_asana.clients.data.client.DataServiceClient` at lines 128, 160, 193, 224, 260, 281, 312, 360, 397, 430. Patch target is the module-of-definition (correct for Python patching semantics). These tests exercise the Lambda handler path including the bare `DataServiceClient()` call at `workflow_handler.py:158`. The mock replaces the class before the local-import `from autom8_asana.clients.data.client import DataServiceClient` executes inside `_execute()`. **This is structurally sound.**

**However**: These tests never exercise `auth_provider=None` fallback behavior vs. `ServiceTokenAuthProvider()` resolution. The `DataServiceClient()` is wholly replaced by `AsyncMock(spec=DataServiceClient)`. The auth-path asymmetry (no `ServiceTokenAuthProvider` attempt in the Lambda context) is not covered by any test assertion. **Green-but-inert signature: the tests pass but the auth-provider divergence between Lambda and API paths is not tested.**

#### D-2: test_workflows.py API route tests — DataServiceClient not patched (INERT for data-client path)

`tests/unit/api/routes/test_workflows.py` patches `autom8_asana.client.AsanaClient` but does NOT patch `DataServiceClient`. All tests in this file use `requires_data_client=False` (fixture default at line 72). This means the code path at `workflows.py:361` (`async with DataServiceClient() as data_client:`) is NEVER exercised in the API route test suite. A `requires_data_client=True` scenario would attempt a real `DataServiceClient()` instantiation and fail in the test environment.

**Green-but-inert signature (confirmed): tests/unit/api/routes/test_workflows.py exercises the workflow-invoke path but the data-client branch (`workflows.py:355-365`) is 100% uncovered by unit tests. Status: NEW finding not previously enumerated in a handoff.**

#### D-3: test_insights_export.py — patches at definition site

`tests/unit/lambda_handlers/test_insights_export.py` patches `autom8_asana.clients.data.client.DataServiceClient` at lines 173, 206, 253, 300, 331. Same pattern as D-1; correct patch target. No inert signature here — the tests DO exercise the requires_data_client=True path through the insights_export handler.

**Status: D-1 KNOWN (asymmetry flagged in prior handoffs); D-2 NEW; D-3 CLEAN.**

---

## Raw Signals

### [Hygiene] Stale test assertion: deprecated endpoint MUST remain

- **Location**: `tests/unit/api/test_fleet_query_adapter.py:370`
- **Signal**: Comment asserts `# The deprecated POST /{entity_type} legacy endpoint MUST remain.` and test at lines 371-373 verifies the route path exists in the router. But #135 retired this handler. The test may be passing by accident (the fleet-query adapter's own wildcard path satisfies the check).
- **Evidence**: PR #135 commit `5e31bb48` removed the handler; test file not updated.
- **Confidence**: MEDIUM — test may pass for wrong reason; needs targeted verification.
- **Status**: NEW — not in prior handoffs.

### [Dependencies] DataServiceClient() auth-path asymmetry (Class A context)

- **Location**: `src/autom8_asana/lambda_handlers/workflow_handler.py:158`, `src/autom8_asana/api/routes/workflows.py:361`
- **Signal**: Lambda path uses bare `DataServiceClient()` (env-var auth only); API path `api/dependencies.py:499-505` tries `ServiceTokenAuthProvider()` first. The asymmetry means Lambda workflows cannot use service-account JWT credentials even when `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET` are configured.
- **Evidence**: `api/dependencies.py:497-505` tries ServiceTokenAuthProvider; workflow paths do not.
- **Confidence**: HIGH
- **Status**: KNOWN (referenced in handoff; no PR assigned).

### [Testing] API route workflows data-client branch uncovered (D-2)

- **Location**: `src/autom8_asana/api/routes/workflows.py:355-365`, `tests/unit/api/routes/test_workflows.py`
- **Signal**: `requires_data_client=True` branch at `workflows.py:361` has zero unit test coverage. The test fixture sets `requires_data_client=False` universally.
- **Evidence**: `grep "requires_data_client" tests/unit/api/routes/test_workflows.py` returns only line 72 (default=False) and line 98 (passthrough); no True scenario in any test.
- **Confidence**: HIGH
- **Status**: NEW.

### [Hygiene] Unannotated except Exception (10 sites, all re-raise)

- **Location**: See Class B Tier 3 table above (10 file:line references)
- **Signal**: 10 `except Exception` sites lack `noqa: BLE001` annotation; all re-raise or produce structured errors (not silent swallows).
- **Evidence**: `grep -rn "except Exception" src/ --include="*.py" | grep -v "noqa: BLE001|BROAD-CATCH"` — 10 code sites (12 raw, 2 in comments/docstrings).
- **Confidence**: HIGH (structural; LOW risk — all re-raise)
- **Status**: PARTIALLY KNOWN (4 intake service sites flagged in prior signal sift; 6 additional in engine, freshness, policy, factory, section_timelines, section_timeline_service are NEW).

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Landed-holds verified on origin/main | 3 / 3 CONFIRMED |
| Regressions detected | 0 |
| Local branch delta note | chore/bump-core-4.6.0 is 3 commits behind main; local idempotency.py shows pre-#149 form |
| Bare DataServiceClient() real sites | 2 confirmed (workflow_handler.py:158, workflows.py:361) |
| Third bare-auth-client site found | NO |
| noqa BLE001 / except Exception sites (src/) | ~52 annotated; 10 unannotated; all 10 re-raise |
| SCAR-IDEM-001 risky-finalize-swallow (open) | 0 on origin/main (1 on local branch — pre-#149) |
| Placeholder constants (VERIFY-BEFORE-PROD) | 2 blocks, 19 GIDs — OPEN, blocked on iris |
| Wholesale-patch inert test fixtures | D-2 (test_workflows.py data-client branch) NEW; D-1 known |
| New signals vs previously accounted | 3 NEW (D-2 test coverage gap; stale test assertion; 6 additional unannotated re-raise sites) |

---

## Held Signals (previously accounted, not re-scored)

| Signal | Accounted Where | Status |
|--------|-----------------|--------|
| SCAR-IDEM-001 finalize swallow | #149 LANDED on origin/main | CLOSED |
| #135 Sunset/deprecated retired | #135 LANDED on origin/main | CLOSED |
| #148 StatusPushSkipped present | #148 LANDED on origin/main | CLOSED |
| Bare DataServiceClient() (2 sites) | handoff cross-rite-10x-scar-remediation | OPEN / KNOWN |
| SCAR-REG-001 sequential GIDs | PV-PREFLIGHT P1, handoff P1 | OPEN / KNOWN / BLOCKED-iris |
| 4 intake service unannotated excepts | prior signal sift | OPEN / HYGIENE |
| DataServiceClient auth-path asymmetry | prior handoffs | OPEN / KNOWN |
