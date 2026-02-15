"""Tests for init action handlers.

Per TDD Section 2.9: Comprehensive tests for all 6 handler types covering
happy paths, edge cases, error handling, and the handler registry.

All handlers accept (ctx, created_entity_gid, action_config, source_process)
per the updated signature contract.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lifecycle.config import InitActionConfig
from autom8_asana.lifecycle.creation import CreationResult
from autom8_asana.lifecycle.init_actions import (
    HANDLER_REGISTRY,
    CampaignHandler,
    CommentHandler,
    EntityCreationHandler,
    PlayCreationHandler,
    ProductsCheckHandler,
)

# -----------------------------------------------------------------------
# CommentHandler
# -----------------------------------------------------------------------


class TestCommentHandler:
    """Tests for CommentHandler (create_comment action type)."""

    @pytest.mark.asyncio
    async def test_comment_contains_source_link(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment text includes Asana deep link to source process."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        call_kwargs = mock_client.stories.create_comment_async.call_args
        comment_text = call_kwargs.kwargs["text"]

        # Source link uses project GID from memberships + process GID
        assert "https://app.asana.com/0/" in comment_text
        assert mock_process.gid in comment_text

    @pytest.mark.asyncio
    async def test_comment_contains_business_name(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment text includes business name."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        call_kwargs = mock_client.stories.create_comment_async.call_args
        comment_text = call_kwargs.kwargs["text"]
        assert "Test Business" in comment_text

    @pytest.mark.asyncio
    async def test_comment_contains_today_date(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment text includes today's date in ISO format."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        call_kwargs = mock_client.stories.create_comment_async.call_args
        comment_text = call_kwargs.kwargs["text"]
        assert date.today().isoformat() in comment_text

    @pytest.mark.asyncio
    async def test_comment_contains_source_name(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment text includes the source process name."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        call_kwargs = mock_client.stories.create_comment_async.call_args
        comment_text = call_kwargs.kwargs["text"]
        assert "Test Process" in comment_text

    @pytest.mark.asyncio
    async def test_comment_contains_pipeline_conversion_header(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment text starts with Pipeline Conversion header."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        call_kwargs = mock_client.stories.create_comment_async.call_args
        comment_text = call_kwargs.kwargs["text"]
        assert comment_text.startswith("Pipeline Conversion")

    @pytest.mark.asyncio
    async def test_comment_soft_fail_on_error(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment handler returns success=True even when API fails."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock(
            side_effect=ConnectionError("API down")
        )

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        # Soft-fail: success is True despite the error
        assert result.success is True
        assert result.entity_gid == ""

    @pytest.mark.asyncio
    async def test_comment_called_with_correct_task_gid(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Comment is created on the correct task (created_entity_gid)."""
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        await handler.execute_async(
            mock_resolution_context,
            "target_task_999",
            action_config,
            mock_process,
        )

        call_kwargs = mock_client.stories.create_comment_async.call_args
        assert call_kwargs.kwargs["task"] == "target_task_999"

    @pytest.mark.asyncio
    async def test_comment_source_with_no_memberships(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When source has no memberships, uses '0' as project GID."""
        mock_process.memberships = []
        handler = CommentHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="create_comment")

        mock_client.stories = MagicMock()
        mock_client.stories.create_comment_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        call_kwargs = mock_client.stories.create_comment_async.call_args
        comment_text = call_kwargs.kwargs["text"]
        assert "https://app.asana.com/0/0/" in comment_text


# -----------------------------------------------------------------------
# EntityCreationHandler
# -----------------------------------------------------------------------


class TestEntityCreationHandler:
    """Tests for EntityCreationHandler (entity_creation action type)."""

    @pytest.mark.asyncio
    async def test_entity_creation_delegates_to_creation_service(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Handler delegates to EntityCreationService.create_entity_async."""
        handler = EntityCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="entity_creation",
            entity_type="asset_edit",
            project_gid="1203992664400125",
            holder_type="asset_edit_holder",
        )

        expected_result = CreationResult(success=True, entity_gid="new_entity_123")

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(return_value=expected_result)

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is True
            assert result.entity_gid == "new_entity_123"
            mock_service.create_entity_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_creation_passes_correct_params(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Handler passes project_gid, holder_type, and stage_config."""
        handler = EntityCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="entity_creation",
            entity_type="asset_edit",
            project_gid="proj_gid_123",
            holder_type="asset_edit_holder",
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(
                return_value=CreationResult(success=True, entity_gid="e1")
            )

            await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            call_kwargs = mock_service.create_entity_async.call_args.kwargs
            assert call_kwargs["project_gid"] == "proj_gid_123"
            assert call_kwargs["holder_type"] == "asset_edit_holder"
            assert call_kwargs["template_section"] == "TEMPLATE"
            assert call_kwargs["ctx"] is mock_resolution_context
            assert call_kwargs["source_process"] is mock_process

    @pytest.mark.asyncio
    async def test_entity_creation_default_holder_type(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """When holder_type not specified, defaults to asset_edit_holder."""
        handler = EntityCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="entity_creation",
            entity_type="asset_edit",
            project_gid="proj_123",
            # holder_type omitted
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(
                return_value=CreationResult(success=True, entity_gid="e1")
            )

            await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            call_kwargs = mock_service.create_entity_async.call_args.kwargs
            assert call_kwargs["holder_type"] == "asset_edit_holder"

    @pytest.mark.asyncio
    async def test_entity_creation_returns_service_result(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Handler returns the CreationResult from the service directly."""
        handler = EntityCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="entity_creation",
            entity_type="asset_edit",
            project_gid="proj_123",
        )

        service_result = CreationResult(
            success=True,
            entity_gid="entity_456",
            entity_name="Asset Edit - Test",
            fields_seeded=["field1"],
            warnings=["some warning"],
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(return_value=service_result)

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result is service_result

    @pytest.mark.asyncio
    async def test_entity_creation_handles_exception(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Handler catches exceptions and returns failure result."""
        handler = EntityCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="entity_creation",
            entity_type="asset_edit",
            project_gid="proj_123",
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(
                side_effect=ConnectionError("Service unavailable")
            )

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is False
            assert "Service unavailable" in result.error

    @pytest.mark.asyncio
    async def test_entity_creation_no_stage_config(
        self,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Handler returns failure when stage config not found."""
        # Use a config with no stages
        config = MagicMock()
        config.get_stage = MagicMock(return_value=None)

        handler = EntityCreationHandler(mock_client, config)
        action_config = InitActionConfig(
            type="entity_creation",
            entity_type="asset_edit",
            project_gid="proj_123",
        )

        result = await handler.execute_async(
            mock_resolution_context,
            "created123",
            action_config,
            mock_process,
        )

        assert result.success is False
        assert "No stage config" in result.error


# -----------------------------------------------------------------------
# ProductsCheckHandler
# -----------------------------------------------------------------------


class TestProductsCheckHandler:
    """Tests for ProductsCheckHandler (products_check action type)."""

    @pytest.mark.asyncio
    async def test_video_match_creates_entity(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When products match video*, creates entity via service."""
        mock_business.products = ["video_production", "photography"]
        handler = ProductsCheckHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
        )

        expected_result = CreationResult(success=True, entity_gid="videographer_123")

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(return_value=expected_result)

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is True
            assert result.entity_gid == "videographer_123"
            mock_service.create_entity_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_video_match_uses_videography_holder(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When no holder_type specified, defaults to videography_holder."""
        mock_business.products = ["video_editing"]
        handler = ProductsCheckHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
            # project_gid and holder_type omitted -- use defaults
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(
                return_value=CreationResult(success=True, entity_gid="v1")
            )

            await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            call_kwargs = mock_service.create_entity_async.call_args.kwargs
            assert call_kwargs["holder_type"] == "videography_holder"
            # Falls back to VIDEOGRAPHY_HOLDER_PROJECT constant
            assert call_kwargs["project_gid"] == "1207984018149338"

    @pytest.mark.asyncio
    async def test_no_match_returns_success(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When no products match, returns success with no entity created."""
        mock_business.products = ["photography", "design"]
        handler = ProductsCheckHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
        )

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        assert result.entity_gid == ""

    @pytest.mark.asyncio
    async def test_no_products_returns_success(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When business has no products field, returns success."""
        mock_business.products = None
        handler = ProductsCheckHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
        )

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        assert result.entity_gid == ""

    @pytest.mark.asyncio
    async def test_string_products_match(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Products as a single string (not list) are also matched."""
        mock_business.products = "video_editing"
        handler = ProductsCheckHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(
                return_value=CreationResult(success=True, entity_gid="v1")
            )

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is True
            mock_service.create_entity_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_products_check_exception_handling(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Handler catches exceptions and returns failure."""
        mock_business.products = ["video_production"]
        handler = ProductsCheckHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
        )

        with patch(
            "autom8_asana.lifecycle.creation.EntityCreationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.create_entity_async = AsyncMock(
                side_effect=ConnectionError("Network failure")
            )

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is False
            assert "Network failure" in result.error

    @pytest.mark.asyncio
    async def test_products_check_no_stage_config(
        self,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Returns failure when stage config not found for process type."""
        mock_business.products = ["video_production"]
        config = MagicMock()
        config.get_stage = MagicMock(return_value=None)

        handler = ProductsCheckHandler(mock_client, config)
        action_config = InitActionConfig(
            type="products_check",
            condition="video*",
            action="request_source_videographer",
        )

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is False
        assert "No stage config" in result.error


# -----------------------------------------------------------------------
# PlayCreationHandler
# -----------------------------------------------------------------------


class TestPlayCreationHandler:
    """Tests for PlayCreationHandler (play_creation action type)."""

    @pytest.mark.asyncio
    async def test_play_creation_success(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Test successful play creation with template."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
        )

        # Mock task with no dependencies
        mock_task = MagicMock()
        mock_task.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        # Mock template discovery
        mock_template = MagicMock()
        mock_template.gid = "template123"
        with patch(
            "autom8_asana.automation.templates.TemplateDiscovery"
        ) as MockDiscovery:
            mock_discovery = MockDiscovery.return_value
            mock_discovery.find_template_task_async = AsyncMock(
                return_value=mock_template
            )

            # Mock duplicate
            mock_play = MagicMock()
            mock_play.gid = "play123"
            mock_client.tasks.duplicate_async = AsyncMock(return_value=mock_play)
            mock_client.tasks.add_to_project_async = AsyncMock()
            mock_client.tasks.add_dependencies_async = AsyncMock()

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is True
            assert result.entity_gid == "play123"
            mock_client.tasks.duplicate_async.assert_called_once()
            mock_client.tasks.add_dependencies_async.assert_called_once_with(
                "created123", ["play123"]
            )

    @pytest.mark.asyncio
    async def test_play_creation_already_linked(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Test play creation when already linked as dependency."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
        )

        # Mock task with existing dependency
        mock_dep = MagicMock()
        mock_dep.gid = "dep123"
        mock_task = MagicMock()
        mock_task.dependencies = [mock_dep]

        # Mock dependency task in play project
        mock_dep_task = MagicMock()
        mock_dep_task.memberships = [
            {"project": {"gid": "1207507299545000", "name": "Plays"}}
        ]

        async def mock_get_async(gid, opt_fields=None):
            if gid == "created123":
                return mock_task
            elif gid == "dep123":
                return mock_dep_task
            return MagicMock()

        mock_client.tasks.get_async = mock_get_async

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        assert result.entity_gid == "dep123"

    @pytest.mark.asyncio
    async def test_play_creation_no_template(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Test play creation when template not found."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
        )

        # Mock task with no dependencies
        mock_task = MagicMock()
        mock_task.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        with patch(
            "autom8_asana.automation.templates.TemplateDiscovery"
        ) as MockDiscovery:
            mock_discovery = MockDiscovery.return_value
            mock_discovery.find_template_task_async = AsyncMock(return_value=None)

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is False
            assert "No play template" in result.error

    @pytest.mark.asyncio
    async def test_play_creation_exception(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Test play creation handler exception handling."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
        )

        mock_client.tasks.get_async = AsyncMock(
            side_effect=ConnectionError("Network error")
        )

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is False
        assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_play_reopen_within_threshold(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Test reopen-or-create: reopens play completed within threshold."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
            reopen_if_completed_within_days=90,
        )

        # No existing dependencies
        mock_task = MagicMock()
        mock_task.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        # Search returns a completed play
        mock_completed_play = MagicMock()
        mock_completed_play.gid = "reopened_play_456"

        mock_search_result = AsyncMock()
        mock_search_result.collect = AsyncMock(return_value=[mock_completed_play])
        mock_client.tasks.search_async = AsyncMock(return_value=mock_search_result)
        mock_client.tasks.update_async = AsyncMock()
        mock_client.tasks.add_dependencies_async = AsyncMock()

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True
        assert result.entity_gid == "reopened_play_456"
        assert result.was_reopened is True

        # Verify it was reopened (marked incomplete)
        mock_client.tasks.update_async.assert_called_once_with(
            "reopened_play_456", completed=False
        )
        # Verify dependency wiring
        mock_client.tasks.add_dependencies_async.assert_called_once_with(
            "created123", ["reopened_play_456"]
        )

    @pytest.mark.asyncio
    async def test_play_create_new_when_outside_threshold(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When no plays found within threshold, creates a new one."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
            reopen_if_completed_within_days=90,
        )

        # No existing dependencies
        mock_task = MagicMock()
        mock_task.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        # Search returns empty (no plays within threshold)
        mock_search_result = AsyncMock()
        mock_search_result.collect = AsyncMock(return_value=[])
        mock_client.tasks.search_async = AsyncMock(return_value=mock_search_result)

        # Template discovery for new creation
        mock_template = MagicMock()
        mock_template.gid = "template123"
        with patch(
            "autom8_asana.automation.templates.TemplateDiscovery"
        ) as MockDiscovery:
            mock_discovery = MockDiscovery.return_value
            mock_discovery.find_template_task_async = AsyncMock(
                return_value=mock_template
            )

            mock_play = MagicMock()
            mock_play.gid = "new_play_789"
            mock_client.tasks.duplicate_async = AsyncMock(return_value=mock_play)
            mock_client.tasks.add_to_project_async = AsyncMock()
            mock_client.tasks.add_dependencies_async = AsyncMock()

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is True
            assert result.entity_gid == "new_play_789"
            assert result.was_reopened is not True
            mock_client.tasks.duplicate_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_reopen_failure_falls_through_to_create(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When reopen search fails, falls through to create new play."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
            reopen_if_completed_within_days=90,
        )

        # No existing dependencies
        mock_task = MagicMock()
        mock_task.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        # Search raises an error
        mock_client.tasks.search_async = AsyncMock(
            side_effect=ConnectionError("Search API down")
        )

        # Template discovery for new creation
        mock_template = MagicMock()
        mock_template.gid = "template123"
        with patch(
            "autom8_asana.automation.templates.TemplateDiscovery"
        ) as MockDiscovery:
            mock_discovery = MockDiscovery.return_value
            mock_discovery.find_template_task_async = AsyncMock(
                return_value=mock_template
            )

            mock_play = MagicMock()
            mock_play.gid = "fallback_play"
            mock_client.tasks.duplicate_async = AsyncMock(return_value=mock_play)
            mock_client.tasks.add_to_project_async = AsyncMock()
            mock_client.tasks.add_dependencies_async = AsyncMock()

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            # Should still succeed via create-new path
            assert result.success is True
            assert result.entity_gid == "fallback_play"

    @pytest.mark.asyncio
    async def test_play_no_reopen_threshold_creates_directly(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """When reopen_if_completed_within_days is None, skips reopen check."""
        handler = PlayCreationHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(
            type="play_creation",
            play_type="backend_onboard_a_business",
            project_gid="1207507299545000",
            condition="not_already_linked",
            # reopen_if_completed_within_days=None (default)
        )

        # No existing dependencies
        mock_task = MagicMock()
        mock_task.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        # Template discovery
        mock_template = MagicMock()
        mock_template.gid = "template123"
        with patch(
            "autom8_asana.automation.templates.TemplateDiscovery"
        ) as MockDiscovery:
            mock_discovery = MockDiscovery.return_value
            mock_discovery.find_template_task_async = AsyncMock(
                return_value=mock_template
            )

            mock_play = MagicMock()
            mock_play.gid = "direct_play"
            mock_client.tasks.duplicate_async = AsyncMock(return_value=mock_play)
            mock_client.tasks.add_to_project_async = AsyncMock()
            mock_client.tasks.add_dependencies_async = AsyncMock()

            result = await handler.execute_async(
                mock_resolution_context,
                "created123",
                action_config,
                mock_process,
            )

            assert result.success is True
            assert result.entity_gid == "direct_play"
            # No search_async call should have been made
            assert (
                not hasattr(mock_client.tasks, "search_async")
                or not mock_client.tasks.search_async.called
            )


# -----------------------------------------------------------------------
# CampaignHandler
# -----------------------------------------------------------------------


class TestCampaignHandler:
    """Tests for CampaignHandler (activate/deactivate campaign types)."""

    @pytest.mark.asyncio
    async def test_campaign_activate(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Test campaign activation handler logs and returns success."""
        handler = CampaignHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="activate_campaign")

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_campaign_deactivate(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_business,
        mock_process,
    ):
        """Test campaign deactivation handler logs and returns success."""
        handler = CampaignHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="deactivate_campaign")

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_campaign_handler_exception(
        self,
        lifecycle_config,
        mock_client,
        mock_resolution_context,
        mock_process,
    ):
        """Test campaign handler catches exceptions."""
        handler = CampaignHandler(mock_client, lifecycle_config)
        action_config = InitActionConfig(type="activate_campaign")

        # Make business_async raise
        mock_resolution_context.business_async = AsyncMock(
            side_effect=ConnectionError("Context failure")
        )

        result = await handler.execute_async(
            mock_resolution_context, "created123", action_config, mock_process
        )

        assert result.success is False
        assert "Context failure" in result.error


# -----------------------------------------------------------------------
# Handler Registry
# -----------------------------------------------------------------------


class TestHandlerRegistry:
    """Tests for HANDLER_REGISTRY completeness."""

    def test_registry_has_all_six_types(self):
        """Registry contains all 6 expected action types."""
        expected_types = {
            "play_creation",
            "entity_creation",
            "products_check",
            "activate_campaign",
            "deactivate_campaign",
            "create_comment",
        }
        assert set(HANDLER_REGISTRY.keys()) == expected_types

    def test_registry_maps_to_correct_handler_classes(self):
        """Each registry entry maps to the correct handler class."""
        assert HANDLER_REGISTRY["play_creation"] is PlayCreationHandler
        assert HANDLER_REGISTRY["entity_creation"] is EntityCreationHandler
        assert HANDLER_REGISTRY["products_check"] is ProductsCheckHandler
        assert HANDLER_REGISTRY["activate_campaign"] is CampaignHandler
        assert HANDLER_REGISTRY["deactivate_campaign"] is CampaignHandler
        assert HANDLER_REGISTRY["create_comment"] is CommentHandler

    def test_all_handlers_are_init_action_handler_subclasses(self):
        """All registered handlers inherit from InitActionHandler."""
        from autom8_asana.lifecycle.init_actions import InitActionHandler

        for type_key, handler_cls in HANDLER_REGISTRY.items():
            assert issubclass(handler_cls, InitActionHandler), (
                f"Handler for '{type_key}' ({handler_cls.__name__}) "
                f"does not inherit from InitActionHandler"
            )

    def test_unknown_type_not_in_registry(self):
        """Unknown action types return None from registry get."""
        assert HANDLER_REGISTRY.get("nonexistent_type") is None
