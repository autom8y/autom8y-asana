# autom8y-asana API Dockerfile
# Dual-mode container supporting both ECS (uvicorn) and Lambda (awslambdaric)
#
# Per TDD-ASANA-SATELLITE (FR-CICD-001):
# - Multi-stage build for minimal image size (<500MB)
# - Health check for container orchestration
# - Dual-mode entrypoint for ECS and Lambda deployment
#
# WP-LOCK: Uses uv.lock as single source of truth for dependency resolution.
# No resolution happens at build time -- uv sync --no-sources ensures registry
# resolution instead of monorepo path deps (DEF-009/SCAR-022).
#
# Build args:
#   EXTRA_INDEX_URL: Optional URL for private package index (e.g., CodeArtifact)
#
# Execution modes (auto-detected via AWS_LAMBDA_RUNTIME_API):
#   ECS Mode:   Starts uvicorn server on port 8000
#   Lambda Mode: Invokes handler via awslambdaric (requires CMD override)
#
# Usage:
#   docker build -t autom8y-asana:latest .
#   docker run -p 8000:8000 autom8y-asana:latest  # ECS mode (default)

# =============================================================================
# Stage 0: AWS Parameters and Secrets Lambda Extension (v12, x86_64)
# =============================================================================
# Container-image Lambdas (package_type=Image) cannot use Lambda Layers; the
# secrets-extension binary MUST be embedded in the image. This stage mirrors
# the canonical pattern from services/pull-payments/Dockerfile (autom8y monorepo).
#
# Source: Official Lambda Layer published by AWS
#   ARN: arn:aws:lambda:us-east-1:177933569100:layer:AWS-Parameters-and-Secrets-Lambda-Extension:12
#
# CI passes a pre-signed URL via SECRETS_EXT_LAYER_URL build-arg. For local
# builds, generate the URL with:
#   aws lambda get-layer-version-by-arn \
#     --arn "arn:aws:lambda:us-east-1:177933569100:layer:AWS-Parameters-and-Secrets-Lambda-Extension:12" \
#     --query 'Content.Location' --output text
#
# When SECRETS_EXT_LAYER_URL is unset (e.g., ECS-only local builds that do
# not need the extension), the stage no-ops by emitting an empty extensions
# directory; the runtime COPY still succeeds and is harmless for ECS mode.
ARG SECRETS_EXT_LAYER_URL=""
FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal@sha256:ab55495e2cfb39304be022524faa3fd04469d6750b133a77618cfbbbc57e56e2 AS secrets-extension
ARG SECRETS_EXT_LAYER_URL
RUN if [ -n "$SECRETS_EXT_LAYER_URL" ]; then \
        dnf install -y unzip && \
        curl -sSL "${SECRETS_EXT_LAYER_URL}" -o /tmp/layer.zip && \
        unzip /tmp/layer.zip -d /opt && \
        rm /tmp/layer.zip && \
        test -f /opt/extensions/bootstrap; \
    else \
        mkdir -p /opt/extensions && \
        echo "SECRETS_EXT_LAYER_URL unset; emitting empty /opt/extensions (ECS-only build)"; \
    fi

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim@sha256:5072b08ad74609c5329ab4085a96dfa873de565fb4751a4cfcd7dcc427661df0 AS builder

# Install uv from official image
COPY --link --from=ghcr.io/astral-sh/uv:latest@sha256:5164bf84e7b4e2e08ce0b4c66b4a8c996a286e6959f72ac5c6e0a3c80e8cb04a /uv /usr/local/bin/uv

# Accept CodeArtifact index URL as build argument
ARG EXTRA_INDEX_URL
# Set UV_EXTRA_INDEX_URL for uv to use CodeArtifact as additional index (keeps PyPI as primary)
ENV UV_EXTRA_INDEX_URL=${EXTRA_INDEX_URL}

# Configure uv for reproducible builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency manifests first (layer caching)
# README.md is required by pyproject.toml metadata (readme = "README.md");
# hatchling build backend reads it during `uv sync` local-project build.
COPY --link pyproject.toml uv.lock README.md ./

# Copy source code
COPY --link src ./src

# Install production dependencies
# Includes api (FastAPI/uvicorn), auth (JWT), and lambda (awslambdaric) extras
# --no-sources: resolve from registry, not monorepo path deps (DEF-009/SCAR-022)
# --frozen omitted: mutually exclusive with --no-sources in uv >=0.15.4
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-sources --no-dev --extra api --extra auth --extra lambda

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim@sha256:5072b08ad74609c5329ab4085a96dfa873de565fb4751a4cfcd7dcc427661df0 AS runtime

# Create non-root user (UID/GID 1000 for EFS compatibility)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# AWS Parameters and Secrets Lambda Extension binary
# Resolves secrets at runtime via http://127.0.0.1:2773 in Lambda mode (consumed
# by the autom8y-config SDK lambda_extension client). Eliminates the need for
# deploy-time secret injection from Terraform. Inert in ECS mode (the extension
# is a Lambda runtime feature; presence in the image is harmless when no Lambda
# runtime is attached). Version pinned to :12 (x86_64) — see Stage 0 above.
# Reference: https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html
COPY --link --from=secrets-extension /opt/extensions/ /opt/extensions/

# Copy virtual environment and source from builder
# Use numeric UID:GID (--link requires numeric IDs since user table isn't available)
COPY --link --from=builder --chown=1000:1000 /app/.venv /app/.venv
COPY --link --from=builder --chown=1000:1000 /app/src /app/src

# Copy entrypoint script
COPY --link scripts/entrypoint.sh /app/entrypoint.sh

# Set ownership and permissions
RUN chown -R appuser:appuser /app && chmod +x /app/entrypoint.sh

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

# Switch to non-root user
USER appuser

# Dual-mode entrypoint: auto-detects ECS vs Lambda via AWS_LAMBDA_RUNTIME_API
# - ECS: Starts uvicorn server
# - Lambda: Requires CMD override with handler path
ENTRYPOINT ["/app/entrypoint.sh"]

# Default CMD for Lambda mode (override with task definition in Lambda)
# For ECS, the entrypoint ignores this and runs uvicorn
CMD ["autom8_asana.lambda_handlers.cache_warmer.handler"]
