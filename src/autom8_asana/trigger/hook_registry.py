"""The ONE writer of the D-1 table ``autom8y-asana-hook-registry`` (D6, registration side).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.6, section 2a (W F-8,
A C-6, W F-6b). Schema (pk / sk, both strings; a one-way door, TDD section 11):

* ``HOOK#{handle}`` / ``META``: state, resource_gid, webhook_gid, expires_at, ttl. This
  module also keeps ``handshaken_at`` on the row, set by the ``pending -> handshaken``
  move. It is an attribute, not a new item, and it is how the reconciler knows whether a
  ``create_unknown`` hook ever stored a value (OR-1).
* ``PROJECT#{gid}`` / ``ACTIVE``: handle. One active hook per project (W F-6b): the put
  requires ``attribute_not_exists`` or ``handle = :old``.
* ``LEASE#reconciler`` / ``-``: owner, until. Conditional on expiry.

The delivery, decision-key and liveness rows belong to the receiver and decision PRs.

Every state transition is a conditional write. A lost condition raises
:class:`HookRegistryConflict`; it is never folded into success. Reads for the handshake
and after verification are ``ConsistentRead=True`` (the default here). There is no Scan
anywhere: the task role holds none.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

logger = get_logger(__name__)

TABLE_ENV_VAR: Final[str] = "ASANA_HOOK_REGISTRY_TABLE"

PENDING_WINDOW_S: Final[int] = 60
PENDING_TTL_GRACE_S: Final[int] = 86_400
CLOSED_ROW_RETENTION_S: Final[int] = 30 * 86_400
LEASE_NAME: Final[str] = "reconciler"


class HookState(StrEnum):
    PENDING = "pending"
    HANDSHAKEN = "handshaken"
    ACTIVE = "active"
    CREATE_UNKNOWN = "create_unknown"
    FAILED = "failed"
    COMPROMISED = "compromised"
    REMOVED = "removed"


class HookRegistryError(RuntimeError):
    """Base for every registry failure."""


class HookRegistryConflict(HookRegistryError):
    """A conditional write lost: the row was not in the required state."""


class HookRegistryUnavailable(HookRegistryError):
    """DynamoDB returned a non-conditional error, or the table is not configured."""

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        self.error_code = error_code
        super().__init__(message)


@dataclass(frozen=True)
class HookRecord:
    handle: str
    state: HookState
    resource_gid: str
    webhook_gid: str | None
    expires_at: int
    handshaken_at: int | None


def _hook_key(handle: str) -> dict[str, dict[str, str]]:
    return {"pk": {"S": f"HOOK#{handle}"}, "sk": {"S": "META"}}


def _active_key(project_gid: str) -> dict[str, dict[str, str]]:
    return {"pk": {"S": f"PROJECT#{project_gid}"}, "sk": {"S": "ACTIVE"}}


def _lease_key(name: str) -> dict[str, dict[str, str]]:
    return {"pk": {"S": f"LEASE#{name}"}, "sk": {"S": "-"}}


def _s(value: str) -> dict[str, str]:
    return {"S": value}


def _n(value: int) -> dict[str, str]:
    return {"N": str(int(value))}


def _error_code(exc: BaseException) -> str | None:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code")
        return code if isinstance(code, str) else None
    return None


_CONFLICT_CODES: Final[frozenset[str]] = frozenset(
    {"ConditionalCheckFailedException", "TransactionCanceledException"}
)


def _state_in(states: Sequence[HookState]) -> tuple[str, dict[str, dict[str, str]]]:
    names = [f":st{i}" for i in range(len(states))]
    values = {name: _s(state.value) for name, state in zip(names, states)}
    return f"#state IN ({', '.join(names)})", values


class HookRegistry:
    """Conditional reads and writes on the D-1 table. ``client`` is a DynamoDB client."""

    def __init__(self, *, table_name: str, client: Any | None = None) -> None:
        if not table_name:
            raise HookRegistryUnavailable("the hook registry table name is empty")
        self._table = table_name
        if client is None:
            import boto3

            client = boto3.client("dynamodb")
        self._client = client

    @classmethod
    def from_env(
        cls, *, environ: Mapping[str, str] | None = None, client: Any | None = None
    ) -> HookRegistry:
        env = os.environ if environ is None else environ
        table = env.get(TABLE_ENV_VAR, "")
        if not table:
            logger.error("hook_registry_unconfigured", extra={"variable": TABLE_ENV_VAR})
            raise HookRegistryUnavailable(f"{TABLE_ENV_VAR} is absent or empty")
        return cls(table_name=table, client=client)

    # -- low-level ------------------------------------------------------------

    def _call(self, operation: str, **kwargs: Any) -> Any:
        try:
            return getattr(self._client, operation)(**kwargs)
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- a lost condition is a conflict, every other SDK or
            # transport failure is a typed unavailability; neither is ever swallowed.
            code = _error_code(exc)
            if code in _CONFLICT_CODES:
                raise HookRegistryConflict(f"{operation}: condition not met ({code})") from None
            logger.error(
                "hook_registry_call_failed",
                extra={
                    "operation": operation,
                    "error_code": code,
                    "error_type": type(exc).__name__,
                },
            )
            raise HookRegistryUnavailable(
                f"{operation} failed ({code or type(exc).__name__})", error_code=code
            ) from None

    def _update_hook(
        self,
        handle: str,
        *,
        set_values: Mapping[str, dict[str, str]],
        remove: Sequence[str] = (),
        condition: str,
        condition_values: Mapping[str, dict[str, str]] | None = None,
    ) -> None:
        # DynamoDB rejects an unused attribute-name placeholder, so #state is declared
        # only when the condition uses it.
        names = {"#state": "state"} if "#state" in condition else {}
        values: dict[str, dict[str, str]] = {}
        sets: list[str] = []
        for i, (attr, value) in enumerate(set_values.items()):
            names[f"#a{i}"] = attr
            values[f":v{i}"] = value
            sets.append(f"#a{i} = :v{i}")
        removes: list[str] = []
        for j, attr in enumerate(remove):
            names[f"#r{j}"] = attr
            removes.append(f"#r{j}")
        expression = "SET " + ", ".join(sets)
        if removes:
            expression += " REMOVE " + ", ".join(removes)
        values.update(condition_values or {})
        self._call(
            "update_item",
            TableName=self._table,
            Key=_hook_key(handle),
            UpdateExpression=expression,
            ConditionExpression=condition,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

    # -- HOOK rows ----------------------------------------------------------------

    def put_pending(self, *, handle: str, resource_gid: str, now: int) -> HookRecord:
        """Create the ``pending`` row, expiring ``PENDING_WINDOW_S`` from ``now``."""
        expires_at = now + PENDING_WINDOW_S
        self._call(
            "put_item",
            TableName=self._table,
            Item={
                **_hook_key(handle),
                "state": _s(HookState.PENDING.value),
                "resource_gid": _s(resource_gid),
                "expires_at": _n(expires_at),
                "created_at": _n(now),
                "ttl": _n(expires_at + PENDING_TTL_GRACE_S),
            },
            ConditionExpression="attribute_not_exists(pk)",
        )
        return HookRecord(
            handle=handle,
            state=HookState.PENDING,
            resource_gid=resource_gid,
            webhook_gid=None,
            expires_at=expires_at,
            handshaken_at=None,
        )

    def get_hook(self, handle: str, *, consistent: bool = True) -> HookRecord | None:
        response = self._call(
            "get_item", TableName=self._table, Key=_hook_key(handle), ConsistentRead=consistent
        )
        item = response.get("Item") if isinstance(response, dict) else None
        if not item:
            return None
        return HookRecord(
            handle=handle,
            state=HookState(item["state"]["S"]),
            resource_gid=item["resource_gid"]["S"],
            webhook_gid=item["webhook_gid"]["S"] if "webhook_gid" in item else None,
            expires_at=int(item["expires_at"]["N"]),
            handshaken_at=int(item["handshaken_at"]["N"]) if "handshaken_at" in item else None,
        )

    def mark_handshaken(self, *, handle: str, now: int) -> None:
        """``pending -> handshaken``; the first handshake wins. Expiry is in the condition."""
        self._update_hook(
            handle,
            set_values={"state": _s(HookState.HANDSHAKEN.value), "handshaken_at": _n(now)},
            condition="#state = :pending AND expires_at > :now",
            condition_values={":pending": _s(HookState.PENDING.value), ":now": _n(now)},
        )

    def set_webhook_gid(self, *, handle: str, webhook_gid: str) -> None:
        clause, values = _state_in(
            (HookState.PENDING, HookState.HANDSHAKEN, HookState.CREATE_UNKNOWN)
        )
        self._update_hook(
            handle,
            set_values={"webhook_gid": _s(webhook_gid)},
            condition=clause,
            condition_values=values,
        )

    def mark_create_unknown(self, *, handle: str, now: int) -> None:
        clause, values = _state_in((HookState.PENDING, HookState.HANDSHAKEN))
        self._update_hook(
            handle,
            set_values={"state": _s(HookState.CREATE_UNKNOWN.value), "updated_at": _n(now)},
            condition=clause,
            condition_values=values,
        )

    def mark_failed(self, *, handle: str, now: int) -> None:
        clause, values = _state_in(
            (HookState.PENDING, HookState.HANDSHAKEN, HookState.CREATE_UNKNOWN)
        )
        self._update_hook(
            handle,
            set_values={
                "state": _s(HookState.FAILED.value),
                "updated_at": _n(now),
                "ttl": _n(now + CLOSED_ROW_RETENTION_S),
            },
            condition=clause,
            condition_values=values,
        )

    def mark_compromised(self, *, handle: str, now: int) -> None:
        """``* -> compromised``. Kept without a TTL, for forensics."""
        self._update_hook(
            handle,
            set_values={"state": _s(HookState.COMPROMISED.value), "updated_at": _n(now)},
            remove=("ttl",),
            condition="attribute_exists(pk)",
        )

    def mark_removed(self, *, handle: str, now: int) -> None:
        """``* -> removed``, except a compromised row, which stays compromised."""
        self._update_hook(
            handle,
            set_values={
                "state": _s(HookState.REMOVED.value),
                "updated_at": _n(now),
                "ttl": _n(now + CLOSED_ROW_RETENTION_S),
            },
            condition="attribute_exists(pk) AND #state <> :compromised",
            condition_values={":compromised": _s(HookState.COMPROMISED.value)},
        )

    def activate(
        self,
        *,
        handle: str,
        project_gid: str,
        webhook_gid: str,
        now: int,
        from_state: HookState,
        previous_handle: str | None,
    ) -> None:
        """Move the hook to ``active`` and point the project's ``ACTIVE`` row at it.

        One transaction. The hook must be in ``from_state``: ``handshaken`` for a normal
        registration, or ``create_unknown`` with ``handshaken_at`` set (adoption, OR-1).
        The ``ACTIVE`` put requires no row, or a row naming ``previous_handle``.
        """
        if from_state is HookState.HANDSHAKEN:
            hook_condition = "#state = :from"
        elif from_state is HookState.CREATE_UNKNOWN:
            hook_condition = "#state = :from AND attribute_exists(handshaken_at)"
        else:
            raise HookRegistryConflict(f"activation from {from_state.value} is not a transition")
        if previous_handle is None:
            active_condition = "attribute_not_exists(pk)"
            active_values: dict[str, dict[str, str]] = {}
        else:
            active_condition = "attribute_not_exists(pk) OR #handle = :old"
            active_values = {":old": _s(previous_handle)}
        active_put: dict[str, Any] = {
            "TableName": self._table,
            "Item": {
                **_active_key(project_gid),
                "handle": _s(handle),
                "updated_at": _n(now),
            },
            "ConditionExpression": active_condition,
        }
        if previous_handle is not None:
            active_put["ExpressionAttributeNames"] = {"#handle": "handle"}
            active_put["ExpressionAttributeValues"] = active_values
        self._call(
            "transact_write_items",
            TransactItems=[
                {
                    "Update": {
                        "TableName": self._table,
                        "Key": _hook_key(handle),
                        "UpdateExpression": (
                            "SET #state = :active, webhook_gid = :wg, updated_at = :now REMOVE #ttl"
                        ),
                        "ConditionExpression": hook_condition,
                        "ExpressionAttributeNames": {"#state": "state", "#ttl": "ttl"},
                        "ExpressionAttributeValues": {
                            ":active": _s(HookState.ACTIVE.value),
                            ":from": _s(from_state.value),
                            ":wg": _s(webhook_gid),
                            ":now": _n(now),
                        },
                    }
                },
                {"Put": active_put},
            ],
        )

    # -- PROJECT#/ACTIVE ------------------------------------------------------------

    def get_active_handle(self, project_gid: str, *, consistent: bool = True) -> str | None:
        response = self._call(
            "get_item",
            TableName=self._table,
            Key=_active_key(project_gid),
            ConsistentRead=consistent,
        )
        item = response.get("Item") if isinstance(response, dict) else None
        if not item:
            return None
        handle = item.get("handle", {}).get("S")
        return handle if isinstance(handle, str) else None

    # -- LEASE#reconciler -----------------------------------------------------------

    def acquire_lease(self, *, owner: str, now: int, duration_s: int) -> bool:
        """Take or renew the reconciler lease. ``False`` when another owner holds it."""
        try:
            self._call(
                "put_item",
                TableName=self._table,
                Item={
                    **_lease_key(LEASE_NAME),
                    "owner": _s(owner),
                    "until": _n(now + duration_s),
                },
                ConditionExpression="attribute_not_exists(pk) OR #until < :now OR #owner = :me",
                ExpressionAttributeNames={"#until": "until", "#owner": "owner"},
                ExpressionAttributeValues={":now": _n(now), ":me": _s(owner)},
            )
        except HookRegistryConflict:
            return False
        return True

    def release_lease(self, *, owner: str) -> None:
        try:
            self._call(
                "delete_item",
                TableName=self._table,
                Key=_lease_key(LEASE_NAME),
                ConditionExpression="#owner = :me",
                ExpressionAttributeNames={"#owner": "owner"},
                ExpressionAttributeValues={":me": _s(owner)},
            )
        except HookRegistryConflict:
            logger.warning("hook_registry_lease_not_held", extra={"owner": owner})
