# SPIKE: Health Endpoint Shadowing (TC-S15)

## Status: RESEARCH COMPLETE

**Date**: 2026-02-20
**Timebox**: 30 min (spike only, no production code)
**Origin**: QA smoke test TC-S15 (MEDIUM, pre-existing)
**Trigger**: Production smoke test revealed `/health/ready` and `/health/s2s` unreachable

## Question

Why are the satellite's `/health/ready` and `/health/s2s` endpoints unreachable at `asana.api.autom8y.io`, and what's the operational risk?

## Findings

### Architecture

The satellite defines 3 health endpoints in `src/autom8_asana/api/routes/health.py`:

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `GET /health` | Liveness probe | Always 200 |
| `GET /health/ready` | Readiness (cache warmth) | 200 or 503 |
| `GET /health/s2s` | S2S connectivity (JWKS + bot PAT) | 200 or 503 |

All three are mounted at the app root (no prefix) via `main.py:171`.

### Shadowing Mechanism

The domain `asana.api.autom8y.io` serves two co-located services:
- **Handler API** (v2.0.0): Claims `/health`, `/api/handlers`, `/auth/*`, `/getter/*`
- **Satellite (autom8_asana)**: Claims `/api/v1/*`, `/health`, `/health/ready`, `/health/s2s`

The Handler API's `/health` route takes precedence. The satellite's `/health/ready` and `/health/s2s` are shadowed — they return 404 from the Handler API rather than reaching the satellite.

### Infrastructure Chain

```
Client → Cloudflare → ALB (host: asana.api.autom8y.io, priority 120)
       → ECS Target Group (port 8000, health check: /health)
       → Container (uvicorn, dual-mode)
       → Handler API catches /health/* first
```

ALB health check uses `/health` (liveness, always 200) — this works because the Handler API responds to it.

### Operational Impact

**Current**: None. The compute-on-read-then-cache architecture (ADR-0148) removed all warm-up state:
- `timeline_warm_count`, `timeline_total`, `timeline_warm_failed` — all deleted
- TIMELINE_NOT_READY/WARM_FAILED 503 codes — deleted
- Readiness gate — deleted

There is currently **nothing for `/health/ready` to gate on**.

**Future risk**: If a future feature re-introduces startup-time computation that requires readiness gating, the shadowed `/health/ready` endpoint cannot be used by the ALB to hold traffic. The ALB would route traffic to unready containers.

### Root Cause

The Handler API and Satellite share a domain but have overlapping route prefixes. The Handler API's catch-all for `/health` absorbs all sub-paths.

## Recommendation

**Defer** — file as a focused initiative for when it's needed.

### If/when a fix is needed, two options:

**Option A: Path-prefix the satellite health endpoints** (~0.5d)
- Change satellite health routes to `/satellite/health/*`
- Update ALB health check path to `/satellite/health`
- Pros: Zero Handler API changes. Satellite owns its namespace.
- Cons: Non-standard path for health checks.

**Option B: Route-split at ALB level** (~1d)
- Add path-based ALB listener rules to route `/health/ready` and `/health/s2s` to the satellite target group
- Requires Terraform changes in `autom8y` repo
- Pros: Standard paths preserved.
- Cons: Couples ALB config to satellite internals. ALB rule proliferation.

**Option C: Consolidate health into Handler API** (~0.5d)
- Handler API aggregates satellite health via internal HTTP call
- `/health` returns composite status
- Pros: Single source of truth. Clean external API.
- Cons: Handler API coupled to satellite internals.

### Recommended option: **None yet**

The readiness gate was removed. There is no current consumer of `/health/ready`. File this as a deferred item with trigger: "re-introduction of startup-time computation requiring readiness gating."

## Follow-up Actions

- [ ] File debt item D-XXX: Health endpoint shadowing (trigger: readiness gate needed)
- [ ] Consider Option A if satellite needs independent health signaling
- [ ] Consider Option C if moving to consolidated health aggregation across services
