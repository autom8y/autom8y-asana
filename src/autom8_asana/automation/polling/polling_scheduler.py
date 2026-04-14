"""Daily polling scheduler for automation rules.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Provides scheduling infrastructure for
polling-based automation with timezone-aware daily execution.

Key responsibilities:
- Load configuration via ConfigurationLoader
- Schedule daily execution at configured time
- Prevent concurrent execution via file locking
- Support both development (APScheduler) and production (cron) modes

Production Cron Example:
    # Run daily at 2:00 AM in configured timezone
    # crontab entry (system cron):
    0 2 * * * cd /app && python -m autom8_asana.automation.polling.scheduler /etc/rules.yaml

    # The scheduler interprets the config file's timezone for logging,
    # but cron itself should be set to match the desired timezone.
    # For timezone-aware cron, use systemd timers or ensure cron runs in the correct TZ.

Development Example:
    from autom8_asana.automation.polling import PollingScheduler

    scheduler = PollingScheduler.from_config_file("/etc/autom8_asana/rules.yaml")
    scheduler.run()  # Blocks, runs job daily at configured time

Single Execution Example:
    scheduler = PollingScheduler.from_config_file("/etc/autom8_asana/rules.yaml")
    scheduler.run_once()  # Execute once and exit (for cron)

Note: APScheduler is required for development mode (scheduler.run()).
    Add 'apscheduler>=3.10.0' to your dependencies if using development mode.
"""

from __future__ import annotations

import asyncio
import fcntl
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from autom8y_log import get_logger

from autom8_asana.automation.polling.action_executor import ActionExecutor
from autom8_asana.automation.polling.config_loader import ConfigurationLoader
from autom8_asana.automation.polling.config_schema import (
    AutomationRulesConfig,
    ScheduleConfig,
)
from autom8_asana.automation.polling.structured_logger import StructuredLogger
from autom8_asana.automation.polling.trigger_evaluator import TriggerEvaluator
from autom8_asana.core.scope import EntityScope
from autom8_asana.errors import ConfigurationError

if TYPE_CHECKING:
    from apscheduler.schedulers.blocking import BlockingScheduler

    from autom8_asana.automation.workflows.base import WorkflowAction
    from autom8_asana.automation.workflows.registry import WorkflowRegistry

__all__ = ["PollingScheduler"]

# Fallback stdlib logger for non-evaluation logging (initialization, locks)
logger = get_logger(__name__)

# Default lock file location
DEFAULT_LOCK_PATH = "/tmp/autom8_asana_polling.lock"


class PollingScheduler:
    """Daily polling scheduler for automation rules.

    Provides scheduling infrastructure for polling-based automation with
    timezone-aware daily execution. Supports both development mode (using
    APScheduler for blocking execution) and production mode (single execution
    for cron-based scheduling).

    Example (development):
        scheduler = PollingScheduler.from_config_file("rules.yaml")
        scheduler.run()  # Blocks, runs job daily

    Example (production cron):
        # crontab: 0 2 * * * python -m autom8_asana.automation.polling.scheduler /etc/rules.yaml
        scheduler = PollingScheduler.from_config_file(sys.argv[1])
        scheduler.run_once()

    Attributes:
        config: The loaded AutomationRulesConfig.
        lock_path: Path to the lock file for preventing concurrent execution.
        timezone: The ZoneInfo object for the configured timezone.
    """

    def __init__(
        self,
        config: AutomationRulesConfig,
        *,
        lock_path: str = DEFAULT_LOCK_PATH,
        client: Any = None,
        workflow_registry: WorkflowRegistry | None = None,
    ) -> None:
        """Initialize the polling scheduler.

        Args:
            config: Validated AutomationRulesConfig containing scheduler settings
                and automation rules.
            lock_path: Path to the lock file for preventing concurrent execution.
                Defaults to /tmp/autom8_asana_polling.lock.
            client: Optional Asana client for action execution. If not provided,
                matched tasks will be logged but actions will not be executed
                (dry-run mode).
            workflow_registry: Optional WorkflowRegistry for batch workflow dispatch.
                Per TDD-CONV-AUDIT-001: Enables schedule-driven workflow execution.

        Raises:
            ConfigurationError: If the configured timezone is invalid.
        """
        self.config = config
        self.lock_path = lock_path
        self._client = client
        self._evaluator = TriggerEvaluator()
        self._action_executor = ActionExecutor(client) if client else None
        self._workflow_registry = workflow_registry

        # Validate and parse timezone
        try:
            self.timezone = ZoneInfo(config.scheduler.timezone)
        except ZoneInfoNotFoundError as e:
            raise ConfigurationError(
                f"Invalid timezone '{config.scheduler.timezone}'. "
                f"Use IANA timezone names (e.g., 'UTC', 'America/New_York')."
            ) from e

        # Parse time into hour and minute
        time_parts = config.scheduler.time.split(":")
        self._hour = int(time_parts[0])
        self._minute = int(time_parts[1])

        logger.info(
            "polling_scheduler_initialized",
            rule_count=len(config.rules),
            scheduled_time=config.scheduler.time,
            timezone=config.scheduler.timezone,
        )

    @classmethod
    def from_config_file(
        cls,
        file_path: str,
        *,
        lock_path: str = DEFAULT_LOCK_PATH,
        client: Any = None,
    ) -> PollingScheduler:
        """Create a PollingScheduler from a YAML configuration file.

        Loads and validates the configuration file, then creates a scheduler
        instance. This is the preferred factory method for creating schedulers.

        Args:
            file_path: Path to the YAML configuration file.
            lock_path: Path to the lock file for preventing concurrent execution.
                Defaults to /tmp/autom8_asana_polling.lock.
            client: Optional Asana client for action execution. If not provided,
                matched tasks will be logged but actions will not be executed
                (dry-run mode).

        Returns:
            Configured PollingScheduler instance.

        Raises:
            ConfigurationError: If the file is missing, invalid YAML,
                or fails schema validation.

        Example:
            scheduler = PollingScheduler.from_config_file("/etc/autom8_asana/rules.yaml")
        """
        config = ConfigurationLoader.load_from_file(file_path, AutomationRulesConfig)
        return cls(config, lock_path=lock_path, client=client)

    def run(self) -> None:
        """Start blocking scheduler for development (APScheduler).

        Creates an APScheduler BlockingScheduler that runs the evaluation job
        daily at the configured time in the configured timezone. This method
        blocks indefinitely until interrupted.

        The job is configured with:
        - CronTrigger for daily execution at the configured hour/minute
        - Timezone-aware scheduling using the configured timezone
        - Coalesce=True to skip missed runs on restart
        - Max instances=1 to prevent overlapping execution

        Raises:
            ImportError: If APScheduler is not installed. Install with:
                pip install apscheduler>=3.10.0

        Example:
            scheduler = PollingScheduler.from_config_file("rules.yaml")
            scheduler.run()  # Blocks until Ctrl+C
        """
        try:
            from apscheduler.schedulers.blocking import (
                BlockingScheduler as APBlockingScheduler,
            )
            from apscheduler.triggers.cron import CronTrigger
        except ImportError as e:
            raise ImportError(
                "APScheduler is required for development mode. "
                "Install with: pip install apscheduler>=3.10.0"
            ) from e

        # Create the blocking scheduler
        scheduler: BlockingScheduler = APBlockingScheduler()

        # Create cron trigger for daily execution
        trigger = CronTrigger(
            hour=self._hour,
            minute=self._minute,
            timezone=self.timezone,
        )

        # Add job with coalesce to skip missed runs
        scheduler.add_job(
            self._evaluate_rules,
            trigger=trigger,
            id="polling_evaluation",
            name=f"Daily rule evaluation at {self.config.scheduler.time}",
            coalesce=True,
            max_instances=1,
        )

        logger.info(
            "blocking_scheduler_started",
            next_run_time=self.config.scheduler.time,
            timezone=self.config.scheduler.timezone,
        )

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("scheduler_stopped_by_user")
            scheduler.shutdown()

    def run_once(self) -> None:
        """Execute one evaluation cycle (for cron).

        Acquires a file lock to prevent concurrent execution, then evaluates
        all enabled rules. This method is designed for production use with
        system cron or similar external schedulers.

        If the lock cannot be acquired (another instance is running), the
        method logs a warning and returns without executing. This provides
        safe behavior when cron jobs overlap due to long-running evaluations.

        The lock is held for the duration of rule evaluation and automatically
        released on completion or error.

        Example:
            # In a cron script:
            scheduler = PollingScheduler.from_config_file(sys.argv[1])
            scheduler.run_once()
        """
        utc_now = datetime.now(UTC)
        local_now = utc_now.astimezone(self.timezone)

        logger.info(
            "single_evaluation_run_started",
            local_time=local_now.isoformat(),
            utc_time=utc_now.isoformat(),
        )

        # Try to acquire lock
        lock_file = None
        try:
            lock_file = self._acquire_lock()
            if lock_file is None:
                logger.warning(
                    "lock_acquisition_failed",
                    lock_path=self.lock_path,
                    reason="another_instance_running",
                )
                return

            # Execute evaluation
            self._evaluate_rules()

        finally:
            if lock_file is not None:
                self._release_lock(lock_file)

        utc_end = datetime.now(UTC)
        duration = (utc_end - utc_now).total_seconds()
        logger.info(
            "evaluation_completed",
            duration_seconds=round(duration, 2),
            utc_time=utc_end.isoformat(),
        )

    def _evaluate_rules(self, tasks_by_project: dict[str, list[Any]] | None = None) -> None:
        """Internal: evaluate all enabled rules and execute actions on matches.

        Iterates through all rules in the configuration, evaluating each
        enabled rule against its project's tasks. Uses structured logging
        for JSON-formatted output suitable for log aggregation.

        For matched tasks, if an ActionExecutor is configured (client was provided),
        actions are executed asynchronously. If no client is provided (dry-run mode),
        matched tasks are logged but actions are not executed.

        This method is called by both run() and run_once().

        Args:
            tasks_by_project: Optional dict mapping project_gid to list of tasks.
                If not provided, rules are evaluated but no tasks will match
                (placeholder for future task fetching integration).
        """
        utc_now = datetime.now(UTC)

        # Get structured logger with bound context for this evaluation cycle
        structured_log = StructuredLogger.get_logger(
            scheduler_timezone=self.config.scheduler.timezone,
            scheduled_time=self.config.scheduler.time,
        )

        structured_log.info(
            "evaluation_cycle_started",
            timestamp_utc=utc_now.isoformat(),
            dry_run=self._action_executor is None,
        )

        enabled_rules = [r for r in self.config.rules if r.enabled]
        structured_log.info(
            "rules_loaded",
            enabled_count=len(enabled_rules),
            total_count=len(self.config.rules),
        )

        # Use empty dict if no tasks provided
        if tasks_by_project is None:
            tasks_by_project = {}

        for rule in enabled_rules:
            rule_start = time.perf_counter()

            # Schedule-driven workflow dispatch (TDD-CONV-AUDIT-001)
            if rule.schedule is not None and rule.action.type == "workflow":
                self._dispatch_scheduled_workflow(rule, structured_log)
                continue  # Skip condition evaluation for schedule-driven rules

            structured_log.debug(
                "rule_evaluation_started",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                project_gid=rule.project_gid,
                condition_count=len(rule.conditions),
                action_type=rule.action.type,
            )

            # Get tasks for this rule's project
            tasks = tasks_by_project.get(rule.project_gid, [])

            # Evaluate conditions using TriggerEvaluator
            matched_tasks = self._evaluator.evaluate_conditions(rule, tasks)
            matches = len(matched_tasks)

            # Execute actions on matched tasks if executor is available
            if matched_tasks and self._action_executor:
                # Run async action execution in sync context
                asyncio.run(self._execute_actions_async(matched_tasks, rule, structured_log))
            elif matched_tasks:
                # Dry-run mode: log matches without executing actions
                for task in matched_tasks:
                    task_gid = getattr(task, "gid", str(task))
                    structured_log.info(
                        "action_skipped_dry_run",
                        rule_id=rule.rule_id,
                        task_gid=task_gid,
                        action_type=rule.action.type,
                    )

            rule_end = time.perf_counter()
            duration_ms = (rule_end - rule_start) * 1000

            # Use structured logging for rule evaluation result
            StructuredLogger.log_rule_evaluation(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                project_gid=rule.project_gid,
                matches=matches,
                duration_ms=duration_ms,
            )

        utc_end = datetime.now(UTC)
        cycle_duration_ms = (utc_end - utc_now).total_seconds() * 1000

        structured_log.info(
            "evaluation_cycle_complete",
            rules_evaluated=len(enabled_rules),
            total_duration_ms=cycle_duration_ms,
            timestamp_utc=utc_end.isoformat(),
        )

    def _dispatch_scheduled_workflow(self, rule: Any, structured_log: Any) -> None:
        """Dispatch a schedule-driven workflow rule.

        Checks if the schedule is due, looks up the workflow in the registry,
        and executes it. Logs errors for missing workflows or unconfigured
        registries, and debug messages for schedules not yet due.

        Args:
            rule: The automation rule with schedule and workflow action.
            structured_log: Logger instance for structured logging.
        """
        if not self._should_run_schedule(rule.schedule):
            structured_log.debug(
                "schedule_not_due",
                rule_id=rule.rule_id,
                frequency=rule.schedule.frequency,
                day_of_week=rule.schedule.day_of_week,
            )
            return

        workflow_id = rule.action.params.get("workflow_id")
        if workflow_id and self._workflow_registry:
            workflow = self._workflow_registry.get(workflow_id)
            if workflow:
                asyncio.run(self._execute_workflow_async(workflow, rule, structured_log))
            else:
                structured_log.error(
                    "workflow_not_found",
                    rule_id=rule.rule_id,
                    workflow_id=workflow_id,
                    available=self._workflow_registry.list_ids(),
                )
        elif not self._workflow_registry:
            structured_log.error(
                "workflow_registry_not_configured",
                rule_id=rule.rule_id,
            )

    async def _execute_actions_async(
        self,
        matched_tasks: list[Any],
        rule: Any,
        structured_log: Any,
    ) -> None:
        """Execute actions on matched tasks asynchronously.

        Iterates through matched tasks and executes the rule's action on each.
        Errors in one action do not prevent other actions from executing.

        Args:
            matched_tasks: List of task objects that matched the rule conditions.
            rule: The automation rule containing the action to execute.
            structured_log: Logger instance for structured logging.
        """
        # This method is only called when _action_executor is not None
        assert self._action_executor is not None

        for task in matched_tasks:
            task_gid = getattr(task, "gid", str(task))
            try:
                result = await self._action_executor.execute_async(
                    task_gid=task_gid,
                    action=rule.action,
                )
                # Log the action result
                StructuredLogger.log_action_result(result, rule_id=rule.rule_id)
            except Exception as exc:  # BROAD-CATCH: isolation -- per-task loop, single task failure must not abort batch  # noqa: BLE001
                structured_log.error(
                    "action_execution_error",
                    rule_id=rule.rule_id,
                    task_gid=task_gid,
                    error=str(exc),
                )

    def _should_run_schedule(self, schedule: ScheduleConfig) -> bool:
        """Check if a schedule-driven rule should run now.

        Per TDD-CONV-AUDIT-001 Section 3.4: For weekly schedules, checks if
        today matches the configured day_of_week. For daily schedules, always
        returns True (runs every day).

        Args:
            schedule: ScheduleConfig with frequency and day_of_week.

        Returns:
            True if the schedule matches the current day.
        """
        local_now = datetime.now(UTC).astimezone(self.timezone)

        if schedule.frequency == "daily":
            return True

        if schedule.frequency == "weekly":
            # Python: Monday=0, Sunday=6
            day_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            target_day = day_map.get(schedule.day_of_week or "", -1)
            return local_now.weekday() == target_day

        return False

    async def _execute_workflow_async(
        self,
        workflow: WorkflowAction,
        rule: Any,
        structured_log: Any,
    ) -> None:
        """Execute a workflow with pre-flight validation and logging.

        Per TDD-CONV-AUDIT-001 Section 3.4: Runs validation, then executes
        the workflow. Errors are caught and logged without re-raising to
        allow the evaluation cycle to continue.

        Args:
            workflow: WorkflowAction instance to execute.
            rule: The automation rule containing workflow parameters.
            structured_log: Logger instance for structured logging.
        """
        workflow_id = rule.action.params.get("workflow_id", "unknown")

        # Pre-flight validation
        validation_errors = await workflow.validate_async()
        if validation_errors:
            structured_log.error(
                "workflow_validation_failed",
                rule_id=rule.rule_id,
                workflow_id=workflow_id,
                errors=validation_errors,
            )
            return

        # Enumerate entities then execute workflow
        try:
            scope = EntityScope.from_event(rule.action.params)
            entities = await workflow.enumerate_async(scope)
            result = await workflow.execute_async(entities, rule.action.params)
            structured_log.info(
                "workflow_completed",
                rule_id=rule.rule_id,
                workflow_id=workflow_id,
                total=result.total,
                succeeded=result.succeeded,
                failed=result.failed,
                skipped=result.skipped,
                duration_seconds=round(result.duration_seconds, 2),
            )
        except (
            Exception  # noqa: BLE001
        ) as exc:  # BROAD-CATCH: isolation -- workflow failure must not abort evaluation cycle
            structured_log.error(
                "workflow_execution_error",
                rule_id=rule.rule_id,
                workflow_id=workflow_id,
                error=str(exc),
            )

    def _acquire_lock(self) -> IO[str] | None:
        """Acquire file lock for concurrent execution prevention.

        Uses fcntl.flock() with LOCK_EX | LOCK_NB for non-blocking exclusive
        lock. If the lock file doesn't exist, it is created.

        Returns:
            Open file handle if lock acquired, None if lock is held by another process.

        Note:
            The caller must call _release_lock() with the returned file handle
            when done, or use a try/finally block.
        """
        lock_path = Path(self.lock_path)

        # Ensure parent directory exists
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Open or create lock file
            lock_file = open(lock_path, "w")  # noqa: SIM115 — lock file held across function return; cannot use `with` block

            # Try to acquire non-blocking exclusive lock
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write PID for debugging
            lock_file.write(f"{datetime.now(UTC).isoformat()}\npid={sys.executable}\n")
            lock_file.flush()

            logger.debug("lock_acquired", lock_path=self.lock_path)
            return lock_file

        except OSError:
            # Lock is held by another process (EWOULDBLOCK/EAGAIN)
            logger.debug("lock_held_by_other_process", lock_path=self.lock_path)
            if lock_file:
                lock_file.close()
            return None

    def _release_lock(self, lock_file: IO[str]) -> None:
        """Release file lock.

        Releases the fcntl lock and closes the file handle.

        Args:
            lock_file: Open file handle from _acquire_lock().
        """
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            logger.debug("lock_released", lock_path=self.lock_path)
        except OSError as e:
            logger.warning("lock_release_error", lock_path=self.lock_path, error=str(e))


# Entry point for cron execution
if __name__ == "__main__":
    import argparse

    from autom8_asana.core.logging import configure

    configure(level="INFO")

    parser = argparse.ArgumentParser(
        description="Run polling scheduler for automation rules.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once (for cron):
  python -m autom8_asana.automation.polling.polling_scheduler /etc/rules.yaml

  # Run in development mode (blocking):
  python -m autom8_asana.automation.polling.polling_scheduler /etc/rules.yaml --dev

Cron entry example:
  0 2 * * * python -m autom8_asana.automation.polling.polling_scheduler /etc/rules.yaml
        """,
    )
    parser.add_argument(
        "config_file",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode with APScheduler (blocking)",
    )
    parser.add_argument(
        "--lock-path",
        default=DEFAULT_LOCK_PATH,
        help=f"Path to lock file (default: {DEFAULT_LOCK_PATH})",
    )

    args = parser.parse_args()

    try:
        scheduler = PollingScheduler.from_config_file(
            args.config_file,
            lock_path=args.lock_path,
        )

        if args.dev:
            scheduler.run()
        else:
            scheduler.run_once()

    except ConfigurationError as e:
        logger.error("configuration_error", error=str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("interrupted_by_user")
        sys.exit(0)
