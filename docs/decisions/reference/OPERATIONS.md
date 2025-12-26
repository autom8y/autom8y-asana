# ADR Summary: Operations & Workflow

> Consolidated decision record for process pipelines, workflow automation, business logic seeding, and migration/refactoring strategies. Individual ADRs archived.

## Overview

This summary consolidates 15 ADRs that define how the autom8_asana SDK manages operational workflows, business entity creation, process pipeline state machines, and migration strategies.

The process pipeline system represents business workflows (sales, onboarding, implementation) as Asana projects with section-based state progression. Processes move through pipeline stages (Opportunity -> Active -> Scheduled -> Converted) by changing sections within their canonical project. The canonical project serves dual purposes: entity registry (for detection) and workflow view (for state management).

Business entity seeding provides find-or-create factory patterns for creating complete hierarchies (Business > Unit > ProcessHolder > Process) from external triggers like webhooks. The automation layer uses event hooks and rule protocols to execute business logic after persistence operations complete.

Migration and refactoring strategies emphasize clean transitions with backward compatibility. Deprecation warnings guide users to updated APIs while maintaining functionality during transition periods. Big-bang migrations with interface evolution patterns enable rapid modernization without dual-codepath maintenance burden.

## Key Decisions

### 1. Process Pipeline: Canonical Project Architecture
**Context**: Initial design assumed separate "pipeline projects" distinct from entity registry projects. This was incorrect - the canonical project IS the pipeline.

**Decision**: Remove ProcessProjectRegistry entirely. Process entities become members of their canonical project (e.g., "Sales") through normal creation flow. Sections within that project represent pipeline states. Derive ProcessType from canonical project name matching. (ADR-0101)

**Rationale**: Eliminates ~1,000 lines of unnecessary registry code, configuration burden, and conceptual complexity. Matches actual Asana workspace structure where "Sales" project contains both entity membership and pipeline sections.

**Source ADRs**: ADR-0101, ADR-0096 (ProcessType expansion), ADR-0102 (pipeline hooks)

### 2. State Machine: ProcessSection Enum with from_name() Matching
**Context**: Pipeline processes move through stages represented as Asana sections. Section names may vary between projects or be decorated by users.

**Decision**: Represent pipeline states via ProcessSection enum (OPPORTUNITY, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT, DELAYED, OTHER). Provide from_name() classmethod for case-insensitive matching with alias support. Do NOT enforce state transition rules in SDK - consumers implement business logic. (ADR-0097)

**Rationale**: Section membership is the canonical representation in Asana board view. from_name() normalization handles decorated names gracefully. State transition enforcement belongs in consumers, not the SDK data layer. OTHER fallback handles custom sections.

**Source ADRs**: ADR-0097

### 3. Process Types: Expansion and Detection Strategy
**Context**: Current ProcessType enum contains only GENERIC placeholder. Stakeholders require 6 specific pipeline types: SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION.

**Decision**: Expand ProcessType enum with 6 stakeholder-aligned values plus GENERIC fallback. Detect ProcessType by deriving from canonical project name (simple string matching: "sales" in project_name -> ProcessType.SALES). GENERIC fallback for processes not in recognized projects. (ADR-0096)

**Rationale**: Project name matching is O(1), deterministic, and requires no configuration. Matches actual Asana workspace naming conventions. GENERIC preserves backward compatibility.

**Source ADRs**: ADR-0096 (partially superseded by ADR-0101 for detection mechanism)

### 4. Project Type Registry: Singleton Pattern
**Context**: Entity type detection requires deterministic O(1) lookup from project GID to EntityType. Legacy autom8 system uses project membership as source of truth.

**Decision**: Implement module-level singleton registry (ProjectTypeRegistry) using __new__ singleton pattern, populated at import-time via __init_subclass__ hooks on BusinessEntity subclasses. Environment variables (ASANA_PROJECT_{ENTITY_TYPE}) override class attribute PRIMARY_PROJECT_GID. (ADR-0093)

**Rationale**: O(1) dict lookup meets NFR-PERF-001 (<1ms detection). Import-time population is simple and predictable. Singleton provides reset() for test isolation. Environment override enables different project GIDs per environment without code changes.

**Source ADRs**: ADR-0093

### 5. ProcessHolder Detection: No Dedicated Project
**Context**: ProcessHolder is a container task grouping Process entities under Unit. Question: should it have a dedicated Asana project for Tier 1 detection?

**Decision**: ProcessHolder SHALL NOT have a dedicated project (PRIMARY_PROJECT_GID = None). Detection relies on Tier 2 name pattern ("processes") and Tier 3 parent inference from Unit. (ADR-0135)

**Rationale**: ProcessHolder is purely structural with no custom fields or business data. Team does not manage ProcessHolders in project views - they are navigation containers. Consistent with LocationHolder and UnitHolder (both None). Tier 3 inference from Unit parent is highly reliable.

**Source ADRs**: ADR-0135

### 6. Process Field Architecture: Composition Over Inheritance
**Context**: Process entity has 8 generic fields, but actual Asana projects contain 67+ fields (Sales), 41+ fields (Onboarding), 35+ fields (Implementation). Should we use inheritance (SalesProcess, OnboardingProcess) or composition?

**Decision**: Use COMPOSITION with field groups. All pipeline fields defined on single Process class, organized into logical groups (Common, Sales, Onboarding, Implementation). All fields accessible on any Process instance - accessing non-existent field returns None. (ADR-0136)

**Rationale**: Process type determined by project membership at runtime, not compile time. No polymorphism benefit. Many fields overlap across pipelines. Single Process class avoids casting burden. ADR-0081 descriptors gracefully return None when field doesn't exist on task.

**Source ADRs**: ADR-0136

### 7. Business Seeding: Factory Pattern with Find-or-Create
**Context**: Consumer applications need to create complete business entity hierarchies (Business > Unit > ProcessHolder > Process) from external triggers (webhooks, Calendly bookings). Manually navigating hierarchy and handling find-or-create is error-prone.

**Decision**: Create BusinessSeeder factory class with seed_async() method. Implements find-or-create pattern for Business (by company_id/name), Unit (by name under Business), ProcessHolder (always "Processes" under Unit). Always creates new Process for each seed call. Returns SeederResult with all entities and creation flags. (ADR-0099)

**Rationale**: Idempotency critical for webhook retries. Factory encapsulates multi-step creation and dual membership setup. Each seed call represents new business event, so Process always created. Pydantic input models provide validation.

**Source ADRs**: ADR-0099, ADR-0101 (simplified by removing pipeline-specific logic)

### 8. Field Seeding: Dedicated FieldSeeder Service
**Context**: Pipeline conversion creates new Process entities requiring field population from multiple sources: cascade from Business/Unit, carry-through from source Process, computed values.

**Decision**: Create dedicated FieldSeeder service with methods for cascade_from_hierarchy_async(), carry_through_from_process_async(), and compute_fields_async(). Field precedence: Business cascade (lowest) -> Unit cascade -> Process carry-through -> Computed (highest). (ADR-0105)

**Rationale**: Single responsibility - FieldSeeder only computes values, doesn't create entities. Testable independently. Reusable across automation rules. Field sources (cascade vs carry-through vs computed) are explicit.

**Source ADRs**: ADR-0105

### 9. Post-Commit Hooks: EventSystem Extension
**Context**: Automation Layer requires mechanism to evaluate rules and execute actions after SaveSession commits complete. SDK has entity-level hooks but lacks session-level post-commit hook.

**Decision**: Extend EventSystem with on_post_commit hook type, consistent with existing on_pre_save/on_post_save/on_error patterns. AutomationEngine integrates as built-in consumer. Post-commit hooks receive full SaveResult. (ADR-0102)

**Rationale**: Consistency with existing hook patterns. Extensibility - consumers can register custom post-commit handlers. Separation - automation becomes one of potentially many post-commit handlers. Automation failures do not fail primary commit.

**Source ADRs**: ADR-0102

### 10. Automation Rules: Runtime-Checkable Protocol
**Context**: Automation Layer needs mechanism for defining and executing rules. Rules must be declarative, extensible, type-safe, and async-first.

**Decision**: Define AutomationRule as @runtime_checkable Protocol with required attributes (id, name, trigger) and methods (should_trigger, execute_async). TriggerCondition dataclass specifies declarative matching (entity_type, event, filters). (ADR-0103)

**Rationale**: Structural subtyping allows flexibility - any class matching protocol works without inheritance. Easy to create mock rules for testing. Static analysis catches missing methods. Rules can inherit from anything (dataclass, Pydantic, etc.).

**Source ADRs**: ADR-0103

### 11. Deprecation Strategy: warnings.warn() with DeprecationWarning
**Context**: Compatibility layer (_compat.py) provides legacy import paths during migration. Need to warn users these imports are deprecated, guide to canonical paths, allow filtering/promotion in CI.

**Decision**: Use warnings.warn() with DeprecationWarning category and lazy __getattr__ imports. Stacklevel=3 points to user's import statement. Warning message includes canonical import path and removal version (1.0.0). (ADR-0011)

**Rationale**: Standard Python mechanism developers recognize. Filterable - teams can configure warning behavior or fail CI on deprecation warnings. pytest shows DeprecationWarning by default in tests. Lazy imports prevent spam - only warns when deprecated names accessed.

**Source ADRs**: ADR-0011

### 12. Cache Migration: Big-Bang Cutover Strategy
**Context**: Legacy autom8 uses S3-backed caching. New intelligent caching uses Redis exclusively. Must transition from S3 to Redis.

**Decision**: Perform big-bang cutover from S3 to Redis with no data migration. Accept 100% cache miss rate at deployment, relying on cache warming to rebuild. No dual-read fallback. Deployment timeline: T+15min for initial warm-up, T+1hr to reach 80% hit rate. (ADR-0025)

**Rationale**: Dual-read introduces complexity (read from S3, check Redis, merge results), tech debt (S3 code remains), and consistency issues. Cache data rebuilds quickly from API. Migration tooling has marginal benefit. Big-bang enables clean cutover in days vs weeks.

**Source ADRs**: ADR-0025

### 13. Dataframe Migration: Interface Evolution Strategy
**Context**: Legacy struc() method (~1,000 lines) transforms Asana task hierarchies to pandas DataFrames. New to_dataframe() API uses schema-based extraction with polars. Must migrate without breaking consumers.

**Decision**: Implement big-bang migration with Interface Evolution. Replace struc() internals with to_dataframe() in single release. Maintain struc() as deprecated wrapper that calls to_dataframe().to_pandas(). Minimum 2 minor version deprecation period before removal in v2.0. (ADR-0027, Completed in v2.0.0)

**Rationale**: Clean cutover - no dual codepath maintenance. Backward compatibility via wrapper. Polars performance benefits (10-100x faster). struc() wrapper provides pandas conversion for legacy consumers. All internal SDK code migrated to to_dataframe() in same release.

**Implementation Note**: Completed in v2.0.0. All struc() references removed. Cache infrastructure renamed (EntryType.STRUC -> EntryType.DATAFRAME). warm_struc() kept as alias for backward compatibility.

**Source ADRs**: ADR-0027

### 14. Exception Rename: Deprecation with Metaclass Warning
**Context**: SDK's ValidationError conflicts with pydantic.ValidationError, causing import shadowing issues. Exception validates GID format specifically, not general validation.

**Decision**: Rename ValidationError to GidValidationError. Provide backward-compatible alias using metaclass that emits DeprecationWarning on class access. Warning fires on except clauses, isinstance checks, and attribute access - not just instantiation. (ADR-0084)

**Rationale**: Eliminates import conflicts with Pydantic. Semantic clarity - name describes purpose. Metaclass approach warns on any usage, not just instantiation. Maintains inheritance - except GidValidationError catches both old and new.

**Source ADRs**: ADR-0084 (originally ADR-HARDENING-A-001)

### 15. Hours Model Compatibility: Deprecated Aliases with Type Changes
**Context**: Hours model requires fundamental changes: field name changes (Monday Hours -> Monday), type changes (text -> multi_enum returns list[str] instead of str), field removal (timezone, hours_notes, sunday_hours don't exist in Asana).

**Decision**: Deprecated aliases with clean break on types. Primary properties use new names (monday, tuesday, etc.) with correct return types (list[str]). Old names (monday_hours, etc.) emit DeprecationWarning and delegate to new properties but return new types (breaking for consumers expecting str). Remove stale fields entirely - no aliases. (ADR-0114)

**Rationale**: Consumer discovery via deprecation warnings. Type safety prevents silent data loss. Returning correct types is unavoidable given Asana reality. Clean future - single code path. Stale fields are breaking regardless - no compatibility possible for fields that don't exist.

**Source ADRs**: ADR-0114

## Design Patterns

### Pipeline Architecture Pattern
- Canonical project serves dual purpose: entity registry + workflow view
- Sections within project represent state machine states
- Project membership determines both EntityType and ProcessType
- No separate "pipeline projects" - simplifies detection and configuration

### Find-or-Create Factory Pattern
- BusinessSeeder finds existing entities by key (company_id, name)
- Creates only when not found, ensuring idempotency
- Returns result with creation flags for consumer logic
- Suitable for webhook handlers that may retry

### Field Computation Layering
- Cascade from hierarchy (Business -> Unit fields flow down)
- Carry-through from source entity (Process fields copied)
- Computed values derived at runtime (timestamps, calculated fields)
- Clear precedence order prevents ambiguity

### Migration Strategies
- **Big-bang with Interface Evolution**: Replace internals, maintain wrapper
- **Deprecation warnings**: Standard Python DeprecationWarning category
- **Timeline clarity**: Removal version explicit in warning messages
- **Lazy evaluation**: Warnings only when deprecated names accessed
- **Clean breaks accepted**: Type changes unavoidable when matching reality

### Event Hook Extension Pattern
- Extend existing EventSystem with new hook types
- Consistency with pre_save/post_save/error patterns
- Consumers can register multiple handlers
- Handlers execute in registration order with no dependency

### Protocol-Based Extensibility
- Runtime-checkable protocols for structural subtyping
- No inheritance required - duck typing with type safety
- Easy to mock for testing
- Compose with dataclasses, Pydantic models, etc.

## Cross-References

**Related PRDs:**
- PRD-PROCESS-PIPELINE (superseded by ADR-0101 correction)
- PRD-AUTOMATION-LAYER (hooks and rules)
- PRD-TECH-DEBT-REMEDIATION (detection strategies, field architecture)
- PRD-0002-intelligent-caching (migration strategy)
- PRD-0003-structured-dataframe-layer (migration strategy)

**Related TDDs:**
- TDD-PROCESS-PIPELINE (superseded by ADR-0101 correction)
- TDD-AUTOMATION-LAYER (field seeding, rule execution)
- TDD-TECH-DEBT-REMEDIATION (ProcessHolder detection, Process fields)
- TDD-0008-intelligent-caching (cache cutover)
- TDD-0006-backward-compatibility (deprecation patterns)

**Related Summaries:**
- ADR-SUMMARY-DETECTION (ProjectTypeRegistry, detection tiers)
- ADR-SUMMARY-PERSISTENCE (SaveSession, event hooks)
- ADR-SUMMARY-BUSINESS-ENTITIES (entity hierarchy, custom fields)

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0093 | Project-to-EntityType Registry Pattern | 2025-12-17 | Module-level singleton registry with __init_subclass__ population |
| ADR-0096 | ProcessType Expansion and Detection | 2025-12-17 | 6 stakeholder-aligned ProcessType values + GENERIC fallback |
| ADR-0097 | ProcessSection State Machine Pattern | 2025-12-17 | ProcessSection enum with from_name() matching, no transition enforcement |
| ADR-0099 | BusinessSeeder Factory Pattern | 2025-12-17 | Find-or-create factory for Business/Unit/ProcessHolder/Process hierarchy |
| ADR-0101 | Process Pipeline Architecture Correction | 2025-12-17 | Remove ProcessProjectRegistry - canonical project IS the pipeline |
| ADR-0102 | Post-Commit Hook Architecture | 2025-12-17 | EventSystem on_post_commit hook for automation integration |
| ADR-0103 | Automation Rule Protocol | 2025-12-17 | Runtime-checkable Protocol for rule extensibility |
| ADR-0105 | Field Seeding Architecture | 2025-12-17 | Dedicated FieldSeeder service for cascade/carry-through/computed |
| ADR-0135 | ProcessHolder Detection Strategy | 2025-12-19 | ProcessHolder has no dedicated project - Tier 2/3 detection |
| ADR-0136 | Process Field Accessor Architecture | 2025-12-19 | Composition with field groups, not inheritance - single Process class |
| ADR-0011 | Deprecation Warning Strategy | 2025-12-08 | warnings.warn() with DeprecationWarning, lazy __getattr__ |
| ADR-0025 | Big-Bang Migration Strategy | 2025-12-09 | S3 to Redis cutover with no data migration, accept cache miss spike |
| ADR-0027 | Dataframe Layer Migration Strategy | 2025-12-09 | Interface Evolution: struc() wrapper calls to_dataframe() |
| ADR-0084 | Exception Rename Strategy | 2025-12-16 | ValidationError -> GidValidationError with metaclass deprecation |
| ADR-0114 | Hours Model Backward Compatibility | 2025-12-18 | Deprecated aliases with type changes, remove stale fields |

## Implementation Guidance

### When building process pipelines:
1. Use ProjectTypeRegistry for EntityType.PROCESS detection via project membership
2. Derive ProcessType from canonical project name matching (no separate registry)
3. Extract pipeline_state from section membership in canonical project
4. Use ProcessSection.from_name() for robust section name matching
5. No state transition validation in SDK - implement in consumer logic

### When creating business entities:
1. Use BusinessSeeder.seed_async() for webhook-triggered creation
2. Rely on find-or-create idempotency for safe retries
3. Use FieldSeeder for field computation when creating converted Processes
4. Check SeederResult.created_* flags for business logic branching

### When adding automation:
1. Register post-commit hooks via EventSystem.register_post_commit()
2. Define rules as classes implementing AutomationRule Protocol
3. Use TriggerCondition for declarative event matching
4. Automation failures must not fail primary SaveSession commit

### When deprecating APIs:
1. Use warnings.warn() with DeprecationWarning category
2. Provide stacklevel to point at user code, not SDK internals
3. Include removal version and migration guidance in warning message
4. Consider lazy __getattr__ to warn only on actual usage
5. Maintain minimum 2 minor version deprecation period

### When migrating systems:
1. Default to big-bang with interface evolution over dual-codepath maintenance
2. Accept temporary performance impact for cleaner architecture
3. Provide explicit wrapper/alias for backward compatibility during transition
4. Document migration path clearly with code examples
5. Use staging environment for warm-up validation before production

## Lessons Learned

**Architecture correction is cheaper than perpetuating wrong abstractions**: ADR-0101 removed ~1,000 lines of ProcessProjectRegistry code when we realized canonical projects serve dual purpose. Early course correction prevented compounding complexity.

**Detect from reality, not configuration**: Deriving ProcessType from project name matching eliminated configuration burden. When Asana structure provides signal, use it directly.

**Idempotency enables retry safety**: BusinessSeeder find-or-create pattern makes webhook handlers safe to retry. Critical for production reliability.

**Deprecation warnings are migration documentation**: Well-crafted warnings guide users to correct usage without blocking their current code. Lazy evaluation prevents warning spam.

**Big-bang migrations reduce maintenance burden**: Dual-codepath maintenance extends migration timeline from days to months and introduces drift risk. Accept short-term pain for long-term simplicity.

**Type safety over false compatibility**: Hours model returning correct types (list[str]) despite breaking old expectations is better than perpetuating incorrect types (str) that lose data.

**Protocols enable extensibility without coupling**: AutomationRule Protocol allows consumers to implement rules as dataclasses, Pydantic models, or plain classes without SDK coupling.

**State machines belong in consumers, not SDK**: ProcessSection enum provides type safety for states, but transition validation is business logic that varies by workflow and belongs in consumer applications.
