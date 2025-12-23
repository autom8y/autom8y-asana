"""Deprecated: Use autom8y_auth.CredentialVaultAuthProvider instead.

This module is deprecated and will be removed in a future release.
Import CredentialVaultAuthProvider directly from the autom8y-auth SDK:

    from autom8y_auth import CredentialVaultAuthProvider

    provider = CredentialVaultAuthProvider(
        credential_client=cred_client,
        business_id="...",
        provider="asana",  # Explicit provider parameter
    )
"""

from __future__ import annotations

import asyncio
import warnings
from typing import TYPE_CHECKING

from autom8_asana.exceptions import AuthenticationError

if TYPE_CHECKING:
    from autom8y_auth import CredentialClient

# Emit deprecation warning on import
warnings.warn(
    "autom8_asana._defaults.vault_auth is deprecated. "
    "Use 'from autom8y_auth import CredentialVaultAuthProvider' instead. "
    "This module will be removed in autom8_asana 0.6.0.",
    DeprecationWarning,
    stacklevel=2,
)


class CredentialVaultAuthProvider:
    """Deprecated: Use autom8y_auth.CredentialVaultAuthProvider.

    This class is a thin wrapper for backward compatibility.
    It sets provider="asana" automatically and maintains the legacy
    interface (including _cached_token and clear_cache).
    """

    def __init__(
        self,
        credential_client: CredentialClient,
        business_id: str,
        user_id: str | None = None,
        identity_type: str = "bot",
    ) -> None:
        """Initialize with provider="asana" for backward compatibility."""
        if identity_type == "user" and user_id is None:
            raise ValueError("user_id is required when identity_type is 'user'")

        self._client = credential_client
        self._business_id = business_id
        self._user_id = user_id
        self._identity_type = identity_type
        self._cached_token: str | None = None

    @property
    def business_id(self) -> str:
        """Get the business ID."""
        return self._business_id

    @property
    def user_id(self) -> str | None:
        """Get the user ID."""
        return self._user_id

    @property
    def identity_type(self) -> str:
        """Get the identity type."""
        return self._identity_type

    def get_secret(self, key: str) -> str:
        """Retrieve Asana access token from vault (sync).

        This method blocks while fetching the credential from the vault.
        For async contexts, use get_secret_async() instead.

        Args:
            key: Secret key (typically "ASANA_PAT"). The key is ignored
                since the vault knows which credential to fetch based
                on provider="asana".

        Returns:
            The Asana access token.

        Raises:
            AuthenticationError: If credential cannot be retrieved.
        """
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.get_secret_async(key))
            finally:
                loop.close()
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(
                f"Failed to retrieve Asana credential from vault: {e}"
            ) from e

    async def get_secret_async(self, key: str) -> str:
        """Retrieve Asana access token from vault (async).

        Args:
            key: Secret key (typically "ASANA_PAT"). The key is ignored
                since the vault knows which credential to fetch based
                on provider="asana".

        Returns:
            The Asana access token.

        Raises:
            AuthenticationError: If credential cannot be retrieved.
        """
        try:
            credential = await self._client.get(
                user_id=self._user_id,
                business_id=self._business_id,
                provider="asana",
                identity_type=self._identity_type,
            )
            # Cache the token for potential reuse
            self._cached_token = credential.access_token
            return credential.access_token

        except Exception as e:
            # Re-raise as AuthenticationError to match legacy protocol
            raise AuthenticationError(
                f"Failed to retrieve Asana credential from vault: {e}"
            ) from e

    def clear_cache(self) -> None:
        """Clear the cached token.

        Call this if you need to force a fresh fetch from the vault.
        """
        self._cached_token = None
