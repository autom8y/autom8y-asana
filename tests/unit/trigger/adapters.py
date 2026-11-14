"""D6 test adapters: the in-memory registry and the in-memory key store (TDD section 2a).

These live under ``tests/`` ONLY. They are absent from the built wheel and image (PM-2,
tests/arch/test_trigger_adapter_placement.py), and nothing in ``src/`` names them (PM-4).
Each constructor calls ``require_test_adapter_environment``: it builds only when
``ASANA_HOOK_ENVIRONMENT`` is exactly ``test`` or ``local`` (PM-1, PM-3).

``InMemoryHookRegistry`` is the real :class:`HookRegistry` over moto's in-memory DynamoDB,
so the registration tests exercise the real conditional expressions. Build it inside an
active ``moto.mock_aws`` context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8_asana.trigger.hook_environment import require_test_adapter_environment
from autom8_asana.trigger.hook_registry import HookRegistry
from autom8_asana.trigger.hook_store import (
    HookStoreReadFailed,
    HookStoreWriteFailed,
    HookValueAlreadyStored,
    hook_secret_name,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

TEST_TABLE_NAME = "autom8y-asana-hook-registry-test"
TEST_REGION = "us-east-1"


def create_registry_table(client: Any, table_name: str = TEST_TABLE_NAME) -> None:
    """The D-1 schema as declared in Terraform: pk/sk strings, sparse GSI, TTL."""
    client.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "undecided_pk", "AttributeType": "S"},
            {"AttributeName": "undecided_sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "undecided",
                "KeySchema": [
                    {"AttributeName": "undecided_pk", "KeyType": "HASH"},
                    {"AttributeName": "undecided_sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
    )


class InMemoryHookRegistry(HookRegistry):
    """The real registry over moto's in-memory DynamoDB. Test marker only."""

    def __init__(self, *, client: Any, environ: Mapping[str, str]) -> None:
        require_test_adapter_environment(consumer="in_memory_hook_registry", environ=environ)
        create_registry_table(client)
        super().__init__(table_name=TEST_TABLE_NAME, client=client)


@dataclass
class InMemoryKeyHookStore:
    """A write-once, dict-backed stand-in for ``HookStore``. Test marker only.

    ``events`` is shared with the fake Asana so tests can assert call order (OR-1: the
    stored value is deleted LAST). ``fail_create`` makes the handshake's store write fail
    (HS-4). ``fail_read`` makes the receiver's key read fail (SM-1, A C-8); ``reads``
    counts key reads (KS-1).
    """

    environ: Mapping[str, str]
    events: list[tuple[str, str]] = field(default_factory=list)
    fail_create: bool = False
    values: dict[str, str] = field(default_factory=dict, repr=False)
    tags: dict[str, dict[str, str]] = field(default_factory=dict)
    on_create: Callable[[str], None] | None = None
    fail_read: bool = False
    reads: int = 0

    def __post_init__(self) -> None:
        require_test_adapter_environment(consumer="in_memory_key_hook_store", environ=self.environ)

    def create_hook_value(
        self, *, handle: str, hook_value: str, resource_gid: str, registered_at: str
    ) -> None:
        name = hook_secret_name(handle)
        self.events.append(("store_create", handle))
        if self.fail_create:
            raise HookStoreWriteFailed("simulated store failure", error_code="InternalServiceError")
        if name in self.values:
            raise HookValueAlreadyStored("write-once", error_code="ResourceExistsException")
        self.values[name] = hook_value

    def tag_webhook_gid(self, *, handle: str, webhook_gid: str) -> None:
        self.tags.setdefault(hook_secret_name(handle), {})["webhook_gid"] = webhook_gid

    def delete_hook_value(self, *, handle: str) -> bool:
        self.events.append(("store_delete", handle))
        return self.values.pop(hook_secret_name(handle), None) is not None

    def has_value(self, handle: str) -> bool:
        return hook_secret_name(handle) in self.values

    def read_hook_value(self, *, handle: str) -> str:
        self.reads += 1
        self.events.append(("store_read", handle))
        if self.fail_read:
            raise HookStoreReadFailed("simulated read failure", error_code="InternalServiceError")
        value = self.values.get(hook_secret_name(handle))
        if value is None:
            raise HookStoreReadFailed("no entry", error_code="ResourceNotFoundException")
        return value

    def put_for_test(self, handle: str, value: str) -> None:
        """Seed a stored value without the handshake (receiver tests)."""
        self.values[hook_secret_name(handle)] = value
