"""Per-business AuthProvider wrapping a single minted token (anti-IDOR).

Per ADR grain-bridge D4 / HANDOFF SC-BUILD-3: one mint -> one
``PerBusinessTokenProvider`` -> one leads ``DataServiceClient`` per business.
The provider wraps exactly ONE single-tenant token and is NEVER reused across
tenants. The served tenant is the JWT's ``business_id``, which DOMINATES the
client ``office_phone`` query param on the data leads endpoint
(``data_service.py:1009`` anti-IDOR) -- the consumer must not assume its
``office_phone`` controls the served tenant.

Satisfies ``protocols.auth.AuthProvider`` structurally: ``get_secret(key)``
returns the wrapped token regardless of key (single-token provider).
"""

from __future__ import annotations


class PerBusinessTokenProvider:
    """AuthProvider that returns ONE per-business token for all keys.

    Args:
        token: the single-tenant per-business access token minted via
            ``BusinessTokenMinter.mint``.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    def get_secret(self, key: str) -> str:
        """Return the wrapped per-business token (key ignored, single token)."""
        return self._token

    def close(self) -> None:
        """No-op: the provider holds no closeable resource."""
        return None
