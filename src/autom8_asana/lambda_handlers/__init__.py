"""Lambda handlers for AWS Lambda functions.

Per TDD-DATAFRAME-CACHE-001: Provides Lambda handlers for cache operations
including pre-deployment warming and invalidation.

Per TDD-LOG-TRACE-LAMBDA: structured logging for Lambda handlers is configured
once at cold-start (this module's import) so log lines carry the active
OpenTelemetry trace_id/span_id and substring-matched sensitive fields are
redacted. ``configure_lambda_logging`` reads only LOG_* env vars (no
get_settings()), preserving this package's import-safety property, and is
idempotent (process-global guards in core.logging + autom8y_log). It runs
before the handler imports below so the structlog chain is wired before any
handler's first ``get_logger`` would otherwise auto-configure with defaults.

Handlers:
    - cache_warmer: Lambda handler for cache pre-warming
    - cache_invalidate: Lambda handler for cache invalidation
"""

from autom8_asana.lambda_handlers.logging_config import configure_lambda_logging

# Cold-start (module-import) wiring — runs ONCE, before handler imports trigger
# get_logger auto-config. Idempotent and env-only; see TDD-LOG-TRACE-LAMBDA.
configure_lambda_logging()

from autom8_asana.lambda_handlers.cache_invalidate import (  # noqa: E402
    handler as cache_invalidate_handler,
)
from autom8_asana.lambda_handlers.cache_warmer import (  # noqa: E402
    handler as cache_warmer_handler,
)
from autom8_asana.lambda_handlers.conversation_audit import (  # noqa: E402
    handler as conversation_audit_handler,
)
from autom8_asana.lambda_handlers.insights_export import (  # noqa: E402
    handler as insights_export_handler,
)
from autom8_asana.lambda_handlers.payment_reconciliation import (  # noqa: E402
    handler as payment_reconciliation_handler,
)

__all__ = [
    "cache_invalidate_handler",
    "cache_warmer_handler",
    "conversation_audit_handler",
    "insights_export_handler",
    "payment_reconciliation_handler",
]
