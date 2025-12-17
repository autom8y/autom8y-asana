# DISCOVERY-RESOLUTION-001: Cross-Holder Relationship Resolution

> **Status**: COMPLETE
> **Date**: 2025-12-16
> **Initiative**: Cross-Holder Relationship Resolution
> **Recommendation**: **GO**

---

## Executive Summary

This discovery validates the Cross-Holder Relationship Resolution initiative. User-provided answers confirm high use case frequency, clear infrastructure requirements, and a well-defined scope. The initiative should proceed to Requirements (Session 2).

---

## Discovery Questions - Findings

### 1. How frequently is cross-holder resolution needed?

**Finding**: **VERY HIGH FREQUENCY**

User confirmation:
> "VERY OFTEN, and also very often in collections. For example, in custom field models these relationships are encoded: when you get `offer.office_phone`, you also load `business.office_phone`. It's incredibly common and often done in threaded access and async methods or batch operations like 'get all office phones of active offers'."

**Impact**: This strongly validates the investment. Cross-holder resolution is not an edge case but a core workflow pattern.

**Implication**: Batch resolution should be considered in initial scope (promoted from "Could" to "Should").

---

### 2. What TasksClient capabilities exist for fetching dependents?

**Finding**: **API EXISTS, SDK METHOD NEEDED**

Asana API provides:
- **Endpoint**: `GET /tasks/{task_gid}/dependents`
- **Scope**: `tasks:read`
- **Returns**: Compact task representations of all dependents
- **Limit**: Tasks can have at most 30 dependents and dependencies combined
- **Pagination**: Standard Asana pagination (offset-based)

**Current SDK State**:
- `TasksClient.subtasks_async()` exists (PageIterator pattern)
- `TasksClient.dependents_async()` does **NOT** exist
- `SaveSession.add_dependent/remove_dependent` exist (write operations only)

**Required Work**: Add `dependents_async()` method to TasksClient following the same pattern as `subtasks_async()`.

**Effort Estimate**: Small (1-2 hours) - follows established pattern.

---

### 3. Is AssetEdit typing a prerequisite?

**Finding**: **YES - PREREQUISITE CONFIRMED**

User provided legacy model definition:

```python
class AssetEdit(Process):
    ASANA_FIELDS = {
        "asset_approval": AssetApproval,
        "asset_id": AssetId,
        "editor": Editor,
        "reviewer": Reviewer,
        "offer_id": OfferId,      # <-- Key for EXPLICIT_OFFER_ID strategy
        "raw_assets": RawAssets,
        "review_all_ads": ReviewAllAds,
        "score": Score,
        "specialty": SpecialtyField,
        "template_id": TemplateId,
        "videos_paid": VideosPaid,
    }
```

**Impact on Phasing**:
1. AssetEdit must be typed before resolution methods can be added to it
2. AssetEdit extends `Process` (not `Task`) - follows existing pattern
3. `offer_id` field is present - enables EXPLICIT_OFFER_ID strategy

**Required Work**:
- Create `AssetEdit` entity class extending `Process`
- Add typed field accessors for 11 custom fields
- Update `AssetEditHolder` to return `AssetEdit` children (currently returns `Task`)
- Add `EntityType.ASSET_EDIT` to detection module

---

### 4. What resolution strategies are actually needed?

**Finding**: **FOUR STRATEGIES CONFIRMED**

| Strategy | Description | Priority | Feasibility |
|----------|-------------|----------|-------------|
| DEPENDENT_TASKS | Process tasks have dependents pointing to Unit | 1 | Feasible - API exists |
| CUSTOM_FIELD_MAPPING | Vertical field matches Unit.vertical | 2 | Feasible - CustomFieldAccessor exists |
| EXPLICIT_OFFER_ID | Read offer_id field directly from AssetEdit | 3 | Feasible - field exists in legacy model |
| AUTO | Try strategies in priority order | Default | Composition of above |

**Note**: Priority ordering may need validation against real data in Architecture phase.

---

### 5. What are the edge cases for ambiguity?

**Finding**: **DEFERRED TO QA SESSION**

Per user request: "Evaluate in the workflow and ensure coverage in QA session."

**Preliminary Edge Cases Identified**:
1. No matches found (resolution fails)
2. Multiple Units match via CUSTOM_FIELD_MAPPING
3. Dependent task points to non-Unit entity
4. EXPLICIT_OFFER_ID value is stale/invalid
5. Circular resolution attempts
6. AssetEdit not in AssetEditHolder context

**Architecture Impact**: Design must support ambiguity reporting. QA must validate handling.

---

## Infrastructure Audit Summary

| Component | Status | Action Required |
|-----------|--------|-----------------|
| AssetEditHolder | Exists (stub) | Update to return AssetEdit children |
| AssetEdit entity | Does not exist | Create with 11 typed fields |
| TasksClient.dependents_async() | Does not exist | Add method (follows subtasks pattern) |
| CustomFieldAccessor | Exists | No changes needed |
| EntityType enum | Exists | Add ASSET_EDIT variant |
| Detection module | Exists | Add AssetEdit detection |
| SaveSession | Exists | May need resolution integration |

---

## Scope Recommendation

### In Scope (Phase 1)

1. **AssetEdit Entity Typing**
   - Create `AssetEdit(Process)` class
   - 11 typed field accessors
   - Update `AssetEditHolder` to return typed children

2. **TasksClient.dependents_async()**
   - Add method following `subtasks_async()` pattern
   - Returns `PageIterator[Task]`

3. **Resolution Framework**
   - Strategy pattern with priority ordering
   - Result type with strategy transparency
   - Ambiguity handling (configurable or fixed)

4. **Resolution Methods**
   - `AssetEdit.resolve_unit_async()` -> Unit | None
   - `AssetEdit.resolve_offer_async()` -> Offer | None
   - Strategy selection (AUTO, explicit)

### In Scope (Consider for Phase 1 based on frequency)

5. **Batch Resolution**
   - Given high frequency, consider batch operations
   - `resolve_units_async(asset_edits: list[AssetEdit])` -> dict[str, Unit]
   - Architecture to assess trade-offs

### Out of Scope

- Improving existing hierarchical fast-paths (already work)
- Other process type resolutions (future initiative)
- Resolution caching (different semantics - defer)
- Bidirectional resolution (Unit -> AssetEdits)

---

## Risk Assessment Update

| Risk | Pre-Discovery | Post-Discovery | Notes |
|------|---------------|----------------|-------|
| Use case frequency insufficient | Medium | **ELIMINATED** | User confirmed very high frequency |
| TasksClient capability gap | Medium | **LOW** | API exists, method is small addition |
| AssetEdit typing blocker | Low-Medium | **CONFIRMED** | Now a known prerequisite |
| Resolution ambiguity | Medium | **MEDIUM** | Deferred to Architecture/QA |
| Domain logic brittleness | Medium | **MEDIUM** | Strategies well-defined |

---

## Go/No-Go Recommendation

### Recommendation: **GO**

**Rationale**:
1. **Use case validated**: Very high frequency, core workflow pattern
2. **Infrastructure feasible**: All required capabilities exist or are small additions
3. **Scope clear**: Four well-defined strategies, clear resolution targets
4. **Prerequisites identified**: AssetEdit typing is known prerequisite
5. **Risk manageable**: No blocking risks, ambiguity handling deferred appropriately

### Conditions Met

- [x] Use case frequency justifies investment
- [x] TasksClient capabilities identified (API exists, method to add)
- [x] AssetEdit typing dependency clarified (prerequisite)
- [x] Resolution strategies validated
- [x] Edge cases identified (deferred to QA per user)

---

## Session Plan Update

Based on Discovery findings, recommended session structure:

| Session | Agent | Deliverable | Notes |
|---------|-------|-------------|-------|
| 2: Requirements | @requirements-analyst | PRD-RESOLUTION | Include batch operations as "Should" |
| 3: Architecture | @architect | TDD-RESOLUTION + ADRs | Strategy pattern, ambiguity handling, batch design |
| 4: Implementation P1 | @principal-engineer | AssetEdit typing + dependents_async() | Prerequisites first |
| 5: Implementation P2 | @principal-engineer | Resolution framework + strategies | Core resolution |
| 6: Validation | @qa-adversary | Validation report | Ambiguity edge cases critical |

**Note**: Sessions 4+5 may merge if scope is smaller than expected after Architecture.

---

## References

- [Asana API: Get dependents from a task](https://developers.asana.com/reference/getdependentsfortask)
- [Asana API: Set dependents for a task](https://developers.asana.com/reference/adddependentsfortask)
- [PROMPT-0-RELATIONSHIP-RESOLUTION.md](../initiatives/PROMPT-0-RELATIONSHIP-RESOLUTION.md)
- [PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md](../initiatives/PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md)

---

*Discovery complete. Initiative approved to proceed to Session 2: Requirements.*
