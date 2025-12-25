# Orchestrator Initialization: Membership-Based Model Detection System

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources, async-first, batch operations
  - Activates when: Working with detection, models, SaveSession integration

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** - Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

**How Skills Work**: Skills load automatically based on your current task. When you need template formats, the `documentation` skill activates. When you need SDK-specific patterns, the `autom8-asana-domain` skill activates.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

## The Mission: Replace broken name-based entity detection with deterministic project-membership detection

The current detection system uses name-based heuristics that fail completely because Asana task names are decorated (e.g., `"Duong Chiropractic Inc - Chiropractic Offers [emoji]"` vs expected `"offers"`). The actual Asana data model uses project membership as the canonical type indicator. This initiative replaces the broken detection with a tiered detection chain anchored by project-membership lookup, enabling reliable model instantiation across the entire business entity hierarchy.

### Why This Initiative?

- **Correctness**: Current system achieves ~0% accuracy; project membership achieves 100%
- **Performance**: O(1) lookup with zero API calls vs O(n) structure inspection
- **Completeness**: Works for all entity types including leaf entities (Offer, Contact)
- **Self-Healing**: Enables automatic project membership correction via SaveSession

### Current State

**Detection System (Broken)**:
- Name-based heuristics in `detection.py` expect literal matches like `"contacts"`, `"offers"`
- Actual Asana names are decorated: `"Business Name - Category Offers [emoji]"`
- Structure inspection fallback requires API calls and still fails for leaf entities
- Returns `EntityType.UNKNOWN` for essentially all real-world entities

**Existing Foundation**:
- `BusinessEntity` base class with `PRIMARY_PROJECT_GID: ClassVar[str | None] = None` (stubbed)
- `EntityType` enum with all business entity types defined
- `SaveSession` with action operations (`add_to_project`, `remove_from_project`)
- `HolderMixin` pattern for holder-child relationships
- Legacy autom8 system with working project-based detection (reference implementation)

**What's Missing**:

```python
# This is what we need to enable:

entity_type = detect_entity_type(task)  # O(1), 0 API calls, 100% accurate
business = Business.from_task(task)     # Type-safe instantiation

# With self-healing:
async with SaveSession(client, auto_heal=True) as session:
    session.track(misplaced_offer)
    await session.commit_async()  # Automatically adds to correct project
```

### Detection System Profile

| Attribute | Value |
|-----------|-------|
| Primary Language | Python 3.10+ |
| Framework | Pydantic v2, async-first |
| Location | `src/autom8_asana/models/business/detection.py` |
| Integration Points | BusinessEntity instantiation, SaveSession healing |
| Configuration Style | ClassVar + environment override |
| Performance Target | <1ms detection, 0 API calls (Tier 1) |

### Target Architecture

```
Detection Request (task with memberships)
         |
         v
+-------------------+
|   Tier 1: Project |  O(1), 0 API, 100% accuracy
|   Membership      |---> EntityType.OFFER (if match)
+-------------------+
         | (no match)
         v
+-------------------+
|   Tier 2: Name    |  O(1), 0 API, ~60% accuracy
|   Convention      |---> EntityType.CONTACT_HOLDER (if pattern match)
+-------------------+
         | (no match)
         v
+-------------------+
|   Tier 3: Parent  |  O(1), 0 API, ~80% accuracy
|   Inference       |---> EntityType.LOCATION (if parent is LocationHolder)
+-------------------+
         | (no match)
         v
+-------------------+
|   Tier 4: Struct  |  O(n), 1+ API, ~90% accuracy
|   Inspection      |---> EntityType.BUSINESS (if has expected subtasks)
+-------------------+
         | (no match)
         v
+-------------------+
|   Tier 5: Unknown |  Flag for self-healing
|   + Healing Flag  |---> EntityType.UNKNOWN, needs_healing=True
+-------------------+
```

### Key Constraints

- **Public SDK**: Patterns must be generalizable, not hardcoded to one workspace
- **Multi-Workspace**: Different Asana workspaces have different project GIDs
- **Performance-Sensitive**: Detection happens on every model instantiation
- **Backward Compatible**: Must work with existing SaveSession patterns
- **Async-First**: SDK is async-first; sync wrappers where needed
- **No Surprise API Calls**: Detection Tier 1-3 must be zero-API

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Project-to-EntityType registry with O(1) lookup | Must |
| Registry population from model ClassVars via `__init_subclass__` | Must |
| Environment variable override for multi-workspace | Must |
| Tiered fallback chain (project -> name -> parent -> structure) | Must |
| Confidence scoring for detection results | Must |
| Self-healing flag on UNKNOWN detection | Must |
| SaveSession `auto_heal` integration | Must |
| Batched healing operations in commit phase | Should |
| Healing operation logging and metrics | Should |
| LocationHolder parent-based detection (no project) | Must |
| Deprecation warnings for direct name-based detection | Should |
| Detection result caching (per-request) | Nice |

### Success Criteria

1. Detection accuracy 100% for all entity types with project membership
2. Detection accuracy >95% for LocationHolder (parent-based fallback)
3. Zero API calls for Tier 1-3 detection paths
4. Detection latency <1ms for Tier 1 (project lookup)
5. Self-healing success rate >90% for misplaced entities
6. All existing tests pass (backward compatibility)
7. Type coverage: all 12+ EntityType values have detection path
8. Multi-workspace support via environment configuration

### Performance Targets

| Metric | Development | Production |
|--------|-------------|------------|
| Tier 1 Detection Latency | <1ms | <1ms |
| Tier 2 Detection Latency | <1ms | <1ms |
| Tier 3 Detection Latency | <1ms | <1ms |
| Tier 4 Detection Latency | <100ms | <50ms (cached) |
| Registry Initialization | <10ms | <10ms |
| Self-Healing Batch Size | 10 (Asana limit) | 10 |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Codebase analysis, project GID collection, legacy pattern extraction |
| **2: Requirements** | Requirements Analyst | PRD-DETECTION with acceptance criteria per tier |
| **3: Architecture** | Architect | TDD-DETECTION + ADR-0084 (Registry), ADR-0085 (Fallback Chain), ADR-0086 (Self-Healing) |
| **4: Implementation P1** | Principal Engineer | Registry pattern, project membership detection (Tier 1) |
| **5: Implementation P2** | Principal Engineer | Fallback chain (Tiers 2-4), confidence scoring |
| **6: Implementation P3** | Principal Engineer | Self-healing integration with SaveSession |
| **7: Validation** | QA/Adversary | Detection accuracy testing, edge case validation, performance verification |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/models/business/detection.py` | Current algorithm, EntityType enum, what's broken |
| `src/autom8_asana/models/business/base.py` | PRIMARY_PROJECT_GID ClassVar, `__init_subclass__` hooks |
| `src/autom8_asana/models/business/*.py` | All model definitions, which have stubbed GIDs |
| `src/autom8_asana/persistence/session.py` | SaveSession action operations, healing integration points |
| `docs/analysis/DETECTION-SYSTEM-ANALYSIS.md` | Architect's analysis, project GID mappings |

### Legacy System Audit

| Resource/System | Questions to Answer |
|-----------------|---------------------|
| autom8 TaskData singleton | How does legacy detection work? What's the boy scout pattern? |
| autom8 model `__post_init__` | How is membership enforced on instantiation? |
| autom8 project constants | Complete list of project GIDs per entity type |
| autom8 caching patterns | How is project metadata cached? TTL strategy? |

### Configuration Gap Analysis

| Area | Questions |
|------|-----------|
| Project GIDs | Which entity types are missing project GID mappings? |
| Environment Config | What's the env var naming convention for SDK? |
| Multi-Workspace | How do consumers specify workspace-specific GIDs? |
| Defaults | What happens if no GID is configured for an entity type? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Detection Strategy Questions

1. **First membership vs explicit primary**: When a task has multiple project memberships, how do we determine the canonical type?
2. **Registry population timing**: Should registry build at import time, first access, or client initialization?
3. **Fallback chain termination**: Should Tier 4 (structure inspection) be optional/configurable?
4. **Confidence exposure**: Should detection return confidence scores to consumers or keep internal?

### Self-Healing Questions

5. **Healing trigger**: What detection result triggers healing flag? UNKNOWN only, or also low-confidence?
6. **Healing scope**: Should healing add missing membership, remove incorrect ones, or both?
7. **Healing opt-in**: Is `SaveSession(auto_heal=True)` the right API, or per-entity flag?
8. **Healing failures**: How should failed healing operations be reported/retried?

### Configuration Questions

9. **Environment variable prefix**: `ASANA_PROJECT_*` or `AUTOM8_ASANA_PROJECT_*`?
10. **Missing GID behavior**: Raise error, log warning, or silently skip Tier 1?
11. **Workspace isolation**: How do multi-workspace consumers configure per-workspace GIDs?

## Your First Task

Confirm understanding by:

1. Summarizing the detection system goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-DETECTION
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Detection System Discovery

Work with the @requirements-analyst agent to analyze the current detection system and audit legacy patterns.

**Goals:**
1. Map current detection algorithm and failure modes
2. Collect complete project GID mappings for all entity types
3. Document legacy autom8 detection and healing patterns
4. Identify all BusinessEntity subclasses and their PRIMARY_PROJECT_GID status
5. Understand LocationHolder special case (no project membership)
6. Document SaveSession action operations available for healing
7. Identify configuration patterns for multi-workspace support

**Files to Analyze:**
- `src/autom8_asana/models/business/detection.py` - Current broken detection
- `src/autom8_asana/models/business/base.py` - ClassVar patterns
- `src/autom8_asana/models/business/*.py` - All model definitions
- `src/autom8_asana/persistence/session.py` - Healing integration points
- `docs/analysis/DETECTION-SYSTEM-ANALYSIS.md` - Prior analysis

**Legacy System to Audit:**
- autom8 detection patterns
- autom8 project GID configuration
- autom8 membership enforcement (`__post_init__`)
- autom8 caching strategies

**Deliverable:**
A discovery document with:
- Complete project GID mapping table
- Current vs required detection capabilities matrix
- Legacy pattern documentation
- Configuration strategy recommendation
- Open questions resolved or escalated
- Risk register for edge cases

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Detection System Requirements Definition

Work with the @requirements-analyst agent to create PRD-DETECTION.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define registry requirements (population, lookup, override)
2. Define detection tier requirements (1-5)
3. Define confidence scoring requirements
4. Define self-healing requirements (trigger, scope, API)
5. Define configuration requirements (ClassVar, env, multi-workspace)
6. Define backward compatibility requirements
7. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What's the complete project GID -> EntityType mapping?
- How should LocationHolder be detected without project membership?
- What's the self-healing integration API with SaveSession?
- How do consumers configure multi-workspace project GIDs?

**PRD Organization:**
- FR-REG-*: Registry requirements (population, lookup, validation)
- FR-DET-*: Detection requirements (tiers 1-5, confidence)
- FR-HEAL-*: Self-healing requirements (trigger, execution, reporting)
- FR-CFG-*: Configuration requirements (ClassVar, env, multi-workspace)
- FR-COMPAT-*: Backward compatibility requirements
- NFR-*: Performance, reliability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Detection System Architecture Design

Work with the @architect agent to create TDD-DETECTION and foundational ADRs.

**Prerequisites:**
- PRD-DETECTION approved

**Goals:**
1. Design registry pattern with `__init_subclass__` population
2. Design tiered detection chain with Chain of Responsibility pattern
3. Design confidence scoring mechanism
4. Design self-healing integration with SaveSession
5. Design configuration override hierarchy
6. Define module/class structure
7. Document trade-off decisions in ADRs

**Required ADRs:**
- ADR-0084: Project-to-EntityType Registry Pattern
- ADR-0085: Detection Fallback Chain Design
- ADR-0086: Self-Healing Integration with SaveSession
- ADR-0087: Multi-Workspace Configuration Strategy

**Module Structure to Consider:**

```
src/autom8_asana/models/business/
  +-- detection.py          # EntityType enum, detect functions
  +-- registry.py           # NEW: ProjectTypeRegistry
  +-- base.py               # PRIMARY_PROJECT_GID ClassVar (existing)
  +-- *.py                  # Model files with GID ClassVars
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Registry Pattern

Work with the @principal-engineer agent to implement the core registry.

**Prerequisites:**
- PRD-DETECTION approved
- TDD-DETECTION approved
- ADRs documented

**Phase 1 Scope:**
1. Create `registry.py` with `ProjectTypeRegistry` class
2. Implement `__init_subclass__` hook to register PRIMARY_PROJECT_GID
3. Implement O(1) project GID -> EntityType lookup
4. Implement environment variable override loading
5. Add registry validation (duplicate detection, missing GIDs)
6. Write unit tests for registry operations

**Hard Constraints:**
- Registry must be importable without side effects
- Environment override must take precedence over ClassVar
- Must support `None` GID (LocationHolder case)
- Must log debug info about registry population

**Explicitly OUT of Phase 1:**
- Detection chain implementation (Phase 2)
- Confidence scoring (Phase 2)
- Self-healing integration (Phase 3)
- SaveSession modifications (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Detection Chain

Work with the @principal-engineer agent to implement the detection tiers.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement `detect_by_project()` - Tier 1 using registry
2. Refactor `detect_by_name()` - Tier 2 with improved patterns
3. Implement `detect_by_parent()` - Tier 3 for LocationHolder
4. Refactor `detect_by_structure()` - Tier 4 async fallback
5. Implement `DetectionResult` with confidence scoring
6. Implement unified `detect_entity_type()` with fallback chain

**Integration Points:**
- Registry lookup for Tier 1
- Parent task access for Tier 3
- Client for Tier 4 API calls
- Deprecation warnings for legacy functions

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Self-Healing Integration

Work with the @principal-engineer agent to implement self-healing.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Add `needs_healing` flag to detection result
2. Implement `HealingOperation` model for membership corrections
3. Add `auto_heal` parameter to SaveSession
4. Implement healing operation collection during commit
5. Execute healing as batched `add_to_project` operations
6. Add healing result reporting to `SaveResult`
7. Write integration tests for healing workflow

**Self-Healing Workflow:**

```
Detection (Tier 5: UNKNOWN)
         |
         v
   needs_healing = True
         |
         v (SaveSession.commit with auto_heal=True)
         |
   Collect HealingOperations
         |
   Execute as batched add_to_project
         |
   Report in SaveResult.healing_results
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Detection System Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete
- Detection system integrated

**Goals:**

**Part 1: Functional Validation**
- Tier 1 detection for all entity types with project membership
- Tier 2 detection for known name patterns
- Tier 3 detection for LocationHolder (parent-based)
- Tier 4 detection via structure inspection
- Tier 5 UNKNOWN with healing flag

**Part 2: Edge Case Testing**
- Multi-project membership (first wins)
- Missing project membership (fallback chain)
- LocationHolder detection (no project)
- Misconfigured environment variables
- Empty registry scenarios

**Part 3: Performance Validation**
- Tier 1 detection <1ms (benchmark)
- Registry initialization <10ms
- No regression in existing tests

**Part 4: Self-Healing Validation**
- Healing triggers on UNKNOWN detection
- Healing batches correctly in SaveSession
- Healing reports in SaveResult
- Healing failures handled gracefully

**Part 5: Backward Compatibility**
- Existing detection code path still works (deprecated)
- No breaking changes to public API
- Deprecation warnings fire appropriately

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Codebase Context:**

- [ ] `src/autom8_asana/models/business/detection.py` - Current detection
- [ ] `src/autom8_asana/models/business/base.py` - BusinessEntity, ClassVars
- [ ] `src/autom8_asana/persistence/session.py` - SaveSession, action operations
- [ ] `docs/analysis/DETECTION-SYSTEM-ANALYSIS.md` - Prior analysis

**Project GID Mapping:**

- [ ] Business project GID
- [ ] Contact/ContactHolder project GIDs
- [ ] Unit/UnitHolder project GIDs
- [ ] Offer/OfferHolder project GIDs
- [ ] Location/LocationHolder project GIDs (LocationHolder has none)
- [ ] Process/ProcessHolder project GIDs
- [ ] DNA/Reconciliation/AssetEdit/Videography project GIDs

**Legacy System Reference:**

- [ ] autom8 detection implementation
- [ ] autom8 project configuration
- [ ] autom8 `__post_init__` membership enforcement
- [ ] autom8 caching patterns

**Configuration Strategy:**

- [ ] Environment variable naming convention
- [ ] Multi-workspace configuration approach
- [ ] Default behavior for missing GIDs
