# Orchestrator Initialization: Workspace Project Registry

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, detection, batch operations
  - Activates when: Working with detection system, entity types, registry patterns

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

**How Skills Work**: Skills load automatically based on your current task.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify—you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Enable Dynamic Workspace Project Discovery

Build a **WorkspaceProjectRegistry** that discovers all projects in an Asana workspace at runtime, enabling dynamic project-to-GID mapping and unblocking pipeline automation by properly detecting Process entities in pipeline projects.

### Why This Initiative?

- **Unblock Pipeline Automation**: Process entities in pipeline projects (Sales, Onboarding) currently fail detection, blocking the entire automation layer
- **Eliminate Hardcoded GIDs**: Current approach requires hardcoding project GIDs that vary by workspace/deployment
- **Enable Multi-Tenant Support**: Different workspaces have different project GIDs - discovery enables portable SDK usage
- **Complete the Detection System**: Tier 1 detection fails for any project not in the static registry

### Current State

**ProjectsClient (Functional)**:
- `list_async(workspace=...)` can fetch all projects in a workspace
- `get_async(gid)` fetches single project
- Infrastructure exists but unused for discovery

**NameResolver (Partial)**:
- `resolve_project_async()` fetches projects and caches per-session
- Cache lost on SaveSession exit
- Does not feed into detection registry

**ProjectTypeRegistry (Static Only)**:
- Maps project GID → EntityType at import time
- Uses hardcoded `PRIMARY_PROJECT_GID` class attributes
- Never updated at runtime
- **Process.PRIMARY_PROJECT_GID = None** (cannot be static)

**Detection System (Broken for Pipeline)**:
- Tier 1 lookup fails for unknown project GIDs
- Process entities fall through to Tier 5 (UNKNOWN)
- Pipeline automation rules don't trigger

**What's Missing**:

```python
# This is what we need to enable:

# At client initialization
registry = await client.workspace_projects.discover_async()

# Detection now works
task_in_sales_project = ...
result = detect_entity_type(task)  # Returns EntityType.PROCESS

# Pipeline automation can resolve by name, not GID
onboarding_project = await client.workspace_projects.get_by_name_async("Onboarding")

# Result:
# - Process tasks detected correctly
# - Pipeline automation triggers
# - No hardcoded GIDs required
```

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AsanaClient                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  WorkspaceProjectRegistry                        │   │
│  │                                                                  │   │
│  │  name_to_gid: {"Sales": "123...", "Onboarding": "456...", ...}  │   │
│  │  gid_to_project: {"123...": Project(...), ...}                  │   │
│  │  pipeline_projects: {"123...": ProcessType.SALES, ...}          │   │
│  │                                                                  │   │
│  │  Methods:                                                        │   │
│  │  - discover_async(workspace_gid) → None                         │   │
│  │  - get_by_name_async(name) → Project | None                     │   │
│  │  - get_by_gid_async(gid) → Project | None                       │   │
│  │  - is_pipeline_project(gid) → bool                              │   │
│  │  - get_process_type(gid) → ProcessType | None                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ProjectTypeRegistry                           │   │
│  │            (Extended with discovered projects)                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Detection System                             │   │
│  │      Tier 1 now succeeds for pipeline projects                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Constraints

- **Backward compatibility**: Existing hardcoded PRIMARY_PROJECT_GID must continue to work
- **Single workspace V1**: Support single workspace initially, multi-workspace is future scope
- **Lazy vs eager**: Discovery should be configurable (on-demand or at client init)
- **No breaking changes**: Detection API signatures unchanged
- **Performance**: Name resolution must be O(1) after discovery
- **Asana API**: Use `GET /workspaces/{workspace_gid}/projects` endpoint

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Discover all projects in workspace via Asana API | Must |
| Build name-to-GID mapping (case-insensitive) | Must |
| Identify pipeline projects by name matching ProcessType values | Must |
| Register pipeline projects as EntityType.PROCESS in registry | Must |
| Enable Tier 1 detection for Process entities in pipeline projects | Must |
| Integrate with AsanaClient.default_workspace_gid | Must |
| Support on-demand refresh of project list | Should |
| Cache discovered projects for session duration | Should |
| Provide get_by_name_async() for name-based project lookup | Should |
| Support environment variable overrides for pipeline projects | Could |

### Success Criteria

1. Process task in "Sales" project detected as `EntityType.PROCESS`
2. `process_type` property returns `ProcessType.SALES` for task in Sales project
3. Pipeline automation rule triggers when Process moves to CONVERTED section
4. Pipeline automation demo script completes successfully without Tier 5 warnings
5. No hardcoded GIDs required in demo script or automation config
6. Existing entity detection (Business, Unit, Offer) unchanged
7. All existing tests continue to pass
8. New tests cover workspace project discovery scenarios

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Discovery time | < 3 seconds | For workspace with < 100 projects |
| Name lookup | O(1) | After discovery complete |
| Registry memory | < 10 MB | For typical workspace |
| API calls for discovery | 1-2 | Paginated if > 100 projects |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Current state audit, API analysis, gap validation |
| **2: Requirements** | Requirements Analyst | PRD-WORKSPACE-PROJECT-REGISTRY with acceptance criteria |
| **3: Architecture** | Architect | TDD-WORKSPACE-PROJECT-REGISTRY + ADRs |
| **4: Implementation P1** | Principal Engineer | WorkspaceProjectRegistry core + discovery |
| **5: Implementation P2** | Principal Engineer | Detection integration + pipeline project detection |
| **6: Implementation P3** | Principal Engineer | Demo script update + automation integration |
| **7: Validation** | QA/Adversary | Validation report, edge cases, regression testing |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/clients/projects.py` | What list methods exist? What opt_fields are available? |
| `src/autom8_asana/clients/name_resolver.py` | How does caching work? Can we reuse patterns? |
| `src/autom8_asana/models/business/registry.py` | How is registration done? Can we extend at runtime? |
| `src/autom8_asana/models/business/detection.py` | How does Tier 1 work? What changes are needed? |
| `src/autom8_asana/client.py` | How is workspace_gid handled? Where should registry live? |

### Asana API Audit

| Resource | Questions to Answer |
|----------|---------------------|
| Projects endpoint | What fields are returned? Is workspace filtering required? |
| Pagination | How does pagination work for large project lists? |
| Workspaces endpoint | How do we get the user's workspaces? |
| Rate limits | Any concerns with project listing at init? |

### Integration Gap Analysis

| Area | Questions |
|------|-----------|
| ProjectTypeRegistry | Can it be extended at runtime, or is it import-time only? |
| Detection System | What changes are needed to use discovered projects? |
| AutomationConfig | Should pipeline_templates accept names instead of GIDs? |
| NameResolver | Should it delegate to WorkspaceProjectRegistry? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Architecture Questions

1. **Singleton vs instance?**: Should WorkspaceProjectRegistry be a module-level singleton or per-client instance?
2. **Discovery timing?**: Eager at client init, lazy on first use, or explicit call required?
3. **Cache scope?**: Session-scoped (like NameResolver) or client-scoped (persists across sessions)?

### Detection Questions

4. **Pipeline project identification?**: How do we identify a project as a pipeline project?
   - Option A: Name contains ProcessType value (e.g., "Sales" in project name)
   - Option B: Project in a specific team/portfolio
   - Option C: Explicit configuration
5. **ProcessType derivation?**: Given a pipeline project, how do we determine its ProcessType?
   - Case-sensitive? Word boundaries? Exact match vs contains?

### Integration Questions

6. **Registry extension?**: Should WorkspaceProjectRegistry extend ProjectTypeRegistry or compose with it?
7. **NameResolver consolidation?**: Should NameResolver.resolve_project_async() delegate to WorkspaceProjectRegistry?
8. **AutomationConfig change?**: Should pipeline_templates values be resolvable by name?

---

## Your First Task

Confirm understanding by:

1. Summarizing the WorkspaceProjectRegistry goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-WORKSPACE-PROJECT-REGISTRY
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Reference Documents

- **Gap Analysis**: `/docs/analysis/GAP-ANALYSIS-WORKSPACE-PROJECT-REGISTRY.md`
- **Detection TDD**: `/docs/design/TDD-DETECTION.md`
- **Detection ADRs**: `/docs/decisions/ADR-0093-project-type-registry.md`, `ADR-0094-detection-fallback-chain.md`
- **Automation PRD**: `/docs/requirements/PRD-AUTOMATION-LAYER.md`
- **Pipeline Demo**: `/scripts/example_pipeline_automation.py`
