<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Agents activate automatically when your prompt matches their description.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start source=ACTIVE_RITE+agents regenerate=true -->
## Quick Start

7-agent workflow (eunomia):

| Agent | Role |
| ----- | ---- |
| **potnia** | Coordinates governance phases, gates complexity, manages track selection and back-routes |
| **test-cartographer** | Inventories test ecosystem (files, fixtures, mocks, coverage, adversarial file accumulation) |
| **pipeline-cartographer** | Inventories CI/CD pipelines (workflows, actions, version skew, safety config, duplication) |
| **entropy-assessor** | Grades entropy severity and health per category using weakest-link model |
| **consolidation-planner** | Designs target state with atomic, independently-revertible change specifications |
| **rationalization-executor** | Executes consolidation plan as atomic commits (one commit per planned change) |
| **verification-auditor** | Validates execution against plan and baseline, computes entropy delta, issues verdict |

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

- `potnia.md` - Coordinates governance phases, gates complexity, manages track selection and back-routes
- `test-cartographer.md` - Inventories test ecosystem (files, fixtures, mocks, coverage, adversarial file accumulation)
- `pipeline-cartographer.md` - Inventories CI/CD pipelines (workflows, actions, version skew, safety config, duplication)
- `entropy-assessor.md` - Grades entropy severity and health per category using weakest-link model
- `consolidation-planner.md` - Designs target state with atomic, independently-revertible change specifications
- `rationalization-executor.md` - Executes consolidation plan as atomic commits (one commit per planned change)
- `verification-auditor.md` - Validates execution against plan and baseline, computes entropy delta, issues verdict

### Summonable Heroes
Operational agents available on demand. Their commands handle the lifecycle:
- **myron** - Feature discovery scout -> `/discover`
- **theoros** - Domain auditor -> `/know`
- **dionysus** - Knowledge synthesizer -> `/land`
- **naxos** - Session hygiene -> `/naxos`
- **charon** - Thresholdspace attestation agent -> `/charon`

Summon: `ari agent summon {name}` then restart Gemini Code Assist.
Dismiss: `ari agent dismiss {name}` then restart Gemini Code Assist.
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

<!-- KNOSSOS:START hierarchy-map -->

<!-- KNOSSOS:END hierarchy-map -->

<!-- KNOSSOS:START user-content -->
## Project-Specific Instructions

<!-- Add project conventions, anti-patterns, and active work here.
     This section is preserved during sync. -->
<!-- KNOSSOS:END user-content -->