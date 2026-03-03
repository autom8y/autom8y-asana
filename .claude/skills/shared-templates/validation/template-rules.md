# Template Validation Rules

**Version:** 1.0
**Purpose:** Validation logic for shared template artifacts

## Overview

This document defines validation rules for the three shared template types:
- Debt Ledger (DL)
- Risk Matrix (RM)
- Sprint Debt Package (SDP)

Validation occurs post-generation to ensure artifacts meet schema requirements and handoff criteria.

## General Validation Rules

### All Templates

1. **Frontmatter Required**: YAML frontmatter MUST be present and parseable
2. **Required Fields**: All required fields MUST be present and non-empty
3. **Schema Version**: `schema_version` MUST be present and valid (e.g., "1.0")
4. **Type Match**: `type` field MUST match expected template type
5. **Status Enum**: `status` MUST be one of allowed values for template type
6. **ISO 8601 Dates**: All date fields MUST use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
7. **Artifact ID Pattern**: `artifact_id` MUST match template-specific pattern
8. **No Placeholder Residue**: Required placeholders `{field}` MUST be replaced
9. **Guidance Comments Stripped**: Template comments `<!-- ... -->` SHOULD be removed in final artifact
10. **Optional Sections**: Optional sections `[{...}]` MUST be removed entirely if unused, or fully populated if included

## Debt Ledger Validation Rules

### Rule DL-V001: Artifact ID Pattern
- **Field**: `artifact_id`
- **Validation**: MUST match regex `^DL-[a-z0-9-]+$`
- **Example**: "DL-api-cleanup", "DL-test-gaps-2024"
- **Error**: "Invalid artifact_id: must match pattern DL-{slug}"

### Rule DL-V002: Type Field
- **Field**: `type`
- **Validation**: MUST be exactly "debt-ledger"
- **Error**: "Invalid type: must be 'debt-ledger'"

### Rule DL-V003: Status Enum
- **Field**: `status`
- **Validation**: MUST be one of: draft, final, archived
- **Error**: "Invalid status: must be draft, final, or archived"

### Rule DL-V004: Statistics Total Match
- **Fields**: `statistics.total_items`, `statistics.by_category.*`
- **Validation**: `total_items` MUST equal sum of all category counts
- **Formula**: `total_items == code + doc + test + infra + design`
- **Error**: "Statistics mismatch: total_items ({total}) != sum of categories ({sum})"

### Rule DL-V005: Scope Categories Non-Empty
- **Field**: `scope.categories`
- **Validation**: MUST be non-empty array
- **Valid Values**: code, doc, test, infra, design
- **Error**: "scope.categories cannot be empty"

### Rule DL-V006: Scope Categories Valid
- **Field**: `scope.categories`
- **Validation**: All entries MUST be one of: code, doc, test, infra, design
- **Error**: "Invalid category: {value} not in [code, doc, test, infra, design]"

### Rule DL-V007: Debt Item Required Fields
- **Section**: Debt Inventory
- **Validation**: Each debt item MUST have: id, location, category, description
- **Error**: "Debt item missing required field: {field}"

### Rule DL-V008: Debt Item Category Valid
- **Field**: debt item `category`
- **Validation**: MUST be one of: code, doc, test, infra, design
- **Error**: "Invalid debt item category: {value}"

### Rule DL-V009: Previous Ledger Reference
- **Field**: `previous_ledger`
- **Validation**: If specified, MUST reference existing Debt Ledger artifact
- **Error**: "previous_ledger references non-existent artifact: {value}"

### Rule DL-V010: Debt Item ID Uniqueness
- **Section**: Debt Inventory
- **Validation**: All debt item IDs MUST be unique within ledger
- **Error**: "Duplicate debt item ID: {id}"

## Risk Matrix Validation Rules

### Rule RM-V001: Artifact ID Pattern
- **Field**: `artifact_id`
- **Validation**: MUST match regex `^RM-[a-z0-9-]+$`
- **Example**: "RM-api-cleanup", "RM-security-audit"
- **Error**: "Invalid artifact_id: must match pattern RM-{slug}"

### Rule RM-V002: Type Field
- **Field**: `type`
- **Validation**: MUST be exactly "risk-matrix"
- **Error**: "Invalid type: must be 'risk-matrix'"

### Rule RM-V003: Status Enum
- **Field**: `status`
- **Validation**: MUST be one of: draft, final, archived
- **Error**: "Invalid status: must be draft, final, or archived"

### Rule RM-V004: Source Ledger Reference
- **Field**: `source_ledger`
- **Validation**: MUST reference existing Debt Ledger artifact
- **Error**: "source_ledger references non-existent artifact: {value}"

### Rule RM-V005: Score Range - Blast Radius
- **Field**: `blast_radius`
- **Validation**: MUST be integer in range 1-5
- **Error**: "blast_radius out of range: {value} not in [1-5]"

### Rule RM-V006: Score Range - Likelihood
- **Field**: `likelihood`
- **Validation**: MUST be integer in range 1-5
- **Error**: "likelihood out of range: {value} not in [1-5]"

### Rule RM-V007: Score Range - Effort
- **Field**: `effort`
- **Validation**: MUST be integer in range 1-5
- **Error**: "effort out of range: {value} not in [1-5]"

### Rule RM-V008: Composite Score Calculation
- **Field**: `composite`
- **Validation**: MUST equal `(blast_radius * likelihood) / effort`
- **Tolerance**: ±0.01 for floating point
- **Error**: "composite score incorrect: expected {expected}, got {actual}"

### Rule RM-V009: Priority Tier Match
- **Field**: `priority`
- **Validation**: MUST match composite score tier:
  - critical: composite >= 8
  - high: 5.0 <= composite < 8.0
  - medium: 2.0 <= composite < 5.0
  - low: composite < 2.0
- **Error**: "priority tier mismatch: composite {score} should be {expected}, got {actual}"

### Rule RM-V010: Priority Counts Sum
- **Fields**: `priority_counts.*`, scored items
- **Validation**: Sum of priority_counts MUST equal total scored items
- **Formula**: `critical + high + medium + low == total_items`
- **Error**: "priority_counts mismatch: sum ({sum}) != total items ({total})"

### Rule RM-V011: Quick Wins Definition
- **Field**: `quick_wins_count`
- **Validation**: Count MUST match items where `(blast_radius * likelihood) >= 10` AND `effort <= 2`
- **Error**: "quick_wins_count incorrect: expected {expected}, got {actual}"

### Rule RM-V012: Scored Item ID Uniqueness
- **Section**: Risk Matrix
- **Validation**: All scored item IDs MUST be unique within matrix
- **Error**: "Duplicate scored item ID: {id}"

## Sprint Debt Package Validation Rules

### Rule SDP-V001: Artifact ID Pattern
- **Field**: `artifact_id`
- **Validation**: MUST match regex `^SDP-[a-z0-9-]+$`
- **Example**: "SDP-sprint-24", "SDP-q1-cleanup"
- **Error**: "Invalid artifact_id: must match pattern SDP-{slug}"

### Rule SDP-V002: Type Field
- **Field**: `type`
- **Validation**: MUST be exactly "sprint-debt-package"
- **Error**: "Invalid type: must be 'sprint-debt-package'"

### Rule SDP-V003: Status Enum
- **Field**: `status`
- **Validation**: MUST be one of: draft, ready, in-progress, complete
- **Error**: "Invalid status: must be draft, ready, in-progress, or complete"

### Rule SDP-V004: Source Matrix Reference
- **Field**: `source_matrix`
- **Validation**: MUST reference existing Risk Matrix artifact
- **Error**: "source_matrix references non-existent artifact: {value}"

### Rule SDP-V005: Capacity Constraint
- **Fields**: `capacity.allocated_hours`, `capacity.total_hours`
- **Validation**: `allocated_hours` MUST NOT exceed `total_hours`
- **Error**: "capacity exceeded: allocated {allocated}h > total {total}h"

### Rule SDP-V006: Total Effort Match
- **Fields**: `total_effort_hours`, package `effort_hours`
- **Validation**: `total_effort_hours` MUST equal sum of all package effort_hours
- **Error**: "total_effort_hours mismatch: expected {sum}, got {total}"

### Rule SDP-V007: Package Acceptance Criteria
- **Field**: package `acceptance_criteria`
- **Validation**: Each package MUST have at least one acceptance criterion
- **Error**: "Package {id} missing acceptance criteria"

### Rule SDP-V008: Package Size Enum
- **Field**: package `size`
- **Validation**: MUST be one of: XS, S, M, L, XL
- **Error**: "Invalid package size: {value} not in [XS, S, M, L, XL]"

### Rule SDP-V009: Package Size Limit
- **Field**: package `size`
- **Validation**: Packages larger than XL MUST be split or flagged for spike
- **Warning**: "Package {id} exceeds XL size: consider splitting or spike"

### Rule SDP-V010: Sprint Date Range
- **Fields**: `sprint.start_date`, `sprint.end_date`
- **Validation**: `start_date` MUST be before `end_date`
- **Error**: "Invalid sprint dates: start {start} >= end {end}"

### Rule SDP-V011: Package Count Match
- **Fields**: `package_count`, packages array
- **Validation**: `package_count` MUST equal number of packages in array
- **Error**: "package_count mismatch: expected {count}, got {actual}"

### Rule SDP-V012: Package Confidence Enum
- **Field**: package `confidence`
- **Validation**: MUST be one of: high, medium, low
- **Error**: "Invalid confidence level: {value} not in [high, medium, low]"

### Rule SDP-V013: Package Priority Enum
- **Field**: package `priority`
- **Validation**: MUST be one of: critical, high, medium, low
- **Error**: "Invalid priority: {value} not in [critical, high, medium, low]"

### Rule SDP-V014: Package ID Uniqueness
- **Section**: Work Packages
- **Validation**: All package IDs MUST be unique within sprint package
- **Error**: "Duplicate package ID: {id}"

### Rule SDP-V015: Dependency Resolution
- **Field**: package `dependencies`
- **Validation**: All dependency package IDs MUST reference existing packages
- **Error**: "Package {id} depends on non-existent package: {dep_id}"

### Rule SDP-V016: Circular Dependencies
- **Field**: package `dependencies`
- **Validation**: Dependency graph MUST NOT contain cycles
- **Error**: "Circular dependency detected: {cycle_path}"

## Handoff Validation

### Debt Ledger → Risk Matrix

**Requirement**: All items in source ledger MUST be scoreable.

**Validations**:
1. Source ledger exists and is valid (status: final or draft)
2. All debt item IDs from source ledger are referenced in risk matrix
3. No orphan items in risk matrix (all source_id values exist in source ledger)

**Errors**:
- "Missing source item: {id} from ledger not scored"
- "Orphan scored item: {id} references non-existent source {source_id}"

### Risk Matrix → Sprint Debt Package

**Requirement**: All items in source matrix MUST be packageable.

**Validations**:
1. Source matrix exists and is valid (status: final or draft)
2. All scored item IDs from source matrix can be traced to packages
3. Package source_items reference valid risk matrix IDs
4. Priority distribution in packages reflects source matrix

**Errors**:
- "Unpackaged item: {id} from matrix not included in any package"
- "Invalid source item: package references non-existent matrix item {id}"

### Sprint Debt Package → HANDOFF

**Requirement**: HANDOFF schema valid when `target_rite` specified.

**Validations**:
1. If `target_rite` specified, HANDOFF section MUST be present
2. HANDOFF section MUST include: context, deliverables, success_criteria
3. All packages in HANDOFF scope MUST have clear ownership transfer

**Errors**:
- "target_rite specified but HANDOFF section missing"
- "HANDOFF missing required field: {field}"

## Validation Implementation

### Pseudocode Structure

```bash
validate_artifact() {
    local file=$1

    # Extract frontmatter
    frontmatter=$(extract_yaml_frontmatter "$file")

    # Detect artifact type
    type=$(echo "$frontmatter" | yq '.type')

    # Route to type-specific validator
    case "$type" in
        debt-ledger)
            validate_debt_ledger "$file"
            ;;
        risk-matrix)
            validate_risk_matrix "$file"
            ;;
        sprint-debt-package)
            validate_sprint_debt_package "$file"
            ;;
        *)
            echo "Unknown artifact type: $type" >&2
            return 1
            ;;
    esac
}

validate_debt_ledger() {
    local file=$1
    local errors=0

    # DL-V001: Artifact ID pattern
    artifact_id=$(yq '.artifact_id' "$file")
    if ! [[ $artifact_id =~ ^DL-[a-z0-9-]+$ ]]; then
        echo "DL-V001: Invalid artifact_id: must match pattern DL-{slug}" >&2
        ((errors++))
    fi

    # DL-V002: Type field
    type=$(yq '.type' "$file")
    if [[ "$type" != "debt-ledger" ]]; then
        echo "DL-V002: Invalid type: must be 'debt-ledger'" >&2
        ((errors++))
    fi

    # ... additional rules

    return $errors
}
```

### Integration Points

Validation runs at:
1. **Post-generation**: After agent creates artifact
2. **Pre-handoff**: Before passing to next agent in chain
3. **CI/CD**: Automated checks on artifact commits
4. **Manual**: Via `validate-artifact.sh` utility

### Error Reporting Format

```
VALIDATION FAILED: docs/debt/DL-api-cleanup.md

Errors (3):
  DL-V004: Statistics mismatch: total_items (42) != sum of categories (41)
  DL-V007: Debt item missing required field: location (item C023)
  DL-V010: Duplicate debt item ID: D015

Warnings (1):
  Optional section [{Ownership Report}] not removed but empty

Status: FAILED
```

## Version Compatibility

### Schema Version Detection

Validation logic MUST check `schema_version` and apply appropriate rules:

```bash
validate_debt_ledger() {
    local version
    version=$(yq '.schema_version' "$file")

    case "$version" in
        1.0) validate_v1_0_debt_ledger "$file" ;;
        1.1) validate_v1_1_debt_ledger "$file" ;;
        *)
            echo "Unknown schema version: $version" >&2
            return 1
            ;;
    esac
}
```

### Backward Compatibility

When MINOR version increases (1.0 → 1.1):
- New optional fields are ignored by older validators
- Old artifacts remain valid under new schema
- New validation rules are additive only

When MAJOR version increases (1.x → 2.0):
- Breaking changes may invalidate old artifacts
- Migration runbook provided
- Validators check version and apply appropriate ruleset

## Related Documentation

- [Debt Ledger Schema](../schemas/debt-ledger-schema.md)
- [Risk Matrix Schema](../schemas/risk-matrix-schema.md)
- [Sprint Debt Package Schema](../schemas/sprint-debt-package-schema.md)
- [TDD: Shared Templates](.ledge/specs/TDD-shared-templates.md)
