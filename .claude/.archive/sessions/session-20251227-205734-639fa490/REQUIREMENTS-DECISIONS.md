# Pipeline Automation Expansion: Confirmed Requirements

**Status**: R&D Phase 1 - Discovery COMPLETE
**Date**: 2025-12-27
**Session**: session-20251227-205734-639fa490

---

## Confirmed Decisions

### 1. Trigger Expansion

| Requirement | Decision | Rationale |
|-------------|----------|-----------|
| **Polling granularity** | Daily | Low-frequency batch processing, minimal API usage |
| **Time-based conditions** | All: stale + deadline + age | Full time-condition flexibility per rule |
| **Field-change triggers** | Whitelist specific fields | Performance-optimized, targeted monitoring |
| **Trigger composition** | Full boolean logic | Start with 2-3 conditions, expand later as needed |

**Implications**:
- Need expression evaluator for boolean conditions
- Daily cron-style scheduler (not real-time)
- Field whitelist configuration per rule
- Phased rollout: simple conditions first, nesting later

### 2. Configuration Externalization

| Requirement | Decision | Rationale |
|-------------|----------|-----------|
| **Config audience** | Developers + Ops hybrid | Devs own schema, Ops own values (GIDs, thresholds) |
| **Validation** | Strict - fail on invalid | Prevents silent misconfiguration |
| **Environment overrides** | None needed | Single config, env differences via env vars |
| **Secrets handling** | Environment variables | ${VAR_NAME} references in YAML |
| **Hot reload** | Restart required | Safest, simplest - config loaded at startup only |

**Implications**:
- JSON Schema for YAML validation
- Clear separation: schema (dev-owned) vs. values (ops-owned)
- No file watcher complexity
- Deploy pipeline handles config changes

### 3. Error Recovery

| Requirement | Decision | Rationale |
|-------------|----------|-----------|
| **Partial failures** | Log and continue | Current graceful degradation pattern maintained |
| **API unavailable** | Drop and log | Simple, no persistence layer needed |

**Implications**:
- No retry queue or persistence layer
- Manual replay via logs if needed
- Matches existing philosophy

### 4. Audit Trail

| Requirement | Decision | Rationale |
|-------------|----------|-----------|
| **Storage** | Structured logs only | JSON logs, grep-able, no database dependency |
| **Retention** | 30 days | Operational debugging window |

**Implications**:
- No new database tables
- Log rotation/archival at 30 days
- Entity-centric queries not supported (acceptable)

---

## Requirement Statements (MoSCoW)

### MUST Have (P0)
- [ ] Daily polling scheduler for time-based triggers
- [ ] Stale detection: "Process in section X for N+ days"
- [ ] Deadline proximity: "Due within N days"
- [ ] Age tracking: "Created N+ days ago, still open"
- [ ] Field whitelist configuration per rule
- [ ] YAML configuration with JSON Schema validation
- [ ] Environment variable substitution in YAML
- [ ] Strict validation (fail on invalid config)
- [ ] Structured JSON logging for all automation runs

### SHOULD Have (P1)
- [ ] Boolean AND composition (2-3 conditions)
- [ ] Schema/values separation for Dev/Ops workflow
- [ ] Clear error messages for validation failures
- [ ] Log format suitable for grep/jq queries

### COULD Have (P2)
- [ ] OR composition for triggers
- [ ] Nested boolean expressions
- [ ] Config validation CLI tool
- [ ] Log aggregation recommendations

### WON'T Have (Out of Scope)
- [ ] Minute-level polling
- [ ] Real-time field change detection
- [ ] UI-based rule editing
- [ ] Persistent audit database
- [ ] Automatic retry/queue on API failure
- [ ] Hot reload without restart

---

## Open Questions for Architecture

1. **Expression Evaluator**: Build custom or use existing library (e.g., `pyparsing`, `lark`)?
2. **Scheduler**: Integrate with existing cron or standalone scheduler?
3. **YAML Schema**: JSON Schema draft version? Validation library?
4. **Logging Format**: OpenTelemetry compatible? Custom structured format?

---

## Next Steps

1. **Technology Scout**: Evaluate expression evaluator libraries, YAML/schema tools
2. **Architect**: Design system from these requirements
3. **PRD Finalization**: User stories, acceptance criteria, edge cases
4. **Sprint Planning**: Break into implementable chunks
