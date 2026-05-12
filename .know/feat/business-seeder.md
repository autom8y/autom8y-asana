---
domain: feat/business-seeder
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/seeder.py"
  - "./src/autom8_asana/automation/seeding.py"
  - "./src/autom8_asana/lifecycle/seeding.py"
  - "./tests/unit/models/business/test_seeder.py"
  - "./tests/unit/automation/test_seeding.py"
  - "./tests/unit/automation/test_seeding_write.py"
  - "./tests/unit/lifecycle/test_seeding.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.92
format_version: "1.0"
---

# Feature: Business Entity Seeder (Field Population Across Lifecycle)

## Purpose

The business-seeder feature handles two closely related but distinct concerns:

1. **Business hierarchy creation** — find-or-create a complete Business → Unit → Process → Contact entity hierarchy in Asana, using a multi-tier matching strategy to detect pre-existing businesses before creating new ones.
2. **Field population** — after a new process is created (either by the seeder itself or by the lifecycle engine), propagate custom field values from the Business and Unit hierarchy downward onto the new process task, and carry through relevant fields from a source process.

The feature spans three packages because these concerns naturally belong to different layers. `models/business/seeder.py` is the **domain class** — it knows about the Business hierarchy and how to build it. `automation/seeding.py` is the **automation write path** — it knows how to translate display-name field values into Asana API GIDs and issue a single batched write. `lifecycle/seeding.py` is the **lifecycle bridge** — it wires zero-config auto-cascade seeding into the `LifecycleEngine`'s `creation.py` phase, so any pipeline transition can seed without static field-list configuration.

**Why it exists**: When a business enters a new lifecycle stage (e.g., Sales → Onboarding), the new process task needs to inherit context fields from its parent hierarchy (company vertical, contact phone, priority). Without seeding, every field would need to be re-entered manually. The feature automates this propagation.

**Prior census gap**: The census noted "Business Seeder boundary unclear." After reading the sources, the boundary is: `BusinessSeeder` creates/finds entities and delegates all writes to `SaveSession`. `FieldSeeder` reads existing entities and writes custom fields via `CustomFieldAccessor`. `AutoCascadeSeeder` composes the two with zero-config matching. The three are not alternatives — they serve different steps of the same pipeline.

**Design decisions in source comments (no standalone ADR files found in `.ledge/decisions/` for these)**:

| Reference | Decision |
|-----------|----------|
| ADR-0099 | Find-or-create pattern for `BusinessSeeder`; uses `SaveSession` for commit |
| ADR-0101 | `ProcessData.initial_state` removed; `SeederResult.added_to_pipeline` removed — canonical project IS the pipeline |
| ADR-0105 | Field seeding architecture: 4-layer precedence (Business → Unit → Process → Computed) |
| ADR-0112 | Custom field GID resolution via `CustomFieldAccessor` (not manual dict manipulation) |
| ADR-EW-003 | `FieldResolver` extracted from `FieldSeeder` into `resolution/field_resolver.py` for reuse by entity-write-api |
| TDD-PROCESS-PIPELINE Phase 3 | Test-driven development anchored for `BusinessSeeder` |
| TDD-BusinessSeeder-v2 | Composite matching tier added (Fellegi-Sunter probabilistic engine via `MatchingEngine`) |
| IMP-02 | `target_task` passthrough on `AutoCascadeSeeder.seed_async` and `FieldSeeder.write_fields_async` eliminates double-fetch |

---

## Conceptual Model

### Three Components

```
BusinessSeeder          FieldSeeder             AutoCascadeSeeder
(models/business/)      (automation/)           (lifecycle/)

Find-or-create         Cascade + carry-through  Zero-config
Business hierarchy  →  field computation    →   name-matching
via SaveSession        + API write              bridge
                       (explicit field lists)   (runtime matching)
```

The three components are not parallel alternatives; they form a dependency chain in the lifecycle context: `LifecycleEngine.creation` calls `AutoCascadeSeeder`, which delegates the write step to `FieldSeeder.write_fields_async`. `BusinessSeeder` is used independently by external callers (e.g., intake pipelines) to create the hierarchy before any lifecycle engine involvement.

### BusinessSeeder: Find-or-Create

`BusinessSeeder` constructs a complete Business → Unit → Process (→ Contact) hierarchy. It follows a two-tier matching strategy before creating new entities:

```
Tier 1: company_id exact match  →  SearchService.find_one_async()
Tier 2: Composite matching      →  MatchingEngine (Fellegi-Sunter probabilistic)
           ↓                           ↓
      load Business by GID       candidates via name search (limit=50)
                                  → CompositeBlockingRule.filter_candidates()
                                  → MatchingEngine.find_best_match()
```

Entities are created with **temp GIDs** (`temp_biz_<hex8>`, `temp_unit_<hex8>`, etc.) and committed together through a single `SaveSession` context manager. After `session.commit_async()`, real Asana GIDs replace the temp GIDs.

`SeederResult` captures the output: `business`, `unit`, `process`, `contact` (optional), and boolean flags `created_business`, `created_unit`, `created_contact`. No `added_to_pipeline` flag exists (removed per ADR-0101; the hierarchy's canonical project IS the pipeline).

### FieldSeeder: Field Computation and Write

`FieldSeeder` computes field values through a 4-layer precedence stack and writes them in a single batched API call:

```
Layer 1: Business cascade fields    (default: [] — empty, varies per target project)
Layer 2: Unit cascade fields        (default: ["Vertical"])
Layer 3: Process carry-through      (default: ["Contact Phone", "Priority"])
Layer 4: Computed fields            (always: {"Launch Date": date.today()})
       ↓ dict.update semantics — later layers override earlier
```

`write_fields_async()` resolves display-name field keys to Asana custom field GIDs via `FieldResolver` (ADR-EW-003) and `CustomFieldAccessor`, then issues a single `tasks.update_async()` call with all resolved fields. Enum and multi-enum fields require GID resolution (Asana silently ignores string names); `FieldSeeder._resolve_enum_value` handles this case-insensitively.

**`WriteResult`** dataclass: `success: bool`, `fields_written: list[str]`, `fields_skipped: list[str]`, `error: str | None`. A skipped field is one not found on the target task; it is logged at WARNING level but does not fail the operation.

### AutoCascadeSeeder: Zero-Config Lifecycle Bridge

`AutoCascadeSeeder` (in `lifecycle/seeding.py`) removes the need for static field-list configuration. Instead of requiring the caller to specify which fields to cascade, it fetches the target task's custom field definitions at runtime and cascades any field whose name (case-insensitive) exists on both the source entity and the target task.

```
AutoCascadeSeeder.seed_async(target_task_gid, business, unit, source_process,
                             exclude_fields=None, computed_fields=None, target_task=None)
     ↓
1. Fetch target task custom field definitions (skip if target_task pre-provided)
2. Build target_field_names = {name.lower(): field_def}
3. For each entity (Business, Unit, Process):
       entity.custom_fields → normalize → name-match → extract display value
4. Computed fields (layer 4, highest priority)
5. Delegate to FieldSeeder.write_fields_async(target_task_gid, seeded, target_task=...)
```

The `target_task` passthrough (IMP-02) threads the pre-fetched task object into `write_fields_async`, eliminating a second `tasks.get_async` call. Callers that pre-fetch the task (e.g., `lifecycle/creation.py`) save 2 API calls per seeding operation.

**`SeedingResult`** dataclass: `fields_seeded: list[str]`, `fields_skipped: list[str]`, `warnings: list[str]`.

### State / Lifecycle Position

The feature participates in the `LifecycleEngine` Phase 1 (Create) pipeline. In `lifecycle/creation.py`, after the target process task is created via the Asana API, `AutoCascadeSeeder.seed_async` is invoked with the newly created task GID, business, unit, and source process. Failure of seeding is **non-fatal** — the lifecycle engine logs a warning and continues. This is consistent with the LifecycleEngine's fail-forward design.

In the `automation/pipeline.py` (pipeline conversion path), `FieldSeeder` is used directly with explicit field lists sourced from `PipelineStage` YAML config. This is the "configured" path; `AutoCascadeSeeder` is the "zero-config" lifecycle path.

---

## Implementation Map

### Production Files

| File | Package | LOC | Primary Responsibility |
|------|---------|-----|------------------------|
| `src/autom8_asana/models/business/seeder.py` | `models/business` | 617 | Domain class: hierarchy find-or-create, multi-tier business matching, SaveSession commit |
| `src/autom8_asana/automation/seeding.py` | `automation` | 816 | Field computation (4-layer cascade), enum GID resolution, batched API write via `write_fields_async` |
| `src/autom8_asana/lifecycle/seeding.py` | `lifecycle` | 302 | Zero-config auto-cascade bridge for LifecycleEngine; `AutoCascadeSeeder`, `SeedingResult` |

Total: 1,735 LOC across 3 packages.

### Key Types

| Type | File | Kind | Role |
|------|------|------|------|
| `BusinessSeeder` | `models/business/seeder.py:119` | class | Entry point for hierarchy creation |
| `BusinessData` | `models/business/seeder.py:48` | Pydantic model | Input DTO: name, company_id, address, email, phone, domain |
| `ContactData` | `models/business/seeder.py:72` | Pydantic model | Input DTO: full_name, contact_email, contact_phone |
| `ProcessData` | `models/business/seeder.py:85` | Pydantic model | Input DTO: name, process_type, assigned_to, due_date, notes |
| `SeederResult` | `models/business/seeder.py:101` | dataclass | Output: business, unit, process, contact, created_* flags, warnings |
| `FieldSeeder` | `automation/seeding.py:61` | class | 4-layer field computation + write path |
| `WriteResult` | `automation/seeding.py:35` | dataclass | Write outcome: success, fields_written, fields_skipped, error |
| `AutoCascadeSeeder` | `lifecycle/seeding.py:56` | class | Zero-config bridge; delegates write to FieldSeeder |
| `SeedingResult` | `lifecycle/seeding.py:42` | dataclass | Auto-cascade outcome: fields_seeded, fields_skipped, warnings |

### Entry Points

**External callers** (hierarchy creation):
- `BusinessSeeder(client).seed_async(business, process, contact=None, unit_name=None)` — async
- `BusinessSeeder(client).seed(...)` — sync wrapper via `transport.sync.sync_wrapper`

**Lifecycle engine** (field seeding in Phase 1):
- `AutoCascadeSeeder(client).seed_async(target_task_gid, business, unit, source_process, ...)` — called from `lifecycle/creation.py:415`

**Pipeline automation** (field seeding in pipeline conversion):
- `FieldSeeder(client, business_cascade_fields=..., ...)` — called from `automation/pipeline.py:390` with explicit field lists from YAML config

### Data Flow — Primary Path (LifecycleEngine)

```
lifecycle/creation.py (Phase 1 — process task created)
    → AutoCascadeSeeder.seed_async(target_task_gid, business, unit, source_process, target_task=task)
        → target task custom fields already pre-fetched (IMP-02 passthrough)
        → _extract_matching_fields(business, target_field_names, excludes)
        → _extract_matching_fields(unit, target_field_names, excludes)
        → _extract_matching_fields(source_process, target_field_names, excludes)
        → computed_fields {"Launch Date": "today"}
        → FieldSeeder(client).write_fields_async(target_task_gid, seeded, target_task=task)
            → normalize_custom_fields(target_task.custom_fields)
            → CustomFieldAccessor(data, strict=False)
            → FieldResolver(custom_fields_data).resolve_fields(mapped_fields)
            → accessor.set(matched_name, resolved_value)  [per resolved field]
            → client.tasks.update_async(target_task_gid, custom_fields=accessor.to_api_dict())
```

### Data Flow — Hierarchy Creation Path (External Callers)

```
BusinessSeeder.seed_async(business, process, contact, unit_name)
    → _find_business_async(data)
        Tier 1: _search_by_company_id → client.search.find_one_async(PRIMARY_PROJECT_GID, ...)
        Tier 2: _find_by_composite_match → MatchingEngine.find_best_match(data, candidates)
    → construct Business/Unit/Process/Contact with temp GIDs
    → async with client.save_session() as session:
        session.track(biz), session.track(unit), session.track(proc), session.track(contact)
        await session.commit_async()
    → return SeederResult(business, unit, process, contact, created_* flags)
```

### Public API Surface

Exported from `automation/__init__.py`: `FieldSeeder`, `WriteResult`
Exported from `lifecycle/__init__.py`: `AutoCascadeSeeder`, `SeedingResult`
Exported from `models/business/seeder.py` (`__all__`): `BusinessSeeder`, `SeederResult`, `BusinessData`, `ContactData`, `ProcessData`

Consumers:
- `lifecycle/creation.py` → `AutoCascadeSeeder` (primary lifecycle consumer)
- `automation/pipeline.py` → `FieldSeeder` (pipeline conversion consumer)
- External SDK callers → `BusinessSeeder` (intake/CRM integration path)

### Test Files

| File | Covers |
|------|--------|
| `tests/unit/models/business/test_seeder.py` | `BusinessData`/`ContactData`/`ProcessData` validation, `SeederResult` defaults, `BusinessSeeder._find_business_async` matching tiers, `_search_by_company_id` graceful degradation |
| `tests/unit/automation/test_seeding.py` | `FieldSeeder` initialization, cascade/carry-through/computed field mechanics, enum normalization, `_get_field_value` multi-source access, `write_fields_async` enum GID resolution (integration) |
| `tests/unit/automation/test_seeding_write.py` | `WriteResult` dataclass, `write_fields_async` batching (FR-SEED-002), missing field skip/warn (FR-SEED-005), empty people field skip bug fix, `target_task` passthrough (IMP-02) |
| `tests/unit/lifecycle/test_seeding.py` | `AutoCascadeSeeder.seed_async` target_task passthrough (IMP-02), backward compat without passthrough, `write_fields_async` delegation with correct kwargs |

---

## Boundaries

### What This Feature Does

- Creates/finds Business, Unit, Process, Contact entities in Asana (hierarchy creation path)
- Computes field values via 4-layer cascade and writes them in a single batched API call
- Bridges zero-config field seeding into the LifecycleEngine via `AutoCascadeSeeder`
- Resolves enum display names to Asana enum GIDs (case-insensitive)
- Degrades gracefully: search failures degrade to "create new entity"; missing fields are skipped with a warning; seeding failure in the lifecycle engine is non-fatal

### What This Feature Does NOT Do

- **Does not manage field schema definitions** — custom field GIDs and definitions come from the live Asana API at runtime
- **Does not own enum option configuration** — enum options are fetched per-task from the API; `FieldSeeder` resolves against whatever options are present
- **Does not trigger webhooks or lifecycle transitions** — seeding is a side effect within a Phase 1 creation, not a lifecycle trigger
- **Does not handle field validation beyond existence checking** — if a field's value does not match any enum option, the field is silently skipped (with warning log)
- **Does not directly manage SaveSession** in the field-seeding path — only `BusinessSeeder` uses `SaveSession`; `FieldSeeder`/`AutoCascadeSeeder` use `tasks.update_async` directly
- **Does not persist the Business hierarchy result to the database** — entities are written to Asana via SaveSession; no local DB writes

### Known Edge Cases and Failure Modes

| Scenario | Behavior |
|----------|----------|
| Multiple businesses found for `company_id` | `find_one_async` raises `ValueError` → fallback to `find_async(limit=1)` → returns first hit |
| Composite matching raises any exception | BROAD-CATCH degrades gracefully: logs warning, returns None → new entity is created |
| Enum value not found in options | `_resolve_enum_value` returns None → field added to `fields_skipped` → no update for that field |
| Empty string or empty list for people field | Explicitly skipped in `write_fields_async` before setting on accessor (bug fix: Asana rejects non-list for people fields) |
| `target_task.custom_fields` is None | `normalize_custom_fields` returns `[]` → `AutoCascadeSeeder` logs `auto_cascade_no_target_fields` and returns empty `SeedingResult` |
| Seeding failure in LifecycleEngine | Non-fatal: `lifecycle/creation.py` logs `pipeline_field_seeding_failed` and continues |
| `BusinessSeeder._find_business_async` with no company_id | Skips Tier 1; proceeds directly to Tier 2 (composite matching) |
| GID passthrough for enum | Numeric string GIDs are validated against known options; invalid GIDs return None |
| Assigned-to (people field) in carry-through | "Assigned To" was removed from `DEFAULT_PROCESS_CARRY_THROUGH_FIELDS` per "Efficient Field Seeding Fix" comment in test_seeding.py:302 |

### Interaction Points and Cross-Feature Dependencies

| Dependency | Direction | What is Consumed |
|------------|-----------|-----------------|
| `models/business/matching/` (MatchingEngine, Candidate) | BusinessSeeder → matching | Composite Fellegi-Sunter scoring |
| `search/service.py` (SearchService) | BusinessSeeder → search | `find_one_async`, `find_async` for candidate retrieval |
| `persistence/session.py` (SaveSession) | BusinessSeeder → persistence | Hierarchy creation commit |
| `models/custom_field_accessor.py` (CustomFieldAccessor) | FieldSeeder → accessor | GID-keyed custom field write dict |
| `resolution/field_resolver.py` (FieldResolver) | FieldSeeder → resolution | Shared field resolution logic (ADR-EW-003) |
| `core/field_utils.py` (get_field_attr, normalize_custom_fields) | Both FieldSeeder and AutoCascadeSeeder → core | Dict/object-safe field access |
| `lifecycle/creation.py` | AutoCascadeSeeder ← lifecycle | AutoCascadeSeeder called from Phase 1 |
| `automation/pipeline.py` | FieldSeeder ← automation | FieldSeeder called with explicit field lists from YAML |
| `transport/sync.py` | BusinessSeeder → transport | Sync wrapper for `seed_async` |

### Configuration Boundaries

- `FieldSeeder` accepts `business_cascade_fields`, `unit_cascade_fields`, `process_carry_through_fields` at construction time; if `None`, uses class-level defaults
- `DEFAULT_BUSINESS_CASCADE_FIELDS = []` — intentionally empty; Business fields do not exist on all target projects; must be configured per-pipeline via `PipelineStage` YAML
- `DEFAULT_UNIT_CASCADE_FIELDS = ["Vertical"]` — only Vertical is reliably present on common target projects (e.g., Onboarding)
- `DEFAULT_PROCESS_CARRY_THROUGH_FIELDS = ["Contact Phone", "Priority"]`
- `AutoCascadeSeeder` has no static field lists; it matches by name at runtime; callers provide `exclude_fields` and `computed_fields` as keyword arguments
- `BusinessSeeder` accepts `matching_config: MatchingConfig | None`; if None, loads from environment via `MatchingConfig.from_env()`
- `Business.PRIMARY_PROJECT_GID` must be set (not None) for search to function; all Tier 1 and Tier 2 search paths assert this

```metadata
confidence: 0.92
evidence_basis:
  - All 3 production files read in full (617 + 816 + 302 = 1,735 LOC)
  - All 4 test files read in full
  - architecture.md pre-loaded for package structure
  - lifecycle/creation.py grep confirmed AutoCascadeSeeder call site
  - automation/pipeline.py grep confirmed FieldSeeder call site
  - feat/INDEX.md census entry read for census gap resolution note
  - feat/lifecycle-engine.md grep confirmed AutoCascadeSeeder in lifecycle feature doc
  - feat/entity-write-api.md grep confirmed ADR-EW-003 FieldResolver extraction
  - .ledge/decisions/ scanned — no standalone ADR files found for ADR-0099/0101/0105/0112; these exist as inline docstring references only
gaps:
  - No standalone ADR decision files found; design rationale captured from source code docstrings only
  - MatchingEngine (models/business/matching/) internals not read; blocking rule and scorer details are opaque
  - automation/pipeline.py read only at grep level; full PipelineStage YAML config integration not traced
```
