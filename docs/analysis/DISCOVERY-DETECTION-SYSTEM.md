# Discovery Document: Detection System Replacement

**Author**: Requirements Analyst
**Date**: 2025-12-17
**Status**: Discovery Complete - Ready for PRD
**Replaces**: ADR-0068 (Name-Based Type Detection Strategy)

---

## 1. Current State Analysis

### 1.1 Current Detection Algorithm

**Location**: `/src/autom8_asana/models/business/detection.py` (lines 133-192)

```python
async def detect_entity_type_async(task: Task, client: AsanaClient) -> EntityType:
    # Phase 1: Name-based detection (works for holders)
    if detected := detect_by_name(task.name):
        return detected

    # Phase 2: Structure inspection (needed for Business/Unit)
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    if subtask_names & {"contacts", "units", "location"}:
        return EntityType.BUSINESS

    # Unit has offer/process holder subtasks
    if subtask_names & {"offers", "processes"}:
        return EntityType.UNIT

    return EntityType.UNKNOWN
```

**Name-based detection** (lines 86-96) uses a hardcoded map:
```python
HOLDER_NAME_MAP: dict[str, EntityType] = {
    "contacts": EntityType.CONTACT_HOLDER,
    "units": EntityType.UNIT_HOLDER,
    "offers": EntityType.OFFER_HOLDER,
    "processes": EntityType.PROCESS_HOLDER,
    "location": EntityType.LOCATION_HOLDER,
    "dna": EntityType.DNA_HOLDER,
    "reconciliations": EntityType.RECONCILIATIONS_HOLDER,
    "asset edit": EntityType.ASSET_EDIT_HOLDER,
    "videography": EntityType.VIDEOGRAPHY_HOLDER,
}
```

### 1.2 Why Detection Fails

| Issue | Expected | Actual |
|-------|----------|--------|
| Holder names | `"offers"` | `"Duong Chiropractic Inc - Chiropractic Offers"` |
| Subtask names | `"contacts"`, `"units"` | Decorated business-prefixed names |
| Leaf entities | N/A (no pattern) | `"$49 Complete Chiropractic Health Screening"` |

**Root Cause**: The current system assumes holder names are simple strings matching `HOLDER_NAME_MAP`. In production, holder names are decorated with business context and emoji. The algorithm cannot detect:
- Leaf entities (Offer, Contact, Location, Process, Hours) - no detection path at all
- Holders with decorated names
- Any entity reliably

**Detection accuracy**: Approximately 0% in production.

### 1.3 EntityType Enum Complete Values

**Location**: `/src/autom8_asana/models/business/detection.py` (lines 41-81)

| Value | Description |
|-------|-------------|
| `BUSINESS` | Root entity |
| `CONTACT_HOLDER` | Business-level holder |
| `UNIT_HOLDER` | Business-level holder |
| `LOCATION_HOLDER` | Business-level holder |
| `DNA_HOLDER` | Business-level holder |
| `RECONCILIATIONS_HOLDER` | Business-level holder |
| `ASSET_EDIT_HOLDER` | Business-level holder |
| `VIDEOGRAPHY_HOLDER` | Business-level holder |
| `OFFER_HOLDER` | Unit-level holder |
| `PROCESS_HOLDER` | Unit-level holder |
| `UNIT` | Composite entity |
| `CONTACT` | Leaf entity |
| `OFFER` | Leaf entity |
| `PROCESS` | Leaf entity |
| `LOCATION` | Leaf entity |
| `HOURS` | Leaf entity |
| `UNKNOWN` | Fallback |

---

## 2. Project GID Inventory

### 2.1 Confirmed Mappings from Legacy System

**Source**: `/autom8/apis/asana_api/objects/project/models/*/main.py`

| EntityType | Project Name | Project GID | Legacy Class | Status |
|------------|--------------|-------------|--------------|--------|
| **BUSINESS** | Businesses | `1200653012566782` | `Businesses` | CONFIRMED |
| **CONTACT_HOLDER** | Contact Holder | `1201500116978260` | `ContactHolder` | CONFIRMED |
| **CONTACT** | Contacts | `1200775689604552` | `Contacts` | CONFIRMED |
| **UNIT_HOLDER** | Units | `1204433992667196` | `Units` | CONFIRMED |
| **UNIT** | Business Units | `1201081073731555` | `BusinessUnits` | CONFIRMED |
| **OFFER_HOLDER** | Offer Holders | `1210679066066870` | `OfferHolders` | CONFIRMED |
| **OFFER** | Business Offers | `1143843662099250` | `BusinessOffers` | CONFIRMED |
| **LOCATION** | Locations | `1200836133305610` | `Locations` | CONFIRMED |
| **HOURS** | Hours | `1201614578074026` | `Hours` | CONFIRMED |
| **RECONCILIATIONS_HOLDER** | Reconciliations | `1203404998225231` | `Reconciliations` | CONFIRMED |
| **ASSET_EDIT_HOLDER** | Asset Edit Holder | `1203992664400125` | `AssetEditHolder` | CONFIRMED |
| **VIDEOGRAPHY_HOLDER** | Videography Services | `1207984018149338` | `VideographyServices` | CONFIRMED |
| **LOCATION_HOLDER** | N/A | N/A | N/A | SPECIAL CASE |
| **DNA_HOLDER** | N/A (Backend DNA) | `1167650840134033` | `BackendClientSuccessDna` | NEEDS VERIFICATION |
| **PROCESS_HOLDER** | N/A | N/A | N/A | MISSING |
| **PROCESS** | (Multiple) | (Multiple) | `ProcessProject` subclasses | SPECIAL CASE |

### 2.2 Special Cases

**LocationHolder**: NO project membership.
- LocationHolder is identified purely by parent reference (Business -> subtask named "Location")
- Detection must fall back to Tier 2 (parent-based) or Tier 3 (name-based)

**ProcessHolder**: NO dedicated project.
- ProcessHolder tasks are not in any project
- Detection must fall back to parent-based detection

**Process**: Multiple process-type projects exist.
- Onboarding: `1201319387632570`
- Implementation: `1201476141989746`
- Consultation: `1201532776033312`
- Sales: `1200944186565610`
- Retention: `1201346565918814`
- And many more...
- Process type is determined by which project, not just "is it a Process"

---

## 3. Legacy Pattern Documentation

### 3.1 How autom8 Detects Entity Types

**Pattern**: Project membership in `__post_init__`

**Location**: `/autom8/apis/asana_api/objects/task/models/business/main.py` (lines 69, 114-116)

```python
@dataclass
class Business(Task):
    PRIMARY_PROJECT_GID = Businesses.PROJECT_GID

    def __post_init__(self):
        if not any(p.gid == Businesses.PROJECT_GID for p in self.projects):
            self.projects.add(Businesses())
```

**Key insight**: Legacy system uses `__post_init__` to ENFORCE project membership if missing. This is a form of "self-healing" - if entity lacks project membership, it is added automatically.

### 3.2 How autom8 Enforces Project Membership

**Enforcement via DEFAULT**: Task creation automatically includes project.

**Location**: `/autom8/apis/asana_api/objects/task/models/offer/main.py` (lines 110, 193-196)

```python
@dataclass
class Offer(Task):
    PRIMARY_PROJECT_GID = BusinessOffers.PROJECT_GID

    def __init__(self, *args, **kwargs):
        self.default_projects = [self._get_default_project()]
        super().__init__(*args, **kwargs)
```

**Pattern to adopt**:
1. Define `PRIMARY_PROJECT_GID` as ClassVar on each entity
2. Build project-to-type registry at runtime from these ClassVars
3. Optionally enforce membership in `model_validator`

### 3.3 Project GID Constants Location

Legacy constants are defined in project model files:
- `/autom8/apis/asana_api/objects/project/models/businesses/main.py`: `PROJECT_GID = "1200653012566782"`
- `/autom8/apis/asana_api/objects/project/models/business_offers/main.py`: `PROJECT_GID = "1143843662099250"`
- etc.

**Pattern to adopt**: Either:
- Define GIDs directly on entity models as ClassVars (code-as-config)
- Load from environment variables (12-factor app style)
- Hybrid: Default in code, env var override

### 3.4 Patterns to Adopt vs Avoid

**Adopt:**
- `PRIMARY_PROJECT_GID` ClassVar on each entity
- Project membership as source of truth
- Self-healing in `__post_init__` / `model_validator`
- Registry built from model introspection

**Avoid:**
- Hardcoded name-based detection
- Subtask structure inspection (requires API call)
- Emoji-based fallback (unreliable)

---

## 4. Integration Points

### 4.1 SaveSession Action Operations

**Location**: `/src/autom8_asana/persistence/session.py` (lines 860-933)

Available healing operations:
- `session.add_to_project(task, project_gid)` - Add entity to correct project
- `session.remove_from_project(task, project_gid)` - Remove from wrong project
- `session.set_parent(task, parent_gid)` - Fix parent hierarchy

**Healing implementation pattern**:
```python
async with SaveSession(client) as session:
    session.track(entity)

    # Detection result indicates missing membership
    if detection_result.needs_healing:
        session.add_to_project(entity, detection_result.expected_project_gid)

    await session.commit_async()
```

### 4.2 Where Detection is Called From

1. **Hydration** (`/src/autom8_asana/models/business/hydration.py`):
   - `_traverse_upward_async()` calls `detect_entity_type_async()` during upward traversal
   - Used to identify entity type when navigating from leaf to root

2. **Direct usage**:
   - `detect_by_name()` - Sync holder detection
   - `detect_entity_type_async()` - Full detection with fallback

### 4.3 How Detection Results are Used

Detection results map to typed entity classes:
- `EntityType.BUSINESS` -> `Business`
- `EntityType.OFFER` -> `Offer`
- etc.

The typed entity is then instantiated via `model_validate()`:
```python
if entity_type == EntityType.BUSINESS:
    business = Business.model_validate(task.model_dump())
```

---

## 5. Configuration Strategy Analysis

### 5.1 Current Env Var Patterns in SDK

**Location**: `/src/autom8_asana/` (various files)

| Pattern | Example | Usage |
|---------|---------|-------|
| `ASANA_PAT` | Token auth | Required |
| `ASANA_CACHE_S3_ENABLED` | Cache toggle | Optional |
| `ASANA_CACHE_S3_BUCKET` | Bucket name | Conditional |

**Naming convention**: `ASANA_*` prefix for SDK settings.

### 5.2 Proposed Env Var Pattern

```bash
# Entity type project GIDs
ASANA_PROJECT_BUSINESS=1200653012566782
ASANA_PROJECT_CONTACT=1200775689604552
ASANA_PROJECT_CONTACT_HOLDER=1201500116978260
ASANA_PROJECT_UNIT=1201081073731555
ASANA_PROJECT_UNIT_HOLDER=1204433992667196
ASANA_PROJECT_OFFER=1143843662099250
ASANA_PROJECT_OFFER_HOLDER=1210679066066870
ASANA_PROJECT_LOCATION=1200836133305610
ASANA_PROJECT_HOURS=1201614578074026
ASANA_PROJECT_RECONCILIATION_HOLDER=1203404998225231
ASANA_PROJECT_ASSET_EDIT_HOLDER=1203992664400125
ASANA_PROJECT_VIDEOGRAPHY_HOLDER=1207984018149338
```

### 5.3 Multi-Workspace Considerations

The current SDK serves a **single workspace**. Project GIDs are workspace-specific.

**Future consideration**: If SDK needs to support multiple workspaces:
- Option A: Namespace by workspace: `ASANA_WS_<workspace_gid>_PROJECT_BUSINESS=...`
- Option B: Config file with workspace sections
- Option C: Runtime configuration passed to client

**Recommendation**: Defer multi-workspace to Phase 2. Current implementation assumes single workspace (matching legacy system behavior).

---

## 6. Gap Analysis

| Capability | Current | Required | Gap |
|------------|---------|----------|-----|
| **Tier 1: Project Membership** | Not implemented | Primary detection method | Full implementation |
| **Tier 2: Parent-Based** | Not implemented | For LocationHolder, ProcessHolder | Full implementation |
| **Tier 3: Name-Based** | Implemented (broken) | Fallback for edge cases | Fix and demote to fallback |
| **Tier 4: Structure Inspection** | Implemented (broken) | Optional last resort | Fix and make optional |
| **Self-Healing** | Not implemented | Add missing project memberships | Full implementation |
| **Registry Population** | Not implemented | Map PROJECT_GID -> EntityType | Full implementation |
| **Configuration** | No env vars | Env var override for GIDs | Full implementation |
| **PRIMARY_PROJECT_GID ClassVar** | Declared (None) | Populated per entity | Values needed |
| **Confidence Scoring** | Not implemented | Optional metadata | Design decision |

### 6.1 PRIMARY_PROJECT_GID Status by Model

**Location**: `/src/autom8_asana/models/business/base.py` (line 209)

```python
class BusinessEntity(Task):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None  # Override in subclasses
```

| Entity | Current Value | Required Value |
|--------|---------------|----------------|
| Business | `None` | `1200653012566782` |
| ContactHolder | `None` | `1201500116978260` |
| Contact | `None` | `1200775689604552` |
| UnitHolder | `None` | `1204433992667196` |
| Unit | `None` | `1201081073731555` |
| OfferHolder | `None` | `1210679066066870` |
| Offer | `None` | `1143843662099250` |
| ProcessHolder | N/A | N/A (no project) |
| Process | N/A | (multiple per type) |
| LocationHolder | N/A | N/A (no project) |
| Location | `None` | `1200836133305610` |
| Hours | `None` | `1201614578074026` |
| DNAHolder | `None` | `1167650840134033` |
| ReconciliationHolder | `None` | `1203404998225231` |
| AssetEditHolder | `None` | `1203992664400125` |
| VideographyHolder | `None` | `1207984018149338` |

---

## 7. Open Questions Resolution

### Detection Strategy Questions

**Q1: First membership vs explicit primary**: When a task has multiple project memberships, how to determine canonical type?

**RESOLVED**: Use first membership (`memberships[0].project.gid`).
- Legacy system uses this pattern
- API evidence confirms single primary membership for business entities
- Multiple memberships occur for cross-project tasks (rare in business hierarchy)

**Q2: Registry population timing**: At import, first access, or client initialization?

**DEFER to Architecture**: Options:
- Import time: Simplest, but requires all env vars present
- First access (lazy): More flexible, but threading concerns
- Client init: Explicit lifecycle, recommended

**Q3: Fallback chain termination**: Should Tier 4 (structure inspection) be optional?

**RESOLVED**: Yes, make Tier 4 optional and disabled by default.
- Requires API call (expensive)
- Rarely needed with project-based detection
- Can enable via flag: `detect_entity_type_async(task, client, allow_structure_inspection=False)`

**Q4: Confidence exposure**: Should detection return confidence scores to consumers?

**DEFER to Architecture**: Consider returning structured result:
```python
@dataclass
class DetectionResult:
    entity_type: EntityType
    tier_used: int  # 1-4
    needs_healing: bool
    expected_project_gid: str | None
```

### Self-Healing Questions

**Q5: Healing trigger**: What detection result triggers healing flag?

**RESOLVED**: Healing triggered when:
- Tier 1 fails but Tier 2/3/4 succeeds
- OR entity is in wrong project
- Flag: `needs_healing = (detection_tier > 1) or project_mismatch`

**Q6: Healing scope**: Add missing membership, remove incorrect ones, or both?

**RESOLVED**: Add-only by default.
- Adding missing membership is safe
- Removing requires confirmation (could break workflows)
- Option: `healing_mode = "add" | "sync" | "prompt"`

**Q7: Healing opt-in**: `SaveSession(auto_heal=True)` or per-entity flag?

**DEFER to Architecture**: Recommend session-level flag with per-entity override:
```python
async with SaveSession(client, auto_heal=True) as session:
    session.track(entity, heal=False)  # Override for this entity
```

**Q8: Healing failures**: How should failed healing be reported/retried?

**RESOLVED**: Include in SaveResult.
- Failed healing -> `SaveResult.healing_failures: list[HealingFailure]`
- Retry left to consumer (don't auto-retry)
- Log warning but don't fail overall commit

### Configuration Questions

**Q9: Environment variable prefix**: `ASANA_PROJECT_*` or `AUTOM8_ASANA_PROJECT_*`?

**RESOLVED**: Use `ASANA_PROJECT_*`.
- Consistent with existing `ASANA_PAT`, `ASANA_CACHE_*`
- Shorter, clearer
- `AUTOM8_` prefix unnecessary (SDK is the autom8_asana package)

**Q10: Missing GID behavior**: Raise error, log warning, or silently skip Tier 1?

**RESOLVED**: Log warning and skip Tier 1.
- Production should have all GIDs configured
- Development may not have full config
- Fail-fast option: `strict_config=True` raises error

**Q11: Workspace isolation**: How do multi-workspace consumers configure per-workspace GIDs?

**DEFER to Phase 2**: Current system is single-workspace.
- Document as limitation
- Design extension point for future
- No immediate implementation needed

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Missing project GIDs in config** | Medium | High (detection fails) | Defaults in code, env var override |
| **Entity in wrong project** | Low | Medium (type mismatch) | Self-healing adds correct project |
| **LocationHolder/ProcessHolder detection** | Medium | Medium (fallback needed) | Tier 2 (parent-based) detection |
| **Multi-membership tasks** | Low | Low (first wins) | Document behavior, first membership rule |
| **Process multi-type** | Medium | Medium (wrong type) | Map all Process projects to PROCESS type |
| **Registry stale after project changes** | Low | Medium | Cache invalidation, startup validation |
| **Legacy system divergence** | Low | High | Sync GIDs from legacy on deploy |
| **Performance regression** | Low | Low | O(1) lookup vs current O(n) name scan |

---

## 9. Recommendations for PRD

### Must Have (P0)

1. **Project-based detection (Tier 1)**
   - Registry mapping `project_gid -> EntityType`
   - `PRIMARY_PROJECT_GID` ClassVar on all entities
   - O(1) lookup, no API calls

2. **Parent-based detection (Tier 2)**
   - For LocationHolder, ProcessHolder
   - Check parent type and holder name pattern

3. **Detection result structure**
   - Return tier used, healing flag, expected project

4. **Configuration via env vars**
   - `ASANA_PROJECT_*` pattern
   - Defaults in code

### Should Have (P1)

5. **Self-healing via SaveSession**
   - `auto_heal` flag on session
   - Add missing project memberships
   - Report in SaveResult

6. **Startup validation**
   - Verify project GIDs exist
   - Warn on missing config

### Could Have (P2)

7. **Name-based fallback (Tier 3)**
   - Keep existing but fix patterns
   - Only as last resort

8. **Structure inspection (Tier 4)**
   - Optional, disabled by default
   - For diagnostic use

### Won't Have (Defer)

9. Multi-workspace support
10. Confidence scoring API
11. Auto-retry healing failures

---

## Appendix A: File References

| File | Lines | Purpose |
|------|-------|---------|
| `/src/autom8_asana/models/business/detection.py` | 1-193 | Current detection module |
| `/src/autom8_asana/models/business/base.py` | 158-373 | BusinessEntity base class |
| `/src/autom8_asana/persistence/session.py` | 1-1840 | SaveSession with action operations |
| `/docs/analysis/DETECTION-SYSTEM-ANALYSIS.md` | All | Prior analysis document |
| `/autom8/apis/asana_api/objects/task/models/business/main.py` | All | Legacy Business model |
| `/autom8/apis/asana_api/objects/task/models/offer/main.py` | All | Legacy Offer model |
| `/autom8/apis/asana_api/objects/project/models/__init__.py` | All | Legacy project GID exports |

---

## Appendix B: Complete Project GID Reference

From legacy system (confirmed):

```python
PROJECT_GIDS = {
    # Core Business Entities
    "BUSINESS": "1200653012566782",
    "CONTACT": "1200775689604552",
    "UNIT": "1201081073731555",
    "OFFER": "1143843662099250",
    "LOCATION": "1200836133305610",
    "HOURS": "1201614578074026",

    # Business-Level Holders
    "CONTACT_HOLDER": "1201500116978260",
    "UNIT_HOLDER": "1204433992667196",
    "RECONCILIATION_HOLDER": "1203404998225231",
    "ASSET_EDIT_HOLDER": "1203992664400125",
    "VIDEOGRAPHY_HOLDER": "1207984018149338",
    "DNA_HOLDER": "1167650840134033",  # Backend Client Success DNA

    # Unit-Level Holders
    "OFFER_HOLDER": "1210679066066870",

    # Process Projects (all map to PROCESS entity type)
    "PROCESS_ONBOARDING": "1201319387632570",
    "PROCESS_IMPLEMENTATION": "1201476141989746",
    "PROCESS_CONSULTATION": "1201532776033312",
    "PROCESS_SALES": "1200944186565610",
    "PROCESS_RETENTION": "1201346565918814",
    "PROCESS_EXPANSION": "1201265144487557",
    "PROCESS_OUTREACH": "1201753128450029",
    "PROCESS_REACTIVATION": "1201265144487549",
    "PROCESS_ACCOUNT_ERROR": "1201684018234520",
    "PROCESS_VIDEOGRAPHER_SOURCING": "1206176773330155",
    "PROCESS_ACTIVATION_CONSULTATION": "1209247943184021",
    "PROCESS_PRACTICE_OF_WEEK": "1209247943184017",

    # Utility Projects (not entity detection)
    "PAID_CONTENT": "1202204184560785",
    "COMMISSION": "1201627461398630",
    "PAUSE_BUSINESS_UNIT": "1206330409791366",
    "QUESTION_ON_PERFORMANCE": "1205526136594283",
    "CUSTOMER_HEALTH": "1208848470341588",
    "OPTIMIZATION_NOTIFICATIONS": "1208231632857419",
    "CALENDAR_INTEGRATIONS": "1209442849265632",
    "ACCESS_PROCESSING": "1209442727608287",
    "BACKEND_ONBOARD": "1207507299545000",
}
```

---

**End of Discovery Document**
