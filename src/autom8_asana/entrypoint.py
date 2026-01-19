"""
Dual-mode entrypoint for ECS (uvicorn) and Lambda (awslambdaric).

Detects execution context via AWS_LAMBDA_RUNTIME_API environment variable:
- Absent: ECS mode - starts uvicorn API server
- Present: Lambda mode - invokes handler via awslambdaric
"""

import json
import os
import sys
from datetime import UTC, datetime


def log(level: str, message: str) -> None:
    """Emit structured JSON log line."""
    entry = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "component": "entrypoint",
        "message": message,
    }
    print(json.dumps(entry), flush=True)


def log_info(message: str) -> None:
    log("INFO", message)


def log_error(message: str) -> None:
    log("ERROR", message)


def run_ecs_mode() -> None:
    """Start uvicorn API server for ECS deployment."""
    import uvicorn

    log_info("Starting in ECS mode")

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))

    log_info(f"Launching uvicorn on {host}:{port}")

    uvicorn.run(
        "autom8_asana.api.main:create_app",
        host=host,
        port=port,
        factory=True,
    )


def run_lambda_mode(handler: str) -> None:
    """Start Lambda handler via awslambdaric."""
    import awslambdaric

    runtime_api = os.environ.get("AWS_LAMBDA_RUNTIME_API", "")
    log_info("Starting in Lambda mode")
    log_info(f"Runtime API: {runtime_api}")
    log_info(f"Invoking handler: {handler}")

    # awslambdaric.main expects sys.argv to contain the handler
    sys.argv = ["awslambdaric", handler]
    awslambdaric.main()


def main() -> None:
    """Detect execution mode and run appropriate entrypoint."""
    runtime_api = os.environ.get("AWS_LAMBDA_RUNTIME_API")

    if not runtime_api:
        # ECS mode
        run_ecs_mode()
    else:
        # Lambda mode - handler passed as first argument
        if len(sys.argv) < 2:
            log_error(
                "No handler specified. Usage: python -m autom8_asana.entrypoint <handler>"
            )
            log_error(
                "Example: python -m autom8_asana.entrypoint autom8_asana.lambda_handlers.cache_warmer.handler"
            )
            sys.exit(1)

        handler = sys.argv[1]

        # Basic validation
        if not all(c.isalnum() or c in "._" for c in handler):
            log_error(f"Invalid handler format: {handler}")
            log_error("Handler must be a valid Python module path")
            sys.exit(1)

        run_lambda_mode(handler)


if __name__ == "__main__":
    main()
