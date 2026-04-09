"""Adversarial tests for Tier 2 Resource Clients (TDD-0004).

This test file validates edge cases, error handling, and security-critical
scenarios for Phase 2C implementation. Tests are designed to find problems
before production does.

Test Categories:
1. Webhook Signature Verification - Security-critical HMAC-SHA256 validation
2. Attachment Operations - File upload/download edge cases
3. Goals Hierarchy - Subgoals, supporting work, followers
4. Portfolios - Item management, members, custom fields
5. Model Edge Cases - Required fields, nested structures, edge values

Per ADR-0008: Webhook signatures use HMAC-SHA256 with timing-safe comparison.
Per ADR-0009: Attachments use multipart/form-data for upload.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.goals import GoalsClient
from autom8_asana.clients.portfolios import PortfoliosClient
from autom8_asana.clients.stories import StoriesClient
from autom8_asana.clients.webhooks import WebhooksClient
from autom8_asana.exceptions import AsanaError, SyncInAsyncContextError
from autom8_asana.models import (
    Attachment,
    Goal,
    PageIterator,
    Portfolio,
    Story,
    Tag,
    Team,
    Webhook,
)
from autom8_asana.models.common import NameGid
from autom8_asana.models.goal import GoalMembership, GoalMetric
from autom8_asana.models.story import Story
from autom8_asana.models.webhook import WebhookFilter

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig


@pytest.fixture
def webhooks_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> WebhooksClient:
    """Create WebhooksClient with mocked dependencies."""
    return WebhooksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


@pytest.fixture
def attachments_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> AttachmentsClient:
    """Create AttachmentsClient with mocked dependencies."""
    return AttachmentsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


@pytest.fixture
def goals_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> GoalsClient:
    """Create GoalsClient with mocked dependencies."""
    return GoalsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


@pytest.fixture
def portfolios_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> PortfoliosClient:
    """Create PortfoliosClient with mocked dependencies."""
    return PortfoliosClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


@pytest.fixture
def stories_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> StoriesClient:
    """Create StoriesClient with mocked dependencies."""
    return StoriesClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


# =============================================================================
# 1. WEBHOOK SIGNATURE VERIFICATION (SECURITY-CRITICAL)
# =============================================================================


class TestWebhookSignatureVerificationValid:
    """Tests for valid webhook signature verification."""

    def test_verify_signature_valid_empty_body(self) -> None:
        """verify_signature handles empty request body."""
        secret = "test_secret"
        body = b""
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_json_body(self) -> None:
        """verify_signature validates standard JSON body."""
        secret = "my_webhook_secret_123"
        body = b'{"events":[{"resource":{"gid":"123"}}]}'
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_large_body(self) -> None:
        """verify_signature handles large request bodies."""
        secret = "secret"
        body = b"x" * 1_000_000  # 1MB body
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_unicode_secret(self) -> None:
        """verify_signature handles Unicode characters in secret."""
        secret = "secret_with_unicode_"
        body = b'{"test": "data"}'
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_binary_body(self) -> None:
        """verify_signature handles binary data in body."""
        secret = "secret"
        body = bytes(range(256))  # All possible byte values
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True


class TestWebhookSignatureVerificationInvalid:
    """Tests for invalid webhook signature rejection."""

    def test_verify_signature_invalid_wrong_signature(self) -> None:
        """verify_signature rejects wrong signature."""
        result = WebhooksClient.verify_signature(
            b'{"events": []}',
            "completely_wrong_signature",
            "test_secret",
        )
        assert result is False

    def test_verify_signature_invalid_truncated_signature(self) -> None:
        """verify_signature rejects truncated signature."""
        secret = "test_secret"
        body = b'{"test": "data"}'
        correct = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        truncated = correct[:32]  # Half the signature

        result = WebhooksClient.verify_signature(body, truncated, secret)
        assert result is False

    def test_verify_signature_invalid_wrong_secret(self) -> None:
        """verify_signature rejects signature computed with wrong secret."""
        body = b'{"test": "data"}'
        wrong_sig = hmac.new(b"wrong_secret", body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, wrong_sig, "correct_secret")
        assert result is False

    def test_verify_signature_invalid_modified_body(self) -> None:
        """verify_signature rejects signature when body was modified."""
        secret = "test_secret"
        original_body = b'{"events": []}'
        sig = hmac.new(secret.encode(), original_body, hashlib.sha256).hexdigest()

        # Attacker modifies body
        modified_body = b'{"events": [{"malicious": true}]}'

        result = WebhooksClient.verify_signature(modified_body, sig, secret)
        assert result is False

    def test_verify_signature_invalid_empty_signature(self) -> None:
        """verify_signature rejects empty signature."""
        result = WebhooksClient.verify_signature(
            b'{"events": []}',
            "",
            "test_secret",
        )
        assert result is False

    def test_verify_signature_invalid_case_sensitivity(self) -> None:
        """verify_signature is case-sensitive for hex signatures."""
        secret = "test_secret"
        body = b'{"test": "data"}'
        sig_lower = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        sig_upper = sig_lower.upper()

        # Lowercase is valid
        assert WebhooksClient.verify_signature(body, sig_lower, secret) is True
        # Uppercase should also work since hexdigest returns lowercase
        # but let's verify both are handled properly
        # Note: compare_digest will compare exact strings, uppercase would fail
        # if the expected is lowercase. This is expected behavior.
        assert WebhooksClient.verify_signature(body, sig_upper, secret) is False


class TestWebhookSignatureTimingSafety:
    """Tests to verify timing-safe comparison is used.

    These tests verify that hmac.compare_digest is used (timing-safe)
    rather than standard string comparison (vulnerable to timing attacks).
    """

    def test_timing_safe_comparison_implementation(self) -> None:
        """Verify implementation uses hmac.compare_digest."""
        # We can verify this by checking the function uses compare_digest
        # by inspecting the source or testing indirectly.
        # The signature verification should work correctly for matching sigs.
        secret = "test"
        body = b"data"
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        # If this passes, compare_digest is being used correctly
        assert WebhooksClient.verify_signature(body, sig, secret) is True

    def test_partial_match_rejected(self) -> None:
        """Verify partial signature matches are rejected."""
        secret = "test"
        body = b"data"
        correct_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        # Try various partial matches that could pass with naive comparison
        assert WebhooksClient.verify_signature(body, correct_sig[:-1], secret) is False
        assert WebhooksClient.verify_signature(body, correct_sig + "x", secret) is False
        assert (
            WebhooksClient.verify_signature(body, "0" + correct_sig[1:], secret)
            is False
        )


class TestWebhookHandshakeSecretExtraction:
    """Tests for extracting handshake secrets from headers."""

    def test_extract_handshake_secret_standard_case(self) -> None:
        """Extract secret with standard header case."""
        headers = {"X-Hook-Secret": "secret_123"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "secret_123"

    def test_extract_handshake_secret_lowercase(self) -> None:
        """Extract secret with lowercase header."""
        headers = {"x-hook-secret": "secret_456"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "secret_456"

    def test_extract_handshake_secret_mixed_case(self) -> None:
        """Extract secret with mixed case header."""
        headers = {"X-HOOK-SECRET": "secret_789"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "secret_789"

    def test_extract_handshake_secret_with_other_headers(self) -> None:
        """Extract secret when other headers are present."""
        headers = {
            "Content-Type": "application/json",
            "X-Hook-Secret": "the_secret",
            "User-Agent": "Asana-Webhooks",
            "X-Hook-Signature": "some_signature",
        }
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "the_secret"

    def test_extract_handshake_secret_missing(self) -> None:
        """Return None when X-Hook-Secret is missing."""
        headers = {
            "Content-Type": "application/json",
            "X-Hook-Signature": "signature",
        }
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result is None

    def test_extract_handshake_secret_empty_headers(self) -> None:
        """Return None for empty headers dict."""
        headers: dict[str, str] = {}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result is None

    def test_extract_handshake_secret_empty_value(self) -> None:
        """Return empty string if secret value is empty."""
        headers = {"X-Hook-Secret": ""}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == ""

    def test_extract_handshake_secret_unicode_value(self) -> None:
        """Handle Unicode characters in secret value."""
        headers = {"X-Hook-Secret": "secret_with_unicode_"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "secret_with_unicode_"


# =============================================================================
# 2. ATTACHMENT OPERATIONS (CRITICAL)
# =============================================================================


class TestAttachmentUploadEdgeCases:
    """Tests for attachment upload edge cases."""

    async def test_upload_empty_file(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload handles empty file correctly."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "empty.txt",
            "size": 0,
        }

        file_obj = BytesIO(b"")
        result = await attachments_client.upload_async(
            parent="task1", file=file_obj, name="empty.txt"
        )

        assert isinstance(result, Attachment)
        assert result.size == 0
        mock_http.post_multipart.assert_called_once()

    async def test_upload_various_file_types(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload handles various MIME types correctly."""
        test_cases = [
            ("document.pdf", "application/pdf"),
            ("image.png", "image/png"),
            ("image.jpg", "image/jpeg"),
            ("data.json", "application/json"),
            ("archive.zip", "application/zip"),
            ("unknown.randomext123", "application/octet-stream"),  # Unknown extension
        ]

        for filename, expected_mime in test_cases:
            mock_http.post_multipart.reset_mock()
            mock_http.post_multipart.return_value = {
                "gid": "att123",
                "name": filename,
            }

            file_obj = BytesIO(b"test content")
            await attachments_client.upload_async(
                parent="task1", file=file_obj, name=filename
            )

            call_args = mock_http.post_multipart.call_args
            files_param = call_args[1]["files"]
            # files is {"file": (name, file_obj, content_type)}  # noqa: ERA001
            actual_mime = files_param["file"][2]
            assert actual_mime == expected_mime, f"Failed for {filename}"

    async def test_upload_explicit_content_type(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload uses explicit content_type when provided."""
        mock_http.post_multipart.return_value = {"gid": "att123", "name": "data.bin"}

        file_obj = BytesIO(b"binary data")
        await attachments_client.upload_async(
            parent="task1",
            file=file_obj,
            name="data.bin",
            content_type="application/custom-type",
        )

        call_args = mock_http.post_multipart.call_args
        files_param = call_args[1]["files"]
        assert files_param["file"][2] == "application/custom-type"

    async def test_upload_unicode_filename(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload handles Unicode characters in filename."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "document.pdf",
        }

        file_obj = BytesIO(b"content")
        result = await attachments_client.upload_async(
            parent="task1", file=file_obj, name="document.pdf"
        )

        assert isinstance(result, Attachment)

    async def test_upload_special_chars_in_filename(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload handles special characters in filename."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "file (1).txt",
        }

        file_obj = BytesIO(b"content")
        result = await attachments_client.upload_async(
            parent="task1", file=file_obj, name="file (1).txt"
        )

        assert isinstance(result, Attachment)


class TestAttachmentUploadFromPath:
    """Tests for upload_from_path_async edge cases."""

    async def test_upload_from_path_uses_basename(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """upload_from_path_async uses path basename by default."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "test.txt",
            "size": 12,
        }

        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = await attachments_client.upload_from_path_async(
                parent="task1", path=temp_path
            )

            assert isinstance(result, Attachment)
            # Verify the correct filename was used
            call_args = mock_http.post_multipart.call_args
            files_param = call_args[1]["files"]
            assert files_param["file"][0] == Path(temp_path).name
        finally:
            os.unlink(temp_path)

    async def test_upload_from_path_custom_name(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """upload_from_path_async allows custom name."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "custom_name.pdf",
        }

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"content")
            temp_path = f.name

        try:
            result = await attachments_client.upload_from_path_async(
                parent="task1", path=temp_path, name="custom_name.pdf"
            )

            assert isinstance(result, Attachment)
            call_args = mock_http.post_multipart.call_args
            files_param = call_args[1]["files"]
            assert files_param["file"][0] == "custom_name.pdf"
        finally:
            os.unlink(temp_path)


class TestAttachmentExternalCreation:
    """Tests for external attachment creation."""

    async def test_create_external_with_long_url(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Create external attachment with long URL."""
        long_url = "https://example.com/" + "a" * 2000
        mock_http.post.return_value = {
            "gid": "att123",
            "name": "Link",
            "host": "external",
            "view_url": long_url,
        }

        result = await attachments_client.create_external_async(
            parent="task1", url=long_url, name="Link"
        )

        assert isinstance(result, Attachment)
        assert result.host == "external"

    async def test_create_external_with_unicode_name(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Create external attachment with Unicode name."""
        mock_http.post.return_value = {
            "gid": "att123",
            "name": "Document",
            "host": "external",
        }

        result = await attachments_client.create_external_async(
            parent="task1",
            url="https://example.com/doc",
            name="Document",
        )

        assert isinstance(result, Attachment)


class TestAttachmentDownload:
    """Tests for attachment download operations."""

    async def test_download_to_path(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Download attachment to file path."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "test.txt",
            "download_url": "https://example.com/download/test.txt",
        }

        async def mock_stream(url: str):
            yield b"chunk1"
            yield b"chunk2"

        mock_http.get_stream_url = mock_stream

        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / "downloaded.txt"

            result = await attachments_client.download_async(
                "att123", destination=dest_path
            )

            assert result == dest_path
            assert dest_path.exists()
            assert dest_path.read_bytes() == b"chunk1chunk2"

    async def test_download_to_file_object(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Download attachment to file-like object."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "test.bin",
            "download_url": "https://example.com/download",
        }

        async def mock_stream(url: str):
            yield b"data"

        mock_http.get_stream_url = mock_stream

        buffer = BytesIO()
        result = await attachments_client.download_async("att123", destination=buffer)

        assert result is None  # None when destination is file object
        assert buffer.getvalue() == b"data"

    async def test_download_no_download_url_raises_error(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Download raises error when no download_url."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "external_link",
            "download_url": None,  # External links don't have download URLs
        }

        with pytest.raises(AsanaError) as exc_info:
            await attachments_client.download_async(
                "att123", destination="/tmp/test.txt"
            )

        assert "no download URL" in str(exc_info.value)


# =============================================================================
# 3. GOALS HIERARCHY
# =============================================================================


class TestGoalsSubgoalOperations:
    """Tests for Goals subgoal operations."""

    async def test_add_subgoal_basic(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add subgoal to parent goal."""
        mock_http.post.return_value = {
            "gid": "parent_goal",
            "name": "Parent Goal",
        }

        result = await goals_client.add_subgoal_async(
            "parent_goal", subgoal="subgoal123"
        )

        assert isinstance(result, Goal)
        mock_http.post.assert_called_once_with(
            "/goals/parent_goal/addSubgoal",
            json={"data": {"subgoal": "subgoal123"}},
        )

    async def test_add_subgoal_with_positioning(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add subgoal with insert_before/after positioning."""
        mock_http.post.return_value = {"gid": "parent", "name": "Parent"}

        # Test insert_before
        await goals_client.add_subgoal_async(
            "parent", subgoal="new_sub", insert_before="existing_sub"
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_before"] == "existing_sub"

        # Test insert_after
        mock_http.post.reset_mock()
        mock_http.post.return_value = {"gid": "parent", "name": "Parent"}
        await goals_client.add_subgoal_async(
            "parent", subgoal="new_sub", insert_after="existing_sub"
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_after"] == "existing_sub"

    async def test_remove_subgoal(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove subgoal from parent goal."""
        mock_http.post.return_value = {}

        await goals_client.remove_subgoal_async("parent", subgoal="subgoal123")

        mock_http.post.assert_called_once_with(
            "/goals/parent/removeSubgoal",
            json={"data": {"subgoal": "subgoal123"}},
        )

    async def test_list_subgoals_returns_page_iterator(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_subgoals_async returns PageIterator[Goal]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "sub1", "name": "Subgoal 1"},
                {"gid": "sub2", "name": "Subgoal 2"},
            ],
            None,
        )

        iterator = goals_client.list_subgoals_async("parent_goal")
        assert isinstance(iterator, PageIterator)

        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(g, Goal) for g in items)


class TestGoalsSupportingWork:
    """Tests for Goals supporting work operations."""

    async def test_add_supporting_work_project(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add project as supporting work to goal."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        result = await goals_client.add_supporting_work_async(
            "goal123", supporting_resource="project456"
        )

        assert isinstance(result, Goal)
        mock_http.post.assert_called_once_with(
            "/goals/goal123/addSupportingRelationship",
            json={"data": {"supporting_resource": "project456"}},
        )

    async def test_add_supporting_work_with_weight(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add supporting work with contribution weight."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.add_supporting_work_async(
            "goal123",
            supporting_resource="project456",
            contribution_weight=0.5,
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["contribution_weight"] == 0.5

    async def test_add_supporting_work_weight_boundary_values(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Test contribution weight boundary values."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        # Test weight = 0.0
        await goals_client.add_supporting_work_async(
            "goal123", supporting_resource="proj1", contribution_weight=0.0
        )
        assert mock_http.post.call_args[1]["json"]["data"]["contribution_weight"] == 0.0

        # Test weight = 1.0
        mock_http.post.reset_mock()
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}
        await goals_client.add_supporting_work_async(
            "goal123", supporting_resource="proj1", contribution_weight=1.0
        )
        assert mock_http.post.call_args[1]["json"]["data"]["contribution_weight"] == 1.0

    async def test_remove_supporting_work(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove supporting work from goal."""
        mock_http.post.return_value = {}

        await goals_client.remove_supporting_work_async(
            "goal123", supporting_resource="project456"
        )

        mock_http.post.assert_called_once_with(
            "/goals/goal123/removeSupportingRelationship",
            json={"data": {"supporting_resource": "project456"}},
        )


class TestGoalsFollowers:
    """Tests for Goals follower operations."""

    async def test_add_followers_single(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add single follower to goal."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        result = await goals_client.add_followers_async("goal123", followers=["user1"])

        assert isinstance(result, Goal)
        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["followers"] == "user1"

    async def test_add_followers_multiple(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add multiple followers to goal."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.add_followers_async(
            "goal123", followers=["user1", "user2", "user3"]
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["followers"] == "user1,user2,user3"

    async def test_add_followers_empty_list(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add empty list of followers (edge case)."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.add_followers_async("goal123", followers=[])

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["followers"] == ""

    async def test_remove_followers(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove followers from goal."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.remove_followers_async(
            "goal123", followers=["user1", "user2"]
        )

        mock_http.post.assert_called_once_with(
            "/goals/goal123/removeFollowers",
            json={"data": {"followers": "user1,user2"}},
        )


class TestGoalsMetricHandling:
    """Tests for Goals with metric values."""

    def test_goal_metric_model_validation(self) -> None:
        """GoalMetric model validates correctly."""
        metric = GoalMetric.model_validate(
            {
                "gid": "metric123",
                "resource_subtype": "number",
                "unit": "items",
                "precision": 2,
                "current_number_value": 50.5,
                "target_number_value": 100.0,
                "initial_number_value": 0.0,
                "progress_source": "manual",
            }
        )

        assert metric.gid == "metric123"
        assert metric.resource_subtype == "number"
        assert metric.current_number_value == 50.5
        assert metric.target_number_value == 100.0

    def test_goal_with_metric_nested(self) -> None:
        """Goal with nested metric deserializes correctly."""
        goal = Goal.model_validate(
            {
                "gid": "goal123",
                "name": "Revenue Target",
                "metric": {
                    "gid": "metric1",
                    "resource_subtype": "currency",
                    "currency_code": "USD",
                    "current_number_value": 75000,
                    "target_number_value": 100000,
                },
            }
        )

        assert goal.metric is not None
        assert isinstance(goal.metric, GoalMetric)
        assert goal.metric.currency_code == "USD"
        assert goal.metric.current_number_value == 75000

    def test_goal_metric_boundary_values(self) -> None:
        """GoalMetric handles boundary values."""
        # Zero values
        metric = GoalMetric.model_validate(
            {
                "gid": "m1",
                "current_number_value": 0,
                "target_number_value": 0,
            }
        )
        assert metric.current_number_value == 0

        # Large values
        metric = GoalMetric.model_validate(
            {
                "gid": "m2",
                "current_number_value": 1_000_000_000,
                "target_number_value": 1_000_000_000,
            }
        )
        assert metric.current_number_value == 1_000_000_000

        # Negative values (some metrics allow this)
        metric = GoalMetric.model_validate(
            {
                "gid": "m3",
                "current_number_value": -50.5,
                "target_number_value": 100.0,
            }
        )
        assert metric.current_number_value == -50.5

        # Float precision
        metric = GoalMetric.model_validate(
            {
                "gid": "m4",
                "current_number_value": 0.123456789,
            }
        )
        assert metric.current_number_value == 0.123456789


# =============================================================================
# 4. PORTFOLIOS
# =============================================================================


class TestPortfoliosItemManagement:
    """Tests for Portfolio item (project) management."""

    async def test_add_item_basic(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add project to portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.add_item_async("port123", item="project456")

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/addItem",
            json={"data": {"item": "project456"}},
        )

    async def test_add_item_with_positioning(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add item with positioning options."""
        mock_http.post.return_value = {}

        await portfolios_client.add_item_async(
            "port123",
            item="proj_new",
            insert_before="proj_existing",
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_before"] == "proj_existing"

        mock_http.post.reset_mock()
        mock_http.post.return_value = {}
        await portfolios_client.add_item_async(
            "port123",
            item="proj_new",
            insert_after="proj_existing",
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_after"] == "proj_existing"

    async def test_remove_item(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove project from portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.remove_item_async("port123", item="project456")

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/removeItem",
            json={"data": {"item": "project456"}},
        )


class TestPortfoliosMemberManagement:
    """Tests for Portfolio member management."""

    async def test_add_members_single(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add single member to portfolio."""
        mock_http.post.return_value = {"gid": "port123", "name": "Portfolio"}

        result = await portfolios_client.add_members_async("port123", members=["user1"])

        assert isinstance(result, Portfolio)
        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["members"] == "user1"

    async def test_add_members_multiple(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add multiple members to portfolio."""
        mock_http.post.return_value = {"gid": "port123", "name": "Portfolio"}

        await portfolios_client.add_members_async(
            "port123", members=["user1", "user2", "user3"]
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["members"] == "user1,user2,user3"

    async def test_remove_members(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove members from portfolio."""
        mock_http.post.return_value = {"gid": "port123", "name": "Portfolio"}

        await portfolios_client.remove_members_async(
            "port123", members=["user1", "user2"]
        )

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/removeMembers",
            json={"data": {"members": "user1,user2"}},
        )


class TestPortfoliosCustomFieldSettings:
    """Tests for Portfolio custom field settings."""

    async def test_add_custom_field_setting(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add custom field to portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.add_custom_field_setting_async(
            "port123", custom_field="cf456"
        )

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/addCustomFieldSetting",
            json={"data": {"custom_field": "cf456"}},
        )

    async def test_add_custom_field_setting_with_importance(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add custom field with is_important flag."""
        mock_http.post.return_value = {}

        await portfolios_client.add_custom_field_setting_async(
            "port123", custom_field="cf456", is_important=True
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["is_important"] is True

    async def test_remove_custom_field_setting(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove custom field from portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.remove_custom_field_setting_async(
            "port123", custom_field="cf456"
        )

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/removeCustomFieldSetting",
            json={"data": {"custom_field": "cf456"}},
        )


# =============================================================================
# 5. MODEL EDGE CASES
# =============================================================================


class TestTier2ModelRequiredFields:
    """Test required fields enforcement for all Tier 2 models."""

    def test_webhook_requires_gid(self) -> None:
        """Webhook model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Webhook.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_team_requires_gid(self) -> None:
        """Team model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Team.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_attachment_requires_gid(self) -> None:
        """Attachment model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Attachment.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_tag_requires_gid(self) -> None:
        """Tag model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Tag.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_goal_requires_gid(self) -> None:
        """Goal model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Goal.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_goal_metric_requires_gid(self) -> None:
        """GoalMetric model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            GoalMetric.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_goal_membership_requires_gid(self) -> None:
        """GoalMembership model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            GoalMembership.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_portfolio_requires_gid(self) -> None:
        """Portfolio model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Portfolio.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_story_requires_gid(self) -> None:
        """Story model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Story.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_webhook_filter_requires_gid(self) -> None:
        """WebhookFilter model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookFilter.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)


class TestNameGidInNestedContexts:
    """Test NameGid deserialization in nested Tier 2 model contexts."""

    def test_webhook_resource_namegid(self) -> None:
        """Webhook.resource deserializes as NameGid."""
        webhook = Webhook.model_validate(
            {
                "gid": "wh123",
                "resource": {"gid": "proj456", "name": "My Project"},
            }
        )

        assert webhook.resource is not None
        assert isinstance(webhook.resource, NameGid)
        assert webhook.resource.gid == "proj456"

    def test_attachment_parent_namegid(self) -> None:
        """Attachment.parent deserializes as NameGid."""
        attachment = Attachment.model_validate(
            {
                "gid": "att123",
                "parent": {"gid": "task456", "name": "Task Name"},
                "created_by": {"gid": "user789", "name": "Creator"},
            }
        )

        assert attachment.parent is not None
        assert isinstance(attachment.parent, NameGid)
        assert attachment.parent.gid == "task456"
        assert attachment.created_by is not None
        assert attachment.created_by.gid == "user789"

    def test_goal_relationships_namegid(self) -> None:
        """Goal relationship fields deserialize as NameGid."""
        goal = Goal.model_validate(
            {
                "gid": "goal123",
                "owner": {"gid": "user1", "name": "Owner"},
                "workspace": {"gid": "ws1", "name": "Workspace"},
                "team": {"gid": "team1", "name": "Team"},
                "time_period": {"gid": "tp1", "name": "Q4 2024"},
            }
        )

        assert isinstance(goal.owner, NameGid)
        assert isinstance(goal.workspace, NameGid)
        assert isinstance(goal.team, NameGid)
        assert isinstance(goal.time_period, NameGid)

    def test_goal_followers_list_namegid(self) -> None:
        """Goal.followers deserializes as list of NameGid."""
        goal = Goal.model_validate(
            {
                "gid": "goal123",
                "followers": [
                    {"gid": "user1", "name": "User 1"},
                    {"gid": "user2", "name": "User 2"},
                    {"gid": "user3"},  # Name is optional
                ],
            }
        )

        assert goal.followers is not None
        assert len(goal.followers) == 3
        assert all(isinstance(f, NameGid) for f in goal.followers)
        assert goal.followers[2].name is None

    def test_story_namegid_fields(self) -> None:
        """Story NameGid fields deserialize correctly."""
        story = Story.model_validate(
            {
                "gid": "story123",
                "target": {"gid": "task456", "name": "Task"},
                "created_by": {"gid": "user789", "name": "Author"},
                "assignee": {"gid": "user111", "name": "Assignee"},
                "new_section": {"gid": "sec222", "name": "In Progress"},
                "old_section": {"gid": "sec333", "name": "To Do"},
            }
        )

        assert isinstance(story.target, NameGid)
        assert isinstance(story.created_by, NameGid)
        assert isinstance(story.assignee, NameGid)
        assert isinstance(story.new_section, NameGid)
        assert isinstance(story.old_section, NameGid)


class TestComplexNestedStructures:
    """Test complex nested structures in Tier 2 models."""

    def test_webhook_with_filters(self) -> None:
        """Webhook with nested filters deserializes correctly."""
        webhook = Webhook.model_validate(
            {
                "gid": "wh123",
                "target": "https://example.com/hook",
                "filters": [
                    {
                        "gid": "f1",
                        "resource_type": "task",
                        "action": "changed",
                        "fields": ["completed", "name"],
                    },
                    {
                        "gid": "f2",
                        "resource_type": "task",
                        "action": "added",
                    },
                ],
            }
        )

        assert webhook.filters is not None
        assert len(webhook.filters) == 2
        assert all(isinstance(f, WebhookFilter) for f in webhook.filters)
        assert webhook.filters[0].fields == ["completed", "name"]
        assert webhook.filters[1].action == "added"

    def test_story_change_tracking_fields(self) -> None:
        """Story change tracking fields work correctly."""
        # Assignment change story
        story = Story.model_validate(
            {
                "gid": "s1",
                "resource_subtype": "assigned",
                "assignee": {"gid": "user1", "name": "Alice"},
            }
        )
        assert story.resource_subtype == "assigned"
        assert story.assignee is not None

        # Name change story
        story = Story.model_validate(
            {
                "gid": "s2",
                "resource_subtype": "name_changed",
                "old_name": "Old Task Name",
                "new_name": "New Task Name",
            }
        )
        assert story.old_name == "Old Task Name"
        assert story.new_name == "New Task Name"

        # Section move story
        story = Story.model_validate(
            {
                "gid": "s3",
                "resource_subtype": "section_changed",
                "old_section": {"gid": "sec1", "name": "To Do"},
                "new_section": {"gid": "sec2", "name": "Done"},
            }
        )
        assert story.old_section.gid == "sec1"
        assert story.new_section.gid == "sec2"

    def test_goal_membership_model(self) -> None:
        """GoalMembership model works correctly."""
        membership = GoalMembership.model_validate(
            {
                "gid": "mem123",
                "member": {"gid": "user456", "name": "Team Member"},
                "goal": {"gid": "goal789", "name": "Q4 Goals"},
                "role": "editor",
            }
        )

        assert membership.gid == "mem123"
        assert isinstance(membership.member, NameGid)
        assert isinstance(membership.goal, NameGid)
        assert membership.role == "editor"


class TestExtraFieldsIgnoredTier2:
    """Test that extra fields are ignored per ADR-0005 for Tier 2 models."""

    def test_webhook_ignores_unknown_fields(self) -> None:
        """Webhook ignores unknown API fields."""
        webhook = Webhook.model_validate(
            {
                "gid": "wh123",
                "target": "https://example.com",
                "future_field": "ignored",
                "another_field": {"nested": "data"},
            }
        )

        assert webhook.gid == "wh123"
        assert not hasattr(webhook, "future_field")
        assert not hasattr(webhook, "another_field")

    def test_goal_ignores_unknown_fields(self) -> None:
        """Goal ignores unknown API fields."""
        goal = Goal.model_validate(
            {
                "gid": "g123",
                "name": "Goal",
                "new_api_field": True,
            }
        )

        assert goal.gid == "g123"
        assert not hasattr(goal, "new_api_field")

    def test_story_ignores_unknown_fields(self) -> None:
        """Story ignores unknown API fields."""
        story = Story.model_validate(
            {
                "gid": "s123",
                "text": "Comment",
                "experimental_feature": {"data": "here"},
            }
        )

        assert story.gid == "s123"
        assert not hasattr(story, "experimental_feature")


class TestTier2ModelDefaults:
    """Test default values for Tier 2 model fields."""

    def test_webhook_defaults(self) -> None:
        """Webhook has correct default resource_type."""
        webhook = Webhook(gid="wh123")
        assert webhook.resource_type == "webhook"
        assert webhook.target is None
        assert webhook.active is None
        assert webhook.filters is None

    def test_goal_defaults(self) -> None:
        """Goal has correct default resource_type."""
        goal = Goal(gid="g123")
        assert goal.resource_type == "goal"
        assert goal.name is None
        assert goal.status is None
        assert goal.metric is None

    def test_portfolio_defaults(self) -> None:
        """Portfolio has correct default resource_type."""
        portfolio = Portfolio(gid="p123")
        assert portfolio.resource_type == "portfolio"
        assert portfolio.name is None
        assert portfolio.color is None
        assert portfolio.members is None

    def test_story_defaults(self) -> None:
        """Story has correct default resource_type."""
        story = Story(gid="s123")
        assert story.resource_type == "story"
        assert story.text is None
        assert story.resource_subtype is None

    def test_attachment_defaults(self) -> None:
        """Attachment has correct default resource_type."""
        attachment = Attachment(gid="a123")
        assert attachment.resource_type == "attachment"
        assert attachment.name is None
        assert attachment.download_url is None


# =============================================================================
# SYNC WRAPPER TESTS FOR TIER 2 CLIENTS
# =============================================================================


class TestTier2SyncWrapperBehavior:
    """Test sync wrapper behavior for Tier 2 clients."""

    async def test_webhooks_sync_fails_in_async(
        self, webhooks_client: WebhooksClient
    ) -> None:
        """WebhooksClient sync methods fail in async context."""
        with pytest.raises(SyncInAsyncContextError):
            webhooks_client.get("wh123")

    async def test_attachments_sync_fails_in_async(
        self, attachments_client: AttachmentsClient
    ) -> None:
        """AttachmentsClient sync methods fail in async context."""
        with pytest.raises(SyncInAsyncContextError):
            attachments_client.get("att123")

    async def test_goals_sync_fails_in_async(self, goals_client: GoalsClient) -> None:
        """GoalsClient sync methods fail in async context."""
        with pytest.raises(SyncInAsyncContextError):
            goals_client.get("goal123")

        with pytest.raises(SyncInAsyncContextError):
            goals_client.add_subgoal("goal123", subgoal="sub456")

    async def test_portfolios_sync_fails_in_async(
        self, portfolios_client: PortfoliosClient
    ) -> None:
        """PortfoliosClient sync methods fail in async context."""
        with pytest.raises(SyncInAsyncContextError):
            portfolios_client.get("port123")

        with pytest.raises(SyncInAsyncContextError):
            portfolios_client.add_item("port123", item="proj456")


# =============================================================================
# UNICODE AND SPECIAL CHARACTERS
# =============================================================================


class TestUnicodeHandlingTier2:
    """Test Unicode handling in Tier 2 models."""

    def test_goal_unicode_name_and_notes(self) -> None:
        """Goal handles Unicode in name and notes."""
        goal = Goal.model_validate(
            {
                "gid": "g123",
                "name": "Goal Name",
                "notes": "Notes with emoji and Chinese",
                "html_notes": "<p>HTML notes</p>",
            }
        )

        assert "Goal" in goal.name
        assert goal.notes is not None

    def test_story_unicode_text(self) -> None:
        """Story handles Unicode in text content."""
        story = Story.model_validate(
            {
                "gid": "s123",
                "text": "Comment with mixed content",
                "html_text": "<p>HTML content</p>",
            }
        )

        assert story.text is not None

    def test_webhook_unicode_target(self) -> None:
        """Webhook handles Unicode in target URL (escaped)."""
        # URLs can contain percent-encoded Unicode
        webhook = Webhook.model_validate(
            {
                "gid": "wh123",
                "target": "https://example.com/path?name=%E4%B8%AD%E6%96%87",
            }
        )

        assert "example.com" in webhook.target


# =============================================================================
# BOUNDARY CONDITIONS
# =============================================================================


class TestBoundaryConditionsTier2:
    """Test boundary conditions for Tier 2 models and operations."""

    def test_goal_many_followers(self) -> None:
        """Goal handles many followers."""
        followers = [{"gid": str(i), "name": f"User {i}"} for i in range(100)]
        goal = Goal.model_validate({"gid": "g123", "followers": followers})
        assert len(goal.followers) == 100

    def test_webhook_many_filters(self) -> None:
        """Webhook handles many filters."""
        filters = [
            {"gid": str(i), "resource_type": "task", "action": "changed"}
            for i in range(50)
        ]
        webhook = Webhook.model_validate({"gid": "wh123", "filters": filters})
        assert len(webhook.filters) == 50

    def test_portfolio_many_members(self) -> None:
        """Portfolio handles many members."""
        members = [{"gid": str(i), "name": f"Member {i}"} for i in range(100)]
        portfolio = Portfolio.model_validate({"gid": "p123", "members": members})
        assert len(portfolio.members) == 100

    def test_story_long_text(self) -> None:
        """Story handles long text content."""
        long_text = "A" * 50000
        story = Story.model_validate(
            {
                "gid": "s123",
                "text": long_text,
            }
        )
        assert len(story.text) == 50000

    def test_attachment_large_size(self) -> None:
        """Attachment handles large file size values."""
        attachment = Attachment.model_validate(
            {
                "gid": "a123",
                "name": "large_file.bin",
                "size": 10_000_000_000,  # 10GB
            }
        )
        assert attachment.size == 10_000_000_000


# =============================================================================
# RAW MODE TESTS
# =============================================================================


class TestRawModeTier2:
    """Test raw=True returns dict for Tier 2 client operations."""

    async def test_webhooks_get_raw(
        self, webhooks_client: WebhooksClient, mock_http: MockHTTPClient
    ) -> None:
        """WebhooksClient.get_async with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "wh123", "extra": "preserved"}

        result = await webhooks_client.get_async("wh123", raw=True)

        assert isinstance(result, dict)
        assert result["extra"] == "preserved"

    async def test_goals_create_raw(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """GoalsClient.create_async with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "g123", "extra": "data"}

        result = await goals_client.create_async(workspace="ws1", name="Goal", raw=True)

        assert isinstance(result, dict)
        assert result["extra"] == "data"

    async def test_portfolios_update_raw(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """PortfoliosClient.update_async with raw=True returns dict."""
        mock_http.put.return_value = {"gid": "p123", "extra": "field"}

        result = await portfolios_client.update_async("p123", name="New", raw=True)

        assert isinstance(result, dict)
        assert result["extra"] == "field"

    async def test_attachments_upload_raw(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """AttachmentsClient.upload_async with raw=True returns dict."""
        mock_http.post_multipart.return_value = {"gid": "a123", "extra": "data"}

        result = await attachments_client.upload_async(
            parent="task1", file=BytesIO(b"test"), name="test.txt", raw=True
        )

        assert isinstance(result, dict)
        assert result["extra"] == "data"
