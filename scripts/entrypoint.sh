#!/bin/sh
# =============================================================================
# Dual-Mode Entrypoint: ECS (uvicorn) and Lambda (awslambdaric)
# =============================================================================
# Detects execution context via AWS_LAMBDA_RUNTIME_API environment variable:
# - Absent: ECS mode - starts uvicorn API server
# - Present: Lambda mode - invokes handler via awslambdaric
#
# Configuration:
#   ECS Mode:
#     - API_HOST: Listen address (default: 0.0.0.0)
#     - API_PORT: Listen port (default: 8000)
#   Lambda Mode:
#     - CMD args: Handler module path (e.g., autom8_asana.lambda_handlers.cache_warmer.handler)

set -eu

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
log() {
    level="$1"
    shift
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf '{"timestamp":"%s","level":"%s","component":"entrypoint","message":"%s"}\n' "${timestamp}" "${level}" "$*"
}

log_info() { log "INFO" "$@"; }
log_error() { log "ERROR" "$@"; }

# -----------------------------------------------------------------------------
# Signal Handling
# -----------------------------------------------------------------------------
shutdown() {
    log_info "Received shutdown signal, terminating gracefully"
    exit 0
}

trap shutdown TERM INT

# -----------------------------------------------------------------------------
# Mode Detection and Execution
# -----------------------------------------------------------------------------
if [ -z "${AWS_LAMBDA_RUNTIME_API:-}" ]; then
    # ECS Mode: Run uvicorn API server
    log_info "Starting in ECS mode"

    API_HOST="${API_HOST:-0.0.0.0}"
    API_PORT="${API_PORT:-8000}"

    log_info "Launching uvicorn on ${API_HOST}:${API_PORT}"
    # Use python -m to ensure PYTHONPATH is respected for module resolution
    exec python -m uvicorn autom8_asana.api.main:create_app \
        --host "${API_HOST}" \
        --port "${API_PORT}" \
        --factory
else
    # Lambda Mode: Run handler via AWS Lambda Runtime Interface Client
    log_info "Starting in Lambda mode"
    log_info "Runtime API: ${AWS_LAMBDA_RUNTIME_API}"

    # Validate handler argument
    if [ $# -eq 0 ]; then
        log_error "No handler specified. Usage: entrypoint.sh <handler_module_path>"
        log_error "Example: entrypoint.sh autom8_asana.lambda_handlers.cache_warmer.handler"
        exit 1
    fi

    HANDLER="$1"

    # Basic validation: handler should look like a Python module path
    case "${HANDLER}" in
        *[!a-zA-Z0-9_.]*)
            log_error "Invalid handler format: ${HANDLER}"
            log_error "Handler must be a valid Python module path (e.g., package.module.function)"
            exit 1
            ;;
    esac

    log_info "Invoking handler: ${HANDLER}"
    exec python -m awslambdaric "${HANDLER}"
fi
