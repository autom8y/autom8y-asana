---
type: review
status: accepted
---

# PV Pre-Flight — asana-ecosystem-coherence deep-dive triage

- **Date:** 2026-06-24
- **HEAD:** `f4f924d2684386093ef656ecde5e98613cdffce8` (`chore(deps): bump autom8y-core to 4.6.0`)
- **Branch (dirty, NOT the triage base):** `chore/bump-core-4.6.0`
- **Gate authority:** `@handoff-premise-validation-entry-gate`, `@premise-validation-discipline`, G-PROVE (`@structural-verification-receipt`), G-DENOM, G-RUNG (`@telos-integrity-ref`)
- **Discipline:** No claim without a pasted LIVE receipt. Rungs named, never rounded up: `authored < emitting < alerting < proven < merged < live < protecting-prod`.

> **Grandeur anchor:** Pick up the torch on autom8y-asana — the ecosystem's CRM-UI / datastore-frontend / workflow-orchestration layer composing into autom8y-{data,ads,sms,scheduling} flows — by driving the review-rite deep-dive from glint-detected signal to a graded, cross-rite-routed case file, advancing the two production-blockers (SCAR-REG-001; SCAR-IDEM-001) from `authored` toward `proven`; proven ONLY by a live receipt — never by a green dashboard or an optimistic merge. Production-mutating levers stay the user's.

## Live baseline receipts

### CI @ HEAD (live, REST — `gh api repos/autom8y/autom8y-asana/commits/<HEAD>/check-runs`)
All required gates GREEN; two non-blocking SKIPPED:
- success: Aggregate Coverage Gate, CodeQL (actions/javascript-typescript/python), gitleaks + Secrets Scan, Test shards 1–4/4, Lint & Type Check, Spectral Fleet Validation, Matrix Prep, Semantic Score Gate, OpenAPI Spec Drift, Fleet Schema Governance, Fleet Conformance Gate, Isolated tests (non-blocking), Fuzz Tests (Hypothesis/Schemathesis), Dependency Review
- **skipped: `ci / Integration Tests`, `ci / Convention Check`** ← note for downstream: integration coverage is NOT exercised at this commit.

### Corpus drift (live, git)
- `git rev-list --count 8980bcd7..HEAD` = **90 commits**
- census `8980bcd7` dated **2026-05-06**; HEAD **2026-06-24** → **49 days** stale; all `.know/` 7d-expiry domains expired.

## Premise validation matrix (P1–P5)

| # | Premise | Verdict | Rung (live) | Receipt |
|---|---------|---------|-------------|---------|
| **P1** | SCAR-REG-001 OPEN — `section_registry.py` ships sequential placeholder GIDs bearing VERIFY-BEFORE-PROD | **TRUE (code-confirmed)** | defect `proven` present in code; live-Asana truth `PENDING` | `reconciliation/section_registry.py:94-99` + `:128-131` two `VERIFY-BEFORE-PROD (SCAR-REG-001)` blocks; `EXCLUDED_SECTION_GIDS={1201081073731600..603}` (`:100-107`), `UNIT_SECTION_GIDS={1201081073731610..624}` (`:132-150`) — visibly sequential. Verify cmd in-code: `GET /projects/1201081073731555/sections`. |
| **P2** | SCAR-IDEM-001 OPEN — `idempotency.py:719` swallows `finalize()` → double-exec for strict-once S2S | **TRUE (code-confirmed)** | risk `proven` open | `idempotency.py:719` `except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD … a client retry will re-execute the mutation (double-execution risk)`; only `logger.exception` follows (`:720-728`). No error-metric promotion. |
| **P3** | `/v1/query/{entity_type}` still MOUNTED & serving with lapsed `Sunset: 2026-06-01` | **TRUE (route live + sunset lapsed); usage UNKNOWN** | route `live`; "is-it-used" `UNVERIFIABLE` from metrics | Route mounted: `api/main.py:470 RouterMount(router=query_router)`. Header set: `query.py:881 response_obj.headers["Sunset"]="2026-06-01"` + `Deprecation: true`. **G-DENOM CATCH:** "usage" telemetry is a **log line** (`query.py:885 logger.info("deprecated_query_endpoint_used", …)`), NOT a CloudWatch metric — `Autom8y/AsanaWorkflows` namespace publishes **0 metrics** (`list-metrics` count=0). Usage proof requires Logs Insights, not done. → genuine retire-vs-extend fork (Pythia). |
| **P4** | TENSION-006 interop gap; "~30%" figure stale | **TRUE (gap code-confirmed); 30% UNVERIFIED** | gap `proven`; quantification `authored`-only | `automation/workflows/protocols.py:32-44`: `get_reconciliation_async()`/`get_export_csv_async()` → "**GAP**: No interop reconciliation/export protocol", "**Migration status**: Do NOT migrate … Interop covers ~30% of the client surface." Figure is an in-code doc-claim; re-quantify at HEAD. |
| **P5** | `.know/` stale; cache features (#128 PRESERVE, #141 governor/AIMD, #139 dead-man, #127 honest-empty/cure) absent from `feat/INDEX.md` | **TRUE** | gap `proven` | 90-commit drift (above). `INDEX.md` grep: `cure`=0, `governor`=0, `dead-man`=0, `honest-empty`=0, `serve-stale`=0, `PRESERVE`=0, `StorageNamespace`=0 (AIMD=2 partial). Source HAS them: `src/autom8_asana/storage_namespace.py` exists; PRESERVE/serve-stale/etc. across `config.py`, `transport/asana_http.py`, `metrics/freshness.py`, `lambda_handlers/pipeline_stage_aggregator.py`. |

## Bonus live signal (new, beyond the glint report)

- **Bridge-fleet success gap.** `Autom8y/AsanaBridgeFleet :: LastSuccessTimestamp` (undimensioned) last datapoint **2026-06-18T13:32:06**; none for 2026-06-19…24 (~6 days). `BridgeFleetHealth` dims = `{environment: staging, workflow_id: insights-export}` only. → INVESTIGATE: bridge fleet idle vs telemetry-gapped; only `insights-export` is observed, in `staging`.
- **Push-seam metric name correction.** Real metric is `StatusPushFailure` via `emit_metric` (`push_orchestrator.py:198`), NOT `GidPushFailure`; namespace not `AsanaBridgeFleet`. Push-seam health was NOT validated — open for N1.
- **Live namespaces present:** `Autom8y/Asana{Audit,BridgeFleet,DataframeSource,Insights,Reconciliation}`, `Autom8y/{Auth/TokenExchange,AuthSync,Canary,Freshness,FreshnessProbe,Reconciliation,Reconciliation/IdentitySeam}`. `AsanaDataframeSource` exposes the cure/empty-frame signals (`ColumnContractFailure`, `EmptyFrameTrip`, `RefreshFallbackCount`, `GetDfFallback`) — telemetry for the undocumented P5 features.

## Tooling state

- **iris:** summoned by user but agent file not yet active (`~/.claude/agents/iris.md` MISSING) — requires CC restart. P1 live-Asana section read deferred to N4 `/iris` handoff (ready post-restart).
- **AWS creds:** LIVE (`arn:aws:iam::696318035277:user/tom.tenuta`).
- **iris/pythia note:** pythia ACTIVE.

## Verdict

All five load-bearing premises **HOLD** at HEAD (P1, P2, P4, P5 code-proven; P3 route-live with usage a genuine fork). Two production-blockers confirmed OPEN in code. **Local tree proven live; the stale `.know/` corpus is NOT the source of truth for this procession.** Cleared to author the shape and dispatch the review-rite deep-dive. Production-mutating levers (incl. the live Asana section-GID write) remain the user's.
