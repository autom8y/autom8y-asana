---
name: doc-artifacts
description: "PRD, TDD, ADR, and Test Plan canonical schemas with validation rules. Use when: creating development artifacts, validating artifact structure, checking handoff criteria. Triggers: PRD schema, TDD schema, ADR schema, test plan schema, artifact validation, canonical template."
---

# doc-artifacts

> PRD, TDD, ADR, and Test Plan templates for 10x development workflow

## Purpose

Provides canonical schemas and templates for core development artifacts. Each schema defines required fields, validation rules, and handoff criteria for workflow phase transitions.

## Schemas

| Schema | Pattern | Purpose | Author |
|--------|---------|---------|--------|
| [prd-schema.md](schemas/prd-schema.md) | `docs/requirements/PRD-*.md` | Product requirements | requirements-analyst |
| [tdd-schema.md](schemas/tdd-schema.md) | `docs/design/TDD-*.md` | Technical design | architect |
| [adr-schema.md](schemas/adr-schema.md) | `docs/design/ADR-*.md` | Architecture decisions | architect |
| [test-plan-schema.md](schemas/test-plan-schema.md) | `docs/testing/TEST-*.md` | Test plans | qa-adversary |

## When to Use

- Writing requirements documents (PRD)
- Creating technical designs (TDD)
- Recording architecture decisions (ADR)
- Planning and tracking tests (Test Plan)

## Triggers

PRD, TDD, ADR, test plan, requirements document, technical design, artifact schema, artifact template

## Quick Reference

### PRD Required Fields
- `artifact_id`: `PRD-{slug}`
- `title`, `created_at`, `author`, `status`, `complexity`
- `success_criteria`: Array with testable conditions

### TDD Required Fields
- `artifact_id`: `TDD-{slug}`
- `title`, `created_at`, `author`, `prd_ref`, `status`
- `components`: Array with system components

### ADR Required Fields
- `artifact_id`: `ADR-{number}`
- `title`, `created_at`, `author`, `status`
- `context`, `decision`, `consequences`

### Test Plan Required Fields
- `artifact_id`: `TEST-{slug}`
- `title`, `created_at`, `author`, `prd_ref`, `status`
- `coverage_matrix`, `test_cases`

## Validation

Each schema includes a bash validation function in `artifact-validator.sh`. Return codes:
- `0`: Valid
- `1`: File not found
- `2`: Missing opening delimiter
- `3`: Missing closing delimiter
- `4`: Missing required field
- `5`: Field validation failed

## Progressive Disclosure

- [prd-schema.md](schemas/prd-schema.md) - PRD structure, required fields, validation
- [tdd-schema.md](schemas/tdd-schema.md) - TDD structure, component definitions
- [adr-schema.md](schemas/adr-schema.md) - ADR format, decision records
- [test-plan-schema.md](schemas/test-plan-schema.md) - Test plan structure, coverage matrix

## Related Skills

- [documentation](../documentation/INDEX.lego.md) - Documentation standards routing
- [prompting](../../guidance/prompting/INDEX.lego.md) - Agent invocation patterns
