# PRD: SDK Demonstration Suite

## Metadata
- **PRD ID**: PRD-SDKDEMO
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-12
- **Last Updated**: 2025-12-12
- **Stakeholders**: SDK Users, Developer Experience Team, QA
- **Related PRDs**: PRD-BIZMODEL (Business Model Layer)
- **Discovery Document**: [DISCOVERY-SDKDEMO.md](/docs/validation/DISCOVERY-SDKDEMO.md)

---

## Problem Statement

### What Problem Are We Solving?

The autom8_asana SDK has implemented comprehensive functionality including SaveSession (Unit of Work pattern), 16 action operations, and CustomFieldAccessor - but **no executable validation exists** to prove these features work correctly against the real Asana API.

### For Whom?

1. **SDK Developers**: Need confidence that SDK operations work as documented
2. **New Team Members**: Need executable examples demonstrating SDK usage patterns
3. **QA Engineers**: Need repeatable validation for regression testing
4. **Integration Engineers**: Need proof that SDK integrates correctly with live Asana workspaces

### Impact of Not Solving

- **Silent regressions**: SDK changes may break functionality without detection
- **Onboarding friction**: New developers must discover patterns through trial-and-error
- **Integration risk**: Production deployments may fail due to untested edge cases
- **Documentation drift**: Written docs may not reflect actual SDK behavior

---

## Goals & Success Metrics

### Primary Goals

1. **Validate all 10 SDK operation categories** against real Asana data
2. **Demonstrate idiomatic SDK usage patterns** through executable code
3. **Ensure reversibility** - demo must not leave permanent changes
4. **Enable interactive exploration** with user confirmation at each step

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Operation coverage | 100% of 10 categories | All demo categories execute successfully |
| State restoration | 100% accuracy | All entities return to initial state after demo |
| Interactive confirmation | Every mutation | No blind writes; user approves each operation |
| Documentation coverage | All patterns shown | Each SDK capability has executable example |
| Execution reliability | >95% success rate | Demo completes without crashes on repeated runs |

---

## Scope

### In Scope

**Demo Script Suite**:
- Main demo script (`demo_sdk_operations.py`) covering all 10 operation categories
- Shared utility module (`_demo_utils.py`) for name resolution, state management, logging
- Business model traversal demo (`demo_business_model.py`) - secondary deliverable

**Operation Categories**:
1. Tag operations (add/remove)
2. Dependency operations (add/remove dependency and dependent)
3. Description modifications (set/update/clear notes)
4. String custom field (set/update/clear)
5. People custom field (change/clear/restore)
6. Enum custom field (change/clear/restore)
7. Number custom field (set/update/clear)
8. Multi-enum custom field (add/replace/remove values)
9. Subtask operations (remove/add/reorder)
10. Membership operations (section change/remove/add)

**Supporting Features**:
- Name-to-GID resolution for tags, users, enum options, sections, projects
- State capture and restoration
- Interactive confirmation flow with preview
- Verbose operation logging
- Graceful error handling with rollback guidance

### Out of Scope

- **Automated test suite**: This is interactive demo, not CI/CD tests
- **Performance benchmarking**: Focus is correctness, not speed optimization
- **Multi-workspace support**: Single workspace demonstration only
- **OAuth flows**: Uses existing PAT authentication
- **Custom field creation**: Assumes fields already exist in Asana
- **Webhook demonstrations**: Not part of SaveSession scope
- **Attachment operations**: Not implemented in current SDK

---

## User Stories / Use Cases

### US-1: SDK Developer Validates New Feature

> As an SDK developer, I want to run the demo suite after making changes so that I can verify existing functionality still works correctly.

**Acceptance**: Demo runs end-to-end without errors after SDK modification.

### US-2: New Team Member Learns SDK Patterns

> As a new team member, I want to step through the demo interactively so that I can learn how SaveSession, action operations, and custom fields work.

**Acceptance**: Each step displays clear explanation of what will happen and why.

### US-3: QA Engineer Validates Releases

> As a QA engineer, I want to execute the demo against our test workspace before releases so that I can confirm SDK operations work with real Asana data.

**Acceptance**: Demo provides clear pass/fail indication for each operation category.

### US-4: Integration Engineer Troubleshoots Issues

> As an integration engineer, I want verbose logging of each operation so that I can diagnose issues when operations fail.

**Acceptance**: Logs show request/response details, GID resolutions, and error messages.

---

## Functional Requirements

### FR-TAG: Tag Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-TAG-001 | Demo shall add a tag to the Business task using `session.add_tag()` | Must | Tag appears on task in Asana UI after commit |
| FR-TAG-002 | Demo shall confirm tag addition before committing | Must | User sees preview and approves before API call |
| FR-TAG-003 | Demo shall remove the previously added tag using `session.remove_tag()` | Must | Tag no longer appears on task after commit |
| FR-TAG-004 | Demo shall resolve tag by name ("optimize") to GID | Must | Tag GID resolved without hardcoding |
| FR-TAG-005 | Demo shall handle missing tag gracefully | Should | Prompt user to create tag if not found |

### FR-DEP: Dependency and Dependent Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEP-001 | Demo shall add a dependent task using `session.add_dependent()` | Must | Dependent relationship visible in Asana |
| FR-DEP-002 | Demo shall remove the dependent using `session.remove_dependent()` | Must | Dependent relationship removed |
| FR-DEP-003 | Demo shall add a dependency using `session.add_dependency()` | Must | Dependency relationship visible in Asana |
| FR-DEP-004 | Demo shall remove the dependency using `session.remove_dependency()` | Must | Dependency relationship removed |
| FR-DEP-005 | Demo shall confirm each dependency operation before commit | Must | User preview and approval required |
| FR-DEP-006 | Demo shall restore original dependency state at completion | Must | Business task has same dependencies as before demo |

### FR-DESC: Description (Notes) Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DESC-001 | Demo shall set task notes to a test value | Must | Notes field updated in Asana |
| FR-DESC-002 | Demo shall update task notes to a different value | Must | Notes show new value in Asana |
| FR-DESC-003 | Demo shall clear task notes by setting to empty/None | Must | Notes field empty in Asana |
| FR-DESC-004 | Demo shall restore original notes value at completion | Must | Notes match initial captured state |
| FR-DESC-005 | Demo shall track notes changes via SaveSession | Must | Change detection works correctly |

### FR-CF-STR: String Custom Field Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CF-STR-001 | Demo shall set a string custom field to a test value | Must | Field shows test value in Asana |
| FR-CF-STR-002 | Demo shall update the string field to a different value | Must | Field shows new value in Asana |
| FR-CF-STR-003 | Demo shall clear the string field by setting to None | Must | Field shows empty in Asana |
| FR-CF-STR-004 | Demo shall use `CustomFieldAccessor.set()` with field name | Must | Name-to-GID resolution works |
| FR-CF-STR-005 | Demo shall restore original field value at completion | Must | Field matches initial state |

### FR-CF-PPL: People Custom Field Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CF-PPL-001 | Demo shall change a people field to a different user | Must | Field shows new user in Asana |
| FR-CF-PPL-002 | Demo shall clear the people field | Must | Field shows no user in Asana |
| FR-CF-PPL-003 | Demo shall restore the original user assignment | Must | Field matches initial state |
| FR-CF-PPL-004 | Demo shall resolve user by display name to GID | Must | User GID resolved without hardcoding |
| FR-CF-PPL-005 | Demo shall handle user not found gracefully | Should | Clear error message if user doesn't exist |

### FR-CF-ENM: Enum Custom Field Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CF-ENM-001 | Demo shall change an enum field to a different option | Must | Field shows new option in Asana |
| FR-CF-ENM-002 | Demo shall clear the enum field | Must | Field shows no selection in Asana |
| FR-CF-ENM-003 | Demo shall restore the original enum selection | Must | Field matches initial state |
| FR-CF-ENM-004 | Demo shall resolve enum option by name to GID | Must | Option GID resolved without hardcoding |
| FR-CF-ENM-005 | Demo shall display available enum options to user | Should | User can see valid choices |

### FR-CF-NUM: Number Custom Field Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CF-NUM-001 | Demo shall set a number field to a test value | Must | Field shows test number in Asana |
| FR-CF-NUM-002 | Demo shall update the number field to a different value | Must | Field shows new number in Asana |
| FR-CF-NUM-003 | Demo shall clear the number field | Must | Field shows empty in Asana |
| FR-CF-NUM-004 | Demo shall restore original number value at completion | Must | Field matches initial state |

### FR-CF-MEN: Multi-Enum Custom Field Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CF-MEN-001 | Demo shall set multi-enum to a single value | Must | Field shows single option in Asana |
| FR-CF-MEN-002 | Demo shall replace multi-enum with multiple values | Must | Field shows all specified options |
| FR-CF-MEN-003 | Demo shall remove one value (keeping others) | Must | Removed option no longer selected |
| FR-CF-MEN-004 | Demo shall clear all multi-enum values | Must | Field shows no selections in Asana |
| FR-CF-MEN-005 | Demo shall restore original multi-enum state | Must | Field matches initial selection set |
| FR-CF-MEN-006 | Demo shall document replace-all semantics | Must | User understands set replaces, doesn't merge |

### FR-SUB: Subtask Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SUB-001 | Demo shall remove subtask from parent using `session.set_parent(task, None)` | Must | Task promoted to top-level in Asana |
| FR-SUB-002 | Demo shall re-add task as subtask using `session.set_parent(task, parent)` | Must | Task appears as subtask in Asana |
| FR-SUB-003 | Demo shall reorder subtask to end using `session.reorder_subtask(insert_after=last)` | Must | Subtask moves to bottom position |
| FR-SUB-004 | Demo shall reorder subtask to beginning using `session.reorder_subtask(insert_before=first)` | Must | Subtask moves to top position |
| FR-SUB-005 | Demo shall restore original subtask parent and position | Must | Subtask hierarchy matches initial state |
| FR-SUB-006 | Demo shall enumerate sibling subtasks for positioning | Must | Can identify first/last siblings |

### FR-MEM: Membership Operations

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-MEM-001 | Demo shall move task to different section using `session.move_to_section()` | Must | Task appears in new section in Asana |
| FR-MEM-002 | Demo shall remove task from project using `session.remove_from_project()` | Must | Task no longer in project |
| FR-MEM-003 | Demo shall add task back to project using `session.add_to_project()` | Must | Task appears in project again |
| FR-MEM-004 | Demo shall restore task to original section | Must | Task in same section as before demo |
| FR-MEM-005 | Demo shall resolve section by name to GID | Must | Section GID resolved without hardcoding |
| FR-MEM-006 | Demo shall resolve project by name to GID | Should | Project GID resolved without hardcoding |

---

## Cross-Cutting Requirements

### FR-INT: Interactivity

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-INT-001 | Demo shall use `session.preview()` before every commit | Must | User sees planned operations before execution |
| FR-INT-002 | Demo shall prompt user with Enter/s/q controls | Must | Enter=execute, s=skip, q=quit available |
| FR-INT-003 | Demo shall display operation details in preview | Must | Shows operation type, entity, target GID |
| FR-INT-004 | Demo shall allow skipping any individual operation | Should | User can skip without aborting entire demo |
| FR-INT-005 | Demo shall allow quitting at any point | Must | Clean exit with partial state restoration |
| FR-INT-006 | Demo shall display CRUD and Action operations separately in preview | Must | Per `session.preview()` return format |

### FR-REST: State Restoration

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-REST-001 | Demo shall capture initial state of all entities at startup | Must | State snapshot taken before any modifications |
| FR-REST-002 | Demo shall track current state after each successful operation | Must | State manager updated on commit success |
| FR-REST-003 | Demo shall restore all entities to initial state at completion | Must | All modified fields return to original values |
| FR-REST-004 | Demo shall verify restoration success | Must | Post-restore fetch confirms state matches |
| FR-REST-005 | Demo shall handle partial failure during restoration | Must | Report which entities could not be restored |
| FR-REST-006 | State capture shall include: notes, custom_fields, tags, parent, memberships | Must | All demo-modified fields captured |

### FR-RES: Name Resolution

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-RES-001 | Demo shall resolve tag names to GIDs via workspace lookup | Must | No hardcoded tag GIDs |
| FR-RES-002 | Demo shall resolve user display names to GIDs via workspace lookup | Must | No hardcoded user GIDs |
| FR-RES-003 | Demo shall resolve enum option names to GIDs via field definition | Must | No hardcoded option GIDs |
| FR-RES-004 | Demo shall resolve section names to GIDs via project lookup | Must | No hardcoded section GIDs |
| FR-RES-005 | Demo shall cache resolved GIDs for reuse within session | Should | Avoid redundant API calls |
| FR-RES-006 | Demo shall provide clear error when resolution fails | Must | User knows why name lookup failed |

---

## Non-Functional Requirements

### NFR-PERF: Performance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Single operation latency | < 2 seconds | Time from user confirmation to completion |
| NFR-PERF-002 | Batch operation latency | < 5 seconds per batch | Time for 10-operation batch |
| NFR-PERF-003 | State restoration time | < 30 seconds total | Time to restore all demo entities |
| NFR-PERF-004 | Name resolution latency | < 3 seconds per type | First lookup for tags/users/sections |
| NFR-PERF-005 | Memory usage | < 100 MB | Peak memory during full demo run |

### NFR-USE: Usability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-USE-001 | Clear operation descriptions | Every operation | User understands what will happen |
| NFR-USE-002 | Consistent prompt format | All interactions | Same Enter/s/q pattern throughout |
| NFR-USE-003 | Progress indication | Category level | User knows which demo category is active |
| NFR-USE-004 | Error messages | Human readable | Actionable guidance on failures |
| NFR-USE-005 | Help text | On demand | User can see available commands |

### NFR-REL: Reliability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-REL-001 | Execution success rate | > 95% | Demo completes without crashes |
| NFR-REL-002 | Graceful degradation | No orphaned state | Partial failure doesn't corrupt workspace |
| NFR-REL-003 | Rate limit handling | Automatic retry | Demo waits on 429 responses |
| NFR-REL-004 | Network error recovery | User guidance | Clear message on connection failures |
| NFR-REL-005 | Concurrent modification detection | Warning | Alert if entity changed externally |

### NFR-LOG: Logging

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-LOG-001 | Operation logging | All mutations | Every API call logged with details |
| NFR-LOG-002 | GID resolution logging | All lookups | Shows name -> GID mappings |
| NFR-LOG-003 | Error logging | Stack traces | Full context on failures |
| NFR-LOG-004 | State change logging | Before/after | Shows field values changed |
| NFR-LOG-005 | Configurable verbosity | --verbose flag | User can enable detailed output |

---

## Acceptance Criteria Matrix

### Demo Category Completion Criteria

| Category | Operations | Pass Criteria |
|----------|------------|---------------|
| Tags | add_tag, remove_tag | Tag added, confirmed visible, then removed |
| Dependencies | add_dependent, remove_dependent, add_dependency, remove_dependency | All 4 operations execute and reverse |
| Description | set notes, update notes, clear notes | Notes modified through all states, restored |
| String CF | set, update, clear | String field modified through all states, restored |
| People CF | change, clear, restore | User assignment changed and restored |
| Enum CF | change, clear, restore | Enum selection changed and restored |
| Number CF | set, update, clear | Number field modified through all states, restored |
| Multi-Enum CF | set single, set multiple, remove one, clear | Multi-enum manipulated all ways, restored |
| Subtasks | remove parent, add parent, reorder bottom, reorder top | Subtask hierarchy modified and restored |
| Memberships | move section, remove project, add project | Task membership changed and restored |

### Overall Acceptance Criteria

- [ ] All 10 demo categories complete without errors
- [ ] User prompted before every mutating operation
- [ ] All entities return to initial state after demo
- [ ] No hardcoded GIDs (all resolved by name)
- [ ] Demo can be safely interrupted and re-run
- [ ] Clear progress indication throughout
- [ ] Verbose mode provides detailed operation logging

---

## Test Data Requirements

### Primary Entities

| Entity | GID | Purpose | Required State |
|--------|-----|---------|----------------|
| Business | `1203504488813198` | All field demos | Must exist with custom fields populated |
| Unit | `1203504489143268` | Multi-enum demo | Must have "Disabled Questions" field |
| Dependency Task | `1211596978294356` | Dependency demo | Must exist in same workspace |
| Subtask | `1203996810236966` | Subtask demo | Must be subtask of Reconciliation Holder |
| Reconciliation Holder | `1203504488912317` | Parent task | Must have multiple subtasks |

### Required Resources

| Resource | Name | Purpose |
|----------|------|---------|
| Tag | "optimize" | Tag operations demo (create if missing) |
| Project | "Businesses" | Membership operations demo |
| Sections | Multiple | Section movement demo |
| Users | At least 2 | People field demo |

### Pre-Flight Verification

Demo shall verify at startup:
1. All entity GIDs are accessible
2. Required custom fields exist on entities
3. Tag exists or can be created
4. User has write permissions
5. Project and sections are accessible

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| SaveSession implementation | SDK Team | Complete | All action methods implemented |
| CustomFieldAccessor | SDK Team | Complete | get/set/remove with name resolution |
| TasksClient | SDK Team | Complete | CRUD and list operations |
| TagsClient | SDK Team | Complete | list_for_workspace for name lookup |
| UsersClient | SDK Team | Complete | list_for_workspace for name lookup |
| SectionsClient | SDK Team | Complete | list_for_project for name lookup |
| Live Asana workspace | Infra | Required | Test entities must exist |
| PAT authentication | User | Required | Valid token with write access |

---

## Assumptions

| Assumption | Basis | Risk if Invalid |
|------------|-------|-----------------|
| Test entity GIDs are stable | Planning document | Demo fails at startup; update GIDs |
| Custom fields exist on entities | Planning document | Demo cannot test CF operations |
| User has write permissions | Standard workspace setup | Operations fail with 403 |
| Network connectivity stable | Development environment | Retries and error handling required |
| Single user running demo | Interactive design | Concurrent runs may conflict |
| Asana API behavior stable | Published API docs | SDK compatibility issues |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test entities deleted | Medium | High | Pre-flight check; fail fast with clear message |
| Tag doesn't exist | High | Low | Offer to create tag with user confirmation |
| Rate limiting | Medium | Medium | Add delays; use SaveResult for retry guidance |
| State restoration fails | Medium | High | Track all modifications; provide manual restore instructions |
| Custom field schema changed | Low | Medium | Fetch current definitions; adapt dynamically |
| Concurrent modifications | Low | High | Capture state; warn if external changes detected |
| Network interruption | Low | Medium | Graceful error handling; resume guidance |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Tag "optimize" existence? | Implementation | Before coding | Check at runtime; create if missing |
| Exact section names? | Implementation | Before coding | Fetch dynamically at startup |
| Which string CF to demo? | Product | PRD Approval | Use "Office Phone" on Business |
| Which enum CF to demo? | Product | PRD Approval | Use "Status" or similar on Business |
| Which number CF to demo? | Product | PRD Approval | Use "MRR" or similar on Business |
| Which people CF to demo? | Product | PRD Approval | Use "Lead Owner" or "Assignee" |

---

## File Deliverables

| File | Purpose | Location |
|------|---------|----------|
| `demo_sdk_operations.py` | Main interactive demo (10 categories) | `scripts/` |
| `_demo_utils.py` | Shared utilities (resolution, state, logging) | `scripts/` |
| `demo_business_model.py` | Business model traversal demo | `scripts/` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Requirements Analyst | Initial draft based on DISCOVERY-SDKDEMO |

---

## Quality Gates Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] Dependencies identified with owners
- [x] Risks documented with mitigations
- [ ] Open questions have owners assigned
- [ ] Stakeholder review complete
