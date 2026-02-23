---
name: task
description: Single task full lifecycle through rite workflow phases
argument-hint: "<task-description> [--complexity=LEVEL]"
allowed-tools: Bash, Read, Task, Glob, Grep
model: opus
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git, workflow).

## Pre-flight

1. **Workflow required**:
   - Verify `.claude/ACTIVE_WORKFLOW.yaml` exists
   - If missing: ERROR "No active workflow. Use /rite to select a rite first."

2. **Rite context**:
   - Verify `.claude/ACTIVE_RITE` exists
   - If missing: ERROR "No rite active. Use /rite <rite-name> to select a rite."

## Your Task

Execute a single task through the complete workflow lifecycle for the active rite. $ARGUMENTS

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
   - Each rite defines its own levels (e.g., SCRIPT/MODULE vs PAGE/SECTION)
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

## Rite-Specific Workflows

The workflow config determines the exact pipeline:

**10x-dev** (4 phases):
```
requirements → design → implementation → validation
```

**docs** (4 phases):
```
audit → architecture → writing → review
```

**hygiene** (4 phases):
```
assessment → planning → execution → audit
```

**debt-triage** (3 phases):
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
6. Delegate phase transition to Moirai: Task(moirai, "transition_phase to='{phase}'")
7. Proceed to phase.next (or complete if null)
```

## Example

```
/task "Add user authentication module"
/task "Audit API documentation" --complexity=SECTION
/task "Clean up utils module" --complexity=MODULE
```

