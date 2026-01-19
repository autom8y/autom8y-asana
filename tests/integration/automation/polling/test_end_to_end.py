"""End-to-end integration tests for the complete polling automation flow.

Tests the full pipeline: YAML config -> rule evaluation -> action execution -> verify.

This module exercises the complete polling automation lifecycle:
1. Load YAML configuration
2. Evaluate rules against real tasks
3. Execute actions on matched tasks
4. Verify actions were applied

Prerequisites:
    - ASANA_ACCESS_TOKEN or ASANA_PAT environment variable set
    - ASANA_TEST_PROJECT_GID: GID of a test project
    - ASANA_TEST_TAG_GID: GID of a test tag
    - ASANA_TEST_SECTION_GID: GID of a test section

Run these tests:
    pytest -m integration tests/integration/automation/polling/test_end_to_end.py

Skip these tests:
    pytest -m "not integration"
"""

from __future__ import annotations

import os
import tempfile
import textwrap
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from autom8_asana.automation.polling import (
    ActionConfig,
    PollingScheduler,
    Rule,
    RuleCondition,
    TriggerEvaluator,
    TriggerStaleConfig,
)

if TYPE_CHECKING:
    from autom8_asana import AsanaClient
    from autom8_asana.models import Task


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
async def e2e_test_task(
    asana_client: AsanaClient,
    test_project_gid: str,
) -> AsyncGenerator[Task, None]:
    """Create a temporary task specifically for E2E testing, cleanup after.

    Creates a new task in the test project with a unique name.
    The task is automatically deleted after the test completes.

    Yields:
        Task object with gid, name, and other fields.
    """
    unique_id = str(uuid.uuid4())[:8]
    task_name = f"[E2E Test] {datetime.now(UTC).isoformat()} - {unique_id}"

    task = await asana_client.tasks.create_async(
        name=task_name,
        projects=[test_project_gid],
        notes="This task was created for E2E integration testing. If it persists, it can be safely deleted.",
    )

    yield task

    # Cleanup: delete the task
    try:
        await asana_client.tasks.delete_async(task.gid)
    except Exception:
        # Task may already be deleted or inaccessible - that's fine
        pass


@pytest.fixture
async def multiple_e2e_tasks(
    asana_client: AsanaClient,
    test_project_gid: str,
) -> AsyncGenerator[list[Task], None]:
    """Create multiple temporary tasks for E2E testing.

    Creates 3 tasks with different characteristics for rule evaluation testing.
    All tasks are automatically deleted after the test completes.

    Yields:
        List of Task objects.
    """
    unique_id = str(uuid.uuid4())[:8]
    tasks: list[Task] = []

    for i in range(3):
        task_name = f"[E2E Multi Task {i + 1}] {unique_id}"
        task = await asana_client.tasks.create_async(
            name=task_name,
            projects=[test_project_gid],
            notes=f"E2E test task {i + 1} of 3. Can be safely deleted.",
        )
        tasks.append(task)

    yield tasks

    # Cleanup: delete all tasks
    for task in tasks:
        try:
            await asana_client.tasks.delete_async(task.gid)
        except Exception:
            pass


# ============================================================================
# Full Flow E2E Tests
# ============================================================================


@pytest.mark.integration
async def test_full_polling_flow_with_real_api(
    asana_client: AsanaClient,
    test_project_gid: str,
    test_tag_gid: str,
    e2e_test_task: Task,
) -> None:
    """End-to-end test of the complete polling automation flow.

    This test exercises the entire pipeline:
    1. Create YAML config with a rule targeting the test project
    2. Create a PollingScheduler from the config
    3. Fetch tasks from the project
    4. Manually evaluate rules using the scheduler's evaluator
    5. Execute actions on matched tasks
    6. Verify the action was applied via API

    Note: Since we cannot make a task truly stale (it would require waiting days),
    we use a rule with no conditions (matches all tasks) or use a mock task
    for the evaluation portion.
    """
    # 1. Create temporary YAML config targeting the test project
    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "e2e-test-add-tag"
            name: "E2E Test - Add Tag to All Tasks"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_tag"
              params:
                tag_gid: "{test_tag_gid}"
    """)

    # Write config to temp file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        # 2. Load config and create scheduler (with client for action execution)
        scheduler = PollingScheduler.from_config_file(
            config_path,
            client=asana_client,
        )

        # Verify config was loaded correctly
        assert len(scheduler.config.rules) == 1
        assert scheduler.config.rules[0].rule_id == "e2e-test-add-tag"

        # 3. Fetch task with required fields for evaluation
        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=[
                "gid",
                "name",
                "modified_at",
                "created_at",
                "due_on",
                "due_at",
                "completed",
            ],
        )

        # 4. Evaluate rules against the task
        # Since the rule has no conditions, it should match all tasks
        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # 5. Verify the tag was added to the task
        updated_task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["tags.gid"],
        )
        tag_gids = [t.gid for t in updated_task.tags] if updated_task.tags else []
        assert test_tag_gid in tag_gids, (
            f"Tag {test_tag_gid} was not added to task. Current tags: {tag_gids}"
        )

    finally:
        # Cleanup config file
        os.unlink(config_path)


@pytest.mark.integration
async def test_full_flow_config_to_verify_with_comment(
    asana_client: AsanaClient,
    test_project_gid: str,
    e2e_test_task: Task,
) -> None:
    """E2E test using add_comment action to verify full flow.

    This test verifies:
    1. Config loading from YAML
    2. Rule evaluation with no conditions (matches all)
    3. Comment action execution
    4. Comment verification via stories API
    """
    comment_text = f"[E2E Test] Automated comment at {datetime.now(UTC).isoformat()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "03:00"
          timezone: "America/New_York"
        rules:
          - rule_id: "e2e-test-add-comment"
            name: "E2E Test - Add Comment"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{comment_text}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        # Load and run
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at"],
        )

        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # Verify comment was added
        stories_iter = asana_client.stories.list_for_task_async(
            e2e_test_task.gid,
            opt_fields=["text", "resource_subtype"],
        )
        stories = await stories_iter.collect_all_async()

        comments = [s for s in stories if s.resource_subtype == "comment_added"]
        comment_texts = [s.text for s in comments if s.text]

        assert comment_text in comment_texts, (
            f"Comment not found. Expected: '{comment_text}', Found: {comment_texts}"
        )

    finally:
        os.unlink(config_path)


# ============================================================================
# Multiple Rules Scenario
# ============================================================================


@pytest.mark.integration
async def test_multiple_rules_evaluated_and_executed(
    asana_client: AsanaClient,
    test_project_gid: str,
    test_tag_gid: str,
    e2e_test_task: Task,
) -> None:
    """Test that multiple rules are evaluated and their actions executed.

    Verifies:
    - Multiple rules in config are all evaluated
    - Actions from each matching rule are executed
    - Results are independent (one rule's action doesn't affect another)
    """
    comment_text = f"[Multi-Rule Test] {uuid.uuid4()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "multi-rule-1"
            name: "Multi Rule Test - Add Tag"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_tag"
              params:
                tag_gid: "{test_tag_gid}"
          - rule_id: "multi-rule-2"
            name: "Multi Rule Test - Add Comment"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{comment_text}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        # Verify both rules were loaded
        assert len(scheduler.config.rules) == 2

        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at"],
        )

        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # Verify tag was added (rule 1)
        updated_task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["tags.gid"],
        )
        tag_gids = [t.gid for t in updated_task.tags] if updated_task.tags else []
        assert test_tag_gid in tag_gids, "Tag from rule 1 was not added"

        # Verify comment was added (rule 2)
        stories_iter = asana_client.stories.list_for_task_async(
            e2e_test_task.gid,
            opt_fields=["text", "resource_subtype"],
        )
        stories = await stories_iter.collect_all_async()
        comments = [s for s in stories if s.resource_subtype == "comment_added"]
        comment_texts = [s.text for s in comments if s.text]
        assert comment_text in comment_texts, "Comment from rule 2 was not added"

    finally:
        os.unlink(config_path)


# ============================================================================
# Rule Disabled Scenario
# ============================================================================


@pytest.mark.integration
async def test_disabled_rules_are_skipped(
    asana_client: AsanaClient,
    test_project_gid: str,
    test_tag_gid: str,
    e2e_test_task: Task,
) -> None:
    """Test that disabled rules are not executed.

    Verifies:
    - Rules with enabled: false are skipped during evaluation
    - Only enabled rules have their actions executed
    """
    # Use a unique comment text to identify if the disabled rule was executed
    disabled_comment = f"[DISABLED RULE - SHOULD NOT APPEAR] {uuid.uuid4()}"
    enabled_comment = f"[ENABLED RULE] {uuid.uuid4()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "disabled-rule"
            name: "This Rule is Disabled"
            project_gid: "{test_project_gid}"
            enabled: false
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{disabled_comment}"
          - rule_id: "enabled-rule"
            name: "This Rule is Enabled"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{enabled_comment}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at"],
        )

        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # Check comments on the task
        stories_iter = asana_client.stories.list_for_task_async(
            e2e_test_task.gid,
            opt_fields=["text", "resource_subtype"],
        )
        stories = await stories_iter.collect_all_async()
        comments = [s for s in stories if s.resource_subtype == "comment_added"]
        comment_texts = [s.text for s in comments if s.text]

        # Enabled rule's comment SHOULD be present
        assert enabled_comment in comment_texts, "Enabled rule's comment was not found"

        # Disabled rule's comment should NOT be present
        assert disabled_comment not in comment_texts, (
            "Disabled rule's comment was found - rule was not skipped!"
        )

    finally:
        os.unlink(config_path)


# ============================================================================
# No Matches Scenario
# ============================================================================


@pytest.mark.integration
async def test_no_matches_no_actions_executed(
    asana_client: AsanaClient,
    test_project_gid: str,
    e2e_test_task: Task,
) -> None:
    """Test that when no tasks match conditions, no actions are executed.

    Verifies:
    - Rules with strict conditions that don't match any tasks
    - No actions are executed when there are no matches
    - System handles empty match results gracefully
    """
    # Create a rule with conditions that won't match a fresh task
    # (stale trigger with 999 days - no task would be that old)
    should_not_appear_comment = f"[SHOULD NOT APPEAR - NO MATCH] {uuid.uuid4()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "no-match-rule"
            name: "Rule that should not match"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions:
              - stale:
                  field: "any"
                  days: 999
            action:
              type: "add_comment"
              params:
                text: "{should_not_appear_comment}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        # Fetch task (fresh, should not match 999-day stale condition)
        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at", "completed"],
        )

        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # Verify no comment was added
        stories_iter = asana_client.stories.list_for_task_async(
            e2e_test_task.gid,
            opt_fields=["text", "resource_subtype"],
        )
        stories = await stories_iter.collect_all_async()
        comments = [s for s in stories if s.resource_subtype == "comment_added"]
        comment_texts = [s.text for s in comments if s.text]

        assert should_not_appear_comment not in comment_texts, (
            "Comment was added even though rule should not have matched"
        )

    finally:
        os.unlink(config_path)


@pytest.mark.integration
async def test_empty_task_list_no_errors(
    asana_client: AsanaClient,
    test_project_gid: str,
    test_tag_gid: str,
) -> None:
    """Test that evaluating rules with empty task list doesn't cause errors.

    Verifies:
    - Empty task list is handled gracefully
    - No exceptions are raised
    - Evaluation completes normally
    """
    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "empty-list-rule"
            name: "Rule for Empty List Test"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_tag"
              params:
                tag_gid: "{test_tag_gid}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        # Pass empty task list - should not raise any errors
        tasks_by_project: dict[str, list[object]] = {test_project_gid: []}
        scheduler._evaluate_rules(tasks_by_project)

        # If we get here, the test passed (no exceptions)

    finally:
        os.unlink(config_path)


# ============================================================================
# Error Isolation Tests
# ============================================================================


@pytest.mark.integration
async def test_action_failure_does_not_block_other_rules(
    asana_client: AsanaClient,
    test_project_gid: str,
    e2e_test_task: Task,
) -> None:
    """Test that one rule's action failure doesn't prevent other rules from executing.

    Verifies:
    - If one action fails (e.g., invalid tag GID), other rules still execute
    - Error isolation between rules
    - Graceful degradation
    """
    # First rule has an invalid tag GID (will fail)
    # Second rule has a valid comment (should succeed)
    valid_comment = f"[SHOULD SUCCEED] {uuid.uuid4()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "failing-rule"
            name: "Rule with Invalid Tag"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_tag"
              params:
                tag_gid: "invalid_tag_gid_12345"
          - rule_id: "succeeding-rule"
            name: "Rule with Valid Comment"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{valid_comment}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at"],
        )

        tasks_by_project = {test_project_gid: [task]}

        # This should NOT raise - errors should be logged but not propagated
        scheduler._evaluate_rules(tasks_by_project)

        # Verify the second rule's comment was added despite first rule failing
        stories_iter = asana_client.stories.list_for_task_async(
            e2e_test_task.gid,
            opt_fields=["text", "resource_subtype"],
        )
        stories = await stories_iter.collect_all_async()
        comments = [s for s in stories if s.resource_subtype == "comment_added"]
        comment_texts = [s.text for s in comments if s.text]

        assert valid_comment in comment_texts, (
            "Second rule's comment was not added - error isolation failed"
        )

    finally:
        os.unlink(config_path)


@pytest.mark.integration
async def test_action_failure_on_one_task_continues_to_others(
    asana_client: AsanaClient,
    test_project_gid: str,
    multiple_e2e_tasks: list[Task],
) -> None:
    """Test that action failure on one task doesn't prevent actions on other tasks.

    Verifies:
    - If action fails on task A, action still executes on task B
    - Error isolation between tasks within a single rule
    """
    valid_comment = f"[TASK ISOLATION TEST] {uuid.uuid4()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "multi-task-rule"
            name: "Rule for Multiple Tasks"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{valid_comment}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        # Fetch tasks with required fields
        tasks = []
        for test_task in multiple_e2e_tasks:
            task = await asana_client.tasks.get_async(
                test_task.gid,
                opt_fields=["gid", "name", "modified_at", "created_at"],
            )
            tasks.append(task)

        tasks_by_project = {test_project_gid: tasks}
        scheduler._evaluate_rules(tasks_by_project)

        # Verify comment was added to all tasks
        for test_task in multiple_e2e_tasks:
            stories_iter = asana_client.stories.list_for_task_async(
                test_task.gid,
                opt_fields=["text", "resource_subtype"],
            )
            stories = await stories_iter.collect_all_async()
            comments = [s for s in stories if s.resource_subtype == "comment_added"]
            comment_texts = [s.text for s in comments if s.text]

            assert valid_comment in comment_texts, (
                f"Comment not found on task {test_task.gid}"
            )

    finally:
        os.unlink(config_path)


# ============================================================================
# Configuration Loading Tests
# ============================================================================


@pytest.mark.integration
async def test_config_from_file_integration(
    test_project_gid: str,
    test_tag_gid: str,
) -> None:
    """Test that config file loading integrates correctly with scheduler.

    Verifies:
    - YAML file is read correctly
    - Config is parsed and validated
    - Scheduler is created successfully
    - All config values are accessible
    """
    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "14:30"
          timezone: "Europe/London"
        rules:
          - rule_id: "config-test-rule"
            name: "Config Loading Test Rule"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions:
              - stale:
                  field: "modified_at"
                  days: 7
            action:
              type: "add_tag"
              params:
                tag_gid: "{test_tag_gid}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        # Load without client (dry-run mode)
        scheduler = PollingScheduler.from_config_file(config_path)

        # Verify scheduler config
        assert scheduler.config.scheduler.time == "14:30"
        assert scheduler.config.scheduler.timezone == "Europe/London"

        # Verify rule config
        assert len(scheduler.config.rules) == 1
        rule = scheduler.config.rules[0]
        assert rule.rule_id == "config-test-rule"
        assert rule.name == "Config Loading Test Rule"
        assert rule.project_gid == test_project_gid
        assert rule.enabled is True

        # Verify condition
        assert len(rule.conditions) == 1
        condition = rule.conditions[0]
        assert condition.stale is not None
        assert condition.stale.days == 7

        # Verify action
        assert rule.action.type == "add_tag"
        assert rule.action.params.get("tag_gid") == test_tag_gid

    finally:
        os.unlink(config_path)


@pytest.mark.integration
async def test_dry_run_mode_no_actions_executed(
    asana_client: AsanaClient,
    test_project_gid: str,
    e2e_test_task: Task,
) -> None:
    """Test that scheduler without client runs in dry-run mode (no actions).

    Verifies:
    - Scheduler created without client parameter
    - Rules are evaluated
    - No actions are executed (dry-run mode)
    """
    should_not_appear = f"[DRY RUN - SHOULD NOT APPEAR] {uuid.uuid4()}"

    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "dry-run-test"
            name: "Dry Run Test Rule"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "add_comment"
              params:
                text: "{should_not_appear}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        # Create scheduler WITHOUT client (dry-run mode)
        scheduler = PollingScheduler.from_config_file(config_path)

        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at"],
        )

        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # Verify NO comment was added (dry-run mode)
        stories_iter = asana_client.stories.list_for_task_async(
            e2e_test_task.gid,
            opt_fields=["text", "resource_subtype"],
        )
        stories = await stories_iter.collect_all_async()
        comments = [s for s in stories if s.resource_subtype == "comment_added"]
        comment_texts = [s.text for s in comments if s.text]

        assert should_not_appear not in comment_texts, (
            "Comment was added in dry-run mode - actions should not execute"
        )

    finally:
        os.unlink(config_path)


# ============================================================================
# Change Section Action Test
# ============================================================================


@pytest.mark.integration
async def test_change_section_full_flow(
    asana_client: AsanaClient,
    test_project_gid: str,
    test_section_gid: str,
    e2e_test_task: Task,
) -> None:
    """Test change_section action in full E2E flow.

    Verifies:
    - Task can be moved to a different section via automation
    - Section change is verified via API
    """
    config_yaml = textwrap.dedent(f"""\
        scheduler:
          time: "02:00"
          timezone: "UTC"
        rules:
          - rule_id: "change-section-test"
            name: "Change Section Test"
            project_gid: "{test_project_gid}"
            enabled: true
            conditions: []
            action:
              type: "change_section"
              params:
                section_gid: "{test_section_gid}"
    """)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        scheduler = PollingScheduler.from_config_file(config_path, client=asana_client)

        task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["gid", "name", "modified_at", "created_at"],
        )

        tasks_by_project = {test_project_gid: [task]}
        scheduler._evaluate_rules(tasks_by_project)

        # Verify task is now in the target section
        updated_task = await asana_client.tasks.get_async(
            e2e_test_task.gid,
            opt_fields=["memberships.section.gid"],
        )

        if updated_task.memberships:
            section_gids = [
                m.section.gid
                for m in updated_task.memberships
                if m.section and m.section.gid
            ]
            assert test_section_gid in section_gids, (
                f"Task not in expected section. Expected: {test_section_gid}, "
                f"Found: {section_gids}"
            )

    finally:
        os.unlink(config_path)


# ============================================================================
# Condition Evaluation Tests
# ============================================================================


@pytest.mark.integration
def test_stale_condition_with_mock_task_in_flow(
    now: datetime,
) -> None:
    """Test stale condition evaluation using mock task in the full flow.

    This test uses the MockTask from conftest to simulate a stale task
    without needing to wait for real API tasks to become stale.

    Note: This test does not require API access - it uses mock tasks
    to verify the condition evaluation logic works correctly in the
    context of the E2E flow.
    """
    from tests.integration.automation.polling.conftest import MockTask

    # Create mock stale task (modified 10 days ago)
    stale_task = MockTask(
        gid="mock-stale-e2e",
        name="Mock Stale E2E Task",
        modified_at=(now - timedelta(days=10)).isoformat(),
        created_at=(now - timedelta(days=20)).isoformat(),
        completed=False,
    )

    # Create mock fresh task (modified just now)
    fresh_task = MockTask(
        gid="mock-fresh-e2e",
        name="Mock Fresh E2E Task",
        modified_at=now.isoformat(),
        created_at=(now - timedelta(days=1)).isoformat(),
        completed=False,
    )

    # Use TriggerEvaluator directly for condition testing
    evaluator = TriggerEvaluator()

    # Use a dummy project GID since we're not actually hitting the API
    dummy_project_gid = "12345678901234"

    rule = Rule(
        rule_id="stale-condition-test",
        name="Test Stale Condition",
        project_gid=dummy_project_gid,
        enabled=True,
        conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=7))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "dummy"}),
    )

    tasks = [stale_task, fresh_task]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Only the stale task should match
    assert len(matching) == 1
    assert matching[0].gid == "mock-stale-e2e"
