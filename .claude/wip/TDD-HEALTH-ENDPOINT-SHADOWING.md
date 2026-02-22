# TDD: Health Endpoint Shadowing Remediation (TC-S15)

## Overview

Path-prefix the satellite's three health endpoints from `/health/*` to `/satellite/health/*` to eliminate namespace collision with the Handler API at the shared domain `asana.api.autom8y.io`. The change is confined to the satellite codebase (one router prefix change, test updates, OpenAPI spec regeneration) plus a coordinated Terraform variable update for the ALB and ECS container health check paths.

## Context

- **PRD**: `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-HEALTH-ENDPOINT-SHADOWING.md`
- **Spike**: `/Users/tomtenuta/Code/autom8y-asana/docs/spikes/SPIKE-health-endpoint-shadowing.md`
- **ADR**: `/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0068-health-endpoint-path-prefix.md`
- **Selected Approach**: Option A -- Path-prefix satellite health endpoints

### Constraint Summary

| Constraint | Source |
|------------|--------|
| Zero downtime during rollout | NFR-2 |
| No Handler API code changes | PRD scope |
| Response bodies unchanged | FR-2 |
| No authentication on health endpoints | FR-3 |

---

## System Design

### Architecture (Before)

```
Client -> Cloudflare -> ALB (host: asana.api.autom8y.io, priority 120)
       -> ECS Target Group (port 8000, health check: /health)
       -> Container (uvicorn, dual-mode)
       -> Handler API catches /health/* first (SHADOWING)
```

### Architecture (After)

```
Client -> Cloudflare -> ALB (host: asana.api.autom8y.io, priority 120)
       -> ECS Target Group (port 8000, health check: /satellite/health)
       -> Container (uvicorn, dual-mode)
       -> Handler API: /health (unchanged)
       -> Satellite:   /satellite/health/* (no longer shadowed)
```

### Components Affected

| Component | Repository | Change |
|-----------|-----------|--------|
| Health router | `autom8y-asana` | Prefix change on `APIRouter` |
| Health tests | `autom8y-asana` | Path updates in all test methods |
| OpenAPI spec | `autom8y-asana` | Regenerate after route change |
| Routes `__init__.py` docstring | `autom8y-asana` | Update route documentation |
| ALB health check path | `autom8y` (Terraform) | `health_check_path` variable |
| ECS container health check path | `autom8y` (Terraform) | Same variable (cascades) |

---

## Code Changes (Satellite Repository)

### 1. Health Router Prefix (`health.py`)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/health.py`

**Current** (line 47):
```python
router = APIRouter(tags=["health"])
```

**Target**:
```python
router = APIRouter(prefix="/satellite", tags=["health"])
```

**Rationale**: Using the `APIRouter(prefix=...)` parameter is the idiomatic FastAPI approach. It changes the prefix for all routes attached to this router in a single place. The individual `@router.get(...)` decorators retain their existing paths (`/health`, `/health/ready`, `/health/s2s`) -- FastAPI prepends the prefix automatically.

**Result**:
| Current Path | New Path |
|-------------|----------|
| `GET /health` | `GET /satellite/health` |
| `GET /health/ready` | `GET /satellite/health/ready` |
| `GET /health/s2s` | `GET /satellite/health/s2s` |

**Alternative considered**: Changing individual route paths (e.g., `@router.get("/satellite/health")`). Rejected because the prefix approach is DRY and prevents future routes from accidentally omitting the prefix.

### 2. Docstring Updates (`health.py`)

Update module-level docstring and individual endpoint docstrings to reference the new paths. Specifically:
- Module docstring: Change `GET /health`, `GET /health/ready`, `GET /health/s2s` references to new paths
- `health_check()` docstring: Update path reference and `For cache readiness checks` pointer
- `readiness_check()` docstring: Update `The ALB should use /satellite/health` reference
- `s2s_health_check()` docstring: No path references in body, no change needed

### 3. Routes `__init__.py` Docstring

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/__init__.py`

Update the module-level docstring to reflect `Health router (/satellite/health)` instead of `Health router (/health)`.

### 4. Test Updates (`test_health.py`)

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/api/test_health.py`

All `client.get("/health")` calls become `client.get("/satellite/health")`.
All `client.get("/health/ready")` calls become `client.get("/satellite/health/ready")`.
All `client.get("/health/s2s")` calls become `client.get("/satellite/health/s2s")`.

Update module-level docstring and class-level docstrings to reference new paths.

**Affected test classes and methods** (exhaustive list):

| Class | Method | Path Change |
|-------|--------|-------------|
| `TestHealthEndpoint` | `test_health_returns_200` | `/health` -> `/satellite/health` |
| `TestHealthEndpoint` | `test_health_response_structure` | `/health` -> `/satellite/health` |
| `TestHealthEndpoint` | `test_health_version_format` | `/health` -> `/satellite/health` |
| `TestHealthEndpoint` | `test_health_no_auth_required` | `/health` -> `/satellite/health` (x2) |
| `TestHealthEndpoint` | `test_health_content_type` | `/health` -> `/satellite/health` |
| `TestS2SHealthEndpoint` | `test_s2s_health_returns_expected_fields` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_no_auth_required` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_reports_bot_pat_not_configured` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_reports_bot_pat_configured` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_status_healthy_when_all_dependencies_ok` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_status_degraded_when_jwks_unreachable` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_status_degraded_when_bot_pat_missing` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_handles_invalid_jwks_response` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestS2SHealthEndpoint` | `test_s2s_health_handles_jwks_connection_error` | `/health/s2s` -> `/satellite/health/s2s` |
| `TestCacheReadiness` | `test_health_returns_200_always_even_when_cache_not_ready` | `/health` -> `/satellite/health` |
| `TestCacheReadiness` | `test_health_includes_cache_ready_flag` | `/health` -> `/satellite/health` (x2) |
| `TestCacheReadiness` | `test_readiness_returns_503_when_cache_not_ready` | `/health/ready` -> `/satellite/health/ready` |
| `TestCacheReadiness` | `test_readiness_returns_200_when_cache_ready` | `/health/ready` -> `/satellite/health/ready` |
| `TestCacheReadiness` | `test_health_always_includes_version` | `/health` -> `/satellite/health` (x2) |
| `TestCacheReadiness` | `test_readiness_warming_includes_version` | `/health/ready` -> `/satellite/health/ready` |
| `TestCacheReadiness` | `test_health_warming_no_auth_required` | `/health` -> `/satellite/health` (x2), `/health/ready` -> `/satellite/health/ready` (x2) |
| `TestCacheReadiness` | `test_readiness_state_transition` | `/health/ready` -> `/satellite/health/ready` (x3) |
| `TestCacheReadiness` | `test_liveness_stable_during_state_transitions` | `/health` -> `/satellite/health` (x3) |

### 5. OpenAPI Spec Regeneration

**File**: `/Users/tomtenuta/Code/autom8y-asana/docs/api-reference/openapi.yaml`

Regenerate via the standard method (running the app and exporting the OpenAPI schema). The new spec will reflect:
- `/satellite/health` instead of `/health`
- `/satellite/health/ready` instead of `/health/ready`
- `/satellite/health/s2s` instead of `/health/s2s`
- `operationId` values will update automatically (e.g., `health_check_satellite_health_get`)

---

## Infrastructure Changes (Terraform)

### ALB Target Group Health Check

**Current Configuration**:

The asana service at `/Users/tomtenuta/code/autom8y/terraform/services/asana/main.tf` calls the `service-stateless` stack module without overriding `health_check_path`. The stack default is `/health` (defined in `/Users/tomtenuta/code/autom8y/terraform/modules/platform/stacks/service-stateless/variables.tf`, line 148).

The health check path flows through two layers:

1. **ALB target group** (`alb-target-group/main.tf`, line 36): `path = var.health_check_path` -- used by ALB to check container health externally
2. **ECS container HEALTHCHECK** (`ecs-fargate-service/main.tf`, line 147): `coalesce(var.container_health_check_path, var.health_check_path)` -- used by ECS agent to check container health locally

Both currently resolve to `/health` because neither is overridden.

**Target Configuration**:

Add `health_check_path = "/satellite/health"` to the `module "service"` block in `/Users/tomtenuta/code/autom8y/terraform/services/asana/main.tf`:

```hcl
module "service" {
  source = "../../modules/platform/stacks/service-stateless"

  # ... existing variables ...

  # Health check path - prefixed to avoid Handler API shadowing
  # See ADR-0068 in autom8y-asana repo
  health_check_path = "/satellite/health"
}
```

**Effect**:
- ALB target group health check path: `/health` -> `/satellite/health`
- ECS container HEALTHCHECK command: `urllib.request.urlopen('http://localhost:8000/health')` -> `urllib.request.urlopen('http://localhost:8000/satellite/health')`
- The `container_health_check_path` variable does NOT need to be set separately because the ECS module's `coalesce()` falls back to `health_check_path`

**Health check matcher**: The ALB health check `matcher` is hardcoded to `"200"` in the `alb-target-group` module. The `/satellite/health` endpoint always returns 200 (liveness probe). No change needed.

---

## Deployment Sequence

### Prerequisites

- Satellite PR merged and image built
- Terraform change prepared (not yet applied)

### Step-by-Step Deployment

```
Phase 1: Deploy Satellite (autom8y-asana)
  1. Merge satellite PR (prefix change)
  2. CI builds and pushes new container image
  3. ECS rolling deploy begins

  During rolling deploy:
  - OLD containers: /health responds (via Handler API shadowing), /satellite/health does NOT exist
  - NEW containers: /satellite/health responds, /health also responds (via Handler API)
  - ALB health check still targets /health -> both old and new containers pass
  - ECS container HEALTHCHECK still targets /health -> both old and new containers pass

  4. Rolling deploy completes. All containers are new.
  5. Verify: curl https://asana.api.autom8y.io/satellite/health -> 200

Phase 2: Update Terraform (autom8y)
  6. Apply Terraform change: health_check_path = "/satellite/health"
  7. AWS updates ALB target group health check path
  8. AWS updates ECS task definition with new container HEALTHCHECK

  During Terraform apply:
  - ALB switches health check to /satellite/health
  - All containers (already new) respond to /satellite/health -> health checks pass
  - ECS task definition updates; next task launch uses new HEALTHCHECK
  - Running tasks continue using old HEALTHCHECK until next deployment

  9. Verify: ALB target group health check shows "healthy" in AWS console
```

### Why This Order Is Safe

**Satellite first, Terraform second**:
- Between steps 3 and 6, the ALB still checks `/health`. The Handler API responds to `/health` with 200. No gap.
- If step 6 were applied first (Terraform before satellite), the ALB would check `/satellite/health` on containers that do not have that route yet. The Handler API does not serve `/satellite/health`. Result: 404 -> containers marked unhealthy -> service outage.

**The critical invariant**: At every point in the deployment, the ALB health check path must resolve to a 200-returning endpoint on every running container.

### Rollback Plan

| Scenario | Action |
|----------|--------|
| Satellite deploy fails (containers crash) | ECS rolls back automatically (minimum healthy percent) |
| Satellite deployed but `/satellite/health` returns errors | Revert satellite PR, redeploy. ALB still checks `/health` (Handler API) -- no impact. |
| Terraform applied but health checks fail | Revert Terraform (`health_check_path` back to default). ALB reverts to `/health`. Handler API still responds. |
| Both deployed, new containers fail | Revert satellite code, redeploy. Then revert Terraform. Order: satellite first (to get `/health` route back locally for ECS HEALTHCHECK), then Terraform. |

---

## Interface Contract

### `GET /satellite/health` (Liveness Probe)

**Purpose**: Indicates the application process is running. Always returns 200.

```
Request:
  GET /satellite/health
  No authentication required.

Response (200 OK):
  Content-Type: application/json
  {
    "status": "healthy",
    "version": "0.1.0",
    "cache_ready": true | false
  }
```

No error responses. This endpoint always returns 200 if the process is running.

### `GET /satellite/health/ready` (Readiness Probe)

**Purpose**: Indicates whether the cache is warm and the service can serve traffic optimally.

```
Request:
  GET /satellite/health/ready
  No authentication required.

Response (200 OK -- cache ready):
  Content-Type: application/json
  {
    "status": "ready",
    "version": "0.1.0"
  }

Response (503 Service Unavailable -- cache warming):
  Content-Type: application/json
  {
    "status": "warming",
    "version": "0.1.0",
    "message": "Cache preload in progress"
  }
```

### `GET /satellite/health/s2s` (S2S Connectivity Probe)

**Purpose**: Verifies JWKS endpoint reachability and bot PAT configuration.

```
Request:
  GET /satellite/health/s2s
  No authentication required.

Response (200 OK -- all dependencies healthy):
  Content-Type: application/json
  {
    "status": "healthy",
    "version": "0.1.0",
    "s2s_connectivity": true,
    "jwks_reachable": true,
    "bot_pat_configured": true,
    "details": {
      "jwks_status": "reachable",
      "bot_pat_status": "configured"
    }
  }

Response (503 Service Unavailable -- degraded):
  Content-Type: application/json
  {
    "status": "degraded",
    "version": "0.1.0",
    "s2s_connectivity": false,
    "jwks_reachable": false | true,
    "bot_pat_configured": false | true,
    "details": {
      "jwks_status": "timeout" | "connection_error" | "invalid_response" | "error" | "http_{code}",
      "bot_pat_status": "configured" | "not_configured"
    }
  }
```

---

## Non-Functional Considerations

### Performance

No performance impact. The prefix is a routing concern resolved at startup (FastAPI builds the route table once). No additional middleware, no additional computation per request.

### Security

No security impact. The endpoints remain unauthenticated (by design -- health checks must not require credentials). No new endpoints are added. No new data is exposed.

### Observability

The following artifacts reference the old `/health` paths and should be updated:

| Artifact | Location | Action |
|----------|----------|--------|
| OpenAPI spec | `docs/api-reference/openapi.yaml` | Regenerate (automatic) |
| Grafana dashboards (if any reference health paths) | `autom8y` repo | Check and update if needed |
| CloudWatch Insights queries | `autom8y` repo | Check `shared/cloudwatch_queries.tf` |

The Grafana alerting file at `/Users/tomtenuta/code/autom8y/terraform/services/grafana/alerting.tf` references the asana service but should be checked for hardcoded health check path references.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Terraform applied before satellite deploy | Low | High (service outage) | Deployment runbook specifies order. PR descriptions cross-reference. |
| ECS container HEALTHCHECK fails during transition | Low | Medium (container restart) | Container HEALTHCHECK uses `coalesce()` -- both old and new paths work during rolling deploy as long as ALB/ECS config has not changed yet. |
| Monitoring dashboards reference old path | Low | Low (cosmetic) | Check Grafana dashboards post-deploy. |
| Future developer adds health route without `/satellite` prefix | Low | Low (shadowed again) | Router prefix on `APIRouter` makes this automatic for routes added to the health router. Only a new router would bypass it. |
| OpenAPI spec not regenerated | Low | Low (documentation drift) | Include in PR checklist. |

---

## Implementation Checklist

### Satellite Repository (`autom8y-asana`)

- [ ] Change `APIRouter(tags=["health"])` to `APIRouter(prefix="/satellite", tags=["health"])` in `health.py`
- [ ] Update docstrings in `health.py` to reference new paths
- [ ] Update docstring in `routes/__init__.py`
- [ ] Update all test paths in `test_health.py` (34 path references across 22 test methods)
- [ ] Update test docstrings and class docstrings in `test_health.py`
- [ ] Regenerate `docs/api-reference/openapi.yaml`
- [ ] Run full test suite, confirm all health tests pass
- [ ] PR merged, image built and pushed

### Infrastructure Repository (`autom8y`)

- [ ] Add `health_check_path = "/satellite/health"` to `services/asana/main.tf` module block
- [ ] Terraform plan (verify only health check path changes, no other resource modifications)
- [ ] Apply after satellite deploy is confirmed healthy

### Post-Deployment Verification

- [ ] `curl https://asana.api.autom8y.io/satellite/health` returns 200
- [ ] `curl https://asana.api.autom8y.io/satellite/health/ready` returns 200 or 503 (not 404)
- [ ] `curl https://asana.api.autom8y.io/satellite/health/s2s` returns 200 or 503 (not 404)
- [ ] `curl https://asana.api.autom8y.io/health` returns 200 (Handler API, unchanged)
- [ ] ALB target group shows all targets healthy in AWS console
- [ ] No ECS container restarts or task failures

---

## ADRs

- [ADR-0068: Health Endpoint Path Prefix](/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0068-health-endpoint-path-prefix.md)

## Open Items

None. All design questions resolved during spike and PRD phases.

---

## File Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-HEALTH-ENDPOINT-SHADOWING.md` | Read |
| Spike | `/Users/tomtenuta/Code/autom8y-asana/docs/spikes/SPIKE-health-endpoint-shadowing.md` | Read |
| Health routes | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/health.py` | Read |
| App factory | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/main.py` | Read |
| Routes init | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/__init__.py` | Read |
| Health tests | `/Users/tomtenuta/Code/autom8y-asana/tests/api/test_health.py` | Read |
| OpenAPI spec | `/Users/tomtenuta/Code/autom8y-asana/docs/api-reference/openapi.yaml` | Read |
| Terraform: asana service | `/Users/tomtenuta/code/autom8y/terraform/services/asana/main.tf` | Read |
| Terraform: service-stateless stack | `/Users/tomtenuta/code/autom8y/terraform/modules/platform/stacks/service-stateless/main.tf` | Read |
| Terraform: service-stateless vars | `/Users/tomtenuta/code/autom8y/terraform/modules/platform/stacks/service-stateless/variables.tf` | Read |
| Terraform: ALB target group | `/Users/tomtenuta/code/autom8y/terraform/modules/platform/primitives/alb-target-group/main.tf` | Read |
| Terraform: ALB target group vars | `/Users/tomtenuta/code/autom8y/terraform/modules/platform/primitives/alb-target-group/variables.tf` | Read |
| Terraform: ECS Fargate service | `/Users/tomtenuta/code/autom8y/terraform/modules/platform/primitives/ecs-fargate-service/main.tf` | Read (health check lines) |
| Terraform: ECS Fargate vars | `/Users/tomtenuta/code/autom8y/terraform/modules/platform/primitives/ecs-fargate-service/variables.tf` | Read |
| ADR-0067 (format reference) | `/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0067-cache-system-divergence.md` | Read |
