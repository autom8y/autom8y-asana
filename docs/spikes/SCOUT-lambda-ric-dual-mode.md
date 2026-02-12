# SCOUT-lambda-ric-dual-mode

## Executive Summary

AWS Lambda Runtime Interface Client (awslambdaric) enables Python container images built with custom base images (like `python:3.12-slim`) to run in AWS Lambda. The current autom8_asana Dockerfile uses `python:3.12-slim` with uvicorn for ECS, but lacks Lambda compatibility. **Verdict: Adopt** - implementing a dual-mode entrypoint script that detects the execution environment via `AWS_LAMBDA_RUNTIME_API` is the proven pattern used across AWS documentation and the community. This approach allows the same ECR image to serve both ECS (uvicorn API) and Lambda (cache warmer handler) with minimal Dockerfile changes.

## Technology Overview

- **Category**: Runtime Interface / Container Tooling
- **Maturity**: Mainstream (GA since December 2020)
- **License**: Apache 2.0
- **Backing**: AWS (official first-party package)

## The Problem

The cache warmer Lambda invocation failed with:
```
Runtime.InvalidEntrypoint: exec "autom8_asana.lambda_handlers.cache_warmer.handler": executable file not found in $PATH
```

**Root Cause**: Lambda expects either:
1. An AWS base image with built-in Lambda runtime, OR
2. A custom image with `awslambdaric` installed and properly configured ENTRYPOINT/CMD

The current Dockerfile has neither - it runs uvicorn directly via CMD.

## Capabilities

**awslambdaric provides:**
- Lambda Runtime API client implementation for Python
- Managed interaction between Lambda service and function code
- Handler invocation with event/context parsing
- Response serialization back to Lambda

**Environment Detection via `AWS_LAMBDA_RUNTIME_API`:**
- Set automatically by Lambda runtime
- Absent in ECS/local environments
- Enables single entrypoint script for dual-mode execution

## Limitations

- Adds ~10MB to image size (minor)
- Requires entrypoint script logic
- Build dependencies needed for older base images (gcc, cmake, libcurl)
- Python 3.9+ required (we use 3.12, no issue)

## Ecosystem Assessment

- **Community**: Official AWS package, 300+ GitHub stars, active maintenance
- **Documentation**: AWS official docs cover this pattern extensively
- **Tooling**: Works with AWS SAM, CDK, Terraform - no special handling needed
- **Adoption**: Standard pattern for Lambda container images since 2020

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Architecture mismatch (x86 vs ARM) | Low | High | Use `--platform linux/amd64` in docker build |
| Entrypoint script bugs | Low | Medium | Test both paths in CI |
| awslambdaric version incompatibility | Very Low | Medium | Pin to stable version |
| Handler not found in path | Low | High | Use absolute module paths |

## Fit Assessment

- **Philosophy Alignment**: Single-image deployment matches DRY principle and simplifies CI/CD
- **Stack Compatibility**: Works with existing python:3.12-slim base, uv package manager, multi-stage build
- **Team Readiness**: Standard Python packaging, minimal learning curve

---

## Implementation Options

### Option A: Dual-Mode Entrypoint Script (Recommended)

Add `awslambdaric` dependency and create an entrypoint script that detects the execution environment.

**entrypoint.sh:**
```bash
#!/bin/bash
set -e

if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    # ECS/Local mode: Run uvicorn API server
    exec uvicorn autom8_asana.api.main:create_app --host 0.0.0.0 --port 8000 --factory
else
    # Lambda mode: Run Lambda Runtime Interface Client with handler
    exec python -m awslambdaric "$@"
fi
```

**Dockerfile changes:**
```dockerfile
# In builder stage, add awslambdaric
RUN uv sync --frozen --no-dev --extra api --extra auth --extra lambda

# In runtime stage
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["autom8_asana.lambda_handlers.cache_warmer.handler"]
```

**Lambda deployment override:**
- No changes needed - uses default CMD

**ECS deployment override:**
- Override CMD to empty (or don't set handler argument)
- Entrypoint detects ECS mode and runs uvicorn

**Pros:**
- Single image, single Dockerfile
- Minimal changes to existing build
- Lambda gets its handler, ECS gets uvicorn
- Easy to add more Lambda handlers via CMD override

**Cons:**
- Slight complexity in entrypoint script
- Need to understand environment detection

### Option B: ECS Task Definition CMD Override

Keep existing Dockerfile for ECS, override ENTRYPOINT/CMD in Lambda function configuration.

**Dockerfile stays focused on ECS:**
```dockerfile
# Add awslambdaric but keep uvicorn as default
RUN uv sync --frozen --no-dev --extra api --extra auth

# Default is still ECS mode
CMD ["uvicorn", "autom8_asana.api.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
```

**Lambda function configuration:**
```yaml
ImageConfig:
  EntryPoint:
    - "/usr/local/bin/python"
    - "-m"
    - "awslambdaric"
  Command:
    - "autom8_asana.lambda_handlers.cache_warmer.handler"
```

**Pros:**
- Dockerfile remains simple
- No entrypoint script needed
- Configuration lives in infrastructure code

**Cons:**
- Requires Terraform/CDK changes for every Lambda handler
- Less obvious what the image supports
- Must remember to configure Lambda correctly

### Option C: Multi-Stage Build with Lambda Target

Create a separate Docker target for Lambda-specific builds.

```dockerfile
# Shared builder stage
FROM python:3.12-slim AS builder
# ... existing builder code ...

# ECS runtime (existing)
FROM python:3.12-slim AS runtime-ecs
# ... existing runtime code ...
CMD ["uvicorn", ...]

# Lambda runtime
FROM python:3.12-slim AS runtime-lambda
# ... similar setup but with awslambdaric ...
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["autom8_asana.lambda_handlers.cache_warmer.handler"]
```

**Pros:**
- Clear separation of concerns
- Optimized images for each use case
- No runtime detection needed

**Cons:**
- Two images to build, tag, push
- Two ECR repositories (or complex tagging)
- More CI/CD complexity
- Violates single-image goal

### Option D: Separate Dockerfiles

Maintain separate `Dockerfile` (ECS) and `Dockerfile.lambda` (Lambda).

**Pros:**
- Maximum clarity
- Independent optimization

**Cons:**
- Code duplication
- Maintenance burden
- Drift between files
- Violates DRY principle

---

## Comparison Matrix

| Criteria | Option A: Dual Entrypoint | Option B: CMD Override | Option C: Multi-Target | Option D: Separate Files |
|----------|--------------------------|------------------------|------------------------|-------------------------|
| Single image | Yes | Yes | No (2 images) | No (2 images) |
| Single Dockerfile | Yes | Yes | Yes | No |
| Dockerfile complexity | Medium | Low | High | Low |
| Infrastructure complexity | Low | Medium | Medium | Low |
| New handler effort | Low (CMD only) | Medium (Terraform) | Medium (build target) | High (new Dockerfile) |
| CI/CD changes | Minimal | Minimal | Significant | Significant |
| Debugging clarity | Medium | High | High | High |
| Image size optimization | Good | Good | Best | Best |

---

## Recommendation

**Verdict**: Adopt (Option A: Dual-Mode Entrypoint Script)

**Rationale:**
1. **Single Image**: Maintains deployment simplicity - one ECR image serves all purposes
2. **Proven Pattern**: This is the documented AWS approach for non-AWS base images
3. **Minimal Changes**: ~20 lines of changes to existing Dockerfile
4. **Future-Proof**: Easy to add more Lambda handlers by varying CMD
5. **Team Fit**: Matches existing entrypoint.sh patterns in autom8y

**Why not Option B?** While simpler in Dockerfile, it pushes configuration to infrastructure, making it harder to understand what the image supports and requiring Terraform changes for each new handler.

**Why not Option C/D?** Multi-image approaches add CI/CD complexity and violate the goal of single-image deployment.

## Implementation Plan

### Phase 1: Add Lambda Dependency (30 min)

1. Add `lambda` extra to `pyproject.toml`:
```toml
[project.optional-dependencies]
lambda = [
    "awslambdaric>=2.0.0",
]
```

2. Update `uv.lock`

### Phase 2: Create Entrypoint Script (30 min)

Create `/Users/tomtenuta/Code/autom8_asana/scripts/entrypoint.sh`:
```bash
#!/bin/bash
set -e

if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    echo "ECS mode: Starting uvicorn..."
    exec uvicorn autom8_asana.api.main:create_app --host 0.0.0.0 --port 8000 --factory
else
    echo "Lambda mode: Starting awslambdaric with handler: $1"
    exec python -m awslambdaric "$@"
fi
```

### Phase 3: Update Dockerfile (30 min)

Modify `/Users/tomtenuta/Code/autom8_asana/Dockerfile`:
1. Add `--extra lambda` to uv sync
2. Copy and chmod entrypoint script
3. Change CMD to use entrypoint with default handler

### Phase 4: Update Lambda Infrastructure (15 min)

1. Remove any ENTRYPOINT/CMD overrides from Lambda Terraform
2. Lambda will use image defaults (entrypoint detects Lambda, CMD provides handler)

### Phase 5: Test Both Paths (1 hour)

1. Local ECS test: `docker run -p 8000:8000 image:tag` - should start uvicorn
2. Local Lambda test: Use AWS Lambda RIE for local testing
3. Deploy to staging and verify both ECS and Lambda work

### Total Effort: ~3 hours

---

## Next Steps

1. **Immediate**: Implement Option A (this spike provides the blueprint)
2. **Validation**: Test locally with Lambda Runtime Interface Emulator before deploy
3. **Rollout**: Deploy to staging first, verify cache warmer invocation succeeds
4. **Documentation**: Update deployment docs to note dual-mode capability

## Sources

- [AWS Lambda Python Container Image Documentation](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html)
- [AWS Lambda Runtime Interface Client GitHub](https://github.com/aws/aws-lambda-python-runtime-interface-client)
- [AWS Blog: Lambda Container Image Support](https://aws.amazon.com/blogs/aws/new-for-aws-lambda-container-image-support/)
- [FastAPI Container Deployment: Lambda and ECS](https://dev.to/eldritchideen/fastapi-container-deployment-with-aws-lambda-and-amazon-ecs-5a2o)
- [Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [AWS Lambda Runtime Interface Emulator](https://github.com/aws/aws-lambda-runtime-interface-emulator)
