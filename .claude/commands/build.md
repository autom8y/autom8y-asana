---
name: build
description: Implementation-only from approved design (no design phase)
argument-hint: "<feature-name> [--design=PATH]"
allowed-tools: Bash, Read, Write, Task, Glob, Grep
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
   - Verify design artifact exists (TDD, refactor-plan, doc-structure, etc.)
   - If missing: WARN "No design artifact found. Consider /architect first."

## Your Task

Implement from an approved design. No design work - execution only. $ARGUMENTS

**ASSUMES DESIGN EXISTS. Implementation/execution only.**

## Workflow Resolution

Read the implementation agent from workflow:

```bash
# Find the "implementation" or "execution" or "writing" phase agent
# This varies by rite - 10x uses "implementation", hygiene uses "execution", etc.
IMPL_AGENT=$(grep -B1 "produces: code\|produces: commits\|produces: documentation" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

## Behavior

1. **Validate prerequisites**:
   - Design artifact exists (TDD, refactor-plan, doc-structure, etc.)
   - Design is approved

2. **Resolve implementation agent** from workflow:
   - 10x-dev → principal-engineer
   - docs → tech-writer
   - hygiene → janitor
   - debt-triage → sprint-planner

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

Full documentation: `.claude/skills/build-ref/INDEX.md`
