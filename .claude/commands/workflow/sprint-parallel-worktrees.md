# Parallel Sprint Pattern with Worktrees

> Reference for running multiple sprints in parallel using git worktrees.

For truly parallel sprints across multiple rites or focuses, use worktrees to get filesystem isolation:

```bash
# Create isolated worktrees per sprint
/worktree create "sprint-backend" --rite=10x-dev
/worktree create "sprint-frontend" --rite=10x-dev
/worktree create "sprint-docs" --rite=docs

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

## Why Worktrees for Parallel Sprints

- Each sprint gets isolated SPRINT_CONTEXT (no collision)
- Different rites can work simultaneously
- Changes don't affect each other
- Use `/sessions --all` to monitor all sprints

## When to Use

- **Single sprint, multiple tasks**: Use `/sprint` directly
- **Multiple parallel sprints**: Use `/worktree` per sprint

## Related

- `/worktree` command for worktree management
- `/sprint` command for single-sprint orchestration
- `/sessions --all` to view sessions across worktrees
