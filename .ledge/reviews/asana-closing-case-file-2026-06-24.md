---
type: review
status: accepted
phase: report
slug: asana-cutover-readiness-closing
upstream: .ledge/reviews/asana-closing-assess-2026-06-24.md
mode: FULL
head_evaluated: origin/main (f795d7dc)
local_branch: chore/bump-core-4.6.0 (3 commits behind origin/main)
date: 2026-06-24
overall_grade: C
construct: CUTOVER-READINESS — legacy→modern cutover production safety, not general tidiness
g_rung_discipline: honored; grades and rungs inherited verbatim from pattern-profiler
---

# Code Review: autom8y-asana — Closing Sweep (Cutover-Readiness Initiative)

**HEAD evaluated**: origin/main f795d7dc | **Local branch**: chore/bump-core-4.6.0 f4f924d2 (3 commits behind) | **Date**: 2026-06-24

---

## Executive Summary

The asana-cutover-readiness initiative closes with substantial progress: all three prior holds (#149 SCAR-IDEM-001 idempotency finalize fix, #135 deprecated-route retirement, #148 StatusPushSkipped metric emission) are **confirmed CLOSED on origin/main**. The service enters the closing sweep in a meaningfully healthier state than it started. However, the initiative cannot declare cutover-ready status because one BLOCKED production-correctness defect remains: **SCAR-REG-001** — 19 sequential placeholder GIDs in `section_registry.py` that have never been verified against the live Asana API, firing a startup WARNING on every deployment and leaving reconciliation routing correctness unverifiable. The overall cutover-readiness grade is **C**, reflecting a mechanical B (two C categories, no floor-drag thresholds hit) overridden to C by Counter-Case discipline because SCAR-REG-001 is structurally BLOCKED-on-auth with no traversable unblock path available today and no CloudWatch alarm on the WARNING it emits. The one action that ends the live BI incident is: **dispatch iris to execute `GET /projects/1201081073731555/sections` and retrieve the live GID receipt** — that single call unblocks W-IRIS, which unblocks the 10x-dev dual-anchor fix, which closes the correctness gate and advances the initiative to cutover-ready.

---

## Cutover-Readiness Report Card

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Complexity | B | No new complexity blockers; `cache_warmer.py` (1437 LOC) is known-deferred and not a cutover gate |
| Testing | C | D-2: `workflows.py:355–365` data-client branch 100% uncovered; D-1 auth-provider divergence untested; stale test assertion `test_fleet_query_adapter.py:370` passes for wrong reason post-#135 |
| Dependencies | B | Two bare `DataServiceClient()` sites use documented env-var fallback; no supply-chain rot or version-mismatch signals in this sweep |
| Structure | B | Reconciliation boundary well-modeled; `section_registry.py` structural design (dedicated registry + startup validation) is correct — the *content* of the constants is unverified, a correctness/hygiene issue, not structural |
| Hygiene | C | SCAR-REG-001 emits WARNING on every startup (19 GIDs, 2 blocks); `VERIFY-BEFORE-PROD` annotations still live; 10 unannotated `except Exception` sites; `query.py` docstring stale post-#135 |
| **Overall** | **C** | Mechanical B overridden to C — SCAR-REG-001 is BLOCKED-on-auth with no traversable unblock path today; startup WARNING fires on every deploy; reconciliation routing correctness unverifiable |

**Grade calculation path (anti-inflation audit, verbatim from pattern-profiler):**
Grades: Complexity=B, Testing=C, Dependencies=B, Structure=B, Hygiene=C.
Mechanical path: median B (3× B vs. 2× C); no F or D categories (no caps fire); 2-of-5 at C does not trigger the 3+ automatic drop rule → mechanical result: **B**.
Override to **C** applied under Counter-Case discipline [AV:SRC-007 Kane 2013 — extrapolation inference: static snapshot underestimates risk when a blocker has no unblock path]: SCAR-REG-001 is BLOCKED-on-auth, fires WARNING on every deployment, and is the construct's primary correctness gate. The mechanical B is recorded here; the C reflects the structural stuck state. [PLATFORM-HEURISTIC: grade override on BLOCKED state rather than count-of-findings is judgment-grounded in Kane 2013 but not a mechanically-derived threshold.]

---

## Metrics Dashboard

| Metric | Value |
|--------|-------|
| HEAD evaluated | origin/main f795d7dc |
| Local branch | chore/bump-core-4.6.0 f4f924d2 (3 commits behind origin/main) |
| Scope | Closing sweep — CONFIRM + COMPLETE (not a fresh hunt) |
| Total residual findings | 10 (1 HIGH open, 3 MEDIUM open, 2 LOW open; 3 CLOSED-LIVE; 1 proven-not-merged) |
| Critical findings | 0 |
| HIGH findings (open) | 1 — SCAR-REG-001, BLOCKED-iris |
| HIGH findings (closed) | 3 — SCAR-IDEM-001 (#149), #135 sunset/deprecated, #148 StatusPushSkipped |
| Production-correctness blockers remaining | 1 (SCAR-REG-001) |
| Test coverage signal | Broad unit suite; data-client branch coverage gap confirmed (D-2) |
| Review mode | FULL |
| Evidence ceiling | MODERATE per G-CRITIC (self-assessed; external corroboration pending) |

---

## Residual Ledger

Every finding from the initiative lifecycle is tagged with its current status, G-RUNG, severity, and routing.

### CLOSED-LIVE — Confirmed on origin/main

| Finding | Closing PR | G-RUNG | Evidence |
|---------|-----------|--------|----------|
| SCAR-IDEM-001: `finalize()` exception swallowed (`idempotency.py:719`) — double-execution risk on S2S retry | #149 (origin/main f795d7dc) | `merged` on main | `git show origin/main:src/autom8_asana/api/middleware/idempotency.py` — bool-check, R-IDEM-1 metric + R-IDEM-2 500 retraction confirmed; pre-#149 form exists only on local branch as branch-state artifact |
| Sunset/deprecated markers retired (`query.py`) — `POST /{entity_type}` handler still live on local branch | #135 (origin/main) | `merged` on main | Scan HOLD-2 receipt: handler removed from `routes/query.py` on origin/main; local branch file is branch-state artifact (3 commits behind) |
| StatusPushSkipped emitting (`gid_push.py:46–54`) — push-seam gate-exit dark | #148 (origin/main) | `merged` on main | `StatusPushSkipped` metric wire-up confirmed on origin/main; prior finding was code-proven absent |

**Operator action required**: Merge `chore/bump-core-4.6.0` locally to pick up #149, #135, and #148. These three fixes are live on origin/main but invisible in local working-tree reads until the local branch is updated. All three go live for the operator simultaneously on merge + deploy.

---

### OPEN / BLOCKED — Requires iris route before unblock is possible

#### H-1: SCAR-REG-001 — Sequential placeholder GIDs at reconciliation routing boundary

- **Location**: `src/autom8_asana/reconciliation/section_registry.py:94–107` (EXCLUDED_SECTION_GIDS, 4 GIDs), `:128–150` (UNIT_SECTION_GIDS, 15 GIDs)
- **Status**: OPEN / BLOCKED-iris
- **G-RUNG**: `proven-in-code-only` — defect is code-confirmed; live-Asana verification is BLOCKED-on-auth (no token-safe iris→Asana route; PAT is Lambda-runtime-only). Cannot round up to `proven` without a live receipt. G-DENOM: absence of receipt is not proof the GIDs are correct.
- **Severity**: HIGH
- **Description**: 19 sequential GID constants (`EXCLUDED_SECTION_GIDS`: 1201081073731600–603; `UNIT_SECTION_GIDS`: 1201081073731610–624) carry `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations. Both blocks are visibly sequential. `_validate_gid_set()` at `:165–166` detects the sequential pattern on every module import and emits `section_registry_gids_appear_fabricated` at WARNING level. If the GIDs are wrong, reconciliation silently misroutes units — tasks enter excluded sections (Templates, Account Error) or active processing sections are silently skipped — with no CloudWatch metric surfacing the mismatch.
- **Production consequence**: Every deployment fires a startup WARNING. Reconciliation routing correctness — the service's primary function — cannot be confirmed until a live API receipt replaces the placeholders.
- **Unblock path**: iris (W-IRIS route build: `GET /projects/1201081073731555/sections`) → 10x-dev (dual-anchor JOIN: live GIDs × monolith name→bucket taxonomy → rebuild `section_registry.py:94–150` with RED-first fixtures) → operator (merge + deploy)
- **Effort**: Blocked on W-IRIS route. Once unblocked: 10x-dev implementation is moderate (~2h + RED-first fixtures).
- **Cross-rite routing**: **iris** (W-IRIS route build, this is the gate) → **10x-dev** (dual-anchor fix) → **operator** (merge + deploy)

---

### OPEN / KNOWN — Tracked; not cutover blockers

#### M-2: Bare `DataServiceClient()` — auth asymmetry, Lambda vs. API paths

- **Location**: `src/autom8_asana/lambda_handlers/workflow_handler.py:158`; `src/autom8_asana/api/routes/workflows.py:361`
- **Status**: OPEN / KNOWN
- **G-RUNG**: `proven` (code-confirmed at both sites)
- **Severity**: MEDIUM
- **Description**: The Lambda path uses bare `DataServiceClient()` (env-var auth only); the API path in `dependencies.py:497–505` tries `ServiceTokenAuthProvider()` first with env-var fallback. Lambda workflows cannot use service-account JWT credentials even when `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET` are configured. The asymmetry is intentional (Lambda env-var fallback is the documented path) but untested.
- **Recommendation**: Either document the asymmetry explicitly with an inline comment, or extend the Lambda path to match `dependencies.py` behavior. Add a test asserting the fallback chain resolves correctly in Lambda context.
- **Effort**: Moderate (~1–2h; design decision required before implementation).
- **Cross-rite routing**: **10x-dev** (M-2; can be addressed in the same sprint as M-1)

---

#### M-1 (D-2): `workflows.py` data-client branch — zero unit test coverage

- **Location**: `src/autom8_asana/api/routes/workflows.py:355–365`; `tests/unit/api/routes/test_workflows.py`
- **Status**: OPEN / NEW (first enumerated in this closing sweep)
- **G-RUNG**: `proven` (code-confirmed — `_make_test_config` defaults `requires_data_client=False`; no `True` scenario in test file)
- **Severity**: MEDIUM
- **Description**: The `requires_data_client=True` branch at `workflows.py:361` has zero unit test coverage. `test_workflows.py:72` sets `requires_data_client=False` universally. The correct pattern is documented in `test_insights_export.py` (patches `DataServiceClient` at import site).
- **Recommendation**: Add a `requires_data_client=True` test variant patching `autom8_asana.clients.data.client.DataServiceClient`.
- **Effort**: Quick fix (~45 min; same patch-pattern as D-3).
- **Cross-rite routing**: **10x-dev** (M-1)

---

#### M-3: Stale test assertion — `test_fleet_query_adapter.py:370`

- **Location**: `tests/unit/api/test_fleet_query_adapter.py:362–374`
- **Status**: OPEN / NEW
- **G-RUNG**: `proven` (test assertion confirmed stale post-#135)
- **Severity**: MEDIUM
- **Description**: `TestLegacyQuerySurfacePreserved.test_legacy_query_router_still_exposes_post_handler` asserts `POST /{entity_type}` MUST remain — the opposite of what #135 accomplished. On origin/main (post-#135), the handler is retired. The test may still pass because other `/{entity_type}/*` routes satisfy the wildcard check, creating a false-positive green signal.
- **Recommendation**: Invert the assertion: `POST /{entity_type}` handler must NOT be present post-retirement. Remove the `MUST remain` comment.
- **Effort**: Quick fix (~30 min).
- **Cross-rite routing**: **10x-dev** or **hygiene** (M-3; combine with M-1 work)

---

### OPEN / LOW PRIORITY

#### L-1: 10 unannotated `except Exception` sites (all re-raise)

- **Location**: `reconciliation/engine.py:119`; `metrics/freshness.py:398`; `clients/data/_policy.py:210`; `cache/dataframe/factory.py:136`; `api/routes/section_timelines.py:166`; `services/section_timeline_service.py:482`; `services/intake_create_service.py:529`; `services/intake_resolve_service.py:229,316`; `services/intake_custom_field_service.py:126`
- **Status**: OPEN / PARTIALLY KNOWN
- **G-RUNG**: `proven` (grep-confirmed; all 10 re-raise or produce structured errors — none are true silent swallows)
- **Severity**: LOW — convention inconsistency only; no functional risk
- **Recommendation**: Add `# noqa: BLE001 — {one-line rationale}` to each of the 10 sites in a single batch PR.
- **Effort**: Quick fix (~20 min; grep + annotation).
- **Cross-rite routing**: **hygiene** (W-HYG; combine with the 185/197 already-annotated mass)

#### L-2: `query.py` module docstring stale post-#135

- **Location**: `src/autom8_asana/api/routes/query.py:7`
- **Status**: OPEN / NEW
- **G-RUNG**: `proven` (doc stale on origin/main post-#135)
- **Severity**: LOW — documentation inconsistency; no functional impact
- **Recommendation**: Update docstring to mark the deprecated route as `REMOVED (retired #135 2026-06-24)` or remove the line.
- **Effort**: Quick fix (1-line edit).
- **Cross-rite routing**: **10x-dev** or **hygiene** (trivial; combine with M-3)

---

## Cross-Rite Routing Recommendations

| Concern | Recommended Rite | Action | Finding |
|---------|-----------------|--------|---------|
| Live Asana GID receipt — the cutover gate | **iris** | Build W-IRIS token-safe route; execute `GET /projects/1201081073731555/sections`; return receipt | H-1 / SCAR-REG-001 |
| Dual-anchor section-registry fix | **10x-dev** | After iris receipt: dual-anchor JOIN (live GIDs × monolith name→bucket); rebuild `section_registry.py:94–150` with RED-first fixtures | H-1 / SCAR-REG-001 |
| Merge local branch to pick up 3 closed PRs | **operator** | Merge `chore/bump-core-4.6.0` → origin/main; deploy to production | SCAR-IDEM-001 / #135 / #148 |
| data-client branch test coverage gap | **10x-dev** | Add `requires_data_client=True` test variant in `test_workflows.py` | M-1 (D-2) |
| Lambda auth-provider asymmetry | **10x-dev** | Document or fix `workflow_handler.py:158` asymmetry vs. `dependencies.py:497–505` | M-2 (D-1) |
| Stale test assertion post-#135 | **10x-dev** / **hygiene** | Invert assertion at `test_fleet_query_adapter.py:370` | M-3 |
| Unannotated broad-except convention gap | **hygiene** | Add `# noqa: BLE001` to 10 sites in a single batch PR | L-1 |
| Stale query.py module docstring | **10x-dev** / **hygiene** | Update docstring at `query.py:7` post-#135 | L-2 |

---

## Recommended Next Steps

Prioritized by impact-to-effort ratio within the cutover-readiness construct:

1. **[Blocking / highest impact] Dispatch iris for live Asana GID receipt.** Execute `GET /projects/1201081073731555/sections` via W-IRIS token-safe route. This is the single gate that unblocks the cutover initiative. Without this receipt, SCAR-REG-001 cannot close and the overall grade cannot advance past C. Route: **iris**.

2. **[Quick / unlocks merge] Merge `chore/bump-core-4.6.0` to origin/main and deploy.** All three closed PRs (#149 SCAR-IDEM-001, #135 deprecated retirement, #148 StatusPushSkipped) are live on origin/main but not deployed until the local branch merges and the Lambda updates. This is the fastest path to getting the closed fixes into production. Route: **operator**.

3. **[Moderate / after iris receipt] 10x-dev: rebuild `section_registry.py` with live GIDs.** Apply dual-anchor JOIN (live GIDs × monolith name→bucket taxonomy); write RED-first fixtures; remove all `VERIFY-BEFORE-PROD` annotations; confirm `_validate_gid_set()` no longer emits WARNING on startup. Route: **10x-dev**.

4. **[Quick / next sprint] Add `requires_data_client=True` test coverage** (`test_workflows.py`). ~45 minutes; same patch pattern as `test_insights_export.py`. Route: **10x-dev**.

5. **[Quick / next sprint] Invert stale test assertion** (`test_fleet_query_adapter.py:370`). ~30 minutes. Route: **10x-dev** or **hygiene**.

6. **[Quick / batch] Annotate 10 unannotated broad-except sites** (`# noqa: BLE001`). ~20 minutes; single PR. Route: **hygiene**.

7. **[Quick / trivial] Update `query.py` module docstring** post-#135. 1-line edit. Route: **10x-dev** or **hygiene**.

---

## What Closes the Initiative

**The initiative closes when SCAR-REG-001 clears its live-Asana verification gate.**

Specifically: iris builds the W-IRIS route and executes `GET /projects/1201081073731555/sections`, returning a receipt with the live GIDs. 10x-dev applies the dual-anchor JOIN to rebuild `section_registry.py:94–150`. On the next deployment, `_validate_gid_set()` no longer emits `section_registry_gids_appear_fabricated`. The startup WARNING goes silent. Reconciliation routing correctness is confirmed.

At that point:
- All three prior holds are CLOSED-LIVE (already done via #149/#135/#148).
- SCAR-REG-001 advances from `proven-in-code-only` to `merged` to `live`.
- The overall grade advances mechanically from C to B (two C categories become one, the 3+ drop rule does not fire, the BLOCKED override no longer applies).
- The initiative is cutover-ready at the B advisory threshold.

The path to A (cutover-ready with full observability) additionally requires M-1 test coverage and an SRE alarm wired to the `section_registry_gids_appear_fabricated` WARNING metric once GIDs are live — but B is the cutover gate.

**The one action that ends the live BI incident today**: build the iris W-IRIS route and run `GET /projects/1201081073731555/sections`.

---

## Key Patterns Identified

**Pattern 1: Silent-by-default failure mode at production boundaries.** SCAR-IDEM-001, #148, and SCAR-REG-001 all share the same structural character — the system degrades or routes incorrectly without emitting an observable error or metric, only a log WARNING at best. The prior holds addressed SCAR-IDEM-001 and #148. SCAR-REG-001 remains in this failure mode. The architectural norm of emitting a named CloudWatch metric (not just a log line) at every gate-exit and failure path would prevent recurrence.

**Pattern 2: Test fixture completeness gap at the `requires_data_client` fork.** Both D-1 and D-2 represent the same structural gap: the `True/False` fork is exercised in production but the `True` path is either uncovered (D-2 for API routes) or tested via wholesale mock replacement that bypasses auth-provider behavior (D-1 for Lambda handlers). `test_insights_export.py` demonstrates the correct pattern. This is a test-design consistency failure across the three files covering this config.

**Pattern 3: Post-retirement stale artifact accumulation.** M-3 (stale test assertion) and L-2 (stale docstring) are both artifacts of #135's retirement cleaning the production code but leaving test and documentation referencing the retired behavior. Individually low-severity; aggregates into false-positive green noise over time.

**Pattern 4: Branch-state masking of origin/main health.** The local branch being 3 commits behind origin/main caused several CLOSED findings to appear re-opened in local file reads. The scan's `git show origin/main:...` HEAD-disambiguation discipline is load-bearing and must be preserved as a review convention for any future sweep.

---

## Evidence Discipline

All findings in this report are inherited verbatim from pattern-profiler (`asana-closing-assess-2026-06-24.md`). No severity has been re-graded by case-reporter. G-RUNG rungs are named per the profiler's assessment and are never rounded up. The G-DENOM constraint applies throughout: absence of a live receipt is not proof the GIDs are correct; absence of telemetry signal is not proof of zero activity.

Self-assessed confidence is capped at MODERATE per G-CRITIC discipline. External corroboration is pending for the HIGH finding (SCAR-REG-001).

---

*Review mode: FULL | Generated by review rite — case-reporter | HEAD: origin/main f795d7dc (evaluated) / chore/bump-core-4.6.0 f4f924d2 (local) | 2026-06-24*
*G-RUNG honored throughout. G-DENOM honored throughout. Grade: C (mechanical B; Counter-Case override documented).*
