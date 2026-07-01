---
type: review
status: accepted
---

# 10x-idem External-Critic Verdict — W-IDEM / W-REG / AI-2 / AI-3

- **Date:** 2026-06-24
- **Critic:** rite-disjoint external (NOT 10x-dev). Default skeptical; all teeth re-run.
- **Subject:** PR #149 `10x/idem-finalize-contract` @ `5ff6843d`, off `origin/main` `5e31bb48`.
- **Worktree:** `/tmp/wt-10x-idem` (verified HEAD `5ff6843d`, base merge-base `5e31bb48`, tree clean).

## VERDICT: **BLOCKING** — CONCUR WITH QA NO-GO (G-HALT, 1 CRITICAL)

The build is technically clean and the W-IDEM fixture is genuinely two-sided, but the
QA's D-IDEM-CRIT-1 is **independently reproduced and confirmed** — and the production
JWT middleware evidence makes it *stronger* than QA stated. W-IDEM is **dead code in
production**. Do not merge as a landed contract. The fix is sound *given correct
service-name resolution*; the wiring is wrong.

---

## GREEN / RED MATRIX

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | W-IDEM RED fixture genuinely two-sided (not green-only theater) | **GREEN** | Restored HEAD middleware into worktree → `5 failed, 4 passed` (matches engineer's HEAD RED signature). Restored GREEN → `9 passed`. Middleware md5 `8a2c8e86143e10420e844574a4118695` byte-identical pre/post. The 4 HEAD-survivors are the no-defect teeth. |
| 2 | Fix honors HARD caller-propagation (not metric-only) **in production** | **RED** | The 500 path (`idempotency.py:771`) gates on `service_name != _DEFAULT_SERVICE`; `service_name` comes from `_get_service_name` (`:474-486`) which reads `request.state.auth_context` — set by NOTHING in `src/`. Caller-propagation is metric+log only for real callers; the 500 never fires. **D-IDEM-CRIT-1 confirmed.** |
| 3 | PR OPEN / not merged / scoped / no benign-tree contamination | **GREEN** | `state=OPEN`, `mergedAt=null`, `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, exactly 4 files (2 src, 2 test), no stray files. |
| 4 | Rungs not rounded up | **GREEN** | W-IDEM proven-in-fixture / merge-pending (and now inert-in-prod). W-REG `authored`-scaffold (10/10 pass, wired nowhere live — confirmed). AI-3 `authored`/located. AI-2 `diagnosed`, not fixed. No rounding observed. |
| 5 | AI-2 correctly NOT coded as asana fix | **GREEN** | `AUTH-TEB` is asana's OWN inbound JWTAuthMiddleware envelope (`error_responses.py:17,37,41`). insights-export is an OUTBOUND caller → `AUTH-TEB-001` would be autom8y-data rejecting asana → user-sovereign / cross-repo. Correctly no code change. |
| 6 | Conventions (no Co-Authored-By) | **GREEN** | Single commit `5ff6843d`; `git log` body has no Co-Authored-By trailer. ruff/mypy reported clean by engineer (untouched on changed lines). |
| 7 | Regression integrity | **GREEN** | Re-ran in worktree: scar `9 passed`; middleware+reconciliation `191 passed`; W-REG `10 passed`. Matches engineer/QA claims. |

---

## D-IDEM-CRIT-1 — CONFIRMED + STRENGTHENED (CRITICAL / P0 / BLOCKING)

**Independent reproduction (my own construction, not the builder's):** built a prod-representative
app wiring auth as `Depends(get_auth_context)`-style (returns `AuthContext(caller_service=
"autom8y-data")`, does NOT preset `request.state`), monkeypatched `store.finalize → False`,
POSTed a valid `Idempotency-Key`:

```
STATUS: 201  (R-IDEM-2 expects 500)
METRIC dims: {'endpoint': '/v1/intake/business', 'service_name': 'unknown'}
DEFECT-CONFIRMED (got 201 not 500): True
```

**Root cause (three independent confirmations):**
1. **Static:** the only writer of `request.state.auth_context = ` in `src/` + `tests/` is the
   test fixture (`test_idempotency_finalize_scar.py:113`). `src/` has zero.
2. **Architectural:** `get_auth_context` (`dependencies.py:108-244`) RETURNS an `AuthContext`;
   it never assigns `request.state`. It is `Depends`-injected → resolves INSIDE the handler,
   AFTER `IdempotencyMiddleware.dispatch` already computed `service_name` at `:580`.
3. **Empirical:** the repro above.

**STRENGTHENED beyond QA — the verified caller identity WAS available at middleware time, under
a different attribute name.** The fleet `JWTAuthMiddleware` (`autom8y_auth/middleware.py`) DOES
run before idempotency (factory ordering `CORS → JWT → RateLimit → extra_middleware[Idempotency]`,
`_factory.py:25`) and DOES populate `request.state` — but it writes `request.state.claims` /
`request.state.claims_dict` (`middleware.py:209,224,229`), **NOT** `request.state.auth_context`.
The fix read the wrong key. QA's "nothing sets it" understated the seam: something authoritative
sets a *neighboring* key the fix didn't read.

**Fix-path note for principal-engineer + architect:** source `service_name` at middleware time
from `request.state.claims`. BUT honor the `rate_limit.py:25-46` scar — production SA tokens carry
`service_account_id` / `client_id`, NOT a `service_name` JWT claim; `ServiceClaims.service_name`
is a Python `@property` returning `self.sub` (the SA UUID), not a human service name. Any
middleware-side extraction must use the canonical SA fields rate-limiting was already corrected to
use, not `claims.service_name`/`sub`.

**Impact:** every real strict-once S2S caller resolves to `"unknown"` → R-IDEM-4 PAT branch →
201 with unpersisted key on finalize failure → blind-retry → double-execution. The exact R-IDEM-2
defect the PR claims to close. Metric also emits `service_name="unknown"` for all callers
(operator cannot distinguish S2S from PAT).

---

## SECONDARY FLAGS (do not change verdict)

- **Engineer overstated "asana repo has no `*.tf`."** FALSE: `terraform/services/asana/observability_alarms.tf`
  exists in-repo. However it is an *alarms* file, not the IAM grant/env block; the AI-3 remediation
  surface (policy `insights_export_cloudwatch_metrics` + insights_export env block) genuinely lives
  OUTSIDE this repo at `autom8y-wt-golive/terraform/services/asana/main.tf`. AI-3 routing
  conclusion (operator-side IaC, no in-repo asana code) stands; the "no .tf" phrasing is inaccurate.
- **AI-3 root cause consistent with source:** `workflow_handler.py:281-292` emits
  `WorkflowDuration`/`WorkflowSuccessRate` via `emit_metric` with no `namespace=` → defaults to
  `autom8/lambda` (`settings.py:698`), outside the granted `Autom8y/AsanaInsights` set. Preferred
  remediation (set `ASANA_CW_NAMESPACE`, mirroring cache_warmer) is sound.
- **xdist:** I could not run the literal `--dist=loadgroup` either (CodeArtifact 401 offline). Ran
  single-process `-o addopts=""`. Accept QA's UV-P: these ASGI tests are stateless across workers;
  loadgroup is a distribution concern, not correctness. **[UV-P deferred — equivalent single-process
  191 passed.]**

---

## CLEARED TO STRONG

- **W-IDEM fixture two-sidedness** → STRONG (HEAD RED `5/4`, GREEN `9/9`, byte-identical restore).
- **PR hygiene** (open/scoped/clean/no-contamination/conventions) → STRONG.
- **W-REG `authored`-only labeling** → STRONG (zero live callers; 10/10; not proven, correctly so).
- **AI-2 diagnosis** (asana inbound envelope; outbound rejection is cross-repo/user-sovereign) → STRONG.

## NOT CLEARED

- **W-IDEM production guarantee (R-IDEM-2)** → BLOCKED by D-IDEM-CRIT-1. The fix's central HARD
  criterion does not execute for any real caller. Caller-propagation is metric-only in prod.
- **Cross-rite contract note to autom8y-data** → must NOT be announced as live. The promised 500
  is currently inert; data would not see it.

**Acid test — would I be surprised if this fails in production?** No. R-IDEM-2 never runs for real
callers. Confirmed by independent repro. **HALT. CONCUR WITH QA NO-GO.**
