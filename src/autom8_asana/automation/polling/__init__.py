"""Polling-based automation for time-based triggers.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Provides daily polling automation
with YAML configuration, environment variable substitution, and Pydantic
validation.

Main API:
    ConfigurationLoader: Loads and validates YAML configuration files
    PollingScheduler: Daily polling scheduler with timezone support
    TriggerEvaluator: Evaluates rule conditions against tasks
    ActionExecutor: Executes actions on tasks matching rule conditions
    ActionResult: Result of action execution
    AutomationRulesConfig: Top-level configuration schema
    Rule: Single automation rule definition
    RuleCondition: Condition specification with trigger types
    ActionConfig: Action to execute when rules match
    SchedulerConfig: Scheduler timing configuration
    TriggerStaleConfig: Stale detection trigger
    TriggerDeadlineConfig: Deadline proximity trigger
    TriggerAgeConfig: Age since creation trigger

Example - Load Configuration:
    from autom8_asana.automation.polling import (
        ConfigurationLoader,
        AutomationRulesConfig,
    )

    config = ConfigurationLoader.load_from_file(
        "/etc/autom8_asana/rules.yaml",
        AutomationRulesConfig,
    )
    print(f"Loaded {len(config.rules)} rules")
    print(f"Scheduler time: {config.scheduler.time}")

Example - Access Rules:
    for rule in config.rules:
        if rule.enabled:
            print(f"Rule: {rule.name}")
            for condition in rule.conditions:
                if condition.stale:
                    print(f"  Stale trigger: {condition.stale.days} days")
                if condition.deadline:
                    print(f"  Deadline trigger: {condition.deadline.days} days")

Example - Evaluate Conditions:
    from autom8_asana.automation.polling import TriggerEvaluator

    evaluator = TriggerEvaluator()
    for rule in config.rules:
        if rule.enabled:
            matching_tasks = evaluator.evaluate_conditions(rule, tasks)
            print(f"Rule '{rule.name}': {len(matching_tasks)} matches")

Example - Run Scheduler (Development):
    from autom8_asana.automation.polling import PollingScheduler

    scheduler = PollingScheduler.from_config_file("/etc/autom8_asana/rules.yaml")
    scheduler.run()  # Blocks, runs daily at configured time

Example - Run Once (Production Cron):
    from autom8_asana.automation.polling import PollingScheduler

    scheduler = PollingScheduler.from_config_file("/etc/autom8_asana/rules.yaml")
    scheduler.run_once()  # Execute once and exit

    # Cron entry: 0 2 * * * python -m autom8_asana.automation.polling.polling_scheduler /etc/rules.yaml

Example - YAML Configuration:
    # rules.yaml
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

from autom8_asana.automation.polling.action_executor import (
    ActionExecutor,
    ActionResult,
)
from autom8_asana.automation.polling.config_loader import ConfigurationLoader
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
from autom8_asana.automation.polling.polling_scheduler import PollingScheduler
from autom8_asana.automation.polling.structured_logger import StructuredLogger
from autom8_asana.automation.polling.trigger_evaluator import TriggerEvaluator

__all__ = [
    # Action executor
    "ActionExecutor",
    "ActionResult",
    # Configuration loader
    "ConfigurationLoader",
    # Polling scheduler
    "PollingScheduler",
    # Structured logger
    "StructuredLogger",
    # Trigger evaluator
    "TriggerEvaluator",
    # Schema models
    "AutomationRulesConfig",
    "SchedulerConfig",
    "Rule",
    "RuleCondition",
    "ActionConfig",
    "TriggerStaleConfig",
    "TriggerDeadlineConfig",
    "TriggerAgeConfig",
]
