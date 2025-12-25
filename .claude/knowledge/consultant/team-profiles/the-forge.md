# The Forge

> Agent Factory - Creates and maintains agent teams

---

## Overview

The Forge is the meta-team for creating and maintaining other agent teams. It provides specialized agents for each phase of team development: design, prompting, orchestration, infrastructure, validation, and integration. Unlike regular teams, The Forge is a **global singleton** that persists across team swaps.

**Not a switchable team** - The Forge agents are always available via `/forge`, `/new-team`, `/validate-team`, and `/eval-agent` commands.

---

## Agents (6)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **Agent Designer** | opus | design | TEAM-SPEC, role definitions |
| **Prompt Architect** | opus | prompting | Agent .md files (11 sections) |
| **Workflow Engineer** | opus | orchestration | workflow.yaml, commands |
| **Platform Engineer** | sonnet | infrastructure | Roster files, directory structure |
| **Eval Specialist** | opus | validation | eval-report.md, test results |
| **Agent Curator** | sonnet | integration | Roster entry, Consultant sync |

---

## Workflow

```
Agent Designer → Prompt Architect → Workflow Engineer → Platform Engineer → Eval Specialist → Agent Curator
     │               │                   │                    │                  │               │
     ▼               ▼                   ▼                    ▼                  ▼               ▼
 TEAM-SPEC      Agent .md files    workflow.yaml      roster/teams/       eval-report      roster entry
                 (11 sections)      + commands           {team}/           pass/fail        + Consultant
```

---

## Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| **PATCH** | Single agent modification | design → prompting → validation |
| **TEAM** | New team (3-5 agents) | All 6 phases |
| **ECOSYSTEM** | Multi-team initiative | All 6 phases + cross-team coordination |

---

## Best For

- Creating new agent teams from scratch
- Adding agents to existing teams
- Modifying agent prompts or workflows
- Validating team configurations
- Testing individual agents
- Cross-team workflow integration

---

## Not For

- Executing work within existing teams (use the team's workflow)
- General development tasks (use `/10x`)
- Documentation (use `/docs`)

---

## Commands

| Command | Purpose |
|---------|---------|
| `/forge` | Display Forge overview and help |
| `/new-team <name>` | Create new team through full workflow |
| `/validate-team <name>` | Run validation suite on team |
| `/eval-agent <name>` | Test single agent |

---

## Quick Start

### Create a new team

```bash
/new-team security-pack --complexity=TEAM
```

Invokes Agent Designer to begin the team creation workflow.

### Validate existing team

```bash
/validate-team 10x-dev-pack
```

Runs Eval Specialist to check team configuration.

### Test single agent

```bash
/eval-agent architect --team=10x-dev-pack
```

Tests specific agent in isolation.

---

## Related

- **Consultant**: Ecosystem navigation (also global singleton)
- **team-development skill**: Detailed templates and patterns
- **COMMAND_REGISTRY.md**: Full command documentation
