# SCOUT: Structured Logging Format for Pipeline Automation

## Problem Statement

Pipeline automation needs structured logging for:
- grep/jq compatibility (operators need to query logs quickly)
- Log aggregation readiness (CloudWatch, Datadog, etc.)
- 30-day retention requirement (external, but format affects storage)
- Consistency with existing project patterns

**Key Constraints** (from stakeholder requirements):
- Structured logs only (no unstructured text)
- grep/jq compatibility for ad-hoc queries
- Aggregation-ready for alerting and dashboards
- Match existing project patterns

## Options Evaluated

| Option | Maturity | Ecosystem | Fit | Risk |
|--------|----------|-----------|-----|------|
| **structlog with JSON** | High (2013+) | Strong | High | Low |
| **OpenTelemetry logs** | Medium (2019+) | Growing | Medium | Medium |
| **python-json-logger** | High (2013+) | Moderate | Medium | Low |
| **Custom JSON format** | N/A (DIY) | None | Low | Medium |

## Analysis

### Option 1: structlog with JSON

**Pros:**
- **Already in use in this project** (api optional dependency)
- Bound loggers carry context across calls
- Processors for filtering, formatting, enrichment
- ConsoleRenderer for dev, JSONRenderer for prod
- Context variables for request correlation
- 3K+ GitHub stars, active maintenance

**Cons:**
- Learning curve for processor pipeline
- Requires initial configuration

**Fit Assessment:** Strong fit. Already used in API layer, proven patterns exist in codebase.

### Option 2: OpenTelemetry Logs

**Pros:**
- Part of CNCF observability standard
- Unified with traces and metrics
- Growing ecosystem support
- Automatic correlation IDs

**Cons:**
- Still maturing (logs API is newer than traces/metrics)
- Heavier setup (collectors, exporters)
- Overkill for single-service automation
- Not currently used in project

**Fit Assessment:** Medium fit. Would be good for distributed systems; overkill for daily batch job.

### Option 3: python-json-logger

**Pros:**
- Simple wrapper around stdlib logging
- Minimal API surface
- Just makes logging.Logger emit JSON
- 1.7K GitHub stars

**Cons:**
- Less flexible than structlog
- No bound loggers (context must be passed explicitly)
- Less processor/filter sophistication

**Fit Assessment:** Medium fit. Simpler than structlog but less powerful. Project already uses structlog.

### Option 4: Custom JSON Format

**Pros:**
- Full control
- Zero dependencies beyond stdlib

**Cons:**
- Reinventing the wheel
- Inconsistent with existing project patterns
- Maintenance burden for edge cases (unicode, exceptions, etc.)

**Fit Assessment:** Low fit. structlog already solves this well.

## Recommendation

**Verdict**: Adopt

**Choice**: structlog with JSON output (extend existing pattern)

**Rationale:**

1. **Matches stakeholder requirements:**
   - Structured logs only: JSONRenderer produces machine-readable JSON
   - grep/jq compatibility: Each log line is valid JSON, jq queries work directly
   - Aggregation-ready: CloudWatch Logs Insights, Datadog, etc. parse JSON natively
   - Match existing patterns: API layer already uses structlog (see middleware.py)

2. **Already in use:**
   - `structlog>=24.1.0` in api optional dependency
   - `configure_structlog()` pattern exists in `api/middleware.py`
   - Sensitive data filtering processor already implemented

3. **Implementation sketch:**

   ```python
   # automation/logging.py
   import structlog
   from typing import Any

   def configure_automation_logging(debug: bool = False) -> None:
       """Configure structured logging for automation layer.

       Mirrors API layer configuration but for CLI/automation context.
       """
       processors = [
           structlog.stdlib.add_log_level,
           structlog.stdlib.add_logger_name,
           structlog.processors.TimeStamper(fmt="iso"),
           _add_automation_context,  # Add trigger_id, run_id, etc.
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.processors.UnicodeDecoder(),
       ]

       if debug:
           processors.append(structlog.dev.ConsoleRenderer())
       else:
           processors.append(structlog.processors.JSONRenderer())

       structlog.configure(
           processors=processors,
           wrapper_class=structlog.stdlib.BoundLogger,
           context_class=dict,
           logger_factory=structlog.stdlib.LoggerFactory(),
           cache_logger_on_first_use=True,
       )

   def _add_automation_context(
       logger: Any,
       method_name: str,
       event_dict: dict,
   ) -> dict:
       """Add automation-specific context to all log events."""
       # These could be set via structlog.contextvars
       return event_dict

   logger = structlog.get_logger(__name__)
   ```

4. **Log format example:**

   ```json
   {"event": "trigger_run_started", "level": "info", "logger": "autom8_asana.automation.cli", "timestamp": "2025-01-15T06:00:00.123456Z", "run_id": "abc123"}
   {"event": "trigger_evaluated", "level": "info", "logger": "autom8_asana.automation.engine", "timestamp": "2025-01-15T06:00:01.234567Z", "run_id": "abc123", "trigger_id": "stale_opportunities", "matched_count": 42}
   {"event": "action_executed", "level": "info", "logger": "autom8_asana.automation.engine", "timestamp": "2025-01-15T06:00:02.345678Z", "run_id": "abc123", "trigger_id": "stale_opportunities", "task_gid": "123456789", "action": "move_to_section", "target_section": "Follow Up"}
   {"event": "api_error", "level": "error", "logger": "autom8_asana.automation.engine", "timestamp": "2025-01-15T06:00:03.456789Z", "run_id": "abc123", "trigger_id": "stale_opportunities", "task_gid": "987654321", "error": "Rate limit exceeded", "retry_after": 60}
   {"event": "trigger_run_completed", "level": "info", "logger": "autom8_asana.automation.cli", "timestamp": "2025-01-15T06:00:30.567890Z", "run_id": "abc123", "triggers_evaluated": 5, "tasks_matched": 127, "actions_succeeded": 125, "actions_failed": 2}
   ```

5. **grep/jq examples:**

   ```bash
   # Find all errors in today's log
   jq 'select(.level == "error")' /var/log/autom8/triggers.log

   # Count actions per trigger
   jq 'select(.event == "action_executed") | .trigger_id' /var/log/autom8/triggers.log | sort | uniq -c

   # Find all rate limit errors
   jq 'select(.error | contains("Rate limit"))' /var/log/autom8/triggers.log

   # Get all events for a specific run
   jq 'select(.run_id == "abc123")' /var/log/autom8/triggers.log

   # Simple grep for task GID
   grep '"task_gid":"123456789"' /var/log/autom8/triggers.log
   ```

6. **Dependency profile:**
   - structlog already in api extras
   - Move to core dependencies or add automation extras group

   ```toml
   [project.optional-dependencies]
   automation = [
       "structlog>=24.1.0",
   ]
   ```

## Standard Log Events

Define consistent event names for easy aggregation:

| Event | Level | Fields | Description |
|-------|-------|--------|-------------|
| `trigger_run_started` | info | run_id | Daily run begins |
| `config_loaded` | info | run_id, trigger_count | Config validated |
| `trigger_evaluated` | info | run_id, trigger_id, matched_count | Trigger evaluation complete |
| `action_executed` | info | run_id, trigger_id, task_gid, action | Successful action |
| `action_failed` | warning | run_id, trigger_id, task_gid, action, error | Action failed (continue) |
| `api_error` | error | run_id, trigger_id, error, retry_after | API outage/rate limit |
| `trigger_run_completed` | info | run_id, summary stats | Daily run ends |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Log volume too high | Medium | Low | Log at appropriate levels; DEBUG for verbose |
| Missing context fields | Medium | Low | Bound logger pattern carries context |
| Inconsistent event names | Medium | Medium | Document standard events, code review |
| Log parsing changes break dashboards | Low | Medium | Version field in logs, gradual rollout |

## Decision Summary

| Criterion | structlog | python-json-logger | OpenTelemetry |
|-----------|-----------|-------------------|---------------|
| Already a dependency | Yes (api) | No | No |
| grep/jq compatible | Yes | Yes | Yes |
| Bound loggers | Yes | No | Yes |
| Processor pipeline | Yes | Limited | Yes |
| Learning curve | Low (already used) | Very low | Medium |
| Ecosystem fit | Matches existing | Would diverge | Overkill |

**Bottom line:** Use structlog. It is already in the project, provides excellent JSON output, and the API layer has established patterns to follow. The ConsoleRenderer/JSONRenderer switch makes dev/prod parity easy.

## Integration with Existing Code

The project's `DefaultLogProvider` in `_defaults/log.py` uses stdlib logging. For automation:

1. **Option A:** Add structlog as core dependency, use everywhere
2. **Option B:** Keep DefaultLogProvider for SDK, structlog for automation layer

Recommendation: **Option B** - keeps SDK dependency-light while automation layer gets full structlog benefits. The automation layer is always deployed with the api extras anyway.
