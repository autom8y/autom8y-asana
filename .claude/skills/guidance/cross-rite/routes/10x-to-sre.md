# 10x-to-SRE Handoff Checklist

> Artifact checklist for handing off deployment-ready work to sre.

## When to Use

This route is **required** when:
- Complexity is SERVICE or PLATFORM
- Feature involves production deployment
- Infrastructure changes needed (new services, scaling, storage)
- Observability instrumentation required

## Artifact Checklist

### Deployment Manifest

- [ ] Deployment configuration exists (k8s, docker-compose, or IaC)
- [ ] Container image tagged and pushed to registry
- [ ] Service dependencies documented (databases, caches, queues)
- [ ] Network configuration specified (ports, protocols, load balancing)
- [ ] Scaling configuration defined (min/max replicas, autoscaling triggers)

**Location**: `deploy/` or `infra/` directory

### Runbook Draft

- [ ] Startup procedure documented (init sequence, warm-up, health checks)
- [ ] Shutdown procedure documented (graceful termination, drain connections)
- [ ] Health check endpoints defined (`/health`, `/ready`, `/live`)
- [ ] Troubleshooting guide for common issues
- [ ] Rollback procedure documented (steps to revert deployment)
- [ ] Incident escalation path defined

**Location**: `docs/runbooks/` or handoff artifact

### Environment Variables

- [ ] All environment variables documented with descriptions
- [ ] Required vs optional clearly marked
- [ ] Default values specified where applicable
- [ ] Secrets identified (to be managed by secret store, not committed)
- [ ] Environment-specific values noted (dev, staging, prod)

**Format**:
```
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | - | PostgreSQL connection string |
| LOG_LEVEL | No | info | Logging verbosity |
```

### Resource Requirements

- [ ] CPU requirements specified (requests and limits)
- [ ] Memory requirements specified (requests and limits)
- [ ] Storage requirements documented (volume size, type, IOPS)
- [ ] Network bandwidth estimates (if applicable)
- [ ] Cost estimate provided (for cloud resources)

**Format**:
```yaml
resources:
  requests:
    cpu: "100m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
storage:
  size: "10Gi"
  type: "ssd"
```

### Observability

- [ ] Logging format documented (structured JSON recommended)
- [ ] Key log events identified for alerting
- [ ] Metrics endpoints exposed (`/metrics` for Prometheus)
- [ ] Critical metrics identified for SLOs
- [ ] Tracing instrumentation added (if distributed system)

## Validation

Run before handoff:
```bash
ari hook handoff-validate --route=sre
```

Expected output:
```
[PASS] Deployment manifest found: deploy/kubernetes/
[PASS] Runbook exists: docs/runbooks/service-name.md
[PASS] Environment variables documented: docs/config/env-vars.md
[PASS] Resource requirements specified in deployment manifest
[WARN] Observability: metrics endpoint not verified (manual check needed)
```

## HANDOFF Artifact Template

Create `HANDOFF-10x-dev-to-sre-YYYY-MM-DD.md`:

```yaml
---
artifact_id: HANDOFF-10x-dev-to-sre-2026-01-05
schema_version: "1.0"
source_rite: 10x-dev
target_rite: sre
handoff_type: validation
priority: high
blocking: true
initiative: "feature-name"
created_at: "2026-01-05T12:00:00Z"
status: pending
items:
  - id: DEPLOY-001
    summary: "Deploy feature-name service to production"
    priority: high
    validation_scope:
      - "Verify deployment manifest correctness"
      - "Validate resource requirements are appropriate"
      - "Confirm health checks pass in staging"
      - "Review runbook completeness"
source_artifacts:
  - "deploy/kubernetes/feature-name.yaml"
  - "docs/runbooks/feature-name.md"
  - "docs/config/feature-name-env.md"
---
```

## After Handoff

SRE rite will:
1. Review deployment configuration
2. Validate in staging environment
3. Schedule production deployment window
4. Execute deployment with monitoring
5. Return HANDOFF-RESPONSE with deployment status

## Common Issues

| Issue | Resolution |
|-------|------------|
| Missing health checks | Add `/health` endpoint returning 200 OK |
| Undefined resource limits | Profile in staging, set conservative limits |
| No rollback procedure | Document revert steps, test in staging |
| Secrets in config | Move to secret store, reference by name only |
