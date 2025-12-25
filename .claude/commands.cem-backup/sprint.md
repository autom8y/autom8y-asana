---
description: Multi-task sprint orchestration
argument-hint: <sprint-name> [--tasks="task1,task2,task3"]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Plan and execute a sprint with multiple coordinated tasks. $ARGUMENTS

## Behavior

1. **Gather sprint parameters**:
   - Sprint name/goal
   - Task list (prompt if not provided)
   - Duration/timebox

2. **Create SPRINT_CONTEXT** at `.claude/SPRINT_CONTEXT`:
   - Sprint metadata
   - Task breakdown with status
   - Dependencies between tasks

3. **For each task**, invoke `/task` workflow:
   - PRD for each task
   - TDD if MODULE+ complexity
   - Implementation
   - QA validation

4. **Track progress**:
   - Update task status (pending → in_progress → complete)
   - Handle blockers
   - Generate sprint burndown

5. **Complete sprint**:
   - Generate retrospective
   - Archive SPRINT_CONTEXT

## Example

```
/sprint "Authentication Sprint" --tasks="Login API,Session management,Password reset"
```

## When to Use

- 3+ related tasks for coordinated delivery
- Time-boxed work periods
- Feature epics spanning multiple components

## Reference

Full documentation: `.claude/skills/sprint-ref/skill.md`
