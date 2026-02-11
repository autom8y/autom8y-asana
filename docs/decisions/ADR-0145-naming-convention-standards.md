# ADR-0145: Naming and Convention Standards

## Metadata

- **Status**: Accepted
- **Author**: Architect Enforcer
- **Date**: 2026-02-11
- **Deciders**: Architect Enforcer, Pythia (Deep Code Hygiene initiative)
- **Related**: Smell Report Phase 3 (WS-8 Catalog), ADR-0001 (Protocol Extensibility)

## Context

The autom8_asana codebase has grown organically over multiple initiative cycles (cache infrastructure, entity resolution, automation, dataframes) with contributions from different agents and sessions. No formal naming or convention standard existed. A systematic catalog (WS-8 of the Deep Code Hygiene initiative) inventoried the current state:

- **74+ production classes** using 12 distinct suffixes (Client, Provider, Manager, Registry, Executor, Coordinator, Service, Builder, Factory, Handler, Strategy, Mixin)
- **30 enum classes** with inconsistent base class choices (20 `str, Enum`, 9 plain `Enum`, 1 `IntEnum`)
- **Zero usage of `Final`** across all module-level constants
- **Two naming collisions**: `ActionExecutor` (2 classes) and `BuildStatus` (2 enums)
- **Four freshness-related enums** with overlapping names and partially overlapping semantics

**Forces at play:**

1. **Consistency**: New contributors (human or AI) need clear conventions to follow
2. **Discoverability**: IDE search for "Executor" should produce a coherent, non-ambiguous result set
3. **Stability**: Renaming existing classes would break imports, test references, and ADR citations across the codebase
4. **Proportionality**: The codebase works correctly today -- conventions should not trigger a mass refactoring campaign
5. **Serialization safety**: Enum string values appear in API responses, cache keys, and log output -- base class choice has runtime consequences

**Problem**: Without codified conventions, each new module risks introducing a new suffix interpretation, a new enum base class choice, or a new naming collision. This ADR codifies the dominant patterns as standards for new code and documents existing exceptions as grandfathered.

## Decision

Adopt the following six convention categories as standards for all new production code in `src/autom8_asana/`. Existing code is grandfathered and need not be modified to comply, though it MAY be aligned during refactoring work that touches the relevant module.

### 1. Class Suffix Conventions

Each suffix carries a specific semantic meaning. New classes MUST use the correct suffix for their role.

| Suffix | Semantic | When to Use | Current Count |
|--------|----------|-------------|---------------|
| **Client** | Wraps an external HTTP/API boundary | Class that sends requests to Asana API or another service | 18 |
| **Provider** | Implements a Protocol to supply a capability | Class that satisfies a dependency injection contract (cache, auth, logging) | 14 |
| **Registry** | Stores and retrieves registrations by key | Lookup table for registered types, schemas, connections, or configurations | 8 |
| **Service** | Orchestrates domain logic using multiple dependencies | Stateless class combining clients, providers, and domain rules to fulfill a use case | 5 |
| **Coordinator** | Manages cross-cutting lifecycle across components | Class that sequences operations across multiple services or subsystems (cache warming, freshness checks) | 4 |
| **Executor** | Runs a unit of work given a prepared plan | Class that takes a pre-built action list and executes it (batch operations, rule actions) | 4 |
| **Builder** | Constructs a complex object step-by-step | Class that assembles DataFrames, action lists, or other composite structures incrementally | 4 |
| **Manager** | Owns lifecycle of a resource | Class that creates, pools, and disposes connections or other stateful resources | 5 |
| **Factory** | Creates instances based on configuration | Class that selects and instantiates the right Provider/Client/Builder variant | 2 |
| **Handler** | Processes an incoming event or response | Class that receives and transforms HTTP responses, webhook payloads, or events | 1 |
| **Strategy** | Encapsulates an algorithm variant | Class that implements one approach to a problem where multiple algorithms exist | 1 |
| **Mixin** | Adds reusable field/method groups to classes | Class providing descriptor fields or utility methods for multiple-inheritance composition | 8 |

**Rules for new code:**

- **DO** choose the suffix that matches the semantic role above.
- **DO NOT** use `Helper`, `Util`, `Wrapper`, or `Base` as class suffixes. Use `Service` for orchestration, `Mixin` for shared behavior, and ABC/Protocol for abstract types.
- **DO NOT** introduce new suffixes without updating this ADR.
- When a class could plausibly use two suffixes (e.g., "is it a Service or a Coordinator?"), prefer the more specific suffix. A `Coordinator` sequences operations across subsystems; a `Service` orchestrates domain logic within a bounded context.

### 2. Enum Base Class Convention

| Pattern | When to Use | Rationale |
|---------|-------------|-----------|
| `str, Enum` | The enum value appears in serialized output (API responses, cache keys, log messages, config files) | String serialization is automatic; `json.dumps()` and f-strings produce the value without `.value` |
| `Enum` (plain) | The enum is used only for internal control flow and never serialized | Avoids implicit string coercion; makes it clear the value is not part of any external contract |
| `IntEnum` | The enum represents a numeric ranking or ordering where arithmetic comparisons (`<`, `>`) are meaningful | Enables `level_a > level_b` comparisons; use sparingly |

**Rules for new code:**

- **Default to `str, Enum`** for new enums. The dominant pattern (20 of 30) is `str, Enum`, and the serialization safety it provides outweighs the minimal overhead.
- **Use plain `Enum`** only when the enum is provably internal (not logged, not cached, not returned in any response). Document this choice with a comment: `# Internal-only; see ADR-0145`.
- **Use `IntEnum`** only when ordinal comparison is required. Current usage: `CompletenessLevel`.
- **DO NOT** mix `str, Enum` and plain `Enum` for enums in the same domain. If one freshness enum is `str, Enum`, all freshness enums should be.

**Grandfathered exceptions**: The 9 existing plain `Enum` classes (`EntityType`, `BackoffType`, `Subsystem`, `CBState`, `ConnectionState`, `EntityState`, `OperationType`, `ActionVariant`, `FreshnessMode`) are not required to change. If any of these is refactored and its values are found in serialized output, it SHOULD be converted to `str, Enum` at that time.

### 3. Module Naming Convention

The existing pattern is already consistent and is codified here.

| Scope | Convention | Example |
|-------|-----------|---------|
| **Model module** (defines a single domain entity) | Singular | `models/task.py`, `models/project.py` |
| **Client module** (operations for a resource type) | Plural | `clients/tasks.py`, `clients/projects.py` |
| **Package directory** | Plural | `clients/`, `services/`, `models/`, `protocols/` |
| **Utility/config module** | Singular (describes the concept) | `config.py`, `entrypoint.py`, `settings.py` |

**Rules for new code:**

- **Model files** are singular: the file defines one entity type.
- **Client/service files** are plural: the file contains operations on a collection of entities.
- **Packages** are always plural.
- **When ambiguous**, ask: "Does this file define a thing (singular) or operations on things (plural)?"

### 4. Constants Typing Convention

The codebase currently uses zero `Final` annotations for module-level constants despite having 20+ module-level immutable values (error tuples, mappings, sets).

**Rules for new code:**

- **New module-level constants SHOULD use `Final`** from `typing` to prevent accidental reassignment:

  ```python
  from typing import Final

  MAX_RETRIES: Final = 3
  SUPPORTED_TYPES: Final[frozenset[str]] = frozenset({"task", "project", "section"})
  ERROR_MAP: Final[dict[str, type[Exception]]] = {"timeout": TimeoutError, ...}
  ```

- **Immutable collection types are preferred** for constants:
  - Use `tuple` over `list` for ordered sequences that should not be mutated.
  - Use `frozenset` over `set` for unordered unique collections.
  - `dict` is acceptable when the mapping is not expected to be modified (Python has no built-in frozen dict).

- **Exception tuples** (used in `except` clauses) SHOULD remain as `tuple[type[Exception], ...]` with `Final`:

  ```python
  TRANSPORT_ERRORS: Final[tuple[type[Exception], ...]] = (ConnectionError, TimeoutError, OSError)
  ```

- **Existing constants are NOT required to migrate to `Final`**. Migration MAY happen opportunistically when a module is being modified for other reasons.

- **DO NOT** add `Final` to class-level attributes or instance variables -- this convention applies only to module-level constants.

### 5. Naming Collision Policy: ActionExecutor

Two classes named `ActionExecutor` exist in different packages:

| Location | Purpose | Bounded Context |
|----------|---------|-----------------|
| `persistence/action_executor.py:98` | Executes batch API actions (create, update, delete tasks via Asana batch API) | Persistence / Save Session |
| `automation/polling/action_executor.py:78` | Executes polling rule actions (triggered by event detection) | Automation / Event Processing |

**Assessment**: These classes serve different bounded contexts (persistence vs. automation) and are never imported together. The collision is an annoyance for global search but not a functional problem.

**Decision**: Accept the collision. No rename is required.

**Rationale:**

1. Both names accurately describe their role (they execute actions).
2. The package hierarchy disambiguates: `persistence.action_executor.ActionExecutor` vs. `automation.polling.action_executor.ActionExecutor`.
3. Renaming either would break existing imports, tests, and documentation references for zero functional benefit.
4. If a future module needs to import both, use aliased imports:

   ```python
   from autom8_asana.persistence.action_executor import ActionExecutor as PersistenceExecutor
   from autom8_asana.automation.polling.action_executor import ActionExecutor as PollingExecutor
   ```

**Rule for new code**: Before creating a new class, search for existing classes with the same name. If a collision would occur across packages, prefer a more specific name (e.g., `BatchActionExecutor` instead of `ActionExecutor`). The existing collisions are grandfathered; new collisions should be avoided.

### 6. Naming Collision Policy: BuildStatus and Freshness Enums

#### BuildStatus

Two `BuildStatus` enums exist with different members and different base classes:

| Location | Base | Members | Domain |
|----------|------|---------|--------|
| `dataframes/builders/build_result.py:90` | `str, Enum` | SUCCESS, PARTIAL, FAILURE | DataFrame build outcomes (API-facing) |
| `cache/dataframe/coalescer.py:21` | `Enum` | BUILDING, SUCCESS, FAILURE | Coalescer internal state tracking |

**Assessment**: These enums serve different domains and are not interchangeable. The coalescer's `BUILDING` state has no analog in the builder's result enum. The builder's `PARTIAL` state has no analog in the coalescer's state machine.

**Decision**: Accept the collision. No rename is required.

**Rationale**: Same reasoning as `ActionExecutor` -- package hierarchy disambiguates, and the enums are never used in the same context. The coalescer enum SHOULD be migrated to `str, Enum` per Convention 2 if it is ever found in serialized output (it currently is not).

#### Freshness Enums

Four freshness-related enums exist across the cache subsystem:

| Enum | Location | Base | Members | Purpose |
|------|----------|------|---------|---------|
| `Freshness` | `cache/models/freshness.py:20` | `str, Enum` | STRICT, EVENTUAL, IMMEDIATE | Cache read mode (how aggressively to validate) |
| `FreshnessClassification` | `cache/models/freshness_stamp.py:37` | `str, Enum` | FRESH, APPROACHING_STALE, STALE | Result of TTL evaluation against policy |
| `FreshnessStatus` | `cache/integration/dataframe_cache.py:43` | `str, Enum` | FRESH, STALE_SERVABLE, EXPIRED_SERVABLE, SCHEMA_MISMATCH, WATERMARK_STALE, CIRCUIT_LKG | Entity-aware freshness check result (per ADR-0066) |
| `FreshnessMode` | `cache/integration/freshness_coordinator.py:30` | `Enum` | STRICT, EVENTUAL, IMMEDIATE | Freshness validation mode for coordinator |

**Assessment**: These are NOT duplicates. They represent four distinct concepts in the cache lifecycle:

1. **`Freshness`** = input parameter (what freshness behavior the caller wants)
2. **`FreshnessClassification`** = TTL evaluation output (how fresh is this entry?)
3. **`FreshnessStatus`** = entity-aware evaluation output (considering LKG, schema, circuit breaker)
4. **`FreshnessMode`** = coordinator configuration (mirrors `Freshness` but decoupled for the coordinator's bounded context)

**Decision**: Accept as intentional domain modeling. The `Freshness` / `FreshnessMode` overlap (identical members, different locations) SHOULD be consolidated in a future refactoring effort -- `FreshnessMode` should import and re-use `Freshness` rather than redefining the same values. This is deferred work, not part of this ADR.

**Decision**: `FreshnessMode` SHOULD additionally be changed from plain `Enum` to `str, Enum` per Convention 2, since it mirrors a `str, Enum` type. This is deferred work.

**Rule for new code**: Do not create additional freshness enums. If a new cache component needs freshness semantics, import one of the existing four enums. If none fits, discuss in a PR review before introducing a fifth.

## Rationale

### Why Codify Dominant Patterns (Not Ideal Patterns)

The conventions above are derived from what the codebase already does, not from theoretical best practices. This is intentional:

1. **Low adoption friction**: Developers following these conventions produce code that looks like existing code.
2. **No mass refactoring**: Grandfathering existing code avoids a risky, high-churn migration with zero functional benefit.
3. **Evidence-based**: Each convention is backed by inventory counts. `str, Enum` is the standard because 20 of 30 enums already use it, not because of an abstract preference.

### Why Grandfather Existing Code

Renaming existing classes or changing enum base classes would:

- Break imports across the codebase
- Invalidate existing ADR references and documentation
- Risk behavioral changes (especially for enums where serialized values appear in caches or APIs)
- Produce large diffs that obscure meaningful changes in code review

The cost of retroactive alignment far exceeds the benefit. Conventions apply to new code; existing code aligns opportunistically during related refactoring.

### Why Accept Naming Collisions

Both `ActionExecutor` and `BuildStatus` collisions occur across well-separated bounded contexts. Renaming would:

- Change names that accurately describe their roles
- Break imports and tests for zero functional benefit
- Set a precedent that every name must be globally unique, which does not scale

The Python import system handles same-named classes in different packages. IDEs can disambiguate. The risk is low.

## Alternatives Considered

### Alternative 1: Prescriptive Standard with Mandatory Migration

- **Description**: Define ideal conventions and require all existing code to conform within a time-boxed sprint
- **Pros**: Complete consistency across the codebase; no grandfathered exceptions
- **Cons**: High risk of behavioral changes (especially enum base class changes affecting serialization); large diff churn; significant test breakage during migration; blocks feature work
- **Why not chosen**: The cost-benefit ratio is extremely unfavorable. The codebase functions correctly with current names. Migration risk outweighs consistency benefit.

### Alternative 2: No Convention Standard (Status Quo)

- **Description**: Continue without formal naming standards; rely on code review to catch issues
- **Pros**: Zero effort; no document to maintain
- **Cons**: Each new contributor (or AI agent) makes ad-hoc choices; naming collisions accumulate; inconsistency compounds over time
- **Why not chosen**: The WS-8 catalog demonstrated that organic growth has already produced collisions and inconsistencies. Without a standard, the problem worsens with each initiative.

### Alternative 3: Automated Linting Enforcement

- **Description**: Implement custom linting rules (e.g., via `ruff` or `pylint` plugins) to enforce naming conventions at CI time
- **Pros**: Conventions enforced automatically; no reliance on code review discipline
- **Cons**: Custom lint rules are expensive to write and maintain; suffix semantics are context-dependent and hard to lint; high false-positive risk for edge cases
- **Why not chosen**: The conventions are semantic, not syntactic. A linter can verify that an enum inherits from `str, Enum`, but it cannot verify that a class suffix matches its architectural role. Code review is the appropriate enforcement mechanism. Targeted lint rules (e.g., "new enums should use `str, Enum`") MAY be added later as a low-cost supplement.

## Consequences

### Positive

1. **Clear guidance for new code**: Contributors know which suffix, base class, and module name to use without studying the entire codebase.
2. **Reduced naming collisions**: The "search before naming" rule prevents new collisions.
3. **Serialization safety**: Defaulting to `str, Enum` prevents the class of bugs where `json.dumps()` produces `<BuildStatus.SUCCESS: 'success'>` instead of `"success"`.
4. **Incremental improvement**: Existing code can align opportunistically during refactoring, producing gradual consistency improvement without dedicated migration sprints.

### Negative

1. **Grandfathered inconsistencies persist**: The 9 plain `Enum` classes and 2 naming collisions remain until separately addressed.
2. **Convention document requires maintenance**: As new patterns emerge, this ADR must be updated or superseded.
3. **Subjective suffix boundaries**: The distinction between Service and Coordinator (or Manager and Provider) requires judgment. This ADR provides guidance but cannot eliminate all ambiguity.

### Neutral

1. **No code changes**: This ADR is documentation only. No production code is modified.
2. **No test impact**: No tests are added, removed, or modified.
3. **Deferred work identified**: `FreshnessMode` consolidation into `Freshness` and `FreshnessMode` base class alignment are identified as future tasks but not scheduled.

## Compliance

### Enforcement Mechanisms

1. **Code review**: Reviewers should check new classes against the suffix table and new enums against the base class convention. Reference this ADR in review comments.
2. **ADR citation**: When creating a new class or enum, include a brief comment citing this ADR if the naming choice is non-obvious: `# Per ADR-0145: Coordinator (sequences cross-subsystem operations)`.
3. **Pre-commit search**: Before naming a new class, search for existing classes with the same name: `grep -r "class ClassName" src/`.
4. **Opportunistic alignment**: When modifying a module for other reasons, consider aligning grandfathered code with these conventions. This is encouraged but not required.

### Scope

- **Applies to**: All new production code in `src/autom8_asana/`
- **Does not apply to**: Test code (test mocks and fixtures follow their own conventions), third-party code, configuration files
- **Grandfather clause**: All existing code as of 2026-02-11 is compliant by definition. Compliance applies only to new or substantially rewritten code.
