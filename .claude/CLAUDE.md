<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Three operating modes:

| Mode | Session | Rite | Main Agent Behavior |
|------|---------|------|---------------------|
| **Native** | No | - | Direct execution, no tracking |
| **Cross-Cutting** | Yes | No | Direct execution + session tracking |
| **Orchestrated** | Yes | Yes (ACTIVE) | Pythia coordinates; delegate via Task tool |

Use `/go` to start any session. Use `/consult` for mode selection.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

This project uses a 5-agent workflow (10x-dev):

| Agent | Role |
| ----- | ---- |
| **pythia** | Coordinates development lifecycle phases and routes work to specialists |
| **requirements-analyst** | Gathers requirements and produces PRD artifacts |
| **architect** | Creates technical design documents and architecture decisions |
| **principal-engineer** | Implements code according to design specifications |
| **qa-adversary** | Validates implementation through adversarial testing |

Entry point: `/go`. Agent invocation patterns: `prompting` skill. Routing guidance: `/consult`.
<!-- KNOSSOS:END quick-start -->

<!-- KNOSSOS:START agent-routing -->
## Agent Routing

**Pythia** coordinates each rite's workflow — routing tasks to specialists, verifying phase gates, and managing handoffs. In orchestrated sessions, the main thread delegates to specialists via Task tool.

Every agent defines its authority via **Exousia** (jurisdiction contract):
- **You Decide**: Actions within the agent's autonomous authority
- **You Escalate**: Situations requiring Pythia or user input
- **You Do NOT Decide**: Boundaries the agent must never cross

Without a session, execute directly or use `/task`. Routing guidance: `/consult`.
<!-- KNOSSOS:END agent-routing -->

<!-- KNOSSOS:START agent-configurations regenerate=true source=agents/*.md -->
## Agents

Prompts in `.claude/agents/`:

- `pythia.md` - Coordinates development lifecycle phases and routes work to specialists
- `requirements-analyst.md` - Gathers requirements and produces PRD artifacts
- `architect.md` - Creates technical design documents and architecture decisions
- `principal-engineer.md` - Implements code according to design specifications
- `qa-adversary.md` - Validates implementation through adversarial testing
<!-- KNOSSOS:END agent-configurations -->

<!-- KNOSSOS:START user-content -->
## Project-Specific Instructions

<!--
Add your project-specific Claude instructions here.
This section is preserved during re-materialization.

Examples:
- Project conventions and coding standards
- Important architectural decisions
- Team-specific workflows
- Links to key documentation

To add more custom sections:
  ari inscription add-region --name=my-section --owner=satellite
-->
<!-- KNOSSOS:END user-content -->