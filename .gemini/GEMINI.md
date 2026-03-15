<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Agents activate automatically when your prompt matches their description.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

6-agent workflow (releaser):

| Agent | Role |
| ----- | ---- |
| **potnia** | Coordinates release phases, gates complexity, manages DAG-branch failure halting |
| **cartographer** | Discovers repos, maps git state, identifies package ecosystems and available commands |
| **dependency-resolver** | Builds cross-repo dependency DAG, detects version mismatches, calculates blast radius |
| **release-planner** | Creates phased execution plan with parallel groups, rollback boundaries, and CI time estimates |
| **release-executor** | Executes the release plan — publishes packages, bumps versions, pushes code, creates PRs |
| **pipeline-monitor** | Monitors CI pipelines via gh CLI, reports green/red matrix, diagnoses failures |

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

<!-- KNOSSOS:START agent-configurations regenerate=true source=agents/*.md -->
## Agents

Prompts in `.gemini/agents/`:

- `potnia.md` - Coordinates release phases, gates complexity, manages DAG-branch failure halting
- `cartographer.md` - Discovers repos, maps git state, identifies package ecosystems and available commands
- `dependency-resolver.md` - Builds cross-repo dependency DAG, detects version mismatches, calculates blast radius
- `release-planner.md` - Creates phased execution plan with parallel groups, rollback boundaries, and CI time estimates
- `release-executor.md` - Executes the release plan — publishes packages, bumps versions, pushes code, creates PRs
- `pipeline-monitor.md` - Monitors CI pipelines via gh CLI, reports green/red matrix, diagnoses failures
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