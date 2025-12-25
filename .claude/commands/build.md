---
description: Implementation-only from approved design (no design phase)
argument-hint: <feature-name> [--design=PATH]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

## Your Task

Implement from an approved design. No design work - execution only. $ARGUMENTS

**ASSUMES DESIGN EXISTS. Implementation/execution only.**

## Workflow Resolution

Read the implementation agent from workflow:

```bash
# Find the "implementation" or "execution" or "writing" phase agent
# This varies by team - 10x uses "implementation", hygiene uses "execution", etc.
IMPL_AGENT=$(grep -B1 "produces: code\|produces: commits\|produces: documentation" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

## Behavior

1. **Validate prerequisites**:
   - Design artifact exists (TDD, refactor-plan, doc-structure, etc.)
   - Design is approved

2. **Resolve implementation agent** from workflow:
   - 10x-dev-pack → principal-engineer
   - doc-team-pack → tech-writer
   - hygiene-pack → janitor
   - debt-triage-pack → sprint-planner

3. **Invoke implementation agent** via Task tool:
   - Follow design specification exactly
   - Implement all interfaces/sections
   - Write tests/validation per spec

4. **Produce artifacts**:
   - Implementation (code, docs, commits, etc.)
   - Tests (if applicable)
   - Notes (if deviations from design)

5. **Escalate if blocked**:
   - Design unclear → return to design phase agent
   - Scope changed → update design first

## When to Use

- Design is approved and ready
- Two-phase workflow after `/architect`
- Design review has passed

## Example

```
/build "user-authentication"
/build "API documentation" --design=docs/architecture/DOC-STRUCTURE-api.md
```

Pairs with: `/architect` (design) and `/qa` (validation)

## Reference

Full documentation: `.claude/skills/build-ref/skill.md`
