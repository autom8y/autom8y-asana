---
description: Display The Forge meta-team overview and available commands
argument-hint: [--agents|--workflow|--commands]
allowed-tools: Read, Glob
model: claude-sonnet-4-5
---

## Your Task

Display information about The Forge - the meta-team for creating and maintaining agent teams.

**Arguments**: $ARGUMENTS

## Behavior

### Default (no arguments)

Display the Forge overview:

```
THE FORGE - Agent Factory Team
==============================

The team that builds teams. Global singleton (always available).

AGENTS (6):
  Agent Designer    (purple)  - Role specs and contracts
  Prompt Architect  (cyan)    - System prompts (11 sections)
  Workflow Engineer (green)   - Orchestration and commands
  Platform Engineer (orange)  - Roster infrastructure
  Eval Specialist   (red)     - Testing and validation
  Agent Curator     (blue)    - Versioning and integration

COMMANDS:
  /new-team <name>      - Full team creation workflow
  /validate-team <name> - Run validation suite on team
  /eval-agent <name>    - Test single agent in isolation

COMPLEXITY LEVELS:
  PATCH     - Single agent modification
  TEAM      - New team with 3-5 agents
  ECOSYSTEM - Multi-team initiative

Full docs: .claude/skills/forge-ref/skill.md
```

### With --agents

List all 6 Forge agents with their responsibilities:

| Agent | Model | Produces | Handoff To |
|-------|-------|----------|------------|
| Agent Designer | opus | TEAM-SPEC | Prompt Architect |
| Prompt Architect | opus | Agent .md files | Workflow Engineer |
| Workflow Engineer | opus | workflow.yaml | Platform Engineer |
| Platform Engineer | sonnet | Roster files | Eval Specialist |
| Eval Specialist | opus | eval-report | Agent Curator |
| Agent Curator | sonnet | Roster entry | (terminal) |

### With --workflow

Display the Forge workflow:

```
Agent Designer → Prompt Architect → Workflow Engineer → Platform Engineer → Eval Specialist → Agent Curator
     │               │                   │                    │                  │               │
     ▼               ▼                   ▼                    ▼                  ▼               ▼
 TEAM-SPEC      Agent .md files    workflow.yaml      roster/teams/       eval-report      roster entry
```

### With --commands

Display available Forge commands with usage:

| Command | Purpose | Entry Agent |
|---------|---------|-------------|
| `/new-team <name>` | Create a new team pack | Agent Designer |
| `/validate-team <name>` | Validate existing team | Eval Specialist |
| `/eval-agent <name>` | Test single agent | Eval Specialist |

## Reference

Full documentation: `.claude/skills/forge-ref/skill.md`
