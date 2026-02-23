---
name: 10x
description: "Switch to 10x-dev rite (PRD-TDD-Code-QA pipeline). Use when: user says /10x, wants development rite, full lifecycle workflow. Triggers: /10x, development rite, dev workflow."
context: fork
---

# /10x - Switch to Development Rite

Switch to 10x-dev, the full lifecycle development rite.

## Behavior

### 1. Invoke Rite Switch

Execute via Bash tool:

```bash
ari sync --rite 10x-dev
```

### 2. Display Knossos

After successful switch, show the agent table:

| Agent | Role |
|-------|------|
| orchestrator | Coordinates multi-phase workflows |
| requirements-analyst | Produces PRDs, clarifies intent |
| architect | Produces TDDs and ADRs, designs solutions |
| principal-engineer | Implements code with craft and discipline |
| qa-adversary | Validates quality, finds edge cases |

### 3. Update Session

If a session is active, update `active_rite` to `10x-dev`.

## When to Use

- Feature development (end-to-end workflow)
- Complex bug fixes requiring design review
- Refactoring with architectural implications
- Integration work, performance optimization

**Don't use for**: Documentation → `/docs` | Code quality → `/hygiene` | Debt assessment → `/debt`
