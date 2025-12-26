# ADR-0054: Factory Patterns for Complex Creation

## Metadata
- **Status**: Accepted
- **Consolidated From**: ADR-0099 (BusinessSeeder Factory), ADR-0122 (Action Method Factory)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Related**: [reference/PATTERNS.md](reference/PATTERNS.md), ADR-SUMMARY-SAVESESSION

---

## Context

The SDK has two complex creation scenarios requiring factory patterns:

### 1. Entity Hierarchy Creation (BusinessSeeder)

**Problem**: Consumer applications (webhook handlers, Calendly integration) need to create complete business hierarchies from external triggers:

```
Business → Unit → ProcessHolder → Process
```

Currently consumers must:
- Manually navigate hierarchy
- Handle find-or-create logic themselves
- Manage multiple SaveSession operations
- Remember dual membership setup

**Forces**:
- Developer ergonomics (common operation should be simple)
- Idempotency (same input → same result, no duplicates)
- Flexibility (support various data inputs)
- Async-first (SDK convention)
- SaveSession integration (compose with existing persistence)

### 2. SaveSession Action Methods

**Problem**: SaveSession has 18 action methods (920 lines, 42% of total) following nearly identical patterns:

```python
def add_tag(self, task, tag) -> SaveSession:
    self._ensure_open()
    if isinstance(tag, str):
        target = NameGid(gid=tag)
    else:
        target = NameGid(gid=tag.gid, name=getattr(tag, "name", None))
    validate_gid(target.gid, "tag_gid")
    action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=target)
    self._pending_actions.append(action)
    if self._log:
        self._log.debug("session_add_tag", task_gid=task.gid, tag_gid=target.gid)
    return self
```

Each method differs only in:
- ActionType enum value
- Parameter name (tag, project, user, etc.)
- Positioning support (insert_before/insert_after)
- Target presence (add_like has no target)

**Forces**:
- Preserve exact function signatures
- Type hints must be accurate
- Docstrings accessible via `help()`
- 5 methods have custom logic beyond pattern
- Performance cannot regress

---

## Decision

Use **factory pattern** for entity hierarchy creation and **descriptor-based factory** for action method generation.

### 1. BusinessSeeder Factory

**Create factory class with find-or-create pattern for complete hierarchy creation.**

```python
class BusinessSeeder:
    """Factory for creating business entity hierarchies.

    Implements find-or-create pattern for idempotent hierarchy creation:
    Business → Unit → ProcessHolder → Process

    Example:
        seeder = BusinessSeeder(client)
        result = await seeder.seed_async(
            business=BusinessData(name="Acme Corp"),
            process=ProcessData(name="Opportunity", process_type=ProcessType.SALES)
        )
        # Result contains all created/found entities
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Create or find complete business hierarchy.

        Args:
            business: Business data (name, company_id, optional fields).
            process: Process data (name, type, initial_state).
            contact: Optional contact data.
            unit_name: Optional unit name override.

        Returns:
            SeederResult with all entities and creation flags.

        Example:
            result = await seeder.seed_async(
                business=BusinessData(name="Acme Corp", company_id="123"),
                process=ProcessData(
                    name="Sales Opportunity",
                    process_type=ProcessType.SALES,
                    initial_state=ProcessSection.OPPORTUNITY
                )
            )

            if result.created_business:
                logger.info(f"Created new business: {result.business.name}")
            else:
                logger.info(f"Found existing business: {result.business.name}")
        """
        # Implementation uses SaveSession internally
        ...

    def seed(self, ...) -> SeederResult:
        """Sync wrapper for seed_async."""
        return run_sync(self.seed_async(...))
```

**Input Data Models**:

```python
class BusinessData(BaseModel):
    """Data for business creation/lookup."""
    name: str
    company_id: str | None = None
    # Optional creation fields


class ProcessData(BaseModel):
    """Data for process creation."""
    name: str
    process_type: ProcessType
    initial_state: ProcessSection = ProcessSection.OPPORTUNITY


class ContactData(BaseModel):
    """Optional contact data."""
    full_name: str
    contact_email: str | None = None
```

**SeederResult**:

```python
@dataclass
class SeederResult:
    """Result of hierarchy seeding operation."""
    business: Business
    unit: Unit
    process_holder: ProcessHolder
    process: Process
    contact: Contact | None = None
    created_business: bool = False
    created_unit: bool = False
    created_process_holder: bool = False
```

**Find-or-Create Algorithm**:

1. **Business**: Find by company_id (exact), then by name (exact), or create
2. **Unit**: Find under Business by name, or create
3. **ProcessHolder**: Find under Unit (always "Processes"), or create
4. **Process**: Always create (not idempotent—each seed is new event)

**Rationale**:
- **Factory encapsulates complexity**: Single entry point
- **Find-or-create ensures idempotency**: Webhooks may retry
- **SeederResult provides metadata**: Creation flags for consumer logic
- **Pydantic input models**: Validation and clear schema
- **Process always created**: Each seed represents new business event

### 2. Action Method Factory

**Use descriptor-based factory pattern with configuration registry.**

```python
# In SaveSession class:
add_tag = ActionBuilder("add_tag")
remove_tag = ActionBuilder("remove_tag")
add_to_project = ActionBuilder("add_to_project")
# ... 13 total ActionBuilder declarations

# 5 methods with custom logic remain explicit:
def add_comment(self, task, text, *, html_text=None) -> SaveSession: ...
def set_parent(self, task, parent, *, insert_before=None, insert_after=None) -> SaveSession: ...
def reorder_subtask(self, task, *, insert_before=None, insert_after=None) -> SaveSession: ...
def add_followers(self, task, users) -> SaveSession: ...
def remove_followers(self, task, users) -> SaveSession: ...
```

**ActionBuilder Descriptor**:

```python
class ActionBuilder:
    """Descriptor that generates action methods from configuration.

    Reads ACTION_REGISTRY to determine method behavior and generates
    appropriate bound method when accessed on instance.
    """

    def __init__(self, action_name: str) -> None:
        self._action_name = action_name
        self._config: ActionConfig | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Called at class definition time."""
        # Lookup configuration from registry
        self._config = ACTION_REGISTRY.get(self._action_name)
        if self._config is None:
            raise ValueError(f"No configuration for action: {self._action_name}")

    def __get__(self, obj, objtype=None):
        """Return descriptor on class access, bound method on instance access."""
        if obj is None:
            return self  # Class access
        return self._make_method(obj)  # Instance access

    def _make_method(self, session: SaveSession):
        """Generate bound method based on configuration."""
        config = self._config

        if config.variant == ActionVariant.NO_TARGET:
            def method(task: AsanaResource) -> SaveSession:
                session._ensure_open()
                validate_gid(task.gid, "task_gid")
                action = ActionOperation(
                    task=task,
                    action=config.action_type,
                    target=None
                )
                session._pending_actions.append(action)
                if session._log:
                    session._log.debug(config.log_event, task_gid=task.gid)
                return session

        elif config.variant == ActionVariant.TARGET_REQUIRED:
            def method(
                task: AsanaResource,
                target: AsanaResource | str
            ) -> SaveSession:
                session._ensure_open()
                if isinstance(target, str):
                    target_obj = NameGid(gid=target)
                else:
                    target_obj = NameGid(gid=target.gid, name=getattr(target, "name", None))
                validate_gid(target_obj.gid, f"{config.target_param}_gid")
                action = ActionOperation(
                    task=task,
                    action=config.action_type,
                    target=target_obj
                )
                session._pending_actions.append(action)
                if session._log:
                    session._log.debug(
                        config.log_event,
                        task_gid=task.gid,
                        target_gid=target_obj.gid
                    )
                return session

        elif config.variant == ActionVariant.POSITIONING:
            def method(
                task: AsanaResource,
                target: AsanaResource | str,
                *,
                insert_before: str | None = None,
                insert_after: str | None = None
            ) -> SaveSession:
                # Validate positioning conflict per ADR-0047
                if insert_before and insert_after:
                    raise ValueError("Cannot specify both insert_before and insert_after")
                session._ensure_open()
                # ... same as TARGET_REQUIRED + positioning
                return session

        # Set method metadata
        method.__doc__ = config.docstring
        method.__name__ = self._action_name
        return method
```

**Configuration Registry**:

```python
@dataclass(frozen=True)
class ActionConfig:
    """Configuration for action method generation."""
    action_type: ActionType
    variant: ActionVariant
    target_param: str = ""  # For TARGET_REQUIRED variant
    log_event: str = ""
    docstring: str = ""


class ActionVariant(str, Enum):
    """Action method signature variants."""
    NO_TARGET = "no_target"          # add_like(task)
    TARGET_REQUIRED = "target"       # add_tag(task, tag)
    POSITIONING = "positioning"      # add_to_project(task, project, *, insert_before=...)


ACTION_REGISTRY: dict[str, ActionConfig] = {
    "add_tag": ActionConfig(
        action_type=ActionType.ADD_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        log_event="session_add_tag",
        docstring="Add a tag to a task...",
    ),
    "add_to_project": ActionConfig(
        action_type=ActionType.ADD_TO_PROJECT,
        variant=ActionVariant.POSITIONING,
        target_param="project",
        log_event="session_add_to_project",
        docstring="Add task to project with optional positioning...",
    ),
    # ... 13 total configurations
}
```

**Impact**: 920 lines → ~150 lines (83% reduction).

**Rationale**:
- **Descriptors preserve signatures**: `help()` and type hints work
- **Registry centralizes config**: Single source of truth
- **Easy to extend**: New action = registry entry + one-line declaration
- **Performance**: Per-call overhead negligible

---

## Rationale

### Why Factory Pattern for BusinessSeeder?

| Pattern | Pros | Cons |
|---------|------|------|
| **Factory (BusinessSeeder)** | **Single entry point, encapsulates complexity** | New class to maintain |
| Builder | Fluent API, incremental construction | Complex for simple case |
| Static methods | No instance needed | Hard to inject dependencies |
| Extension methods on client | Discoverable | Pollutes client API |

Factory encapsulates multi-step creation while allowing dependency injection (AsanaClient).

### Why Find-or-Create?

Idempotency critical for webhook handlers:
- Webhooks may retry on failure
- Same booking may trigger multiple calls
- Duplicate entities cause data quality issues

Find-or-create ensures:
- Existing Business reused if found
- New Business created only if needed
- Result always contains valid hierarchy

### Why Process Always Created?

Each seed call represents new business event (sale opportunity, booking, etc.). Even if Business exists, new Process should be created. Process name includes distinguishing info (timestamp, booking ID).

### Why Descriptors for Action Methods?

| Criterion | Decorator | Metaclass | Factory Function | **Descriptor** |
|-----------|-----------|-----------|------------------|----------------|
| Signature preservation | Hard (wraps) | Hard (generates) | Medium | **Easy** |
| IDE support | Poor | Poor | Medium | **Good** |
| `help()` works | No (shows wrapper) | Yes | Medium | **Yes** |
| Runtime cost | Per-call | Class load | Per-call | **Per-call (cached)** |
| Complexity | Low | High | Medium | **Medium** |
| Type hints | Lost | Complex | Partial | **Preserved** |

Descriptors are Python mechanism for attribute access customization. Used by `@property`, `@classmethod`, Django ORM.

### Why Configuration Registry?

Instead of:
```python
add_tag = ActionBuilder(ActionType.ADD_TAG, variant=ActionVariant.TARGET_REQUIRED, ...)
```

Use:
```python
add_tag = ActionBuilder("add_tag")  # Looks up in ACTION_REGISTRY
```

Benefits:
- Class definition stays clean
- Configuration centralized and auditable
- Adding action = registry entry + declaration
- Type checker validates completeness

### Why Keep 5 Methods Explicit?

These methods have logic beyond standard pattern:

| Method | Custom Logic |
|--------|-------------|
| `add_comment` | Validates non-empty text; has `html_text` parameter |
| `set_parent` | `parent=None` means promote to top-level |
| `reorder_subtask` | Validates task has parent before calling set_parent |
| `add_followers` | Loops over list, calls add_follower for each |
| `remove_followers` | Loops over list, calls remove_follower for each |

Parameterizing these would add complexity without reducing lines.

---

## Alternatives Considered

### BusinessSeeder Alternatives

#### Alternative 1: Client Extension Method

- **Description**: Add `client.seed_business()` to AsanaClient
- **Pros**: Discoverable, no new import
- **Cons**: Bloats AsanaClient, mixes core API with business logic
- **Why not chosen**: AsanaClient should remain API-focused

#### Alternative 2: Builder Pattern

- **Description**: `BusinessSeeder.for_business(data).with_unit(...).with_process(...).build()`
- **Pros**: Flexible, self-documenting
- **Cons**: Overly complex for common case
- **Why not chosen**: Single `seed_async()` simpler for 90% use case

#### Alternative 3: Static Factory Functions

- **Description**: `seed_business(client, business_data, process_data)` module function
- **Pros**: Simple, no class instantiation
- **Cons**: Hard to test (client injection), no state for extensions
- **Why not chosen**: Class allows dependency injection

### Action Method Alternatives

#### Alternative 1: Decorator-Based Generation

```python
@action_method(ActionType.ADD_TAG, variant=ActionVariant.TARGET_REQUIRED)
def add_tag(self, task, tag): pass
```

- **Pros**: Familiar decorator syntax
- **Cons**: Wrapping breaks `help()`, type hints may not propagate
- **Why not chosen**: Introspection broken

#### Alternative 2: Metaclass Generation

```python
class SaveSession(metaclass=ActionMethodsMeta):
    ACTION_METHODS = ["add_tag", "remove_tag", ...]
```

- **Pros**: Methods generated once at class definition, no per-call overhead
- **Cons**: Metaclass complexity, harder to debug (magic)
- **Why not chosen**: Maintenance cost too high for benefit

#### Alternative 3: Code Generation (Pre-Commit)

```bash
python scripts/generate_action_methods.py > src/.../session_actions.py
```

- **Pros**: Zero runtime cost, full type hints
- **Cons**: Sync burden, two sources of truth, merge conflicts
- **Why not chosen**: Synchronization overhead

#### Alternative 4: functools.partialmethod

```python
def _action_impl(self, task, target, action_type): ...
add_tag = partialmethod(_action_impl, action_type=ActionType.ADD_TAG)
```

- **Pros**: Built-in Python tool
- **Cons**: Cannot handle different signatures (NO_TARGET vs POSITIONING), loss of docstring
- **Why not chosen**: Different method signatures require different implementations

---

## Consequences

### Positive

1. **BusinessSeeder**:
   - Simple API for common operation
   - Idempotent for Business/Unit/ProcessHolder
   - Clear result object with creation flags
   - Async-first with sync wrapper
   - Encapsulates dual membership setup

2. **Action Method Factory**:
   - 920 → ~150 lines (83% reduction)
   - Single source of truth (ACTION_REGISTRY)
   - Consistent behavior across all methods
   - Easy to extend (registry entry + declaration)
   - Preserved API (all signatures unchanged)
   - IDE support (`help()`, type hints work)

### Negative

1. **BusinessSeeder**:
   - New class and data models to maintain
   - Find logic requires search API (may be slow)
   - Not idempotent for Process creation (intentional)
   - Limited flexibility for complex hierarchies

2. **Action Method Factory**:
   - Learning curve (descriptor pattern)
   - Debug complexity (stack traces include descriptor machinery)
   - 5 explicit methods (cannot unify all 18)
   - Runtime cost (per-call method generation, likely negligible)

### Neutral

1. **BusinessSeeder**:
   - SaveSession used internally (consistent)
   - ContactData optional (covers both cases)
   - unit_name parameter for customization

2. **Action Method Factory**:
   - New module (`persistence/actions.py` ~150 lines)
   - ActionBuilder needs dedicated tests
   - Pattern must be documented

---

## Compliance

### How This Decision Will Be Enforced

1. **BusinessSeeder**:
   - [ ] seed_async() creates Business if not found
   - [ ] Find by company_id, then name
   - [ ] Unit created under Business
   - [ ] ProcessHolder created under Unit
   - [ ] Process created in ProcessHolder
   - [ ] Process added to pipeline project
   - [ ] SeederResult returned
   - [ ] SaveSession used internally
   - [ ] Async-first with sync wrapper
   - [ ] Idempotent for same Business input

2. **Action Method Factory**:
   - [ ] New action methods use ActionBuilder unless custom logic required
   - [ ] Registry completeness: all ActionType values have entries
   - [ ] Signature tests: `inspect.signature()` before/after verification
   - [ ] Performance gate: <5% regression benchmark

---

## Usage Examples

### BusinessSeeder

```python
# Webhook handler
seeder = BusinessSeeder(client)

result = await seeder.seed_async(
    business=BusinessData(
        name="Acme Corp",
        company_id="123"
    ),
    process=ProcessData(
        name="Sales Opportunity - John Doe",
        process_type=ProcessType.SALES,
        initial_state=ProcessSection.OPPORTUNITY
    ),
    contact=ContactData(
        full_name="John Doe",
        contact_email="john@acme.com"
    )
)

if result.created_business:
    logger.info(f"New business created: {result.business.name}")

# Process is always new (not idempotent)
logger.info(f"Created process: {result.process.name}")
```

### Adding New Action Method

1. Add ActionType enum:
```python
class ActionType(str, Enum):
    ADD_ATTACHMENT = "add_attachment"
```

2. Add registry entry:
```python
ACTION_REGISTRY["add_attachment"] = ActionConfig(
    action_type=ActionType.ADD_ATTACHMENT,
    variant=ActionVariant.TARGET_REQUIRED,
    target_param="attachment",
    log_event="session_add_attachment",
    docstring="Add an attachment to a task...",
)
```

3. Add declaration:
```python
add_attachment = ActionBuilder("add_attachment")
```

Total: ~10 lines vs. ~50 lines for manual method.

---

**Related**: ADR-SUMMARY-SAVESESSION (Unit of Work pattern), ADR-SUMMARY-DATA-MODEL (entity hierarchy), reference/PATTERNS.md (full catalog)

**Supersedes**: Individual ADRs ADR-0099, ADR-0122
