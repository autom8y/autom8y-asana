# Impact Analysis: Process Pipeline Cleanup

## Executive Summary

The current implementation incorrectly assumes separate "pipeline projects" exist for each ProcessType (Sales, Onboarding, etc.), when in reality the canonical project (e.g., "Sales" project) IS the pipeline itself. Process entities are already members of their canonical project - there is no separate pipeline project to add them to.

**Root Cause**: Misunderstanding of domain model - Process projects are named "Sales", "Onboarding", etc. (not "Sales Processes"), and processes are direct members of these projects.

## Impact Summary

| Category | Count | Details |
|----------|-------|---------|
| Files to DELETE | 2 | process_registry.py, test_process_registry.py |
| Files to MODIFY | 5 | process.py, seeder.py, detection.py, __init__.py, test_process.py |
| Tests to DELETE | 1 | Full test file (test_process_registry.py) |
| Test Classes to DELETE | 2 | TestAddToPipeline, TestMoveToState |
| Test Classes to MODIFY | 2 | TestProcessPipelineState, TestProcessTypeDetection |
| Total Lines to Delete | ~1,085 | Source + tests |
| Total Lines to Modify | ~300 | Estimated modifications |

---

## Files to DELETE

### 1. process_registry.py

- **Path**: `src/autom8_asana/models/business/process_registry.py`
- **Lines**: 299
- **Reason**: Wrong concept - assumes separate pipeline projects exist when the canonical project IS the pipeline

**Contents Being Deleted**:
```python
# ProcessProjectRegistry class (lines 45-290)
# - Singleton mapping ProcessType -> "pipeline project" GID
# - Environment variable pattern: AUTOM8_PROCESS_PROJECT_{TYPE}
# - Section GID management: AUTOM8_SECTION_{TYPE}_{SECTION}
# - Forward/reverse lookup methods
# - register(), reset() methods

# get_process_project_registry() function (lines 293-299)
```

**Why Wrong**:
- Processes are already in their canonical project (e.g., "Sales" project GID is stored on the Process entity itself)
- There is no separate "Sales Pipeline" project to register
- The registry adds unnecessary indirection

---

### 2. test_process_registry.py

- **Path**: `tests/unit/models/business/test_process_registry.py`
- **Lines**: 393
- **Reason**: Tests deleted module

**Test Classes Being Deleted**:
- `TestProcessProjectRegistrySingleton` (lines 41-75)
- `TestRegistrationAndLookup` (lines 77-171)
- `TestEnvironmentVariableInitialization` (lines 173-291)
- `TestSectionGIDLookup` (lines 293-337)
- `TestReset` (lines 339-357)
- `TestBackwardCompatibility` (lines 359-393)

---

## Files to MODIFY

### 1. process.py

- **Path**: `src/autom8_asana/models/business/process.py`
- **Lines Affected**: ~170 lines (methods + imports)

#### REMOVE: add_to_pipeline() method (lines 325-369)

**Current Implementation**:
```python
def add_to_pipeline(
    self,
    session: "SaveSession",
    process_type: ProcessType,
    *,
    section: ProcessSection | None = None,
) -> "SaveSession":
    """Queue adding this process to a pipeline project."""
    from autom8_asana.models.business.process_registry import (
        get_process_project_registry,
    )
    registry = get_process_project_registry()
    project_gid = registry.get_project_gid(process_type)
    # ... queues add_to_project and move_to_section
```

**Reason for Removal**:
- No separate pipeline project exists to add to
- Process is already a member of its canonical project (e.g., "Sales")
- Concept fundamentally wrong

---

#### MODIFY: pipeline_state property (lines 241-278)

**Current Implementation**:
```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """Get current pipeline state from section membership."""
    # Uses ProcessProjectRegistry.reverse_lookup() to identify "pipeline project"
    from autom8_asana.models.business.process_registry import (
        get_process_project_registry,
    )
    registry = get_process_project_registry()
    # Filters memberships to find registered pipeline project
```

**New Implementation Direction**:
- Should extract section from membership in canonical project (Process.PRIMARY_PROJECT_GID or entity type's primary project)
- No registry lookup needed - the Process knows its project

**Keep**: The concept of getting pipeline state from section membership

---

#### MODIFY: process_type property (lines 280-321)

**Current Implementation**:
```python
@property
def process_type(self) -> ProcessType:
    """Determine process type from pipeline project membership."""
    from autom8_asana.models.business.process_registry import (
        get_process_project_registry,
    )
    registry = get_process_project_registry()
    # Uses registry.reverse_lookup(project_gid) to determine type
```

**New Implementation Direction**:
- Derive from PRIMARY_PROJECT_GID via ProjectTypeRegistry
- Or derive from project name (e.g., "Sales" -> ProcessType.SALES)
- Consider: Is ProcessType even needed if we have EntityType.PROCESS?

**Keep**: The concept of detecting process type

---

#### MODIFY: move_to_state() method (lines 371-416)

**Current Implementation**:
```python
def move_to_state(
    self,
    session: "SaveSession",
    target_state: ProcessSection,
) -> "SaveSession":
    """Queue moving this process to a new pipeline state (section)."""
    from autom8_asana.models.business.process_registry import (
        get_process_project_registry,
    )
    # Uses registry.get_section_gid(current_type, target_state)
```

**New Implementation Direction**:
- Should look up section GID from the canonical project's sections
- May require fetching project sections or using a simpler mapping
- Consider direct section GID parameter instead of ProcessSection enum

**Keep**: The concept of moving between sections/states

---

### 2. seeder.py

- **Path**: `src/autom8_asana/models/business/seeder.py`
- **Lines Affected**: ~50 lines

#### REMOVE: ProcessProjectRegistry import and usage (lines 166-168, 279-306)

**Current Implementation**:
```python
from autom8_asana.models.business.process_registry import (
    get_process_project_registry,
)

# ... later in seed_async() ...
registry = get_process_project_registry()
project_gid = registry.get_project_gid(process.process_type)

if project_gid is not None:
    session.add_to_project(proc, project_gid)
    section_gid = registry.get_section_gid(...)
    if section_gid is not None:
        session.move_to_section(proc, section_gid)
    added_to_pipeline = True
```

**New Implementation Direction**:
- Process should already be in correct project via parent relationship
- Pipeline membership is implicit, not explicit
- May remove `added_to_pipeline` tracking from SeederResult

---

### 3. detection.py

- **Path**: `src/autom8_asana/models/business/detection.py`
- **Lines Affected**: ~40 lines

#### MODIFY: _detect_tier1_project_membership() (lines 445-541)

**Current Implementation**:
```python
def _detect_tier1_project_membership(task: Task) -> DetectionResult | None:
    # Per TDD-PROCESS-PIPELINE Phase 3: Check ProcessProjectRegistry BEFORE
    # ProjectTypeRegistry for pipeline project detection.
    from autom8_asana.models.business.process_registry import (
        get_process_project_registry,
    )

    process_registry = get_process_project_registry()
    for membership in task.memberships:
        project_gid = project_data.get("gid")
        if project_gid and process_registry.is_registered(project_gid):
            return DetectionResult(
                entity_type=EntityType.PROCESS,
                ...
            )
```

**New Implementation Direction**:
- Remove ProcessProjectRegistry check entirely
- Use only ProjectTypeRegistry for all entity type detection
- Process detection should come from project membership in a registered Process project

---

### 4. __init__.py

- **Path**: `src/autom8_asana/models/business/__init__.py`
- **Lines Affected**: ~10 lines

#### REMOVE: ProcessProjectRegistry exports (lines 106-108, 133-134)

**Current Exports**:
```python
from autom8_asana.models.business.process_registry import (
    ProcessProjectRegistry,
    get_process_project_registry,
)

__all__ = [
    ...
    # Process Pipeline Registry (TDD-PROCESS-PIPELINE)
    "ProcessProjectRegistry",
    "get_process_project_registry",
    ...
]
```

**New Implementation**: Remove these 4 lines entirely

---

### 5. test_process.py

- **Path**: `tests/unit/models/business/test_process.py`
- **Lines Affected**: ~220 lines

#### DELETE: TestAddToPipeline class (lines 598-691)

**Reason**: Tests deleted method `add_to_pipeline()`

#### DELETE: TestMoveToState class (lines 693-815)

**Reason**: Tests method that will be significantly modified or removed

#### MODIFY: TestProcessPipelineState class (lines 400-496)

**Current Tests**:
- Use `clean_registry` fixture to reset ProcessProjectRegistry
- Mock registry with `registry.register(ProcessType.SALES, "sales_project_gid")`
- Test pipeline_state detection via registry lookup

**New Tests Direction**:
- Remove registry mocking
- Test pipeline_state extraction from canonical project membership
- Test with PRIMARY_PROJECT_GID-based detection

#### MODIFY: TestProcessTypeDetection class (lines 499-595)

**Current Tests**:
- Use `clean_registry` fixture
- Mock registry.register() for type detection
- Test process_type property via registry reverse_lookup

**New Tests Direction**:
- Remove registry mocking
- Test process_type detection via ProjectTypeRegistry or project name
- Consider if this property is still needed

---

### 6. test_detection.py

- **Path**: `tests/unit/models/business/test_detection.py`
- **Lines Affected**: ~130 lines

#### MODIFY: TestPipelineDetection class (lines 768-899)

**Current Tests**:
```python
class TestPipelineDetection:
    @pytest.fixture
    def registered_pipeline_project(self, clean_registry: None) -> str:
        """Register a SALES pipeline project and return the GID."""
        gid = "sales_pipeline_project_gid"
        registry = get_process_project_registry()
        registry.register(ProcessType.SALES, gid)
        return gid

    def test_tier1_detects_process_from_pipeline_project(...)
    def test_tier1_pipeline_detection_before_entity_registry(...)
    def test_pipeline_project_in_any_membership_position(...)
    def test_no_pipeline_falls_through_to_entity_registry(...)
    def test_all_process_types_detected(...)
```

**New Tests Direction**:
- Remove ProcessProjectRegistry usage
- Test Process detection via ProjectTypeRegistry
- Remove "pipeline vs entity registry priority" tests (no longer applicable)

#### MODIFY: clean_registry fixture (lines 59-66)

**Current Implementation**:
```python
@pytest.fixture
def clean_registry() -> Generator[None, None, None]:
    """Reset registry before and after each test for isolation."""
    ProjectTypeRegistry.reset()
    ProcessProjectRegistry.reset()  # REMOVE THIS
    yield
    ProjectTypeRegistry.reset()
    ProcessProjectRegistry.reset()  # REMOVE THIS
```

---

## Import Dependency Graph

Files that import from ProcessProjectRegistry:

| File | Import Statement | Usage |
|------|-----------------|-------|
| `process.py` | `from ...process_registry import get_process_project_registry` | pipeline_state, process_type, add_to_pipeline, move_to_state |
| `seeder.py` | `from ...process_registry import get_process_project_registry` | seed_async() - add to pipeline project |
| `detection.py` | `from ...process_registry import get_process_project_registry` | _detect_tier1_project_membership() |
| `__init__.py` | `from ...process_registry import ProcessProjectRegistry, get_process_project_registry` | Module exports |
| `test_process.py` | `from ...process_registry import ProcessProjectRegistry` | Fixture reset, test setup |
| `test_detection.py` | `from ...process_registry import ProcessProjectRegistry, get_process_project_registry` | Fixture reset, test setup |
| `test_process_registry.py` | Full imports | DELETE entire file |

---

## What to KEEP (Do NOT Remove)

### ProcessType enum (lines 40-66 in process.py)
- 7 values: SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION, GENERIC
- May still be useful for categorization
- Consider: Could be derived from project name instead

### ProcessSection enum (lines 69-138 in process.py)
- 7 values + from_name() method
- Correctly represents Asana section states
- from_name() handles case-insensitive matching with aliases

### TestProcessTypeEnum class (test_process.py lines 275-312)
- Tests enum values and membership
- Still valid

### TestProcessSectionEnum class (test_process.py lines 315-338)
- Tests enum values
- Still valid

### TestProcessSectionFromName class (test_process.py lines 341-393)
- Tests from_name() method
- Still valid

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing workflows using add_to_pipeline() | High | Medium | Announce deprecation, provide migration path |
| Tests fail due to missing registry | High | High | Delete/modify tests in same PR |
| Seeder functionality breaks | Medium | High | Update seeder to work without registry |
| Detection system misidentifies Processes | Medium | Medium | Ensure ProjectTypeRegistry has Process projects |
| process_type property returns wrong values | Low | Medium | Reimplement using ProjectTypeRegistry |
| pipeline_state property returns None | Medium | High | Reimplement using canonical project sections |

---

## Migration Strategy

### Phase 1: Remove Registry Infrastructure
1. Delete `process_registry.py`
2. Delete `test_process_registry.py`
3. Remove exports from `__init__.py`
4. Update `clean_registry` fixture in test files

### Phase 2: Update Detection System
1. Remove ProcessProjectRegistry check from `_detect_tier1_project_membership()`
2. Ensure Process projects are registered in ProjectTypeRegistry
3. Update/delete `TestPipelineDetection` tests

### Phase 3: Update Process Entity
1. Remove `add_to_pipeline()` method
2. Reimplement `pipeline_state` using canonical project
3. Reimplement `process_type` using ProjectTypeRegistry or project name
4. Update or remove `move_to_state()` based on new approach
5. Delete TestAddToPipeline and TestMoveToState test classes

### Phase 4: Update Seeder
1. Remove registry usage from `seed_async()`
2. Update SeederResult (remove added_to_pipeline?)
3. Update related tests

---

## Open Questions

1. **ProcessType enum future**: Is ProcessType still needed if we have EntityType.PROCESS? Could derive type from project name.

2. **Section GID lookup**: How should move_to_state() get section GIDs without the registry? Options:
   - Fetch from API on demand
   - Use ProjectTypeRegistry with section mappings
   - Accept raw section GID parameter

3. **Seeder behavior**: Should seeder automatically detect canonical project from parent Unit's project membership?

4. **Backward compatibility**: Any external code using ProcessProjectRegistry?

---

## Affected Documentation

The following docs reference the incorrect pipeline concept and may need updates:

- `docs/design/TDD-PROCESS-PIPELINE.md` - Original design (now invalid)
- `docs/requirements/PRD-PROCESS-PIPELINE.md` - Original requirements
- `docs/decisions/ADR-0096-processtype-expansion.md`
- `docs/decisions/ADR-0097-processsection-state-machine.md`
- `docs/decisions/ADR-0098-dual-membership-model.md`
- `docs/decisions/ADR-0099-seeder-pattern.md` (implied)
- `docs/decisions/ADR-0100-state-transition-composition.md`
- `docs/analysis/DISCOVERY-PROCESS-PIPELINE.md`

---

## Appendix: Line Count Summary

| File | Type | Lines | Action |
|------|------|-------|--------|
| process_registry.py | Source | 299 | DELETE |
| test_process_registry.py | Test | 393 | DELETE |
| process.py | Source | ~170 | MODIFY |
| seeder.py | Source | ~50 | MODIFY |
| detection.py | Source | ~40 | MODIFY |
| __init__.py | Source | ~10 | MODIFY |
| test_process.py | Test | ~220 | MODIFY |
| test_detection.py | Test | ~130 | MODIFY |
| **Total** | | **~1,312** | |

---

*Generated: 2025-12-17*
*Initiative: Process Pipeline Cleanup*
*Phase: Discovery*
