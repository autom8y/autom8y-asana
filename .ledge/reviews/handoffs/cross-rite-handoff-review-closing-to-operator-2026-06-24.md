---
type: handoff
status: accepted
from: review
to: operator, 10x-dev, iris, platform, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — review closing-coherence-verdict → operator / 10x-dev / iris / platform / know

> **Grandeur anchor:** Render the definitive coherence verdict on autom8y-asana cutover-readiness — proven by HEAD-code receipts, never handoff prose. The review rite mutated only `.ledge/`.

## VERDICT: cutover-readiness grade **C** (mechanical B; Counter-Case override — a live, BLOCKED-on-auth correctness gate). Rite-disjoint critic: **CONCUR-WITH-FLAGS**, no fabricated findings, all 3 landed-holds STRONG.
Artifacts: `.ledge/reviews/asana-closing-{scan,assess,case-file,critic-verdict}-2026-06-24.md`.

## Landed & holding on `origin/main` (STRONG — merged-on-main + absent-from-branch, critic-reproduced)
- **#135** `/v1/query` retire — 0 Sunset/deprecated markers on main (`5e31bb48`).
- **#148** `StatusPushSkipped` obs — present (`gid_push.py:46-54`), 3 callsites (`9b698280`).
- **#149** idempotency claims-discriminator — `request.state.claims` (NOT `auth_context`), finalize-bool read, 500-propagation (`f795d7dc`).
- (Branch trap: the local `chore/bump-core-4.6.0` is behind main and still shows the OLD bugs — verify via `git show origin/main:` only.)

## Residual ledger — CORRECTED by the rite-disjoint critic (the case file mis-prioritized; this is authoritative)

| Residual | Status / rung | Severity | The action |
|---|---|---|---|
| **Insights BI outage (live, succeeded:0 since ~2026-06-03)** — cause is **AUTH-TEB-001 / bare `DataServiceClient`**, fixed by **PR #151** (proven, OPEN/not-merged) | `proven`, not `merged` | **HIGHEST (live)** | **operator: `gh pr merge 151 --squash` + deploy** — THE one action that ends the outage |
| **R4 (NEW): insights-export role lacks `cloudwatch:PutMetricData`** → WorkflowSuccessRate/Duration silently fail; the incident's own alarm is partly dark | live gap | **MEDIUM-HIGH** | platform: grant the IAM action (autom8y monorepo) before relying on the metric as a deploy gate |
| **SCAR-REG-001: 19 placeholder section GIDs — LIVE** (`EXCLUDED_SECTION_GIDS` is the default at `reconciliation/processor.py:165`; only the join-scaffold is dark) | `proven-in-code` / BLOCKED-on-iris | **HIGH** | iris (W-IRIS read route) → 10x-dev (dual-anchor fix) → operator (deploy) |
| `workflows.py:361` bare `DataServiceClient()` sibling (live `POST /v1/workflows/{id}/invoke`) | `proven` / OPEN | MEDIUM | 10x-dev (same injection as #151) |
| D-2: `workflows.py:355-365` data-client branch — zero unit coverage | `proven` / NEW | MEDIUM | 10x-dev |
| Stale test `test_fleet_query_adapter.py:370` asserts retired endpoint "MUST remain" (passes by substring accident, masks #135) | `proven` / NEW | LOW-MEDIUM | 10x-dev/hygiene: re-assert the deprecated POST is GONE |
| ~12 `except Exception` sites (most BROAD-CATCH-annotated; a couple degrade/swallow at `health.py:381`, `factory.py:136`) | `proven` / partial | LOW | hygiene |
| `query.py` stale module docstring post-#135 | `proven` / NEW | LOW | hygiene |

**Defect-class roster COMPLETE:** bare-`DataServiceClient` = exactly 2 real sites (both accounted); SCAR-IDEM-001 finalize-swallow CLOSED (#149); no third bare site.

## The corrected headline (the review pantheon got this wrong; the critic fixed it)
The case-reporter named SCAR-REG-001 the "#1 residual." **The rite-disjoint critic proved otherwise:** the *live* BI outage is the insights-export **AUTH-TEB-001** problem — a **different Lambda** — fixed by **OPEN PR #151**. SCAR-REG-001 is a *separate* live reconciliation-routing risk (BLOCKED-on-iris). **Two distinct issues; do not conflate.** The single highest-value action remains **merge + deploy #151**.

## Routing (next `/frame` targets; do NOT dispatch their specialists from here)
- **operator/framing** — merge + deploy #151 (ends the BI outage); the IAM `PutMetricData` grant (R4).
- **10x-dev/framing** — `workflows.py:361` sibling injection; D-2 coverage; the stale-test fix; docstring.
- **iris/framing** — W-IRIS token-safe read route (unblocks SCAR-REG-001 / W-REG).
- **know/framing** — corpus refresh (90+ commits stale) + defer-watch reconcile.

## Production-mutating levers — surfaced, NOT executed (operator-sovereign)
`gh pr merge 151 --squash` + Lambda deploy · IAM PutMetricData grant · the live Asana section-GID WRITE (W-REG) · any merge/deploy/rollback/alarm-arm.

## Watch-registered DEFER
FORK-2 interop substrate (2026-09-29); H-4 cache_warmer decomposition; W-REG until W-IRIS lands.

## Inherited receipts
`.ledge/reviews/asana-closing-*-2026-06-24.md`; PRs #135/#148/#149/#150 on main (HEAD `8bc31a6a`); #151 OPEN; `cross-rite-handoff-10x-wauth-to-operator-2026-06-24.md`.
