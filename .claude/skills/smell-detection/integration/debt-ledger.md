# Debt Ledger Integration

> Schema and patterns for mapping smells to debt ledger entries.

## Overview

Code smells detected by **code-smeller** (hygiene) or **debt-collector** (debt-triage) map to debt ledger entries with preserved references. This enables traceability from smell detection → debt tracking → sprint planning.

## Smell-to-Debt Category Mapping

| Smell Category | Debt Category | Debt ID Prefix | Example Mapping |
|----------------|---------------|----------------|-----------------|
| Dead Code | Code > Dead Code | C042 | DC-FN-001 → C042-001 |
| DRY Violations | Code > Duplication | C043 | DRY-COPY-001 → C043-001 |
| Complexity Hotspots | Code > Complexity | C044 | CX-CYCLO-001 → C044-001 |
| Naming Inconsistencies | Code > Naming | C045 | NM-INCONSIST-001 → C045-001 |
| Import Hygiene | Code > Dependencies | C046 | IM-CIRC-001 → C046-001 |
| Architecture Smells | Design > Coupling | D001 | AR-COUPLE-001 → D001-001 |
| Process Smells | Process > Workflow | P001 | PR-FLAKY-001 → P001-001 |

## Mapping Schema

### Smell Report Entry

```yaml
# Produced by code-smeller or debt-collector
smell_id: DRY-COPY-001
smell_type: DRY-COPY
category: DRY Violations
locations:
  - src/validators/user.ts:45-62
  - src/validators/contact.ts:23-40
description: Duplicate email validation across 2 files
severity: HIGH
priority: P2
score: 14
factors:
  impact: 3
  frequency: 2
  blast_radius: 2
  fix_complexity: 1
context_notes: "Validation runs on every request (hot path)"
detected_at: 2026-01-03T10:30:00Z
detection_method: jscpd (automated)
```

### Corresponding Debt Ledger Entry

```yaml
# Produced by debt-collector, stored in DEBT_LEDGER.yaml
debt_id: C043-001
smell_ref: DRY-COPY-001  # Reference back to smell
category: Code > Duplication
location: src/validators/user.ts:45 (and 1 other)
description: Duplicate email validation across 2 files
evidence: "85% similarity, 18 lines each (smell-detection DRY-COPY heuristic)"
age: 14 months  # From git blame
owner: "@platform-team"
severity: HIGH
priority: P2
score: 14
estimated_effort: 2h
tags:
  - validation
  - duplication
  - hot-path
```

## Integration Points

| Source | Target | Integration Type | Reference Field |
|--------|--------|------------------|-----------------|
| code-smeller (hygiene) | Smell Report | Produces | - |
| debt-collector (debt-triage) | Debt Ledger | Produces | - |
| Smell Report | Debt Ledger | Reference | `smell_ref` field in debt entry |
| Debt Ledger | Sprint Packages | Reference | `debt_id` field in package |
| Sprint Packages | HANDOFF | Reference | `PKG-XXX` field |

## Cross-Rite Workflow

```
smell-detection skill (patterns + severity classification)
        |
        v
+-------------------+     +-------------------+
| code-smeller      |     | debt-collector    |
| (hygiene)    |     | (debt-triage)|
+-------------------+     +-------------------+
        |                         |
        v                         v
  Smell Report              Debt Ledger
  (smell_id)                (debt_id, smell_ref)
        |                         |
        +----------+  +-----------+
                   |  |
                   v  v
            risk-assessor
            (debt-triage)
                   |
                   v
            Sprint Packages
            (PKG-XXX, debt_id)
                   |
                   v
                HANDOFF
```

## Field Mapping Details

### Smell ID to Debt ID

**Pattern**: `{SMELL_TYPE}-{SEQUENCE}` → `{DEBT_PREFIX}-{SEQUENCE}`

| Smell ID | Smell Type | Debt Category | Debt ID |
|----------|------------|---------------|---------|
| DC-FN-003 | DC-FN | Code > Dead Code | C042-003 |
| DRY-COPY-012 | DRY-COPY | Code > Duplication | C043-012 |
| CX-GOD-005 | CX-GOD | Code > Complexity | C044-005 |
| AR-COUPLE-001 | AR-COUPLE | Design > Coupling | D001-001 |
| PR-FLAKY-008 | PR-FLAKY | Process > Workflow | P001-008 |

### Severity and Priority Preservation

Severity and priority calculated by smell-detection skill are **preserved** in debt ledger:

```yaml
# Smell Report
severity: HIGH
priority: P2
score: 14

# Debt Ledger (same values)
severity: HIGH
priority: P2
score: 14
```

**Rationale**: Avoid recalculating severity; smell-detection is the authoritative source.

### Evidence Field Population

The `evidence` field in debt ledger should reference the smell detection method:

```yaml
# From automated detection
evidence: "85% similarity, 18 lines each (smell-detection DRY-COPY heuristic, jscpd)"

# From semi-automated detection
evidence: "15 decision points (smell-detection CX-CYCLO heuristic, eslint-plugin-complexity)"

# From manual detection
evidence: "getUserData() modifies cache (smell-detection NM-MISLEAD heuristic, manual review)"
```

**Pattern**: `{finding_summary} (smell-detection {SMELL_TYPE} heuristic, {detection_method})`

## Agent Responsibilities

### code-smeller (hygiene)

**Produces**: Smell Report
**Uses smell-detection for**:
- Taxonomy: Which smells to detect
- Detection heuristics: How to detect them
- Severity classification: How severe each smell is

**Output**: `docs/quality/SMELL_REPORT.md` with smell entries

### debt-collector (debt-triage)

**Produces**: Debt Ledger
**Uses smell-detection for**:
- Systematic smell detection (same taxonomy as code-smeller)
- Severity classification
- Mapping to debt categories

**Input**: Codebase (or Smell Report from code-smeller)
**Output**: `DEBT_LEDGER.yaml` with debt entries (smell_ref preserved)

### risk-assessor (debt-triage)

**Consumes**: Debt Ledger
**Produces**: Sprint Packages

**Uses**: Severity/priority from smell-detection (already in debt ledger)
**Does NOT**: Recalculate severity; trusts debt-collector's classification

## Example: End-to-End Flow

### Step 1: code-smeller detects smell

```bash
# Invoked by user
Task(code-smeller, "Analyze code quality for src/validators/")

# code-smeller uses smell-detection skill
# - Runs jscpd (DRY-COPY automated detection)
# - Finds 85% similarity between user.ts and contact.ts
# - Calculates severity: score=14, HIGH, P2
# - Writes to SMELL_REPORT.md
```

### Step 2: debt-collector creates ledger entry

```bash
# Invoked by user
Task(debt-collector, "Collect technical debt from src/")

# debt-collector uses smell-detection skill
# - Reads SMELL_REPORT.md (or re-scans codebase)
# - Maps DRY-COPY-001 → C043-001
# - Preserves smell_ref: DRY-COPY-001
# - Writes to DEBT_LEDGER.yaml
```

### Step 3: risk-assessor packages debt

```bash
# Invoked by user
Task(risk-assessor, "Create sprint packages from DEBT_LEDGER.yaml")

# risk-assessor
# - Groups debt entries by priority and theme
# - Creates PKG-003: "Validation Duplication" (contains C043-001)
# - Writes to SPRINT_PACKAGES/PKG-003.yaml
```

### Step 4: HANDOFF to implementation rite

```yaml
# HANDOFF.md
- task: "Consolidate email validation"
  package: PKG-003
  debt_entries: [C043-001]
  smell_refs: [DRY-COPY-001]
  priority: P2
  estimated_effort: 2h
```

## Validation Rules

### Required Fields for Debt Integration

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| smell_id | Yes | Generated | Format: `{TYPE}-{SEQ}` |
| smell_type | Yes | Taxonomy | Must match taxonomy ID pattern |
| severity | Yes | Classification | CRITICAL, HIGH, MEDIUM, LOW |
| priority | Yes | Classification | P1, P2, P3, P4 |
| score | Yes | Classification | 1-21 range |
| factors | Yes | Classification | impact, frequency, blast_radius, fix_complexity |
| debt_id | Yes (ledger) | Generated | Format: `{PREFIX}-{SEQ}` |
| smell_ref | Yes (ledger) | Reference | Must match existing smell_id |

### Integrity Checks

1. **Smell ID uniqueness**: No duplicate smell IDs within a smell report
2. **Debt ID uniqueness**: No duplicate debt IDs within a debt ledger
3. **Smell ref validity**: Every smell_ref in debt ledger must reference an existing smell_id
4. **Category consistency**: Smell category must map to correct debt category
5. **Severity preservation**: Severity/priority/score must match between smell and debt entry

## Related Documentation

- [smell-report.md](smell-report.md) - Smell report format and field requirements
- [../severity/classification.md](../severity/classification.md) - Severity calculation algorithm
- [../taxonomy/](../taxonomy/) - Smell type definitions
- `/docs/testing/e2e-debt-remediation.md` - End-to-end workflow validation
