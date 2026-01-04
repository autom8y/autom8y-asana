---
name: shared-templates
description: "Multi-team document templates for debt-ledger, risk-matrix, and sprint-debt-package artifacts. Use when: creating debt triage artifacts, producing consistent handoff documents, or validating artifact structure. Triggers: debt ledger, risk matrix, sprint package, debt template, triage template."
---

# Shared Templates

> Canonical templates for debt triage workflow artifacts.

## Templates

| Template | Anchor | Agent | Purpose |
|----------|--------|-------|---------|
| [Debt Ledger](templates/debt-ledger.md) | `#debt-ledger-template` | debt-collector | Technical debt inventory |
| [Risk Matrix](templates/risk-matrix.md) | `#risk-matrix-template` | risk-assessor | Scored and prioritized debt |
| [Sprint Package](templates/sprint-debt-package.md) | `#sprint-debt-packages-template` | sprint-planner | Sprint-ready work units |

## Usage

Reference templates in agent prompts:

```markdown
Produce debt ledgers using `@shared-templates#debt-ledger-template`.
```

## Schemas

Full schema definitions with validation rules:

- [Debt Ledger Schema](schemas/debt-ledger-schema.md)
- [Risk Matrix Schema](schemas/risk-matrix-schema.md)
- [Sprint Debt Package Schema](schemas/sprint-debt-package-schema.md)

## Placeholder Conventions

| Syntax | Meaning |
|--------|---------|
| `{field}` | Required, must replace |
| `{field:default}` | Optional with default |
| `[{section}]` | Optional section |
| `<!-- ... -->` | Guidance (stripped) |

## Versioning

Current: `1.0`

Templates follow semantic versioning. MINOR versions are backward compatible.

## Related

- `@documentation` - Core PRD/TDD/ADR templates
- `@doc-ecosystem` - Ecosystem change templates
- `@cross-team-handoff` - HANDOFF artifact schema
