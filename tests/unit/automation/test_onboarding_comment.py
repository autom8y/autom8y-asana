"""Unit tests for onboarding comment creation in PipelineConversionRule.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT Phase 3: Test onboarding comment creation.
Per FR-COMMENT-001 through FR-COMMENT-005: Comment creation requirements.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.models.business.process import ProcessType


class MockTask:
    """Mock Task for testing."""

    def __init__(self, gid: str = "new_task_123") -> None:
        self.gid = gid


class MockMembership:
    """Mock membership for testing."""

    def __init__(self, project_gid: str) -> None:
        self.project = MagicMock()
        self.project.gid = project_gid


class MockProcess:
    """Mock Process entity for testing."""

    def __init__(
        self,
        gid: str = "process_123",
        name: str | None = "Test Process",
        process_type: ProcessType = ProcessType.SALES,
        memberships: list[Any] | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.process_type = process_type
        self.memberships = memberships or []


class MockBusiness:
    """Mock Business entity for testing."""

    def __init__(self, name: str = "Test Business") -> None:
        self.gid = "business_123"
        self.name = name


class TestCreateOnboardingCommentAsync:
    """Tests for _create_onboarding_comment_async method."""

    @pytest.fixture
    def rule(self) -> PipelineConversionRule:
        """Create a PipelineConversionRule for testing."""
        return PipelineConversionRule()

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with stories.create_comment_async."""
        client = MagicMock()
        client.stories = MagicMock()
        client.stories.create_comment_async = AsyncMock(return_value=MagicMock())
        return client

    @pytest.mark.asyncio
    async def test_comment_created_successfully(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-COMMENT-001: Comment added to new Process."""
        new_task = MockTask("new_task_gid")
        source_process = MockProcess(name="Sales Lead")
        business = MockBusiness(name="Acme Corp")

        result = await rule._create_onboarding_comment_async(
            new_task=new_task,
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
            target_project_gid="onboarding_project_123",
            client=mock_client,
        )

        assert result is True
        mock_client.stories.create_comment_async.assert_called_once()
        call_kwargs = mock_client.stories.create_comment_async.call_args.kwargs
        assert call_kwargs["task"] == "new_task_gid"
        assert "text" in call_kwargs

    @pytest.mark.asyncio
    async def test_comment_includes_source_name_and_type_and_date(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-COMMENT-002: Include ProcessType, source name, date."""
        new_task = MockTask("new_task_gid")
        source_process = MockProcess(name="Sales Lead")
        business = MockBusiness(name="Acme Corp")

        await rule._create_onboarding_comment_async(
            new_task=new_task,
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
            target_project_gid="onboarding_project_123",
            client=mock_client,
        )

        call_kwargs = mock_client.stories.create_comment_async.call_args.kwargs
        comment_text = call_kwargs["text"]

        # Check ProcessType is included
        assert "Onboarding" in comment_text

        # Check source name is included
        assert "Sales Lead" in comment_text

        # Check date is included (format: YYYY-MM-DD)
        today = date.today().isoformat()
        assert today in comment_text

    @pytest.mark.asyncio
    async def test_comment_includes_asana_link(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-COMMENT-003: Include link to source Process."""
        new_task = MockTask("new_task_gid")
        # Create process with membership to get project GID
        source_process = MockProcess(
            gid="source_process_gid",
            name="Sales Lead",
            memberships=[MockMembership("source_project_gid")],
        )
        business = MockBusiness(name="Acme Corp")

        await rule._create_onboarding_comment_async(
            new_task=new_task,
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
            target_project_gid="onboarding_project_123",
            client=mock_client,
        )

        call_kwargs = mock_client.stories.create_comment_async.call_args.kwargs
        comment_text = call_kwargs["text"]

        # Check link format
        assert "https://app.asana.com/0/source_project_gid/source_process_gid" in comment_text

    @pytest.mark.asyncio
    async def test_create_comment_async_fails_returns_false_gracefully(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test FR-COMMENT-005: Failure doesn't stop conversion."""
        mock_client.stories.create_comment_async = AsyncMock(
            side_effect=ConnectionError("API Error: Story creation failed")
        )
        new_task = MockTask("new_task_gid")
        source_process = MockProcess(name="Sales Lead")
        business = MockBusiness(name="Acme Corp")

        result = await rule._create_onboarding_comment_async(
            new_task=new_task,
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
            target_project_gid="onboarding_project_123",
            client=mock_client,
        )

        # Should return False (graceful degradation), not raise
        assert result is False
        mock_client.stories.create_comment_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_comment_includes_business_name(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test that comment includes business name."""
        new_task = MockTask("new_task_gid")
        source_process = MockProcess(name="Sales Lead")
        business = MockBusiness(name="Acme Corp")

        await rule._create_onboarding_comment_async(
            new_task=new_task,
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
            target_project_gid="onboarding_project_123",
            client=mock_client,
        )

        call_kwargs = mock_client.stories.create_comment_async.call_args.kwargs
        comment_text = call_kwargs["text"]

        assert "Acme Corp" in comment_text

    @pytest.mark.asyncio
    async def test_comment_with_none_business_uses_unknown(
        self, rule: PipelineConversionRule, mock_client: MagicMock
    ) -> None:
        """Test that comment uses 'Unknown' for business when None."""
        new_task = MockTask("new_task_gid")
        source_process = MockProcess(name="Sales Lead")

        await rule._create_onboarding_comment_async(
            new_task=new_task,
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=None,
            target_project_gid="onboarding_project_123",
            client=mock_client,
        )

        call_kwargs = mock_client.stories.create_comment_async.call_args.kwargs
        comment_text = call_kwargs["text"]

        assert "Unknown" in comment_text


class TestBuildOnboardingComment:
    """Tests for _build_onboarding_comment method."""

    @pytest.fixture
    def rule(self) -> PipelineConversionRule:
        """Create a PipelineConversionRule for testing."""
        return PipelineConversionRule()

    def test_template_formatting_correct(self, rule: PipelineConversionRule) -> None:
        """Test that comment template is correctly formatted."""
        source_process = MockProcess(
            gid="source_123",
            name="Sales Lead",
            memberships=[{"project": {"gid": "project_456"}}],
        )
        business = MockBusiness(name="Acme Corp")

        comment = rule._build_onboarding_comment(
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
        )

        # Check overall structure
        assert "Pipeline Conversion" in comment
        assert "automatically created" in comment
        assert "was converted on" in comment
        assert "Source:" in comment
        assert "Business:" in comment

    def test_uses_unknown_for_missing_source_name(self, rule: PipelineConversionRule) -> None:
        """Test that 'Unknown' is used when source process name is None."""
        source_process = MockProcess(
            gid="source_123",
            name=None,
        )
        business = MockBusiness(name="Acme Corp")

        comment = rule._build_onboarding_comment(
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
        )

        assert '"Unknown"' in comment

    def test_handles_dict_style_memberships(self, rule: PipelineConversionRule) -> None:
        """Test handling of dict-style memberships (API response format)."""
        source_process = MockProcess(
            gid="source_123",
            name="Sales Lead",
            memberships=[{"project": {"gid": "project_456", "name": "Sales Project"}}],
        )
        business = MockBusiness(name="Acme Corp")

        comment = rule._build_onboarding_comment(
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
        )

        assert "https://app.asana.com/0/project_456/source_123" in comment

    def test_fallback_project_gid_for_no_memberships(self, rule: PipelineConversionRule) -> None:
        """Test that fallback '0' is used when no memberships available."""
        source_process = MockProcess(
            gid="source_123",
            name="Sales Lead",
            memberships=[],
        )
        business = MockBusiness(name="Acme Corp")

        comment = rule._build_onboarding_comment(
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
        )

        # Should use fallback '0' for project GID
        assert "https://app.asana.com/0/0/source_123" in comment

    def test_different_process_types(self, rule: PipelineConversionRule) -> None:
        """Test that different process types are correctly represented."""
        source_process = MockProcess(gid="source_123", name="Sales Lead")
        business = MockBusiness(name="Acme Corp")

        # Test ONBOARDING
        comment = rule._build_onboarding_comment(
            source_process=source_process,
            target_process_type=ProcessType.ONBOARDING,
            business=business,
        )
        assert "Onboarding process" in comment

        # Test IMPLEMENTATION
        comment = rule._build_onboarding_comment(
            source_process=source_process,
            target_process_type=ProcessType.IMPLEMENTATION,
            business=business,
        )
        assert "Implementation process" in comment
