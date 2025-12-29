"""Test fixtures for polling automation tests.

Provides shared fixtures for config_schema, config_loader, trigger_evaluator,
polling_scheduler, structured_logger, and cli tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.polling.config_schema import (
    ActionConfig,
    AutomationRulesConfig,
    Rule,
    RuleCondition,
    SchedulerConfig,
    TriggerAgeConfig,
    TriggerDeadlineConfig,
    TriggerStaleConfig,
)


# ============================================================================
# YAML Configuration Fixtures
# ============================================================================


@pytest.fixture
def valid_config_yaml() -> str:
    """Sample valid YAML configuration string."""
    return """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "escalate-stale"
    name: "Escalate Stale Tasks"
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
  - rule_id: "deadline-warning"
    name: "Deadline Warning"
    project_gid: "9876543210987"
    conditions:
      - deadline:
          days: 7
    action:
      type: "add_comment"
      params:
        text: "Due soon!"
    enabled: true
"""


@pytest.fixture
def valid_config_yaml_with_env_vars() -> str:
    """Sample valid YAML with environment variable placeholders."""
    return """
scheduler:
  time: "02:00"
  timezone: "${POLL_TIMEZONE}"
rules:
  - rule_id: "project-check"
    name: "Check Project"
    project_gid: "${PROJECT_GID}"
    conditions:
      - stale:
          field: "Section"
          days: 3
    action:
      type: "add_tag"
      params:
        tag: "${TAG_NAME}"
    enabled: true
"""


@pytest.fixture
def valid_config_yaml_nested_env_vars() -> str:
    """Sample valid YAML with nested environment variable placeholders."""
    return """
scheduler:
  time: "${POLL_TIME}"
  timezone: "UTC"
rules:
  - rule_id: "${RULE_ID}"
    name: "Test Rule"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "${FIELD_NAME}"
          days: 3
    action:
      type: "add_tag"
      params:
        tag: "${TAG_NAME}"
        extra: "prefix-${SUFFIX_VAR}-suffix"
    enabled: true
"""


@pytest.fixture
def invalid_config_yaml_bad_days() -> str:
    """YAML with invalid days value (< 1)."""
    return """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "invalid-rule"
    name: "Invalid Days"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "Section"
          days: 0
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
"""


@pytest.fixture
def invalid_config_yaml_bad_time() -> str:
    """YAML with invalid time format."""
    return """
scheduler:
  time: "25:00"
  timezone: "UTC"
rules:
  - rule_id: "test-rule"
    name: "Test"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
"""


@pytest.fixture
def invalid_config_yaml_missing_scheduler() -> str:
    """YAML missing required scheduler field."""
    return """
rules:
  - rule_id: "test-rule"
    name: "Test"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
"""


@pytest.fixture
def invalid_config_yaml_extra_fields() -> str:
    """YAML with extra fields (strict mode should reject)."""
    return """
scheduler:
  time: "02:00"
  timezone: "UTC"
  unexpected_field: "should fail"
rules:
  - rule_id: "test-rule"
    name: "Test"
    project_gid: "1234567890123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
"""


@pytest.fixture
def invalid_config_yaml_no_trigger() -> str:
    """YAML with condition that has no trigger type."""
    return """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "test-rule"
    name: "Test"
    project_gid: "1234567890123"
    conditions:
      - field_whitelist:
          - "custom_field_123"
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
"""


@pytest.fixture
def invalid_yaml_syntax() -> str:
    """YAML with syntax errors."""
    return """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "test-rule"
    name: "Test
    project_gid: "1234567890123"
"""


# ============================================================================
# Pydantic Model Fixtures
# ============================================================================


@pytest.fixture
def sample_scheduler_config() -> SchedulerConfig:
    """Sample valid SchedulerConfig."""
    return SchedulerConfig(time="02:00", timezone="UTC")


@pytest.fixture
def sample_stale_trigger() -> TriggerStaleConfig:
    """Sample stale trigger configuration."""
    return TriggerStaleConfig(field="Section", days=3)


@pytest.fixture
def sample_deadline_trigger() -> TriggerDeadlineConfig:
    """Sample deadline trigger configuration."""
    return TriggerDeadlineConfig(days=7)


@pytest.fixture
def sample_age_trigger() -> TriggerAgeConfig:
    """Sample age trigger configuration."""
    return TriggerAgeConfig(days=90)


@pytest.fixture
def sample_action_config() -> ActionConfig:
    """Sample action configuration."""
    return ActionConfig(type="add_tag", params={"tag": "escalate"})


@pytest.fixture
def sample_rule_condition(sample_stale_trigger: TriggerStaleConfig) -> RuleCondition:
    """Sample rule condition with stale trigger."""
    return RuleCondition(stale=sample_stale_trigger)


@pytest.fixture
def sample_rule(
    sample_rule_condition: RuleCondition,
    sample_action_config: ActionConfig,
) -> Rule:
    """Sample complete rule."""
    return Rule(
        rule_id="escalate-stale",
        name="Escalate Stale Tasks",
        project_gid="1234567890123",
        conditions=[sample_rule_condition],
        action=sample_action_config,
        enabled=True,
    )


@pytest.fixture
def sample_rules_list() -> list[Rule]:
    """List of sample rules for testing."""
    return [
        Rule(
            rule_id="stale-check",
            name="Stale Task Check",
            project_gid="1234567890123",
            conditions=[RuleCondition(stale=TriggerStaleConfig(field="Section", days=3))],
            action=ActionConfig(type="add_tag", params={"tag": "stale"}),
            enabled=True,
        ),
        Rule(
            rule_id="deadline-alert",
            name="Deadline Alert",
            project_gid="9876543210987",
            conditions=[RuleCondition(deadline=TriggerDeadlineConfig(days=7))],
            action=ActionConfig(type="add_comment", params={"text": "Due soon!"}),
            enabled=True,
        ),
        Rule(
            rule_id="old-task-cleanup",
            name="Old Task Cleanup",
            project_gid="1111111111111",
            conditions=[RuleCondition(age=TriggerAgeConfig(days=90))],
            action=ActionConfig(type="change_section", params={"section": "Archive"}),
            enabled=False,  # Disabled rule
        ),
    ]


@pytest.fixture
def sample_automation_config(
    sample_scheduler_config: SchedulerConfig,
    sample_rules_list: list[Rule],
) -> AutomationRulesConfig:
    """Sample complete automation configuration."""
    return AutomationRulesConfig(
        scheduler=sample_scheduler_config,
        rules=sample_rules_list,
    )


# ============================================================================
# Task Fixtures for Trigger Evaluation
# ============================================================================

from tests._shared.mocks import MockTask


@pytest.fixture
def now() -> datetime:
    """Current UTC datetime for consistent testing."""
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_tasks(now: datetime) -> list[MockTask]:
    """List of sample mock tasks with various date configurations.

    Creates tasks with the following characteristics:
    - task-1: Modified 5 days ago (stale at 3-day threshold)
    - task-2: Modified today (not stale)
    - task-3: Due in 3 days
    - task-4: Due in 14 days
    - task-5: Created 100 days ago, not completed (old)
    - task-6: Created 100 days ago, completed (old but done)
    - task-7: Created 30 days ago, not completed (not old enough)
    - task-8: No dates set (edge case)
    """
    return [
        MockTask(
            gid="task-1",
            name="Stale Task",
            modified_at=(now - timedelta(days=5)).isoformat(),
            created_at=(now - timedelta(days=10)).isoformat(),
        ),
        MockTask(
            gid="task-2",
            name="Fresh Task",
            modified_at=now.isoformat(),
            created_at=(now - timedelta(days=2)).isoformat(),
        ),
        MockTask(
            gid="task-3",
            name="Due Soon Task",
            modified_at=now.isoformat(),
            created_at=(now - timedelta(days=5)).isoformat(),
            due_on=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
        ),
        MockTask(
            gid="task-4",
            name="Due Later Task",
            modified_at=now.isoformat(),
            created_at=(now - timedelta(days=5)).isoformat(),
            due_on=(now + timedelta(days=14)).strftime("%Y-%m-%d"),
        ),
        MockTask(
            gid="task-5",
            name="Old Open Task",
            modified_at=(now - timedelta(days=50)).isoformat(),
            created_at=(now - timedelta(days=100)).isoformat(),
            completed=False,
        ),
        MockTask(
            gid="task-6",
            name="Old Completed Task",
            modified_at=(now - timedelta(days=10)).isoformat(),
            created_at=(now - timedelta(days=100)).isoformat(),
            completed=True,
        ),
        MockTask(
            gid="task-7",
            name="Newer Open Task",
            modified_at=(now - timedelta(days=5)).isoformat(),
            created_at=(now - timedelta(days=30)).isoformat(),
            completed=False,
        ),
        MockTask(
            gid="task-8",
            name="Task Without Dates",
            # No dates set - tests graceful handling
        ),
    ]


@pytest.fixture
def stale_tasks(sample_tasks: list[MockTask]) -> list[MockTask]:
    """Tasks that are stale (modified 3+ days ago)."""
    # task-1, task-5, task-7 are modified 5+ days ago
    return [t for t in sample_tasks if t.gid in ("task-1", "task-5", "task-7")]


@pytest.fixture
def fresh_tasks(sample_tasks: list[MockTask]) -> list[MockTask]:
    """Tasks that are not stale (modified within 3 days)."""
    return [t for t in sample_tasks if t.gid in ("task-2", "task-3", "task-4", "task-6")]


@pytest.fixture
def due_soon_tasks(sample_tasks: list[MockTask]) -> list[MockTask]:
    """Tasks due within 7 days."""
    return [t for t in sample_tasks if t.gid == "task-3"]


@pytest.fixture
def old_open_tasks(sample_tasks: list[MockTask]) -> list[MockTask]:
    """Tasks created 90+ days ago that are still open."""
    return [t for t in sample_tasks if t.gid == "task-5"]


# ============================================================================
# Temporary File Fixtures
# ============================================================================


@pytest.fixture
def temp_config_file(tmp_path, valid_config_yaml: str):
    """Create a temporary valid config file."""
    config_file = tmp_path / "rules.yaml"
    config_file.write_text(valid_config_yaml)
    return config_file


@pytest.fixture
def temp_invalid_config_file(tmp_path, invalid_config_yaml_bad_days: str):
    """Create a temporary invalid config file."""
    config_file = tmp_path / "invalid_rules.yaml"
    config_file.write_text(invalid_config_yaml_bad_days)
    return config_file


@pytest.fixture
def temp_config_file_with_env_vars(tmp_path, valid_config_yaml_with_env_vars: str):
    """Create a temporary config file with env var placeholders."""
    config_file = tmp_path / "rules_env.yaml"
    config_file.write_text(valid_config_yaml_with_env_vars)
    return config_file
