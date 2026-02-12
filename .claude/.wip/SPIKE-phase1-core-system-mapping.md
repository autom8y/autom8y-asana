# SPIKE: Workflow Resolution Platform -- Phase 1: Core System Mapping

**Date**: 2026-02-11
**Scope**: Research-only exploration across microservice and legacy codebases
**Phase**: 1 of 3

---

## Objective 1: ActionExecutor <-> Legacy Section/Tag Routing

### Summary Verdict

The stakeholder's belief that the microservice's ActionExecutor is the equivalent of legacy section-based routing + tag-based automations is **partially correct but significantly incomplete**. The two systems operate at different abstraction levels and the microservice currently covers only a fraction of legacy routing capabilities.

### Microservice Automation Architecture

The microservice has **three distinct automation subsystems**, not one:

#### 1. PipelineConversionRule (Event-Driven, Commit-Triggered)
**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/pipeline.py` (lines 51-1084)

Triggers on `section_changed` events detected after a `SaveSession.commit()`. This is the closest equivalent to legacy section-based routing.

```python
# pipeline.py:112-120 -- Trigger condition
self._trigger = TriggerCondition(
    entity_type="Process",
    event=EventType.SECTION_CHANGED,
    filters={
        "process_type": source_type.value,
        "section": trigger_section.value,
    },
)
```

**Current capability**: Sales -> Onboarding conversion only (hardcoded source/target types).

**Actions performed** (lines 260-480):
1. Lookup target project via PipelineStage config
2. Discover template in target project
3. Duplicate template task with subtasks
4. Add to target project + move to target section
5. Set due date (configurable offset)
6. Wait for subtask propagation
7. Seed fields from Business/Unit/Source Process cascade
8. Place in hierarchy (ProcessHolder, insert_after source)
9. Set assignee from rep cascade (Unit.rep -> Business.rep)
10. Create onboarding comment with source link

#### 2. Polling-Based ActionExecutor (Scheduled, Condition-Driven)
**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/polling/action_executor.py` (lines 78-245)

Supports three action types only:
```python
# action_executor.py:41-45
_SUPPORTED_ACTIONS: dict[str, list[str]] = {
    "add_tag": ["tag_gid"],
    "add_comment": ["text"],
    "change_section": ["section_gid"],
}
```

Triggered by `TriggerEvaluator` (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/polling/trigger_evaluator.py`) which evaluates:
- **Stale triggers**: tasks not modified in N days
- **Deadline triggers**: tasks due within N days
- **Age triggers**: tasks created N+ days ago and still open

Configured via YAML (`config_schema.py`, lines 1-391) with rules per project.

#### 3. WorkflowAction (Batch, Schedule-Driven)
**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/base.py` (lines 72-120)

General-purpose batch workflow framework. Currently one implementation:
- `ConversationAuditWorkflow` (`conversation_audit.py`): weekly CSV refresh for ContactHolders

### Legacy Routing Architecture

The legacy system uses a fundamentally different pattern: **tag-driven dispatch through a ProcessManager**.

#### Tag-Based Routing (Primary Mechanism)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/main/actions.py` (lines 341-416)

```python
# actions.py:341-356 -- Tag name parsing determines routing behavior
def router(self: "Task", tag_name: str, **kwargs) -> Optional["Task"]:
    method, direction = None, None
    if tag_name.startswith("request") or tag_name.endswith("request"):
        method = "request"
        direction = "outbound" if tag_name.startswith("request") else "inbound"
    elif tag_name.startswith("route") or tag_name.endswith("route"):
        method = "route"
        direction = "outbound" if tag_name.startswith("route") else "inbound"
    elif tag_name.startswith("play") or tag_name.endswith("play"):
        method = "play"
        direction = "outbound" if tag_name.startswith("play") else "inbound"
```

Three tag prefixes drive three different managers:
- `route_*` / `request_*` -> `ProcessManager.route()` / `ProcessManager.request()`
- `play_*` -> `DnaManager`
- `*_asset_*` -> `AssetManager`

#### ProcessManager Route Execution
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/managers/process_manager/main.py` (lines 26-496)

The ProcessManager handles full lifecycle:
1. Parse action/direction/category from tag name
2. Resolve target project (action name -> project mapping, lines 145-179)
3. Check for existing process (duplicate prevention via DataFrame lookup, lines 181-230)
4. Find template in target project
5. Duplicate template with trigger task reference
6. Init process: seed fields from trigger, set holder, set section, set due date, close prior processes
7. Add trigger story (comment with context)
8. Save cascading (process -> unit -> business)

#### Section-Based Actions (Per-Process Overrides)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/sales/main.py` (lines 37-57)

Each pipeline stage overrides `converted()` and `did_not_convert()`:

```python
# sales/main.py:37-57
class Sales(Pipeline):
    def converted(self):
        self.internal_notes = f"... {self.link} has converted! ..."
        next_process = self.route("route_onboarding")  # <-- TAG-BASED ROUTING
        super().converted()

    def did_not_convert(self):
        next_process = self.route("route_outreach")
        super().did_not_convert()
```

The section name determines which method is called on the process. This is the legacy equivalent of the microservice's `section_changed` event.

### Mapping: Legacy Triggers vs. Microservice

| Legacy Trigger Pattern | Legacy Action | Microservice Equivalent | Status |
|---|---|---|---|
| Sales.converted() (section -> CONVERTED) | route("route_onboarding") | PipelineConversionRule (Sales->Onboarding) | **PARTIAL** -- microservice has this specific transition |
| Sales.did_not_convert() | route("route_outreach") | None | **GAP** |
| Onboarding.converted() | route("route_implementation") | None (only Sales->Onboard configured) | **GAP** |
| Onboarding.did_not_convert() | route("route_sales") | None | **GAP** |
| Onboarding.init_process() | route("request_source_videographer") | None | **GAP** |
| Implementation.converted() | route("route_month_1") | None | **GAP** |
| Retention/Reactivation/AccountError converted/did_not_convert | Various route_* calls | None | **GAP** |
| `request_asset_edit` tag | AssetManager -> PaidContent template | None | **GAP** |
| `request_*` consultation tags (20+ types) | ProcessManager -> Consultation template | None | **GAP** |
| `play_*` DNA tags | DnaManager -> BackendClientSuccessDna | None | **GAP** |
| Polling: stale/deadline/age triggers | add_tag, add_comment, change_section | Polling ActionExecutor | **EQUIVALENT** |
| Section._run_tasks() (batch handler per section) | Call handle_payload per task in section | WorkflowAction framework | **PARTIAL** (different implementation) |

### Key Differences

1. **Trigger mechanism**: Legacy uses tag parsing (`route_*`, `request_*`). Microservice uses `EventType.SECTION_CHANGED` after commit.

2. **Scope of routing**: Legacy has ~20+ consultation types, 7+ pipeline stages, DNA plays, and asset editing templates. Microservice has exactly one route: Sales -> Onboarding.

3. **Field seeding**: Legacy copies fields via `trigger_task` reference traversal and `_init_fields()` (threaded, per-field). Microservice uses `FieldSeeder` with configurable field lists per PipelineStage.

4. **Dependency handling during routing**: Legacy's `Pipeline.init_process()` (lines 57-103 in `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/main.py`) auto-completes earlier pipeline stages by traversing `offer.dependencies + offer.dependents`. The microservice does NOT do this.

5. **Side effects**: Legacy routing cascades saves (process -> unit -> business) and modifies sections on related entities (offer, unit, business). Microservice's PipelineConversionRule operates in isolation on the new task only.

### Critical Gaps for Workflow Resolution Platform

- **No tag-based dispatch** in microservice -- the entire `route_*` / `request_*` / `play_*` vocabulary is missing
- **No consultation routing** -- 20+ consultation subtypes exist only in legacy
- **No DNA play routing** -- legacy DNA plays are not represented at all
- **No asset edit routing** -- template asset selection logic is legacy-only
- **No cascading save** -- legacy saves propagate to unit/business; microservice doesn't

---

## Objective 2: Cache Granularity Audit

### Summary

Caching operates at **task-level granularity** (individual Asana task GID), NOT at entity-level, holder-level, or Business-level. The cache key is always a task GID, and relationships (subtasks, dependencies, stories) are cached as separate entries keyed by the parent task GID.

### Cache Key Structure

**S3 Backend** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py`, lines 257-281):

```python
# s3.py:257-270
def _make_key(self, key: str, entry_type: EntryType) -> str:
    if entry_type == EntryType.DATAFRAME:
        return f"{self._config.prefix}/dataframe/{key}.json"
    return f"{self._config.prefix}/tasks/{key}/{entry_type.value}.json"

def _make_simple_key(self, key: str) -> str:
    return f"{self._config.prefix}/simple/{key}.json"
```

Key patterns:
- Task data: `asana-cache/tasks/{gid}/task.json[.gz]`
- Subtasks: `asana-cache/tasks/{gid}/subtasks.json[.gz]`
- Dependencies: `asana-cache/tasks/{gid}/dependencies.json[.gz]`
- Dependents: `asana-cache/tasks/{gid}/dependents.json[.gz]`
- Stories: `asana-cache/tasks/{gid}/stories.json[.gz]`
- DataFrame: `asana-cache/dataframe/{key}.json`

### Entry Types

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/entry.py` (lines 20-52)

```python
class EntryType(str, Enum):
    TASK = "task"            # Single task data
    SUBTASKS = "subtasks"    # Child task list
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    DATAFRAME = "dataframe"  # DataFrame metadata
    PROJECT = "project"
    SECTION = "section"
    USER = "user"
    CUSTOM_FIELD = "custom_field"
    DETECTION = "detection"
    PROJECT_SECTIONS = "project_sections"
    GID_ENUMERATION = "gid_enumeration"
    INSIGHTS = "insights"
```

### Cache Entry Hierarchy (Typed Subclasses)

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/entry.py` (lines 346-580):

- `EntityCacheEntry` -> TASK, PROJECT, SECTION, USER, CUSTOM_FIELD
- `RelationshipCacheEntry` -> SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS
- `DataFrameMetaCacheEntry` -> DATAFRAME, PROJECT_SECTIONS, GID_ENUMERATION
- `DetectionCacheEntry` -> DETECTION

### Overflow Thresholds

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/settings.py` (lines 11-49)

```python
class OverflowSettings:
    subtasks: int = 40       # Max before skipping cache
    dependencies: int = 40
    dependents: int = 40
    stories: int = 100
    attachments: int = 40
```

### Entity TTLs and Warm Priority

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` (lines 310-440)

| Entity | TTL (seconds) | Warm Priority | Warmable |
|---|---|---|---|
| Business | 3600 (1hr) | 2 | Yes |
| Unit | 900 (15min) | 1 (highest) | Yes |
| Contact | 900 (15min) | 4 | Yes |
| Offer | 180 (3min) | 3 | Yes |
| AssetEdit | 300 (5min) | 5 | Yes |
| Process | 60 (1min) | N/A | No |
| Location | 3600 (1hr) | N/A | No |
| Hours | 3600 (1hr) | N/A | No |

### Cache Warming Lambda

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` (lines 217-620)

Warm processing order (lines 300-310):
```python
default_priority = [
    "unit",              # Priority 1 -- most accessed
    "business",          # Priority 2
    "offer",             # Priority 3
    "contact",           # Priority 4
    "asset_edit",        # Priority 5
    "asset_edit_holder", # Holder
    "unit_holder",       # Holder
]
```

Features:
- **Checkpoint-based resume**: Saves progress after each entity type (S3-backed checkpoints)
- **Timeout detection**: Exits 2 min before Lambda timeout, self-invokes continuation
- **CloudWatch metrics**: Per-entity-type success/failure/duration tracking
- **Sequential per-entity-type**: One entity type warmed at a time (no interleaving)

### Hierarchy Warming

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/hierarchy_warmer.py` (lines 103-274)

`warm_ancestors_async()` recursively fetches parent chains (up to depth 5) for cascade resolution. This ensures that when a Unit is cached, its parent Business task data is also available for field cascade (e.g., Unit.rep -> Business.rep fallback).

### Answer: Can Workflows Leverage Cached Entities?

**Yes, with caveats:**

1. **Individual task data** is cached and accessible by GID. A workflow resolver could look up any cached task.

2. **Granularity is task-level, not Business-level**. There is no "Business object cache" -- a Business is a single cached task. To get a complete Business picture, you need: Business task + Unit tasks + Offer tasks + their relationships. Each is separately cached.

3. **Relationships are cached separately**. To traverse from a Process to its Business, you would need: Process GID -> ProcessHolder (subtasks cache) -> Unit (parent chain) -> Business. Each hop is a separate cache lookup.

4. **TTLs vary dramatically**. An Offer (180s TTL) may be stale while its Business (3600s TTL) is fresh. Workflow logic that joins across entities needs to account for this.

5. **Dependencies/dependents are cached but overflow-limited**. Tasks with >40 dependencies are NOT cached (overflow threshold). This directly impacts dependency-based traversal.

6. **Process entities are NOT warmed** (warmable=False, TTL=60s). Any workflow touching Processes will likely have cold cache.

---

## Objective 3: Asana Task Dependency Link Usage Inventory

### Summary

Dependencies are **heavily used for traversal** in the legacy codebase and **structurally supported but not actively created** in the microservice. The legacy system uses dependencies as the primary mechanism for navigating between Offers, Units, ProcessHolders, and Processes. The microservice reads them but does not create them.

### Legacy Codebase: Dependencies Are Central to Entity Resolution

#### Dependency/Dependent Objects
**Files**:
- `/Users/tomtenuta/code/autom8/apis/asana_api/objects/dependency/main.py` (lines 1-133)
- `/Users/tomtenuta/code/autom8/apis/asana_api/objects/dependent/main.py` (lines 1-133)

Both provide:
- `get_dependencies_for_task()` / `get_dependents_for_task()` -- Asana API calls with full fields
- `add_dependency_to_task()` / `add_dependent_to_task()` -- Creates dependency links
- `remove_dependency_from_task()` / `remove_dependent_from_task()` -- Removes dependency links
- `.task` property -- Lazily loads the linked Task object

#### Dependencies Used for Entity Resolution (Process.unit, Process.offer)

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py`

**Process.unit property** (lines 582-686): When the trigger_task chain fails to resolve a Unit, it falls back to dependency traversal:
```python
# process/main.py:648-673
if self_relevant_deps:
    self._unit = next(
        (d.task for d in self.dependents if isinstance(d.task, Unit)),
        next(
            (d2.task.unit for d2 in self.dependents if isinstance(d2.task, Offer)),
            None,
        ),
    )
```

**Process.offer property** (lines 709-867): Even more dependency-dependent. Multiple fallback paths traverse dependencies/dependents to find the Offer:
```python
# process/main.py:786-815
if self_relevant_deps:
    self._offer = next(
        (d.task.offer for d in self.dependents if isinstance(d.task, OfferHolder)),
        ...
    )
```

#### Dependencies Used for Auto-Completion

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/main.py` (lines 30-101)

`Pipeline.init_process()` traverses dependencies to auto-complete prior pipeline stages:
```python
# pipeline/main.py:57-82
deps: list["Task"] = [getattr(d, "task") for d in self.offer.dependencies] + [
    getattr(d, "task") for d in self.offer.dependents
]
deps = [d for d in deps if d.gid != self.gid]

for d in deps:
    if not isinstance(d, Pipeline):
        continue
    if d.pipeline_stage > self.pipeline_stage:
        continue
    d.is_completed = True
    auto_completed.append(d)
```

#### Dependencies Used for Default Wiring

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 967-1100)

`Process.default_dependencies` and `Process.default_dependents` compute which entities should be linked:
- Pipelines get DNA plays as dependencies
- Non-Pipeline processes get OfferHolder's open dependents
- All processes get Unit + OfferHolder as default dependents

#### Programmatic Dependency Creation in Legacy

Found in multiple locations:
- `Dependency.add_dependency_to_task()` -- called from `default_dependencies` wiring
- `Dependency.remove_dependency_from_task()` -- called when restructuring (line 1092 in process/main.py)
- `Dependent.add_dependent_to_task()` -- mirror operation

These are actively called during `init_process()` to wire up newly created processes.

### Microservice Codebase: Read-Only Dependency Support

#### TasksClient Dependency Support

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (line 613)

`dependents_async()` method exists for reading dependents with pagination. This is a READ operation only.

#### SaveSession Dependency Actions

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/actions.py` (lines 208-262)

```python
# actions.py:208-234
"add_dependency": ActionConfig(
    action_type=ActionType.ADD_DEPENDENCY,
    ...
)
"remove_dependency": ActionConfig(
    action_type=ActionType.REMOVE_DEPENDENCY,
    ...
)
```

The microservice has the **plumbing** for add/remove dependency via SaveSession, but a search of the codebase reveals these are **not called by any automation rule or workflow**. They exist as primitives but are unused by PipelineConversionRule.

#### Cache Supports Dependencies

Dependencies and dependents are entry types in the cache system with 40-item overflow thresholds. They are READ from cache but never WRITTEN by automation.

### Current State of Dependency Link Coverage

| Aspect | Legacy | Microservice |
|---|---|---|
| **Reading dependencies** | Heavy -- entity resolution, auto-completion, default wiring | Supported via TasksClient + cache |
| **Creating dependencies** | Active -- during init_process() for every new Process | Not done (primitives exist, unused) |
| **Removing dependencies** | Active -- during restructuring | Not done (primitives exist, unused) |
| **Traversal for resolution** | Primary navigation mechanism | Not used -- uses parent chain (hierarchy) instead |
| **Cache support** | N/A (legacy has its own caching) | Yes, but 40-item overflow limit |

### Implications for Workflow Resolution Platform

1. **Dependency links ARE often missing** -- confirmed. The microservice never creates them. Only legacy code creates dependencies, and only during `init_process()` calls (which require section-based trigger flow). Any task created outside the legacy flow will have no dependency links.

2. **Hierarchy traversal (parent chain) is the microservice's primary resolution path**. The microservice uses `set_parent()` + HierarchyIndex instead of dependency links. See `_place_in_hierarchy_async()` in pipeline.py and `warm_ancestors_async()` in hierarchy_warmer.py.

3. **The 2-API-call shortcut via dependencies** (stakeholder's claim) only works if dependencies exist. For legacy-created tasks, they usually do. For microservice-created tasks, they do not. The platform would need to either:
   - Create dependency links during microservice pipeline conversions (align with legacy behavior)
   - Use the hierarchy path (parent chain traversal: 3-5 API calls)
   - Build a hybrid that tries dependencies first, falls back to hierarchy

4. **The dependency overflow threshold (40)** means heavily-linked tasks won't have their dependencies cached. This could silently break traversal for Offers with many linked processes.

---

## Questions and Gaps Affecting Phase 2/3

### Architecture Questions

1. **Which routing paths must the Workflow Resolution Platform support?** The legacy has ~30+ distinct route/request actions. Are all needed, or only pipeline transitions?

2. **Should dependency links be created by the microservice's PipelineConversionRule?** Currently they are not. The legacy creates them. This is a design decision that impacts the "2 API calls vs 3-5" traversal strategy.

3. **What is the source of truth for entity resolution -- parent chain (hierarchy) or dependency links?** The two codebases use fundamentally different strategies. The platform needs to pick one or implement both.

### Data Model Questions

4. **Process entities are not cache-warmed** (warmable=False, TTL=60s). If the Workflow Resolution Platform needs to resolve workflows involving Processes, will cache be cold every time?

5. **Overflow thresholds**: Tasks with >40 dependencies/dependents are not cached. What is the actual distribution of dependency counts across the live workspace?

### Legacy Migration Questions

6. **Section-to-method dispatch** (`converted()`, `did_not_convert()`, etc.) is deeply embedded in the legacy class hierarchy. Each of the 7+ pipeline stages and 20+ consultation types has custom behavior. How much of this needs to be ported vs. reimagined?

7. **Tag vocabulary**: The legacy `route_*` / `request_*` tag vocabulary is the primary automation API for operations teams. Does the workflow platform need to preserve this vocabulary or introduce a new mechanism?
