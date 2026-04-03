"""Service token auth provider for cross-service JWT exchange.

Wraps autom8y_core.TokenManager to satisfy the AuthProvider protocol,
enabling DataServiceClient to authenticate with data-service using the
standard ServiceAccount client_credentials grant flow.

Used by:
- API DI factory (dependencies.py) for cross-service enrichment joins
- CLI data client factory (__main__.py) for --enrich / data-service joins
"""

from __future__ import annotations

import os


class ServiceTokenAuthProvider:
    """AuthProvider that exchanges ServiceAccount credentials for JWT via TokenManager.

    Satisfies ``protocols.auth.AuthProvider`` protocol. TokenManager handles
    caching, refresh, retry, and backoff internally.

    Args:
        client_id: ServiceAccount client_id. Defaults to SERVICE_CLIENT_ID env var.
        client_secret: ServiceAccount client_secret. Defaults to SERVICE_CLIENT_SECRET env var.
        auth_url: Auth service URL for JWT exchange.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        auth_url: str = "https://auth.api.autom8y.io",
    ) -> None:
        from autom8y_core import Config, TokenManager

        cid = client_id or os.environ.get("SERVICE_CLIENT_ID", "")
        csecret = client_secret or os.environ.get("SERVICE_CLIENT_SECRET", "")
        if not cid or not csecret:
            raise ValueError(
                "SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET are required for "
                "data-service authentication. Set them in the environment or "
                "pass client_id and client_secret explicitly."
            )

        config = Config(
            client_id=cid,
            client_secret=csecret,
            auth_url=auth_url,
            service_name="autom8y-asana",
        )
        self._manager = TokenManager(config)

    def get_secret(self, key: str) -> str:
        """Return JWT token (key parameter ignored — single-service auth)."""
        return self._manager.get_token()

    def close(self) -> None:
        """Release TokenManager resources."""
        self._manager.close()
