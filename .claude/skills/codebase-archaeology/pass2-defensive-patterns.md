# Pass 2: Defensive Pattern Inventory

> Catalog every guard, assertion, constraint, validation, and safety check that prevents correctness failures. Also identify unguarded risk zones where defenses are missing.

## Purpose

Defensive patterns form a dependency graph -- guards protect against specific failure modes, and removing or bypassing one can re-enable a class of bugs. Agents need to understand which guards are load-bearing and what they protect. More importantly, **unguarded risk zones** (places where defenses are missing) tell agents where to be extra careful.

## Sources

| Source | What to Extract |
|--------|----------------|
| Assertion statements | Domain-specific conditions, invariant checks |
| Validation patterns | Input validation, schema validation, type guards |
| Error handling | Custom exception types, error boundaries, circuit breakers |
| Post-init validation | Constructor-time validation in data classes |
| Configuration guards | Bounds checking, default enforcement, feature flags |
| Runtime safety | Locks, circuit breakers, timeout enforcement, retry policies |

## Search Queries

Parameterized for the target codebase:

```bash
# Assertions with domain conditions
Grep pattern: "assert\\s+\\w" (exclude test files with glob: "!**/test_*")

# Validation patterns
Grep pattern: "raise\\s+(ValueError|TypeError|ValidationError|\\w+Error)"
Grep pattern: "if.*raise|validate|check|guard|ensure|verify"

# Circuit breakers and safety mechanisms
Grep pattern: "circuit.?breaker|retry|timeout|rate.?limit|backoff"

# Post-init and constructor validation
Grep pattern: "__post_init__|__init__.*validate|constructor.*check"
```

### Project-Type Variants

| Language | Guard Patterns | Validation Patterns |
|----------|---------------|---------------------|
| Python | `assert`, `raise ValueError`, `@validator`, `__post_init__` | Pydantic validators, `@property` guards, `frozen=True` |
| Go | `if err != nil`, `panic(`, custom error types | Struct validation, interface compliance checks, `sync.Once` |
| TypeScript | `throw new Error`, type guards (`is`), Zod schemas | Runtime type checks, exhaustive switches, `readonly` |
| Infrastructure | `prevent_destroy`, `precondition`, policy checks | Plan validation, state locking, drift detection |

## Categorization

Group guards by the failure mode they prevent:

- **Data integrity**: Cartesian prevention, row count preservation, referential integrity
- **Schema validation**: Input validation, type safety, name resolution
- **Security**: Injection prevention, access control, escaping
- **Freshness/Staleness**: Cache validity, data age limits, fallback routing
- **Concurrency**: Locks, circuit breakers, rate limiting, idempotency
- **Configuration**: Bounds checking, default enforcement, environment validation
- **Dependency ordering**: Registration order, initialization sequence, DAG validation

## Output Schema

Write each guard using the [guard-entry.md](schemas/guard-entry.md) schema. Number sequentially: `[GUARD-001]`, etc. After cataloging guards, identify risk zones where guards are absent but should exist.

## Risk Zone Detection

After cataloging guards, look for gaps:

1. **Caller-responsibility enforcement**: Guards that generate correct values but rely on callers to use them
2. **Silent fallback**: `except Exception: return default` patterns that swallow errors
3. **Missing validation pairs**: Constructor validates field A but not field B
4. **Incomplete coverage**: Guard exists for path X but not for parallel path Y

Write risk zones as `[RISK-NNN]` entries with recommended guards.

## Quality Indicators

- **Minimum guard yield**: 30+ guards for a mature codebase
- **Guard-to-risk ratio**: At least 10:1. High risk count suggests under-defended system
- **Category coverage**: At least 4 distinct guard categories
- **Dependency graph**: Document which guards depend on other guards

## Example Entry

```markdown
### [GUARD-001] Split-query detection prevents Cartesian products
- **Location**: `src/core/query/resolver.py:285-314`
- **Guards Against**: Cartesian products when metrics span multiple source tables
- **Trigger Condition**: `requires_split_query()` returns True when metrics come
  from 2+ different source tables
- **Failure Without Guard**: 1000 x 1000 = 1,000,000 inflated rows; every metric
  value multiplied by every other table's row count
- **Agent Mapping**: query-specialist (must understand split-query triggers),
  definition-engineer (must not compose definitions that trigger silent cartesians)
```

```markdown
### [RISK-001] No guard against policy bypass in raw query paths
- **Risk**: Code paths executing raw queries may not apply the date floor filter.
  The policy module generates filter strings but enforcement is caller-responsibility.
- **Evidence**: Comment at `engine.py:1416`: "This method does NOT apply date filtering"
- **Impact**: Historical test data leaking into specific query paths
- **Recommended Guard**: Centralized enforcement layer or query builder hook
- **Agent Mapping**: quality-sentinel, query-specialist
```

## After This Pass

Proceed to Pass 3 (Design Tensions) or continue running passes in parallel. The guard inventory informs Pass 4 (Golden Paths) by establishing what the safety net looks like.
