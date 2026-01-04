# Default Severity Factors

> Default impact, frequency, blast radius, and fix complexity values for all 42 smell types.

## Overview

This document specifies default severity factors for each smell type. These defaults can be adjusted based on context (see [overrides.md](overrides.md)).

**Scoring Formula**: `score = (impact * 3) + (frequency * 2) + (blast_radius * 2) - (fix_complexity * 1)`

**Factor Scale**: 1 (Low), 2 (Medium), 3 (High)

## Dead Code (DC-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| Unused Functions | DC-FN | 1 | 1 | 1 | 1 | 4 | LOW |
| Unused Variables | DC-VAR | 1 | 2 | 1 | 1 | 6 | MEDIUM |
| Unreachable Code | DC-UNREACH | 2 | 1 | 1 | 1 | 8 | MEDIUM |
| Orphaned Modules | DC-MOD | 2 | 1 | 2 | 1 | 10 | MEDIUM |
| Zombie Imports | DC-IMP | 1 | 2 | 1 | 1 | 6 | MEDIUM |
| Dead Branches | DC-BRANCH | 2 | 1 | 1 | 1 | 8 | MEDIUM |
| Commented Code | DC-COMMENT | 1 | 2 | 1 | 1 | 6 | MEDIUM |

### Rationale

Dead code typically has:
- **Low impact**: Doesn't affect runtime behavior
- **Low-medium frequency**: Can accumulate but rarely causes immediate issues
- **Low-medium blast radius**: Usually isolated to single file or module
- **Low fix complexity**: Safe to delete after verification

## DRY Violations (DRY-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| Copy-Paste Code | DRY-COPY | 3 | 3 | 2 | 1 | 16 | CRITICAL |
| Repeated Constants | DRY-CONST | 2 | 2 | 2 | 1 | 11 | HIGH |
| Parallel Implementations | DRY-PARA | 3 | 2 | 3 | 2 | 16 | CRITICAL |
| Config Drift | DRY-CFG | 2 | 1 | 1 | 1 | 7 | MEDIUM |
| Test Duplication | DRY-TEST | 1 | 2 | 1 | 2 | 5 | LOW |

### Rationale

DRY violations typically have:
- **High impact**: Bugs in duplicated code multiply across instances
- **High frequency**: Duplication increases maintenance burden
- **Medium-high blast radius**: Changes require coordinating multiple files
- **Low-medium fix complexity**: Refactoring is usually straightforward, but test consolidation needs care

## Complexity Hotspots (CX-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| High Cyclomatic | CX-CYCLO | 3 | 3 | 1 | 2 | 14 | HIGH |
| Deep Nesting | CX-NEST | 2 | 2 | 1 | 1 | 9 | MEDIUM |
| God Object | CX-GOD | 3 | 2 | 3 | 3 | 16 | CRITICAL |
| Long Parameter List | CX-PARAM | 2 | 2 | 1 | 2 | 9 | MEDIUM |
| Boolean Blindness | CX-BOOL | 1 | 2 | 1 | 1 | 6 | MEDIUM |
| Primitive Obsession | CX-PRIM | 2 | 3 | 2 | 3 | 12 | HIGH |
| Feature Envy | CX-ENVY | 2 | 2 | 2 | 2 | 10 | MEDIUM |

### Rationale

Complexity hotspots typically have:
- **High impact**: Complex code is error-prone and hard to maintain
- **Medium-high frequency**: Complexity compounds over time
- **Low-medium blast radius**: Usually localized, except for god objects
- **Medium-high fix complexity**: Refactoring complex code requires care, especially for god objects and primitive obsession

## Naming Inconsistencies (NM-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| Inconsistent Naming | NM-INCONSIST | 2 | 3 | 3 | 2 | 14 | HIGH |
| Misleading Names | NM-MISLEAD | 3 | 1 | 2 | 1 | 12 | HIGH |
| Convention Violations | NM-CONV | 1 | 2 | 2 | 1 | 8 | MEDIUM |
| Abbreviation Soup | NM-ABBREV | 1 | 2 | 1 | 1 | 6 | MEDIUM |
| Type-Name Mismatch | NM-TYPE | 2 | 1 | 1 | 1 | 7 | MEDIUM |

### Rationale

Naming inconsistencies typically have:
- **Medium-high impact**: Poor names reduce comprehension; misleading names cause bugs
- **Medium-high frequency**: Naming issues accumulate as codebase grows
- **Medium-high blast radius**: Names used across multiple files
- **Low-medium fix complexity**: Renaming is safe with modern IDEs, but requires coordination

## Import Hygiene (IM-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| Circular Dependencies | IM-CIRC | 3 | 2 | 3 | 3 | 16 | CRITICAL |
| Wildcard Imports | IM-WILD | 2 | 2 | 1 | 1 | 9 | MEDIUM |
| Deep Imports | IM-DEEP | 2 | 1 | 2 | 1 | 9 | MEDIUM |
| Barrel Bloat | IM-BARREL | 1 | 1 | 2 | 2 | 6 | MEDIUM |
| Version Skew | IM-VERSION | 2 | 1 | 2 | 2 | 9 | MEDIUM |
| Unused Dependencies | IM-UNUSED | 1 | 1 | 1 | 1 | 4 | LOW |

### Rationale

Import hygiene issues typically have:
- **Medium-high impact**: Circular dependencies block refactoring; version skew causes runtime errors
- **Low-medium frequency**: Import issues accumulate slowly
- **Medium-high blast radius**: Dependency changes affect many files
- **Medium-high fix complexity**: Breaking circular dependencies is complex; other fixes are simpler

## Architecture Smells (AR-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| Leaky Abstraction | AR-LEAK | 3 | 2 | 2 | 2 | 14 | HIGH |
| Tight Coupling | AR-COUPLE | 3 | 3 | 3 | 3 | 18 | CRITICAL |
| Layer Violation | AR-LAYER | 3 | 1 | 3 | 2 | 15 | HIGH |
| Missing Abstraction | AR-MISSING | 2 | 3 | 2 | 2 | 14 | HIGH |
| Shotgun Surgery | AR-SHOT | 3 | 2 | 3 | 3 | 16 | CRITICAL |
| Divergent Change | AR-DIVERGE | 2 | 3 | 2 | 3 | 13 | HIGH |

### Rationale

Architecture smells typically have:
- **High impact**: Architectural issues affect entire system
- **Medium-high frequency**: Poor architecture compounds over time
- **High blast radius**: Changes ripple across many modules
- **Medium-high fix complexity**: Architectural refactoring is risky and time-consuming

## Process Smells (PR-*)

| Smell Type | ID | Impact | Frequency | Blast Radius | Fix Complexity | Default Score | Default Severity |
|------------|-----|--------|-----------|--------------|----------------|---------------|------------------|
| Missing Tests | PR-TEST | 3 | 2 | 2 | 2 | 14 | HIGH |
| Flaky Tests | PR-FLAKY | 3 | 3 | 1 | 2 | 16 | CRITICAL |
| Slow Tests | PR-SLOW | 2 | 2 | 1 | 2 | 9 | MEDIUM |
| Outdated Docs | PR-DOCS | 2 | 2 | 2 | 1 | 11 | HIGH |
| TODO Accumulation | PR-TODO | 1 | 3 | 1 | 1 | 7 | MEDIUM |
| Disabled Tests | PR-SKIP | 2 | 1 | 1 | 1 | 7 | MEDIUM |

### Rationale

Process smells typically have:
- **Medium-high impact**: Poor testing/docs increase risk; flaky tests block deployments
- **Medium-high frequency**: Process issues compound over time
- **Low-medium blast radius**: Usually affects team workflow rather than end users
- **Low-medium fix complexity**: Varies by smell; flaky tests can be tricky, docs are straightforward

## Summary Statistics

| Category | Smell Count | Avg Score | Common Severity |
|----------|-------------|-----------|-----------------|
| Dead Code | 7 | 6.9 | MEDIUM |
| DRY Violations | 5 | 11.0 | HIGH |
| Complexity | 7 | 10.9 | MEDIUM-HIGH |
| Naming | 5 | 9.4 | MEDIUM |
| Imports | 6 | 8.8 | MEDIUM |
| Architecture | 6 | 15.0 | HIGH-CRITICAL |
| Process | 6 | 10.7 | MEDIUM-HIGH |

## Usage

When detecting a smell:

1. Look up the smell type in the appropriate category table
2. Use default factors as starting point
3. Apply context-based adjustments (see [overrides.md](overrides.md))
4. Calculate severity score using the formula in [classification.md](classification.md)
5. Map score to severity level (Critical/High/Medium/Low)

## Related Documentation

- [classification.md](classification.md) - Scoring algorithm and severity mapping
- [overrides.md](overrides.md) - Context-based factor adjustments
- [../taxonomy/](../taxonomy/) - Detailed smell type definitions
