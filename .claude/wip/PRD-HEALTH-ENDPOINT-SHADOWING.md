# PRD: Health Endpoint Shadowing Remediation (TC-S15)

## Overview

The satellite's `/health/ready` and `/health/s2s` endpoints are unreachable in production because the Handler API shadows them at the shared domain `asana.api.autom8y.io`. This PRD specifies the remediation to restore reachability by path-prefixing the satellite health endpoints, eliminating the namespace collision without touching the Handler API.

## Impact Assessment

impact: high
impact_categories: [api_contract, cross_service]

Rationale: Changes health endpoint paths (API contract), requires ALB health check configuration update (cross-service coordination between satellite and infrastructure), and affects container orchestration behavior.

## Background

### Problem Statement

The satellite (`autom8_asana`) and the Handler API are co-located behind the domain `asana.api.autom8y.io`. Both services register a `/health` route. The request routing chain is:

```
Client -> Cloudflare -> ALB (host: asana.api.autom8y.io, priority 120)
       -> ECS Target Group (port 8000)
       -> Container (uvicorn, dual-mode)
       -> Handler API catches /health/* first
```

The Handler API's `/health` route takes precedence over the satellite's routes. As a result:

| Endpoint | Expected Behavior | Actual Behavior |
|----------|-------------------|-----------------|
| `GET /health` | 200 (liveness) | 200 (Handler API responds, satellite shadowed but functionally equivalent) |
| `GET /health/ready` | 200 or 503 (readiness) | 404 (Handler API has no `/health/ready` route) |
| `GET /health/s2s` | 200 or 503 (S2S connectivity) | 404 (Handler API has no `/health/s2s` route) |

### Why Now

The spike (`docs/spikes/SPIKE-health-endpoint-shadowing.md`) recommended deferral because the compute-on-read architecture (ADR-0148) removed all startup-time gating. The stakeholder has decided to proceed with remediation now to eliminate latent risk: any future feature requiring startup-time readiness gating would be blocked by this shadowing, and discovering that under time pressure is worse than fixing it proactively.

### Current Operational Impact

Zero. The readiness gate was removed with ADR-0148. The ALB liveness check (`/health`) works because the Handler API responds to it. No feature currently depends on `/health/ready` or `/health/s2s` being reachable via the external domain.

### Future Risk

If a future feature re-introduces startup-time computation requiring readiness gating, the ALB cannot use `/health/ready` to hold traffic from unready containers. The shadowed endpoint would silently return 404, and the ALB would route traffic to containers that are not ready.

## Remediation Options Analysis

### Option A: Path-Prefix Satellite Health (Recommended)

Change satellite health routes from `/health/*` to `/satellite/health/*`. Update ALB health check target path.

| Dimension | Assessment |
|-----------|------------|
| Effort | ~0.5 day |
| Blast radius | Satellite only (health.py, main.py, tests, ALB health check config) |
| Cross-repo changes | None (ALB health check path is configured per target group) |
| Handler API changes | None |
| Path convention | Non-standard (`/satellite/health` instead of `/health`), but unambiguously satellite-owned |
| Rollback | Revert satellite code + ALB health check path |

**Pros**:
- Minimal blast radius: changes are confined to the satellite codebase
- Zero Handler API changes: no coordination with another team or service
- Clear namespace ownership: `/satellite/health/*` is unambiguously the satellite's domain
- Simplest deployment: single service deploy + ALB config update

**Cons**:
- Non-standard path for health checks (monitoring tools may expect `/health`)
- Liveness probe path changes from `/health` to `/satellite/health` (ALB config update required)

### Option B: ALB Route-Split

Add path-based ALB listener rules to route `/health/ready` and `/health/s2s` to the satellite target group while leaving `/health` routed to Handler API.

| Dimension | Assessment |
|-----------|------------|
| Effort | ~1 day |
| Blast radius | Satellite + ALB Terraform in `autom8y` repo |
| Cross-repo changes | Required (Terraform in `autom8y` repo) |
| Handler API changes | None |
| Path convention | Standard (`/health/*` preserved) |
| Rollback | Revert Terraform + satellite deploy |

**Pros**:
- Preserves standard `/health/*` paths
- No satellite code changes to route paths

**Cons**:
- Couples ALB configuration to satellite-internal route structure
- Requires Terraform changes in a separate repository (`autom8y`)
- ALB rule proliferation: each new satellite health sub-path needs an ALB rule
- More complex deployment: Terraform apply + satellite deploy coordination
- Fragile: adding a new health sub-endpoint requires infrastructure changes

### Option C: Consolidated Health in Handler API

Handler API aggregates satellite health via internal HTTP call. `/health` returns composite status.

| Dimension | Assessment |
|-----------|------------|
| Effort | ~0.5 day |
| Blast radius | Handler API + satellite (adds coupling) |
| Cross-repo changes | Handler API code changes required |
| Handler API changes | Required (new internal HTTP call to satellite) |
| Path convention | Standard (`/health` returns composite) |
| Rollback | Revert Handler API changes |

**Pros**:
- Single source of truth for external health status
- Clean external API surface

**Cons**:
- Couples Handler API to satellite internals (Handler API must know satellite health URL)
- Adds latency to Handler API health checks (internal HTTP round-trip)
- Handler API health check now depends on satellite being reachable
- Violates existing architecture: satellite owns its operational domain
- Requires Handler API code changes and deployment

## Recommendation: Option A (Path-Prefix Satellite Health)

Option A is the best fit for a MODULE-complexity remediation for three reasons:

1. **Minimal blast radius**: All changes are within the satellite codebase. No cross-repo Terraform (Option B) or Handler API coupling (Option C).

2. **Architectural alignment**: The satellite already owns its operational domain. Prefixing with `/satellite/` makes this ownership explicit and prevents future shadowing conflicts on any sub-path.

3. **Simplest deployment and rollback**: A single satellite deploy plus an ALB health check path configuration update. No multi-repo coordination required.

The non-standard path (`/satellite/health` instead of `/health`) is an acceptable tradeoff. Health check paths are infrastructure configuration, not user-facing API contracts. Monitoring tools and ALB configuration are the only consumers, and both are configurable.

## User Stories

### US-1: Satellite Readiness Probe Reachability

As an **infrastructure operator**, I want the satellite's readiness probe to be reachable at a non-shadowed path, so that future ALB traffic-holding configurations can gate on satellite cache warmth.

**Acceptance Criteria**:
- AC-1.1: `GET /satellite/health/ready` returns 200 with `{"status": "ready"}` when cache is warm
- AC-1.2: `GET /satellite/health/ready` returns 503 with `{"status": "warming"}` when cache is not ready
- AC-1.3: The endpoint does not require authentication
- AC-1.4: The endpoint is reachable in production (not shadowed by Handler API)

### US-2: Satellite S2S Connectivity Probe Reachability

As an **infrastructure operator**, I want the satellite's S2S connectivity probe to be reachable at a non-shadowed path, so that I can verify JWKS and bot PAT health from outside the container.

**Acceptance Criteria**:
- AC-2.1: `GET /satellite/health/s2s` returns 200 with S2S connectivity details when all dependencies are healthy
- AC-2.2: `GET /satellite/health/s2s` returns 503 with degraded status when any dependency is unhealthy
- AC-2.3: The endpoint does not require authentication
- AC-2.4: Response includes `s2s_connectivity`, `jwks_reachable`, `bot_pat_configured`, and `details` fields
- AC-2.5: The endpoint is reachable in production (not shadowed by Handler API)

### US-3: Satellite Liveness Probe Continuity

As an **infrastructure operator**, I want the satellite's liveness probe to continue functioning after the path change, so that the ALB does not kill healthy containers.

**Acceptance Criteria**:
- AC-3.1: `GET /satellite/health` returns 200 with `{"status": "healthy"}` regardless of cache state
- AC-3.2: ALB health check is updated to target `/satellite/health`
- AC-3.3: ALB health check continues to pass for healthy containers
- AC-3.4: No interruption to container health during deployment (zero-downtime rollout)

### US-4: No Regression to Existing Routing

As a **developer**, I want the path change to not affect any other endpoint routing, so that existing API consumers are unaffected.

**Acceptance Criteria**:
- AC-4.1: Handler API `/health` endpoint continues to return 200
- AC-4.2: All `/api/v1/*` satellite endpoints remain reachable
- AC-4.3: All `/api/handlers/*` Handler API endpoints remain reachable
- AC-4.4: No new 404s on any endpoint other than the old `/health/ready` and `/health/s2s` (which were already 404)

## Functional Requirements

### Must Have

- **FR-1**: Satellite health router prefix changes from `/health` to `/satellite/health` for all three endpoints (`/satellite/health`, `/satellite/health/ready`, `/satellite/health/s2s`)
- **FR-2**: Response bodies and status codes for all three endpoints remain identical to current behavior (only the path changes)
- **FR-3**: No authentication required on any `/satellite/health/*` endpoint
- **FR-4**: ALB health check target path is updated from `/health` to `/satellite/health`

### Should Have

- **FR-5**: Old `/health/ready` and `/health/s2s` paths return 404 (no redirect, no backward compatibility shim -- these were already 404 in production)
- **FR-6**: All existing health endpoint tests updated to use new paths

### Could Have

- **FR-7**: Structured log entry on startup confirming health endpoint prefix (aids debugging if ALB misconfiguration occurs)

## Non-Functional Requirements

- **NFR-1**: Performance -- Health endpoint response time does not increase (target: <10ms p99, same as current)
- **NFR-2**: Availability -- Zero-downtime deployment; ALB health check path update must be coordinated with satellite deploy to avoid a window where health checks fail
- **NFR-3**: Observability -- Health check paths in any existing metrics or dashboards are updated to reflect new paths

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| ALB health check hits old `/health` path after satellite deploy | Handler API still responds to `/health` with 200 -- no container kill. ALB config update can follow satellite deploy safely. |
| ALB health check updated to `/satellite/health` before satellite deploy | ALB gets 404 from Handler API. **Mitigation**: Deploy satellite first, then update ALB config. |
| Request to `/health/ready` after remediation | Returns 404 (Handler API has no such route). This is the same behavior as today -- no regression. |
| Request to `/satellite/health/ready` during cache warming | Returns 503 `{"status": "warming"}` as designed. |
| Request to `/satellite/health/s2s` when JWKS is unreachable | Returns 503 `{"status": "degraded"}` with details. |
| Container startup before cache is ready | `/satellite/health` returns 200 (liveness). `/satellite/health/ready` returns 503 (readiness). ALB does not kill the container. |
| Multiple containers in different states during rolling deploy | Each container independently reports its own health at `/satellite/health/*`. No cross-container interference. |

## Deployment Sequence

The order of operations matters to avoid a health check gap:

1. Deploy satellite with new `/satellite/health/*` routes (both old and new paths temporarily work within the satellite, but `/health/*` is still shadowed by Handler API -- no change in external behavior)
2. Verify `/satellite/health` returns 200 in production
3. Update ALB health check target path from `/health` to `/satellite/health`
4. Verify ALB health checks pass

Between steps 1 and 3, the ALB still checks `/health` (Handler API responds) -- no gap.

## Success Criteria

- [ ] TC-S15 smoke test passes: `GET /satellite/health/ready` returns 200 or 503 (not 404)
- [ ] TC-S15 smoke test passes: `GET /satellite/health/s2s` returns 200 or 503 (not 404)
- [ ] `GET /satellite/health` returns 200 with `{"status": "healthy"}`
- [ ] ALB health check passes using `/satellite/health` path
- [ ] No regression: Handler API `/health` continues returning 200
- [ ] No regression: All existing satellite API endpoints (`/api/v1/*`) remain reachable
- [ ] All health endpoint unit tests pass with updated paths
- [ ] Zero-downtime deployment (no container kills during rollout)

## Out of Scope

- Adding new health dimensions or check types
- Changing health check response bodies or status code logic
- Modifying Handler API health behavior or code
- Consolidating health across services (Option C -- separate initiative if desired)
- ALB listener rule changes (Option B -- rejected)
- Readiness gating logic changes (the readiness gate was removed with ADR-0148; re-introduction is a separate feature)
- Monitoring/alerting configuration changes beyond health check path

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| ALB health check path configuration | Infrastructure | Must be updated after satellite deploy. Configuration is per-target-group, no Terraform in external repo required. |
| Handler API `/health` route | Runtime (existing) | Must continue responding to `/health` for the transition window. No changes to Handler API. |

## Open Questions

None. All questions resolved during spike investigation.

## Traceability

| Requirement | Source |
|-------------|--------|
| FR-1 through FR-4 | Spike TC-S15 Option A |
| US-1 (readiness probe) | Sprint-materialization-002 FR-004 |
| US-2 (S2S probe) | PRD-S2S-001 NFR-OPS-002 |
| US-3 (liveness continuity) | FR-API-HEALTH-001, FR-API-HEALTH-002 |
| US-4 (no regression) | Operational requirement |
| NFR-2 (zero-downtime) | Standard deployment requirement |

## File Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-HEALTH-ENDPOINT-SHADOWING.md` | Read |
| Spike (source) | `/Users/tomtenuta/Code/autom8y-asana/docs/spikes/SPIKE-health-endpoint-shadowing.md` | Read |
| Health routes (source) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/health.py` | Read |
| App factory (source) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/main.py` | Read |
| Health tests (source) | `/Users/tomtenuta/Code/autom8y-asana/tests/api/test_health.py` | Read |
