<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Delegate complex work to specialists via Task tool.
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

Delegate to specialists via Task tool.
<!-- KNOSSOS:END quick-start -->

<!-- KNOSSOS:START agent-routing -->
## Agent Routing

Delegate to specialists via Task tool.
<!-- KNOSSOS:END agent-routing -->

<!-- KNOSSOS:START commands -->
## CC Primitives

| CC Primitive | Invocation | Source |
|---|---|---|
| Slash command | User types `/name` | `.claude/commands/` |
| Skill tool | Model calls `Skill("name")` | `.claude/skills/` |
| Task tool | Model calls `Task(subagent_type)` | `.claude/agents/` |
| Hook | Auto-fires on lifecycle events | `.claude/settings.json` |
Agents cannot spawn other agents — only the main thread has Task tool access.
<!-- KNOSSOS:END commands -->

<!-- KNOSSOS:START agent-configurations source=agents/*.md regenerate=true -->
## Agents

Prompts in `.claude/agents/`:

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

- `Read(".know/architecture.md")` — package structure, layers, data flow (read before code changes)
- `Read(".know/scar-tissue.md")` — past bugs, defensive patterns
- `Read(".know/design-constraints.md")` — frozen areas, structural tensions
- `Read(".know/conventions.md")` — error handling, file organization, domain idioms
- `Read(".know/test-coverage.md")` — test gaps, coverage patterns
- `Read(".know/feat/INDEX.md")` — feature catalog and taxonomy (generate with `/know --scope=feature`)
Work product artifacts in `.ledge/`:

- `.ledge/decisions/` — ADRs and design decisions
- `.ledge/specs/` — PRDs and technical specs
- `.ledge/reviews/` — audit reports and code reviews
- `.ledge/spikes/` — exploration and research artifacts
<!-- KNOSSOS:END know -->

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