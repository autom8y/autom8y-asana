<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Agents activate automatically when your prompt matches their description.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

5-agent workflow (intelligence):

| Agent | Role |
| ----- | ---- |
| **potnia** | Coordinates analytics and research initiative phases |
| **analytics-engineer** | Designs tracking plans and implements event instrumentation |
| **user-researcher** | Conducts user research and extracts qualitative insights |
| **experimentation-lead** | Designs experiments with proper statistical methodology |
| **insights-analyst** | Synthesizes quantitative and qualitative data into insights |

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
Agents cannot spawn other agents — only the main thread can dispatch sub-agents.
<!-- KNOSSOS:END commands -->

<!-- KNOSSOS:START agent-configurations regenerate=true source=agents/*.md -->
## Agents

Prompts in `.gemini/agents/`:

- `potnia.md` - Coordinates analytics and research initiative phases
- `analytics-engineer.md` - Designs tracking plans and implements event instrumentation
- `user-researcher.md` - Conducts user research and extracts qualitative insights
- `experimentation-lead.md` - Designs experiments with proper statistical methodology
- `insights-analyst.md` - Synthesizes quantitative and qualitative data into insights

### Summonable Heroes
Operational agents available on demand. Their commands handle the lifecycle:
- **myron** - Feature discovery scout -> `/discover`
- **theoros** - Domain auditor -> `/know`
- **dionysus** - Knowledge synthesizer -> `/land`
- **naxos** - Session hygiene -> `/naxos`

Summon: `ari agent summon {name}` then restart CC.
Dismiss: `ari agent dismiss {name}` then restart CC.
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