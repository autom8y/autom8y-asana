# Operational Runbook: Pipeline Automation

**Last updated**: 2025-12-28
**Owner**: Operations Team
**Severity classification**: P2 (Business Impact: Delayed task escalations)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Health Checks](#2-health-checks)
3. [Common Incidents](#3-common-incidents)
4. [Incident Response Procedures](#4-incident-response-procedures)
5. [Maintenance Procedures](#5-maintenance-procedures)
6. [Escalation](#6-escalation)
7. [Metrics and Monitoring](#7-metrics-and-monitoring)

---

## 1. System Overview

### 1.1 Purpose

Pipeline Automation evaluates Asana tasks against time-based rules and executes actions (tagging, commenting, moving sections) once daily. It automates repetitive task management workflows such as escalating stale tasks or warning about approaching deadlines.

### 1.2 Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **PollingScheduler** | `polling_scheduler.py` | Orchestrates daily evaluation cycles |
| **ConfigurationLoader** | `config_loader.py` | Loads YAML, substitutes env vars, validates schema |
| **TriggerEvaluator** | `trigger_evaluator.py` | Matches tasks against rule conditions |
| **ActionExecutor** | `action_executor.py` | Executes add_tag, add_comment, change_section |
| **StructuredLogger** | `structured_logger.py` | JSON-formatted logging for observability |
| **CLI** | `cli.py` | Manual validation, status, and evaluation commands |

### 1.3 Data Flow

```
┌──────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  Cron / APScheduler  │────>│  PollingScheduler │────>│ ConfigurationLoader│
└──────────────────┘     └───────────────────┘     └──────────────────┘
                                   │                         │
                                   │  Load rules.yaml        │
                                   │<────────────────────────┘
                                   │
                                   v
                         ┌───────────────────┐
                         │  TriggerEvaluator │
                         │  (match tasks)    │
                         └───────────────────┘
                                   │
                                   v
                         ┌───────────────────┐     ┌──────────────────┐
                         │   ActionExecutor  │────>│   Asana API      │
                         │  (execute actions)│     │  (tags/stories/  │
                         └───────────────────┘     │   sections)      │
                                   │               └──────────────────┘
                                   v
                         ┌───────────────────┐
                         │ StructuredLogger  │────> stdout (JSON)
                         └───────────────────┘
```

### 1.4 Dependencies

| Dependency | Purpose | Failure Impact |
|------------|---------|----------------|
| **Asana API** | Task queries and action execution | Full outage - actions fail |
| **YAML Config** | Rule definitions | Startup failure |
| **Python 3.10+** | Runtime environment | Cannot start |
| **APScheduler** (dev only) | Blocking scheduler mode | Dev mode unavailable |
| **structlog** (optional) | Enhanced JSON logging | Falls back to stdlib |

### 1.5 Expected Behavior

- **Execution frequency**: Once daily at configured time
- **Typical duration**: 1-30 seconds depending on rule count and task volume
- **Lock behavior**: Only one instance runs at a time (file lock)
- **Error handling**: Graceful degradation - failed rules do not stop other rules

---

## 2. Health Checks

### 2.1 Verify Scheduler Is Running

**For cron-based production deployment:**

```bash
# Check if cron job is scheduled
crontab -l | grep polling_scheduler
```

Expected output:
```
0 2 * * * cd /app && python -m autom8_asana.automation.polling.polling_scheduler /etc/autom8_asana/rules.yaml
```

**For APScheduler development mode:**

```bash
# Check if process is running
ps aux | grep "polling_scheduler.*--dev" | grep -v grep
```

### 2.2 Check Last Execution

```bash
# Find most recent log entry (adjust path to your log location)
grep "evaluation_cycle_complete" /var/log/autom8_asana/automation.log | tail -1 | jq .
```

Expected output:
```json
{
  "timestamp": "2025-12-28T02:00:15.123456Z",
  "event": "evaluation_cycle_complete",
  "rules_evaluated": 5,
  "total_duration_ms": 1234.56
}
```

### 2.3 Validate Configuration

```bash
python -m autom8_asana.automation.polling.cli validate /etc/autom8_asana/rules.yaml
```

Expected output:
```
Configuration valid: 5 rules loaded
```

### 2.4 Show Current Status

```bash
python -m autom8_asana.automation.polling.cli status /etc/autom8_asana/rules.yaml
```

Expected output:
```
Scheduler Configuration:
  Time: 02:00
  Timezone: America/New_York

Rules Summary:
  Total: 5
  Enabled: 4
  Disabled: 1
```

### 2.5 Lock File Status

```bash
# Check if lock file exists and contains recent timestamp
cat /tmp/autom8_asana_polling.lock 2>/dev/null || echo "No lock file (normal if not running)"
```

### 2.6 Log File Locations

| Environment | Log Location |
|-------------|--------------|
| Production (cron) | stdout redirected by cron (check `/var/mail/$USER` or syslog) |
| Production (systemd) | `journalctl -u autom8-polling.service` |
| Development | stdout (terminal) |
| Recommended | Redirect to `/var/log/autom8_asana/automation.log` |

---

## 3. Common Incidents

### 3.1 Incident Classification

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| **P1** | All rules failing, no automation running | 15 minutes |
| **P2** | Multiple rules failing, some automation working | 1 hour |
| **P3** | Single rule failing | 4 hours |
| **P4** | Performance degradation, log warnings | Next business day |

### 3.2 Incident Types

| ID | Incident | Severity | Symptoms |
|----|----------|----------|----------|
| INC-01 | Configuration validation failure | P2 | Scheduler fails to start |
| INC-02 | Asana API rate limiting | P2 | Actions fail with 429 errors |
| INC-03 | Action execution failure | P3 | Specific actions fail (tag/section not found) |
| INC-04 | File lock contention | P3 | "Could not acquire lock" warnings |
| INC-05 | Scheduler not starting | P1 | No evaluation cycles in logs |
| INC-06 | Environment variable missing | P2 | Startup failure with env var error |
| INC-07 | Invalid timezone | P2 | ConfigurationError on startup |

---

## 4. Incident Response Procedures

### 4.1 INC-01: Configuration Validation Failure

**Symptoms:**
- Scheduler exits immediately on startup
- Error message: `Configuration error: ...`

**Triage Steps:**

1. **Check the specific error:**
   ```bash
   python -m autom8_asana.automation.polling.cli validate /etc/autom8_asana/rules.yaml 2>&1
   ```

2. **Common validation errors and fixes:**

   | Error Message | Cause | Fix |
   |---------------|-------|-----|
   | `Configuration file not found` | Wrong path | Verify file exists: `ls -la /path/to/rules.yaml` |
   | `Invalid YAML syntax` | YAML formatting | Check indentation, use `yamllint rules.yaml` |
   | `At least one trigger type required` | Empty conditions | Add stale/deadline/age trigger |
   | `days must be >= 1` | Zero or negative days | Set days to 1 or higher |
   | `rule_id must be non-empty` | Missing rule_id | Add unique rule_id to each rule |
   | `time must be in HH:MM format` | Invalid time | Use 24-hour format like "02:00" |

3. **Validate YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('/etc/autom8_asana/rules.yaml'))"
   ```

4. **Check for tab characters (YAML requires spaces):**
   ```bash
   grep -P '\t' /etc/autom8_asana/rules.yaml && echo "ERROR: Found tabs" || echo "OK: No tabs"
   ```

**Recovery:**
- Fix the configuration error
- Re-run validation
- Restart scheduler

---

### 4.2 INC-02: Asana API Rate Limiting

**Symptoms:**
- Log entries with `"error": "429 Too Many Requests"`
- Actions fail but rules continue evaluating

**Triage Steps:**

1. **Check for rate limit errors:**
   ```bash
   grep -i "429" /var/log/autom8_asana/automation.log | jq -s 'length'
   ```

2. **Identify affected rules:**
   ```bash
   grep "action_failed" /var/log/autom8_asana/automation.log | \
     jq 'select(.error | contains("429")) | {rule_id, task_gid, timestamp}'
   ```

3. **Check request volume:**
   ```bash
   # Count actions per rule in last 24 hours
   grep "action_executed\|action_failed" /var/log/autom8_asana/automation.log | \
     jq -s 'group_by(.rule_id) | map({rule_id: .[0].rule_id, count: length})'
   ```

**Recovery:**

1. **Short-term**: Wait 1-5 minutes for rate limit window to reset
2. **Long-term**:
   - Reduce rule frequency (consider disabling high-volume rules)
   - Optimize conditions to match fewer tasks
   - Stagger rule execution times across multiple config files

**Asana Rate Limits Reference:**
- Standard: 1500 requests per minute
- Batch endpoints have higher limits

---

### 4.3 INC-03: Action Execution Failure

**Symptoms:**
- Log entries with `"event": "action_failed"`
- Specific tasks not receiving expected actions

**Triage Steps:**

1. **Identify failed actions:**
   ```bash
   grep "action_failed" /var/log/autom8_asana/automation.log | tail -10 | jq .
   ```

2. **Common failure causes:**

   | Error Pattern | Cause | Verification |
   |---------------|-------|--------------|
   | `Tag not found` | Invalid tag_gid | Verify tag exists in Asana |
   | `Section not found` | Invalid section_gid | Verify section exists in project |
   | `Not a member` | Permission issue | Check API token permissions |
   | `Task not found` | Task deleted/moved | Task may have been removed |

3. **Verify Asana entity exists:**
   ```bash
   # Check if tag exists (requires asana CLI or API call)
   curl -H "Authorization: Bearer $ASANA_TOKEN" \
     "https://app.asana.com/api/1.0/tags/TAG_GID_HERE"
   ```

**Recovery:**

1. Update configuration with correct GIDs
2. Verify API token has required permissions
3. Re-run evaluation: `python -m autom8_asana.automation.polling.cli evaluate rules.yaml`

---

### 4.4 INC-04: File Lock Contention

**Symptoms:**
- Log message: `Could not acquire lock at /tmp/autom8_asana_polling.lock. Another instance may be running.`
- Evaluation cycles being skipped

**Triage Steps:**

1. **Check for running processes:**
   ```bash
   ps aux | grep polling_scheduler | grep -v grep
   ```

2. **Check lock file age:**
   ```bash
   ls -la /tmp/autom8_asana_polling.lock
   cat /tmp/autom8_asana_polling.lock
   ```

3. **Determine if process is actually running:**
   ```bash
   # Extract PID from lock file (if written)
   cat /tmp/autom8_asana_polling.lock
   # Check if that process exists
   ps -p <PID> 2>/dev/null
   ```

**Recovery:**

If no process is running but lock file exists (stale lock):

```bash
# Remove stale lock file
rm /tmp/autom8_asana_polling.lock

# Verify next execution works
python -m autom8_asana.automation.polling.cli evaluate rules.yaml
```

If multiple cron jobs are overlapping:

```bash
# Check cron schedule
crontab -l | grep polling

# Ensure only one entry exists
# Consider increasing interval or optimizing rule evaluation time
```

---

### 4.5 INC-05: Scheduler Not Starting

**Symptoms:**
- No recent log entries
- Cron job not executing

**Triage Steps:**

1. **Check cron daemon:**
   ```bash
   systemctl status cron  # or crond on some systems
   ```

2. **Check cron logs:**
   ```bash
   grep CRON /var/log/syslog | tail -20
   # or
   journalctl -u cron | tail -20
   ```

3. **Check cron entry syntax:**
   ```bash
   crontab -l | grep polling_scheduler
   ```

4. **Test manual execution:**
   ```bash
   cd /app && python -m autom8_asana.automation.polling.polling_scheduler /etc/autom8_asana/rules.yaml
   ```

5. **Check Python environment:**
   ```bash
   which python
   python --version
   python -c "import autom8_asana"
   ```

**Recovery:**

1. Fix any identified issues (cron syntax, Python path, module import)
2. Re-add cron entry if missing:
   ```bash
   (crontab -l 2>/dev/null; echo "0 2 * * * cd /app && python -m autom8_asana.automation.polling.polling_scheduler /etc/autom8_asana/rules.yaml >> /var/log/autom8_asana/automation.log 2>&1") | crontab -
   ```

---

### 4.6 INC-06: Environment Variable Missing

**Symptoms:**
- Error: `Configuration error: Environment variable 'VAR_NAME' not found`
- Scheduler fails to start

**Triage Steps:**

1. **Identify missing variable:**
   ```bash
   python -m autom8_asana.automation.polling.cli validate /etc/autom8_asana/rules.yaml 2>&1 | grep "Environment variable"
   ```

2. **Check current environment:**
   ```bash
   env | grep -E "ASANA|AUTOM8"
   ```

3. **Check cron environment (cron has minimal env):**
   ```bash
   # Add to top of cron entry or use env file
   SHELL=/bin/bash
   PATH=/usr/local/bin:/usr/bin:/bin
   ```

**Recovery:**

1. Set the required environment variable:
   ```bash
   export VAR_NAME=value
   ```

2. For cron jobs, source an env file:
   ```bash
   0 2 * * * . /etc/autom8_asana/env.sh && cd /app && python -m autom8_asana.automation.polling.polling_scheduler /etc/autom8_asana/rules.yaml
   ```

---

### 4.7 INC-07: Invalid Timezone

**Symptoms:**
- Error: `ConfigurationError: Invalid timezone 'XYZ'. Use IANA timezone names`

**Triage Steps:**

1. **Check configured timezone:**
   ```bash
   grep timezone /etc/autom8_asana/rules.yaml
   ```

2. **Verify IANA timezone name:**
   ```bash
   python -c "from zoneinfo import ZoneInfo; ZoneInfo('America/New_York')"
   ```

3. **List available timezones:**
   ```bash
   python -c "import zoneinfo; print(sorted(zoneinfo.available_timezones())[:20])"
   ```

**Recovery:**

Update configuration with valid IANA timezone:
- `UTC`
- `America/New_York`
- `America/Los_Angeles`
- `Europe/London`
- `Asia/Tokyo`

---

## 5. Maintenance Procedures

### 5.1 Adding New Rules (Safe Rollout)

**Pre-deployment checklist:**

| Step | Command | Expected Result |
|------|---------|-----------------|
| 1. Create rule in staging config | (edit file) | New rule added |
| 2. Validate configuration | `cli validate staging-rules.yaml` | "Configuration valid" |
| 3. Dry-run evaluation | `cli evaluate staging-rules.yaml --dry-run` | Rule appears in output |
| 4. Test with single project | (use test project GID) | Actions execute correctly |
| 5. Deploy to production | (copy to production config) | Rule active |

**Procedure:**

1. **Create the new rule in a staging file:**
   ```yaml
   rules:
     - rule_id: "new-rule-name"
       name: "Human-readable description"
       project_gid: "1234567890123"  # Use test project first
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

2. **Validate:**
   ```bash
   python -m autom8_asana.automation.polling.cli validate staging-rules.yaml
   ```

3. **Dry-run:**
   ```bash
   python -m autom8_asana.automation.polling.cli evaluate staging-rules.yaml --dry-run
   ```

4. **Test execution:**
   ```bash
   python -m autom8_asana.automation.polling.cli evaluate staging-rules.yaml
   ```

5. **Verify actions in Asana** (check test project for expected changes)

6. **Deploy to production:**
   ```bash
   cp staging-rules.yaml /etc/autom8_asana/rules.yaml
   # Next scheduled run will use new config
   ```

---

### 5.2 Modifying Existing Rules

**Procedure:**

1. **Identify current rule state:**
   ```bash
   grep -A 20 "rule_id: \"target-rule\"" /etc/autom8_asana/rules.yaml
   ```

2. **Create backup:**
   ```bash
   cp /etc/autom8_asana/rules.yaml /etc/autom8_asana/rules.yaml.bak.$(date +%Y%m%d)
   ```

3. **Edit the rule** (change conditions, action, etc.)

4. **Validate:**
   ```bash
   python -m autom8_asana.automation.polling.cli validate /etc/autom8_asana/rules.yaml
   ```

5. **Dry-run to preview impact:**
   ```bash
   python -m autom8_asana.automation.polling.cli evaluate /etc/autom8_asana/rules.yaml --dry-run
   ```

6. **Rule takes effect on next scheduled run** (or trigger manual evaluation)

**Rollback if needed:**
```bash
cp /etc/autom8_asana/rules.yaml.bak.YYYYMMDD /etc/autom8_asana/rules.yaml
```

---

### 5.3 Disabling Rules Temporarily

**To disable a single rule:**

1. Edit the configuration file
2. Set `enabled: false` for the target rule
3. Validate the configuration

```yaml
rules:
  - rule_id: "escalate-stale"
    name: "Escalate stale tasks"
    enabled: false  # <-- Temporarily disabled
    ...
```

**To verify disabled state:**
```bash
python -m autom8_asana.automation.polling.cli status /etc/autom8_asana/rules.yaml
# Should show: Disabled: 1 (or more)
```

**To re-enable:**
```bash
# Set enabled: true and validate
python -m autom8_asana.automation.polling.cli validate /etc/autom8_asana/rules.yaml
```

---

### 5.4 Emergency: Disable All Automation

**Option 1: Stop cron job**
```bash
# Comment out the cron entry
crontab -e
# Add # before the line

# Verify
crontab -l | grep polling
```

**Option 2: Rename config file**
```bash
mv /etc/autom8_asana/rules.yaml /etc/autom8_asana/rules.yaml.disabled
```

**Option 3: Disable all rules in config**
```bash
# Set all rules to enabled: false
sed -i 's/enabled: true/enabled: false/g' /etc/autom8_asana/rules.yaml
```

---

### 5.5 Log Rotation

**Recommended logrotate configuration:**

Create `/etc/logrotate.d/autom8_asana`:

```
/var/log/autom8_asana/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 appuser appgroup
}
```

**Manual log rotation:**
```bash
# Rotate current log
mv /var/log/autom8_asana/automation.log /var/log/autom8_asana/automation.log.$(date +%Y%m%d)
gzip /var/log/autom8_asana/automation.log.*

# Cleanup old logs (keep 30 days)
find /var/log/autom8_asana -name "*.log.*.gz" -mtime +30 -delete
```

---

## 6. Escalation

### 6.1 When to Escalate

| Condition | Action |
|-----------|--------|
| P1 incident not resolved in 30 minutes | Escalate to on-call engineer |
| Asana API consistently failing (> 1 hour) | Contact Asana support |
| Data inconsistency (wrong tasks modified) | Escalate immediately |
| Security concern (exposed credentials) | Escalate immediately to security |

### 6.2 Information to Collect Before Escalating

```bash
# Collect diagnostic bundle
mkdir /tmp/autom8-diag-$(date +%Y%m%d%H%M)
cd /tmp/autom8-diag-*

# Configuration (redact secrets)
cp /etc/autom8_asana/rules.yaml config.yaml
sed -i 's/\${[^}]*}/[REDACTED]/g' config.yaml

# Recent logs
tail -1000 /var/log/autom8_asana/automation.log > recent-logs.json

# System state
ps aux | grep autom8 > processes.txt
crontab -l > crontab.txt
python --version > python-version.txt
pip list | grep -E "autom8|asana|pydantic|structlog" > dependencies.txt

# Lock file
ls -la /tmp/autom8_asana_polling.lock >> lock-state.txt 2>&1
cat /tmp/autom8_asana_polling.lock >> lock-state.txt 2>&1

# Bundle
tar -czvf ../autom8-diagnostic-bundle.tar.gz .
```

### 6.3 Escalation Contacts

| Role | Contact | Hours |
|------|---------|-------|
| Primary On-Call | [PLACEHOLDER: on-call rotation] | 24/7 |
| Platform Engineering | [PLACEHOLDER: team channel] | Business hours |
| Asana Support | support@asana.com | Business hours |

---

## 7. Metrics and Monitoring

### 7.1 Key Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Evaluation cycle duration | `total_duration_ms` in logs | > 60000ms (1 min) |
| Rules evaluated per cycle | `rules_evaluated` in logs | < expected count |
| Action success rate | ratio of `action_executed` / total | < 95% |
| Rate limit errors | count of 429 errors | > 0 in 5 min |
| Lock contention events | "Could not acquire lock" | > 0 |
| Configuration validation errors | startup failures | > 0 |

### 7.2 Log Queries for Metrics

**Evaluation duration over time:**
```bash
grep "evaluation_cycle_complete" automation.log | \
  jq '{timestamp, duration_ms: .total_duration_ms}' | \
  tail -100
```

**Action success rate (last 24 hours):**
```bash
grep -E "action_executed|action_failed" automation.log | \
  jq -s '
    group_by(.event) |
    map({event: .[0].event, count: length}) |
    add
  '
```

**Failed rules summary:**
```bash
grep "action_failed" automation.log | \
  jq -s 'group_by(.rule_id) | map({rule_id: .[0].rule_id, failures: length}) | sort_by(-.failures)'
```

**Slow evaluations (> 5 seconds):**
```bash
grep "rule_evaluation_complete" automation.log | \
  jq 'select(.duration_ms > 5000) | {rule_id, rule_name, duration_ms}'
```

### 7.3 Alert Thresholds

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| No evaluation in 26 hours | Last log entry > 26h ago | P1 | Check cron, scheduler health |
| High failure rate | > 5% actions failed | P2 | Investigate specific failures |
| Rate limiting | Any 429 errors | P3 | Reduce request volume |
| Slow evaluation | Duration > 60s | P3 | Optimize rules or reduce scope |
| Lock contention | Any lock failure | P4 | Check for overlapping runs |

### 7.4 Dashboard Suggestions

**Recommended panels:**

1. **Evaluation Health**
   - Time series: Evaluation duration over time
   - Counter: Successful vs failed evaluations (24h)
   - Gauge: Time since last successful evaluation

2. **Rule Performance**
   - Bar chart: Matches per rule (24h)
   - Table: Slowest rules by average duration
   - Heatmap: Rule execution by hour of day

3. **Action Metrics**
   - Pie chart: Actions by type (add_tag, add_comment, change_section)
   - Time series: Action success rate over time
   - Table: Recent failures with error details

4. **System Health**
   - Status indicator: Cron job active
   - Status indicator: Config validation passing
   - Counter: Lock contention events (24h)

**Example Grafana query (if using Loki):**
```logql
{job="autom8-automation"} |= "evaluation_cycle_complete" | json | line_format "{{.total_duration_ms}}"
```

---

## Quick Reference Card

```
# Health check commands
python -m autom8_asana.automation.polling.cli validate rules.yaml
python -m autom8_asana.automation.polling.cli status rules.yaml
python -m autom8_asana.automation.polling.cli evaluate rules.yaml --dry-run

# View recent logs
grep "evaluation_cycle" automation.log | tail -5 | jq .
grep "action_failed" automation.log | tail -10 | jq .

# Lock file management
cat /tmp/autom8_asana_polling.lock
rm /tmp/autom8_asana_polling.lock  # Only if stale

# Emergency disable
mv rules.yaml rules.yaml.disabled

# Rollback
cp rules.yaml.bak.YYYYMMDD rules.yaml
```

---

## Related Documentation

- [Pipeline Automation Setup Guide](../guides/pipeline-automation-setup.md) - Configuration and deployment
- [Pipeline Automation Expansion TDD](../../.claude/.archive/sessions/session-20251227-205734-639fa490/TDD-PIPELINE-AUTOMATION-EXPANSION.md) - Technical design
- Source code: `src/autom8_asana/automation/polling/`
