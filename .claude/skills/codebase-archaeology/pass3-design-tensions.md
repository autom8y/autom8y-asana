# Pass 3: Design Tension Catalog

> Identify structural conflicts, premature/missing abstractions, layering violations, naming mismatches, and load-bearing jank that agents must navigate rather than "fix."

## Purpose

Design tensions are the knowledge that prevents agents from "fixing" things that are intentionally broken. When an agent encounters a backward-compatibility alias, the naive response is to rename it. The tension analysis explains that this alias is imported everywhere -- removing it without a codebase-wide rename will break everything. This is **Load-Bearing Jank Navigation**: teaching agents to work WITH constraints rather than reflexively removing them.

## Sources

| Source | What to Extract |
|--------|----------------|
| Type hierarchy | Classes, inheritance, mixins, interface compliance |
| Import graph | Circular or surprising dependencies, layering violations |
| Naming audit | Same concept different names, misleading names |
| Responsibility analysis | God objects, classes doing too much or too little |
| Backward-compat markers | Aliases, deprecated fields, TODO comments |
| Dual systems | Two mechanisms for the same concern (legacy + replacement) |

## Search Queries

Parameterized for the target codebase:

```bash
# Backward-compatibility aliases and deprecated markers
Grep pattern: "= \\w+  # (backward|legacy|compat|alias|deprecated)"
Grep pattern: "@deprecated|DeprecationWarning|DEPRECATED"

# TODO/FIXME with structural implications
Grep pattern: "TODO.*refactor|FIXME.*architecture|HACK.*because"

# Layering violations (imports crossing boundaries)
Grep pattern: "from.*\\.(infra|internal).*import" (in non-infra files)

# God objects (files with many methods/functions)
# Use wc -l on source files, flag those >500 lines

# Dual systems (two patterns for same concern)
Grep pattern: "legacy|backward.?compat|fallback.*old|v1.*v2"
```

### Project-Type Variants

| Language | Tension Signals | Common Patterns |
|----------|----------------|-----------------|
| Python | `TypeVar` proliferation, `Protocol` vs ABC, `__all__` inconsistency | Mixin hierarchies, metaclass abuse, `TYPE_CHECKING` imports |
| Go | Interface in wrong package, `interface{}` overuse, package cycles | God packages, leaky abstractions, error wrapping depth |
| TypeScript | `any` escape hatches, `as` casts, barrel file complexity | Props drilling, state management layers, HOC vs hooks |
| Infrastructure | Module boundary violations, env parity gaps, secret sprawl | Monolithic modules, provider lock-in, state management split |

## Categorization

Classify each tension by type:

- **naming_mismatch**: Same concept, different names across the codebase
- **layering_violation**: Component in wrong layer or crossing boundaries
- **under_engineering**: String surgery, regex heuristics, manual parsing where structure is needed
- **over_engineering**: Premature abstraction, unused generalization, dead flexibility
- **missing_abstraction**: Duplicated logic that should be shared
- **premature_abstraction**: Generalization that serves one use case

## Output Schema

Write each tension using the [tension-entry.md](schemas/tension-entry.md) schema. Number sequentially: `[TENSION-001]`, etc.

## Load-Bearing Jank Identification

After cataloging tensions, identify which ones are **load-bearing** -- they MUST NOT be resolved without extreme care because other systems depend on their current behavior.

Criteria for load-bearing status:
1. Multiple callers depend on the current (incorrect) behavior
2. Fixing it requires coordinated changes across many files
3. A partial fix is worse than the current state
4. The tension has survived multiple refactoring efforts (evidence it resists change)

## Quality Indicators

- **Minimum yield**: 8+ tensions for a mature codebase
- **Resolution cost distribution**: Most should be Low or Medium. Many High-cost tensions suggest the system needs refactoring before agent creation
- **Load-bearing count**: 2-5 load-bearing tensions is typical. Zero suggests under-analysis
- **Layer coverage**: Tensions should span at least 3 architectural layers

## Example Entry

```markdown
### [TENSION-001] Type Hierarchy Identity Crisis
- **Type**: naming_mismatch / layering_violation
- **Location**: `src/core/models/entity.py` (lines 324-326), `src/core/registry/`
- **The Tension**: The codebase has three entity types but a backward-compat alias
  `Entity = QueryableEntity` means most call sites import `Entity` without knowing
  they get `QueryableEntity`. The registry returns `EntityBase` but callers routinely
  downcast with isinstance checks, creating a diamond-shaped type hierarchy.
- **Historical Reason**: The system started with a single Entity class. When composites
  were added, they needed a different base. The alias avoids a codebase-wide rename.
- **Ideal Resolution**: Complete the migration: rename all `Entity` imports to
  `QueryableEntity`, remove the alias, introduce proper capability interfaces.
- **Resolution Cost**: Medium -- mechanical rename but touches every registration and test.
- **Agent Navigation Guide**: Work WITH the alias. Be aware the registry returns the
  base type. Use isinstance checks to determine capabilities at runtime.
```

## After This Pass

Proceed to Pass 4 (Golden Paths). Tensions directly inform golden path identification -- the best exemplars are those that navigate tensions correctly.
