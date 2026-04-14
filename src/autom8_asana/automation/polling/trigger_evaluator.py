"""Trigger evaluator for polling-based automation rules.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Evaluates rule conditions against tasks
to determine which tasks match for action execution.

Key responsibilities:
- Evaluate stale triggers (modified_at >= N days ago)
- Evaluate deadline triggers (due_on/due_at within N days)
- Evaluate age triggers (created_at >= N days ago AND not completed)
- AND composition: All conditions in a rule must match

Example:
    from autom8_asana.automation.polling import TriggerEvaluator, Rule

    evaluator = TriggerEvaluator()
    matching_tasks = evaluator.evaluate_conditions(rule, tasks)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.automation.polling.config_schema import (
        Rule,
        RuleCondition,
        TriggerAgeConfig,
        TriggerDeadlineConfig,
        TriggerStaleConfig,
    )

__all__ = ["TriggerEvaluator"]

logger = get_logger(__name__)


class TriggerEvaluator:
    """Evaluates rule conditions against tasks.

    This class provides methods for filtering tasks based on automation rule
    conditions. It handles:

    - Stale triggers: Tasks not modified in N days
    - Deadline triggers: Tasks due within N days
    - Age triggers: Tasks created N+ days ago that are still open
    - AND composition: All conditions must match

    All date comparisons use UTC timezone for consistency.

    Example:
        evaluator = TriggerEvaluator()
        matching = evaluator.evaluate_conditions(rule, tasks)
        for task in matching:
            print(f"Task {task.gid} matches rule {rule.rule_id}")
    """

    def evaluate_conditions(self, rule: Rule, tasks: list[Any]) -> list[Any]:
        """Return tasks that match ALL conditions in the rule (AND composition).

        Evaluates each task against all conditions in the rule. A task is
        included in the result only if it matches every condition.

        Args:
            rule: The automation rule containing conditions to evaluate.
            tasks: List of task objects to filter. Expected to have Task-like
                attributes (modified_at, created_at, due_on, due_at, completed).

        Returns:
            List of tasks that match ALL conditions in the rule.

        Example:
            rule = Rule(
                rule_id="stale-check",
                name="Find stale tasks",
                project_gid="123",
                conditions=[RuleCondition(stale=TriggerStaleConfig(field="any", days=7))],
                action=ActionConfig(type="add_tag", params={"tag": "stale"}),
            )
            matching = evaluator.evaluate_conditions(rule, tasks)
        """
        if not rule.conditions:
            logger.debug("rule_no_conditions_returning_all_tasks", rule_id=rule.rule_id)
            return list(tasks)

        now = datetime.now(UTC)
        matching_tasks: list[Any] = []

        for task in tasks:
            if self._task_matches_all_conditions(task, rule.conditions, now):
                matching_tasks.append(task)

        logger.debug(
            "rule_evaluation_complete",
            rule_id=rule.rule_id,
            matched_count=len(matching_tasks),
            total_count=len(tasks),
        )
        return matching_tasks

    def _task_matches_all_conditions(
        self,
        task: Any,
        conditions: list[RuleCondition],
        now: datetime,
    ) -> bool:
        """Check if a task matches ALL conditions (AND composition).

        Args:
            task: Task object to evaluate.
            conditions: List of conditions to check.
            now: Current UTC datetime for date comparisons.

        Returns:
            True if task matches all conditions, False otherwise.
        """
        return all(self._task_matches_condition(task, condition, now) for condition in conditions)

    def _task_matches_condition(
        self,
        task: Any,
        condition: RuleCondition,
        now: datetime,
    ) -> bool:
        """Check if a task matches a single condition.

        A condition may have multiple trigger types. For a condition to match,
        ALL specified triggers within that condition must match.

        Args:
            task: Task object to evaluate.
            condition: Single condition with one or more trigger types.
            now: Current UTC datetime for date comparisons.

        Returns:
            True if task matches the condition, False otherwise.
        """
        # All specified triggers in a condition must match
        if condition.stale is not None and not self._evaluate_stale_trigger(
            task, condition.stale, now
        ):
            return False

        if condition.deadline is not None and not self._evaluate_deadline_trigger(
            task, condition.deadline, now
        ):
            return False

        return condition.age is None or self._evaluate_age_trigger(task, condition.age, now)

    def _evaluate_stale_trigger(
        self,
        task: Any,
        config: TriggerStaleConfig,
        now: datetime,
    ) -> bool:
        """Evaluate stale trigger: task not modified in N days.

        Per TDD: MVP checks modified_at only (field parameter deferred).

        Args:
            task: Task object with modified_at attribute.
            config: Stale trigger configuration (field, days).
            now: Current UTC datetime for comparison.

        Returns:
            True if task is stale (modified_at >= N days ago), False otherwise.
            Returns False if modified_at is missing/None.
        """
        modified_at_str = getattr(task, "modified_at", None)
        if modified_at_str is None:
            logger.debug(
                "task_missing_modified_at_skipping_stale_check",
                task_gid=getattr(task, "gid", "unknown"),
            )
            return False

        modified_at = self._parse_iso_datetime(modified_at_str)
        if modified_at is None:
            logger.warning(
                "task_invalid_modified_at_format",
                task_gid=getattr(task, "gid", "unknown"),
                modified_at_value=modified_at_str,
            )
            return False

        threshold = now - timedelta(days=config.days)
        return modified_at <= threshold

    def _evaluate_deadline_trigger(
        self,
        task: Any,
        config: TriggerDeadlineConfig,
        now: datetime,
    ) -> bool:
        """Evaluate deadline trigger: task due within N days.

        Checks due_at first (more specific), then due_on if due_at is not set.

        Args:
            task: Task object with due_on/due_at attributes.
            config: Deadline trigger configuration (days).
            now: Current UTC datetime for comparison.

        Returns:
            True if task is due within N days, False otherwise.
            Returns False if no due date is set.
        """
        # Try due_at first (datetime), then due_on (date)
        due_at_str = getattr(task, "due_at", None)
        due_on_str = getattr(task, "due_on", None)

        due_datetime: datetime | None = None

        if due_at_str:
            due_datetime = self._parse_iso_datetime(due_at_str)
        elif due_on_str:
            due_datetime = self._parse_iso_date(due_on_str)

        if due_datetime is None:
            logger.debug(
                "task_no_due_date_skipping_deadline_check",
                task_gid=getattr(task, "gid", "unknown"),
            )
            return False

        threshold = now + timedelta(days=config.days)
        # Task matches if due date is within the threshold (now <= due <= threshold)
        return due_datetime <= threshold

    def _evaluate_age_trigger(
        self,
        task: Any,
        config: TriggerAgeConfig,
        now: datetime,
    ) -> bool:
        """Evaluate age trigger: task created N+ days ago and not completed.

        Args:
            task: Task object with created_at and completed attributes.
            config: Age trigger configuration (days).
            now: Current UTC datetime for comparison.

        Returns:
            True if task is old enough AND not completed, False otherwise.
            Returns False if created_at is missing/None.
        """
        # Check completion status first (quick exit)
        completed = getattr(task, "completed", None)
        if completed is True:
            logger.debug(
                "task_completed_skipping_age_check",
                task_gid=getattr(task, "gid", "unknown"),
            )
            return False

        created_at_str = getattr(task, "created_at", None)
        if created_at_str is None:
            logger.debug(
                "task_missing_created_at_skipping_age_check",
                task_gid=getattr(task, "gid", "unknown"),
            )
            return False

        created_at = self._parse_iso_datetime(created_at_str)
        if created_at is None:
            logger.warning(
                "task_invalid_created_at_format",
                task_gid=getattr(task, "gid", "unknown"),
                created_at_value=created_at_str,
            )
            return False

        threshold = now - timedelta(days=config.days)
        return created_at <= threshold

    def _parse_iso_datetime(self, value: str) -> datetime | None:
        """Parse ISO 8601 datetime string to timezone-aware datetime.

        Handles both formats:
        - Full datetime: "2024-01-15T10:30:00.000Z"
        - Date only: "2024-01-15"

        Args:
            value: ISO 8601 formatted datetime string.

        Returns:
            Timezone-aware datetime in UTC, or None if parsing fails.
        """
        if not value:
            return None

        try:
            # Try full ISO format with timezone
            if "T" in value:
                # Handle Z suffix and +00:00 format
                clean = value.replace("Z", "+00:00")
                return datetime.fromisoformat(clean)
            else:
                # Date-only format: treat as start of day UTC
                return self._parse_iso_date(value)
        except (ValueError, TypeError):
            return None

    def _parse_iso_date(self, value: str) -> datetime | None:
        """Parse ISO 8601 date string to timezone-aware datetime.

        Treats the date as midnight UTC.

        Args:
            value: ISO 8601 date string (YYYY-MM-DD).

        Returns:
            Timezone-aware datetime at midnight UTC, or None if parsing fails.
        """
        if not value:
            return None

        try:
            date = datetime.strptime(value, "%Y-%m-%d")
            return date.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return None
