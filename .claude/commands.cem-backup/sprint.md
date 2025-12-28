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

2. **Create SPRINT_CONTEXT** in session directory (`$SESSION_DIR/SPRINT_CONTEXT.md`):
   - Sprint metadata (links to session)
   - Task breakdown with status
   - Dependencies between tasks
   - Note: Uses session-scoped path to allow parallel sprints without collision

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

## Parallel Sprint Pattern

For truly parallel sprints across multiple teams/focuses, use **worktrees**:

```bash
# Create isolated worktrees per sprint
/worktree create "sprint-backend" --team=10x-dev-pack
/worktree create "sprint-frontend" --team=10x-dev-pack
/worktree create "sprint-docs" --team=doc-team-pack

# In each terminal, navigate and start sprint independently:
# Terminal 1:
cd worktrees/wt-xxx && claude
/sprint "Backend Sprint" --tasks="API,Database,Auth"

# Terminal 2:
cd worktrees/wt-yyy && claude
/sprint "Frontend Sprint" --tasks="Components,State,Tests"

# Terminal 3:
cd worktrees/wt-zzz && claude
/sprint "Docs Sprint" --tasks="API Docs,User Guide,Examples"
```

**Why worktrees for parallel sprints?**
- Each sprint gets isolated SPRINT_CONTEXT (no collision)
- Different teams can work simultaneously
- Changes don't affect each other
- Use `/sessions --all` to monitor all sprints

**Single sprint, multiple tasks** → use this command directly
**Multiple parallel sprints** → use `/worktree` per sprint

## Reference

Full documentation: `.claude/skills/sprint-ref/skill.md`
