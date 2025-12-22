# PRD: Membership-Based Entity Type Detection

## Metadata

- **PRD ID**: PRD-DETECTION
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-17
- **Stakeholders**: SDK users, SDK maintainers, Business Model consumers, Hydration system
- **Related PRDs**: PRD-HYDRATION (Hierarchy Hydration), PRD-BIZMODEL (Business Model Phase 1)
- **Related Discovery**: DISCOVERY-DETECTION-SYSTEM (2025-12-17)
- **Supersedes**: ADR-0068 (Name-Based Type Detection Strategy)

---

## Problem Statement

### Current State

The SDK's entity type detection system is fundamentally broken. The current implementation at `/src/autom8_asana/models/business/detection.py` uses name-based pattern matching that assumes holder names are simple strings like `"offers"` or `"contacts"`.

**Detection accuracy in production: approximately 0%**

### Why Detection Fails

| Expected Input | Actual Production Data |
|----------------|----------------------|
| `"offers"` | `"Duong Chiropractic Inc - Chiropractic Offers"` |
| `"contacts"` | `"Acme Corp - Business Contacts"` |
| N/A (no pattern) | `"$49 Complete Chiropractic Health Screening"` |

The current algorithm:
1. Attempts exact name matching against `HOLDER_NAME_MAP` (fails on decorated names)
2. Falls back to subtask structure inspection (requires API call, still unreliable)
3. Returns `EntityType.UNKNOWN` for all leaf entities (Contact, Offer, Location, Process, Hours)

### Who Is Affected

- **Hydration system**: `_traverse_upward_async()` cannot identify parent entity types
- **Webhook handlers**: Cannot determine entity type from task GID
- **Type-safe navigation**: Cannot convert generic Tasks to typed entities
- **Self-healing workflows**: Cannot detect entities needing project membership repair

### Impact of Not Solving

- **Hydration completely broken**: Upward traversal fails on all entities
- **Type safety compromised**: Consumers cannot use typed Business models reliably
- **Manual workarounds required**: Developers must implement custom detection logic
- **Technical debt accumulates**: Current broken system creates false confidence

### Root Cause

The legacy autom8 system uses **project membership** as the source of truth for entity type detection. Each entity type has a dedicated Asana project, and membership in that project determines type. The current SDK attempted to use name patterns as a shortcut, but production data does not conform to expected patterns.

---

## Goals & Success Metrics

### Goals

1. **Deterministic detection**: Every task with project membership has a deterministic type
2. **Zero API calls for primary path**: Tier 1 detection requires no API calls
3. **Graceful degradation**: When Tier 1 fails, fall back through tiers gracefully
4. **Self-healing enablement**: Detection flags entities needing project membership repair
5. **Backward compatibility**: Existing code continues to work during migration

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Detection accuracy (entities with project membership) | ~0% | 100% | Integration test against real tasks |
| Detection accuracy (entities without project membership) | ~0% | >80% | Integration test with Tiers 2-4 |
| Tier 1 detection latency | N/A | <1ms | Benchmark test |
| API calls for Tier 1 detection | N/A | 0 | Code inspection |
| Registry initialization time | N/A | <10ms | Startup profiling |
| Existing tests pass | 100% | 100% | `pytest` before/after |

---

## Scope

### In Scope

**P0 - Registry System (Core)**
- Type registry mapping `project_gid -> EntityType`
- `PRIMARY_PROJECT_GID` ClassVar population on all entity classes
- Auto-population via `__init_subclass__` hook
- Environment variable override for project GIDs
- Registry validation (duplicate detection, missing GID warnings)

**P0 - Tier 1 Detection (Primary Path)**
- O(1) lookup by first project membership
- Detection for 14 entity types with project membership
- `DetectionResult` model with tier, confidence, healing flag

**P1 - Tier 2-3 Detection (Fallbacks)**
- Tier 2: Name convention pattern matching (improved)
- Tier 3: Parent type inference for LocationHolder, ProcessHolder

**P1 - Self-Healing Integration**
- `needs_healing` flag in detection result
- SaveSession `auto_heal` parameter support
- Add missing project memberships during commit

**P2 - Tier 4-5 Detection (Last Resort)**
- Tier 4: Structure inspection (optional, disabled by default)
- Tier 5: UNKNOWN with healing flag

### Out of Scope

| Item | Rationale |
|------|-----------|
| Multi-workspace support | Current system is single-workspace; defer to Phase 2 |
| Confidence scoring API | Nice-to-have; tier information sufficient for MVP |
| Auto-retry healing failures | Leave retry to consumer |
| Remove project membership healing | Only additive healing; removal could break workflows |
| Process subtype detection | Multiple projects map to PROCESS; subtype is separate concern |

---

## Requirements

### Registry Requirements (FR-REG-*)

#### FR-REG-001: Type Registry Data Structure

| Field | Value |
|-------|-------|
| **ID** | FR-REG-001 |
| **Requirement** | A registry maps project GIDs to EntityType values with O(1) lookup |
| **Priority** | Must |
| **Trace** | Discovery Section 3.1: Legacy pattern uses PROJECT_GID ClassVar |
| **Acceptance Criteria** | |

- [ ] Registry is a `dict[str, EntityType]` for O(1) lookup
- [ ] Registry is populated at module load or first access
- [ ] Lookup returns `None` for unknown project GIDs (not KeyError)
- [ ] Registry is module-level singleton (not per-client)
- [ ] Registry supports 30+ project GID mappings

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-REG-002: PRIMARY_PROJECT_GID ClassVar

| Field | Value |
|-------|-------|
| **ID** | FR-REG-002 |
| **Requirement** | Each entity class declares its primary project GID as a ClassVar |
| **Priority** | Must |
| **Trace** | Discovery Section 6.1: PRIMARY_PROJECT_GID declared but set to None |
| **Acceptance Criteria** | |

- [ ] `BusinessEntity.PRIMARY_PROJECT_GID: ClassVar[str | None] = None` (base class)
- [ ] `Business.PRIMARY_PROJECT_GID = "1200653012566782"` (or env var)
- [ ] `Contact.PRIMARY_PROJECT_GID = "1200775689604552"` (or env var)
- [ ] `ContactHolder.PRIMARY_PROJECT_GID = "1201500116978260"` (or env var)
- [ ] `Unit.PRIMARY_PROJECT_GID = "1201081073731555"` (or env var)
- [ ] `UnitHolder.PRIMARY_PROJECT_GID = "1204433992667196"` (or env var)
- [ ] `Offer.PRIMARY_PROJECT_GID = "1143843662099250"` (or env var)
- [ ] `OfferHolder.PRIMARY_PROJECT_GID = "1210679066066870"` (or env var)
- [ ] `Location.PRIMARY_PROJECT_GID = "1200836133305610"` (or env var)
- [ ] `Hours.PRIMARY_PROJECT_GID = "1201614578074026"` (or env var)
- [ ] `DNAHolder.PRIMARY_PROJECT_GID = "1167650840134033"` (or env var)
- [ ] `ReconciliationHolder.PRIMARY_PROJECT_GID = "1203404998225231"` (or env var)
- [ ] `AssetEditHolder.PRIMARY_PROJECT_GID = "1203992664400125"` (or env var)
- [ ] `VideographyHolder.PRIMARY_PROJECT_GID = "1207984018149338"` (or env var)
- [ ] `LocationHolder.PRIMARY_PROJECT_GID = None` (no project - special case)
- [ ] `ProcessHolder.PRIMARY_PROJECT_GID = None` (no project - special case)
- [ ] `Process.PRIMARY_PROJECT_GID = None` (multiple projects - special case)

**Integration Point**: Each entity class file in `/src/autom8_asana/models/business/`

---

#### FR-REG-003: Auto-Population via __init_subclass__

| Field | Value |
|-------|-------|
| **ID** | FR-REG-003 |
| **Requirement** | Registry auto-populates when BusinessEntity subclasses are defined |
| **Priority** | Must |
| **Trace** | Discovery Section 3.4: Pattern to adopt - registry built from model introspection |
| **Acceptance Criteria** | |

- [ ] `BusinessEntity.__init_subclass__()` hook registers entity types
- [ ] If subclass has non-None `PRIMARY_PROJECT_GID`, it is added to registry
- [ ] EntityType is derived from class name (Business -> EntityType.BUSINESS)
- [ ] Duplicate GID registration raises `ValueError` with clear message
- [ ] Registration is idempotent (re-importing module does not duplicate)

**Integration Point**: `/src/autom8_asana/models/business/base.py`

---

#### FR-REG-004: Environment Variable Override

| Field | Value |
|-------|-------|
| **ID** | FR-REG-004 |
| **Requirement** | Project GIDs can be overridden via environment variables |
| **Priority** | Must |
| **Trace** | Discovery Section 5.2: ASANA_PROJECT_* prefix pattern |
| **Acceptance Criteria** | |

- [ ] Pattern: `ASANA_PROJECT_{ENTITY_TYPE}` (e.g., `ASANA_PROJECT_BUSINESS`)
- [ ] Entity type names are uppercase with underscores (e.g., `CONTACT_HOLDER`)
- [ ] Env var value takes precedence over hardcoded default
- [ ] Missing env var uses hardcoded default (not an error)
- [ ] Empty env var value uses hardcoded default
- [ ] Invalid GID format logs warning but allows registration

**Example environment variables**:
```bash
ASANA_PROJECT_BUSINESS=1200653012566782
ASANA_PROJECT_CONTACT=1200775689604552
ASANA_PROJECT_UNIT=1201081073731555
ASANA_PROJECT_OFFER=1143843662099250
```

**Integration Point**: `/src/autom8_asana/models/business/base.py` (in `__init_subclass__`)

---

#### FR-REG-005: Registry Validation

| Field | Value |
|-------|-------|
| **ID** | FR-REG-005 |
| **Requirement** | Registry validates configuration and logs warnings for issues |
| **Priority** | Should |
| **Trace** | Discovery Section 8: Risk - Missing project GIDs in config |
| **Acceptance Criteria** | |

- [ ] Duplicate GID raises `ValueError` at registration time
- [ ] Missing GID for entity with `PRIMARY_PROJECT_GID = None` is logged as debug (expected)
- [ ] Logs warning if expected entity type not found in registry after all imports
- [ ] Provides `validate_registry()` function for explicit validation
- [ ] Validation callable returns list of warnings/errors

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-REG-006: Process Project Mapping

| Field | Value |
|-------|-------|
| **ID** | FR-REG-006 |
| **Requirement** | All Process-related project GIDs map to EntityType.PROCESS |
| **Priority** | Must |
| **Trace** | Discovery Section 2.2: Process has multiple project types |
| **Acceptance Criteria** | |

- [ ] Onboarding project (`1201319387632570`) maps to `EntityType.PROCESS`
- [ ] Implementation project (`1201476141989746`) maps to `EntityType.PROCESS`
- [ ] Consultation project (`1201532776033312`) maps to `EntityType.PROCESS`
- [ ] Sales project (`1200944186565610`) maps to `EntityType.PROCESS`
- [ ] Retention project (`1201346565918814`) maps to `EntityType.PROCESS`
- [ ] Expansion project (`1201265144487557`) maps to `EntityType.PROCESS`
- [ ] All 12+ Process project GIDs map to `EntityType.PROCESS`
- [ ] Process GIDs are registered via supplementary configuration (not ClassVar)
- [ ] Env var pattern: `ASANA_PROJECT_PROCESS_ONBOARDING`, `ASANA_PROJECT_PROCESS_SALES`, etc.

**Integration Point**: `/src/autom8_asana/models/business/detection.py` (separate registration)

---

### Detection Requirements (FR-DET-*)

#### FR-DET-001: DetectionResult Model

| Field | Value |
|-------|-------|
| **ID** | FR-DET-001 |
| **Requirement** | Detection returns a structured result with type, tier, and healing information |
| **Priority** | Must |
| **Trace** | Discovery Section 7 Q4: Detection should return structured result |
| **Acceptance Criteria** | |

- [ ] `DetectionResult` is a dataclass or Pydantic model
- [ ] Fields: `entity_type: EntityType`, `tier_used: int`, `needs_healing: bool`, `expected_project_gid: str | None`
- [ ] `entity_type` is the detected type or `EntityType.UNKNOWN`
- [ ] `tier_used` is 1-5 indicating which detection tier succeeded
- [ ] `needs_healing` is `True` if entity lacks expected project membership
- [ ] `expected_project_gid` is the GID entity should have (for healing)
- [ ] Implements `__bool__` returning `False` for UNKNOWN, `True` otherwise

**Example**:
```python
@dataclass
class DetectionResult:
    entity_type: EntityType
    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None

    def __bool__(self) -> bool:
        return self.entity_type != EntityType.UNKNOWN
```

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-002: Tier 1 - Project Membership Detection

| Field | Value |
|-------|-------|
| **ID** | FR-DET-002 |
| **Requirement** | Primary detection uses task's first project membership to determine type |
| **Priority** | Must |
| **Trace** | Discovery Section 7 Q1: First membership wins |
| **Acceptance Criteria** | |

- [ ] Checks `task.memberships[0].project.gid` if memberships exist
- [ ] Looks up GID in registry
- [ ] Returns `DetectionResult(entity_type=TYPE, tier_used=1, needs_healing=False, expected_project_gid=GID)`
- [ ] If GID not in registry, proceeds to Tier 2
- [ ] If memberships is empty or None, proceeds to Tier 2
- [ ] O(1) lookup time complexity
- [ ] Zero API calls

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-003: Tier 2 - Name Convention Detection

| Field | Value |
|-------|-------|
| **ID** | FR-DET-003 |
| **Requirement** | Secondary detection uses improved name pattern matching for holders |
| **Priority** | Should |
| **Trace** | Discovery Section 1.2: Current name matching is broken |
| **Acceptance Criteria** | |

- [ ] Matches holder names by suffix/contains pattern (not exact match)
- [ ] `"*Contacts*"` -> `EntityType.CONTACT_HOLDER` (case insensitive)
- [ ] `"*Units*"` -> `EntityType.UNIT_HOLDER`
- [ ] `"*Offers*"` -> `EntityType.OFFER_HOLDER`
- [ ] `"*Processes*"` -> `EntityType.PROCESS_HOLDER`
- [ ] `"*Location*"` -> `EntityType.LOCATION_HOLDER`
- [ ] `"*DNA*"` -> `EntityType.DNA_HOLDER`
- [ ] `"*Reconciliation*"` -> `EntityType.RECONCILIATIONS_HOLDER`
- [ ] `"*Asset Edit*"` -> `EntityType.ASSET_EDIT_HOLDER`
- [ ] `"*Videography*"` -> `EntityType.VIDEOGRAPHY_HOLDER`
- [ ] Returns `DetectionResult(entity_type=TYPE, tier_used=2, needs_healing=True, expected_project_gid=EXPECTED_GID)`
- [ ] If no pattern matches, proceeds to Tier 3
- [ ] Zero API calls

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-004: Tier 3 - Parent Type Inference

| Field | Value |
|-------|-------|
| **ID** | FR-DET-004 |
| **Requirement** | Tertiary detection infers type from already-detected parent type |
| **Priority** | Should |
| **Trace** | Discovery Section 2.2: LocationHolder and ProcessHolder have no project |
| **Acceptance Criteria** | |

- [ ] Requires parent entity type to be known (passed as context)
- [ ] If parent is Business and name contains "Location", return `EntityType.LOCATION_HOLDER`
- [ ] If parent is Unit and name contains "Processes", return `EntityType.PROCESS_HOLDER`
- [ ] If parent is ContactHolder, return `EntityType.CONTACT`
- [ ] If parent is UnitHolder, return `EntityType.UNIT`
- [ ] If parent is OfferHolder, return `EntityType.OFFER`
- [ ] If parent is ProcessHolder, return `EntityType.PROCESS`
- [ ] If parent is LocationHolder and name starts with "Hours", return `EntityType.HOURS`
- [ ] If parent is LocationHolder otherwise, return `EntityType.LOCATION`
- [ ] Returns `DetectionResult(entity_type=TYPE, tier_used=3, needs_healing=True, expected_project_gid=EXPECTED_GID)`
- [ ] If parent type unknown, proceeds to Tier 4
- [ ] Zero API calls

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-005: Tier 4 - Structure Inspection

| Field | Value |
|-------|-------|
| **ID** | FR-DET-005 |
| **Requirement** | Optional detection inspects task subtask structure to determine type |
| **Priority** | Could |
| **Trace** | Discovery Section 7 Q3: Tier 4 should be optional and disabled by default |
| **Acceptance Criteria** | |

- [ ] Disabled by default; enabled via `allow_structure_inspection=True` parameter
- [ ] Fetches subtasks via `client.tasks.subtasks_async(task.gid).collect()`
- [ ] If subtasks contain holder names (Contacts, Units, Location), return `EntityType.BUSINESS`
- [ ] If subtasks contain Offers/Processes holders, return `EntityType.UNIT`
- [ ] Returns `DetectionResult(entity_type=TYPE, tier_used=4, needs_healing=True, expected_project_gid=EXPECTED_GID)`
- [ ] If structure doesn't match known patterns, proceeds to Tier 5
- [ ] Requires API call (1+ depending on depth)
- [ ] Logs debug message when structure inspection is invoked

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-006: Tier 5 - Unknown with Healing Flag

| Field | Value |
|-------|-------|
| **ID** | FR-DET-006 |
| **Requirement** | Final tier returns UNKNOWN with healing flag set |
| **Priority** | Must |
| **Trace** | Discovery Section 7 Q5: Healing triggered when detection fails |
| **Acceptance Criteria** | |

- [ ] Returns `DetectionResult(entity_type=EntityType.UNKNOWN, tier_used=5, needs_healing=True, expected_project_gid=None)`
- [ ] Logs warning with task GID and name
- [ ] Does not raise exception (detection never fails, just returns UNKNOWN)

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-007: Synchronous Detection Function

| Field | Value |
|-------|-------|
| **ID** | FR-DET-007 |
| **Requirement** | Synchronous detection function for Tiers 1-3 (no API calls) |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Function signature: `detect_entity_type(task: Task, parent_type: EntityType | None = None) -> DetectionResult`
- [ ] Executes Tiers 1, 2, 3 in order
- [ ] Does not execute Tier 4 (requires async)
- [ ] Returns after first successful tier or Tier 5 UNKNOWN
- [ ] Pure function (no side effects except logging)

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-DET-008: Asynchronous Detection Function

| Field | Value |
|-------|-------|
| **ID** | FR-DET-008 |
| **Requirement** | Asynchronous detection function including optional Tier 4 |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Function signature: `detect_entity_type_async(task: Task, client: AsanaClient, parent_type: EntityType | None = None, allow_structure_inspection: bool = False) -> DetectionResult`
- [ ] Executes Tiers 1, 2, 3 synchronously first
- [ ] If `allow_structure_inspection=True` and Tier 3 fails, executes Tier 4
- [ ] Returns after first successful tier or Tier 5 UNKNOWN
- [ ] Backward compatible with existing callers (same name as current function)

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

### Self-Healing Requirements (FR-HEAL-*)

#### FR-HEAL-001: Healing Flag in Detection Result

| Field | Value |
|-------|-------|
| **ID** | FR-HEAL-001 |
| **Requirement** | Detection result indicates when entity needs project membership repair |
| **Priority** | Must |
| **Trace** | Discovery Section 7 Q5: needs_healing = (detection_tier > 1) |
| **Acceptance Criteria** | |

- [ ] `needs_healing = True` when `tier_used > 1`
- [ ] `needs_healing = True` when entity is in wrong project (future: project mismatch detection)
- [ ] `expected_project_gid` populated from entity class's `PRIMARY_PROJECT_GID`
- [ ] `expected_project_gid = None` for entities without primary project (LocationHolder, ProcessHolder)

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-HEAL-002: SaveSession auto_heal Parameter

| Field | Value |
|-------|-------|
| **ID** | FR-HEAL-002 |
| **Requirement** | SaveSession accepts auto_heal parameter to enable automatic healing |
| **Priority** | Should |
| **Trace** | Discovery Section 7 Q7: Session-level flag with per-entity override |
| **Acceptance Criteria** | |

- [ ] Constructor: `SaveSession(client, auto_heal: bool = False)`
- [ ] When `auto_heal=True`, entities with `needs_healing=True` are healed during commit
- [ ] Healing adds missing project membership via `add_to_project` operation
- [ ] Healing is additive only (never removes project memberships)
- [ ] Per-entity override: `session.track(entity, heal=False)` skips healing for that entity

**Integration Point**: `/src/autom8_asana/persistence/session.py`

---

#### FR-HEAL-003: Healing Execution

| Field | Value |
|-------|-------|
| **ID** | FR-HEAL-003 |
| **Requirement** | Healing operations are batched and executed during SaveSession commit |
| **Priority** | Should |
| **Trace** | Discovery Section 4.1: SaveSession has add_to_project operation |
| **Acceptance Criteria** | |

- [ ] For each tracked entity with `needs_healing=True`:
  - [ ] Call `session.add_to_project(entity, expected_project_gid)`
- [ ] Healing operations batched with other operations
- [ ] Healing failures logged but do not fail overall commit
- [ ] Healing skipped if `expected_project_gid` is None

**Integration Point**: `/src/autom8_asana/persistence/session.py`

---

#### FR-HEAL-004: Healing Result Reporting

| Field | Value |
|-------|-------|
| **ID** | FR-HEAL-004 |
| **Requirement** | SaveResult includes healing outcomes |
| **Priority** | Should |
| **Trace** | Discovery Section 7 Q8: Include in SaveResult |
| **Acceptance Criteria** | |

- [ ] `SaveResult.healed_entities: list[str]` - GIDs of entities successfully healed
- [ ] `SaveResult.healing_failures: list[HealingFailure]` - Failed healing operations
- [ ] `HealingFailure` dataclass with `entity_gid`, `expected_project_gid`, `error`
- [ ] Consumer can inspect results to handle failures

**Integration Point**: `/src/autom8_asana/persistence/session.py`

---

### Configuration Requirements (FR-CFG-*)

#### FR-CFG-001: Default Project GIDs

| Field | Value |
|-------|-------|
| **ID** | FR-CFG-001 |
| **Requirement** | Hardcoded default project GIDs from legacy system |
| **Priority** | Must |
| **Trace** | Discovery Appendix B: Complete Project GID Reference |
| **Acceptance Criteria** | |

- [ ] All 14 core entity project GIDs hardcoded as defaults
- [ ] All 12+ Process project GIDs hardcoded as defaults
- [ ] Defaults are defined in single location (not scattered)
- [ ] Defaults documented in docstrings

**Integration Point**: `/src/autom8_asana/models/business/detection.py` or dedicated config module

---

#### FR-CFG-002: Strict Configuration Mode

| Field | Value |
|-------|-------|
| **ID** | FR-CFG-002 |
| **Requirement** | Optional strict mode raises errors for missing configuration |
| **Priority** | Could |
| **Trace** | Discovery Section 7 Q10: Fail-fast option via strict_config=True |
| **Acceptance Criteria** | |

- [ ] Environment variable: `ASANA_DETECTION_STRICT=true`
- [ ] When strict mode enabled, missing PRIMARY_PROJECT_GID raises `ConfigurationError`
- [ ] When strict mode disabled (default), missing GID logs warning
- [ ] Error message identifies which entity type is misconfigured

**Integration Point**: `/src/autom8_asana/models/business/base.py`

---

### Backward Compatibility Requirements (FR-COMPAT-*)

#### FR-COMPAT-001: Existing Function Signatures

| Field | Value |
|-------|-------|
| **ID** | FR-COMPAT-001 |
| **Requirement** | Existing detection function signatures preserved |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] `detect_by_name(name: str) -> EntityType | None` preserved (returns simple type)
- [ ] `detect_entity_type_async(task, client) -> EntityType` overload preserved
- [ ] New detection functions have different signatures or use overloads
- [ ] Existing callers do not need modification

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

#### FR-COMPAT-002: Deprecation Path

| Field | Value |
|-------|-------|
| **ID** | FR-COMPAT-002 |
| **Requirement** | Old detection patterns have deprecation warnings |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] `detect_by_name()` emits `DeprecationWarning` (still functions)
- [ ] Old `detect_entity_type_async()` that returns just EntityType emits warning
- [ ] Warnings suggest migration to `DetectionResult`-returning functions
- [ ] Deprecation warnings suppressible via standard Python mechanisms

**Integration Point**: `/src/autom8_asana/models/business/detection.py`

---

### Non-Functional Requirements

#### NFR-PERF-001: Tier 1 Detection Performance

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-001 |
| **Requirement** | Tier 1 detection completes in under 1ms |
| **Target** | <1ms |
| **Measurement** | Benchmark test with 1000 detections |

**Acceptance Criteria**:
- [ ] Dict lookup is O(1)
- [ ] No string parsing or pattern matching in Tier 1
- [ ] No I/O operations in Tier 1

---

#### NFR-PERF-002: Registry Initialization Performance

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-002 |
| **Requirement** | Registry initialization completes in under 10ms |
| **Target** | <10ms |
| **Measurement** | Startup profiling |

**Acceptance Criteria**:
- [ ] Registry populated during module import
- [ ] No API calls during initialization
- [ ] Env var reads are fast (os.environ is dict-like)

---

#### NFR-PERF-003: Zero API Calls for Tiers 1-3

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-003 |
| **Requirement** | Tiers 1, 2, 3 require zero API calls |
| **Target** | 0 API calls |
| **Measurement** | Code inspection, mock verification in tests |

**Acceptance Criteria**:
- [ ] Tier 1: Lookup in local registry
- [ ] Tier 2: String pattern matching on task.name
- [ ] Tier 3: Logic based on passed parent_type parameter
- [ ] Client parameter optional for sync detection

---

#### NFR-SAFE-001: Type Safety

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-001 |
| **Requirement** | All new code passes mypy strict mode |
| **Target** | mypy exit code 0 |
| **Measurement** | `mypy src/autom8_asana` |

**Acceptance Criteria**:
- [ ] `DetectionResult` fully typed
- [ ] Registry type: `dict[str, EntityType]`
- [ ] Function signatures fully typed
- [ ] No `# type: ignore` except where unavoidable

---

#### NFR-SAFE-002: Test Coverage

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-002 |
| **Requirement** | New detection code has >90% test coverage |
| **Target** | >90% coverage |
| **Measurement** | `pytest --cov` |

**Acceptance Criteria**:
- [ ] Unit tests for each detection tier
- [ ] Unit tests for registry population
- [ ] Unit tests for env var override
- [ ] Integration tests with real task data structures
- [ ] Edge case tests (empty memberships, None values)

---

#### NFR-COMPAT-001: Backward Compatibility

| Field | Value |
|-------|-------|
| **ID** | NFR-COMPAT-001 |
| **Requirement** | All existing tests pass without modification |
| **Target** | 100% existing tests pass |
| **Measurement** | `pytest` before/after |

**Acceptance Criteria**:
- [ ] Existing detection tests unchanged and passing
- [ ] Existing hydration tests unchanged and passing
- [ ] No breaking changes to public API signatures

---

## User Stories / Use Cases

### US-001: Webhook Handler Entity Type Detection

**As a** webhook handler developer
**I want to** determine the type of a task received via webhook
**So that** I can route it to the appropriate handler

**Scenario**:
```python
async def handle_task_webhook(task_gid: str):
    task = await client.tasks.get_async(task_gid)

    # NEW: Deterministic type detection
    result = detect_entity_type(task)

    if result.entity_type == EntityType.OFFER:
        await handle_offer_update(Offer.model_validate(task.model_dump()))
    elif result.entity_type == EntityType.CONTACT:
        await handle_contact_update(Contact.model_validate(task.model_dump()))
    elif result.entity_type == EntityType.UNKNOWN:
        logger.warning(f"Unknown entity type for task {task_gid}")
```

---

### US-002: Hydration Parent Detection

**As a** hydration system
**I want to** identify parent entity types during upward traversal
**So that** I can convert Tasks to typed entities

**Scenario**:
```python
async def traverse_to_business(entity: Task, client: AsanaClient) -> Business:
    current = entity
    parent_type: EntityType | None = None

    while current.parent:
        parent_task = await client.tasks.get_async(current.parent.gid)

        # NEW: Pass parent_type for context
        result = detect_entity_type(parent_task, parent_type=parent_type)

        if result.entity_type == EntityType.BUSINESS:
            return Business.model_validate(parent_task.model_dump())

        parent_type = result.entity_type
        current = parent_task

    raise HydrationError("No Business found in parent chain")
```

---

### US-003: Self-Healing During Save

**As a** SDK user
**I want to** automatically repair entities missing project membership
**So that** future detection works correctly

**Scenario**:
```python
async def save_with_healing(entity: BusinessEntity):
    async with SaveSession(client, auto_heal=True) as session:
        session.track(entity)
        result = await session.commit_async()

        if result.healed_entities:
            logger.info(f"Healed {len(result.healed_entities)} entities")
        if result.healing_failures:
            logger.warning(f"Failed to heal: {result.healing_failures}")
```

---

### US-004: Debug Missing Detection

**As a** developer debugging detection issues
**I want to** understand why detection failed
**So that** I can fix the underlying data

**Scenario**:
```python
def debug_detection(task: Task):
    result = detect_entity_type(task)

    print(f"Detected: {result.entity_type}")
    print(f"Detection tier: {result.tier_used}")
    print(f"Needs healing: {result.needs_healing}")
    print(f"Expected project: {result.expected_project_gid}")

    if result.tier_used == 5:
        print("Detection failed - task has no project membership and name doesn't match patterns")
        print(f"Task memberships: {task.memberships}")
        print(f"Task name: {task.name}")
```

---

## Assumptions

1. **Project GIDs are stable**: Asana project GIDs do not change once created

2. **First membership is primary**: For tasks in multiple projects, the first membership is canonical

3. **Name patterns are semi-stable**: Holder names contain type keywords (Contacts, Units, Offers, etc.) even when decorated

4. **Single workspace**: Current implementation serves one workspace; project GIDs are workspace-specific

5. **Env vars available at import**: Environment variables are set before module import for registry population

6. **Legacy GIDs are accurate**: Project GIDs from legacy system are correct for production

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `Task.memberships` field | Task model | Implemented |
| `Task.memberships[].project.gid` access | Task model | Implemented |
| `SaveSession.add_to_project()` operation | SaveSession | Implemented |
| `EntityType` enum | detection.py | Implemented (needs PROCESS_HOLDER if missing) |
| Legacy project GID inventory | Discovery | Documented |

---

## Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| Q1 | Should registry be populated at import time or lazily? | Architect | TDD Session | Recommendation: Import time for simplicity |
| Q2 | Should DetectionResult be a dataclass or Pydantic model? | Architect | TDD Session | - |
| Q3 | Should Process subtype detection be added? (Onboarding vs Sales) | Product | Future PRD | Defer to future enhancement |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Requirements Analyst | Initial PRD based on DISCOVERY-DETECTION-SYSTEM |

---

## Appendix: Entity Type to Project GID Mapping

From Discovery Appendix B:

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
| PROCESS | Multiple (see below) | Multiple |

**Process Project GIDs** (all map to EntityType.PROCESS):
| Process Type | Project GID | Env Var |
|--------------|-------------|---------|
| Onboarding | `1201319387632570` | `ASANA_PROJECT_PROCESS_ONBOARDING` |
| Implementation | `1201476141989746` | `ASANA_PROJECT_PROCESS_IMPLEMENTATION` |
| Consultation | `1201532776033312` | `ASANA_PROJECT_PROCESS_CONSULTATION` |
| Sales | `1200944186565610` | `ASANA_PROJECT_PROCESS_SALES` |
| Retention | `1201346565918814` | `ASANA_PROJECT_PROCESS_RETENTION` |
| Expansion | `1201265144487557` | `ASANA_PROJECT_PROCESS_EXPANSION` |
| Outreach | `1201753128450029` | `ASANA_PROJECT_PROCESS_OUTREACH` |
| Reactivation | `1201265144487549` | `ASANA_PROJECT_PROCESS_REACTIVATION` |
| Account Error | `1201684018234520` | `ASANA_PROJECT_PROCESS_ACCOUNT_ERROR` |
| Videographer Sourcing | `1206176773330155` | `ASANA_PROJECT_PROCESS_VIDEOGRAPHER_SOURCING` |
| Activation Consultation | `1209247943184021` | `ASANA_PROJECT_PROCESS_ACTIVATION_CONSULTATION` |
| Practice of Week | `1209247943184017` | `ASANA_PROJECT_PROCESS_PRACTICE_OF_WEEK` |

---

## Appendix: Detection Tier Flow

```
Task Input
    |
    v
[Tier 1] Project Membership Lookup
    |-- Found in registry --> Return (tier=1, needs_healing=False)
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

## Quality Gates Checklist

- [x] Problem statement is clear and specific
- [x] Scope explicitly defines in/out boundaries
- [x] Every requirement has acceptance criteria
- [x] MoSCoW priorities assigned to all requirements
- [x] Requirements trace to discovery findings
- [x] No blocking open questions remain (3 deferred to Architect)
- [x] All 5 detection tiers have requirements defined
- [x] Self-healing requirements are complete
- [x] Assumptions documented
- [x] Dependencies identified with status
- [x] Success metrics are quantified
