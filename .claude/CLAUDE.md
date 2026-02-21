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

This project uses a 5-agent workflow (hygiene):

| Agent | Role |
| ----- | ---- |
| **pythia** | Coordinates code hygiene initiative phases |
| **code-smeller** | Detects code smells and quality issues across codebase |
| **architect-enforcer** | Plans refactoring approach and enforces architecture standards |
| **janitor** | Executes code cleanup and improvements |
| **audit-lead** | Audits cleanup results and provides quality signoff |

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

### Throughline Resume Protocol

The main thread MAY track subagent IDs for throughline agents (Pythia, Moirai) and pass `resume: {agentId}` on subsequent Task calls. This gives the agent full history of its prior consultations within the workflow.

- Agent IDs are valid only within the current CC session
- Clear stored IDs on rite switch or session wrap
- If resume fails (invalid ID, session changed), fall back to fresh invocation
- Resume is opportunistic -- orchestrated workflows function correctly without it
<!-- KNOSSOS:END agent-routing -->

<!-- KNOSSOS:START agent-configurations source=agents/*.md regenerate=true -->
## Agents

Prompts in `.claude/agents/`:

- `pythia.md` - Coordinates code hygiene initiative phases
- `code-smeller.md` - Detects code smells and quality issues across codebase
- `architect-enforcer.md` - Plans refactoring approach and enforces architecture standards
- `janitor.md` - Executes code cleanup and improvements
- `audit-lead.md` - Audits cleanup results and provides quality signoff
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