# autom8_asana API Dockerfile
# Dual-mode container supporting both ECS (uvicorn) and Lambda (awslambdaric)
#
# Per TDD-ASANA-SATELLITE (FR-CICD-001):
# - Multi-stage build for minimal image size (<500MB)
# - Health check for container orchestration
# - Dual-mode entrypoint for ECS and Lambda deployment
#
# WP-LOCK: Uses uv.lock as single source of truth for dependency resolution.
# No resolution happens at build time -- uv sync --frozen enforces lockfile
# consistency and fails if uv.lock is stale.
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

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Accept CodeArtifact index URL as build argument
ARG EXTRA_INDEX_URL
# Set UV_EXTRA_INDEX_URL for uv to use CodeArtifact as additional index (keeps PyPI as primary)
ENV UV_EXTRA_INDEX_URL=${EXTRA_INDEX_URL}

# Configure uv for reproducible builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency manifests first (layer caching)
COPY pyproject.toml uv.lock ./

# Copy source code
COPY src ./src

# Install production dependencies with frozen lockfile
# Includes api (FastAPI/uvicorn), auth (JWT), and lambda (awslambdaric) extras
RUN uv sync --frozen --no-dev --extra api --extra auth --extra lambda

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Copy entrypoint script
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set PATH to use venv (replaces PYTHONPATH approach)
ENV PATH="/app/.venv/bin:${PATH}" \
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
