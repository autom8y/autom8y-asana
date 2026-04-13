"""Tests for polling automation trigger evaluator.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for trigger evaluation logic
that determines which tasks match automation rule conditions.

Covers:
- Stale trigger matches old tasks
- Stale trigger skips recent tasks
- Deadline trigger matches tasks due soon
- Deadline trigger skips tasks due far away
- Age trigger matches old incomplete tasks
- Age trigger skips completed tasks
- AND composition requires all conditions match
- Empty conditions returns all tasks
- Missing date fields handled gracefully
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from autom8_asana.automation.polling.config_schema import (
    ActionConfig,
    Rule,
    RuleCondition,
    ScheduleConfig,
    TriggerAgeConfig,
    TriggerDeadlineConfig,
    TriggerStaleConfig,
)
from autom8_asana.automation.polling.trigger_evaluator import TriggerEvaluator

from .conftest import MockTask


class TestTriggerEvaluatorStaleTrigger:
    """Tests for stale trigger evaluation."""

    @pytest.fixture
    def evaluator(self) -> TriggerEvaluator:
        """Create TriggerEvaluator instance."""
        return TriggerEvaluator()

    @pytest.fixture
    def stale_rule(self) -> Rule:
        """Rule with stale trigger (3 days)."""
        return Rule(
            rule_id="stale-check",
            name="Stale Check",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "stale"}),
        )

    def test_stale_trigger_matches_old_tasks(
        self,
        evaluator: TriggerEvaluator,
        stale_rule: Rule,
        now: datetime,
    ) -> None:
        """Stale trigger matches tasks not modified in N+ days."""
        # Task modified 5 days ago (stale at 3-day threshold)
        stale_task = MockTask(
            gid="task-1",
            name="Stale Task",
            modified_at=(now - timedelta(days=5)).isoformat(),
        )

        matching = evaluator.evaluate_conditions(stale_rule, [stale_task])

        assert len(matching) == 1
        assert matching[0].gid == "task-1"

    def test_stale_trigger_skips_recent_tasks(
        self,
        evaluator: TriggerEvaluator,
        stale_rule: Rule,
        now: datetime,
    ) -> None:
        """Stale trigger skips tasks modified recently."""
        # Task modified 1 day ago (not stale at 3-day threshold)
        fresh_task = MockTask(
            gid="task-2",
            name="Fresh Task",
            modified_at=(now - timedelta(days=1)).isoformat(),
        )

        matching = evaluator.evaluate_conditions(stale_rule, [fresh_task])

        assert len(matching) == 0

    def test_stale_trigger_boundary_condition(
        self,
        evaluator: TriggerEvaluator,
        stale_rule: Rule,
        now: datetime,
    ) -> None:
        """Stale trigger matches at exactly N days threshold."""
        # Task modified exactly 3 days ago (should match)
        boundary_task = MockTask(
            gid="task-boundary",
            name="Boundary Task",
            modified_at=(now - timedelta(days=3)).isoformat(),
        )

        matching = evaluator.evaluate_conditions(stale_rule, [boundary_task])

        assert len(matching) == 1

    def test_stale_trigger_handles_missing_modified_at(
        self,
        evaluator: TriggerEvaluator,
        stale_rule: Rule,
    ) -> None:
        """Stale trigger gracefully handles tasks without modified_at."""
        task_no_date = MockTask(
            gid="task-no-date",
            name="No Date Task",
            modified_at=None,
        )

        matching = evaluator.evaluate_conditions(stale_rule, [task_no_date])

        # Should skip task without error
        assert len(matching) == 0

    def test_stale_trigger_handles_invalid_date_format(
        self,
        evaluator: TriggerEvaluator,
        stale_rule: Rule,
    ) -> None:
        """Stale trigger handles invalid date format gracefully."""
        task_bad_date = MockTask(
            gid="task-bad-date",
            name="Bad Date Task",
            modified_at="not-a-date",
        )

        matching = evaluator.evaluate_conditions(stale_rule, [task_bad_date])

        # Should skip task without error
        assert len(matching) == 0

    def test_stale_trigger_filters_mixed_tasks(
        self,
        evaluator: TriggerEvaluator,
        stale_rule: Rule,
        sample_tasks: list[MockTask],
    ) -> None:
        """Stale trigger correctly filters a mix of stale and fresh tasks."""
        matching = evaluator.evaluate_conditions(stale_rule, sample_tasks)

        # Should find tasks modified 3+ days ago
        matching_gids = {t.gid for t in matching}
        # task-1 (5 days), task-5 (50 days), task-7 (5 days) are stale
        assert "task-1" in matching_gids
        assert "task-5" in matching_gids
        assert "task-7" in matching_gids
        # task-2, task-3, task-4 are fresh, task-6 is 10 days ago, task-8 has no date
        assert "task-2" not in matching_gids
        assert "task-8" not in matching_gids


class TestTriggerEvaluatorDeadlineTrigger:
    """Tests for deadline trigger evaluation."""

    @pytest.fixture
    def evaluator(self) -> TriggerEvaluator:
        """Create TriggerEvaluator instance."""
        return TriggerEvaluator()

    @pytest.fixture
    def deadline_rule(self) -> Rule:
        """Rule with deadline trigger (7 days)."""
        return Rule(
            rule_id="deadline-check",
            name="Deadline Check",
            project_gid="123",
            conditions=[RuleCondition(deadline=TriggerDeadlineConfig(days=7))],
            action=ActionConfig(type="add_comment", params={"text": "Due soon!"}),
        )

    def test_deadline_trigger_matches_tasks_due_soon(
        self,
        evaluator: TriggerEvaluator,
        deadline_rule: Rule,
        now: datetime,
    ) -> None:
        """Deadline trigger matches tasks due within N days."""
        # Task due in 3 days (within 7-day threshold)
        due_soon_task = MockTask(
            gid="task-due-soon",
            name="Due Soon",
            modified_at=now.isoformat(),
            due_on=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
        )

        matching = evaluator.evaluate_conditions(deadline_rule, [due_soon_task])

        assert len(matching) == 1
        assert matching[0].gid == "task-due-soon"

    def test_deadline_trigger_skips_tasks_due_far_away(
        self,
        evaluator: TriggerEvaluator,
        deadline_rule: Rule,
        now: datetime,
    ) -> None:
        """Deadline trigger skips tasks due more than N days away."""
        # Task due in 14 days (beyond 7-day threshold)
        due_later_task = MockTask(
            gid="task-due-later",
            name="Due Later",
            modified_at=now.isoformat(),
            due_on=(now + timedelta(days=14)).strftime("%Y-%m-%d"),
        )

        matching = evaluator.evaluate_conditions(deadline_rule, [due_later_task])

        assert len(matching) == 0

    def test_deadline_trigger_matches_overdue_tasks(
        self,
        evaluator: TriggerEvaluator,
        deadline_rule: Rule,
        now: datetime,
    ) -> None:
        """Deadline trigger matches already overdue tasks."""
        # Task was due 2 days ago (overdue, still within threshold logic)
        overdue_task = MockTask(
            gid="task-overdue",
            name="Overdue Task",
            modified_at=now.isoformat(),
            due_on=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
        )

        matching = evaluator.evaluate_conditions(deadline_rule, [overdue_task])

        # Overdue tasks are "due within N days" (they're past due)
        assert len(matching) == 1

    def test_deadline_trigger_uses_due_at_over_due_on(
        self,
        evaluator: TriggerEvaluator,
        deadline_rule: Rule,
        now: datetime,
    ) -> None:
        """Deadline trigger prefers due_at (datetime) over due_on (date)."""
        # Task with both due_at and due_on - due_at should be used
        task_with_both = MockTask(
            gid="task-both-dates",
            name="Both Dates",
            modified_at=now.isoformat(),
            due_on=(now + timedelta(days=14)).strftime("%Y-%m-%d"),  # Far away
            due_at=(now + timedelta(days=3)).isoformat(),  # Soon
        )

        matching = evaluator.evaluate_conditions(deadline_rule, [task_with_both])

        # Should match because due_at is soon (even though due_on is far)
        assert len(matching) == 1

    def test_deadline_trigger_handles_missing_due_date(
        self,
        evaluator: TriggerEvaluator,
        deadline_rule: Rule,
        now: datetime,
    ) -> None:
        """Deadline trigger skips tasks without due date."""
        task_no_due = MockTask(
            gid="task-no-due",
            name="No Due Date",
            modified_at=now.isoformat(),
        )

        matching = evaluator.evaluate_conditions(deadline_rule, [task_no_due])

        assert len(matching) == 0

    def test_deadline_trigger_boundary_condition(
        self,
        evaluator: TriggerEvaluator,
        deadline_rule: Rule,
        now: datetime,
    ) -> None:
        """Deadline trigger matches at exactly N days threshold."""
        # Task due exactly 7 days from now
        boundary_task = MockTask(
            gid="task-boundary",
            name="Boundary Task",
            modified_at=now.isoformat(),
            due_on=(now + timedelta(days=7)).strftime("%Y-%m-%d"),
        )

        matching = evaluator.evaluate_conditions(deadline_rule, [boundary_task])

        assert len(matching) == 1


class TestTriggerEvaluatorAgeTrigger:
    """Tests for age trigger evaluation."""

    @pytest.fixture
    def evaluator(self) -> TriggerEvaluator:
        """Create TriggerEvaluator instance."""
        return TriggerEvaluator()

    @pytest.fixture
    def age_rule(self) -> Rule:
        """Rule with age trigger (90 days)."""
        return Rule(
            rule_id="age-check",
            name="Age Check",
            project_gid="123",
            conditions=[RuleCondition(age=TriggerAgeConfig(days=90))],
            action=ActionConfig(type="change_section", params={"section": "Archive"}),
        )

    def test_age_trigger_matches_old_incomplete_tasks(
        self,
        evaluator: TriggerEvaluator,
        age_rule: Rule,
        now: datetime,
    ) -> None:
        """Age trigger matches tasks created N+ days ago that are not completed."""
        # Task created 100 days ago, not completed
        old_open_task = MockTask(
            gid="task-old-open",
            name="Old Open Task",
            created_at=(now - timedelta(days=100)).isoformat(),
            completed=False,
        )

        matching = evaluator.evaluate_conditions(age_rule, [old_open_task])

        assert len(matching) == 1
        assert matching[0].gid == "task-old-open"

    def test_age_trigger_skips_completed_tasks(
        self,
        evaluator: TriggerEvaluator,
        age_rule: Rule,
        now: datetime,
    ) -> None:
        """Age trigger skips old tasks that are completed."""
        # Task created 100 days ago, but completed
        old_completed_task = MockTask(
            gid="task-old-completed",
            name="Old Completed Task",
            created_at=(now - timedelta(days=100)).isoformat(),
            completed=True,
        )

        matching = evaluator.evaluate_conditions(age_rule, [old_completed_task])

        assert len(matching) == 0

    def test_age_trigger_skips_newer_tasks(
        self,
        evaluator: TriggerEvaluator,
        age_rule: Rule,
        now: datetime,
    ) -> None:
        """Age trigger skips tasks created less than N days ago."""
        # Task created 30 days ago (below 90-day threshold)
        newer_task = MockTask(
            gid="task-newer",
            name="Newer Task",
            created_at=(now - timedelta(days=30)).isoformat(),
            completed=False,
        )

        matching = evaluator.evaluate_conditions(age_rule, [newer_task])

        assert len(matching) == 0

    def test_age_trigger_handles_missing_created_at(
        self,
        evaluator: TriggerEvaluator,
        age_rule: Rule,
    ) -> None:
        """Age trigger skips tasks without created_at."""
        task_no_created = MockTask(
            gid="task-no-created",
            name="No Created Date",
            created_at=None,
            completed=False,
        )

        matching = evaluator.evaluate_conditions(age_rule, [task_no_created])

        assert len(matching) == 0

    def test_age_trigger_boundary_condition(
        self,
        evaluator: TriggerEvaluator,
        age_rule: Rule,
        now: datetime,
    ) -> None:
        """Age trigger matches at exactly N days threshold."""
        # Task created exactly 90 days ago
        boundary_task = MockTask(
            gid="task-boundary",
            name="Boundary Task",
            created_at=(now - timedelta(days=90)).isoformat(),
            completed=False,
        )

        matching = evaluator.evaluate_conditions(age_rule, [boundary_task])

        assert len(matching) == 1


class TestTriggerEvaluatorANDComposition:
    """Tests for AND composition of multiple conditions."""

    @pytest.fixture
    def evaluator(self) -> TriggerEvaluator:
        """Create TriggerEvaluator instance."""
        return TriggerEvaluator()

    def test_and_composition_requires_all_conditions_match(
        self,
        evaluator: TriggerEvaluator,
        now: datetime,
    ) -> None:
        """Task must match ALL conditions when multiple are specified."""
        # Rule with both stale (3 days) and age (30 days) conditions
        multi_condition_rule = Rule(
            rule_id="multi-check",
            name="Multi Condition Check",
            project_gid="123",
            conditions=[
                RuleCondition(stale=TriggerStaleConfig(field="Section", days=3)),
                RuleCondition(age=TriggerAgeConfig(days=30)),
            ],
            action=ActionConfig(type="add_tag", params={"tag": "escalate"}),
        )

        # Task that is stale (modified 5 days ago) but NOT old (created 10 days ago)
        stale_but_new = MockTask(
            gid="task-stale-new",
            name="Stale But New",
            modified_at=(now - timedelta(days=5)).isoformat(),
            created_at=(now - timedelta(days=10)).isoformat(),
            completed=False,
        )

        # Task that is old (created 60 days ago) but NOT stale (modified today)
        old_but_fresh = MockTask(
            gid="task-old-fresh",
            name="Old But Fresh",
            modified_at=now.isoformat(),
            created_at=(now - timedelta(days=60)).isoformat(),
            completed=False,
        )

        # Task that matches BOTH conditions
        stale_and_old = MockTask(
            gid="task-stale-old",
            name="Stale And Old",
            modified_at=(now - timedelta(days=10)).isoformat(),
            created_at=(now - timedelta(days=60)).isoformat(),
            completed=False,
        )

        tasks = [stale_but_new, old_but_fresh, stale_and_old]
        matching = evaluator.evaluate_conditions(multi_condition_rule, tasks)

        # Only the task matching both conditions should be returned
        assert len(matching) == 1
        assert matching[0].gid == "task-stale-old"

    def test_multiple_triggers_in_single_condition(
        self,
        evaluator: TriggerEvaluator,
        now: datetime,
    ) -> None:
        """Single condition with multiple triggers requires all to match."""
        # Single condition with both stale AND deadline triggers
        combined_trigger_rule = Rule(
            rule_id="combined-check",
            name="Combined Trigger Check",
            project_gid="123",
            conditions=[
                RuleCondition(
                    stale=TriggerStaleConfig(field="Section", days=3),
                    deadline=TriggerDeadlineConfig(days=7),
                )
            ],
            action=ActionConfig(type="add_tag", params={"tag": "urgent"}),
        )

        # Task that is stale AND due soon
        matches_both = MockTask(
            gid="task-both",
            name="Matches Both",
            modified_at=(now - timedelta(days=5)).isoformat(),
            due_on=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
        )

        # Task that is stale but not due soon
        stale_only = MockTask(
            gid="task-stale-only",
            name="Stale Only",
            modified_at=(now - timedelta(days=5)).isoformat(),
            due_on=(now + timedelta(days=30)).strftime("%Y-%m-%d"),
        )

        tasks = [matches_both, stale_only]
        matching = evaluator.evaluate_conditions(combined_trigger_rule, tasks)

        assert len(matching) == 1
        assert matching[0].gid == "task-both"


class TestTriggerEvaluatorEmptyConditions:
    """Tests for edge case of empty conditions."""

    @pytest.fixture
    def evaluator(self) -> TriggerEvaluator:
        """Create TriggerEvaluator instance."""
        return TriggerEvaluator()

    def test_empty_conditions_returns_all_tasks(
        self,
        evaluator: TriggerEvaluator,
        sample_tasks: list[MockTask],
    ) -> None:
        """Rule with empty conditions list returns all tasks."""
        # This is an edge case - normally rules have conditions
        # But the evaluator should handle it gracefully
        empty_conditions_rule = Rule(
            rule_id="all-tasks",
            name="All Tasks",
            project_gid="123",
            conditions=[],  # Empty conditions list — valid with schedule
            action=ActionConfig(type="workflow", params={"workflow_id": "test"}),
            schedule=ScheduleConfig(frequency="weekly", day_of_week="monday"),
        )

        matching = evaluator.evaluate_conditions(empty_conditions_rule, sample_tasks)

        # Should return all tasks
        assert len(matching) == len(sample_tasks)

    def test_empty_task_list_returns_empty(
        self,
        evaluator: TriggerEvaluator,
    ) -> None:
        """Evaluation with empty task list returns empty result."""
        rule = Rule(
            rule_id="test",
            name="Test",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        matching = evaluator.evaluate_conditions(rule, [])

        assert matching == []


class TestTriggerEvaluatorEdgeCases:
    """Edge case tests for trigger evaluator."""

    @pytest.fixture
    def evaluator(self) -> TriggerEvaluator:
        """Create TriggerEvaluator instance."""
        return TriggerEvaluator()

    def test_task_with_z_suffix_datetime(
        self,
        evaluator: TriggerEvaluator,
        now: datetime,
    ) -> None:
        """Task with Z suffix datetime parses correctly."""
        rule = Rule(
            rule_id="test",
            name="Test",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        # ISO format with Z suffix (common from APIs)
        task = MockTask(
            gid="task-z",
            name="Z Suffix Task",
            modified_at="2024-01-01T12:00:00.000Z",
        )

        # Should not raise exception
        matching = evaluator.evaluate_conditions(rule, [task])
        # Result depends on whether the date is stale relative to 'now'

    def test_task_with_timezone_offset(
        self,
        evaluator: TriggerEvaluator,
        now: datetime,
    ) -> None:
        """Task with timezone offset parses correctly."""
        rule = Rule(
            rule_id="test",
            name="Test",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        # ISO format with explicit timezone offset
        task = MockTask(
            gid="task-tz",
            name="TZ Offset Task",
            modified_at="2024-01-01T12:00:00+05:00",
        )

        # Should not raise exception
        matching = evaluator.evaluate_conditions(rule, [task])

    def test_task_with_date_only_modified_at(
        self,
        evaluator: TriggerEvaluator,
        now: datetime,
    ) -> None:
        """Task with date-only modified_at (no time) parses correctly."""
        rule = Rule(
            rule_id="test",
            name="Test",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        # Date only (no time component) - should treat as midnight UTC
        stale_date = (now - timedelta(days=10)).strftime("%Y-%m-%d")
        task = MockTask(
            gid="task-date-only",
            name="Date Only Task",
            modified_at=stale_date,
        )

        matching = evaluator.evaluate_conditions(rule, [task])

        # Should match as it's stale
        assert len(matching) == 1

    def test_task_attribute_access_graceful(
        self,
        evaluator: TriggerEvaluator,
    ) -> None:
        """Evaluator gracefully handles tasks without expected attributes."""
        rule = Rule(
            rule_id="test",
            name="Test",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        # Plain object without the expected attributes
        class PlainTask:
            def __init__(self):
                self.gid = "task-plain"
                self.name = "Plain Task"
                # No modified_at, created_at, etc.

        task = PlainTask()
        matching = evaluator.evaluate_conditions(rule, [task])

        # Should not raise, just skip the task
        assert len(matching) == 0
