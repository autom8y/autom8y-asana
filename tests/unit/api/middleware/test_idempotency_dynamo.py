"""Tests for DynamoDBIdempotencyStore, NoopIdempotencyStore, and environment gate.

Covers:
- DynamoDB store protocol conformance with mocked boto3 client
- Noop store passthrough behavior
- Environment gate in create_app() selecting correct store type
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.api.middleware.idempotency import (
    DynamoDBIdempotencyStore,
    IdempotencyStore,
    InMemoryIdempotencyStore,
    NoopIdempotencyStore,
    StoredResponse,
)

# ===========================================================================
# DynamoDBIdempotencyStore tests
# ===========================================================================


class TestDynamoDBIdempotencyStoreProtocol:
    """Verify DynamoDBIdempotencyStore conforms to IdempotencyStore protocol."""

    def test_implements_protocol(self) -> None:
        """DynamoDBIdempotencyStore is recognized as an IdempotencyStore."""
        with patch("boto3.client"):
            store = DynamoDBIdempotencyStore(
                table_name="test-table",
                region="us-east-1",
            )
        assert isinstance(store, IdempotencyStore)


class TestDynamoDBIdempotencyStoreGet:
    """Tests for DynamoDBIdempotencyStore.get()."""

    def _make_store(self, mock_client: MagicMock) -> DynamoDBIdempotencyStore:
        with patch("boto3.client", return_value=mock_client):
            return DynamoDBIdempotencyStore(
                table_name="test-table",
                region="us-east-1",
            )

    async def test_get_returns_none_for_missing_key(self) -> None:
        """get() returns None when GetItem finds no item."""
        mock_client = MagicMock()
        mock_client.get_item.return_value = {}
        store = self._make_store(mock_client)

        result = await store.get("svc#key1", "POST#/v1/intake/business")
        assert result is None

    async def test_get_returns_stored_response_for_existing_key(self) -> None:
        """get() returns StoredResponse when item exists in DynamoDB."""
        body_b64 = base64.b64encode(b'{"ok": true}').decode("ascii")
        headers_json = json.dumps({"content-type": "application/json"})

        mock_client = MagicMock()
        mock_client.get_item.return_value = {
            "Item": {
                "pk": {"S": "svc#key1"},
                "sk": {"S": "POST#/v1/intake/business"},
                "status": {"S": "complete"},
                "request_fingerprint": {"S": "abc123"},
                "response_status": {"N": "201"},
                "response_body": {"S": body_b64},
                "response_headers": {"S": headers_json},
                "created_at": {"S": "2026-03-27T00:00:00+00:00"},
                "ttl": {"N": "1711584000"},
            }
        }
        store = self._make_store(mock_client)

        result = await store.get("svc#key1", "POST#/v1/intake/business")
        assert result is not None
        assert result.status == "complete"
        assert result.request_fingerprint == "abc123"
        assert result.response_status == 201
        assert result.response_body == b'{"ok": true}'
        assert result.response_headers == {"content-type": "application/json"}
        assert result.created_at == "2026-03-27T00:00:00+00:00"

    async def test_get_returns_none_on_client_error(self) -> None:
        """get() returns None when DynamoDB client raises an exception."""
        mock_client = MagicMock()
        mock_client.get_item.side_effect = Exception("DynamoDB unavailable")
        store = self._make_store(mock_client)

        result = await store.get("svc#key1", "POST#/v1/intake/business")
        assert result is None


class TestDynamoDBIdempotencyStoreClaim:
    """Tests for DynamoDBIdempotencyStore.claim()."""

    def _make_store(self, mock_client: MagicMock) -> DynamoDBIdempotencyStore:
        with patch("boto3.client", return_value=mock_client):
            return DynamoDBIdempotencyStore(
                table_name="test-table",
                region="us-east-1",
            )

    async def test_claim_succeeds_on_new_key(self) -> None:
        """claim() returns True when PutItem succeeds (key does not exist)."""
        mock_client = MagicMock()
        mock_client.put_item.return_value = {}
        # Need to set up the exceptions attribute for ConditionalCheckFailedException
        mock_client.exceptions.ConditionalCheckFailedException = type(
            "ConditionalCheckFailedException", (Exception,), {}
        )
        store = self._make_store(mock_client)

        result = await store.claim(
            "svc#key1", "POST#/v1/intake/business", "fingerprint123"
        )
        assert result is True

        # Verify PutItem was called with condition expression
        call_kwargs = mock_client.put_item.call_args[1]
        assert call_kwargs["ConditionExpression"] == "attribute_not_exists(pk)"
        assert call_kwargs["Item"]["status"]["S"] == "processing"
        assert call_kwargs["Item"]["request_fingerprint"]["S"] == "fingerprint123"

    async def test_claim_returns_false_on_existing_key(self) -> None:
        """claim() returns False when ConditionalCheckFailedException is raised."""
        mock_client = MagicMock()
        exc_class = type("ConditionalCheckFailedException", (Exception,), {})
        mock_client.exceptions.ConditionalCheckFailedException = exc_class
        mock_client.put_item.side_effect = exc_class("Key already exists")
        store = self._make_store(mock_client)

        result = await store.claim(
            "svc#key1", "POST#/v1/intake/business", "fingerprint123"
        )
        assert result is False

    async def test_claim_returns_false_on_unexpected_error(self) -> None:
        """claim() returns False on unexpected DynamoDB errors."""
        mock_client = MagicMock()
        mock_client.exceptions.ConditionalCheckFailedException = type(
            "ConditionalCheckFailedException", (Exception,), {}
        )
        mock_client.put_item.side_effect = RuntimeError("Network error")
        store = self._make_store(mock_client)

        result = await store.claim(
            "svc#key1", "POST#/v1/intake/business", "fingerprint123"
        )
        assert result is False


class TestDynamoDBIdempotencyStoreFinalize:
    """Tests for DynamoDBIdempotencyStore.finalize()."""

    def _make_store(self, mock_client: MagicMock) -> DynamoDBIdempotencyStore:
        with patch("boto3.client", return_value=mock_client):
            return DynamoDBIdempotencyStore(
                table_name="test-table",
                region="us-east-1",
            )

    async def test_finalize_updates_stored_response(self) -> None:
        """finalize() writes complete status with response data."""
        mock_client = MagicMock()
        # get_item returns the existing claim
        mock_client.get_item.return_value = {
            "Item": {
                "pk": {"S": "svc#key1"},
                "sk": {"S": "POST#/v1/intake/business"},
                "status": {"S": "processing"},
                "request_fingerprint": {"S": "fp123"},
                "response_status": {"N": "0"},
                "response_body": {"S": ""},
                "response_headers": {"S": "{}"},
                "created_at": {"S": "2026-03-27T00:00:00+00:00"},
                "ttl": {"N": "1711584000"},
            }
        }
        mock_client.put_item.return_value = {}
        store = self._make_store(mock_client)

        result = await store.finalize(
            pk="svc#key1",
            sk="POST#/v1/intake/business",
            response_status=201,
            response_body=b'{"gid": "123"}',
            response_headers={"content-type": "application/json"},
        )
        assert result is True

        # Verify the finalize PutItem call
        # put_item is called once (finalize only; get used get_item)
        call_kwargs = mock_client.put_item.call_args[1]
        assert call_kwargs["Item"]["status"]["S"] == "complete"
        assert call_kwargs["Item"]["response_status"]["N"] == "201"
        assert call_kwargs["Item"]["request_fingerprint"]["S"] == "fp123"
        assert call_kwargs["Item"]["created_at"]["S"] == "2026-03-27T00:00:00+00:00"

        # Verify body is base64-encoded
        stored_body = base64.b64decode(call_kwargs["Item"]["response_body"]["S"])
        assert stored_body == b'{"gid": "123"}'

    async def test_finalize_returns_false_on_error(self) -> None:
        """finalize() returns False when DynamoDB put_item fails."""
        mock_client = MagicMock()
        # get_item succeeds (returns the existing claim), but put_item fails
        mock_client.get_item.return_value = {
            "Item": {
                "pk": {"S": "svc#key1"},
                "sk": {"S": "POST#/v1/intake/business"},
                "status": {"S": "processing"},
                "request_fingerprint": {"S": "fp123"},
                "response_status": {"N": "0"},
                "response_body": {"S": ""},
                "response_headers": {"S": "{}"},
                "created_at": {"S": "2026-03-27T00:00:00+00:00"},
                "ttl": {"N": "1711584000"},
            }
        }
        mock_client.put_item.side_effect = Exception("DynamoDB write failed")
        store = self._make_store(mock_client)

        result = await store.finalize(
            pk="svc#key1",
            sk="POST#/v1/intake/business",
            response_status=201,
            response_body=b'{"gid": "123"}',
            response_headers={},
        )
        assert result is False


class TestDynamoDBIdempotencyStoreDelete:
    """Tests for DynamoDBIdempotencyStore.delete()."""

    def _make_store(self, mock_client: MagicMock) -> DynamoDBIdempotencyStore:
        with patch("boto3.client", return_value=mock_client):
            return DynamoDBIdempotencyStore(
                table_name="test-table",
                region="us-east-1",
            )

    async def test_delete_removes_key(self) -> None:
        """delete() calls DeleteItem and returns True on success."""
        mock_client = MagicMock()
        mock_client.delete_item.return_value = {}
        store = self._make_store(mock_client)

        result = await store.delete("svc#key1", "POST#/v1/intake/business")
        assert result is True

        call_kwargs = mock_client.delete_item.call_args[1]
        assert call_kwargs["Key"]["pk"]["S"] == "svc#key1"
        assert call_kwargs["Key"]["sk"]["S"] == "POST#/v1/intake/business"

    async def test_delete_returns_false_on_error(self) -> None:
        """delete() returns False when DynamoDB client raises."""
        mock_client = MagicMock()
        mock_client.delete_item.side_effect = Exception("DynamoDB unavailable")
        store = self._make_store(mock_client)

        result = await store.delete("svc#key1", "POST#/v1/intake/business")
        assert result is False


# ===========================================================================
# NoopIdempotencyStore tests
# ===========================================================================


class TestNoopIdempotencyStore:
    """Verify NoopIdempotencyStore passthrough behavior."""

    def test_implements_protocol(self) -> None:
        """NoopIdempotencyStore is recognized as an IdempotencyStore."""
        store = NoopIdempotencyStore()
        assert isinstance(store, IdempotencyStore)

    async def test_get_returns_none(self) -> None:
        """get() always returns None (no stored responses)."""
        store = NoopIdempotencyStore()
        result = await store.get("any-pk", "any-sk")
        assert result is None

    async def test_claim_returns_true(self) -> None:
        """claim() always returns True (always succeeds passthrough)."""
        store = NoopIdempotencyStore()
        result = await store.claim("any-pk", "any-sk", "any-fingerprint")
        assert result is True

    async def test_finalize_returns_true(self) -> None:
        """finalize() always returns True (no-op)."""
        store = NoopIdempotencyStore()
        result = await store.finalize(
            pk="any-pk",
            sk="any-sk",
            response_status=200,
            response_body=b"body",
            response_headers={"content-type": "application/json"},
        )
        assert result is True

    async def test_delete_returns_true(self) -> None:
        """delete() always returns True (no-op)."""
        store = NoopIdempotencyStore()
        result = await store.delete("any-pk", "any-sk")
        assert result is True


# ===========================================================================
# Environment gate tests
# ===========================================================================


class TestEnvironmentGate:
    """Test that IDEMPOTENCY_STORE_BACKEND selects the correct store type."""

    def _get_idempotency_store(self, app: Any) -> Any:
        """Extract the idempotency store from the middleware stack."""
        for mw in app.user_middleware:
            if mw.cls.__name__ == "IdempotencyMiddleware":
                return mw.kwargs.get("store")
        return None

    @patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "memory"})
    def test_memory_backend(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=memory creates InMemoryIdempotencyStore."""
        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ):
            from autom8_asana.api.main import create_app

            app = create_app()
            store = self._get_idempotency_store(app)
            assert isinstance(store, InMemoryIdempotencyStore)

    @patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "noop"})
    def test_noop_backend(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=noop creates NoopIdempotencyStore."""
        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ):
            from autom8_asana.api.main import create_app

            app = create_app()
            store = self._get_idempotency_store(app)
            assert isinstance(store, NoopIdempotencyStore)

    @patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "dynamodb"})
    def test_dynamodb_backend(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=dynamodb creates DynamoDBIdempotencyStore."""
        with (
            patch(
                "autom8_asana.api.lifespan._discover_entity_projects",
                new_callable=AsyncMock,
            ),
            patch("boto3.client"),
        ):
            from autom8_asana.api.main import create_app

            app = create_app()
            store = self._get_idempotency_store(app)
            assert isinstance(store, DynamoDBIdempotencyStore)

    @patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "unknown-backend"})
    def test_unknown_backend_falls_back_to_noop(self) -> None:
        """Unknown IDEMPOTENCY_STORE_BACKEND falls back to NoopIdempotencyStore."""
        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ):
            from autom8_asana.api.main import create_app

            app = create_app()
            store = self._get_idempotency_store(app)
            assert isinstance(store, NoopIdempotencyStore)

    @patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "dynamodb"})
    def test_dynamodb_creation_failure_falls_back_to_noop(self) -> None:
        """DynamoDB creation failure falls back to NoopIdempotencyStore."""
        with (
            patch(
                "autom8_asana.api.lifespan._discover_entity_projects",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.api.middleware.idempotency.DynamoDBIdempotencyStore.__init__",
                side_effect=Exception("Cannot connect"),
            ),
        ):
            from autom8_asana.api.main import create_app

            app = create_app()
            store = self._get_idempotency_store(app)
            assert isinstance(store, NoopIdempotencyStore)
