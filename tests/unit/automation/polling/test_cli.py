"""Tests for polling automation CLI commands.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for CLI commands including
validation, status checking, and evaluation cycles.

Covers:
- validate command returns 0 on valid config
- validate command returns 1 on invalid config
- status command shows scheduler config
- evaluate --dry-run doesn't execute actions
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from autom8_asana.automation.polling.cli import (
    evaluate_command,
    main,
    status_command,
    validate_command,
)


class TestValidateCommand:
    """Tests for validate_command()."""

    def test_validate_returns_0_on_valid_config(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """validate_command() returns 0 for valid configuration."""
        exit_code = validate_command(str(temp_config_file))

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Configuration valid" in captured.out
        assert "2 rules loaded" in captured.out

    def test_validate_returns_1_on_invalid_config(
        self,
        temp_invalid_config_file: Path,
        capsys,
    ) -> None:
        """validate_command() returns 1 for invalid configuration."""
        exit_code = validate_command(str(temp_invalid_config_file))

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Configuration error" in captured.err

    def test_validate_returns_1_on_missing_file(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """validate_command() returns 1 for missing file."""
        nonexistent = str(tmp_path / "nonexistent.yaml")

        exit_code = validate_command(nonexistent)

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Configuration error" in captured.err
        assert "not found" in captured.err

    def test_validate_returns_1_on_syntax_error(
        self,
        tmp_path: Path,
        invalid_yaml_syntax: str,
        capsys,
    ) -> None:
        """validate_command() returns 1 for YAML syntax errors."""
        bad_yaml = tmp_path / "syntax_error.yaml"
        bad_yaml.write_text(invalid_yaml_syntax)

        exit_code = validate_command(str(bad_yaml))

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Configuration error" in captured.err

    def test_validate_shows_rule_count(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """validate_command() shows number of rules loaded."""
        validate_command(str(temp_config_file))

        captured = capsys.readouterr()
        assert "rules loaded" in captured.out


class TestStatusCommand:
    """Tests for status_command()."""

    def test_status_returns_0_on_valid_config(
        self,
        temp_config_file: Path,
    ) -> None:
        """status_command() returns 0 for valid configuration."""
        exit_code = status_command(str(temp_config_file))

        assert exit_code == 0

    def test_status_shows_scheduler_config(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """status_command() displays scheduler configuration."""
        status_command(str(temp_config_file))

        captured = capsys.readouterr()
        assert "Scheduler Configuration:" in captured.out
        assert "Time: 02:00" in captured.out
        assert "Timezone: UTC" in captured.out

    def test_status_shows_rules_summary(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """status_command() displays rules summary."""
        status_command(str(temp_config_file))

        captured = capsys.readouterr()
        assert "Rules Summary:" in captured.out
        assert "Total:" in captured.out
        assert "Enabled:" in captured.out
        assert "Disabled:" in captured.out

    def test_status_counts_enabled_disabled_correctly(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """status_command() correctly counts enabled/disabled rules."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "enabled-1"
    name: "Enabled 1"
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
  - rule_id: "enabled-2"
    name: "Enabled 2"
    project_gid: "456"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: true
  - rule_id: "disabled-1"
    name: "Disabled 1"
    project_gid: "789"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: false
"""
        config_file = tmp_path / "mixed_rules.yaml"
        config_file.write_text(yaml_content)

        status_command(str(config_file))

        captured = capsys.readouterr()
        assert "Total: 3" in captured.out
        assert "Enabled: 2" in captured.out
        assert "Disabled: 1" in captured.out

    def test_status_returns_1_on_invalid_config(
        self,
        temp_invalid_config_file: Path,
        capsys,
    ) -> None:
        """status_command() returns 1 for invalid configuration."""
        exit_code = status_command(str(temp_invalid_config_file))

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Configuration error" in captured.err


class TestEvaluateCommand:
    """Tests for evaluate_command()."""

    def test_evaluate_returns_0_on_success(
        self,
        temp_config_file: Path,
    ) -> None:
        """evaluate_command() returns 0 on successful evaluation."""
        exit_code = evaluate_command(str(temp_config_file))

        assert exit_code == 0

    def test_evaluate_dry_run_does_not_execute_actions(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """evaluate_command() with dry_run=True shows plan without executing."""
        exit_code = evaluate_command(str(temp_config_file), dry_run=True)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Would evaluate" in captured.out
        assert "Skipping actual evaluation" in captured.out

    def test_evaluate_dry_run_shows_rule_details(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """evaluate_command() dry-run shows details for each rule."""
        evaluate_command(str(temp_config_file), dry_run=True)

        captured = capsys.readouterr()
        # Should show rule information
        assert "Rule:" in captured.out
        assert "Name:" in captured.out
        assert "Project GID:" in captured.out
        assert "Action:" in captured.out

    def test_evaluate_dry_run_shows_only_enabled_rules(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """evaluate_command() dry-run only shows enabled rules."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "enabled-rule"
    name: "Enabled Rule"
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
  - rule_id: "disabled-rule"
    name: "Disabled Rule"
    project_gid: "456"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: false
"""
        config_file = tmp_path / "mixed.yaml"
        config_file.write_text(yaml_content)

        evaluate_command(str(config_file), dry_run=True)

        captured = capsys.readouterr()
        assert "enabled-rule" in captured.out
        assert "disabled-rule" not in captured.out

    def test_evaluate_shows_timing(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """evaluate_command() shows evaluation timing information."""
        evaluate_command(str(temp_config_file))

        captured = capsys.readouterr()
        assert "completed in" in captured.out
        assert "seconds" in captured.out

    def test_evaluate_returns_1_on_invalid_config(
        self,
        temp_invalid_config_file: Path,
        capsys,
    ) -> None:
        """evaluate_command() returns 1 for invalid configuration."""
        exit_code = evaluate_command(str(temp_invalid_config_file))

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Configuration error" in captured.err

    def test_evaluate_returns_1_on_evaluation_error(
        self,
        temp_config_file: Path,
        capsys,
    ) -> None:
        """evaluate_command() returns 1 on evaluation error."""
        with patch(
            "autom8_asana.automation.polling.cli.PollingScheduler._evaluate_rules",
            side_effect=RuntimeError("Test error"),
        ):
            exit_code = evaluate_command(str(temp_config_file))

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "error" in captured.err.lower()


class TestMainCLI:
    """Tests for main() CLI entry point."""

    def test_main_validate_command(
        self,
        temp_config_file: Path,
        monkeypatch,
    ) -> None:
        """main() dispatches to validate_command correctly."""
        monkeypatch.setattr(
            sys, "argv",
            ["cli", "validate", str(temp_config_file)],
        )

        exit_code = main()

        assert exit_code == 0

    def test_main_status_command(
        self,
        temp_config_file: Path,
        monkeypatch,
    ) -> None:
        """main() dispatches to status_command correctly."""
        monkeypatch.setattr(
            sys, "argv",
            ["cli", "status", str(temp_config_file)],
        )

        exit_code = main()

        assert exit_code == 0

    def test_main_evaluate_command(
        self,
        temp_config_file: Path,
        monkeypatch,
    ) -> None:
        """main() dispatches to evaluate_command correctly."""
        monkeypatch.setattr(
            sys, "argv",
            ["cli", "evaluate", str(temp_config_file)],
        )

        exit_code = main()

        assert exit_code == 0

    def test_main_evaluate_with_dry_run(
        self,
        temp_config_file: Path,
        monkeypatch,
        capsys,
    ) -> None:
        """main() passes --dry-run flag to evaluate_command."""
        monkeypatch.setattr(
            sys, "argv",
            ["cli", "evaluate", str(temp_config_file), "--dry-run"],
        )

        exit_code = main()

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_main_no_command_shows_help(
        self,
        monkeypatch,
        capsys,
    ) -> None:
        """main() shows help when no command provided."""
        monkeypatch.setattr(sys, "argv", ["cli"])

        # argparse will call sys.exit with error for missing required subcommand
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit with error code
        assert exc_info.value.code != 0

    def test_main_help_flag(
        self,
        monkeypatch,
        capsys,
    ) -> None:
        """main() shows help with --help flag."""
        monkeypatch.setattr(sys, "argv", ["cli", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "validate" in captured.out
        assert "status" in captured.out
        assert "evaluate" in captured.out

    def test_main_validate_help(
        self,
        monkeypatch,
        capsys,
    ) -> None:
        """main() shows validate subcommand help."""
        monkeypatch.setattr(sys, "argv", ["cli", "validate", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "config_path" in captured.out

    def test_main_evaluate_help(
        self,
        monkeypatch,
        capsys,
    ) -> None:
        """main() shows evaluate subcommand help with --dry-run option."""
        monkeypatch.setattr(sys, "argv", ["cli", "evaluate", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "--dry-run" in captured.out


class TestCLIEdgeCases:
    """Edge case tests for CLI."""

    def test_validate_empty_rules_list(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """validate_command() accepts config with empty rules list."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules: []
"""
        config_file = tmp_path / "empty_rules.yaml"
        config_file.write_text(yaml_content)

        exit_code = validate_command(str(config_file))

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "0 rules loaded" in captured.out

    def test_status_empty_rules_list(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """status_command() handles config with empty rules list."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules: []
"""
        config_file = tmp_path / "empty_rules.yaml"
        config_file.write_text(yaml_content)

        exit_code = status_command(str(config_file))

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Total: 0" in captured.out
        assert "Enabled: 0" in captured.out
        assert "Disabled: 0" in captured.out

    def test_evaluate_dry_run_empty_rules(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """evaluate_command() dry-run handles empty rules list."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules: []
"""
        config_file = tmp_path / "empty_rules.yaml"
        config_file.write_text(yaml_content)

        exit_code = evaluate_command(str(config_file), dry_run=True)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Would evaluate 0 enabled rules" in captured.out

    def test_evaluate_handles_all_disabled_rules(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """evaluate_command() handles config with all rules disabled."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "disabled-1"
    name: "Disabled 1"
    project_gid: "123"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: false
  - rule_id: "disabled-2"
    name: "Disabled 2"
    project_gid: "456"
    conditions:
      - stale:
          field: "Section"
          days: 1
    action:
      type: "add_tag"
      params:
        tag: "test"
    enabled: false
"""
        config_file = tmp_path / "all_disabled.yaml"
        config_file.write_text(yaml_content)

        exit_code = evaluate_command(str(config_file), dry_run=True)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Would evaluate 0 enabled rules" in captured.out

    def test_validate_handles_unicode_in_config(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        """validate_command() handles unicode content in config."""
        yaml_content = """
scheduler:
  time: "02:00"
  timezone: "UTC"
rules:
  - rule_id: "unicode-rule"
    name: "Rule with Unicode"
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

        exit_code = validate_command(str(config_file))

        assert exit_code == 0
