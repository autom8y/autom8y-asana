<!-- KNOSSOS:START execution-mode -->
## Execution Mode

Use the available agents and slash commands. Agents activate automatically when your prompt matches their description.
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

Summon: `ari agent summon {name}` then restart Gemini Code Assist.
Dismiss: `ari agent dismiss {name}` then restart Gemini Code Assist.
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