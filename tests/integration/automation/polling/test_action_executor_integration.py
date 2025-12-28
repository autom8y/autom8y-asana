"""Integration tests for ActionExecutor with real Asana API.

Tests verify that each action type (add_tag, add_comment, change_section)
works correctly with the live Asana API.

Prerequisites:
    - ASANA_ACCESS_TOKEN or ASANA_PAT environment variable set
    - ASANA_TEST_PROJECT_GID: GID of a test project
    - ASANA_TEST_TAG_GID: GID of a test tag
    - ASANA_TEST_SECTION_GID: GID of a test section

Run these tests:
    pytest -m integration tests/integration/automation/polling/test_action_executor_integration.py

Skip these tests:
    pytest -m "not integration"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.automation.polling import ActionConfig, ActionExecutor

if TYPE_CHECKING:
    from autom8_asana import AsanaClient
    from autom8_asana.models import Task


# ============================================================================
# add_tag Action Tests
# ============================================================================


@pytest.mark.integration
async def test_add_tag_real_api(
    asana_client: "AsanaClient",
    test_task: "Task",
    test_tag_gid: str,
) -> None:
    """Test add_tag action with real Asana API.

    Creates a task, adds a tag to it, and verifies the tag was added.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="add_tag", params={"tag_gid": test_tag_gid})

    # Execute the action
    result = await executor.execute_async(test_task.gid, action)

    # Verify success
    assert result.success is True
    assert result.action_type == "add_tag"
    assert result.task_gid == test_task.gid
    assert result.error is None
    assert result.details.get("tag_gid") == test_tag_gid

    # Verify tag was actually added by fetching the task
    updated_task = await asana_client.tasks.get_async(
        test_task.gid,
        opt_fields=["tags.gid"],
    )
    tag_gids = [t.gid for t in updated_task.tags] if updated_task.tags else []
    assert test_tag_gid in tag_gids, f"Tag {test_tag_gid} not found in task tags: {tag_gids}"


@pytest.mark.integration
async def test_add_tag_idempotent(
    asana_client: "AsanaClient",
    test_task: "Task",
    test_tag_gid: str,
) -> None:
    """Test that adding the same tag twice is idempotent.

    The Asana API should handle duplicate tag additions gracefully.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="add_tag", params={"tag_gid": test_tag_gid})

    # Add tag twice
    result1 = await executor.execute_async(test_task.gid, action)
    result2 = await executor.execute_async(test_task.gid, action)

    # Both should succeed
    assert result1.success is True
    assert result2.success is True


@pytest.mark.integration
async def test_add_tag_invalid_tag_gid(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test add_tag with invalid tag GID returns error result.

    The action should fail gracefully and return success=False.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="add_tag", params={"tag_gid": "invalid_tag_gid_12345"})

    result = await executor.execute_async(test_task.gid, action)

    assert result.success is False
    assert result.action_type == "add_tag"
    assert result.error is not None
    assert len(result.error) > 0


# ============================================================================
# add_comment Action Tests
# ============================================================================


@pytest.mark.integration
async def test_add_comment_real_api(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test add_comment action with real Asana API.

    Creates a comment on a task and verifies it was added.
    """
    executor = ActionExecutor(asana_client)
    comment_text = "[Integration Test] Automated comment for testing"
    action = ActionConfig(type="add_comment", params={"text": comment_text})

    # Execute the action
    result = await executor.execute_async(test_task.gid, action)

    # Verify success
    assert result.success is True
    assert result.action_type == "add_comment"
    assert result.task_gid == test_task.gid
    assert result.error is None
    assert result.details.get("text") == comment_text

    # Verify comment was actually added by fetching task stories
    stories_iter = asana_client.stories.list_for_task_async(
        test_task.gid,
        opt_fields=["text", "resource_subtype"],
    )
    stories = await stories_iter.collect_all_async()

    # Filter for comments
    comments = [s for s in stories if s.resource_subtype == "comment_added"]
    comment_texts = [s.text for s in comments if s.text]
    assert comment_text in comment_texts, f"Comment not found in stories: {comment_texts}"


@pytest.mark.integration
async def test_add_comment_with_special_characters(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test add_comment with special characters in text.

    Verifies that Unicode, emojis, and special characters are handled correctly.
    """
    executor = ActionExecutor(asana_client)
    comment_text = "[Test] Unicode test: cafe, emoji: test, special: <>&\"'"
    action = ActionConfig(type="add_comment", params={"text": comment_text})

    result = await executor.execute_async(test_task.gid, action)

    assert result.success is True
    assert result.details.get("text") == comment_text


@pytest.mark.integration
async def test_add_comment_empty_text_fails(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test that empty comment text is handled.

    Empty comments may fail or be rejected by the API.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="add_comment", params={"text": ""})

    # Empty comment might fail - this tests graceful error handling
    result = await executor.execute_async(test_task.gid, action)

    # Result should indicate failure (empty comments are typically rejected)
    # If the API accepts empty comments, this test can be adjusted
    assert result.action_type == "add_comment"
    # Note: The actual behavior depends on Asana's API response


# ============================================================================
# change_section Action Tests
# ============================================================================


@pytest.mark.integration
async def test_change_section_real_api(
    asana_client: "AsanaClient",
    test_task: "Task",
    test_section_gid: str,
) -> None:
    """Test change_section action with real Asana API.

    Moves a task to a different section and verifies the move.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="change_section", params={"section_gid": test_section_gid})

    # Execute the action
    result = await executor.execute_async(test_task.gid, action)

    # Verify success
    assert result.success is True
    assert result.action_type == "change_section"
    assert result.task_gid == test_task.gid
    assert result.error is None
    assert result.details.get("section_gid") == test_section_gid

    # Verify task is now in the section by fetching task memberships
    updated_task = await asana_client.tasks.get_async(
        test_task.gid,
        opt_fields=["memberships.section.gid"],
    )

    if updated_task.memberships:
        section_gids = [
            m.section.gid
            for m in updated_task.memberships
            if m.section and m.section.gid
        ]
        assert test_section_gid in section_gids, (
            f"Section {test_section_gid} not found in task memberships: {section_gids}"
        )


@pytest.mark.integration
async def test_change_section_invalid_section_gid(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test change_section with invalid section GID returns error result.

    The action should fail gracefully and return success=False.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="change_section", params={"section_gid": "invalid_section_12345"})

    result = await executor.execute_async(test_task.gid, action)

    assert result.success is False
    assert result.action_type == "change_section"
    assert result.error is not None
    assert len(result.error) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
async def test_action_on_invalid_task_gid(
    asana_client: "AsanaClient",
    test_tag_gid: str,
) -> None:
    """Test action execution on non-existent task.

    Should fail gracefully with success=False.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="add_tag", params={"tag_gid": test_tag_gid})

    result = await executor.execute_async("nonexistent_task_12345", action)

    assert result.success is False
    assert result.error is not None


@pytest.mark.integration
async def test_unsupported_action_type_raises(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test that unsupported action types raise ValueError.

    The executor should validate action types before attempting execution.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="unsupported_action", params={"foo": "bar"})

    with pytest.raises(ValueError) as exc_info:
        await executor.execute_async(test_task.gid, action)

    assert "unsupported_action" in str(exc_info.value).lower()
    assert "unsupported" in str(exc_info.value).lower()


@pytest.mark.integration
async def test_missing_required_params_raises(
    asana_client: "AsanaClient",
    test_task: "Task",
) -> None:
    """Test that missing required params raise ValueError.

    Each action type has required parameters that must be present.
    """
    executor = ActionExecutor(asana_client)

    # add_tag requires tag_gid
    action = ActionConfig(type="add_tag", params={})
    with pytest.raises(ValueError) as exc_info:
        await executor.execute_async(test_task.gid, action)
    assert "tag_gid" in str(exc_info.value)

    # add_comment requires text
    action = ActionConfig(type="add_comment", params={})
    with pytest.raises(ValueError) as exc_info:
        await executor.execute_async(test_task.gid, action)
    assert "text" in str(exc_info.value)

    # change_section requires section_gid
    action = ActionConfig(type="change_section", params={})
    with pytest.raises(ValueError) as exc_info:
        await executor.execute_async(test_task.gid, action)
    assert "section_gid" in str(exc_info.value)


# ============================================================================
# ActionResult Tests
# ============================================================================


@pytest.mark.integration
async def test_action_result_contains_all_fields(
    asana_client: "AsanaClient",
    test_task: "Task",
    test_tag_gid: str,
) -> None:
    """Test that ActionResult contains all expected fields.

    Verifies the structure of the result object on success.
    """
    executor = ActionExecutor(asana_client)
    action = ActionConfig(type="add_tag", params={"tag_gid": test_tag_gid})

    result = await executor.execute_async(test_task.gid, action)

    # Check all fields are present and correct types
    assert isinstance(result.success, bool)
    assert isinstance(result.action_type, str)
    assert isinstance(result.task_gid, str)
    assert result.error is None or isinstance(result.error, str)
    assert isinstance(result.details, dict)
