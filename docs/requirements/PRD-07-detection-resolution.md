# PRD-07: Detection & Resolution

> Consolidated PRD for entity detection, cross-holder resolution, and workspace registry.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-DETECTION, PRD-0014 (Cross-Holder Resolution), PRD-WORKSPACE-PROJECT-REGISTRY
- **Related TDDs**: TDD-09-registry-seeding, TDD-11-resolution-hardening

---

## Executive Summary

The autom8_asana SDK requires reliable mechanisms to identify entity types from Asana tasks and resolve relationships that cross holder boundaries. This consolidated PRD addresses three interconnected problems:

1. **Entity Detection**: The current name-based detection has ~0% accuracy in production because actual task names (e.g., "Duong Chiropractic Inc - Chiropractic Offers") do not match expected patterns (e.g., "offers").

2. **Cross-Holder Resolution**: Entities like AssetEdit need to resolve to their owning Unit/Offer, but live outside the containment hierarchy, requiring multi-strategy resolution logic.

3. **Workspace Project Discovery**: Process entities in pipeline projects cannot be detected because pipeline project GIDs are not statically registered.

The solution introduces a tiered detection system, a resolution framework with transparent strategy selection, and dynamic workspace project discovery.

---

## Problem Statement

### Detection Failure

The SDK's entity type detection is fundamentally broken. Detection accuracy in production is approximately **0%** because:

| Expected Input | Actual Production Data |
|----------------|------------------------|
| `"offers"` | `"Duong Chiropractic Inc - Chiropractic Offers"` |
| `"contacts"` | `"Acme Corp - Business Contacts"` |
| N/A | `"$49 Complete Chiropractic Health Screening"` |

The legacy autom8 system uses **project membership** as the source of truth, but the SDK attempted name pattern matching as a shortcut. This affects:

- **Hydration system**: Cannot identify parent entity types during upward traversal
- **Webhook handlers**: Cannot determine entity type from task GID
- **Type-safe navigation**: Cannot convert generic Tasks to typed entities
- **Self-healing workflows**: Cannot detect entities needing project membership repair

### Cross-Holder Resolution Gap

Hierarchical navigation works well (offer.unit, unit.business), but **cross-holder relationships** require domain logic the SDK does not encapsulate:

```
Business
  +-- AssetEditHolder
  |     +-- AssetEdit (process task)     <-- START: Need owning Unit/Offer
  |
  +-- UnitHolder
        +-- Unit                          <-- TARGET: Which Unit?
              +-- OfferHolder
                    +-- Offer             <-- TARGET: Which Offer?
```

Every consumer currently reimplements resolution logic, leading to:
- Duplicated domain logic across consumers
- Inconsistent behavior between implementations
- No transparency about which resolution strategy succeeded
- Undefined behavior for ambiguous matches

### Pipeline Project Discovery Failure

Process entities in pipeline projects fail detection entirely:

| Entity Type | Project Assignment | Detection Result |
|-------------|-------------------|------------------|
| Business | Single dedicated project | Tier 1 success |
| Contact | Single dedicated project | Tier 1 success |
| **Process** | **Multiple pipeline projects** | **Tier 5 UNKNOWN** |

Pipeline projects (Sales, Onboarding, Retention, etc.) cannot be statically mapped because:
- There are 7+ pipeline projects per ProcessType
- GIDs vary between workspaces/deployments
- `Process.PRIMARY_PROJECT_GID = None` by design

---

## Goals & Non-Goals

### Goals

**Detection System**:
1. Deterministic detection via project membership (Tier 1 = 100% accuracy)
2. Zero API calls for primary detection path
3. Graceful degradation through detection tiers
4. Self-healing flag for entities needing project membership repair

**Resolution System**:
5. AssetEdit resolution to owning Unit and Offer
6. Strategy transparency in resolution results
7. Clear, consistent ambiguity handling
8. Batch resolution for collections (high-frequency use case)

**Workspace Registry**:
9. Dynamic pipeline project discovery at runtime
10. Name-to-GID mapping with O(1) lookup
11. ProcessType derivation from project name
12. No hardcoded GIDs required for pipeline automation

### Non-Goals

| Item | Rationale |
|------|-----------|
| Multi-workspace support | Single workspace sufficient for V1 |
| Resolution caching | Different semantics than hierarchy cache |
| Bidirectional resolution (Unit -> AssetEdits) | Inverse pattern; different use case |
| Process subtype detection | Multiple projects map to PROCESS; defer |
| Confidence scoring API | Tier information sufficient for MVP |
| Real-time project change sync | Refresh-on-demand is sufficient |

---

## Requirements

### R1: Detection System

#### R1.1 Project Type Registry

**Must Have**:
- Registry maps project GIDs to EntityType with O(1) lookup
- Each entity class declares `PRIMARY_PROJECT_GID` as ClassVar
- Auto-population via `__init_subclass__` hook
- Environment variable override pattern: `ASANA_PROJECT_{ENTITY_TYPE}`
- All Process project GIDs (12+) map to `EntityType.PROCESS`

**Acceptance Criteria**:
- [ ] Registry is `dict[str, EntityType]` populated at module load
- [ ] Duplicate GID registration raises `ValueError`
- [ ] Missing GID for expected entity logs warning
- [ ] Env var takes precedence over hardcoded default

#### R1.2 Detection Result Model

**Must Have**:
- `DetectionResult` dataclass with fields:
  - `entity_type: EntityType`
  - `tier_used: int` (1-5)
  - `needs_healing: bool`
  - `expected_project_gid: str | None`
- `__bool__` returns `False` for UNKNOWN, `True` otherwise

#### R1.3 Tiered Detection

**Tier 1 - Project Membership (Must Have)**:
- Checks `task.memberships[0].project.gid`
- O(1) registry lookup
- Zero API calls
- Returns `tier=1, needs_healing=False` on success

**Tier 2 - Name Convention (Should Have)**:
- Matches holder names by suffix/contains pattern (case insensitive)
- Patterns: `*Contacts*`, `*Units*`, `*Offers*`, `*Processes*`, etc.
- Returns `tier=2, needs_healing=True`

**Tier 3 - Parent Type Inference (Should Have)**:
- Requires parent entity type context
- Infers child type from known parent (ContactHolder -> CONTACT)
- Returns `tier=3, needs_healing=True`

**Tier 4 - Structure Inspection (Could Have)**:
- Disabled by default (`allow_structure_inspection=True`)
- Fetches subtasks to identify entity structure
- Requires API calls

**Tier 5 - Unknown (Must Have)**:
- Returns `EntityType.UNKNOWN, tier=5, needs_healing=True`
- Logs warning with task GID and name
- Never raises exception

#### R1.4 Detection Functions

**Must Have**:
- `detect_entity_type(task, parent_type=None) -> DetectionResult` (sync, Tiers 1-3)
- `detect_entity_type_async(task, client, parent_type=None, allow_structure_inspection=False) -> DetectionResult`

**Should Have**:
- Backward-compatible signatures preserved
- Deprecation warnings for old patterns

### R2: Self-Healing Integration

#### R2.1 Healing Flag

**Must Have**:
- `needs_healing = True` when `tier_used > 1`
- `expected_project_gid` populated from entity class's `PRIMARY_PROJECT_GID`

#### R2.2 SaveSession Healing

**Should Have**:
- `SaveSession(client, auto_heal=False)` parameter
- When enabled, adds missing project memberships via `add_to_project`
- Healing is additive only (never removes memberships)
- Per-entity override: `session.track(entity, heal=False)`

**Should Have**:
- `SaveResult.healed_entities: list[str]` - GIDs successfully healed
- `SaveResult.healing_failures: list[HealingFailure]` - Failed operations

### R3: Cross-Holder Resolution

#### R3.1 AssetEdit Entity

**Must Have (Prerequisite)**:
- `AssetEdit` class extending `Process`
- 11 typed field accessors:
  - `asset_approval`, `asset_id`, `editor`, `reviewer`
  - `offer_id` (key for EXPLICIT_OFFER_ID strategy)
  - `raw_assets`, `review_all_ads`, `score`
  - `specialty`, `template_id`, `videos_paid`
- `AssetEditHolder.asset_edits` property returning typed children
- mypy strict mode compliance

#### R3.2 TasksClient.dependents_async()

**Must Have (Prerequisite)**:
- `dependents_async(task_gid, *, opt_fields=None, limit=100) -> PageIterator[Task]`
- Calls Asana API: `GET /tasks/{task_gid}/dependents`
- Handles 30 dependents+dependencies combined limit

#### R3.3 Resolution Methods

**Must Have**:
- `AssetEdit.resolve_unit_async(client, *, strategy=AUTO) -> ResolutionResult[Unit]`
- `AssetEdit.resolve_offer_async(client, *, strategy=AUTO) -> ResolutionResult[Offer]`

**Should Have**:
- Sync wrappers using `@sync_wrapper` pattern

#### R3.4 Resolution Result

**Must Have**:
- `ResolutionResult[T]` with fields:
  - `entity: T | None`
  - `strategy_used: ResolutionStrategy | None`
  - `strategies_tried: list[ResolutionStrategy]`
  - `ambiguous: bool`
  - `candidates: list[T]`
  - `error: str | None`
- `success` property: `True` if exactly one match found

#### R3.5 Resolution Strategies

**Must Have**:
- `ResolutionStrategy` enum:
  - `DEPENDENT_TASKS` - Priority 1 (most reliable)
  - `CUSTOM_FIELD_MAPPING` - Priority 2
  - `EXPLICIT_OFFER_ID` - Priority 3
  - `AUTO` - Try in priority order (default)

**DEPENDENT_TASKS**:
- Fetches task dependents via `dependents_async()`
- Identifies Unit in dependents chain
- Returns first Unit found

**CUSTOM_FIELD_MAPPING**:
- Matches AssetEdit.vertical to Unit.vertical
- Requires Business context
- Marks ambiguous if multiple Units match

**EXPLICIT_OFFER_ID**:
- Reads `self.offer_id` field
- Fetches Offer directly by GID
- Navigates to Unit via `offer.unit`

**AUTO Strategy Execution**:
- Executes strategies in priority order
- Stops at first successful (non-ambiguous) resolution
- Records all `strategies_tried`

#### R3.6 Ambiguity Handling

**No Matches Found**:
- Returns `entity=None, success=False, error="No matching entity found"`
- Does NOT raise exception

**Multiple Matches Found**:
- Returns `ambiguous=True, entity=first_match, candidates=[all_matches]`
- `success=False` (ambiguous is not success)
- AUTO mode continues to next strategy

**Strategy Failure**:
- API errors caught and logged
- Strategy returns "no match" on error
- AUTO mode continues to next strategy

#### R3.7 Batch Operations

**Should Have**:
- `resolve_units_async(asset_edits, client, *, strategy=AUTO) -> dict[str, ResolutionResult[Unit]]`
- `resolve_offers_async(asset_edits, client, *, strategy=AUTO) -> dict[str, ResolutionResult[Offer]]`
- Optimizes shared lookups (fetch Business units once)
- Uses concurrent fetching where possible

### R4: Workspace Project Registry

#### R4.1 Project Discovery

**Must Have**:
- Discovers all workspace projects via `GET /workspaces/{workspace_gid}/projects`
- Handles pagination for >100 projects
- Excludes archived projects by default
- Discovery completes in <3 seconds for typical workspace

#### R4.2 Name-to-GID Mapping

**Must Have**:
- `get_by_name(name) -> str | None` returns GID in O(1) time
- Case-insensitive matching
- Whitespace normalized
- Returns `None` for unknown names

#### R4.3 Discovery Timing

**Must Have**:
- Lazy discovery: Triggered on first detection for unregistered GID
- Explicit discovery: `await registry.discover_async(workspace_gid)`
- Idempotent (repeated calls refresh, don't duplicate)

#### R4.4 Pipeline Project Registration

**Must Have**:
- Identifies pipeline projects by ProcessType in name (case-insensitive)
- ProcessTypes: LEAD, SALES, ONBOARDING, PRODUCTION, RETENTION, OFFBOARDING, ARCHIVE
- Registers as `EntityType.PROCESS` in ProjectTypeRegistry
- Static registrations preserved (not overwritten)

**Must Have**:
- `get_process_type(project_gid) -> ProcessType | None`
- Returns ProcessType that matched during identification
- O(1) lookup after discovery

#### R4.5 Detection Integration

**Must Have**:
- Tier 1 detection succeeds for tasks in discovered pipeline projects
- Returns `EntityType.PROCESS, tier=1, needs_healing=False`
- Detection function signatures unchanged

#### R4.6 Backward Compatibility

**Must Have**:
- Static `PRIMARY_PROJECT_GID` registration unchanged
- Static registrations take precedence for same GID
- Environment variable override unchanged
- All existing tests pass without modification

---

## User Stories

### US-001: Webhook Handler Detection

**As a** webhook handler developer
**I want to** determine the type of a task received via webhook
**So that** I can route it to the appropriate handler

```python
async def handle_task_webhook(task_gid: str):
    task = await client.tasks.get_async(task_gid)
    result = detect_entity_type(task)

    if result.entity_type == EntityType.OFFER:
        await handle_offer_update(Offer.model_validate(task.model_dump()))
    elif result.entity_type == EntityType.UNKNOWN:
        logger.warning(f"Unknown entity type for task {task_gid}")
```

### US-002: Cross-Holder Resolution

**As a** webhook handler developer
**I want to** resolve an AssetEdit to its owning Unit
**So that** I can access Unit-level settings when processing changes

```python
async def handle_asset_edit_webhook(asset_edit_gid: str):
    task = await client.tasks.get_async(asset_edit_gid)
    asset_edit = AssetEdit.model_validate(task.model_dump())

    result = await asset_edit.resolve_unit_async(client)

    if result.success:
        unit = result.entity
        print(f"Resolved via: {result.strategy_used}")
    elif result.ambiguous:
        print(f"Multiple Units: {[u.name for u in result.candidates]}")
```

### US-003: Pipeline Process Detection

**As a** pipeline automation engine
**I want to** detect Process entities in pipeline projects
**So that** I can trigger conversion rules on stage advancement

```python
# After discovery, detection works for pipeline projects
task_in_sales = await client.tasks.get_async(task_gid)
result = detect_entity_type(task_in_sales)  # Returns PROCESS (tier 1)

process = Process.model_validate(task_in_sales.model_dump())
print(process.process_type)  # ProcessType.SALES
```

### US-004: Batch Resolution for Reporting

**As a** reporting developer
**I want to** resolve all AssetEdits to Units efficiently
**So that** I can aggregate metrics by Unit

```python
async def generate_report(business_gid: str):
    business = await Business.from_gid_async(client, business_gid)
    asset_edits = business.asset_edit_holder.asset_edits

    results = await resolve_units_async(asset_edits, client)

    by_unit = defaultdict(list)
    for ae in asset_edits:
        result = results[ae.gid]
        unit_name = result.entity.name if result.success else "Unresolved"
        by_unit[unit_name].append(ae)
```

### US-005: Self-Healing Save

**As a** SDK user
**I want to** automatically repair entities missing project membership
**So that** future detection works correctly

```python
async def save_with_healing(entity: BusinessEntity):
    async with SaveSession(client, auto_heal=True) as session:
        session.track(entity)
        result = await session.commit_async()

        if result.healed_entities:
            logger.info(f"Healed {len(result.healed_entities)} entities")
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Detection accuracy (entities with project membership) | ~0% | 100% |
| Detection accuracy (Tiers 2-4 fallback) | ~0% | >80% |
| Tier 1 detection latency | N/A | <1ms |
| API calls for Tier 1 detection | N/A | 0 |
| Process detection in pipeline projects | 0% | 100% |
| Hardcoded GIDs in demo scripts | Required | Zero |
| Name-to-GID resolution | Per-request API | O(1) cached |
| Workspace discovery time | N/A | <3 seconds |
| AssetEdit typed field accessors | 0 | 11 |
| Strategy transparency in resolution | N/A | strategy_used field |
| Existing tests pass | 100% | 100% |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `Task.memberships` field | Implemented | Required for Tier 1 |
| `SaveSession.add_to_project()` | Implemented | Required for healing |
| `EntityType` enum | Implemented | May need PROCESS_HOLDER |
| `ProjectsClient.list_async(workspace=...)` | Implemented | For discovery |
| `AsanaClient.default_workspace_gid` | Implemented | For workspace context |
| `ProcessType` enum | Implemented | 7 pipeline stages |
| `Process` base class | Implemented | AssetEdit extends |
| `CustomFieldAccessor` | Implemented | For typed fields |
| Asana API dependents endpoint | Available | For resolution |

---

## Appendix A: Entity Type to Project GID Mapping

| EntityType | Project GID | Env Var |
|------------|-------------|---------|
| BUSINESS | `1200653012566782` | `ASANA_PROJECT_BUSINESS` |
| CONTACT | `1200775689604552` | `ASANA_PROJECT_CONTACT` |
| CONTACT_HOLDER | `1201500116978260` | `ASANA_PROJECT_CONTACT_HOLDER` |
| UNIT | `1201081073731555` | `ASANA_PROJECT_UNIT` |
| UNIT_HOLDER | `1204433992667196` | `ASANA_PROJECT_UNIT_HOLDER` |
| OFFER | `1143843662099250` | `ASANA_PROJECT_OFFER` |
| OFFER_HOLDER | `1210679066066870` | `ASANA_PROJECT_OFFER_HOLDER` |
| LOCATION | `1200836133305610` | `ASANA_PROJECT_LOCATION` |
| HOURS | `1201614578074026` | `ASANA_PROJECT_HOURS` |
| DNA_HOLDER | `1167650840134033` | `ASANA_PROJECT_DNA_HOLDER` |
| RECONCILIATIONS_HOLDER | `1203404998225231` | `ASANA_PROJECT_RECONCILIATION_HOLDER` |
| ASSET_EDIT_HOLDER | `1203992664400125` | `ASANA_PROJECT_ASSET_EDIT_HOLDER` |
| VIDEOGRAPHY_HOLDER | `1207984018149338` | `ASANA_PROJECT_VIDEOGRAPHY_HOLDER` |
| LOCATION_HOLDER | N/A | N/A (no project) |
| PROCESS_HOLDER | N/A | N/A (no project) |
| PROCESS | Multiple (pipeline projects) | Multiple |

**Process Project GIDs** (all map to EntityType.PROCESS):

| Process Type | Project GID |
|--------------|-------------|
| Onboarding | `1201319387632570` |
| Implementation | `1201476141989746` |
| Consultation | `1201532776033312` |
| Sales | `1200944186565610` |
| Retention | `1201346565918814` |
| Expansion | `1201265144487557` |
| Outreach | `1201753128450029` |
| Reactivation | `1201265144487549` |
| Account Error | `1201684018234520` |
| Videographer Sourcing | `1206176773330155` |
| Activation Consultation | `1209247943184021` |
| Practice of Week | `1209247943184017` |

---

## Appendix B: Detection Tier Flow

```
Task Input
    |
    v
[Tier 1] Project Membership Lookup
    |-- Found in static registry --> Return (tier=1, needs_healing=False)
    |-- Found in discovered pipeline registry --> Return (tier=1, needs_healing=False)
    |-- Not found --> Continue
    v
[Tier 2] Name Pattern Matching
    |-- Pattern matches --> Return (tier=2, needs_healing=True)
    |-- No match --> Continue
    v
[Tier 3] Parent Type Inference (if parent_type provided)
    |-- Can infer type --> Return (tier=3, needs_healing=True)
    |-- Cannot infer --> Continue
    v
[Tier 4] Structure Inspection (if allow_structure_inspection=True)
    |-- Structure matches --> Return (tier=4, needs_healing=True)
    |-- No match --> Continue
    v
[Tier 5] Unknown
    |-- Return (entity_type=UNKNOWN, tier=5, needs_healing=True)
```

---

## Appendix C: Resolution Strategy Flow

```
AssetEdit.resolve_unit_async(strategy=AUTO)
    |
    v
[DEPENDENT_TASKS]
    | Found Unit via dependents?
    +-- YES --> Return ResolutionResult(entity=Unit, strategy_used=DEPENDENT_TASKS)
    +-- NO/ERROR --> Continue
    v
[CUSTOM_FIELD_MAPPING]
    | AssetEdit.vertical matches Unit.vertical?
    +-- YES (single) --> Return ResolutionResult(entity=Unit)
    +-- YES (multiple) --> Mark ambiguous, continue
    +-- NO --> Continue
    v
[EXPLICIT_OFFER_ID]
    | AssetEdit.offer_id set and valid?
    +-- YES --> Fetch Offer, get Unit from offer.unit, Return
    +-- NO --> Continue
    v
[ALL STRATEGIES EXHAUSTED]
    | Any ambiguous results found?
    +-- YES --> Return ResolutionResult(entity=first_match, ambiguous=True)
    +-- NO --> Return ResolutionResult(entity=None, error="No matching entity found")
```

---

## Appendix D: ProcessType to Project Name Matching

| ProcessType | Example Matching Project Names |
|-------------|-------------------------------|
| LEAD | "Lead Pipeline", "New Leads" |
| SALES | "Sales Pipeline", "Active Sales" |
| ONBOARDING | "Client Onboarding", "Onboarding Process" |
| PRODUCTION | "Production", "Active Production" |
| RETENTION | "Retention Pipeline", "Client Retention" |
| OFFBOARDING | "Offboarding", "Client Offboarding" |
| ARCHIVE | "Archive", "Archived Processes" |

Matching is case-insensitive with configurable word boundary handling.
