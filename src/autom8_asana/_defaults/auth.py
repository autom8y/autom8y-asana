"""Default authentication providers."""

from __future__ import annotations

import os

from autom8_asana.exceptions import AuthenticationError


class EnvAuthProvider:
    """Auth provider that reads from environment variables.

    This is the default for standalone SDK usage.

    Example:
        export ASANA_PAT=your_token_here

        client = AsanaClient()  # Uses EnvAuthProvider by default
    """

    def get_secret(self, key: str) -> str:
        """Get secret from environment variable.

        Args:
            key: Environment variable name

        Returns:
            Value of environment variable

        Raises:
            AuthenticationError: If variable not set or empty
        """
        value = os.environ.get(key)
        if value is None:
            raise AuthenticationError(
                f"Environment variable '{key}' not set. "
                f"Set it or provide a custom AuthProvider."
            )
        if not value.strip():
            raise AuthenticationError(
                f"Environment variable '{key}' is empty. "
                f"Provide a valid token value."
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
