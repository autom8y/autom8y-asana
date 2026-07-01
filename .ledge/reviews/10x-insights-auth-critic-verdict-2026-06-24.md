---
type: review
status: accepted
---

# W-AUTH Secret-Resolution Fix — Rite-Disjoint External Critic Verdict

- **Date:** 2026-06-24
- **Critic:** rite-disjoint external (NOT 10x-dev; adversarial, default-skeptical)
- **Subject:** PR #151 `fix/w-auth-secret-resolution` (commit `ec975e7c`)
- **Precedent guarded:** #149 (green-but-inert: tests pass against synthetic wiring, prod stays dark)
- **Verdict:** **CONCUR-WITH-FLAGS** — GO for PR #151 at the code/contract altitude. One pre-existing sibling defect confirmed and escalated (non-blocking). One operator-gated live attestation remains open (correctly not closed).

---

## GREEN / RED matrix

| # | Check | Result | Evidence (re-reproduced by critic) |
|---|-------|--------|-------------------------------------|
| 1 | RED fixture drives PRODUCTION entrypoint (not synthetic) | **GREEN** | Test calls real `create_workflow_handler(...)` -> `handler({}, ctx)` -> `asyncio.run(_handler_async)` -> `_execute` -> real `DataServiceClient(auth_provider=...)` at workflow_handler.py:175. Spy shims only `__init__` via `patch.object(DataServiceClient,"__init__",...)`; class identity / `async with` dunders / `_get_auth_token` stay REAL. NOT the #149 wholesale-class-patch. |
| 1a | Two-sided RED->GREEN re-proven by critic | **GREEN** | I reverted both source files to `origin/main` byte-state (defect re-injected), kept tests at fix-state: **2 failed** — AC-1 `AssertionError: W-AUTH regression ... auth_provider`; AC-2 `AttributeError: ... does not have the attribute 'resolve_secret_from_env'`. Restored fix byte-exact (empty diff vs HEAD): **2 passed**. |
| 2 | Secret resolution actually correct — valid bearer at runtime, not unresolved ARN/null | **GREEN** | `resolve_secret_from_env` (autom8y_config.lambda_extension) Strategy 1: `{name}_ARN` present -> `resolve_secret_arn(arn)` returns the resolved SECRET VALUE (not the ARN string); Strategy 2: bare `{name}` (ECS/local). Value flows into `Config(client_secret=...)` -> `TokenManager` -> `get_secret()` returns `get_token()` JWT -> `Authorization: Bearer {jwt}` at client.py:439. Secret does NOT stay null/ARN at runtime. |
| 2a | `RuntimeError` (extension failure) propagates honestly | **GREEN** | Fix narrows ONLY `ValueError` (absent secret) at service_token.py:59-62. `RuntimeError` (extension HTTP failure) propagates -> top-level 500, not silent no-credential degrade. |
| 3 | Code-vs-IaC-vs-operator split honest | **GREEN** | CODE: 5 files only (2 src + 1 new test + 2 autouse fixtures). PR #151 OPEN, not merged, base `main`, MERGEABLE/CLEAN, headRefOid `ec975e7c`. NO monorepo PR exists (verified via `gh` + worktree list). |
| 3a | IaC claim (QA deferred as UV-P) — RESOLVED by critic | **GREEN (upgraded from UV-P)** | Monorepo IS local. `terraform/services/asana/main.tf:1860-1864`: insights_export `enable_secrets_extension=true`, `secret_arns={ SERVICE_CLIENT_SECRET = ...service_client_secret.arn, ... }`. conversation_audit identical @1788-1790. Sibling local modules `scheduled-lambda`/`event-driven-lambda` (main.tf:120 / :110) rename keys `{ for k,v : "${k}_ARN" => v }` -> env `SERVICE_CLIENT_SECRET_ARN`. **CAVEAT:** insights_export uses REMOTE pinned module `service-lambda-scheduled?ref=v1.0.2` (a8.git), not the local module — the `_ARN` rename in the deployed module is STRONG-inferred from local siblings + variable docs, not directly inspected. Immaterial to code GO: the fix is correct on BOTH topologies (Strategy 1 `_ARN` / Strategy 2 bare). |
| 4 | Rungs not rounded up | **GREEN** | W-AUTH is proven-fixture, NOT incident-closed. `succeeded>0` live run correctly remains operator-gated `[UNATTESTED — DEFER-POST-HANDOFF]`. Autouse fixtures in the two existing tests no-op ONLY `ServiceTokenAuthProvider.__init__` and explicitly disclaim the auth contract (owned solely by the new contract test). |

### Regression / lint (re-run by critic, single-process `-p no:xdist -o addopts=""`)
| Suite | Result |
|-------|--------|
| `test_workflow_handler_auth_injection.py` (AC-1/AC-2) | **2 passed** |
| touched-module (`test_workflow_handler` + auth_injection + `test_insights_export` + `test_cross_service_wiring`) | **81 passed** |
| `tests/unit/auth/` + `tests/unit/clients/data/` | **532 passed, 1 skipped** |
| `ruff check` (uvx) on 5 touched files | **All checks passed!** |
| `ruff format --check` (uvx) | **3 files already formatted** |

---

## Cleared to STRONG
- **AC-1 (handler injects provider):** STRONG. Two-sided RED->GREEN re-proven by critic-injected defect; prod entrypoint driven; spy preserves class identity.
- **AC-2 (provider convention-agnostic):** STRONG. `resolve_secret_from_env` inspected — both topologies resolve to a real secret value; resolved value proven to flow into Config.
- **AC-RED-ON-HEAD:** STRONG. Both ACs fail on byte-reverted source for the correct reasons (assertion + AttributeError).
- **Prod-inertness (#149 guard):** STRONG. The full bearer chain (provider -> TokenManager JWT -> `Bearer` header) inspected end-to-end; no wholesale class patch in the auth-contract test.
- **Honest-failure shape:** STRONG. Only `ValueError` narrowed; `RuntimeError` and `TokenManager` auth errors (`InvalidServiceKeyError`/`RetryExhaustedError`/`TokenAcquisitionError`) propagate — NONE intersect the `(KeyError,AttributeError,TypeError)` mask at client.py:463, so the latent mask is unreachable by normal failure modes.
- **IaC delivery (insights-export + conversation-audit):** MODERATE->STRONG. Service-level `secret_arns` directly inspected; remote-module `_ARN` rename STRONG-inferred (not directly opened). Code-GO does not depend on it.

## NOT cleared (correctly open — not blocking PR #151)
- **`succeeded>0` live attestation (AC-V):** operator-gated. Requires real deploy + invocation. Honest-failure means a prod-unresolvable secret now 500s loudly (no silent `succeeded:0`).

---

## ESCALATE — pre-existing sibling dark-export (confirmed; OUT OF SCOPE for #151)
- **`src/autom8_asana/api/routes/workflows.py:361`** — `async with DataServiceClient() as data_client:` constructed **BARE** (no `auth_provider`).
- Live API route `POST /api/v1/workflows/{workflow_id}/invoke`; `workflows_router` mounted at `api/main.py:462`. Shares the same `requires_data_client`/`workflow_factory` registry as the Lambda.
- **Verified pre-existing:** present on `origin/main` at line 361; last touched by #27 (`5793aa53`, 2026-04-27) — predates W-AUTH (2026-06-10). NOT in PR #151 diff (0 matches). NOT a regression introduced by this fix.
- **Routing:** principal-engineer to apply the same provider injection (mirror `dependencies.py:505` / new `workflow_handler.py:173-175`) as a SEPARATE change. Escalated to Potnia.
- Repo-wide scan: exactly one remaining bare site (`workflows.py:361`); the fixed site (`workflow_handler.py:175`) is the only `DataServiceClient(auth_provider=...)` injection.

---

## Critic hygiene
Worktree mutated then restored byte-exact (empty diff vs HEAD `ec975e7c`); worktree clean; main repo HEAD `f4f924d2` unmutated; PR #151 untouched (still OPEN); scratch files removed.

## Overall
**CONCUR-WITH-FLAGS.** The W-AUTH fix is genuinely two-sided RED->GREEN, drives the real production entrypoint, sends a real `Bearer` JWT at runtime, fails honestly, and is NOT green-but-inert. Flags: (1) `workflows.py:361` sibling — ESCALATED, separate scope, non-blocking; (2) `succeeded>0` live run — operator-gated, correctly not closed; (3) remote terraform module `_ARN` rename strong-inferred not directly opened — immaterial to code GO. No BLOCKING finding.
