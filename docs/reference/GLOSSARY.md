# Unified Glossary

> Comprehensive terminology reference for autom8_asana platform and 10x development workflow

**Last Updated**: 2025-12-24

---

## How to Use This Glossary

This glossary combines:
- **Core SDK concepts** - Asana API wrapper, entities, caching
- **Business domain** - Business entities, holders, hierarchy
- **Workflow process** - Agent roles, phases, artifacts
- **Quality practices** - Principles, anti-patterns, decision frameworks

**Navigation**:
- Terms are organized by domain for easy scanning
- See **Related References** sections for deep-dive documentation
- Use your editor's search to find specific terms quickly

**Cross-References**:
- `REF-*` documents provide detailed explanations of concepts
- Agent definitions in `.claude/agents/` explain specialist roles
- Skills in `.claude/skills/` provide domain-specific guidance

---

## Table of Contents

1. [Core Asana Concepts](#core-asana-concepts)
2. [SDK Architecture](#sdk-architecture)
3. [Business Entities](#business-entities)
4. [Persistence & State](#persistence--state)
5. [Detection System](#detection-system)
6. [Cache Architecture](#cache-architecture)
7. [Automation System](#automation-system)
8. [Pipeline Management](#pipeline-management)
9. [Workflow Phases](#workflow-phases)
10. [Agent Roles](#agent-roles)
11. [Documentation Artifacts](#documentation-artifacts)
12. [Quality Concepts](#quality-concepts)
13. [Communication Patterns](#communication-patterns)
14. [Decision Frameworks](#decision-frameworks)
15. [Anti-Patterns](#anti-patterns)
16. [Workflow Principles](#workflow-principles)
17. [Acronyms](#acronyms)

---

## Core Asana Concepts

### GID (Global ID)
Asana's unique identifier for resources. Format: numeric string (e.g., `"1234567890"`). Temporary GIDs created before server persistence use format `temp_{uuid}`.

**Related**: [REF-entity-lifecycle.md](REF-entity-lifecycle.md)

### Task
The fundamental Asana resource. Can have custom fields, subtasks, dependencies, attachments, and stories. Tasks belong to projects and sections.

### Project
Container for tasks organized by sections. In the business domain, projects represent entity collections (e.g., "Businesses", "Contacts").

**Related**: [REF-asana-hierarchy.md](REF-asana-hierarchy.md)

### Section
Visual grouping within a project. Used for workflow states (BACKLOG, IN_PROGRESS, COMPLETE) in process management.

**Related**: [REF-asana-hierarchy.md](REF-asana-hierarchy.md)

### Custom Field
Typed metadata on tasks. Types: text, number, dropdown, date. Business entities use custom fields for domain properties (e.g., `office_phone`, `vertical`).

**Related**: [REF-custom-field-catalog.md](REF-custom-field-catalog.md)

### Membership
A task's relationship to a project, including its section placement. Tasks can be members of multiple projects (multi-homing).

### Pagination Cursor
Opaque string token for fetching the next page of results from Asana API. SDK handles automatically via AsyncIterator pattern.

### opt_fields
Query parameter requesting specific fields from Asana API. Used to minimize payload size and improve performance.

---

## SDK Architecture

### SaveSession
Unit of Work pattern for deferred batch saves. Tracks entity changes, builds dependency graph, executes operations in optimized order.

**Example**:
```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()
```

**Related**: [REF-savesession-lifecycle.md](REF-savesession-lifecycle.md), [REF-batch-operations.md](REF-batch-operations.md)

### Async-First Design
All SDK interfaces are async by default. Sync wrappers available via `sync_wrapper` decorator for blocking contexts.

**Pattern**: Primary implementation is async; sync is a thin wrapper.

### Protocol
Python structural typing interface. Used for dependency injection and testability. Key protocols: `AuthProtocol`, `CacheProtocol`.

**Example**: `CacheProtocol` defines `get()`, `set()`, `delete()`, `clear()` without mandating implementation.

### Client
Resource-specific API wrapper. Examples: `TaskClient`, `ProjectClient`, `UserClient`. Encapsulates HTTP operations and response parsing.

### Batch Request
Request to Asana's `/batch` endpoint. Limit: 10 actions per request. SDK automatically chunks larger batches.

**Related**: [REF-batch-operations.md](REF-batch-operations.md)

---

## Business Entities

### Business Entity
Typed wrapper around Asana Task with custom field properties as first-class attributes. Seven types: Business, Contact, Unit, Offer, Address, Hours, Process.

**Pattern**: Pydantic models with custom field accessors.

**Related**: [REF-entity-type-table.md](REF-entity-type-table.md), [REF-entity-lifecycle.md](REF-entity-lifecycle.md)

### Holder
Special task that groups related child entities. Types: ContactHolder, UnitHolder, LocationHolder, OfferHolder, ProcessHolder.

**Purpose**: Provides consistent navigation structure (e.g., `business.contacts.children` accesses ContactHolder's subtasks).

**Key**: Each holder type uses naming convention (`📇 Contacts`, `🏢 Units`) for detection.

### HOLDER_KEY_MAP
Class attribute mapping holder property names to (name_pattern, emoji) tuples. Enables programmatic holder creation and detection.

**Example**: `{"contacts": ("Contacts", "📇")}`

### Composite Entity
Entity that is both a child and a parent. Unit is composite: child of UnitHolder under Business, parent of OfferHolder and ProcessHolder.

**Pattern**: Units navigate both up (to Business) and down (to Offers/Processes).

### Sibling Relationship
Address and Hours are siblings under LocationHolder. Cross-reference via `address.hours` and `hours.address` properties.

**Related**: [REF-asana-hierarchy.md](REF-asana-hierarchy.md)

---

## Persistence & State

### ChangeTracker
Component that snapshots entity state on `track()`, then compares at `commit()` to detect dirty entities.

**Pattern**: Immutable snapshot → compare → emit changes.

### DependencyGraph
Orders SaveSession operations topologically. Parents save before children to ensure valid foreign keys. Implementation: Kahn's algorithm.

**Related**: [REF-savesession-lifecycle.md](REF-savesession-lifecycle.md)

### EntityState
Lifecycle state enum:
- `NEW`: Temp GID, will POST to create
- `CLEAN`: Tracked but unmodified
- `MODIFIED`: Pending changes, will PATCH
- `DELETED`: Marked for deletion, will DELETE

**Related**: [REF-entity-lifecycle.md](REF-entity-lifecycle.md)

### ActionOperation
Operation using Asana's action endpoints (not CRUD). Types: `ADD_TAG`, `REMOVE_TAG`, `ADD_TO_PROJECT`, `MOVE_TO_SECTION`, `ADD_DEPENDENCY`, `SET_PARENT`.

**Pattern**: Actions are atomic, idempotent operations that bypass full resource updates.

### SaveResult
Result object from `commit()`. Fields: `success` (bool), `succeeded` (list), `failed` (list), `gid_map` (dict mapping temp GIDs to real GIDs).

**Usage**: Consumers use `gid_map` to update references after commit.

### Cascading Field
Value propagated from parent to descendants. Stored redundantly for O(1) read access. Example: `office_phone` cascades from Business to all descendants.

**Flag**: `allow_override` (True = skip non-null descendants, False = always overwrite).

**Related**: [REF-entity-lifecycle.md](REF-entity-lifecycle.md)

### Inherited Field
Resolved from parent chain at read time. Not stored on child entity. Example: `vertical` on Offer is inherited from parent Unit's Business.

**Pattern**: Walk parent chain until field is found or root is reached.

---

## Detection System

### Detection Tier
Method for identifying entity type from an Asana task. Five tiers, ordered by performance:

1. **Project membership** (O(1) via ProjectTypeRegistry)
2. **Name pattern** (regex matching on task name)
3. **Parent inference** (type derived from parent entity)
4. **Structure inspection** (check custom fields, subtasks)
5. **Unknown** (detection failed)

**Related**: [REF-detection-tiers.md](REF-detection-tiers.md)

### ProjectTypeRegistry
Singleton mapping project GIDs to EntityTypes. Enables O(1) Tier 1 lookups. Populated from configuration or discovered dynamically.

**Pattern**: Pre-warm registry at startup for known projects.

### DetectionResult
Result object from entity detection. Fields:
- `entity_type`: Detected type (or UNKNOWN)
- `confidence`: Float 0.0-1.0
- `tier_used`: Which tier succeeded
- `needs_healing`: Bool, True if lower tier succeeded but Tier 1 would fail
- `expected_project_gid`: Where entity should be registered

**Related**: [REF-detection-tiers.md](REF-detection-tiers.md)

### Self-Healing
Auto-registration of entities when lower tiers succeed but Tier 1 would fail. Updates ProjectTypeRegistry to enable future O(1) lookups.

**Principle**: System learns from inference and improves performance over time.

---

## Cache Architecture

### CacheProtocol
Interface for cache backends. Methods: `get()`, `set()`, `delete()`, `clear()`. Implementations: InMemoryCache, RedisCache, DiskCache.

**Pattern**: Protocol-based design enables swappable backends and testing with mocks.

**Related**: [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md)

### EntryType
Enum defining cache entry categories. 15 types including: TASK, SUBTASKS, DEPENDENCIES, DATAFRAME, PROJECT, DETECTION, GID_ENUMERATION.

**Location**: `cache/entry.py`

**Purpose**: Enables targeted invalidation by entry type.

### CacheEntry
Dataclass representing cached data. Fields:
- `key`: Cache key (string)
- `data`: Cached payload (Any)
- `entry_type`: EntryType enum
- `version`: Data version for staleness detection
- `cached_at`: Timestamp (float)
- `ttl`: Time-to-live in seconds (int)

**Methods**: `is_expired()`, `is_current(version)`

**Related**: [REF-cache-architecture.md](REF-cache-architecture.md)

### TTL (Time-To-Live)
Seconds until cache entry expires. Entity-specific values in `config.py:DEFAULT_ENTITY_TTLS`.

**Range**: 60s (Process) to 3600s (Business)

**Principle**: Cache stability correlates with update frequency.

**Related**: [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md)

### Staleness Detection
Lightweight mechanism to detect when cached data is outdated. Uses progressive TTL and version comparison.

**Pattern**: Check `is_expired()` → Check `is_current(version)` → Evict if stale.

**Related**: [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md)

### TaskCacheCoordinator
Encapsulates task-level cache operations for DataFrame builds. Methods: `lookup_tasks_async()`, `populate_tasks_async()`, `merge_results()`.

**Location**: `dataframes/builders/task_cache.py`

**Pattern**: Two-phase cache strategy (enumerate → lookup → fetch misses → populate → merge).

### GID Enumeration
Lightweight fetch of task GIDs only (not full task data). Cached separately via `GID_ENUMERATION` entry type.

**Key Learning**: Caching GID enumeration enabled 187x speedup for warm fetches.

**Related**: [REF-cache-patterns.md](REF-cache-patterns.md)

### Two-Phase Cache Strategy
Pattern for cache-aware fetching:
1. Enumerate GIDs (lightweight, ~0.5s)
2. Batch cache lookup for enumerated GIDs
3. Fetch only cache misses from API
4. Batch cache populate with fetched data
5. Merge cached + fetched results

**Performance**: Warm fetch: 0.11s (187x faster than cold 20.6s fetch).

**Related**: [REF-cache-patterns.md](REF-cache-patterns.md)

### Graceful Degradation
Cache failure handling pattern. Cache failures log WARNING and return empty result; primary operation continues.

**Principle**: Never block or fail operations due to cache unavailability. Cache is performance optimization, not dependency.

### Cache Invalidation
Removing stale entries after mutations. SaveSession invalidates all relevant entry types for modified GIDs on commit.

**Strategy**: Aggressive invalidation on write, conservative retention on read.

**Related**: [REF-cache-invalidation.md](REF-cache-invalidation.md)

### Warm Fetch
Second fetch of same data when cache is populated. Performance target: <1s. Achieved: 0.11s (187x improvement over cold).

### Cold Fetch
First fetch when cache is empty. Performance matches uncached baseline (~11-20s for large projects).

---

## Automation System

### AutomationEngine
Post-commit hook consumer that orchestrates automation rule execution. Receives SaveResult after commit, evaluates rules against changed entities, spawns nested SaveSessions for automation changes.

**Pattern**: Hook → Evaluate → Execute → Commit.

### AutomationRule
Protocol for automation rules. Methods:
- `should_trigger(entity, result)`: Bool, check if rule applies
- `execute(session, entity, result)`: Perform automation actions

**Example**: PipelineConversionRule triggers on Process completion.

### PipelineConversionRule
Rule that triggers when a Process reaches COMPLETE section. Creates new Process in next pipeline stage using TemplateDiscovery and FieldSeeder.

**Flow**: Detect completion → Find template → Seed fields → Create new Process.

### TemplateDiscovery
Service for finding template tasks in target stage projects. Uses fuzzy matching (configurable threshold) to locate templates by name pattern.

**Purpose**: Templates define default field values for new Processes.

### FieldSeeder
Component that propagates field values to newly created Processes. Two modes:
- **Cascade**: Copy specific fields from source to target (e.g., `office_phone`)
- **Carry-through**: Inherit contextual fields from parent hierarchy (e.g., `vertical` from Unit)

### Post-Commit Hook
Extension point on SaveSession. Protocol method `on_commit(session, result)` called after successful commit.

**Primary Consumer**: AutomationEngine.

**Pattern**: Observer pattern for decoupled automation.

### Pipeline Conversion
Automatic creation of a new Process when an existing Process advances to COMPLETE section. Core automation use case.

**Trigger**: ProcessSection = COMPLETE AND ProcessType != ARCHIVE.

---

## Pipeline Management

### ProcessType
Enum representing 7 pipeline stages: LEAD, SALES, ONBOARDING, PRODUCTION, RETENTION, OFFBOARDING, ARCHIVE.

**Cardinality**: Each Process has exactly one ProcessType.

### ProcessSection
Enum representing visual state within a stage: BACKLOG, IN_PROGRESS, BLOCKED, REVIEW, COMPLETE.

**Mapping**: Maps to Asana project sections for visual workflow.

### PipelineState
Computed property on Process combining ProcessType and ProcessSection.

**Usage**: Automation rules query `process.pipeline_state` to detect advancement eligibility.

### Stage Advancement
Movement from one ProcessType to the next (e.g., SALES → ONBOARDING).

**Trigger**: Process section = COMPLETE AND ProcessType != terminal.

### Terminal Stage
ARCHIVE ProcessType. Processes in terminal stage cannot advance further.

**Principle**: End-of-lifecycle state with no outbound transitions.

### AutomationConfig
Top-level configuration for AutomationEngine. Fields:
- `enabled`: Bool, master switch
- `dry_run`: Bool, log without executing
- `pipeline_config`: PipelineConfig instance
- `safety_limits`: Max operations per commit

### PipelineConfig
Configuration for pipeline conversion:
- `enabled_stages`: Which ProcessTypes participate in automation
- `template_discovery`: Project suffix pattern, fuzzy threshold
- `field_seeding`: Lists of cascade/carry-through fields

### Dry Run
Automation mode where rules evaluate and log actions without executing.

**Usage**: Test automation logic before enabling live execution.

---

## Workflow Phases

### Prompt -1 (Scoping Phase)
Pre-initialization phase that validates initiative readiness before committing to full workflow.

**Question**: "Do we know enough to write Prompt 0?"

**Owner**: User (with AI assistance)

**Outputs**: Go/No-Go recommendation, validated scope, identified blockers, open questions.

**Principle**: Cheap validation prevents expensive rework. 30 minutes of scoping can save days of misdirected effort.

**Related**: `.claude/skills/initiative-scoping/session-minus-1-protocol.md`

### Prompt 0 (Initialization Phase)
Orchestrator initialization document that establishes mission context, defines success criteria, and structures the session-phased approach.

**Owner**: User (creates) → Orchestrator (consumes)

**Outputs**: Mission statement, session plan, trigger prompts, quality gates, context checklists.

**Principle**: Orchestrator should execute entire workflow from Prompt 0 without additional context gathering.

**Related**: `.claude/skills/initiative-scoping/session-0-protocol.md`

### Session
Discrete phase of work with a specific agent, clear deliverable, and quality gate. Sessions are the atomic unit of workflow.

**Owner**: Orchestrator (defines) → Specialist Agent (executes)

**Outputs**: Phase-specific deliverable (PRD, TDD, code, validation report).

**Principle**: Each session should be completable in a single focused effort. If a session needs splitting, it was scoped too broadly.

### Discovery Phase
First session(s) of a workflow where unknowns are explored, gaps identified, and requirements clarified.

**Owner**: Requirements Analyst (typically)

**Outputs**: Gap analysis, current state audit, scope refinement, technical clarifications.

**Principle**: Discovery is not optional for complex initiatives. Skipping discovery leads to rework.

---

## Agent Roles

### Orchestrator
Coordinating agent that plans, delegates, coordinates, and verifies. Does not implement directly.

**Responsibilities**: Assess complexity, Plan phases, Delegate to specialists, Verify quality gates, Adapt plans.

**Principle**: Orchestrator's judgment determines agent routing, session ordering, and workflow adaptation.

### Requirements Analyst
Specialist that clarifies intent, defines scope, and creates testable requirements. Transforms vague requests into precise specifications.

**Responsibilities**: Challenge assumptions, Create PRDs with acceptance criteria, Define scope boundaries (in AND out), Ask "why" before documenting "what".

**Primary Artifacts**: PRD

**Principle**: "Clarity before velocity. An hour of good questions saves a week of building the wrong thing."

### Architect
Specialist that designs solutions, makes structural decisions, and creates technical specifications. Translates "what" into "how."

**Responsibilities**: Design system architecture, Create TDDs with component definitions, Document decisions in ADRs, Calibrate complexity to requirements.

**Primary Artifacts**: TDD, ADR

**Principle**: "The right design feels inevitable in hindsight. Right-size everything."

### Principal Engineer
Specialist that implements solutions with craft. Translates designs into working, maintainable code.

**Responsibilities**: Implement per TDD specs, Maintain code quality and type safety, Create tests for all paths, Document implementation decisions.

**Primary Artifacts**: Code, unit tests, implementation ADRs

**Principle**: "Simplicity is a feature. Build exactly what's specified, nothing more."

### QA/Adversary
Specialist that validates implementations, finds edge cases, and ensures production readiness.

**Responsibilities**: Validate against acceptance criteria, Find edge cases and failure modes, Execute test plans, Assess production readiness.

**Primary Artifacts**: Test Plan, validation reports, defect lists

**Principle**: "Your job is to break things. Every bug found in review is a bug users don't find in production."

---

## Documentation Artifacts

### PRD (Product Requirements Document)
Defines WHAT we're building and WHY from a product/user perspective.

**Owner**: Requirements Analyst

**Location**: `/docs/requirements/PRD-{NNNN}-{slug}.md`

**Key Sections**: Problem Statement, Scope (In/Out), Functional Requirements, Acceptance Criteria

### TDD (Technical Design Document)
Defines HOW we're building it from a technical perspective.

**Owner**: Architect

**Location**: `/docs/design/TDD-{NNNN}-{slug}.md`

**Key Sections**: Overview, Component Architecture, Data Model, API Contracts, Implementation Plan

### ADR (Architecture Decision Record)
Captures WHY a specific architectural decision was made.

**Owner**: Architect (primary), Principal Engineer (implementation-level)

**Location**: `/docs/decisions/ADR-{NNNN}-{slug}.md`

**Key Sections**: Context, Decision, Rationale, Alternatives Considered, Consequences

**When to Write**: Choosing between viable approaches, adopting new patterns, deviating from established conventions, making trade-offs with long-term implications.

### Test Plan
Defines HOW we validate the implementation meets requirements.

**Owner**: QA/Adversary

**Location**: `/docs/testing/TP-{NNNN}-{slug}.md`

**Key Sections**: Test Scope, Requirements Traceability, Test Cases, Edge Cases, Exit Criteria

---

## Quality Concepts

### Quality Gate
Checkpoint between phases that must be passed before proceeding. Prevents low-quality work from propagating downstream.

**Types**:
- **PRD Quality Gate**: Problem clear, scope defined, requirements testable
- **TDD Quality Gate**: Traces to PRD, decisions documented, interfaces defined
- **Implementation Quality Gate**: Satisfies TDD, tests pass, type-safe
- **Validation Quality Gate**: Acceptance criteria met, edge cases covered

**Principle**: Quality gates are non-negotiable. Failing a gate means routing back, not proceeding with gaps.

### Fresh-Machine Test
Validation that code/documentation works on a clean environment without implicit dependencies on the author's setup.

**Application**: Examples must run, procedures must execute, from a fresh starting point.

### Acid Test
Specific, measurable validation that proves an initiative achieved its goals.

**Characteristics**: Concrete scenario (not abstract), Measurable outcome (time, success rate), Tests the real goal (not proxies).

**Example**: "New developer completes first successful API call in under 5 minutes using only the documentation."

### Backward Compatibility
Constraint that existing interfaces, behaviors, or contracts must continue to work after changes.

**Application**: New parameters must be optional with sensible defaults. Existing method signatures must not change.

---

## Communication Patterns

### Plan → Clarify → Execute
Mandatory communication pattern before any significant work.

**Steps**:
1. **Plan**: Agent creates detailed plan for the phase
2. **Clarify**: Surface ambiguities, get user input on decisions
3. **Execute**: Only after explicit confirmation ("Proceed with the plan")

**Principle**: "Never execute without confirmation. Plans are cheap; rework is expensive."

### Session Trigger Prompt
Specific prompt used to initiate a session, containing prerequisites, goals, scope, and deliverables.

**Purpose**: Provides specialist agent with everything needed to plan and execute the session.

**Key Sections**: Prerequisites, Goals, Scope (In/Out), Constraints, Deliverable specification

### Checkpoint
Summary of progress at phase boundaries, including what was accomplished, what changed, and what's next.

**Contents**: Deliverables produced, decisions made, open items, recommended next phase.

### Handoff
Transition between agents or phases, including all context, artifacts, and open items needed for receiving agent to succeed.

**Requirements**: Summary of what was produced, Quality gate status, Open questions or concerns, Inputs needed for next phase.

**Principle**: A good handoff enables the receiving agent to work without asking clarifying questions about prior work.

---

## Decision Frameworks

### Go/No-Go
Binary decision point in Prompt -1 that determines whether to proceed with Prompt 0.

**Outcomes**:
- **Go**: Proceed to Prompt 0 generation and workflow execution
- **No-Go**: Resolve blockers, gather more context, descope, or abandon initiative
- **Conditional Go**: Proceed with specific conditions that must be met before certain phases

### Must/Should/Could (MoSCoW)
Requirement prioritization framework used in PRDs.

| Priority | Meaning | Implication |
|----------|---------|-------------|
| **Must** | Non-negotiable | Blocks release if missing |
| **Should** | Important | Include if possible, defer if constrained |
| **Could** | Nice to have | Only if time permits |
| **Won't** | Explicitly excluded | Out of scope for this initiative |

### Blocking vs. Non-Blocking
Classification of dependencies and issues by their impact on progress.

**Blocking**: Cannot proceed until resolved. Requires immediate attention or scope change.

**Non-Blocking**: Can be worked around or deferred. Document and continue.

### Scope Creep
Uncontrolled expansion of scope during execution, often disguised as "clarification" or "while we're at it."

**Detection**: New requirements appearing mid-phase that weren't in the approved PRD.

**Response**: Flag explicitly, distinguish "nice to have" from "blocking," propose deferral or re-planning.

**Principle**: Scope creep is the primary cause of project failure. Name it when you see it.

### Spike
Timeboxed investigation to reduce uncertainty before committing to larger effort. Produces knowledge, not production code.

**Characteristics**: Fixed timebox (hours, not days), Specific question to answer, Output is decision-enabling information.

**When to Use**: High-uncertainty items identified in Prompt -1, technical feasibility questions, "build vs. buy" decisions.

### Complexity Level
Classification of initiative scope that determines appropriate workflow depth.

| Level | Description | Typical Workflow |
|-------|-------------|------------------|
| **Script** | Single file, utility function | Direct implementation |
| **Module** | Multiple files, single concern | Engineer → QA |
| **Service** | Multiple modules, external interfaces | Full 4-agent workflow |
| **Platform** | Multiple services, organizational impact | Extended workflow with multiple implementation phases |

**Principle**: Right-size the workflow. Not every task needs all four agents.

---

## Anti-Patterns

### Rubber-Stamp Approval
Approving artifacts without genuine validation. Passing quality gates without checking criteria.

**Impact**: Low-quality work propagates downstream, causing expensive rework.

### Analysis Paralysis
Endless scoping and planning without reaching a Go/No-Go decision.

**Mitigation**: Timebox Prompt -1, accept uncertainty, use spikes for high-risk unknowns.

### Premature Implementation
Writing code before requirements and design are understood.

**Impact**: Building the wrong thing, rework, scope creep.

### Documentation Theater
Creating documents to satisfy process rather than to enable success.

**Detection**: Documents that no one reads or references.

**Mitigation**: Every document should have a clear consumer and purpose.

### Footgun Framing
Documentation that emphasizes what NOT to do rather than what TO do.

**Impact**: Makes users feel stupid, doesn't teach the right patterns.

**Better Approach**: Lead with the correct pattern, explain why it's correct.

---

## Workflow Principles

### The 10x Principle
Well-structured agentic workflows can achieve 10x productivity by:
- Preventing rework through clear requirements
- Right-sizing effort to complexity
- Parallelizing where possible
- Catching issues early through quality gates

### Specialist Sovereignty
Each specialist agent has authority over their domain. Orchestrator delegates decisions within scope, not just tasks.

**Application**: Architect decides architecture, Engineer decides implementation details, QA decides test strategy.

### Explicit Over Implicit
State assumptions, boundaries, and decisions explicitly rather than relying on shared understanding.

**Application**: Define scope IN and OUT, document decisions in ADRs, surface open questions.

### Reference, Don't Duplicate
Information should exist in exactly one canonical location. Other documents should link to it.

**Application**: PRD defines requirements (reference from TDD). TDD defines design (reference from implementation). ADR explains decision (reference from everywhere).

---

## Acronyms

| Acronym | Expansion | Domain |
|---------|-----------|--------|
| ADR | Architecture Decision Record | Documentation |
| API | Application Programming Interface | Technical |
| GID | Global ID | Asana |
| MRR | Monthly Recurring Revenue | Business |
| MoSCoW | Must/Should/Could/Won't | Requirements |
| NFR | Non-Functional Requirement | Requirements |
| PAT | Personal Access Token | Authentication |
| PRD | Product Requirements Document | Documentation |
| TDD | Technical Design Document | Documentation |
| TTL | Time-To-Live | Cache |
| UoW | Unit of Work | Architecture |

---

## See Also

### Reference Documentation
- [REF-asana-hierarchy.md](REF-asana-hierarchy.md) - Asana resource structure
- [REF-entity-lifecycle.md](REF-entity-lifecycle.md) - Entity creation, detection, persistence
- [REF-savesession-lifecycle.md](REF-savesession-lifecycle.md) - SaveSession workflow
- [REF-detection-tiers.md](REF-detection-tiers.md) - Entity type detection system
- [REF-cache-architecture.md](REF-cache-architecture.md) - Cache design and patterns
- [REF-batch-operations.md](REF-batch-operations.md) - Batch API usage
- [REF-workflow-phases.md](REF-workflow-phases.md) - Development workflow phases

### Skills
- `.claude/skills/10x-workflow/` - Full workflow process documentation
- `.claude/skills/documentation/` - Document templates and standards
- `.claude/skills/initiative-scoping/` - Prompt -1 and Prompt 0 protocols

### Agent Definitions
- `.claude/agents/doc-auditor.md` - Documentation quality auditing
- `.claude/agents/doc-reviewer.md` - Technical accuracy verification
- `.claude/agents/information-architect.md` - Documentation structure
- `.claude/agents/tech-writer.md` - Content creation

---

**Maintenance**: This glossary is the single source of truth for terminology. Update this file when introducing new concepts or refining existing definitions. Mark deprecated terms clearly and provide migration guidance.
