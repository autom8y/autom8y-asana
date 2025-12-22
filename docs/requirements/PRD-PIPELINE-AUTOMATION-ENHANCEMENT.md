# PRD: Pipeline Automation Enhancement

## Metadata

- **PRD ID**: PRD-PIPELINE-AUTOMATION-ENHANCEMENT
- **Status**: Draft
- **Author**: Requirements Analyst (Claude)
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **Stakeholders**: Engineering Team, Operations
- **Related PRDs**: [PRD-AUTOMATION-LAYER](PRD-AUTOMATION-LAYER.md), [PRD-PROCESS-PIPELINE](PRD-PROCESS-PIPELINE.md)
- **Discovery Document**: [DISCOVERY-PIPELINE-AUTOMATION-ENHANCEMENT](/docs/analysis/DISCOVERY-PIPELINE-AUTOMATION-ENHANCEMENT.md)
- **Initiative**: [PROMPT-0-PIPELINE-AUTOMATION-ENHANCEMENT](PROMPT-0-PIPELINE-AUTOMATION-ENHANCEMENT.md)

---

## Problem Statement

### What problem are we solving?

The Pipeline Automation Layer successfully triggers on Process conversion (section change to CONVERTED) and creates a new Process in the target project. However, the current implementation achieves only ~10% of legacy feature parity. Critical automation behaviors are missing:

1. **No subtask duplication**: Template checklist items are not copied to new Processes
2. **No hierarchy integration**: New Processes float as top-level tasks instead of being placed under ProcessHolder
3. **No field propagation**: Seeded field values are computed but never written to the API
4. **No assignee assignment**: New Processes have no owner
5. **No context**: Users cannot tell why a Process was created or where it came from

### For whom?

- **Operations team**: Relies on automated pipeline handoffs to reduce manual work
- **Business users**: Expect consistent Process structure with pre-populated checklists
- **Account managers**: Need assignee set correctly based on rep field

### What's the impact of not solving it?

- Manual copying of subtasks and checklists for every conversion
- Processes orphaned from Business hierarchy, breaking navigation and reporting
- Custom field values manually re-entered, increasing error rate
- Assignee manually set on every new Process, delaying response time
- Lost audit trail - no way to trace a Process back to its source

---

## Goals and Success Metrics

### Primary Goals

1. **Legacy Parity**: Match all automation behaviors from the legacy system
2. **Production Readiness**: Handle race conditions, edge cases, and graceful degradation
3. **Hierarchy Integrity**: New Processes correctly placed in Business > Unit > ProcessHolder chain
4. **Complete Data Flow**: Seeded fields actually propagate to new Processes via API

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Subtask duplication rate | 100% | Template subtasks present on new Process |
| Field propagation rate | 100% | Seeded fields written to API |
| Hierarchy placement rate | 95%+ | New Process is subtask of ProcessHolder |
| Assignee assignment rate | 90%+ | New Process has assignee from rep field |
| Comment creation rate | 95%+ | Onboarding comment present on new Process |
| Full conversion time | <3s | End-to-end pipeline completion |
| Graceful degradation | 100% | No conversion failures from enhancement errors |

---

## Scope

### In Scope

- Task duplication with subtasks via Asana duplicate API
- Subtask wait strategy with configurable polling timeout
- ProcessHolder parent relationship via `set_parent()`
- Process ordering within ProcessHolder (insert after preceding Process)
- Custom field value writing to API via `update_async()`
- Assignee assignment from rep field (Unit.rep with Business.rep fallback)
- Onboarding comment creation with conversion context
- Graceful degradation for all enhancement steps
- Unit tests for all new functionality
- Integration tests for full pipeline

### Out of Scope

- ProcessHolder auto-creation (if missing, log warning and continue)
- Custom field creation (fields must already exist on target project)
- Multi-hop pipeline (Sales -> Onboarding -> Implementation in one commit)
- Rollback on partial failure (log and continue approach)
- Webhook-based subtask detection
- Template subtask modification or customization
- Attachment duplication
- Dry-run mode for conversion preview

---

## Requirements

### Functional Requirements: Task Duplication (FR-DUP)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DUP-001 | TasksClient SHALL provide `duplicate_async()` method wrapping Asana's `POST /tasks/{task_gid}/duplicate` endpoint | Must | GIVEN a valid task GID and name WHEN `duplicate_async()` is called THEN a new task is created with the specified name and returns the new task object |
| FR-DUP-002 | `duplicate_async()` SHALL accept an `include` parameter specifying which attributes to copy | Must | GIVEN `include=["subtasks", "notes"]` WHEN duplicating a task THEN the new task has subtasks and notes copied from the template |
| FR-DUP-003 | `duplicate_async()` SHALL support `subtasks` in the `include` parameter to duplicate the template's subtask hierarchy | Must | GIVEN a template with 5 subtasks WHEN duplicating with `include=["subtasks"]` THEN the new task eventually has 5 subtasks |
| FR-DUP-004 | `duplicate_async()` SHALL return the new task object with its GID immediately available | Must | GIVEN a successful duplication WHEN the API returns THEN the response contains `new_task.gid` for subsequent operations |
| FR-DUP-005 | PipelineConversionRule SHALL use `duplicate_async()` instead of `create_async()` for new Process creation | Must | GIVEN a Process conversion WHEN the rule executes THEN the new Process is created via duplication, not creation |

### Functional Requirements: Subtask Wait Strategy (FR-WAIT)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-WAIT-001 | The system SHALL provide a `SubtaskWaiter` utility for polling subtask creation status | Must | GIVEN `SubtaskWaiter` WHEN instantiated with a client THEN it provides `wait_for_subtasks_async()` method |
| FR-WAIT-002 | `wait_for_subtasks_async()` SHALL poll until subtask count matches expected count or timeout | Must | GIVEN expected count of 5 WHEN polling a task that eventually has 5 subtasks THEN the method returns `True` before timeout |
| FR-WAIT-003 | The subtask wait timeout SHALL be configurable with a default of 2.0 seconds | Must | GIVEN no explicit timeout WHEN waiting for subtasks THEN timeout defaults to 2.0 seconds; GIVEN timeout=5.0 WHEN waiting THEN timeout is 5.0 seconds |
| FR-WAIT-004 | The poll interval SHALL be configurable with a default of 0.2 seconds | Should | GIVEN no explicit interval WHEN polling THEN checks occur every 0.2 seconds |
| FR-WAIT-005 | On timeout, `wait_for_subtasks_async()` SHALL return `False` and log a warning | Must | GIVEN timeout exceeded WHEN subtask count not reached THEN method returns `False` and logs warning with current vs expected count |
| FR-WAIT-006 | PipelineConversionRule SHALL wait for subtasks before proceeding to field seeding | Must | GIVEN subtask duplication triggered WHEN wait completes (success or timeout) THEN proceed to field seeding |
| FR-WAIT-007 | Expected subtask count SHALL be determined from the template task before duplication | Must | GIVEN a template task WHEN preparing for duplication THEN fetch `num_subtasks` or call `subtasks_async()` to get expected count |

### Functional Requirements: Field Seeding Write (FR-SEED)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SEED-001 | FieldSeeder SHALL provide `write_fields_async()` method to persist seeded values to API | Must | GIVEN seeded field values WHEN `write_fields_async()` is called THEN values are written to the target task via API |
| FR-SEED-002 | `write_fields_async()` SHALL use a single `update_async()` call with all fields | Must | GIVEN 5 fields to write WHEN `write_fields_async()` executes THEN exactly one API call is made with all 5 fields |
| FR-SEED-003 | Field names SHALL be resolved to GIDs using `CustomFieldAccessor._resolve_gid()` | Must | GIVEN field name "Vertical" WHEN resolving THEN returns the GID for that field from the target task's custom field definitions |
| FR-SEED-004 | Enum field values SHALL be resolved to option GIDs before API write | Must | GIVEN enum field "Vertical" with value "Dental" WHEN writing THEN the API receives the GID of the "Dental" option, not the string |
| FR-SEED-005 | Missing fields on target project SHALL be skipped with a warning log | Should | GIVEN field "Legacy Status" not on target project WHEN writing fields THEN skip that field, log warning, continue with other fields |
| FR-SEED-006 | Field seeding write SHALL complete within 300ms for typical field sets | Should | GIVEN 5-10 fields to write WHEN `write_fields_async()` executes THEN completes in <300ms |
| FR-SEED-007 | `write_fields_async()` SHALL use `CustomFieldAccessor.to_api_dict()` to format the payload | Must | GIVEN seeded values WHEN preparing API payload THEN use accessor's formatting for type conversion (Decimal, lists, enums) |

### Functional Requirements: Hierarchy Placement (FR-HIER)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-HIER-001 | PipelineConversionRule SHALL discover the ProcessHolder from the source Process's Unit | Must | GIVEN source Process with Unit WHEN discovering ProcessHolder THEN access via `unit.process_holder` property |
| FR-HIER-002 | New Process SHALL be set as subtask of ProcessHolder using `set_parent()` | Must | GIVEN ProcessHolder discovered WHEN placing new Process THEN call `session.set_parent(new_process, process_holder)` |
| FR-HIER-003 | New Process SHALL be inserted after the source Process in ProcessHolder's children | Must | GIVEN source Process in ProcessHolder WHEN placing new Process THEN use `insert_after=source_process` parameter |
| FR-HIER-004 | If source Process is not in ProcessHolder, new Process SHALL be inserted at end | Should | GIVEN source Process not found in ProcessHolder children WHEN placing THEN omit `insert_after` to append at end |
| FR-HIER-005 | If ProcessHolder is not hydrated, the system SHALL fetch it on-demand | Should | GIVEN `unit.process_holder` returns None WHEN hierarchy placement needed THEN call `unit._fetch_holders_async()` first |
| FR-HIER-006 | If ProcessHolder is missing (not just unhydrated), log warning and skip hierarchy placement | Must | GIVEN Unit with no ProcessHolder (data hygiene issue) WHEN discovering ProcessHolder THEN log warning, continue without hierarchy placement |
| FR-HIER-007 | Hierarchy placement SHALL complete within 200ms | Should | GIVEN ProcessHolder discovered WHEN `set_parent()` executes THEN completes in <200ms |

### Functional Requirements: Assignee Assignment (FR-ASSIGN)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ASSIGN-001 | New Process assignee SHALL be determined from rep field | Must | GIVEN Unit with rep field populated WHEN assigning THEN use first user GID from rep field |
| FR-ASSIGN-002 | Rep resolution SHALL check `Unit.rep` first, falling back to `Business.rep` | Must | GIVEN Unit.rep populated WHEN resolving rep THEN use Unit.rep; GIVEN Unit.rep empty WHEN resolving THEN use Business.rep |
| FR-ASSIGN-003 | Rep field is a `PeopleField` returning `list[dict]` with user GIDs | Must | GIVEN rep field value WHEN extracting assignee THEN access `rep[0]["gid"]` for first user's GID |
| FR-ASSIGN-004 | Assignee SHALL be set using existing `set_assignee_async()` method | Must | GIVEN assignee GID resolved WHEN setting assignee THEN call `client.tasks.set_assignee_async(task_gid, assignee_gid)` |
| FR-ASSIGN-005 | If rep field is empty on both Unit and Business, log warning and skip assignee | Must | GIVEN no rep found WHEN assigning THEN log warning "No rep found for conversion", leave assignee unset |
| FR-ASSIGN-006 | Assignee assignment failure SHALL NOT fail the conversion | Must | GIVEN assignee API call fails WHEN handling error THEN log warning, continue conversion |

### Functional Requirements: Onboarding Comment (FR-COMMENT)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-COMMENT-001 | New Process SHALL receive an onboarding comment explaining its creation context | Must | GIVEN successful Process creation WHEN comment step executes THEN comment is added to new Process |
| FR-COMMENT-002 | Comment SHALL use `create_comment_async()` from StoriesClient | Must | GIVEN comment text WHEN creating comment THEN call `client.stories.create_comment_async(task=gid, text=text)` |
| FR-COMMENT-003 | Comment SHALL include: ProcessType, source Process name, conversion date, source project | Must | GIVEN conversion context WHEN generating comment THEN include all four elements per template |
| FR-COMMENT-004 | Comment SHALL include clickable link to source Process | Should | GIVEN source Process GID and project GID WHEN generating comment THEN include `https://app.asana.com/0/{project_gid}/{task_gid}` |
| FR-COMMENT-005 | Comment template: "This {ProcessType} process was automatically created when \"{Source Process Name}\" was converted on {Date}.\n\nSource Process: {URL}" | Must | GIVEN template WHEN generating THEN output matches format with substituted values |
| FR-COMMENT-006 | Comment creation SHALL occur AFTER field seeding and hierarchy placement | Must | GIVEN conversion steps WHEN ordering THEN comment is last step after all data operations |
| FR-COMMENT-007 | Comment creation failure SHALL NOT fail the conversion | Must | GIVEN comment API call fails WHEN handling error THEN log warning, continue (conversion is still valid) |
| FR-COMMENT-008 | Comment creation SHALL complete within 100ms | Should | GIVEN comment text WHEN `create_comment_async()` executes THEN completes in <100ms |

### Functional Requirements: Error Handling (FR-ERR)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ERR-001 | Each enhancement step SHALL be wrapped in try/except with graceful degradation | Must | GIVEN any enhancement step fails WHEN exception caught THEN log error, continue to next step |
| FR-ERR-002 | Conversion SHALL succeed if core task duplication succeeds, even if enhancements fail | Must | GIVEN field seeding fails WHEN conversion completes THEN new Process exists (partial success) |
| FR-ERR-003 | Each step SHALL log its outcome (success, skipped, or failed with reason) | Should | GIVEN any step completes WHEN logging THEN record step name, outcome, and timing |
| FR-ERR-004 | Failed steps SHALL be tracked in the conversion result for debugging | Should | GIVEN multiple steps fail WHEN conversion completes THEN result includes list of failed steps with reasons |
| FR-ERR-005 | Transient API errors (rate limit, timeout) SHALL be distinguished from permanent errors | Should | GIVEN rate limit error WHEN logging THEN indicate it's transient vs field-not-found which is permanent |
| FR-ERR-006 | Existing automation behavior SHALL be unchanged for current consumers | Must | GIVEN existing PipelineConversionRule consumers WHEN enhancements are added THEN no breaking changes to API or behavior |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Task duplication latency | <500ms | Time from `duplicate_async()` call to response |
| NFR-002 | Subtask wait timeout | Configurable, default 2.0s | Configuration parameter |
| NFR-003 | Subtask poll interval | Configurable, default 0.2s | Configuration parameter |
| NFR-004 | Field seeding write latency | <300ms | Time for `update_async()` with all fields |
| NFR-005 | Hierarchy placement latency | <200ms | Time for `set_parent()` operation |
| NFR-006 | Comment creation latency | <100ms | Time for `create_comment_async()` |
| NFR-007 | Full conversion time | <3.0s | End-to-end from trigger to completion |
| NFR-008 | Enhancement step failure rate | <1% | Percentage of steps that fail vs succeed |
| NFR-009 | Code coverage for new code | >90% | Unit test coverage for new functionality |
| NFR-010 | No regression in existing tests | 100% pass | All existing automation tests pass |

---

## User Stories / Use Cases

### UC-001: Sales to Onboarding Conversion

**As an** operations user
**I want** a Sales Process to automatically create an Onboarding Process when converted
**So that** the implementation team has a pre-configured task with all relevant information

**Flow**:
1. User moves Sales Process to "Converted" section
2. System triggers PipelineConversionRule
3. System finds "Onboarding Template" in Onboarding Pipeline project
4. System duplicates template with all subtasks (checklist items)
5. System waits for subtasks to be fully created
6. System places new Process under ProcessHolder as sibling of Sales Process
7. System writes seeded fields (Contact Phone, Vertical, Started At, etc.)
8. System sets assignee from Unit.rep (or Business.rep fallback)
9. System adds onboarding comment with source context

**Outcome**: Onboarding Process exists with complete checklist, correct hierarchy position, populated fields, assigned owner, and audit trail comment.

### UC-002: Conversion with Missing ProcessHolder

**As an** operations user
**I want** conversion to succeed even if ProcessHolder is missing
**So that** data hygiene issues don't block business operations

**Flow**:
1. User moves Process to "Converted" section
2. System cannot find ProcessHolder for Unit
3. System logs warning: "ProcessHolder not found for unit X, skipping hierarchy placement"
4. System continues with field seeding, assignee, and comment
5. New Process is created but as top-level task (not under ProcessHolder)

**Outcome**: Conversion completes partially; Operations team can later fix hierarchy manually.

### UC-003: Conversion with Empty Rep Field

**As an** operations user
**I want** conversion to succeed even if no rep is assigned
**So that** the Process is created and can be assigned later

**Flow**:
1. Conversion triggers for Process
2. System checks Unit.rep - empty
3. System checks Business.rep - empty
4. System logs warning: "No rep found for conversion, leaving assignee unset"
5. System continues with other steps
6. New Process created without assignee

**Outcome**: Process exists; Operations team assigns owner manually.

---

## Assumptions

| # | Assumption | Basis |
|---|------------|-------|
| A1 | `rep` is the consistent field name across Unit and Business | User clarification during discovery |
| A2 | Asana duplicate API returns new task GID immediately, subtasks created async | Asana API documentation and forum research |
| A3 | Template tasks have stable subtask counts (not dynamically changing) | Operational practice - templates are manually maintained |
| A4 | ProcessHolder exists for well-maintained Units | Business process design; absence indicates data hygiene issue |
| A5 | Target projects have required custom fields already configured | Field creation is out of scope per Prompt 0 |
| A6 | Rep field contains at most one user for assignment purposes | Business process - single owner per Process |
| A7 | 2-second default timeout is sufficient for typical subtask counts (1-10) | Empirical testing of Asana duplication timing |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| `set_parent()` with `insert_after` | SDK Team | EXISTS | Confirmed in SaveSession, lines 1747-1835 |
| `create_comment_async()` | SDK Team | EXISTS | Confirmed in StoriesClient, lines 352-392 |
| `set_assignee_async()` | SDK Team | EXISTS | Confirmed in TasksClient |
| `PeopleField` descriptor | SDK Team | EXISTS | Returns `list[dict]` with user GIDs |
| `unit.process_holder` via HolderRef | SDK Team | EXISTS | Unit.py lines 78-79 |
| `CustomFieldAccessor.to_api_dict()` | SDK Team | EXISTS | custom_field_accessor.py lines 205-217 |
| `duplicate_async()` in TasksClient | SDK Team | GAP | Must be implemented (Gap 1) |
| `SubtaskWaiter` utility | SDK Team | GAP | Must be implemented (Gap 2) |
| `write_fields_async()` in FieldSeeder | SDK Team | GAP | Must be implemented (Gap 3) |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All 20 discovery questions resolved in Session 1 |

---

## Traceability Matrix

| Requirement | Discovery Finding | Prompt 0 Reference |
|-------------|-------------------|-------------------|
| FR-DUP-* | Gap 1: duplicate_async() does NOT exist | "Use duplicate_async() for task creation with subtasks" |
| FR-WAIT-* | Gap 2: No wait mechanism exists | "Wait for subtasks before further API operations" |
| FR-SEED-* | Gap 3: FieldSeeder computes only | "Write seeded fields to API via update_async()" |
| FR-HIER-* | Gap 4: ProcessHolder discovery EXISTS via HolderRef | "Set ProcessHolder as parent via set_parent()" |
| FR-ASSIGN-* | Gap 5: Rep field EXISTS via PeopleField | "Resolve assignee from rep field" |
| FR-COMMENT-* | Gap 6: create_comment_async() EXISTS | "Add onboarding comment via create_comment_async()" |
| FR-ERR-* | Risk Register: Graceful degradation | "If any enhancement step fails, log and continue" |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Requirements Analyst | Initial draft from discovery findings |
