"""Machine-operator token mint client (GAP-1 PR-A, SigV4 front-end).

This is the asana-side half of the C-6 ``sts:GetCallerIdentity`` mint. It proves
the Lambda's AWS identity to the auth service WITHOUT any secret at rest (CG-6):
the export's ambient IAM execution-role credentials
(``autom8-asana-insights-export-lambda-role``; AWS-managed, AWS-rotated) SigV4-sign
an ``sts:GetCallerIdentity`` request. The signed COMPONENTS (not a live STS call)
are forwarded as a JSON body to auth's ``POST /operator/token``, which re-plays them
to the host-pinned STS endpoint, reads back the attested caller ARN, authorizes it
against a single-agency allowlist, and mints a short-TTL, data-plane-aud, verb-scoped
``OperatorClaims`` Bearer token.

Contract facts (auth ``services/operator_identity.py`` @ origin/main 3df3298a):
  - the signed body MUST equal ``Action=GetCallerIdentity&Version=2011-06-15``
    (any other action -> auth ``disallowed_sts_action`` -> 403);
  - the signed ``Host`` header MUST equal the pinned STS host ``sts.amazonaws.com``
    (``_assert_host_pin``); a regional host -> auth ``host_pin_mismatch`` -> 403;
  - the signed ``X-Amz-Date`` MUST be within ``OPERATOR_STS_MAX_SKEW_SECONDS`` (60s)
    of now (``_enforce_freshness``); a stale date -> auth ``stale_x_amz_date`` -> 403;
    therefore SIGN IMMEDIATELY BEFORE POST;
  - INERT at merge: an empty ``OPERATOR_ARN_ALLOWLIST`` makes auth 403 EVERY mint
    (``arn_not_allowlisted``) -- the natural deploy-INERT gate, no asana flag needed.

No ``autom8y-auth`` SDK floor on asana: the export SENDS a token string and never
deserializes ``OperatorClaims`` (the data plane does, at the REC-3 recognizer). The
signer is botocore ``SigV4Auth`` -- already in-image via the runtime ``boto3`` dep
(``pyproject.toml`` ``[project.dependencies]``); a hand-rolled signer is rejected
(needless defect surface). The mint POST itself uses ``Autom8yHttpClient`` (a plain
JSON post; the SigV4 signing is purely local, so no verbatim-header-forward concern
that would force raw httpx).

This module is NOT part of the public API.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any, Protocol

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from autom8_asana.errors import OperatorMintRefusedError

if TYPE_CHECKING:
    from botocore.credentials import ReadOnlyCredentials

    from autom8_asana.protocols.log import LogProvider

__all__ = [
    "OperatorMintClient",
    "OperatorTokenProvider",
    "default_credentials_provider",
    "sign_get_caller_identity",
    "GET_CALLER_IDENTITY_BODY",
    "STS_ENDPOINT",
    "STS_HOST",
    "STS_SIGV4_REGION",
]

# The ONLY STS action the auth front-end will replay. MUST be byte-identical to
# auth ``operator_identity._GET_CALLER_IDENTITY_BODY``; one mutated byte -> 403.
GET_CALLER_IDENTITY_BODY = "Action=GetCallerIdentity&Version=2011-06-15"

# The pinned (global) STS endpoint + host. MUST match auth ``OPERATOR_STS_ENDPOINT``
# ("https://sts.amazonaws.com"); we sign for this host so the auth host-pin admits
# the request and (on replay) STS validates the signature against the same host.
STS_ENDPOINT = "https://sts.amazonaws.com/"
STS_HOST = "sts.amazonaws.com"

# SigV4 credential-scope region for the GLOBAL STS endpoint. The global endpoint
# accepts a us-east-1 scoped signature (confirmed in the H-A round-trip; UV-P).
STS_SIGV4_REGION = "us-east-1"

# Fallback TTL if the mint response omits ``expires_in`` (auth default is 300s).
_DEFAULT_TTL_SECONDS = 300

# Re-mint this many seconds BEFORE the token's nominal expiry so a long-running
# batch never presents an expired Bearer mid-run.
_DEFAULT_EXPIRY_SAFETY_SECONDS = 30


class CredentialsProvider(Protocol):
    """Returns the ambient AWS credentials to SigV4-sign with, or None."""

    def __call__(self) -> ReadOnlyCredentials | None: ...


class _HttpClientLike(Protocol):
    """Minimal async POST surface (satisfied by ``Autom8yHttpClient``)."""

    async def post(self, url: str, *, json: Any = ..., **kwargs: Any) -> Any: ...


def default_credentials_provider() -> ReadOnlyCredentials | None:
    """Resolve the Lambda's ambient IAM execution-role credentials.

    Returns frozen (read-only) credentials from the default boto3 session, or
    None when no credential chain is available (e.g. local dev with no role) --
    the caller maps None to a graceful ``OperatorMintRefusedError`` (no crash).
    """
    import boto3

    creds = boto3.Session().get_credentials()
    if creds is None:
        return None
    return creds.get_frozen_credentials()


def sign_get_caller_identity(
    credentials: ReadOnlyCredentials,
    *,
    region: str = STS_SIGV4_REGION,
    sts_endpoint: str = STS_ENDPOINT,
    sts_host: str = STS_HOST,
) -> dict[str, str]:
    """SigV4-sign an ``sts:GetCallerIdentity`` request; return the signed headers.

    The ``Host`` header is set EXPLICITLY before signing (so it is part of
    SignedHeaders AND present in the returned dict) -- this is what lets auth's
    host-pin defense-in-depth assert against it and lets the host-pin canary
    (RT-1/AT-MINT-2) mutate it. botocore otherwise computes ``host`` from the URL
    for the signature but does not emit it as a literal header.

    Returns:
        The signed header dict (Authorization + X-Amz-Date + Host + any
        X-Amz-Security-Token for session credentials) to forward to auth verbatim.
    """
    request = AWSRequest(
        method="POST",
        url=sts_endpoint,
        data=GET_CALLER_IDENTITY_BODY,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": sts_host,
        },
    )
    SigV4Auth(credentials, "sts", region).add_auth(request)
    return dict(request.headers)


class OperatorMintClient:
    """Mints a machine-operator Bearer token via auth's SigV4 front-end.

    One ``mint()`` performs the full local-sign -> forward -> parse round-trip.
    Token REUSE across a batch (and re-mint on near-expiry / 401) is the
    :class:`OperatorTokenProvider`'s job, not this client's.
    """

    def __init__(
        self,
        *,
        token_url: str | None,
        http_client: _HttpClientLike,
        region: str = STS_SIGV4_REGION,
        sts_endpoint: str = STS_ENDPOINT,
        sts_host: str = STS_HOST,
        credentials_provider: CredentialsProvider = default_credentials_provider,
        default_ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        logger: LogProvider | None = None,
    ) -> None:
        self._token_url = token_url
        self._http_client = http_client
        self._region = region
        self._sts_endpoint = sts_endpoint
        self._sts_host = sts_host
        self._credentials_provider = credentials_provider
        self._default_ttl = default_ttl_seconds
        self._log = logger

    async def mint(self) -> tuple[str, int]:
        """Sign, forward, and parse a single operator token mint.

        Returns:
            Tuple ``(access_token, expires_in_seconds)``.

        Raises:
            OperatorMintRefusedError: no mint URL configured, no ambient AWS
                credentials, a 403/429/non-200 from auth (incl. the INERT
                empty-allowlist 403), or a malformed mint response. ALWAYS fails
                closed -- never falls back to the SA fleet-read.
        """
        if not self._token_url:
            raise OperatorMintRefusedError(
                "operator token mint URL is not configured (AUTOM8Y_AUTH_OPERATOR_TOKEN_URL unset)",
                reason="no_token_url",
            )

        credentials = self._credentials_provider()
        if credentials is None:
            raise OperatorMintRefusedError(
                "no ambient AWS credentials available to sign the operator mint",
                reason="no_credentials",
            )

        # Sign IMMEDIATELY before the POST (X-Amz-Date freshness window is 60s).
        signed_headers = sign_get_caller_identity(
            credentials,
            region=self._region,
            sts_endpoint=self._sts_endpoint,
            sts_host=self._sts_host,
        )
        payload = {
            "iam_request_method": "POST",
            "iam_request_body": GET_CALLER_IDENTITY_BODY,
            "iam_request_headers": signed_headers,
            "nonce": uuid.uuid4().hex,
        }

        response = await self._http_client.post(
            self._token_url,
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        status_code = response.status_code

        if status_code != 200:
            # 403 = the INERT gate / identity refusal (uniform; reason hidden by
            # design); 429 = mint rate-limited; anything else = unexpected. ALL
            # fail closed with a typed error -- NEVER an SA fleet-read fallback.
            reason = (
                "mint_refused_403"
                if status_code == 403
                else "mint_rate_limited_429"
                if status_code == 429
                else f"mint_unexpected_{status_code}"
            )
            raise OperatorMintRefusedError(
                f"operator token mint refused (HTTP {status_code})",
                reason=reason,
                status_code=status_code,
            )

        try:
            body = response.json()
            data = body.get("data") or {}
            access_token = data.get("access_token")
            expires_in = int(data.get("expires_in", self._default_ttl))
        except (ValueError, AttributeError, TypeError) as exc:
            raise OperatorMintRefusedError(
                "operator token mint returned a malformed response",
                reason="mint_malformed_response",
            ) from exc

        if not access_token:
            raise OperatorMintRefusedError(
                "operator token mint response carried no access_token",
                reason="mint_malformed_response",
            )

        return access_token, expires_in


class OperatorTokenProvider:
    """Caches one minted operator token per run and re-mints on near-expiry.

    Per TDD §5.4: mint ONCE per run, hold in process memory (never disk / Secrets
    Manager / log; dies with the Lambda invocation), reuse across the batch, and
    re-mint on near-expiry or a forced refresh (the consume path forces one
    refresh on a 401). Concurrency-safe so concurrent batch calls share one mint.
    """

    def __init__(
        self,
        mint_client: OperatorMintClient,
        *,
        expiry_safety_seconds: int = _DEFAULT_EXPIRY_SAFETY_SECONDS,
        logger: LogProvider | None = None,
    ) -> None:
        self._mint_client = mint_client
        self._expiry_safety = expiry_safety_seconds
        self._log = logger
        self._access_token: str | None = None
        self._expires_at_monotonic: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self, *, force_refresh: bool = False) -> str:
        """Return a cached fresh token, minting (once) only when needed.

        Raises:
            OperatorMintRefusedError: propagated from the underlying mint.
        """
        async with self._lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self._access_token is not None
                and self._expires_at_monotonic - self._expiry_safety > now
            ):
                return self._access_token

            access_token, expires_in = await self._mint_client.mint()
            self._access_token = access_token
            self._expires_at_monotonic = time.monotonic() + expires_in
            if self._log:
                self._log.debug(
                    "operator_token_minted",
                    extra={"expires_in": expires_in, "force_refresh": force_refresh},
                )
            return access_token
