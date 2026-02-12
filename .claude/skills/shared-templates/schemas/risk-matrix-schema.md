# Risk Matrix Schema

**Version:** 1.0
**Type:** risk-matrix
**File Pattern:** `docs/debt/RM-{slug}.md`

## Purpose

Scored and prioritized debt items produced by Risk Assessor agent.

## YAML Frontmatter Schema

```yaml
---
# Required fields
artifact_id: string        # Pattern: RM-{slug}
title: string              # Human-readable title
type: string               # Must be "risk-matrix"
created_at: string         # ISO 8601 timestamp
author: string             # Creating agent (e.g., "risk-assessor")
status: enum               # draft | final | archived
schema_version: "1.0"      # Schema version

# Source reference
source_ledger: string      # Reference to input Debt Ledger (e.g., "DL-api-cleanup")

# Priority summary
priority_counts:
  critical: integer        # Composite score >= 8
  high: integer            # Composite score 5-7.9
  medium: integer          # Composite score 2-4.9
  low: integer             # Composite score < 2

# Quick wins (high value, low effort)
quick_wins_count: integer

# Optional fields
session_id: string         # Associated session
initiative: string         # Parent initiative
risk_tolerance: string     # Org risk tolerance context
---
```

## Required Sections

| Section | Purpose | Authored By |
|---------|---------|-------------|
| Executive Summary | Key findings and recommendations | risk-assessor |
| Scoring Methodology | Blast radius, likelihood, effort scales | risk-assessor |
| Risk Matrix | Scored items with composite priority | risk-assessor |
| Priority Breakdown | Items by critical/high/medium/low | risk-assessor |
| Quick Wins | High value, low effort items | risk-assessor |

## Optional Sections

| Section | Purpose | When Included |
|---------|---------|---------------|
| Executive Briefing | One-page leadership summary | For leadership handoff |
| Risk Clusters | Related items for batched remediation | When clusters identified |
| Assessment Assumptions | Context and limitations | Always recommended |

## Scored Item Object Schema

```yaml
scored_items:
  - id: string             # From source ledger
    source_id: string      # Original debt item ID
    blast_radius: integer  # 1-5 scale
    likelihood: integer    # 1-5 scale
    effort: integer        # 1-5 scale
    composite: float       # (blast * likelihood) / effort
    priority: enum         # critical | high | medium | low
    trigger: string        # What triggers this risk
    rationale: string      # Why these scores
```

## Scoring Formula

```
Composite = (Blast Radius * Likelihood) / Effort

Priority Tiers:
- Critical: >= 8
- High: 5.0 - 7.9
- Medium: 2.0 - 4.9
- Low: < 2.0
```

## Scoring Dimensions

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

## Validation Rules

1. `artifact_id` MUST match pattern `^RM-[a-z0-9-]+$`
2. `type` MUST be exactly "risk-matrix"
3. `source_ledger` MUST reference existing Debt Ledger
4. `blast_radius`, `likelihood`, `effort` MUST be integers 1-5
5. `composite` MUST equal (blast_radius * likelihood) / effort
6. `priority` MUST match composite score tier
7. Sum of priority_counts MUST equal total scored items

## Version History

| Version | Changes | Migration Required |
|---------|---------|-------------------|
| 1.0 | Initial schema | N/A |
