---
type: decision
altitude: OPERATIONAL
status: accepted
disposition: partial
initiative: log-trace-lambda
rite: sre
date: 2026-06-02
---

# SRE Verdict — LOG-TRACE-LAMBDA: Span<->Log Correlation in the Lambda Path

## Summary

The Lambda execution path emitted structured logs that carried no
OpenTelemetry `trace_id`/`span_id` and applied only the SDK's exact-match
sensitive-field filter. The ECS/FastAPI path had already wired both correlation
and substring-redaction at `api/lifespan.py:77`
(`additional_processors=[add_otel_trace_ids, _filter_sensitive_data]`); the
Lambda path had no equivalent. As a result, the LAMBDA-OBS-001 spans (PR #86)
opened by `@instrument_lambda` produced no correlatable log lines in the Lambda
runtime — the spans existed, but logs could not be joined to them.

PR #88 closes the correlation gap by introducing an idempotent cold-start
logging configurator and wiring it ahead of the handler-import surface. The
disposition is **partial/ratified**: the trace<->log correlation unit is
shippable and verified; a span-fidelity refinement is bundled as deferred, and
the residual SRE backlog (endpoint opacity, API SLOs, sampling, credential
topology) is untouched and explicitly carried forward.

## Outcome

**Wiring location**: `src/autom8_asana/lambda_handlers/logging_config.py` — new
module exposing `configure_lambda_logging()`. Invoked at Lambda cold-start from
`src/autom8_asana/lambda_handlers/__init__.py` (after the
`logging_config` import, before the handler imports at `__init__.py:26+`). The
function composes two structlog processors into the `autom8y_log` chain via
`core.logging.configure(additional_processors=[add_otel_trace_ids,
_filter_sensitive_data_substring])`, mirroring the ECS reference at
`api/lifespan.py:77` without dragging the FastAPI app graph into the Lambda
image.

**Handlers covered**: All entry-point Lambda handlers re-exported from
`lambda_handlers/__init__.py` inherit the cold-start configuration because it
runs once at package import, before any handler module is imported. The 6-of-6
entry-point handlers established by LAMBDA-OBS-001 (`cache_warmer` direct,
`workflow_handler` factory, `conversation_audit` / `insights_export` /
`payment_reconciliation` transitive via `create_workflow_handler`,
`cache_invalidate`) now run inside a structlog chain that carries trace
correlation and substring redaction. The configuration is process-global and
cold-start-once (PROCESS-GLOBAL constraint), guarded three ways:
`logging_config._configured`, `core.logging._configured` (verified at
`core/logging.py:84`), and the `autom8y_log` SDK global.

**Frozen-adjacency**: Verified. PR #88 touches exactly three files —
`lambda_handlers/logging_config.py` (new), `lambda_handlers/__init__.py`
(cold-start wiring + E402 import reordering), and
`tests/unit/lambda_handlers/test_logging_config.py` (new). `api/lifespan.py`,
the middleware, the handler sources, and the LAMBDA-OBS-001 spans are untouched
(QA Probe 7).

## Span-Log Correlation Verdict

**PROVEN.** The correlation is verified non-vacuously, not merely asserted:

- `test_trace_ids_injected_inside_active_span` — inside an active span,
  `add_otel_trace_ids` injects a 32-hex `trace_id` and a 16-hex `span_id`; the
  test parses both as hex and rejects the all-zero (invalid) trace id.
- `test_trace_ids_match_active_span_context` — the injected ids equal the active
  span's own `SpanContext` (`format(ctx.trace_id, "032x")` /
  `format(ctx.span_id, "016x")`), establishing true correlation rather than
  presence of arbitrary fields.
- `test_no_trace_ids_outside_span_context` — outside any span, no correlation
  ids are fabricated (negative control).

The processor wired into the Lambda chain (`add_otel_trace_ids` from
`autom8y_log.processors`) is the identical function the ECS path uses at
`api/lifespan.py:77`, so the Lambda path reaches parity with the ECS reference
site rather than reimplementing correlation.

**Import-ordering invariant (resolved, but load-bearing)**: The auto-config
guard is tripped by the first module-scope `get_logger(__name__)` call. There
are 10 such offenders inside `lambda_handlers/` alone (190 repo-wide), and any
one transitively imported before `configure_lambda_logging()` runs would
pre-empt the wiring with bare `LogConfig()` defaults. Direct inspection
confirms the committed ordering is safe: `logging_config.py`'s own import chain
reaches `core.logging` (line 55), but `core.logging` calls `get_logger` only
inside a function body (`core/logging.py:35-36`), NOT at module scope — so
importing it does not trip the guard. The first module-scope offender on the
import path, `cache_invalidate.py:46`, is imported at `__init__.py:26+`, which
runs *after* the cold-start `configure_lambda_logging()` call. The guard
installs ahead of the offender surface. This invariant is fragile to future
reordering of `__init__.py` and is flagged for reviewer attention.

## Sensitive-Data Preservation

**PRESERVED.** Redaction is composed alongside (not in place of) correlation.
The Lambda path uses an independent `_filter_sensitive_data_substring`
processor whose semantics are asserted behavior-equivalent to the satellite
filter:

- `_SENSITIVE_FIELDS` in `logging_config.py` is
  `{"authorization", "token", "pat", "password", "secret"}` — byte-for-byte
  identical to `SENSITIVE_FIELDS` at `api/middleware/core.py:32` (verified at
  source).
- Substring matching (not exact matching) is the load-bearing property: it
  redacts compound keys (`asana_pat`, `bot_token`, `client_secret`) that the
  `autom8y_log` exact-match default filter would leak.
- `test_substring_filter_matches_satellite_semantics` imports the real
  satellite `_filter_sensitive_data` and asserts identical output on a shared
  payload — an explicit anti-drift guard.

The decoupling rationale is sound: importing the satellite filter directly
would transitively load the FastAPI app surface (~138 modules incl. the frozen
`api.lifespan`), inflating Lambda cold-start and coupling the Lambda image to
the web app. The cost is a maintained copy of the field set with an explicit
sync comment and a behavior-equivalence test. **Residual risk**: the two field
sets can drift; the equivalence test is the only mechanical guard. Acceptable
for ship; flagged in the backlog as a watch item.

## Span-Fidelity Flag Disposition

**DEFER (bundled).** A span-fidelity refinement — richer span-attribute
propagation into log records beyond `trace_id`/`span_id` — is intentionally
out of scope for PR #88. The shippable unit is trace<->log correlation via IDs,
which is sufficient to join LAMBDA-OBS-001 spans to their logs. Expanding to
full attribute propagation would broaden the change beyond frozen-adjacent and
is not required to close the LOG-TRACE-LAMBDA gap. Deferred per
defer-watch discipline; watch-trigger = a debugging incident where ID-only
correlation proves insufficient to attribute a log line to a span's business
context.

## Residual SRE Backlog

These remain OPEN after PR #88. None are regressed by this change; all are
carried forward against the obs.md Instrumentation Gaps Registry.

| ID | Surface | Severity | Status |
|---|---|---|---|
| OTLP-ENDPOINT-OPACITY | OTLP push endpoint + auth-routing-field opaque at satellite level; delegated entirely to platform SDK. No `OTEL_EXPORTER_OTLP_ENDPOINT` in-repo. The Lambda trace backend (X-Ray vs OTLP/Tempo) remains undeclared — correlation now produces IDs whose consumer backend is still unverified. | P2 | OPEN |
| SLO-API-SURFACE | Zero ECS/API SLOs (no latency/availability/error-rate targets for any FastAPI route). Correlation improves debuggability but defines no objective. | P2 | OPEN |
| SAMPLING-UNDOC | No `OTEL_TRACES_SAMPLER` configured in-repo. Sampling delegated to the platform SDK; rate unconfirmed. Correlation is only as complete as the sampled span population — under aggressive sampling, many Lambda invocations emit logs with no parent span and thus no correlation IDs (the no-context passthrough path). | P3 | OPEN |
| CRED-TOPOLOGY-MATRIX | No satellite `credential-topology-matrix` instance; schema exists framework-side only. The 2-axis OTLP auth bifurcation (`stack_id` vs `signal_instance_id`) is undeclared and unverified locally. | P2 | OPEN |

## Disposition

**RATIFIED — PARTIAL.** The span<->log correlation unit ships: wiring is
frozen-adjacent, correlation is proven non-vacuously, sensitive-data redaction
is preserved and behavior-equivalent to the satellite filter, and the
import-ordering invariant is verified safe as committed. Span-fidelity is
deferred (bundled). The four residual backlog items are explicitly carried
forward and do not block this ship.

**Verification at ship**: PR #88 CI in progress (test shards pending; lint,
semantic-score, fleet-conformance, fleet-schema, secrets-scan gates pass at
verdict-authoring time). Disposition is contingent on the Test conclusion
turning green (the deploy gate keys on the whole Test conclusion per the
satellite deploy-gate topology).
