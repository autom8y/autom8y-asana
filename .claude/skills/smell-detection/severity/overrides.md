# Context-Based Severity Overrides

> Patterns for adjusting default severity factors based on context.

## Overview

Default severity factors (see [defaults.md](defaults.md)) provide a baseline, but context matters. This document specifies when and how to adjust severity factors based on codebase context.

**General Rule**: Adjust factors by ±1 based on context. Rarely adjust by ±2.

## Impact Adjustments

### Increase Impact (+1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Critical path code** | Code in request handling, payment processing, auth | Complexity smell in payment processor → Impact 3 (was 2) |
| **Security-sensitive code** | Authentication, authorization, data validation | Leaky abstraction in auth module → Impact 3 (was 2) |
| **Public API surface** | Exported functions, public interfaces | Misleading name in public API → Impact 3 (was 2) |
| **High-traffic code** | Hot paths, frequently executed code | Unused variable in request handler → Impact 2 (was 1) |
| **Data integrity code** | Database migrations, data transformations | Copy-paste code in migration → Impact 3 (already 3, confirm) |

### Decrease Impact (-1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Test-only code** | Test helpers, fixtures, mocks | Complexity in test setup → Impact 1 (was 2) |
| **Development tools** | Build scripts, local dev utilities | Dead code in build script → Impact 1 (already 1) |
| **Deprecated code** | Code scheduled for removal | Naming inconsistency in deprecated module → Impact 1 (was 2) |
| **Experimental code** | Prototypes, spike code (marked as such) | God object in spike → Impact 1 (was 3) |

## Frequency Adjustments

### Increase Frequency (+1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Frequently modified files** | Files changed in >20% of recent commits | Divergent change in router.ts → Frequency 3 (confirm) |
| **Active development areas** | Features under active development | DRY violation in new feature area → Frequency 3 (was 2) |
| **CI/CD bottlenecks** | Flaky tests, slow builds | Flaky test → Frequency 3 (already 3, confirm) |
| **Team pain points** | Issues repeatedly mentioned in retros | Complexity in commonly debugged module → Frequency 3 (was 2) |

### Decrease Frequency (-1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Stable, rarely touched code** | Files unchanged for 6+ months | Dead code in legacy module → Frequency 1 (already 1) |
| **One-time scripts** | Migration scripts, data fixes | Missing tests in one-off script → Frequency 1 (was 2) |
| **External dependencies** | Vendored code, third-party wrappers | Convention violation in vendored code → Frequency 1 (was 2) |

## Blast Radius Adjustments

### Increase Blast Radius (+1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Widely imported modules** | Utilities, shared libraries, base classes | Naming inconsistency in shared util → Blast Radius 3 (was 2) |
| **Framework core** | Core abstractions, plugin systems | Leaky abstraction in plugin API → Blast Radius 3 (was 2) |
| **Cross-rite dependencies** | Code used by multiple teams | Breaking change in shared module → Blast Radius 3 (was 2) |
| **Database schema** | Schema changes affecting many queries | Missing abstraction for DB access → Blast Radius 3 (was 2) |

### Decrease Blast Radius (-1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Isolated modules** | Feature-specific code with no external dependencies | God object in isolated feature → Blast Radius 2 (was 3) |
| **Internal implementation** | Private functions, unexported code | Complexity in private helper → Blast Radius 1 (was 2) |
| **Single-use code** | Code used in exactly one place | Parallel implementations in isolated module → Blast Radius 1 (was 3) |

## Fix Complexity Adjustments

### Increase Fix Complexity (+1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **No test coverage** | Refactoring requires writing tests first | God object with 0% coverage → Fix Complexity 3 (confirm) |
| **Legacy code** | Old code with unclear requirements | DRY violation in legacy module → Fix Complexity 2 (was 1) |
| **External contracts** | Published APIs, database schemas | Convention violation in public API → Fix Complexity 3 (was 1) |
| **Performance-critical code** | Optimized code where refactoring may regress performance | Complexity in hot path → Fix Complexity 3 (was 2) |

### Decrease Fix Complexity (-1)

| Context | When to Apply | Example |
|---------|---------------|---------|
| **Well-tested code** | >80% coverage with clear tests | Refactoring with test safety net → Fix Complexity 1 (was 2) |
| **Simple extraction** | Obvious refactoring with IDE support | Extract duplicated code → Fix Complexity 1 (already 1, confirm) |
| **Isolated impact** | Change doesn't affect external consumers | Renaming private variable → Fix Complexity 1 (already 1) |
| **Automated fixes available** | Linter auto-fix, code mod | Import order → Fix Complexity 1 (already 1) |

## Combined Context Patterns

### High-Risk Production Code

**Context**: Critical path, public API, high traffic, no tests

| Factor | Adjustment | Rationale |
|--------|------------|-----------|
| Impact | +1 | Critical path |
| Frequency | +0 | Default (varies by smell) |
| Blast Radius | +1 | Public API |
| Fix Complexity | +1 | No tests |

**Example**: Copy-paste code in payment processor
```
Default: Impact 3, Frequency 3, Blast Radius 2, Fix Complexity 1 → Score 16 (CRITICAL)
Adjusted: Impact 3, Frequency 3, Blast Radius 3, Fix Complexity 2 → Score 16 (CRITICAL)
```

### Experimental/Spike Code

**Context**: Prototype, not production-bound, isolated

| Factor | Adjustment | Rationale |
|--------|------------|-----------|
| Impact | -1 | Not production |
| Frequency | -1 | Temporary code |
| Blast Radius | -1 | Isolated |
| Fix Complexity | +0 | May be discarded anyway |

**Example**: God object in spike
```
Default: Impact 3, Frequency 2, Blast Radius 3, Fix Complexity 3 → Score 16 (CRITICAL)
Adjusted: Impact 2, Frequency 1, Blast Radius 2, Fix Complexity 3 → Score 10 (MEDIUM)
```

### Well-Tested Shared Library

**Context**: Widely used, high coverage, clear ownership

| Factor | Adjustment | Rationale |
|--------|------------|-----------|
| Impact | +1 | Widely used |
| Frequency | +0 | Stable code |
| Blast Radius | +1 | Many consumers |
| Fix Complexity | -1 | Tests provide safety |

**Example**: Complexity hotspot in util library
```
Default: Impact 3, Frequency 3, Blast Radius 1, Fix Complexity 2 → Score 14 (HIGH)
Adjusted: Impact 3, Frequency 3, Blast Radius 2, Fix Complexity 1 → Score 17 (CRITICAL)
```

### Legacy Deprecated Module

**Context**: Scheduled for removal, low activity, no new features

| Factor | Adjustment | Rationale |
|--------|------------|-----------|
| Impact | -1 | Being replaced |
| Frequency | -1 | Rarely touched |
| Blast Radius | +0 | Existing consumers remain |
| Fix Complexity | +1 | No tests, unclear requirements |

**Example**: Tight coupling in legacy module
```
Default: Impact 3, Frequency 3, Blast Radius 3, Fix Complexity 3 → Score 18 (CRITICAL)
Adjusted: Impact 2, Frequency 2, Blast Radius 3, Fix Complexity 3 → Score 13 (HIGH)
```

## Documentation Format

When documenting context overrides, use this format:

```yaml
smell_id: CX-GOD-001
smell_type: CX-GOD
location: src/services/payment-processor.ts
severity: CRITICAL
priority: P1
score: 17
factors:
  impact: 3        # Default: 3 (no change)
  frequency: 2     # Default: 2 (no change)
  blast_radius: 3  # Default: 3 (no change)
  fix_complexity: 2  # Default: 3 (-1: well-tested, 85% coverage)
context_notes: |
  - Critical path: payment processing (confirms high impact)
  - Well-tested (85% coverage): reduced fix complexity from 3 to 2
  - Widely used across checkout flow: confirms high blast radius
```

## Anti-Patterns

### Over-Adjustment

**Don't**: Adjust multiple factors by ±2 or adjust all four factors
- This indicates either wrong default or exceptional context requiring manual assessment

**Example**: Don't adjust DRY-COPY from (3,3,2,1) to (1,1,1,3) - if context is that different, reconsider if it's actually a smell

### Ignoring Defaults

**Don't**: Always adjust without checking defaults first
- Defaults are calibrated; only adjust when context truly differs

**Example**: Don't automatically increase impact for all public APIs - check if default already accounts for it

### Inconsistent Application

**Don't**: Apply overrides inconsistently across similar smells
- Document patterns and apply them uniformly

**Example**: If you increase blast radius for shared utils, apply same logic to all smells in shared utils

## Related Documentation

- [defaults.md](defaults.md) - Default severity factors for all smell types
- [classification.md](classification.md) - Scoring algorithm and severity mapping
- [../taxonomy/](../taxonomy/) - Smell type definitions and detection heuristics
