# ADR-0025: Big-Bang Migration Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team, User
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0017](ADR-0017-redis-backend-architecture.md)

## Context

The legacy autom8 system uses S3-backed caching (TaskCache). The new intelligent caching layer uses Redis exclusively. We must decide how to transition from S3 to Redis.

**Current state**:
- Production S3 cache contains task data for ~1M tasks
- autom8 services actively read/write S3 cache
- Cache hit rate ~85%

**Target state**:
- Redis cache contains task data
- S3 cache deprecated and decommissioned
- Same or better hit rate

**Migration options**:
1. **Big-bang**: Switch entirely to Redis on deployment
2. **Dual-read**: Read from both S3 and Redis, write to Redis only
3. **Gradual rollout**: Migrate by project/workspace incrementally

**User decision**: Big-bang cutover. Accept initial cache miss spike at deployment. No dual-read fallback.

**Requirements**:
- PRD-0002 Out of Scope: "Legacy autom8 migration: Cache data migration is not included; this is a big-bang cutover accepting cache miss spike at deployment"

## Decision

**Perform a big-bang cutover from S3 to Redis with no data migration. Accept 100% cache miss rate at deployment, relying on cache warming to rebuild.**

### Migration Timeline

```
T-7 days: Provision Redis infrastructure (ElastiCache)
T-3 days: Deploy SDK to staging with Redis
T-1 day:  Performance test in staging
T-0:      Production deployment (cutover)
T+15min:  Monitor cache warm-up
T+1hr:    Verify hit rate stabilizing
T+24hr:   Confirm normal operations
T+7 days: Decommission S3 cache
```

### Deployment Procedure

```
1. PRE-DEPLOYMENT
   ├── Verify ElastiCache cluster healthy
   ├── Confirm connection strings configured
   ├── Prepare rollback plan
   └── Notify stakeholders of expected performance dip

2. DEPLOYMENT (T-0)
   ├── Deploy new SDK version to all services
   ├── Services start using Redis (empty cache)
   └── Observe: 100% cache miss rate expected

3. WARM-UP (T+0 to T+15min)
   ├── Cache populates from API responses
   ├── Hit rate increases as tasks are accessed
   └── High-traffic tasks cache first

4. STABILIZATION (T+15min to T+1hr)
   ├── Hit rate should reach 50%+ within 30 min
   ├── Hit rate should reach 80%+ within 1 hour
   └── Alert if hit rate below 70% at T+1hr

5. VERIFICATION (T+1hr to T+24hr)
   ├── Confirm hit rate stable at >= 80%
   ├── Verify API call rates reduced
   ├── Check for errors in cache operations
   └── Monitor Redis memory usage

6. CLEANUP (T+7 days)
   ├── Disable S3 cache writes in legacy code
   ├── Archive S3 cache bucket (optional)
   └── Delete S3 cache bucket (final)
```

### Cache Warming Strategy

For high-traffic services, use `warm()` API post-deployment:

```python
# Post-deployment warming script
async def warm_high_traffic_tasks():
    """Pre-warm cache for frequently accessed tasks."""
    client = AsanaClient(...)

    # Get list of high-traffic project GIDs (from config or analytics)
    high_traffic_projects = [
        "project_gid_1",
        "project_gid_2",
        # ...
    ]

    for project_gid in high_traffic_projects:
        # Get all tasks in project
        tasks = [t async for t in client.projects.tasks(project_gid)]
        task_gids = [t.gid for t in tasks]

        # Warm cache for all entry types
        result = await client.cache.warm(
            gids=task_gids,
            entry_types=[
                EntryType.TASK,
                EntryType.SUBTASKS,
                EntryType.STORIES,
            ],
        )
        print(f"Warmed {result.success_count} tasks for project {project_gid}")
```

### Rollback Plan

If issues detected:

```
1. IMMEDIATE (< 5 min fix)
   └── Disable caching: CacheSettings.enabled = False
       └── SDK continues operating with NullCacheProvider
       └── All requests go to API (100% miss)

2. SHORT-TERM (< 30 min fix)
   └── Revert SDK deployment to previous version
       └── Services restore to S3 cache (if still functional)

3. INVESTIGATION
   └── Analyze cache event logs
   └── Review Redis metrics
   └── Identify root cause
   └── Fix and redeploy
```

### Monitoring Checklist

| Metric | Expected at T+0 | Expected at T+1hr | Alert Threshold |
|--------|-----------------|-------------------|-----------------|
| Cache hit rate | 0% | >= 80% | < 70% at T+1hr |
| Redis connection errors | 0 | 0 | > 0 sustained |
| API call rate | +100% vs baseline | Normal | > 150% at T+1hr |
| p99 latency | +50% vs baseline | Normal | > 200% at T+1hr |
| Redis memory | Growing | Stable | > 80% capacity |

## Rationale

**Why big-bang over dual-read?**

| Factor | Big-Bang | Dual-Read |
|--------|----------|-----------|
| Complexity | Low | High |
| Tech debt | None | S3 read code remains |
| Consistency | Single source of truth | Potential conflicts |
| Failure modes | Simple (Redis or nothing) | Complex (S3 vs Redis) |
| Migration length | Days | Weeks/months |
| Team effort | Low | High |

Dual-read introduces:
- Code to read from S3, check Redis, merge results
- Logic to decide which cache is authoritative
- Extended maintenance of S3 code path
- Potential for S3/Redis data inconsistency
- Longer deprecation timeline

**Why no data migration?**

S3 cache data is:
- Relatively small (serialized JSON)
- Quickly rebuilt from API
- Not critical (cache, not source of truth)
- Different format than Redis cache

Migrating data would require:
- ETL pipeline from S3 to Redis
- Format transformation
- Version alignment
- Complexity with marginal benefit

It's faster to accept initial misses than to build migration tooling.

**Why accept cache miss spike?**

Initial miss spike is:
- Temporary (~15-30 minutes to stabilize)
- Recoverable (each miss populates cache)
- Predictable (we know it will happen)
- Manageable (Asana rate limits are sufficient)

The alternative (complex migration) has longer-term costs.

## Alternatives Considered

### Alternative 1: Dual-Read Fallback

- **Description**: Read from both S3 and Redis during transition. If Redis miss, check S3. Write only to Redis.
- **Pros**:
  - Gradual transition
  - No initial miss spike
  - Rollback is just "use S3 only"
- **Cons**:
  - Complex read logic
  - S3 code must be maintained
  - Unclear deprecation timeline
  - Potential for S3/Redis conflicts
  - User explicitly rejected this approach
- **Why not chosen**: User decision. Complexity and tech debt outweigh smoother transition.

### Alternative 2: Data Migration ETL

- **Description**: Run ETL job to copy S3 cache data to Redis before cutover.
- **Pros**:
  - No cold cache at cutover
  - Warm start in Redis
  - Could migrate incrementally
- **Cons**:
  - Format transformation complexity
  - Potential data inconsistency during migration
  - ETL tooling to build and maintain
  - Time window where data could diverge
- **Why not chosen**: Engineering effort not justified. Cache rebuilds naturally.

### Alternative 3: Gradual Project Rollout

- **Description**: Migrate one project/workspace at a time to Redis.
- **Pros**:
  - Limited blast radius
  - Can pause if issues
  - Incremental validation
- **Cons**:
  - Requires project-level cache routing
  - Complex configuration management
  - Extended migration timeline
  - Dual-code-path maintenance
- **Why not chosen**: Adds complexity without significant risk reduction. Big-bang with rollback is simpler.

### Alternative 4: Shadow Mode

- **Description**: Write to Redis in parallel with S3 for weeks, validate, then switch reads.
- **Pros**:
  - Validates Redis behavior before cutover
  - Can compare hit rates
  - Low risk cutover
- **Cons**:
  - Double write overhead
  - Extended timeline
  - Still need cutover moment
  - Validation effort
- **Why not chosen**: Extends migration timeline significantly. Cache behavior is straightforward to validate in staging.

### Alternative 5: Feature Flag Rollout

- **Description**: Feature flag controls percentage of traffic using Redis.
- **Pros**:
  - Gradual rollout (1%, 10%, 50%, 100%)
  - Can rollback by flag
  - A/B testing possible
- **Cons**:
  - Complex traffic splitting
  - Potential for cache incoherence
  - Feature flag infrastructure required
  - Doesn't eliminate dual-code-path
- **Why not chosen**: Overkill for cache migration. Simpler to deploy and monitor.

## Consequences

### Positive

- **Clean cutover**: No legacy S3 code in new system
- **Simple architecture**: Single cache backend
- **Fast execution**: Days instead of weeks
- **Low effort**: No migration tooling to build
- **No tech debt**: S3 code removed completely

### Negative

- **Initial performance dip**: 100% miss at T+0
- **API load spike**: All requests hit API initially
- **User-visible latency**: Operations slower during warm-up
- **Monitoring required**: Active observation during cutover
- **No instant rollback to warm cache**: Rollback means S3 (if still functional)

### Neutral

- **S3 data discarded**: Cache data not preserved (acceptable)
- **Warm API provided**: Consumers can pre-warm if needed
- **Timeline flexibility**: Cutover date is deployment choice

## Compliance

To ensure this decision is followed:

1. **Pre-deployment checklist**:
   - [ ] ElastiCache cluster provisioned and healthy
   - [ ] Connection strings configured in all environments
   - [ ] Rollback plan documented and reviewed
   - [ ] Stakeholders notified of expected performance impact

2. **Deployment checklist**:
   - [ ] Deploy to staging first
   - [ ] Verify cache operations in staging
   - [ ] Deploy to production during low-traffic window
   - [ ] Monitor hit rate recovery

3. **Post-deployment checklist**:
   - [ ] Confirm hit rate >= 80% within 1 hour
   - [ ] Verify API call rates normalized
   - [ ] Check for cache operation errors
   - [ ] Schedule S3 cache decommissioning

4. **Rollback criteria**:
   - Redis connection failures > 1 minute
   - Hit rate < 50% after 2 hours
   - API rate limit exhaustion
   - User-reported latency issues
