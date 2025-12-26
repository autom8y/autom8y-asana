# TDD-12: Technical Debt & Migration

> Consolidated TDD for debt remediation, documentation reset, and legacy cleanup.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-TECH-DEBT-REMEDIATION, TDD-DOCS-EPOCH-RESET
- **Related ADRs**: ADR-0018 (Deprecation and Migration), ADR-0014 (Backward Compatibility)
- **PRD References**: PRD-TECH-DEBT-REMEDIATION, PRD-DOCS-EPOCH-RESET

---

## Overview

This consolidated TDD addresses two complementary initiatives:

1. **Technical Debt Remediation**: 13 items across detection system reliability, Process entity enhancement, and test coverage improvements
2. **Documentation Epoch Reset**: Removing outdated status claims, correcting entity counts, and establishing the Asana-as-database paradigm documentation

Both initiatives share a common theme: aligning documentation and implementation with current reality while maintaining backward compatibility during transition.

---

## Tech Debt Remediation

### Detection System Foundation

The detection system determines entity types using a 5-tier strategy. Technical debt exists in configuration, pattern matching, and self-healing capabilities.

#### PRIMARY_PROJECT_GID Configuration

| Entity | PRIMARY_PROJECT_GID | Rationale |
|--------|---------------------|-----------|
| Process | None | Dynamic via WorkspaceProjectRegistry (multiple pipeline projects) |
| ProcessHolder | None (intentional) | Container task with no custom fields; uses Tier 2/3 detection |
| LocationHolder | None (intentional) | Container task; no dedicated project |
| UnitHolder | None (intentional) | Container task; no dedicated project |

**Detection Flow for Process**:

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

#### Tier 2 Pattern Matching Enhancement

Word boundary-aware regex prevents false positives (e.g., "Community" should not match "unit").

**Pattern Configuration**:

```python
@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Configuration for entity type pattern matching."""
    patterns: tuple[str, ...]  # Patterns to match (singular and plural)
    word_boundary: bool = True  # Use word boundary matching
    strip_decorations: bool = True  # Strip [URGENT], (Primary), etc.

PATTERN_CONFIG: dict[EntityType, PatternSpec] = {
    EntityType.CONTACT_HOLDER: PatternSpec(patterns=("contacts", "contact")),
    EntityType.UNIT_HOLDER: PatternSpec(patterns=("units", "unit", "business units")),
    EntityType.OFFER_HOLDER: PatternSpec(patterns=("offers", "offer")),
    EntityType.PROCESS_HOLDER: PatternSpec(patterns=("processes", "process")),
    # ... additional patterns
}
```

**Decoration Stripping**: Removes common prefixes/suffixes before matching:
- `[URGENT] Contacts` -> `Contacts`
- `Acme Corp - Contacts (Primary)` -> `Acme Corp - Contacts`

#### Self-Healing Mechanism

Entities detected via Tier 2+ may be missing project membership. Self-healing adds them to the correct project.

**API**:

```python
@dataclass(frozen=True, slots=True)
class HealingResult:
    entity_gid: str
    expected_project_gid: str
    success: bool
    dry_run: bool
    error: Exception | None

async def heal_entity_async(
    entity: BusinessEntity,
    client: AsanaClient,
    dry_run: bool = False,
) -> HealingResult: ...

async def heal_entities_async(
    entities: list[BusinessEntity],
    client: AsanaClient,
    dry_run: bool = False,
    max_concurrent: int = 5,
) -> list[HealingResult]: ...
```

**Trigger Points**:
1. SaveSession integration (auto_heal parameter)
2. Standalone `heal_entity_async()` function

### Process Entity Enhancement

Process entities support multiple pipeline types (Sales, Onboarding, Implementation) with 80+ custom field accessors.

**Field Organization** (composition over inheritance):

| Category | Field Count | Examples |
|----------|-------------|----------|
| Common | 8 | started_at, status, priority, assigned_to |
| Sales | 54+ | deal_value, mrr, rep, closer, sales_stage |
| Onboarding | 33+ | onboarding_status, go_live_date, kickoff_completed |
| Implementation | 28+ | implementation_status, build_status, launch_date |

All fields are accessible on any Process instance; accessing a field not present on the underlying task returns None.

### Startup Validation

Environment variable validation warns on invalid `ASANA_PROJECT_*` values:

```python
def validate_project_env_vars(strict: bool = False) -> list[str]:
    """Validate ASANA_PROJECT_* environment variables.

    Args:
        strict: If True, raise on invalid vars. If False, warn only.

    Returns:
        List of warning messages for invalid vars.
    """
```

---

## Documentation Epoch Reset

### Status Corrections

Files containing outdated claims:

| File | Current Claim | Correction |
|------|---------------|------------|
| PROJECT_CONTEXT.md | `Stage: Prototype` | `Stage: Production` |
| context.md | "Prototype for extracting other APIs" | "Production SDK" |
| context.md | `Test coverage: ~0%` | "Comprehensive" (qualitative) |
| tech-stack.md | `Version: 0.1.0 (prototype)` | `Version: 0.1.0` |
| entity-reference.md | 4 stubs listed | 3 stubs (DNAHolder, ReconciliationHolder, VideographyHolder) |

**Note**: AssetEdit is fully implemented (681 lines, 11 typed fields) and not a stub.

### Paradigm Documentation

The Asana-as-database paradigm is the architectural foundation enabling typed business entities.

**Location**: `.claude/skills/autom8-asana-domain/paradigm.md`

**Core Mapping**:

| Asana Concept | Database Analog | SDK Implementation |
|---------------|-----------------|-------------------|
| Task | Row | Entity instance (Business, Contact, etc.) |
| Custom Field | Column | Typed property descriptor |
| Subtask | FK / Child row | Holder children (ContactHolder -> Contact[]) |
| Project membership | Table membership | Entity type detection |
| Asana UI | Admin interface | Free CRUD for operators |

**Discoverability**: 2-click path from CLAUDE.md via Skills Architecture table.

---

## Migration Patterns

### Deprecation Warning Strategy

Standard Python mechanism for API deprecation:

```python
warnings.warn(
    f"Importing '{name}' from 'autom8_asana.compat' is deprecated. "
    f"Use '{canonical_location}' instead. "
    f"This alias will be removed in version 1.0.0.",
    DeprecationWarning,
    stacklevel=3,  # Points to user's import statement
)
```

**Key Choices**:
- **DeprecationWarning category**: Standard, filterable, shown in pytest
- **Lazy `__getattr__`**: Only warns when attribute actually used
- **Removal version in message**: Clear timeline for migration

### Big-Bang Migration for Infrastructure

Cache backend migration (S3 to Redis) uses big-bang cutover:

```
T-7 days: Provision Redis infrastructure
T-3 days: Deploy SDK to staging with Redis
T-0:      Production deployment (100% cache miss expected)
T+1hr:    Verify hit rate stabilizing (target >= 80%)
T+7 days: Decommission S3 cache
```

**Rationale**: Dual-read introduces complexity, tech debt, and consistency issues. Cache data rebuilds quickly from API.

### Interface Evolution for API Changes

Replace internals with new implementation; maintain deprecated wrapper:

```python
def struc(self, ...) -> "pd.DataFrame":
    """Deprecated: Use to_dataframe() instead."""
    warnings.warn(
        "struc() is deprecated. Use to_dataframe() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Delegate to new implementation, convert to pandas
    return self.to_dataframe(...).to_pandas()
```

**Minimum Deprecation Period**: 2 minor versions

### Deprecated Aliases with Type Changes

For fundamental incompatible changes (e.g., Hours model):

```python
@property
def monday(self) -> list[str]:
    """Monday operating hours (multi-enum time values)."""
    return self._get_multi_enum_field(self.Fields.MONDAY)

@property
def monday_hours(self) -> list[str]:
    """Deprecated: Use .monday instead. Returns list[str], not str."""
    warnings.warn(
        "monday_hours is deprecated. Use 'monday' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return self.monday
```

**Key Principle**: Return correct types even if breaking. Type safety prevents silent data loss.

---

## Testing Strategy

### Detection Integration Tests

```python
class TestTier2Detection:
    @pytest.mark.parametrize("name,expected_type", [
        ("Contacts", EntityType.CONTACT_HOLDER),
        ("[URGENT] Contacts", EntityType.CONTACT_HOLDER),
        ("Acme Corp - Contacts (Primary)", EntityType.CONTACT_HOLDER),
    ])
    def test_decorated_names(self, name, expected_type):
        task = Task(gid="test", name=name)
        result = detect_entity_type(task)
        assert result.entity_type == expected_type
        assert result.tier_used == 2
        assert result.needs_healing

    @pytest.mark.parametrize("name", [
        "Community",   # Contains "unit" but not word boundary
        "Recontact",   # Contains "contact" but not word boundary
    ])
    def test_false_positives_avoided(self, name):
        task = Task(gid="test", name=name)
        result = detect_entity_type(task)
        assert result.entity_type == EntityType.UNKNOWN
```

### Documentation Validation

```bash
# Verify no stale claims remain
grep -r "Prototype" .claude/           # Should return 0 hits
grep -r "~0%" .claude/                 # Should return 0 hits
grep -r "4 stub" .claude/              # Should return 0 hits

# Verify discoverability path
# Navigate CLAUDE.md -> Skills table -> paradigm.md in 2 clicks

# Verify cross-references
# All markdown links in updated files resolve
```

### Migration Testing

- Deprecated API calls emit warnings in test output
- Type changes surface immediately (fail fast)
- Caller logging tracks remaining deprecated usage

---

## Implementation Plan

### Phase 1: Detection System (5 days)

| Task | Estimate |
|------|----------|
| Verify ProcessProjectRegistry absence | 0.5 day |
| Add PRIMARY_PROJECT_GID docstrings | 0.5 day |
| Tier 2 pattern enhancement | 2 days |
| Self-healing implementation | 2 days |
| Startup validation | 0.5 day |

### Phase 2: Process Entity (5 days)

| Task | Estimate |
|------|----------|
| Sales fields (54+) | 3 days |
| Onboarding fields (33+) | 1 day |
| Implementation fields (28+) | 1 day |

### Phase 3: Tests & Documentation (3 days)

| Task | Estimate |
|------|----------|
| Detection integration tests | 2 days |
| Documentation epoch reset | 0.5 day |
| Documentation cleanup (remove stale refs) | 0.5 day |

**Total**: ~13 developer-days

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tier 2 regex performance | Medium | LRU cache for compiled patterns |
| Field naming conflicts | Medium | Use `process_` prefix for conflicts |
| Self-healing API failures | Low | Non-blocking; retry support |
| Breaking type changes | Medium | Clear deprecation warnings with migration guidance |
| Initial cache miss spike | Low | Temporary; cache warms within 1 hour |

---

## Cross-References

### Related ADRs

| ADR | Topic |
|-----|-------|
| ADR-0014 | Backward Compatibility and Deprecation |
| ADR-0018 | Deprecation and Migration Strategies |

### Module Structure

**New Files**:
- `src/autom8_asana/models/business/patterns.py` - Pattern matching configuration
- `src/autom8_asana/persistence/healing.py` - Self-healing utilities
- `.claude/skills/autom8-asana-domain/paradigm.md` - Asana-as-database documentation
- `tests/integration/test_detection.py` - Detection integration tests

**Modified Files**:
- `src/autom8_asana/models/business/detection.py` - Enhanced Tier 2
- `src/autom8_asana/models/business/process.py` - 80+ field descriptors
- `src/autom8_asana/persistence/session.py` - Healing integration
- `.claude/skills/autom8-asana-domain/context.md` - Status updates
- `.claude/PROJECT_CONTEXT.md` - Stage update, paradigm reference

### Observability

**Metrics**:
- Detection tier distribution (% Tier 1 vs 2 vs 3)
- Healing operations count (success/failure)
- Deprecated API call frequency (caller logging)

**Alerts**:
- Tier 1 detection rate drops below 80%
- Self-healing failure rate exceeds 10%

---

## Quality Gate Checklist

- [x] Traces to approved PRDs (PRD-TECH-DEBT-REMEDIATION, PRD-DOCS-EPOCH-RESET)
- [x] Significant decisions have ADRs (ADR-0014, ADR-0018)
- [x] Component responsibilities defined (detection, healing, Process fields)
- [x] Migration patterns documented with examples
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable with estimates
- [x] Test strategy covers detection, deprecation, and documentation validation
- [x] Backward compatibility maintained via deprecation period
