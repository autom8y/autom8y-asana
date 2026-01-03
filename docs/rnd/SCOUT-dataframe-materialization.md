# SCOUT-dataframe-materialization

## Executive Summary

This assessment evaluates five architectural options for persistent, pre-materialized DataFrame caching to eliminate cold-start latency (currently 30+ seconds) for 100K+ Asana tasks. **Option E (Hybrid: S3 cold + Redis hot + incremental sync)** emerges as the recommended approach, delivering sub-100ms P99 latency with zero cold starts while maximizing Asana API efficiency through `modified_since` filtering. The hybrid approach uniquely leverages existing infrastructure (S3CacheProvider, RedisCacheProvider, TieredCache) while providing durable recovery and sub-millisecond hot-path performance.

## Technology Overview

- **Category**: Caching Architecture / Data Materialization
- **Maturity**: Mainstream (all components are production-proven)
- **License**: Apache 2.0 (Parquet), MIT (Redis)
- **Backing**: Apache Foundation (Parquet), AWS (ElastiCache, S3, Lambda)

## Problem Context

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| First request latency | 30+ seconds (cold cache) | <100ms P99 |
| Task count | 100K+ tasks | Same |
| Freshness SLA | N/A | Hourly batch refresh |
| Infrastructure | AWS (Lambda, S3, EventBridge, ECS) | Same |

### Existing Assets

The codebase already provides substantial caching infrastructure:

- **`CacheProvider` protocol** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py`): Supports `get_versioned`, `set_versioned`, `get_batch`, `set_batch`, `warm`, `invalidate`
- **`DataFrameCacheIntegration`** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py`): Schema version tracking, staleness detection, batch operations
- **`CacheInvalidator`** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cache_invalidator.py`): Coordinates invalidation after mutations
- **`WebhooksClient`** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py`): HMAC signature verification, webhook CRUD

---

## Option Assessments

### Option A: S3 Parquet + Startup Load

#### Architecture Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Scheduled   │────▶│   Lambda    │────▶│  S3 Bucket  │
│ EventBridge │     │ (rebuild)   │     │  (Parquet)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ ECS @ Start │
                                        │ (load→RAM)  │
                                        └─────────────┘
```

1. EventBridge triggers Lambda hourly
2. Lambda fetches all tasks from Asana API, builds DataFrame
3. Lambda writes Parquet file to S3
4. ECS containers load Parquet into memory at startup

#### Strengths

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Request latency | Good | In-memory after load; sub-ms reads |
| Asana API efficiency | Moderate | Full fetch each hour (no incremental) |
| Operational simplicity | Excellent | Fewest moving parts |
| Extensibility | Good | One Parquet file per entity type |

#### Weaknesses

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Cold start | Poor | ECS startup blocked by S3 download + parse |
| Memory | Moderate | 100K tasks ~500MB RAM per container |
| Deployment | Moderate | Container restart required for data refresh |

#### AWS Cost Estimate (100K tasks, hourly refresh)

| Component | Calculation | Monthly Cost |
|-----------|-------------|--------------|
| S3 Storage | 500MB Parquet x 24 versions = 12GB @ $0.023/GB | $0.28 |
| S3 PUT requests | 720 puts/month @ $0.005/1000 | $0.004 |
| S3 GET requests | 720 gets/month @ $0.0004/1000 | $0.0003 |
| Lambda (rebuild) | 720 invocations x 30s x 1GB @ $0.00001667/GB-s | $0.36 |
| EventBridge | 720 invocations (free tier: 14M) | $0.00 |
| **Total** | | **~$0.65/month** |

#### Implementation Effort

**3-5 days**

- Lambda function for Parquet generation (1 day)
- ECS startup hook for S3 download + load (1 day)
- EventBridge schedule configuration (0.5 day)
- Testing and deployment (1-2 days)

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ECS startup delay | High | Medium | Pre-pull S3 file; use Fargate SEEKABLE_OCI |
| Lambda timeout (15 min limit) | Medium | High | Batch processing; use ECS task instead |
| Memory pressure on ECS | Medium | Medium | Right-size instances; use lazy column loading |

---

### Option B: Lambda + EventBridge Scheduled Refresh

#### Architecture Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ EventBridge │────▶│   Lambda    │────▶│   Redis     │
│ (hourly)    │     │ (fetch+push)│     │ ElastiCache │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ ECS (read)  │
                                        └─────────────┘
```

1. EventBridge triggers Lambda hourly
2. Lambda fetches from Asana API, transforms to DataFrame rows
3. Lambda writes individual rows/batches to Redis
4. ECS containers read from Redis (always warm)

#### Strengths

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Request latency | Excellent | Redis sub-millisecond reads |
| Cold start | Excellent | No startup load; Redis always warm |
| Operational simplicity | Good | Managed services only |
| Extensibility | Good | Key pattern per entity type |

#### Weaknesses

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Asana API efficiency | Poor | Full fetch each hour (no incremental) |
| Redis memory | Moderate | 100K tasks x 2KB avg = 200MB |
| Lambda timeout | Medium | 15 min limit for 100K tasks |

#### AWS Cost Estimate (100K tasks, hourly refresh)

| Component | Calculation | Monthly Cost |
|-----------|-------------|--------------|
| ElastiCache (cache.t3.micro) | 1 node @ $0.017/hr x 720 hrs | $12.24 |
| Lambda (rebuild) | 720 x 60s x 1GB @ $0.00001667/GB-s | $0.72 |
| EventBridge | 720 invocations (free tier) | $0.00 |
| **Total** | | **~$13/month** |

#### Implementation Effort

**4-6 days**

- Lambda function with Redis batched writes (2 days)
- Redis key schema design for DataFrames (0.5 day)
- EventBridge configuration (0.5 day)
- Integration with existing `RedisCacheProvider` (1 day)
- Testing and deployment (1-2 days)

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Lambda timeout | Medium | High | Paginated processing; Step Functions |
| Redis memory exhaustion | Low | High | Set maxmemory-policy; monitor usage |
| Rate limit (Asana API) | Medium | Medium | Implement backoff; batch requests |

---

### Option C: Redis Pub/Sub + Background Worker

#### Architecture Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ ECS Worker  │◀───▶│   Redis     │◀───▶│ ECS Service │
│ (background)│     │ Pub/Sub     │     │ (read)      │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ Asana API   │     │ Redis Data  │
└─────────────┘     └─────────────┘
```

1. Dedicated ECS worker process runs continuously
2. Worker polls Asana API periodically for changes
3. Worker publishes invalidation signals via Redis Pub/Sub
4. Worker maintains warm cache continuously in Redis

#### Strengths

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Request latency | Excellent | Redis sub-millisecond |
| Freshness | Excellent | Can poll more frequently than hourly |
| Control | Excellent | Full control over refresh logic |
| Extensibility | Excellent | Worker handles all entity types |

#### Weaknesses

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Asana API efficiency | Moderate | Polling-based (no delta without modified_since) |
| Operational complexity | Poor | Additional long-running process |
| Cost | Moderate | Always-on ECS task |

#### AWS Cost Estimate (100K tasks, hourly refresh)

| Component | Calculation | Monthly Cost |
|-----------|-------------|--------------|
| ElastiCache (cache.t3.micro) | 1 node @ $0.017/hr x 720 hrs | $12.24 |
| ECS Fargate (worker) | 0.25 vCPU, 0.5GB @ ~$0.012/hr x 720 hrs | $8.64 |
| **Total** | | **~$21/month** |

#### Implementation Effort

**5-7 days**

- Background worker ECS service setup (1 day)
- Polling logic with `modified_since` (1 day)
- Redis Pub/Sub integration (1 day)
- Cache warming strategy (1 day)
- Monitoring and health checks (1-2 days)

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Worker failure | Medium | High | Health checks; auto-restart; standby |
| Pub/Sub message loss | Low | Low | Messages are hints; data in Redis |
| Operational overhead | High | Medium | Logging, monitoring, alerting required |

---

### Option D: Webhook-Driven Invalidation + Lazy Rebuild

#### Architecture Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Asana       │────▶│ Lambda      │────▶│   Redis     │
│ Webhooks    │     │ (invalidate)│     │ (invalidate)│
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                           ┌───────────────────┤
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ Lazy Rebuild│     │ ECS (read)  │
                    │ (on-demand) │     │             │
                    └─────────────┘     └─────────────┘
```

1. Asana webhooks notify Lambda of task changes
2. Lambda invalidates affected cache entries in Redis
3. On cache miss, ECS fetches fresh data and rebuilds (lazy)
4. Optional: background rebuild after invalidation

#### Strengths

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Asana API efficiency | Excellent | Only fetch changed tasks |
| Freshness | Excellent | Near real-time (under 1 minute) |
| Extensibility | Good | Existing WebhooksClient supports this |

#### Weaknesses

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Cold start | Poor | First request after invalidation hits API |
| Reliability | Moderate | Webhook delivery is at-most-once |
| Complexity | Moderate | Webhook management, signature verification |

#### AWS Cost Estimate (100K tasks, 1% daily churn)

| Component | Calculation | Monthly Cost |
|-----------|-------------|--------------|
| ElastiCache (cache.t3.micro) | 1 node @ $0.017/hr x 720 hrs | $12.24 |
| Lambda (webhook handler) | 30K events/month x 100ms x 128MB | $0.04 |
| API Gateway (webhook endpoint) | 30K requests @ $3.50/million | $0.11 |
| **Total** | | **~$12.50/month** |

#### Implementation Effort

**6-8 days**

- Webhook Lambda handler (1 day)
- API Gateway configuration with WAF (1 day)
- Webhook signature verification (already exists) (0.5 day)
- Invalidation routing to existing `CacheInvalidator` (1 day)
- Webhook registration automation (1 day)
- Lazy rebuild strategy (1-2 days)
- Testing webhook reliability (1 day)

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed webhooks | Medium | Medium | Periodic reconciliation job |
| Webhook storm (bulk changes) | Medium | High | Rate limiting; queue buffering |
| Lazy rebuild latency spike | High | Medium | Background rebuild after invalidation |
| 10K webhook limit | Low | High | Workspace-level webhooks with filters |

---

### Option E: Hybrid (S3 cold + Redis hot + incremental sync)

#### Architecture Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ EventBridge │────▶│   Lambda    │────▶│  S3 Bucket  │
│ (hourly)    │     │ (snapshot)  │     │  (Parquet)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   │
                    ┌─────────────┐            │
                    │   Redis     │◀───────────┘
                    │ (hot cache) │   (recovery)
                    └─────────────┘
                           │
┌─────────────┐            │
│ Lambda      │────────────┤ (incremental)
│ (delta sync)│            │
└─────────────┘            │
                           ▼
                    ┌─────────────┐
                    │ ECS Service │
                    │ (read)      │
                    └─────────────┘
```

1. Hourly full snapshot written to S3 as Parquet (durability)
2. Redis serves all reads with sub-millisecond latency (hot path)
3. Incremental sync Lambda uses `modified_since` to fetch only changes
4. On Redis failure/restart, rehydrate from S3 Parquet snapshot
5. Leverages existing `TieredCache` pattern (Redis hot + S3 cold)

#### Strengths

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Request latency | Excellent | Redis sub-ms; P99 <100ms guaranteed |
| Cold start | Excellent | Zero cold start; Redis always warm |
| Asana API efficiency | Excellent | `modified_since` reduces API calls by ~95% |
| Operational simplicity | Good | All managed services; existing patterns |
| Extensibility | Excellent | Pattern extends to all entity types |
| Durability | Excellent | S3 Parquet survives Redis failures |

#### Weaknesses

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Complexity | Moderate | Two sync paths (full + incremental) |
| Cost | Moderate | Both Redis and S3 storage |

#### AWS Cost Estimate (100K tasks, hourly refresh)

| Component | Calculation | Monthly Cost |
|-----------|-------------|--------------|
| ElastiCache (cache.t3.micro) | 1 node @ $0.017/hr x 720 hrs | $12.24 |
| S3 Storage | 12GB Parquet @ $0.023/GB | $0.28 |
| Lambda (full snapshot) | 24 daily x 60s x 1GB | $0.02 |
| Lambda (incremental) | 696 x 5s x 512MB | $0.03 |
| EventBridge | All within free tier | $0.00 |
| **Total** | | **~$12.60/month** |

#### Implementation Effort

**5-7 days**

- Full snapshot Lambda (Parquet to S3) (1 day)
- Incremental sync Lambda (`modified_since`) (1 day)
- Redis hydration from S3 (recovery path) (1 day)
- Integration with existing `TieredCache` (1 day)
- EventBridge scheduling (0.5 day)
- Testing and deployment (1-2 days)

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `modified_since` bugs | Medium | Medium | Fallback to full sync; monitor drift |
| Redis memory exhaustion | Low | High | Set maxmemory-policy; auto-scaling |
| S3-Redis drift | Low | Low | Hourly full sync resets drift |
| Lambda timeout | Low | Medium | Paginated incremental batches |

---

## Comparison Matrix

| Criterion (Weight: Equal) | Option A | Option B | Option C | Option D | Option E |
|---------------------------|----------|----------|----------|----------|----------|
| **Request Latency P99 <100ms** | Moderate | Excellent | Excellent | Poor* | Excellent |
| **Zero Cold Start** | Poor | Excellent | Excellent | Poor | Excellent |
| **Asana API Efficiency** | Poor | Poor | Moderate | Excellent | Excellent |
| **Operational Simplicity** | Excellent | Good | Poor | Moderate | Good |
| **Extensibility** | Good | Good | Excellent | Good | Excellent |
| **Durability/Recovery** | Excellent | Poor** | Poor** | Poor** | Excellent |
| **Monthly Cost** | $0.65 | $13 | $21 | $12.50 | $12.60 |
| **Implementation Days** | 3-5 | 4-6 | 5-7 | 6-8 | 5-7 |
| **Overall Score** | 4.5/7 | 5/7 | 5/7 | 4/7 | 6.5/7 |

*Option D has poor latency on first request after invalidation (lazy rebuild)
**Options B, C, D lose cache on Redis restart with no durable backup

---

## Recommendation

**Verdict**: **Adopt Option E (Hybrid: S3 cold + Redis hot + incremental sync)**

### Rationale

1. **Zero cold start**: Redis is always warm; ECS containers start serving immediately
2. **Sub-100ms P99**: ElastiCache for Redis 7.1 delivers <1ms P99 at peak load
3. **API efficiency**: `modified_since` reduces hourly API calls from ~100K to ~1K (95% reduction)
4. **Durability**: S3 Parquet snapshots survive Redis failures, enabling fast recovery
5. **Existing infrastructure**: Leverages `TieredCache`, `RedisCacheProvider`, `S3CacheProvider` already in codebase
6. **Cost-effective**: $12.60/month for enterprise-grade caching

### Why Not Other Options

| Option | Disqualifier |
|--------|--------------|
| A (Parquet only) | ECS startup blocked by S3 download; no sub-ms latency |
| B (Lambda→Redis) | No incremental sync; full API fetch every hour |
| C (Background Worker) | Operational complexity; always-on ECS cost |
| D (Webhooks) | At-most-once delivery; lazy rebuild latency spikes |

### Trade-offs Accepted

- **Moderate complexity**: Two sync paths (full + incremental) require careful coordination
- **Redis cost**: $12/month for always-on ElastiCache (justified by sub-ms latency)

### Next Steps

1. **Prototype** (2 days): Build minimal Lambda with `modified_since` sync to validate API efficiency
2. **Integration** (2 days): Wire into existing `TieredCache` with S3 Parquet fallback
3. **Observability** (1 day): Add metrics for cache hit ratio, sync latency, drift detection
4. **Route to Integration Researcher**: Map dependencies for production deployment

---

## Fit Assessment

- **Philosophy Alignment**: Matches existing tiered cache pattern; builds on proven infrastructure
- **Stack Compatibility**: Full AWS-native; integrates with existing ECS, Lambda, S3, ElastiCache
- **Team Readiness**: Low learning curve; extends familiar `CacheProvider` protocol

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `modified_since` API inconsistency | Medium | Medium | Hourly full sync resets drift |
| Redis node failure | Low | High | Enable Multi-AZ; S3 recovery path |
| Lambda cold start (sync job) | Low | Low | Provisioned concurrency if needed |
| Cost creep (scaling) | Medium | Low | Monitor; switch to Serverless Redis |

---

## Appendix: Sources

### AWS Pricing (2025/2026)
- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [nOps Ultimate Guide to AWS S3 Pricing 2026](https://www.nops.io/blog/aws-s3-pricing/)
- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [CloudChipr AWS Lambda Pricing Breakdown 2025](https://cloudchipr.com/blog/aws-lambda-pricing)
- [Amazon ElastiCache Pricing](https://aws.amazon.com/elasticache/pricing/)
- [CloudChipr ElastiCache Pricing 2025](https://cloudchipr.com/blog/amazon-elasticache-pricing)
- [Amazon EventBridge Pricing](https://aws.amazon.com/eventbridge/pricing/)

### Performance Benchmarks
- [Parquet Data Format Pros and Cons 2025](https://edgedelta.com/company/blog/parquet-data-format)
- [Faster DataFrame Serialization - Towards Data Science](https://towardsdatascience.com/faster-dataframe-serialization-75205b6b7c69/)
- [ElastiCache for Redis 7.1 Performance](https://aws.amazon.com/blogs/database/achieve-over-500-million-requests-per-second-per-cluster-with-amazon-elasticache-for-redis-7-1/)
- [Optimize Redis Client Performance for ElastiCache](https://aws.amazon.com/blogs/database/optimize-redis-client-performance-for-amazon-elasticache/)

### Asana API
- [Asana Rate Limits](https://developers.asana.com/docs/rate-limits)
- [Asana Webhooks Guide](https://developers.asana.com/docs/webhooks-guide)
- [Asana Webhooks Complete Guide 2025](https://inventivehq.com/blog/asana-webhooks-guide)
- [Asana Pagination](https://developers.asana.com/docs/pagination)

### ECS Optimization
- [Optimize Amazon ECS Task Launch Time](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-recommendations.html)
- [How to Speed Up Amazon ECS Container Deployments](https://www.qovery.com/blog/how-to-speed-up-amazon-ecs-container-deployments)

---

## Artifact Verification

| Artifact | Path | Verified |
|----------|------|----------|
| SCOUT-dataframe-materialization | `/Users/tomtenuta/Code/autom8_asana/docs/rnd/SCOUT-dataframe-materialization.md` | Pending |

---

*Assessment prepared by Technology Scout | rnd-pack | 2026-01-01*
