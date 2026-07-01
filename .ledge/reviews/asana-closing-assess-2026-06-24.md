---
type: review
status: accepted
scan_artifact: .ledge/reviews/asana-closing-scan-2026-06-24.md
head_evaluated: origin/main (f795d7dc) — all landed-hold verification against origin/main
local_branch_note: chore/bump-core-4.6.0 is 3 commits behind; pre-#149/135/148 local files are branch artifacts, not main regressions
construct: CUTOVER-READINESS — production-readiness for the legacy→modern cutover, not general tidiness
date: 2026-06-24
profiler: pattern-profiler
g_rung_discipline: honored throughout; rungs named, not rounded up
g_denom_discipline: honored; no findings upgraded on absence-of-evidence
---

# Assessment: autom8y-asana — Closing Sweep 2026-06-24

> **Construct validity caveat (applies to all grades):**
> These grades measure *cutover-readiness* — can this service carry production
> reconciliation and workflow traffic after the legacy monolith cutover without
> silent correctness failures or unobservable failure modes? They do NOT measure
> general code tidiness, style completeness, or test thoroughness in the
> abstract. A C-grade does not mean the codebase is poorly written; it means
> one or more correctness/observability blockers stand between HEAD and a safe
> cutover. [AV:SRC-001 Messick 1989 — construct validity: every grade operationalizes
> a declared construct; grades without a declared construct have no validity argument]
> [STRONG | 0.72 @ 2026-03-31]

---

## Health Grades (Cutover-Readiness Construct)

| Category | Grade | Rationale |
|----------|-------|-----------|
| Complexity | B | No new complexity blockers; `cache_warmer.py` (1437 LOC) is known-deferred; all other core service files are well within bounds. |
| Testing | C | D-2 confirmed: `workflows.py:355–365` data-client branch is 100% uncovered; D-1 auth-provider divergence untested; stale test assertion at `test_fleet_query_adapter.py:370` passes for wrong reason post-#135. Three test-quality gaps, one with correctness implications. |
| Dependencies | B | Two bare `DataServiceClient()` sites (Class A) use documented env-var fallback; known asymmetry vs. API path; no supply-chain rot or version-mismatch signals in this sweep. |
| Structure | B | Reconciliation boundary is well-modeled; `section_registry.py` is correctly isolated as the single source-of-truth per REVIEW-reconciliation-deep-audit TC-2. Structure grades B despite SCAR-REG-001 because the structural design (a dedicated registry module with startup validation) is correct — the *content* of the constants is unverified, which is a correctness/hygiene issue, not a structural one. |
| Hygiene | C | SCAR-REG-001 sequential-placeholder GIDs emit a WARNING on every startup (19 GIDs, 2 blocks); 10 unannotated `except Exception` sites; stale `VERIFY-BEFORE-PROD` annotations remain; query.py module-level docstring still describes the deprecated POST route as present. |
| **Overall** | **C** | Median across five categories is B/C boundary. Two C categories and one standing BLOCKED production-correctness defect (SCAR-REG-001) pull the overall to C. No D or F; weakest-link caps do not fire. The single most important residual is SCAR-REG-001 — every deployment fires a startup WARNING, reconciliation routing correctness is unverified, and the unblock is BLOCKED-on-auth (no iris→Asana route exists). |

### Grade Calculation Path (Anti-Inflation Audit)

Grades: Complexity=B, Testing=C, Dependencies=B, Structure=B, Hygiene=C.
Median: B (three B-grades vs. two C-grades → median is B).
Floor-drag check: no F categories (no cap to D), no D categories (no cap to C).
3+ C-or-below check: two C categories — does NOT trigger the 3+ drop rule.
Result by anchors: median B, no floor-drag fires → **Overall: B**.

**Override rationale (Counter-Case application):** The weakest-link model in its
mechanical form would yield B. However, SCAR-REG-001 is a standing production-
correctness defect that fires a WARNING log on every startup, is BLOCKED-on-auth
for its unblock path, and is the construct's primary cutover gate. The Testing=C
grade is driven partly by the data-client branch coverage gap which touches the
same workflow paths that SCAR-REG-001 affects. Applying the counter-case
calibration anchor [AV:SRC-007 Kane 2013 — extrapolation inference: a static
snapshot grade underestimates risk when blockers have no unblock path]: the
overall grade is adjusted to **C** to surface that one blocker is structurally
stuck, not merely pending work. This adjustment is documented here, not silently
applied — the mechanical B is noted; the C reflects the BLOCKED-on-auth state of
the highest-priority blocker. [PLATFORM-HEURISTIC: grade override on BLOCKED state
rather than count-of-findings is a judgment call grounded in Kane 2013 extrapolation
inference but not a mechanically-derived threshold.]

---

## Validated Findings

### Critical

*None. No findings at Critical severity in this sweep.*

---

### High

#### H-1: SCAR-REG-001 — Sequential placeholder GIDs at reconciliation routing boundary

- **Location**: `src/autom8_asana/reconciliation/section_registry.py:94–107` (EXCLUDED_SECTION_GIDS, 4 GIDs), `:128–150` (UNIT_SECTION_GIDS, 15 GIDs)
- **Description**: 19 sequential placeholder GIDs annotated `VERIFY-BEFORE-PROD (SCAR-REG-001)` have never been verified against the live Asana API. On every module import, `_validate_gid_set()` at lines 165–166 detects the sequential pattern and emits `section_registry_gids_appear_fabricated` at WARNING level. If the GIDs are wrong, reconciliation silently misroutes units — tasks processed under excluded sections (Templates, Account Error) or skipped when active processing sections are unmatched — with no CloudWatch metric surfacing the mismatch.
- **Evidence confirmed**: Direct read of `section_registry.py:94–107` and `:128–150` — EXCLUDED set `{1201081073731600..603}`, UNIT set `{1201081073731610..624}`, both visibly sequential, both carrying `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations. `_validate_gid_set()` confirmed present at `:165–166`.
- **G-RUNG**: `proven-in-code-only` — defect is code-confirmed; live-Asana verification is BLOCKED-on-auth (no token-safe iris→Asana route; PAT is Lambda-runtime-only).
- **G-DENOM**: Absence of live GID receipt cannot be rounded up to "probably correct." The rung is `proven-in-code-only`, not `proven`.
- **Severity**: HIGH — correctness risk at reconciliation routing boundary; silent failure mode; every deployment fires WARNING.
- **Recommendation**: Build the token-safe iris→Asana route (W-IRIS per adjudicated plan), obtain live receipt from `GET /projects/1201081073731555/sections`, then apply the dual-anchor JOIN design (live GIDs × monolith name→bucket taxonomy) to rebuild `section_registry.py:94–150`. Do not GID-match without the dual-anchor join; that re-introduces silent miscategorization.
- **Effort**: Significant — blocked on W-IRIS route build (operator/platform-ops action); once unblocked, 10x-dev implementation is moderate (~2h + RED-first fixtures).
- **Cross-rite routing**: iris (W-IRIS route build) → 10x-dev (dual-anchor fix + RED-first fixtures) → operator (merge + deploy)

---

#### H-2: SCAR-IDEM-001 — Idempotency `finalize()` exception swallowed (LOCAL BRANCH ONLY; CLOSED on origin/main)

- **Location**: `src/autom8_asana/api/middleware/idempotency.py:719` — LOCAL BRANCH `chore/bump-core-4.6.0` only
- **Description**: On the local branch (pre-#149), `DynamoDBIdempotencyStore.finalize()` is wrapped in a bare `except Exception` that logs and swallows the exception; the idempotency key is not persisted; a client retry re-executes the mutation. No CloudWatch error metric emitted on this path.
- **Evidence confirmed**: The local branch file at `:719` shows `except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD` — pre-#149 form confirmed. Origin/main has the fix: `finalized = await self.store.finalize(...)` with bool-check and R-IDEM-1 metric + R-IDEM-2 500 retraction (scan HOLD-1 receipt, lines 30–36).
- **G-RUNG on origin/main**: `merged` — fix is live on origin/main. The local branch carries the pre-fix form as a branch-state artifact.
- **Severity**: HIGH for S2S strict-once callers — **but CLOSED on origin/main**. This finding is included in the ledger with CLOSED status to maintain audit continuity.
- **Action required**: Merge `chore/bump-core-4.6.0` to pick up #149 (already landed on main). No separate fix needed; the fix is live.
- **Cross-rite routing**: operator (merge local branch to pick up #149 / #135 / #148)

---

### Medium

#### M-1: D-2 — `workflows.py` data-client branch uncovered by unit tests

- **Location**: `src/autom8_asana/api/routes/workflows.py:355–365`; `tests/unit/api/routes/test_workflows.py`
- **Description**: The `requires_data_client=True` branch at `workflows.py:361` (the `async with DataServiceClient() as data_client:` context manager) has zero unit test coverage. The test fixture at `test_workflows.py:72` sets `requires_data_client=False` universally; no `True` scenario exists in the test file. A test that exercises this path would fail in the test environment without proper mocking, meaning the branch was written but never given a test harness.
- **Evidence confirmed**: Direct read of `test_workflows.py:70–103` — `_make_test_config` defaults `requires_data_client=False`; `grep "requires_data_client=True"` returns zero hits in this test file.
- **G-RUNG**: NEW finding — not in prior handoffs; first enumerated in this closing scan.
- **Severity**: Medium — correctness gap (the code path exists in production; the test gap means any regression in the data-client path goes undetected), but not an immediate production correctness failure on its own.
- **Recommendation**: Add a `requires_data_client=True` test variant that patches `DataServiceClient` at the import site (`autom8_asana.clients.data.client.DataServiceClient`) and asserts the context manager is entered and the workflow receives the `data_client` argument.
- **Effort**: Quick fix (~45 min; same patch-pattern as D-3 `test_insights_export.py` which handles this correctly).
- **Cross-rite routing**: 10x-dev (test coverage gap; add alongside W-OBS or W-IDEM work)

#### M-2: D-1 — Auth-provider divergence between Lambda and API paths untested

- **Location**: `src/autom8_asana/lambda_handlers/workflow_handler.py:158`; `src/autom8_asana/api/routes/workflows.py:361`; `src/autom8_asana/api/dependencies.py:497–505`
- **Description**: The Lambda path uses bare `DataServiceClient()` (env-var auth only); the API path in `dependencies.py:497–505` tries `ServiceTokenAuthProvider()` first, falling back to env-var. Lambda workflows cannot use service-account JWT credentials even when `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET` are configured. The test suite (`test_workflow_handler.py`) replaces `DataServiceClient` entirely with `AsyncMock(spec=DataServiceClient)`, so the auth-path asymmetry is never tested.
- **Evidence confirmed**: Direct read of `workflow_handler.py:155–165` (bare `DataServiceClient()`); `dependencies.py:490–510` (`ServiceTokenAuthProvider()` attempt → env-var fallback); confirmed the test mock at `test_workflow_handler.py` patches the class before instantiation.
- **Severity**: Medium — known asymmetry with a documented rationale (Lambda env-var fallback is the documented path), but the JWT credential path is silently unavailable for Lambda callers even when configured.
- **Recommendation**: Either document the asymmetry explicitly in the Lambda handler (inline comment stating JWT auth is not attempted and why), or add `ServiceTokenAuthProvider()` fallback to the Lambda path matching `dependencies.py` behavior. Add a test asserting the fallback chain resolves correctly in Lambda context.
- **Effort**: Moderate — design decision required (document vs. fix) before implementation; estimate 1–2h once decision is made.
- **Cross-rite routing**: 10x-dev (KNOWN; tracked in cross-rite-handoff-10x-scar-remediation.md — can be addressed in the same sprint as M-1)

#### M-3: Hygiene — Stale test assertion; deprecated endpoint MUST remain (test_fleet_query_adapter.py:370)

- **Location**: `tests/unit/api/test_fleet_query_adapter.py:362–374`
- **Description**: `TestLegacyQuerySurfacePreserved.test_legacy_query_router_still_exposes_post_handler` contains the assertion `# The deprecated POST /{entity_type} legacy endpoint MUST remain.` and asserts `any("/{entity_type}" in (p or "") for p in legacy_paths)`. PR #135 retired this handler from `routes/query.py`. The test may still pass because (a) the local branch has not merged #135 yet, or (b) the fleet-query adapter's own wildcard path satisfies the `/{entity_type}` check. On origin/main (post-#135), the `POST /{entity_type}` handler is removed from `routes/query.py`, but the `/{entity_type}/rows` and `/{entity_type}/aggregate` routes still exist and could satisfy the wildcard check.
- **Evidence confirmed**: Direct read of `test_fleet_query_adapter.py:362–374` — assertion comment and route-path check confirmed verbatim. On the local branch, `query.py:748` still has the `POST /{entity_type}` handler (branch-state artifact). On origin/main (post-#135), per scan HOLD-2, the handler was removed.
- **Severity**: Medium — false-positive test passing for wrong reason; the test no longer reflects the intended contract post-#135 and does not catch a regression on the retired path.
- **Recommendation**: Update the test class to assert the opposite: `POST /{entity_type}` handler must NOT be present in the legacy query router post-retirement. Or convert to a `test_retired_endpoints_removed` assertion. Remove the `MUST remain` comment.
- **Effort**: Quick fix (~30 min; targeted test update).
- **Cross-rite routing**: 10x-dev (hygiene/test update; low priority, combine with M-1 work)

---

### Low

#### L-1: 10 unannotated `except Exception` sites (all re-raise)

- **Location**: `reconciliation/engine.py:119`, `metrics/freshness.py:398`, `clients/data/_policy.py:210`, `cache/dataframe/factory.py:136`, `api/routes/section_timelines.py:166`, `services/section_timeline_service.py:482`, `services/intake_create_service.py:529`, `services/intake_resolve_service.py:229,316`, `services/intake_custom_field_service.py:126`
- **Description**: 10 `except Exception` sites in `src/` lack the `noqa: BLE001` annotation that is the codebase convention for intentional broad-catch. All 10 re-raise or produce structured errors (none are true silent swallows). The only true swallow in the SCAR-IDEM-001 class is closed on origin/main.
- **Evidence confirmed**: Scan Class B Tier 3 enumeration; all sites reviewed — all re-raise paths confirmed.
- **Severity**: Low — no functional risk; convention inconsistency only.
- **Recommendation**: Add `# noqa: BLE001 — {one-line rationale}` to each of the 10 sites. Batch task; can be done in a single PR.
- **Effort**: Quick fix (~20 min; grep + annotation).
- **Cross-rite routing**: hygiene rite (W-HYG per adjudicated plan; combine with the 185/197 already-annotated mass)

#### L-2: query.py module docstring still describes deprecated route as present

- **Location**: `src/autom8_asana/api/routes/query.py:7`
- **Description**: The module-level docstring lists `POST /v1/query/{entity_type} - Legacy query with flat equality filtering (deprecated, sunset 2026-06-01)` as an active route. On origin/main post-#135, this handler was retired. The docstring is stale on origin/main; on the local branch it is still accurate (handler present).
- **Evidence confirmed**: Direct read of `query.py:1–15` — the deprecated route description is present in the docstring header.
- **Severity**: Low — documentation inconsistency; no functional impact.
- **Recommendation**: Update module docstring to mark the deprecated route as `REMOVED (retired #135 2026-06-24)` or remove the line.
- **Effort**: Quick fix (1-line edit).
- **Cross-rite routing**: 10x-dev or hygiene (trivial; combine with M-3 test update)

---

## Patterns Identified

### Pattern 1: Silent-by-default failure mode at every production boundary

All three prior holds (SCAR-IDEM-001, #135 sunset markers, #148 StatusPushSkipped) and SCAR-REG-001 share a common theme: the system fails silently rather than loudly. The finalize swallow had no metric; the deprecated route emitted no counter for callers; the push-seam emitted no metric when skipped; the placeholder GIDs emit a WARNING (not an ERROR or alarm) and then proceed. The codebase has a structural tendency to prefer silent degradation at boundary transitions. This is partially intentional (best-effort semantics for additive paths like cache and metrics emission) but has bled into correctness-critical paths (idempotency finalize, reconciliation routing). The pattern was addressed by #149 and #148 but the GID registry remains in this failure mode.

### Pattern 2: Test fixture completeness gap at the Lambda/requires_data_client fork

Both D-1 and D-2 are variations of the same structural gap: the `requires_data_client=True/False` fork in `WorkflowHandlerConfig` is exercised in production code but the `True` path is either never tested (D-2 for API routes) or tested via wholesale mock replacement that cannot exercise auth-provider behavior (D-1 for Lambda handlers). The D-3 case (`test_insights_export.py`) shows the correct pattern. The gap is a test-design consistency failure across the three test files that cover this config.

### Pattern 3: Post-retirement stale artifacts accumulate

M-3 (`test_fleet_query_adapter.py:370` stale assertion) and L-2 (query.py docstring) both represent the pattern where a retirement (PR #135) cleaned the production code but left test assertions and documentation referencing the retired behavior. This pattern is low-severity individually but aggregates into test suites where `MUST remain` assertions become false-positive green noise.

### Pattern 4: Branch-state artifacts masking origin/main health

The local branch `chore/bump-core-4.6.0` is 3 commits behind origin/main. Several findings that appear present in local file reads (SCAR-IDEM-001 at `idempotency.py:719`, `POST /{entity_type}` handler in `query.py`) are actually resolved on origin/main. The scan correctly disambiguated these via `git show origin/main:...` probes. Any future sweep operating only against the local working tree would incorrectly re-open CLOSED findings. The mitigation is the scan's explicit HEAD-disambiguation discipline, which should be preserved as a review convention.

---

## Residual Ledger (Full)

| Finding | Status | G-RUNG | Severity | Routing |
|---------|--------|--------|----------|---------|
| SCAR-IDEM-001: finalize swallow (idempotency.py:719) | CLOSED-LIVE (#149 on origin/main) | `merged` on main | — | operator: merge local branch |
| #135: Sunset/deprecated markers retired (query.py) | CLOSED-LIVE (#135 on origin/main) | `merged` on main | — | operator: merge local branch |
| #148: StatusPushSkipped emitting (gid_push.py:46–54) | CLOSED-LIVE (#148 on origin/main) | `merged` on main | — | operator: merge local branch |
| **SCAR-REG-001: sequential placeholder GIDs (section_registry.py:94–107, :128–150)** | **OPEN / BLOCKED-iris** | `proven-in-code-only` | **HIGH** | iris (W-IRIS route) → 10x-dev (dual-anchor fix) |
| Bare DataServiceClient() (workflow_handler.py:158, workflows.py:361) | OPEN / KNOWN | `proven` (code-confirmed) | MEDIUM (auth asymmetry advisory) | 10x-dev (M-2) |
| D-2: test_workflows.py data-client branch 100% uncovered | OPEN / NEW | `proven` (code-confirmed) | MEDIUM | 10x-dev (M-1) |
| D-1: test_workflow_handler.py auth-provider divergence untested | OPEN / KNOWN | `proven` (code-confirmed) | MEDIUM | 10x-dev (M-2) |
| Stale test assertion test_fleet_query_adapter.py:370 | OPEN / NEW | `proven` (code-confirmed) | MEDIUM | 10x-dev / hygiene (M-3) |
| 10 unannotated except Exception sites (all re-raise) | OPEN / PARTIALLY KNOWN | `proven` (code-confirmed) | LOW | hygiene (L-1, W-HYG) |
| query.py docstring stale re: deprecated route | OPEN / NEW | `proven` (code-confirmed) | LOW | 10x-dev / hygiene (L-2) |

---

## Cross-Rite Routing Recommendations

| Finding | Target Rite | Trigger Signal | G-RUNG at Route Time |
|---------|-------------|----------------|----------------------|
| SCAR-REG-001 live-receipt | **iris** (W-IRIS route build) | No token-safe iris→Asana route; PAT is Lambda-runtime-only; BLOCKED-on-auth, not merely pending | `proven-in-code-only` → `proven` requires live receipt |
| SCAR-REG-001 dual-anchor fix + RED-first fixtures | **10x-dev** | After iris receipt lands; dual-anchor JOIN (live GIDs × monolith name→bucket); `section_registry.py:94–150` rebuild | `proven` → `merged` (USER-SOVEREIGN) |
| D-2 data-client branch test coverage (M-1) | **10x-dev** | `workflows.py:355–365` zero unit coverage; `test_workflows.py` has no `requires_data_client=True` scenario | `proven` (gap confirmed) |
| D-1 auth-provider divergence (M-2) | **10x-dev** | Lambda bare `DataServiceClient()` vs. API `ServiceTokenAuthProvider()` attempt; untested asymmetry | `proven` (design decision pending) |
| Stale test assertion (M-3) | **10x-dev** | `test_fleet_query_adapter.py:370` asserts retired endpoint MUST remain; passes for wrong reason | `proven` (test stale post-#135) |
| 10 unannotated broad-except sites (L-1) | **hygiene** | Convention gap: 185/197 annotated; 10 unannotated in engine/services/clients | `proven` (grep-confirmed) |
| query.py docstring stale (L-2) | **hygiene** or **10x-dev** | Module docstring lists retired handler as present post-#135 | `proven` (doc stale post-#135) |
| Merge local branch to pick up #149/#135/#148 | **operator** | `chore/bump-core-4.6.0` is 3 commits behind origin/main; pre-fix forms visible in local working tree | `merged` on main; `live` requires operator action |

---

## False Positives Dismissed

| Signal | Dismissal Reason |
|--------|-----------------|
| Third bare `DataServiceClient()` site (Class A) | Not found. `grep -rn "DataServiceClient()" src/ --include="*.py"` returns exactly 2 runtime sites; other occurrences are in docstrings/README (non-runtime). Signal correctly absent. |
| SCAR-IDEM-001 open on origin/main | False positive for origin/main assessment context. Local branch shows pre-#149 form but origin/main is fixed. Scan disambiguated correctly via `git show origin/main:...` probe; local branch state is branch-state artifact only. |
| Class B Tier 1 annotated broad-except sites (~52 sites) | All carry `noqa: BLE001` or `BROAD-CATCH` annotations with inline rationale. They are intentional boundary guards consistent with the Lambda best-effort degradation pattern documented in ADR-005. Not scored as findings. |
| D-3 `test_insights_export.py` | Scan correctly assessed as CLEAN. Patches at definition site; exercises `requires_data_client=True` path. No inert signature. Not a finding. |

---

## Coverage Gaps

No significant coverage gaps detected that would trigger a back-route to signal-sifter. The closing sweep was scoped to CONFIRM + COMPLETE (not a fresh hunt), and that scope was honored. The following are noted as boundary observations, not gaps requiring re-scan:

- **Bridge-fleet dark window** (`Autom8y/AsanaBridgeFleet :: LastSuccessTimestamp` frozen at 2026-06-18T13:32:06; no datapoints 2026-06-19…24): this is an SRE/iris observability investigation (W-BRIDGE per adjudicated plan), not a code-scan signal. The structural explanation (push-seam gate-absence when `AUTOM8Y_DATA_URL` absent) is noted in the handoff; the env-config state in production is UNVERIFIABLE from code alone. [G-DENOM: absence of telemetry is not proof of zero activity; route to sre + iris for denominator establishment.]
- **W-FORK1 (`/v1/query` retire-vs-extend decision)**: requires CloudWatch Logs Insights probe (`deprecated_query_endpoint_used` since 2026-06-01); not resolvable from static code scan. Route to iris per adjudicated plan.
- **`.know/` corpus drift (90-commit drift)**: route to `know` rite (W-KNOW per adjudicated plan); not a code-scan finding.

**Back-route decision**: NOT triggered. No coverage gaps require signal-sifter re-scan. Identified gaps are SRE/iris/know-rite work items already routed in the adjudicated execution plan.

---

## Overall Cutover-Readiness Verdict

**Grade: C**

The autom8y-asana service is NOT yet production-ready for a safe legacy→modern cutover. The single load-bearing blocker is **SCAR-REG-001** — 19 sequential placeholder GIDs in `section_registry.py` that have never been verified against the live Asana API. Every deployment fires a startup WARNING. Reconciliation routing correctness (the service's primary function) cannot be confirmed until the W-IRIS route provides a live receipt.

All three prior holds (#149 SCAR-IDEM-001, #135 Sunset/deprecated, #148 StatusPushSkipped) are **CONFIRMED CLOSED on origin/main**. The codebase improved substantially through this review cycle. The C grade reflects the one remaining BLOCKED correctness blocker, not a wholesale failure.

The path to B (cutover-ready advisory) is: W-IRIS live receipt → W-REG dual-anchor fix → operator merge + deploy. The path to A (cutover-ready with full observability) additionally requires W-IDEM RED-first fixtures, M-1 test coverage, and SRE alarm wiring (W-BRIDGE, alarm on SCAR-REG-001 WARNING metric once GIDs are live).

*Pattern-profiler | 2026-06-24 | HEAD: origin/main f795d7dc (evaluated) / chore/bump-core-4.6.0 f4f924d2 (local)*
*G-RUNG honored throughout. G-DENOM honored throughout. No findings rounded up.*
*Evidence ceiling: [MODERATE] per G-CRITIC — self-assessed; external corroboration PENDING for HIGH findings.*
