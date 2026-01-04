---
artifact_id: {artifact_id}
title: {title}
type: risk-matrix
created_at: {created_at}
author: {author}
status: {status:draft}
schema_version: "1.0"

source_ledger: {source_ledger}

priority_counts:
  critical: {critical_count:0}
  high: {high_count:0}
  medium: {medium_count:0}
  low: {low_count:0}

quick_wins_count: {quick_wins_count:0}

[{session_id: {session_id}}]
[{initiative: {initiative}}]
[{risk_tolerance: {risk_tolerance}}]
---

# {title}

<!-- TEMPLATE GUIDANCE: Replace all {placeholders} with actual values.
     Remove optional sections [{...}] if not needed.
     Strip this comment and all <!-- --> comments in final artifact.

     Scoring Formula: Composite = (Blast Radius * Likelihood) / Effort
     Priority Tiers:
     - Critical: >= 8
     - High: 5.0 - 7.9
     - Medium: 2.0 - 4.9
     - Low: < 2.0
-->

## Executive Summary

<!-- Provide key findings and recommendations in 2-3 sentences -->

{executive_summary}

**Quick Summary:**
- {critical_count} critical priority items
- {high_count} high priority items
- {quick_wins_count} quick wins identified
- Source: {source_ledger}

## Scoring Methodology

**Formula:** `Composite Score = (Blast Radius × Likelihood) / Effort`

### Blast Radius (1-5)

| Score | Impact | Description |
|-------|--------|-------------|
| 5 | Catastrophic | System-wide failure, data loss, security breach |
| 4 | Severe | Multiple modules affected, user-facing errors |
| 3 | Moderate | Single module, degraded functionality |
| 2 | Minor | Edge cases, performance degradation |
| 1 | Minimal | Isolated, cosmetic issues |

### Likelihood (1-5)

| Score | Probability | Description |
|-------|-------------|-------------|
| 5 | Near certain | Already occurring or imminent |
| 4 | Highly likely | Frequently triggered condition |
| 3 | Possible | Occasional trigger in normal operation |
| 2 | Unlikely | Rare scenario or edge case |
| 1 | Rare | Theoretical or untriggered |

### Effort (1-5)

| Score | Investment | Description |
|-------|-----------|-------------|
| 5 | Major | Multi-sprint, architectural changes |
| 4 | Significant | 1-2 sprints, cross-module work |
| 3 | Moderate | Single sprint, focused changes |
| 2 | Minor | Days, isolated changes |
| 1 | Trivial | Hours, config or documentation |

## Risk Matrix

<!-- All scored items with composite priority calculation -->

| ID | Source ID | Description | Blast | Likelihood | Effort | Composite | Priority | Trigger |
|----|-----------|-------------|-------|------------|--------|-----------|----------|---------|
| {id} | {source_id} | {description} | {blast_radius} | {likelihood} | {effort} | {composite} | {priority} | {trigger} |

**Rationale for {id}:**
{rationale}

## Priority Breakdown

### Critical Priority (Score >= 8)

<!-- Items requiring immediate attention -->

**Count:** {critical_count}

| ID | Description | Composite | Trigger |
|----|-------------|-----------|---------|
| {id} | {description} | {composite} | {trigger} |

**Recommended Action:** {action_recommendation}

### High Priority (Score 5.0-7.9)

<!-- Items for near-term planning -->

**Count:** {high_count}

| ID | Description | Composite | Trigger |
|----|-------------|-----------|---------|
| {id} | {description} | {composite} | {trigger} |

### Medium Priority (Score 2.0-4.9)

<!-- Items for backlog -->

**Count:** {medium_count}

| ID | Description | Composite | Trigger |
|----|-------------|-----------|---------|
| {id} | {description} | {composite} | {trigger} |

### Low Priority (Score < 2.0)

<!-- Items for opportunistic cleanup -->

**Count:** {low_count}

| ID | Description | Composite | Trigger |
|----|-------------|-----------|---------|
| {id} | {description} | {composite} | {trigger} |

## Quick Wins

<!-- High value (Blast × Likelihood >= 10), Low effort (Effort <= 2) -->

**Count:** {quick_wins_count}

| ID | Description | Composite | Blast × Likelihood | Effort |
|----|-------------|-----------|-------------------|--------|
| {id} | {description} | {composite} | {value_score} | {effort} |

**Rationale:**
{quick_win_rationale}

[{## Executive Briefing

<!-- OPTIONAL: One-page leadership summary for executive handoff -->

**For Leadership Review**

**Critical Risks:** {critical_count} items requiring immediate action

**High Priority Risks:** {high_count} items for near-term planning

**Quick Wins:** {quick_wins_count} high-value, low-effort opportunities

**Recommended Next Steps:**
1. {recommendation_1}
2. {recommendation_2}
3. {recommendation_3}
}]

[{## Risk Clusters

<!-- OPTIONAL: Related items that can be addressed together -->

### Cluster: {cluster_name}

**Items:** {cluster_item_ids}

**Combined Impact:** {cluster_impact}

**Batching Benefit:** {batching_rationale}

**Recommended Approach:** {cluster_approach}
}]

[{## Assessment Assumptions

<!-- OPTIONAL but recommended: Context and limitations of assessment -->

**Context:**
- {context_item_1}
- {context_item_2}

**Assumptions:**
- {assumption_1}
- {assumption_2}

**Limitations:**
- {limitation_1}
- {limitation_2}

**Risk Tolerance:** {risk_tolerance}
}]
