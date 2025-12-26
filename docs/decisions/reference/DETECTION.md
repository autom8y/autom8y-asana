# ADR Summary: Detection & Auto-Resolution

> Consolidated decision record for entity type detection, auto-resolution, name resolution, and self-healing patterns. Individual ADRs archived.

## Overview

The Detection & Auto-Resolution system enables the SDK to automatically determine entity types from Asana tasks and resolve ambiguities without requiring explicit configuration. This system evolved from simple name-based heuristics to a sophisticated five-tier detection architecture with integrated self-healing capabilities.

Entity type detection is critical for two primary scenarios: (1) upward hierarchy traversal during hydration, where each parent task must be typed correctly to build the Business model structure, and (2) orphaned entity recovery, where entities missing project membership can still be identified through fallback strategies. The system balances performance (most detections complete in <1ms with zero API calls) with accuracy (95%+ success rate) through a carefully ordered fallback chain.

The detection architecture integrates tightly with SaveSession's self-healing mechanism, enabling entities detected via fallback tiers to be automatically repaired by adding correct project membership—ensuring future detections succeed via the fast Tier 1 path.

## Key Decisions

### 1. Core Architecture: Five-Tier Fallback Chain

**Context**: Need robust type detection that handles healthy entities, orphaned entities, decorated names, and unknown structures with predictable performance.

**Decision**: Implement five-tier detection with strict ordering and early return:
1. **Tier 1**: Project membership lookup (O(1), deterministic)
2. **Tier 2**: Name pattern matching with word boundaries (60% confidence)
3. **Tier 3**: Parent-child type inference (80% confidence)
4. **Tier 4**: Structure inspection via API (requires async, opt-in)
5. **Tier 5**: UNKNOWN fallback

Synchronous path covers Tiers 1-3 (zero API calls). Async path adds Tier 4 behind `allow_structure_inspection` flag.

**Rationale**: Sequential if-else with early return provides simplicity, debuggability, and observable tier metrics while maintaining strict performance guarantees. Tier ordering prioritizes speed and reliability: project membership is definitive (Tier 1), name patterns are fast but heuristic (Tier 2), parent inference is reliable when available (Tier 3), structure inspection is accurate but expensive (Tier 4).

**Source ADRs**: ADR-0094 (Fallback Chain Design), ADR-0142 (Package Structure)

### 2. Tier 1: Dynamic Project Discovery

**Context**: Static project GID registry (`PRIMARY_PROJECT_GID`) covers known entity types but cannot handle dynamically created pipeline projects or multi-workspace deployments.

**Decision**: Implement `WorkspaceProjectRegistry` with lazy discovery that supplements static `ProjectTypeRegistry`. On first async detection for an unregistered project GID, discover all workspace projects and register them dynamically. Discovery is idempotent and session-scoped.

**Rationale**: Lazy discovery provides zero-configuration DX while enabling support for dynamic pipelines. Discovery triggered on first unknown GID (not at startup) minimizes latency. Static registrations remain authoritative and are never overwritten by discovery.

**Source ADRs**: ADR-0109 (Lazy Discovery Timing), ADR-0093 (Project Type Registry), ADR-0096 (ProcessType Expansion)

### 3. Tier 2: Enhanced Pattern Matching with Word Boundaries

**Context**: Simple substring matching (`"contacts" in name.lower()`) fails for decorated names ("Contact List", "Unit 1") and risks false positives ("Community" matching "unit").

**Decision**: Implement word boundary-aware regex matching with decoration stripping:
- Patterns include both singular and plural forms ("contacts", "contact")
- Regex with `\b` word boundaries prevents substring false positives
- Strip common decorations ([URGENT], >>, (Primary)) before matching
- Patterns compiled with `lru_cache` for performance

**Rationale**: Word boundary matching achieves 95%+ accuracy on decorated names while maintaining sub-millisecond performance through cached compilation. Decoration stripping handles real-world task naming conventions without requiring strict naming discipline.

**Source ADRs**: ADR-0138 (Tier 2 Pattern Enhancement), ADR-0068 (Type Detection Strategy)

### 4. Tier 3: Parent-Child Type Inference

**Context**: Holder entities (ContactHolder, OfferHolder, etc.) have predictable children. When traversing upward or hydrating downward, parent type provides strong signal.

**Decision**: Implement `PARENT_CHILD_MAP` that maps parent EntityType to expected child types. When `parent_type` is provided to detection, Tier 3 infers child type with 80% confidence. Supports disambiguation for parents with multiple child types (e.g., Unit has both OfferHolder and ProcessHolder children, distinguished by name).

**Rationale**: Parent-child relationships are structural invariants in the Business model hierarchy. Leveraging this knowledge provides high-confidence detection without API calls. 80% confidence (vs Tier 2's 60%) reflects the reliability of structural relationships.

**Source ADRs**: ADR-0094 (Fallback Chain), ADR-0068 (Type Detection Strategy)

### 5. Tier 4: Structure Inspection with Opt-In

**Context**: Business and Unit entities have variable names ("Acme Corp", "Premium Package") that cannot be detected via Tier 2 patterns. Structure inspection (examining subtask names) provides definitive detection but requires API call.

**Decision**: Tier 4 fetches subtasks and examines their names for holder indicators:
- Business: has "contacts", "units", or "location" subtasks
- Unit: has "offers" or "processes" subtasks
- Gated behind `allow_structure_inspection=True` flag (disabled by default)
- Only available in async detection path
- Adds ~200ms latency per detection

**Rationale**: Structure inspection is deterministic but expensive. Opt-in design ensures callers explicitly accept the latency cost. Async-only constraint prevents accidental API calls in synchronous code paths.

**Source ADRs**: ADR-0094 (Fallback Chain), ADR-0068 (Type Detection Strategy)

### 6. Name Resolution: Dynamic Field and Resource Resolution

**Context**: SDK needs to resolve human-readable names to Asana GIDs for custom fields, tags, users, enum options, and sections without requiring environment-specific configuration.

**Decision**: Implement context-specific resolution strategies:
- **Custom fields**: `CustomFieldAccessor` with name-to-GID index built from entity's `custom_fields` list (session-cached)
- **Tags/Users**: `NameResolver` with lazy-loaded workspace-level caches (case-insensitive)
- **Sections**: Project-scoped lazy cache
- **Templates**: Fuzzy section matching ("template", "templates", "template tasks")

All resolvers use lazy loading (cache populated on first use) and case-insensitive matching.

**Rationale**: Different resource types have fundamentally different resolution patterns. Custom fields are entity-scoped, tags/users are workspace-scoped, sections are project-scoped. Lazy loading minimizes startup latency. Case-insensitive matching provides user-friendly API.

**Source ADRs**: ADR-0034 (Dynamic Custom Field Resolution), ADR-0089 (Demo Name Resolution), ADR-0112 (Custom Field GID Resolution), ADR-0106 (Template Discovery)

### 7. Ambiguity Handling: First Match with Full Transparency

**Context**: Resolution strategies may find multiple matching entities (e.g., multiple Units with same vertical). How should results be returned?

**Decision**: Return first match in `entity` field with `ambiguous=True` flag and all matches in `candidates` list:
```python
result.entity        # First match (convenience)
result.ambiguous     # True if multiple matches
result.success       # False when ambiguous
result.candidates    # All matches for inspection
```

**Rationale**: First match enables simple code paths ("give me a Unit") while preserving full information for sophisticated callers. `success` property returns False for ambiguous results, forcing explicit handling. No information loss—all candidates available for manual selection.

**Source ADRs**: ADR-0071 (Resolution Ambiguity Handling)

### 8. Self-Healing: Opt-In Additive Repair

**Context**: Entities detected via Tiers 2-5 lack proper project membership. How should we repair them for future Tier 1 detection?

**Decision**: Implement self-healing with two trigger points:
1. **SaveSession integration**: `SaveSession(auto_heal=True)` heals tracked entities after commit
2. **Standalone utility**: `heal_entity_async()` for on-demand healing

Healing is:
- Opt-in (disabled by default)
- Additive-only (adds project membership, never removes)
- Non-blocking (failures don't fail commit)
- Observable (results in `SaveResult.healed_entities` and `healing_failures`)
- Dry-run capable (`heal_dry_run=True` previews without executing)

**Rationale**: Opt-in design prevents surprise behavior. Additive-only is safe—removing memberships could break workflows. Non-blocking ensures save operations succeed even if healing fails. Two trigger points serve different use cases: SaveSession for normal workflow, standalone for batch repair scripts.

**Source ADRs**: ADR-0095 (Self-Healing Integration), ADR-0139 (Self-Healing Opt-In Design), ADR-0144 (HealingResult Consolidation)

### 9. Validation-Phase Detection for Unsupported Operations

**Context**: Direct modifications to collection fields (`tags`, `projects`, `memberships`, `dependencies`) are silently ignored by Asana API, causing data loss and confusion.

**Decision**: Detect unsupported modifications during SavePipeline's VALIDATE phase (before API calls) by checking `ChangeTracker.get_changes()` against `UNSUPPORTED_FIELDS` set. Raise `UnsupportedOperationError` with actionable error message suggesting correct action methods (`add_tag()`, `add_to_project()`, etc.).

**Rationale**: Validation phase is the natural extension point for policy enforcement. Leveraging existing `ChangeTracker.get_changes()` avoids duplicating change detection logic. Fail-fast prevents partial commits. Actionable error messages guide developers to correct API.

**Source ADRs**: ADR-0043 (Validation-Phase Detection)

### 10. Detection Package Structure: Separation by Tier

**Context**: `detection.py` grew to 1125 lines containing types, configuration, detection logic for 5 tiers, and utilities in a single file—violating 250-line soft limit and Single Responsibility Principle.

**Decision**: Convert to package directory with 7 focused modules:
- `types.py`: EntityType enum, DetectionResult dataclass (170 lines)
- `config.py`: ENTITY_TYPE_INFO, NAME_PATTERNS, mappings (230 lines)
- `tier1.py`: Project membership detection (180 lines)
- `tier2.py`: Name pattern detection (150 lines)
- `tier3.py`: Parent inference detection (60 lines)
- `tier4.py`: Structure inspection detection (80 lines)
- `facade.py`: Unified detection orchestration (200 lines)
- `__init__.py`: Re-exports for backward compatibility

**Rationale**: Module boundaries follow natural concern separation. Each tier is logically independent. Strict layering (types → config → tiers → facade) prevents circular imports. Re-exports maintain 100% backward compatibility.

**Source ADRs**: ADR-0142 (Detection Package Structure)

### 11. Detection Result Caching: Inline Integration Before Tier 4

**Context**: Tier 4 structure inspection adds 200ms per call. Repeated detection for same task (e.g., during multi-level hydration) compounds latency.

**Decision**: Cache detection results inline within `detect_entity_type_async()`:
- Cache check AFTER Tiers 1-3, BEFORE Tier 4 (no fast-path overhead)
- Extract cache provider from `client` parameter (no new parameter)
- Serialize `DetectionResult` via `dataclasses.asdict()` with enum string conversion
- Cache only successful Tier 4 results (Tiers 1-3 are O(1), caching adds overhead)

**Rationale**: Caching before Tier 4 only targets the expensive operation without slowing Tiers 1-3. Extracting cache from existing client parameter avoids API breakage. Inline logic (vs dedicated coordinator) is appropriate for simple check-store pattern.

**Source ADRs**: ADR-0143 (Detection Result Caching Strategy)

### 12. ProcessHolder Detection: Intentional None Project

**Context**: ProcessHolder is a container task with `PRIMARY_PROJECT_GID = None`. Should it have a dedicated project for Tier 1 detection?

**Decision**: ProcessHolder SHALL NOT have a dedicated project. Detection relies on Tier 2 (name pattern "processes") and Tier 3 (child of Unit). Document intentional None in docstring.

**Rationale**: ProcessHolder is purely structural with no custom fields or business data. Team does not manage holders in project views. Creating project just for detection would add operational overhead without business value. Tier 3 parent inference from Unit is highly reliable for this use case.

**Source ADRs**: ADR-0135 (ProcessHolder Detection Strategy)

## Evolution Timeline

| Date | Decision | Impact |
|------|----------|--------|
| 2025-12-09 | ADR-0034: Dynamic custom field resolution | Enabled name-based field resolution, eliminating hardcoded GIDs |
| 2025-12-10 | ADR-0043: Validation-phase unsupported operation detection | Prevented silent failures on collection field modifications |
| 2025-12-12 | ADR-0089: Name resolution for demo scripts | Established lazy-loading session-scoped caching pattern |
| 2025-12-16 | ADR-0068: Type detection strategy | Defined name-based primary with structure fallback |
| 2025-12-16 | ADR-0071: Resolution ambiguity handling | Established first-match-with-transparency pattern |
| 2025-12-17 | ADR-0094: Detection fallback chain design | Core five-tier architecture with sync/async split |
| 2025-12-17 | ADR-0095: Self-healing SaveSession integration | Opt-in healing after commit operations |
| 2025-12-17 | ADR-0096: ProcessType expansion | Added 6 pipeline process types with detection |
| 2025-12-18 | ADR-0106: Template discovery pattern | Fuzzy section matching for template tasks |
| 2025-12-18 | ADR-0109: Lazy discovery timing | Workspace project discovery on first unknown GID |
| 2025-12-18 | ADR-0112: Custom field GID resolution | CustomFieldAccessor pattern for field name resolution |
| 2025-12-19 | ADR-0135: ProcessHolder detection | Intentional None project with Tier 2/3 detection |
| 2025-12-19 | ADR-0138: Tier 2 pattern enhancement | Word boundary regex with decoration stripping |
| 2025-12-19 | ADR-0139: Self-healing opt-in design | Two trigger points (SaveSession + standalone utility) |
| 2025-12-19 | ADR-0142: Detection package structure | Split 1125-line monolith into 7 focused modules |
| 2025-12-19 | ADR-0144: HealingResult consolidation | Unified result type across healing contexts |
| 2025-12-23 | ADR-0143: Detection result caching | Cache Tier 4 results for 40x speedup on repeat calls |

## Cross-References

**Related PRDs**:
- PRD-DETECTION: Detection system requirements
- PRD-PROCESS-PIPELINE: Pipeline process type detection
- PRD-WORKSPACE-PROJECT-REGISTRY: Dynamic project discovery
- PRD-0003.1: Dynamic custom field resolution
- PRD-0006: Unsupported operation detection

**Related TDDs**:
- TDD-DETECTION: Detection architecture and algorithms
- TDD-CACHE-PERF-DETECTION: Detection result caching design
- TDD-0009.1: Dynamic custom field resolution implementation
- TDD-0011: Validation phase implementation

**Related Summaries**:
- ADR-SUMMARY-SAVESESSION: Self-healing integration with SaveSession workflow
- ADR-SUMMARY-CACHE: Detection result caching integration with cache infrastructure
- ADR-SUMMARY-HYDRATION: Detection usage during hierarchy traversal

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0034 | Dynamic Custom Field Resolution Strategy | 2025-12-09 | Protocol-based resolver with name normalization and session-cached index |
| ADR-0043 | Validation-Phase Detection for Unsupported Operations | 2025-12-10 | Detect unsupported collection modifications in VALIDATE phase before API calls |
| ADR-0068 | Type Detection Strategy for Upward Traversal | 2025-12-16 | Name-based primary with structure inspection fallback |
| ADR-0071 | Resolution Ambiguity Handling | 2025-12-16 | Return first match with ambiguous flag and full candidates list |
| ADR-0089 | Name Resolution Approach for Demo Scripts | 2025-12-12 | Lazy-loading name resolver with session-scoped caching |
| ADR-0094 | Detection Fallback Chain Design | 2025-12-17 | Five-tier sequential detection with early return and async gate for Tier 4 |
| ADR-0095 | Self-Healing Integration with SaveSession | 2025-12-17 | Opt-in healing after normal save operations with non-blocking failures |
| ADR-0096 | ProcessType Expansion and Detection | 2025-12-17 | Six pipeline process types with project-based detection |
| ADR-0106 | Template Discovery Pattern | 2025-12-18 | Fuzzy section matching for "template" patterns |
| ADR-0109 | Lazy Discovery Timing for WorkspaceProjectRegistry | 2025-12-18 | Trigger discovery on first async detection for unregistered project GID |
| ADR-0112 | Custom Field GID Resolution Pattern | 2025-12-18 | Use CustomFieldAccessor for name-to-GID resolution and API formatting |
| ADR-0135 | ProcessHolder Detection Strategy | 2025-12-19 | No dedicated project; rely on Tier 2/3 detection with intentional None |
| ADR-0138 | Detection Tier 2 Pattern Matching Enhancement | 2025-12-19 | Word boundary regex with singular/plural forms and decoration stripping |
| ADR-0139 | Self-Healing Opt-In Design | 2025-12-19 | Two trigger points (SaveSession + standalone) with dry-run support |
| ADR-0142 | Detection Package Structure | 2025-12-19 | Convert 1125-line file to 7-module package with tier-based separation |
| ADR-0143 | Detection Result Caching Strategy | 2025-12-23 | Inline cache integration before Tier 4 for 40x speedup |
| ADR-0144 | HealingResult Type Consolidation | 2025-12-19 | Unified HealingResult in models.py with str errors and dry_run support |

## Implementation Guidance

### When to Use Which Tier

**Tier 1** (Project Membership):
- Use for all entities with correct project membership
- Preferred path for performance (<1ms, O(1))
- Requires `WorkspaceProjectRegistry` discovery for dynamic projects

**Tier 2** (Name Patterns):
- Fallback for holder entities ("Contacts", "Offers", "Processes")
- 60% confidence due to heuristic nature
- Triggers `needs_healing=True` for subsequent repair

**Tier 3** (Parent Inference):
- Use when `parent_type` is known from traversal
- 80% confidence from structural relationships
- Ideal for upward hydration where parent is already typed

**Tier 4** (Structure Inspection):
- Last resort for Business/Unit with variable names
- Requires explicit `allow_structure_inspection=True`
- Adds ~200ms latency per call (cache mitigates repeats)
- Only available in async path

**Tier 5** (UNKNOWN):
- Fallback when all tiers fail
- Entity can still be tracked but operations may be limited
- Consider manual intervention or additional metadata

### Healing Best Practices

**SaveSession Integration**:
```python
# Opt-in healing during commit
async with SaveSession(client, auto_heal=True) as session:
    session.track(entity)  # Detection result must have needs_healing=True
    result = await session.commit()

    if result.healed_entities:
        logger.info(f"Healed {len(result.healed_entities)} entities")

    if result.healing_failures:
        for failure in result.healing_failures:
            logger.warning(f"Failed to heal {failure.entity_gid}: {failure.error}")
```

**Standalone Healing**:
```python
# Heal specific entity
result = await detect_entity_type_async(task, client)
if result.needs_healing:
    healing = await heal_entity_async(entity, client)
    if not healing.success:
        logger.error(f"Healing failed: {healing.error}")

# Batch healing
entities = await fetch_orphaned_entities()
results = await heal_entities_async(entities, client, max_concurrent=5)
success_count = sum(1 for r in results if r.success)
```

**Dry-Run Preview**:
```python
# Preview what would be healed
async with SaveSession(client, auto_heal=True, heal_dry_run=True) as session:
    session.track(entity)
    preview = await session.commit()
    print(f"Would heal: {preview.healed_entities}")

# Then execute
async with SaveSession(client, auto_heal=True) as session:
    session.track(entity)
    result = await session.commit()
```

### Performance Considerations

**Zero Overhead for Fast Path**:
- Tiers 1-3 must complete without API calls
- Cache check only before Tier 4 (not at function entry)
- Regex patterns compiled with `lru_cache`

**Lazy Loading Strategy**:
- Discovery triggered on first unknown GID (not at startup)
- Name resolver caches populated on first use
- Custom field index built once per extraction session

**Caching Efficiency**:
- Detection results cached only for Tier 4 (expensive operation)
- 300s TTL with invalidation on SaveSession commit
- 40x speedup on repeated detection (200ms → <5ms)

### Error Handling Patterns

**Detection Errors**:
```python
result = await detect_entity_type_async(task, client, allow_structure_inspection=True)

if result.entity_type == EntityType.UNKNOWN:
    logger.warning(
        f"Could not detect type for {task.gid}",
        tier_used=result.tier_used,
        strategies_tried=result.strategies_tried,
    )
    # Fallback: prompt user or use default type
```

**Resolution Errors**:
```python
result = await asset_edit.resolve_unit_async(client)

if not result.success:
    if result.ambiguous:
        # Multiple matches - user decides
        selected = await prompt_user_choice(result.candidates)
    elif result.error:
        logger.error(f"Resolution failed: {result.error}")
    else:
        logger.warning("No matching Unit found")
```

**Healing Errors**:
```python
result = await session.commit()

for failure in result.healing_failures:
    if "already in project" in str(failure.error):
        # Idempotent - entity already healed
        continue
    elif "permission denied" in str(failure.error):
        # Escalate to user
        await notify_permission_issue(failure.entity_gid)
    else:
        # Retry with exponential backoff
        await retry_healing(failure)
```

## Migration from Individual ADRs

**Code currently using detection**:
- Update imports if using internal detection functions (package structure change)
- No changes needed for public API (`detect_entity_type()` signature unchanged)
- Consider enabling detection caching via client cache provider
- Review healing opt-in if using SaveSession

**New implementations**:
- Start with async detection for Tier 4 access
- Enable `auto_heal=True` for automatic repair
- Use dry-run mode to preview healing before committing
- Leverage `WorkspaceProjectRegistry` discovery for dynamic projects

**Testing migrations**:
- Update imports to detection package modules
- Mock `CustomFieldAccessor` for field resolution tests
- Use `heal_dry_run=True` in tests to avoid API calls
- Verify tier-specific behavior with isolated tier tests
