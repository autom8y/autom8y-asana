---
type: decision
altitude: OPERATIONAL
status: accepted
disposition: partial
initiative: lambda-obs-001
rite: sre
date: 2026-06-01
branch: sre-lambda-obs-001-instrumentation-2026-06-01
commit: 27064498573adc83d75e2f3b76e8788984e02b63
pr: 86
pr_url: https://github.com/autom8y/autom8y-asana/pull/86
obs_registry_updated: true
gaps_touched:
  - LAMBDA-OBS-001  # RESOLVED-in-repo
  - LOG-TRACE-LAMBDA # remains OPEN (out of scope)
---

# SRE Verdict — LAMBDA-OBS-001 Lambda Span Instrumentation

## Summary

`LAMBDA-OBS-001` is **RESOLVED-in-repo**. Every Lambda **entry-point handler** in
`src/autom8_asana/lambda_handlers/` now carries `@instrument_lambda` span
instrumentation from `autom8y_telemetry.aws`. The single genuinely-uninstrumented
entry point — `cache_invalidate.handler` — was instrumented in commit `27064498`
(PR #86, branch `sre-lambda-obs-001-instrumentation-2026-06-01`). The other five
entry points were already covered: `cache_warmer.handler` directly (the FROZEN,
production-proven baseline) and `conversation_audit`/`insights_export`/
`payment_reconciliation` transitively via the `create_workflow_handler` factory,
which applies `@instrument_lambda` inside the factory body (`workflow_handler.py:95`).

The registry's prior framing of "10 of 13 Lambda handlers uninstrumented" was a
**denominator error**: it counted 7 non-entry-point modules (shared utilities and
private async helpers that export no Lambda `handler`) as if they were
deployable handlers requiring instrumentation. Corrected denominator: **6 of 6
entry-point handlers instrumented** (100%).

## Outcome

**1 handler instrumented this initiative** (`cache_invalidate.handler`); 6 of 6
entry-point handlers instrumented at close.

Entry-point handler inventory (source-verified at `27064498`):

| Module | Entry point | Instrumentation | Mechanism |
|---|---|---|---|
| `cache_warmer.py` | `handler` | YES | direct `@instrument_lambda` (FROZEN baseline) |
| `cache_invalidate.py` | `handler` | YES (this initiative) | direct `@instrument_lambda` (line 278) |
| `workflow_handler.py` | factory `handler` (line 96) | YES | `@instrument_lambda` in factory (line 95) |
| `conversation_audit.py` | `handler = create_workflow_handler(...)` (line 52) | YES | transitive via factory |
| `insights_export.py` | `handler = create_workflow_handler(...)` (line 59) | YES | transitive via factory |
| `payment_reconciliation.py` | `handler = create_workflow_handler(...)` (line 60) | YES | transitive via factory |

## Behavior-Preservation Verdict

**PRESERVED.** Instrumentation wraps; it does not alter control flow.

- The `cache_invalidate.py` source diff is exactly two lines: the
  `from autom8y_telemetry.aws import instrument_lambda` import and the
  `@instrument_lambda` decorator above `def handler(...)`. Handler body, the
  `asyncio.run` dispatch, the broad-catch boundary, and the `{statusCode, body}`
  return contract are observably unchanged.
- **Cold-start characteristic is IDENTICAL to the established baseline** (QA Probe 6
  resolved). `cache_invalidate` uses the same `@instrument_lambda` decorator from
  the same `autom8y_telemetry.aws` package as the FROZEN, production-proven
  `cache_warmer`. `init_telemetry()` is gated once-per-container via the closure
  `_initialized` flag (`lambda_instrument.py:62-65`); subsequent invocations skip
  init and take only `trace.get_tracer(...)` + span-open cost. No new cold-start
  class is introduced.
- Tests (`tests/unit/lambda_handlers/test_cache_invalidate.py`,
  `TestHandlerInstrumentation`) install a hermetic OTel seam — a test
  `TracerProvider` via `trace.set_tracer_provider` plus a no-op of `init_telemetry`
  at the decorator-module binding site so first-invocation init does not clobber
  the `InMemorySpanExporter`. Coverage: span-per-invocation + attribute assertions,
  `StatusCode.OK` on success, return-contract preservation through the handler's
  internal 500 envelope, and `functools.wraps` identity preservation.

## DEFER List

The following 7 modules are **out of scope** for LAMBDA-OBS-001 — they are not
Lambda entry points and therefore have no `handler` to instrument. Instrumenting
them would be incorrect (they have no invocation boundary) or redundant (they
execute inside an already-instrumented parent span).

| Module | Kind | Public surface | Deferral rationale |
|---|---|---|---|
| `cloudwatch.py` | shared utility | `emit_metric`, `_get_cloudwatch_client` | Metric-emit helper imported by handlers; no Lambda entry point. |
| `timeout.py` | shared utility | `_should_exit_early`, `_self_invoke_continuation` | Self-continuation timing helper; no entry point. |
| `checkpoint.py` | shared utility | `_default_bucket` (+ checkpoint I/O) | State-persistence helper; no entry point. |
| `story_warmer.py` | private async helper | `_warm_story_caches_for_completed_entities` | Invoked inside an instrumented parent handler span; private (`_`) coroutine, no `handler`. |
| `push_orchestrator.py` | private async helper | `_push_gid_mappings_for_completed_entities`, `_push_account_status_for_completed_entities` | Same — runs within parent handler span; no entry point. |
| `reconciliation_runner.py` | private async helper | `_run_reconciliation_shadow` | Same — shadow-run coroutine, no entry point. |
| `pipeline_stage_aggregator.py` | private async helper | `_derive_pipeline_type`, `_aggregate_pipeline_stages` | Same — aggregation coroutine, no entry point. |

If any of these is promoted to a standalone Lambda (gains a `handler` export),
it re-enters scope and must receive `@instrument_lambda` at that time. Recommend
a watch-trigger on `grep -lE '^handler' src/autom8_asana/lambda_handlers/*.py`
yielding a count > 6.

## Residual (cross-repo SLO / alert tie-in)

- **Trace backend identity unresolved.** `@instrument_lambda` emits spans, but the
  destination (CloudWatch X-Ray vs Grafana Tempo via OTLP vs other) is opaque at
  satellite level (obs.md Knowledge Gap #4, and `OTLP-ENDPOINT-OPACITY` /
  `OTLP backend identity` gaps). Spans now exist for `cache_invalidate`, but
  end-to-end traceability cannot be attested until the backend and OTLP
  auth-routing-field are confirmed. This is a cross-repo dependency on the
  `autom8y` telemetry/IaC repo.
- **No Lambda-handler SLO consumes these spans.** Span emission is a precondition,
  not an SLO. No latency/error SLO is defined against any Lambda handler; alarm
  IaC (ALERT-1/ALERT-2/DMS-1) lives in the `autom8y` repo and its live state is
  unverified (obs.md Knowledge Gaps #6, #8). No on-call ownership documented.

## Next SRE Backlog (remaining OBS gaps)

Priority-ordered, source-verified open gaps in the registry after this verdict:

1. **LOG-TRACE-LAMBDA** (P3, OPEN) — `add_otel_trace_ids` is wired into the
   FastAPI/ECS structlog chain (`api/lifespan.py:77`) but NOT into the Lambda
   handler log-processor chain. Spans now carry trace IDs; Lambda logs do not yet
   correlate to them. Recommended next: wire `add_otel_trace_ids` into the Lambda
   logging init so CloudWatch log lines carry `trace_id`/`span_id`.
2. **SAMPLING-UNDOC** (P3, OPEN) — no `OTEL_TRACES_SAMPLER` env var configured;
   sampling behavior for the now-emitting Lambda spans is undocumented/defaulted.
   Risk of either cost blow-up (always-on) or silent under-sampling. Document and
   pin the sampler explicitly (cross-repo IaC).
3. **SLO-API-SURFACE** (P2, OPEN) — zero ECS/API SLOs defined. Highest-severity
   open instrumentation gap; spans/metrics exist with nothing consuming them.
4. **OBS-EXPORTS-001** (P2, deadline 2026-06-15) — exports route instrumentation
   still unaddressed; nearest hard deadline.
5. **OTLP-ENDPOINT-OPACITY** / OTLP backend identity (P2) — resolves the trace
   backend Residual above; gates true end-to-end traceability attestation.
6. **CRED-TOPOLOGY-MATRIX** (P2) — schema exists, no instance; blocks
   credential-topology attestation for push surfaces.
7. **H-006** (P3) — `trace_computation` unavailable in telemetry 0.6.1; inline
   TODO persists in `bridge_base.py`.

## Disposition

Initiative status **partial** at the verdict level: LAMBDA-OBS-001 itself is
RESOLVED-in-repo (the in-scope objective — instrument all Lambda entry-point
handlers — is fully met and behavior-preserving), but the broader Lambda
observability posture remains partial because trace-backend identity, log-trace
correlation (LOG-TRACE-LAMBDA), and sampling configuration are unresolved
residuals owned partly cross-repo. PR #86 carries the source change; the obs.md
Instrumentation Gaps Registry has been updated to reflect the corrected
denominator and resolved status.
