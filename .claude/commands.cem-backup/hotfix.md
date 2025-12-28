---
description: Rapid fix workflow for urgent issues
argument-hint: <issue-description> [--severity=LEVEL]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

## Your Task

Execute a rapid fix for an urgent issue. $ARGUMENTS

## Workflow Resolution

For hotfix, use the implementation agent with fast-path workflow:

```bash
# Get implementation agent from workflow
IMPL_AGENT=$(grep -B1 "produces: code\|produces: commits\|produces: documentation" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

## Behavior

**Skip initial phases, minimal design. Focus on: diagnose → fix → validate → ship.**

1. **Diagnose issue**:
   - Reproduce the problem
   - Identify root cause
   - Determine blast radius

2. **Plan fix** (minimal design):
   - What changes are needed
   - What could break
   - Rollback strategy

3. **Implement fix** → Invoke implementation agent:
   - Minimal, focused changes
   - Add regression test/check
   - Inline documentation
   - Agent varies by team:
     - 10x-dev-pack → principal-engineer
     - doc-team-pack → tech-writer
     - hygiene-pack → janitor

4. **Fast validation** → Quick verification:
   - Verify fix works
   - Check for regressions
   - Confirm rollback path

5. **Document for follow-up**:
   - Create TODO for proper fix if needed
   - Note technical debt incurred

## Severity Levels

| Level | Response Time | Scope |
|-------|--------------|-------|
| CRITICAL | < 1 hour | Production down |
| HIGH | < 4 hours | Major feature broken |
| MEDIUM | < 1 day | Degraded functionality |

## Example

```
/hotfix "API returning 500 errors on login" --severity=CRITICAL
/hotfix "Broken link in documentation"
```

## Reference

Full documentation: `.claude/skills/hotfix-ref/skill.md`
