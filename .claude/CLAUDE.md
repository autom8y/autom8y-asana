<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Delegate complex work to specialists via Task tool.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

5-agent workflow (hygiene):

| Agent | Role |
| ----- | ---- |
| **potnia** | Coordinates code hygiene initiative phases |
| **code-smeller** | Detects code smells and quality issues across codebase |
| **architect-enforcer** | Plans refactoring approach and enforces architecture standards |
| **janitor** | Executes code cleanup and improvements |
| **audit-lead** | Audits cleanup results and provides quality signoff |

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

<!-- KNOSSOS:START agent-configurations regenerate=true source=agents/*.md -->
## Agents

Prompts in `.claude/agents/`:

- `potnia.md` - Coordinates code hygiene initiative phases
- `code-smeller.md` - Detects code smells and quality issues across codebase
- `architect-enforcer.md` - Plans refactoring approach and enforces architecture standards
- `janitor.md` - Executes code cleanup and improvements
- `audit-lead.md` - Audits cleanup results and provides quality signoff

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

<!-- KNOSSOS:START hierarchy-map -->

<!-- KNOSSOS:END hierarchy-map -->

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