# PRD: Workspace Project Registry

## Metadata

- **PRD ID**: PRD-WORKSPACE-PROJECT-REGISTRY
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **Stakeholders**: SDK consumers, Pipeline automation, Detection system, Demo scripts
- **Related PRDs**: PRD-DETECTION (Entity Detection System), PRD-AUTOMATION-LAYER
- **Related ADRs**: ADR-0093 (Project-to-EntityType Registry Pattern), ADR-0094 (Detection Fallback Chain)
- **Input Documents**: PROMPT-0-WORKSPACE-PROJECT-REGISTRY, GAP-ANALYSIS-WORKSPACE-PROJECT-REGISTRY

---

## Problem Statement

### Current State

The autom8_asana SDK uses a **static ProjectTypeRegistry** to map Asana project GIDs to EntityTypes for O(1) detection (Tier 1). This registry is populated at import time via `__init_subclass__` hooks using hardcoded `PRIMARY_PROJECT_GID` class attributes.

**This approach completely fails for Process entities in pipeline projects.**

### Why It Fails

| Entity Type | Project Assignment | Registry State | Detection Result |
|-------------|-------------------|----------------|------------------|
| Business | Single dedicated project | Registered at import | Tier 1 success |
| Contact | Single dedicated project | Registered at import | Tier 1 success |
| Unit | Single dedicated project | Registered at import | Tier 1 success |
| Offer | Single dedicated project | Registered at import | Tier 1 success |
| **Process** | **Multiple pipeline projects** | **Not registered** | **Tier 5 UNKNOWN** |

Process entities live in pipeline projects (Sales, Onboarding, Retention, etc.) that:
1. Cannot be statically mapped - there are 7+ pipeline projects, each for a different ProcessType
2. Are not registered because `Process.PRIMARY_PROJECT_GID = None`
3. Have GIDs that vary between workspaces/deployments

### Detection Failure Flow

```
Task in "Sales" pipeline project
    -> Tier 1: lookup("sales_project_gid") = None  # Not in static registry
    -> Tier 2: "Task Name" doesn't match holder patterns
    -> Tier 3: No parent_type context
    -> Tier 5: Returns EntityType.UNKNOWN, needs_healing=True
```

### Who Is Affected

- **Pipeline automation**: Cannot trigger conversion rules because Process not detected
- **Demo scripts**: Require hardcoded GIDs that break in different workspaces
- **Multi-tenant usage**: Each workspace has different project GIDs
- **SDK adopters**: Must manually configure GIDs per environment

### Impact of Not Solving

- **Pipeline automation is blocked**: PipelineConversionRule cannot identify Process entities
- **Portability broken**: SDK cannot work across workspaces without manual GID configuration
- **Developer experience degraded**: Every new workspace requires configuration updates
- **Detection system incomplete**: Tier 1 detection is only partial

### Root Cause

The gap analysis identified that **infrastructure exists but is disconnected**:

1. `ProjectsClient.list_async(workspace=...)` can fetch all projects (infrastructure exists)
2. `NameResolver` caches project name-to-GID mappings per session (partial solution)
3. `ProjectTypeRegistry` is static-only, populated at import time (the blocker)
4. No mechanism connects runtime project discovery to the detection registry

---

## Goals and Success Metrics

### Goals

1. **Enable dynamic project discovery**: Fetch all workspace projects at runtime
2. **Register pipeline projects for detection**: Pipeline project GIDs map to EntityType.PROCESS
3. **Maintain backward compatibility**: Existing static PRIMARY_PROJECT_GID must continue to work
4. **Improve developer experience**: No hardcoded GIDs required for pipeline automation
5. **Support name-based project resolution**: Look up projects by name, not GID

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Process detection in pipeline projects | 0% | 100% | Integration test |
| Hardcoded GIDs in demo scripts | Required | Zero | Code inspection |
| Pipeline automation trigger rate | 0% | 100% | Demo script success |
| Existing entity detection (Business, Unit, etc.) | Working | Unchanged | Regression tests |
| Name-to-GID resolution | Per-request API | O(1) cached | Benchmark test |
| Discovery time (typical workspace) | N/A | <3 seconds | Performance test |

---

## Scope

### In Scope

**Must Have (P0)**:
- WorkspaceProjectRegistry component for runtime project discovery
- Dynamic pipeline project registration in ProjectTypeRegistry
- Process entity detection via Tier 1 for discovered pipeline projects
- Name-to-GID mapping with O(1) lookup after discovery
- Backward compatibility with static PRIMARY_PROJECT_GID registrations
- Integration with AsanaClient.default_workspace_gid

**Should Have (P1)**:
- Case-insensitive project name matching
- On-demand refresh capability for project list
- ProcessType derivation from project name (e.g., "Sales" -> ProcessType.SALES)
- Session-scoped caching of discovered projects

**Could Have (P2)**:
- Environment variable overrides for pipeline project mappings
- Custom override mechanism for edge cases in pipeline identification

### Out of Scope

| Item | Rationale |
|------|-----------|
| Multi-workspace support | Single workspace is sufficient for V1; defer to Phase 2 |
| Project creation/deletion handling | Discovery is read-only; mutations are separate concern |
| Real-time project change sync | Refresh-on-demand is sufficient |
| NameResolver consolidation | May delegate to registry, but full refactor is separate initiative |
| AutomationConfig name resolution | Pipeline templates can use registry, but refactor is separate |
| Holder project detection | Holder projects are already statically registered |

---

## Requirements

### Discovery Requirements (FR-DISC-*)

#### FR-DISC-001: Workspace Project Discovery

| Field | Value |
|-------|-------|
| **ID** | FR-DISC-001 |
| **Requirement** | WorkspaceProjectRegistry discovers all projects in a workspace via Asana API |
| **Priority** | Must |
| **Trace** | GAP G1: No dynamic project discovery |
| **Acceptance Criteria** | |

- [ ] Calls `GET /workspaces/{workspace_gid}/projects` endpoint
- [ ] Handles pagination for workspaces with >100 projects
- [ ] Returns complete project list including name, GID, and archived status
- [ ] Excludes archived projects by default (configurable)
- [ ] Discovery completes in <3 seconds for typical workspace (<100 projects)

**Integration Point**: `src/autom8_asana/models/business/registry.py` or new module

---

#### FR-DISC-002: Name-to-GID Mapping

| Field | Value |
|-------|-------|
| **ID** | FR-DISC-002 |
| **Requirement** | WorkspaceProjectRegistry maintains name-to-GID mapping with O(1) lookup |
| **Priority** | Must |
| **Trace** | GAP G3: No name-to-GID mapping at runtime |
| **Acceptance Criteria** | |

- [ ] After discovery, `get_by_name(name)` returns project GID in O(1) time
- [ ] Name matching is case-insensitive
- [ ] Whitespace is normalized (trimmed)
- [ ] Returns `None` for unknown names (not exception)
- [ ] Mapping persists for registry lifetime

**Integration Point**: `src/autom8_asana/models/business/registry.py`

---

#### FR-DISC-003: Discovery Timing

| Field | Value |
|-------|-------|
| **ID** | FR-DISC-003 |
| **Requirement** | Discovery can be triggered automatically (lazy) or explicitly, but must not impede DX |
| **Priority** | Must |
| **Trace** | User Decision #1: Architect recommends timing, must not impede DX |
| **Acceptance Criteria** | |

- [ ] Lazy discovery: Triggered on first detection call for unregistered project GID
- [ ] Explicit discovery: `await registry.discover_async(workspace_gid)` available
- [ ] Discovery is idempotent (repeated calls refresh, don't duplicate)
- [ ] No explicit call required for basic usage (lazy is default)
- [ ] Architect determines optimal approach in TDD

**Note**: Explicit-call-only is explicitly rejected as it impedes DX.

**Integration Point**: `src/autom8_asana/models/business/registry.py`

---

### Pipeline Registration Requirements (FR-PIPE-*)

#### FR-PIPE-001: Pipeline Project Identification

| Field | Value |
|-------|-------|
| **ID** | FR-PIPE-001 |
| **Requirement** | Registry identifies pipeline projects by matching ProcessType values in project names |
| **Priority** | Must |
| **Trace** | User Decision #2: Name-contains algorithm acceptable with override mechanism |
| **Acceptance Criteria** | |

- [ ] Project name containing ProcessType value (case-insensitive) is identified as pipeline project
- [ ] Example: "Sales Pipeline" matches ProcessType.SALES
- [ ] Example: "Client Onboarding" matches ProcessType.ONBOARDING
- [ ] Word boundaries considered: "Sales" matches, "Salesforce" does not (configurable)
- [ ] Override mechanism exists for edge cases (Could Have)

**ProcessType values to match**: LEAD, SALES, ONBOARDING, PRODUCTION, RETENTION, OFFBOARDING, ARCHIVE

**Integration Point**: `src/autom8_asana/models/business/registry.py`

---

#### FR-PIPE-002: Pipeline Project Registration

| Field | Value |
|-------|-------|
| **ID** | FR-PIPE-002 |
| **Requirement** | Identified pipeline projects are registered as EntityType.PROCESS in ProjectTypeRegistry |
| **Priority** | Must |
| **Trace** | GAP G2: Process entities fail detection |
| **Acceptance Criteria** | |

- [ ] Discovered pipeline project GIDs registered with `EntityType.PROCESS`
- [ ] Registration happens automatically after discovery
- [ ] Static PRIMARY_PROJECT_GID registrations are preserved (not overwritten)
- [ ] Duplicate GID registration logs warning but does not error
- [ ] Registered projects appear in `get_registry().lookup(gid)`

**Integration Point**: `src/autom8_asana/models/business/registry.py`

---

#### FR-PIPE-003: ProcessType Derivation

| Field | Value |
|-------|-------|
| **ID** | FR-PIPE-003 |
| **Requirement** | Registry can derive ProcessType from pipeline project GID |
| **Priority** | Must |
| **Trace** | Success Criterion #2: process_type property returns correct type |
| **Acceptance Criteria** | |

- [ ] `get_process_type(project_gid)` returns `ProcessType | None`
- [ ] Returns the ProcessType that matched the project name during identification
- [ ] Returns `None` for non-pipeline projects
- [ ] O(1) lookup after discovery

**Example**:
```python
registry.get_process_type("123...")  # -> ProcessType.SALES
process.process_type  # Uses registry for lookup
```

**Integration Point**: `src/autom8_asana/models/business/registry.py`, `src/autom8_asana/models/business/process.py`

---

### Detection Integration Requirements (FR-DET-*)

#### FR-DET-001: Tier 1 Detection for Pipeline Projects

| Field | Value |
|-------|-------|
| **ID** | FR-DET-001 |
| **Requirement** | Detection Tier 1 succeeds for tasks in discovered pipeline projects |
| **Priority** | Must |
| **Trace** | Success Criterion #1: Process task in "Sales" detected as EntityType.PROCESS |
| **Acceptance Criteria** | |

- [ ] Task with membership in registered pipeline project returns `EntityType.PROCESS`
- [ ] Detection tier is 1 (O(1), no API calls)
- [ ] `needs_healing` is `False` (project membership exists)
- [ ] Detection works identically to other Tier 1 detections

**Integration Point**: `src/autom8_asana/models/business/detection.py`

---

#### FR-DET-002: Detection API Unchanged

| Field | Value |
|-------|-------|
| **ID** | FR-DET-002 |
| **Requirement** | Detection function signatures remain unchanged |
| **Priority** | Must |
| **Trace** | Constraint: No breaking changes to detection API signatures |
| **Acceptance Criteria** | |

- [ ] `detect_entity_type(task, parent_type=None)` signature preserved
- [ ] `detect_entity_type_async(task, client, ...)` signature preserved
- [ ] Return type `DetectionResult` unchanged
- [ ] Existing callers require no modification

**Integration Point**: `src/autom8_asana/models/business/detection.py`

---

### Backward Compatibility Requirements (FR-COMPAT-*)

#### FR-COMPAT-001: Static Registration Preserved

| Field | Value |
|-------|-------|
| **ID** | FR-COMPAT-001 |
| **Requirement** | Existing PRIMARY_PROJECT_GID static registration continues to work |
| **Priority** | Must |
| **Trace** | Constraint: Backward compatibility |
| **Acceptance Criteria** | |

- [ ] Static `Business.PRIMARY_PROJECT_GID` registration unchanged
- [ ] Static registrations take precedence over dynamic discovery for same GID
- [ ] `__init_subclass__` hook registration unchanged
- [ ] Environment variable override (`ASANA_PROJECT_*`) unchanged
- [ ] All existing detection tests pass without modification

**Integration Point**: `src/autom8_asana/models/business/base.py`

---

#### FR-COMPAT-002: Existing Tests Pass

| Field | Value |
|-------|-------|
| **ID** | FR-COMPAT-002 |
| **Requirement** | All existing tests pass without modification |
| **Priority** | Must |
| **Trace** | Success Criterion #6: All existing tests pass |
| **Acceptance Criteria** | |

- [ ] `pytest` exit code 0 before and after implementation
- [ ] No test modifications required for existing functionality
- [ ] Coverage does not decrease for existing modules

**Measurement**: `pytest` execution

---

### Refresh Requirements (FR-REF-*)

#### FR-REF-001: On-Demand Refresh

| Field | Value |
|-------|-------|
| **ID** | FR-REF-001 |
| **Requirement** | Registry supports on-demand refresh of project list |
| **Priority** | Should |
| **Trace** | GAP-ANALYSIS Section 4.2: Refresh mechanism needed |
| **Acceptance Criteria** | |

- [ ] `await registry.refresh_async()` re-fetches workspace projects
- [ ] Refresh updates name-to-GID mapping with current state
- [ ] New projects discovered and registered
- [ ] Renamed projects update name mapping
- [ ] Deleted projects remain in mapping (no removal)

**Note**: Projects are stable - no frequent spin-up/spin-down pattern per User Decision #3.

**Integration Point**: `src/autom8_asana/models/business/registry.py`

---

### Non-Functional Requirements

#### NFR-PERF-001: Discovery Performance

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-001 |
| **Requirement** | Discovery completes in under 3 seconds for typical workspace |
| **Target** | <3 seconds for workspace with <100 projects |
| **Measurement** | Performance test |

**Acceptance Criteria**:
- [ ] Single API call for workspaces with <100 projects
- [ ] Pagination handled efficiently for larger workspaces
- [ ] No unnecessary field fetching (minimal opt_fields)

---

#### NFR-PERF-002: Name Resolution Performance

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-002 |
| **Requirement** | Name-to-GID resolution is O(1) after discovery |
| **Target** | O(1) |
| **Measurement** | Code inspection, benchmark test |

**Acceptance Criteria**:
- [ ] Hash map (dict) used for name-to-GID mapping
- [ ] No iteration or API calls during lookup
- [ ] Case normalization done at insertion time

---

#### NFR-PERF-003: Registry Memory Usage

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-003 |
| **Requirement** | Registry memory usage reasonable for typical workspace |
| **Target** | <10 MB for workspace with 100 projects |
| **Measurement** | Memory profiling |

**Acceptance Criteria**:
- [ ] Only essential project metadata stored (GID, name, ProcessType)
- [ ] Full Project objects not cached (only GIDs and names)
- [ ] Mapping structures are simple dicts

---

#### NFR-SAFE-001: Type Safety

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-001 |
| **Requirement** | All new code passes mypy strict mode |
| **Target** | mypy exit code 0 |
| **Measurement** | `mypy src/autom8_asana` |

**Acceptance Criteria**:
- [ ] All new functions fully typed
- [ ] ProcessType | None return types where appropriate
- [ ] No `# type: ignore` except where unavoidable

---

#### NFR-SAFE-002: Test Coverage

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-002 |
| **Requirement** | New code has >90% test coverage |
| **Target** | >90% coverage for new modules |
| **Measurement** | `pytest --cov` |

**Acceptance Criteria**:
- [ ] Unit tests for discovery mechanism
- [ ] Unit tests for pipeline identification logic
- [ ] Unit tests for ProcessType derivation
- [ ] Integration tests for end-to-end detection
- [ ] Edge case tests (empty workspace, no pipeline projects)

---

## User Stories / Use Cases

### US-001: Pipeline Automation Detection

**As a** pipeline automation engine
**I want to** detect Process entities in pipeline projects
**So that** I can trigger conversion rules when stage advancement occurs

**Scenario**:
```python
# Before: Fails
task_in_sales_project = await client.tasks.get_async(task_gid)
result = detect_entity_type(task)  # Returns UNKNOWN

# After: Works
await registry.discover_async(workspace_gid)  # Or automatic via lazy
task_in_sales_project = await client.tasks.get_async(task_gid)
result = detect_entity_type(task)  # Returns PROCESS (tier 1)
process = Process.model_validate(task.model_dump())
print(process.process_type)  # ProcessType.SALES
```

---

### US-002: Demo Script Without Hardcoded GIDs

**As a** developer writing demo scripts
**I want to** reference projects by name
**So that** my scripts work in any workspace without configuration

**Scenario**:
```python
# Before: Requires hardcoded GIDs
SALES_PROJECT_GID = "1234567890"  # Breaks in other workspaces

# After: Name-based resolution
sales_gid = registry.get_by_name("Sales")
# Or: Detection just works because pipeline projects are registered
```

---

### US-003: Process Type Resolution

**As a** business logic consumer
**I want to** know which ProcessType a Process entity belongs to
**So that** I can apply stage-specific behavior

**Scenario**:
```python
process = Process.model_validate(task.model_dump())

# process_type property uses registry
if process.process_type == ProcessType.ONBOARDING:
    # Apply onboarding-specific logic
    await send_welcome_email(process)
elif process.process_type == ProcessType.RETENTION:
    # Apply retention-specific logic
    await schedule_renewal_call(process)
```

---

### US-004: Graceful Degradation

**As a** SDK consumer
**I want** detection to work even if discovery hasn't run
**So that** I don't need to remember explicit initialization

**Scenario**:
```python
# Consumer doesn't explicitly call discover
# First detection of task in unknown project triggers lazy discovery
result = detect_entity_type(task)  # Triggers discovery internally if needed
# Subsequent detections are O(1)
```

---

## Assumptions

1. **Single workspace per client**: AsanaClient is initialized with one workspace_gid; multi-workspace is future scope

2. **Projects are stable**: Per User Decision #3, projects are mature and do not frequently spin up/down. Refresh-on-demand is sufficient.

3. **ProcessType names are in project names**: Pipeline projects contain their ProcessType as a word in the name (e.g., "Sales Pipeline", "Client Onboarding")

4. **Workspace GID available**: `AsanaClient.default_workspace_gid` is populated at client initialization

5. **Asana API access**: Client has permission to list workspace projects

6. **Case-insensitive matching sufficient**: "SALES" and "Sales" and "sales" all match ProcessType.SALES

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| `ProjectsClient.list_async(workspace=...)` | SDK | Implemented | Infrastructure exists |
| `AsanaClient.default_workspace_gid` | SDK | Implemented | Auto-detected or configured |
| `ProjectTypeRegistry` | SDK | Implemented | Needs runtime registration extension |
| `ProcessType` enum | SDK | Implemented | 7 pipeline stages defined |
| `detect_entity_type()` | SDK | Implemented | Uses registry lookup |

---

## Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| Q1 | Should WorkspaceProjectRegistry be a separate class or extend ProjectTypeRegistry? | Architect | TDD Session | Deferred to architecture |
| Q2 | Exact lazy discovery trigger point (on unknown GID lookup, on first detection, on client init)? | Architect | TDD Session | Deferred to architecture |
| Q3 | Should registry be per-client instance or module singleton? | Architect | TDD Session | Deferred - note projects are stable |
| Q4 | Word boundary matching for ProcessType detection (strict vs contains)? | Architect | TDD Session | Default to contains, configurable |

**Note**: All open questions are non-blocking. They are architectural decisions to be resolved in TDD phase.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Requirements Analyst | Initial PRD from Prompt 0 and Gap Analysis |

---

## Appendix A: Detection Flow After Implementation

```
Task Input (with memberships)
    |
    v
[Tier 1] Registry Lookup
    |
    +-- GID in static registry (Business, Unit, etc.)
    |       --> Return EntityType, tier=1
    |
    +-- GID in discovered pipeline registry
    |       --> Return EntityType.PROCESS, tier=1
    |
    +-- GID not found
            |
            v
    [Lazy Discovery Trigger?] (If enabled)
            |
            +-- Discovers workspace projects
            +-- Registers pipeline projects
            +-- Re-attempts Tier 1 lookup
            |
            +-- Still not found
                    |
                    v
            [Tier 2-5] Fallback chain (unchanged)
```

---

## Appendix B: ProcessType to Project Name Matching

| ProcessType | Example Matching Project Names |
|-------------|-------------------------------|
| LEAD | "Lead Pipeline", "New Leads", "Lead Generation" |
| SALES | "Sales Pipeline", "Sales Process", "Active Sales" |
| ONBOARDING | "Client Onboarding", "Onboarding Process" |
| PRODUCTION | "Production", "Active Production" |
| RETENTION | "Retention Pipeline", "Client Retention" |
| OFFBOARDING | "Offboarding", "Client Offboarding" |
| ARCHIVE | "Archive", "Archived Processes" |

Matching is case-insensitive. Word boundary matching is configurable (default: contains match).

---

## Appendix C: Registry Architecture Context

From ADR-0093 (Project-to-EntityType Registry Pattern):

- Registry is currently a **module-level singleton** using `__new__` pattern
- Populated at **import time** via `__init_subclass__` hooks
- Supports **environment variable override** (`ASANA_PROJECT_{ENTITY_TYPE}`)
- Provides **reset()** for test isolation

The new dynamic registration must integrate with this existing pattern without breaking it.

---

## Quality Gates Checklist

- [x] Problem statement is clear and specific
- [x] Success metrics are quantified and measurable
- [x] Scope explicitly defines in/out boundaries
- [x] Every requirement has acceptance criteria
- [x] MoSCoW priorities assigned to all requirements
- [x] Requirements trace to gap analysis and user decisions
- [x] User stories illustrate key scenarios
- [x] Assumptions documented
- [x] Dependencies identified with status
- [x] Open questions assigned to Architect (non-blocking)
- [x] Backward compatibility explicitly addressed
- [x] Performance targets specified
