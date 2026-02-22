---
name: session-shared
description: "Session and workflow resolution patterns. Use when: validating session state before operations, resolving rite and agent context, delegating to Moirai. Triggers: session resolution, moirai invocation, session pre-flight, workflow resolution."
---

# Session-Lifecycle Shared Sections

> Reusable behavior patterns for session lifecycle commands.

## Available Partials

| Partial | Purpose | Used By |
|---------|---------|---------|
| [session-resolution](session-resolution.md) | Session existence and state validation | All 5 commands |
| [workflow-resolution](workflow-resolution.md) | Rite and agent validation | start, resume, handoff |
| [moirai-invocation](moirai-invocation.md) | Moirai delegation pattern | park, resume, wrap |

## Usage Pattern

Reference partials from behavior.md files:

```markdown
### Pre-flight Validation

Apply [Session Resolution Pattern](session-resolution.md):
- Requires: {state requirement}
- Verb: "{command verb}"
```

## Design Rationale

Partials extract duplicated patterns to:
1. **Single source of truth**: Error messages, validation logic defined once
2. **Consistent behavior**: All commands follow identical patterns
3. **Easier maintenance**: Update pattern in one place
4. **Progressive disclosure**: Skill users can drill into details

## Relationship to session-common

| Directory | Contains | Example |
|-----------|----------|---------|
| `shared/` | **How** (behavioral patterns, validation logic) | Session resolution logic, Moirai invocation |
| `session-common/` | **What** (schemas, data structures, reference docs) | Field definitions, state values, complexity levels |

Both are reference modules; neither is invoked directly.

**Navigation**: For schemas and conceptual models, see the `session-common` skill

## Adding New Partials

1. Identify pattern duplicated across 2+ behavior.md files
2. Extract to new `shared/{pattern-name}.md`
3. Follow schema: When to Apply, Checks, Implementation, Errors, Customization
4. Update INDEX.md with new entry
5. Refactor behavior.md files to reference partial
