"""Dual-mode authentication for autom8_asana.

This package provides authentication support for both:
- Service-to-service (S2S) calls with JWT tokens
- User pass-through with Asana PAT tokens

Per TDD-S2S-001:
- Token detection via dot counting (ADR-S2S-001)
- JWT validation via autom8y-auth SDK
- Bot PAT activation from environment (ADR-S2S-002)

Usage:
    # In route handlers, use the dependencies from api.dependencies:
    from autom8_asana.api.dependencies import get_auth_context, AuthContext

    @app.get("/api/v1/tasks")
    async def get_tasks(auth: AuthContext = Depends(get_auth_context)):
        # auth.mode is AuthMode.JWT or AuthMode.PAT
        # auth.asana_pat is the PAT to use for Asana API calls
        # auth.caller_service is set for JWT mode
        ...
"""

from .audit import (
    S2SAuditEntry,
    S2SAuditLogger,
    get_audit_logger,
    reset_audit_logger,
)
from .bot_pat import BotPATError, clear_bot_pat_cache, get_bot_pat
from .dual_mode import AuthMode, detect_token_type, get_auth_mode
from .jwt_validator import reset_auth_client, validate_service_token

__all__ = [
    # Dual mode
    "AuthMode",
    "detect_token_type",
    "get_auth_mode",
    # JWT validation
    "validate_service_token",
    "reset_auth_client",
    # Bot PAT
    "BotPATError",
    "get_bot_pat",
    "clear_bot_pat_cache",
    # Audit logging
    "S2SAuditEntry",
    "S2SAuditLogger",
    "get_audit_logger",
    "reset_audit_logger",
]
