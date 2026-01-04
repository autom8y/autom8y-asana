---
name: smell-detection
description: "Cross-team code smell detection patterns with severity classification and debt integration. Use when: detecting code quality issues, cataloging smells for reports or debt ledgers, classifying smell severity. Triggers: smell detection, code smell, dead code, duplication, complexity, naming, imports, architecture smell, process smell, smell taxonomy, severity classification."
---

# smell-detection

> Unified smell detection patterns for code quality assessment.

## Purpose

Provides canonical smell taxonomy, detection heuristics, and severity classification for use across debt-triage-pack, hygiene-pack, and any team assessing code quality.

## Quick Reference

### Smell Categories

| Category | ID Prefix | Example Types |
|----------|-----------|---------------|
| Dead Code | DC-* | Unused functions, zombie imports, orphaned modules |
| DRY Violations | DRY-* | Copy-paste code, repeated constants, parallel implementations |
| Complexity | CX-* | High cyclomatic, deep nesting, god objects |
| Naming | NM-* | Inconsistent naming, misleading names, convention violations |
| Imports | IM-* | Circular deps, wildcard imports, version skew |
| Architecture | AR-* | Leaky abstraction, tight coupling, layer violations |
| Process | PR-* | Missing tests, flaky tests, TODO accumulation |

### Severity Classification

| Score | Severity | Priority | Action |
|-------|----------|----------|--------|
| 16-21 | Critical | P1 | Address immediately |
| 11-15 | High | P2 | Address in sprint |
| 6-10 | Medium | P3 | Address opportunistically |
| 1-5 | Low | P4 | Track for future |

### Detection Approaches

| Approach | When to Use |
|----------|-------------|
| Automated | Clear signatures, high confidence (run first) |
| Semi-Automated | Tool output + judgment (run second) |
| Manual | Subjective or context-dependent (run last) |

## When to Use

| Scenario | What to Read |
|----------|--------------|
| Detecting specific smell type | `taxonomy/{category}.md` |
| Classifying severity | `severity/classification.md` |
| Adjusting for context | `severity/overrides.md` |
| Mapping to debt ledger | `integration/debt-ledger.md` |
| Running automated checks | `integration/tooling.md` |

## Consumers

- **code-smeller** (hygiene-pack): Produces Smell Reports
- **debt-collector** (debt-triage-pack): Produces Debt Ledgers
- Any agent performing code quality assessment

## Progressive Disclosure

### Taxonomy
- [dead-code.md](taxonomy/dead-code.md) - DC-* smell types
- [dry-violations.md](taxonomy/dry-violations.md) - DRY-* smell types
- [complexity.md](taxonomy/complexity.md) - CX-* smell types
- [naming.md](taxonomy/naming.md) - NM-* smell types
- [imports.md](taxonomy/imports.md) - IM-* smell types
- [architecture.md](taxonomy/architecture.md) - AR-* smell types
- [process.md](taxonomy/process.md) - PR-* smell types

### Severity
- [classification.md](severity/classification.md) - Algorithm and weights
- [defaults.md](severity/defaults.md) - Default severity per type
- [overrides.md](severity/overrides.md) - Context adjustments

### Integration
- [debt-ledger.md](integration/debt-ledger.md) - Mapping schema
- [smell-report.md](integration/smell-report.md) - Report format
- [tooling.md](integration/tooling.md) - Automated tools

## Related Skills

- [doc-ecosystem](../../ecosystem-pack/skills/doc-ecosystem/SKILL.md) - Smell report template
- [standards](../../../.claude/skills/standards/SKILL.md) - Code conventions
