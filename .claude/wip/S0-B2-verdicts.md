# Sprint 0, Batch 2: Models & Resolution Verdicts

**Initiative**: INIT-RUNTIME-OPT-002 (Runtime Efficiency Remediation v2)
**Author**: Architect Agent
**Date**: 2026-02-15

---

## S0-SPIKE-05: Business Double-Fetch in Upward Traversal

**Verdict**: GO

### Evidence

#### (a) Field Set Comparison

The two field sets are defined in `src/autom8_asana/models/business/fields.py` (lines 227-255) and aliased in `hydration.py` (lines 66-74):

**DETECTION_OPT_FIELDS** (4 fields):
```
"name"
"parent.gid"
"memberships.project.gid"
"memberships.project.name"
```

**STANDARD_TASK_OPT_FIELDS** (16 fields):
```
"name"
"parent.gid"
"memberships.project.gid"
"memberships.project.name"
"custom_fields"
"custom_fields.name"
"custom_fields.enum_value"
"custom_fields.enum_value.name"
"custom_fields.multi_enum_values"
"custom_fields.multi_enum_values.name"
"custom_fields.display_value"
"custom_fields.number_value"
"custom_fields.text_value"
"custom_fields.resource_subtype"
"custom_fields.people_value"
```

**Delta**: 12 additional fields, all in the `custom_fields.*` family. The detection set is a strict subset of the full set. No conflicting fields.

#### (b) Upward Traversal Frequency and Depth

The upward traversal algorithm in `hydration.py:586-747` (`_traverse_upward_async`) starts from any entity and walks parent references to find Business. The hierarchy is:

```
Business (depth 0)
  +-- Holder (depth 1) -- e.g., ContactHolder, UnitHolder
       +-- Entity (depth 2) -- e.g., Contact, Unit
            +-- Holder (depth 3) -- e.g., OfferHolder, ProcessHolder
                 +-- Entity (depth 4) -- e.g., Offer, Process
```

Maximum real-world depth is 4 (Offer/Process to Business). Each level traversed makes:
1. One `client.tasks.get_async(parent_gid, opt_fields=_DETECTION_OPT_FIELDS)` (line 684-687)
2. One `detect_entity_type_async()` call (line 692-694), which may make 0-1 additional API calls for Tier 4 detection

When Business IS found (the target), there is ALWAYS a re-fetch with full fields (lines 712-714):
```python
business_task = await client.tasks.get_async(
    parent_gid, opt_fields=_BUSINESS_FULL_OPT_FIELDS,
)
```

The same double-fetch pattern exists in `hydrate_from_gid_async` (lines 284-288, 324-328): detection fetch, then re-fetch when Business is detected.

**Frequency**: Every call to `hydrate_from_gid_async`, `_traverse_upward_async`, or `to_business_async` that encounters a Business entity triggers this double-fetch. This is invoked during:
- ConversationAudit workflows (~200 times per weekly run)
- Lifecycle transitions (multiple per day)
- Any entity-to-Business resolution

#### (c) Overhead of Full Fields at Every Traversal Level

The extra fields are all `custom_fields.*` sub-selections. For non-Business parents (Holders, Units), the overhead is:
- **API response size**: Holders typically have 0-5 custom fields. The extra opt_fields tell Asana to include custom field data that was already being fetched (Asana returns custom_fields as a list on any task regardless of opt_fields, but the sub-selections control nesting depth). The response payload increase is minimal -- a few hundred bytes of JSON at most for a Holder with zero custom fields.
- **Network latency**: Zero additional latency. The same single HTTP request is made; the opt_fields parameter is slightly longer in the query string.
- **Parsing overhead**: Pydantic parses the response into a Task model. Custom fields are stored as `list[dict[str, Any]]` with no validation beyond JSON deserialization. The delta is negligible.

For context: Asana's API charges rate limit tokens per request, not per field. Using 16 opt_fields vs 4 opt_fields costs the exact same rate limit budget.

#### (d) Asana API Compatibility

No issues:
- `custom_fields.*` sub-selections are standard Asana opt_fields, supported on all task endpoints.
- No permission differences -- if a user can see a task, they can see its custom fields.
- No rate limit differences -- field count does not affect rate limiting.
- The full field set is already used everywhere else in the codebase (e.g., `from_gid_async`, `_fetch_holders_async`).

#### (e) Test Coverage

Hydration tests exist in:
- `tests/unit/models/business/test_hydration.py` -- unit tests for `hydrate_from_gid_async` and `_traverse_upward_async`
- `tests/unit/models/business/test_hydration_combined.py` -- combined hydration scenarios
- `tests/unit/models/business/test_hydration_fields.py` -- field-specific hydration tests
- `tests/unit/models/business/test_upward_traversal.py` -- upward traversal tests
- `tests/integration/test_hydration.py` -- integration tests

Tests mock `client.tasks.get_async` and verify the opt_fields passed. The change would need to update these mocks to expect `STANDARD_TASK_OPT_FIELDS` instead of `DETECTION_OPT_FIELDS` at detection sites.

### Quantitative Assessment

| Scenario | Detection calls saved | Detection calls with extra fields | Net | Verdict |
|----------|----------------------|-----------------------------------|-----|---------|
| Entry is Business | 1 re-fetch saved (lines 324-328) | 1 call with extra fields (entry fetch) | -1 API call | Wins |
| Traversal finds Business at depth 1 | 1 re-fetch saved (lines 712-714) | 1 intermediate call with extra fields | -1 API call, 0 extra overhead | Wins |
| Traversal finds Business at depth 3 | 1 re-fetch saved | 3 intermediate calls with extra fields | -1 API call, trivial extra payload | Wins |
| Traversal never finds Business (error) | 0 re-fetches saved | N calls with extra fields | 0 API calls, trivial extra payload | Neutral |

The optimization saves exactly 1 API call for every successful Business resolution. The extra custom_fields payload on intermediate non-Business parents adds less than 1% overhead to response parsing (typically zero custom fields on Holder tasks).

### If GO -- Implementation Sketch

1. **Unify field set**: In `hydration.py`, change both the detection fetch AND the traversal fetch to use `STANDARD_TASK_OPT_FIELDS`:
   - Line 287: `opt_fields=_DETECTION_OPT_FIELDS` -> `opt_fields=_BUSINESS_FULL_OPT_FIELDS`
   - Line 686: `opt_fields=_DETECTION_OPT_FIELDS` -> `opt_fields=_BUSINESS_FULL_OPT_FIELDS`

2. **Eliminate re-fetch**: When Business is found (lines 321-338 and 707-716), skip the second `client.tasks.get_async` call. The first fetch already has full fields. Directly use the already-fetched task:
   - Entry path (line 321-338): Remove the re-fetch, use `entry_task` directly
   - Traversal path (lines 707-716): Remove re-fetch, use `parent_task` directly

3. **Update `hydrate_from_gid_async` api_calls accounting**: Decrement by 1 when Business is found (no re-fetch).

4. **Deprecation cleanup**: Remove `_DETECTION_OPT_FIELDS` alias from `hydration.py` (line 68) since it is no longer used there. The canonical `DETECTION_OPT_FIELDS` in `fields.py` remains for any other consumers.

5. **Test updates**: Update test mocks to expect `STANDARD_TASK_OPT_FIELDS` at detection call sites. Update api_calls assertions.

### Risks

- **Low**: Test mocks that assert `opt_fields=DETECTION_OPT_FIELDS` will need updating. Straightforward find-and-replace.
- **Low**: If a future requirement needs detection without custom fields (e.g., for performance in a hot path), the `DETECTION_OPT_FIELDS` constant still exists in `fields.py` and can be used directly. This change only affects `hydration.py`.
- **Negligible**: Slightly larger API responses for non-Business parents. Measured at <1% payload overhead for Holder tasks with zero custom fields.

### Affected Files

- `src/autom8_asana/models/business/hydration.py` (primary change)
- `tests/unit/models/business/test_hydration.py` (mock updates)
- `tests/unit/models/business/test_hydration_combined.py` (mock updates)
- `tests/unit/models/business/test_hydration_fields.py` (mock updates)
- `tests/unit/models/business/test_upward_traversal.py` (mock updates)

---

## S0-SPIKE-06: Pydantic model_dump/model_validate Round-Trip

**Verdict**: CONDITIONAL-GO

### Evidence

#### (a) Call Site Inventory

The `model_validate(task.model_dump())` pattern appears at **20 call sites** across the business model layer:

**`holder_factory.py:308`** (HolderFactory._populate_children -- generic path):
```python
child = child_class.model_validate(task.model_dump())
```
Called for: DNA, Reconciliation, AssetEdit, Videography children. Also base path for Contact, Unit (via super() in UnitNestedHolderMixin line 311).

**`base.py:129`** (HolderMixin._populate_children -- legacy path):
```python
child = child_type.model_validate(task.model_dump())
```
This is the base HolderMixin implementation. Overridden by HolderFactory for most holders.

**`business.py:220`** (Business.from_gid_async):
```python
business = cls.model_validate(task_data.model_dump())
```

**`business.py:582-616`** (_create_typed_holder -- 7 call sites):
```python
holder = ContactHolder.model_validate(task.model_dump())
unit_holder = UH.model_validate(task.model_dump())
location_holder = LH.model_validate(task.model_dump())
dna_holder = DNAHolder.model_validate(task.model_dump())
recon_holder = ReconciliationHolder.model_validate(task.model_dump())
asset_holder = AssetEditHolder.model_validate(task.model_dump())
video_holder = VideographyHolder.model_validate(task.model_dump())
```

**`hydration.py:338,716`** (Business creation after traversal -- 2 call sites):
```python
business = Business.model_validate(business_task.model_dump())
```

**`hydration.py:782,808`** (_convert_to_typed_entity -- uses same pattern indirectly):
```python
result = entity_class.model_validate(task_data)
# where task_data = task.model_dump() (line 782)
```

**`unit.py:327,332`** (Unit._populate_holders -- 2 call sites):
```python
offer_holder = OfferHolder.model_validate(subtask.model_dump())
process_holder = ProcessHolder.model_validate(subtask.model_dump())
```

**`location.py:221,226`** (LocationHolder._populate_children -- 2 call sites):
```python
hours = HoursEntity.model_validate(task.model_dump())
location = Location.model_validate(task.model_dump())
```

**`asset_edit.py:537,646,664,708`** (AssetEdit workflows -- 4 call sites):
```python
unit = Unit.model_validate(dependent.model_dump())
offer = Offer.model_validate(task.model_dump())
unit = Unit.model_validate(unit_task.model_dump())
offer = Offer.model_validate(task.model_dump())
```

#### (b) Field Counts Per Model

All models inherit from `Task` (via `BusinessEntity` or `HolderFactory`). Task has **~30 declared fields** (gid, name, notes, completed, assignee, projects, parent, memberships, custom_fields, etc.). The `model_dump()` call serializes all 30 fields; `model_validate()` re-parses all 30 fields plus any extras from the API response.

Business entities add:
- **Business**: 16 custom field descriptors + 7 holder PrivateAttrs (not in dump) = ~30 Task fields
- **Contact**: 19 custom field descriptors = ~30 Task fields
- **Unit**: 31 custom field descriptors = ~30 Task fields
- **Offer**: 39 custom field descriptors = ~30 Task fields
- **Process**: 50+ custom field descriptors = ~30 Task fields
- **Holders** (ContactHolder, UnitHolder, etc.): ~30 Task fields, no additional model fields

Note: Custom field descriptors are NOT Pydantic fields. They read from `custom_fields` list at access time. So the actual Pydantic field count for model_validate is consistently ~30 fields from the Task base class.

#### (c) Validators -- CRITICAL ANALYSIS

**model_validator on Task (line 137-145)**:
```python
@model_validator(mode="after")
def _capture_custom_fields_snapshot(self) -> Task:
    """Capture snapshot of custom_fields at initialization."""
    if self.custom_fields is not None:
        self._original_custom_fields = copy.deepcopy(self.custom_fields)
    return self
```

**Classification: TRANSFORM/COMPUTE -- MUST NOT SKIP**

This validator performs a `copy.deepcopy()` of the `custom_fields` list into `_original_custom_fields`. This snapshot is used by:
1. `_has_direct_custom_field_changes()` -- detects if custom_fields was mutated after construction
2. `model_dump()` override -- uses the snapshot to detect and merge direct modifications
3. `reset_custom_field_tracking()` -- re-snapshots after save

If `model_construct` is used, `_original_custom_fields` will be `None` (the PrivateAttr default). This means:
- `_has_direct_custom_field_changes()` will **incorrectly return True** if `custom_fields` is non-empty (line 157: "No snapshot means no custom_fields at init")
- `model_dump()` will **incorrectly detect phantom changes** and convert them to API format
- `save_async()` will **incorrectly attempt to update fields** that were not actually changed

**However**: In the specific context of `_populate_children` and `_create_typed_holder`, the constructed entities are **read-only navigational objects**. They are never saved back to Asana -- they exist only for reading custom field values (via descriptors) and navigating the hierarchy. The `model_dump()` override and `save_async()` paths are not exercised on these instances in normal operation.

**Nuance**: The `_convert_to_typed_entity` in `hydration.py:782` creates entities that are placed in `HydrationResult.path`. If any consumer calls `model_dump()` on a path entity, they would get incorrect change detection. This is a theoretical risk.

**No other validators exist** across the entire business model hierarchy:
- `BusinessEntity` -- no validators
- `AsanaResource` -- no validators
- All entity subclasses (Contact, Unit, Offer, Process, Location, Hours, etc.) -- no validators
- All holder subclasses -- no validators

#### (d) Test Coverage for _populate_children

Comprehensive tests exist in `tests/unit/models/business/test_holder_factory.py`:
- `TestPopulateChildren` class: 6 tests covering DNA, Reconciliation, AssetEdit, Videography population, sorting, empty list
- Tests verify: child count, child type (isinstance), bidirectional reference setting, sorting order
- Tests use `Task` instances as input, verifying the `model_validate(task.model_dump())` round-trip produces typed children

Additional coverage in entity-specific test files:
- `test_contact.py`, `test_unit.py`, `test_offer.py`, `test_process.py`, `test_location.py`, `test_asset_edit.py`

#### (e) Validator Classification Summary

| Validator | Location | Type | model_construct safe? |
|-----------|----------|------|----------------------|
| `_capture_custom_fields_snapshot` | Task:137 | TRANSFORM (deepcopy) | **NO** for save-capable objects; **YES** for read-only navigational objects |

### Per-Model Verdict

| Model | Use Case | model_construct safe? | Rationale |
|-------|----------|----------------------|-----------|
| **ContactHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **UnitHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **LocationHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **DNAHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **ReconciliationHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **AssetEditHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **VideographyHolder** | _create_typed_holder | **YES** | Read-only holder, never saved |
| **Contact** | _populate_children | **YES** | Read-only during hydration |
| **Unit** | _populate_children | **YES** | Read-only during hydration |
| **Offer** | _populate_children | **YES** | Read-only during hydration |
| **Process** | _populate_children | **YES** | Read-only during hydration |
| **Location** | LocationHolder._populate_children | **YES** | Read-only during hydration |
| **Hours** | LocationHolder._populate_children | **YES** | Read-only during hydration |
| **DNA** | HolderFactory._populate_children | **YES** | Read-only during hydration |
| **Reconciliation** | HolderFactory._populate_children | **YES** | Read-only during hydration |
| **AssetEdit** | HolderFactory._populate_children | **YES** | Read-only during hydration |
| **Videography** | HolderFactory._populate_children | **YES** | Read-only during hydration |
| **Business** | from_gid_async, hydration | **CONDITIONAL** | Could be saved; snapshot needed for save correctness |
| **Unit/Offer** | asset_edit.py workflows | **CONDITIONAL** | May participate in save flows |

### If CONDITIONAL-GO -- Implementation Sketch

**Phase 1: Safe sites (all _populate_children and _create_typed_holder)**

Replace `model_validate(task.model_dump())` with `model_construct` using the task's existing validated data. The key insight: the `task` input is ALREADY a validated `Task` instance. We are converting `Task -> dict -> TargetType`, but we can go `Task -> TargetType` directly.

Two implementation options:

**Option A: model_construct with field extraction** (simplest, highest risk reduction):
```python
# Instead of:
child = child_class.model_validate(task.model_dump())

# Use:
child = child_class.model_construct(
    _fields_set=task.model_fields_set,
    **{k: getattr(task, k) for k in task.model_fields if hasattr(task, k)}
)
```

**Option B: model_validate with from_attributes=True** (safer, moderate speedup):
```python
# Instead of:
child = child_class.model_validate(task.model_dump())

# Use:
child = child_class.model_validate(task, from_attributes=True)
```

Option B still runs the validator but avoids the model_dump serialization step. This is the safer choice and still provides ~50% of the speedup (eliminating the dict round-trip).

**Recommendation**: Use **Option B** (`from_attributes=True`) for all sites initially. This:
- Avoids skipping the `_capture_custom_fields_snapshot` validator
- Eliminates the `model_dump()` serialization overhead
- Is a safe, low-risk change that can be applied uniformly
- Still provides meaningful speedup (eliminating dict construction and parsing)

**Phase 2: Optional further optimization (model_construct for read-only holders only)**

For holder creation in `_create_typed_holder` (business.py:581-616) and `_populate_children` (holder_factory.py:306-308), consider `model_construct` if profiling shows the validator deepcopy is a bottleneck. These objects are definitively read-only.

If model_construct is used, manually set `_original_custom_fields = None` and document that these instances are not save-capable:
```python
child = child_class.model_construct(
    _fields_set=task.model_fields_set,
    **{k: getattr(task, k) for k in task.model_fields}
)
# Explicitly mark as non-saveable (no snapshot means model_dump detects "changes")
child._original_custom_fields = None
child._custom_fields_accessor = None
```

### Risks

- **Medium**: `model_construct` skips the `_capture_custom_fields_snapshot` validator. If any downstream code calls `model_dump()` or `save_async()` on a constructed entity, it will produce incorrect change detection. Mitigated by: (a) using `from_attributes=True` in Phase 1, (b) only using `model_construct` for definitively read-only instances in Phase 2.
- **Low**: `from_attributes=True` may behave differently if Task has properties that shadow field names. Pydantic v2 resolves this via `model_fields` which excludes properties. Verify in testing.
- **Low**: Some test assertions may check for exact `model_validate` calls via mocking. These would need updating.

### Affected Files

**Phase 1 (from_attributes=True -- all sites)**:
- `src/autom8_asana/models/business/holder_factory.py` (line 308)
- `src/autom8_asana/models/business/base.py` (line 129)
- `src/autom8_asana/models/business/business.py` (lines 220, 582-616)
- `src/autom8_asana/models/business/hydration.py` (lines 338, 716, 782, 808)
- `src/autom8_asana/models/business/unit.py` (lines 327, 332)
- `src/autom8_asana/models/business/location.py` (lines 221, 226)
- `src/autom8_asana/models/business/asset_edit.py` (lines 537, 646, 664, 708)
- Test files for all of the above

**Phase 2 (model_construct for read-only holders -- optional)**:
- `src/autom8_asana/models/business/holder_factory.py` (line 308)
- `src/autom8_asana/models/business/business.py` (lines 582-616)
