"""Tests for polling automation config loader.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for YAML configuration loading
with environment variable substitution and Pydantic validation.

Covers:
- Valid YAML loads successfully
- Missing file raises ConfigurationError
- Invalid YAML syntax raises ConfigurationError
- Environment variable substitution works
- Missing env var raises ConfigurationError
- Nested env var substitution works
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from autom8_asana.automation.polling.config_loader import ConfigurationLoader
from autom8_asana.automation.polling.config_schema import AutomationRulesConfig
from autom8_asana.errors import ConfigurationError

if TYPE_CHECKING:
    from pathlib import Path


class TestConfigurationLoaderLoadFromFile:
    """Tests for ConfigurationLoader.load_from_file()."""

    def test_valid_yaml_loads_successfully(
        self,
        temp_config_file: Path,
    ) -> None:
        """Valid YAML configuration loads and parses correctly."""
        config = ConfigurationLoader.load_from_file(
            str(temp_config_file),
            AutomationRulesConfig,
        )

        assert config.scheduler.time == "02:00"
        assert config.scheduler.timezone == "UTC"
        assert len(config.rules) == 2
        assert config.rules[0].rule_id == "escalate-stale"
        assert config.rules[1].rule_id == "deadline-warning"

    def test_missing_file_raises_configuration_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Missing file raises ConfigurationError with clear message."""
        nonexistent_path = str(tmp_path / "nonexistent.yaml")

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationLoader.load_from_file(
                nonexistent_path,
                AutomationRulesConfig,
            )

        assert "Configuration file not found" in str(exc_info.value)
        assert "nonexistent.yaml" in str(exc_info.value)

    def test_invalid_yaml_syntax_raises_configuration_error(
        self,
        tmp_path: Path,
        invalid_yaml_syntax: str,
    ) -> None:
        """Invalid YAML syntax raises ConfigurationError."""
        config_file = tmp_path / "bad_syntax.yaml"
        config_file.write_text(invalid_yaml_syntax)

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationLoader.load_from_file(
                str(config_file),
                AutomationRulesConfig,
            )

        assert "Invalid YAML syntax" in str(exc_info.value)

    def test_schema_validation_error_raises_configuration_error(
        self,
        temp_invalid_config_file: Path,
    ) -> None:
        """Schema validation failure raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationLoader.load_from_file(
                str(temp_invalid_config_file),
                AutomationRulesConfig,
            )

        assert "Config validation failed" in str(exc_info.value)
        # Should mention the specific validation issue
        assert "days must be >= 1" in str(exc_info.value)

    def test_empty_file_raises_configuration_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Empty YAML file raises ConfigurationError for missing fields."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationLoader.load_from_file(
                str(empty_file),
                AutomationRulesConfig,
            )

        # Should report missing required fields
        assert "Config validation failed" in str(exc_info.value)


class TestConfigurationLoaderEnvVarSubstitution:
    """Tests for environment variable substitution."""

    def test_env_var_substitution_works(
        self,
        temp_config_file_with_env_vars: Path,
    ) -> None:
        """Environment variable placeholders are substituted."""
        env_vars = {
            "POLL_TIMEZONE": "America/New_York",
            "PROJECT_GID": "9999999999999",
            "TAG_NAME": "escalated",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ConfigurationLoader.load_from_file(
                str(temp_config_file_with_env_vars),
                AutomationRulesConfig,
            )

        assert config.scheduler.timezone == "America/New_York"
        assert config.rules[0].project_gid == "9999999999999"
        assert config.rules[0].action.params["tag"] == "escalated"

    def test_missing_env_var_raises_configuration_error(
        self,
        temp_config_file_with_env_vars: Path,
    ) -> None:
        """Missing environment variable raises ConfigurationError."""
        # Only provide some of the required env vars
        env_vars = {
            "POLL_TIMEZONE": "UTC",
            # PROJECT_GID is missing
            # TAG_NAME is missing
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigurationLoader.load_from_file(
                    str(temp_config_file_with_env_vars),
                    AutomationRulesConfig,
                )

        assert "Environment variable" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_nested_env_var_substitution_works(
        self,
        tmp_path: Path,
        valid_config_yaml_nested_env_vars: str,
    ) -> None:
        """Nested environment variable substitution works correctly."""
        config_file = tmp_path / "nested_env.yaml"
        config_file.write_text(valid_config_yaml_nested_env_vars)

        env_vars = {
            "POLL_TIME": "03:30",
            "RULE_ID": "dynamic-rule",
            "FIELD_NAME": "Status",
            "TAG_NAME": "auto-tagged",
            "SUFFIX_VAR": "middle",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ConfigurationLoader.load_from_file(
                str(config_file),
                AutomationRulesConfig,
            )

        assert config.scheduler.time == "03:30"
        assert config.rules[0].rule_id == "dynamic-rule"
        assert config.rules[0].conditions[0].stale.field == "Status"
        assert config.rules[0].action.params["tag"] == "auto-tagged"
        assert config.rules[0].action.params["extra"] == "prefix-middle-suffix"

    def test_multiple_env_vars_in_same_string(
        self,
        tmp_path: Path,
    ) -> None:
        """Multiple env vars in the same string value are all substituted."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "test"
    name: "Test"
    project_gid: "123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_comment"
      params:
        text: "${GREETING} ${NAME}! Today is ${DAY}."
    enabled: true
"""
        config_file = tmp_path / "multi_env.yaml"
        config_file.write_text(yaml_content)

        env_vars = {
            "GREETING": "Hello",
            "NAME": "World",
            "DAY": "Monday",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ConfigurationLoader.load_from_file(
                str(config_file),
                AutomationRulesConfig,
            )

        assert config.rules[0].action.params["text"] == "Hello World! Today is Monday."


class TestConfigurationLoaderSubstituteEnvVars:
    """Tests for ConfigurationLoader.substitute_env_vars() directly."""

    def test_substitute_simple_string(self) -> None:
        """Simple string substitution works."""
        raw = {"key": "${TEST_VAR}"}

        with patch.dict(os.environ, {"TEST_VAR": "value"}, clear=False):
            result = ConfigurationLoader.substitute_env_vars(raw)

        assert result["key"] == "value"

    def test_substitute_nested_dict(self) -> None:
        """Nested dict values are substituted."""
        raw = {
            "outer": {
                "inner": "${NESTED_VAR}",
            },
        }

        with patch.dict(os.environ, {"NESTED_VAR": "nested_value"}, clear=False):
            result = ConfigurationLoader.substitute_env_vars(raw)

        assert result["outer"]["inner"] == "nested_value"

    def test_substitute_list_items(self) -> None:
        """List items are substituted."""
        raw = {
            "items": ["${ITEM_1}", "${ITEM_2}", "static"],
        }

        env_vars = {"ITEM_1": "first", "ITEM_2": "second"}

        with patch.dict(os.environ, env_vars, clear=False):
            result = ConfigurationLoader.substitute_env_vars(raw)

        assert result["items"] == ["first", "second", "static"]

    def test_non_string_values_unchanged(self) -> None:
        """Non-string values (int, bool, None) are unchanged."""
        raw = {
            "count": 42,
            "enabled": True,
            "optional": None,
        }

        result = ConfigurationLoader.substitute_env_vars(raw)

        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["optional"] is None

    def test_partial_substitution_in_string(self) -> None:
        """Partial substitution within a string works."""
        raw = {"message": "Hello, ${NAME}! Welcome."}

        with patch.dict(os.environ, {"NAME": "Alice"}, clear=False):
            result = ConfigurationLoader.substitute_env_vars(raw)

        assert result["message"] == "Hello, Alice! Welcome."

    def test_env_var_pattern_case_sensitive(self) -> None:
        """Environment variable names are case-sensitive."""
        raw = {"key": "${UPPER_CASE}"}

        with patch.dict(
            os.environ, {"UPPER_CASE": "correct", "upper_case": "wrong"}, clear=False
        ):
            result = ConfigurationLoader.substitute_env_vars(raw)

        assert result["key"] == "correct"

    def test_missing_env_var_in_nested_path(self) -> None:
        """Missing env var error includes the config path."""
        raw = {
            "outer": {
                "inner": "${MISSING_VAR}",
            },
        }

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigurationLoader.substitute_env_vars(raw)

        error_msg = str(exc_info.value)
        assert "MISSING_VAR" in error_msg
        assert "not found" in error_msg
        # Should include path information
        assert "outer.inner" in error_msg


class TestConfigurationLoaderEdgeCases:
    """Edge case tests for config loader."""

    def test_unicode_content_loads_correctly(
        self,
        tmp_path: Path,
    ) -> None:
        """Unicode content in YAML is handled correctly."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "unicode-rule"
    name: "Unicode Test"
    project_gid: "123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_comment"
      params:
        text: "Hello World"
    enabled: true
"""
        config_file = tmp_path / "unicode.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        config = ConfigurationLoader.load_from_file(
            str(config_file),
            AutomationRulesConfig,
        )

        assert config.rules[0].action.params["text"] == "Hello World"

    def test_yaml_with_comments_loads_correctly(
        self,
        tmp_path: Path,
    ) -> None:
        """YAML comments are ignored during parsing."""
        yaml_content = """
# This is a comment
scheduler:
  time: "02:00"  # Time comment
  timezone: "UTC"  # TZ comment
# Another comment
rules:
  - rule_id: "commented-rule"
    name: "Test"
    project_gid: "123"
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
        config_file = tmp_path / "commented.yaml"
        config_file.write_text(yaml_content)

        config = ConfigurationLoader.load_from_file(
            str(config_file),
            AutomationRulesConfig,
        )

        assert config.scheduler.time == "02:00"
        assert config.rules[0].rule_id == "commented-rule"

    def test_yaml_with_anchors_loads_correctly(
        self,
        tmp_path: Path,
    ) -> None:
        """YAML anchors and aliases work correctly."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "rule-1"
    name: "First Rule"
    project_gid: "123"
    conditions: &common_condition
      - stale:
          field: "Section"
          days: 3
    action: &common_action
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
  - rule_id: "rule-2"
    name: "Second Rule"
    project_gid: "456"
    conditions: *common_condition
    action: *common_action
    enabled: true
"""
        config_file = tmp_path / "anchors.yaml"
        config_file.write_text(yaml_content)

        config = ConfigurationLoader.load_from_file(
            str(config_file),
            AutomationRulesConfig,
        )

        assert len(config.rules) == 2
        # Both rules should have the same conditions from anchor
        assert config.rules[0].conditions[0].stale.days == 3
        assert config.rules[1].conditions[0].stale.days == 3

    def test_validation_error_includes_location(
        self,
        tmp_path: Path,
    ) -> None:
        """Validation errors include field location information."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "valid-rule"
    name: "Valid"
    project_gid: "123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
  - rule_id: "invalid-rule"
    name: "Invalid"
    project_gid: "456"
    conditions:
      - stale:
          field: "Section"
          days: -5
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
"""
        config_file = tmp_path / "multi_rules.yaml"
        config_file.write_text(yaml_content)

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationLoader.load_from_file(
                str(config_file),
                AutomationRulesConfig,
            )

        error_msg = str(exc_info.value)
        # Should include field path information
        assert "rules" in error_msg
        assert "days" in error_msg
