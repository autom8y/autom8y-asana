# TDD: Technical Debt Remediation Initiative

## Metadata

- **TDD ID**: TDD-TECH-DEBT-REMEDIATION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-19
- **PRD Reference**: [PRD-TECH-DEBT-REMEDIATION](/docs/requirements/PRD-TECH-DEBT-REMEDIATION.md)
- **Related TDDs**: TDD-DETECTION, TDD-WORKSPACE-PROJECT-REGISTRY
- **Related ADRs**: ADR-0115, ADR-0116, ADR-0117, ADR-0118, ADR-0093, ADR-0094, ADR-0095

---

## Overview

This TDD defines the technical approach for remediating 13 remaining technical debt items across detection system reliability, Process entity enhancement, and test coverage improvements. The design prioritizes backward compatibility while enabling deterministic entity detection and type-safe Process field access.

---

## Requirements Summary

### Phase 1: Detection System Foundation (7 requirements)

| ID | Requirement | Priority | Design Section |
|----|-------------|----------|----------------|
| FR-DET-001 | Delete ProcessProjectRegistry | Must | 3.1 |
| FR-DET-002 | Process.PRIMARY_PROJECT_GID via WorkspaceProjectRegistry | Must | 3.2 |
| FR-DET-003 | ProcessHolder.PRIMARY_PROJECT_GID handling | Must | 3.2, ADR-0115 |
| FR-DET-004 | Validate LocationHolder/UnitHolder PRIMARY_PROJECT_GID | Should | 3.2 |
| FR-DET-005 | Improve Tier 2 name pattern matching | Should | 3.3, ADR-0117 |
| FR-DET-006 | Implement self-healing | Could | 3.4, ADR-0118 |
| FR-DET-007 | Startup validation for env vars | Could | 3.5 |

### Phase 2: Process Entity Enhancement (4 requirements)

| ID | Requirement | Priority | Design Section |
|----|-------------|----------|----------------|
| FR-PROC-001 | Sales pipeline field accessors | Must | 4.1, ADR-0116 |
| FR-PROC-002 | Onboarding pipeline field accessors | Should | 4.1 |
| FR-PROC-003 | Implementation pipeline field accessors | Should | 4.1 |
| FR-PROC-004 | Extend ProcessType enum if needed | Could | 4.2 |

### Phase 3: Test Coverage & Documentation (3 requirements)

| ID | Requirement | Priority | Design Section |
|----|-------------|----------|----------------|
| FR-TEST-001 | Integration tests for detection | Must | 5.1 |
| FR-TEST-002 | Improve test pyramid ratio | Should | 5.2 |
| FR-TEST-003 | Remove stale documentation | Must | 5.3 |

---

## System Context

```
+----------------------------------------------------------+
|                     Consumer Applications                 |
+----------------------------------------------------------+
                              |
                              v
+----------------------------------------------------------+
|                   autom8_asana SDK                        |
|  +----------------------------------------------------+  |
|  |              Detection Layer (Modified)            |  |
|  |  - Tier 1: Project membership (WorkspaceRegistry)  |  |
|  |  - Tier 2: Enhanced name patterns (ADR-0117)       |  |
|  |  - Tier 3: Parent inference                        |  |
|  |  - Tier 4: Structure inspection (async)            |  |
|  |  - Tier 5: Unknown fallback                        |  |
|  +----------------------------------------------------+  |
|  +----------------------------------------------------+  |
|  |              Process Entity (Enhanced)             |  |
|  |  - Common fields (8)                               |  |
|  |  - Sales fields (54+)                              |  |
|  |  - Onboarding fields (33+)                         |  |
|  |  - Implementation fields (28+)                     |  |
|  +----------------------------------------------------+  |
|  +----------------------------------------------------+  |
|  |              Self-Healing (New)                    |  |
|  |  - SaveSession integration                         |  |
|  |  - Standalone heal_entity_async()                  |  |
|  |  - Dry-run support                                 |  |
|  +----------------------------------------------------+  |
|  +----------------------------------------------------+  |
|  |           SaveSession (Existing + Healing)         |  |
|  +----------------------------------------------------+  |
+----------------------------------------------------------+
                              |
                              v
                       Asana REST API
```

---

## Design

### 3. Detection System Changes

#### 3.1 ProcessProjectRegistry Deletion (FR-DET-001)

**Requirement**: Delete ProcessProjectRegistry module and all references.

**Approach**: The `ProcessProjectRegistry` class in `registry.py` was planned but never implemented (confirmed in Discovery). No deletion is needed - verify absence and document.

**Files to Verify**:
- `src/autom8_asana/models/business/registry.py` - Confirm no ProcessProjectRegistry class
- `tests/unit/models/business/test_registry.py` - Confirm no ProcessProjectRegistry tests
- `src/autom8_asana/models/business/__init__.py` - Confirm no export

**Acceptance**: Import `registry.py` successfully with no `ProcessProjectRegistry` symbol.

#### 3.2 PRIMARY_PROJECT_GID Configuration (FR-DET-002, FR-DET-003, FR-DET-004)

**Requirement**: Configure PRIMARY_PROJECT_GID for Process and related holders.

##### Process.PRIMARY_PROJECT_GID (FR-DET-002)

Process entities belong to **dynamic pipeline projects** (Sales, Onboarding, etc.). Rather than a static GID, Process detection relies on:

1. **WorkspaceProjectRegistry**: Discovers pipeline projects at runtime
2. **Async Tier 1**: `_detect_tier1_project_membership_async()` triggers discovery

**Design**: `Process.PRIMARY_PROJECT_GID` remains `None`. Detection uses WorkspaceProjectRegistry:

```python
class Process(BusinessEntity):
    """Process entity.

    PRIMARY_PROJECT_GID is None because Process entities belong to
    multiple pipeline projects (Sales, Onboarding, etc.). Detection
    uses WorkspaceProjectRegistry for dynamic project lookup.
    """
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None  # Dynamic via WorkspaceProjectRegistry
```

**Detection Flow**:
```
Process Task
    |
    v
Async Tier 1 (WorkspaceProjectRegistry.lookup_or_discover_async)
    |
    +-- Found in Sales project -> EntityType.PROCESS, ProcessType.SALES
    +-- Found in Onboarding project -> EntityType.PROCESS, ProcessType.ONBOARDING
    +-- Not found -> Tier 2 fallback
```

##### ProcessHolder.PRIMARY_PROJECT_GID (FR-DET-003)

Per **ADR-0115**: ProcessHolder does NOT have a dedicated project. Detection relies on Tier 2 (name pattern) and Tier 3 (parent inference).

```python
class ProcessHolder(Task, HolderMixin["Process"]):
    """Holder for Process entities.

    PRIMARY_PROJECT_GID is intentionally None. ProcessHolder is a
    container task with no custom fields, not managed as a project
    member. Detection uses:
    - Tier 2: Name pattern "processes"/"process"
    - Tier 3: Parent inference from Unit
    """
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None  # Intentional - see ADR-0115
```

##### LocationHolder and UnitHolder (FR-DET-004)

Both holders have `PRIMARY_PROJECT_GID = None`, which is **intentional**:

| Holder | PRIMARY_PROJECT_GID | Rationale |
|--------|---------------------|-----------|
| LocationHolder | None | Container task; no dedicated project |
| UnitHolder | None | Container task; no dedicated project |

**Action**: Add docstring clarification to both classes explaining intentional None.

#### 3.3 Tier 2 Pattern Matching Enhancement (FR-DET-005)

Per **ADR-0117**: Enhance name pattern matching with word boundary-aware regex.

**Module Structure**:

```
src/autom8_asana/models/business/
    detection.py      # Enhanced _detect_by_name_pattern()
    patterns.py       # NEW: PatternSpec and PATTERN_CONFIG
```

**New File**: `patterns.py`

```python
"""Entity type detection patterns.

Per ADR-0117: Word boundary-aware pattern matching configuration.
"""

from dataclasses import dataclass
from autom8_asana.models.business.detection import EntityType

@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Configuration for entity type pattern matching."""
    patterns: tuple[str, ...]  # Patterns to match (singular and plural)
    word_boundary: bool = True  # Use word boundary matching
    strip_decorations: bool = True  # Strip [URGENT], (Primary), etc.


PATTERN_CONFIG: dict[EntityType, PatternSpec] = {
    EntityType.CONTACT_HOLDER: PatternSpec(
        patterns=("contacts", "contact"),
    ),
    EntityType.UNIT_HOLDER: PatternSpec(
        patterns=("units", "unit", "business units"),
    ),
    EntityType.OFFER_HOLDER: PatternSpec(
        patterns=("offers", "offer"),
    ),
    EntityType.PROCESS_HOLDER: PatternSpec(
        patterns=("processes", "process"),
    ),
    EntityType.LOCATION_HOLDER: PatternSpec(
        patterns=("location", "address"),
    ),
    EntityType.DNA_HOLDER: PatternSpec(
        patterns=("dna",),
    ),
    EntityType.RECONCILIATIONS_HOLDER: PatternSpec(
        patterns=("reconciliations", "reconciliation"),
    ),
    EntityType.ASSET_EDIT_HOLDER: PatternSpec(
        patterns=("asset edit", "asset edits"),
    ),
    EntityType.VIDEOGRAPHY_HOLDER: PatternSpec(
        patterns=("videography",),
    ),
}

# Priority order for pattern matching (most specific first)
PATTERN_PRIORITY: list[EntityType] = [
    EntityType.ASSET_EDIT_HOLDER,  # "asset edit" before others
    EntityType.CONTACT_HOLDER,
    EntityType.UNIT_HOLDER,
    EntityType.OFFER_HOLDER,
    EntityType.PROCESS_HOLDER,
    EntityType.LOCATION_HOLDER,
    EntityType.DNA_HOLDER,
    EntityType.RECONCILIATIONS_HOLDER,
    EntityType.VIDEOGRAPHY_HOLDER,
]
```

**Modified**: `detection.py` - `_detect_by_name_pattern()`

```python
import re
from functools import lru_cache
from .patterns import PATTERN_CONFIG, PATTERN_PRIORITY, PatternSpec

# Decoration stripping patterns
STRIP_PATTERNS = [
    r"^\[.*?\]\s*",      # [URGENT] prefix
    r"^>+\s*",           # >> prefix
    r"\s*<+$",           # << suffix
    r"\s*\(.*?\)$",      # (Primary) suffix
    r"^\d+\.\s*",        # "1. " numbered prefix
    r"^[-*]\s*",         # "- " or "* " bullet prefix
]

@lru_cache(maxsize=128)
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile pattern with word boundary markers (cached)."""
    return re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)


def _strip_decorations(name: str) -> str:
    """Remove common task name decorations."""
    result = name
    for pattern in STRIP_PATTERNS:
        result = re.sub(pattern, "", result)
    return result.strip()


def _matches_pattern(name: str, spec: PatternSpec) -> bool:
    """Check if name matches pattern spec."""
    for pattern in spec.patterns:
        if spec.word_boundary:
            compiled = _compile_pattern(pattern)
            if compiled.search(name):
                return True
        else:
            if pattern in name.lower():
                return True
    return False


def _detect_by_name_pattern(task: Task) -> DetectionResult | None:
    """Tier 2: Enhanced name pattern matching.

    Per ADR-0117: Word boundary matching with decoration stripping.
    """
    if not task.name:
        return None

    name_original = task.name
    name_stripped = _strip_decorations(name_original)

    for entity_type in PATTERN_PRIORITY:
        spec = PATTERN_CONFIG.get(entity_type)
        if spec is None:
            continue

        # Check both original and stripped
        for name in (name_original, name_stripped):
            if _matches_pattern(name, spec):
                expected_gid = get_registry().get_primary_gid(entity_type)
                return DetectionResult(
                    entity_type=entity_type,
                    confidence=CONFIDENCE_TIER_2,
                    tier_used=2,
                    needs_healing=True,
                    expected_project_gid=expected_gid,
                )

    return None
```

#### 3.4 Self-Healing Mechanism (FR-DET-006)

Per **ADR-0095** and **ADR-0118**: Self-healing with two trigger points.

**Module Structure**:

```
src/autom8_asana/
    persistence/
        session.py    # Modified: auto_heal, heal_dry_run parameters
        healing.py    # NEW: HealingResult, heal_entity_async, heal_entities_async
```

**New File**: `healing.py`

```python
"""Entity self-healing utilities.

Per ADR-0095/ADR-0118: Self-healing for entities missing project membership.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.base import BusinessEntity

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HealingResult:
    """Outcome of a healing operation."""
    entity_gid: str
    expected_project_gid: str
    success: bool
    dry_run: bool
    error: Exception | None

    def __bool__(self) -> bool:
        return self.success


async def heal_entity_async(
    entity: "BusinessEntity",
    client: "AsanaClient",
    dry_run: bool = False,
) -> HealingResult:
    """Heal a single entity by adding to expected project."""
    detection = getattr(entity, "_detection_result", None)

    if detection is None:
        raise ValueError(f"Entity {entity.gid} has no detection result")
    if not detection.needs_healing:
        raise ValueError(f"Entity {entity.gid} does not need healing")
    if not detection.expected_project_gid:
        raise ValueError(f"Entity {entity.gid} has no expected_project_gid")

    if dry_run:
        logger.info(
            "Dry run: would heal entity",
            extra={
                "entity_gid": entity.gid,
                "expected_project_gid": detection.expected_project_gid,
            },
        )
        return HealingResult(
            entity_gid=entity.gid,
            expected_project_gid=detection.expected_project_gid,
            success=True,
            dry_run=True,
            error=None,
        )

    try:
        await client.tasks.add_to_project_async(
            entity.gid,
            project_gid=detection.expected_project_gid,
        )
        logger.info(
            "Healed entity",
            extra={
                "entity_gid": entity.gid,
                "expected_project_gid": detection.expected_project_gid,
            },
        )
        return HealingResult(
            entity_gid=entity.gid,
            expected_project_gid=detection.expected_project_gid,
            success=True,
            dry_run=False,
            error=None,
        )
    except Exception as e:
        logger.warning(
            "Failed to heal entity",
            extra={
                "entity_gid": entity.gid,
                "expected_project_gid": detection.expected_project_gid,
                "error": str(e),
            },
        )
        return HealingResult(
            entity_gid=entity.gid,
            expected_project_gid=detection.expected_project_gid,
            success=False,
            dry_run=False,
            error=e,
        )


async def heal_entities_async(
    entities: list["BusinessEntity"],
    client: "AsanaClient",
    dry_run: bool = False,
    max_concurrent: int = 5,
) -> list[HealingResult]:
    """Heal multiple entities with concurrency control."""
    to_heal = [
        e for e in entities
        if hasattr(e, "_detection_result")
        and e._detection_result
        and e._detection_result.needs_healing
        and e._detection_result.expected_project_gid
    ]

    if not to_heal:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)

    async def heal_one(entity: "BusinessEntity") -> HealingResult:
        async with semaphore:
            return await heal_entity_async(entity, client, dry_run)

    return list(await asyncio.gather(*[heal_one(e) for e in to_heal]))
```

**Modified**: `session.py` - SaveSession

Add parameters and healing execution per ADR-0095.

#### 3.5 Startup Validation (FR-DET-007)

**Requirement**: Warn on invalid `ASANA_PROJECT_*` environment variables.

**Module**: `src/autom8_asana/config.py` (new or existing)

```python
"""Configuration validation utilities."""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Valid GID pattern (numeric string, typically 16+ digits)
GID_PATTERN = re.compile(r"^\d{10,}$")


def validate_project_env_vars(strict: bool = False) -> list[str]:
    """Validate ASANA_PROJECT_* environment variables.

    Args:
        strict: If True, raise on invalid vars. If False, warn only.

    Returns:
        List of warning messages for invalid vars.

    Raises:
        ValueError: If strict=True and invalid vars found.
    """
    warnings = []

    for key, value in os.environ.items():
        if not key.startswith("ASANA_PROJECT_"):
            continue

        if not value.strip():
            continue  # Empty is valid (use class default)

        if not GID_PATTERN.match(value.strip()):
            msg = f"Invalid GID format for {key}: '{value}' (expected numeric string)"
            warnings.append(msg)
            logger.warning(msg)

    if strict and warnings:
        raise ValueError(f"Invalid ASANA_PROJECT_* environment variables: {warnings}")

    return warnings


# Auto-validate at import if ASANA_STRICT_CONFIG is set
if os.environ.get("ASANA_STRICT_CONFIG", "").lower() == "true":
    validate_project_env_vars(strict=True)
```

---

### 4. Process Field Architecture

#### 4.1 Field Accessor Implementation (FR-PROC-001, FR-PROC-002, FR-PROC-003)

Per **ADR-0116**: Composition approach with all fields on single Process class.

**Module**: `src/autom8_asana/models/business/process.py`

**Field Organization**:

```python
class Process(BusinessEntity):
    """Process entity supporting all pipeline types.

    Fields are organized by pipeline type. All fields are accessible
    on any Process instance; accessing a field not present on the
    underlying task returns None.

    Per ADR-0116: Composition over inheritance.
    """

    # === COMMON FIELDS (8) ===
    # Available on all process types
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    process_notes = TextField(field_name="Process Notes")
    status = EnumField()
    priority = EnumField()
    vertical = EnumField()
    process_due_date = TextField(field_name="Due Date")
    assigned_to = PeopleField()

    # === SALES PIPELINE FIELDS (54+) ===

    # -- Financial --
    deal_value = NumberField(field_name="Deal Value")
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField(field_name="Weekly Ad Spend")
    discount = EnumField(field_name="Discount")
    solution_fee = NumberField(field_name="Solution Fee")

    # -- Dates --
    close_date = DateField(field_name="Close Date")
    demo_date = DateField(field_name="Demo Date")
    follow_up_date = DateField(field_name="Follow Up Date")
    appointment_date = DateField(field_name="Appointment Date")

    # -- Stage Tracking --
    sales_stage = EnumField(field_name="Sales Stage")
    lead_source = EnumField(field_name="Lead Source")
    lead_type = EnumField(field_name="Lead Type")
    lost_reason = EnumField(field_name="Lost Reason")
    objection = EnumField(field_name="Objection")

    # -- Assignment --
    rep = PeopleField(field_name="Rep")
    closer = PeopleField(field_name="Closer")
    setter = PeopleField(field_name="Setter")

    # -- Contact Info --
    contact_name = TextField(field_name="Contact Name")
    contact_email = TextField(field_name="Contact Email")
    contact_phone = TextField(field_name="Contact Phone")

    # -- Business Info --
    specialty = EnumField(field_name="Specialty")
    zip_code = TextField(field_name="Zip Code")
    time_zone = EnumField(field_name="Time Zone")

    # -- Platform/Product --
    platforms = MultiEnumField(field_name="Platforms")
    products = MultiEnumField(field_name="Products")
    services = MultiEnumField(field_name="Services")

    # -- Tracking --
    company_id = TextField(field_name="Company ID")
    ad_account_id = TextField(field_name="Ad Account ID")
    crm_id = TextField(field_name="CRM ID")

    # -- Notes/Comments --
    sales_notes = TextField(field_name="Sales Notes")
    demo_notes = TextField(field_name="Demo Notes")
    call_notes = TextField(field_name="Call Notes")

    # (Additional Sales fields - see Field Inventory Appendix)

    # === ONBOARDING PIPELINE FIELDS (33+) ===

    onboarding_status = EnumField(field_name="Onboarding Status")
    go_live_date = DateField(field_name="Go Live Date")
    kickoff_date = DateField(field_name="Kickoff Date")
    kickoff_completed = EnumField(field_name="Kickoff Completed")
    account_setup_complete = EnumField(field_name="Account Setup Complete")
    training_complete = EnumField(field_name="Training Complete")
    onboarding_rep = PeopleField(field_name="Onboarding Rep")
    implementation_notes = TextField(field_name="Implementation Notes")

    # (Additional Onboarding fields - see Field Inventory Appendix)

    # === IMPLEMENTATION PIPELINE FIELDS (28+) ===

    implementation_status = EnumField(field_name="Implementation Status")
    delivery_date = DateField(field_name="Delivery Date")
    build_status = EnumField(field_name="Build Status")
    creative_status = EnumField(field_name="Creative Status")
    launch_date = DateField(field_name="Launch Date")

    # (Additional Implementation fields - see Field Inventory Appendix)
```

**Field Inventory**: Complete field lists derived from CUSTOM-FIELD-REALITY-AUDIT.md.

#### 4.2 ProcessType Enum Extension (FR-PROC-004)

Current ProcessType enum has 7 values per PRD. If new pipeline types are discovered:

```python
class ProcessType(str, Enum):
    # Pipeline types (stakeholder-aligned)
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"

    # Future: Add new types here if discovered
    # AUDIT = "audit"
    # BUILD = "build"

    # Fallback (backward compatibility)
    GENERIC = "generic"
```

**Enum Extension Rules**:
1. New values MUST be lowercase
2. New values MUST have corresponding pipeline project in Asana
3. WorkspaceProjectRegistry MUST be updated to match new types
4. Existing values MUST NOT be removed (backward compatibility)

---

### 5. Test Strategy

#### 5.1 Integration Tests for Detection (FR-TEST-001)

**New File**: `tests/integration/test_detection.py`

```python
"""Integration tests for entity type detection.

Tests detection system with realistic task data across all tiers.
"""

import pytest
from autom8_asana.models.business.detection import (
    detect_entity_type,
    detect_entity_type_async,
    EntityType,
)
from autom8_asana.models.task import Task


class TestTier1Detection:
    """Tier 1: Project membership detection."""

    def test_business_detected_by_project(self, business_task):
        result = detect_entity_type(business_task)
        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1
        assert result.confidence == 1.0
        assert not result.needs_healing

    def test_process_detected_by_pipeline_project(self, sales_process_task):
        result = detect_entity_type(sales_process_task)
        assert result.entity_type == EntityType.PROCESS
        assert result.tier_used == 1


class TestTier2Detection:
    """Tier 2: Name pattern detection."""

    @pytest.mark.parametrize("name,expected_type", [
        ("Contacts", EntityType.CONTACT_HOLDER),
        ("Contact", EntityType.CONTACT_HOLDER),
        ("[URGENT] Contacts", EntityType.CONTACT_HOLDER),
        ("Acme Corp - Contacts (Primary)", EntityType.CONTACT_HOLDER),
        ("Units", EntityType.UNIT_HOLDER),
        ("Unit 1", EntityType.UNIT_HOLDER),
        ("Offers", EntityType.OFFER_HOLDER),
        ("Special Offer", EntityType.OFFER_HOLDER),
        ("Processes", EntityType.PROCESS_HOLDER),
        ("Process", EntityType.PROCESS_HOLDER),
    ])
    def test_decorated_names(self, name, expected_type):
        task = Task(gid="test", name=name)
        result = detect_entity_type(task)
        assert result.entity_type == expected_type
        assert result.tier_used == 2
        assert result.needs_healing

    @pytest.mark.parametrize("name", [
        "Community",      # Contains "unit" but not word boundary
        "Recontact",      # Contains "contact" but not word boundary
        "Prooffer",       # Contains "offer" but not word boundary
        "Random Task",
    ])
    def test_false_positives_avoided(self, name):
        task = Task(gid="test", name=name)
        result = detect_entity_type(task)
        assert result.entity_type == EntityType.UNKNOWN


class TestTier3Detection:
    """Tier 3: Parent inference detection."""

    def test_contact_inferred_from_contact_holder(self, contact_task):
        result = detect_entity_type(
            contact_task,
            parent_type=EntityType.CONTACT_HOLDER,
        )
        assert result.entity_type == EntityType.CONTACT
        assert result.tier_used == 3


class TestAsyncDetection:
    """Async detection with workspace discovery."""

    @pytest.mark.asyncio
    async def test_process_detected_via_workspace_discovery(
        self, sales_process_task, client
    ):
        result = await detect_entity_type_async(sales_process_task, client)
        assert result.entity_type == EntityType.PROCESS
```

#### 5.2 Test Pyramid Improvement (FR-TEST-002)

**Target**: Integration test files >= 18 (from 15).

**New Integration Test Files**:

| File | Coverage Area |
|------|---------------|
| `tests/integration/test_detection.py` | Detection system |
| `tests/integration/test_workspace_registry.py` | Registry discovery |
| `tests/integration/test_hydration.py` | Hierarchy hydration |

#### 5.3 Documentation Cleanup (FR-TEST-003)

**Files to Review**:
- All TDDs in `/docs/design/`
- All ADRs in `/docs/decisions/`
- Skill documentation in `/.claude/skills/`

**Action**: Search for "ProcessProjectRegistry" and remove/update references.

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| ProcessHolder project | None | Container task, no business data | ADR-0115 |
| Process field approach | Composition | Runtime type, field overlap | ADR-0116 |
| Tier 2 pattern matching | Word boundary regex | Accuracy, false positive prevention | ADR-0117 |
| Self-healing trigger | SaveSession + standalone | Flexible, opt-in | ADR-0118 |

---

## Complexity Assessment

**Level**: Module

**Justification**:
- Changes are contained within existing modules
- No new services or external dependencies
- Clear API boundaries maintained
- Existing patterns reused (descriptors, registry)

**Escalation Triggers** (would push to Service):
- If detection required external ML service
- If healing required separate worker process
- If field inventory required schema synchronization service

---

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 0 | Verify ProcessProjectRegistry absence | None | 0.5 day |
| 1a | PRIMARY_PROJECT_GID docstrings | Phase 0 | 0.5 day |
| 1b | Tier 2 pattern enhancement | Phase 0 | 2 days |
| 1c | Self-healing implementation | Phase 0 | 2 days |
| 1d | Startup validation | Phase 0 | 0.5 day |
| 2a | Process Sales fields (54+) | Phase 1a | 3 days |
| 2b | Process Onboarding fields | Phase 2a | 1 day |
| 2c | Process Implementation fields | Phase 2b | 1 day |
| 3a | Detection integration tests | Phase 1b | 2 days |
| 3b | Documentation cleanup | Phase 2 | 0.5 day |

**Total Estimate**: ~13 developer-days

### Migration Strategy

No migration needed - all changes are additive:
- New fields on Process are optional (return None if absent)
- Self-healing is opt-in
- Pattern matching improvements are backward compatible
- Existing tests continue to pass

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Tier 2 regex performance | Medium | Low | LRU cache for compiled patterns |
| Field naming conflicts | Medium | Medium | Use `process_` prefix for conflicts |
| Self-healing API failures | Low | Low | Non-blocking failures; retry support |
| Large Process class | Low | Low | Clear organization with comments |

---

## Observability

### Metrics

- Detection tier distribution (% Tier 1 vs 2 vs 3)
- Healing operations count (success/failure)
- Pattern match rate by entity type

### Logging

- Structured logging for all detection results
- Healing operations logged with entity_gid, project_gid
- Startup validation warnings logged

### Alerting

- Alert if Tier 1 detection rate drops below 80%
- Alert on self-healing failure rate > 10%

---

## Testing Strategy

### Unit Testing

- Pattern matching edge cases
- Decoration stripping variations
- Healing result scenarios

### Integration Testing

- Full detection chain with fixtures
- WorkspaceProjectRegistry discovery
- SaveSession with healing enabled

### Performance Testing

- Pattern matching latency (<1ms target)
- Detection throughput (1000 tasks/second target)

---

## Open Questions

All open questions resolved:

| Question | Resolution | ADR |
|----------|------------|-----|
| OQ-1: ProcessHolder project | None is intentional | ADR-0115 |
| OQ-2: Composition vs inheritance | Composition | ADR-0116 |
| OQ-3: Rollback plan | Git revert; PRD acknowledges | N/A |

---

## Module Structure Summary

### New Files

| File | Purpose |
|------|---------|
| `src/autom8_asana/models/business/patterns.py` | Pattern matching configuration |
| `src/autom8_asana/persistence/healing.py` | Self-healing utilities |
| `tests/integration/test_detection.py` | Detection integration tests |
| `tests/integration/test_workspace_registry.py` | Registry integration tests |

### Modified Files

| File | Changes |
|------|---------|
| `src/autom8_asana/models/business/detection.py` | Enhanced Tier 2 |
| `src/autom8_asana/models/business/process.py` | 80+ field descriptors |
| `src/autom8_asana/persistence/session.py` | Healing integration |
| `src/autom8_asana/config.py` | Startup validation |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Architect | Initial draft |

---

## Quality Gate Checklist

- [x] Traces to approved PRD (13 requirements mapped)
- [x] All significant decisions have ADRs (ADR-0115, 0116, 0117, 0118)
- [x] Component responsibilities are clear
- [x] Interfaces defined (healing API, pattern config)
- [x] Complexity level justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable
- [x] OQ-1 resolved (ProcessHolder detection - ADR-0115)
- [x] OQ-2 resolved (composition vs inheritance - ADR-0116)
- [x] Process field architecture supports 54+ Sales fields
- [x] Module structure defined for new/modified files
- [x] No blocking open questions remain

---

## Appendix A: Field Inventory

### Sales Pipeline Fields (Target: 54+)

See CUSTOM-FIELD-REALITY-AUDIT.md for complete field listing.

**Categories**:
- Financial (5): deal_value, mrr, weekly_ad_spend, discount, solution_fee
- Dates (4): close_date, demo_date, follow_up_date, appointment_date
- Stage Tracking (5): sales_stage, lead_source, lead_type, lost_reason, objection
- Assignment (3): rep, closer, setter
- Contact Info (3): contact_name, contact_email, contact_phone
- Business Info (3): specialty, zip_code, time_zone
- Platform/Product (3): platforms, products, services
- Tracking (3): company_id, ad_account_id, crm_id
- Notes (3): sales_notes, demo_notes, call_notes
- Additional (22): Various pipeline-specific fields

### Onboarding Pipeline Fields (Target: 33+)

**Categories**:
- Status (3): onboarding_status, kickoff_completed, account_setup_complete
- Dates (2): go_live_date, kickoff_date
- Assignment (1): onboarding_rep
- Notes (1): implementation_notes
- Additional (26): Various onboarding-specific fields

### Implementation Pipeline Fields (Target: 28+)

**Categories**:
- Status (3): implementation_status, build_status, creative_status
- Dates (2): delivery_date, launch_date
- Additional (23): Various implementation-specific fields
