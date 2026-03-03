---
name: release-history-criteria
description: "Criteria for release history knowledge capture. Use when: release specialists (pipeline-monitor) are producing .know/release/history.md documenting release outcomes, CI patterns, and failure classifications. Triggers: release history, release outcomes, CI patterns, failure classification, release knowledge."
---

# Release History Criteria

> Grades the completeness of release outcome history. This is agent-produced knowledge (by pipeline-monitor, not theoros). The goal is to capture release outcomes so subsequent `/release` invocations can learn from past successes and failures.

## Scope

**Producer agent**: pipeline-monitor (release rite specialist)

**Target sources** (what the specialist observes and records):
- Release execution artifacts in `.sos/wip/release/` (ephemeral, per-session)
- CI pipeline run results (pass/fail, duration, failure messages)
- Git tags and release notes
- Post-release verification results
- Failure classifications and recovery actions taken

**Knowledge focus**: Produce a release history log that enables specialists to avoid repeating past mistakes and leverage known-good patterns. The history must answer: What was released when? What succeeded? What failed and why? What patterns recur?

**NOTE**: This domain uses knowledge-capture grading. Grade the COMPLETENESS of historical record, NOT the quality of the releases themselves. A = "a specialist reading this file knows the platform's release track record and can anticipate common failure modes." F = "no historical context available."

## Criteria

### Criterion 1: Release Outcome Log (weight: 40%)

**What to capture**: A structured log of recent releases with outcomes — versions released, repos affected, success/failure status, and timestamps.

**Evidence required**:
- Release date and session identifier
- Repos released with version numbers
- Overall outcome (success, partial success, rollback, aborted)
- Duration from start to completion
- Complexity level used (PATCH, RELEASE, PLATFORM)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | Last 20 releases documented with all fields. Chronologically ordered. Linked to session artifacts where available. |
| B | 80-89% | Most recent releases documented. Some missing duration or complexity fields. |
| C | 70-79% | Release outcomes listed but several fields incomplete. |
| D | 60-69% | Partial log. Major releases missing. |
| F | < 60% | Release log too sparse for pattern recognition. |

---

### Criterion 2: Failure Classification (weight: 30%)

**What to capture**: Categorized failures from past releases — what went wrong, at which stage, in which repo, and how it was resolved.

**Evidence required**:
- Failure category: CI failure, publish failure, dependency conflict, environment issue, test regression, manual error
- Affected repo and pipeline stage
- Root cause description
- Resolution action taken (retry, fix, rollback, skip)
- Recurrence indicator (first occurrence, recurring, resolved)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All failures from logged releases classified with category, root cause, resolution, and recurrence. Patterns identified across failures. |
| B | 80-89% | Most failures classified. Some missing root cause or resolution detail. |
| C | 70-79% | Failures listed but classification incomplete for several. |
| D | 60-69% | Partial failure documentation. No pattern analysis. |
| F | < 60% | Failure history too incomplete to inform future releases. |

---

### Criterion 3: CI Pattern Recognition (weight: 20%)

**What to capture**: Recurring CI behaviors — known flaky tests, token rotation schedules, rate limit patterns, expected pipeline durations.

**Evidence required**:
- Known flaky tests by repo (test name, flake frequency, workaround)
- Token/credential rotation patterns (which tokens, expiry cadence, renewal process)
- Rate limit encounters (which registry/service, typical triggers, cooldown period)
- Expected pipeline durations by repo (baseline for anomaly detection)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | Comprehensive CI quirk catalog with actionable workarounds. Duration baselines established per repo. |
| B | 80-89% | Major CI patterns documented. Some repos missing duration baselines. |
| C | 70-79% | Known flaky tests documented but other patterns sparse. |
| D | 60-69% | Minimal CI pattern documentation. |
| F | < 60% | No CI pattern awareness cached. |

---

### Criterion 4: Trend Summary (weight: 10%)

**What to capture**: High-level release health trends — success rate over time, most problematic repos, improving or degrading patterns.

**Evidence required**:
- Success rate (successful releases / total releases) over the logged period
- Most frequently failing repo or pipeline stage
- Improving trends (failures that stopped recurring after fixes)
- Degrading trends (new or increasing failure patterns)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | Trends computed with supporting data. Clear identification of improving and degrading areas. |
| B | 80-89% | Success rate computed. Problem areas identified. Trend direction noted. |
| C | 70-79% | Basic success rate. Problem repos listed without trend analysis. |
| D | 60-69% | Minimal trend data. |
| F | < 60% | No trend analysis available. |

## History Management

The history file is append-only with a 20-entry cap. When the cap is reached:
1. Archive entries 1-10 into a `## Historical Summary` section (compressed prose, not per-entry)
2. Retain entries 11-20 as the active log
3. Increment the `archive_count` frontmatter field

This ensures the file stays within context window limits while preserving institutional memory.
