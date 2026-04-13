"""Configuration schema models for polling-based automation rules.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Pydantic v2 models for YAML configuration
validation with strict mode (extra="forbid").

Schema ownership: Devs own schema (this file), Ops own values (YAML files).

Example YAML structure:
    scheduler:
      time: "02:00"
      timezone: "UTC"
    rules:
      - rule_id: "escalate-triage"
        name: "Escalate stale triage tasks"
        project_gid: "1234567890123"
        conditions:
          - stale:
              field: "Section"
              days: 3
        action:
          type: "add_tag"
          params:
            tag: "escalate"
        enabled: true
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

__all__ = [
    "TriggerStaleConfig",
    "TriggerDeadlineConfig",
    "TriggerAgeConfig",
    "RuleCondition",
    "ActionConfig",
    "ScheduleConfig",
    "Rule",
    "SchedulerConfig",
    "AutomationRulesConfig",
]


class TriggerStaleConfig(BaseModel):
    """Stale detection trigger configuration.

    Monitors a field for tasks that haven't been modified in N days.

    Attributes:
        field: Field name or GID to monitor (e.g., "Section").
        days: Number of days threshold. Task is stale if modified_at >= N days ago.
            Must be >= 1.

    Example:
        stale:
          field: "Section"
          days: 3  # Task is stale if not modified in 3+ days
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    days: int

    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        """Validate that days is at least 1."""
        if v < 1:
            raise ValueError("days must be >= 1")
        return v


class TriggerDeadlineConfig(BaseModel):
    """Deadline proximity trigger configuration.

    Matches tasks with due dates within N days from today.

    Attributes:
        days: Number of days from today. Task matches if due_date <= today + N days.
            Must be >= 1.

    Example:
        deadline:
          days: 7  # Task due within next 7 days
    """

    model_config = ConfigDict(extra="forbid")

    days: int

    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        """Validate that days is at least 1."""
        if v < 1:
            raise ValueError("days must be >= 1")
        return v


class TriggerAgeConfig(BaseModel):
    """Age since creation trigger configuration.

    Matches tasks created N+ days ago that are still open (not completed).

    Attributes:
        days: Number of days since creation. Task matches if created >= N days ago
            and is still open. Must be >= 1.

    Example:
        age:
          days: 90  # Task created 90+ days ago and still open
    """

    model_config = ConfigDict(extra="forbid")

    days: int

    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        """Validate that days is at least 1."""
        if v < 1:
            raise ValueError("days must be >= 1")
        return v


class RuleCondition(BaseModel):
    """A single condition in a rule (supports AND composition).

    At least one trigger type (stale, deadline, or age) must be specified.
    Multiple conditions in a rule are combined with AND logic.

    Attributes:
        stale: Optional stale detection trigger.
        deadline: Optional deadline proximity trigger.
        age: Optional age since creation trigger.
        field_whitelist: Optional list of custom field GIDs to monitor.
            When specified, only trigger on changes to these fields.
            When None or empty, trigger on any field changes.

    Example:
        conditions:
          - stale:
              field: "Section"
              days: 3
            field_whitelist:
              - "custom_gid_abc123"
    """

    model_config = ConfigDict(extra="forbid")

    stale: TriggerStaleConfig | None = None
    deadline: TriggerDeadlineConfig | None = None
    age: TriggerAgeConfig | None = None
    field_whitelist: list[str] | None = None

    @model_validator(mode="after")
    def at_least_one_trigger_required(self) -> RuleCondition:
        """Validate that at least one trigger type is specified."""
        if self.stale is None and self.deadline is None and self.age is None:
            raise ValueError("At least one trigger type (stale, deadline, or age) is required")
        return self


class ScheduleConfig(BaseModel):
    """Per-rule schedule configuration for time-based workflow triggers.

    Per TDD-CONV-AUDIT-001 Section 3.3: Enables YAML-configurable schedule
    without hardcoded day/time values.

    Attributes:
        frequency: Schedule frequency ("weekly", "daily").
        day_of_week: ISO day name for weekly schedules (e.g., "sunday").
            Required when frequency is "weekly". Ignored for "daily".

    Example YAML:
        schedule:
          frequency: "weekly"
          day_of_week: "sunday"
    """

    model_config = ConfigDict(extra="forbid")

    frequency: str
    day_of_week: str | None = None

    @field_validator("frequency")
    @classmethod
    def frequency_must_be_valid(cls, v: str) -> str:
        valid = {"weekly", "daily"}
        if v.lower() not in valid:
            raise ValueError(f"frequency must be one of {valid}, got '{v}'")
        return v.lower()

    @field_validator("day_of_week")
    @classmethod
    def day_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }
        if v.lower() not in valid:
            raise ValueError(f"day_of_week must be one of {valid}, got '{v}'")
        return v.lower()

    @model_validator(mode="after")
    def weekly_requires_day(self) -> ScheduleConfig:
        if self.frequency == "weekly" and self.day_of_week is None:
            raise ValueError("day_of_week is required when frequency is 'weekly'")
        return self


class ActionConfig(BaseModel):
    """Action to execute when a rule matches.

    Attributes:
        type: Action type identifier (e.g., "add_tag", "add_comment", "change_section").
        params: Action-specific parameters as key-value pairs.

    Example:
        action:
          type: "add_tag"
          params:
            tag: "escalate"
    """

    model_config = ConfigDict(extra="forbid")

    type: str
    params: dict[str, Any]


class Rule(BaseModel):
    """A single automation rule definition.

    Per TDD-CONV-AUDIT-001: Extended to support schedule-driven workflow rules.
    - Condition-based rules: conditions is required (at least 1), schedule is None.
    - Schedule-based rules: conditions can be empty, schedule is required,
      action.type must be "workflow".

    Attributes:
        rule_id: Unique identifier for this rule. Must be non-empty.
        name: Human-readable name for display and logging.
        project_gid: Asana project GID to evaluate this rule against.
        conditions: List of conditions (combined with AND logic).
            Default empty list; must have at least 1 unless schedule is present.
        action: Action to execute when all conditions match.
        enabled: Whether this rule is active (default: True).
        schedule: Optional schedule configuration for time-based triggers.

    Example (condition-based):
        - rule_id: "escalate-triage"
          name: "Escalate stale triage tasks"
          project_gid: "1234567890123"
          conditions:
            - stale:
                field: "Section"
                days: 3
          action:
            type: "add_tag"
            params:
              tag: "escalate"
          enabled: true

    Example (schedule-based):
        - rule_id: "weekly-conversation-audit"
          name: "Weekly conversation audit CSV refresh"
          project_gid: "1201500116978260"
          conditions: []
          action:
            type: "workflow"
            params:
              workflow_id: "conversation-audit"
          schedule:
            frequency: "weekly"
            day_of_week: "sunday"
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    name: str
    project_gid: str
    conditions: list[RuleCondition] = []
    action: ActionConfig
    enabled: bool = True
    schedule: ScheduleConfig | None = None

    @field_validator("rule_id")
    @classmethod
    def rule_id_must_be_non_empty(cls, v: str) -> str:
        """Validate that rule_id is non-empty."""
        if not v or not v.strip():
            raise ValueError("rule_id must be non-empty")
        return v

    @model_validator(mode="after")
    def validate_rule_completeness(self) -> Rule:
        """Ensure rule has either conditions or schedule (or both)."""
        has_conditions = len(self.conditions) > 0
        has_schedule = self.schedule is not None

        if not has_conditions and not has_schedule:
            raise ValueError(
                "Rule must have at least one condition or a schedule block. "
                "Empty conditions are only allowed for schedule-driven rules."
            )

        if has_schedule and self.action.type != "workflow":
            raise ValueError(
                "Schedule-driven rules must use action.type='workflow'. "
                f"Got action.type='{self.action.type}'."
            )

        return self


class SchedulerConfig(BaseModel):
    """Polling scheduler configuration.

    Attributes:
        time: Time of day to run daily evaluation in 24-hour format "HH:MM".
        timezone: IANA timezone name (e.g., "UTC", "America/New_York").

    Example:
        scheduler:
          time: "02:00"
          timezone: "UTC"
    """

    model_config = ConfigDict(extra="forbid")

    time: str
    timezone: str

    @field_validator("time")
    @classmethod
    def time_must_be_valid_format(cls, v: str) -> str:
        """Validate that time is in HH:MM format (24-hour)."""
        pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
        if not re.match(pattern, v):
            raise ValueError(f"time must be in HH:MM format (24-hour), got '{v}'")
        return v


class AutomationRulesConfig(BaseModel):
    """Top-level configuration for polling-based automation rules.

    This is the root schema for the YAML configuration file.

    Attributes:
        scheduler: Polling scheduler configuration (time and timezone).
        rules: List of automation rules to evaluate.

    Example YAML:
        scheduler:
          time: "02:00"
          timezone: "America/New_York"
        rules:
          - rule_id: "escalate-triage"
            name: "Escalate stale triage tasks"
            project_gid: "1234567890123"
            conditions:
              - stale:
                  field: "Section"
                  days: 3
            action:
              type: "add_tag"
              params:
                tag: "escalate"
            enabled: true
    """

    model_config = ConfigDict(extra="forbid")

    scheduler: SchedulerConfig
    rules: list[Rule]
