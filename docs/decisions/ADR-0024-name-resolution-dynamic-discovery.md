# ADR-0024: Name Resolution and Dynamic Discovery

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: SDK Team
- **Consolidated From**: ADR-0034, ADR-0071, ADR-0089, ADR-0106, ADR-0109, ADR-0112
- **Related**: [reference/DETECTION.md](reference/DETECTION.md), ADR-0020, PRD-0003.1, PRD-WORKSPACE-PROJECT-REGISTRY

## Context

The SDK needs to resolve human-readable names to Asana GIDs for multiple resource types without requiring explicit environment-specific configuration. This requirement spans several domains:

1. **Custom fields**: Resolve field names ("MRR", "Weekly Ad Spend") to GIDs for data extraction
2. **Projects**: Discover workspace projects dynamically for Process entity detection
3. **Tags and users**: Resolve names for task organization and assignment
4. **Sections**: Find template sections for task creation
5. **Business entities**: Resolve ambiguous entity references

Each resource type has different scoping (entity-level, project-level, workspace-level) and different resolution patterns. The system must balance convenience, performance, and correctness.

### Design Challenges

1. **Environment-specific GIDs**: Hardcoded GIDs don't work across production/staging/development
2. **API call overhead**: Each resolution potentially requires network access
3. **Ambiguity handling**: Multiple matches must be handled gracefully
4. **Initialization timing**: When to trigger discovery (eager vs lazy)
5. **Cache scope**: Entity-level, session-level, or global caching

## Decision

We will implement **context-specific resolution strategies** with **lazy loading**, **session-scoped caching**, and **first-match-with-transparency** for ambiguous results.

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           Resolution Layer                       │
├──────────────┬──────────────┬───────────────────┤
│   Custom     │   Project    │  Tag/User/Section │
│   Fields     │   Discovery  │    Resolution     │
├──────────────┼──────────────┼───────────────────┤
│ Entity-scope │ Workspace    │ Workspace/Project │
│ Session      │ Process      │ Session cache     │
│ cached       │ lifetime     │                   │
└──────────────┴──────────────┴───────────────────┘
```

### Component 1: Custom Field Resolution

**Scope**: Entity-level (custom fields vary by task type)
**Cache**: Session-scoped index built on first use
**API calls**: Zero (uses task.custom_fields already loaded)

#### Source Convention

```python
# Self-documenting schema definition
ColumnDef(name="mrr", source="cf:MRR")           # Resolve by name
ColumnDef(name="mrr", source="gid:123456")       # Explicit GID (testing/override)
ColumnDef(name="mrr", source=None)               # Use column name as field name
ColumnDef(name="created", source="created_at")   # Attribute path (not custom field)
```

#### CustomFieldAccessor Pattern

```python
class CustomFieldAccessor:
    """Session-scoped custom field name-to-GID resolution.

    Per ADR-0034: Protocol-based resolver with name normalization.
    """

    def __init__(self, task: Task):
        self._task = task
        self._index: dict[str, str] | None = None
        self._lock = threading.RLock()

    def get_gid(self, field_name: str) -> str | None:
        """Resolve custom field name to GID.

        Args:
            field_name: Human-readable field name (e.g., "MRR")

        Returns:
            GID if found, None otherwise
        """
        with self._lock:
            if self._index is None:
                self._build_index()

            # Normalize name for matching
            normalized = self._normalize_name(field_name)
            return self._index.get(normalized)

    def _build_index(self) -> None:
        """Build name-to-GID index from task.custom_fields."""
        self._index = {}
        if not self._task.custom_fields:
            return

        for cf in self._task.custom_fields:
            if cf.name:
                normalized = self._normalize_name(cf.name)
                self._index[normalized] = cf.gid

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize name to canonical form.

        Handles variations:
        - "Weekly Ad Spend" → "weeklyadspend"
        - "MRR" → "mrr"
        - "monthly-recurring-revenue" → "monthlyrecurringrevenue"
        """
        return "".join(c.lower() for c in name if c.isalnum())
```

**Usage**:

```python
# In extraction
accessor = CustomFieldAccessor(task)
mrr_gid = accessor.get_gid("MRR")
if mrr_gid:
    mrr_value = next(
        (cf.number_value for cf in task.custom_fields if cf.gid == mrr_gid),
        None,
    )
```

### Component 2: Workspace Project Discovery

**Scope**: Workspace-level (all projects in workspace)
**Cache**: Process-lifetime singleton registry
**API calls**: One-time discovery on first unknown GID

#### Lazy Discovery Timing

Discovery is triggered **on first async detection for an unregistered project GID**:

```python
async def _detect_tier1_project_membership_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 1 with lazy workspace discovery.

    Per ADR-0109: Discovery triggered on first unknown GID.
    """
    project_gid = _extract_project_gid(task)
    if not project_gid:
        return None

    # Use workspace registry for dynamic discovery
    workspace_registry = get_workspace_registry()
    entity_type = await workspace_registry.lookup_or_discover_async(
        project_gid,
        client,
    )

    if entity_type is None:
        return None

    return DetectionResult(
        entity_type=entity_type,
        confidence=CONFIDENCE_TIER_1,
        tier_used=1,
        needs_healing=False,
        expected_project_gid=project_gid,
    )
```

#### WorkspaceProjectRegistry

```python
class WorkspaceProjectRegistry:
    """Workspace-scoped project discovery registry.

    Per ADR-0109: Lazy discovery with idempotent refresh.
    """

    def __init__(self):
        self._name_to_gid: dict[str, str] = {}
        self._gid_to_type: dict[str, EntityType] = {}
        self._discovered_workspace: str | None = None
        self._lock = threading.RLock()

    async def lookup_or_discover_async(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> EntityType | None:
        """Lookup project GID, discovering workspace if needed."""
        with self._lock:
            # Check static registry first
            entity_type = get_static_registry().lookup(project_gid)
            if entity_type is not None:
                return entity_type

            # Check discovered registry
            if project_gid in self._gid_to_type:
                return self._gid_to_type[project_gid]

            # Trigger discovery if not yet done
            if self._discovered_workspace is None:
                await self._discover_async(client)
                # Retry lookup after discovery
                return self._gid_to_type.get(project_gid)

        return None

    async def _discover_async(self, client: AsanaClient) -> None:
        """Discover workspace projects (idempotent)."""
        workspace_gid = client.default_workspace_gid
        if not workspace_gid:
            logger.warning("No default workspace GID for discovery")
            return

        # Fetch all projects
        projects = await client.projects.list_async(
            workspace=workspace_gid,
            archived=False,
        ).collect()

        # Register all projects
        self._populate_from_projects(projects)
        self._discovered_workspace = workspace_gid

    def _populate_from_projects(self, projects: list[Project]) -> None:
        """Populate registry from project list."""
        for project in projects:
            # Detect ProcessType from project name pattern
            process_type = self._detect_process_type(project.name)
            if process_type:
                self._gid_to_type[project.gid] = process_type
                self._name_to_gid[project.name] = project.gid
```

**Discovery characteristics**:
- **Lazy**: Triggered on first unknown GID, not at client init
- **Idempotent**: Calling `discover_async()` multiple times refreshes registry
- **Non-overwriting**: Static PRIMARY_PROJECT_GID registrations never replaced
- **One-time API call**: Discovery fetches all workspace projects once

### Component 3: Name Resolution for Tags/Users/Sections

**Scope**: Workspace-level (tags, users) or project-level (sections)
**Cache**: Session-scoped lazy-loaded caches
**API calls**: One per resource type on first use

#### NameResolver Pattern

```python
class NameResolver:
    """Session-scoped name resolution for workspace resources.

    Per ADR-0089: Lazy-loading with case-insensitive matching.
    """

    def __init__(self, client: AsanaClient):
        self._client = client
        self._tag_cache: dict[str, str] | None = None
        self._user_cache: dict[str, str] | None = None
        self._lock = threading.RLock()

    async def resolve_tag_async(self, tag_name: str) -> str | None:
        """Resolve tag name to GID."""
        with self._lock:
            if self._tag_cache is None:
                await self._load_tags_async()

            # Case-insensitive lookup
            normalized = tag_name.lower()
            return self._tag_cache.get(normalized)

    async def _load_tags_async(self) -> None:
        """Lazy-load workspace tags."""
        workspace_gid = self._client.default_workspace_gid
        tags = await self._client.tags.list_async(workspace=workspace_gid).collect()

        self._tag_cache = {
            tag.name.lower(): tag.gid
            for tag in tags
            if tag.name
        }
```

#### Section Resolution with Fuzzy Matching

```python
async def find_template_section_async(
    project_gid: str,
    client: AsanaClient,
) -> str | None:
    """Find template section with fuzzy matching.

    Per ADR-0106: Fuzzy section matching for "template" patterns.

    Matches:
    - "template"
    - "templates"
    - "template tasks"
    - "task templates"
    """
    sections = await client.sections.list_async(project_gid).collect()

    # Fuzzy patterns (case-insensitive)
    template_patterns = ["template", "templates", "template tasks", "task templates"]

    for section in sections:
        if not section.name:
            continue

        name_lower = section.name.lower()
        if any(pattern in name_lower for pattern in template_patterns):
            return section.gid

    return None
```

### Component 4: Ambiguity Handling

**Pattern**: First-match-with-transparency for all resolution types

#### ResolutionResult Structure

```python
@dataclass(frozen=True, slots=True)
class ResolutionResult(Generic[T]):
    """Outcome of entity resolution.

    Per ADR-0071: First match with ambiguous flag and candidates.
    """
    entity: T | None = None  # First match (for convenience)
    strategy_used: str | None = None
    ambiguous: bool = False  # True if multiple matches
    candidates: list[T] = field(default_factory=list)  # All matches
    error: str | None = None

    @property
    def success(self) -> bool:
        """True only if exactly one match (not ambiguous)."""
        return self.entity is not None and not self.ambiguous
```

#### Ambiguity Handling Pattern

```python
# Example: Resolve Unit by vertical (may be ambiguous)
result = await asset_edit.resolve_unit_async(client)

if result.success:
    # Unambiguous - use entity directly
    unit = result.entity
    logger.info("Resolved to single Unit", unit_gid=unit.gid)

elif result.ambiguous:
    # Multiple matches - caller decides
    logger.warning(
        "Ambiguous Unit resolution",
        vertical=asset_edit.vertical,
        candidates=[u.gid for u in result.candidates],
    )
    unit = result.candidates[0]  # Or prompt user, or filter further

else:
    # No match found
    logger.error("No matching Unit found", vertical=asset_edit.vertical)
    handle_no_match()
```

**Why first match?**:
1. **Pragmatic**: Many callers need "a" match for context, even if not certain
2. **Progressive disclosure**: Simple callers get simple behavior; sophisticated callers check `ambiguous`
3. **No information loss**: All candidates available for inspection
4. **Matches mental model**: "Find X" suggests returning something if found

## Rationale

### Why Context-Specific Strategies?

Different resource types have fundamentally different resolution patterns:

| Resource | Scope | Cache Lifetime | API Pattern |
|----------|-------|----------------|-------------|
| Custom fields | Entity | Session | Zero (uses task.custom_fields) |
| Projects | Workspace | Process | One-time discovery |
| Tags/Users | Workspace | Session | Lazy on first use |
| Sections | Project | Per-call | No caching (small scope) |

A unified resolver would force all resources into the same pattern, losing these optimizations.

### Why Lazy Loading?

**Advantages**:
- Zero initialization overhead if resolution not needed
- Minimal API calls (only for resources actually used)
- Better DX (no explicit init required)

**Disadvantages**:
- First-use latency (1-3 seconds for workspace discovery)
- Requires async for full functionality

**Decision**: Lazy wins because discovery is stable (projects rarely change) and DX is prioritized.

### Why Session-Scoped Caching?

**Custom fields**:
- Scope: Entity-level (different tasks have different fields)
- Lifetime: Session (fields stable during extraction)
- Reason: Index built once per extraction, reused for all rows

**Tags/Users**:
- Scope: Workspace-level (same across tasks)
- Lifetime: Session (names stable during operation)
- Reason: Avoid repeated API calls for same resource

**Projects**:
- Scope: Workspace-level
- Lifetime: Process (projects very stable)
- Reason: Discovery expensive; singleton registry sufficient

### Why Name Normalization?

Asana custom field names can vary:
- "Weekly Ad Spend" (Title Case with spaces)
- "MRR" (ALL CAPS)
- "monthly-recurring-revenue" (hyphenated)

Normalization to lowercase alphanumeric enables matching regardless of styling:
- `normalize("Weekly Ad Spend")` → `"weeklyadspend"`
- `normalize("weekly_ad_spend")` → `"weeklyadspend"`
- `normalize("WEEKLY-AD-SPEND")` → `"weeklyadspend"`

### Why First-Match for Ambiguity?

Returning first match with `ambiguous=True`:
- **Convenience**: Simple callers get working code (`result.entity`)
- **Safety**: `result.success` returns False for ambiguous results
- **Transparency**: `result.candidates` provides all matches
- **Composability**: Works well with batch operations

## Alternatives Considered

### Alternative A: Static GID Configuration

Hardcoded GID constants in code.

**Why not chosen**:
- Environment-specific (production vs staging vs dev)
- Doesn't scale (50+ task types)
- No self-documentation
- Blocks implementation progress

### Alternative B: Configuration File (YAML/JSON)

Store mappings in configuration file.

**Why not chosen**:
- Over-engineering for current needs
- Configuration drift risk
- No IDE autocomplete
- Adds infrastructure complexity

### Alternative C: Global Eager Loading

Load all registries at client initialization.

**Why not chosen**:
- API calls even if resolution not needed
- Slower client startup
- DX regression (explicit init)

### Alternative D: Return None on Ambiguity

`entity=None` when `ambiguous=True`.

**Why not chosen**:
- Adds friction for common "just give me something" use case
- Information available via `candidates[0]` anyway
- Forces extra code for simple scenarios

### Alternative E: Raise Exception on Ambiguity

Throw `AmbiguousResolutionError` when multiple matches.

**Why not chosen**:
- Ambiguity is a normal outcome, not exceptional
- Breaks simple iteration over collections
- Different use cases handle ambiguity differently

## Consequences

### Positive

**Custom field resolution**:
- Environment-agnostic (discovers GIDs at runtime)
- Zero extra API calls (uses task.custom_fields)
- Self-documenting schemas (`source="cf:MRR"`)
- Testable without Asana (protocol-based)

**Project discovery**:
- Good DX (no explicit initialization required)
- Efficient (discovery only when needed)
- Idempotent (safe to call multiple times)
- Explicit option available (`discover_async()`)

**Name resolution**:
- Case-insensitive matching
- Lazy-loaded (minimal API calls)
- Session-scoped caching (no repeated calls)
- Fuzzy matching for templates

**Ambiguity handling**:
- Simple default path (`result.entity` usable when not None)
- Explicit detection (`result.ambiguous`, `result.success`)
- Full transparency (`candidates` list)
- Composable (works with batch operations)

### Negative

**Custom field resolution**:
- First task must have all custom fields defined
- Name changes require schema updates

**Project discovery**:
- First detection latency (1-3 seconds on discovery)
- Async only for full registry
- Client required for API access

**Name resolution**:
- Session cache memory overhead
- Case-insensitive only (no substring matching)

**Ambiguity handling**:
- Possible misuse (callers ignoring `ambiguous` flag)
- Non-deterministic order (first match depends on iteration)

### Neutral

- Deprecates static GID constants (migration path needed)
- Multiple resolution strategies (appropriate for different resources)
- Thread-safety via RLock (standard synchronization)

## Compliance

How do we ensure this decision is followed?

**Custom field resolution**:
1. **Schema sources MUST use `cf:` prefix** - verified by code review
2. **No new static GID constants** - linting rule
3. **Tests use protocol-based mocks** - test pattern enforcement

**Project discovery**:
1. **Discovery triggered on first unknown GID** - verified by integration tests
2. **Sync detection MUST NOT trigger discovery** - verified by mock assertions
3. **Discovery MUST be idempotent** - verified by unit tests
4. **Static registrations MUST NOT be overwritten** - verified by assertion

**Name resolution**:
1. **Case-insensitive matching required** - verified by test cases
2. **Lazy loading pattern enforced** - code review
3. **Session-scoped caching documented** - docstrings required

**Ambiguity handling**:
1. **`ResolutionResult.success` MUST return False when ambiguous** - unit test
2. **`entity` MUST be first candidate when ambiguous** - unit test
3. **`candidates` MUST contain all matches** - integration test
4. **Documentation MUST explain ambiguity semantics** - docstring requirement

## Implementation Notes

**Adding new custom field**:

```python
# No code changes needed - just update schema
ColumnDef(name="new_metric", source="cf:New Metric")
```

**Triggering explicit discovery**:

```python
# Optional eager initialization
await get_workspace_registry().discover_async(client)

# Or rely on lazy (recommended)
result = await detect_entity_type_async(task, client)
```

**Handling ambiguous resolution**:

```python
result = await resolve_unit_async(client, vertical="chiropractic")

if result.success:
    unit = result.entity
elif result.ambiguous:
    # Let user choose or apply business logic
    unit = await prompt_user_choice(result.candidates)
else:
    raise ValueError(f"No Unit found for vertical {vertical}")
```

**Testing with mocks**:

```python
# Custom field resolution
class MockFieldAccessor:
    def get_gid(self, field_name: str) -> str | None:
        return {"MRR": "mock-gid-123"}.get(field_name)

# Project discovery
registry = WorkspaceProjectRegistry()
registry._gid_to_type = {"123": EntityType.PROCESS}
```
