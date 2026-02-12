# MOONSHOT-dataframe-materialization

## Executive Summary

This document stress-tests five DataFrame materialization architectures against plausible 2-year futures: 10x scale, real-time requirements, multi-region deployment, cost pressure, and Asana API evolution. Each option represents a distinct philosophy--from stateless simplicity (Option A) to event-driven sophistication (Option D) to pragmatic hybrid approaches (Option E).

**Key Insight**: The optimal choice depends less on today's requirements and more on which future arrives first. Option E (Hybrid S3 cold + Redis hot + incremental sync) provides the best balance of immediate simplicity, scale headroom, and pivot flexibility. It is the only option that performs acceptably across all scenarios without requiring fundamental re-architecture.

**Time Horizon**: 2 years (2026-2027)

**Recommendation**: Proceed with Option E (Hybrid), implemented in phases that allow course-correction as signals materialize.

---

## Current State

### Architecture Overview

```
                        Current DataFrame Architecture

    ┌─────────────────────────────────────────────────────────────────┐
    │                       autom8_asana SDK                          │
    ├─────────────────────────────────────────────────────────────────┤
    │  DataFrame Layer (Polars)                                       │
    │  - Schema-driven extraction (BASE, UNIT, CONTACT schemas)       │
    │  - Type coercion with logging                                   │
    │  - LAZY_THRESHOLD = 100 tasks                                   │
    │  - ProjectDataFrameBuilder, SectionDataFrameBuilder             │
    └───────────────┬─────────────────────────────────────────────────┘
                    │
    ┌───────────────▼─────────────────────────────────────────────────┐
    │  Two-Tier Cache (ADR-0047)                                      │
    │  ├─ Redis (Hot Tier)                                            │
    │  │   - Modification timestamps, active metadata                 │
    │  │   - TTL: 1-24h, Size: ~100MB                                 │
    │  └─ S3 (Cold Tier)                                              │
    │      - Full task snapshots, STRUC data, DataFrames              │
    │      - TTL: 7-30d, Size: 1GB+                                   │
    │      - Parquet format for project dataframes                    │
    └───────────────┬─────────────────────────────────────────────────┘
                    │
    ┌───────────────▼─────────────────────────────────────────────────┐
    │  Asana API                                                      │
    │  - Rate limit: 1500 req/min                                     │
    │  - Per-entity TTLs (business: 1h, process: 1min)                │
    │  - No native change detection (polling required)                │
    └─────────────────────────────────────────────────────────────────┘
```

### Key Constraints

| Constraint | Current State | Impact on Materialization |
|------------|---------------|---------------------------|
| **Scale** | 100K tasks, 4 entity types | Cold start = seconds, not minutes |
| **Freshness SLA** | Hourly batch refresh | Can tolerate staleness |
| **Infrastructure** | AWS ECS, S3, Redis, Lambda | All options technically feasible |
| **Rate Limit** | 1500 req/min (Asana) | Cannot brute-force rebuild |
| **Cache Durability** | S3 survives restarts | Rebuild cost = hours without cache |

### Technical Debt Affecting Future

| Debt | Impact on Materialization |
|------|---------------------------|
| No webhook infrastructure | Options C/D require new capability |
| Polars-only output | S3 Parquet alignment is natural |
| Per-project cache keys | Multi-tenant complexity not addressed |
| Sync-first API | Async materialization requires wrapper |

---

## Scenario Definition

### Scenario 1: 10x Scale (High Probability)

**Probability**: High (60%)
**Impact if True**: High

The business grows to 1M+ tasks across 10+ entity types with multiple workspaces/tenants.

**Assumptions**:
- Linear growth in task count over 2 years
- New entity types added (Address, Hours, custom verticals)
- Multiple Asana workspaces for tenant isolation
- No change to Asana rate limits

**Observable Signals**:
1. Task count exceeds 500K (halfway trigger)
2. DataFrame build time exceeds 10 seconds (UX degradation)
3. Redis memory usage exceeds 500MB (cost inflection)
4. Rate limit violations exceed 50/day (capacity constraint)

---

### Scenario 2: Real-Time Requirements (Medium Probability)

**Probability**: Medium (35%)
**Impact if True**: Critical

Business demands sub-minute freshness instead of hourly. Sales pipeline visibility requires near-instant sync.

**Assumptions**:
- SLA tightens from 1 hour to <1 minute
- Users expect "live" dashboards
- Competitive pressure drives requirement
- Willing to invest in infrastructure

**Observable Signals**:
1. User complaints about stale data exceed 5/month
2. Competitor launches real-time Asana integration
3. Sales leadership requests "live pipeline view"
4. Business case approved for real-time infrastructure

---

### Scenario 3: Multi-Region Deployment (Low Probability)

**Probability**: Low (20%)
**Impact if True**: Critical

Expansion to EU and APAC requires data residency compliance. Global cache consistency becomes a challenge.

**Assumptions**:
- GDPR or similar regulation triggers requirement
- Data must not leave region (tasks, caches)
- Latency requirements for each region
- 3x infrastructure cost acceptable

**Observable Signals**:
1. EU customer contract includes data residency clause
2. Legal requests data residency policy documentation
3. Sales opportunity lost due to data residency
4. AWS announces region-specific data controls

---

### Scenario 4: Cost Pressure (Medium Probability)

**Probability**: Medium (40%)
**Impact if True**: High

Budget constraints force optimization. Infrastructure costs scrutinized at board level.

**Assumptions**:
- 30%+ cost reduction required
- Performance cannot degrade significantly
- Engineering time is "free" (already budgeted)
- Cloud spend visible at executive level

**Observable Signals**:
1. Monthly AWS bill exceeds $5K for cache infrastructure
2. CFO requests infrastructure cost breakdown
3. Company-wide cost reduction initiative announced
4. Redis/ElastiCache identified as top 3 spend category

---

### Scenario 5: Asana API Evolution (Medium Probability)

**Probability**: Medium (30%)
**Impact if True**: High

Asana introduces GraphQL, streaming API, or significantly improves webhook reliability.

**Assumptions**:
- Asana invests in developer experience
- New API is significantly better for our use case
- Migration effort required but worthwhile
- Backward compatibility maintained for 2+ years

**Observable Signals**:
1. Asana announces GraphQL API beta
2. Asana launches webhook reliability SLA (>99.9%)
3. Asana introduces streaming/change feed API
4. Asana raises rate limits significantly (>5000/min)

---

## Materialization Options

### Option A: S3 Parquet + Startup Load

**Philosophy**: Simplest possible architecture. Pre-compute DataFrames, store in S3, load at application startup.

**Architecture**:
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Scheduled Job  │────▶│   S3 Parquet    │────▶│   App Startup   │
│  (hourly build) │     │   (per entity)  │     │   (load to mem) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Characteristics**:
- Build: Scheduled Lambda/ECS task builds DataFrames hourly
- Store: Parquet files in S3 (natural fit for Polars)
- Load: Application loads DataFrames at startup
- Refresh: Restart or explicit reload command

---

### Option B: Lambda + EventBridge Scheduled Refresh

**Philosophy**: Serverless, event-driven refresh. Lambda builds DataFrames on schedule, stores in S3/Redis.

**Architecture**:
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  EventBridge    │────▶│     Lambda      │────▶│  S3 + Redis     │
│  (cron trigger) │     │  (build logic)  │     │  (dual write)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Asana API     │
                        │   (fetch data)  │
                        └─────────────────┘
```

**Characteristics**:
- Trigger: EventBridge cron (every hour, every 15 min, etc.)
- Compute: Lambda function with 15-minute timeout
- Store: S3 for persistence, Redis for hot access
- Scale: Parallel Lambda invocations for different entity types

---

### Option C: Redis Pub/Sub + Background Worker

**Philosophy**: Push-based architecture. Changes published to Redis, background workers maintain materialized views.

**Architecture**:
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   App Writes    │────▶│  Redis Pub/Sub  │────▶│ Background Wkr  │
│   (mutations)   │     │   (channels)    │     │ (materialize)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Redis + S3     │
                                                │  (store frames) │
                                                └─────────────────┘
```

**Characteristics**:
- Publish: SaveSession commits publish change events
- Subscribe: Background worker receives and processes
- Materialize: Incremental DataFrame updates
- Consistency: Eventually consistent with mutation order

---

### Option D: Webhook-Driven Invalidation + Lazy Rebuild

**Philosophy**: Event-sourced architecture. Asana webhooks drive invalidation, lazy rebuild on demand.

**Architecture**:
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Asana Webhooks  │────▶│  Invalidation   │────▶│  Cache Layer    │
│   (push)        │     │   Service       │     │  (mark stale)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Lazy Rebuild   │
                                                │  (on access)    │
                                                └─────────────────┘
```

**Characteristics**:
- Trigger: Asana webhooks notify of changes
- Invalidate: Mark affected cache entries as stale
- Rebuild: Lazy (on next access) or eager (background)
- Freshness: Near real-time (webhook latency only)

---

### Option E: Hybrid (S3 Cold + Redis Hot + Incremental Sync)

**Philosophy**: Pragmatic combination. S3 for durable baseline, Redis for hot data, incremental sync for freshness.

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────┐
│                      Hybrid Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │   S3 Cold   │───▶│ Redis Hot   │◀───│ Incremental │        │
│   │  (baseline) │    │  (working)  │    │    Sync     │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  ▲                   │                 │
│         │                  │                   │                 │
│         ▼                  │                   ▼                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │  Scheduled  │    │   On-Read   │    │  Mutation   │        │
│   │   Rebuild   │    │  Promotion  │    │   Capture   │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Characteristics**:
- Baseline: S3 Parquet rebuilt on schedule (daily/hourly)
- Hot Cache: Redis with recent changes overlay
- Incremental: SaveSession mutations update Redis immediately
- Promotion: S3 data promoted to Redis on first access
- Merge: Query combines S3 baseline with Redis delta

---

## Scenario Impact Matrix

Rate each option 1-5 against each scenario (5 = handles well, 1 = breaks or requires re-architecture).

| Scenario | A: S3+Startup | B: Lambda+EB | C: Redis Pub/Sub | D: Webhook | E: Hybrid |
|----------|---------------|--------------|------------------|------------|-----------|
| **1. 10x Scale** | 2 | 3 | 3 | 4 | 4 |
| **2. Real-Time** | 1 | 2 | 4 | 5 | 3 |
| **3. Multi-Region** | 4 | 3 | 2 | 2 | 3 |
| **4. Cost Pressure** | 5 | 4 | 2 | 3 | 4 |
| **5. API Evolution** | 3 | 3 | 2 | 4 | 4 |
| **Weighted Score** | 2.8 | 3.0 | 2.7 | 3.6 | 3.7 |

*Weights: Scale (0.3), Real-Time (0.2), Multi-Region (0.1), Cost (0.2), API Evolution (0.2)*

### Detailed Analysis

#### Scenario 1: 10x Scale

| Option | Rating | Rationale |
|--------|--------|-----------|
| A | 2 | Startup load of 10M-row DataFrame takes minutes. Memory footprint unsustainable. |
| B | 3 | Lambda timeout (15min) may not complete. Fan-out pattern adds complexity. |
| C | 3 | Redis memory costs scale linearly. Pub/Sub throughput may bottleneck. |
| D | 4 | Webhook volume manageable. Lazy rebuild distributes load. |
| E | 4 | S3 scales infinitely. Redis holds only hot data subset. Incremental sync bounded. |

#### Scenario 2: Real-Time Requirements

| Option | Rating | Rationale |
|--------|--------|-----------|
| A | 1 | Hourly batches fundamentally incompatible. Would require complete re-architecture. |
| B | 2 | Can reduce schedule to 1 minute, but Lambda cold start adds latency. Not truly real-time. |
| C | 4 | Pub/Sub latency is sub-second. Background worker can process immediately. |
| D | 5 | Webhook-driven is inherently real-time (within Asana's webhook latency). |
| E | 3 | Incremental sync captures own mutations instantly. External changes need polling or webhook addon. |

#### Scenario 3: Multi-Region Deployment

| Option | Rating | Rationale |
|--------|--------|-----------|
| A | 4 | S3 replication is native. Per-region startup load is straightforward. |
| B | 3 | Per-region Lambda + S3 works. EventBridge routing adds complexity. |
| C | 2 | Redis Global Tables (ElastiCache) expensive. Pub/Sub doesn't cross regions. |
| D | 2 | Webhooks need per-region endpoints. Asana doesn't support regional delivery. |
| E | 3 | S3 replicates easily. Redis per-region with regional baseline. |

#### Scenario 4: Cost Pressure

| Option | Rating | Rationale |
|--------|--------|-----------|
| A | 5 | S3 storage is $0.023/GB. No running compute. Minimal cost. |
| B | 4 | Lambda pay-per-use. S3 storage. No idle compute. |
| C | 2 | Redis/ElastiCache is expensive ($0.068/GB-hour). Always-on worker. |
| D | 3 | Webhook receiver needs always-on. Storage costs moderate. |
| E | 4 | S3 for bulk, Redis only for hot data. Right-sizes each tier. |

#### Scenario 5: API Evolution

| Option | Rating | Rationale |
|--------|--------|-----------|
| A | 3 | GraphQL would help batch builds. Streaming would require architecture change. |
| B | 3 | Similar to A. Lambda isolation limits benefit. |
| C | 2 | Architecture assumes REST polling. New APIs would require significant rework. |
| D | 4 | Better webhooks directly benefit. GraphQL/streaming natural evolution. |
| E | 4 | Modular design allows incremental adoption. Sync layer can swap implementations. |

---

## Architecture Evolution Paths

### Option A: S3 Parquet + Startup Load

**Year 1**: Works well for current scale. Simple to operate.

**Year 2 (10x Scale)**:
- Startup time becomes unacceptable (minutes)
- Must partition DataFrames by entity type, workspace
- Memory pressure forces lazy loading
- Effectively evolves toward Option E

**Year 2 (Real-Time)**:
- Fundamental mismatch. Must abandon and rebuild.
- No evolutionary path exists.

### Option B: Lambda + EventBridge

**Year 1**: Clean separation. Easy to adjust refresh frequency.

**Year 2 (10x Scale)**:
- Lambda timeout forces partitioning strategy
- Step Functions for orchestration
- Cost remains reasonable

**Year 2 (Real-Time)**:
- Can push schedule to 1-minute intervals
- Still not true real-time (60-second lag minimum)
- Would need webhook addon for sub-minute

### Option C: Redis Pub/Sub + Background Worker

**Year 1**: Low latency for internal mutations. Elegant event-driven model.

**Year 2 (10x Scale)**:
- Redis memory costs escalate significantly
- Must add S3 tier for cold data (evolves toward E)
- Worker scaling complexity increases

**Year 2 (Real-Time)**:
- Already real-time for internal mutations
- External changes require polling or webhooks
- Natural fit for webhook integration

### Option D: Webhook-Driven Invalidation

**Year 1**: Requires significant investment in webhook infrastructure.

**Year 2 (10x Scale)**:
- Webhook volume manageable (Asana batches)
- Lazy rebuild distributes compute load
- May need eager rebuild for frequently accessed entities

**Year 2 (Real-Time)**:
- Inherently real-time. No evolution needed.
- Asana webhook reliability is the constraint

### Option E: Hybrid

**Year 1**: Moderate complexity, but all pieces exist (S3, Redis, SaveSession hooks).

**Year 2 (Any Scenario)**:
- S3 baseline handles scale
- Redis hot tier handles real-time for active data
- Incremental sync provides mutation capture
- Can add webhooks as incremental improvement
- Can adjust tier sizing for cost

---

## Technology Discontinuities

What paradigm shifts could make each option obsolete?

| Discontinuity | A | B | C | D | E | Risk Level |
|---------------|---|---|---|---|---|------------|
| **Asana streaming API** | Obsolete | Obsolete | Adapt | Benefit | Adapt | Medium |
| **eBPF cache invalidation** | N/A | N/A | Obsolete | Adapt | Adapt | Low |
| **Serverless databases (Neon, PlanetScale)** | N/A | Enhance | Obsolete | N/A | Adapt | Low |
| **Edge compute (CloudFlare Workers, Deno Deploy)** | Enhance | Adapt | Complex | Complex | Adapt | Medium |
| **AI-driven prefetch/prediction** | Enhance | Enhance | Enhance | Enhance | Enhance | Medium |

**Analysis**:

1. **Asana Streaming API**: If Asana launches a change feed, Options A and B become inefficient (polling when push is available). Options D and E adapt naturally.

2. **eBPF Cache Invalidation**: Kernel-level observability could obsolete application-level pub/sub (Option C). Others unaffected.

3. **Serverless Databases**: Options relying on always-on Redis could migrate to serverless. Option C's pub/sub doesn't translate well.

4. **Edge Compute**: Multi-region materialization at edge favors S3-backed options (A, B, E) over Redis-dependent (C, D).

5. **AI Prefetch**: All options benefit from predictive cache warming. No obsolescence risk.

---

## Migration Flexibility Analysis

**Question**: Which option provides easiest pivot if requirements change dramatically?

| Option | Pivot to Scale | Pivot to Real-Time | Pivot to Cost | Exit Complexity |
|--------|----------------|--------------------|--------------|--------------------|
| A | Medium | Very Hard | Easy | Low |
| B | Medium | Medium | Easy | Low |
| C | Hard | Easy | Hard | Medium |
| D | Easy | Already There | Medium | High |
| E | Easy | Medium | Easy | Medium |

### Option E Migration Flexibility Deep Dive

**Pivot to Scale (10x)**:
- S3 tier: No changes needed (scales infinitely)
- Redis tier: Reduce TTL, increase eviction aggressiveness
- Incremental sync: Add partitioning by workspace
- **Effort**: Low (configuration changes)

**Pivot to Real-Time**:
- Add webhook receiver service
- Change invalidation from polling to event-driven
- Redis tier already supports immediate updates
- **Effort**: Medium (new webhook infrastructure)

**Pivot to Cost Reduction**:
- Reduce Redis tier size (promote less aggressively)
- Increase S3 baseline rebuild frequency
- Remove incremental sync (accept staleness)
- **Effort**: Low (configuration changes)

---

## Technical Debt Trajectory

Which option accumulates least debt over 2 years?

| Option | Year 1 Debt | Year 2 Debt | Debt Drivers |
|--------|-------------|-------------|--------------|
| A | Low | High | Scale workarounds, memory hacks |
| B | Low | Medium | Lambda partitioning, orchestration |
| C | Medium | High | Redis cost optimization, pub/sub reliability |
| D | High | Medium | Webhook infrastructure built properly |
| E | Medium | Low | Modular components, clear upgrade paths |

### Analysis

**Option A**: Starts clean but accumulates debt quickly as scale forces workarounds (lazy loading, partitioning, memory mapping).

**Option B**: Lambda isolation keeps debt contained, but orchestration complexity grows with entity types.

**Option C**: Pub/Sub reliability requires careful handling. Redis cost pressure forces tier optimization hacks.

**Option D**: High initial investment in webhook infrastructure pays off. Well-designed event system has low ongoing debt.

**Option E**: Modular design means each component can be upgraded independently. Clear boundaries prevent cross-cutting debt.

---

## Risk Analysis

### Scenario Risks

| Risk | Probability | Impact | Options Affected | Mitigation |
|------|-------------|--------|------------------|------------|
| Asana deprecates current API | Low | Critical | All | Thin wrapper, not deep integration |
| Redis cost exceeds budget | Medium | High | C, D, E | S3-heavy variants, tier sizing |
| Webhook reliability <99% | High | Medium | D | Hybrid approach, polling backup |
| Cold start latency unacceptable | Medium | High | A, B | Warm pool, lazy load, hybrid |
| Multi-tenant isolation required | Medium | High | C | Per-tenant Redis, namespace isolation |

### Execution Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Underestimate integration complexity | Medium | Medium | Spike first, time-box |
| Team unfamiliar with chosen stack | Low | Medium | Stick with known tech (S3, Redis) |
| Production rollout breaks existing | Medium | High | Feature flags, shadow mode |
| Performance doesn't meet SLA | Medium | High | Benchmarks before commit |

---

## Investment Summary

| Option | Initial Build | Year 1 Ops | Year 2 Ops | Total 2Y |
|--------|---------------|------------|------------|----------|
| A | 2 weeks | Low | Medium | $15K |
| B | 3 weeks | Low | Low | $20K |
| C | 4 weeks | Medium | High | $45K |
| D | 6 weeks | Medium | Medium | $50K |
| E | 4 weeks | Medium | Low | $35K |

*Assumes: 1 FTE @ $150K/year, AWS costs at current scale, ops = maintenance + incident response*

---

## Recommendation

### Primary: Option E (Hybrid)

**Rationale**:

1. **Best Weighted Score (3.7)**: Performs acceptably across all scenarios without critical failures in any.

2. **Lowest Technical Debt Trajectory**: Modular design means components can be upgraded independently.

3. **Highest Migration Flexibility**: Easy pivots to scale, cost, or real-time as signals emerge.

4. **Builds on Existing Infrastructure**: S3 + Redis two-tier cache (ADR-0047) already implemented.

5. **No Regrets Decision**: If any scenario arrives in 18 months, Option E is either adequate or easily extensible.

### Implementation Phases

#### Phase 1: Foundation (Q1 2026) - 2 weeks
**Goal**: Establish S3 baseline materialization

**Deliverables**:
- Scheduled ECS task for DataFrame build
- S3 Parquet storage for materialized DataFrames
- Startup load with S3 fallback

**Investment**: 2 person-weeks
**Reversibility**: Two-Way Door (additive, can disable)

#### Phase 2: Hot Tier (Q1 2026) - 1 week
**Goal**: Redis overlay for recent changes

**Deliverables**:
- SaveSession hook for mutation capture
- Redis delta storage (DataFrameCacheIntegration extended)
- Merge logic for baseline + delta

**Investment**: 1 person-week
**Reversibility**: Two-Way Door (feature flag)

#### Phase 3: Observability (Q2 2026) - 1 week
**Goal**: Understand cache effectiveness

**Deliverables**:
- Hit/miss metrics per tier
- Freshness distribution (age of served data)
- Cold start latency dashboard

**Investment**: 1 person-week
**Reversibility**: Two-Way Door (metrics are additive)

#### Phase 4: Scale Optimization (If Triggered) - 2-4 weeks
**Trigger**: Task count exceeds 500K OR build time exceeds 5 minutes

**Deliverables**:
- Per-entity-type Parquet partitioning
- Parallel Lambda build for large entity types
- Workspace-level isolation for multi-tenant

**Investment**: 2-4 person-weeks
**Reversibility**: Two-Way Door (configuration)

#### Phase 5: Real-Time Addon (If Triggered) - 3-4 weeks
**Trigger**: User complaints exceed 5/month OR competitor launches real-time

**Deliverables**:
- Webhook receiver service (ECS Fargate)
- Event-driven invalidation
- Eager rebuild for high-value entities

**Investment**: 3-4 person-weeks
**Reversibility**: One-Way Door (webhook infrastructure is significant investment)

---

## Observable Signals and Decision Points

### Watch List (Monitor Now)

| Signal | Measurement | Threshold | Action |
|--------|-------------|-----------|--------|
| Task count growth | Weekly count | >500K | Trigger Phase 4 |
| Cold start latency | P95 startup | >5s | Investigate, possibly Phase 4 |
| Redis memory | ElastiCache metrics | >300MB | Review tier sizing |
| User staleness complaints | Support tickets | >3/month | Consider Phase 5 |
| Asana API announcements | Developer blog | Streaming/GraphQL | Evaluate early adoption |

### Decision Points

| Decision | When | Options | Implications |
|----------|------|---------|--------------|
| Phase 4 trigger | Task count >500K | Execute / Defer | Scale investment |
| Phase 5 trigger | Complaints >5/month | Execute / Defer | Real-time investment |
| Webhook infrastructure | If Phase 5 | Build / Buy / Skip | One-way door |
| Multi-region | Client contract | Execute / Decline | 3x infrastructure |

---

## Immediate Actions

### Start Now (Regardless of Future)

1. **Establish baseline metrics**: Measure current cold start latency, cache hit rates, build times
2. **Instrument SaveSession**: Add hooks for mutation tracking (prerequisite for Phase 2)
3. **Spike S3 Parquet load**: Validate Polars can efficiently read S3 Parquet at scale
4. **Document current architecture**: Capture ADR for materialization decision

### Decisions Needed

1. **Refresh frequency**: Hourly baseline rebuild sufficient for Phase 1?
   - **Recommendation**: Start hourly, add daily full rebuild for consistency
   - **By**: Start of Phase 1

2. **Redis tier sizing**: What percentage of entities are "hot"?
   - **Recommendation**: Analyze access patterns, estimate 10-20%
   - **By**: Start of Phase 2

3. **Webhook investment criteria**: What user pain level triggers Phase 5?
   - **Recommendation**: 5 complaints/month OR lost sales opportunity
   - **By**: Q2 2026

---

## Open Questions

1. **Multi-tenant partitioning**: When do we need workspace-level isolation?
   - **Lean**: Defer until second workspace is imminent

2. **Webhook reliability**: Is Asana webhook SLA sufficient for production?
   - **Research needed**: Evaluate webhook delivery guarantees before Phase 5 decision

3. **Parquet vs. JSON in S3**: Is Parquet compression worth the complexity?
   - **Lean**: Yes--Polars native support, 3-5x compression, columnar access

4. **Lambda vs. ECS for builds**: Which is more cost-effective at scale?
   - **Lean**: Lambda for predictable workloads, ECS for long-running builds

5. **Incremental sync granularity**: Row-level or entity-level delta?
   - **Lean**: Entity-level (simpler merge logic, acceptable freshness)

---

## The Acid Test

> "If this future arrives in 18 months, will we wish we had started preparing today?"

**10x Scale**: Yes. S3 baseline handles scale; Redis tier right-sizes hot data. Phase 1-2 provide foundation. **Start now.**

**Real-Time**: Partial yes. Phases 1-2 don't solve real-time, but they don't block it either. Phase 5 is additive. **Start Phases 1-2 now; monitor for Phase 5 trigger.**

**Multi-Region**: No immediate regret. S3 replication is straightforward when needed. **Defer, but don't block.**

**Cost Pressure**: Yes. Hybrid is inherently cost-optimized (cheap S3 for bulk, expensive Redis for hot). **Start now.**

**API Evolution**: Yes. Modular design allows incremental adoption of new APIs. **Start now.**

**Conclusion**: All scenarios benefit from Phases 1-2 (S3 baseline + Redis hot tier). Proceed immediately. Monitor signals for Phases 4-5.

---

## Artifact Verification

| Artifact | Path | Verified |
|----------|------|----------|
| Two-Tier Cache ADR | `docs/decisions/ADR-0047-two-tier-cache-architecture.md` | Read via Read tool |
| DataFrame Layer ADR | `docs/decisions/ADR-0012-dataframe-layer-architecture.md` | Read via Read tool |
| Current DataFrames | `src/autom8_asana/dataframes/__init__.py` | Read via Read tool |
| Cache Integration | `src/autom8_asana/dataframes/cache_integration.py` | Read via Read tool |
| Cache Invalidator | `src/autom8_asana/persistence/cache_invalidator.py` | Read via Read tool |
| Configuration | `src/autom8_asana/config.py` | Read via Read tool |
| Settings | `src/autom8_asana/settings.py` | Grep verified |
| Prior Moonshot | `docs/rnd/MOONSHOT-autom8y.md` | Read via Read tool |
| Session Context | `.claude/sessions/session-20251231-134242-00b4d145/SESSION_CONTEXT.md` | Read via Read tool |

---

## References

- [ADR-0047: Two-Tier Cache Architecture](/docs/decisions/ADR-0047-two-tier-cache-architecture.md)
- [ADR-0012: DataFrame Layer Architecture](/docs/decisions/ADR-0012-dataframe-layer-architecture.md)
- [MOONSHOT-autom8y](/docs/rnd/MOONSHOT-autom8y.md)
- [Polars Documentation](https://pola.rs/)
- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [ElastiCache Pricing](https://aws.amazon.com/elasticache/pricing/)
- [Asana API Documentation](https://developers.asana.com/docs)
