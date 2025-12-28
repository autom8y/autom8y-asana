# Pipeline Automation Setup Guide

This guide explains how to configure and run the Pipeline Automation system for time-based task management in Asana.

## Overview

Pipeline Automation enables daily, time-based automation rules that evaluate tasks and execute actions without code changes. It supports:

- **Stale detection**: Find tasks that have not been modified in N days
- **Deadline proximity**: Identify tasks due within N days
- **Age tracking**: Locate tasks created N+ days ago that remain open
- **Combined triggers**: Compose multiple conditions with AND logic

**When to use Pipeline Automation**:

- Escalating tasks stuck in triage sections
- Warning about approaching deadlines
- Archiving old open tasks
- Automating repetitive task management workflows

**Key characteristics**:

- Runs once daily at a configurable time (not real-time)
- Configuration lives in YAML (Operations owns values, Developers own schema)
- All executions are logged in structured JSON format
- Graceful degradation on API failures (no retry, logged and continued)

---

## Quick Start

Get your first automation rule running in under 5 minutes.

### Prerequisites

- Python 3.10+
- Access to Asana project GIDs (found in project URLs)
- Environment configured with Asana API credentials

### Minimal Configuration

Create a configuration file at `config/pipeline-rules.yaml`:

```yaml
scheduler:
  time: "02:00"
  timezone: "UTC"

rules:
  - rule_id: "my-first-rule"
    name: "Tag stale tasks in Triage"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "Section"
          days: 3
    action:
      type: "add_tag"
      params:
        tag_gid: "9876543210987"
    enabled: true
```

### Validate Configuration

```bash
python -m autom8_asana.automation.polling.cli validate config/pipeline-rules.yaml
```

Expected output:
```
Configuration valid: 1 rules loaded
```

### Preview Actions (Dry Run)

```bash
python -m autom8_asana.automation.polling.cli evaluate config/pipeline-rules.yaml --dry-run
```

This shows which rules would execute without making changes.

### Run Evaluation

```bash
python -m autom8_asana.automation.polling.cli evaluate config/pipeline-rules.yaml
```

---

## Configuration Reference

### YAML Structure

The configuration file has two main sections:

```yaml
scheduler:      # When to run daily evaluation
  time: "HH:MM"
  timezone: "IANA_TIMEZONE"

rules:          # List of automation rules
  - rule_id: "unique-id"
    name: "Human-readable name"
    project_gid: "asana_project_gid"
    conditions: [...]
    action: {...}
    enabled: true|false
```

### Scheduler Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `time` | string | Yes | Time of day in 24-hour format (HH:MM). Example: `"02:00"`, `"14:30"` |
| `timezone` | string | Yes | IANA timezone name. Examples: `"UTC"`, `"America/New_York"`, `"Europe/London"`, `"Asia/Tokyo"` |

```yaml
scheduler:
  time: "02:00"
  timezone: "America/New_York"
```

### Rule Definition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rule_id` | string | Yes | Unique identifier for logging and debugging. Must be non-empty. |
| `name` | string | Yes | Human-readable name shown in logs. |
| `project_gid` | string | Yes | Asana project GID to evaluate. Find in project URL or Asana API. |
| `conditions` | list | Yes | One or more conditions (combined with AND logic). |
| `action` | object | Yes | Action to execute when all conditions match. |
| `enabled` | boolean | No | Whether rule is active. Default: `true`. |

### Trigger Types

#### Stale Trigger (`stale`)

Matches tasks that have not been modified in N or more days.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field` | string | Yes | Field to monitor (e.g., `"Section"`). Currently uses `modified_at` date. |
| `days` | integer | Yes | Number of days threshold. Must be >= 1. Task is stale if not modified in N+ days. |

```yaml
conditions:
  - stale:
      field: "Section"
      days: 3
```

**How it works**: Compares task's `modified_at` timestamp against `today - N days`. Tasks modified on or before that threshold are considered stale.

#### Deadline Trigger (`deadline`)

Matches tasks with due dates within N days from today.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `days` | integer | Yes | Number of days from today. Must be >= 1. Task matches if due date <= today + N days. |

```yaml
conditions:
  - deadline:
      days: 7
```

**How it works**: Checks both `due_at` (datetime) and `due_on` (date). Tasks due today or in the next N days match. Tasks without due dates are skipped.

#### Age Trigger (`age`)

Matches tasks created N or more days ago that are still open (not completed).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `days` | integer | Yes | Number of days since creation. Must be >= 1. |

```yaml
conditions:
  - age:
      days: 90
```

**How it works**: Compares task's `created_at` against `today - N days`. Completed tasks are always excluded.

#### Field Whitelist (Optional)

Restrict trigger evaluation to specific custom fields:

```yaml
conditions:
  - stale:
      field: "Section"
      days: 3
    field_whitelist:
      - "1205678901234567"  # Custom field GID
```

When specified, only changes to whitelisted fields are considered. An empty list or omitting `field_whitelist` triggers on any field change.

### Action Types

#### Add Tag (`add_tag`)

Adds a tag to matching tasks.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_gid` | string | Yes | Asana tag GID to add. |

```yaml
action:
  type: "add_tag"
  params:
    tag_gid: "1234567890123456"
```

#### Add Comment (`add_comment`)

Adds a comment to matching tasks.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Comment text to add. |

```yaml
action:
  type: "add_comment"
  params:
    text: "This task is stale. Please review and update status."
```

#### Change Section (`change_section`)

Moves matching tasks to a different section.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `section_gid` | string | Yes | Target section GID. |

```yaml
action:
  type: "change_section"
  params:
    section_gid: "9876543210987654"
```

### Environment Variable Substitution

Use `${VAR_NAME}` syntax for values that should come from environment variables:

```yaml
action:
  type: "add_tag"
  params:
    tag_gid: "${ESCALATION_TAG_GID}"
```

**Rules**:
- Variables are expanded at configuration load time
- Missing variables cause a startup failure with a clear error message
- Variable names must match pattern: `[A-Z_][A-Z0-9_]*`
- Substituted values are never logged (security redaction)

---

## Common Scenarios

### Scenario 1: Escalate Stale Tasks

Automatically tag tasks that have been sitting in Triage for too long.

```yaml
rules:
  - rule_id: "escalate-stale-triage"
    name: "Escalate stale triage tasks"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "Section"
          days: 3
    action:
      type: "add_tag"
      params:
        tag_gid: "9876543210987"
    enabled: true
```

**What happens**: Tasks in the project not modified for 3+ days receive the escalation tag.

### Scenario 2: Deadline Warning Comments

Add a comment to tasks approaching their due date.

```yaml
rules:
  - rule_id: "deadline-warning"
    name: "Flag approaching deadlines"
    project_gid: "1234567890123"
    conditions:
      - deadline:
          days: 7
    action:
      type: "add_comment"
      params:
        text: "Reminder: This task is due within 7 days. Please review priority."
    enabled: true
```

**What happens**: Tasks due within the next 7 days receive a reminder comment.

### Scenario 3: Age-Based Section Moves

Move old tasks to an archive section.

```yaml
rules:
  - rule_id: "archive-old-tasks"
    name: "Archive very old open tasks"
    project_gid: "9876543210987"
    conditions:
      - age:
          days: 90
    action:
      type: "change_section"
      params:
        section_gid: "1111222233334444"
    enabled: true
```

**What happens**: Tasks created 90+ days ago that are still open are moved to the Archive section.

### Scenario 4: Combined Triggers (AND Composition)

Escalate tasks that are both stale AND have an upcoming deadline.

```yaml
rules:
  - rule_id: "urgent-stale-tasks"
    name: "Urgent attention for stale tasks with deadlines"
    project_gid: "1234567890123"
    conditions:
      # Condition 1: Task is stale
      - stale:
          field: "Section"
          days: 5

      # Condition 2: Task has upcoming deadline
      - deadline:
          days: 14
    action:
      type: "add_comment"
      params:
        text: "URGENT: This task is stale and has an upcoming deadline. Please review immediately."
    enabled: true
```

**What happens**: Only tasks that match BOTH conditions (stale for 5+ days AND due within 14 days) receive the comment. This is AND logic - all conditions must be true.

---

## CLI Commands

All commands use the module path `autom8_asana.automation.polling.cli`.

### validate

Check configuration syntax and schema validity.

```bash
python -m autom8_asana.automation.polling.cli validate <config_path>
```

**Arguments**:
- `config_path`: Path to YAML configuration file

**Exit codes**:
- `0`: Configuration valid
- `1`: Validation failed

**Example output (success)**:
```
Configuration valid: 5 rules loaded
```

**Example output (failure)**:
```
Configuration error: rules.0.conditions.0: At least one trigger type (stale, deadline, or age) is required
```

### status

Show scheduler configuration and rule summary.

```bash
python -m autom8_asana.automation.polling.cli status <config_path>
```

**Example output**:
```
Scheduler Configuration:
  Time: 02:00
  Timezone: America/New_York

Rules Summary:
  Total: 5
  Enabled: 4
  Disabled: 1
```

### evaluate

Run one evaluation cycle.

```bash
python -m autom8_asana.automation.polling.cli evaluate <config_path> [--dry-run]
```

**Arguments**:
- `config_path`: Path to YAML configuration file
- `--dry-run`: Preview what would happen without executing actions

**Dry-run output**:
```
[DRY RUN] Would evaluate 4 enabled rules...

  Rule: escalate-stale-triage
    Name: Escalate stale triage tasks
    Project GID: 1234567890123
    Conditions: 1
    Action: add_tag

  Rule: deadline-warning
    Name: Flag approaching deadlines
    Project GID: 1234567890123
    Conditions: 1
    Action: add_tag

[DRY RUN] Skipping actual evaluation (use without --dry-run to execute)
```

**Live execution output**:
```
Starting evaluation cycle at 2025-12-28T02:00:01.234567+00:00
Evaluating 4 enabled rules...

Evaluation completed in 1.23 seconds
```

---

## Deployment

### Development Mode (APScheduler)

For local development and testing, use the built-in APScheduler:

```bash
python -m autom8_asana.automation.polling.polling_scheduler config/pipeline-rules.yaml --dev
```

This runs a blocking scheduler that executes the evaluation at the configured time daily. Press Ctrl+C to stop.

**Requirements**: Install APScheduler (`pip install apscheduler>=3.10.0`)

### Production Mode (Cron)

For production, use system cron for reliability and observability:

```bash
# Add to crontab
0 2 * * * cd /app && python -m autom8_asana.automation.polling.polling_scheduler /etc/autom8_asana/rules.yaml
```

The scheduler runs once and exits (no `--dev` flag). Each cron invocation:
1. Acquires a file lock to prevent concurrent execution
2. Evaluates all enabled rules
3. Logs results
4. Releases lock and exits

**Lock file location**: `/tmp/autom8_asana_polling.lock` (configurable via `--lock-path`)

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AUTOM8_RULES_CONFIG` | Path to configuration file (alternative to CLI argument) | No |
| Custom variables | Any `${VAR_NAME}` references in YAML | Yes, if used |

---

## Troubleshooting

### Common Errors

#### "Configuration file not found"

```
Configuration error: Configuration file not found: /path/to/rules.yaml
```

**Fix**: Verify the file path exists and is readable.

#### "Invalid YAML syntax"

```
Configuration error: Invalid YAML syntax in config file: line 10: expected '<document start>'
```

**Fix**: Check YAML formatting. Common issues include:
- Incorrect indentation (YAML uses spaces, not tabs)
- Missing colons after keys
- Unquoted special characters

#### "At least one trigger type required"

```
Config validation failed: rules.0.conditions.0: At least one trigger type (stale, deadline, or age) is required
```

**Fix**: Each condition must specify at least one trigger (`stale`, `deadline`, or `age`).

#### "Environment variable not found"

```
Configuration error: Environment variable 'API_KEY' not found in config path rules[0].action.params.token
```

**Fix**: Set the required environment variable before starting:
```bash
export API_KEY=your_value
```

#### "days must be >= 1"

```
Config validation failed: rules.0.conditions.0.stale.days: days must be >= 1
```

**Fix**: The `days` threshold must be at least 1.

#### "Missing required params"

```
ValueError: Missing required params for 'add_tag': ['tag_gid']
```

**Fix**: Ensure all required parameters are provided in the action's `params` section.

### Log Interpretation

Logs are output in structured JSON format. Key fields:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp (UTC) |
| `rule_id` | Which rule was evaluated |
| `status` | `success`, `error`, or `skipped_no_retry` |
| `matches` | Number of tasks that matched conditions |
| `duration_ms` | Evaluation time in milliseconds |
| `error` | Error message (if status is error) |

**Example log entry**:
```json
{
  "timestamp": "2025-12-28T02:00:01.234Z",
  "event": "rule_evaluation",
  "rule_id": "escalate-stale-triage",
  "rule_name": "Escalate stale triage tasks",
  "project_gid": "1234567890123",
  "matches": 3,
  "duration_ms": 456.78
}
```

**Query logs with jq**:
```bash
# Find failed rules
jq 'select(.status == "error")' automation.json

# Count matches per rule
jq -s 'group_by(.rule_id) | map({rule_id: .[0].rule_id, total_matches: map(.matches) | add})' automation.json

# Find slow evaluations (> 2 seconds)
jq 'select(.duration_ms > 2000)' automation.json
```

### Lock File Issues

If you see "Could not acquire lock... Another instance may be running":

1. Check if another process is running: `ps aux | grep polling_scheduler`
2. If no process is running, the lock may be stale. Remove it:
   ```bash
   rm /tmp/autom8_asana_polling.lock
   ```

### Tasks Not Matching

If rules are not matching expected tasks:

1. **Check task dates**: Run `--dry-run` and verify task `modified_at`, `created_at`, and `due_on` values
2. **Verify project GID**: Ensure the rule targets the correct project
3. **Check enabled status**: Confirm `enabled: true` in the rule configuration
4. **Review conditions**: Use AND logic - all conditions must match

---

## Related Resources

- **Source code**: `src/autom8_asana/automation/polling/`
- **Example config**: `config/pipeline-rules.yaml.example`
- **PRD**: PRD-PIPELINE-AUTOMATION-EXPANSION
- **TDD**: TDD-PIPELINE-AUTOMATION-EXPANSION

---

## Quick Reference Card

```
# Validate config
python -m autom8_asana.automation.polling.cli validate rules.yaml

# Show status
python -m autom8_asana.automation.polling.cli status rules.yaml

# Dry run
python -m autom8_asana.automation.polling.cli evaluate rules.yaml --dry-run

# Live evaluation
python -m autom8_asana.automation.polling.cli evaluate rules.yaml

# Development scheduler (blocking)
python -m autom8_asana.automation.polling.polling_scheduler rules.yaml --dev

# Production cron entry
0 2 * * * python -m autom8_asana.automation.polling.polling_scheduler /etc/rules.yaml
```
