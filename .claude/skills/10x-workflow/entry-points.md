---
name: 10x-workflow-entry-points
description: "Entry point selection for the 10x workflow. Use when: deciding which agent to start with based on work type, skipping phases for bug fixes or refactors. Triggers: entry point, work type, bug fix, refactoring, new feature, hotfix."
---

# 10x Workflow: Entry Points

The default workflow starts with Requirements Analyst, but work type determines the optimal entry point.

## Entry Point Selection

| Work Type | Entry Agent | Phases Run |
|-----------|-------------|------------|
| New feature | requirements-analyst | PRD -> TDD -> Code -> QA |
| Enhancement | requirements-analyst | PRD -> TDD -> Code -> QA |
| Technical refactoring | architect | TDD -> Code -> QA |
| Performance optimization | architect | TDD -> Code -> QA |
| Bug fix | principal-engineer | Code -> QA |
| Security fix | principal-engineer | Code -> QA |
| Hotfix | principal-engineer | Code -> QA |

## Usage Examples

**New feature (default entry)**:
```
/task "Add user profile photo upload"
```
Starts with Requirements Analyst -> full workflow.

**Bug fix (principal-engineer entry)**:
```
/task --entry=principal-engineer "Fix login timeout after 5 minutes"
/task --work-type=bug_fix "Fix null pointer in user service"
```
Skips PRD and TDD; goes directly to implementation and QA.

**Refactoring (architect entry)**:
```
/task --entry=architect "Migrate from REST to GraphQL"
/task --work-type=technical_refactoring "Extract payment module"
```
Skips PRD; starts with TDD to document design decisions.

## Decision Criteria

1. **Adding user-facing capability?** → requirements-analyst
2. **Changing system structure without new features?** → architect
3. **Fixing known broken behavior?** → principal-engineer
4. **Time-critical remediation?** → principal-engineer

When uncertain, default to requirements-analyst. Skipping phases is cheaper than backtracking.
