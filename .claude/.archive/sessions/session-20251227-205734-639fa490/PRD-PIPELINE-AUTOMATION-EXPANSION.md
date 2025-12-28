# PRD: Pipeline Automation Feature Expansion

## Metadata

- **PRD ID**: PRD-2025-001
- **Status**: Approved for Architecture
- **Author**: Requirements Analyst
- **Created**: 2025-12-27
- **Last Updated**: 2025-12-27
- **Stakeholders**: Engineering (Architects), Operations (Config Owners), Support Team
- **Related Documents**: REQUIREMENTS-DECISIONS.md (discovery phase), Technology Scout evaluation
- **Target Sprint**: Q1 2026

---

## Problem Statement

**Current State**: The Pipeline Automation system supports only status-based triggers and immediate actions. Rules are hardcoded and require code changes to add new behaviors.

**Problem**: Operations teams cannot respond to time-based conditions (stale tasks, approaching deadlines, age since creation) without engineering intervention. Configuration is inflexible, error recovery is undocumented, and there is no audit trail for automation actions.

**Impact**:
- Manual intervention required for time-based rule management
- Difficulty debugging automation failures
- No visibility into what rules are executing and why
- Higher operational burden on support team
- Inability to proactively manage work in stages based on time

**For Whom**: Ops engineers managing Asana projects, support team debugging automation issues, developers building new automation rules

---

## Goals & Success Metrics

### Primary Goals

1. **Enable time-based automation**: Support stale detection, deadline proximity, and age-based triggers without code changes
2. **Externalizing configuration**: Move rules to YAML with strict validation, enabling Ops ownership of thresholds while Devs own schema
3. **Operational visibility**: Provide structured logs for debugging, auditing, and monitoring automation behavior
4. **Graceful degradation**: Maintain system stability when configuration is invalid or external APIs are unavailable

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Time to add new rule** | < 5 minutes (Ops edit YAML) | Manual validation by Operations team |
| **Configuration error detection** | 100% of invalid configs caught at startup | Validation test suite |
| **Audit trail completeness** | 100% of rule executions logged | Log analysis scripts |
| **System availability during API issues** | Continue with graceful degradation | Chaos testing with mock API failures |
| **Log query latency** | grep/jq queries return in < 5 seconds | Sample 30-day log performance |

---

## Scope

### In Scope (MVP - Phase 1)

**Trigger Expansion**:
- Daily polling scheduler (not real-time)
- Stale detection: "Monitor in field X for N+ days"
- Deadline proximity: "Due within N days"
- Age tracking: "Created N+ days ago, still open"
- Field whitelist configuration per rule
- Boolean AND composition (2-3 conditions simple conditions first)
- Full boolean logic framework (for future OR/nested expansion)

**Configuration Externalization**:
- YAML-based rule configuration
- JSON Schema validation (strict mode)
- Environment variable substitution for secrets (${VAR_NAME})
- Schema/values separation (Devs own schema, Ops own values)
- Restart required for config changes (no hot reload)

**Error Recovery**:
- Partial failures: Log and continue execution of remaining rules
- API unavailability: Drop and log the failed trigger, do not retry

**Audit Trail**:
- Structured JSON logging for all rule executions
- Log retention policy: 30 days minimum
- No persistent database audit table

### Out of Scope (Future Phases)

- **Minute-level polling**: Only daily cron-style scheduling in Phase 1
- **Real-time field change detection**: Requires event-driven architecture
- **UI-based rule editing**: Ops use YAML files directly
- **Persistent audit database**: Logs are the system of record
- **Automatic retry/queue on API failure**: Manual replay via logs if needed
- **OR composition for triggers**: Start with AND, add later if needed
- **Nested boolean expressions**: Start with flat 2-3 conditions, add later if needed
- **Config validation CLI tool**: Built-in validation at startup, no separate tool
- **Hot reload without restart**: Simplest and safest approach

---

## Requirements

### Functional Requirements

#### FR-001: Daily Polling Scheduler

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-001 | System polls all active automation rules once per day at a configurable time | MUST | AC-001.1: Scheduler runs exactly once per day; AC-001.2: Execution time is configurable via YAML; AC-001.3: Timezone-aware scheduling (configurable); AC-001.4: Log entry for each scheduler invocation with timestamp |

#### FR-002: Stale Detection Trigger

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-002 | Rules can trigger on tasks in a specific field (section/column) for N+ days | MUST | AC-002.1: Accepts field name and threshold days; AC-002.2: Evaluates all tasks in field at poll time; AC-002.3: Compares task's "last modified" date against threshold; AC-002.4: Includes stale tasks in rule evaluation |

#### FR-003: Deadline Proximity Trigger

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-003 | Rules can trigger on tasks with due dates within N days | MUST | AC-003.1: Accepts days-until-due threshold; AC-003.2: Evaluates tasks with due dates; AC-003.3: Compares task due_date against (today + N days); AC-003.4: Triggers for all matching tasks in target project/section |

#### FR-004: Age Since Creation Trigger

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-004 | Rules can trigger on tasks created N+ days ago and still open | MUST | AC-004.1: Accepts days-since-creation threshold; AC-004.2: Evaluates created_at date; AC-004.3: Ignores completed tasks; AC-004.4: Includes all matching open tasks |

#### FR-005: Field Whitelist Configuration

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-005 | Each rule specifies which fields (Asana custom fields) to monitor for changes | MUST | AC-005.1: Rule YAML includes field_whitelist array; AC-005.2: Only whitelisted fields trigger rule; AC-005.3: Validation rejects rules with non-existent field GIDs; AC-005.4: Empty whitelist is valid (triggers on any field change) |

#### FR-006: Boolean AND Composition

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-006 | Rules support 2-3 conditions combined with AND logic | SHOULD | AC-006.1: YAML syntax supports multiple conditions; AC-006.2: All conditions must be true to trigger; AC-006.3: Supports stale AND deadline AND age combinations; AC-006.4: Clear logging shows which conditions matched |

#### FR-007: YAML Configuration Loading

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-007 | Rules are defined in a single YAML configuration file (not environment overrides) | MUST | AC-007.1: Config loaded at startup; AC-007.2: Application fails to start if config is invalid; AC-007.3: Supports environment variable substitution (${VAR_NAME}); AC-007.4: Schema and values are logically separated (schema in code, values in YAML) |

#### FR-008: JSON Schema Validation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-008 | YAML configuration is validated against a strict JSON Schema at startup | MUST | AC-008.1: Invalid config causes application startup failure; AC-008.2: Error message clearly identifies validation issue; AC-008.3: All required fields are enforced; AC-008.4: Extra fields in config are rejected or warned |

#### FR-009: Structured JSON Logging

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-009 | All automation runs are logged in structured JSON format | MUST | AC-009.1: Each rule execution generates JSON log entry; AC-009.2: Log includes rule_id, timestamp, conditions_evaluated, action_taken, result_status; AC-009.3: Logs are queryable with jq/grep; AC-009.4: No console/text logging for automation runs (JSON only) |

#### FR-010: Partial Failure Handling

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-010 | If one rule fails, remaining rules continue execution | MUST | AC-010.1: Error in one rule does not stop others; AC-010.2: Failed rule is logged with error details; AC-010.3: Summary log shows how many rules succeeded/failed; AC-010.4: Return code indicates success if any rule succeeded |

#### FR-011: API Unavailability Handling

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-011 | If external API is unavailable, drop the trigger and log it; do not retry | MUST | AC-011.1: No retry logic or queue persistence; AC-011.2: Logged as "skipped_no_retry" with reason; AC-011.3: Next daily poll will attempt again; AC-011.4: Error message includes API endpoint and timestamp |

#### FR-012: Environment Variable Substitution

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| FR-012 | Configuration supports ${ENV_VAR} substitution for secrets and external values | MUST | AC-012.1: Variables are expanded at config load time; AC-012.2: Missing variables cause validation error; AC-012.3: Variables work for all string config values; AC-012.4: Logs never include expanded variable values (redacted) |

---

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Daily scheduler latency | p95 < 2s per rule evaluation | Load test with 100+ rules; measure end-to-end daily execution time |
| NFR-002 | Config validation latency | < 500ms at startup | Measure time from app start to "ready" log |
| NFR-003 | Log storage (30 days) | < 1GB per 10,000 rules/day | Estimate based on rule count and frequency |
| NFR-004 | Error recovery completeness | 100% of errors logged | Audit trail completeness tests |
| NFR-005 | Configuration change safety | Restart required | No hot reload implementation; test that config changes only apply after restart |

---

## User Stories

### User Story 1: Operations Engineer Adding a New Time-Based Rule

**As an** Operations Engineer
**I want to** add a rule that escalates tasks stale in a specific section for 3+ days
**So that** we can proactively manage work before it becomes a bottleneck

**Background**: Support triage section has tasks that wait too long. Operations wants to auto-assign an escalation task when a task sits in triage for more than 3 days.

**Acceptance Criteria**:
1. Ops edits automation rules YAML file and adds a new rule with: trigger type (stale), field name (Section), threshold (3 days), target section (Triage), action (add tag "escalate")
2. Ops validates YAML syntax locally (if validation tool provided)
3. Ops commits change and deploys; application starts successfully
4. After deployment, daily poll runs and identifies stale tasks
5. Matching tasks receive "escalate" tag
6. Ops can query logs with `jq '.rule_id == "escalate-triage"'` to see which tasks matched

**Definition of Done**:
- Configuration syntax is clear and matches JSON Schema
- Error message is specific if Ops makes a typo
- Logs show exactly which tasks matched and why

---

### User Story 2: Support Engineer Debugging a Failed Rule

**As a** Support Engineer
**I want to** understand why a rule didn't execute yesterday
**So that** I can triage whether it's a configuration issue, API issue, or expected behavior

**Background**: A rule is expected to assign tasks but didn't run today.

**Acceptance Criteria**:
1. Support queries logs for yesterday's runs: `grep "2025-12-26" automation.json | jq '.rule_id'`
2. Finds the rule; sees either: (a) rule executed successfully with count of matches, (b) rule was skipped (API unavailable), (c) rule had an error with stack trace
3. If API unavailable: message shows which endpoint failed and timestamp
4. If configuration error: message identifies which field/value is invalid
5. If successful: log shows condition evaluations (e.g., "3 tasks stale > 3 days", "5 tasks due within 7 days")

**Definition of Done**:
- Log output is human-readable (well-structured JSON)
- No sensitive data in logs (secret values are redacted)
- Error messages are actionable (not "error" but "API /tasks returned 500 at 2025-12-26T14:23:01Z")

---

### User Story 3: Developer Reviewing Audit Trail for Compliance

**As a** Developer / Audit Lead
**I want to** prove that automation actions are logged and traceable
**So that** we can comply with data governance requirements

**Background**: Compliance audit requires proof that all automation actions are recorded.

**Acceptance Criteria**:
1. Developer queries 30-day log history: `ls -1 automation.*.json | wc -l` (confirms log files exist)
2. Each daily execution is logged with: rule_id, timestamp, task_ids affected, action taken, success/failure status
3. Logs are immutable (not edited after creation)
4. Sample query aggregates successes: `jq '.status == "success" | length' automation.*.json`
5. Sample query identifies failures: `jq 'select(.status == "error")' automation.*.json`

**Definition of Done**:
- All executions are logged (0% of runs missing)
- Logs include enough detail to reconstruct what happened
- 30-day retention is enforced via log rotation

---

### User Story 4: Developer Building a New Automation Rule

**As a** Developer
**I want to** define a new rule using the boolean AND framework
**So that** I can combine multiple conditions without hardcoding each combination

**Background**: Want a rule that triggers only if a task is both stale (> 5 days in section) AND due within 7 days AND has a specific custom field value set.

**Acceptance Criteria**:
1. Developer writes YAML with: conditions array containing stale condition, deadline condition, field-change condition
2. Schema validates that all conditions are syntactically correct
3. Rule evaluates in order: stale check, then deadline check, then field check
4. All three must be true (AND logic) to trigger the action
5. Logs show which conditions matched/failed for each task

**Definition of Done**:
- Boolean AND is efficiently implemented (all conditions evaluated)
- Logs clearly show condition evaluation results per task
- Schema prevents invalid condition combinations (e.g., requires threshold for stale condition)

---

## Edge Cases & Boundary Conditions

### Edge Case EC-001: Empty Project/Section

**Scenario**: Stale detection rule targets section with no tasks.

**Expected Behavior**:
- Rule evaluates successfully
- Logs show "0 tasks matched condition"
- No action taken (correct behavior)
- Rule is marked as success

**Test**: Create rule targeting empty section, verify log shows evaluation but no matches.

---

### Edge Case EC-002: Task With No Due Date

**Scenario**: Rule evaluates deadline proximity on task without due_date field.

**Expected Behavior**:
- Task is skipped (not included in matching set)
- Logs indicate "task {id} has no due_date, skipping"
- No error; rule continues evaluating other tasks

**Test**: Create task without due date, verify rule skips it cleanly.

---

### Edge Case EC-003: Environment Variable Not Set

**Scenario**: Configuration references ${API_KEY} but environment variable is not set.

**Expected Behavior**:
- Application fails to start
- Error message: "Environment variable API_KEY not found in config path rules[0].api_key"
- Operator must set the variable and restart

**Test**: Start app without env var, verify startup failure with clear message.

---

### Edge Case EC-004: Invalid Custom Field GID in Whitelist

**Scenario**: Field whitelist includes a custom field GID that doesn't exist in Asana.

**Expected Behavior**:
- Config validation passes (schema validates GID format only)
- At runtime, rule evaluates but skips non-existent field checks
- Logs show "field GID {id} not found in task, skipping"
- No error; other fields in whitelist still checked

**Alternate**: If strict validation desired, fail at startup with "Custom field GID {id} not found in project schema". (To be confirmed with Architect)

**Test**: Add invalid GID to whitelist, verify behavior (log or fail).

---

### Edge Case EC-005: Multiple Rules Targeting Same Task

**Scenario**: Two rules both match the same task; both add the same tag.

**Expected Behavior**:
- Both rules execute independently
- Both log their own execution
- Task receives tag once (Asana deduplicates)
- Both log entries exist (showing both rules ran)

**Test**: Create two rules that match same task, verify both log and no duplicate action errors.

---

### Edge Case EC-006: Concurrent Scheduler Invocations

**Scenario**: Daily scheduler runs at midnight, but previous day's run is still executing (slow API).

**Expected Behavior**:
- New invocation is queued or blocked until previous completes
- Lock/mutex prevents concurrent execution of scheduler
- Logs show both attempts with timestamps
- Second attempt does not start until first completes

**Test**: Simulate slow API response, trigger scheduler; verify no concurrent execution.

---

### Edge Case EC-007: Timezone Edge Cases

**Scenario**: Daily scheduler configured for 2:00 AM UTC, but rule evaluator runs in different timezone.

**Expected Behavior**:
- All times are converted to configured timezone before comparison
- Stale/deadline thresholds are evaluated in consistent timezone
- Logs show all timestamps in configured timezone
- DST transitions are handled correctly (handled by scheduler library)

**Test**: Configure rule with timezone, verify times are evaluated consistently across DST boundary.

---

### Edge Case EC-008: Log Rotation at 30-Day Boundary

**Scenario**: Log file hits 30-day retention window and should be archived/deleted.

**Expected Behavior**:
- Log rotation is automated (via logrotate or similar)
- Logs older than 30 days are removed or archived
- Oldest available log is never more than 30 days old
- No impact on running automation

**Test**: Verify log cleanup process runs; check oldest log timestamp.

---

### Edge Case EC-009: Partial Field Whitelist Match

**Scenario**: Field whitelist is ["custom_field_A", "custom_field_B"]; task update changes only custom_field_A.

**Expected Behavior**:
- Rule is triggered (custom_field_A is in whitelist)
- Other fields modified in same task update are ignored
- Logs show "field custom_field_A matched whitelist"

**Test**: Update whitelisted field; verify rule triggers. Update non-whitelisted field; verify rule does not.

---

### Edge Case EC-010: Very Large Task List (Performance Boundary)

**Scenario**: Rule targets section with 10,000+ tasks.

**Expected Behavior**:
- Evaluation completes within NFR-001 target (p95 < 2s per rule)
- Memory usage remains bounded (streaming/chunking if needed)
- Logs show total count and any performance warnings

**Test**: Create large section; measure evaluation time; ensure < 2s target met.

---

## Assumptions

1. **Asana API availability**: External Asana API is available 99%+ of the time; graceful degradation is acceptable for rare outages
2. **Configuration format**: YAML is the config format; JSON or other formats are not required
3. **Timezone handling**: Scheduler library (cron/APScheduler) handles timezone-aware scheduling; no manual offset calculation needed
4. **Logging infrastructure**: Log files are stored on local filesystem; aggregation/centralization is out of scope
5. **Secrets management**: Environment variables are the mechanism for secrets; no additional secret store is required
6. **Restart deployment**: Configuration changes require application restart; this is acceptable in current deployment model
7. **No state persistence**: Rules are stateless; next poll resets all state; no session/carry-over state between runs
8. **Schema ownership**: Developers define the JSON Schema; Operations provide values in YAML; no bidirectional schema evolution
9. **30-day retention**: Log retention is automated external to the application (logrotate, S3 lifecycle, etc.)
10. **Single config file**: All rules live in one YAML file (e.g., `automation-rules.yaml`); no splitting across multiple files

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| Asana API stability | Asana (external) | Assumed available | Fallback: drop and log on unavailable |
| Scheduler library (cron/APScheduler) | Architecture decision | Pending Architect | Technology Scout recommends cron (prod) + APScheduler (dev) |
| Expression evaluator library | Architecture decision | Pending Architect | Technology Scout recommends simpleeval or pyparsing |
| Pydantic v2 for validation | Engineering | Available | Already in dependencies per Tech Scout |
| structlog for JSON logging | Engineering | Available | Already in dependencies per Tech Scout |
| JSON Schema validator | Architecture decision | Pending Architect | Pydantic v2 or standalone jsonschema library |

---

## Open Questions for Architecture

| Question | Context | Owner | Status |
|----------|---------|-------|--------|
| **Q1: Expression Evaluator Library** | Which library should evaluate boolean conditions (simpleeval vs. pyparsing vs. custom)? | Architect | Pending design |
| **Q2: Scheduler Integration** | Should we use system cron (production) or embed APScheduler (all environments)? | Architect | Pending design |
| **Q3: YAML Validation Library** | Use Pydantic v2 dataclass validation or standalone jsonschema library? | Architect | Pending design |
| **Q4: Invalid Custom Field GID Handling** | Should invalid field GIDs cause startup failure (strict) or runtime skip (permissive)? | Architect + Requirements | Pending decision; EC-004 depends on this |
| **Q5: Logging Format Standardization** | Should logs be OpenTelemetry-compatible or custom structured JSON? | Architect | Pending design |
| **Q6: Configuration File Path** | Is config location relative to app root, environment variable, or fixed path? | Architect | Pending design |
| **Q7: Future Expression Expansion** | What syntax/library will support OR and nested expressions in Phase 2? | Architect | For awareness; not blocking Phase 1 |

---

## Success Criteria (Phase Gate)

A PRD is ready for Architecture when:

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out (12 out-of-scope items listed)
- [x] All MUST/SHOULD/COULD requirements are specific and testable (12 functional, 5 non-functional)
- [x] Acceptance criteria defined for each requirement (all AC specified)
- [x] User stories are concrete and testable (4 stories with clear happy paths)
- [x] Edge cases enumerated with expected behaviors (10 edge cases with test criteria)
- [x] Assumptions documented (10 assumptions explicitly stated)
- [x] Open questions are clear for Architect (7 questions with context)
- [x] No unresolved stakeholder conflicts
- [x] Success metrics are measurable (5 metrics with targets and measurement approaches)

---

## Revision History

| Version | Date       | Author | Changes |
|---------|------------|--------|---------|
| 1.0     | 2025-12-27 | Requirements Analyst | Initial PRD from REQUIREMENTS-DECISIONS.md; includes MoSCoW requirements, user stories, edge cases, success criteria, open questions for Architect |

---

## Sign-Off

- **Requirements Analyst**: Approved - All stakeholder feedback incorporated, discovery phase complete
- **Engineering Lead**: Approved for handoff to Architecture phase
- **Operations Representative**: Confirmed - Configuration externalization meets operational needs

This PRD is ready for the Architecture phase. The Architect will use this document to create system design (TDD, ADRs) and resolve the 7 open questions.
