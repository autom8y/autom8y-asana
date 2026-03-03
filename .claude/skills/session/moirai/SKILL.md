---
name: moirai-fates
description: "Moirai routing table for Fate domains (Clotho/Lachesis/Atropos). Use when: dispatching session operations to the correct Fate, looking up CLI commands for session lifecycle, understanding create/measure/cut domains. Triggers: moirai routing, fate lookup, operation dispatch, session operation."
---

# Moirai Fates Routing Table

> The Moirai are the unified voice of the three Fates. What Clotho spins, Lachesis measures, and Atropos cuts.

## Operation Routing

| Operation | Fate | Domain | CLI Command |
|-----------|------|--------|-------------|
| create_session | Clotho | Creation | `ari session create "{initiative}" -c "{complexity}" [-r {rite}]` |
| create_sprint | Clotho | Creation | — |
| mark_complete | Lachesis | Measurement | — |
| transition_phase | Lachesis | Measurement | `ari session transition -s "{session_id}" {phase}` |
| update_field | Lachesis | Measurement | — |
| park_session | Lachesis | Measurement | `ari session park -s "{session_id}" --reason="{reason}"` |
| resume_session | Lachesis | Measurement | `ari session resume -s "{session_id}"` |
| handoff | Lachesis | Measurement | `ari handoff execute --artifact={artifact} --to={agent}` |
| record_decision | Lachesis | Measurement | — |
| append_content | Lachesis | Measurement | — |
| wrap_session | Atropos | Termination | `ari session wrap -s "{session_id}" [--force]` |
| generate_sails | Atropos | Termination | `ari sails check` |
| delete_sprint | Atropos | Termination | — |

## Loading Protocol

When executing an operation:

1. Parse operation name from input
2. Look up Fate domain in routing table above
3. Read the Fate skill from the source mena: `mena/session/moirai/{fate}.md`
4. Follow operation-specific guidance from the skill
5. Execute via ari CLI where applicable
6. Return structured JSON response

## Error Codes

| Code | Description |
|------|-------------|
| INVALID_OPERATION | Operation name not recognized |
| INVALID_STATE_TRANSITION | State transition not allowed |
| LOCK_HELD | Context lock held by another agent |
| SESSION_NOT_FOUND | No active session exists |
| SPRINT_NOT_FOUND | Specified sprint does not exist |
| LIFECYCLE_VIOLATION | Operation not allowed in current state |
| CLI_FAILURE | ari CLI command failed |

## Control Flags

- `--dry-run`: Preview operation without execution
- `--force`: Bypass non-critical validations
- `--override`: Bypass lifecycle rules (requires reason)
