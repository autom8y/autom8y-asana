"""Default authentication providers.

This module provides authentication providers for different deployment scenarios:
- EnvAuthProvider: Read secrets from environment variables (default for standalone/ECS)
- SecretsManagerAuthProvider: Fetch secrets directly from AWS Secrets Manager
- NotConfiguredAuthProvider: Placeholder when no auth is configured

Per ADR-VAULT-001: Platform Service Auth uses Secrets Manager, not custom vaults.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.exceptions import AuthenticationError
from autom8_asana.settings import get_settings

if TYPE_CHECKING:
    from mypy_boto3_secretsmanager import SecretsManagerClient

logger = get_logger(__name__)


class EnvAuthProvider:
    """Auth provider that reads from environment variables.

    This is the default for standalone SDK usage. Uses Pydantic Settings
    for common keys (ASANA_PAT, ASANA_WORKSPACE_GID) with fallback to
    direct environment variable lookup for other keys.

    Example:
        export ASANA_PAT=your_token_here

        client = AsanaClient()  # Uses EnvAuthProvider by default
    """

    def get_secret(self, key: str) -> str:
        """Get secret from environment variable.

        For known keys (ASANA_PAT, ASANA_WORKSPACE_GID), uses the unified
        Pydantic Settings first, then falls back to direct env var lookup.

        Args:
            key: Environment variable name

        Returns:
            Value of environment variable

        Raises:
            AuthenticationError: If variable not set or empty
        """
        # Check Pydantic Settings first for known keys
        settings = get_settings()
        if key == "ASANA_PAT" and settings.asana.pat:
            pat_value = settings.asana.pat.get_secret_value()
            # Validate that the value isn't just whitespace
            if not pat_value.strip():
                raise AuthenticationError(
                    f"Environment variable '{key}' is empty. Provide a valid token value."
                )
            return pat_value
        if key == "ASANA_WORKSPACE_GID" and settings.asana.workspace_gid:
            # Validate that the value isn't just whitespace
            if not settings.asana.workspace_gid.strip():
                raise AuthenticationError(
                    f"Environment variable '{key}' is empty. Provide a valid token value."
                )
            return settings.asana.workspace_gid

        # Fall back to direct environment variable lookup
        value = os.environ.get(key)
        if value is None:
            raise AuthenticationError(
                f"Environment variable '{key}' not set. "
                f"Set it or provide a custom AuthProvider."
            )
        if not value.strip():
            raise AuthenticationError(
                f"Environment variable '{key}' is empty. Provide a valid token value."
            )
        return value


class NotConfiguredAuthProvider:
    """Placeholder auth provider that always raises.

    Used when neither token nor auth_provider is supplied.
    """

    def get_secret(self, key: str) -> str:
        raise AuthenticationError(
            "No authentication configured. Provide either 'token' parameter "
            "or 'auth_provider' to AsanaClient."
        )


class SecretsManagerAuthProvider:
    """Auth provider that fetches secrets from AWS Secrets Manager.

    This provider is designed for ECS Fargate deployments where secrets are
    stored in AWS Secrets Manager following the autom8y naming convention:
    autom8y/{service}/{secret_name}

    The provider caches secrets in memory to minimize API calls. Use clear_cache()
    to refresh secrets if they are rotated.

    Environment Variables:
        AWS_REGION: AWS region for Secrets Manager (default: us-east-1)

    Example:
        # Standard usage with autom8y naming convention
        provider = SecretsManagerAuthProvider(service_name="asana")
        pat = provider.get_secret("bot_pat")  # Fetches autom8y/asana/bot_pat

        # Custom secret path pattern
        provider = SecretsManagerAuthProvider(
            service_name="asana",
            secret_path_pattern="myorg/{service}/{key}"
        )

        # Use with AsanaClient
        client = AsanaClient(auth_provider=provider)

    Per ADR-VAULT-001: Uses AWS Secrets Manager for credential storage.
    Per autom8y naming convention: autom8y/{service}/{credential}
    """

    def __init__(
        self,
        service_name: str = "asana",
        *,
        secret_path_pattern: str = "autom8y/{service}/{key}",
        region: str | None = None,
        client: SecretsManagerClient | None = None,
    ) -> None:
        """Initialize SecretsManagerAuthProvider.

        Args:
            service_name: Service name for secret path construction (default: asana).
            secret_path_pattern: Pattern for constructing secret paths.
                Supports {service} and {key} placeholders.
                Default: autom8y/{service}/{key}
            region: AWS region for Secrets Manager. If None, uses AWS_REGION
                env var or defaults to us-east-1.
            client: Optional boto3 Secrets Manager client for testing/custom config.
                If None, creates a new client on first use.
        """
        self._service_name = service_name
        self._secret_path_pattern = secret_path_pattern
        self._region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._client = client
        self._cache: dict[str, str] = {}

    def _get_client(self) -> SecretsManagerClient:
        """Get or create boto3 Secrets Manager client.

        Returns:
            boto3 Secrets Manager client.

        Raises:
            AuthenticationError: If boto3 is not installed.
        """
        if self._client is not None:
            return self._client

        try:
            import boto3
        except ImportError as e:
            raise AuthenticationError(
                "boto3 is required for SecretsManagerAuthProvider. "
                "Install with: pip install boto3"
            ) from e

        self._client = boto3.client("secretsmanager", region_name=self._region)
        return self._client

    def _build_secret_path(self, key: str) -> str:
        """Build full secret path from key.

        Args:
            key: Secret key name (e.g., "bot_pat", "workspace_gid").

        Returns:
            Full secret path (e.g., "autom8y/asana/bot_pat").
        """
        return self._secret_path_pattern.format(
            service=self._service_name,
            key=key,
        )

    def get_secret(self, key: str) -> str:
        """Retrieve a secret value from AWS Secrets Manager.

        Args:
            key: Secret key name (e.g., "bot_pat", "workspace_gid").
                Will be combined with service_name and pattern to form
                the full secret path.

        Returns:
            Secret value as string.

        Raises:
            AuthenticationError: If secret not found, access denied, or AWS error.

        Example:
            >>> provider = SecretsManagerAuthProvider(service_name="asana")
            >>> pat = provider.get_secret("bot_pat")  # Fetches autom8y/asana/bot_pat
        """
        # Check cache first
        if key in self._cache:
            logger.debug("secrets_cache_hit", extra={"key": key})
            return self._cache[key]

        secret_path = self._build_secret_path(key)
        logger.debug(
            "secrets_fetch",
            extra={"key": key, "path": secret_path, "region": self._region},
        )

        try:
            client = self._get_client()
            response = client.get_secret_value(SecretId=secret_path)

            # Handle string secrets (not binary)
            if "SecretString" in response:
                value = response["SecretString"]
            else:
                raise AuthenticationError(
                    f"Secret '{secret_path}' is binary, expected string. "
                    "Use SecretString for authentication tokens."
                )

            # Cache the value
            self._cache[key] = value
            logger.debug("secrets_cached", extra={"key": key})
            return value

        except AuthenticationError:
            # Re-raise our own errors directly
            raise
        except Exception as e:  # BROAD-CATCH: boundary -- wraps diverse boto3 errors into AuthenticationError
            # Handle boto3 exceptions
            error_response: dict[str, Any] | None = getattr(e, "response", None)
            error_code = ""
            if error_response is not None:
                error_dict: dict[str, Any] = error_response.get("Error", {})
                error_code = error_dict.get("Code", "")

            if error_code == "ResourceNotFoundException":
                raise AuthenticationError(
                    f"Secret '{secret_path}' not found in Secrets Manager. "
                    f"Ensure the secret exists in region '{self._region}'."
                ) from e
            elif error_code == "AccessDeniedException":
                raise AuthenticationError(
                    f"Access denied to secret '{secret_path}'. "
                    "Check IAM permissions for secretsmanager:GetSecretValue."
                ) from e
            elif error_code in ("DecryptionFailure", "InvalidRequestException"):
                raise AuthenticationError(
                    f"Failed to decrypt secret '{secret_path}'. "
                    "Check KMS key permissions."
                ) from e
            else:
                raise AuthenticationError(
                    f"Failed to retrieve secret '{secret_path}': {e}"
                ) from e

    def clear_cache(self) -> None:
        """Clear the in-memory secret cache.

        Call this method after rotating secrets to force re-fetch from
        Secrets Manager on next access.
        """
        self._cache.clear()
        logger.debug("secrets_cache_cleared")

    @property
    def service_name(self) -> str:
        """Get the configured service name."""
        return self._service_name

    @property
    def region(self) -> str:
        """Get the configured AWS region."""
        return self._region
