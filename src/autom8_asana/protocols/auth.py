"""Authentication provider protocol."""

from typing import Protocol


class AuthProvider(Protocol):
    """Protocol for authentication/secret retrieval.

    Implementations must provide a get_secret method that retrieves
    authentication tokens by key name.

    Example keys:
        - "ASANA_PAT": Personal Access Token
        - "ASANA_CLIENT_ID": OAuth client ID
        - "ASANA_CLIENT_SECRET": OAuth client secret
    """

    def get_secret(self, key: str) -> str:
        """Retrieve a secret value by key.

        Args:
            key: Secret identifier (e.g., "ASANA_PAT")

        Returns:
            Secret value as string

        Raises:
            AuthenticationError: If secret not found or invalid
        """
        ...
