# SPIKE: Lambda RIC Dual-Mode Docker Support

**Date**: 2026-01-08
**Status**: COMPLETE
**Decision**: ADOPT - Option A (Dual-Mode Entrypoint)

## Question

How do we modify our existing ECS-only Dockerfile to support both ECS (uvicorn API server) and AWS Lambda (cache warmer handler) execution from the same container image?

## Context

We deployed a cache warmer Lambda to production using the same ECR image as our ECS service. The Lambda invocation failed with:

```
Runtime.InvalidEntrypoint: exec "autom8_asana.lambda_handlers.cache_warmer.handler": executable file not found in $PATH
```

**Root Cause**: The Dockerfile builds for ECS-only (runs uvicorn directly) and lacks the AWS Lambda Runtime Interface Client (RIC) required for Lambda container execution.

## Research Findings

### AWS Lambda Container Requirements

Lambda containers require:
1. **Lambda Runtime Interface Client (RIC)** - Implements Lambda Runtime API protocol
2. **Specific entrypoint** - Must invoke handler via RIC, not directly
3. **Handler format** - Module path like `package.module.function`

The `awslambdaric` Python package provides RIC implementation.

### Detection Mechanism

Lambda sets `AWS_LAMBDA_RUNTIME_API` environment variable at runtime:
- **Present**: Running in Lambda
- **Absent**: Running elsewhere (ECS, local, etc.)

### Options Evaluated

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Dual Entrypoint** | Single script detects context | Single image, simple infra | Medium Dockerfile complexity |
| **B. CMD Override** | Terraform overrides CMD | Minimal Dockerfile changes | Infra coupling, error-prone |
| **C. Multi-Target** | Separate Docker targets | Clean separation | Two images to manage |
| **D. Separate Files** | Different Dockerfiles | Full control | Duplication, drift risk |

**Selected**: Option A - Dual-Mode Entrypoint Script

## POC Implementation

### Files Created

1. **`scripts/entrypoint.sh`** - Dual-mode detection script
```bash
#!/bin/bash
set -e

if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    # ECS mode: run uvicorn API server
    exec uvicorn autom8_asana.api.main:create_app --host 0.0.0.0 --port 8000 --factory
else
    # Lambda mode: run handler via awslambdaric
    exec python -m awslambdaric "$@"
fi
```

2. **Dockerfile Updates**
```dockerfile
# Install awslambdaric in builder
RUN uv sync --frozen --no-dev --extra api --extra auth && \
    uv pip install awslambdaric

# Copy entrypoint script
COPY --chown=appuser:appuser scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Dual-mode entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["autom8_asana.lambda_handlers.cache_warmer.handler"]
```

### How It Works

**ECS Execution** (AWS_LAMBDA_RUNTIME_API unset):
```
docker run -p 8000:8000 image:tag
→ Runs uvicorn server on port 8000
```

**Lambda Execution** (AWS_LAMBDA_RUNTIME_API set by Lambda):
```
Lambda invokes container
→ Runs awslambdaric with handler path from CMD
```

## Production Hardening Required

### P0 - Critical (Before Production)
- [ ] Add `awslambdaric` to `pyproject.toml` with version pinning
- [ ] Add structured logging with mode detection
- [ ] Validate handler path format before execution
- [ ] Add graceful shutdown signal handling

### P1 - Important
- [ ] Make uvicorn host/port configurable via env vars
- [ ] Add startup health checks
- [ ] Create separate health check strategies for Lambda vs ECS
- [ ] Add timeout handling for Lambda cold starts

### P2 - Nice to Have
- [ ] Add Lambda RIE for local testing
- [ ] Create integration tests for mode switching
- [ ] Add metrics for mode detection and startup time

## Deliberate Shortcuts (POC)

1. **awslambdaric installed via pip** - Should be in pyproject.toml
2. **No error handling** - Only `set -e` for basic safety
3. **No logging** - Silent operation, no debugging output
4. **Hardcoded configuration** - Ports and hosts not configurable
5. **Health check mismatch** - Only works in ECS mode

## Validation Steps

### Local ECS Mode
```bash
docker build -t autom8_asana:test .
docker run -p 8000:8000 autom8_asana:test
curl http://localhost:8000/health
```

### Local Lambda Mode (with RIE)
```bash
# Install Lambda Runtime Interface Emulator
docker run -p 9000:8080 \
  -e AWS_LAMBDA_RUNTIME_API=localhost:8080 \
  autom8_asana:test

# Invoke handler
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"projects": ["1201081073731555"]}'
```

### AWS Lambda Test
```bash
# After image push
just cache-warm-lambda env=production
just cache-warm-lambda-logs env=production
```

## Recommendation

**ADOPT** the dual-mode entrypoint pattern with the following next steps:

1. **Immediate**: Complete P0 hardening items
2. **This Sprint**: Build and push updated image
3. **Validation**: Test Lambda invocation in staging then production
4. **Follow-up**: Add RIE-based integration tests to CI

## Effort Estimate

| Task | Effort |
|------|--------|
| P0 Hardening | 2-3 hours |
| Build & Push | 30 minutes |
| Staging Validation | 1 hour |
| Production Deployment | 30 minutes |
| **Total** | ~4-5 hours |

## References

- [AWS Lambda Python Container Images](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html)
- [AWS Lambda RIC GitHub](https://github.com/aws/aws-lambda-python-runtime-interface-client)
- [Lambda Runtime Interface Emulator](https://github.com/aws/aws-lambda-runtime-interface-emulator)
- [Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
