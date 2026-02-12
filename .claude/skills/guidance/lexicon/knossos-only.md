# Knossos-Only Terms

Framework concepts that have no direct CC primitive equivalent. These are organizational/infrastructure abstractions managed by the `ari` CLI and materialization pipeline.

## Infrastructure Terms

| Term | Definition | Managed By |
|---|---|---|
| **Rite** | Practice bundle grouping agents + mena + config for a domain (e.g., `10x-dev`, `hygiene`) | `ari rite` CLI |
| **Materialization** | Source-to-`.claude/` projection pipeline. Copies agents, mena, hooks, settings into CC-readable locations. | `ari sync` |
| **Inscription** | CLAUDE.md generation from section templates + manifest. Assembles the always-loaded project instructions. | `internal/inscription/` |
| **Mena** | Source directory for dromena + legomena. Contains `.dro.md` and `.lego.md` files that materialize to `.claude/commands/` and `.claude/skills/`. | `ari sync` |
| **Session** | Tracked work context with state machine (ACTIVE/PARKED/ARCHIVED), managed by Moirai agent. | `ari session` CLI |
| **Moirai** | Session lifecycle agent (the Fates). Sole authority for `*_CONTEXT.md` mutations. | Task tool invocation |
| **Clew** | Append-only JSONL event log for session telemetry. Enterprise feature. | `internal/hook/clewcontract/` |
| **White Sails** | Confidence signal (WHITE/GRAY/BLACK) computed at session wrap. Enterprise feature. | `ari sails check` |
| **Pantheon** | Agent collection within a rite. Informal term for the set of agents a rite provides. | Rite manifest |

## Mythology Reference

Evocative labels used throughout the codebase. Each maps to a concrete technical component.

| Myth | Technical Referent |
|---|---|
| **Ariadne** | CLI binary (`ari`) — the thread ensuring return from the labyrinth |
| **Theseus** | Claude Code agent — the navigator with amnesia (finite context window) |
| **Minotaur** | The problem being solved — what Theseus is sent to defeat |
| **Moirai** | Session lifecycle (Clotho=creation, Lachesis=measurement, Atropos=termination) |
| **Pythia** | Intelligence/analytics rite — the oracle |
| **Daedalus** | The builder/architect archetype |
| **Naxos** | Abandonment/parking — where Ariadne was left (session parking) |
| **Athens** | Successful return — session wrap with WHITE sails |
| **Knossos** | The platform itself — the labyrinth |
