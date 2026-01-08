# POC: Lambda RIC Dual-Mode Docker Image

## Objective
Validate the dual-mode entrypoint pattern for running both ECS (uvicorn) and Lambda (handler) from the same Docker image using AWS Lambda Runtime Interface Client (awslambdaric).

## Implementation Summary

### Files Modified
1. **Dockerfile** (`/Users/tomtenuta/Code/autom8_asana/Dockerfile`)
   - Added `awslambdaric` installation in builder stage
   - Copied entrypoint script to runtime stage
   - Changed from `CMD` to `ENTRYPOINT` + `CMD` pattern
   - Default handler: `autom8_asana.lambda_handlers.cache_warmer.handler`

2. **Entrypoint Script** (`/Users/tomtenuta/Code/autom8_asana/scripts/entrypoint.sh`)
   - Detects execution context via `AWS_LAMBDA_RUNTIME_API` environment variable
   - ECS mode: runs `uvicorn autom8_asana.api.main:create_app --host 0.0.0.0 --port 8000 --factory`
   - Lambda mode: runs `python -m awslambdaric "$@"` with handler path from CMD

### How It Works

**ECS Execution:**
```bash
docker run -p 8000:8000 autom8_asana:latest
# AWS_LAMBDA_RUNTIME_API not set → entrypoint.sh runs uvicorn
```

**Lambda Execution:**
```bash
docker run -e AWS_LAMBDA_RUNTIME_API=host:port autom8_asana:latest [optional-handler-override]
# AWS_LAMBDA_RUNTIME_API set → entrypoint.sh runs awslambdaric with handler
```

**Handler Override Example:**
```bash
docker run -e AWS_LAMBDA_RUNTIME_API=host:port \
  autom8_asana:latest \
  autom8_asana.lambda_handlers.cache_warmer.handler
```

## Deliberate Shortcuts (POC Only)

### 1. Error Handling
- ❌ No validation of `AWS_LAMBDA_RUNTIME_API` format
- ❌ No fallback behavior if uvicorn/awslambdaric fails to start
- ❌ No environment variable validation (e.g., checking for required secrets)
- ❌ Single `set -e` for error handling (no granular failure modes)

### 2. Logging & Observability
- ❌ No structured logging from entrypoint script
- ❌ No startup confirmation messages
- ❌ No debugging output for mode detection
- ❌ No metrics or traces for entrypoint execution

### 3. Configuration
- ❌ Hardcoded host `0.0.0.0` and port `8000` for ECS
- ❌ Hardcoded handler path in CMD (not configurable via env)
- ❌ No support for multiple handler types without CMD override
- ❌ No configurable uvicorn workers, reload, or logging settings

### 4. Health Checks
- ❌ HEALTHCHECK only works in ECS mode (fails silently in Lambda)
- ❌ No separate health check strategy for Lambda mode
- ❌ No readiness vs. liveness differentiation

### 5. Shutdown & Signals
- ❌ No graceful shutdown handling for SIGTERM/SIGINT
- ❌ No signal forwarding to child processes
- ❌ No cleanup logic for resources

### 6. Security
- ❌ No input sanitization for CMD arguments
- ❌ No validation that handler path is within expected modules
- ❌ No runtime security scanning or compliance checks

### 7. Dependency Management
- ❌ `awslambdaric` installed via `uv pip install` (not in pyproject.toml)
- ❌ No version pinning for awslambdaric
- ❌ Not tracked in dependency lockfile

### 8. Testing
- ❌ No automated tests for entrypoint script behavior
- ❌ No smoke tests for ECS vs Lambda mode switching
- ❌ No integration tests with actual Lambda Runtime API emulator

## Production Hardening Checklist

### Critical (P0)
- [ ] Add awslambdaric to pyproject.toml with version constraint
- [ ] Validate AWS_LAMBDA_RUNTIME_API format before passing to awslambdaric
- [ ] Add structured logging (JSON) to entrypoint script with mode detection
- [ ] Implement graceful shutdown handling with signal forwarding
- [ ] Add input validation and sanitization for CMD arguments
- [ ] Create separate health check strategies for ECS and Lambda modes
- [ ] Add startup health checks before declaring ready

### Important (P1)
- [ ] Make host, port, and handler configurable via environment variables
- [ ] Add fallback behavior for startup failures (retry logic, alerting)
- [ ] Add debugging mode (verbose logging) controlled by env var
- [ ] Add timeout and retry logic for critical operations
- [ ] Add metrics and traces for entrypoint execution (CloudWatch, X-Ray)
- [ ] Create integration tests with Lambda RIE (Runtime Interface Emulator)
- [ ] Document deployment patterns for ECS vs Lambda (Terraform examples)

### Nice-to-Have (P2)
- [ ] Support multiple handler types without CMD override (routing logic)
- [ ] Add configurable uvicorn settings (workers, reload, log level)
- [ ] Add runtime security scanning and compliance checks
- [ ] Create smoke test suite for mode switching
- [ ] Add entrypoint script unit tests (bats or similar)
- [ ] Add performance benchmarks for mode detection overhead

## Validation Steps (Not Executed in POC)

### Local ECS Mode Test
```bash
docker build -t autom8_asana:poc .
docker run -p 8000:8000 autom8_asana:poc
curl http://localhost:8000/health  # Should return 200
```

### Local Lambda Mode Test (with Lambda RIE)
```bash
# Install Lambda Runtime Interface Emulator
docker pull amazon/aws-lambda-rie:latest

# Run container with RIE
docker run -d -v ~/.aws-lambda-rie:/aws-lambda -p 9000:8080 \
  --entrypoint /aws-lambda/aws-lambda-rie \
  autom8_asana:poc \
  /app/entrypoint.sh autom8_asana.lambda_handlers.cache_warmer.handler

# Invoke handler
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"entity_types": ["unit"], "strict": false}'
```

### AWS Lambda Test
```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag autom8_asana:poc <account>.dkr.ecr.us-east-1.amazonaws.com/autom8-asana:poc
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/autom8-asana:poc

# Deploy Lambda function with container image
# Configure handler override in Lambda configuration if needed
```

### ECS Task Test
```bash
# Deploy to ECS with existing task definition
# Ensure AWS_LAMBDA_RUNTIME_API is NOT set in container environment
# Verify service health checks pass
```

## Decision Points

### Why awslambdaric?
- Official AWS Lambda Runtime Interface Client for Python
- Maintained by AWS (better long-term support than alternatives)
- Standard approach recommended in AWS documentation
- Minimal additional dependencies

### Why Environment Variable Detection?
- `AWS_LAMBDA_RUNTIME_API` is automatically set by Lambda runtime
- No custom configuration needed
- Clear separation of concerns (runtime controls mode, not application)
- Standard pattern across AWS Lambda container images

### Why Single Entrypoint Script?
- Simplifies Dockerfile (single ENTRYPOINT)
- Centralized mode detection logic
- Easier to debug and maintain than multiple image variants
- Follows AWS best practices for dual-mode images

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Health check fails silently in Lambda mode | Medium | High | Add conditional health check logic in entrypoint |
| awslambdaric version mismatch | High | Medium | Pin version in pyproject.toml, test with RIE |
| Handler path injection | High | Low | Validate handler path against allowlist |
| Startup failure cascades | High | Low | Add fallback behavior and alerting |
| Performance overhead from mode detection | Low | Low | Benchmark entrypoint execution time |

## Next Steps

1. **Immediate (before merging POC):**
   - Add awslambdaric to pyproject.toml with version constraint
   - Test with Lambda RIE locally to validate handler invocation
   - Document deployment patterns in TDD

2. **Short-term (before production deployment):**
   - Implement P0 hardening items (logging, validation, graceful shutdown)
   - Create integration tests with RIE
   - Add CloudWatch metrics for entrypoint mode detection

3. **Long-term (production readiness):**
   - Complete P1 hardening items
   - Add comprehensive test suite (unit, integration, E2E)
   - Document operational runbooks for troubleshooting

## References
- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [AWS Lambda Runtime Interface Clients](https://docs.aws.amazon.com/lambda/latest/dg/runtimes-images.html#runtimes-api-client)
- [awslambdaric GitHub](https://github.com/aws/aws-lambda-python-runtime-interface-client)
- [Technology Scout Report: Lambda RIC Integration](docs/spikes/SPIKE-platform-schema-lookup-abstraction.md)
