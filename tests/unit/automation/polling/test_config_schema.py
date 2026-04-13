"""Tests for polling automation config schema.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for Pydantic v2 schema validation
with strict mode (extra="forbid").

Covers:
- Valid config parsing
- Invalid days validation (< 1)
- Invalid time format validation
- Missing required fields
- Extra fields rejection (strict mode)
- At least one trigger required in RuleCondition
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.automation.polling.config_schema import (
    ActionConfig,
    AutomationRulesConfig,
    Rule,
    RuleCondition,
    ScheduleConfig,
    SchedulerConfig,
    TriggerAgeConfig,
    TriggerDeadlineConfig,
    TriggerStaleConfig,
)


class TestTriggerStaleConfig:
    """Tests for TriggerStaleConfig validation."""

    def test_valid_stale_trigger(self) -> None:
        """Valid stale trigger with positive days parses correctly."""
        trigger = TriggerStaleConfig(field="Section", days=3)

        assert trigger.field == "Section"
        assert trigger.days == 3

    def test_days_must_be_positive(self) -> None:
        """days < 1 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerStaleConfig(field="Section", days=0)

        assert "days must be >= 1" in str(exc_info.value)

    def test_negative_days_raises_error(self) -> None:
        """Negative days raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerStaleConfig(field="Section", days=-5)

        assert "days must be >= 1" in str(exc_info.value)

    def test_minimum_valid_days(self) -> None:
        """days=1 is the minimum valid value."""
        trigger = TriggerStaleConfig(field="Section", days=1)
        assert trigger.days == 1

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerStaleConfig(field="Section", days=3, extra_field="nope")

        assert "extra" in str(exc_info.value).lower()


class TestTriggerDeadlineConfig:
    """Tests for TriggerDeadlineConfig validation."""

    def test_valid_deadline_trigger(self) -> None:
        """Valid deadline trigger parses correctly."""
        trigger = TriggerDeadlineConfig(days=7)

        assert trigger.days == 7

    def test_days_must_be_positive(self) -> None:
        """days < 1 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerDeadlineConfig(days=0)

        assert "days must be >= 1" in str(exc_info.value)

    def test_negative_days_raises_error(self) -> None:
        """Negative days raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerDeadlineConfig(days=-1)

        assert "days must be >= 1" in str(exc_info.value)

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerDeadlineConfig(days=7, unknown="field")

        assert "extra" in str(exc_info.value).lower()


class TestTriggerAgeConfig:
    """Tests for TriggerAgeConfig validation."""

    def test_valid_age_trigger(self) -> None:
        """Valid age trigger parses correctly."""
        trigger = TriggerAgeConfig(days=90)

        assert trigger.days == 90

    def test_days_must_be_positive(self) -> None:
        """days < 1 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerAgeConfig(days=0)

        assert "days must be >= 1" in str(exc_info.value)

    def test_negative_days_raises_error(self) -> None:
        """Negative days raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerAgeConfig(days=-10)

        assert "days must be >= 1" in str(exc_info.value)

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            TriggerAgeConfig(days=90, created_before="2024-01-01")

        assert "extra" in str(exc_info.value).lower()


class TestRuleCondition:
    """Tests for RuleCondition validation."""

    def test_stale_trigger_only(self) -> None:
        """Condition with only stale trigger is valid."""
        condition = RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))

        assert condition.stale is not None
        assert condition.deadline is None
        assert condition.age is None

    def test_deadline_trigger_only(self) -> None:
        """Condition with only deadline trigger is valid."""
        condition = RuleCondition(deadline=TriggerDeadlineConfig(days=7))

        assert condition.stale is None
        assert condition.deadline is not None
        assert condition.age is None

    def test_age_trigger_only(self) -> None:
        """Condition with only age trigger is valid."""
        condition = RuleCondition(age=TriggerAgeConfig(days=90))

        assert condition.stale is None
        assert condition.deadline is None
        assert condition.age is not None

    def test_multiple_triggers_allowed(self) -> None:
        """Condition with multiple triggers is valid (AND composition)."""
        condition = RuleCondition(
            stale=TriggerStaleConfig(field="Section", days=3),
            deadline=TriggerDeadlineConfig(days=7),
        )

        assert condition.stale is not None
        assert condition.deadline is not None
        assert condition.age is None

    def test_all_triggers_allowed(self) -> None:
        """Condition with all three triggers is valid."""
        condition = RuleCondition(
            stale=TriggerStaleConfig(field="Section", days=3),
            deadline=TriggerDeadlineConfig(days=7),
            age=TriggerAgeConfig(days=90),
        )

        assert condition.stale is not None
        assert condition.deadline is not None
        assert condition.age is not None

    def test_at_least_one_trigger_required(self) -> None:
        """Condition without any trigger raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            RuleCondition()

        assert "At least one trigger type" in str(exc_info.value)

    def test_field_whitelist_without_trigger_fails(self) -> None:
        """field_whitelist alone is not valid (needs trigger)."""
        with pytest.raises(ValidationError) as exc_info:
            RuleCondition(field_whitelist=["custom_field_123"])

        assert "At least one trigger type" in str(exc_info.value)

    def test_field_whitelist_with_trigger_valid(self) -> None:
        """field_whitelist with a trigger is valid."""
        condition = RuleCondition(
            stale=TriggerStaleConfig(field="Section", days=3),
            field_whitelist=["custom_field_123", "custom_field_456"],
        )

        assert condition.stale is not None
        assert condition.field_whitelist == ["custom_field_123", "custom_field_456"]

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            RuleCondition(
                stale=TriggerStaleConfig(field="Section", days=3),
                custom_trigger={"type": "unknown"},
            )

        assert "extra" in str(exc_info.value).lower()


class TestActionConfig:
    """Tests for ActionConfig validation."""

    def test_valid_action(self) -> None:
        """Valid action config parses correctly."""
        action = ActionConfig(type="add_tag", params={"tag": "escalate"})

        assert action.type == "add_tag"
        assert action.params == {"tag": "escalate"}

    def test_empty_params_allowed(self) -> None:
        """Empty params dict is allowed."""
        action = ActionConfig(type="notify", params={})

        assert action.type == "notify"
        assert action.params == {}

    def test_complex_params_allowed(self) -> None:
        """Complex nested params are allowed."""
        action = ActionConfig(
            type="add_comment",
            params={
                "text": "Due soon!",
                "is_pinned": True,
                "mentions": ["user_123", "user_456"],
            },
        )

        assert action.params["mentions"] == ["user_123", "user_456"]

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            ActionConfig(
                type="add_tag",
                params={"tag": "test"},
                description="Extra field",
            )

        assert "extra" in str(exc_info.value).lower()


class TestRule:
    """Tests for Rule validation."""

    def test_valid_rule(self) -> None:
        """Valid rule parses correctly."""
        rule = Rule(
            rule_id="escalate-stale",
            name="Escalate Stale Tasks",
            project_gid="1234567890123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "escalate"}),
            enabled=True,
        )

        assert rule.rule_id == "escalate-stale"
        assert rule.name == "Escalate Stale Tasks"
        assert rule.project_gid == "1234567890123"
        assert len(rule.conditions) == 1
        assert rule.action.type == "add_tag"
        assert rule.enabled is True

    def test_enabled_defaults_to_true(self) -> None:
        """enabled field defaults to True if not specified."""
        rule = Rule(
            rule_id="test-rule",
            name="Test Rule",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=1))],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        assert rule.enabled is True

    def test_empty_rule_id_raises_error(self) -> None:
        """Empty rule_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                rule_id="",
                name="Test Rule",
                project_gid="123",
                conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=1))],
                action=ActionConfig(type="add_tag", params={"tag": "test"}),
            )

        assert "rule_id must be non-empty" in str(exc_info.value)

    def test_whitespace_only_rule_id_raises_error(self) -> None:
        """Whitespace-only rule_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                rule_id="   ",
                name="Test Rule",
                project_gid="123",
                conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=1))],
                action=ActionConfig(type="add_tag", params={"tag": "test"}),
            )

        assert "rule_id must be non-empty" in str(exc_info.value)

    def test_multiple_conditions_allowed(self) -> None:
        """Rule with multiple conditions (AND composition) is valid."""
        rule = Rule(
            rule_id="complex-rule",
            name="Complex Rule",
            project_gid="123",
            conditions=[
                RuleCondition(stale=TriggerStaleConfig(field="Section", days=3)),
                RuleCondition(deadline=TriggerDeadlineConfig(days=7)),
            ],
            action=ActionConfig(type="add_tag", params={"tag": "test"}),
        )

        assert len(rule.conditions) == 2

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                rule_id="test-rule",
                name="Test Rule",
                project_gid="123",
                conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=1))],
                action=ActionConfig(type="add_tag", params={"tag": "test"}),
                priority=1,  # Extra field
            )

        assert "extra" in str(exc_info.value).lower()


class TestSchedulerConfig:
    """Tests for SchedulerConfig validation."""

    def test_valid_scheduler_config(self) -> None:
        """Valid scheduler config parses correctly."""
        config = SchedulerConfig(time="02:00", timezone="UTC")

        assert config.time == "02:00"
        assert config.timezone == "UTC"

    def test_valid_time_formats(self) -> None:
        """Various valid 24-hour time formats parse correctly."""
        valid_times = ["00:00", "01:30", "12:00", "13:45", "23:59"]

        for time in valid_times:
            config = SchedulerConfig(time=time, timezone="UTC")
            assert config.time == time

    @pytest.mark.parametrize(
        "time_str",
        [
            pytest.param("25:00", id="invalid-24h-hour"),
            pytest.param("12:60", id="invalid-minutes"),
            pytest.param("2:00 PM", id="12h-format-rejected"),
            pytest.param("2:00", id="single-digit-hour"),
        ],
    )
    def test_invalid_time_format_rejected(self, time_str: str) -> None:
        """Invalid time formats raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SchedulerConfig(time=time_str, timezone="UTC")

        assert "time must be in HH:MM format" in str(exc_info.value)

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            SchedulerConfig(time="02:00", timezone="UTC", interval="daily")

        assert "extra" in str(exc_info.value).lower()


class TestAutomationRulesConfig:
    """Tests for AutomationRulesConfig (top-level) validation."""

    def test_valid_config(self) -> None:
        """Valid complete config parses correctly."""
        config = AutomationRulesConfig(
            scheduler=SchedulerConfig(time="02:00", timezone="UTC"),
            rules=[
                Rule(
                    rule_id="test-rule",
                    name="Test Rule",
                    project_gid="123",
                    conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
                    action=ActionConfig(type="add_tag", params={"tag": "test"}),
                )
            ],
        )

        assert config.scheduler.time == "02:00"
        assert len(config.rules) == 1
        assert config.rules[0].rule_id == "test-rule"

    def test_empty_rules_list_allowed(self) -> None:
        """Empty rules list is allowed (though not useful)."""
        config = AutomationRulesConfig(
            scheduler=SchedulerConfig(time="02:00", timezone="UTC"),
            rules=[],
        )

        assert len(config.rules) == 0

    def test_missing_scheduler_raises_error(self) -> None:
        """Missing scheduler field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AutomationRulesConfig(
                rules=[
                    Rule(
                        rule_id="test-rule",
                        name="Test Rule",
                        project_gid="123",
                        conditions=[
                            RuleCondition(stale=TriggerStaleConfig(field="Section", days=1))
                        ],
                        action=ActionConfig(type="add_tag", params={"tag": "test"}),
                    )
                ],
            )

        # Pydantic will report missing required field
        assert "scheduler" in str(exc_info.value).lower()

    def test_missing_rules_raises_error(self) -> None:
        """Missing rules field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AutomationRulesConfig(
                scheduler=SchedulerConfig(time="02:00", timezone="UTC"),
            )

        # Pydantic will report missing required field
        assert "rules" in str(exc_info.value).lower()

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            AutomationRulesConfig(
                scheduler=SchedulerConfig(time="02:00", timezone="UTC"),
                rules=[],
                version="1.0",  # Extra field
            )

        assert "extra" in str(exc_info.value).lower()

    def test_multiple_rules_valid(self, sample_rules_list: list[Rule]) -> None:
        """Multiple rules in the list parse correctly."""
        config = AutomationRulesConfig(
            scheduler=SchedulerConfig(time="02:00", timezone="UTC"),
            rules=sample_rules_list,
        )

        assert len(config.rules) == 3
        assert config.rules[0].rule_id == "stale-check"
        assert config.rules[1].rule_id == "deadline-alert"
        assert config.rules[2].rule_id == "old-task-cleanup"


class TestScheduleConfig:
    """Tests for ScheduleConfig validation.

    Per DEF-005: Zero ScheduleConfig validator tests.
    """

    def test_valid_weekly_schedule(self) -> None:
        """Valid weekly schedule with day_of_week parses correctly."""
        schedule = ScheduleConfig(frequency="weekly", day_of_week="sunday")
        assert schedule.frequency == "weekly"
        assert schedule.day_of_week == "sunday"

    def test_valid_daily_schedule(self) -> None:
        """Valid daily schedule without day_of_week parses correctly."""
        schedule = ScheduleConfig(frequency="daily")
        assert schedule.frequency == "daily"
        assert schedule.day_of_week is None

    def test_frequency_case_insensitive(self) -> None:
        """Frequency is normalized to lowercase."""
        schedule = ScheduleConfig(frequency="Weekly", day_of_week="monday")
        assert schedule.frequency == "weekly"

    def test_day_of_week_case_insensitive(self) -> None:
        """day_of_week is normalized to lowercase."""
        schedule = ScheduleConfig(frequency="weekly", day_of_week="Sunday")
        assert schedule.day_of_week == "sunday"

    def test_invalid_frequency_raises_error(self) -> None:
        """Invalid frequency raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleConfig(frequency="monthly")
        assert "frequency must be one of" in str(exc_info.value)

    def test_invalid_day_of_week_raises_error(self) -> None:
        """Invalid day_of_week raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleConfig(frequency="weekly", day_of_week="funday")
        assert "day_of_week must be one of" in str(exc_info.value)

    def test_weekly_without_day_of_week_raises_error(self) -> None:
        """Weekly frequency without day_of_week raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleConfig(frequency="weekly")
        assert "day_of_week is required" in str(exc_info.value)

    def test_daily_with_day_of_week_allowed(self) -> None:
        """Daily frequency with day_of_week is allowed (ignored)."""
        schedule = ScheduleConfig(frequency="daily", day_of_week="monday")
        assert schedule.frequency == "daily"
        assert schedule.day_of_week == "monday"

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleConfig(frequency="daily", cron="0 2 * * *")
        assert "extra" in str(exc_info.value).lower()

    def test_all_days_of_week_valid(self) -> None:
        """All 7 day names are accepted."""
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        for day in days:
            schedule = ScheduleConfig(frequency="weekly", day_of_week=day)
            assert schedule.day_of_week == day


class TestRuleValidateCompleteness:
    """Tests for Rule.validate_rule_completeness model validator.

    Per DEF-005: Validates schedule vs conditions mutual requirements.
    """

    def test_empty_conditions_without_schedule_rejected(self) -> None:
        """Rule with no conditions and no schedule raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                rule_id="bad-rule",
                name="Bad Rule",
                project_gid="123",
                conditions=[],
                action=ActionConfig(type="add_tag", params={"tag": "test"}),
            )
        assert "at least one condition or a schedule" in str(exc_info.value).lower()

    def test_schedule_with_non_workflow_action_rejected(self) -> None:
        """Schedule-driven rule with non-workflow action raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                rule_id="bad-schedule-rule",
                name="Bad Schedule Rule",
                project_gid="123",
                conditions=[],
                action=ActionConfig(type="add_tag", params={"tag": "test"}),
                schedule=ScheduleConfig(frequency="daily"),
            )
        assert "action.type='workflow'" in str(exc_info.value)

    def test_schedule_with_workflow_action_valid(self) -> None:
        """Schedule-driven rule with workflow action and empty conditions is valid."""
        rule = Rule(
            rule_id="valid-schedule-rule",
            name="Valid Schedule Rule",
            project_gid="123",
            conditions=[],
            action=ActionConfig(
                type="workflow",
                params={"workflow_id": "conversation-audit"},
            ),
            schedule=ScheduleConfig(frequency="weekly", day_of_week="sunday"),
        )
        assert rule.schedule is not None
        assert rule.action.type == "workflow"
        assert len(rule.conditions) == 0

    def test_conditions_and_schedule_both_present_valid(self) -> None:
        """Rule with both conditions and schedule is valid (if action is workflow)."""
        rule = Rule(
            rule_id="dual-rule",
            name="Dual Rule",
            project_gid="123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(
                type="workflow",
                params={"workflow_id": "conversation-audit"},
            ),
            schedule=ScheduleConfig(frequency="daily"),
        )
        assert rule.schedule is not None
        assert len(rule.conditions) == 1
