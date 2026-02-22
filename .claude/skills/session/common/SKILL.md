---
name: session-common
description: "Session schema: fields, FSM states, complexity levels, validation. Use when: checking session field definitions, understanding state transitions, validating session data structure. Triggers: session schema, session fields, state machine, session validation."
---

# Session-Common Reference Module

> Shared schemas and patterns for session-lifecycle skills.

## Purpose

This directory contains reference documentation for session state management. These are **not** behavioral patterns (see `../shared/` for those), but rather **schema definitions** and **conceptual models** that describe what session data looks like.

## Available References

| Reference | Purpose | Used By |
|-----------|---------|---------|
| [session-context-schema](session-context-schema.md) | SESSION_CONTEXT.md field definitions | All 5 commands |
| [session-phases](session-phases.md) | Workflow phase transitions and rules | start, handoff, wrap |
| [session-validation](session-validation.md) | Pre-flight validation patterns | All 5 commands |
| [session-state-machine](session-state-machine.md) | Lifecycle state transitions | park, resume, wrap |
| [complexity-levels](complexity-levels.md) | Complexity classification guide | start |
| [anti-patterns](anti-patterns.md) | Common session lifecycle mistakes | All commands |
| [error-messages](error-messages.md) | Standard error message templates | All commands |
| [agent-delegation](agent-delegation.md) | Task tool invocation patterns | start, handoff, wrap |

**Status**: ✓ All referenced files created and validated

## Usage Pattern

Reference schemas from INDEX.lego.md or behavior.md files:

```markdown
See [session-context-schema](../../session-common/session-context-schema.md) for field definitions.
```

## Relationship to shared-sections

| Directory | Contains | Example |
|-----------|----------|---------|
| `session-common/` | **What** (schemas, data structures) | Field definitions, state values |
| `shared/` | **How** (validation patterns, invocation) | Session resolution logic, moirai calls |

Both are reference modules; neither is invoked directly.

## Design Rationale

Centralizing schemas enables:
1. **Single source of truth**: Field definitions in one place
2. **Consistency**: All commands use identical field names
3. **Validation**: Schema can validate SESSION_CONTEXT files
4. **Documentation**: Users can reference schema independently
5. **Evolution**: Schema changes propagate automatically

## Adding New Schemas

1. Identify data structure used across 2+ skills
2. Create new `session-common/{schema-name}.md`
3. Follow format: Overview, Schema Table, Examples, Validation Rules
4. Update INDEX.md with new entry
5. Reference from skill files using relative links
