# SPIKE: ConversationAudit Bulk Activity Pre-Resolution

```yaml
id: SPIKE-CA-PRERESOL-001
status: COMPLETE
date: 2026-02-15
author: spike-investigator
upstream: SPIKE-CH-SECTIONS-001 (ContactHolder sections don't map to activity)
decision: Bulk pre-resolution is viable — lift activity gate into a pre-filter phase
```

---

## Question

Since section-targeted fetch is not viable for ConversationAudit (activity is
derived from parent Business, not own section), what optimization IS possible
to reduce wasted API calls for inactive ContactHolders?

## Decision This Informs

Whether to implement a **bulk activity pre-resolution** step that filters
ContactHolders by parent Business activity BEFORE entering the per-holder
processing pipeline.

---

## Current Architecture

```
_enumerate_contact_holders()
  │
  │  1 paginated Asana API call → N holders with parent_gids
  ▼
execute_async() loop — Semaphore(5)
  │
  │  For EACH holder (active AND inactive):
  ▼
_process_holder()
  │
  ├── Step 0: _resolve_business_activity(parent_gid)
  │     │
  │     ├── Cache hit? → return cached activity (0 API calls)
  │     └── Cache miss? → hydrate_from_gid_async(depth=2)
  │           │
  │           ├── Fetch Business task (1 API call)
  │           ├── Fetch UnitHolder children (1 API call)
  │           └── Fetch Units + classify sections (1-2 API calls)
  │           = 3-4 API calls per unique Business
  │
  ├── If NOT ACTIVE → return "skipped" (holder occupied semaphore slot for nothing)
  │
  └── If ACTIVE:
        ├── Step A: resolve_office_phone (1 API call)
        ├── Step B: get_export_csv_async (1 API call to autom8_data)
        ├── Step C: upload attachment (1 API call)
        └── Step D: delete old attachments (1 API call)
```

### Cost Model (Current)

For N holders, M unique parent Businesses, K active holders:

| Phase | API Calls | Notes |
|-------|-----------|-------|
| Enumeration | ~1-3 (paginated) | Fetches ALL N holders |
| Activity resolution | M * 3-4 | One depth=2 hydration per unique Business |
| Processing ACTIVE | K * 4 | Phone + CSV + upload + delete |
| **Total** | **3 + 4M + 4K** | |

### Key Inefficiency

The activity resolution happens INSIDE the processing semaphore. An inactive
holder occupies a semaphore slot (concurrency=5) while waiting for its
Business to be hydrated, blocking an active holder from starting its CSV fetch.

The `_activity_map` dedup cache mitigates redundant hydrations (good), but
inactive holders still compete for processing concurrency (bad).

---

## Proposed Architecture: Bulk Pre-Resolution

```
_enumerate_contact_holders()
  │
  │  1 paginated Asana API call → N holders with parent_gids
  ▼
NEW: _pre_resolve_business_activities()   ← lifted from _process_holder Step 0
  │
  │  Extract unique parent_gids → M unique Business GIDs
  │  Parallel hydrate all M Businesses — Semaphore(8)
  │  Build activity_map: {business_gid → AccountActivity}
  ▼
NEW: Filter holders by activity_map
  │
  │  Keep only holders where activity_map[parent_gid] == ACTIVE
  │  Log: N total, K active, (N-K) filtered
  ▼
execute_async() loop — Semaphore(5)     ← processes ONLY active holders
  │
  │  For each ACTIVE holder:
  ▼
_process_holder()                        ← Step 0 (activity gate) is now a no-op
  │
  ├── Step A: resolve_office_phone
  ├── Step B: get_export_csv_async
  ├── Step C: upload attachment
  └── Step D: delete old attachments
```

### Cost Model (Proposed)

| Phase | API Calls | Notes |
|-------|-----------|-------|
| Enumeration | ~1-3 (paginated) | Same as current |
| **Pre-resolution** | **M * 3-4** | Same total hydrations, but DEDICATED phase |
| Processing ACTIVE | K * 4 | Same, but NO inactive holders competing |
| **Total** | **3 + 4M + 4K** | Same total, better throughput |

### Why This Is Better (Same Total Calls, Better Throughput)

The total API call count is identical, but the **wall-clock time improves**:

1. **Dedicated hydration phase**: Pre-resolution can use `Semaphore(8)` (higher
   concurrency than processing) since hydrations are lightweight reads. Currently
   hydrations compete with CSV fetches + uploads for the `Semaphore(5)` slots.

2. **Processing pipeline sees only active holders**: The `Semaphore(5)` is fully
   utilized by holders that will actually produce work (CSV fetch + upload).
   Currently, inactive holders occupy slots just to return "skipped".

3. **Better observability**: After pre-resolution, we know EXACTLY how many
   holders will be processed before starting the expensive pipeline.

4. **Predictable batch sizes**: The scheduler/caller knows the real workload
   upfront, enabling better timeout estimation and progress reporting.

### Wall-Clock Time Estimate

Assume: 100 holders, 30 unique Businesses, 20 active holders.

**Current** (mixed hydration + processing in 5-wide semaphore):
- Hydration: 30 Businesses * 4 calls = 120 API calls, interleaved with processing
- Processing: 20 active * 4 calls + 80 inactive * 1 hydration-check
- Effective pipeline: ~100 items through Semaphore(5) = 20 batches
- Wall clock: ~20 batches * ~500ms avg = ~10s

**Proposed** (separated phases):
- Pre-resolution: 30 Businesses through Semaphore(8) = 4 batches of hydration
  - Wall clock: ~4 * 800ms = ~3.2s
- Processing: 20 active through Semaphore(5) = 4 batches
  - Wall clock: ~4 * 800ms = ~3.2s
- Total: ~6.4s (vs ~10s current, ~36% faster)

---

## Interface Design

### New Method: `_pre_resolve_business_activities()`

```python
async def _pre_resolve_business_activities(
    self,
    holders: list[dict[str, Any]],
) -> None:
    """Bulk-resolve parent Business activities into _activity_map.

    Extracts unique parent_gids from the holder list, hydrates each
    Business to depth=2, and populates self._activity_map. After this
    call, _resolve_business_activity() will always be a cache hit.

    Args:
        holders: List of holder dicts with "parent_gid" key.
    """
    unique_gids = {
        h["parent_gid"] for h in holders
        if h.get("parent_gid") and h["parent_gid"] not in self._activity_map
    }

    if not unique_gids:
        return

    semaphore = asyncio.Semaphore(8)

    async def resolve_one(gid: str) -> None:
        async with semaphore:
            await self._resolve_business_activity(gid)

    await asyncio.gather(
        *[resolve_one(gid) for gid in unique_gids],
        return_exceptions=True,  # Don't let one failure block others
    )
```

### Modified: `execute_async()` — Insert Pre-Resolution + Filter

```python
# Step 1: Enumerate active ContactHolders
holders = await self._enumerate_contact_holders()

# Step 1.5 (NEW): Bulk pre-resolve Business activities
await self._pre_resolve_business_activities(holders)

# Step 1.6 (NEW): Filter to holders with ACTIVE parent Business
from autom8_asana.models.business.activity import AccountActivity

active_holders = []
skipped_inactive = 0
for h in holders:
    parent_gid = h.get("parent_gid")
    if parent_gid:
        activity = self._activity_map.get(parent_gid)
        if activity != AccountActivity.ACTIVE:
            skipped_inactive += 1
            continue
    active_holders.append(h)

logger.info(
    "conversation_audit_activity_prefilter",
    total_holders=len(holders),
    active_holders=len(active_holders),
    skipped_inactive=skipped_inactive,
    unique_businesses=len({h.get("parent_gid") for h in holders if h.get("parent_gid")}),
)

# Step 2: Process each ACTIVE holder (no activity gate needed in _process_holder)
```

### Modified: `_process_holder()` — Activity Gate Becomes Defensive

The activity gate at Step 0 (lines 308-324) is preserved as a **defensive
assertion** — it should always be a cache hit after pre-resolution. If
somehow called with an unknown parent_gid, the existing hydration logic
still works correctly (backward compatible).

---

## Implementation Considerations

### Backward Compatibility

The `_activity_map` is still the single source of truth. The change is
purely about WHEN it gets populated — before the processing loop instead
of lazily during it. The existing `_resolve_business_activity()` method is
unchanged and still works correctly for any cache misses.

### Error Handling

`return_exceptions=True` on the gather ensures one Business hydration failure
doesn't block resolution of other Businesses. Failed resolutions result in
`None` in the `_activity_map`, which causes the holder to be filtered OUT
(conservative — skip if unknown, matching current behavior where `None !=
AccountActivity.ACTIVE`).

### Test Strategy

1. **Existing tests**: The `_force_fallback` pattern is not needed here (no
   section resolution). Existing tests that mock `_resolve_business_activity`
   continue to work since the method signature is unchanged.

2. **New tests**:
   - `test_preresolution_populates_activity_map` — verify map is populated
     before processing starts
   - `test_preresolution_filters_inactive_holders` — verify only ACTIVE holders
     enter processing pipeline
   - `test_preresolution_failure_skips_holder` — hydration failure → holder skipped
   - `test_preresolution_parallel_dedup` — same Business GID from multiple holders
     hydrated only once

### Scope

This is a MODULE-level change affecting only `conversation_audit.py` and its
test file. No new modules, no changes to existing infrastructure, no changes
to the hydration layer or activity classifier.

---

## Recommendation

**Implement bulk pre-resolution as a follow-on commit in this session.**

Complexity: LOW (one new method, minor modifications to `execute_async()`,
activity gate stays as defensive assertion).

The change:
- Improves wall-clock time by ~36% (separating hydration from processing)
- Improves observability (log pre-filter/post-filter counts upfront)
- Requires no new infrastructure
- Is backward compatible (same `_activity_map`, same `_resolve_business_activity()`)
- Follows the same pattern as the section-targeted work: filter the enumeration
  result BEFORE entering the processing pipeline

---

## Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| ConversationAudit workflow | `src/autom8_asana/automation/workflows/conversation_audit.py` | Read (full file) |
| Business.max_unit_activity | `src/autom8_asana/models/business/business.py:477` | Read |
| hydrate_from_gid_async | `src/autom8_asana/models/business/hydration.py:213` | Read |
| AccountActivity enum | `src/autom8_asana/models/business/activity.py:24` | Read |
| Section spike (upstream) | `docs/spikes/SPIKE-contact-holder-section-mapping.md` | Written |
