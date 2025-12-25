# Glossary Index

Navigation for team development terminology.

## Categories

| Category | File | Contents |
|----------|------|----------|
| **Agents** | [agents.md](agents.md) | Role types, model/color assignment, tool allocation |
| **Workflows** | [workflows.md](workflows.md) | Phases, sequencing, complexity gating |
| **Artifacts** | [artifacts.md](artifacts.md) | Naming, path templates, prefixes |

## Quick Definitions

### Core Concepts

| Term | Definition |
|------|------------|
| **Team Pack** | Directory containing agents and workflow for a specialized domain |
| **Workflow** | Sequential pipeline of phases producing artifacts |
| **Phase** | Single step in workflow, owned by one agent |
| **Agent** | Specialized prompt with defined role, tools, and authority |
| **Artifact** | Document produced by a phase (PRD, TDD, report, etc.) |
| **Complexity Level** | Scope classifier that determines which phases run |
| **Entry Point** | First agent in workflow, triggered by `/start` |
| **Command Mapping** | How slash commands route to team agents |

### File Locations

| Component | Path Pattern |
|-----------|-------------|
| Team Pack | `~/Code/roster/teams/{name}-pack/` |
| Workflow Config | `~/Code/roster/teams/{name}-pack/workflow.yaml` |
| Agent Prompts | `~/Code/roster/teams/{name}-pack/agents/*.md` |
| Quick-Switch Command | `.claude/commands/{name}.md` |
| Reference Skill | `.claude/skills/{name}-ref/skill.md` |
| Active Workflow | `.claude/ACTIVE_WORKFLOW.yaml` (copied on swap) |
| Active Team | `.claude/ACTIVE_TEAM` (team name file) |
