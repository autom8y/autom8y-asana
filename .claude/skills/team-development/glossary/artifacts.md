# Artifact Glossary

Naming patterns and conventions for workflow artifacts.

---

## Artifact Types

### By Domain

| Domain | Artifact Types |
|--------|---------------|
| **Development** | prd, tdd, adr, code, test-plan |
| **Documentation** | audit-report, doc-structure, documentation, review-signoff |
| **Hygiene** | smell-report, refactor-plan, commits, audit-signoff |
| **Debt** | debt-ledger, risk-report, sprint-plan |
| **SRE** | observability-report, reliability-plan, infrastructure-changes, resilience-report |

### Type Naming Convention
- All lowercase
- Hyphenated for multi-word
- Describes what is produced, not the agent

```
prd              # Product Requirements Document
tdd              # Technical Design Document
adr              # Architecture Decision Record
smell-report     # Code smell analysis
resilience-report # Chaos engineering results
```

---

## Path Templates

### Pattern
```
docs/{category}/{PREFIX}-{slug}.md
```

### Components

| Component | Description | Examples |
|-----------|-------------|----------|
| `docs/` | Standard documentation root | Always `docs/` |
| `{category}` | Domain-specific subdirectory | requirements, design, hygiene, reliability |
| `{PREFIX}` | Artifact type abbreviation (uppercase) | PRD, TDD, ADR, OBS |
| `{slug}` | Dynamic name placeholder | user-auth, api-gateway |

### Examples by Team

| Team | Path Template | Example |
|------|--------------|---------|
| 10x-dev | `docs/requirements/PRD-{slug}.md` | `docs/requirements/PRD-user-auth.md` |
| 10x-dev | `docs/design/TDD-{slug}.md` | `docs/design/TDD-payment-api.md` |
| doc-team | `docs/audits/AUDIT-{slug}.md` | `docs/audits/AUDIT-api-docs.md` |
| hygiene | `docs/hygiene/SMELL-{slug}.md` | `docs/hygiene/SMELL-legacy-utils.md` |
| debt | `docs/debt/LEDGER-{slug}.md` | `docs/debt/LEDGER-2024-q4.md` |
| sre | `docs/reliability/OBS-{slug}.md` | `docs/reliability/OBS-payment-svc.md` |

---

## Prefix Conventions

### Standard Prefixes

| Prefix | Full Name | Team |
|--------|-----------|------|
| PRD | Product Requirements Document | 10x-dev |
| TDD | Technical Design Document | 10x-dev |
| ADR | Architecture Decision Record | 10x-dev |
| AUDIT | Audit Report | doc-team |
| SMELL | Smell Report | hygiene |
| REFACTOR | Refactor Plan | hygiene |
| LEDGER | Debt Ledger | debt-triage |
| OBS | Observability Report | sre |
| REL | Reliability Plan | sre |
| CHAOS | Chaos Experiment | sre |

### Creating New Prefixes
- 3-6 uppercase letters
- Abbreviation of artifact name
- Unique within team
- Clear meaning when seen in file listings

---

## Category Directories

### Standard Categories

| Category | Purpose | Teams |
|----------|---------|-------|
| `requirements/` | PRDs and requirements | 10x-dev |
| `design/` | TDDs and architecture | 10x-dev |
| `decisions/` | ADRs | 10x-dev |
| `audits/` | Audit reports | doc-team |
| `hygiene/` | Code quality reports | hygiene |
| `debt/` | Debt tracking | debt-triage |
| `reliability/` | SRE artifacts | sre |
| `tests/` | Test plans and results | all |

### Creating New Categories
- Lowercase, singular or plural (be consistent)
- Describes the artifact type, not the team
- Create at project root under `docs/`

---

## Artifact Quality Patterns

### Handoff Artifacts
Artifacts passed between phases should be:
- Self-contained (reader needs no external context)
- Actionable (next agent can work from it alone)
- Complete (all required sections filled)
- Validated (meets handoff criteria)

### Template Sections
Most artifacts include:

1. **Metadata** - Title, date, author, status
2. **Summary** - Executive overview
3. **Body** - Main content sections
4. **Decisions** - Key choices made
5. **Next Steps** - Handoff instructions
6. **References** - Links to related artifacts

---

## Artifact Lifecycle

```
Created → In Progress → Ready for Review → Approved → Archived
```

### Status Tracking
In artifact frontmatter:

```yaml
---
title: PRD-user-auth
status: approved  # draft | in-progress | ready-for-review | approved
author: requirements-analyst
created: 2024-01-15
approved: 2024-01-16
---
```

---

## Cross-References

### Linking Artifacts
Use relative paths:

```markdown
See [PRD-user-auth](../requirements/PRD-user-auth.md) for requirements.
```

### Artifact Chains
Track upstream/downstream:

```markdown
## Related Artifacts
- **Upstream**: [PRD-user-auth](../requirements/PRD-user-auth.md)
- **Downstream**: [Code Implementation](../../src/auth/)
```
