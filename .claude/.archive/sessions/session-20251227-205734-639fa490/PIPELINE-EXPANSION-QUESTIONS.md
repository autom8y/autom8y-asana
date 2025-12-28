# Pipeline Automation Expansion: Discovery Questions

**Status**: R&D Phase 1 - Discovery
**Date**: 2025-12-27
**Objective**: Elicit requirements for pipeline automation expansion before specification

---

## 1. Trigger Expansion

The current system only triggers on `section_changed` events when a Process moves to CONVERTED. We need to understand requirements for additional trigger types.

### Proposed Default: Cron-style scheduling with hourly granularity

Time-based triggers would run on a polling schedule (e.g., hourly) and evaluate conditions against entity state at poll time.

**Q1.1**: The default polling interval is **hourly**. Is that sufficient, or do you need minute-level granularity for time-sensitive workflows (e.g., SLA escalation)?

**Q1.2**: For time-based triggers, what conditions should be evaluated? Examples:
- "Process has been in ACTIVE section for 30+ days" (stale detection)
- "Due date is within 7 days and status is not COMPLETED" (deadline approaching)
- Something else?

**Q1.3**: For field-change triggers, should we watch **all custom fields**, or a **whitelist of specific fields**? Watching all fields has performance implications; a whitelist is more targeted but requires configuration.

**Q1.4**: When a field changes, should we capture the **old value and new value** for use in automation logic (e.g., "only trigger if status changed FROM 'Pending' TO 'Approved'")?

**Q1.5**: Should multiple trigger types be combinable? For example: "When section changes to ACTIVE **AND** assignee is empty, then auto-assign." This adds complexity but enables richer rules.

---

## 2. Configuration Externalization

Currently, pipeline rules are defined in Python code (`PipelineConversionRule`, `PipelineStage`). Moving to YAML enables non-developer configuration changes without code deploys.

### Proposed Default: Single YAML file with schema validation, reload on file change

Rules would be defined in a `pipeline-rules.yaml` file, validated against a JSON Schema, and reloaded when the file changes (inotify/polling).

**Q2.1**: Who will be editing the YAML configuration?
- Developers only (deploy-time changes acceptable)
- Operations team (needs hot-reload without restart)
- End users via UI (requires database storage, not YAML)

**Q2.2**: Should we support **environment-specific overrides**? For example: `pipeline-rules.yaml` (base) + `pipeline-rules.staging.yaml` (overrides for staging). This adds merge complexity.

**Q2.3**: What validation strictness do you need?
- **Strict**: Invalid YAML = system refuses to start
- **Warn**: Invalid rules are skipped with warnings, valid rules still run
- **Fallback**: On invalid YAML, fall back to last known good config

**Q2.4**: For hot-reload, what is the acceptable delay between file change and rule activation? Default: **5 seconds** (polling interval). Real-time requires file watchers with complexity.

**Q2.5**: Should secrets (e.g., assignee GIDs, project GIDs) be referenced from environment variables in YAML, or is inline configuration acceptable for your security posture?

---

## 3. Error Recovery

The current implementation has "graceful degradation" - failures in non-critical steps (comment creation, assignee setting) are logged but don't block the conversion. We need to understand recovery requirements.

### Proposed Default: Fail-forward with audit log, no automatic retry

When a step fails, log it, continue with remaining steps, and record the partial state for manual review.

**Q3.1**: For **partial failures** (e.g., task created but assignee not set), is manual remediation acceptable, or do you need:
- Automatic retry with exponential backoff?
- Compensation/rollback (delete the partially-created task)?
- Notification to ops team for intervention?

**Q3.2**: If the Asana API is unavailable (rate limit, outage), should the system:
- **Queue and retry**: Buffer events and replay when API recovers (requires persistence)
- **Drop and log**: Lose the event but log for manual replay later
- **Block and alert**: Stop processing until API recovers (affects all events)

**Q3.3**: For time-based triggers, if a poll cycle fails (e.g., can't read project state), should we:
- Skip that cycle and try again next interval?
- Retry immediately with backoff?
- Alert if N consecutive failures occur?

---

## 4. Audit Trail

The current `AutomationResult` captures actions executed, entities created/updated, and timing. We need to understand observability requirements.

### Proposed Default: Structured JSON logs with entity GIDs and timestamps

Each automation run produces a structured log entry that can be queried/aggregated.

**Q4.1**: Beyond logging, do you need a **persistent audit table** (database) for:
- Compliance/regulatory review?
- Historical analysis ("what automations affected this entity?")?
- Debugging ("why is this task in the wrong section?")

**Q4.2**: For audit entries, how long should they be retained? Options:
- 30 days (operational debugging)
- 1 year (business analysis)
- Indefinite (compliance requirement)

**Q4.3**: Should the audit trail be **queryable by entity**? For example: "Show me all automations that touched Business X in the last 90 days." This requires indexing and adds storage/query complexity.

---

## 5. Proposed Sensible Defaults Summary

For your reaction - these are starting points, not commitments:

| Area | Default | Why This Default |
|------|---------|------------------|
| **Trigger polling** | Hourly | Balances freshness vs. API quota usage |
| **Field watching** | Whitelist | Performance; most workflows care about specific fields |
| **YAML location** | `config/pipeline-rules.yaml` | Conventional config directory |
| **Schema validation** | Strict (fail on invalid) | Prevents silent misconfiguration |
| **Hot-reload interval** | 5 seconds | Fast enough for ops, not expensive |
| **Error handling** | Fail-forward, log, continue | Matches current graceful degradation philosophy |
| **Retry policy** | No automatic retry | Keeps system simple; failures are rare |
| **Audit storage** | Structured logs only | No database dependency; grep-able |
| **Audit retention** | 30 days | Operational debugging window |

---

## Next Steps

After you provide answers to these questions:

1. **Consolidate answers** into requirement statements (MUST/SHOULD/COULD/WONT)
2. **Identify conflicts** between answers and surface tradeoffs
3. **Draft PRD** with user stories, acceptance criteria, and edge cases
4. **Handoff to Architect** for technical design (TDD/ADR)

**Estimated timeline**:
- Discovery answers: You (1-2 days to review and respond)
- PRD draft: Requirements Analyst (1 day after answers received)
- Architecture review: Architect (1-2 days after PRD)

---

## Questions for Clarification

If any question above is unclear, please tell me:
- Which question number
- What part is confusing
- What context would help you answer

I can rephrase or provide examples.
