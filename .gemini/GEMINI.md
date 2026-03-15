<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Agents activate automatically when your prompt matches their description.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

5-agent workflow (10x-dev):

| Agent | Role |
| ----- | ---- |
| **potnia** | Coordinates development lifecycle phases and routes work to specialists |
| **requirements-analyst** | Gathers requirements and produces PRD artifacts |
| **architect** | Creates technical design documents and architecture decisions |
| **principal-engineer** | Implements code according to design specifications |
| **qa-adversary** | Validates implementation through adversarial testing |

Agents activate when your prompt matches their description.
<!-- KNOSSOS:END quick-start -->

<!-- KNOSSOS:START agent-routing -->
## Agent Routing

Agents activate automatically based on description matching. Write prompts that align with specialist descriptions for effective routing.
<!-- KNOSSOS:END agent-routing -->

<!-- KNOSSOS:START commands -->
## Gemini Primitives

| Primitive | Invocation | Source |
|---|---|---|
| Slash command | User types `/name` | `.gemini/commands/` |
| Skill | Loaded into context | `.gemini/skills/` |
| Agent | Activates on description match | `.gemini/agents/` |
| Hook | Auto-fires on lifecycle events | `.gemini/settings.local.json` |

<!-- KNOSSOS:END commands -->

<!-- KNOSSOS:START agent-configurations source=agents/*.md regenerate=true -->
## Agents

Prompts in `.gemini/agents/`:

- `potnia.md` - Coordinates development lifecycle phases and routes work to specialists
- `requirements-analyst.md` - Gathers requirements and produces PRD artifacts
- `architect.md` - Creates technical design documents and architecture decisions
- `principal-engineer.md` - Implements code according to design specifications
- `qa-adversary.md` - Validates implementation through adversarial testing
<!-- KNOSSOS:END agent-configurations -->

<!-- KNOSSOS:START platform-infrastructure -->
## Platform

CLI reference: `ari --help`.
<!-- KNOSSOS:END platform-infrastructure -->

<!-- KNOSSOS:START know -->
## Codebase Knowledge

Persistent knowledge in `.know/`. Generate with `/know --all` if not present.

- `read_file(".know/architecture.md")` — package structure, layers, data flow (read before code changes)
- `read_file(".know/scar-tissue.md")` — past bugs, defensive patterns
- `read_file(".know/design-constraints.md")` — frozen areas, structural tensions
- `read_file(".know/conventions.md")` — error handling, file organization, domain idioms
- `read_file(".know/test-coverage.md")` — test gaps, coverage patterns
- `read_file(".know/feat/INDEX.md")` — feature catalog and taxonomy (generate with `/know --scope=feature`)
Work product artifacts in `.ledge/`:

- `.ledge/decisions/` — ADRs and design decisions
- `.ledge/specs/` — PRDs and technical specs
- `.ledge/reviews/` — audit reports and code reviews
- `.ledge/spikes/` — exploration and research artifacts
<!-- KNOSSOS:END know -->

<!-- KNOSSOS:START user-content -->
## Project-Specific Instructions

<!-- Add project conventions, anti-patterns, and active work here.
     This section is preserved during sync. -->
<!-- KNOSSOS:END user-content -->