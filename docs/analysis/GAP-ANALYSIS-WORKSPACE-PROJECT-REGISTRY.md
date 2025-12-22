# Gap Analysis: Workspace Project Registry

**Date**: 2025-12-18
**Author**: Requirements Analyst
**Status**: Discovery Complete
**Purpose**: Inform Prompt 0 for WorkspaceProjectRegistry initiative

---

## Executive Summary

The autom8_asana SDK currently relies on **static, hardcoded project GIDs** for entity type detection. This approach works for known entity types but **completely fails for pipeline projects and any dynamically created projects**. The pipeline automation demo revealed that Process entities cannot be detected because their pipeline projects (Sales, Onboarding, etc.) are not registered in the ProjectTypeRegistry.

**Critical finding**: There is no mechanism to dynamically discover projects within a workspace at runtime. This is a blocking gap for pipeline automation and any multi-tenant usage of the SDK.

---

## 1. Current State Analysis

### 1.1 Project Client (`/src/autom8_asana/clients/projects.py`)

**Capabilities**:
- `list_async(workspace=..., team=..., archived=...)` - Returns `PageIterator[Project]` for workspace-scoped project listing
- `get_async(project_gid)` - Fetch single project by GID
- Standard CRUD operations (create, update, delete)
- Membership operations (add/remove members)
- Section listing via `get_sections_async()`

**Key observation**: The `list_async()` method **does support workspace-level project listing**. The infrastructure exists, but it is not being used for discovery or registry population.

```python
# Existing capability (line 433-479)
def list_async(
    self,
    *,
    workspace: str | None = None,  # <-- Workspace filtering supported
    team: str | None = None,
    archived: bool | None = None,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Project]:
```

### 1.2 Name Resolver (`/src/autom8_asana/clients/name_resolver.py`)

**Capabilities**:
- `resolve_project_async(name_or_gid, workspace_gid)` - Resolves project name to GID
- Per-SaveSession caching (cleared on context exit)
- Polymorphic input handling (GID passthrough if 20+ chars)
- Case-insensitive matching with whitespace tolerance
- Suggestion generation on NameNotFoundError

**How it works** (lines 160-212):
1. If input looks like GID, return as-is
2. Check per-session cache
3. Fetch ALL projects in workspace via `client.projects.list_async(workspace=workspace_gid)`
4. Find exact match (case-insensitive)
5. Cache and return GID

**Limitations**:
- **Cache is session-scoped** - Cleared when SaveSession exits
- **No persistent registry integration** - Results are not fed into ProjectTypeRegistry
- **Requires explicit workspace_gid parameter** - No default workspace awareness
- **Read-only** - Does not populate any registry for detection

### 1.3 Project Type Registry (`/src/autom8_asana/models/business/registry.py`)

**Purpose**: Maps project GIDs to EntityType for O(1) detection lookup.

**Current registration mechanism**:
1. Entity classes define `PRIMARY_PROJECT_GID: ClassVar[str | None]`
2. `__init_subclass__` hook calls `_register_entity_with_registry(cls)`
3. Environment variable override: `ASANA_PROJECT_{ENTITY_TYPE}` takes precedence

**Example entity GID mappings**:
```python
# From business entity files:
Business.PRIMARY_PROJECT_GID = "1200653012566782"
Unit.PRIMARY_PROJECT_GID = "1201081073731555"
Offer.PRIMARY_PROJECT_GID = "1143843662099250"
ContactHolder.PRIMARY_PROJECT_GID = "1202653012566783"  # (example)
DNAHolder.PRIMARY_PROJECT_GID = "1167650840134033"
ReconciliationHolder.PRIMARY_PROJECT_GID = "1203404998225231"
AssetEditHolder.PRIMARY_PROJECT_GID = "1203992664400125"
VideographyHolder.PRIMARY_PROJECT_GID = "1207984018149338"
OfferHolder.PRIMARY_PROJECT_GID = "1210679066066870"

# Entities WITHOUT dedicated projects (None):
Process.PRIMARY_PROJECT_GID = None  # <-- CRITICAL GAP
ProcessHolder.PRIMARY_PROJECT_GID = None
UnitHolder.PRIMARY_PROJECT_GID = None
LocationHolder.PRIMARY_PROJECT_GID = None
```

**Critical observation**: Process and ProcessHolder have `PRIMARY_PROJECT_GID = None` because they can exist in **multiple different pipeline projects** (Sales, Onboarding, etc.).

### 1.4 Detection System (`/src/autom8_asana/models/business/detection.py`)

**Detection Tiers**:
1. **Tier 1 - Project membership** (O(1), no API, deterministic) - Uses ProjectTypeRegistry
2. **Tier 2 - Name patterns** (string ops, no API) - Case-insensitive contains matching
3. **Tier 3 - Parent inference** (logic only) - Infer child type from parent
4. **Tier 4 - Structure inspection** (async, API call) - Examine subtask names
5. **Tier 5 - Unknown fallback** (needs_healing=True)

**Why Process entities fail Tier 1** (lines 445-511):
```python
def _detect_tier1_project_membership(task: Task) -> DetectionResult | None:
    # Get first project GID from memberships
    project_gid = task.memberships[0].get("project", {}).get("gid")

    # Registry lookup - FAILS for pipeline projects
    registry = get_registry()
    entity_type = registry.lookup(project_gid)  # Returns None for unknown projects

    if entity_type is None:
        return None  # Falls through to Tier 2+
```

Process entities in pipeline projects (e.g., "Sales Pipeline" project) fail because:
1. The pipeline project GID is not in the registry
2. Process has no static PRIMARY_PROJECT_GID (it's None)
3. Detection falls through to Tier 2 (name patterns), which doesn't match "Process"

### 1.5 Configuration (`/src/autom8_asana/config.py`)

**Current state**:
- `AsanaConfig` - Main configuration dataclass
- `AutomationConfig.pipeline_templates: dict[str, str]` - ProcessType to project GID mapping

**Workspace handling in AsanaClient** (`/src/autom8_asana/client.py`):
- `workspace_gid: str | None` parameter on init
- Auto-detection if token provided and exactly one workspace exists
- Stored as `self.default_workspace_gid`

**Gap**: No mechanism to use `default_workspace_gid` for project discovery.

### 1.6 Related Patterns

**Custom Fields Discovery** (`/src/autom8_asana/clients/custom_fields.py`):
- `list_for_workspace_async(workspace_gid)` - Lists all custom fields in workspace
- Returns `PageIterator[CustomField]`
- Pattern: Workspace-scoped listing with pagination

**Sections Client** (`/src/autom8_asana/clients/sections.py`):
- `list_for_project_async(project_gid)` - Lists sections in a project
- Pattern: Project-scoped listing

Both demonstrate the **workspace/project-scoped listing pattern** that should inform WorkspaceProjectRegistry.

---

## 2. Gap Identification

### 2.1 Primary Gaps

| Gap | Impact | Severity |
|-----|--------|----------|
| **G1: No dynamic project discovery** | Pipeline projects not in registry | **CRITICAL** |
| **G2: Process entities fail detection** | Pipeline automation blocked | **CRITICAL** |
| **G3: No name-to-GID mapping at runtime** | Cannot resolve "Sales Pipeline" to GID | HIGH |
| **G4: Static registry only** | Cannot adapt to new projects | HIGH |
| **G5: No workspace-default integration** | Must pass workspace_gid everywhere | MEDIUM |

### 2.2 Detailed Gap Analysis

#### G1: No Dynamic Project Discovery

**Current state**: ProjectTypeRegistry is populated only at import time via `__init_subclass__`.

**Required**: Ability to:
1. Fetch all projects in workspace
2. Categorize them (entity project, pipeline project, other)
3. Register them in the type registry
4. Update when projects are created/renamed

**Asana API support**:
```
GET /workspaces/{workspace_gid}/projects
GET /projects?workspace={workspace_gid}
```

Both are supported by existing `ProjectsClient.list_async(workspace=...)`.

#### G2: Process Entities Fail Detection

**Root cause**: Process entities exist in pipeline projects (Sales, Onboarding, etc.) that:
1. Are not registered in ProjectTypeRegistry
2. Cannot be statically mapped (ProcessType is runtime-determined)

**Example failure flow**:
```
Task in "Sales Pipeline" project
    -> Tier 1: lookup("sales_pipeline_gid") = None (not registered)
    -> Tier 2: "Task Name" doesn't contain "processes" pattern
    -> Tier 3: No parent_type provided
    -> Tier 5: Returns UNKNOWN, needs_healing=True
```

**Required**: Register pipeline projects with EntityType.PROCESS mapping.

#### G3: No Name-to-GID Mapping at Runtime

**Current state**: `NameResolver.resolve_project_async()` fetches projects but:
1. Cache is session-scoped (lost after SaveSession)
2. Does not feed into ProjectTypeRegistry
3. Does not categorize projects by type

**Required**: Persistent mapping from project name to:
1. Project GID
2. Project category (entity, pipeline, other)
3. Associated EntityType (if applicable)

#### G4: Static Registry Only

**Current state**: Registry populated at import time, never updated.

**Required**:
1. Discovery phase at client init or on-demand
2. Refresh mechanism for workspace changes
3. Runtime registration API

#### G5: No Workspace-Default Integration

**Current state**: `NameResolver.resolve_project_async()` requires explicit `workspace_gid`.

**Required**: Use `AsanaClient.default_workspace_gid` as default.

---

## 3. Impact on Pipeline Automation

### 3.1 Current Pipeline Flow (Broken)

```
Process task created
    -> Automation trigger fires
    -> Need to identify task as Process
    -> detect_entity_type() called
    -> Tier 1: Project GID not in registry -> None
    -> Tier 2: Name doesn't match "processes" -> None
    -> Returns UNKNOWN
    -> Automation rule doesn't match
    -> Pipeline conversion FAILS
```

### 3.2 Required Pipeline Flow

```
Client initialization
    -> WorkspaceProjectRegistry.discover_async(workspace_gid)
    -> Fetches all projects in workspace
    -> Categorizes: "Sales Pipeline" -> (EntityType.PROCESS, ProcessType.SALES)
    -> Registers all pipeline projects

Process task created
    -> detect_entity_type() called
    -> Tier 1: lookup("sales_pipeline_gid") = EntityType.PROCESS
    -> Returns DetectionResult(entity_type=PROCESS, ...)
    -> Automation rule matches
    -> Pipeline conversion SUCCEEDS
```

### 3.3 AutomationConfig Integration

Current `AutomationConfig.pipeline_templates`:
```python
pipeline_templates: dict[str, str] = field(default_factory=dict)
# Example: {"sales": "1234567890123", "onboarding": "9876543210987"}
```

**Gap**: This requires hardcoded GIDs. Should be discoverable by name.

---

## 4. Recommended Approach

### 4.1 WorkspaceProjectRegistry Component

**Responsibilities**:
1. Discover all projects in a workspace
2. Categorize projects (entity, pipeline, other)
3. Maintain name-to-GID mapping
4. Integrate with ProjectTypeRegistry for detection
5. Support refresh/update operations

**Key design considerations**:
1. **Caching strategy**: Instance-level cache vs global singleton
2. **Discovery trigger**: On-demand vs eager at client init
3. **Refresh policy**: Manual, TTL-based, or event-driven
4. **Integration point**: How does it feed ProjectTypeRegistry?

### 4.2 Project Categorization Strategy

Projects should be categorized as:

| Category | Identification Method | Registry Action |
|----------|----------------------|-----------------|
| **Entity projects** | Matches PRIMARY_PROJECT_GID | Already registered |
| **Pipeline projects** | Name contains ProcessType value | Register as EntityType.PROCESS |
| **Holder projects** | Name ends with "Holder" pattern | Register as EntityType.*_HOLDER |
| **Other** | Default | Don't register |

### 4.3 Integration Points

1. **AsanaClient init**: Optional eager discovery
2. **SaveSession**: Access to registry for detection
3. **NameResolver**: Uses WorkspaceProjectRegistry for resolution
4. **AutomationConfig**: Pipeline templates resolved by name

---

## 5. Key Requirements for WorkspaceProjectRegistry

### 5.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Discover all projects in a workspace via API | MUST |
| FR-02 | Map project names to GIDs | MUST |
| FR-03 | Categorize projects (entity, pipeline, other) | MUST |
| FR-04 | Register pipeline projects with EntityType.PROCESS | MUST |
| FR-05 | Integrate with existing ProjectTypeRegistry | MUST |
| FR-06 | Support case-insensitive name matching | SHOULD |
| FR-07 | Support project refresh on-demand | SHOULD |
| FR-08 | Use default_workspace_gid from client | SHOULD |
| FR-09 | Cache discovered projects | SHOULD |
| FR-10 | Support multiple workspaces | COULD |

### 5.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Discovery should complete in < 5 seconds for typical workspace | Performance |
| NFR-02 | Name resolution should be O(1) after discovery | Performance |
| NFR-03 | Registry should not duplicate existing entity project mappings | Correctness |
| NFR-04 | Detection of Process entities in pipeline projects should succeed | Correctness |

### 5.3 Acceptance Criteria

1. Process task in "Sales Pipeline" project detected as EntityType.PROCESS
2. Pipeline automation rule triggers correctly for detected Process
3. Project name resolution works without hardcoded GIDs
4. Existing entity detection (Business, Unit, Offer, etc.) unaffected

---

## 6. Open Questions for PRD Phase

### 6.1 Architecture Questions

1. **Singleton vs instance?** Should WorkspaceProjectRegistry be a module-level singleton like ProjectTypeRegistry, or an instance per AsanaClient?

2. **Discovery timing?** Should discovery happen:
   - At AsanaClient init (eager)
   - On first detection call (lazy)
   - Explicitly via method call (manual)

3. **Cache invalidation?** How should the registry handle:
   - New projects created during session
   - Renamed projects
   - Deleted projects

4. **Multi-workspace support?** Should the registry support multiple workspaces, or is single-workspace sufficient for V1?

### 6.2 Integration Questions

5. **ProjectTypeRegistry relationship?** Should WorkspaceProjectRegistry:
   - Extend ProjectTypeRegistry
   - Compose with ProjectTypeRegistry
   - Replace ProjectTypeRegistry

6. **NameResolver integration?** Should NameResolver use WorkspaceProjectRegistry, or should they remain separate?

7. **AutomationConfig impact?** Should `pipeline_templates` accept names instead of GIDs after this change?

### 6.3 Implementation Questions

8. **Project categorization rules?** What rules determine if a project is:
   - An entity project (should match static PRIMARY_PROJECT_GID)
   - A pipeline project (contains ProcessType value?)
   - A holder project (ends with known pattern?)

9. **ProcessType derivation?** How do we determine ProcessType from project name?
   - Exact match required? ("Sales" in name)
   - Case sensitivity?
   - Word boundaries?

10. **Backward compatibility?** How do we ensure existing hardcoded GIDs continue to work?

---

## 7. Appendix: Relevant File Locations

| Component | Path |
|-----------|------|
| ProjectsClient | `/src/autom8_asana/clients/projects.py` |
| NameResolver | `/src/autom8_asana/clients/name_resolver.py` |
| ProjectTypeRegistry | `/src/autom8_asana/models/business/registry.py` |
| Detection System | `/src/autom8_asana/models/business/detection.py` |
| AsanaClient | `/src/autom8_asana/client.py` |
| AsanaConfig | `/src/autom8_asana/config.py` |
| AutomationConfig | `/src/autom8_asana/automation/config.py` |
| Business Entity | `/src/autom8_asana/models/business/business.py` |
| Process Entity | `/src/autom8_asana/models/business/process.py` |
| Unit Entity | `/src/autom8_asana/models/business/unit.py` |
| Offer Entity | `/src/autom8_asana/models/business/offer.py` |

---

## 8. Summary and Next Steps

### Key Findings

1. **Infrastructure exists** - `ProjectsClient.list_async(workspace=...)` can discover projects
2. **Registry is static** - ProjectTypeRegistry only populated at import time
3. **Process detection fails** - Pipeline projects not in registry
4. **NameResolver is isolated** - Results not integrated with detection system

### Recommended Actions

1. **Create Prompt 0** defining the WorkspaceProjectRegistry initiative scope
2. **Design decision needed** on registry architecture (singleton vs instance)
3. **Design decision needed** on discovery timing (eager vs lazy)
4. **PRD should specify** project categorization rules

### Success Criteria for Initiative

The WorkspaceProjectRegistry initiative will be successful when:
1. Process tasks in pipeline projects are correctly detected as EntityType.PROCESS
2. Pipeline automation rules trigger correctly
3. Project names can be resolved to GIDs without hardcoding
4. Existing entity detection remains unchanged
