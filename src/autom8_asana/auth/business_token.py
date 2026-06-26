"""Per-business token minter for the grain-bridge leads consumer.

Builds a thin client over ``POST /tokens/exchange-business`` (auth S1
AUTH-BRIDGE v2, ``tokens.py:524-530`` @ 1ad88e87). This is a hand-built
exchange client -- NOT the pinned ``autom8y-auth`` TokenManager -- because that
SDK's exchange sends an EMPTY body (``token_manager.py:355-368`` @ 1ad88e87),
which is the fleet/exempt path this initiative exists to retire (ADR
grain-bridge D3).

Security (HANDOFF SC-BUILD-1 / SC-BUILD-4):

- ``requested_scopes`` is the FROZEN constant ``["data:read"]`` on EVERY mint;
  never ``read:pii`` (the meta-lead-service adjacency unmasks PII on the leads
  surface).
- Credentials are process-env only: ``SERVICE_CLIENT_ID`` +
  ``resolve_secret_from_env("SERVICE_CLIENT_SECRET")`` (mirrors
  ``service_token.py:38-78``). The client_secret is never persisted to disk and
  never logged; the minter authenticates as the delegator and exchanges for the
  single-tenant per-business token. No re-mint, no fleet fallback.

The minter is the SINGLE site that constructs the exchange request, so the
scope pin (SC-BUILD-1) and the credential discipline (SC-BUILD-4) are enforced
in one place and asserted by the two-sided discriminating canary.
"""

from __future__ import annotations

import base64
import contextlib
import os
from typing import TYPE_CHECKING, ClassVar

from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_http import (
    Autom8yHttpClient,
    HttpClientConfig,
    HTTPError,
    TimeoutException,
)
from autom8y_log import get_logger

from autom8_asana.errors import AsanaError

if TYPE_CHECKING:
    from autom8y_http import Response

logger = get_logger(__name__)


# --- Typed mint-exception hierarchy (status -> exception; see consumer §4) ---


class MintError(AsanaError):
    """Base class for all exchange-business mint failures."""


class MintResolutionMiss(MintError):
    """404 AUTH-TEB-005 -- ebid unresolved OR out-of-authorized_organizations.

    This is the oracle-seal RED arm at consumer altitude: no per-business token
    is minted and no leads read occurs (DATA-VAL-003 non-regression). Maps to
    ``SkipClass.RESOLUTION_MISS`` (sub_reason ``server_404``). NEVER a fleet
    fallback.
    """


class MintRateLimited(MintError):
    """429 AUTH-TEB-006 -- per-IP or per-credential rate limit (transient).

    The consumer is credential-agnostic: either SA rate-limit bucket lands here
    identically. Maps to ``SkipClass.MINT_UNAVAILABLE`` (sub_reason
    ``rate_limited``).
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class MintCredentialError(MintError):
    """401 AUTH-TEB-001 -- bad delegator credentials.

    FATAL delegator-level misconfiguration: it manifests identically for EVERY
    business, so it is raised-and-halted by the consumer (honest propagation,
    mirroring ``service_token.py``) rather than masquerading as N per-business
    ``resolution_miss`` skips.
    """


class MintScopeError(MintError):
    """403 AUTH-TEB-003 -- delegator lacks the requested grant (data:read).

    FATAL delegator-level misconfiguration (see ``MintCredentialError``).
    """


class MintCollision(MintError):
    """409 DATA-CONFLICT-002 -- office_phone collision. Fail-closed.

    Maps to ``SkipClass.COLLISION_CONFLICT``. Defensively handled (not
    primary-path-reachable in the merged contract; see consumer §4 / ADR D5).
    """


class MintUnavailable(MintError):
    """5xx / network / timeout / malformed-200 -- transient upstream failure.

    Maps to ``SkipClass.MINT_UNAVAILABLE`` (sub_reason ``upstream_5xx``). NEVER
    a fleet fallback; never conflated with the permanent 404.
    """


class BusinessTokenMinter:
    """Mints a single-tenant per-business token via exchange-business.

    Args:
        client_id: ServiceAccount client_id. Defaults to ``SERVICE_CLIENT_ID``.
        client_secret: ServiceAccount client_secret. Defaults to
            ``resolve_secret_from_env("SERVICE_CLIENT_SECRET")`` -- resolves the
            ``_ARN``-suffixed key on Lambda and the bare name on ECS / local.
        auth_url: Auth service base URL for the exchange.
        http_client: Optional injected HTTP client (test seam). When ``None`` a
            platform ``Autom8yHttpClient`` is created lazily.
    """

    #: SC-BUILD-1: FROZEN scope pin. Never read:pii.
    SCOPE_DATA_READ: ClassVar[list[str]] = ["data:read"]

    #: exchange-business path (auth tokens router).
    EXCHANGE_PATH: ClassVar[str] = "/tokens/exchange-business"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        auth_url: str = "https://auth.api.autom8y.io",
        *,
        http_client: Autom8yHttpClient | None = None,
    ) -> None:
        cid = client_id or os.environ.get("SERVICE_CLIENT_ID", "")
        # SC-BUILD-4: read SERVICE_CLIENT_SECRET via resolve_secret_from_env so
        # the minter is delivery-convention-agnostic (ECS bare name vs Lambda
        # `_ARN`). RuntimeError (extension HTTP failure) is deliberately NOT
        # caught -- it must propagate honestly rather than degrade to a silent
        # no-credential path. Only the absent-secret ValueError is narrowed.
        csecret = client_secret
        if not csecret:
            try:
                csecret = resolve_secret_from_env("SERVICE_CLIENT_SECRET")
            except ValueError:
                csecret = ""
        if not cid or not csecret:
            raise ValueError(
                "SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET are required for "
                "exchange-business token minting. Set them in the environment "
                "or pass client_id and client_secret explicitly."
            )

        self._client_id = cid
        # Basic-auth credential, computed once. The secret is held only inside
        # this encoded value -- never logged, never written to disk.
        self._basic_auth = base64.b64encode(f"{cid}:{csecret}".encode()).decode("ascii")
        self._auth_url = auth_url
        self._http_client = http_client

    async def _get_client(self) -> Autom8yHttpClient:
        if self._http_client is None:
            config = HttpClientConfig(
                base_url=self._auth_url,
                enable_retry=True,
                enable_circuit_breaker=False,
            )
            self._http_client = Autom8yHttpClient(config=config, logger=logger)
        return self._http_client

    async def mint(self, external_business_id: str) -> str:
        """Exchange the ebid for a single-tenant per-business access token.

        Args:
            external_business_id: the ebid (``normalize_chiropractor_guid``
                output) consumed as a request INPUT only -- the minter folds it
                into no token payload it constructs (c1b; it constructs none).

        Returns:
            The per-business access token (single-tenant JWT).

        Raises:
            MintResolutionMiss: 404 AUTH-TEB-005 (the RED arm).
            MintRateLimited: 429 AUTH-TEB-006 (transient).
            MintCredentialError: 401 AUTH-TEB-001 (FATAL delegator misconfig).
            MintScopeError: 403 AUTH-TEB-003 (FATAL delegator misconfig).
            MintCollision: 409 DATA-CONFLICT-002 (defensive, fail-closed).
            MintUnavailable: 5xx / network / timeout / malformed-200.
        """
        client = await self._get_client()
        try:
            response = await client.post(
                self.EXCHANGE_PATH,
                json={
                    "external_business_id": external_business_id,
                    # SC-BUILD-1: new list per call so the frozen constant
                    # cannot be mutated by a caller holding a reference.
                    "requested_scopes": list(self.SCOPE_DATA_READ),
                },
                headers={
                    "Authorization": f"Basic {self._basic_auth}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        except (HTTPError, TimeoutException) as exc:
            raise MintUnavailable(
                f"exchange-business transport failure: {type(exc).__name__}"
            ) from exc

        return self._handle_response(response)

    def _handle_response(self, response: Response) -> str:
        status = response.status_code
        if 200 <= status < 300:
            return self._extract_token(response)
        if status == 401:
            raise MintCredentialError(
                "exchange-business 401 AUTH-TEB-001: delegator credentials "
                "rejected (FATAL misconfiguration)",
                status_code=401,
            )
        if status == 403:
            raise MintScopeError(
                "exchange-business 403 AUTH-TEB-003: delegator lacks the "
                "requested grant (FATAL misconfiguration)",
                status_code=403,
            )
        if status == 404:
            # Uniform 404 -- miss == out-of-set, byte-identical. The minter does
            # NOT log the (absent) resolved business_id: there is none.
            raise MintResolutionMiss(
                "exchange-business 404 AUTH-TEB-005: ebid unresolved or "
                "out-of-authorized_organizations",
                status_code=404,
            )
        if status == 409:
            raise MintCollision(
                "exchange-business 409 DATA-CONFLICT-002: office_phone collision",
                status_code=409,
            )
        if status == 429:
            raise MintRateLimited(
                "exchange-business 429 AUTH-TEB-006: rate limited",
                retry_after=_parse_retry_after(response),
                status_code=429,
            )
        if status >= 500:
            raise MintUnavailable(
                f"exchange-business {status}: upstream server error",
                status_code=status,
            )
        # Unexpected 4xx: fail closed as transient-unavailable (never silent).
        raise MintUnavailable(
            f"exchange-business unexpected status {status}",
            status_code=status,
        )

    def _extract_token(self, response: Response) -> str:
        try:
            body = response.json()
        except ValueError as exc:
            raise MintUnavailable("exchange-business 200 body was not valid JSON") from exc
        token = body.get("access_token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            raise MintUnavailable("exchange-business 200 lacked an access_token")
        return token

    async def close(self) -> None:
        """Release the HTTP client (idempotent)."""
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None


def _parse_retry_after(response: Response) -> int | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    with contextlib.suppress(ValueError):
        return int(raw)
    return None
