# autom8_asana API Dockerfile
# Multi-stage build for production-ready container
#
# Per TDD-ASANA-SATELLITE (FR-CICD-001):
# - Multi-stage build for minimal image size (<500MB)
# - Non-root user for security
# - Health check for container orchestration
#
# Build args:
#   EXTRA_INDEX_URL: Optional URL for private package index (e.g., CodeArtifact)
#
# Usage:
#   docker build -t autom8_asana:latest .
#   docker run -p 8000:8000 autom8_asana:latest

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Build arguments for private package index
ARG EXTRA_INDEX_URL
ENV UV_EXTRA_INDEX_URL=${EXTRA_INDEX_URL}

# Optimize Python and uv behavior
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Copy source code
COPY src ./src

# Install dependencies with [api] and [s2s] extras
# --frozen ensures lockfile is used exactly
# --no-dev excludes development dependencies
# --extra s2s includes autom8y-auth SDK for S2S authentication
RUN uv sync --frozen --no-dev --extra api --extra s2s

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check for container orchestration
# Per FR-API-HEALTH-001: GET /health returns 200 when healthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run uvicorn with factory pattern
# --factory: create_app is a factory function, not an app instance
CMD ["uvicorn", "autom8_asana.api.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
