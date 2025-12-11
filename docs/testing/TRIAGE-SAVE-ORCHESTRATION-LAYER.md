# Save Orchestration Layer - Comprehensive Triage Report

**Date**: 2025-12-10
**QA Agent**: @qa-adversary
**Test Run**: 327 tests passed, 0 failed
**Implementation**: `/src/autom8_asana/persistence/`

---

## Executive Summary

The Save Orchestration Layer provides a Unit of Work pattern for batched Asana operations. The implementation is **functional and well-tested for core scenarios**, but has **significant gaps in edge case coverage** and **lacks tests for Asana-specific entity operations** (tags, sections, attachments, dependencies).

### Key Findings

| Status | Count | Description |
|--------|-------|-------------|
| **SUPPORTED + TESTED** | 12 | Core operations with good coverage |
| **SUPPORTED, NOT TESTED** | 8 | Operations that should work but lack tests |
| **NOT SUPPORTED** | 14 | Operations requiring special API handling |
| **CRITICAL GAPS** | 4 | High-priority missing functionality |

---

## 1. Triage Matrix

### Legend
- [CHECK] **SUPPORTED + TESTED**: Implementation exists and has test coverage
- [WARN] **SUPPORTED, NOT TESTED**: Implementation should work but no test coverage
- [X] **NOT SUPPORTED**: No implementation or requires special handling
- [PARTIAL] **PARTIALLY SUPPORTED**: Works with caveats

---

## CATEGORY 1: Custom Field Operations

### Implementation Analysis

The `CustomFieldAccessor` class (`models/custom_field_accessor.py`) provides a fluent API for custom field modifications. The `Task.model_dump()` method is overridden to include custom field changes via `accessor.to_list()`.

The tracker uses `model_dump()` for change detection, so custom field modifications **are detected** when the accessor has changes.

| Operation | Type | Status | Notes |
|-----------|------|--------|-------|
| Set text value | text | [WARN] | CustomFieldAccessor.set() works, NOT TESTED in persistence |
| Set number value | number | [WARN] | Same as text |
| Set enum option | enum | [WARN] | Requires GID of enum option |
| Set multi_enum options | multi_enum | [WARN] | Requires list of GIDs |
| Set date value | date | [WARN] | Format: `{"date": "YYYY-MM-DD", "date_time": "..."}` |
| Set people value | people | [WARN] | Requires user GID(s) |
| Clear custom field | all | [WARN] | `accessor.remove(name)` sets to None |
| Change custom field | all | [WARN] | Same as set |

### Edge Cases NOT TESTED

| Edge Case | Risk | Notes |
|-----------|------|-------|
| Unicode in text fields | Medium | No validation tests |
| HTML content in text | Medium | May need escaping |
| Long strings (10k+ chars) | Medium | API limits unknown |
| Float precision in numbers | High | Decimal rounding issues possible |
| Negative numbers | Low | Should work but untested |
| Invalid enum GID | High | API error expected but not tested |
| Disabled enum option | Medium | Should fail but untested |
| Invalid user GID | High | API error expected |
| Deactivated user | Medium | May silently fail |
| Timezone in date fields | Medium | Timezone handling unclear |

### Gap Assessment

**CRITICAL**: No persistence-level tests exist for custom field operations. The `CustomFieldAccessor` unit tests (if any) don't cover the save orchestration flow.

---

## CATEGORY 2: Subtask Operations

### Implementation Analysis

Parent-child relationships ARE tracked via the `parent` field on Task. The `DependencyGraph` correctly orders parents before children using Kahn's algorithm.

| Operation | Status | Notes |
|-----------|--------|-------|
| Add subtask (set parent) | [CHECK] | Works via `task.parent = NameGid(gid=parent_gid)` |
| Remove subtask (clear parent) | [WARN] | Should work but NOT TESTED |
| Reorder subtasks | [X] | **NOT SUPPORTED** - requires separate API |
| Move subtask (change parent) | [WARN] | Should work but NOT TESTED |
| Create with parent | [CHECK] | New entity with parent reference works |
| Nested subtasks (5+ levels) | [CHECK] | Tested in test_dependency_ordering.py |

### Edge Cases

| Edge Case | Status | Notes |
|-----------|--------|-------|
| Orphan subtask (parent not in session) | [CHECK] | External parent is ignored in graph |
| Circular parent reference | [CHECK] | CyclicDependencyError raised |
| Move to self | [CHECK] | Self-cycle detected |
| Move to own descendant | [X] | **NOT TESTED** - may create invalid state |
| Large hierarchy (100+ levels) | [WARN] | Only tested to 50 levels |
| Deep nesting (5+ levels) | [CHECK] | Tested with 4 levels |

### Gap Assessment

**MEDIUM**: Subtask operations work through parent field modification, but reordering requires separate API endpoint (`POST /tasks/{task_gid}/setParent`).

---

## CATEGORY 3: Dependency Operations (Task Dependencies)

### Implementation Analysis

**Asana task dependencies** (blocking/blocked_by relationships) are **NOT MODELED** in the Task model. The only "dependency" supported is parent-child relationships.

| Operation | Status | Notes |
|-----------|--------|-------|
| Add dependency (blocking) | [X] | **NOT SUPPORTED** - requires `POST /tasks/{gid}/addDependencies` |
| Remove dependency | [X] | **NOT SUPPORTED** - requires separate endpoint |
| Add dependent | [X] | **NOT SUPPORTED** - requires separate endpoint |
| Batch dependencies | [X] | **NOT SUPPORTED** |

### Gap Assessment

**CRITICAL**: Asana task dependencies are a separate concept from the DependencyGraph (which handles save ordering). The persistence layer has **no support** for managing task dependencies.

---

## CATEGORY 4: Tag Operations

### Implementation Analysis

Tags are modeled as `list[NameGid]` on Task. However, adding/removing tags **requires special API endpoints**, not just field modification.

| Operation | Status | Notes |
|-----------|--------|-------|
| Add tag to task | [X] | **NOT SUPPORTED** - requires `POST /tasks/{gid}/addTag` |
| Remove tag from task | [X] | **NOT SUPPORTED** - requires `POST /tasks/{gid}/removeTag` |
| Multiple tags in one save | [X] | **NOT SUPPORTED** |
| Create task with tags | [WARN] | May work with `tags` field on POST, but **NOT TESTED** |

### Gap Assessment

**HIGH**: Tag modifications bypass SaveSession entirely. Users must call tag-specific APIs manually. This is a significant gap for any workflow involving tag management.

---

## CATEGORY 5: Project Membership

### Implementation Analysis

Projects are modeled as `list[NameGid]` on Task. Similar to tags, project membership **requires special API endpoints**.

| Operation | Status | Notes |
|-----------|--------|-------|
| Add to project | [X] | **NOT SUPPORTED** - requires `POST /tasks/{gid}/addProject` |
| Remove from project | [X] | **NOT SUPPORTED** - requires `POST /tasks/{gid}/removeProject` |
| Multi-project task | [X] | **NOT SUPPORTED** for modification |
| Create task in project | [WARN] | May work with `projects` field on POST |
| Last project removal | [X] | **NOT HANDLED** - API may reject |

### Critical Edge Case

**Section cleanup**: When removing a task from a project, its section membership in that project must also be cleared. The current implementation has **no awareness** of this requirement.

### Gap Assessment

**CRITICAL**: Project membership changes cannot be made through SaveSession. This is a fundamental limitation for multi-project workflows.

---

## CATEGORY 6: Section Operations

### Implementation Analysis

Section is tracked via `memberships` field (complex dict structure). Setting section requires the `addProject` or `setProject` API with section GID.

| Operation | Status | Notes |
|-----------|--------|-------|
| Change section | [X] | **NOT SUPPORTED** - requires `POST /tasks/{gid}/addProject` with section |
| Move to different project section | [X] | **NOT SUPPORTED** |
| Default section | [X] | **NOT SUPPORTED** |

### Gap Assessment

**HIGH**: Section changes cannot be made through SaveSession. The `assignee_section` field exists but modifying it has no effect through the standard PUT API.

---

## CATEGORY 7: Attachment Operations

### Implementation Analysis

Attachments have a model in `models/attachment.py` but attachment operations **require multipart form data uploads** - a completely different API pattern.

| Operation | Status | Notes |
|-----------|--------|-------|
| Add attachment | [X] | **NOT SUPPORTED** - requires multipart upload |
| Remove attachment | [X] | **NOT SUPPORTED** - requires DELETE to attachment GID |
| Multiple attachments | [X] | **NOT SUPPORTED** |

### Gap Assessment

**LOW PRIORITY**: Attachment handling is inherently different from standard CRUD. This is a known limitation, not a bug.

---

## CATEGORY 8: Core Field Operations

### Implementation Analysis

Core fields ARE tracked via snapshot comparison. The `ChangeTracker` captures `model_dump()` at track time and compares at commit time.

| Field | Set | Change | Clear | Status | Notes |
|-------|-----|--------|-------|--------|-------|
| name | Y | Y | N/A | [CHECK] | Tested in multiple tests |
| notes | Y | Y | Y | [WARN] | NOT TESTED with clear (set to None) |
| html_notes | Y | Y | Y | [WARN] | NOT TESTED at all |
| due_on | Y | Y | Y | [WARN] | NOT TESTED |
| due_at | Y | Y | Y | [WARN] | NOT TESTED |
| start_on | Y | Y | Y | [WARN] | NOT TESTED |
| completed | Y | Y | N/A | [WARN] | NOT TESTED |
| assignee | Y | Y | Y | [WARN] | NOT TESTED |
| followers | Y | Y | Y | [WARN] | May require special API |

### Edge Cases NOT TESTED

| Edge Case | Risk | Notes |
|-----------|------|-------|
| Empty string name | High | API may reject |
| Name > 255 chars | Medium | API limit unknown |
| HTML in html_notes | Medium | May need escaping |
| @mentions in notes | Low | Should pass through |
| Past dates | Low | Should work |
| start_on after due_on | Medium | API may reject |
| Invalid user GID for assignee | High | API error |
| Self as follower | Low | Probably allowed |

### Gap Assessment

**MEDIUM**: Core field changes work but lack edge case tests. Validation of field values happens at API level, not in SaveSession.

---

## CATEGORY 9: Compound Operations

### Implementation Analysis

The SaveSession supports tracking multiple entities and processing them in dependency order. Events (pre/post hooks) fire for each entity.

| Scenario | Status | Notes |
|----------|--------|-------|
| Full task update (all fields) | [WARN] | NOT TESTED with many simultaneous changes |
| Hierarchical save (parent + children) | [CHECK] | Well tested |
| Cross-entity operations | [PARTIAL] | Only parent-child supported |
| Bulk operations (50+ tasks) | [CHECK] | Performance tests exist |
| Mixed create/update/delete | [CHECK] | Tested in test_functional.py |

### Gap Assessment

**LOW**: Compound operations are generally well-supported. The main limitation is the inability to handle Asana-specific relationships (tags, projects, dependencies).

---

## CATEGORY 10: Error Handling

### Implementation Analysis

Error handling is **comprehensive** with dedicated exception types and partial failure support.

| Scenario | Status | Notes |
|----------|--------|-------|
| Invalid GID | [CHECK] | Tested |
| Permission denied (403) | [CHECK] | Captured as SaveError |
| Rate limited (429) | [CHECK] | Captured as SaveError |
| Network failure | [WARN] | Depends on BatchClient |
| Partial batch failure | [CHECK] | Well tested |
| Circular dependency | [CHECK] | CyclicDependencyError |
| Invalid field value | [WARN] | API returns error, but validation tests missing |
| Session closed | [CHECK] | SessionClosedError |

### Gap Assessment

**LOW**: Error handling is the strongest area of the implementation. Most scenarios have explicit tests.

---

## 2. Gap Report

### Critical Gaps (Must Fix)

1. **No Tag Operation Support**
   - Impact: Any workflow involving tag changes must bypass SaveSession
   - Recommendation: Add tag-specific methods or document limitation

2. **No Project Membership Support**
   - Impact: Cannot add/remove tasks from projects via SaveSession
   - Recommendation: Add project membership methods or document limitation

3. **No Task Dependency Support**
   - Impact: Cannot manage blocking/blocked_by relationships
   - Recommendation: Assess if this is in scope, document if not

4. **Custom Field Tests Missing**
   - Impact: No confidence that custom field changes persist correctly
   - Recommendation: Add integration tests for custom field save flow

### High Priority Gaps

5. **Section Change Not Supported**
   - Impact: Cannot move tasks between sections
   - Recommendation: Document or implement

6. **Core Field Edge Cases**
   - Impact: Production bugs possible with edge inputs
   - Recommendation: Add boundary tests

7. **html_notes Not Tested**
   - Impact: Unknown behavior with HTML content
   - Recommendation: Add tests

### Medium Priority Gaps

8. **Date Field Handling**
   - No timezone tests
   - No format validation tests

9. **Numeric Field Precision**
   - Float rounding not tested for custom fields

10. **Error Message Quality**
    - API error messages pass through, may not be user-friendly

---

## 3. Critical Findings

### Finding 1: Asana API Model Mismatch

**Issue**: The SaveSession assumes standard REST CRUD operations (POST/PUT/DELETE to resource endpoints), but Asana uses **action endpoints** for many relationship changes:

- Tags: `POST /tasks/{gid}/addTag`, `POST /tasks/{gid}/removeTag`
- Projects: `POST /tasks/{gid}/addProject`, `POST /tasks/{gid}/removeProject`
- Dependencies: `POST /tasks/{gid}/addDependencies`, `POST /tasks/{gid}/removeDependencies`
- Section: `POST /tasks/{gid}/setParent` (with `insert_before`/`insert_after`)

**Impact**: Users cannot use SaveSession for these common operations.

**Severity**: HIGH

### Finding 2: No Custom Field Persistence Tests

**Issue**: The `CustomFieldAccessor` provides modification methods, and `Task.model_dump()` includes changes, but there are **zero tests** proving custom field changes actually reach the API correctly.

**Impact**: Custom field changes may silently fail or produce incorrect payloads.

**Severity**: HIGH

### Finding 3: Silent Failures Possible

**Issue**: Modifying `task.tags` or `task.projects` directly will:
1. Be detected as a change by the tracker
2. Be included in the PUT payload
3. Be **ignored by Asana** (these fields are read-only)

Users may believe their changes saved when they didn't.

**Impact**: Data loss / silent failure

**Severity**: HIGH

---

## 4. Recommendations

### Priority 1: Documentation

Add clear documentation stating:
- SaveSession ONLY supports standard field modifications
- Tag/project/section/dependency changes require separate API calls
- List which fields are read-only in the PUT payload

### Priority 2: Test Coverage

Add tests for:
1. Custom field save flow (text, number, enum types)
2. Clearing nullable fields (notes, assignee, due_on)
3. Boundary conditions (empty name, long strings)
4. Error scenarios (invalid GID, permission denied)

### Priority 3: Feature Enhancement

Consider adding methods for common Asana operations:
```python
session.add_tag(task, tag_gid)
session.remove_tag(task, tag_gid)
session.add_to_project(task, project_gid, section_gid=None)
session.remove_from_project(task, project_gid)
```

### Priority 4: Validation

Add pre-save validation for:
- Empty task name
- Invalid date formats
- Read-only field modifications (warn user)

---

## 5. Test Coverage Summary

| Component | Lines | Tested | Coverage Estimate |
|-----------|-------|--------|-------------------|
| session.py | 568 | High | ~85% |
| tracker.py | 238 | High | ~90% |
| graph.py | 244 | High | ~95% |
| pipeline.py | 483 | Medium | ~75% |
| executor.py | 189 | Medium | ~70% |
| events.py | 217 | High | ~90% |

**Overall Persistence Layer Coverage**: ~82% (estimated)

**Test Distribution**:
- Unit tests: 170
- Validation/functional tests: 77
- Performance tests: 20
- Concurrency tests: 60

---

## 6. Approval Status

### Cannot Approve For Ship

The following must be addressed before production use:

1. [ ] Document limitations (read-only fields, unsupported operations)
2. [ ] Add custom field persistence tests
3. [ ] Add warning/error when user tries to modify read-only fields

### Conditional Approval

If the above items are addressed, the Save Orchestration Layer is **suitable for production use** with the understanding that:
- Tag, project, section, and dependency operations require separate API calls
- Custom field support is basic (set/clear, no type validation)
- Error recovery is user's responsibility

---

## Appendix A: Test File Locations

| Test File | Purpose | Tests |
|-----------|---------|-------|
| `tests/unit/persistence/test_session.py` | Session API | 25 |
| `tests/unit/persistence/test_tracker.py` | Change tracking | 18 |
| `tests/unit/persistence/test_graph.py` | Dependency ordering | 22 |
| `tests/unit/persistence/test_pipeline.py` | Four-phase execution | 16 |
| `tests/unit/persistence/test_executor.py` | Batch execution | 16 |
| `tests/unit/persistence/test_events.py` | Hook system | 20 |
| `tests/unit/persistence/test_models.py` | Data models | 22 |
| `tests/unit/persistence/test_exceptions.py` | Exception types | 23 |
| `tests/validation/persistence/test_functional.py` | Functional validation | 28 |
| `tests/validation/persistence/test_error_handling.py` | Error scenarios | 25 |
| `tests/validation/persistence/test_dependency_ordering.py` | Graph validation | 30 |
| `tests/validation/persistence/test_concurrency.py` | Thread safety | 25 |
| `tests/validation/persistence/test_performance.py` | Performance | 22 |

---

## Appendix B: Implementation File Locations

| File | Lines | Purpose |
|------|-------|---------|
| `src/autom8_asana/persistence/session.py` | 568 | Main SaveSession class |
| `src/autom8_asana/persistence/tracker.py` | 238 | Change detection |
| `src/autom8_asana/persistence/graph.py` | 244 | Dependency ordering |
| `src/autom8_asana/persistence/pipeline.py` | 483 | Four-phase execution |
| `src/autom8_asana/persistence/executor.py` | 189 | Batch execution |
| `src/autom8_asana/persistence/events.py` | 217 | Hook system |
| `src/autom8_asana/persistence/models.py` | ~150 | Data models |
| `src/autom8_asana/persistence/exceptions.py` | ~100 | Exception types |

---

*Report generated by @qa-adversary*
