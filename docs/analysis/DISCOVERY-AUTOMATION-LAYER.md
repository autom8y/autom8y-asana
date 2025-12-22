# Discovery: Automation Layer for autom8_asana SDK

**Date**: 2025-12-18
**Purpose**: Answer blocking questions before PRD creation for SDK-native automation infrastructure

---

## Executive Summary

The autom8_asana SDK has well-established extension points for automation infrastructure. The existing SaveSession architecture provides multiple hook injection points (pre-save, post-save, error, and a new post-commit phase). The SDK already has cascade field propagation, section-based state management, and field seeding patterns that can be leveraged for pipeline conversion flows.

**Key Findings**:
1. SaveSession supports post-commit hooks today via `on_post_save` - extending to batch-level is straightforward
2. SaveResult can carry automation outcomes via existing `cascade_results` and `healing_report` patterns
3. ProcessSection already implements fuzzy section name matching with alias support
4. CascadingFieldDef/InheritedFieldDef provide field propagation infrastructure
5. AsanaConfig accepts configuration via constructor injection - automation config follows same pattern

---

## 1. SaveSession Extension Points

### 1.1 Current Commit Flow

The commit flow in `session.py` has a clear four-phase structure with existing hook points:

```
commit_async()
    |
    +-- Phase 1: CRUD Operations (via SavePipeline.execute_with_actions)
    |       |-- emit_pre_save() for each entity
    |       |-- batch execution
    |       |-- emit_post_save() for each entity on success
    |       |-- emit_error() for each entity on failure
    |
    +-- Phase 2: Action Operations (tags, projects, dependencies)
    |       |-- ActionExecutor.execute_async()
    |
    +-- Phase 3: Cascade Operations
    |       |-- CascadeExecutor.execute()
    |
    +-- Phase 4: Healing Operations (TDD-DETECTION/ADR-0095)
    |       |-- _execute_healing_async()
    |
    +-- Reset entity states, return SaveResult
```

### 1.2 Recommended Hook Injection Points

**Option A: Post-Commit Hook (Session-Level)**

Insert after all phases complete but before returning SaveResult:

```python
# In session.py commit_async(), around line 700
async def commit_async(self) -> SaveResult:
    # ... existing Phase 1-4 ...

    # NEW: Phase 5 - Automation Hooks
    await self._emit_post_commit(crud_result)

    return crud_result
```

**Option B: Extend EventSystem with Commit-Level Events**

Add to `events.py`:

```python
PostCommitHook = Callable[[SaveResult], None] | Callable[[SaveResult], Coroutine[Any, Any, None]]

class EventSystem:
    def __init__(self) -> None:
        # ... existing ...
        self._post_commit_hooks: list[PostCommitHook] = []

    def register_post_commit(self, func: PostCommitHook) -> Callable[..., Any]:
        """Register hook called after entire commit completes."""
        self._post_commit_hooks.append(func)
        return func

    async def emit_post_commit(self, result: SaveResult) -> None:
        """Emit post-commit event with full SaveResult."""
        for hook in self._post_commit_hooks:
            try:
                result = hook(result)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass  # Post-commit hooks should not fail
```

### 1.3 Code Location

**Primary File**: `/src/autom8_asana/persistence/session.py`
- Lines 575-702: `commit_async()` implementation
- Lines 727-814: Existing hook registration (`on_pre_save`, `on_post_save`, `on_error`)

**Event System**: `/src/autom8_asana/persistence/events.py`
- Lines 35-218: EventSystem class

### 1.4 Recommendation

**Use Option B** - Add `on_post_commit` to EventSystem for consistency with existing patterns. This allows automation handlers to receive the full SaveResult including succeeded entities, action results, cascade results, and healing report.

---

## 2. SaveResult Structure

### 2.1 Current Structure

From `/src/autom8_asana/persistence/models.py`:

```python
@dataclass
class SaveResult:
    """Result of a commit operation."""

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)
    cascade_results: list[CascadeResult] = field(default_factory=list)
    healing_report: HealingReport | None = None

    # Computed properties
    @property
    def success(self) -> bool: ...
    @property
    def partial(self) -> bool: ...
    @property
    def total_count(self) -> int: ...
```

### 2.2 Can SaveResult Carry Automation Outcomes?

**Yes** - The pattern for extending SaveResult is already established:
- `cascade_results` was added for TDD-TRIAGE-FIXES
- `healing_report` was added for TDD-DETECTION/ADR-0095

### 2.3 Recommended Extension for Automation

```python
@dataclass
class AutomationResult:
    """Result of automation operations triggered by commit."""

    rule_id: str
    triggered: bool = False
    actions_executed: list[str] = field(default_factory=list)
    entities_affected: list[str] = field(default_factory=list)  # GIDs
    error: str | None = None

@dataclass
class SaveResult:
    # ... existing fields ...
    automation_results: list[AutomationResult] = field(default_factory=list)

    @property
    def automation_succeeded(self) -> int:
        """Count of successful automation executions."""
        return sum(1 for r in self.automation_results if not r.error)
```

---

## 3. Template Section Naming Patterns

### 3.1 Existing Section Matching

The codebase already has robust section matching in `ProcessSection.from_name()`:

```python
# From /src/autom8_asana/models/business/process.py, lines 92-137

class ProcessSection(str, Enum):
    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"

    @classmethod
    def from_name(cls, name: str | None) -> ProcessSection | None:
        """Match section name case-insensitively."""
        if name is None:
            return None

        # Normalize: lowercase, replace spaces/hyphens with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")

        # Direct enum lookup
        for member in cls:
            if member.value == normalized:
                return member

        # Aliases for common variations
        ALIASES = {
            "did_not_convert": cls.DID_NOT_CONVERT,
            "didnt_convert": cls.DID_NOT_CONVERT,
            "didnotconvert": cls.DID_NOT_CONVERT,
            "not_converted": cls.DID_NOT_CONVERT,
            "lost": cls.DID_NOT_CONVERT,
            "dnc": cls.DID_NOT_CONVERT,
        }

        if normalized in ALIASES:
            return ALIASES[normalized]

        return cls.OTHER
```

### 3.2 Additional Section Matching in NameResolver

From `/src/autom8_asana/clients/name_resolver.py`:

```python
async def resolve_section_async(self, name_or_gid: str, project_gid: str) -> str:
    """Resolve section name to GID (project-scoped)."""
    if name_or_gid.isdigit():
        return name_or_gid

    # Case-insensitive exact match
    for section in all_sections:
        if section.name.lower().strip() == name_or_gid.lower().strip():
            return section.gid

    # Fuzzy matching suggestions (difflib.get_close_matches)
    raise NameResolutionError(f"Section '{name_or_gid}' not found")
```

### 3.3 Template Reference in AssetEdit

From `/src/autom8_asana/models/business/asset_edit.py`:

```python
class AssetEdit(BusinessEntity):
    class Fields:
        TEMPLATE_ID = "Template ID"

    @property
    def template_id(self) -> str | None:
        """Template identifier (text custom field)."""
        return self._get_text_field(self.Fields.TEMPLATE_ID)
```

### 3.4 Recommendation for Automation Layer

Leverage existing `ProcessSection.from_name()` pattern and extend for:
1. **Pipeline template matching**: Map process types to target project templates
2. **Section state transitions**: Use ProcessSection enum for state machine validation

---

## 4. Field Seeding Inventory

### 4.1 Existing Seeder Infrastructure

From `/src/autom8_asana/models/business/seeder.py`:

```python
class BusinessSeeder:
    """Factory for creating complete business entity hierarchies."""

    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Seed complete business hierarchy with process."""
        # Creates Business -> Unit -> Process chain
        # Sets parent references via NameGid
        # Commits via SaveSession
```

### 4.2 Cascading Fields (Business -> Descendants)

From `/src/autom8_asana/models/business/business.py`:

| Field Name | Target Types | Allow Override |
|------------|--------------|----------------|
| Office Phone | Unit, Offer, Process, Contact | No (always overwrite) |
| Company ID | All descendants (None) | No |
| Business Name | Unit, Offer | No (source: Task.name) |
| Primary Contact Phone | Unit, Offer, Process | No |

### 4.3 Cascading Fields (Unit -> Descendants)

From `/src/autom8_asana/models/business/unit.py`:

| Field Name | Target Types | Allow Override |
|------------|--------------|----------------|
| Platforms | Offer | **Yes** (Offers can keep value) |
| Vertical | Offer, Process | No |
| Booking Type | Offer | No |

### 4.4 Inherited Fields (Child <- Parent Chain)

| Field Name | Inherit From | Allow Override |
|------------|--------------|----------------|
| Default Vertical (Unit) | Business | Yes |
| Vertical (Offer) | Unit, Business | Yes |
| Platforms (Offer) | Unit | Yes |

### 4.5 Process Entity Fields

From `/src/autom8_asana/models/business/process.py`:

```python
class Process(BusinessEntity):
    # Text fields
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    process_notes = TextField(field_name="Process Notes")
    process_due_date = TextField(field_name="Due Date")

    # Enum fields
    status = EnumField()
    priority = EnumField()
    vertical = EnumField()

    # People field
    assigned_to = PeopleField()
```

### 4.6 Recommendation for Pipeline Conversion

**Fields to seed on conversion (Sales -> Onboarding)**:

| Field | Source | Target | Notes |
|-------|--------|--------|-------|
| Business Name | Business.name | Process.name (prefix) | Carry through |
| Company ID | Business.company_id | Process (custom) | Cascade |
| Vertical | Unit.vertical | Process.vertical | Cascade |
| Assigned To | Config / Rule | Process.assigned_to | Rule-based |
| Priority | Config / Rule | Process.priority | Rule-based |
| Office Phone | Business.office_phone | Process (custom) | Cascade |
| Contact Phone | Contact.contact_phone | Process (custom) | Carry-through |

---

## 5. AsanaClient Configuration

### 5.1 Current Configuration Pattern

From `/src/autom8_asana/client.py`:

```python
class AsanaClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        workspace_gid: str | None = None,
        auth_provider: AuthProvider | None = None,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
        config: AsanaConfig | None = None,
        observability_hook: ObservabilityHook | None = None,
    ) -> None:
        self._config = config or AsanaConfig()
        # ... provider resolution ...
```

### 5.2 AsanaConfig Structure

From `/src/autom8_asana/config.py`:

```python
@dataclass
class AsanaConfig:
    base_url: str = "https://app.asana.com/api/1.0"
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    token_key: str = "ASANA_PAT"
```

### 5.3 Recommended Automation Configuration

```python
@dataclass
class AutomationConfig:
    """Configuration for Automation Layer."""
    enabled: bool = True
    rules_source: str = "inline"  # "inline" | "file" | "api"
    max_cascade_depth: int = 5
    pipeline_templates: dict[str, str] = field(default_factory=dict)
    # e.g., {"sales": "1234567890", "onboarding": "0987654321"}

@dataclass
class AsanaConfig:
    # ... existing fields ...
    automation: AutomationConfig = field(default_factory=AutomationConfig)
```

### 5.4 SaveSession Configuration Extension

```python
class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
        auto_heal: bool = False,
        automation_enabled: bool | None = None,  # NEW: Override client config
    ) -> None:
        # ...
        self._automation_enabled = (
            automation_enabled
            if automation_enabled is not None
            else client._config.automation.enabled
        )
```

---

## 6. Risks and Constraints

### 6.1 Identified Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Circular trigger loops | High | Max recursion depth, visited set tracking |
| Rate limiting during cascades | Medium | Batch operations, rate limit config |
| Partial failures in multi-step automation | Medium | Transaction-like semantics, rollback hooks |
| Section name mismatch | Low | Use ProcessSection.from_name() with OTHER fallback |
| Custom field GID changes | Low | Use field names, not GIDs; runtime resolution |

### 6.2 Constraints

1. **Asana API Limitations**:
   - Batch API limited to 10 requests per call
   - 1500 requests/minute rate limit
   - Section operations are not batchable

2. **SDK Architecture**:
   - SaveSession is per-transaction (no cross-session automation)
   - CascadeExecutor updates in-memory only (requires separate commit)
   - No built-in rollback mechanism

3. **Business Logic**:
   - ProcessType enum must match project name patterns
   - Pipeline transitions require explicit section movement (not automatic)

---

## 7. Recommended Architecture

### 7.1 Component Overview

```
AsanaClient
    |
    +-- AutomationEngine (NEW)
    |       |-- RuleRegistry
    |       |-- TriggerMatcher
    |       |-- ActionExecutor
    |
    +-- SaveSession (extended)
            |-- on_post_commit hook -> AutomationEngine.evaluate()
```

### 7.2 Hook Integration

```python
# In SaveSession
async def commit_async(self) -> SaveResult:
    # ... existing phases 1-4 ...

    # Phase 5: Automation (NEW)
    if self._automation_enabled:
        automation_results = await self._client.automation.evaluate(crud_result)
        crud_result.automation_results = automation_results

    return crud_result
```

### 7.3 Rule Definition Pattern

```python
@dataclass
class AutomationRule:
    id: str
    trigger: TriggerCondition
    actions: list[Action]
    enabled: bool = True

@dataclass
class TriggerCondition:
    entity_type: str  # "Process", "Offer", etc.
    event: str  # "created", "updated", "section_changed"
    filters: dict[str, Any]  # {"process_type": "sales", "section": "converted"}

@dataclass
class Action:
    type: str  # "create_process", "add_to_project", "set_field"
    params: dict[str, Any]
```

---

## 8. Next Steps

1. **PRD Creation**: Document functional requirements for Automation Layer
2. **TDD Creation**: Design automation engine architecture
3. **ADR Decision**: Post-commit hook pattern (Option B recommended)
4. **POC**: Implement single Sales -> Onboarding conversion rule

---

## Appendix A: Relevant File Locations

| Component | File Path |
|-----------|-----------|
| SaveSession | `/src/autom8_asana/persistence/session.py` |
| SaveResult | `/src/autom8_asana/persistence/models.py` |
| EventSystem | `/src/autom8_asana/persistence/events.py` |
| SavePipeline | `/src/autom8_asana/persistence/pipeline.py` |
| CascadeExecutor | `/src/autom8_asana/persistence/cascade.py` |
| AsanaConfig | `/src/autom8_asana/config.py` |
| AsanaClient | `/src/autom8_asana/client.py` |
| Process | `/src/autom8_asana/models/business/process.py` |
| ProcessSection | `/src/autom8_asana/models/business/process.py` |
| BusinessSeeder | `/src/autom8_asana/models/business/seeder.py` |
| CascadingFieldDef | `/src/autom8_asana/models/business/fields.py` |
| Business | `/src/autom8_asana/models/business/business.py` |
| Unit | `/src/autom8_asana/models/business/unit.py` |
| Offer | `/src/autom8_asana/models/business/offer.py` |
| NameResolver | `/src/autom8_asana/clients/name_resolver.py` |
| SectionsClient | `/src/autom8_asana/clients/sections.py` |

## Appendix B: Code Snippets for Key Extension Points

### B.1 Post-Commit Hook Registration (EventSystem Extension)

```python
# events.py addition
PostCommitHook = (
    Callable[[SaveResult], None]
    | Callable[[SaveResult], Coroutine[Any, Any, None]]
)

class EventSystem:
    def __init__(self) -> None:
        self._pre_save_hooks: list[PreSaveHook] = []
        self._post_save_hooks: list[PostSaveHook] = []
        self._error_hooks: list[ErrorHook] = []
        self._post_commit_hooks: list[PostCommitHook] = []  # NEW

    def register_post_commit(self, func: PostCommitHook) -> Callable[..., Any]:
        """Register post-commit hook called after entire commit completes."""
        self._post_commit_hooks.append(func)
        return func

    async def emit_post_commit(self, result: SaveResult) -> None:
        """Emit post-commit event with full SaveResult."""
        for hook in self._post_commit_hooks:
            try:
                hook_result = hook(result)
                if asyncio.iscoroutine(hook_result):
                    await hook_result
            except Exception:
                pass  # Post-commit hooks should not fail the commit
```

### B.2 SaveSession Integration

```python
# session.py addition
def on_post_commit(
    self,
    func: PostCommitHook,
) -> Callable[..., Any]:
    """Register post-commit hook (decorator).

    Post-commit hooks are called after the entire commit operation
    completes, including CRUD, actions, cascades, and healing.
    They receive the full SaveResult for inspection.

    Args:
        func: Hook function receiving (SaveResult). Can be sync or async.

    Returns:
        The decorated function.

    Example:
        @session.on_post_commit
        async def trigger_automation(result: SaveResult) -> None:
            for entity in result.succeeded:
                await evaluate_automation_rules(entity)
    """
    return self._events.register_post_commit(func)

async def commit_async(self) -> SaveResult:
    # ... existing phases 1-4 ...

    # Emit post-commit hooks
    await self._events.emit_post_commit(crud_result)

    return crud_result
```

### B.3 AutomationResult Model

```python
# models.py addition
@dataclass
class AutomationResult:
    """Result of an automation rule execution."""

    rule_id: str
    rule_name: str
    triggered_by_gid: str  # Entity that triggered the rule
    triggered_by_type: str  # Entity type name
    actions_executed: list[str] = field(default_factory=list)
    entities_created: list[str] = field(default_factory=list)  # GIDs
    entities_updated: list[str] = field(default_factory=list)  # GIDs
    success: bool = True
    error: str | None = None
    execution_time_ms: float = 0.0

    def __repr__(self) -> str:
        status = "success" if self.success else f"failed: {self.error}"
        return f"AutomationResult({self.rule_name}, {status})"
```
