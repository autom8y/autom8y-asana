---
description: Create a new agent team pack through The Forge workflow
argument-hint: <team-name> [--complexity=PATCH|TEAM|ECOSYSTEM]
allowed-tools: Bash, Glob, Grep, Read, Write, Edit, Task, TodoWrite
model: claude-opus-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session context).

## Your Task

Create a new team pack: $ARGUMENTS

## Behavior

### 1. Parse Arguments

- `team-name`: Required. Name for the new team (will become `{name}-pack`)
- `--complexity`: Optional. Default is TEAM.
  - PATCH: Single agent modification (phases: design, prompting, validation)
  - TEAM: Full team with 3-5 agents (all 6 phases)
  - ECOSYSTEM: Multi-team initiative (all 6 phases)

### 2. Invoke Agent Designer

Start the Forge workflow by invoking the Agent Designer:

```
Use the Task tool to invoke the agent-designer agent with:

"Create a TEAM-SPEC for {team-name}-pack.

The user wants to create a new team. Your job is to:
1. Clarify the team's purpose with the user
2. Design 3-5 agent roles with clear boundaries
3. Define input/output contracts
4. Specify complexity levels
5. Document handoff criteria

Complexity level: {complexity}

When the TEAM-SPEC is complete, hand off to Prompt Architect."
```

### 3. Workflow Continues

The Forge workflow proceeds through all phases:

```
Agent Designer → Prompt Architect → Workflow Engineer → Platform Engineer → Eval Specialist → Agent Curator
```

Each agent hands off to the next when their handoff criteria are met.

### 4. Completion

When Agent Curator finishes, the team is:
- Deployed to `~/Code/roster/teams/{team-name}-pack/`
- Discoverable via `/consult`
- Ready for use via `/{team-name}` or `/team {team-name}-pack`

## Example Usage

```bash
# Create a new API development team
/new-team api-dev

# Create a minimal agent modification
/new-team security-auditor --complexity=PATCH

# Create a multi-team ecosystem initiative
/new-team observability-platform --complexity=ECOSYSTEM
```

## Reference

Full documentation: `.claude/skills/forge-ref/skill.md`
Forge overview: `/forge`
