# Smell Report Format

> Field requirements and structure for smell report documents.

## Overview

Smell reports are produced by **code-smeller** (hygiene) and document code quality issues discovered through systematic smell detection. This document specifies required fields, format, and validation rules.

**Template Location**: `.claude/skills/doc-ecosystem/templates/smell-report.md`

## Required Fields

### Smell Entry Schema

Each smell in the report must include:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `smell_id` | string | Yes | Unique identifier: `{TYPE}-{SEQ}` | `DRY-COPY-001` |
| `smell_type` | string | Yes | Smell type ID from taxonomy | `DRY-COPY` |
| `category` | string | Yes | Smell category name | `DRY Violations` |
| `locations` | list | Yes | File paths and line numbers | `["src/file.ts:45-62"]` |
| `description` | string | Yes | Human-readable summary | `Duplicate email validation across 2 files` |
| `severity` | string | Yes | CRITICAL, HIGH, MEDIUM, LOW | `HIGH` |
| `priority` | string | Yes | P1, P2, P3, P4 | `P2` |
| `score` | integer | Yes | Severity score (1-21) | `14` |
| `factors` | object | Yes | Severity factors | See below |
| `detected_at` | datetime | Yes | ISO 8601 timestamp | `2026-01-03T10:30:00Z` |
| `detection_method` | string | Yes | Automated, Semi-Automated, Manual + tool | `jscpd (automated)` |
| `context_notes` | string | No | Contextual information | `Hot path: runs on every request` |

### Factors Object

```yaml
factors:
  impact: 3           # 1-3 scale
  frequency: 2        # 1-3 scale
  blast_radius: 2     # 1-3 scale
  fix_complexity: 1   # 1-3 scale
```

## Report Structure

### Frontmatter

```yaml
---
title: Code Smell Report
scope: src/validators/
generated_at: 2026-01-03T10:30:00Z
generated_by: code-smeller (hygiene)
total_smells: 12
severity_breakdown:
  critical: 2
  high: 4
  medium: 5
  low: 1
categories:
  - Dead Code
  - DRY Violations
  - Complexity Hotspots
  - Naming Inconsistencies
---
```

### Category Sections

Organize smells by category in the report:

```markdown
## Dead Code

### DC-FN-001: Unused function formatPhoneNumber

**Location**: src/utils/formatters.ts:67-82
**Severity**: LOW (P4)
**Score**: 4

Detected via: grep (automated)

Function `formatPhoneNumber` has zero call sites in the codebase.

**Factors**:
- Impact: 1 (no runtime effect)
- Frequency: 1 (rarely causes issues)
- Blast Radius: 1 (single file)
- Fix Complexity: 1 (safe to delete)

**Recommendation**: Remove function after verifying it's not used via dynamic calls.

---

## DRY Violations

### DRY-COPY-001: Duplicate email validation

**Location**:
- src/validators/user.ts:45-62
- src/validators/contact.ts:23-40

**Severity**: HIGH (P2)
**Score**: 14

Detected via: jscpd (automated)

85% similarity across 18 lines each. Email validation logic duplicated in two validators.

**Factors**:
- Impact: 3 (bugs multiply across instances)
- Frequency: 2 (occasional inconsistency)
- Blast Radius: 2 (2 files)
- Fix Complexity: 1 (extract to shared function)

**Context**: Hot path - validation runs on every user/contact request.

**Recommendation**: Extract to shared `validators/shared/email.ts` module.
```

## Field Validation Rules

### smell_id Format

- **Pattern**: `{TYPE}-{SEQUENCE}`
- **Type**: Must match taxonomy ID pattern (DC-, DRY-, CX-, NM-, IM-, AR-, PR-)
- **Sequence**: Zero-padded 3-digit number (001, 002, etc.)
- **Uniqueness**: Must be unique within report

**Valid**: `DRY-COPY-001`, `CX-CYCLO-012`, `AR-COUPLE-003`
**Invalid**: `COPY-001` (missing prefix), `DRY-1` (not zero-padded), `DRY-COPY` (missing sequence)

### smell_type Validation

Must match one of 42 defined smell types from taxonomy:

| Category | Valid Types |
|----------|-------------|
| Dead Code | DC-FN, DC-VAR, DC-UNREACH, DC-MOD, DC-IMP, DC-BRANCH, DC-COMMENT |
| DRY Violations | DRY-COPY, DRY-CONST, DRY-PARA, DRY-CFG, DRY-TEST |
| Complexity | CX-CYCLO, CX-NEST, CX-GOD, CX-PARAM, CX-BOOL, CX-PRIM, CX-ENVY |
| Naming | NM-INCONSIST, NM-MISLEAD, NM-CONV, NM-ABBREV, NM-TYPE |
| Imports | IM-CIRC, IM-WILD, IM-DEEP, IM-BARREL, IM-VERSION, IM-UNUSED |
| Architecture | AR-LEAK, AR-COUPLE, AR-LAYER, AR-MISSING, AR-SHOT, AR-DIVERGE |
| Process | PR-TEST, PR-FLAKY, PR-SLOW, PR-DOCS, PR-TODO, PR-SKIP |

### Severity and Priority Alignment

| Severity | Priority | Score Range |
|----------|----------|-------------|
| CRITICAL | P1 | 16-21 |
| HIGH | P2 | 11-15 |
| MEDIUM | P3 | 6-10 |
| LOW | P4 | 1-5 |

**Validation**: Severity, priority, and score must be consistent per classification.md rules.

### detection_method Format

- **Pattern**: `{tool_or_approach} ({detection_type})`
- **Detection type**: automated, semi-automated, manual

**Examples**:
- `jscpd (automated)`
- `eslint-plugin-complexity (automated)`
- `git blame analysis (semi-automated)`
- `code review (manual)`

## Example: Complete Smell Entry

```yaml
smell_id: AR-COUPLE-001
smell_type: AR-COUPLE
category: Architecture Smells
locations:
  - src/services/payment.ts
  - src/services/order.ts
  - src/services/inventory.ts
description: Tight coupling between payment, order, and inventory services
severity: CRITICAL
priority: P1
score: 18
factors:
  impact: 3
  frequency: 3
  blast_radius: 3
  fix_complexity: 3
detected_at: 2026-01-03T14:22:00Z
detection_method: madge dependency analysis (semi-automated)
context_notes: |
  - Payment service directly imports 15 functions from order service
  - Order service imports 8 functions from inventory service
  - Circular dependency between payment and order
  - Refactoring requires introducing event-based decoupling
```

## Integration with Debt Ledger

Smell reports serve as input to debt-collector:

1. **code-smeller** produces smell report with above fields
2. **debt-collector** reads smell report (or re-scans codebase)
3. **debt-collector** creates debt ledger entries with `smell_ref` pointing to `smell_id`

See [debt-ledger.md](debt-ledger.md) for mapping details.

## Quality Checks

Before finalizing a smell report, validate:

- [ ] All required fields present for each smell
- [ ] smell_id format is valid and unique
- [ ] smell_type matches taxonomy
- [ ] Severity/priority/score are consistent
- [ ] Factors are in 1-3 range
- [ ] Locations include file paths and line numbers
- [ ] detection_method specifies tool and type
- [ ] Frontmatter summary matches smell count

## Related Documentation

- [../taxonomy/](../taxonomy/) - Smell type definitions
- [../severity/classification.md](../severity/classification.md) - Severity calculation
- [debt-ledger.md](debt-ledger.md) - Integration with debt tracking
- `/.claude/skills/doc-ecosystem/templates/smell-report.md` - Template
