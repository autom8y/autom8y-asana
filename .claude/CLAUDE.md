<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Delegate complex work to specialists via Task tool.
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

5-agent workflow (data-analyst):

| Agent | Role |
| ----- | ---- |
| **potnia** | Coordinates numerical-product build phases; holds GATE-1 and GATE-2 as phase-entry conditions, selects the complexity track (READOUT/METRIC/EMISSION), and triggers critic-substitution on lineage degeneracy |
| **model-provenance-author** | Authors the authoritative definitions + provenance trail (G7), proves cross-method equivalence (G6), and rules + defends the denominator population (G2-ruling) — the merged authoritative-definition soul (domain workflow entry) |
| **grain-integrity-engineer** | Constructs the numeric assembly at the declared unit-of-analysis grain — preserves grain keys or fails loud and asserts post-combination cardinality (G1); enforces the ruled denominator population (G2-enforcement) |
| **integrity-guard-author** | Builds the edge-ordered runtime/CI guards (G3) and mints the typed non-null-coercible refusal (G4) — the SPINE build-half; never authors the oracle that grades whether its own guard bites (critic-never-author) |
| **numerical-adversary** | Authors the two-sided golden + deliberately-broken day-one fixtures and proves the guard bit (teeth, not presence) — the SPINE prove-half; the rite-disjoint adversary, escalates to critic-substitution when in the producing lineage |

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

- `potnia.md` - Coordinates numerical-product build phases; holds GATE-1 and GATE-2 as phase-entry conditions, selects the complexity track (READOUT/METRIC/EMISSION), and triggers critic-substitution on lineage degeneracy
- `model-provenance-author.md` - Authors the authoritative definitions + provenance trail (G7), proves cross-method equivalence (G6), and rules + defends the denominator population (G2-ruling) — the merged authoritative-definition soul (domain workflow entry)
- `grain-integrity-engineer.md` - Constructs the numeric assembly at the declared unit-of-analysis grain — preserves grain keys or fails loud and asserts post-combination cardinality (G1); enforces the ruled denominator population (G2-enforcement)
- `integrity-guard-author.md` - Builds the edge-ordered runtime/CI guards (G3) and mints the typed non-null-coercible refusal (G4) — the SPINE build-half; never authors the oracle that grades whether its own guard bites (critic-never-author)
- `numerical-adversary.md` - Authors the two-sided golden + deliberately-broken day-one fixtures and proves the guard bit (teeth, not presence) — the SPINE prove-half; the rite-disjoint adversary, escalates to critic-substitution when in the producing lineage

### Summonable Heroes
Operational agents available on demand. Their commands handle the lifecycle:
- **myron** - Feature discovery scout -> `/discover`
- **theoros** - Domain auditor -> `/know`
- **dionysus** - Knowledge synthesizer -> `/land`
- **naxos** - Session hygiene -> `/naxos`
- **charon** - Thresholdspace attestation agent -> `/charon`

Summon: `ari agent summon {name}` then restart CC.
Dismiss: `ari agent dismiss {name}` then restart CC.
### Harness Agents
Cross-harness peer-dispatch agents available via their command:
- **iris** - Operational bot — executes API integrations against org-ecosystem services -> `/iris`
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