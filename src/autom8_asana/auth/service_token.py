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

from autom8y_config.lambda_extension import resolve_secret_from_env


class ServiceTokenAuthProvider:
    """AuthProvider that exchanges ServiceAccount credentials for JWT via TokenManager.

    Satisfies ``protocols.auth.AuthProvider`` protocol. TokenManager handles
    caching, refresh, retry, and backoff internally.

    Args:
        client_id: ServiceAccount client_id. Defaults to SERVICE_CLIENT_ID env var.
        client_secret: ServiceAccount client_secret. Defaults to
            ``resolve_secret_from_env("SERVICE_CLIENT_SECRET")`` -- resolves the
            ``_ARN``-suffixed key on Lambda (secret_arns delivery via the
            secrets extension) and falls back to the bare name on ECS / local.
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
        # W-AUTH: read SERVICE_CLIENT_SECRET via resolve_secret_from_env so the
        # provider is delivery-convention-agnostic. ECS injects the bare name via
        # terraform `external_secrets`; the scheduled-lambda module injects it via
        # `secret_arns`, which renames the key to SERVICE_CLIENT_SECRET_ARN
        # (`${k}_ARN`) and resolves the ARN lazily through the Parameters-and-
        # Secrets extension. resolve_secret_from_env keys on `<name>_ARN` first
        # (Lambda) and falls back to the bare `<name>` (ECS / local dev), so a
        # single read is correct on BOTH topologies. A bare os.environ.get was
        # blind to the Lambda `_ARN` convention -> the insights-export
        # `succeeded:0` dark-export. RuntimeError (extension HTTP failure) is
        # deliberately NOT caught here: it must propagate honestly (raise-and-500
        # at workflow_handler.py top-level) rather than degrade to a silent
        # no-credential path. Only the absent-secret ValueError is narrowed into
        # the explicit credentials-required error below.
        csecret = client_secret
        if not csecret:
            try:
                csecret = resolve_secret_from_env("SERVICE_CLIENT_SECRET")
            except ValueError:
                csecret = ""
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
