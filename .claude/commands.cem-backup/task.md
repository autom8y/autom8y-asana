---
description: Single task full lifecycle through team workflow phases
argument-hint: <task-description> [--complexity=LEVEL]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

## Your Task

Execute a single task through the complete workflow lifecycle for the active team. $ARGUMENTS

## Workflow Resolution

Read the active workflow from `.claude/ACTIVE_WORKFLOW.yaml`:

```bash
# Get workflow phases
PHASES=$(grep -A20 "^phases:" .claude/ACTIVE_WORKFLOW.yaml)

# Get complexity levels
COMPLEXITY_LEVELS=$(grep -A20 "^complexity_levels:" .claude/ACTIVE_WORKFLOW.yaml)
```

## Behavior

1. **Assess complexity** (if not provided):
   - Read complexity levels from workflow config
   - Each team defines its own levels (e.g., SCRIPT/MODULE vs PAGE/SECTION)
   - Match task scope to appropriate level

2. **Determine applicable phases**:
   - Read phases for the selected complexity level
   - Filter workflow phases to only those that apply

3. **Execute each phase in sequence**:
   For each phase in the workflow:
   - Read agent name from phase config
   - Read artifact type from phase config
   - Invoke agent via Task tool
   - Verify artifact produced
   - Check phase condition (if any)
   - Proceed to next phase

4. **Quality gates at each phase**:
   - Entry phase produces initial artifact
   - Subsequent phases build on previous artifacts
   - Final phase provides approval/sign-off

## Team-Specific Workflows

The workflow config determines the exact pipeline:

**10x-dev-pack** (4 phases):
```
requirements → design → implementation → validation
```

**doc-team-pack** (4 phases):
```
audit → architecture → writing → review
```

**hygiene-pack** (4 phases):
```
assessment → planning → execution → audit
```

**debt-triage-pack** (3 phases):
```
collection → assessment → planning
```

## Phase Execution

For each phase:
```
1. Read phase.agent from workflow
2. Read phase.produces artifact type
3. Check phase.condition (skip if not met)
4. Invoke agent via Task tool
5. Verify artifact created
6. Update session phase in SESSION_CONTEXT.md
7. Proceed to phase.next (or complete if null)
```

## Example

```
/task "Add user authentication module"
/task "Audit API documentation" --complexity=SECTION
/task "Clean up utils module" --complexity=MODULE
```

## Reference

Full documentation: `.claude/skills/task-ref/skill.md`
