"""CLI commands for polling-based automation.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Provides CLI commands for manual operations
including validation, status checking, and single evaluation cycles.

Usage:
    # Validate configuration
    python -m autom8_asana.automation.polling.cli validate /path/to/rules.yaml

    # Show scheduler status and rule summary
    python -m autom8_asana.automation.polling.cli status /path/to/rules.yaml

    # Run one evaluation cycle
    python -m autom8_asana.automation.polling.cli evaluate /path/to/rules.yaml

    # Run evaluation in dry-run mode (log without executing)
    python -m autom8_asana.automation.polling.cli evaluate /path/to/rules.yaml --dry-run

Exit Codes:
    0: Success
    1: Error (configuration invalid, evaluation failed, etc.)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from autom8y_log import get_logger

from autom8_asana.automation.polling.config_loader import ConfigurationLoader
from autom8_asana.automation.polling.config_schema import AutomationRulesConfig
from autom8_asana.automation.polling.polling_scheduler import PollingScheduler
from autom8_asana.automation.polling.structured_logger import StructuredLogger
from autom8_asana.exceptions import ConfigurationError

__all__ = [
    "validate_command",
    "status_command",
    "evaluate_command",
    "main",
]

# Configure module logger
logger = get_logger(__name__)


def validate_command(config_path: str) -> int:
    """Validate configuration file.

    Loads and validates the YAML configuration file against the schema.
    Performs:
    - YAML syntax validation
    - Environment variable substitution
    - Pydantic schema validation

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Exit code: 0 on success, 1 on validation failure.

    Example:
        exit_code = validate_command("/etc/autom8_asana/rules.yaml")
        # Prints: Configuration valid: 5 rules loaded
    """
    try:
        config = ConfigurationLoader.load_from_file(config_path, AutomationRulesConfig)
        print(f"Configuration valid: {len(config.rules)} rules loaded")
        return 0

    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    except Exception as e:  # BROAD-CATCH: boundary -- CLI entry point
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def status_command(config_path: str) -> int:
    """Show scheduler and rule status.

    Validates configuration and displays:
    - Scheduler configuration (time, timezone)
    - Rule summary (total, enabled, disabled counts)

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Exit code: 0 on success, 1 on error.

    Example:
        exit_code = status_command("/etc/autom8_asana/rules.yaml")
        # Prints:
        # Scheduler Configuration:
        #   Time: 02:00
        #   Timezone: America/New_York
        #
        # Rules Summary:
        #   Total: 5
        #   Enabled: 4
        #   Disabled: 1
    """
    try:
        config = ConfigurationLoader.load_from_file(config_path, AutomationRulesConfig)

        # Count enabled/disabled rules
        enabled_count = sum(1 for rule in config.rules if rule.enabled)
        disabled_count = len(config.rules) - enabled_count

        # Print scheduler configuration
        print("Scheduler Configuration:")
        print(f"  Time: {config.scheduler.time}")
        print(f"  Timezone: {config.scheduler.timezone}")
        print()

        # Print rules summary
        print("Rules Summary:")
        print(f"  Total: {len(config.rules)}")
        print(f"  Enabled: {enabled_count}")
        print(f"  Disabled: {disabled_count}")

        return 0

    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    except Exception as e:  # BROAD-CATCH: boundary -- CLI entry point
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def evaluate_command(config_path: str, dry_run: bool = False) -> int:
    """Run one evaluation cycle.

    Loads configuration and runs a single evaluation cycle. In dry-run mode,
    logs what would happen without executing actions.

    Args:
        config_path: Path to the YAML configuration file.
        dry_run: If True, log what would happen without executing actions.

    Returns:
        Exit code: 0 on success, 1 on error.

    Example:
        # Normal evaluation
        exit_code = evaluate_command("/etc/autom8_asana/rules.yaml")

        # Dry-run mode
        exit_code = evaluate_command("/etc/autom8_asana/rules.yaml", dry_run=True)
        # Prints: [DRY RUN] Would evaluate 4 enabled rules...
    """
    try:
        # Configure structured logging for evaluation output
        StructuredLogger.configure(json_format=False, level="INFO")

        # Load and validate configuration
        config = ConfigurationLoader.load_from_file(config_path, AutomationRulesConfig)

        # Count enabled rules
        enabled_count = sum(1 for rule in config.rules if rule.enabled)

        if dry_run:
            # Dry-run mode: log what would happen
            print(f"[DRY RUN] Would evaluate {enabled_count} enabled rules...")
            print()

            for rule in config.rules:
                if rule.enabled:
                    print(f"  Rule: {rule.rule_id}")
                    print(f"    Name: {rule.name}")
                    print(f"    Project GID: {rule.project_gid}")
                    print(f"    Conditions: {len(rule.conditions)}")
                    print(f"    Action: {rule.action.type}")
                    print()

            print(
                "[DRY RUN] Skipping actual evaluation (use without --dry-run to execute)"
            )
            return 0

        # Create scheduler and run single evaluation
        scheduler = PollingScheduler(config)

        # Log evaluation start
        utc_now = datetime.now(UTC)
        print(f"Starting evaluation cycle at {utc_now.isoformat()}")
        print(f"Evaluating {enabled_count} enabled rules...")
        print()

        # Run the evaluation (uses run_once internally without lock for CLI)
        # Note: We call _evaluate_rules directly to avoid file locking for CLI usage
        scheduler._evaluate_rules()

        # Log completion
        utc_end = datetime.now(UTC)
        duration = (utc_end - utc_now).total_seconds()
        print()
        print(f"Evaluation completed in {duration:.2f} seconds")

        return 0

    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    except Exception as e:  # BROAD-CATCH: boundary -- CLI entry point
        print(f"Evaluation error: {e}", file=sys.stderr)
        logger.exception("Evaluation failed")
        return 1


def main() -> int:
    """CLI entry point.

    Parses command-line arguments and dispatches to the appropriate
    subcommand handler.

    Returns:
        Exit code: 0 on success, 1 on error.

    Usage:
        python -m autom8_asana.automation.polling.cli <command> [options]

    Commands:
        validate <config_path>           Validate configuration file
        status <config_path>             Show scheduler and rule status
        evaluate <config_path> [--dry-run]  Run one evaluation cycle
    """
    # Configure logging via SDK (idempotent guard prevents double-configure)
    from autom8_asana.core.logging import configure

    configure(level="WARNING")

    # Create main parser
    parser = argparse.ArgumentParser(
        prog="autom8_asana.automation.polling.cli",
        description="CLI commands for polling-based automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate configuration
  python -m autom8_asana.automation.polling.cli validate rules.yaml

  # Show scheduler status
  python -m autom8_asana.automation.polling.cli status rules.yaml

  # Run evaluation
  python -m autom8_asana.automation.polling.cli evaluate rules.yaml

  # Dry-run evaluation
  python -m autom8_asana.automation.polling.cli evaluate rules.yaml --dry-run
        """,
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
        help="Available commands",
    )

    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate configuration without starting scheduler",
        description="Load and validate YAML configuration file.",
    )
    validate_parser.add_argument(
        "config_path",
        help="Path to YAML configuration file",
    )

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show scheduler status and rule summary",
        description="Display scheduler configuration and rule counts.",
    )
    status_parser.add_argument(
        "config_path",
        help="Path to YAML configuration file",
    )

    # evaluate command
    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Run one evaluation cycle (for testing/debugging)",
        description="Execute a single evaluation cycle against configured rules.",
    )
    evaluate_parser.add_argument(
        "config_path",
        help="Path to YAML configuration file",
    )
    evaluate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would happen without executing actions",
    )

    # Parse arguments
    args = parser.parse_args()

    # Dispatch to command handler
    if args.command == "validate":
        return validate_command(args.config_path)
    elif args.command == "status":
        return status_command(args.config_path)
    elif args.command == "evaluate":
        return evaluate_command(args.config_path, dry_run=args.dry_run)
    else:
        parser.print_help()
        return 1


# Entry point for python -m execution
if __name__ == "__main__":
    sys.exit(main())
