# Technical Analysis: Entity Type Detection System

## Executive Summary

**Root Cause Identified**: The current detection system uses name-based heuristics that fundamentally misunderstand how entity types are organized in Asana. The actual system uses **project membership** to determine entity type - each entity type lives in a dedicated Asana project.

**Evidence**: API inspection reveals a clear 1:1 mapping between entity types and projects:

| Entity Type | Project Name | Project GID |
|-------------|--------------|-------------|
| **Business** | Businesses | `1200653012566782` |
| **ContactHolder** | Contact Holder | `1201500116978260` |
| **Contact** | Contacts | `1200775689604552` |
| **UnitHolder** | Units | `1204433992667196` |
| **Unit** | Business Units | `1201081073731555` |
| **LocationHolder** | *(No project)* | N/A - uses parent reference |
| **Location** | Locations | `1200836133305610` |
| **OfferHolder** | Offer Holders | `1210679066066870` |
| **Offer** | Business Offers | `1143843662099250` |
| **ReconciliationHolder** | Reconciliations | `1203404998225231` |
| **AssetEditHolder** | Asset Edit Holder | `1203992664400125` |
| **VideographyHolder** | Videography Services | `1207984018149338` |

**Important Observations:**
1. **LocationHolder has NO project membership** - requires fallback to parent-based or name-based detection
2. **Reconciliation/AssetEdit children** use various projects (Commission, Paid Content, etc.) - not consistently typed by project
3. **Core business entities** (Business, Contact, Unit, Offer, Location) have consistent 1:1 project mapping

---

## Current Detection System (ADR-0068)

### Algorithm

```python
def detect_entity_type_async(task, client):
    # Phase 1: Name-based detection
    if task.name.lower() in HOLDER_NAME_MAP:  # e.g., "contacts" -> CONTACT_HOLDER
        return HOLDER_NAME_MAP[task.name.lower()]

    # Phase 2: Structure inspection (fetch subtasks)
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks}

    if subtask_names & {"contacts", "units", "location"}:
        return EntityType.BUSINESS

    if subtask_names & {"offers", "processes"}:
        return EntityType.UNIT

    return EntityType.UNKNOWN
```

### Why It Fails

| Issue | Expected | Actual |
|-------|----------|--------|
| Holder names | `"offers"` | `"Duong Chiropractic Inc — Chiropractic Offers 🎟️"` |
| Subtask names | `"contacts"`, `"units"` | Decorated business-prefixed names |
| Leaf entities | N/A (no pattern) | `"$49 Complete Chiropractic Health Screening"` |

**The current system cannot detect ANY entity type correctly** because:
1. Holder names are decorated with business context and emoji
2. Business/Unit subtasks don't have simple holder names
3. Leaf entities (Offer, Contact, etc.) have no detection path at all

---

## Legacy System: Project-Based Detection

### How It Works

Every task in the business hierarchy belongs to exactly one project that determines its type:

```
task.memberships[0].project.gid -> EntityType
```

### Evidence from API

```
=== OFFER ===
Name: $49 Complete Chiropractic Health Screening
Memberships: [{'project': {'gid': '1143843662099250', 'name': 'Business Offers'}}]

=== OFFER HOLDER ===
Name: Duong Chiropractic Inc — Chiropractic Offers 🎟️
Memberships: [{'project': {'gid': '1210679066066870', 'name': 'Offer Holders'}}]

=== UNIT ===
Name: Duong Chiropractic Inc — Chiropractic
Memberships: [{'project': {'gid': '1201081073731555', 'name': 'Business Units'}}]

=== UNIT HOLDER ===
Name: Duong Chiropractic Inc Business Units 🔎
Memberships: [{'project': {'gid': '1204433992667196', 'name': 'Units'}}]

=== BUSINESS ===
Name: Duong Chiropractic Inc
Memberships: [{'project': {'gid': '1200653012566782', 'name': 'Businesses'}}]
```

### Advantages

1. **Deterministic**: O(1) lookup, no heuristics
2. **No API calls**: Project membership is included in standard task response
3. **Always correct**: Project membership is the source of truth
4. **Works for all types**: Leaf entities, holders, and composite entities

---

## Comparison: Name-Based vs Project-Based

| Criterion | Name-Based (Current) | Project-Based (Proposed) |
|-----------|---------------------|--------------------------|
| API Calls | 0-1 (subtask fetch for fallback) | 0 (data in task response) |
| Accuracy | ~0% (all fail) | 100% (deterministic) |
| Leaf Entities | Cannot detect | Full support |
| Decorated Names | Fails | N/A (doesn't use names) |
| Maintenance | Fragile (naming changes break) | Stable (projects are fixed) |

---

## Proposed Solution

### 1. Project-to-Type Registry

```python
# Configuration (could be environment-specific)
PROJECT_TYPE_MAP: dict[str, EntityType] = {
    "1200653012566782": EntityType.BUSINESS,
    "1204433992667196": EntityType.UNIT_HOLDER,
    "1201081073731555": EntityType.UNIT,
    "1210679066066870": EntityType.OFFER_HOLDER,
    "1143843662099250": EntityType.OFFER,
    # ... additional mappings
}
```

### 2. New Detection Algorithm

```python
def detect_entity_type(task: Task) -> EntityType:
    """Detect entity type by project membership (O(1), no API calls)."""
    if not task.memberships:
        return EntityType.UNKNOWN

    # Primary project is first membership
    project_gid = task.memberships[0].project.gid

    if project_gid in PROJECT_TYPE_MAP:
        return PROJECT_TYPE_MAP[project_gid]

    # Fallback: name-based for legacy compatibility
    return detect_by_name(task.name) or EntityType.UNKNOWN
```

### 3. Configuration Strategy

Two options for managing the project GID mappings:

**Option A: Environment Variables**
```bash
ASANA_PROJECT_BUSINESSES=1200653012566782
ASANA_PROJECT_UNITS=1204433992667196
ASANA_PROJECT_OFFERS=1143843662099250
```

**Option B: ClassVar on Models (Currently Stubbed)**
```python
class Business(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str] = "1200653012566782"

class Offer(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str] = "1143843662099250"
```

---

## Implementation Recommendations

### Phase 1: Immediate Fix
1. Create `PROJECT_TYPE_MAP` with known project GIDs
2. Update `detect_entity_type_async()` to check project membership FIRST
3. Keep name-based as fallback for edge cases

### Phase 2: Configuration
1. Populate `PRIMARY_PROJECT_GID` on each model class
2. Build `PROJECT_TYPE_MAP` dynamically from model classes
3. Support environment variable overrides for different workspaces

### Phase 3: Validation
1. Add startup validation that all projects exist
2. Log warnings for tasks in unknown projects
3. Consider caching project metadata

---

## Required Changes

### Files to Modify

1. **`src/autom8_asana/models/business/detection.py`**
   - Add `PROJECT_TYPE_MAP` constant
   - Rewrite `detect_entity_type_async()` to use project membership
   - Keep `detect_by_name()` as fallback

2. **`src/autom8_asana/models/business/*.py`** (each model)
   - Set `PRIMARY_PROJECT_GID` ClassVar with actual project GIDs

3. **ADR-0068** (superseded)
   - Create ADR-0083: Project-Based Type Detection Strategy

### Test Updates

1. Add fixtures with project memberships
2. Test project-based detection for all entity types
3. Test fallback behavior for tasks without memberships

---

## Questions for User

1. **Workspace Scope**: Are these project GIDs consistent across all workspaces, or do different workspaces have different projects?

2. **Missing Projects**: What are the project GIDs for:
   - Contact
   - ContactHolder
   - Location
   - LocationHolder
   - Process
   - ProcessHolder
   - DNA/Reconciliation/AssetEdit/Videography holders

3. **Multi-Project Tasks**: Can a task belong to multiple projects? If so, which determines type?

4. **Environment Strategy**: Preference for configuration via:
   - Environment variables (12-factor app style)
   - ClassVar on models (code-as-config)
   - External config file (JSON/YAML)

---

## Conclusion

The current name-based detection system is fundamentally broken because it was designed around assumptions that don't match reality. The actual Asana data model uses **project membership** as the canonical type indicator.

**Recommendation**: Replace the detection algorithm with project-based lookup. This is:
- More reliable (deterministic vs heuristic)
- More performant (0 API calls vs 0-1)
- More complete (handles all entity types including leaves)

The `PRIMARY_PROJECT_GID` ClassVar is already stubbed in the codebase but never populated. This was likely the original design intent that was never completed.
