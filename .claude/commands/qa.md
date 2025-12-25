---
description: Validation-only with review and approval
argument-hint: <feature-name> [--requirements=PATH]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

## Your Task

Validate implementation against requirements. Testing and validation only. $ARGUMENTS

**NO IMPLEMENTATION. Testing and validation only.**

## Workflow Resolution

Read the validation agent from workflow:

```bash
# Find the final phase agent (validation, review, audit, etc.)
# This is typically the last phase in the workflow
VALIDATION_AGENT=$(grep -B1 "next: null" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

## Behavior

1. **Validate prerequisites**:
   - Requirements artifact exists (PRD, audit-report, etc.)
   - Implementation exists (code, docs, etc.)

2. **Resolve validation agent** from workflow:
   - 10x-dev-pack → qa-adversary
   - doc-team-pack → doc-reviewer
   - hygiene-pack → audit-lead
   - debt-triage-pack → (risk-assessor for validation)

3. **Invoke validation agent** via Task tool:
   - Create validation plan
   - Execute checks/tests
   - Report issues
   - Adversarial/thorough review

4. **Produce artifacts**:
   - Validation report/test plan
   - Issue reports (if found)
   - Approval summary

5. **Make ship decision**:
   - APPROVED: All criteria met
   - REJECTED: Critical issues found
   - CONDITIONAL: Minor issues, document and proceed

## Validation Categories

| Category | Focus |
|----------|-------|
| Functional | Requirements satisfaction |
| Accuracy | Correct implementation |
| Quality | Maintainability/clarity |
| Edge cases | Boundary conditions |

## Example

```
/qa "user-authentication"
/qa "API documentation" --requirements=docs/audits/AUDIT-api.md
```

## Reference

Full documentation: `.claude/skills/qa-ref/skill.md`
