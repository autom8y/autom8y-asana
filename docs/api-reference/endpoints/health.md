# Health Endpoints

Health check endpoints for monitoring service availability and readiness.

## Endpoint Summary

| Endpoint | Purpose | Auth | Success | Failure |
|----------|---------|------|---------|---------|
| `GET /health` | Liveness probe | None | 200 (always) | - |
| `GET /health/ready` | Readiness probe | None | 200 (cache ready) | 503 (warming) |
| `GET /health/s2s` | S2S connectivity | None | 200 (all deps healthy) | 503 (deps unavailable) |

All health endpoints are unauthenticated and publicly accessible.

---

## GET /health

**Liveness probe** - Confirms the application process is running and accepting connections.

### Response Codes

- **200**: Application is running (always returned)

This endpoint always returns 200, even during cache warming or degraded states. Used by ALB/ECS health checks to determine if the container should remain alive. Do not use this for traffic routing decisions.

### Response Body

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "cache_ready": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"healthy"` |
| `version` | string | Current API version |
| `cache_ready` | boolean | Cache readiness state (observability only) |

---

## GET /health/ready

**Readiness probe** - Confirms the service is ready to handle traffic optimally.

### Response Codes

- **200**: Cache is warm, service ready for traffic
- **503**: Cache is warming, service may have degraded performance

Use this endpoint for traffic gating decisions that require warm cache (e.g., ALB target group routing, autoscaling readiness gates).

### Response Body (200 - Ready)

```json
{
  "status": "ready",
  "version": "0.1.0"
}
```

### Response Body (503 - Warming)

```json
{
  "status": "warming",
  "version": "0.1.0",
  "message": "Cache preload in progress"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"ready"` when cache warm, `"warming"` during preload |
| `version` | string | Current API version |
| `message` | string | (503 only) Human-readable status explanation |

### Example

```bash
curl -X GET https://api.autom8y.io/health/ready
```

---

## GET /health/s2s

**S2S connectivity check** - Verifies JWT authentication dependencies are available.

### Response Codes

- **200**: All S2S dependencies healthy
- **503**: One or more dependencies unavailable

Checks two critical dependencies:
1. **JWKS endpoint reachability** - Can fetch public keys for JWT signature validation
2. **Bot PAT configuration** - Asana Personal Access Token is configured

### Response Body (200 - Healthy)

```json
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
```

### Response Body (503 - Degraded)

```json
{
  "status": "degraded",
  "version": "0.1.0",
  "s2s_connectivity": false,
  "jwks_reachable": false,
  "bot_pat_configured": true,
  "details": {
    "jwks_status": "timeout",
    "bot_pat_status": "configured"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"healthy"` if all deps available, `"degraded"` otherwise |
| `version` | string | Current API version |
| `s2s_connectivity` | boolean | Overall S2S readiness (JWKS + PAT) |
| `jwks_reachable` | boolean | JWKS endpoint is reachable and valid |
| `bot_pat_configured` | boolean | Bot PAT environment variable is set |
| `details` | object | Detailed status for each component |

### Details Object

| Field | Possible Values | Description |
|-------|-----------------|-------------|
| `jwks_status` | `"reachable"`, `"timeout"`, `"connection_error"`, `"invalid_response"`, `"http_{code}"`, `"error"` | JWKS endpoint check result |
| `bot_pat_status` | `"configured"`, `"not_configured"` | Bot PAT presence check |

---

## Architecture Notes

### Health Check Layers

1. **Liveness** (`/health`): Process is running
2. **Readiness** (`/health/ready`): Service can handle traffic optimally
3. **Dependency Health** (`/health/s2s`): External integrations are available

### Recommended ALB Configuration

- **Health check path**: `/health` (liveness)
- **Readiness gate**: `/health/ready` (for target registration delay)
- **Monitoring**: `/health/s2s` (alerts for S2S degradation)

### Cache Warming Flow

During startup:
1. Application starts → `/health` returns 200 (container stays alive)
2. Cache preload begins → `/health/ready` returns 503
3. Cache preload completes → `set_cache_ready(True)` called
4. `/health/ready` returns 200 → ALB routes traffic

---

## See Also

- [API Overview](../overview.md)
- [Authentication](../authentication.md)
- [Deployment Architecture](../../architecture/deployment.md)
