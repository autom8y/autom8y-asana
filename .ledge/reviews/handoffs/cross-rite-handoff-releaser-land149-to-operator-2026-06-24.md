---
type: handoff
status: accepted
from: releaser
to: operator, platform, iris, sre, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — releaser land-#149 → operator / platform / iris / sre / know

> **Grandeur anchor:** Land the proven SCAR-IDEM-001 fix (#149) to main, advancing W-IDEM proven→merged→live, only after the caller-contract is safe; proven by a green post-merge main CI matrix, never an enabled auto-merge or a green badge.

## LANDED (attested live receipts)
- **W-IDEM — SCAR-IDEM-001 finalize double-exec: MERGED + functionally LIVE.** PR **#149** squash **`f795d7dc`** on `main` (13:44:42Z). Post-merge main CI: `Test [f795d7dc]` **SUCCESS**, `Push on main` SUCCESS, `Satellite Dispatch` SUCCESS, `Secrets Scan` SUCCESS, `Aegis Synthetic Coverage` SUCCESS; trailing `Post-Merge Coverage` still in_progress (non-blocking aggregation — rung is `merged`+functional-`live`, not rounded to fully-green). Fix confirmed on main: `request.state.claims` discriminator (×6), `auth_context` no longer read. **The double-execution blocker is closed end-to-end.** Corroboration: 10x-dev QA GO + DELTA rite-disjoint critic CONCUR (STRONG); releaser-pass merge self-attested MODERATE.
- **W-REG scaffold** rode in on #149 — `authored`, wired to ZERO live callers, BLOCKED-on-W-IRIS. Not live, not proven. No live GIDs touched.

## Caller-contract (R2) — resolved by evidence, satisfied by vacuity
The new `500 IDEMPOTENCY_KEY_NOT_PERSISTED` for strict-once S2S callers has **no live consumer today**:
- Middleware is opt-in/additive — `idempotency.py` R-006: requests without `Idempotency-Key` behave exactly as before.
- No fleet service (data/ads/sms/scheduling) sends an `Idempotency-Key` header to asana's mutating intake/entity-write routes (their idempotency keys are all service-internal dedup).
- The only live S2S caller of asana is the legacy monolith `calendly_api` → `/v1/resolve/business` (a READ/resolve, no key, not the mutation path).
- **Latent contract:** a FUTURE strict-once S2S caller that opts into `Idempotency-Key` must treat `500 IDEMPOTENCY_KEY_NOT_PERSISTED` as "not-persisted, safe-to-retry-with-awareness" — NOT a blind retry. Document at the seam when such a caller is introduced.

## Routed — genuinely remaining (do NOT dispatch next-rite specialists from here)

### → operator (the LIVE production incident — highest business impact, still open)
- **AI-2:** insights-export BI has produced `succeeded:0` since 2026-06-10 (`AUTH-TEB-001` = autom8y-data rejecting asana's outbound S2S JWT, every table). Fix is user-sovereign/cross-repo: rotate/re-issue `AUTOM8Y_DATA_API_KEY`, or register asana's `SERVICE_CLIENT_ID` on the autom8y-data side. `aws logs filter-log-events --log-group-name /aws/lambda/autom8-asana-insights-export --filter-pattern "AUTH-TEB"` to disambiguate.

### → platform (cross-repo autom8y-wt-golive + IAM)
- **AI-3:** add `ASANA_CW_NAMESPACE = "Autom8y/AsanaInsights"` to the insights_export env block (`autom8y-wt-golive/terraform/services/asana/main.tf:1851-1856`) — the PutMetricData grant's namespace condition excludes the default `autom8/lambda`.
- **AI-5 / AI-7:** add `environment` dim to BridgeFleetHealth emit (prod fleet dim); apply + arm the #148 alarm IaC (paging = confirm-first).

### → iris / sre
- **W-IRIS:** build the token-safe read-only Asana section-list route — the structural blocker gating W-REG → proven.

### → know
- corpus refresh (`/know --all`) + defer-watch dispositions.

## Operator-sovereign (surfaced, NOT executed)
`AUTOM8Y_DATA_API_KEY` rotation (AI-2) · `terraform apply` (AI-3/AI-5/alarms) · Lambda deploy · the live Asana section-GID WRITE (W-REG). I fired none.

## Watch-registered DEFER
FORK-2 interop shared-substrate PR (2026-09-29); H-4 cache_warmer decomposition; lapsed 2026-05-29 triggers; fleet uv.lock hygiene (ranges already satisfy core-4.6.0 — DEFER per-repo hygiene).

## Inherited receipts
PR #149 (`f795d7dc`, MERGED); main HEAD `f795d7dc`; `.ledge/reviews/10x-idem-critic-verdict-2026-06-24.md` (round-1 BLOCKING) + DELTA verdict (round-2 CONCUR); `release-execution-ledger-2026-06-24.md`; `sre-dark-subsystem-postmortem.md`; `asana-coherence-case-file.md`.
