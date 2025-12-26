# PRD: Process Pipeline

> **PARTIAL SUPERSESSION NOTICE (2025-12-19)**
>
> The `ProcessProjectRegistry` requirements (FR-REG-*) in this PRD have been **superseded** by [ADR-0101](../decisions/ADR-0101-process-pipeline-correction.md) and [PRD-TECH-DEBT-REMEDIATION](PRD-TECH-DEBT-REMEDIATION.md). The ProcessProjectRegistry was never implemented - pipeline project detection now uses `ProjectTypeRegistry` with dynamic discovery via `WorkspaceProjectRegistry`.
>
> **Superseded requirements**: FR-REG-001 through FR-REG-005, FR-DETECT-001 (ProcessProjectRegistry integration)
>
> **Still valid**: FR-TYPE, FR-SECTION, FR-STATE, FR-DUAL (dual membership concepts), FR-SEED (BusinessSeeder)

## Metadata
- **PRD ID**: PRD-PROCESS-PIPELINE
- **Status**: Partially Superseded
- **Author**: Requirements Analyst
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-19
- **Stakeholders**: autom8 platform team
- **Related PRDs**: [PRD-0010 Business Model Layer](PRD-0010-business-model-layer.md), [PRD-0013 Hierarchy Hydration](PRD-0013-hierarchy-hydration.md), **[PRD-TECH-DEBT-REMEDIATION](PRD-TECH-DEBT-REMEDIATION.md) (supersedes FR-REG-*)**
- **Discovery**: [DISCOVERY-PROCESS-PIPELINE](../analysis/DISCOVERY-PROCESS-PIPELINE.md)

---

## Problem Statement

**What problem are we solving?**

Process entities currently exist only as hierarchy children (Business > Unit > ProcessHolder > Process) with a stub `ProcessType.GENERIC`. They cannot represent first-class pipeline events like sales opportunities, onboarding workflows, or retention campaigns. The SDK lacks:

1. **Type distinction**: All processes are `GENERIC` - no way to differentiate sales from onboarding
2. **Pipeline state**: No mechanism to track pipeline position (Opportunity, Active, Converted, etc.)
3. **Dual membership**: Processes cannot simultaneously belong to the hierarchy AND a pipeline project
4. **State transitions**: No helpers to move processes between pipeline stages
5. **Seeding**: No factory to create complete entity hierarchies for new leads/businesses

**For whom?**

Consumer applications (autom8 platform, webhook handlers, Calendly integrations) that need to:
- Create business entities from external triggers (Calendly bookings, form submissions)
- Track sales pipeline progression
- Query processes by type and state
- Automate state transitions based on business events

**Impact of not solving:**

Without this functionality, consumers must implement pipeline logic outside the SDK, leading to:
- Duplicated project/section lookup code across consumers
- Inconsistent state extraction from memberships
- No type safety for process types or pipeline states
- Manual entity creation with error-prone hierarchy construction

---

## Goals & Success Metrics

| Goal | Success Metric |
|------|----------------|
| **Type safety** | ProcessType enum covers all stakeholder workflow types |
| **Pipeline visibility** | `process.pipeline_state` returns current section without API call |
| **Easy creation** | BusinessSeeder creates full hierarchy in single call |
| **State transitions** | Pipeline moves queue via SaveSession pattern |
| **Backward compatibility** | All existing tests pass (with allowed count changes) |

---

## Scope

### In Scope

1. **ProcessType enum expansion** with stakeholder-aligned types
2. **ProcessSection enum** for pipeline states
3. **ProcessProjectRegistry** mapping types to project GIDs
4. **pipeline_state property** extracting state from memberships
5. **Dual membership helpers** for creating pipeline-aware processes
6. **State transition helpers** composing with SaveSession
7. **BusinessSeeder factory** for full hierarchy creation
8. **Detection integration** for ProcessType via pipeline project
9. **Backward compatibility** preservation

### Out of Scope

1. **Workflow orchestration logic** - Business rules for when/how to transition states belong in consumers, not SDK
2. **Calendly integration** - Webhook parsing and event routing is consumer responsibility
3. **Webhook event dispatch** - SDK provides primitives, not automation
4. **State machine enforcement** - SDK enables transitions, does not enforce valid sequences
5. **Pipeline analytics/reporting** - Query and aggregation logic belongs in consumers
6. **Section creation/management** - Assumes sections exist in pipeline projects
7. **Custom field for ProcessType** - Detection uses project membership only (Phase 1)

---

## Requirements

### Functional Requirements

#### FR-TYPE: ProcessType Enum

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-TYPE-001 | ProcessType enum includes SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION values | Must | `ProcessType.SALES` and other values exist and are valid enum members |
| FR-TYPE-002 | ProcessType.GENERIC is preserved for backward compatibility | Must | `ProcessType.GENERIC` returns "generic" and existing code continues to work |
| FR-TYPE-003 | ProcessType values are lowercase strings (str, Enum) | Must | `ProcessType.SALES.value == "sales"` |

#### FR-SECTION: ProcessSection Enum

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SECTION-001 | ProcessSection enum includes OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT, OTHER values | Must | All 7 enum members exist and are importable |
| FR-SECTION-002 | ProcessSection.from_name() classmethod matches section names case-insensitively | Must | `ProcessSection.from_name("Opportunity")` returns `ProcessSection.OPPORTUNITY` |
| FR-SECTION-003 | ProcessSection.from_name() returns OTHER for unrecognized section names | Must | `ProcessSection.from_name("Unknown Section")` returns `ProcessSection.OTHER` |
| FR-SECTION-004 | ProcessSection.from_name() handles None input gracefully | Must | `ProcessSection.from_name(None)` returns `None` |

#### FR-REG: ProcessProjectRegistry

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-REG-001 | ProcessProjectRegistry is a singleton accessed via get_process_project_registry() | Must | Multiple calls return same instance |
| FR-REG-002 | Registry maps ProcessType to project GID | Must | `registry.get_project_gid(ProcessType.SALES)` returns GID string or None |
| FR-REG-003 | Registry supports environment variable override pattern: ASANA_PROCESS_PROJECT_{TYPE} | Must | Setting `ASANA_PROCESS_PROJECT_SALES=123` overrides registered GID |
| FR-REG-004 | Registry provides reverse lookup: project GID to ProcessType | Must | `registry.get_process_type("123456")` returns `ProcessType.SALES` or None |
| FR-REG-005 | Registry initialization is lazy (no env var reads until first access) | Should | Environment variables can be set after import |

#### FR-STATE: Pipeline State Access

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-STATE-001 | Process.pipeline_state property returns ProcessSection or None | Must | Property is accessible and returns correct type |
| FR-STATE-002 | pipeline_state extracts state from cached memberships without API call | Must | No HTTP request made when accessing pipeline_state |
| FR-STATE-003 | pipeline_state uses ProcessProjectRegistry to identify correct project membership | Must | Only pipeline project membership is checked, not hierarchy project |
| FR-STATE-004 | pipeline_state returns None if process not in any pipeline project | Must | Process in hierarchy-only returns None for pipeline_state |
| FR-STATE-005 | pipeline_state returns None with warning log if process is in multiple pipeline projects | Must | Log warning includes process GID and project GIDs; returns None |
| FR-STATE-006 | Process.process_type property returns detected ProcessType from pipeline project | Must | Property uses registry reverse lookup |
| FR-STATE-007 | process_type returns GENERIC if not in any registered pipeline project | Must | Fallback behavior preserves backward compatibility |
| FR-STATE-008 | process_type returns GENERIC with warning if in multiple pipeline projects | Must | Ambiguous state falls back to safe default |

#### FR-DUAL: Dual Membership Support

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DUAL-001 | Process.add_to_pipeline() helper queues add_to_project action for pipeline project | Must | `process.add_to_pipeline(session, ProcessType.SALES)` queues action |
| FR-DUAL-002 | add_to_pipeline looks up project GID from ProcessProjectRegistry | Must | Caller provides ProcessType, not raw GID |
| FR-DUAL-003 | add_to_pipeline optionally accepts target section | Should | `add_to_pipeline(session, type, section=ProcessSection.OPPORTUNITY)` |
| FR-DUAL-004 | add_to_pipeline raises ValueError if ProcessType has no registered project | Must | Clear error message indicates missing configuration |
| FR-DUAL-005 | Detection system recognizes dual-membership processes | Must | detect_entity_type returns PROCESS for tasks in both hierarchy and pipeline |

#### FR-TRANS: State Transition Helpers

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-TRANS-001 | Process.move_to_state() helper queues move_to_section action | Must | `process.move_to_state(session, ProcessSection.CONVERTED)` queues action |
| FR-TRANS-002 | move_to_state looks up section GID in current pipeline project | Must | Section lookup uses process.process_type to find correct project |
| FR-TRANS-003 | move_to_state raises ValueError if process not in pipeline project | Must | Clear error for processes without pipeline membership |
| FR-TRANS-004 | move_to_state raises ValueError if section not found in project | Must | Error includes section name and project GID |
| FR-TRANS-005 | Section GID lookup uses cached section data or lazy fetch | Should | Minimize API calls; cache section GIDs per project |

#### FR-SEED: BusinessSeeder Factory

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SEED-001 | BusinessSeeder.seed_async() creates Business entity if not found | Must | New Business created with provided data |
| FR-SEED-002 | BusinessSeeder.seed_async() finds existing Business by company_id or name | Must | Existing Business returned if match found |
| FR-SEED-003 | BusinessSeeder creates Unit under Business if not exists | Must | Unit created with standard naming convention |
| FR-SEED-004 | BusinessSeeder creates ProcessHolder under Unit if not exists | Must | ProcessHolder created with standard "Processes" name |
| FR-SEED-005 | BusinessSeeder creates Process in ProcessHolder | Must | Process created as subtask of ProcessHolder |
| FR-SEED-006 | BusinessSeeder adds Process to specified pipeline project | Must | Dual membership established at creation |
| FR-SEED-007 | BusinessSeeder returns SeederResult with all created/found entities | Must | Result object provides access to business, unit, process_holder, process |
| FR-SEED-008 | BusinessSeeder uses SaveSession for all operations | Must | Changes committed via SaveSession.commit_async() |
| FR-SEED-009 | BusinessSeeder is async-first with optional sync wrapper | Must | seed_async() is primary API; seed() is sync wrapper |
| FR-SEED-010 | BusinessSeeder accepts optional Contact data to seed | Should | Seed Contact alongside Business if provided |
| FR-SEED-011 | BusinessSeeder is idempotent for same input | Must | Multiple calls with same data produce same result |

#### FR-DETECT: Detection Integration

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DETECT-001 | ProcessProjectRegistry integrates with detection Tier 1 | Must | Detection checks ProcessProjectRegistry.get_process_type(project_gid) |
| FR-DETECT-002 | Detection returns EntityType.PROCESS for tasks in registered pipeline projects | Must | Tier 1 detection works for pipeline project membership |
| FR-DETECT-003 | Detection fallback chain works for unregistered projects | Must | Tier 2+ detection still functions for processes not in registry |

#### FR-COMPAT: Backward Compatibility

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-COMPAT-001 | ProcessType.GENERIC remains valid and functional | Must | Existing code using GENERIC continues to work |
| FR-COMPAT-002 | ProcessHolder pattern unchanged | Must | ProcessHolder children, _populate_children work as before |
| FR-COMPAT-003 | Process navigation (process_holder, unit, business) unchanged | Must | Existing navigation code works without modification |
| FR-COMPAT-004 | Process custom field accessors unchanged | Must | All 8 existing field accessors work |
| FR-COMPAT-005 | Existing Process tests pass (allow enum count update) | Must | Only test_process_type_enum_member_count needs update for new types |

---

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | pipeline_state access latency | < 1ms | No API call; pure in-memory lookup from cached memberships |
| NFR-PERF-002 | process_type detection latency | < 1ms | Registry lookup is O(1) dict access |
| NFR-PERF-003 | BusinessSeeder.seed_async() latency (dev) | < 500ms | End-to-end time for full hierarchy creation |
| NFR-PERF-004 | BusinessSeeder.seed_async() latency (prod) | < 200ms | With connection pooling and warm cache |
| NFR-CONFIG-001 | ProcessProjectRegistry configurable via environment | Required | ASANA_PROCESS_PROJECT_{TYPE} pattern works |
| NFR-CONFIG-002 | Section name matching is case-insensitive | Required | "opportunity" matches "Opportunity" |
| NFR-TEST-001 | Unit test coverage for new code | >= 90% | pytest --cov reports coverage |
| NFR-TEST-002 | No mocking of ProcessProjectRegistry in consumer tests | Preferred | Registry uses real env vars or test fixtures |

---

## User Stories / Use Cases

### UC-1: Calendly Booking Creates Sales Process

**Actor**: Webhook handler (consumer application)

**Scenario**:
1. Calendly webhook fires with new booking data
2. Handler extracts business name, contact email from payload
3. Handler calls `BusinessSeeder.seed_async(client, business_data, process_type=ProcessType.SALES)`
4. Seeder finds or creates Business, Unit, ProcessHolder
5. Seeder creates Process in ProcessHolder
6. Seeder adds Process to Sales Pipeline project in "Opportunity" section
7. Handler receives SeederResult with all entity references
8. Handler can update Contact email on `result.contact`

### UC-2: Query Processes by Pipeline State

**Actor**: Platform service

**Scenario**:
1. Service loads Process entity with memberships populated
2. Service accesses `process.pipeline_state`
3. Property returns `ProcessSection.ACTIVE` (no API call)
4. Service filters processes by state for dashboard display

### UC-3: Transition Process to Converted

**Actor**: Sales automation service

**Scenario**:
1. Service determines sale is closed
2. Service creates SaveSession
3. Service calls `process.move_to_state(session, ProcessSection.CONVERTED)`
4. Service commits session
5. Process moves to "Converted" section in Asana

### UC-4: Detect Process Type from Task

**Actor**: Detection system (internal)

**Scenario**:
1. Detection receives task with memberships
2. Tier 1: Check if any membership project is in ProcessProjectRegistry
3. If yes: Return EntityType.PROCESS with process_type from registry
4. If no: Fall back to Tier 2+ detection

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| All pipeline projects have standard section names (Opportunity, Delayed, Active, Scheduled, Converted, Did Not Convert) | Stakeholder input; validated by fuzzy matching fallback |
| Section names are consistent across all ProcessType pipeline projects | Design constraint; OTHER fallback handles exceptions |
| Tasks can belong to multiple Asana projects simultaneously | Asana API documented behavior |
| Process entities should not be in multiple pipeline projects | Business logic constraint; treated as error condition |
| Environment variables are available at SDK initialization time | Standard deployment pattern |
| BusinessSeeder find-by-name uses exact match | Simplest implementation; can extend to fuzzy if needed |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| SaveSession.move_to_section() | SDK (existing) | Available - session.py:1121-1195 |
| SaveSession.add_to_project() | SDK (existing) | Available - session.py:906-979 |
| ProjectTypeRegistry pattern | SDK (existing) | Available - registry.py |
| Task.memberships structure | SDK (existing) | Available - task.py:71 |
| Detection Tier 1 extension point | SDK (existing) | Available - detection.py:445-515 |
| Pipeline project GIDs | User configuration | Required at runtime via env vars |
| Section GIDs | Runtime lookup | Lazy fetch or user configuration |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should ProcessType have a priority order for multi-project edge case? | Stakeholder | Before TDD | Resolved: Treat as error, return None/GENERIC with warning |
| Should section GIDs be cached globally or per-project? | Architect | TDD phase | TBD in TDD |
| Should BusinessSeeder accept custom field overrides for Process? | Stakeholder | TDD phase | TBD - consider ProcessData input model |
| Should sync wrappers be provided for all new methods? | Architect | TDD phase | Likely yes per SDK pattern |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Requirements Analyst | Initial draft from discovery |
