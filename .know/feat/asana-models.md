---
domain: feat/asana-models
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/*.py"
  - "./src/autom8_asana/exceptions.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.88
format_version: "1.0"
---

# Pydantic v2 Asana Resource Models

## Purpose and Design Rationale

The `models/` package provides typed Pydantic v2 representations of every Asana API resource. The core design decision is **defensive parsing by default**: every model carries `extra="ignore"` per ADR-0005, so Asana can add fields without breaking the SDK.

Models serve three consumers: `clients/` (parse API JSON), `services/` (pass typed models), and `models/business/` (subclasses `Task`).

## Conceptual Model

### Inheritance Hierarchy

All models extend `AsanaResource(BaseModel)` with `extra="ignore"`, `populate_by_name=True`, `str_strip_whitespace=True`. `NameGid` is standalone (frozen, hashable on `gid`, NOT an AsanaResource subclass).

### Two Field Tiers

**Tier A (typed with NameGid)**: Relationship fields -- `Task.assignee`, `Task.projects`, `Project.owner`.
**Tier B (raw dicts)**: Complex/irregular structures -- `Task.custom_fields`, `Task.memberships`.

### Custom Field Access (Three-Layer)

1. **Raw list** (`task.custom_fields`): As received from API
2. **`CustomFieldAccessor`** (`task.custom_fields_editor()`): Fluent wrapper with `set/get/remove`, name resolution, type validation
3. **Snapshot tracking**: `_original_custom_fields` captured at `model_validate()` for change detection

### Forward Reference Resolution

All files use `from __future__ import annotations`. `__init__.py` calls `model_rebuild()` on every model with `_NAMEGID_NS = {"NameGid": NameGid}` namespace.

## Implementation Map

17 model files: base.py, common.py (NameGid, PageIterator), task.py (largest, active record with save/refresh), project.py, section.py, user.py, workspace.py, webhook.py, custom_field.py, custom_field_accessor.py, goal.py, portfolio.py, tag.py, story.py, team.py, attachment.py. Plus exceptions.py (14 exception types).

**Key ADRs**: ADR-0005 (extra=ignore), ADR-0006 (NameGid), ADR-0056 (custom field write format), ADR-0067 (snapshot detection), ADR-0074 (reset tracking post-commit).

## Boundaries and Failure Modes

- `models/` imports only from `core/` at module level. Exception: `task.py` defers `persistence.session` imports.
- `extra="ignore"` is non-negotiable per ADR-0005.
- `Task.model_dump()` must check both accessor and snapshot; accessor changes beat direct-list changes.
- `tasks`/`sections` fields on `Project`/`Section` use `exclude=True` to prevent API serialization.

## Knowledge Gaps

1. **`CustomFieldAccessor.resolver` integration** path not visible in this scope.
2. **`Story.resource_subtype` enumeration** not enforced as enum.
3. **`PageIterator` thread safety**: No concurrency guards.
