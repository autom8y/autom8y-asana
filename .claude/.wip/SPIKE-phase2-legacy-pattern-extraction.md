# SPIKE: Workflow Resolution Platform -- Phase 2: Legacy Pattern Extraction

**Date**: 2026-02-11
**Scope**: Deep dive into legacy codebase patterns for extraction and avoidance
**Phase**: 2 of 3
**Dependency**: Phase 1 (`.claude/.wip/SPIKE-phase1-core-system-mapping.md`)

---

## Objective 4: Legacy Resolution Patterns (Good + Bad)

### Summary Verdict

The legacy resolution system is a **mixed bag of architectural sophistication and accumulated brittleness**. The core entity resolution patterns (Process.unit, Process.offer) implement robust multi-step fallback chains that gracefully degrade through trigger_task traversal, dependency traversal, and custom field lookup. These are worth extracting. However, the resolution system is tightly coupled to mutable class instances, relies on string-based field matching for defaults, and chains API calls without error budgets. These patterns should be avoided.

### Good Patterns Worth Extracting

#### Pattern 1: Multi-Step Fallback Resolution Chain (Process.unit)

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 582-686)

The `Process.unit` property implements a resolution strategy with 6 ordered fallback steps:

1. **Cache check**: Return `_unit` if already resolved (line 593-594)
2. **Trigger-type dispatch**: Branch on trigger_task type with type-appropriate traversal (lines 607-646):
   - `trigger_task is Unit` -> direct assignment
   - `trigger_task is Offer` -> `trigger_task.unit`
   - `trigger_task is Process` -> through `process_holder.unit` (with special-casing for DnaHolder and AssetEditHolder)
   - `trigger_task is AssetEditHolder` -> dependency traversal to find OfferHolder, then `.unit`
   - Generic fallback: check for `.unit` attribute on trigger_task
3. **Self-dependency traversal**: Check own dependents for Unit or Offer (lines 654-661)
4. **Trigger-dependency traversal**: Check trigger_task's dependents for Unit or Offer (lines 662-673)
5. **Vertical-based lookup**: Fall back to `unit_for_vertical` (line 674-675)
6. **Validation gate**: If trigger_task was set and resolution failed, raise AttributeError (lines 680-684)

**Why this is good**: The fallback chain makes entity resolution resilient to incomplete data. Tasks created by different code paths (tag routing, manual creation, API import) may have different data available. The chain tries cheap/reliable paths first, expensive/fallback paths later.

**What to extract**: The _strategy_ of ordered fallback resolution with type-dispatched traversal. NOT the specific implementation (which is tightly coupled to mutable objects).

#### Pattern 2: Multi-Step Fallback Resolution Chain (Process.offer)

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 709-868)

The `Process.offer` property follows a similar pattern but with even more fallback steps:

1. Cache check (line 722-723)
2. Trigger-type dispatch (lines 733-760): Offer, OfferHolder (with dependency traversal), Unit, Process (with DnaHolder special-casing)
3. Self-dependency traversal in `finally` block (lines 786-802): OfferHolder -> Offer, direct Offer, Unit -> offer
4. Trigger-dependency traversal (lines 803-819)
5. Custom field lookup: `offer_id` display_value matched against `unit_for_vertical.offer_holder.offers` (lines 822-836)
6. Active offers fallback: `offer_holder.active_offers[0]` (line 837-838)
7. Offer ID mismatch correction: If resolved offer has wrong `offer_id`, search siblings (lines 846-857)

**Why this is good**: The offer resolution handles a fundamentally ambiguous relationship -- a Process may relate to multiple offers through an OfferHolder. The multi-step chain with final offer_id validation ensures correct resolution even when structural traversal produces the wrong result.

**What to extract**: The concept of resolution with post-resolution validation. After resolving via structural traversal, verify the result against identifying fields and correct if needed.

#### Pattern 3: Pipeline Auto-Completion on Init

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/main.py` (lines 57-103)

When a new Pipeline process is initialized via `init_process()`, the system automatically completes earlier pipeline stages:

```python
# Traverses offer's dependencies + dependents
deps = [d.task for d in self.offer.dependencies] + [d.task for d in self.offer.dependents]
for d in deps:
    if not isinstance(d, Pipeline): continue
    if d.pipeline_stage > self.pipeline_stage: continue
    d.is_completed = True
    # Move to COMPLETED section if not already in terminal section
    if not any(snake_lower(s.name) in {"converted", "did_not_convert"} for s in d.sections):
        d.sections.add("COMPLETED")
```

This uses threaded saves for completed processes (lines 98-100).

**Why this is good**: Auto-completion prevents orphaned in-progress pipeline stages when a higher stage is created. If Implementation (stage 4) is created, any open Sales (stage 2) or Onboarding (stage 3) are auto-completed. This is a critical business rule.

**What to extract**: The concept of hierarchical stage completion. When a later stage begins, earlier stages should be transitioned to a terminal state. The specific implementation (dependency traversal + threaded saves) can be improved.

#### Pattern 4: Cascading Section Updates on Init

Each pipeline stage's `init_process()` updates the Offer, Unit, and Business sections to reflect the new lifecycle state:

| Pipeline Stage | Offer Section | Unit Section | Business Section |
|---|---|---|---|
| Sales (stage 2) | "Sales Process" | "Next Steps" | "OPPORTUNITY" |
| Outreach (stage 1) | "Sales Process" | "Engaged" | "OPPORTUNITY" |
| Onboarding (stage 3) | "ACTIVATING" | "Onboarding" | "ONBOARDING" |
| Implementation (stage 4) | "IMPLEMENTING" | "Implementing" | "IMPLEMENTING" |
| Retention (stage 1) | (deactivate campaign) | "Account Review" | -- |
| Reactivation (stage 2) | (deactivate campaign) | "Paused" | -- |
| Month1 (stage 5) | "STAGED" | "Month 1" | "BUSINESSES" |
| AccountError (stage 6) | "ACCOUNT ERROR" | "Account Error" | (activate/deactivate) |

**Why this is good**: Entity lifecycle is kept consistent across the hierarchy. When Onboarding begins, the Offer, Unit, and Business all reflect that fact via section membership. This is a critical visibility/reporting requirement.

**What to extract**: The mapping table of pipeline stage -> entity section updates. This is business configuration that should be data-driven, not embedded in class methods.

#### Pattern 5: Default Dependency/Dependent Wiring

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 966-1100)

Newly created processes are wired with default dependency links:
- **Pipelines** get DNA plays as dependencies (lines 976-979)
- **Non-Pipelines** get OfferHolder's open dependents that are DNA plays (lines 980-1005)
- **All processes** get Unit + OfferHolder as default dependents (lines 1046-1055)
- **Pipelines** additionally get other open dependencies from their primary holder (lines 1057-1084)

**Why this is good**: Automatic dependency wiring ensures new processes are connected to the entity graph without manual intervention. It enables the traversal-based resolution patterns described above.

**What to extract**: The concept of "default wiring rules" -- when an entity is created, what connections should be automatically established. The specific rules are business logic that should be configurable.

#### Pattern 6: ProcessManager Duplicate Detection

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/managers/process_manager/main.py` (lines 181-230)

Before creating a new process, the ProcessManager checks for existing ones:
1. Load the target project's DataFrame (cached)
2. Filter by action type (snake_lower match)
3. Filter by matching attributes (office_phone, vertical)
4. If match found, return existing process (bump instead of create)

**Why this is good**: Prevents duplicate process creation when a tag is applied multiple times or when an existing process already covers the action. Returns the existing process for "bump" behavior instead.

**What to extract**: The duplicate detection concept -- before creating, check if an equivalent entity already exists. The implementation should use a more robust matching strategy than string comparison on DataFrames.

### Cautionary Tales to Avoid

#### Anti-Pattern 1: String-Based Field Default Resolution

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 1292-1684)

Field defaults are specified as dot-separated string paths evaluated at runtime:

```python
@classmethod
def default_office_phone(cls) -> str:
    return "offer.office_phone"

@classmethod
def default_vertical(cls) -> str:
    return "unit.vertical"

@classmethod
def default_mrr(cls) -> str:
    return "unit.mrr"
```

These strings are resolved dynamically by the CustomField base class, traversing the object graph via `getattr` chains. This means:
- **No compile-time validation** -- typos in paths fail silently at runtime
- **Hidden coupling** -- changing a property name on Offer breaks Process field defaults without any detectable link
- **Debugging difficulty** -- failures in default resolution produce opaque errors deep in the CustomField framework

**Recommendation**: Replace with explicit typed references or a configuration registry with validation.

#### Anti-Pattern 2: Deep Mutable Object Graphs with Thread-Unsafe State

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 285-448)

The `_init_fields()` method spawns threads to process fields in parallel:

```python
for field_name in all_fields:
    thread_manager.start_thread(field_name, process_field, field_name, debug=debug)
```

Each thread mutates the same Process instance and its connected entities. The `thread_safe_property` decorator provides some protection, but the underlying pattern of concurrent mutation of shared mutable state is inherently fragile.

The `save()` method (lines 225-264) compounds this by cascading saves:
```python
super().save(attributes=attributes, **kwargs)
if self.unit is not None:
    self.unit.save(**save_kwargs)
    if self.business is not None:
        self.business.save(**save_kwargs)
```

**Impact**: Race conditions between field initialization and save propagation. A field's default value resolution may trigger a property access that triggers an API call on a different thread.

**Recommendation**: Use an immutable snapshot + mutation plan pattern. Collect all changes, then apply them atomically.

#### Anti-Pattern 3: Excessive API Call Chains Without Error Budgets

The `Process.unit` property (lines 582-686) can trigger deep API call chains:

```
Process -> trigger_task (API: get_task)
  -> process_holder (API: get_parent)
    -> AssetEditHolder (instance check)
      -> dependents (API: get_dependents_for_task)
        -> each dependent.task (API: get_task per dependent)
          -> OfferHolder? (instance check)
            -> .unit (API: traverse parent)
```

This worst-case path involves 4-6 API calls to resolve a single property. There is no error budget, timeout, or circuit breaker. If the Asana API is slow, resolution of a single Process could take 30+ seconds.

**Recommendation**: Resolution should have a configurable depth limit and total API call budget. After N calls, fail fast or return partial resolution.

#### Anti-Pattern 4: Tight Coupling Between Entity Types via isinstance Checks

Throughout the resolution code, behavior is dispatched via `isinstance` checks on approximately 8 entity types:

```python
if isinstance(self.trigger_task, Unit): ...
elif isinstance(self.trigger_task, Offer): ...
elif isinstance(self.trigger_task, Process):
    if isinstance(self.trigger_task.process_holder, DnaHolder): ...
    elif isinstance(self.trigger_task.process_holder, AssetEditHolder): ...
```

**Impact**: Adding a new entity type requires modifying every resolution method that does isinstance dispatch. The ProcessManager._get_next_project (lines 145-179) has a hardcoded action_map with specific project class references.

**Recommendation**: Use a resolution strategy registry where entity types register their navigation capabilities declaratively.

#### Anti-Pattern 5: Commented-Out Debug Code and Dead Branches

The legacy codebase contains extensive commented-out print statements and debug code:
- `pipeline/main.py`: 6 commented `# print(...)` blocks
- `process_manager/main.py`: 10+ commented `# print(...)` blocks
- `process/main.py`: Multiple commented sleep/retry blocks (lines 1033-1044)
- `_init_close_processes()`: Entire method body disabled with `return` on line 519-521

The `_init_close_processes` method (lines 501-554) is completely dead code -- it returns immediately after a log warning. Yet it's still called conditionally via `kwargs.get("close_processes")`.

**Recommendation**: Dead code should be removed, not commented out. Git history preserves old implementations.

#### Anti-Pattern 6: Retry-via-Sleep Without Backoff

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/service/source_videographer/main.py` (lines 82-91, 119-139)

The SourceVideographer uses hardcoded `sleep(1)` retries for holder resolution:

```python
for _ in range(3):
    self._videography_holder = self.holder
    if self._videography_holder:
        break
    sleep(1)
```

**Impact**: Blocks the thread for up to 3 seconds with no exponential backoff, jitter, or diagnostics beyond a warning log. This pattern appears because the async creation of parent tasks hasn't propagated yet -- a timing dependency papered over with sleeps.

**Recommendation**: Use async/await with proper retry policies, or redesign the creation flow so parent tasks are guaranteed to exist before child resolution is attempted.

#### Anti-Pattern 7: Inconsistent Error Handling (QUIET Flag)

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (line 59, 763-764, 839-844, 859-860)

A module-level `QUIET = True` flag suppresses error logging throughout the Process class:

```python
QUIET = True  # line 59

# In offer resolution:
except Exception as e:
    if QUIET:
        return self._offer  # Silently return None
    LOG.error(...)  # Only logs if QUIET is False
```

**Impact**: Resolution failures are silently swallowed. A broken dependency link or missing entity returns `None` instead of surfacing an error. Downstream code must handle `None` at every step, and when it doesn't, the actual failure point is obscured.

**Recommendation**: Use structured error responses (e.g., `ResolutionResult` with success/failure/partial states) instead of None returns.

### Extraction Summary

| Pattern | Extract? | As What? |
|---|---|---|
| Multi-step fallback resolution | YES | Resolution strategy chain (configurable, typed) |
| Post-resolution validation | YES | Validation layer in resolution pipeline |
| Pipeline auto-completion | YES | Business rule in lifecycle transition config |
| Cascading section updates | YES | Data-driven mapping (stage -> section config) |
| Default dependency wiring | YES | Wiring rules registry |
| Duplicate detection | YES | Idempotency check in process creation |
| String-based field defaults | NO | Use typed references or validated config |
| Thread-unsafe mutation | NO | Use immutable snapshot + mutation plan |
| Unbounded API chains | NO | Add depth limits and error budgets |
| isinstance dispatch | NO | Use strategy registry pattern |
| Debug code in production | NO | Clean code practices |
| Sleep-based retries | NO | Use async retry with backoff |
| QUIET error suppression | NO | Use structured resolution results |

---

## Objective 5: Products-Field-Driven Entity Creation Routing

### Summary

The Products field is a **MultiEnumField on Process entities** that drives two distinct behaviors:

1. **Conditional entity creation during pipeline transitions** (Onboarding `init_process` creates SourceVideographer if products contain "Videography")
2. **Product list synchronization between Process and Unit** (Pipeline `init_process` syncs products bidirectionally for stages >= 3)

The routing is surprisingly simple -- only ONE product value triggers conditional entity creation. The more complex behavior is the product synchronization logic.

### Products Field Model

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/custom_field/models/multi_enum/products.py`

```python
class Products(MultiEnumField):
    VALID_PRODUCT_STAGE_CUT_OFF = 3  # Only stages >= 3 can set products on Unit
```

Products is a list of string values (multi-enum Asana custom field). The `VALID_PRODUCT_STAGE_CUT_OFF = 3` means only Onboarding (stage 3) and later can propagate products to the Unit.

The default value for Products on a new Process is `"unit.products"` (string-based default resolution from Process.default_products, line 1452-1453 of process/main.py), meaning new processes inherit their products from the Unit.

### Products-Driven Entity Creation

There is exactly **one** products-driven creation in the legacy codebase:

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/onboarding/main.py` (lines 52-53)

```python
def init_process(self, *args, **kwargs):
    # ... section updates ...
    super().init_process(*args, **kwargs)  # seeds fields, including products

    if any(p.lower().startswith("video") for p in self.products):
        self.route("request_source_videographer")
```

**Trigger**: Products list contains any value starting with "video" (case-insensitive)
**Action**: Route a `request_source_videographer` via the ProcessManager

The `request_source_videographer` route:
1. Goes to ProcessManager.request() (which calls _route())
2. `_get_next_project("source_videographer")` returns `VideographerSourcing()` project (line 161 of process_manager/main.py)
3. Finds template, duplicates it
4. Creates a SourceVideographer process placed under the Business's VideographyHolder

### Implementation-Stage Entity Creation (NOT Products-Driven)

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/implementation/main.py` (lines 34-100)

Implementation's `init_process` creates two additional entities, but these are **not** driven by the Products field -- they are always created (unless skip flags are set):

1. **BackendOnboardABusiness** (DNA play): Created via `play_backend_onboard_a_business` if no existing BackendOnboardABusiness is linked as a dependency
2. **AssetEdit**: Created via `request_asset_edit` if no existing AssetEdit is linked as a dependency

Both check for existing linked entities before creating new ones (duplicate avoidance).

### Product Synchronization Logic

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/main.py` (lines 36-52)

For pipeline stages >= 3 (Onboarding, Implementation, Month1, AccountError):

```python
if self.pipeline_stage >= 3 and self.products:
    if self.unit.products != self.products:
        # Step 1: Add any new products from Process to Unit
        for p in self.products:
            if p not in self.unit.products:
                self.unit.products.append(p)

        # Step 2: Remove products from Unit that are not in Process
        # BUT only if they're not present in ANY other active pipeline stage >= 3
        # AND only if they contain "marketing" AND the offer is not active/activating
        for p in self.unit.products:
            if p not in self.products and p not in [
                p for stage, process_products
                in self.process_holder.pipeline_stage_product_map.items()
                if stage >= 3
                for p in process_products
                if p not in self.products
            ]:
                if "marketing" in p.lower() and not (
                    self.offer_holder.is_active or self.offer_holder.is_activating
                ):
                    self.unit.products.remove(p)
```

**Key insight**: Product removal is highly guarded:
- Only "marketing" products can be removed
- Only if the offer is NOT active or activating
- Only if no other active pipeline process (stage >= 3) still has that product

The `pipeline_stage_product_map` on ProcessHolder (line 104-117 of process_holder/main.py) aggregates products across all pipeline processes by stage number.

### Products on converted() and did_not_convert()

**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/main.py` (lines 168-200)

Base Process class handles products during lifecycle transitions:
- **converted()** (line 178-182): If products field exists and process has products not on unit, extend unit.products
- **did_not_convert()** (line 198-200): If Pipeline, remove the process's products from unit.products (deactivation)

### Full Products-to-Entity Creation Routing DAG

```
Products Field Values Evaluated At:
====================================

Onboarding.init_process() [stage 3]:
  if "video*" in products:
    -> request_source_videographer
       -> VideographerSourcing project
       -> SourceVideographer template duplicated
       -> Placed under Business.videography_holder

Implementation.init_process() [stage 4]:  (NOT products-driven)
  always:
    -> play_backend_onboard_a_business (unless already linked)
       -> BackendClientSuccessDna project
       -> BackendOnboardABusiness template duplicated
       -> Placed under Business.dna_holder
    -> request_asset_edit (unless already linked)
       -> PaidContent project
       -> AssetEdit template duplicated
       -> Placed under Business.asset_edit_holder

Pipeline Lifecycle Transitions:
================================

Sales.converted()      -> route_onboarding      [ProcessHolder]
Sales.did_not_convert() -> route_outreach        [ProcessHolder]

Outreach.converted()    -> route_sales           [ProcessHolder]
Outreach.did_not_convert() -> route_outreach     [ProcessHolder]

Onboarding.converted()  -> route_implementation  [ProcessHolder]
Onboarding.did_not_convert() -> route_sales      [ProcessHolder]

Implementation.converted() -> route_month_1      [ProcessHolder]
Implementation.did_not_convert() -> route_sales  [ProcessHolder]

Month1.converted()      -> (completes, no route) [Offer -> OPTIMIZE section if notes]

Retention.converted()   -> route_implementation  [ProcessHolder]
Retention.did_not_convert() -> route_reactivation [ProcessHolder]

Reactivation.converted() -> route_implementation [ProcessHolder]
Reactivation.did_not_convert() -> route_reactivation [ProcessHolder]

AccountError.converted() -> (reactivate campaign, update sections)
AccountError.did_not_convert() -> route_retention [ProcessHolder]

Expansion                -> (no converted/did_not_convert overrides)
```

### Dependency Wiring During Creation

When entities are created via `init_process()`:

| Created Entity | Wired As | On |
|---|---|---|
| SourceVideographer | No dependency wiring | Standalone under VideographyHolder |
| BackendOnboardABusiness | Added as dependency | On Implementation process |
| AssetEdit | Added as dependency | On Implementation process |
| All Pipeline processes | default_dependents: Unit + OfferHolder | Via dependency API |
| All Pipeline processes | default_dependencies: open DNA plays | Via dependency API |

---

## Objective 6: Process Subclass Completeness Evaluation

### Summary

The legacy has **11 Process subclass types** across 3 hierarchies, each with specific behaviors. The microservice has a **single Process class with a ProcessType enum** that covers 6 of the 8 pipeline types but none of the service/DNA types. The gap is significant -- the microservice models Process as data (fields + state), while the legacy models Process as behavior (methods + side effects).

### Legacy Process Class Hierarchy

```
Task
  +-- Process (base)                       [process/main.py]
        +-- Pipeline (base)                [process/pipeline/main.py]
        |     +-- Sales        (stage 2)   [pipeline/sales/main.py]
        |     +-- Outreach     (stage 1)   [pipeline/outreach/main.py]
        |     +-- Onboarding   (stage 3)   [pipeline/onboarding/main.py]
        |     +-- Implementation (stage 4) [pipeline/implementation/main.py]
        |     +-- Retention    (stage 1)   [pipeline/retention/main.py]
        |     +-- Reactivation (stage 2)   [pipeline/reactivation/main.py]
        |     +-- Month1       (stage 5)   [pipeline/month_1/main.py]
        |     +-- AccountError (stage 6)   [pipeline/account_error/main.py]
        |     +-- Expansion    (stage 6)   [pipeline/expansion/main.py]
        |
        +-- Service (base)                 [process/service/main.py]
        |     +-- SourceVideographer       [service/source_videographer/main.py]
        |
        +-- Consultation                   [process/consultation/main.py]
        |
        +-- AssetEdit                      [asset_edit/main.py]

  +-- Dna (separate hierarchy)             [dna/main.py]
        +-- IsolatedPlay
              +-- BackendOnboardABusiness
```

### Per-Pipeline-Stage Behavior Catalog

#### Sales (stage 2)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/sales/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Offer -> "Sales Process", Unit -> "Next Steps", Business -> "OPPORTUNITY" |
| `converted()` | Sets internal_notes with celebration message + link; routes `route_onboarding` |
| `did_not_convert()` | Sets internal_notes with retry message; routes `route_outreach` |
| `pipeline_stage` | 2 |
| Custom fields | None beyond Pipeline base |
| Default rep | `InternalRole.SALES` (inherited from Pipeline) |

#### Outreach (stage 1)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/outreach/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Offer -> "Sales Process", Unit -> "Engaged", Business -> "OPPORTUNITY" |
| `converted()` | Sets internal_notes; routes `route_sales` |
| `did_not_convert()` | Sets internal_notes; routes `route_outreach` (self-loop: creates another Outreach) |
| `pipeline_stage` | 1 |
| Custom fields | `contact_email`, `contact_phone`, `contact_url` with defaults from `business.contact_holder.contact.*` |
| Default rep | `InternalRole.SALES` (inherited from Pipeline) |

#### Onboarding (stage 3)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/onboarding/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Offer -> "ACTIVATING", Unit -> "Onboarding", Business -> "ONBOARDING"; calls super().init_process() THEN checks products for videography |
| `converted()` | Sets internal_notes; routes `route_implementation` |
| `did_not_convert()` | Sets internal_notes; routes `route_sales` |
| `pipeline_stage` | 3 |
| Custom fields | `client_goal_mrr`, `asset_edit_comments`, `current_revenue_growth`, `client_current_mrr`, `goal_revenue_growth` |
| Default rep | `InternalRole.SALES` (inherited from Pipeline) |
| **Special**: Products-driven creation | If products contain "video*" -> creates SourceVideographer |

#### Implementation (stage 4)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/implementation/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Creates BackendOnboardABusiness (DNA play) + AssetEdit (via Onboarding route); Offer -> "IMPLEMENTING", Unit -> "Implementing", Business -> "IMPLEMENTING" |
| `converted()` | Sets internal_notes; routes `route_month_1`; adds base_story to stories |
| `did_not_convert()` | Sets internal_notes; routes `route_sales`; adds base_story to stories |
| `pipeline_stage` | 4 |
| Custom fields | None beyond Pipeline base |
| Default rep | `InternalRole.SUCCESS` |
| **Special**: Dedup logic | Checks for existing BackendOnboardABusiness and AssetEdit in dependencies before creating |
| **Special**: Routes through Onboarding | Uses `self.process_holder.recent_onboarding.route(...)` to route via the most recent Onboarding process |

#### Month1 (stage 5)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/month_1/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Unit -> "Month 1", Offer -> "STAGED", Business -> "BUSINESSES"; due_date = implementation completed_at + 21 days; activates offer (ad campaign) |
| `converted()` | Unit -> "Active"; if internal_notes present, sets review_offer=True (sends Offer to "OPTIMIZE - Human Review") |
| `did_not_convert()` | Not overridden (uses Pipeline base: `LOG.warning(...)` + `is_completed = True`) |
| `pipeline_stage` | 5 |
| Custom fields | None beyond Pipeline base |
| Default rep | `InternalRole.SUCCESS` |
| Default priority | "High" (hardcoded in `__init__`) |
| **Special**: Offer activation | Calls `self.offer.activate()` during init -- starts the ad campaign |

#### Retention (stage 1)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/retention/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Unit -> "Account Review"; deactivates offer campaign |
| `converted()` | Sets internal_notes; routes `route_implementation` |
| `did_not_convert()` | Sets internal_notes; routes `route_reactivation` |
| `pipeline_stage` | 1 |
| Custom fields | None beyond Pipeline base |
| Default rep | `InternalRole.SUCCESS` |
| **Special**: Campaign deactivation | Calls `self.offer.deactivate_campaign()` during init |

#### Reactivation (stage 2)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/reactivation/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Unit -> "Paused"; deactivates offer campaign |
| `converted()` | Sets internal_notes; routes `route_implementation` |
| `did_not_convert()` | Sets internal_notes; routes `route_reactivation` (self-loop) |
| `pipeline_stage` | 2 |
| Custom fields | None beyond Pipeline base |
| Default rep | `InternalRole.SALES` (inherited from Pipeline) |
| **Special**: Campaign deactivation | Calls `self.offer.deactivate_campaign()` during init |

#### AccountError (stage 6)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/account_error/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Unit -> "Account Error", Offer -> "ACCOUNT ERROR"; deactivates campaign; passes `close_processes=True` to super |
| `converted()` | Unit -> "Active", Offer -> "ACTIVE"; reactivates campaign via `self.offer.ad_manager.activate()` |
| `did_not_convert()` | Sets internal_notes; routes `route_retention`; adds base_story |
| `pipeline_stage` | 6 |
| Custom fields | None beyond Pipeline base |
| **Special**: close_processes=True | Triggers auto-closing of related processes during init (via `_init_close_processes`) -- though this is currently disabled with `return` on line 519 of process/main.py |

#### Expansion (stage 6)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/pipeline/expansion/main.py`

| Behavior | Details |
|---|---|
| `init_process()` | Not overridden (uses Pipeline base) |
| `converted()` | Not overridden (uses Pipeline base: `LOG.warning(...)` + `is_completed = True`) |
| `did_not_convert()` | Not overridden (uses Pipeline base: `LOG.warning(...)` + `is_completed = True`) |
| `pipeline_stage` | 6 |
| Custom fields | None |
| **Note**: Minimal implementation | Appears to be a placeholder or rarely-used stage |

### Non-Pipeline Process Types

#### Consultation (Service base)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/consultation/main.py`

Identical to Service base class. Provides:
- `converted()`: Generates a story with converter user tag, internal notes or first comment. Posts story to self, offer, and unit.
- `did_not_convert()`: Same pattern as converted but with failure messaging.
- `ai_comment_summary`: Uses LLM to summarize the consultation's comment history.
- Default rep: `InternalRole.CONSULTATION`

#### SourceVideographer (Service base)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/process/service/source_videographer/main.py`

- Custom ASANA_FIELDS: `office_phone`, `vertical`, `city`, `state`, `contractor_cost`, `sourcing_ad_spend`, `client_invoice`, `shoot_date`
- All field defaults derived from business entity graph (e.g., `city` from `business.location.city`)
- Custom holder resolution: lives under VideographyHolder, not ProcessHolder
- `rejected_or_canceled()` section handler (calls `super().did_not_convert()`)
- Default rep: `InternalRole.SALES`

#### AssetEdit (extends Process directly)
**File**: `/Users/tomtenuta/code/autom8/apis/asana_api/objects/task/models/asset_edit/main.py`

- Custom ASANA_FIELDS: `asset_approval`, `asset_id`, `editor`, `reviewer`, `offer_id`, `raw_assets`, `review_all_ads`, `score`, `specialty`, `template_id`, `videos_paid`
- Lives under AssetEditHolder (separate from ProcessHolder)
- Has section-based update functions in `asset_edit/funcs/section_updates.py`
- Template selection is sophisticated (vertical + specialty matching with dedup against existing template assets)

### Microservice Process Model

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py`

```python
class ProcessType(str, Enum):
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"
    GENERIC = "generic"
```

The microservice has:
- `ProcessType` enum with 6 pipeline types + GENERIC (missing: Month1, AccountError, Expansion)
- `ProcessSection` enum with 7 states (OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT, OTHER)
- `Process` class with field descriptors organized by pipeline type (51+ Sales fields, 33+ Onboarding fields, 28+ Implementation fields)
- `ProcessHolder` with HolderFactory pattern

**The microservice's Process is a data model only.** It has:
- Field accessors (descriptors)
- State querying (`pipeline_state`, `process_type`)
- Navigation (`unit`, `business`, `process_holder`)

It does NOT have:
- `init_process()` (initialization side effects)
- `converted()` / `did_not_convert()` (lifecycle transition behavior)
- Section update propagation to Offer/Unit/Business
- Entity creation routing (SourceVideographer, AssetEdit, BackendOnboardABusiness)
- Product synchronization logic
- Dependency wiring
- Cascading saves

### Gap Analysis: Legacy vs. Microservice

#### Missing Process Types

| Process Type | Legacy | Microservice ProcessType | Gap |
|---|---|---|---|
| Sales | Full behavior | SALES enum | Data model only, no behavior |
| Outreach | Full behavior | OUTREACH enum | Data model only, no behavior |
| Onboarding | Full behavior + SourceVideographer creation | ONBOARDING enum | Data model only, no creation |
| Implementation | Full behavior + BackendOB + AssetEdit creation | IMPLEMENTATION enum | Data model only, no creation |
| Month1 | Full behavior + offer activation | **MISSING** | Not in ProcessType enum |
| Retention | Full behavior + campaign deactivation | RETENTION enum | Data model only, no campaign control |
| Reactivation | Full behavior + campaign deactivation | REACTIVATION enum | Data model only, no campaign control |
| AccountError | Full behavior + campaign reactivation | **MISSING** | Not in ProcessType enum |
| Expansion | Minimal (placeholder) | **MISSING** | Not in ProcessType enum |
| Consultation | Full behavior + AI summaries | **MISSING** | Not a pipeline type |
| Service/SourceVideographer | Full behavior | **MISSING** | Not a pipeline type |
| AssetEdit | Full behavior + template matching | **MISSING** | Not a pipeline type |
| DNA/BackendOnboardABusiness | Full behavior | **MISSING** | Separate hierarchy |

#### Missing Behavioral Capabilities

| Capability | Legacy | Microservice |
|---|---|---|
| init_process() lifecycle initialization | Per-subclass, 8+ implementations | None |
| converted() / did_not_convert() | Per-subclass routing + section updates | None |
| Cascading section updates (Offer, Unit, Business) | Per-subclass section mapping | None |
| Product-driven entity creation | Onboarding -> SourceVideographer | None |
| Default dependency/dependent wiring | Process.default_dependencies/dependents | None (SaveSession has primitives) |
| Pipeline auto-completion | Pipeline.init_process() | None |
| Duplicate process detection | ProcessManager._check_for_existing_process | None |
| Campaign activation/deactivation | Month1, Retention, Reactivation, AccountError | None |
| AI comment summaries | Consultation/Service.ai_comment_summary | None |
| Field seeding from trigger task | Process._init_fields() with threaded field processing | PipelineConversionRule.FieldSeeder (limited) |

#### Subclass-Specific Fields Beyond Common Fields

| Subclass | Extra Fields |
|---|---|
| Outreach | `contact_email`, `contact_phone`, `contact_url` |
| Onboarding | `client_goal_mrr`, `asset_edit_comments`, `current_revenue_growth`, `client_current_mrr`, `goal_revenue_growth` |
| SourceVideographer | `city`, `state`, `contractor_cost`, `sourcing_ad_spend`, `client_invoice`, `shoot_date` |
| AssetEdit | `asset_approval`, `asset_id`, `editor`, `reviewer`, `offer_id`, `raw_assets`, `review_all_ads`, `score`, `specialty`, `template_id`, `videos_paid` |
| Implementation | Uses `_default_rep = InternalRole.SUCCESS` |
| Month1 | Uses `_default_rep = InternalRole.SUCCESS`, hardcoded `priority = "High"` |
| Retention | Uses `_default_rep = InternalRole.SUCCESS` |

The microservice's composition pattern (all fields on single Process class) covers Sales, Onboarding, and Implementation fields via descriptor groups but does NOT cover SourceVideographer, AssetEdit, or Consultation fields.

---

## Key Findings for Phase 3

### What the Workflow Resolution Platform Must Support

1. **Lifecycle transition routing**: The full DAG of converted/did_not_convert routes across 9+ pipeline stages
2. **Conditional entity creation**: Products-driven SourceVideographer and Implementation-triggered BackendOB/AssetEdit
3. **Cascading state updates**: Section propagation to Offer, Unit, and Business during transitions
4. **Product synchronization**: Bidirectional product list management between Process and Unit
5. **Pipeline auto-completion**: Earlier stages complete when later stages begin
6. **Campaign lifecycle**: Activation (Month1), deactivation (Retention/Reactivation), reactivation (AccountError)

### What the Platform Should Improve Over Legacy

1. **Resolution strategy**: Replace deep isinstance chains with a strategy registry
2. **Error handling**: Replace QUIET flag with structured resolution results
3. **Field defaults**: Replace string-path evaluation with typed, validated configuration
4. **Concurrency**: Replace thread-unsafe mutable state with immutable snapshots
5. **API budgets**: Add depth limits and circuit breakers to resolution chains
6. **Dead code**: Start clean without commented-out debug code
7. **Retry logic**: Use proper async retry with exponential backoff

### Open Questions for Phase 3

1. **Campaign control API**: The legacy calls `offer.deactivate_campaign()` and `offer.ad_manager.activate()`. What is the microservice equivalent? Is there an ad management client?

2. **Consultation types**: The legacy ProcessManager maps 20+ action names to the Consultation project. How many consultation types actually exist and which are actively used?

3. **DNA play routing**: The DnaManager routes `play_*` tags to BackendClientSuccessDna project. How many DNA play types exist beyond BackendOnboardABusiness?

4. **AssetEdit template matching**: The legacy has sophisticated template selection based on vertical + specialty + existing template assets. How should this be represented in the new platform?

5. **Expansion pipeline**: This is a minimal placeholder in legacy (no overrides). Is it actively used or deprecated?

6. **Self-loop transitions**: Outreach.did_not_convert routes to route_outreach (creates another Outreach). Reactivation.did_not_convert routes to route_reactivation. Is this intentional behavior or should there be a limit?
