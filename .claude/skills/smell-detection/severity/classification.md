# Severity Classification

> Multi-factor weighted scoring algorithm for smell severity assessment.

## Algorithm

### Scoring Formula

```
severity_score = (impact * 3) + (frequency * 2) + (blast_radius * 2) - (fix_complexity * 1)
```

### Factor Definitions

| Factor | Weight | Scale | Description |
|--------|--------|-------|-------------|
| **Impact** | 3x | 1-3 | Business/user impact if unaddressed |
| **Frequency** | 2x | 1-3 | How often the smell causes problems |
| **Blast Radius** | 2x | 1-3 | Files/components affected by the smell |
| **Fix Complexity** | -1x | 1-3 | Effort to resolve (inverse: higher = lower score) |

### Impact Scale

| Value | Level | Description | Examples |
|-------|-------|-------------|----------|
| **3** | High | Affects users, business logic, or security | Security vulnerability, data corruption risk, user-facing errors |
| **2** | Medium | Affects developer productivity or system reliability | Build failures, flaky tests, unclear architecture |
| **1** | Low | Cosmetic or minor maintenance burden | Naming inconsistencies, unused imports, minor duplication |

### Frequency Scale

| Value | Level | Description | Examples |
|-------|-------|-------------|----------|
| **3** | High | Causes problems daily or on every change | Flaky tests failing every CI run, circular deps blocking refactors |
| **2** | Medium | Causes problems weekly or occasionally | Slow tests delaying feedback, config drift requiring manual sync |
| **1** | Low | Rarely causes problems | Dead code consuming disk space, TODOs requiring occasional triage |

### Blast Radius Scale

| Value | Level | Description | Examples |
|-------|-------|-------------|----------|
| **3** | High | Affects 10+ files or critical system components | God object used across entire codebase, architectural smell in core module |
| **2** | Medium | Affects 3-9 files or moderate scope | Duplicated validation in multiple controllers, parallel implementations |
| **1** | Low | Affects 1-2 files or isolated scope | Single unused function, local complexity hotspot |

### Fix Complexity Scale

| Value | Level | Description | Examples |
|-------|-------|-------------|----------|
| **3** | High | Requires significant refactoring, risky changes | Breaking circular dependency, splitting god object, architectural refactor |
| **2** | Medium | Requires moderate effort, some risk | Extracting duplicated code, improving test coverage, renaming across files |
| **1** | Low | Quick fix, low risk | Removing dead code, fixing import order, deleting unused variable |

## Severity Mapping

### Score to Severity

| Score Range | Severity | Priority | Action | Typical Timeline |
|-------------|----------|----------|--------|------------------|
| **16-21** | Critical | P1 | Address immediately | Within 1 sprint |
| **11-15** | High | P2 | Address in sprint | Within 2 sprints |
| **6-10** | Medium | P3 | Address opportunistically | Within quarter |
| **1-5** | Low | P4 | Track for future | Backlog |

### Example Calculations

#### Example 1: Flaky Test (Critical)

```
Impact: 3 (blocks CI/CD)
Frequency: 3 (fails daily)
Blast Radius: 1 (single test)
Fix Complexity: 1 (usually simple fix)

Score = (3 * 3) + (3 * 2) + (1 * 2) - (1 * 1) = 9 + 6 + 2 - 1 = 16
Severity: CRITICAL (P1)
```

#### Example 2: Circular Dependency (High)

```
Impact: 3 (blocks refactoring)
Frequency: 2 (causes issues occasionally)
Blast Radius: 3 (affects multiple modules)
Fix Complexity: 3 (requires significant refactor)

Score = (3 * 3) + (2 * 2) + (3 * 2) - (3 * 1) = 9 + 4 + 6 - 3 = 16
Severity: CRITICAL (P1)
```

#### Example 3: Copy-Paste Code (High)

```
Impact: 3 (bugs multiply across copies)
Frequency: 2 (occasional inconsistency)
Blast Radius: 2 (3-5 locations)
Fix Complexity: 1 (extract to function)

Score = (3 * 3) + (2 * 2) + (2 * 2) - (1 * 1) = 9 + 4 + 4 - 1 = 16
Severity: CRITICAL (P1)

Note: May be adjusted to HIGH if impact is reduced to 2
```

#### Example 4: Unused Variable (Low)

```
Impact: 1 (no runtime effect)
Frequency: 1 (rarely causes issues)
Blast Radius: 1 (single file)
Fix Complexity: 1 (delete line)

Score = (1 * 3) + (1 * 2) + (1 * 2) - (1 * 1) = 3 + 2 + 2 - 1 = 6
Severity: MEDIUM (P3)

Note: May be adjusted to LOW if frequency is 0 or context allows
```

## Usage Guidelines

### When to Override Defaults

Context-specific factors may warrant adjusting default severity factors:

1. **Critical path code**: Increase Impact (+1)
2. **Frequently modified files**: Increase Frequency (+1)
3. **Public API surface**: Increase Blast Radius (+1)
4. **Simple extraction refactor**: Decrease Fix Complexity (-1)
5. **Legacy code, no tests**: Increase Fix Complexity (+1)

See [overrides.md](overrides.md) for detailed context-based adjustment patterns.

### Severity Output Format

```yaml
smell_id: DRY-COPY-001
smell_type: DRY-COPY
location: src/validators/user.ts:45-62
severity: HIGH
priority: P2
score: 14
factors:
  impact: 3
  frequency: 2
  blast_radius: 2
  fix_complexity: 1
context_notes: "Hot path: validation runs on every request"
```

## Implementation Pseudocode

```python
def classify_severity(smell_type, context_overrides=None):
    # Load default factors for smell_type
    defaults = load_defaults(smell_type)

    # Apply context overrides
    factors = apply_overrides(defaults, context_overrides)

    # Calculate score
    score = (
        (factors.impact * 3) +
        (factors.frequency * 2) +
        (factors.blast_radius * 2) -
        (factors.fix_complexity * 1)
    )

    # Map to severity
    if score >= 16:
        severity, priority = "CRITICAL", "P1"
    elif score >= 11:
        severity, priority = "HIGH", "P2"
    elif score >= 6:
        severity, priority = "MEDIUM", "P3"
    else:
        severity, priority = "LOW", "P4"

    return {
        "severity": severity,
        "priority": priority,
        "score": score,
        "factors": factors
    }
```

## Alignment with Risk Assessment

This scoring system aligns with the risk-assessor scoring from debt-triage:

- **Both use multi-factor weighted scoring**
- **Both prioritize impact over fix complexity**
- **Both map scores to P1-P4 priorities**

Key difference: Smell classification focuses on **code quality metrics**, while risk assessment focuses on **business risk**.

## Related Documentation

- [defaults.md](defaults.md) - Default severity factors for all 42 smell types
- [overrides.md](overrides.md) - Context-based adjustment patterns
- [../integration/debt-ledger.md](../integration/debt-ledger.md) - Integration with debt tracking
