# ADR-0007: Consistent Client Pattern Across Resource Types

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0003](../design/TDD-0003-tier1-clients.md), [TDD-0001](../design/TDD-0001-sdk-architecture.md)

## Context

The SDK needs to implement multiple resource clients (Projects, Sections, CustomFields, Users, Workspaces) in addition to the existing TasksClient. We need to decide how consistently these clients should follow the same patterns.

Forces at play:
1. **Learnability**: Developers using one client should immediately understand others
2. **Maintainability**: Consistent patterns are easier to maintain and extend
3. **Flexibility**: Different resources have different capabilities (some are read-only, some have special operations)
4. **Code reuse**: Duplicating boilerplate across clients is error-prone
5. **Type safety**: All clients should provide proper typing with raw fallback

The TasksClient establishes a pattern:
- Async-first methods with `_async` suffix
- Sync wrappers using `@sync_wrapper` decorator
- `raw=True` parameter for dict fallback
- Type overloads for correct inference
- PageIterator for list operations

## Decision

**All resource clients SHALL follow the TasksClient pattern exactly**, with these specific conventions:

### 1. Method Naming Convention

```python
# Async primary (always has _async suffix)
async def get_async(self, gid: str, *, raw: bool = False, ...) -> Model | dict

# Sync wrapper (no suffix, delegates to _async via decorator)
def get(self, gid: str, *, raw: bool = False, ...) -> Model | dict

# List operations (return PageIterator, naming includes what's being listed)
def list_async(self, ...) -> PageIterator[Model]  # Global list
def list_for_project_async(self, project_gid: str, ...) -> PageIterator[Model]  # Scoped list
```

### 2. Standard CRUD Methods (when applicable)

| Method | Async | Sync | Returns |
|--------|-------|------|---------|
| Get by GID | `get_async` | `get` | Model or dict |
| Create | `create_async` | `create` | Model or dict |
| Update | `update_async` | `update` | Model or dict |
| Delete | `delete_async` | `delete` | None |
| List | `list_async` | N/A | PageIterator[Model] |

### 3. Parameter Conventions

```python
# GID parameters: named by resource type
def get_async(self, project_gid: str, ...)  # Not just "gid"

# Raw parameter: always keyword-only, always defaults to False
def get_async(self, ..., *, raw: bool = False, ...)

# opt_fields: always keyword-only, always optional
def get_async(self, ..., *, opt_fields: list[str] | None = None, ...)

# Pagination limit: default 100, keyword-only
def list_async(self, ..., *, limit: int = 100, ...) -> PageIterator
```

### 4. Type Overloads

Every method with `raw` parameter SHALL have overloads:

```python
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ..., ...) -> Model: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True], ...) -> dict[str, Any]: ...

async def get_async(self, gid: str, *, raw: bool = False, ...) -> Model | dict[str, Any]:
    # Implementation
```

### 5. Special Operations

Resource-specific operations follow consistent naming:

```python
# Membership operations (Projects)
async def add_members_async(self, project_gid: str, *, members: list[str]) -> Model
async def remove_members_async(self, project_gid: str, *, members: list[str]) -> Model

# Task operations (Sections)
async def add_task_async(self, section_gid: str, *, task: str, ...) -> None

# Scoped lists
def list_for_workspace_async(self, workspace_gid: str, ...) -> PageIterator[Model]
def list_for_project_async(self, project_gid: str, ...) -> PageIterator[Model]
```

## Rationale

1. **Cognitive load reduction**: Learning one client teaches all clients
2. **Copy-paste safety**: Consistent patterns mean copy-pasting code works predictably
3. **Testing patterns**: Test utilities can be shared across clients
4. **Documentation**: One pattern to document, examples transfer between clients
5. **IDE support**: Consistent naming helps autocomplete and discovery

The TasksClient pattern specifically was chosen because:
- It's already implemented and tested (373 tests passing)
- It balances type safety with flexibility (`raw` parameter)
- PageIterator pattern proven for pagination
- Overloads provide correct type inference without runtime cost

## Alternatives Considered

### Per-Resource Custom Patterns

- **Description**: Let each client evolve its own patterns based on resource needs
- **Pros**:
  - Potentially more ergonomic for specific resources
  - No artificial constraints
- **Cons**:
  - Steeper learning curve
  - Documentation burden
  - Testing complexity
  - Code duplication
- **Why not chosen**: Consistency value exceeds potential ergonomic gains

### Generic Base Client with Method Generation

- **Description**: Define resource schemas, auto-generate CRUD methods
- **Pros**:
  - Less code to maintain
  - Guaranteed consistency
- **Cons**:
  - Harder to customize special operations
  - Magic makes debugging harder
  - Type hints become complex
  - Metaprogramming overhead
- **Why not chosen**: Explicit implementations are clearer and more maintainable

### Separate Async/Sync Client Classes

- **Description**: `TasksAsyncClient` and `TasksSyncClient` as separate classes
- **Pros**:
  - Cleaner separation
  - No need for `_async` suffix
- **Cons**:
  - Doubles number of classes
  - Harder to share internal logic
  - More imports for users
- **Why not chosen**: Single class with both APIs is more convenient

### No Raw Parameter (Models Only)

- **Description**: Always return typed models, users call `model_dump()` for dicts
- **Pros**:
  - Simpler API
  - Forces type safety
- **Cons**:
  - Breaks backward compatibility with autom8
  - Some use cases genuinely need raw dicts
  - Serialization overhead when dict is wanted
- **Why not chosen**: `raw=True` provides escape hatch without breaking typed usage

## Consequences

### Positive
- **Predictable API**: Users know what to expect from any client
- **Shared documentation**: Examples work across clients
- **Easy onboarding**: Learn once, use everywhere
- **Maintainable**: Patterns are easy to verify in code review

### Negative
- **Verbosity**: Some clients might have simpler APIs possible
- **Boilerplate**: Each client repeats similar method signatures
- **Rigid**: Adding truly novel patterns requires careful thought

### Neutral
- **Convention over configuration**: Pattern is documented, not configurable
- **Specific naming**: `_async` suffix is unconventional but clear

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - [ ] All CRUD methods follow naming convention
   - [ ] `raw` parameter with overloads present
   - [ ] PageIterator used for list operations
   - [ ] GID parameters named by resource type

2. **Tests verify pattern**:
   - Test that all clients have expected method signatures
   - Test that overloads work correctly with mypy

3. **Documentation template**: Each client uses same docstring structure

4. **Linting**: Custom lint rule could verify method patterns (future)
