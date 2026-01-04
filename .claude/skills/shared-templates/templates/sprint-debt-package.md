---
artifact_id: {artifact_id}
title: {title}
type: sprint-debt-package
created_at: {created_at}
author: {author}
status: {status:draft}
schema_version: "1.0"

source_matrix: {source_matrix}

capacity:
  total_hours: {total_hours}
  buffer_percent: {buffer_percent:20}
  allocated_hours: {allocated_hours}

package_count: {package_count}
total_effort_hours: {total_effort_hours}

sprint:
  name: {sprint_name}
  start_date: {start_date}
  end_date: {end_date}

[{session_id: {session_id}}]
[{initiative: {initiative}}]
[{target_team: {target_team}}]
---

# {title}

<!-- TEMPLATE GUIDANCE: Replace all {placeholders} with actual values.
     Remove optional sections [{...}] if not needed.
     Strip this comment and all <!-- --> comments in final artifact.

     Size Guidelines:
     - XS: 1-2h (config, small fix)
     - S: 2-4h (single file)
     - M: 4-8h (multiple files)
     - L: 8-16h (cross-module)
     - XL: 16-32h (significant refactor)

     Confidence adjustments:
     - high: 1.0x (known work)
     - medium: 1.25-1.5x (some unknowns)
     - low: 1.5-2.0x (significant unknowns)
-->

## Executive Summary

<!-- Provide sprint goals and key packages overview -->

{executive_summary}

**Sprint:** {sprint_name} ({start_date} to {end_date})
**Source:** {source_matrix}
**Packages:** {package_count}
**Total Effort:** {total_effort_hours}h

## Capacity Model

**Available Capacity:** {total_hours}h
**Buffer:** {buffer_percent}% ({buffer_hours}h)
**Allocated:** {allocated_hours}h
**Remaining:** {remaining_hours}h

**Utilization:** {utilization_percent}%

[{**Notes:** {capacity_notes}}]

## Work Packages

<!-- Detailed package specifications with acceptance criteria -->

### {package_id}: {package_title}

**Priority:** {priority}
**Size:** {size} ({effort_hours}h)
**Confidence:** {confidence}
**Sprint:** {sprint_target}

**Source Items:**
- {source_item_id}: {source_item_description}

[{**Dependencies:**
- {dependency_package_id}: {dependency_description}
}]

**Acceptance Criteria:**
- [ ] {criterion_1}
- [ ] {criterion_2}
- [ ] {criterion_3}

[{**Owner:** {owner}}]

[{**Notes:**
{package_notes}
}]

---

## Dependency Map

<!-- Visual or table representation of package dependencies -->

```
{package_id} → {dependency_package_id}
{package_id} → {dependency_package_id}
```

**Dependency Analysis:**
- {dependency_insight_1}
- {dependency_insight_2}

**Recommended Sequencing:**
1. {package_id} ({reason})
2. {package_id} ({reason})
3. {package_id} ({reason})

## Acceptance Criteria Summary

<!-- Roll-up of all acceptance criteria across packages -->

**Total Criteria:** {total_criteria_count}

### {package_id}
- [ ] {criterion}
- [ ] {criterion}

### {package_id}
- [ ] {criterion}
- [ ] {criterion}

[{## Deferred Items

<!-- OPTIONAL: Items not included with rationale -->

**Count:** {deferred_count}

| ID | Description | Priority | Reason for Deferral |
|----|-------------|----------|---------------------|
| {item_id} | {description} | {priority} | {deferral_reason} |

**When to Revisit:**
- {revisit_condition_1}
- {revisit_condition_2}
}]

[{## HANDOFF

<!-- OPTIONAL: Cross-team handoff artifact when target_team specified -->

**To:** {target_team}
**From:** {author}
**Date:** {created_at}

### Context

{handoff_context}

### Deliverables

{handoff_deliverables}

### Success Criteria

{handoff_success_criteria}

### Support Available

{handoff_support}

### Questions/Concerns

{handoff_questions}
}]

[{## Capacity Scenarios

<!-- OPTIONAL: What-if planning alternatives -->

### Scenario: {scenario_name}

**Assumptions:**
- {assumption_1}
- {assumption_2}

**Adjusted Packages:**
- {package_id}: {adjustment}

**Impact:**
- Total effort: {scenario_effort_hours}h
- Utilization: {scenario_utilization_percent}%

**Recommendation:** {scenario_recommendation}
}]

## Package Reference

<!-- Quick lookup table for all packages -->

| ID | Title | Size | Hours | Priority | Sprint | Dependencies |
|----|-------|------|-------|----------|--------|--------------|
| {package_id} | {title} | {size} | {effort_hours} | {priority} | {sprint_target} | {deps} |

## Effort Distribution

**By Size:**
- XS: {xs_count} packages ({xs_hours}h)
- S: {s_count} packages ({s_hours}h)
- M: {m_count} packages ({m_hours}h)
- L: {l_count} packages ({l_hours}h)
- XL: {xl_count} packages ({xl_hours}h)

**By Priority:**
- Critical: {critical_count} packages ({critical_hours}h)
- High: {high_count} packages ({high_hours}h)
- Medium: {medium_count} packages ({medium_hours}h)
- Low: {low_count} packages ({low_hours}h)

**By Confidence:**
- High: {high_conf_count} packages ({high_conf_hours}h)
- Medium: {med_conf_count} packages ({med_conf_hours}h)
- Low: {low_conf_count} packages ({low_conf_hours}h)
