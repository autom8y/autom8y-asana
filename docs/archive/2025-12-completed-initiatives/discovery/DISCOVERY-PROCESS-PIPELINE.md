# Discovery: Process Pipeline Initiative

> **Status**: Complete
> **Date**: 2025-12-17
> **Session**: 1 of 7
> **Agent**: Requirements Analyst
> **Purpose**: Analyze current implementation and discover inputs for PRD-PROCESS-PIPELINE

---

## Executive Summary

This discovery analyzed the current Process implementation to identify extension points for modeling Process entities as first-class pipeline events. Key findings:

1. **Process/ProcessHolder are fully implemented** with 8 custom fields and standard navigation
2. **ProcessType enum is stub** with only GENERIC - ready for expansion
3. **ProjectTypeRegistry pattern exists** and can be extended for ProcessProjectRegistry
4. **Detection system supports process entities** but lacks ProcessType-specific detection
5. **SaveSession provides all needed operations** (move_to_section, add_to_project)
6. **No existing seeding patterns** - BusinessSeeder will be new functionality
7. **Task.memberships structure documented** - key for pipeline_state extraction

---

## 1. Current Implementation Analysis

### 1.1 Process Entity

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py`

| Component | Lines | Status |
|-----------|-------|--------|
| `ProcessType` enum | 35-65 | Stub - only GENERIC |
| `Process` class | 67-189 | Complete with 8 fields |
| `ProcessHolder` class | 190-266 | Complete |

**Custom Fields (8 total)**:
```python
# Text fields (4) - Lines 150-161
started_at = TextField()
process_completed_at = TextField(field_name="Process Completed At")
process_notes = TextField(field_name="Process Notes")
process_due_date = TextField(field_name="Due Date")

# Enum fields (3) - Lines 155-157
status = EnumField()
priority = EnumField()
vertical = EnumField()

# People field (1) - Line 163
assigned_to = PeopleField()
```

**Navigation Pattern (Lines 103-131)**:
- `process_holder` - HolderRef descriptor to parent
- `unit` - Property navigating via `_process_holder._unit`
- `business` - Property navigating via `unit.business`

**Key Constraint (Lines 91-92)**:
```python
PRIMARY_PROJECT_GID: ClassVar[str | None] = None
```
Process has no dedicated project in current implementation. This is the **key extension point** for ProcessProjectRegistry.

### 1.2 ProcessType Enum Status

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py` (Lines 35-65)

**Current State**:
```python
class ProcessType(str, Enum):
    GENERIC = "generic"
    # Phase 2 placeholders in comments only
```

**Commented Placeholders** (not stakeholder-aligned):
- AUDIT, BUILD, CREATIVE, DELIVERY, ONBOARDING, OPTIMIZATION, QA, REPORTING, RESEARCH, SETUP, STRATEGY, SUPPORT, TRAINING

**Stakeholder-Required Types** (from Prompt 0):
- SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION

**Gap**: Enum needs expansion with stakeholder-aligned types.

### 1.3 ProcessHolder Implementation

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py` (Lines 190-266)

**Follows standard holder pattern**:
- `CHILD_TYPE = Process`
- `PARENT_REF_NAME = "_process_holder"`
- `CHILDREN_ATTR = "_processes"`
- `_populate_children()` with intermediate `_unit` ref propagation

**Key Detail**: ProcessHolder has `PRIMARY_PROJECT_GID = None` (Line 203) - children of Unit hierarchy only.

### 1.4 process_type Property

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py` (Lines 167-188)

```python
@property
def process_type(self) -> ProcessType:
    # Phase 1: All processes are generic
    return ProcessType.GENERIC
```

**Extension Point**: Property is ready for detection logic. Comments indicate future detection from custom field or name pattern.

---

## 2. Detection System Integration Points

### 2.1 EntityType Enum

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection.py` (Lines 66-107)

**Existing Types**:
```python
EntityType.PROCESS = "process"
EntityType.PROCESS_HOLDER = "process_holder"
```

**Gap**: No ProcessType-specific EntityTypes (e.g., SALES_PROCESS, ONBOARDING_PROCESS).

### 2.2 EntityTypeInfo Configuration

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection.py`

**ProcessHolder (Lines 274-282)**:
```python
EntityType.PROCESS_HOLDER: EntityTypeInfo(
    entity_type=EntityType.PROCESS_HOLDER,
    name_pattern="processes",
    display_name="Processes",
    emoji="gear",
    holder_attr="_process_holder",
    child_type=EntityType.PROCESS,
    has_project=False,  # ProcessHolder has no dedicated project
)
```

**Process (Lines 300-304)**:
```python
EntityType.PROCESS: EntityTypeInfo(
    entity_type=EntityType.PROCESS,
    display_name="Process",
    has_project=True,  # Process entities CAN have dedicated projects
)
```

**Critical Finding**: `has_project=True` for Process but no `PRIMARY_PROJECT_GID`. This is the extension point for pipeline projects.

### 2.3 Detection Tiers

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection.py`

| Tier | Method | Confidence | API Call | Lines |
|------|--------|------------|----------|-------|
| 1 | Project membership | 1.0 | No | 445-515 |
| 2 | Name pattern | 0.6 | No | 518-559 |
| 3 | Parent inference | 0.8 | No | 562-606 |
| 4 | Structure inspection | 0.9 | Yes | 609-677 |
| 5 | Unknown fallback | 0.0 | No | 680-703 |

**Extension Point for ProcessType Detection**:
- **Tier 1**: Add pipeline project GIDs to registry, detect ProcessType from project membership
- Project membership check (Lines 466-501) already extracts project_gid from `task.memberships[0]`

---

## 3. ProjectTypeRegistry Pattern

### 3.1 Registry Implementation

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/registry.py`

**Pattern Summary**:
- Singleton with `get_registry()` (Line 194)
- O(1) lookup via `_gid_to_type` dict (Line 132)
- Auto-registration via `__init_subclass__` hook (Lines 245-311)
- Environment variable override pattern (Lines 273-278)

**Environment Variable Pattern** (Lines 273-278):
```python
env_var = f"ASANA_PROJECT_{entity_type.name}"
env_value = os.environ.get(env_var, "")
```

**Example**: `ASANA_PROJECT_BUSINESS` overrides `Business.PRIMARY_PROJECT_GID`

### 3.2 Applicability to ProcessProjectRegistry

The existing pattern can be extended:
1. Create `ProcessProjectRegistry` following same singleton pattern
2. Map `ProcessType` -> `project_gid` (analogous to `EntityType` -> `project_gid`)
3. Use environment variable override: `ASANA_PROCESS_PROJECT_SALES`, etc.
4. Auto-registration via `__init_subclass__` on Process subclasses (if using subclasses)

**Alternative**: Single `ProcessProjectRegistry` configuration dict without subclasses:
```python
PROCESS_PROJECT_MAPPING = {
    ProcessType.SALES: os.environ.get("ASANA_PROCESS_PROJECT_SALES"),
    ProcessType.ONBOARDING: os.environ.get("ASANA_PROCESS_PROJECT_ONBOARDING"),
    # ...
}
```

---

## 4. SaveSession Operations Analysis

### 4.1 move_to_section()

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (Lines 1121-1195)

```python
def move_to_section(
    self,
    task: AsanaResource,
    section: AsanaResource | str,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession:
```

**Capabilities**:
- Accepts Section object or section GID string
- Optional positioning (insert_before/insert_after)
- Queued as `ActionOperation` executed at commit time
- Returns self for fluent chaining

**Usage for State Transitions**:
```python
session.move_to_section(process, converted_section_gid)
await session.commit_async()
```

### 4.2 add_to_project()

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (Lines 906-979)

```python
def add_to_project(
    self,
    task: AsanaResource,
    project: AsanaResource | str,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession:
```

**Capabilities**:
- Accepts Project object or project GID string
- Optional positioning
- Queued as `ActionOperation`
- Returns self for fluent chaining

**Usage for Dual Membership**:
```python
# Add process to hierarchy (as subtask - implicit)
# Add process to pipeline project (explicit)
session.add_to_project(process, sales_pipeline_project_gid)
await session.commit_async()
```

### 4.3 ActionType Enum

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py` (Lines 435-470)

```python
class ActionType(str, Enum):
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    MOVE_TO_SECTION = "move_to_section"
    # ... plus tag, dependency, follower operations
```

**Finding**: All needed action types exist for pipeline operations.

---

## 5. Task Memberships Structure

### 5.1 Task.memberships Attribute

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` (Line 71)

```python
memberships: list[dict[str, Any]] | None = None  # Keep as dict (complex structure)
```

**Structure per Asana API**:
```python
memberships = [
    {
        "project": {"gid": "1234567890", "name": "Sales Pipeline"},
        "section": {"gid": "9876543210", "name": "Opportunity"}
    },
    {
        "project": {"gid": "1111111111", "name": "Parent Project"},
        "section": {"gid": "2222222222", "name": "Some Section"}
    }
]
```

### 5.2 Detection Usage Pattern

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection.py` (Lines 466-501)

```python
# Check for project memberships
if not task.memberships:
    return None

# Get first project GID from memberships
first_membership = task.memberships[0]
project_data = first_membership.get("project")
project_gid = project_data.get("gid")
```

### 5.3 Implications for pipeline_state

**To extract section from memberships**:
```python
def get_section_from_project(memberships, project_gid):
    for m in memberships or []:
        if m.get("project", {}).get("gid") == project_gid:
            return m.get("section", {}).get("name")
    return None
```

**Key Insight**: Section extraction requires knowing which project membership to check (pipeline project, not hierarchy project).

---

## 6. HolderFactory Pattern

### 6.1 Pattern Overview

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/holder_factory.py`

**Purpose**: Reduce boilerplate via `__init_subclass__` pattern.

**Usage Example**:
```python
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    pass
```

**Generates**:
- CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR ClassVars
- children and business properties
- _populate_children method with dynamic import

**Relevance to ProcessProjectRegistry**:
- Same `__init_subclass__` pattern can be used for auto-registration
- Lines 199-202 show registry integration:
```python
from autom8_asana.models.business.registry import _register_entity_with_registry
_register_entity_with_registry(cls)
```

---

## 7. Webhook Infrastructure

### 7.1 WebhooksClient

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py`

**Available Operations**:
- `get_async()` / `get()` - Get webhook by GID
- `create_async()` / `create()` - Create webhook on resource
- Signature verification via HMAC-SHA256

### 7.2 Webhook Model

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/webhook.py`

**Attributes**:
- `target` - URL receiving events
- `resource` - NameGid of watched resource
- `filters` - List of WebhookFilter (resource_type, action, fields)

### 7.3 Gap Analysis

**Not Currently Supported**:
- Webhook event parsing (raw JSON -> typed event)
- Section change event identification
- Process-specific event helpers

**Recommendation**: Webhook helpers are "Should Have" per Prompt 0, defer to Phase 3.

---

## 8. Section Model and Client

### 8.1 Section Model

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/section.py`

```python
class Section(AsanaResource):
    name: str | None = None
    project: NameGid | None = None
    created_at: str | None = None
```

**No semantic section type** - just name and project reference.

### 8.2 SectionsClient

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`

**Available Operations**:
- `get()` / `get_async()` - Get section by GID
- `create()` / `create_async()` - Create section in project
- `list_for_project()` / `list_for_project_async()` - List sections

### 8.3 Implications for ProcessSection

**Section name -> ProcessSection mapping** will be SDK responsibility:
- Match section names case-insensitively
- Map "Opportunity" -> ProcessSection.OPPORTUNITY
- Allow GID override for edge cases

---

## 9. Existing Test Coverage

### 9.1 Process Tests

**File**: `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/business/test_process.py`

| Test Class | Focus | Count |
|------------|-------|-------|
| TestProcess | Basic construction | 1 |
| TestProcessType | GENERIC enum | 2 |
| TestProcessNavigation | Holder/unit/business nav | 4 |
| TestProcessCustomFields | 8 field accessors | 10 |
| TestProcessHolder | Holder pattern | 6 |
| TestProcessTypeEnum | Enum extensibility | 2 |

**Key Test (Lines 278-282)**:
```python
def test_process_type_enum_member_count(self) -> None:
    """Phase 1 has only GENERIC type."""
    members = list(ProcessType)
    assert len(members) == 1  # WILL BREAK when we add types
```

**Backward Compatibility Requirement**: This test explicitly expects only GENERIC. Must update when expanding enum.

---

## 10. Open Questions Status

### 10.1 Resolved (From Codebase Analysis)

| Question | Answer | Source |
|----------|--------|--------|
| ProcessType extension point? | Expand enum, update process_type property | process.py:35-65, 167-188 |
| ProjectTypeRegistry pattern? | Singleton with __init_subclass__, env var override | registry.py |
| SaveSession operations? | move_to_section(), add_to_project() available | session.py:906-1195 |
| Memberships structure? | list[dict] with project.gid and section.name | task.py:71, detection.py:466-501 |
| Section model? | Basic - name, project ref, no semantic type | section.py |

### 10.2 Unresolved (Requires User Input)

| Question | Impact | Recommendation |
|----------|--------|----------------|
| **Q1: Process Project GIDs** | Cannot configure registry without GIDs | User provides GIDs OR document env var pattern for runtime config |
| **Q2: Section name consistency** | Section mapping depends on naming | Assume standard names, allow override |
| **Q3: Legacy integration access** | Cannot validate seeding pattern | Design from requirements, validate later |
| **Q4: BusinessSeeder scope** | Factory interface design | Recommend find-or-create pattern |

---

## 11. Risk Register

### 11.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Section names vary by project** | Medium | High | Name matching with fuzzy logic, GID override |
| **Dual membership detection ambiguity** | Medium | Medium | Check hierarchy project first, then pipeline |
| **ProcessType from project vs custom field** | Low | Medium | Primary: project membership, fallback: custom field |
| **Backward compatibility in tests** | Certain | Low | Update test_process_type_enum_member_count |

### 11.2 Assumptions to Validate

| Assumption | Validation Approach |
|------------|---------------------|
| All pipeline projects have same 7 sections | Audit process projects (user provides GIDs) |
| Section membership is single per project | Test with dual-membership task |
| Tasks can belong to multiple projects | Verify Asana API behavior |
| Section name matching sufficient | Test with actual section names |

---

## 12. Inputs for PRD Session

### 12.1 Facts to Include

1. **ProcessType enum expansion**: 6 new types (SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION) + preserve GENERIC
2. **ProcessSection enum**: 7 values (OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT, OTHER)
3. **ProcessProjectRegistry**: Map ProcessType -> project GID, env var override pattern
4. **pipeline_state property**: Extract from memberships using ProcessProjectRegistry to identify correct project
5. **Dual membership creation**: Use SaveSession.add_to_project() after entity creation
6. **State transitions**: Use SaveSession.move_to_section() with section GID lookup
7. **BusinessSeeder factory**: New module, async-first, find-or-create pattern

### 12.2 Gaps Requiring Requirements Decisions

| Gap | Decision Needed |
|-----|-----------------|
| ProcessType detection: project vs custom field priority | Which is primary? |
| Section name matching: exact vs fuzzy | How flexible? |
| BusinessSeeder: create Unit or reuse existing? | Scope of seeding |
| process_type setter: should it change project membership? | Mutability semantics |
| Multi-process-project membership: which takes precedence? | First match? Most specific? |

### 12.3 Backward Compatibility Constraints

1. `ProcessType.GENERIC` must remain
2. `process_type` property must return valid ProcessType (GENERIC as fallback)
3. `ProcessHolder` pattern unchanged
4. All existing Process tests must pass (update enum count test)
5. `PRIMARY_PROJECT_GID = None` remains valid for generic processes

---

## Appendix A: Key File References

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/autom8_asana/models/business/process.py` | Process, ProcessHolder, ProcessType | 35-266 |
| `src/autom8_asana/models/business/registry.py` | ProjectTypeRegistry pattern | 29-201 |
| `src/autom8_asana/models/business/detection.py` | EntityType, detection tiers | 66-806 |
| `src/autom8_asana/persistence/session.py` | SaveSession operations | 906-1195 |
| `src/autom8_asana/models/task.py` | Task.memberships | 71 |
| `src/autom8_asana/models/section.py` | Section model | 24-51 |
| `tests/unit/models/business/test_process.py` | Process tests | 1-283 |

---

## Appendix B: Code Snippets for Reference

### B.1 ProcessType Expansion (Recommended)

```python
class ProcessType(str, Enum):
    """Process types representing workflow stages."""

    # Pipeline types (stakeholder-aligned)
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"

    # Fallback
    GENERIC = "generic"
```

### B.2 ProcessSection Enum (Recommended)

```python
class ProcessSection(str, Enum):
    """Standard sections in process pipeline projects."""

    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"
```

### B.3 pipeline_state Property Pattern (Recommended)

```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """Get current pipeline state from section membership."""
    if not self.memberships:
        return None

    # Get pipeline project GID from registry
    registry = get_process_project_registry()
    pipeline_gid = registry.get_project_gid(self.process_type)
    if not pipeline_gid:
        return None

    # Find section in pipeline project membership
    for membership in self.memberships:
        if membership.get("project", {}).get("gid") == pipeline_gid:
            section_name = membership.get("section", {}).get("name", "").lower()
            return ProcessSection.from_name(section_name)

    return None
```

---

*End of discovery document.*
