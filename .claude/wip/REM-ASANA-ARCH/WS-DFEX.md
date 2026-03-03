# WS-DFEX: DataFrame Extraction + Holder Registry

**Objective**: Extract `Project.build_dataframe()` and `Section.build_dataframe()`
convenience methods to DataFrameService (eliminating Cycle 1 models->dataframes
direction), and add a holder type registry to persistence/holder_construction.py
(eliminating fragile explicit Holder imports).

**Rite**: hygiene
**Complexity**: MODULE
**Recommendations**: R-006, R-009
**Preconditions**: Cleaner after WS-SYSCTX (R-005), but not blocked by it
**Estimated Effort**: 3-3.5 days (R-006: 1.5 days, R-009: 1.5-2 days)

---

## Part A: Extract build_dataframe() to DataFrameService (R-006)

### Problem

`models/project.py` and `models/section.py` contain convenience methods that
import from `dataframes/` via deferred imports, creating the models -> dataframes
direction of Cycle 1 (coupling score 68).

**Evidence**: ARCHITECTURE-ASSESSMENT.md AP-2; DEPENDENCY-MAP.md Section 7.2

### Key Source Files

- `src/autom8_asana/models/project.py` -- `build_dataframe()`, `build_section_dataframe()`
- `src/autom8_asana/models/section.py` -- `build_dataframe()`
- `src/autom8_asana/services/dataframe_service.py` (360 LOC, already exists)

### Steps

1. Read current convenience methods in `models/project.py` and `models/section.py`
   to understand their signatures and deferred imports
2. Add new functions to `services/dataframe_service.py`:
   - `build_for_project(project, ...) -> DataFrame`
   - `build_for_section(section, ...) -> DataFrame`
   Move the logic currently deferred-imported in the model methods
3. Audit all callers: `grep -rn "\.build_dataframe\(\)" src/` and
   `grep -rn "\.build_section_dataframe\(\)" src/`
4. Update ONE caller to use `dataframe_service.build_for_project()` -- verify tests
5. Update all remaining callers
6. Remove convenience methods and deferred imports from model files
7. Verify: `python -c "from autom8_asana.models import Project"` does not
   trigger any dataframes import
8. Run: `pytest tests/unit/models/ tests/unit/dataframes/ tests/unit/services/ -x`

### Rollback Strategy

Keep convenience methods as thin wrappers calling service functions during
transition. If downstream breakage appears, wrappers remain until cause identified.

---

## Part B: Holder Type Registry (R-009)

### Problem

`persistence/holder_construction.py` imports 6 specific Holder types, creating
tight coupling to the entity hierarchy. Adding a new entity type requires updating
this file -- if forgotten, holders are never auto-created (silent behavioral gap).

**Evidence**: ARCHITECTURE-REPORT.md R-009; DEPENDENCY-MAP.md Section 7.3

### Key Source Files

- `src/autom8_asana/persistence/holder_construction.py`
- `src/autom8_asana/models/business/` (Holder types: ContactHolder, LocationHolder,
  OfferHolder, ProcessHolder, UnitHolder, Business)

### Steps

1. Add `HOLDER_REGISTRY: dict[str, type[Holder]]` to `persistence/holder_construction.py`
2. Replace the 6 explicit Holder imports with registry lookups:
   `holder_class = HOLDER_REGISTRY[entity_type_str]`
3. Each entity type module registers its Holder type:
   `HolderRegistry.register("unit", UnitHolder)` (in `_bootstrap.py` or Holder module)
4. Add a completeness test: assert all known entity types from `EntityRegistry`
   have a registered Holder
5. Run: `pytest tests/unit/persistence/ -x`

---

## Do NOT

- Extract `Task.save()` / `Task.save_sync()` in this sprint (separate follow-on)
- Change any model field definitions or Pydantic configuration
- Modify the SaveSession coordinator internals
- Change the DataFrame builder logic (only move where it is called from)

---

## Green-to-Green Gates

**Part A**:
- `pytest tests/unit/models/` passes throughout migration
- `pytest tests/unit/dataframes/` passes throughout migration
- `pytest tests/unit/services/` passes after new service methods added
- Static check: no imports of `dataframes/` in `models/project.py` or `models/section.py`

**Part B**:
- `pytest tests/unit/persistence/` passes after registry migration
- Holder completeness test asserts all entity types have registered Holders
- No runtime behavior change in holder construction

---

## Definition of Done

- [ ] R-006: build_dataframe() extracted to DataFrameService
- [ ] R-006: models/project.py and models/section.py have zero dataframes imports
- [ ] R-006: Cycle 1 (models->dataframes direction) eliminated
- [ ] R-009: Holder type registry implemented in persistence
- [ ] R-009: Completeness test covers all entity types
- [ ] Full test suite green
- [ ] MEMORY.md updated: "WS-DFEX: DataFrame extraction + holder registry DONE"
