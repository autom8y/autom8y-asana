---
name: sprint
description: Multi-task sprint orchestration
argument-hint: <sprint-name> [--tasks="task1,task2,task3"]
allowed-tools: Bash, Read, Task, Glob, Grep
model: opus
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Pre-flight

1. **Workflow required**:
   - Verify `.claude/ACTIVE_WORKFLOW.yaml` exists
   - If missing: ERROR "No active workflow. Use /rite to select a rite first."

2. **Rite context**:
   - Verify `.claude/ACTIVE_RITE` exists
   - If missing: ERROR "No rite active. Use /rite <rite-name> to select a rite."

## Your Task

Plan and execute a sprint with multiple coordinated tasks. $ARGUMENTS

## Behavior

1. **Gather sprint parameters**:
   - Sprint name/goal
   - Task list (prompt if not provided)
   - Duration/timebox

2. **Create SPRINT_CONTEXT via Moirai**:

   Delegate to Moirai for sprint state creation:
   ```
   Task(moirai, "create_sprint name='<sprint-name>' goal='<sprint-goal>' tasks='<task1,task2,task3>'")
   ```

   Moirai will:
   - Create `SPRINT_CONTEXT.md` in the session directory with proper schema
   - Initialize task breakdown with status tracking
   - Set up sprint metadata linked to current session
   - Return confirmation with sprint path

3. **For each task**, invoke `/task` workflow:
   - PRD for each task
   - TDD if MODULE+ complexity
   - Implementation
   - QA validation

4. **Track progress** via Moirai:
   - Mark tasks complete: `Task(moirai, "mark_complete task_id='{id}'")`
   - Handle blockers and update task notes
   - Generate sprint burndown summary

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

## Parallel Sprints

For multiple parallel sprints, see `/worktree` command.

