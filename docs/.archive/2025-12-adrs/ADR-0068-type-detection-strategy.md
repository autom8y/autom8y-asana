# ADR-0068: Type Detection Strategy for Upward Traversal

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-HYDRATION, TDD-HYDRATION, DISCOVERY-HYDRATION-001, ADR-0050

## Context

When hydrating a business model hierarchy from an arbitrary entry point (e.g., Contact, Offer), we must traverse upward through the parent chain to find the Business root. Each parent task fetched via `Task.parent.gid` is a generic Task object--we need to determine its actual type (Business, Unit, Holder) to:

1. Convert it to the appropriate typed model
2. Set correct bidirectional references
3. Know when we have reached the Business root

The parent chain for an Offer looks like:
```
Offer -> OfferHolder -> Unit -> UnitHolder -> Business
```

**Question from PRD (Q1)**: How should we determine the type of a parent task during upward traversal?

### Forces

1. **Convention stability**: Business model naming conventions ("Contacts", "Units", "Offers", etc.) are established and unlikely to change
2. **API call cost**: Structure inspection (fetching subtasks) adds API calls
3. **Robustness**: Name-only detection can fail if naming conventions change or are inconsistent
4. **Performance**: Upward traversal should be fast (user waiting for hierarchy load)
5. **Maintainability**: Detection logic should be centralized and easy to update

## Decision

We will use **name-based heuristics as the primary detection method with structure inspection as fallback** (Option A with Option C fallback).

### Detection Algorithm

```python
def detect_entity_type(task: Task, client: AsanaClient) -> EntityType:
    # Phase 1: Name-based detection (no API calls)
    if detected := _detect_by_name(task.name):
        return detected

    # Phase 2: Structure inspection fallback (1 API call)
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    return _detect_by_structure(task, subtasks)

def _detect_by_name(name: str | None) -> EntityType | None:
    if name is None:
        return None

    name_lower = name.lower().strip()

    # Holder detection (exact or close match)
    HOLDER_NAMES = {
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
    if name_lower in HOLDER_NAMES:
        return HOLDER_NAMES[name_lower]

    # Business/Unit cannot be detected by name alone
    # (they have variable names like "Acme Corp" or "Premium Package")
    return None

def _detect_by_structure(task: Task, subtasks: list[Task]) -> EntityType:
    """Detect type by examining subtask names."""
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    business_indicators = {"contacts", "units", "location"}
    if subtask_names & business_indicators:
        return EntityType.BUSINESS

    # Unit has offer/process holder subtasks
    unit_indicators = {"offers", "processes"}
    if subtask_names & unit_indicators:
        return EntityType.UNIT

    # Ambiguous - likely a leaf entity or unknown structure
    return EntityType.UNKNOWN
```

### Type Enumeration

```python
class EntityType(Enum):
    BUSINESS = "business"
    CONTACT_HOLDER = "contact_holder"
    UNIT_HOLDER = "unit_holder"
    LOCATION_HOLDER = "location_holder"
    DNA_HOLDER = "dna_holder"
    RECONCILIATIONS_HOLDER = "reconciliations_holder"
    ASSET_EDIT_HOLDER = "asset_edit_holder"
    VIDEOGRAPHY_HOLDER = "videography_holder"
    UNIT = "unit"
    OFFER_HOLDER = "offer_holder"
    PROCESS_HOLDER = "process_holder"
    CONTACT = "contact"
    OFFER = "offer"
    PROCESS = "process"
    LOCATION = "location"
    HOURS = "hours"
    UNKNOWN = "unknown"
```

## Rationale

**Why name-based primary?**
- Zero API calls for holder detection (80%+ of cases)
- Holder names are standardized and controlled by the SDK
- Fast path for common traversal patterns

**Why structure fallback?**
- Business and Unit have variable names (business names, package names)
- Structure inspection is deterministic--presence of specific holder subtasks confirms type
- Fallback only needed for Business/Unit detection (2 types out of ~15)

**Why not other options?**

- **Option B (Custom field storing type)**: Would require data migration across all existing tasks, and custom fields are already heavily used for business data
- **Option D (GID registry)**: Would require maintaining a persistent cache, adding complexity and potential staleness issues

## Alternatives Considered

### Option B: Custom Field Type Marker

- **Description**: Store `_entity_type: "Business"` in a custom field on each task
- **Pros**: Reliable, O(1) lookup, no heuristics
- **Cons**: Requires data migration, uses a custom field slot, requires coordinated updates when creating new tasks
- **Why not chosen**: Migration burden and ongoing maintenance cost outweigh benefits

### Option D: GID-to-Type Registry

- **Description**: Maintain an in-memory or persistent map of GID -> EntityType
- **Pros**: O(1) lookup after first resolution
- **Cons**: Registry must be populated somehow (chicken-egg), staleness risk, memory overhead
- **Why not chosen**: Doesn't solve the initial detection problem, adds caching complexity

## Consequences

### Positive

- **Fast**: Most detections complete with zero additional API calls
- **Simple**: Centralized detection logic, easy to understand
- **Robust**: Structure fallback handles edge cases and naming variations
- **Extensible**: Easy to add new holder types to the name map

### Negative

- **Brittleness**: If holder naming conventions change, detection will fail gracefully to structure inspection (acceptable)
- **Extra API call**: Business/Unit detection requires fetching subtasks (1 additional call)
- **Logging noise**: Ambiguous cases will log warnings (acceptable for debugging)

### Neutral

- Detection logic is isolated and testable
- No data migration required
- Compatible with existing holder patterns (ADR-0050)

## Compliance

- Type detection logic MUST be implemented in a dedicated module: `src/autom8_asana/models/business/detection.py`
- All holder name patterns MUST match existing `HOLDER_KEY_MAP` definitions
- Structure fallback MUST log a warning when used (for monitoring unexpected cases)
- Unit tests MUST cover all EntityType values with appropriate fixtures

## Implementation Notes

Location: `src/autom8_asana/models/business/detection.py`

The detection module should provide:
1. `EntityType` enum
2. `detect_entity_type_async(task, client)` - full detection with fallback
3. `detect_by_name(name)` - name-only detection (sync, for testing)
4. `HOLDER_NAME_MAP` - centralized holder name definitions
