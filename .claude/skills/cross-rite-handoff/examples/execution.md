---
artifact_id: HANDOFF-debt-triage-to-hygiene-2026-01-03
schema_version: "1.0"
source_rite: debt-triage
target_rite: hygiene
handoff_type: execution
priority: high
blocking: false
initiative: "Q1 2026 Debt Remediation"
created_at: "2026-01-03T14:00:00Z"
status: pending
source_artifacts:
  - docs/debt/SPRINT-PLAN-q1-2026.md
  - docs/debt/RISK-ASSESSMENT-email-validators.md
sprint_id: sprint-debt-q1-2026
items:
  - id: PKG-001
    summary: "Consolidate email validation logic across 4 services"
    priority: high
    acceptance_criteria:
      - "Single EmailValidator class in shared/validation/"
      - "All 4 services import from shared location"
      - "Behavior preserved: all existing tests pass"
      - "No new dependencies introduced"
    estimated_effort: "4 hours"
  - id: PKG-002
    summary: "Remove deprecated date parsing functions"
    priority: medium
    acceptance_criteria:
      - "All usages of parse_date_legacy() replaced with parse_date()"
      - "parse_date_legacy() function deleted"
      - "All date-related tests pass"
    dependencies: []
    estimated_effort: "2 hours"
---

## Context

The debt-triage has completed assessment and planning for Q1 2026 debt remediation. These packages are ready for execution by hygiene.

## Package Prioritization

Execute in order: PKG-001, PKG-002 (no dependencies between them, but PKG-001 is higher priority).

## Notes for Hygiene Rite

- PKG-001 affects: user-service, billing-service, notification-service, auth-service
- All changes must preserve existing behavior (see acceptance criteria)
- Report any behavior changes discovered during refactoring

## Background

These refactoring packages emerged from debt triage session DT-2026-Q1-001. Both packages address code duplication and deprecated patterns that increase maintenance burden.

### PKG-001: Email Validation Consolidation

Current state: 4 different implementations of email validation logic with slight variations. This creates:
- Inconsistent behavior across services
- Duplicate test coverage
- Risk of diverging validation rules

Target state: Single source of truth for email validation in shared library.

### PKG-002: Date Parsing Cleanup

Current state: Legacy `parse_date_legacy()` function exists alongside new `parse_date()` implementation. The legacy version:
- Uses deprecated datetime library patterns
- Has known timezone handling bugs (documented in RISK-ASSESSMENT)
- Is only used in 3 locations (migration 80% complete)

Target state: Complete migration to new implementation, remove legacy code.

## Expected Outcomes

- Reduced code duplication
- Improved maintainability
- No behavior changes (behavior-preserving refactoring)
- All tests passing

## Contact

For questions during execution, contact debt-triage lead or reference source artifacts.
