---
name: pinakes
description: "Theoria domain registry and audit criteria catalog. Use when: running /theoria audits, discovering available audit domains, understanding grading criteria. Triggers: theoria, audit, domain criteria, pinakes, grading, domain registry."
---

# pinakes

> The domain registry for theoria audits -- Callimachus's catalog of the labyrinth.

## Purpose

The Pinakes catalogs audit domains: what can be audited, where the criteria live, and how to grade what is found. Every theoria consults the Pinakes before dispatching theoroi.

Named for Callimachus's Pinakes -- the first systematic catalog of the Library of Alexandria. Callimachus did not write the books; he told you which books existed and what they contained. The Pinakes does the same for audit domains.

## Domain Registry

This table IS the registry. A domain exists when it has a row here and a criteria file in `domains/`.

| Domain | Criteria | Scope | Description |
|--------|----------|-------|-------------|
| **dromena** | `domains/dromena.lego.md` | framework | Slash commands: naming, structure, completeness |
| **legomena** | `domains/legomena.lego.md` | framework | Skills: description quality, trigger precision |
| **agents** | `domains/agents.lego.md` | framework | Agent prompts: role clarity, handoff criteria |
| **hooks** | `domains/hooks.lego.md` | framework | Hook wiring: lifecycle coverage, matchers, timeouts |
| **mena-structure** | `domains/mena-structure.lego.md` | framework | Mena directories: naming, INDEX files, manifest registration |

### Scope Values

| Scope | Meaning |
|-------|---------|
| `framework` | Knossos infrastructure (agents, dromena, legomena) |
| `codebase` | Source code quality (Go, Python, shell scripts) |
| `process` | Development workflow (git, CI/CD, testing) |
| `culture` | Team practices (docs, naming, conventions) |

### Grading Scale

All domains use simple letter grades A through F:

| Grade | Meaning | Threshold |
|-------|---------|-----------|
| **A** | Excellent | 90-100% criteria met |
| **B** | Good | 80-89% criteria met |
| **C** | Adequate | 70-79% criteria met |
| **D** | Below Standard | 60-69% criteria met |
| **F** | Failing | Below 60% criteria met |

No +/- modifiers. Simplicity prevents grade inflation and gaming.

## When to Use

| Scenario | What to Read |
|----------|--------------|
| Running a theoria audit | This INDEX (domain registry) |
| Understanding criteria for a domain | `domains/{domain}.lego.md` |
| Adding a new audit domain | `registry-format.lego.md` |
| Understanding grading in detail | `schemas/grading.lego.md` |
| Interpreting audit reports | `schemas/report-format.lego.md` |

## Progressive Disclosure

### Domain Criteria
- [dromena.lego.md](domains/dromena.lego.md) - Slash command audit criteria
- [legomena.lego.md](domains/legomena.lego.md) - Skill audit criteria
- [agents.lego.md](domains/agents.lego.md) - Agent prompt audit criteria
- [hooks.lego.md](domains/hooks.lego.md) - Hook wiring audit criteria
- [mena-structure.lego.md](domains/mena-structure.lego.md) - Mena directory audit criteria

### Schemas
- [registry-format.lego.md](registry-format.lego.md) - How to add new domains
- [grading.lego.md](schemas/grading.lego.md) - Grading scale definitions
- [report-format.lego.md](schemas/report-format.lego.md) - Audit report structure

## Consumers

- **theoros agent**: Domain evaluator dispatched by `/theoria`
- **/theoria dromena**: User-facing audit command
- Any agent performing domain-specific quality assessment

## How to Add a Domain

1. Write criteria file in `domains/{domain}.lego.md`
2. Add row to the Domain Registry table above
3. Run `/theoria {domain}` to validate
4. See `registry-format.lego.md` for full format specification

## Related Skills

- [smell-detection](../smell-detection/INDEX.lego.md) - Code quality smell taxonomy
- [doc-ecosystem](../../../ecosystem/mena/doc-ecosystem/INDEX.lego.md) - Template patterns
