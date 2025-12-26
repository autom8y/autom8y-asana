# ADR Summary: Custom Fields

> Consolidated decision record for custom field handling, accessors, cascading, and resolution. Individual ADRs archived.

## Overview

Custom fields are Asana's mechanism for domain-specific metadata. The SDK evolved from static GID constants (ADR-0030) to dynamic name-based resolution (ADR-0034), then added type-safe property access (ADR-0051, ADR-0081), API format conversion (ADR-0056), change detection (ADR-0067, ADR-0074), and field cascading (ADR-0054, ADR-0113). The current architecture provides both infrastructure-level access (CustomFieldAccessor) and domain-level typed properties (CustomFieldDescriptor subclasses), with proper layering and single source of truth for field resolution (ADR-0117).

Custom fields presented unique challenges: Asana identifies them by GIDs (stable) but users refer to them by names (readable). Field values require type-specific handling (text, number, enum, multi-enum, people, date). The API expects different formats for reading versus writing. Hierarchical entities (Business, Unit, Offer) need fields that cascade or inherit across levels. Change tracking must coordinate across multiple systems.

The solution is a layered architecture: CustomFieldAccessor provides infrastructure (name-to-GID resolution, change tracking, API serialization), while CustomFieldDescriptor subclasses provide domain semantics (typed properties, transformation, auto-generation). This separation satisfies both generic Task access patterns and business entity type safety.

## Key Decisions

### 1. Field Identification: Static GIDs vs Dynamic Resolution

**Context**: Custom field GIDs are stable but environment-specific. Names are human-readable but can change.

**Decision**: Use dynamic name-based resolution with session-level caching (ADR-0034). For MVP, static GID constants provided type safety (ADR-0030), but dynamic resolution scales better across environments and eliminates hardcoded placeholders.

**Resolution Pattern**:
- Parse source prefix: `cf:Name` (resolve by name), `gid:123` (explicit GID), or attribute path
- Normalize field names to lowercase alphanumeric for case-insensitive matching
- Build session-cached name-to-GID index from first task's custom_fields
- Zero extra API calls (use existing task data)

**Source ADRs**: ADR-0030 (Static GIDs for MVP), ADR-0034 (Dynamic Resolution Strategy)

**Rationale**: Static GIDs blocked progress with environment-specific placeholders. Dynamic resolution provides environment agnosticism, self-documenting schemas (`source="cf:MRR"`), and scales to 50+ task types without code changes.

### 2. Type Safety: Property Accessors vs Stringly-Typed Access

**Context**: 80+ business custom fields across Business, Contact, Unit models need type hints and IDE autocomplete.

**Decision**: Hybrid approach using typed property accessors that delegate to CustomFieldAccessor (ADR-0051). Later evolved to descriptor pattern for code reduction (ADR-0081).

**Property Pattern (ADR-0051)**:
```python
@property
def company_id(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

**Descriptor Pattern (ADR-0081)**:
```python
company_id = TextField()  # Auto-derives field name, provides type hints
```

**Source ADRs**: ADR-0051 (Custom Field Type Safety), ADR-0081 (Custom Field Descriptor Pattern)

**Rationale**: Properties provide ergonomics and type conversion while reusing CustomFieldAccessor's change tracking. Descriptors reduce 800+ lines of boilerplate to ~110 declarative lines (86% reduction) while maintaining type safety.

### 3. API Format Conversion: List vs Dict Serialization

**Context**: `CustomFieldAccessor.to_list()` produced array format incompatible with Asana API update requirements.

**Decision**: Add `to_api_dict()` method producing `{gid: value}` dict format, keeping `to_list()` for backward compatibility (ADR-0056).

**API Format Requirements**:
- Text fields: string value
- Number fields: numeric value
- Enum fields: option GID string (not `{"gid": "...", "name": "..."}` dict)
- Multi-enum fields: array of option GIDs
- People fields: array of user GIDs
- Date fields: date object

**Source ADRs**: ADR-0056 (Custom Field API Format Conversion)

**Rationale**: Separate methods for reading (`to_list()`) vs writing (`to_api_dict()`) provide clear intent without breaking existing code. Type-specific value normalization handles enum GID extraction automatically.

### 4. Change Detection: Accessor Modifications vs Direct Mutations

**Context**: CustomFieldAccessor tracks changes via `_modifications` dict, but users can also mutate `task.custom_fields` list directly. After successful save, both systems needed reset.

**Decision**:
- Capture deep copy snapshot of custom_fields at Task initialization (ADR-0067)
- Make CustomFieldAccessor the authoritative change tracking system (ADR-0074)
- SaveSession coordinates reset across all three systems (ChangeTracker, accessor, snapshot) after successful commit

**Detection Strategy**:
- Accessor modifications: `_modifications` dict tracks `.set()` calls
- Direct mutations: Compare current `custom_fields` to `_original_custom_fields` snapshot
- Accessor precedence: When both modified, accessor wins (explicit API)

**Source ADRs**: ADR-0067 (Custom Field Snapshot Detection Strategy), ADR-0074 (Unified Custom Field Tracking via CustomFieldAccessor)

**Rationale**: Deep copy detects nested dict mutations. Snapshot comparison catches direct list modifications. Coordinated reset prevents duplicate API calls and cross-session pollution.

### 5. Cascading Fields: Multi-Level Propagation with Opt-In Override

**Context**: Business hierarchy requires fields that flow from parent to descendants (e.g., Office Phone from Business to all Units/Offers/Processes).

**Decision**: Denormalized storage with explicit cascade operations and multi-level support (ADR-0054). Default is no override; `allow_override=True` is explicit opt-in.

**Cascade Behavior**:
- `allow_override=False` (DEFAULT): Always overwrite descendant value with parent value
- `allow_override=True` (explicit): Only overwrite if descendant value is null

**Cascade Scope**: Relative to source entity
- `cascade_field(business, "Office Phone")` affects all business descendants
- `cascade_field(unit, "Platforms")` affects only that unit's offers

**Source ADRs**: ADR-0054 (Cascading Custom Fields Strategy), ADR-0113 (Rep Field Cascade Pattern)

**Rationale**: Denormalized storage provides O(1) read access without traversing hierarchy. Explicit cascade calls avoid hidden behavior. Override opt-in prevents accidental local values from being preserved when parent should control the field.

### 6. Rep Field Inheritance: Unit-First Cascade

**Context**: New Process creation requires assignee from representative field. Both Unit and Business have `rep` custom field.

**Decision**: Cascade pattern preferring Unit.rep, falling back to Business.rep (ADR-0113).

**Resolution Order**:
1. Try Unit.rep first (more specific)
2. Fall back to Business.rep
3. Return None if both empty (log warning, leave unassigned)

**Source ADRs**: ADR-0113 (Rep Field Cascade Pattern)

**Rationale**: Unit-level assignment overrides business-level default. Specificity principle aligns with hierarchy. Graceful fallback maximizes assignee coverage without failing conversion.

### 7. GID Resolution: Using CustomFieldAccessor for API Calls

**Context**: Field seeding and pipeline automation compute values using human-readable names, but API requires GIDs.

**Decision**: Use existing `CustomFieldAccessor._resolve_gid()` for all name-to-GID resolution, and `to_api_dict()` for API payload formatting (ADR-0112).

**Resolution Process**:
1. Fetch target task with `opt_fields=["custom_fields", "custom_fields.enum_options"]`
2. Build accessor from target's field definitions
3. Set values by name - accessor handles resolution
4. Convert to API format via `to_api_dict()`
5. Single API call with formatted payload

**Source ADRs**: ADR-0112 (Custom Field GID Resolution Pattern)

**Rationale**: Reuses battle-tested accessor code. Handles case-insensitivity, type conversion, enum option resolution. Avoids reinventing the wheel.

### 8. Dictionary-Style Access: Enhancing Accessor vs Wrapper

**Context**: Users expect dictionary syntax: `task.custom_fields["Priority"] = "High"`

**Decision**: Enhance CustomFieldAccessor with `__getitem__` and `__setitem__` methods directly (ADR-0062).

**Implementation**:
```python
def __getitem__(self, name_or_gid: str) -> Any:
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result

def __setitem__(self, name_or_gid: str, value: Any) -> None:
    self.set(name_or_gid, value)
```

**Source ADRs**: ADR-0062 (CustomFieldAccessor Enhancement vs. Wrapper)

**Rationale**: Simpler than wrapper class. Backward compatible (existing `.get()`/`.set()` unchanged). Change tracking works automatically via existing `_modifications` dict.

### 9. Layered Architecture: Accessor Infrastructure + Descriptor Domain

**Context**: Two patterns appeared to create duality: CustomFieldAccessor (infrastructure) and CustomFieldDescriptor subclasses (domain).

**Decision**: Retain current architecture as-is. The patterns are not competing but properly layered: descriptors wrap accessor infrastructure (ADR-0117).

**Architecture**:
```
Domain Layer (Consumer-Facing)
  CustomFieldDescriptor subclasses
    - TextField, EnumField, NumberField, DateField
    - Declarative: company_id = TextField()
    - Type transformation
    - Auto-generated Fields class

  delegates internally to

Infrastructure Layer (Implementation)
  CustomFieldAccessor
    - obj.get_custom_fields().get/set()
    - Name-to-GID resolution
    - Change tracking
    - API serialization
```

**Usage Guidance**:
- Business entity field access: Descriptor property (`business.vertical`)
- Generic Task field access: Accessor method (`task.custom_fields_editor().get("Status")`)
- Cascade/inheritance metadata: CascadingFieldDef
- Raw API serialization: Accessor method (`accessor.to_api_dict()`)

**Source ADRs**: ADR-0117 (CustomFieldAccessor/Descriptor Unification Strategy)

**Rationale**: Layering is correct as-designed. Field resolution is centralized in `CustomFieldAccessor._resolve_gid()`. Zero breaking changes. Design validation confirms ADR-0081/ADR-0082 were correctly implemented.

## Cross-References

### Related PRDs
- PRD-0003: Structured DataFrame Layer (custom field typing for MVP)
- PRD-0003.1: Dynamic Custom Field Resolution
- PRD-SDKDEMO: SDK Demo Script (API format bug discovery)
- PRD-SDKUX: SDK Usability Overhaul (dictionary-style access)
- PRD-HARDENING-B: Change Tracking Hardening (unified reset)
- PRD-PATTERNS-A: Pattern Extraction (descriptor pattern)
- PRD-PIPELINE-AUTOMATION-ENHANCEMENT: Pipeline automation (GID resolution, rep cascade)

### Related TDDs
- TDD-0009: Structured DataFrame Layer
- TDD-0009.1: Dynamic Custom Field Resolution
- TDD-0015: Business Model Architecture
- TDD-TRIAGE-FIXES: QA Adversarial Review Fixes
- TDD-HARDENING-B: Change Tracking Hardening
- TDD-PATTERNS-A: Pattern Extraction
- TDD-PIPELINE-AUTOMATION-ENHANCEMENT: Pipeline automation
- TDD-TECH-DEBT-REMEDIATION: Technical debt remediation

### Related Summaries
- ADR-SUMMARY-PATTERNS: Pattern evolution (navigation descriptors, field descriptors)
- ADR-SUMMARY-DETECTION: Change detection and tracking patterns
- ADR-SUMMARY-HIERARCHY: Business model hierarchy and relationships

## Implementation Timeline

| Phase | ADRs | Key Milestone |
|-------|------|---------------|
| **MVP (Dec 9)** | ADR-0030 | Static GID constants for Unit/Contact extractors |
| **Resolution (Dec 9)** | ADR-0034 | Dynamic name-based resolution with session caching |
| **Type Safety (Dec 11)** | ADR-0051 | Typed property accessors for 80+ business fields |
| **API Format (Dec 12)** | ADR-0056 | `to_api_dict()` for correct API payload format |
| **Usability (Dec 12)** | ADR-0062 | Dictionary-style access via `__getitem__`/`__setitem__` |
| **Change Detection (Dec 12)** | ADR-0067 | Deep copy snapshot for direct mutation detection |
| **Cascading (Dec 11)** | ADR-0054 | Multi-level cascading with opt-in override |
| **Unified Tracking (Dec 16)** | ADR-0074 | SaveSession-coordinated reset across all systems |
| **Descriptor Pattern (Dec 16)** | ADR-0081 | 86% code reduction via descriptor pattern |
| **GID Resolution (Dec 18)** | ADR-0112 | CustomFieldAccessor for pipeline automation |
| **Rep Cascade (Dec 18)** | ADR-0113 | Unit-first cascade for assignee resolution |
| **Unification (Dec 19)** | ADR-0117 | Layered architecture clarification |

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0030 | Custom Field Typing | 2025-12-09 | Hardcoded GID constants for MVP; post-MVP configurable |
| ADR-0034 | Dynamic Custom Field Resolution Strategy | 2025-12-09 | Protocol-based resolver with name normalization, session caching |
| ADR-0051 | Custom Field Type Safety | 2025-12-11 | Typed property accessors delegating to CustomFieldAccessor |
| ADR-0054 | Cascading Custom Fields Strategy | 2025-12-11 | Denormalized storage with explicit cascade, multi-level support |
| ADR-0056 | Custom Field API Format Conversion | 2025-12-12 | `to_api_dict()` method for correct API payload format |
| ADR-0062 | CustomFieldAccessor Enhancement vs. Wrapper | 2025-12-12 | Enhance accessor with `__getitem__`/`__setitem__`, not wrapper |
| ADR-0067 | Custom Field Snapshot Detection Strategy | 2025-12-12 | Deep copy snapshot at initialization for direct mutation detection |
| ADR-0074 | Unified Custom Field Tracking via CustomFieldAccessor | 2025-12-16 | CustomFieldAccessor authoritative; SaveSession coordinates reset |
| ADR-0081 | Custom Field Descriptor Pattern | 2025-12-16 | Generic descriptors reduce 800 lines to 110 (86% reduction) |
| ADR-0112 | Custom Field GID Resolution Pattern | 2025-12-18 | Use CustomFieldAccessor for all name-to-GID resolution |
| ADR-0113 | Rep Field Cascade Pattern | 2025-12-18 | Unit.rep precedence over Business.rep for assignee |
| ADR-0117 | CustomFieldAccessor/Descriptor Unification Strategy | 2025-12-19 | Retain layered architecture: descriptors wrap accessor |

## Migration Guide

### From Static GIDs to Dynamic Resolution

**Before (ADR-0030)**:
```python
from autom8_asana.dataframes.models.custom_fields import MRR_GID

mrr = self._extract_custom_field(task, MRR_GID, Decimal)
```

**After (ADR-0034)**:
```python
ColumnDef(name="mrr", source="cf:MRR")  # Self-documenting schema
```

### From Property Boilerplate to Descriptors

**Before (ADR-0051)**:
```python
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"

    @property
    def company_id(self) -> str | None:
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

**After (ADR-0081)**:
```python
class Business(Task):
    company_id = TextField()  # 1 line replaces 7-8 lines
```

### From Method Calls to Dictionary Access

**Before**:
```python
task.get_custom_fields().set("Priority", "High")
value = task.get_custom_fields().get("Priority")
```

**After (ADR-0062)**:
```python
task.custom_fields["Priority"] = "High"
value = task.custom_fields["Priority"]
```

## Lessons Learned

1. **Progressive disclosure works**: Started with simple static GIDs, evolved to dynamic resolution only when needed.

2. **Layering prevents duplication**: CustomFieldAccessor provides infrastructure (resolution, change tracking, API format), descriptors provide domain semantics (types, transformation). Trying to merge them would create confusion.

3. **Snapshot comparison is reliable**: Deep copy for change detection is simpler and more robust than proxy objects or hash-based detection.

4. **Explicit is better than implicit**: Cascade operations are explicit method calls, not hidden side effects. Accessor takes precedence over direct mutations with warning.

5. **Backward compatibility requires multiple paths**: Supporting both accessor methods and dictionary syntax provides migration path without breaking changes.

6. **Type-specific subclasses scale**: TextField, EnumField, NumberField, etc. provide clear type guarantees better than generic `CustomField(type="text")`.

7. **Default should be safe**: `allow_override=False` prevents descendant overrides by default. Opt-in to override only when explicitly needed.

8. **Centralized resolution is critical**: Single source of truth (`CustomFieldAccessor._resolve_gid()`) prevents divergence between systems.

9. **Change tracking must coordinate**: Three systems (ChangeTracker, accessor, snapshot) require coordinated reset to prevent duplicate API calls.

10. **Analysis before refactoring**: ADR-0117 prevented unnecessary unification work by clarifying that the layered architecture was already correct.
