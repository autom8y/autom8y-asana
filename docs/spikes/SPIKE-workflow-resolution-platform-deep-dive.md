# SPIKE: Workflow Resolution Platform -- Consolidated Deep Dive

**Date**: 2026-02-11
**Scope**: 3-phase research spike across microservice and legacy codebases
**Status**: COMPLETE
**Stakeholder Context**: 13-round structured interview (see STAKEHOLDER-CONTEXT-workflow-resolution-platform.md)
**Phase Sources**: Phase 1 (Core System Mapping), Phase 2 (Legacy Pattern Extraction), Phase 3 (DNA/Play Modeling + Synthesis)

---

## 1. Executive Summary

1. **The microservice has exactly ONE automated workflow route (Sales to Onboarding) out of 30+ that exist in the legacy system.** The gap is not incremental -- it spans the entire lifecycle routing DAG, entity creation, dependency wiring, and cascading state updates. Building the Workflow Resolution Platform is the prerequisite for closing this gap.

2. **The legacy resolution system implements robust multi-step fallback chains (6-7 step chains for Process.unit and Process.offer) that gracefully degrade through trigger traversal, dependency traversal, and custom field lookup.** These strategy patterns should be extracted and reimplemented cleanly. The anti-patterns (string-based field resolution, QUIET error suppression, unbounded API chains, thread-unsafe mutation) should be explicitly avoided.

3. **DNA/Play entities are critical to lifecycle workflows but entirely absent from the microservice beyond a navigation stub.** BackendOnboardABusiness is created during every Implementation init and wired as a dependency. Five IsolatedPlay subtypes exist in legacy; the microservice's DNA model has zero custom fields or behavioral methods. Minimum viable modeling is required for lifecycle support.

4. **Dependency links are the primary navigation mechanism in legacy but are never created by the microservice.** The microservice uses hierarchy traversal (parent chain) instead. Both strategies have tradeoffs -- dependencies are cheaper (2 API calls) but often missing; hierarchy is reliable (3-5 API calls) but more expensive. The platform needs a hybrid approach.

5. **Process entities are not cache-warmed (warmable=False, TTL=60s), creating a cold-cache challenge for workflow resolution.** Since workflows primarily create and transition Processes, the resolution platform will operate mostly against uncached data. Cache strategy adjustments or workflow-specific pre-fetching may be needed.

---

## 2. Architecture Reality Map

### 2.1 What the Microservice Has

| Capability | Implementation | Maturity |
|---|---|---|
| **Entity model layer** | BusinessEntity + descriptors (TextField, EnumField, etc.) + HolderFactory | Production |
| **Entity hierarchy** | 9 holders, 1 root, 1 composite, 8 leaf models (3 stubs) | Production |
| **Cache system** | Task-level S3/Redis cache with TTLs, overflow thresholds, warming | Production |
| **Pipeline conversion** | PipelineConversionRule: Sales -> Onboarding only | Production |
| **Polling automation** | ActionExecutor: add_tag, add_comment, change_section | Production |
| **Batch workflows** | WorkflowAction ABC + ConversationAuditWorkflow | Production |
| **SaveSession** | Commit-based persistence with dependency add/remove primitives | Production |
| **Process data model** | Single Process class with ProcessType enum (6 types + GENERIC) | Production |
| **DNAHolder** | HolderFactory-based holder with PRIMARY_PROJECT_GID | Production |
| **DNA stub** | BusinessEntity with ParentRef/HolderRef navigation, zero fields | Stub |

### 2.2 What Is Needed (Full Gap Picture)

| Capability | Legacy Has | Microservice Status | Gap Severity |
|---|---|---|---|
| **Lifecycle routing DAG** | 15+ route transitions across 9 pipeline stages | 1 route (Sales->Onboarding) | CRITICAL |
| **Tag-based dispatch** | `route_*`, `request_*`, `play_*` vocabulary (~30+ actions) | None | HIGH |
| **Cascading section updates** | Per-stage: Offer + Unit + Business sections updated | None | HIGH |
| **Pipeline auto-completion** | Earlier stages auto-completed when later stages begin | None | HIGH |
| **Dependency wiring** | Default dependencies/dependents created on init_process | Primitives exist, unused | HIGH |
| **DNA/Play creation** | 5 IsolatedPlay subtypes created via DnaManager | Stub DNA model only | HIGH |
| **Entity creation routing** | BackendOnboardABusiness, AssetEdit, SourceVideographer | None | HIGH |
| **Product-driven creation** | "video*" in products -> SourceVideographer | None | MEDIUM |
| **Product synchronization** | Bidirectional products between Process and Unit | None | MEDIUM |
| **Duplicate detection** | ProcessManager checks DataFrame for existing process | None | MEDIUM |
| **Campaign lifecycle** | activate/deactivate via offer.ad_manager | None | MEDIUM |
| **Consultation routing** | 18+ consultation subtypes via ProcessManager | None | LOW (initially) |
| **Month1/AccountError/Expansion** | 3 pipeline types missing from ProcessType enum | Missing | MEDIUM |
| **Field seeding from trigger** | Threaded _init_fields with string-path defaults | FieldSeeder (limited) | MEDIUM |
| **Process warmable cache** | N/A (legacy has own caching) | warmable=False, TTL=60s | MEDIUM |
| **Resolution fallback chains** | 6-7 step chains for Process.unit and Process.offer | Not implemented | HIGH |

### 2.3 Entity Hierarchy -- Complete Inventory

```
Business (ROOT) -- 19 descriptors, fully modeled, warmable (pri 2, TTL 3600s)
+-- ContactHolder (HOLDER) -- HolderFactory, fully modeled
|   +-- Contact (LEAF) -- 19 descriptors, warmable (pri 4, TTL 900s)
+-- UnitHolder (HOLDER) -- HolderFactory, fully modeled
|   +-- Unit (COMPOSITE) -- warmable (pri 1, TTL 900s)
|       +-- OfferHolder (HOLDER) -- UnitNestedHolderMixin + HolderFactory
|       |   +-- Offer (LEAF) -- warmable (pri 3, TTL 180s)
|       +-- ProcessHolder (HOLDER) -- UnitNestedHolderMixin + HolderFactory
|           +-- Process (LEAF) -- NOT warmable, TTL 60s
+-- LocationHolder (HOLDER) -- HolderFactory
|   +-- Location (LEAF) -- TTL 3600s
|   +-- Hours (LEAF) -- TTL 3600s
+-- DNAHolder (HOLDER) -- HolderFactory, PRIMARY_PROJECT_GID=1167650840134033
|   +-- DNA (LEAF) -- STUB: navigation only, zero fields
+-- ReconciliationHolder (HOLDER)
|   +-- Reconciliation (LEAF) -- STUB
+-- AssetEditHolder (HOLDER) -- warmable (pri 5, TTL 300s)
|   +-- AssetEdit (LEAF) -- Process subclass, warmable
+-- VideographyHolder (HOLDER)
    +-- Videography (LEAF) -- STUB
```

---

## 3. Resolution Strategy Recommendations

### 3.1 Extract These Legacy Patterns

| Pattern | Legacy Source | Recommended Implementation |
|---|---|---|
| **Multi-step fallback resolution** | Process.unit (6 steps), Process.offer (7 steps) | Resolution strategy chain: configurable, typed, with depth limits |
| **Post-resolution validation** | Process.offer validates offer_id after structural traversal | Validation layer in resolution pipeline |
| **Pipeline auto-completion** | Pipeline.init_process() traverses offer deps | Business rule in lifecycle transition config |
| **Cascading section updates** | Per-stage mapping (Offer/Unit/Business sections) | Data-driven mapping table, not class methods |
| **Default dependency wiring** | Process.default_dependencies/default_dependents | Wiring rules registry (configurable per entity type) |
| **Duplicate detection** | ProcessManager._check_for_existing_process | Idempotency check in process creation flow |

### 3.2 Avoid These Legacy Anti-Patterns

| Anti-Pattern | Legacy Impact | Recommended Alternative |
|---|---|---|
| String-based field defaults (`"offer.office_phone"`) | No compile-time validation, hidden coupling | Typed references or validated configuration registry |
| QUIET error suppression (module-level flag) | Silent failures, None propagation | Structured ResolutionResult with success/failure/partial states |
| Unbounded API call chains (4-6 calls per property) | 30+ second resolution for single Process | Configurable depth limit + total API call budget |
| isinstance dispatch (8+ type checks) | Adding entity type requires modifying every resolution method | Strategy registry: entities register navigation capabilities |
| Thread-unsafe mutation (_init_fields spawns threads on shared state) | Race conditions between init and save | Immutable snapshot + mutation plan (collect changes, apply atomically) |
| Sleep-based retries (hardcoded sleep(1) for 3 attempts) | Blocks thread, no backoff, no diagnostics | Async retry with exponential backoff policy |

### 3.3 Resolution Architecture

The resolution platform should implement a **hybrid traversal strategy** with ordered fallback:

```
Resolution Request (e.g., "Get Unit for this Process")
  |
  1. Cache lookup (if entity GID known)
  |     Hit -> return cached entity
  |     Miss -> continue
  |
  2. Dependency shortcut (2 API calls: get deps -> get target)
  |     Found -> cache + return
  |     Not found -> continue (deps often missing)
  |
  3. Hierarchy traversal (3-5 API calls: up to Business -> down to holder -> down to entity)
  |     Found -> cache + return
  |     Not found -> continue
  |
  4. Custom field lookup (e.g., offer_id match against sibling entities)
  |     Found -> cache + return
  |     Not found -> return ResolutionResult.FAILED with diagnostics
  |
  Budget: max 8 API calls per resolution. Fail fast after budget exhausted.
```

Each step should produce a `ResolutionResult`:
- `RESOLVED` -- entity found, confidence level attached
- `PARTIAL` -- entity found but data may be stale/incomplete
- `FAILED` -- exhausted all strategies, diagnostic message attached

---

## 4. Entity Modeling Priorities

### 4.1 DNA/Play Modeling Assessment

#### Legacy DNA/Play Class Hierarchy

```
Task
  +-- Dna (base)
  |     Custom fields: dna_priority (EnumField), intercom_link (TextField)
  |     Navigation: .business (via dna_holder.business), .unit (via deps or business.unit)
  |     Default project: BackendClientSuccessDna (GID: 1167650840134033)
  |     Behavior: init_dna() sets due_on, tier section, intercom link, priority
  |
  +-- Play (extends Process + Dna via multi-inheritance)
  |     Inherits both Process behaviors (routing, lifecycle) and Dna behaviors (init_dna)
  |     init_process() calls super().init_process() then super().init_dna()
  |     Navigation: .business, .unit, .offer, .holder all use Dna's implementations
  |
  +-- IsolatedPlay (extends Play)
  |     Removes BackendClientSuccessDna from default projects
  |     Sets default rep to TIER_1
  |     Each subtype overrides default_projects with its own project
  |
  +-- BackendOnboardABusiness (extends IsolatedPlay)
  |     Project: BackendOnboardABusiness (GID: 1207507299545000)
  |     Created during: Implementation.init_process() (always)
  |     Wired as: dependency on Implementation process
  |     Behavior: minimal -- just init_process passthrough
  |
  +-- PauseABusinessUnit (extends IsolatedPlay)
  |     Project: PauseABusinessUnit (separate GID)
  |     Default rep: TIER_2
  |     Behavior: init_process deactivates ALL active offers in offer_holder
  |     Navigation: .vertical from self.unit.vertical
  |
  +-- QuestionOnPerformance (extends IsolatedPlay)
  |     Project: QuestionOnPerformance (separate GID)
  |     Default rep: SUCCESS, default priority: 2
  |     STRUC_COLS: comments_summary, ai_concern_type, ai_resolution_success, ai_key_metrics, etc.
  |     Behavior: AI-powered comment history analysis (OpenAI integration)
  |     Properties: .cost (from offer), .weekly_ad_spend (from unit), .lead_testing_link (from offer)
  |
  +-- MetaAdminAccess (extends IsolatedPlay)
  |     Project: AccessProcessing (separate GID)
  |     Behavior: minimal -- init_process passthrough
  |
  +-- CustomCalendarIntegration (extends IsolatedPlay)
        Project: CalendarIntegrations (separate GID)
        Behavior: minimal -- init_process passthrough
```

#### DnaManager Routing Logic

The `DnaManager` extends `ProcessManager` and adds a single method:

```python
def play(self, action: str, **kwargs):
    kwargs["action"] = action
    return self._route(**kwargs)  # Delegates to ProcessManager._route()
```

The `_route` method in ProcessManager:
1. Calls `_get_next_project(action)` which checks if the holder is a DnaHolder -- if so, routes to BackendClientSuccessDna; otherwise, routes to Consultation project
2. Checks for existing process (duplicate detection via DataFrame)
3. Finds template in target project
4. Duplicates template with trigger task reference
5. Calls init_process (which triggers init_dna for DNA types)
6. Wires default dependencies/dependents
7. Saves cascading

The `play_*` tag convention triggers the DnaManager instead of ProcessManager (detected by tag prefix in the legacy router).

#### Which Play Subtypes Are Actively Used vs. Deprecated

| Play Subtype | Active? | Evidence |
|---|---|---|
| **BackendOnboardABusiness** | YES -- Critical | Created on every Implementation init; has dedicated project with active tasks |
| **QuestionOnPerformance** | YES -- Active | Has AI integration, STRUC_COLS for reporting, dedicated project |
| **PauseABusinessUnit** | YES -- Active | Has campaign deactivation behavior; affects offer lifecycle |
| **MetaAdminAccess** | LIKELY Active | Simple but has dedicated project (AccessProcessing) |
| **CustomCalendarIntegration** | LIKELY Active | Simple but has dedicated project (CalendarIntegrations) |

None appear deprecated. All 5 have dedicated Asana projects and non-trivial __main__ blocks suggesting active developer use.

#### Minimum Viable DNA Modeling for Lifecycle Workflows

**Phase 1 (Required for lifecycle routing):**
- Add `dna_priority` (EnumField) and `intercom_link` (TextField) to the DNA model
- No behavioral methods needed initially -- these are read-path fields
- DNAHolder already exists with HolderFactory and PRIMARY_PROJECT_GID

**Phase 2 (Required for Implementation stage):**
- BackendOnboardABusiness creation support:
  - Needs: template duplication in BackendOnboardABusiness project (GID: 1207507299545000)
  - Needs: dependency wiring (add as dependency on Implementation process)
  - Needs: init_dna behavior (set due_on, tier section routing)
- This is a write-path concern: the resolution platform must be able to CREATE DNA/Play entities, not just read them

**Phase 3 (Needed for full parity):**
- PauseABusinessUnit: campaign deactivation across all active offers
- QuestionOnPerformance: AI comment analysis, cost/ad_spend properties
- MetaAdminAccess, CustomCalendarIntegration: simple template creation in dedicated projects

### 4.2 Entity Modeling Priority Order

| Priority | Entity/Capability | Rationale | Effort (Confidence) |
|---|---|---|---|
| **P0** | Resolution primitives (strategy chains, ResolutionResult) | Foundation everything else builds on | 2-3 weeks (HIGH) |
| **P1** | Process lifecycle transitions (converted/did_not_convert routing) | Primary workflow pattern per stakeholder | 2-3 weeks (MEDIUM) |
| **P1** | Cascading section updates (per-stage Offer/Unit/Business mapping) | Required for lifecycle visibility | 1 week (HIGH) |
| **P1** | Pipeline auto-completion | Business rule: prevents orphaned stages | 3-5 days (HIGH) |
| **P2** | ProcessType enum expansion (Month1, AccountError, Expansion) | Missing pipeline types block those routes | 2-3 days (HIGH) |
| **P2** | DNA custom fields (dna_priority, intercom_link) | Required before Play creation | 1-2 days (HIGH) |
| **P2** | BackendOnboardABusiness creation + dependency wiring | Required for Implementation stage | 1 week (MEDIUM) |
| **P2** | Default dependency/dependent wiring rules | Required for entity graph connectivity | 1 week (MEDIUM) |
| **P3** | Duplicate detection | Prevents double-creation on retries/reapplied tags | 3-5 days (MEDIUM) |
| **P3** | Product synchronization (Process <-> Unit) | Required for correct product tracking | 3-5 days (MEDIUM) |
| **P3** | PauseABusinessUnit + campaign deactivation | Operational workflow for account pausing | 1 week (LOW) |
| **P3** | AssetEdit creation routing | Required for Implementation stage (second entity) | 1 week (MEDIUM) |
| **P3** | SourceVideographer creation | Products-driven, Onboarding stage only | 1 week (LOW) |
| **P4** | QuestionOnPerformance (AI integration) | Active but complex; AI dependency | 2 weeks (LOW) |
| **P4** | Consultation routing (18+ subtypes) | High count but uniform behavior | 1 week (MEDIUM) |
| **P4** | MetaAdminAccess, CustomCalendarIntegration | Simple template creation | 2-3 days (HIGH) |

---

## 5. Dependency Strategy

### 5.1 Current State

| Aspect | Legacy | Microservice |
|---|---|---|
| Reading dependencies | Heavy -- entity resolution, auto-completion, default wiring | Supported via TasksClient + cache |
| Creating dependencies | Active -- during init_process() for every new Process | Not done (primitives exist in SaveSession, unused) |
| Removing dependencies | Active -- during restructuring | Not done (primitives exist, unused) |
| Traversal for resolution | Primary navigation mechanism | Not used -- uses parent chain (hierarchy) instead |
| Cache support | N/A | Yes, but 40-item overflow limit |

### 5.2 Recommendation: Hybrid Strategy

**The microservice should create dependency links AND maintain hierarchy traversal as fallback.**

Arguments for creating dependency links:
- **Consistency**: Legacy-created tasks have dependencies; microservice-created tasks do not. Mixed-origin tasks create resolution inconsistency.
- **Performance**: 2 API calls (deps -> target) vs 3-5 (hierarchy chain). For batch workflows processing hundreds of entities, this matters.
- **Business semantics**: Dependencies encode relationships that hierarchy cannot (e.g., "this Implementation depends on this BackendOnboardABusiness completing first").

Arguments for maintaining hierarchy fallback:
- **Dependencies are often missing** (stakeholder confirmed). Manual task creation, API imports, and historical data all lack dependency links.
- **The 40-item overflow threshold** means heavily-linked tasks silently lose cached dependencies.
- **Hierarchy is always available** as the ground truth for parent-child relationships.

### 5.3 Implementation Approach

```
1. On entity creation (new processes, DNA plays, asset edits):
   - Create dependency links per legacy wiring rules
   - Set parent via hierarchy (existing set_parent)
   - Both are done; hierarchy is the reliable path, deps are the fast path

2. On entity resolution:
   - Try dependency shortcut first (2 calls)
   - Fall back to hierarchy traversal (3-5 calls)
   - Cache successful resolutions for subsequent access

3. Dependency wiring rules (configurable, not hardcoded):
   - Pipelines: default_dependents = [Unit, OfferHolder]; default_dependencies = [open DNA plays]
   - BackendOnboardABusiness: added as dependency on Implementation
   - AssetEdit: added as dependency on Implementation
   - SourceVideographer: no dependency wiring (standalone under VideographyHolder)
```

---

## 6. Cache Integration Strategy

### 6.1 Current Cache Architecture

- **Granularity**: Task-level (individual Asana task GIDs)
- **Backend**: S3 with optional Redis tiering
- **Key pattern**: `asana-cache/tasks/{gid}/{entry_type}.json[.gz]`
- **Entry types**: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME, etc.
- **Overflow thresholds**: 40 items for dependencies/dependents/subtasks; 100 for stories

### 6.2 TTLs and Warm Priority

| Entity | TTL | Warm Priority | Warmable | Workflow Impact |
|---|---|---|---|---|
| Unit | 900s (15min) | 1 (highest) | Yes | Usually warm -- good for resolution |
| Business | 3600s (1hr) | 2 | Yes | Usually warm -- good for field access |
| Offer | 180s (3min) | 3 | Yes | Often stale -- frequent section changes |
| Contact | 900s (15min) | 4 | Yes | Usually warm |
| AssetEdit | 300s (5min) | 5 | Yes | Moderate |
| Process | 60s (1min) | N/A | No | ALWAYS COLD -- major concern |

### 6.3 Workflow Cache Strategy

**Problem**: Workflows primarily operate on Processes (TTL=60s, not warmable). By the time a workflow resolves a Process, its cache entry is likely expired or was never created.

**Recommendations**:

1. **Workflow-local resolution cache**: During a single workflow execution, cache resolved entities in memory. A Process resolved once in a batch run should not require re-resolution for the same run.

2. **Pre-fetch during enumeration**: When enumerating processes in a project for lifecycle transitions, fetch task data in the enumeration call (Asana API supports `opt_fields` on task listing). This avoids N+1 individual fetches.

3. **Post-creation warming**: After creating a new entity (Process, DNA Play), immediately cache it. The entity just came from the API; caching it prevents a cold-cache situation on subsequent access within the same workflow.

4. **Do NOT make Process warmable**: The existing warm priority system is for background periodic warming. Process entities change too frequently (section moves, field updates) for background warming to provide reliable data. Workflow-local caching is more appropriate.

5. **Leverage warm ancestors**: The hierarchy warmer (`warm_ancestors_async`) already warms parent chains (Business, Unit). Resolution fallback through hierarchy will benefit from this warm data even when the Process itself is cold.

---

## 7. Risk Register

### 7.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Dependency overflow (>40 items) breaks traversal** | Medium | High | Hybrid strategy: always fall back to hierarchy; monitor real dependency counts |
| **Process cold cache degrades resolution performance** | High | Medium | Workflow-local cache; pre-fetch during enumeration; post-creation warming |
| **Legacy tag vocabulary removal breaks operations team** | Medium | High | Preserve tag vocabulary if operations currently uses it; or negotiate new trigger mechanism |
| **Multi-inheritance complexity in DNA/Play** | Medium | Medium | Microservice uses composition (single class + type enum) instead of inheritance; avoid legacy MRO issues |
| **Campaign activation/deactivation side effects** | Low | High | Requires understanding of ad_manager integration; spike the ad management API separately |
| **Consultation subtype explosion (18+ types)** | Low | Medium | Most consultations share identical behavior (Service base); model as configurable type, not subclasses |

### 7.2 Data/Migration Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Mixed-origin dependency data** | High | Medium | Legacy tasks have deps, microservice tasks do not. Hybrid resolution handles both. |
| **Section name mismatches** | Medium | Medium | Legacy uses string section names ("CONVERTED"); microservice uses enum. Validate mapping completeness. |
| **Custom field GID drift** | Low | High | Custom field GIDs are workspace-specific. Validate against live workspace; use name-based fallback. |
| **ProcessType enum incompleteness** | Certain | Low | Month1, AccountError, Expansion missing; add before lifecycle routing. |

### 7.3 Architectural Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Over-engineering resolution (premature abstraction)** | Medium | Medium | Start with 2-3 concrete workflows; extract patterns after proven. Stakeholder explicitly warned against over-abstraction. |
| **Under-engineering resolution (bespoke per workflow)** | Medium | High | Stakeholder explicitly warned against this. Use shared primitives from day 1. |
| **Bidirectional trigger complexity** | Low | Medium | Stakeholder wants Actions<->Workflows bidirectional triggers. Design interaction model carefully; avoid circular triggers. |

### 7.4 Unverified Assumptions

| Assumption | Why It Matters | How to Verify |
|---|---|---|
| **All 5 IsolatedPlay subtypes are actively used** | Determines minimum DNA modeling scope | Query each play's Asana project for recent task counts |
| **Legacy tag routing is the only trigger mechanism** | Microservice may need different trigger (webhook, section event) | Confirm with stakeholder how operations team initiates workflows |
| **Asana Rules webhook POST is the production trigger** | Section-change detection depends on external webhook | Verify webhook configuration in Asana workspace |
| **Ad manager API exists and is accessible** | Campaign activate/deactivate behavior depends on it | Explore offer.ad_manager in legacy; check for microservice equivalent |
| **40-item overflow threshold is sufficient for production** | Tasks with >40 deps lose cache. Unknown distribution of dep counts | Query production data for dependency count distribution |

---

## 8. Recommended Initiative Phases

### Phase 1: Resolution Foundation (3-4 weeks)

**Goal**: Build the shared resolution primitives that all workflows and actions will use.

| Deliverable | Description | Effort |
|---|---|---|
| ResolutionResult type | Success/partial/failed with diagnostics | 2 days |
| Resolution strategy chain | Ordered fallback: cache -> deps -> hierarchy -> custom field | 1 week |
| API call budget/depth limiter | Configurable max calls per resolution | 2-3 days |
| Workflow-local resolution cache | In-memory cache for single execution context | 2-3 days |
| Entity selection strategies | Top-level-with-override, compound predicates, type filtering | 1 week |
| Refactor ConversationAuditWorkflow | Replace `_resolve_office_phone()` with resolution primitives | 2-3 days |

**Rollback point**: Resolution primitives are additive. ConversationAuditWorkflow refactor is the only modification to existing code and can be reverted to the current manual resolution.

**Success criteria**:
- ConversationAuditWorkflow uses resolution primitives (no manual field parsing)
- Resolution handles both dependency-present and dependency-absent tasks
- API call count per resolution is bounded and measurable

### Phase 2: Lifecycle Routing Core (3-4 weeks)

**Goal**: Implement the lifecycle transition DAG with cascading section updates.

| Deliverable | Description | Effort |
|---|---|---|
| ProcessType enum expansion | Add Month1, AccountError, Expansion | 1 day |
| Lifecycle transition config | Data-driven mapping: stage -> converted_route, did_not_convert_route | 3-5 days |
| Cascading section update config | Per-stage: Offer section, Unit section, Business section | 3-5 days |
| Pipeline auto-completion | When later stage begins, complete earlier stages | 3-5 days |
| Section-change event handler | Detect section transitions and dispatch to lifecycle engine | 1 week |
| Sales -> Onboarding parity | Ensure existing PipelineConversionRule aligns with lifecycle engine | 2-3 days |

**Rollback point**: Lifecycle routing is a new subsystem. Existing PipelineConversionRule remains operational. New routing can be feature-flagged per pipeline stage.

**Success criteria**:
- Sales -> Onboarding -> Implementation -> Month1 chain works end-to-end
- Cascading section updates propagate correctly (Offer, Unit, Business all reflect new stage)
- Pipeline auto-completion triggers when Implementation is created (Sales and Onboarding complete)

### Phase 3: Entity Creation + Dependency Wiring (2-3 weeks)

**Goal**: Support creating new entities during lifecycle transitions and wiring dependencies.

| Deliverable | Description | Effort |
|---|---|---|
| DNA model enhancement | Add dna_priority, intercom_link fields to DNA | 1-2 days |
| Template duplication primitive | Generic: find template in project, duplicate with trigger ref | 3-5 days |
| BackendOnboardABusiness creation | Create during Implementation init, wire as dependency | 3-5 days |
| Default dependency wiring rules | Configurable rules: Pipelines get open DNA plays as deps | 3-5 days |
| Duplicate detection | Check for existing entity before creation | 2-3 days |

**Rollback point**: Entity creation is additive. Each creation type can be individually disabled via configuration.

**Success criteria**:
- Implementation.init creates BackendOnboardABusiness and wires as dependency
- Duplicate detection prevents re-creation on retry
- Default wiring rules apply to newly created processes

### Phase 4: Extended Entity Support (2-3 weeks)

**Goal**: Support the remaining entity types needed for full lifecycle coverage.

| Deliverable | Description | Effort |
|---|---|---|
| AssetEdit creation routing | Create during Implementation init via request_asset_edit | 3-5 days |
| SourceVideographer creation | Products-driven creation during Onboarding | 3-5 days |
| Product synchronization | Bidirectional products between Process and Unit | 3-5 days |
| Retention/Reactivation campaign control | Deactivation on Retention/Reactivation init | 3-5 days |
| Month1 offer activation | Activate campaign on Month1 init | 2-3 days |

**Rollback point**: Each entity creation type is independently configurable. Campaign control requires careful verification before production use.

**Success criteria**:
- Full pipeline lifecycle works: Sales -> Outreach -> Onboarding -> Implementation -> Month1
- Products-driven SourceVideographer creation works
- Campaign lifecycle (activate/deactivate) is functional

### Phase 5: Consultation + DNA Play Expansion (1-2 weeks)

**Goal**: Support remaining process types for feature completeness.

| Deliverable | Description | Effort |
|---|---|---|
| Consultation routing | Configurable consultation type mapping | 3-5 days |
| PauseABusinessUnit | Campaign deactivation across all active offers | 2-3 days |
| MetaAdminAccess, CustomCalendarIntegration | Simple template creation in dedicated projects | 1-2 days |
| QuestionOnPerformance | AI integration (OpenAI), reporting columns | 1 week (if needed) |

**Rollback point**: These are additive capabilities. Each can be individually enabled.

---

## 9. Open Questions for Stakeholder

### Priority 1: Blocking Design Decisions

1. **Trigger mechanism for lifecycle transitions**: The legacy uses Asana Rules webhook POSTs to detect section changes. The microservice has `EventType.SECTION_CHANGED` in PipelineConversionRule triggered after `SaveSession.commit()`. **Which mechanism should the new lifecycle routing use?** Options: (a) webhook from Asana Rules, (b) section_changed events from SaveSession, (c) polling-based detection, (d) hybrid.

2. **Should the tag vocabulary (`route_*`, `request_*`, `play_*`) be preserved?** The operations team may rely on these tag conventions. The microservice could: (a) implement tag-based dispatch matching legacy, (b) introduce a new trigger mechanism and migrate operations, (c) support both during transition.

3. **Campaign activate/deactivate**: Month1 calls `offer.activate()`, Retention/Reactivation call `offer.deactivate_campaign()`, AccountError calls `offer.ad_manager.activate()`. **Does a campaign management client exist in the microservice, or does this require new integration work?** This determines whether Phase 4 is 2-3 weeks or significantly longer.

### Priority 2: Scoping Decisions

4. **Which pipeline stages are in active use?** Expansion (stage 6) has minimal behavior in legacy (no overrides). AccountError's `_init_close_processes` is disabled (returns immediately). Are these actively used or can they be deferred?

5. **Consultation subtypes (18 classes)**: All share identical Service base behavior. Are all 18 actively used, or have some been deprecated? This affects whether consultation routing is a 3-day or 2-week effort.

6. **Self-loop transitions**: Outreach.did_not_convert routes to route_outreach (creates another Outreach). Reactivation.did_not_convert routes to route_reactivation. **Is this intentional business behavior, or should there be a limit to prevent infinite loops?**

### Priority 3: Verification Needed

7. **Dependency count distribution in production**: The 40-item overflow threshold means heavily-linked tasks lose cached dependencies. **What is the actual distribution of dependency counts?** This validates whether the hybrid strategy is sufficient or whether the overflow threshold needs adjustment.

8. **DNA/Play subtype active usage**: All 5 IsolatedPlay subtypes appear active based on code, but **how frequently is each used in production?** This prioritizes which DNA subtypes to model first.

9. **Products field values inventory**: The legacy checks `any(p.lower().startswith("video") for p in self.products)`. **What are the complete set of Products enum values, and which drive entity creation?** Only "video*" currently triggers creation, but this may be expanding.

10. **PipelineConversionRule alignment**: The existing Sales -> Onboarding conversion in the microservice was built before this spike. **Should it be refactored to use the new lifecycle routing engine, or maintained as a separate code path?** Refactoring ensures consistency; maintaining it avoids regression risk.

---

## Appendix A: Complete Lifecycle Routing DAG

```
Sales (stage 2)
  CONVERTED    -> route_onboarding      -> Onboarding (stage 3)
  DID NOT CONV -> route_outreach        -> Outreach (stage 1)

Outreach (stage 1)
  CONVERTED    -> route_sales           -> Sales (stage 2)
  DID NOT CONV -> route_outreach        -> Outreach (stage 1) [SELF-LOOP]

Onboarding (stage 3)
  CONVERTED    -> route_implementation  -> Implementation (stage 4)
  DID NOT CONV -> route_sales           -> Sales (stage 2)
  INIT: if "video*" in products -> request_source_videographer

Implementation (stage 4)
  CONVERTED    -> route_month_1         -> Month1 (stage 5)
  DID NOT CONV -> route_sales           -> Sales (stage 2)
  INIT: play_backend_onboard_a_business (unless already linked)
  INIT: request_asset_edit (unless already linked)

Month1 (stage 5)
  CONVERTED    -> (no route; Unit -> "Active"; optional offer review)
  DID NOT CONV -> (no route; Pipeline base: complete)
  INIT: offer.activate() (start campaign)

Retention (stage 1)
  CONVERTED    -> route_implementation  -> Implementation (stage 4)
  DID NOT CONV -> route_reactivation    -> Reactivation (stage 2)
  INIT: offer.deactivate_campaign()

Reactivation (stage 2)
  CONVERTED    -> route_implementation  -> Implementation (stage 4)
  DID NOT CONV -> route_reactivation    -> Reactivation (stage 2) [SELF-LOOP]
  INIT: offer.deactivate_campaign()

AccountError (stage 6)
  CONVERTED    -> (no route; Unit -> "Active"; Offer -> "ACTIVE"; reactivate campaign)
  DID NOT CONV -> route_retention       -> Retention (stage 1)
  INIT: offer.deactivate_campaign(); close_processes=True (disabled in legacy)

Expansion (stage 6)
  CONVERTED    -> (Pipeline base: LOG.warning + complete)
  DID NOT CONV -> (Pipeline base: LOG.warning + complete)
  [MINIMAL -- likely placeholder]
```

## Appendix B: Cascading Section Updates by Pipeline Stage

| Pipeline Stage | Offer Section | Unit Section | Business Section |
|---|---|---|---|
| Outreach init | "Sales Process" | "Engaged" | "OPPORTUNITY" |
| Sales init | "Sales Process" | "Next Steps" | "OPPORTUNITY" |
| Onboarding init | "ACTIVATING" | "Onboarding" | "ONBOARDING" |
| Implementation init | "IMPLEMENTING" | "Implementing" | "IMPLEMENTING" |
| Month1 init | "STAGED" | "Month 1" | "BUSINESSES" |
| Retention init | (deactivate campaign) | "Account Review" | -- |
| Reactivation init | (deactivate campaign) | "Paused" | -- |
| AccountError init | "ACCOUNT ERROR" | "Account Error" | (deactivate campaign) |
| Month1 converted | -- | "Active" | -- |
| AccountError converted | "ACTIVE" | "Active" | (reactivate campaign) |

## Appendix C: DNA/Play Custom Fields

| Field | Type | On Model | Description |
|---|---|---|---|
| dna_priority | EnumField | Dna (base) | Priority level for DNA tasks |
| intercom_link | TextField | Dna (base) | Link to Intercom conversation |
| (Process fields) | Various | Play (inherited) | All standard Process fields (office_phone, vertical, etc.) via multi-inheritance |

Play entities inherit ALL Process custom fields because Play extends both Process and Dna. The only DNA-specific fields are `dna_priority` and `intercom_link`.

## Appendix D: Default Dependency Wiring Rules

| Created Entity | Wired As Dependent On | Wired As Dependency Of |
|---|---|---|
| All Pipeline processes | Unit, OfferHolder (default dependents) | Open DNA plays (default dependencies) |
| BackendOnboardABusiness | -- | Implementation process |
| AssetEdit | -- | Implementation process |
| SourceVideographer | -- | (no dependency wiring -- standalone under VideographyHolder) |
| Non-Pipeline processes | -- | OfferHolder's open Dna dependents (recently completed < 30 days included) |

## Appendix E: Products-Driven Entity Creation

```
Products Field Evaluated During:
=================================

Onboarding.init_process() [stage 3]:
  Condition: any(p.lower().startswith("video") for p in self.products)
  Action: request_source_videographer
  Result: SourceVideographer created under Business.videography_holder

Pipeline.init_process() [stage >= 3]:
  Product synchronization:
  - Add new products from Process to Unit
  - Remove "marketing" products from Unit if:
    (a) not in Process's products AND
    (b) not in any other active pipeline process (stage >= 3) AND
    (c) offer is not active or activating

Process.converted():
  - Products on Process but not on Unit -> extend Unit.products

Process.did_not_convert() [Pipeline only]:
  - Remove Process's products from Unit.products
```

## Appendix F: File References

### Microservice Key Files

| File | Relevance |
|---|---|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/pipeline.py` | PipelineConversionRule (Sales->Onboarding) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/polling/action_executor.py` | ActionExecutor (3 action types) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/base.py` | WorkflowAction ABC |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py` | ConversationAuditWorkflow (the smell to refactor) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py` | Business entity + DNAHolder |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py` | Process + ProcessType enum + ProcessHolder |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/dna.py` | DNA stub (navigation only) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/entry.py` | EntryType + cache entry hierarchy |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/settings.py` | Overflow thresholds |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | TTLs and warm priorities |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/actions.py` | SaveSession dependency add/remove primitives |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/hierarchy_warmer.py` | Ancestor warming for hierarchy traversal |

### Legacy Key Files

| File | Relevance |
|---|---|
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` | Process base: resolution chains, field defaults, default deps |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/main.py` | Pipeline base: auto-completion, product sync |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/implementation/main.py` | Implementation: BackendOB + AssetEdit creation |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/managers/process_manager/main.py` | ProcessManager: routing, template duplication, duplicate detection |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/managers/process_manager/dna_manager/main.py` | DnaManager: play routing |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna/main.py` | Dna base: custom fields, holder resolution |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna/play/main.py` | Play: multi-inheritance (Process + Dna) |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna/play/isolated_play/main.py` | IsolatedPlay: removes default project, sets TIER_1 rep |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna/play/isolated_play/backend_onboard_a_business/main.py` | BackendOnboardABusiness: created during Implementation init |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna/play/isolated_play/pause_a_business_unit/main.py` | PauseABusinessUnit: deactivates all active offers |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna/play/isolated_play/question_on_performance/main.py` | QuestionOnPerformance: AI analysis, reporting columns |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/dna_holder/main.py` | DnaHolder: open_plays, open_backend_onboardings |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/main/actions.py` | Tag-based routing dispatch (route_*, request_*, play_*) |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/project/models/backend_client_success_dna/main.py` | BackendClientSuccessDna project (GID: 1167650840134033) |
| `/Users/tomtenuta/code/autom8/apis/asana_api/objects/project/models/backend_onboard_a_businesss/main.py` | BackendOnboardABusiness project (GID: 1207507299545000) |
