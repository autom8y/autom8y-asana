---
type: handoff
status: accepted
from: releaser
to: 10x-dev, platform, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — releaser fleet-release → 10x-dev / platform / know

> **Grandeur anchor:** Land the asana-cutover-readiness scope across the ecosystem in dependency-DAG order, advancing each finding merged→live; proven ONLY by a published-artifact receipt + green consumer CI with run IDs.

## LANDED this cycle (attested live)
- **PR #148 — obs instrumentation** (`StatusPushSkipped{skip_reason}` + alarm IaC). Squash `9b698280` on `main`; post-merge main CI GREEN (`Test [9b698280]` run 28097575439 success); `StatusPushSkipped` present in `gid_push.py` on main. **Rung: live.** Alarm IaC (`terraform/services/asana/observability_alarms.tf`) is merged **un-armed**.
- **PR #135 — `/v1/query` full retire** (FORK-1). Squash `5e31bb48` on `main` (12:22:13Z); deprecated `POST /{entity_type}`, `Sunset` header, `deprecated_query_endpoint_used` all = 0 on main (−1301 lines). **Rung: merged** (evidence-licensed: 0 prod hits / 18.9M scanned).
- **autom8y-core 4.6.0** — already live via **PR #146** (`4f05876b`); fleet consumes by range `>=4.2.0,<5.0.0`. **No cross-repo cascade existed** (G-DENOM: no fleet sweep manufactured).
- Rite-disjoint critic: **CONCUR-WITH-FLAGS**, 0 BLOCKING. Artifacts: `release-execution-ledger-2026-06-24.md`, `release-critic-verdict-2026-06-24.md`.

## Cleanup / surfaced (not fired)
- `chore/bump-core-4.6.0` branch is a redundant duplicate of #146 — **abandon** (`git branch -d chore/bump-core-4.6.0`); not deleted by an agent.
- A `lockfile-bump/autom8y-core-4.7.0` remote branch was observed during fetch — **out of scope** (4.7.0 not part of this initiative; do not pull in).
- User-sovereign / confirm-first (untouched): token rotation, paging, deploy-freeze, prod rollback, version yank, any red-bypass merge.

## What genuinely remains — routed (do NOT dispatch next-rite specialists from here)

### → platform / 10x-dev — THE REAL PRODUCTION INCIDENT (highest value)
- **AI-2** insights-export `AUTH-TEB-001` upstream auth failure — the BI insights export has produced **`succeeded:0` since 2026-06-10** (every daily run fails upstream). Likely cross-repo (autom8y-data insights service). Rung: `authored`→`proven` on a `succeeded>0` run.
- **AI-3** IAM: grant `cloudwatch:PutMetricData` to `autom8-asana-insights-export-lambda-role` (denied since 06-10) — restores the bridge-fleet success metric. Rung: `authored`→`live`.
- **AI-5** add the `environment` dimension to `BridgeFleetHealth` emit (`workflow_handler.py:256-262,330-339`) → creates the missing prod fleet dim that AL-4 targets.
- **AI-7** apply + arm the merged alarm IaC (paging = confirm-first).
- **AI-1** decide: re-enable `autom8y-account-status-recon-schedule` (currently DISABLED — the recon gap was EXPECTED, not a defect) or record the intended pause.

### → 10x-dev — the still-open blockers (W-IDEM / W-REG)
- **W-IDEM** SCAR-IDEM-001 finalize double-exec (`idempotency.py:719`, RED-first).
- **W-REG** SCAR-REG-001 dual-anchor GID join (`section_registry.py:94-150`) — **still BLOCKED** on the W-IRIS live-Asana read route (no token-safe route exists; PAT Lambda-runtime-only). Build the read-only route first.

### → autom8y-data (cross-repo)
- **AI-6** classify/repair the `three_way_denominator_null` + empty-vertical skips at `query_grain_guard.py` / `batch_grain_guard.py`.

### → know
- corpus refresh (`/know --all`, 90-commit drift) + defer-watch dispositions.

## Watch-registered DEFER (not scope-crept)
FORK-2 interop shared-substrate PR (2026-09-29); H-4 cache_warmer decomposition; lapsed 2026-05-29 defer-watch triggers.

## Inherited receipts
`.ledge/reviews/`: `release-execution-ledger-2026-06-24.md` · `release-critic-verdict-2026-06-24.md` · `sre-dark-subsystem-postmortem.md` (the AI-1..AI-8 source) · `asana-coherence-case-file.md` · PRs #148 (`9b698280`), #135 (`5e31bb48`), #146 (`4f05876b`).
