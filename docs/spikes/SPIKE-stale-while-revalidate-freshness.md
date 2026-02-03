# SPIKE: Wiring FreshnessCoordinator with Stale-While-Revalidate

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Complete |
| **Date** | 2026-02-03 |
| **Trigger** | Entity TTLs (offer: 180s, contact: 900s) configured but unenforced on query reads; daily Lambda warming means data is 0–24 hours stale |
| **Scope** | Research only (no production code) |

---

## 1. Question

How should we wire `FreshnessCoordinator` into the query read path so that entity-level TTLs are actually enforced, using stale-while-revalidate (SWR) to avoid blocking requests while cache refreshes?

## 2. Context

### The Gap

The system has entity-level TTLs configured in `config.py`:

```python
DEFAULT_ENTITY_TTLS = {
    "offer": 180,      # 3 minutes
    "contact": 900,    # 15 minutes
    "unit": 900,       # 15 minutes
    "business": 3600,  # 1 hour
}
```

These TTLs are **not enforced** on the query read path. The `DataFrameCache` uses a 12-hour TTL (`ttl_hours=12`) for DataFrame-level expiry, but the per-entity TTLs are only consumed by `TasksClient` (individual task caching) — a completely separate subsystem from the DataFrame query pipeline.

The actual data freshness depends entirely on when the cache warming Lambda last ran. If it runs daily, the query serves data that's 0–24 hours old regardless of what the entity TTLs say.

### What Currently Happens

```
POST /v1/query/offer/rows
    └─ DataFrameCache.get_async()
        ├─ memory_tier.get()
        │   └─ _is_valid(entry, current_watermark=None)
        │       ├─ Schema version check   ✓ enforced
        │       ├─ TTL check (12 HOURS)   ✓ enforced, but far too generous
        │       └─ Watermark check         ✗ skipped (current_watermark=None)
        │
        └─ On _is_valid() == True → return entry (even if 23 hours old)
```

The FreshnessCoordinator exists, is implemented, and supports three modes (IMMEDIATE, EVENTUAL, STRICT) — but nothing in the query path calls it.

## 3. Findings

### 3.1 Current Read Path (`dataframe_cache.py:197-272`)

```python
async def get_async(self, project_gid, entity_type, current_watermark=None):
    # 1. Circuit breaker check
    if self.circuit_breaker.is_open(project_gid):
        return None

    # 2. Memory tier
    entry = self.memory_tier.get(cache_key)
    if entry and self._is_valid(entry, current_watermark):
        return entry                    # ← Serves stale data
    else:
        self.memory_tier.remove(cache_key)

    # 3. S3 tier
    entry = await self.progressive_tier.get_async(cache_key)
    if entry and self._is_valid(entry, current_watermark):
        self.memory_tier.put(cache_key, entry)
        return entry                    # ← Serves stale data

    return None  # Cache miss → 503 CACHE_NOT_WARMED
```

**The problem is line 507-509 of `_is_valid()`**:
```python
ttl_seconds = self.ttl_hours * 3600    # 12 * 3600 = 43,200 seconds
if entry.is_stale(ttl_seconds):
    return False
```

A 12-hour TTL means offer data (which should be 3 minutes fresh) passes validation for 12 hours.

### 3.2 What _is_valid() Checks

| Check | Enforced | Gap |
|-------|----------|-----|
| Schema version | Yes | None — works correctly |
| TTL (12 hours) | Yes | Way too generous for entity-level freshness |
| Watermark | Skipped | `current_watermark` is never passed by callers |

### 3.3 FreshnessCoordinator Capabilities

The coordinator (`cache/freshness_coordinator.py`) provides batch staleness checks:

```python
async def check_batch_async(entries, mode=FreshnessMode.EVENTUAL) -> list[FreshnessResult]
```

Returns per-entry results with `action` field:
- `"use_cache"` — data is fresh, serve it
- `"extend_ttl"` — TTL expired but data version unchanged (API verified)
- `"fetch"` — data is stale, needs refresh

The `"extend_ttl"` action is exactly the SWR signal — the coordinator already contemplates serving stale data when the underlying data hasn't changed.

### 3.4 Existing Infrastructure for Background Refresh

| Component | Location | Reusable? |
|-----------|----------|-----------|
| `DataFrameCacheCoalescer` | `cache/dataframe/coalescer.py` | Yes — prevents duplicate builds |
| `asyncio.create_task()` | `main.py:214`, `coalescer.py:214` | Proven pattern |
| Lambda fire-and-forget | `admin.py:347` (`InvocationType="Event"`) | Yes — async Lambda invocation |
| `CircuitBreaker` | `cache/dataframe/circuit_breaker.py` | Yes — per-project failure isolation |
| `BackgroundTasks` (FastAPI) | `admin.py:378` | Alternative to `asyncio.create_task()` |

### 3.5 CacheEntry Metadata

```python
@dataclass
class CacheEntry:
    project_gid: str
    entity_type: str        # ← Can look up entity-level TTL
    dataframe: pl.DataFrame
    watermark: datetime     # ← max(modified_at) from source
    created_at: datetime    # ← Age calculation
    schema_version: str     # ← Schema invalidation
```

The entry has everything needed for SWR decisions: `entity_type` to look up the per-entity TTL, `created_at` for age, and `watermark` for version comparison.

## 4. Options

### Option A: Entity-TTL SWR in DataFrameCache (Recommended)

**Where**: `DataFrameCache._is_valid()` and `get_async()`

Replace the 12-hour flat TTL with entity-aware TTL + SWR grace window:

```python
def _is_valid(self, entry, current_watermark):
    # Schema check (unchanged)
    ...

    # Entity-aware TTL with SWR
    entity_ttl = get_entity_ttl(entry.entity_type)  # offer=180, contact=900
    swr_grace = entity_ttl * SWR_GRACE_MULTIPLIER   # e.g., 3x = serve up to 9 min for offer

    age = (datetime.now(UTC) - entry.created_at).total_seconds()

    if age <= entity_ttl:
        return True           # Fresh — serve immediately

    if age <= swr_grace:
        self._schedule_background_refresh(entry)
        return True           # Stale but within grace — serve + refresh

    return False              # Beyond grace — force rebuild (503)
```

**Characteristics**:
- Entity TTLs become operational, not decorative
- Offer data served fresh for 3 min, stale-but-refreshing for up to ~9 min, then 503
- Background refresh uses coalescer to prevent duplicate builds
- No API-level changes; transparent to callers

**Risk**: Background refresh in ECS competes with request-serving for CPU/memory. For offer entities with 180s TTL, during a busy period every ~3 minutes a background build fires.

### Option B: FreshnessCoordinator in Query Service Layer

**Where**: `services/query_service.py` `EntityQueryService.get_dataframe()`

Inject the coordinator between cache lookup and query execution:

```python
async def get_dataframe(self, entity_type, project_gid, client):
    df_entry = await cache.get_async(project_gid, entity_type)

    if df_entry is None:
        raise CacheNotWarmError(...)

    # NEW: Freshness check using FreshnessCoordinator
    freshness = await self.freshness_coordinator.check_batch_async(
        [df_entry], mode=FreshnessMode.EVENTUAL
    )
    if freshness[0].action == "fetch":
        self._schedule_rebuild(project_gid, entity_type)
        # Still return the stale DataFrame (SWR)

    return df_entry.dataframe
```

**Problem**: The FreshnessCoordinator checks individual task entries via Asana Batch API (`GET /batch` with `modified_at` checks). For a DataFrame with 22,836 rows, this would be thousands of API calls per query — completely impractical.

**Verdict**: Wrong level of granularity. The coordinator was designed for individual task freshness, not DataFrame-level freshness.

### Option C: Manifest-Age SWR (Lightweight)

**Where**: `DataFrameCache.get_async()` or progressive tier

Use the S3 manifest's `started_at` timestamp instead of CacheEntry metadata:

```python
manifest = await self.section_persistence.load_manifest(project_gid)
if manifest:
    age = (datetime.now(UTC) - manifest.started_at).total_seconds()
    entity_ttl = get_entity_ttl(entity_type)
    if age > entity_ttl:
        self._schedule_lambda_refresh(entity_type)
```

**Characteristics**:
- Uses existing manifest timestamps (no new metadata)
- Can trigger Lambda refresh instead of local build
- Adds S3 read (manifest) to every query — ~100ms overhead

**Drawback**: Manifest is S3 metadata, not in-memory. Adding an S3 read per query defeats the purpose of the memory tier. Would need to cache manifest metadata in memory.

### Option D: Scheduled Lambda Per Entity TTL (Infrastructure-Only)

No code changes. Configure EventBridge to run the warming Lambda at entity-appropriate intervals:

```terraform
# EventBridge rules per entity
resource "aws_cloudwatch_event_rule" "warm_offer" {
  schedule_expression = "rate(5 minutes)"  # offer TTL = 3 min + margin
}
resource "aws_cloudwatch_event_rule" "warm_contact" {
  schedule_expression = "rate(15 minutes)" # contact TTL = 15 min
}
resource "aws_cloudwatch_event_rule" "warm_business" {
  schedule_expression = "rate(60 minutes)" # business TTL = 1 hour
}
```

**Characteristics**:
- Zero code changes to ECS
- Entity freshness matches TTL by construction
- Lambda handles all rebuild work (no ECS CPU competition)
- Simple, predictable, easy to monitor

**Drawback**: Lambda runs whether data changed or not. For offer entities every 5 minutes, that's ~288 Lambda invocations/day. At ~2 min per build, that's ~576 Lambda-minutes/day. Cost depends on memory allocation but is likely $5-15/month — negligible.

## 5. Recommendation

**Option A (Entity-TTL SWR in DataFrameCache) combined with Option D (scheduled Lambda per entity).**

They address different failure modes and complement each other:

| Scenario | Option A Alone | Option D Alone | A + D Together |
|----------|---------------|---------------|----------------|
| Normal operation | SWR serves stale 3-9 min, background refresh | Lambda keeps data <5 min fresh | Lambda keeps it fresh; SWR is safety net |
| Lambda fails/delayed | SWR bridges the gap | Data goes stale until next run | SWR bridges, no user impact |
| ECS cold start | 503 until first build | Data already in S3 from Lambda | Best of both |
| High query volume | Background builds compete with requests | Lambda handles builds externally | Lambda does heavy lifting |

### Why Not Option B

The FreshnessCoordinator is designed for individual task staleness checks via Asana Batch API. Using it for DataFrame freshness would require thousands of API calls per query. It's the wrong granularity — DataFrame freshness should be checked at the manifest/entry level, not per-row.

The FreshnessCoordinator remains valuable for its original purpose: validating individual task cache entries during `UnifiedTaskStore` operations.

### Why Not Option C

Manifest-age checking adds S3 I/O to the hot query path. The CacheEntry already has `created_at` and `entity_type` — everything needed for entity-aware TTL. No need to go back to S3.

## 6. Implementation Sketch (Option A)

### Changes to `DataFrameCache`

```python
# New: Entity-aware TTL lookup
def _get_entity_ttl_seconds(self, entity_type: str) -> int:
    """Get TTL for entity type, falling back to DataFrame-level TTL."""
    from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL
    return DEFAULT_ENTITY_TTLS.get(entity_type, DEFAULT_TTL)

# New: SWR grace window
SWR_GRACE_MULTIPLIER: float = 3.0  # Serve stale up to 3x TTL

# Modified: _is_valid() splits into fresh/stale/expired
def _check_freshness(self, entry: CacheEntry, current_watermark) -> str:
    """Returns: 'fresh', 'stale_servable', or 'expired'."""
    # Schema check first
    if not self._schema_valid(entry):
        return "expired"

    entity_ttl = self._get_entity_ttl_seconds(entry.entity_type)
    grace_ttl = entity_ttl * SWR_GRACE_MULTIPLIER
    age = (datetime.now(UTC) - entry.created_at).total_seconds()

    if age <= entity_ttl:
        return "fresh"
    if age <= grace_ttl:
        return "stale_servable"     # SWR window
    return "expired"                 # Beyond grace

# Modified: get_async() handles SWR
async def get_async(self, project_gid, entity_type, current_watermark=None):
    entry = self.memory_tier.get(cache_key)
    if entry is not None:
        status = self._check_freshness(entry, current_watermark)
        if status == "fresh":
            return entry
        if status == "stale_servable":
            self._trigger_background_refresh(project_gid, entity_type)
            return entry  # Serve stale
        # "expired" → remove, fall through
        self.memory_tier.remove(cache_key)

    # Same for S3 tier...
    ...
```

### Background Refresh

```python
def _trigger_background_refresh(self, project_gid: str, entity_type: str):
    """Schedule non-blocking background refresh, deduped by coalescer."""
    cache_key = self._build_key(project_gid, entity_type)

    # Check if refresh already in progress
    if self.coalescer.is_building(cache_key):
        return

    asyncio.create_task(
        self._background_refresh_async(project_gid, entity_type),
        name=f"swr:{entity_type}:{project_gid}",
    )
```

### Files Modified

| File | Change | ~LOC |
|------|--------|------|
| `cache/dataframe_cache.py` | Entity-aware TTL, SWR check, background refresh | ~80 |
| `config.py` | `SWR_GRACE_MULTIPLIER` constant | ~5 |
| `tests/unit/cache/test_dataframe_cache.py` | SWR behavior tests | ~100 |

### Complexity

SCRIPT-to-MODULE. The core change is ~80 lines in `dataframe_cache.py`. The architecture is unchanged — this is a policy change within the existing cache read path.

## 7. Open Questions

1. **What triggers the background build?** Local async rebuild on ECS, or Lambda invocation? Local is simpler but competes for resources. Lambda is cleaner but adds ~60s latency before data is available.

2. **Should SWR grace be configurable per entity?** Offer might want 3x (9 min), business might want 1.5x (1.5 hours). Or a single multiplier is fine for simplicity.

3. **What about the progressive (S3) tier?** If memory expires but S3 still has data, the S3 entry was written by the last full build. Its age reflects build time, not data freshness. Is serving a 12-hour-old S3 entry with a 3-minute entity TTL acceptable during SWR?

4. **ECS cold start**: On fresh ECS deployment with empty memory, every first query hits S3 → hydrates memory. If S3 data is >entity TTL, SWR immediately triggers background refresh. This is a burst of N background refreshes (one per entity/project). Acceptable?

## 8. Follow-Up Actions

| Action | Priority | Effort |
|--------|----------|--------|
| Implement Option A (entity-TTL SWR in DataFrameCache) | P1 | MODULE (~200 LOC) |
| Configure Option D (EventBridge per-entity Lambda schedules) | P1 | SCRIPT (Terraform) |
| Add SWR observability (stale_served, refresh_triggered, refresh_completed) | P2 | SCRIPT (~20 LOC) |
| Evaluate FreshnessCoordinator role — keep for task-level, not DataFrame | P3 | Documentation |
