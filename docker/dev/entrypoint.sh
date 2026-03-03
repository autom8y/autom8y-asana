#!/usr/bin/env bash
# Asana service dev entrypoint.
# No database, no migrations. Just starts uvicorn.
# See TDD-DEV-STACK-ENTRYPOINT-STANDARDIZATION.md, ADR-DSR-008.
set -euo pipefail

# Source shared library (monorepo mount preferred, local fallback)
if [ -f /app/entrypoint-lib.sh ]; then
    source /app/entrypoint-lib.sh
else
    # Minimal inline fallback for standalone satellite use
    dev_log() { echo "=== [$(date -u +%H:%M:%S)] $1 ==="; }
    dev_start_uvicorn() {
        exec uvicorn "$1" ${2:+"$2"} --host 0.0.0.0 --port 8000 \
            --reload --reload-dir /app/src --reload-dir /app/sdks
    }
fi

dev_log "Asana Service Startup (dev)"

export PYTHONPATH="/app/sdks:/app/src:${PYTHONPATH:-}"

dev_start_uvicorn "autom8_asana.api.main:create_app" "--factory"
