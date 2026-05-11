"""AC-R5 tests — ProjectTaskHandler + SectionTaskHandler intake event routing.

Sprint 2 receiver-surface — Item E (AC-R5 gate).

Verifies:
  1. ProjectTaskHandler resolves project_gid from event payload (not registry).
  2. SectionTaskHandler resolves project_gid from event payload (not registry).
  3. Handlers route to ProgressiveProjectBuilder with the payload-extracted GID.
  4. Handlers reject events missing project_gid (ValueError).
  5. dry_run flag passes through to payload.

Deliberate shortcuts:
  - ProgressiveProjectBuilder.build_progressive_async() is fully mocked.
  - AsanaClient, get_bot_pat, resolve_secret_from_env are all mocked.
  - No live S3 or Asana API calls.
  - S3DataFrameStorage setup path is patched to avoid settings dependency.

What is NOT tested here:
  - Live progressive build execution (requires Asana credentials + S3).
  - EntityProjectRegistry — intentionally absent from handler path (AC-R5 constraint).
  - Idempotency (production requirement, not prototype scope).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.services.intake_task_handlers import (
    IntakeEventPayload,
    ProjectTaskHandler,
    SectionTaskHandler,
)

# Synthetic 16-digit GIDs (S-06 pattern).
_PROJECT_GID = "1200000000000001"
_SECTION_GID = "1200000000000002"


def _make_mock_build_result(total_rows: int = 5) -> MagicMock:
    """Create a mock BuildResult returned by ProgressiveProjectBuilder."""
    result = MagicMock()
    result.status = MagicMock()
    result.status.value = "COMPLETE"
    result.total_rows = total_rows
    result.sections_built = 2
    result.sections_resumed = 0
    return result



class TestIntakeEventPayload:
    """Unit tests for IntakeEventPayload dataclass."""

    def test_payload_stores_project_gid(self) -> None:
        """IntakeEventPayload carries the payload-extracted GID."""
        payload = IntakeEventPayload(project_gid=_PROJECT_GID, entity_type="project")
        assert payload.project_gid == _PROJECT_GID
        assert payload.entity_type == "project"
        assert payload.dry_run is False

    def test_payload_dry_run_flag(self) -> None:
        """IntakeEventPayload dry_run defaults to False, accepts True."""
        p = IntakeEventPayload(project_gid=_SECTION_GID, entity_type="section", dry_run=True)
        assert p.dry_run is True


class TestProjectTaskHandlerExtractPayload:
    """ProjectTaskHandler._extract_payload() — payload extraction without Asana IO."""

    def test_extracts_project_gid_from_event(self) -> None:
        """AC-R5: project_gid comes from event, not registry."""
        payload = ProjectTaskHandler._extract_payload({"project_gid": _PROJECT_GID})
        assert payload.project_gid == _PROJECT_GID
        assert payload.entity_type == "project"

    def test_strips_whitespace_from_gid(self) -> None:
        """Leading/trailing whitespace is stripped from project_gid."""
        payload = ProjectTaskHandler._extract_payload({"project_gid": f"  {_PROJECT_GID}  "})
        assert payload.project_gid == _PROJECT_GID

    def test_dry_run_false_by_default(self) -> None:
        """dry_run defaults to False when not in event."""
        payload = ProjectTaskHandler._extract_payload({"project_gid": _PROJECT_GID})
        assert payload.dry_run is False

    def test_dry_run_true_when_set(self) -> None:
        """dry_run=True passes through from event."""
        payload = ProjectTaskHandler._extract_payload(
            {"project_gid": _PROJECT_GID, "dry_run": True}
        )
        assert payload.dry_run is True

    def test_raises_value_error_when_project_gid_missing(self) -> None:
        """AC-R5 guard: missing project_gid raises ValueError — not registry fallback."""
        with pytest.raises(ValueError, match="project_gid"):
            ProjectTaskHandler._extract_payload({})

    def test_raises_value_error_when_project_gid_empty_string(self) -> None:
        """Empty string project_gid raises ValueError."""
        with pytest.raises(ValueError, match="project_gid"):
            ProjectTaskHandler._extract_payload({"project_gid": ""})

    def test_raises_value_error_when_project_gid_whitespace_only(self) -> None:
        """Whitespace-only project_gid raises ValueError."""
        with pytest.raises(ValueError, match="project_gid"):
            ProjectTaskHandler._extract_payload({"project_gid": "   "})

    def test_raises_value_error_when_project_gid_none(self) -> None:
        """None project_gid raises ValueError."""
        with pytest.raises(ValueError, match="project_gid"):
            ProjectTaskHandler._extract_payload({"project_gid": None})


class TestSectionTaskHandlerExtractPayload:
    """SectionTaskHandler._extract_payload() — mirrors ProjectTaskHandler with section entity_type."""

    def test_extracts_section_gid_from_event(self) -> None:
        """AC-R5: project_gid comes from event for section type."""
        payload = SectionTaskHandler._extract_payload({"project_gid": _SECTION_GID})
        assert payload.project_gid == _SECTION_GID
        assert payload.entity_type == "section"

    def test_raises_when_missing(self) -> None:
        """SectionTaskHandler also rejects missing project_gid."""
        with pytest.raises(ValueError, match="project_gid"):
            SectionTaskHandler._extract_payload({})


class TestProjectTaskHandlerEntityType:
    """ProjectTaskHandler.ENTITY_TYPE — static class attribute."""

    def test_entity_type_is_project(self) -> None:
        """ProjectTaskHandler.ENTITY_TYPE is 'project'."""
        assert ProjectTaskHandler.ENTITY_TYPE == "project"


class TestSectionTaskHandlerEntityType:
    """SectionTaskHandler.ENTITY_TYPE — static class attribute."""

    def test_entity_type_is_section(self) -> None:
        """SectionTaskHandler.ENTITY_TYPE is 'section'."""
        assert SectionTaskHandler.ENTITY_TYPE == "section"


class TestProjectTaskHandlerHandleAsync:
    """AC-R5 positive-path: ProjectTaskHandler.handle_async routes to builder with payload GID."""

    @pytest.mark.asyncio
    async def test_routes_project_event_to_progressive_builder(self) -> None:
        """AC-R5 gate: ProjectTaskHandler calls ProgressiveProjectBuilder with event GID."""
        build_result = _make_mock_build_result(total_rows=10)

        mock_builder_instance = MagicMock()
        mock_builder_instance.build_progressive_async = AsyncMock(return_value=build_result)

        mock_persistence = MagicMock()
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.services.intake_task_handlers.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch(
                "autom8_asana.services.intake_task_handlers._get_workspace_gid",
                return_value="test-workspace-gid",
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.create_section_persistence",
                return_value=mock_persistence,
            ),
            # AsanaClient is imported lazily inside handle_async — patch at source
            patch(
                "autom8_asana.AsanaClient",
                return_value=mock_asana,
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.ProgressiveProjectBuilder",
                return_value=mock_builder_instance,
            ) as mock_builder_cls,
            patch(
                "autom8_asana.services.intake_task_handlers.get_schema",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.DefaultCustomFieldResolver",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.build_gid_index_data",
                return_value=None,
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.get_settings",
                return_value=MagicMock(s3=None),
            ),
        ):
            result = await ProjectTaskHandler.handle_async({"project_gid": _PROJECT_GID})

        # Builder must be called with the payload-extracted GID (not registry lookup)
        mock_builder_cls.assert_called_once()
        call_kwargs = mock_builder_cls.call_args.kwargs
        assert call_kwargs["project_gid"] == _PROJECT_GID, (
            f"AC-R5: ProgressiveProjectBuilder must receive payload GID {_PROJECT_GID!r}, "
            f"got {call_kwargs.get('project_gid')!r}"
        )
        assert call_kwargs["entity_type"] == "project"

        # Build must execute
        mock_builder_instance.build_progressive_async.assert_called_once()
        assert result.total_rows == 10


class TestSectionTaskHandlerHandleAsync:
    """AC-R5 positive-path: SectionTaskHandler.handle_async routes to builder with payload GID."""

    @pytest.mark.asyncio
    async def test_routes_section_event_to_progressive_builder(self) -> None:
        """AC-R5 gate: SectionTaskHandler calls ProgressiveProjectBuilder with event GID."""
        build_result = _make_mock_build_result(total_rows=7)

        mock_builder_instance = MagicMock()
        mock_builder_instance.build_progressive_async = AsyncMock(return_value=build_result)

        mock_persistence = MagicMock()
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.services.intake_task_handlers.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch(
                "autom8_asana.services.intake_task_handlers._get_workspace_gid",
                return_value="test-workspace-gid",
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.create_section_persistence",
                return_value=mock_persistence,
            ),
            # AsanaClient is imported lazily inside handle_async — patch at source
            patch(
                "autom8_asana.AsanaClient",
                return_value=mock_asana,
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.ProgressiveProjectBuilder",
                return_value=mock_builder_instance,
            ) as mock_builder_cls,
            patch(
                "autom8_asana.services.intake_task_handlers.get_schema",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.DefaultCustomFieldResolver",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.build_gid_index_data",
                return_value=None,
            ),
            patch(
                "autom8_asana.services.intake_task_handlers.get_settings",
                return_value=MagicMock(s3=None),
            ),
        ):
            result = await SectionTaskHandler.handle_async({"project_gid": _SECTION_GID})

        call_kwargs = mock_builder_cls.call_args.kwargs
        assert call_kwargs["project_gid"] == _SECTION_GID, (
            f"AC-R5: SectionTaskHandler must receive payload GID {_SECTION_GID!r}, "
            f"got {call_kwargs.get('project_gid')!r}"
        )
        assert call_kwargs["entity_type"] == "section"
        assert result.total_rows == 7
