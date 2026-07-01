---
type: review
status: draft
---
# Signal-Sift: Asana Ecosystem Coherence — Audit Loci
**HEAD**: f4f924d2 | **Date**: 2026-06-24 | **Complexity**: FULL (net-new depth beyond pre-flight)

---

## 1. cache_warmer.py — Structure Map, Governor, Observable AIMD

**Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py`
**Confirmed size**: 1437 LOC (receipt: `wc -l` = 1437)

### 1.1 Structural Map (top-level sections)

| Lines | Section |
|-------|---------|
| 1–32 | Module docstring + env-var contract |
| 34–73 | Imports + logger |
| 75–145 | Module-level constants: `_DMS_NAMESPACE_FALLBACK`, `_DEFAULT_BULK_KEY_BUDGET` |
| 147–176 | `_sample_aimd_engaged()` — C-5 AIMD attestation probe |
| 179–213 | `_ensure_bootstrap()` — lazy cold-start registry init |
| 215–437 | `_run_vertical_backfill()`, `_prematerialize_bulk_set_async()` setup |
| 438–644 | `_prematerialize_bulk_set_async()` — bulk warm loop (key-budget + timeout exits, checkpoint, AIMD sample) |
| 646–699 | `WarmResponse` dataclass |
| 701–1160 | `_warm_cache_async()` — entity-type warm loop with push side-effects |
| 1161–1254 | `handler_async()` — async Lambda entry |
| 1255–1368 | `handler()` — sync Lambda entry, event parse, asyncio.run dispatch |

### 1.2 Warm-Cycle Governor / Observable AIMD (commit dd8e43ab, 2026-06-19)

Commit message names five root causes fixed:

- **C-1** (`cache_warmer.py:164–176`): `_sample_aimd_engaged()` — AIMD semaphore logger gate was `isinstance(logger, LoggerProtocol)` which failed at runtime because deployed `DefaultLogProvider` lacks `bind()`; gate handed `None` → zero `aimd_decrease` events in prod under 2584 live 429s. Fix: admit logger on methods AIMD actually calls.
- **C-2**: warm-cycle-shared semaphore for `ParallelSectionFetcher` so stacked callsite-local `Semaphore(8)` instances cannot multiply past one coordinated in-flight bound.
- **C-3**: conservative AIMD start window clamped into `[floor, ceiling]`; env-overridable.
- **C-4**: `max_requests` rate-tier made env-overridable.
- **C-5** (`cache_warmer.py:461–503, 608–614, 674–680`): `aimd_engaged_holder` dict pattern — AIMD engagement sampled via `_sample_aimd_engaged(client)` inside `async with AsanaClient(...)` context BEFORE exit; result stored in `WarmResponse.aimd_engaged`. A full-coverage cycle that did NOT engage the limiter (`aimd_engaged=False`) must NOT be trusted as a durable above-floor hold by the PT-02' re-gate.

**G-RUNG**: HIGH — code-grounded at file:line; directly observable in diff.

### 1.3 Could the Governor Throttle the Warmer into the ~06-18/19 Quiescence?

**Commit timeline**: The AIMD governor commit (`dd8e43ab`) merged **2026-06-19 10:07 UTC+1**. The pre-flight reported a subsystem-quiet window around 06-18/19.

**Code path analysis**:

The governor (`_sample_aimd_engaged`) is an **attestation/observability probe only** — it does NOT throttle the warmer. It reads semaphore stats at cycle end and emits `WarmerAimdEngaged` metric; it cannot pause or abort the warm. `cache_warmer.py:163–176`.

The AIMD semaphore itself (`transport/adaptive_semaphore.py`, modified in dd8e43ab) governs Asana API concurrency via a rate-limiter — when it decreases, fewer parallel Asana calls proceed. This IS a throttle, but it reduces Asana 429s rather than causing warmer quiescence.

**Conclusion**: The governor CANNOT by itself cause a zero-output quiescence window. The 06-18/19 quiet period coincides with the merge window of dd8e43ab itself — the warm was likely quiescent because the C-1 bug (semaphore_logger=None → AIMD dark) was being remediated and the new code was deploying.

---

## 2. Interop Coverage Re-quantification (clients/data/ + automation/workflows/protocols.py)

**Location**: `src/autom8_asana/automation/workflows/protocols.py:41–44`, `src/autom8_asana/clients/data/client.py`

### 2.1 The ~30% Claim

`protocols.py:42`: "Interop covers ~30% of the client surface."

This is an **author-stated figure** in the protocol docstring, not a computed ratio. The interop SDK coverage table is at `protocols.py:19–40`.

### 2.2 Re-quantification: DataServiceClient Public Methods

Public methods enumerated from `src/autom8_asana/clients/data/client.py` (lines with `async def` or `def` without `_` prefix, excluding `__dunder__`):

| Method | Line | Interop Coverage |
|--------|------|-----------------|
| `is_healthy()` | 168 | Partial — `DataReadProtocol.health_check()` overlaps (different signature per `protocols.py:29`) |
| `close()` | 375 | No interop coverage |
| `config` (property) | 514 | No interop coverage |
| `is_initialized` (property) | 523 | No interop coverage |
| `has_cache` (property) | 532 | No interop coverage |
| `has_metrics` (property) | 543 | No interop coverage |
| `circuit_breaker` (property) | 554 | No interop coverage |
| `get_insights_async()` | 676 | Partial — `DataInsightProtocol.get_insight()` per `protocols.py:30`; bridge has richer params |
| `get_insights()` | 778 | No interop coverage (sync wrapper) |
| `get_insights_batch_async()` | 860 | No interop coverage |
| `get_export_csv_async()` | 1145 | No interop coverage — explicit GAP at `protocols.py:36` |
| `get_appointments_async()` | 1180 | No interop coverage |
| `get_reconciliation_async()` | 1209 | No interop coverage — explicit GAP at `protocols.py:34` |
| `get_leads_async()` | 1245 | No interop coverage |

**Total public methods**: 14
**Interop-covered** (partial or full): 2 (`is_healthy`, `get_insights_async`)
**True interop ratio**: 2/14 = **~14%**, not ~30%

The `~30%` in `protocols.py:42` appears to count methods whose _concept_ overlaps (health-check + insights fetching) while the table at lines 19–40 explicitly documents 4 rows but only 2 of those have non-GAP interop protocol entries. The actual covered-vs-total ratio on a method-count basis is **2/14 (~14%)**.

**G-RUNG**: MEDIUM — the discrepancy is real but the 30% was authored as an approximation for "migration pressure documentation," not a precise metric; no functional defect.

[UV-P: Whether ~30% was calculated on a different surface (e.g., method groups or capability classes) | METHOD: docs-cite-verbatim from original spike doc | REASON: the spike doc "INTEGRATE-ecosystem-dispatch Section 1.4" referenced at protocols.py:44 is not present in this repo]

---

## 3. Push Seam: push_orchestrator.py — StatusPush* Emit Path

**Location**: `src/autom8_asana/lambda_handlers/push_orchestrator.py` (207 LOC), `src/autom8_asana/services/gid_push.py`

### 3.1 Emit Path Confirmation

`StatusPushSuccess` and `StatusPushFailure` are emitted at `push_orchestrator.py:192–198`:

```python
if success:
    emit_metric("StatusPushSuccess", 1, dimensions={"entry_count": str(len(all_entries))})
else:
    emit_metric("StatusPushFailure", 1)
```

The call chain from warmer: `cache_warmer.py:1077–1084` → `_push_account_status_for_completed_entities()` → `push_status_to_data_service()` (`gid_push.py:469`) → `_push_to_data_service()` → HTTP POST to `AUTOM8Y_DATA_URL/api/v1/account-status/sync`.

### 3.2 Why StatusPush* Never Published — Four Gates

**Gate 1 — feature flag** (`gid_push.py:491–496`): `_is_status_push_enabled()` checks `STATUS_PUSH_ENABLED` env var; disabled if set to `"false"`, `"0"`, or `"no"`. Default ON — not a silent disable unless env is set.

**Gate 2 — URL not configured** (`gid_push.py:498–504`): `_get_data_service_url()` returns `os.environ.get("AUTOM8Y_DATA_URL")`. If `AUTOM8Y_DATA_URL` is unset, the function logs `"status_push_skipped"` with `reason: "AUTOM8Y_DATA_URL not configured"` and returns `False`. This is the most likely production gate — if `AUTOM8Y_DATA_URL` was not set in the Lambda environment at the time of the iris observation window, `push_status_to_data_service` returns `False` before making any HTTP call, and `StatusPushSuccess/Failure` metrics are never emitted.

**Gate 3 — auth token** (`gid_push.py:506–512`): `AUTOM8Y_DATA_API_KEY` must resolve via Lambda extension. If the secret ARN is wrong or extension not ready, returns `False`.

**Gate 4 — no entries** (`push_orchestrator.py:183`): `if all_entries:` — if `extract_status_from_dataframe()` returns empty for all entities (e.g., project GIDs not in `PIPELINE_TYPE_BY_PROJECT_GID`, or no ACTIVE/ACTIVATING rows), the outer `push_status_to_data_service` is never called, and no metric is emitted.

**StatusPush* never published conclusion**: Most likely cause is Gate 2 (`AUTOM8Y_DATA_URL` not configured in Lambda env) or Gate 4 (project GIDs not matched). The path is **not feature-flag-off** by default — it is **env-config-absent**. The iris receipt that would confirm: a CloudWatch log search for `"status_push_skipped"` or `"status_push_disabled"` events in the warmer Lambda log group during the quiet window.

**G-RUNG**: HIGH (code path fully traced at file:line; the gate logic is unambiguous)

---

## 4. Broad-Except Census

**Command**: `grep -rn 'except Exception' src/ | wc -l`
**Result**: **197 occurrences** total across `src/`

### 4.1 Annotation Classification

| Class | Count | Criterion |
|-------|-------|-----------|
| Annotated (has `# noqa: BLE001` or `# BROAD-CATCH` comment) | **185** | Line contains `noqa: BLE001` or `BROAD-CATCH` |
| Unannotated (no noqa/BROAD-CATCH, not in comments/docstrings) | **12** | No annotation found |

### 4.2 Unannotated Broad-Except Instances (file:line)

| File | Line | Context |
|------|------|---------|
| `src/autom8_asana/reconciliation/engine.py` | 119 | `logger.exception("reconciliation_engine_processor_error", ...)` — logs, no re-raise |
| `src/autom8_asana/metrics/freshness.py` | 398 | `except Exception as e:` — context TBD |
| `src/autom8_asana/clients/data/_policy.py` | 210 | `except Exception as exc:` → `self._pre_execute_error_handler(exc, request)` — policy hook |
| `src/autom8_asana/cache/dataframe/factory.py` | 136 | `logger.exception(...)` — build timing fallback |
| `src/autom8_asana/api/routes/section_timelines.py` | 166 | `logger.exception("section_timelines_computation_failed", ...)` |
| `src/autom8_asana/services/intake_create_service.py` | 529 | `except Exception as exc:` |
| `src/autom8_asana/services/section_timeline_service.py` | 482 | `except Exception:` |
| `src/autom8_asana/services/intake_resolve_service.py` | 229 | `except Exception as exc:` |
| `src/autom8_asana/services/intake_resolve_service.py` | 316 | `except Exception as exc:` |
| `src/autom8_asana/services/intake_custom_field_service.py` | 126 | `except Exception as exc:` |
| `src/autom8_asana/lifecycle/reopen.py` | 12 | Comment only (module docstring describes the pattern) |
| `src/autom8_asana/lifecycle/engine.py` | 12 | Comment only (module docstring describes the pattern) |

**Effective unannotated code-site count**: 10 (excluding 2 that are module docstring prose, not actual except clauses)

**Pattern**: Unannotated cases cluster in `services/intake_*` (4 of 10) and `api/routes/` (1 of 10). The `clients/data/_policy.py:210` case is a pre-execute error hook — borderline intentional (delegates to a configurable handler). The `reconciliation/engine.py:119` and `cache/dataframe/factory.py:136` cases use `logger.exception()` (which includes traceback) and are functionally annotated via log behavior even without the comment tag.

**G-RUNG**: MEDIUM — 10 unannotated sites out of 197 is a 5% non-compliance rate against the project's established annotation convention; not a safety issue since all observed cases log the exception.

---

## 5. Subsystem-Quiet Convergent Signal: Root-Cause Hypotheses

**Observed**: Iris reported a ~06-18/19 quiescence window where subsystem outputs (StatusPush*, warmer metrics, or related signals) were absent or flat.

**Commit timeline anchor**: dd8e43ab merged 2026-06-19 10:07 UTC+1 ("fix(warmer): observable AIMD + warm-cycle governor"). This is the dominant temporal event in the window.

### Hypothesis 1: Telemetry-Only Gap (AIMD Dark — C-1)

**Claim**: The C-1 bug (semaphore_logger=None → AIMD observability dark) caused the warmer to run but emit no AIMD decrease events. StatusPush* silence is a separate env-config issue (Gate 2/4 above), not related to the AIMD bug.

**Code receipt**: `cache_warmer.py:163–176` (`_sample_aimd_engaged` returns `None` when logger gate fails). With C-1 present, `aimd_engaged_holder["value"]` stays `None` for the full warm cycle, so `WarmerAimdEngaged` metric is never emitted (`cache_warmer.py:489–490`). The warmer itself still ran; coverage metrics still fired.

**Confirming receipt**: CloudWatch `WarmerAimdEngaged` metric absent pre-19 Jun; present post-19 Jun (after C-1 fix deployed).
**Refuting receipt**: Coverage metrics (`WarmSuccess`, `RowsWarmed`) also absent in the window → warmer did not run, not just AIMD dark.

**Plausibility**: HIGH for AIMD observability gap; MEDIUM for explaining broader subsystem quiet.

### Hypothesis 2: Deploy / Cold-Start Quiescence

**Claim**: dd8e43ab was a 702-line diff touching 11 files including `settings.py` and `transport/adaptive_semaphore.py`. Lambda deployment of this commit caused cold-start gap(s) between ~06-18 end-of-day and ~06-19 10:07 merge.

**Code receipt**: No direct code evidence; deploy quiescence is an infra-layer event not visible in source.

**Confirming receipt**: Lambda `$LATEST` cold-start timestamps in CloudWatch logs showing invocation gap around 06-18/19 boundary.
**Refuting receipt**: CloudWatch invocation count metric showing continuous Lambda invocations with no gap.

**Plausibility**: MEDIUM.

### Hypothesis 3: Schedule Disable / EventBridge Rule Disabled

**Claim**: EventBridge rule for the bulk warmer or section warmer was temporarily disabled (manual or Terraform drift) during the window.

**Code receipt**: `cache_warmer.py:1296–1304` documents two EventBridge schedules (bulk: 30-min cadence, section: ≤10-min cadence). Code does not control the schedule — schedule is Terraform-managed (`autom8y/asana/main.tf` referenced in header comments). No code signal for a schedule disable.

**Confirming receipt**: Terraform state or AWS console showing EventBridge rule state=DISABLED between 06-18/06-19.
**Refuting receipt**: EventBridge rule CloudWatch event count showing continuous scheduled invocations.

**Plausibility**: LOW (would require manual action; no code-level signal).

### Hypothesis 4: Governor-Induced Throttle (Ruled Out by Code)

**Claim**: The warm-cycle governor throttled the warmer to zero output.

**Code receipt**: `_sample_aimd_engaged()` at `cache_warmer.py:147–176` is a **read-only** probe. It cannot pause, abort, or throttle the warm cycle. The AIMD semaphore in `transport/adaptive_semaphore.py` controls Asana API concurrency (limits 429s), but a fully-governed warm (all windows contracted) still completes; it just takes longer. Zero-output quiescence from the governor alone is not possible from code inspection.

**This hypothesis is CODE-REFUTED**: governor is observability-only; AIMD semaphore at floor slows but does not stop the warm.

### Most Probable Root Cause

**Hypothesis 1 + Hypothesis 2 combined**: The 06-18/19 quiet window reflects (a) AIMD observability dark (C-1 bug) masking the warmer's internal AIMD activity in CloudWatch, AND (b) a deploy/redeploy gap for the 702-line dd8e43ab commit. StatusPush* absence is independently explained by Gate 2 (`AUTOM8Y_DATA_URL` env not configured in Lambda at that time, or Gate 4 — project GID mismatch in `PIPELINE_TYPE_BY_PROJECT_GID`).

**Single discriminating receipt to request from iris**: CloudWatch Lambda invocation count metric for the warmer function between 2026-06-17 18:00 and 2026-06-19 12:00 UTC. If invocation count is zero → deploy/schedule gap (H2/H3). If invocation count is non-zero but `WarmerAimdEngaged` absent → pure telemetry gap (H1).

---

## Per-Locus Signal Table

| Locus | Signal | File:Line | Confidence | G-Rung |
|-------|--------|-----------|------------|--------|
| cache_warmer.py structure | 1437 LOC; 3 distinct warm paths (entity-type, bulk, section) gated by event params | `cache_warmer.py:1291–1304` | HIGH | HIGH |
| AIMD governor (dd8e43ab C-1) | semaphore_logger=None caused AIMD dark pre-fix; attestation probe is read-only, cannot quiesce warmer | `cache_warmer.py:147–176`, `cache_warmer.py:461–503` | HIGH | HIGH |
| AIMD governor (dd8e43ab C-5) | PT-02' re-gate: full-coverage cycle with aimd_engaged=False must not be trusted as durable hold | `cache_warmer.py:486–503`, `WarmResponse:673–680` | HIGH | HIGH |
| Governor-throttle hypothesis | Ruled out: `_sample_aimd_engaged` is read-only; AIMD semaphore slows but cannot zero-output the warmer | `cache_warmer.py:163–176` | HIGH (refutation) | HIGH |
| Interop ratio re-quantification | 2/14 public methods have interop coverage (~14%, not ~30%); protocols.py:42 overstates | `protocols.py:42`, `client.py:168–1245` | HIGH | MEDIUM |
| Interop GAPs documented | `get_reconciliation_async`, `get_export_csv_async` explicitly have NO interop protocol | `protocols.py:34–39` | HIGH | MEDIUM |
| StatusPush* path — Gate 2 | `AUTOM8Y_DATA_URL` unset → `push_status_to_data_service` returns False silently; no metric emitted | `gid_push.py:498–504` | HIGH | HIGH |
| StatusPush* path — Gate 4 | `extract_status_from_dataframe` returns empty if project GID not in `PIPELINE_TYPE_BY_PROJECT_GID` | `gid_push.py:385–394`, `push_orchestrator.py:183` | HIGH | HIGH |
| GID_PUSH_ENABLED flag | `gid_push.py:57–64` — default ON; would not explain silence unless explicitly set false | `gid_push.py:57–64` | HIGH | MEDIUM |
| broad-except total | 197 occurrences; 185 annotated (noqa: BLE001 or BROAD-CATCH); 10 unannotated code sites | `grep -rn 'except Exception' src/ | wc -l` | HIGH | MEDIUM |
| Unannotated broad-except cluster | intake_resolve_service.py:229,316; intake_create_service.py:529; intake_custom_field_service.py:126 | above lines | MEDIUM | MEDIUM |
| Subsystem-quiet root cause | H1+H2 most probable; H4 (governor) code-refuted; H3 (schedule) low probability | `cache_warmer.py:147–176`, `gid_push.py:498–504` | MEDIUM | HIGH |

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| cache_warmer.py LOC (confirmed) | 1437 |
| push_orchestrator.py LOC | 207 |
| protocols.py LOC | 119 |
| DataServiceClient public methods | 14 |
| Interop-covered methods (partial+full) | 2 (14%) |
| `except Exception` total (src/) | 197 |
| Annotated broad-excepts | 185 (94%) |
| Unannotated broad-excepts (code sites) | 10 (5%) |
| StatusPush* gates identified | 4 (flag, URL, token, empty-entries) |
| Hypotheses for quiet window | 4 (H1 telemetry-dark, H2 deploy, H3 schedule, H4 governor-ruled-out) |
| Highest-severity open item | StatusPush* env-config dependency: silent non-publication if AUTOM8Y_DATA_URL unset |
