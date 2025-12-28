---
name: sprint-ref
description: "Multi-task sprint orchestration. Breaks sprint goals into tasks, coordinates multiple /task executions, tracks sprint progress. Triggers: /sprint, sprint planning, multi-task workflow, sprint coordination."
---

# /sprint - Multi-Task Sprint Orchestration

> **Category**: Development | **Phase**: Sprint Planning | **Complexity**: High

## Purpose

Orchestrate a multi-task development sprint by breaking down sprint goals into individual tasks, coordinating multiple `/task` executions, and tracking overall sprint progress.

This command provides the highest level of workflow automation, suitable for sprint planning sessions where multiple related features or fixes need to be delivered together.

---

## Usage

```bash
/sprint "sprint-name" [--duration=2w] [--tasks="task1,task2,task3"]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `sprint-name` | Yes | - | Name of the sprint (e.g., "Q1 Authentication Sprint") |
| `--duration` | No | 2w | Sprint duration (1w, 2w, 1m) |
| `--tasks` | No | Prompted | Comma-separated task list or interactive |

---

## Behavior

### 1. Sprint Initialization

Prompt user for sprint details if not provided:

- **Sprint name**: Clear sprint identifier
- **Sprint goal**: High-level objective for this sprint
- **Duration**: Timeboxed period (1 week, 2 weeks, 1 month)
- **Task list**: Either provided via `--tasks` or gathered interactively

### 2. Create Sprint Context

Generate `$SESSION_DIR/SPRINT_CONTEXT.md` file (session-scoped):

```yaml
---
sprint_id: "sprint-20251224-HHMMSS"
created_at: "2025-12-24THH:MM:SSZ"
sprint_name: "{user-provided-name}"
sprint_goal: "{high-level-objective}"
duration: "{1w|2w|1m}"
start_date: "2025-12-24"
end_date: "{calculated}"
active_team: "{current-team}"
tasks:
  - id: "task-001"
    name: "{task-name}"
    status: "pending"
    complexity: null
    artifacts: []
  - id: "task-002"
    name: "{task-name}"
    status: "pending"
    complexity: null
    artifacts: []
blockers: []
completed_tasks: 0
total_tasks: 0
---

## Sprint Goal

{One-line sprint objective}

## Sprint Progress

(Updated as tasks complete)

## Sprint Retrospective

(To be filled at sprint completion)
```

### 3. Task Breakdown

For each task in the sprint:

1. **Estimate complexity**: Prompt user or analyze task
   - SCRIPT, MODULE, SERVICE, PLATFORM
2. **Sequence tasks**: Identify dependencies
3. **Create task queue**: Ordered list of tasks to execute

### 4. Sequential Task Execution

For each task in queue:

**Invoke /task skill**:

```markdown
Act as **Orchestrator**.

Execute task from sprint: {sprint-name}
Task: {task-name}
Complexity: {estimated-complexity}

Follow full /task workflow:
1. Requirements Analyst → PRD
2. Architect → TDD (if complexity > SCRIPT)
3. Principal Engineer → Implementation
4. QA Adversary → Validation

Update SPRINT_CONTEXT when task completes.
```

**Wait for task completion** before starting next task.

**Update SPRINT_CONTEXT**:
- Mark task status: `pending` → `in_progress` → `completed`
- Add artifact references
- Update progress counters
- Document blockers if encountered

### 5. Sprint Progress Tracking

Display progress after each task completion:

```
Sprint Progress: {sprint-name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tasks Completed: 2/5 (40%)
Current Task: [task-003] Implement user session management

✓ [task-001] Add login endpoint
✓ [task-002] Create authentication middleware
⧗ [task-003] Implement user session management (IN PROGRESS)
☐ [task-004] Add password reset flow
☐ [task-005] Integrate OAuth providers

Blockers: None
Days Remaining: 8/14
```

### 6. Blocker Management

If a task encounters a blocker:

1. **Document blocker** in SPRINT_CONTEXT
2. **Prompt user**: "Task blocked. Skip and continue, or resolve now?"
3. **If skip**: Mark task as `blocked`, continue with next task
4. **If resolve**: Pause sprint, help resolve, resume

### 7. Sprint Completion

When all tasks completed (or sprint duration reached):

```bash
/wrap-sprint
```

**Actions**:
- Generate sprint retrospective summary
- List completed tasks with artifact links
- Document incomplete tasks (if any)
- Calculate sprint velocity (tasks/week)
- Archive SPRINT_CONTEXT to `/docs/sprints/SPRINT-{name}.md`

---

## Workflow

```mermaid
graph TD
    A[/sprint invoked] --> B[Gather sprint details]
    B --> C[Create SPRINT_CONTEXT]
    C --> D[Break down tasks]
    D --> E[Estimate complexity]
    E --> F[Sequence tasks]
    F --> G{More tasks?}
    G -->|Yes| H[Execute /task]
    H --> I{Task success?}
    I -->|Yes| J[Update progress]
    I -->|No| K[Document blocker]
    K --> L{Skip or resolve?}
    L -->|Skip| J
    L -->|Resolve| M[Help resolve]
    M --> H
    J --> G
    G -->|No| N[Sprint complete]
    N --> O[Generate retrospective]
    O --> P[Archive sprint]
```

---

## Deliverables

For each sprint, produces:

1. **SPRINT_CONTEXT**: Live sprint state and progress
2. **Per-task artifacts**:
   - PRDs (all tasks)
   - TDDs (MODULE+ complexity)
   - Implementation code
   - Test plans
3. **Sprint retrospective**: Summary document at completion
4. **Sprint archive**: Historical record in `/docs/sprints/`

---

## Examples

### Example 1: Basic Sprint

```bash
/sprint "Authentication Sprint" --tasks="Login API,Session mgmt,Password reset"
```

Output:
```
Sprint initialized: Authentication Sprint
Duration: 2 weeks (Dec 24 - Jan 7)
Tasks: 3

Task breakdown:
1. [task-001] Login API (estimated: MODULE)
2. [task-002] Session mgmt (estimated: MODULE)
3. [task-003] Password reset (estimated: SCRIPT)

Starting task execution...

[TASK 1/3] Login API
✓ Requirements Analyst → PRD created
✓ Architect → TDD created
✓ Principal Engineer → Implementation complete
✓ QA Adversary → Tests passing

Progress: 1/3 tasks complete (33%)

[TASK 2/3] Session mgmt
...
```

### Example 2: Sprint with Blocker

```bash
/sprint "Payment Integration"
```

Output:
```
Sprint: Payment Integration
Tasks: 4

[TASK 2/4] Stripe webhook integration
✗ Blocker encountered: "Missing Stripe API credentials"

Options:
1. Skip this task and continue with others
2. Pause sprint to resolve blocker

Choose: 1

Task [task-002] marked as BLOCKED
Continuing with next task...

[TASK 3/4] Payment confirmation email
...

Sprint summary:
✓ 3/4 tasks completed
⚠ 1 blocked task: Stripe webhook integration
  Blocker: Missing Stripe API credentials

Recommend: Resolve blocker and run `/task "Stripe webhook integration"` separately
```

---

## When to Use vs Alternatives

| Use /sprint when... | Use alternative when... |
|---------------------|-------------------------|
| Planning 3+ related tasks | Single task → Use `/task` |
| Multi-week initiative | Single file/quick fix → Use `/hotfix` |
| Team sprint planning | Research question → Use `/spike` |
| Coordinated feature delivery | Just exploring feasibility → Use `/spike` |

### /sprint vs /task

- `/sprint`: Coordinates MULTIPLE tasks with progress tracking
- `/task`: Executes SINGLE task through full lifecycle

### /sprint vs /start

- `/sprint`: Multi-task execution with task sequencing
- `/start`: Single session initialization with PRD/TDD

---

## Complexity Level

**HIGH** - This command:
- Manages multiple task executions
- Tracks dependencies and sequencing
- Handles blockers and resumption
- Produces comprehensive documentation

**Recommended for**:
- Experienced teams familiar with `/task` workflow
- Well-defined multi-task initiatives
- Sprint planning with clear deliverables

**Not recommended for**:
- First-time workflow users (start with `/task`)
- Exploratory work (use `/spike` instead)
- Single tasks (use `/task` instead)

---

## State Changes

### Files Created

| File | Purpose |
|------|---------|
| `$SESSION_DIR/SPRINT_CONTEXT.md` | Sprint state and progress (session-scoped) |
| `/docs/sprints/SPRINT-{name}.md` | Sprint archive (at completion) |
| Per-task artifacts | PRDs, TDDs, code, test plans |

### Fields in SPRINT_CONTEXT

| Field | Description |
|-------|-------------|
| `sprint_id` | Unique sprint identifier |
| `sprint_name` | User-provided sprint name |
| `sprint_goal` | High-level objective |
| `duration` | Timeboxed period |
| `start_date` | Sprint start date |
| `end_date` | Calculated end date |
| `tasks` | Array of task objects |
| `blockers` | List of encountered blockers |
| `completed_tasks` | Counter |
| `total_tasks` | Counter |

---

## Prerequisites

- 10x-dev-pack active (or team with all 4 agents)
- No active SPRINT_CONTEXT (one sprint at a time)
- Clear sprint goal and task list

---

## Success Criteria

- SPRINT_CONTEXT created with valid tasks
- Each task executes full PRD → TDD → Code → QA cycle
- Progress tracked and displayed after each task
- Sprint completes with retrospective document
- All artifacts properly archived

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Sprint already active | SPRINT_CONTEXT exists | Use `/wrap-sprint` to complete or `/resume-sprint` to continue |
| Invalid task name | Empty or duplicate task | Prompt for valid task name |
| Task execution fails | Agent error during /task | Document blocker, offer skip/resolve |
| Missing team agents | Required agent not in active team | Switch to 10x-dev-pack with `/10x` |

---

## Related Commands

- `/task` - Execute single task (used by /sprint)
- `/hotfix` - Rapid fix without full workflow
- `/spike` - Time-boxed research (no production code)
- `/start` - Initialize single session
- `/wrap-sprint` - Complete and archive sprint

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
- [documentation](../documentation/SKILL.md) - Artifact templates
- [task](../task/SKILL.md) - Single task execution skill

---

## Notes

### Sprint Duration Guidelines

| Duration | Typical Tasks | Complexity Range |
|----------|---------------|------------------|
| 1 week | 2-3 tasks | SCRIPT to MODULE |
| 2 weeks | 3-5 tasks | MODULE to SERVICE |
| 1 month | 5-10 tasks | SERVICE to PLATFORM |

### Task Sequencing

Sprint automatically sequences tasks, but you can specify dependencies:

```bash
/sprint "API Integration" --tasks="Schema design,API client,Integration tests" --sequence=true
```

Tasks execute in order, blocking on failures.

### Parallel vs Sequential

By default, tasks execute sequentially. For independent tasks that can run in parallel:

```bash
/sprint "UI Updates" --parallel=true
```

**Warning**: Parallel execution requires careful coordination to avoid conflicts.

---

## Integration Points

### With SESSION_CONTEXT

If a session is active when sprint starts:
- Sprint becomes a "sub-context" of the session
- Session artifacts inherit sprint artifacts
- `/wrap` wraps both session and sprint

### With Git

Each completed task can trigger:
- Automatic commit (optional)
- Feature branch creation (optional)
- PR generation (optional)

Configure in sprint initialization.

---

## Future Enhancements

Planned improvements (not yet implemented):

- **Sprint burndown charts**: Visual progress tracking
- **Velocity calculation**: Historical sprint performance
- **Automated task estimation**: ML-based complexity prediction
- **Slack/Teams integration**: Sprint progress notifications
- **Template sprints**: Reusable sprint patterns (e.g., "API Sprint", "UI Sprint")
