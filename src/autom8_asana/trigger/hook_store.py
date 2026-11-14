"""The ONE Secrets Manager writer for ``autom8y/asana/webhook-hook/*`` (D6).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.6, sections 2 and 2a;
custody: RULING-project-bootstrapping-asana-webhook-hook-custody-20261110 sections 2-5
and its section 8 amendment (warden-bench L-1).

Nothing else in this package touches the prefix. The value Asana sends in the handshake
is written ONCE, by ``CreateSecret`` carrying the value. There is no Put and no Update
path: a second write for a handle is refused here (``ResourceExistsException``) and by
IAM (the task role holds no ``PutSecretValue`` or ``UpdateSecretVersionStage``).

Gates, in order, before any AWS call (the auth precedent, sa_pointer_store.py):

1. The marker ``ASANA_HOOK_ENVIRONMENT``, read once at construction. Only exactly
   ``production`` permits a call. ``test``/``local`` construct a store that refuses every
   call (PM-5). Any other value refuses at construction (PM-3).
2. The ECS task-role credential check, before every call. It is env-only (no network):
   the container credential source and the task metadata variable must be present, and no
   credential source that outranks the container provider may be set. The default client
   is also pinned to the container provider alone, so a stray credential file can never
   become the writer.

Every refusal raises a typed error and makes no AWS call. The value is never logged and
never appears in an exception message.

Reads (A3, the receiver's key cache, TDD section 4 steps 5 and 6) pass the same gates as
writes: :meth:`HookStore.read_hook_value` reads only on exactly ``production`` with the
task-role check passing. Any read failure raises :class:`HookStoreReadFailed`, which the
receiver answers with 500, never 401 and never a fallback key (A C-8).

The handle is never logged (auth-bench A3-1). Log lines carry :func:`handle_fingerprint`,
a short one-way digest, so lines about one hook can be joined without a log reader
learning the handle.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import TYPE_CHECKING, Any, Final

from autom8y_log import get_logger

from autom8_asana.trigger.hook_environment import (
    HookEnvironment,
    read_hook_environment,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

STORE_PREFIX: Final[str] = "autom8y/asana/webhook-hook/"
HANDLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{32}$")
RECOVERY_WINDOW_DAYS: Final[int] = 7

# auth-bench A3-1: a short one-way digest of the handle for log lines. 12 hex characters
# (48 bits) of a domain-separated SHA-256; the handle itself carries 128 random bits.
_FINGERPRINT_DOMAIN: Final[bytes] = b"autom8y-asana-hook-handle:"
_FINGERPRINT_CHARS: Final[int] = 12

# Tags the IAM CreateSecret condition requires (custody ruling section 4).
TAG_SERVICE: Final[str] = "asana"
TAG_PURPOSE: Final[str] = "asana-webhook-hook"

_TASK_ROLE_CREDENTIALS_ENV: Final[str] = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
_ECS_METADATA_ENV: Final[str] = "ECS_CONTAINER_METADATA_URI_V4"
# Credential sources that outrank the container provider in boto3's default chain.
_OUTRANKING_CREDENTIAL_ENVS: Final[tuple[str, ...]] = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_ROLE_ARN",
)

_CONNECT_TIMEOUT_S: Final[float] = 2.0
_READ_TIMEOUT_S: Final[float] = 3.0
_TOTAL_MAX_ATTEMPTS: Final[int] = 2


class HookStoreError(RuntimeError):
    """Base for every hook_store failure."""


class HookStoreRefused(HookStoreError):
    """A gate refused the call before any AWS call was made."""


class HookStoreWriteFailed(HookStoreError):
    """Secrets Manager returned an error, or the call failed in transport."""

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        self.error_code = error_code
        super().__init__(message)


class HookValueAlreadyStored(HookStoreWriteFailed):
    """A value already exists for this handle. The value is write-once."""


class HookStoreReadFailed(HookStoreError):
    """The read failed, the entry is missing, or it is malformed. Never carries the value."""

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        self.error_code = error_code
        super().__init__(message)


def handle_fingerprint(handle: str) -> str:
    """A short one-way digest of ``handle`` for log lines (auth-bench A3-1).

    The handle is never logged. The fingerprint lets an operator join the lines about one
    hook, and it cannot be turned back into the handle.
    """
    digest = hashlib.sha256(_FINGERPRINT_DOMAIN + str(handle).encode("utf-8", "replace"))
    return digest.hexdigest()[:_FINGERPRINT_CHARS]


def hook_secret_name(handle: str) -> str:
    """``autom8y/asana/webhook-hook/{handle}``, after the handle's shape is checked."""
    if not isinstance(handle, str) or not HANDLE_PATTERN.fullmatch(handle):
        raise HookStoreRefused("handle is not 32 lowercase hex characters")
    return f"{STORE_PREFIX}{handle}"


def task_role_credential_refusal(environ: Mapping[str, str] | None = None) -> str | None:
    """Return why the credentials would NOT be the ECS task role, else ``None``.

    Names variables only; never echoes a value.
    """
    env = os.environ if environ is None else environ
    for name in (_TASK_ROLE_CREDENTIALS_ENV, _ECS_METADATA_ENV):
        if not env.get(name):
            return f"{name} unset (not running as an ECS task with a task role)"
    outranking = [name for name in _OUTRANKING_CREDENTIAL_ENVS if env.get(name)]
    if outranking:
        return f"{', '.join(outranking)} set (outranks the ECS task role credential source)"
    return None


def _task_role_secrets_client() -> Any:
    """A Secrets Manager client whose ONLY credential source is the ECS task role."""
    import boto3
    import botocore.session
    from botocore.config import Config
    from botocore.credentials import ContainerProvider, CredentialResolver

    core = botocore.session.get_session()
    core.register_component("credential_provider", CredentialResolver([ContainerProvider()]))
    session = boto3.Session(botocore_session=core)
    return session.client(
        "secretsmanager",
        config=Config(
            connect_timeout=_CONNECT_TIMEOUT_S,
            read_timeout=_READ_TIMEOUT_S,
            retries={"total_max_attempts": _TOTAL_MAX_ATTEMPTS, "mode": "standard"},
        ),
    )


def _error_code(exc: BaseException) -> str | None:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code")
        return code if isinstance(code, str) else None
    return None


class HookStore:
    """The single writer for the webhook-hook prefix.

    ``client`` may be injected (tests); the gates still apply to an injected client, so a
    refused posture never reaches it. ``environ`` defaults to the process environment.
    """

    def __init__(
        self,
        *,
        client: Any | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._environ: Mapping[str, str] = os.environ if environ is None else environ
        # Read ONCE. Absent, empty or unrecognized refuses here, loudly (PM-3).
        self._marker: HookEnvironment = read_hook_environment(
            consumer="hook_store", environ=self._environ
        )
        self._client = client

    @property
    def marker(self) -> HookEnvironment:
        return self._marker

    def _permit(self, operation: str) -> Any:
        """The single choke point. Returns the client, or raises before any call."""
        if self._marker is not HookEnvironment.PRODUCTION:
            logger.error(
                "hook_store_refused",
                extra={"operation": operation, "reason": "marker_not_production"},
            )
            raise HookStoreRefused(
                f"hook_store {operation} refused: ASANA_HOOK_ENVIRONMENT is "
                f"{self._marker.value!r}, and the store writes only on 'production'"
            )
        reason = task_role_credential_refusal(self._environ)
        if reason is not None:
            logger.error(
                "hook_store_refused",
                extra={"operation": operation, "reason": "task_role_check_failed"},
            )
            raise HookStoreRefused(f"hook_store {operation} refused: {reason}")
        if self._client is None:
            self._client = _task_role_secrets_client()
        return self._client

    def create_hook_value(
        self,
        *,
        handle: str,
        hook_value: str,
        resource_gid: str,
        registered_at: str,
    ) -> None:
        """Write the handshake value for ``handle``, exactly once (CreateSecret)."""
        name = hook_secret_name(handle)
        client = self._permit("create")
        body = json.dumps(
            {"hook_value": hook_value, "resource_gid": resource_gid, "registered_at": registered_at}
        )
        try:
            client.create_secret(
                Name=name,
                SecretString=body,
                Tags=[
                    {"Key": "service", "Value": TAG_SERVICE},
                    {"Key": "purpose", "Value": TAG_PURPOSE},
                    {"Key": "handle", "Value": handle},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- every SDK or transport failure becomes a typed
            # store failure; the message carries the code only, never the value.
            code = _error_code(exc)
            logger.error(
                "hook_store_create_failed",
                extra={
                    "handle_fp": handle_fingerprint(handle),
                    "error_code": code,
                    "error_type": type(exc).__name__,
                },
            )
            if code == "ResourceExistsException":
                raise HookValueAlreadyStored(
                    "a value already exists for this handle (write-once)", error_code=code
                ) from None
            raise HookStoreWriteFailed(
                f"CreateSecret failed ({code or type(exc).__name__})", error_code=code
            ) from None
        logger.info("hook_store_created", extra={"handle_fp": handle_fingerprint(handle)})

    def tag_webhook_gid(self, *, handle: str, webhook_gid: str) -> None:
        """Add the ``webhook_gid`` tag after create-webhook returns (ruling section 2)."""
        name = hook_secret_name(handle)
        client = self._permit("tag")
        try:
            client.tag_resource(SecretId=name, Tags=[{"Key": "webhook_gid", "Value": webhook_gid}])
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- typed store failure, code only.
            code = _error_code(exc)
            logger.error(
                "hook_store_tag_failed",
                extra={
                    "handle_fp": handle_fingerprint(handle),
                    "error_code": code,
                    "error_type": type(exc).__name__,
                },
            )
            raise HookStoreWriteFailed(
                f"TagResource failed ({code or type(exc).__name__})", error_code=code
            ) from None

    def delete_hook_value(self, *, handle: str) -> bool:
        """Delete the entry with a 7-day recovery window.

        Returns ``False`` when no entry exists (nothing to delete), ``True`` on delete.
        Every other failure raises.
        """
        name = hook_secret_name(handle)
        client = self._permit("delete")
        try:
            client.delete_secret(SecretId=name, RecoveryWindowInDays=RECOVERY_WINDOW_DAYS)
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- not-found is a value, anything else is typed.
            code = _error_code(exc)
            if code == "ResourceNotFoundException":
                logger.info(
                    "hook_store_delete_absent", extra={"handle_fp": handle_fingerprint(handle)}
                )
                return False
            logger.error(
                "hook_store_delete_failed",
                extra={
                    "handle_fp": handle_fingerprint(handle),
                    "error_code": code,
                    "error_type": type(exc).__name__,
                },
            )
            raise HookStoreWriteFailed(
                f"DeleteSecret failed ({code or type(exc).__name__})", error_code=code
            ) from None
        logger.info("hook_store_deleted", extra={"handle_fp": handle_fingerprint(handle)})
        return True

    def read_hook_value(self, *, handle: str) -> str:
        """Read the handshake value stored for ``handle`` (the receiver's key, A3).

        The same gates as every write run first: exactly ``production`` and the task-role
        check, before any AWS call. Every SDK or transport failure, a missing entry and a
        malformed entry raise :class:`HookStoreReadFailed`. The value is never logged and
        never appears in an exception message.
        """
        name = hook_secret_name(handle)
        client = self._permit("read")
        try:
            response = client.get_secret_value(SecretId=name)
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- every SDK or transport failure is a typed read
            # failure, code only. The receiver answers it with 500, never 401 (A C-8).
            code = _error_code(exc)
            logger.error(
                "hook_store_read_failed",
                extra={
                    "handle_fp": handle_fingerprint(handle),
                    "error_code": code,
                    "error_type": type(exc).__name__,
                },
            )
            raise HookStoreReadFailed(
                f"read failed ({code or type(exc).__name__})", error_code=code
            ) from None
        value = _stored_hook_value(response)
        if value is None:
            logger.error(
                "hook_store_read_failed",
                extra={"handle_fp": handle_fingerprint(handle), "error_code": "malformed_entry"},
            )
            raise HookStoreReadFailed("the stored entry is malformed", error_code="malformed_entry")
        return value


def _stored_hook_value(response: Any) -> str | None:
    """The ``hook_value`` field of a read response, or ``None`` when it is malformed."""
    raw = response.get("SecretString") if isinstance(response, dict) else None
    if not isinstance(raw, str):
        return None
    try:
        body = json.loads(raw)
    except ValueError:
        return None
    value = body.get("hook_value") if isinstance(body, dict) else None
    return value if isinstance(value, str) and value else None
