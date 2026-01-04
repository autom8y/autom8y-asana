# Debt Ledger Schema

**Version:** 1.0
**Type:** debt-ledger
**File Pattern:** `docs/debt/DL-{slug}.md`

## Purpose

Structured inventory of technical debt produced by Debt Collector agent.

## YAML Frontmatter Schema

```yaml
---
# Required fields
artifact_id: string        # Pattern: DL-{slug}
title: string              # Human-readable title
type: string               # Must be "debt-ledger"
created_at: string         # ISO 8601 timestamp
author: string             # Creating agent (e.g., "debt-collector")
status: enum               # draft | final | archived
schema_version: "1.0"      # Schema version

# Audit scope
scope:
  directories: array       # Paths audited
  categories: array        # Categories included (code, doc, test, infra, design)
  exclusions: array        # Paths or patterns excluded

# Summary statistics
statistics:
  total_items: integer     # Total debt items found
  by_category:
    code: integer
    doc: integer
    test: integer
    infra: integer
    design: integer
  by_type: object          # Breakdown by specific type

# Optional fields
session_id: string         # Associated session
initiative: string         # Parent initiative
previous_ledger: string    # Reference to baseline for diff
---
```

## Required Sections

| Section | Purpose | Authored By |
|---------|---------|-------------|
| Executive Summary | 2-3 sentence overview | debt-collector |
| Audit Scope | What was audited, exclusions | debt-collector |
| Debt Inventory | Categorized items with ID, location, description | debt-collector |
| Summary Statistics | Counts by category and type | debt-collector |
| Audit Limitations | Known gaps or incomplete areas | debt-collector |

## Optional Sections

| Section | Purpose | When Included |
|---------|---------|---------------|
| Debt Diff | Comparison to previous ledger | When `previous_ledger` specified |
| Ownership Report | Items grouped by owner | When ownership data available |

## Debt Item Object Schema

```yaml
debt_items:
  - id: string             # "C042", "D007", etc.
    location: string       # file:line or module path
    category: enum         # code | doc | test | infra | design
    type: string           # Specific type (e.g., "hardcoded", "missing-doc")
    description: string    # What the debt is
    age: string            # How old (optional, from git blame)
    owner: string          # Responsible party (optional)
    related: array         # Related item IDs (optional)
    evidence: string       # Quote or reference (optional)
```

## Validation Rules

1. `artifact_id` MUST match pattern `^DL-[a-z0-9-]+$`
2. `type` MUST be exactly "debt-ledger"
3. `status` MUST be one of: draft, final, archived
4. `statistics.total_items` MUST equal sum of category counts
5. `scope.categories` MUST be non-empty array
6. Each item in Debt Inventory MUST have id, location, category, description

## Category Definitions

| Category | Description | Example Types |
|----------|-------------|---------------|
| code | Production code issues | hardcoded, duplication, complexity |
| doc | Documentation gaps | missing-doc, outdated-doc, incomplete-api |
| test | Test coverage and quality | missing-test, flaky-test, insufficient-coverage |
| infra | Infrastructure and tooling | deprecated-dependency, config-drift, missing-automation |
| design | Architectural and design debt | tight-coupling, missing-abstraction, pattern-violation |

## Version History

| Version | Changes | Migration Required |
|---------|---------|-------------------|
| 1.0 | Initial schema | N/A |
