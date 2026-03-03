---
name: qa
description: Validation-only with review and approval
argument-hint: "<feature-name> [--requirements=PATH]"
allowed-tools: Bash, Read, Task, Glob, Grep
model: opus
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git, workflow).

## Pre-flight

1. **Session context** (recommended):
   - Check Session Status in context above
   - If no session: WARN "No active session. Consider /start for tracked workflow."

2. **Prerequisites check**:
   - Verify implementation exists to validate
   - If missing: WARN "No implementation found. Consider /build first."

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
   - 10x-dev → qa-adversary
   - docs → doc-reviewer
   - hygiene → audit-lead
   - debt-triage → (risk-assessor for validation)

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

Full documentation: `.claude/commands/operations/qa/INDEX.md`

## Sigil

### On Success

End your response with:

✅ validated · next: {hint}

Resolve the hint based on your validation outcome:
- APPROVED → `next: /commit && /pr` (or `/wrap` if already committed).
- REJECTED → `next: fix issues, then /qa`.
- CONDITIONAL → `next: /commit && /pr` (document caveats in PR).
No active session → output `✅ validated` without hint.

### On Failure

❌ validation failed: {brief reason} · fix: {recovery}

Infer recovery: no implementation found → implement first; missing requirements → create PRD; uncertain → `/consult`.
