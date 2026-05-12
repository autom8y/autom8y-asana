---
domain: feat/asana-models
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Pydantic v2 Asana Resource Models

## Purpose and Design Rationale

The `models/` package provides typed Pydantic v2 representations of every Asana API resource consumed by the SDK and FastAPI service. The central design problem it solves: the Asana REST API returns JSON that can grow (new fields added over time) without coordinated SDK releases. The solution is **defensive parsing by default**: every model carries `extra="ignore"` (per ADR-0005), so Asana can add new fields without breaking deserialization.

Three downstream consumers drive the model design:

1. **`clients/`** — parse raw API JSON into typed models via `model_validate()`
2. **`services/`** — receive typed models and operate on them without raw-dict access
3. **`models/business/`** — subclass `Task` for rich domain entities (separate `business-domain-model` feature; intentionally out of scope here)

**Design decisions with rationale:**

- **ADR-0005 (`extra="ignore`)**: Forward compatibility against Asana API evolution. Non-negotiable — removing it would cause `ValidationError` on every new Asana field addition.
- **ADR-0006 (`NameGid` standalone)**: Asana frequently returns compact resource references (`{gid, name, resource_type}`). A frozen, hashable `NameGid` (not an `AsanaResource` subclass) keeps reference objects minimal and usable as set/dict keys. The distinction (`NameGid` is NOT an `AsanaResource`) is load-bearing.
- **ADR-0056 (custom field write format)**: Asana's API accepts custom field updates as `{"field_gid": value}` dict, not the `[{gid, value_key}]` list format returned in reads. `CustomFieldAccessor.to_api_dict()` owns this conversion.
- **ADR-0067 (snapshot detection)**: `Task` captures `_original_custom_fields` at `model_validate()` time to detect direct mutations (bypassing the accessor). Prevents silent loss of changes.
- **ADR-0074 (reset tracking post-commit)**: `SaveSession` calls `task.reset_custom_field_tracking()` after a successful commit to clear accessor modifications (System 2) and update the snapshot to current state (System 3). Ensures the task's tracking state reflects committed reality.
- **GID pattern guard** (`base.py:21-25`): Production enforces numeric-only GIDs (`r"^\d{1,64}$"`). Test/local environments relax this to `None` for human-readable test GIDs. This guard reads `AUTOM8Y_ENV` directly from `os.environ` at module load time to avoid triggering full Pydantic settings validation during early import.

**Rejected alternatives**: Typed custom field subclasses were rejected (too many field variants; Asana's type system is runtime-only). Full `TypedDict` for custom field dicts was rejected (schema varies per workspace project configuration).

## Conceptual Model

### Inheritance Hierarchy

```
BaseModel (pydantic)
└── AsanaResource          (base.py) — all Asana resources, extra="ignore"
    ├── Task               (task.py) — hub type; active-record with save/refresh
    ├── Project            (project.py)
    ├── Section            (section.py)
    ├── User               (user.py)
    ├── Workspace          (workspace.py)
    ├── CustomField        (custom_field.py) — field definition, not value
    ├── CustomFieldEnumOption (custom_field.py)
    ├── CustomFieldSetting (custom_field.py)
    ├── Attachment         (attachment.py)
    ├── Goal               (goal.py)
    ├── GoalMembership     (goal.py)
    ├── GoalMetric         (goal.py)
    ├── Portfolio          (portfolio.py)
    ├── Story              (story.py)
    ├── Tag                (tag.py)
    ├── Team               (team.py)
    ├── TeamMembership     (team.py)
    ├── Webhook            (webhook.py)
    └── WebhookFilter      (webhook.py)

BaseModel (pydantic)
└── NameGid                (common.py) — frozen, hashable on gid; NOT AsanaResource

(not a BaseModel subclass)
└── CustomFieldAccessor    (custom_field_accessor.py) — fluent accessor wrapping list[dict]
└── PageIterator[T]        (common.py) — async paginator
```

### AsanaResource Config (inherited by all models)

```python
model_config = ConfigDict(
    extra="ignore",          # ADR-0005: forward compat
    populate_by_name=True,   # accept both Python names and API aliases
    str_strip_whitespace=True,
)
```

### Two Field Tiers

**Tier A (typed with NameGid)**: Relationship fields where the Asana API reliably returns compact reference objects. Examples: `Task.assignee`, `Task.projects`, `Task.parent`, `Task.workspace`, `Project.owner`, `Project.team`, `Section.project`, `Task.completed_by`, `Task.created_by`.

**Tier B (raw dicts)**: Complex or irregular structures with variable schema. Examples: `Task.custom_fields` (`list[dict]`), `Task.memberships` (`list[dict]`), `Task.likes` (`list[dict]`), `Project.custom_field_settings` (`list[dict]`), `Task.external` (`dict`).

### Custom Field Tracking (Three-System model on Task)

| System | Attribute | Mechanism | Purpose |
|--------|-----------|-----------|---------|
| System 1 | `task.custom_fields` | Pydantic field (`list[dict]`) | Raw API data |
| System 2 | `task._custom_fields_accessor` | `PrivateAttr` (`CustomFieldAccessor`) | Fluent writes, tracks `_modifications` dict |
| System 3 | `task._original_custom_fields` | `PrivateAttr` (deep-copied at `model_validate`) | Detects direct mutations to System 1 |

**Precedence rule** (in `Task.model_dump()`): accessor changes (System 2) beat direct-list changes (System 3). Both detected → accessor wins; warning logged.

### CustomFieldAccessor

Wraps `list[dict[str, Any]]`. Internal indexes:
- `_name_to_gid: dict[str, str]` — case-insensitive name lookup
- `_gid_to_field: dict[str, dict]` — O(1) field dict lookup
- `_modifications: dict[str, Any]` — pending `{gid: value}`

**Resolution chain** in `_resolve_gid()`: numeric → local name index → local GID index → optional `_resolver` (injected `DefaultCustomFieldResolver`) → strict error / non-strict passthrough.

**Strict mode** (`strict=True` default, `strict=False` for business models): strict raises `NameNotFoundError` with difflib suggestions on unknown names. Business models are instantiated with `strict=False` because they may set fields absent from the current workspace; Asana validates on write.

**API serialization**: `to_api_dict()` produces `{gid: formatted_value}` per ADR-0056. Date values are wrapped as `{"date": "YYYY-MM-DD"}` per Asana API contract.

### Forward Reference Resolution

All model files use `from __future__ import annotations` (deferred evaluation). `NameGid` is imported under `TYPE_CHECKING` only in each resource file (e.g., `task.py:22`). `__init__.py` calls `model_rebuild(_types_namespace={"NameGid": NameGid})` on every model after all imports are resolved. `Task` is rebuilt first because `models/business/` subclasses inherit from it.

### `exclude=True` Convention

`Project.tasks` and `Section.tasks` are `list[Any] | None` fields populated externally (by DataFrame builders) but excluded from serialization (`exclude=True`). This prevents accidental round-trip back to Asana API.

### `__init__.py` Tier Classification

The `__init__.py` comment separates models into tiers for rebuild ordering:
- **Tier 0**: `Task` (rebuilt first — business subclasses depend on it)
- **Tier 1**: `Attachment`, `CustomField`, `CustomFieldSetting`, `Project`, `Section`, `User`, `Workspace`
- **Tier 2**: `Goal`, `GoalMembership`, `GoalMetric`, `Portfolio`, `Story`, `Tag`, `Team`, `TeamMembership`, `Webhook`, `WebhookFilter`

## Implementation Map

### Package Contents

| File | Purpose | Key Types / Notes |
|------|---------|-------------------|
| `base.py` | `AsanaResource` base | `_GID_PATTERN` env-gated; `ConfigDict(extra="ignore", populate_by_name=True, str_strip_whitespace=True)` |
| `common.py` | Shared primitives | `NameGid` (frozen, hashable on `.gid`); `PageIterator[T]` (async paginator with `collect()`, `first()`, `take()`) |
| `task.py` | Hub model | `Task`; PrivateAttrs `_custom_fields_accessor`, `_client`, `_original_custom_fields`; active record `save_async()` / `save()` / `refresh_async()` / `refresh()`; `reset_custom_field_tracking()` |
| `custom_field_accessor.py` | Fluent CF wrapper | `CustomFieldAccessor`; dict-like API (`__getitem__`, `__setitem__`, `__delitem__`); `to_api_dict()`, `to_list()`, `has_changes()`, `clear_changes()`, `list_available_fields()` |
| `project.py` | Project model | `Project`; `tasks: list[Any] | None = Field(exclude=True)` |
| `section.py` | Section model | `Section`; `tasks: list[Any] | None = Field(exclude=True)` |
| `user.py` | User model | `User` |
| `workspace.py` | Workspace model | `Workspace` |
| `custom_field.py` | CF definition | `CustomFieldEnumOption`, `CustomField`, `CustomFieldSetting` |
| `attachment.py` | Attachment model | `Attachment` |
| `story.py` | Story model | `Story`; `resource_subtype` not enforced as enum (known gap) |
| `tag.py` | Tag model | `Tag` |
| `team.py` | Team models | `TeamMembership`, `Team` |
| `goal.py` | Goal models | `GoalMetric`, `Goal`, `GoalMembership` |
| `portfolio.py` | Portfolio model | `Portfolio` |
| `webhook.py` | Webhook models | `WebhookFilter`, `Webhook` |
| `__init__.py` | Public API + rebuild | Exports 22 types; orchestrates `model_rebuild()` in tier order |

### Public API Surface

`from autom8_asana.models import ...` exports (22 symbols):
- Base: `AsanaResource`, `NameGid`, `PageIterator`
- Accessor: `CustomFieldAccessor`
- Tier 1: `CustomField`, `CustomFieldEnumOption`, `CustomFieldSetting`, `Project`, `Section`, `Task`, `User`, `Workspace`
- Tier 2: `Attachment`, `Goal`, `GoalMembership`, `GoalMetric`, `Portfolio`, `Story`, `Tag`, `Team`, `TeamMembership`, `Webhook`, `WebhookFilter`

### Consuming Packages

| Consumer | What it uses |
|----------|-------------|
| `clients/*.py` | `model_validate()` on API responses; `Task`, `Project`, `Section`, etc. |
| `clients/tasks.py` | Injects `_client` reference into returned `Task` objects (enables `save_async()`) |
| `services/` | Typed model inputs/outputs |
| `persistence/session.py` | `SaveSession` tracks `Task` objects; calls `task.reset_custom_field_tracking()` post-commit |
| `persistence/errors.py` | Imported lazily from `task.py` and `custom_field_accessor.py` (TENSION-003) |
| `dataframes/builders/` | Populates `Project.tasks` / `Section.tasks` (excluded fields) |
| `models/business/` (separate feature) | Subclasses `Task`; rebuilds via `__init__.py` tier-0 |

### Test Locations

| Test File | Coverage |
|-----------|---------|
| `tests/unit/models/test_models.py` | `AsanaResource`, `NameGid` basics, `extra="ignore"` |
| `tests/unit/models/test_common_models.py` | `NameGid`, `PageIterator` |
| `tests/unit/models/test_custom_field_accessor.py` | `CustomFieldAccessor` (set/get/remove, strict, to_api_dict) |
| `tests/unit/models/test_task_custom_fields.py` | Three-system tracking (accessor vs direct changes, precedence, reset) |
| `tests/integration/test_custom_field_type_validation.py` | Type validation at `set()` time |
| `tests/unit/persistence/test_custom_field_persistence.py` | Accessor integration with persistence layer |

## Boundaries and Failure Modes

### What This Feature Does NOT Do

- **Does not validate custom field schema against workspace**: `CustomFieldAccessor` validates value types (text/number/enum/date/people/multi_enum) at `set()` time but cannot verify that a given field GID exists in the Asana workspace. Asana API validates on write.
- **Does not own business domain models**: `models/business/` is the `business-domain-model` feature. This entry covers ONLY the 16 top-level resource files in `models/`.
- **Does not enforce `Story.resource_subtype` as enum**: The field is `str | None`. Known gap.
- **Does not provide thread safety for `PageIterator`**: No concurrency guards on the iterator's `_buffer`/`_started`/`_exhausted` state. Not designed for concurrent iteration.
- **Does not own API request/response models**: Those live in `api/routes/*_models.py` (TENSION-002).

### TENSION-003: Models → Persistence Circular Import

**Location**: `models/task.py:414-418`, `models/custom_field_accessor.py:421`

Both files contain lazy imports inside function bodies, guarded by `nosemgrep: autom8y.no-models-import-upper`:
- `task.py:save_async()` imports `persistence.errors.SaveSessionError` and `persistence.session.SaveSession`
- `custom_field_accessor.py:_validate_type()` imports `persistence.errors.GidValidationError`

These imports are NOT under `TYPE_CHECKING` — they are runtime function-body imports. They fire only when `save_async()` / `_validate_type()` is called, avoiding circular import at module load time. The `nosemgrep` annotations suppress the `autom8y.no-models-import-upper` semgrep rule. Resolution would require redesigning `SaveSession` to not be referenced from the model layer (TENSION-003, medium cost).

`transport.sync.sync_wrapper` is also imported lazily in `task.save()` / `task.refresh()` — same pattern, lower severity (no circular dep risk there).

### Error Paths

| Condition | Error | Raised By |
|-----------|-------|-----------|
| `Task.save_async()` with no `_client` | `ValueError` | `task.py:409` |
| `Task.refresh_async()` with no `_client` | `ValueError` | `task.py:459` |
| `CustomFieldAccessor._resolve_gid()` — unknown name, `strict=True` | `NameNotFoundError` (from `autom8_asana.errors`) | `custom_field_accessor.py:377` — includes difflib suggestions |
| `CustomFieldAccessor._validate_type()` — wrong type | `GidValidationError` (from `persistence.errors`) | `custom_field_accessor.py:437-488` |
| `SaveSession.commit_async()` failure | `SaveSessionError` (re-raised in `Task.save_async()`) | `task.py:425` |
| GID pattern violation (production) | `ValidationError` (pydantic) | `base.py:47` |

### Known Edge Cases

- **`Task.model_dump()` with both accessor + direct changes**: Accessor wins; `logger.warning("task_custom_field_conflict", ...)` is emitted. Caller only sees accessor result.
- **`reset_custom_field_tracking()` called before snapshot exists**: Idempotent (`None` snapshot → `None` stays).
- **`CustomFieldAccessor` with `data=None`**: Constructor normalizes to empty list; `len()` returns 0.
- **`NameGid` equality**: Based solely on `gid` — two `NameGid` objects with different `name` but same `gid` compare equal and share the same hash.
- **`to_api_dict()` date wrapping**: Only fires when field's `resource_subtype == "date"` AND the value is a `str`. Callers passing non-string dates bypass this wrapping.
- **`_GID_PATTERN` at module load time**: Reads `os.environ` directly — not `settings.is_production`. This means a process that imports `models` before setting `AUTOM8Y_ENV` will get production-mode GID validation regardless.

### Interaction Points and Boundary Clarity

| Boundary | Clarity |
|----------|---------|
| `models/ → clients/` | Clean: clients call `model_validate()`, then inject `_client` into returned `Task` |
| `models/ → persistence/` | Managed violation (TENSION-003): lazy imports inside `save_async()` and `_validate_type()` only; `nosemgrep` suppresses CI rule |
| `models/ → transport.sync` | Lazy import in `Task.save()` / `Task.refresh()` only |
| `models/ → dataframes/resolver` | `CustomFieldAccessor.__init__` accepts optional `DefaultCustomFieldResolver`; import under `TYPE_CHECKING` only; runtime import not triggered unless resolver is provided and used |
| `models/ → autom8y_log` | `task.py:25` — `get_logger(__name__)` at module level; no circularity |
| `models/ → core/` (errors) | `NameNotFoundError` from `autom8_asana.errors` (not `core/`); lazy import in `_resolve_gid()` |

```metadata
{
  "domain": "feat/asana-models",
  "generated_at": "2026-05-08T00:00Z",
  "source_hash": "8980bcd7",
  "confidence": 0.95,
  "file_count": 16,
  "model_count": 22,
  "adrs_referenced": ["ADR-0005", "ADR-0006", "ADR-0056", "ADR-0067", "ADR-0074"],
  "tensions": ["TENSION-003"],
  "test_files": 6,
  "key_types": ["AsanaResource", "NameGid", "Task", "CustomFieldAccessor", "PageIterator"]
}
```
