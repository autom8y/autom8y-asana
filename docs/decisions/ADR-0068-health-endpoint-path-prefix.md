# ADR-0068: Health Endpoint Path Prefix (`/satellite/health`)

**Date**: 2026-02-20
**Status**: ACCEPTED
**Deciders**: TC-S15 Health Endpoint Shadowing Remediation
**Supersedes**: None

---

## Context

The satellite (`autom8_asana`) and the Handler API are co-located behind the shared domain `asana.api.autom8y.io`. Both services register routes under `/health`. The Handler API's routes take precedence in the request routing chain, shadowing the satellite's `/health/ready` and `/health/s2s` endpoints.

The shadowing was discovered during QA smoke testing (TC-S15). In production:
- `GET /health` returns 200 from the Handler API (satellite shadowed but functionally equivalent)
- `GET /health/ready` returns 404 (Handler API has no such route; satellite is shadowed)
- `GET /health/s2s` returns 404 (same reason)

The routing chain is:

```
Client -> Cloudflare -> ALB (host-header rule, priority 120)
       -> ECS Target Group (port 8000)
       -> Container (uvicorn, dual-mode)
       -> Handler API catches /health/* first
```

Current operational impact is zero because the compute-on-read architecture (ADR-0148) removed all startup-time readiness gating. However, any future feature requiring readiness gating would be blocked by this shadowing, and discovering that under time pressure is worse than fixing it proactively.

The ALB liveness health check (`/health`) works today because the Handler API responds to it.

---

## Decision

**Path-prefix all satellite health endpoints from `/health/*` to `/satellite/health/*`.**

The satellite's `APIRouter` for health endpoints gains `prefix="/satellite"`. The three endpoints become:

| Before | After |
|--------|-------|
| `GET /health` | `GET /satellite/health` |
| `GET /health/ready` | `GET /satellite/health/ready` |
| `GET /health/s2s` | `GET /satellite/health/s2s` |

The ALB target group health check path and ECS container HEALTHCHECK path are updated from `/health` to `/satellite/health` via Terraform (`health_check_path` variable on the asana service module).

Response bodies, status codes, and endpoint behavior are unchanged.

---

## Alternatives Considered

### Option A: Path-Prefix Satellite Health (Selected)

Change satellite health routes from `/health/*` to `/satellite/health/*`. Update ALB health check target path.

**Pros**:
- Minimal blast radius: changes confined to the satellite codebase
- Zero Handler API changes: no cross-team coordination
- Clear namespace ownership: `/satellite/health/*` is unambiguously satellite-owned
- Simplest deployment: single service deploy + ALB config update
- Prevents future shadowing: any route added to the health router automatically gets the prefix

**Cons**:
- Non-standard path for health checks (`/satellite/health` instead of `/health`)
- ALB and ECS health check configuration must be updated

### Option B: ALB Route-Split

Add path-based ALB listener rules to route `/health/ready` and `/health/s2s` directly to the satellite target group, leaving `/health` routed to the Handler API.

**Pros**:
- Preserves standard `/health/*` path convention
- No satellite code changes to route paths

**Cons**:
- Couples ALB configuration to satellite-internal route structure
- Requires Terraform changes in a separate repository (`autom8y`) for route rules
- ALB rule proliferation: each new satellite health sub-path needs a new ALB listener rule
- More complex deployment: Terraform apply + satellite deploy coordination
- Fragile: adding a new health sub-endpoint requires infrastructure changes

### Option C: Consolidated Health in Handler API

Handler API aggregates satellite health via internal HTTP call. `/health` returns composite status.

**Pros**:
- Single source of truth for external health status
- Clean external API surface

**Cons**:
- Couples Handler API to satellite internals (must know satellite health URL)
- Adds latency to Handler API health checks (internal HTTP round-trip)
- Handler API health check now depends on satellite being reachable
- Violates existing architecture: satellite owns its operational domain
- Requires Handler API code changes and deployment

---

## Rationale

Option A was selected for three reasons:

1. **Blast radius minimization**. All code changes are in the satellite repository. The only infrastructure change is a single Terraform variable (`health_check_path`). No Handler API modifications. No ALB listener rule additions. No cross-service runtime coupling.

2. **Architectural alignment**. The satellite already owns its operational domain. The prefix makes this ownership explicit in the URL namespace. The Handler API's `/health` continues to work independently. Each service's health is independently addressable.

3. **Future-proofing via the router prefix pattern**. Using `APIRouter(prefix="/satellite")` means any future health endpoint added to the health router automatically gets the `/satellite/` prefix. Option B would require an infrastructure change for each new health sub-endpoint. Option C would require Handler API changes for each new health dimension.

The non-standard path (`/satellite/health` instead of `/health`) is acceptable because health check paths are infrastructure configuration, not user-facing API contracts. The only consumers are the ALB health check (configurable) and operational tooling (also configurable).

---

## Consequences

### Positive

1. Satellite readiness and S2S connectivity probes become externally reachable for the first time in production
2. Clear namespace separation eliminates all current and future health endpoint shadowing
3. Deployment risk is minimal due to safe ordering (satellite first, Terraform second)
4. Router prefix pattern prevents accidental re-shadowing on future health sub-endpoints

### Negative

1. Non-standard health check path requires awareness in operational runbooks and monitoring configuration
2. Two-step deployment (satellite then Terraform) required; cannot be atomic
3. OpenAPI spec changes (path updates) -- minor but must be included in the PR

### Neutral

1. Handler API's `/health` endpoint is completely unaffected
2. The old `/health/ready` and `/health/s2s` paths continue to return 404 (same as before the fix -- these were never reachable)

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| PRD: Health Endpoint Shadowing Remediation | Requirements source |
| TDD: Health Endpoint Shadowing Remediation | Implementation design |
| Spike: SPIKE-health-endpoint-shadowing | Root cause investigation |
| ADR-0148 (compute-on-read architecture) | Removed readiness gate that originally surfaced this issue |
