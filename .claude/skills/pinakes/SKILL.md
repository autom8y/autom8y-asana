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
| **architecture** | `domains/architecture.lego.md` | codebase | Source code structure: packages, layers, entry points, abstractions, data flow |
| **conventions** | `domains/conventions.lego.md` | codebase | Error handling style, file organization, domain-specific idioms, naming patterns |
| **test-coverage** | `domains/test-coverage.lego.md` | codebase | Test gaps, coverage patterns, testing conventions, fixture patterns |
| **scar-tissue** | `domains/scar-tissue.lego.md` | codebase | Past bugs, regressions, fix locations, defensive patterns born from failures |
| **design-constraints** | `domains/design-constraints.lego.md` | codebase | Structural tensions, load-bearing jank, abstraction gaps, evolution constraints, risk zones |
| **radar-confidence-gaps** | `domains/radar-confidence-gaps.lego.md` | radar | Flags .know/ domains where confidence < 0.80 |
| **radar-staleness** | `domains/radar-staleness.lego.md` | radar | Flags .know/ domains past their expires_after window |
| **radar-unguarded-scars** | `domains/radar-unguarded-scars.lego.md` | radar | Matches SCAR locations against untested packages — scars in untested code are unguarded regressions |
| **radar-constraint-violations** | `domains/radar-constraint-violations.lego.md` | radar | Checks documented design constraints and frozen areas against codebase patterns |
| **radar-convention-drift** | `domains/radar-convention-drift.lego.md` | radar | Samples files and checks adherence to documented conventions (error handling, naming, testing style) |
| **radar-architecture-decay** | `domains/radar-architecture-decay.lego.md` | radar | Checks import graph against documented layer model for boundary violations and undocumented cross-cutting imports |
| **radar-recurring-scars** | `domains/radar-recurring-scars.lego.md` | radar | Counts SCARs by category; flags categories with 3+ entries as systemic patterns |
| **advocatus-conventions** | `domains/advocatus-conventions.lego.md` | adversarial | Finds code that contradicts documented conventions in .know/conventions.md |
| **advocatus-architecture** | `domains/advocatus-architecture.lego.md` | adversarial | Finds structural evidence that contradicts documented architecture in .know/architecture.md |
| **advocatus-scar-tissue** | `domains/advocatus-scar-tissue.lego.md` | adversarial | Finds undocumented scars or scars whose fixes have regressed |
| **socratic-architecture** | `domains/socratic-architecture.lego.md` | socratic | Surfaces unstated assumptions in .know/architecture.md |
| **socratic-design-constraints** | `domains/socratic-design-constraints.lego.md` | socratic | Surfaces constraints present in the code but missing from .know/design-constraints.md |
| **feature-census** | `domains/feature-census.lego.md` | feature | Feature enumeration: scans project sources to produce feature taxonomy with GENERATE/SKIP recommendations |
| **feature-knowledge** | `domains/feature-knowledge.lego.md` | feature | Per-feature knowledge capture: purpose, conceptual model, implementation map, boundaries |
| **release-platform-profile** | `domains/release-platform-profile.lego.md` | release | Cached stable platform state: repo ecosystems, pipeline chains, dependency topology, build configs |
| **release-history** | `domains/release-history.lego.md` | release | Release outcome log: versions released, CI pass/fail patterns, failure classifications, trend analysis |

### Scope Values

| Scope | Meaning |
|-------|---------|
| `framework` | Knossos infrastructure (agents, dromena, legomena) |
| `codebase` | Source code quality (Go, Python, shell scripts) |
| `process` | Development workflow (git, CI/CD, testing) |
| `culture` | Team practices (docs, naming, conventions) |
| `radar` | Cross-reference signals: reads .know/ files and detects gaps, drift, decay, and violations |
| `adversarial` | Advocatus diaboli mode: actively searches for evidence that contradicts .know/ claims |
| `socratic` | Socratic mode: surfaces unstated assumptions and undocumented constraints in .know/ files |
| `feature` | Product/feature knowledge: what the project does, why features work the way they do, conceptual models |
| `release` | Release engineering knowledge: platform profiles, dependency topologies, release history, CI patterns |

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

### Domain Criteria — Framework
- [dromena.lego.md](domains/dromena.lego.md) - Slash command audit criteria
- [legomena.lego.md](domains/legomena.lego.md) - Skill audit criteria
- [agents.lego.md](domains/agents.lego.md) - Agent prompt audit criteria
- [hooks.lego.md](domains/hooks.lego.md) - Hook wiring audit criteria
- [mena-structure.lego.md](domains/mena-structure.lego.md) - Mena directory audit criteria

### Domain Criteria — Codebase
- [architecture.lego.md](domains/architecture.lego.md) - Architecture knowledge capture
- [conventions.lego.md](domains/conventions.lego.md) - Conventions knowledge capture
- [test-coverage.lego.md](domains/test-coverage.lego.md) - Test structure and coverage knowledge capture
- [scar-tissue.lego.md](domains/scar-tissue.lego.md) - Scar tissue knowledge capture (failure history, regressions)
- [design-constraints.lego.md](domains/design-constraints.lego.md) - Design constraint knowledge capture (tensions, load-bearing code, risk zones)

### Domain Criteria — Radar (cross-reference signals)
- [radar-confidence-gaps.lego.md](domains/radar-confidence-gaps.lego.md) - Flag .know/ domains with confidence < 0.80
- [radar-staleness.lego.md](domains/radar-staleness.lego.md) - Flag .know/ domains past their expiry window
- [radar-unguarded-scars.lego.md](domains/radar-unguarded-scars.lego.md) - Scars in untested packages (unguarded regressions)
- [radar-constraint-violations.lego.md](domains/radar-constraint-violations.lego.md) - Design constraints contradicted by codebase patterns
- [radar-convention-drift.lego.md](domains/radar-convention-drift.lego.md) - Convention adherence gaps in active packages
- [radar-architecture-decay.lego.md](domains/radar-architecture-decay.lego.md) - Import boundary violations against documented layer model
- [radar-recurring-scars.lego.md](domains/radar-recurring-scars.lego.md) - Scar categories with 3+ entries (systemic patterns)

### Domain Criteria — Adversarial (advocatus diaboli)
- [advocatus-conventions.lego.md](domains/advocatus-conventions.lego.md) - Find code contradicting documented conventions
- [advocatus-architecture.lego.md](domains/advocatus-architecture.lego.md) - Find structural evidence contradicting documented architecture
- [advocatus-scar-tissue.lego.md](domains/advocatus-scar-tissue.lego.md) - Find undocumented scars or regressed fixes

### Domain Criteria — Socratic
- [socratic-architecture.lego.md](domains/socratic-architecture.lego.md) - Surface unstated assumptions in architecture documentation
- [socratic-design-constraints.lego.md](domains/socratic-design-constraints.lego.md) - Surface undocumented constraints present in code

### Domain Criteria — Feature
- [feature-census.lego.md](domains/feature-census.lego.md) - Feature enumeration census with GENERATE/SKIP recommendations
- [feature-knowledge.lego.md](domains/feature-knowledge.lego.md) - Per-feature knowledge capture (purpose, model, implementation, boundaries)

### Domain Criteria — Release
- [release-platform-profile.lego.md](domains/release-platform-profile.lego.md) - Cached platform state (ecosystems, pipelines, topology, configs)
- [release-history.lego.md](domains/release-history.lego.md) - Release outcome history (log, failures, CI patterns, trends)

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

- `smell-detection` skill — Code quality smell taxonomy
- `doc-ecosystem` skill — Template patterns
