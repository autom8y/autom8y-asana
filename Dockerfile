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
# Stage 1: Builder (using Lambda base for architecture compatibility)
# =============================================================================
FROM public.ecr.aws/lambda/python:3.12 AS builder

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

# Install dependencies using pip (not uv) for better cross-platform native extensions
# NOTE: Do NOT use editable mode (-e) as it creates .pth files pointing to build paths
# that won't exist in the runtime container
RUN pip install --target /packages ".[api,auth]" "awslambdaric>=2.2.0"

# =============================================================================
# Stage 2: Runtime (AWS Lambda Python base)
# =============================================================================
FROM public.ecr.aws/lambda/python:3.12 AS runtime

# Copy installed packages to Lambda task root
COPY --from=builder /packages /var/task

# Copy source code to Lambda task root
COPY --from=builder /build/src/autom8_asana /var/task/autom8_asana

# Ensure all files are readable (Lambda runs as sbx_user1051)
RUN chmod -R a+r /var/task

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Lambda handler
CMD ["autom8_asana.lambda_handlers.cache_warmer.handler"]
