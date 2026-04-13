"""Integration tests for TriggerEvaluator with real Asana tasks.

Tests verify that trigger conditions (stale, deadline, age) are correctly
evaluated against real and mock task data.

Note: True staleness testing requires tasks that haven't been modified for
the configured number of days. Most tests here use mock tasks with controlled
date fields to ensure reliable testing.

Prerequisites:
    - ASANA_ACCESS_TOKEN or ASANA_PAT environment variable set
    - ASANA_TEST_PROJECT_GID: GID of a test project

Run these tests:
    pytest -m integration tests/integration/automation/polling/test_trigger_evaluator_integration.py

Skip these tests:
    pytest -m "not integration"
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from autom8_asana.automation.polling import (
    ActionConfig,
    Rule,
    RuleCondition,
    TriggerAgeConfig,
    TriggerDeadlineConfig,
    TriggerEvaluator,
    TriggerStaleConfig,
)

if TYPE_CHECKING:
    from tests.integration.automation.polling.conftest import MockTask


# ============================================================================
# Stale Trigger Tests (using mock tasks)
# ============================================================================


@pytest.mark.integration
def test_stale_trigger_matches_old_tasks(
    mock_stale_task: MockTask,
    mock_fresh_task: MockTask,
) -> None:
    """Test stale trigger matches tasks not modified recently.

    Uses mock tasks with controlled modified_at values.
    """
    evaluator = TriggerEvaluator()

    # Rule: tasks not modified in 3 days
    rule = Rule(
        rule_id="stale-test",
        name="Find stale tasks",
        project_gid="123",
        conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=3))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    tasks = [mock_stale_task, mock_fresh_task]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Only the stale task (modified 5 days ago) should match 3-day threshold
    assert len(matching) == 1
    assert matching[0].gid == mock_stale_task.gid


@pytest.mark.integration
def test_stale_trigger_threshold_boundary(now: datetime) -> None:
    """Test stale trigger at exact threshold boundary.

    A task modified exactly N days ago should match.
    A task modified N-1 days ago should not match.
    """
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    # Create tasks at exact boundaries
    exactly_3_days = MockTask(
        gid="exact-3",
        name="Exactly 3 days old",
        modified_at=(now - timedelta(days=3)).isoformat(),
    )
    just_under_3_days = MockTask(
        gid="under-3",
        name="Just under 3 days old",
        modified_at=(now - timedelta(days=2, hours=23, minutes=59)).isoformat(),
    )

    rule = Rule(
        rule_id="boundary-test",
        name="Boundary test",
        project_gid="123",
        conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=3))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    tasks = [exactly_3_days, just_under_3_days]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Exactly 3 days should match, just under should not
    assert len(matching) == 1
    assert matching[0].gid == "exact-3"


@pytest.mark.integration
def test_stale_trigger_missing_modified_at(now: datetime) -> None:
    """Test that tasks without modified_at are skipped gracefully."""
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    task_no_date = MockTask(gid="no-date", name="No modified_at")

    rule = Rule(
        rule_id="no-date-test",
        name="Test missing date",
        project_gid="123",
        conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=3))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    matching = evaluator.evaluate_conditions(rule, [task_no_date])

    # Task without modified_at should not match
    assert len(matching) == 0


# ============================================================================
# Deadline Trigger Tests (using mock tasks)
# ============================================================================


@pytest.mark.integration
def test_deadline_trigger_matches_due_soon_tasks(
    mock_due_soon_task: MockTask,
    mock_fresh_task: MockTask,
    now: datetime,
) -> None:
    """Test deadline trigger matches tasks due within threshold.

    Uses mock tasks with controlled due_on values.
    """
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    # Create a task due in 14 days (outside threshold)
    due_later_task = MockTask(
        gid="due-later",
        name="Due later",
        due_on=(now + timedelta(days=14)).strftime("%Y-%m-%d"),
    )

    # Rule: tasks due within 7 days
    rule = Rule(
        rule_id="deadline-test",
        name="Find tasks due soon",
        project_gid="123",
        conditions=[RuleCondition(deadline=TriggerDeadlineConfig(days=7))],
        action=ActionConfig(type="add_comment", params={"text": "Due soon!"}),
    )

    tasks = [mock_due_soon_task, mock_fresh_task, due_later_task]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Only the task due in 3 days should match 7-day threshold
    assert len(matching) == 1
    assert matching[0].gid == mock_due_soon_task.gid


@pytest.mark.integration
def test_deadline_trigger_includes_overdue(now: datetime) -> None:
    """Test that deadline trigger includes overdue tasks.

    Tasks with due dates in the past should also match.
    """
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    overdue_task = MockTask(
        gid="overdue",
        name="Overdue task",
        due_on=(now - timedelta(days=5)).strftime("%Y-%m-%d"),
    )

    rule = Rule(
        rule_id="overdue-test",
        name="Find overdue tasks",
        project_gid="123",
        conditions=[RuleCondition(deadline=TriggerDeadlineConfig(days=7))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    matching = evaluator.evaluate_conditions(rule, [overdue_task])

    # Overdue task should match (due <= now + threshold)
    assert len(matching) == 1
    assert matching[0].gid == "overdue"


@pytest.mark.integration
def test_deadline_trigger_no_due_date_skipped(now: datetime) -> None:
    """Test that tasks without due dates are skipped."""
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    task_no_due = MockTask(gid="no-due", name="No due date")

    rule = Rule(
        rule_id="no-due-test",
        name="Test missing due date",
        project_gid="123",
        conditions=[RuleCondition(deadline=TriggerDeadlineConfig(days=7))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    matching = evaluator.evaluate_conditions(rule, [task_no_due])

    # Task without due date should not match
    assert len(matching) == 0


@pytest.mark.integration
def test_deadline_trigger_due_at_preferred_over_due_on(now: datetime) -> None:
    """Test that due_at (datetime) is preferred over due_on (date).

    When both are present, due_at should be used for more precise matching.
    """
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    # Task with both due_at and due_on
    task_both = MockTask(
        gid="both-dates",
        name="Has both dates",
        due_at=(now + timedelta(days=2)).isoformat(),
        due_on=(now + timedelta(days=10)).strftime("%Y-%m-%d"),  # Would be outside threshold
    )

    rule = Rule(
        rule_id="due-at-test",
        name="Test due_at priority",
        project_gid="123",
        conditions=[RuleCondition(deadline=TriggerDeadlineConfig(days=5))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    matching = evaluator.evaluate_conditions(rule, [task_both])

    # Should match based on due_at (2 days), not due_on (10 days)
    assert len(matching) == 1


# ============================================================================
# Age Trigger Tests (using mock tasks)
# ============================================================================


@pytest.mark.integration
def test_age_trigger_matches_old_open_tasks(
    mock_old_open_task: MockTask,
    mock_old_completed_task: MockTask,
    mock_fresh_task: MockTask,
) -> None:
    """Test age trigger matches old open tasks but not completed ones.

    Age trigger requires: created >= N days ago AND not completed.
    """
    evaluator = TriggerEvaluator()

    # Rule: tasks created 90+ days ago, still open
    rule = Rule(
        rule_id="age-test",
        name="Find old open tasks",
        project_gid="123",
        conditions=[RuleCondition(age=TriggerAgeConfig(days=90))],
        action=ActionConfig(type="change_section", params={"section_gid": "archive"}),
    )

    tasks = [mock_old_open_task, mock_old_completed_task, mock_fresh_task]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Only the old open task should match
    assert len(matching) == 1
    assert matching[0].gid == mock_old_open_task.gid


@pytest.mark.integration
def test_age_trigger_completed_tasks_excluded(
    mock_old_completed_task: MockTask,
) -> None:
    """Test that completed tasks are always excluded from age trigger."""
    evaluator = TriggerEvaluator()

    rule = Rule(
        rule_id="completed-test",
        name="Test completed exclusion",
        project_gid="123",
        conditions=[RuleCondition(age=TriggerAgeConfig(days=90))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    matching = evaluator.evaluate_conditions(rule, [mock_old_completed_task])

    # Completed task should not match, even if old enough
    assert len(matching) == 0


@pytest.mark.integration
def test_age_trigger_missing_created_at_skipped(now: datetime) -> None:
    """Test that tasks without created_at are skipped."""
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    task_no_created = MockTask(gid="no-created", name="No created_at", completed=False)

    rule = Rule(
        rule_id="no-created-test",
        name="Test missing created_at",
        project_gid="123",
        conditions=[RuleCondition(age=TriggerAgeConfig(days=90))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    matching = evaluator.evaluate_conditions(rule, [task_no_created])

    # Task without created_at should not match
    assert len(matching) == 0


# ============================================================================
# AND Composition Tests
# ============================================================================


@pytest.mark.integration
def test_multiple_conditions_and_composition(now: datetime) -> None:
    """Test that multiple conditions are combined with AND logic.

    A task must match ALL conditions to be included in results.
    """
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    # Task that is both stale AND old AND open
    stale_and_old = MockTask(
        gid="stale-and-old",
        name="Stale and old",
        modified_at=(now - timedelta(days=10)).isoformat(),
        created_at=(now - timedelta(days=100)).isoformat(),
        completed=False,
    )

    # Task that is stale but not old enough
    stale_only = MockTask(
        gid="stale-only",
        name="Stale but not old",
        modified_at=(now - timedelta(days=10)).isoformat(),
        created_at=(now - timedelta(days=30)).isoformat(),
        completed=False,
    )

    # Task that is old but not stale
    old_only = MockTask(
        gid="old-only",
        name="Old but not stale",
        modified_at=now.isoformat(),
        created_at=(now - timedelta(days=100)).isoformat(),
        completed=False,
    )

    # Rule with multiple conditions: stale AND age
    rule = Rule(
        rule_id="compound-test",
        name="Test AND composition",
        project_gid="123",
        conditions=[
            RuleCondition(stale=TriggerStaleConfig(field="any", days=7)),
            RuleCondition(age=TriggerAgeConfig(days=90)),
        ],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    tasks = [stale_and_old, stale_only, old_only]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Only the task that matches BOTH conditions should be included
    assert len(matching) == 1
    assert matching[0].gid == "stale-and-old"


@pytest.mark.integration
def test_single_condition_with_multiple_triggers(now: datetime) -> None:
    """Test a single condition with multiple trigger types.

    Within one RuleCondition, all triggers must match.
    """
    from tests.integration.automation.polling.conftest import MockTask

    evaluator = TriggerEvaluator()

    # Task that is both stale AND has upcoming deadline
    stale_with_deadline = MockTask(
        gid="stale-deadline",
        name="Stale with deadline",
        modified_at=(now - timedelta(days=10)).isoformat(),
        due_on=(now + timedelta(days=5)).strftime("%Y-%m-%d"),
    )

    # Task that is stale but no deadline
    stale_no_deadline = MockTask(
        gid="stale-no-deadline",
        name="Stale without deadline",
        modified_at=(now - timedelta(days=10)).isoformat(),
    )

    # Rule with one condition containing both stale AND deadline triggers
    rule = Rule(
        rule_id="multi-trigger-test",
        name="Test multi-trigger condition",
        project_gid="123",
        conditions=[
            RuleCondition(
                stale=TriggerStaleConfig(field="any", days=7),
                deadline=TriggerDeadlineConfig(days=7),
            ),
        ],
        action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
    )

    tasks = [stale_with_deadline, stale_no_deadline]
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Only task matching BOTH stale AND deadline should match
    assert len(matching) == 1
    assert matching[0].gid == "stale-deadline"


# ============================================================================
# Empty Conditions Test
# ============================================================================


@pytest.mark.integration
def test_no_conditions_without_schedule_rejected(
    mock_stale_task: MockTask,
    mock_fresh_task: MockTask,
) -> None:
    """Test that a rule with no conditions AND no schedule is rejected.

    Empty conditions are only allowed for schedule-driven workflow rules.
    Condition-based rules must have at least one condition.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        Rule(
            rule_id="no-conditions",
            name="No conditions rule",
            project_gid="123",
            conditions=[],  # Empty conditions list
            action=ActionConfig(type="add_tag", params={"tag_gid": "456"}),
        )

    assert "at least one condition or a schedule" in str(exc_info.value).lower()


# ============================================================================
# Real API Integration Tests
# ============================================================================


@pytest.mark.integration
async def test_evaluate_real_project_tasks(
    asana_client,
    test_project_gid: str,
) -> None:
    """Test TriggerEvaluator with real tasks from an Asana project.

    This test fetches actual tasks from the test project and runs
    trigger evaluation on them. It validates that:
    - Tasks are fetched successfully
    - Evaluation runs without errors
    - Results are returned (may be empty if no tasks match)
    """
    evaluator = TriggerEvaluator()

    # Fetch tasks from the test project
    tasks_iter = asana_client.tasks.list_async(
        project=test_project_gid,
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
    tasks = await tasks_iter.collect_all_async()

    if not tasks:
        pytest.skip("No tasks in test project")

    # Create a rule that would likely match some tasks
    rule = Rule(
        rule_id="real-project-test",
        name="Test with real tasks",
        project_gid=test_project_gid,
        conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=1))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "test"}),
    )

    # Evaluate - should not raise any errors
    matching = evaluator.evaluate_conditions(rule, tasks)

    # Verify results are a list
    assert isinstance(matching, list)

    # Each matching task should have expected attributes
    for task in matching:
        assert hasattr(task, "gid")
        assert hasattr(task, "modified_at")


@pytest.mark.integration
async def test_evaluate_task_with_real_dates(
    asana_client,
    test_task,
) -> None:
    """Test TriggerEvaluator with a freshly created task.

    A freshly created task should:
    - NOT match stale triggers (just created)
    - NOT match deadline triggers (no due date by default)
    - NOT match age triggers (just created)
    """
    evaluator = TriggerEvaluator()

    # Fetch the fresh task with all required fields
    task = await asana_client.tasks.get_async(
        test_task.gid,
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

    # Test stale trigger - fresh task should NOT match
    stale_rule = Rule(
        rule_id="stale-fresh-test",
        name="Test stale on fresh task",
        project_gid="123",
        conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=1))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "test"}),
    )
    stale_matches = evaluator.evaluate_conditions(stale_rule, [task])
    assert len(stale_matches) == 0, "Fresh task should not match stale trigger"

    # Test age trigger - fresh task should NOT match
    age_rule = Rule(
        rule_id="age-fresh-test",
        name="Test age on fresh task",
        project_gid="123",
        conditions=[RuleCondition(age=TriggerAgeConfig(days=1))],
        action=ActionConfig(type="add_tag", params={"tag_gid": "test"}),
    )
    age_matches = evaluator.evaluate_conditions(age_rule, [task])
    assert len(age_matches) == 0, "Fresh task should not match age trigger"
