# autom8_asana API Dockerfile
# Dual-mode container supporting both ECS (uvicorn) and Lambda (awslambdaric)
#
# Per TDD-ASANA-SATELLITE (FR-CICD-001):
# - Multi-stage build for minimal image size (<500MB)
# - Health check for container orchestration
# - Dual-mode entrypoint for ECS and Lambda deployment
#
# Build args:
#   EXTRA_INDEX_URL: Optional URL for private package index (e.g., CodeArtifact)
#
# Execution modes (auto-detected via AWS_LAMBDA_RUNTIME_API):
#   ECS Mode:   Starts uvicorn server on port 8000
#   Lambda Mode: Invokes handler via awslambdaric (requires CMD override)
#
# Usage:
#   docker build -t autom8_asana:latest .
#   docker run -p 8000:8000 autom8_asana:latest  # ECS mode (default)

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim AS builder

# Build arguments for private package index
ARG EXTRA_INDEX_URL

# Environment for pip
ENV PIP_EXTRA_INDEX_URL=${EXTRA_INDEX_URL} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Copy source code
COPY src ./src

# Install dependencies using pip
# Include awslambdaric for Lambda mode support
RUN pip install --target /packages ".[api,auth]" "awslambdaric>=2.2.0"

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages
COPY --from=builder /packages /app/packages

# Copy source code
COPY --from=builder /build/src/autom8_asana /app/autom8_asana

# Copy entrypoint script
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Add packages to Python path
ENV PYTHONPATH="/app/packages:/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose API port for ECS
EXPOSE 8000

# Health check for ECS container orchestration
# Per FR-API-HEALTH-001: GET /health returns 200 when healthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Dual-mode entrypoint: auto-detects ECS vs Lambda via AWS_LAMBDA_RUNTIME_API
# - ECS: Starts uvicorn server
# - Lambda: Requires CMD override with handler path
ENTRYPOINT ["/app/entrypoint.sh"]

# Default CMD for Lambda mode (override with task definition in Lambda)
# For ECS, the entrypoint ignores this and runs uvicorn
CMD ["autom8_asana.lambda_handlers.cache_warmer.handler"]
