# PRD-DESIGN-PATTERNS-E: CRUD Client Base Class

| Field | Value |
|-------|-------|
| **ID** | PRD-DESIGN-PATTERNS-E |
| **Title** | CRUD Client Base Class |
| **Status** | Active |
| **Created** | 2025-12-16 |
| **Meta-Initiative** | Design Patterns Sprint |

---

## 1. Problem Statement

### 1.1 Current State

The SDK contains 6+ resource clients (Tasks, Sections, Tags, Projects, Workspaces, etc.) that implement similar CRUD operations with significant code duplication:

- **get/get_async**: Fetch single resource by GID
- **create/create_async**: Create new resource
- **update/update_async**: Update existing resource
- **delete/delete_async**: Delete resource
- **list/list_async**: Paginated listing (varies by resource)

Initiative D's `@async_method` decorator already reduced async/sync duplication by ~65%. However, the remaining CRUD implementation logic still follows repetitive patterns:

```python
# Pattern repeated in every client
@async_method
@error_handler
async def get(self, {resource}_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Model | dict:
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/{resources}/{{{resource}_gid}}", params=params)
    if raw:
        return data
    return Model.model_validate(data)
```

### 1.2 Original Meta-Initiative Scope

The meta-initiative proposed a **metaclass** approach (`CRUDClientMeta`) to auto-generate CRUD methods. Discovery revealed this approach has critical limitations:

1. **Type overloads cannot be runtime-generated** for mypy/IDE support
2. **Create method signatures vary significantly** between resources
3. **Metaclass complexity is HIGH** for marginal additional benefit
4. **@async_method already handles the major duplication**

### 1.3 Revised Approach

Instead of a metaclass, this PRD specifies a **configuration-based generic base class** that:
- Provides template implementations for standard CRUD operations
- Uses configuration to customize resource-specific details
- Preserves full type safety with explicit overloads
- Integrates with `@async_method` from Initiative D

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. **Reduce CRUD boilerplate** by providing reusable base implementations
2. **Maintain full type safety** with IDE autocomplete and mypy compliance
3. **Support customization** for resource-specific parameters and logic
4. **Demonstrate feasibility** with SectionsClient proof-of-concept
5. **Provide go/no-go recommendation** for migrating remaining clients

### 2.2 Non-Goals

1. **Full metaclass implementation** - Discovery proved this too complex for the benefit
2. **Auto-generate type overloads** - Type checkers cannot see runtime-generated signatures
3. **Eliminate all per-client code** - Custom methods and variations will remain
4. **Migrate all clients** - This initiative migrates SectionsClient only as PoC

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-E-001: CRUDClientConfig Data Class
- Provide a configuration class specifying CRUD behavior
- Include: resource_name, model_class, endpoint_base, gid_param_name
- Support optional overrides for create/update endpoints

#### FR-E-002: CRUDClient Generic Base Class
- Generic over model type `T` (e.g., `CRUDClient[Section]`)
- Inherit from `BaseClient`
- Provide default implementations for get, update, delete
- Create method must remain abstract (signatures vary too much)

#### FR-E-003: Get Method Template
- Standard implementation using config
- Return `T` by default, `dict[str, Any]` when `raw=True`
- Support `opt_fields` parameter

#### FR-E-004: Update Method Template
- Standard implementation using config
- Accept `**kwargs` for fields to update
- Return updated model or raw dict

#### FR-E-005: Delete Method Template
- Standard implementation using config
- Return None
- Use configured endpoint

#### FR-E-006: Type Overload Pattern
- Document required overload pattern for subclasses
- Overloads must be explicit in source for type checker support
- Provide copy-paste templates in TDD

### 3.2 Non-Functional Requirements

#### NFR-E-001: Type Safety
- Full mypy compliance without `type: ignore`
- IDE autocomplete for all methods
- Correct return type inference based on `raw` parameter

#### NFR-E-002: Backward Compatibility
- No changes to public API of migrated clients
- Existing tests must pass without modification

#### NFR-E-003: Performance
- No measurable performance regression
- Identical behavior to hand-written implementations

---

## 4. Design Constraints

### 4.1 Type System Constraints

Python's type system requires **explicit** overload declarations for methods with return types that vary based on parameter values (like `raw`). These cannot be generated at runtime.

Therefore:
- Each subclass MUST declare its own `@overload` signatures
- The base class provides implementation, subclasses provide type declarations
- This is a fundamental limitation, not a design choice

### 4.2 Create Method Variability

Create methods vary significantly:
- **Task**: `name`, `workspace`, `projects`, `parent`, `notes`
- **Section**: `name`, `project`, `insert_before`, `insert_after`
- **Tag**: `workspace`, `name`, `color`, `notes`
- **Project**: `name`, `workspace`, `team`, `public`, `color`, `default_view`

The base class cannot provide a generic create method. Subclasses must implement create individually.

### 4.3 Integration with @async_method

The base class methods will use `@async_method` from Initiative D:
```python
class CRUDClient(BaseClient, Generic[T]):
    @async_method
    @error_handler
    async def get(self, gid: str, *, raw: bool = False, ...) -> T | dict:
        ...
```

---

## 5. Success Criteria

| Criterion | Target |
|-----------|--------|
| Lines reduced in SectionsClient | >= 30% |
| Type safety preserved | 100% mypy pass |
| Existing tests pass | 100% |
| IDE autocomplete functional | Verified |
| Go/no-go recommendation | Documented |

---

## 6. Deliverables

| Deliverable | Description |
|-------------|-------------|
| `CRUDClientConfig` | Configuration dataclass |
| `CRUDClient[T]` | Generic base class with CRUD templates |
| Migrated `SectionsClient` | Proof of concept implementation |
| Evaluation report | Go/no-go recommendation for remaining clients |
| ADR | Decision record for approach taken |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Type overloads too verbose to be useful | Medium | Medium | Provide copy-paste templates |
| Base class doesn't handle edge cases | Medium | Low | Keep ability to override |
| Complexity outweighs benefit | Medium | Medium | PoC evaluation gate |

---

## 8. References

- [TDD-DESIGN-PATTERNS-D](../design/TDD-DESIGN-PATTERNS-D.md) - @async_method decorator
- [ADR-0007](../decisions/ADR-0007-consistent-client-pattern.md) - Consistent Client Pattern
- [PROMPT-MINUS-1-DESIGN-PATTERNS](../initiatives/PROMPT-MINUS-1-DESIGN-PATTERNS.md) - Meta-initiative
- [Mypy Metaclasses Documentation](https://mypy.readthedocs.io/en/stable/metaclasses.html)
