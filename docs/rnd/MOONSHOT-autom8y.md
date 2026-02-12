# MOONSHOT-autom8y

## Executive Summary

This document envisions the autom8y platform architecture for 2027 and beyond. Building on the validated autom8y-telemetry POC, we chart a path from the current fragmented satellite architecture (autom8_asana, autom8_data, autom8y-auth) to a unified platform primitive layer that enables:

- **65-70% boilerplate reduction** per service through shared infrastructure
- **Distributed tracing** across all satellites via OpenTelemetry
- **Sub-second service bootstrap** with pre-configured observability, auth, and HTTP clients
- **Future-proof architecture** that survives 100x scale, regulatory changes, and technology shifts

**Time Horizon**: 3 years (2025-2027)

**Key Insight**: The prototype demonstrated that thin wrappers over mature standards (OTel + structlog + httpx) provide enterprise-grade observability without building custom infrastructure. The moonshot extends this pattern to authentication, configuration, caching, and service mesh integration.

---

## Scenario Definition

### Scenario A: Organic Growth (60% Probability)

**Impact if True**: Medium

The autom8 ecosystem grows steadily to 8-12 satellites by 2027. Current patterns remain viable but increasingly painful. Developer onboarding takes 2+ weeks due to tribal knowledge.

**Assumptions**:
- No major regulatory changes requiring architectural pivots
- AWS remains primary cloud provider
- Python remains dominant language for internal tooling
- Team size grows 50-100% over 3 years

**Triggers/Signals**:
- 3rd satellite launched requiring copy-paste boilerplate
- Developer onboarding survey shows infrastructure setup as top friction point
- Cross-service debugging time exceeds 1 hour average

**Observable Signals**:
1. Time-to-first-deployment for new satellite exceeds 2 weeks
2. Cross-service correlation ID lookup requires manual log aggregation
3. Rate limit violations increase due to inconsistent client configuration

---

### Scenario B: Scale Pressure (25% Probability)

**Impact if True**: Critical

Asana automation volume reaches 10M+ requests/day. Current TokenBucketRateLimiter hits limits. Circuit breaker coordination across satellites becomes critical.

**Assumptions**:
- Business grows 10x in request volume
- Asana maintains current rate limit structure (1500/min)
- Cost optimization becomes board-level priority

**Triggers/Signals**:
- Asana rate limit violations exceed 100/day
- AWS costs for observability exceed $10K/month
- P99 latency exceeds 2 seconds for cross-service operations

**Observable Signals**:
1. Rate limiter queue depth exceeds 1000 pending requests
2. OTel exporter drops exceed 1% of spans
3. Circuit breaker opens more than 10x/day

---

### Scenario C: Platform Commoditization (10% Probability)

**Impact if True**: High

eBPF-based observability (Cilium, Pixie) or AI-powered AIOps eliminate need for application-level instrumentation. OpenTelemetry becomes "legacy" approach.

**Assumptions**:
- Kernel-level observability matures for Python/asyncio
- Cloud providers offer zero-code distributed tracing
- AI anomaly detection replaces threshold-based alerting

**Triggers/Signals**:
- AWS announces native Python tracing without SDK
- Datadog/Grafana launch "no-code" observability for ECS
- Cilium supports Python application visibility without code changes

**Observable Signals**:
1. OpenTelemetry Python SDK receives <50 commits/month
2. Major cloud providers deprecate SDK-based instrumentation
3. Production-ready eBPF Python profiler launched

---

### Scenario D: Regulatory Inversion (5% Probability)

**Impact if True**: Critical

GDPR-like regulations require trace/log PII sanitization at collection time. Data residency requirements mandate multi-region telemetry with routing rules.

**Assumptions**:
- US or EU mandates client data isolation in observability
- PII in request/response payloads becomes compliance risk
- Multi-region deployment required for data sovereignty

**Triggers/Signals**:
- GDPR enforcement action against SaaS for telemetry data
- US federal agency mandates FedRAMP-style observability controls
- Client contract requires data never leaves region

**Observable Signals**:
1. Legal requests telemetry data residency policy
2. Client audit requires demonstration of PII-free traces
3. AWS launches region-locked OTel Collector variant

---

## Current State

### Architecture Overview

```
                      Current (2025)

    autom8_asana          autom8_data         autom8y-auth
    ┌─────────────┐       ┌─────────────┐     ┌─────────────┐
    │ Transport   │       │ Custom HTTP │     │ JWT Validate│
    │ - HTTP      │       │ - Copy-paste│     │ - JWKS Fetch│
    │ - Retry     │       │   patterns  │     └─────────────┘
    │ - Circuit   │       └─────────────┘
    │ - RateLimit │
    ├─────────────┤
    │ Logging     │       No structured      No observability
    │ - stdlib    │       logging
    │ - Basic fmt │
    ├─────────────┤
    │ Config      │       Manual env vars    Manual config
    │ - pydantic  │
    │ - Settings  │
    └─────────────┘
```

### Key Constraints

1. **No distributed tracing**: Cross-service debugging requires manual log correlation
2. **Duplicated transport code**: autom8_data re-implements rate limiting, retry, circuit breaker
3. **Inconsistent logging**: No structured logs, no trace ID correlation
4. **Service-specific configuration**: Each satellite reinvents configuration patterns
5. **No shared caching patterns**: autom8_asana has sophisticated cache; others have none

### Technical Debt Affecting Future

| Debt | Location | Impact |
|------|----------|--------|
| Asana-specific exceptions in transport | `autom8_asana/exceptions.py` | Blocks extraction |
| Response unwrapping in HTTP client | `transport/http.py:229-232` | Couples client to Asana API |
| DataServiceClient duplicates transport | `clients/data/client.py` | Code duplication |
| No protocol abstractions | All modules | Tight coupling |
| stdlib logging only | `_defaults/log.py` | No structured output |

---

## Future Architecture

### Vision

By 2027, spinning up a new autom8 satellite looks like this:

```python
# dream_dx_2027.py
from autom8y import Platform

app = Platform.create(
    service_name="autom8-inventory",
    # Auto-configured from environment:
    # - OTEL_EXPORTER_OTLP_ENDPOINT
    # - AUTOM8_AUTH_JWKS_URL
    # - AUTOM8_CONFIG_SOURCE (SSM/Secrets Manager)
)

# Pre-configured clients with observability
asana = app.http_client("asana")
data_service = app.http_client("autom8-data")

# Automatic trace propagation, structured logging, metrics
async def process_task(task_id: str):
    with app.span("process_task") as span:
        span.set_attribute("task.id", task_id)

        task = await asana.get(f"/tasks/{task_id}")
        app.log.info("task_fetched", task_id=task_id)

        await data_service.post("/sync", json=task)
        # Trace ID propagated automatically
```

### Architecture Diagram

```
                     Target State (2027)

┌─────────────────────────────────────────────────────────────────┐
│                      autom8y Platform Layer                      │
├────────────────┬────────────────┬────────────────┬──────────────┤
│ autom8y-       │ autom8y-       │ autom8y-       │ autom8y-     │
│ telemetry      │ http           │ auth           │ config       │
│                │                │                │              │
│ - OTel setup   │ - Base client  │ - JWT validate │ - SSM/Secrets│
│ - structlog    │ - RateLimiter  │ - JWKS fetch   │ - Env vars   │
│ - Trace ctx    │ - Retry/CB     │ - Token cache  │ - Pydantic   │
│ - Log/trace    │ - Instrumented │ - Middleware   │ - Hot reload │
│   correlation  │   transport    │                │              │
└───────┬────────┴───────┬────────┴───────┬────────┴──────┬───────┘
        │                │                │               │
        └────────────────┴───────┬────────┴───────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │  autom8y Platform SDK   │
                    │  (Facade/Composition)   │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼───────┐       ┌────────▼────────┐       ┌───────▼───────┐
│ autom8_asana  │       │ autom8_data     │       │ autom8_web    │
│               │       │                 │       │ (future)      │
│ Uses platform │       │ Uses platform   │       │ Uses platform │
│ primitives    │       │ primitives      │       │ primitives    │
└───────────────┘       └─────────────────┘       └───────────────┘
```

### Key Changes

| Area | Current | Future | Rationale |
|------|---------|--------|-----------|
| **HTTP Transport** | Embedded in autom8_asana | autom8y-http package | Reuse across satellites |
| **Telemetry** | None | autom8y-telemetry (OTel) | Distributed tracing |
| **Logging** | stdlib, basic format | structlog + OTel | Trace correlation |
| **Configuration** | Per-service pydantic | autom8y-config (unified) | Consistent patterns |
| **Authentication** | autom8y-auth (exists) | Enhanced with telemetry | Already extracted |
| **Caching** | autom8_asana only | autom8y-cache protocols | Portable patterns |

### New Capabilities Required

1. **Trace Context Propagation**: W3C Trace Context injected/extracted automatically across HTTP boundaries
2. **Unified Configuration**: Single pattern for env vars, SSM Parameter Store, Secrets Manager with hot reload
3. **Adaptive Rate Limiting**: Distributed rate limiter that coordinates across satellites via Redis
4. **Circuit Breaker Federation**: Shared circuit breaker state for common dependencies
5. **Log/Trace Correlation**: Every log line includes trace_id for cross-service debugging

### Technology Dependencies

| Technology | Purpose | Maturity | Risk |
|------------|---------|----------|------|
| OpenTelemetry Python 1.x | Telemetry standard | Stable | Low |
| structlog | Structured logging | Stable | Low |
| httpx | HTTP client | Stable | Low (already using) |
| OTel Collector | Telemetry aggregation | Stable | Low |
| Grafana Tempo | Trace storage | Growing | Medium |
| Redis (shared state) | Distributed rate limit | Stable | Medium |

### Scaling Implications

**10x Scale (10M requests/day)**:
- Head-based sampling at 10% reduces storage 90%
- OTel Collector gateway handles batching (200 spans/batch)
- Estimated telemetry cost: $2-3K/month

**100x Scale (100M requests/day)**:
- Tail-based sampling required (keep errors + slow requests + 1%)
- Multi-collector deployment with load balancing
- Consider switch to sampling at satellite level
- Estimated telemetry cost: $15-25K/month

---

## Migration Path

### Phase 1: Foundation (Q1 2025) - 4-5 Weeks

**Goal**: Extract and package core primitives with production-grade quality

**Deliverables**:
1. `autom8y-http` package (PyPI)
   - TokenBucketRateLimiter (extracted from autom8_asana)
   - RetryHandler (extracted)
   - CircuitBreaker (extracted)
   - Protocol definitions
2. `autom8y-telemetry` package (PyPI)
   - OTel SDK initialization wrapper
   - structlog processor for trace correlation
   - TelemetryHTTPClient base class
3. Documentation site skeleton

**Investment**: 4-5 person-weeks
**Reversibility**: **Two-Way Door** - Can continue using internal autom8_asana transport; extraction is additive

**Success Criteria**:
- [ ] All extracted components pass original test suites
- [ ] Type checker (mypy) passes with protocols
- [ ] Benchmark shows <5% latency increase

---

### Phase 2: Adoption (Q2-Q3 2025) - 8-10 Weeks

**Goal**: Migrate autom8_asana and autom8_data to platform primitives

**Deliverables**:
1. autom8_asana updated to use autom8y-http/telemetry
   - AsyncHTTPClient extends TelemetryHTTPClient
   - Backward-compatible re-exports maintained
2. autom8_data updated to use platform primitives
   - Removes duplicate transport code
   - Full distributed tracing enabled
3. OTel Collector deployed in ECS
   - Gateway pattern (centralized)
   - Export to Tempo + CloudWatch

**Investment**: 8-10 person-weeks
**Reversibility**: **Two-Way Door** - Feature flag can disable platform primitives; fallback to original code

**Success Criteria**:
- [ ] Cross-service trace visible in Tempo
- [ ] 50%+ reduction in transport code in autom8_data
- [ ] No increase in production error rate

---

### Phase 3: Optimization (Q4 2025) - 6-8 Weeks

**Goal**: Add advanced features and optimize for scale

**Deliverables**:
1. `autom8y-config` package
   - SSM Parameter Store integration
   - Secrets Manager integration
   - Hot reload for non-secret config
2. Metrics pipeline
   - Business metrics (SLIs)
   - Technical metrics (latency histograms)
   - Prometheus/Grafana dashboards
3. Tail-based sampling in Collector
4. PII sanitization processor

**Investment**: 6-8 person-weeks
**Reversibility**: **Two-Way Door** - Features are additive; can be disabled without rollback

**Success Criteria**:
- [ ] Zero secrets in code or environment variables (all from Secrets Manager)
- [ ] SLO dashboard operational
- [ ] Trace storage costs reduced 50% via sampling

---

### Phase 4: Advanced (2026+) - Ongoing

**Goal**: Prepare for paradigm shifts and scale challenges

**Deliverables**:
1. `autom8y-cache` protocols
   - Portable cache patterns from autom8_asana
   - Redis and memory backends
   - Cache observability (hit rate, latency)
2. Distributed rate limiting (Redis-backed)
3. Service mesh evaluation
   - Istio/Linkerd for ECS
   - Zero-trust networking
4. eBPF observability spike
   - Evaluate Cilium Hubble for Python
   - Determine if kernel-level tracing supplements OTel

**Investment**: Variable based on observed signals
**Reversibility**: Phase-dependent - service mesh is One-Way Door; cache extraction is Two-Way

**Success Criteria**:
- [ ] Rate limiting works across all satellites via shared Redis state
- [ ] Service mesh POC demonstrates value for autom8 architecture
- [ ] eBPF evaluation informs 2027 observability strategy

---

### Decision Points

| Decision | When | Options | Implications |
|----------|------|---------|--------------|
| Trace backend selection | Before Phase 2 | Tempo / Jaeger / Datadog | Cost, feature set, vendor lock-in |
| Collector deployment | Phase 2 start | Gateway / Sidecar | Resource usage, sampling flexibility |
| Service mesh adoption | Phase 4 | Istio / Linkerd / None | Complexity vs. security benefits |
| eBPF investment | 2026 H1 | Adopt / Wait / Skip | Depends on Python support maturity |
| Multi-region deployment | Regulatory trigger | Single / Multi | Cost 3x, complexity 5x |

---

## Risk Analysis

### Scenario Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OTel Logs API breaks | High | Medium | Pin version, isolate behind interface |
| Tempo scales poorly at 10M spans/day | Medium | High | Evaluate Datadog/Honeycomb as backup |
| Team lacks OTel expertise | Medium | Medium | Wrapper hides complexity; training plan |
| Regulatory PII requirement emerges | Low | Critical | PII processor in Phase 3 |

### Execution Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Phase 1 extraction takes >6 weeks | Medium | Medium | Time-box ruthlessly; MVP first |
| Breaking changes in autom8_asana migration | Medium | High | Feature flags; shadow mode |
| Collector becomes single point of failure | Low | Critical | Multi-AZ deployment; fallback to direct export |
| Cost overrun on telemetry storage | Medium | Medium | Aggressive sampling; Tempo's low storage cost |

---

## Investment Summary

| Phase | Duration | Team Size | Key Investments |
|-------|----------|-----------|-----------------|
| Phase 1: Foundation | 4-5 weeks | 1 FTE | Package extraction, testing, PyPI publish |
| Phase 2: Adoption | 8-10 weeks | 1.5 FTE | Migration, Collector deploy, validation |
| Phase 3: Optimization | 6-8 weeks | 1 FTE | Config package, metrics, sampling |
| Phase 4: Advanced | Ongoing | 0.5 FTE | Cache, distributed state, mesh eval |

**Total Estimated Investment (2025)**: 18-24 person-weeks (~$75K-$100K fully loaded)

**Expected ROI**:
- Developer time saved: 2 weeks per new satellite (4 satellites in 3 years = 8 weeks saved)
- Debugging time reduction: 50% for cross-service issues (estimated 10 hours/month = 120 hours/year)
- Incident response improvement: MTTR reduced 40% with distributed tracing

---

## Strategic Implications

### Platform as Competitive Advantage

The autom8y platform becomes the foundation for rapid service development. Any new integration (CRM, ERP, project management) inherits:
- Observability from day 1
- Consistent auth patterns
- Proven transport resilience

### Talent and Hiring

Platform primitives reduce tribal knowledge. New engineers see consistent patterns across all satellites. Onboarding drops from 2 weeks to 3 days for "ready to contribute."

### Vendor Strategy

By building on OTel (vendor-neutral), we preserve optionality:
- Can switch backends without code changes
- No lock-in to single observability vendor
- Community support reduces maintenance burden

---

## Recommendations

### Immediate Actions (Start Now)

1. **Create `autom8y-http` repository**: Skeleton structure, CI/CD pipeline
2. **Begin TokenBucketRateLimiter extraction**: First extraction target (low coupling)
3. **Evaluate trace backends**: Tempo vs. Jaeger vs. Datadog for cost/features
4. **Deploy OTel Collector in staging**: Validate gateway pattern in ECS

### Decisions Needed

1. **Repository structure**: Monorepo (`autom8y/`) or multi-repo? - **By Q1 2025 start**
2. **Trace backend selection**: Tempo/Jaeger/Datadog - **By Phase 2 start**
3. **PyPI publishing strategy**: Private PyPI or public with restricted access? - **By Phase 1 end**

### What to Watch (Observable Signals)

1. **OpenTelemetry Python release cadence**: >50 commits/month indicates healthy project
2. **eBPF Python support**: Cilium Hubble Python application visibility announcements
3. **AWS observability announcements**: Native ECS tracing without SDK would change strategy
4. **Asana rate limit changes**: Any increase/decrease affects distributed rate limiting design

---

## Open Questions

1. **Monorepo vs. multi-repo**: Should `autom8y-http`, `autom8y-telemetry`, `autom8y-config` live in one repo or separate?
   - **Lean**: Monorepo for coordinated versioning; import cost is low with workspace packages

2. **Private vs. public PyPI**: Is `autom8y-*` published to PyPI (public) or private registry?
   - **Lean**: Private (CodeArtifact or similar) - no public visibility needed

3. **Redis for distributed state**: When does distributed rate limiting become necessary?
   - **Signal**: Rate limit violations exceed 50/day across satellites

4. **Service mesh timeline**: At what scale does service mesh complexity pay off?
   - **Signal**: >10 satellites OR security audit requires zero-trust networking

5. **eBPF bet timing**: When to invest in kernel-level observability?
   - **Signal**: Cilium announces production-ready Python asyncio support

---

## Artifact Verification

| Artifact | Path | Verified |
|----------|------|----------|
| Technology Scout Assessment | `docs/rnd/SCOUT-autom8y-telemetry.md` | Read via Read tool |
| Integration Map | `docs/rnd/INTEGRATION-MAP-autom8y-telemetry.md` | Read via Read tool |
| POC Documentation | `docs/rnd/POC-autom8y-telemetry.md` | Read via Read tool |
| Prototype Code | `prototypes/autom8y_telemetry/` | Glob verified |
| Current Transport | `src/autom8_asana/transport/http.py` | Read via Read tool |
| Current Config | `src/autom8_asana/config.py` | Read via Read tool |
| Project Dependencies | `pyproject.toml` | Read via Read tool |

---

## The Acid Test

> "If this future arrives in 18 months, will we wish we had started preparing today?"

**Scenario A (Organic Growth)**: Yes. Every new satellite without platform primitives adds 2 weeks of boilerplate and increases debugging complexity. Start Phase 1 now.

**Scenario B (Scale Pressure)**: Yes. Distributed tracing becomes critical for debugging at 10M+ requests. OTel Collector sampling saves storage costs. Start Phase 1 now.

**Scenario C (Commoditization)**: No regret. Thin wrapper over OTel means migration to eBPF/native tracing is additive, not replacement. Start Phase 1 now.

**Scenario D (Regulatory)**: Partial yes. PII processor in Phase 3 provides foundation. Multi-region can wait for trigger signal. Start Phase 1 now.

**Conclusion**: All scenarios benefit from Phase 1 (Foundation) and Phase 2 (Adoption). Proceed.

---

## References

- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [structlog Documentation](https://www.structlog.org/)
- [httpx Documentation](https://www.python-httpx.org/)
- [OTel Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
- [eBPF Observability](https://ebpf.io/what-is-ebpf/)
- [Cilium Hubble](https://docs.cilium.io/en/stable/observability/hubble/)
