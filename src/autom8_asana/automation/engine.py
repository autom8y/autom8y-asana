"""Automation Engine for rule evaluation and execution.

Per TDD-AUTOMATION-LAYER: AutomationEngine orchestrates rule evaluation and execution.
Per FR-001: Evaluates registered rules after SaveSession commit.
Per NFR-003: Failures do not propagate (isolated execution).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.base import AutomationRule
from autom8_asana.automation.config import AutomationConfig
from autom8_asana.automation.context import AutomationContext
from autom8_asana.persistence.models import AutomationResult

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.models import SaveResult


logger = get_logger(__name__)


class AutomationEngine:
    """Orchestrates automation rule evaluation and execution.

    Per FR-001: Evaluates registered rules after SaveSession commit.

    The engine maintains a registry of rules and evaluates them against
    committed entities. Rules are evaluated in registration order.

    Example:
        engine = AutomationEngine(config)
        engine.register(PipelineConversionRule())
        engine.register(custom_rule)

        # Called by SaveSession after commit
        results = await engine.evaluate_async(save_result, client)
    """

    def __init__(self, config: AutomationConfig) -> None:
        """Initialize automation engine.

        Args:
            config: AutomationConfig with settings.
        """
        self._config = config
        self._rules: list[AutomationRule] = []
        self._enabled = config.enabled

    def register(self, rule: AutomationRule) -> None:
        """Register an automation rule.

        Per FR-008: Rule registry for custom rules.

        Args:
            rule: AutomationRule implementation.

        Raises:
            ValueError: If rule with same ID already registered.

        Example:
            engine.register(PipelineConversionRule())
            engine.register(MyCustomRule())
        """
        for existing in self._rules:
            if existing.id == rule.id:
                raise ValueError(f"Rule with ID '{rule.id}' already registered")
        self._rules.append(rule)
        logger.info(
            "automation_rule_registered",
            rule_name=rule.name,
            rule_id=rule.id,
        )

    def unregister(self, rule_id: str) -> bool:
        """Unregister a rule by ID.

        Args:
            rule_id: ID of rule to remove.

        Returns:
            True if rule was found and removed, False otherwise.
        """
        for i, rule in enumerate(self._rules):
            if rule.id == rule_id:
                del self._rules[i]
                logger.info("automation_rule_unregistered", rule_id=rule_id)
                return True
        return False

    @property
    def rules(self) -> list[AutomationRule]:
        """Get list of registered rules (read-only copy)."""
        return list(self._rules)

    @property
    def enabled(self) -> bool:
        """Whether automation is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether automation is enabled."""
        self._enabled = value

    async def evaluate_async(
        self,
        save_result: SaveResult,
        client: AsanaClient,
    ) -> list[AutomationResult]:
        """Evaluate all rules against committed entities.

        Per FR-001: Called after SaveSession commit completes.
        Per NFR-003: Failures do not propagate (isolated execution).

        Args:
            save_result: SaveResult from completed commit.
            client: AsanaClient for rule execution.

        Returns:
            List of AutomationResult for each rule evaluated.
        """
        if not self._enabled:
            return []

        if not self._rules:
            return []

        results: list[AutomationResult] = []
        context = AutomationContext(
            client=client,
            config=self._config,
            depth=0,
            visited=set(),
            save_result=save_result,
        )

        # Collect entities from successful CRUD operations
        entities_to_evaluate = list(save_result.succeeded)
        seen_gids = {e.gid for e in entities_to_evaluate}

        # Also collect entities from successful action operations that trigger automation
        # Per ADR-0055: Action operations (like MOVE_TO_SECTION) are tracked separately
        # from CRUD operations. A Process moved to a section has no dirty fields, so it
        # won't appear in succeeded - but it should still trigger automation evaluation.
        from autom8_asana.persistence.models import ActionType

        for action_result in save_result.action_results:
            if (
                action_result.success
                and action_result.action.action == ActionType.MOVE_TO_SECTION
            ):
                task = action_result.action.task
                if task.gid not in seen_gids:
                    entities_to_evaluate.append(task)
                    seen_gids.add(task.gid)

        for entity in entities_to_evaluate:
            # Detect event type from entity state
            event = self._detect_event(entity, save_result)
            event_context = self._build_event_context(entity, event, save_result)

            for rule in self._rules:
                # Check if rule should trigger
                if not rule.should_trigger(entity, event, event_context):
                    continue

                # Check loop prevention
                if not context.can_continue(entity.gid, rule.id):
                    results.append(
                        AutomationResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            triggered_by_gid=entity.gid,
                            triggered_by_type=type(entity).__name__,
                            success=True,
                            skipped_reason="circular_reference_prevented",
                        )
                    )
                    logger.debug(
                        "rule_skipped_circular_reference",
                        rule_name=rule.name,
                        rule_id=rule.id,
                        entity_gid=entity.gid,
                    )
                    continue

                # Execute rule with isolation
                context.mark_visited(entity.gid, rule.id)
                start_time = time.perf_counter()

                try:
                    logger.debug(
                        "rule_triggered",
                        rule_name=rule.name,
                        entity_gid=entity.gid,
                        rule_id=rule.id,
                        entity_type=type(entity).__name__,
                    )
                    result = await rule.execute_async(entity, context)
                    results.append(result)

                    if result.success:
                        logger.info(
                            "rule_executed_successfully",
                            rule_name=rule.name,
                            rule_id=rule.id,
                            entities_created=result.entities_created,
                            execution_time_ms=result.execution_time_ms,
                        )
                    else:
                        logger.warning(
                            "rule_execution_failed",
                            rule_name=rule.name,
                            error=result.error,
                            rule_id=rule.id,
                            triggered_by=result.triggered_by_gid,
                        )

                except Exception as e:  # BROAD-CATCH: isolation -- per-rule loop, single rule failure must not abort batch
                    # Per NFR-003: Capture failure, don't propagate
                    execution_time_ms = (time.perf_counter() - start_time) * 1000
                    results.append(
                        AutomationResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            triggered_by_gid=entity.gid,
                            triggered_by_type=type(entity).__name__,
                            success=False,
                            error=str(e),
                            execution_time_ms=execution_time_ms,
                        )
                    )
                    logger.warning(
                        "rule_execution_exception",
                        rule_name=rule.name,
                        error=str(e),
                        rule_id=rule.id,
                        triggered_by=entity.gid,
                    )

        logger.debug(
            "automation_evaluation_complete",
            rules_evaluated=len(results),
            succeeded=sum(1 for r in results if r.success and not r.was_skipped),
            failed=sum(1 for r in results if not r.success),
            skipped=sum(1 for r in results if r.was_skipped),
        )

        return results

    def _detect_event(
        self,
        entity: AsanaResource,
        result: SaveResult,
    ) -> str:
        """Detect event type for entity.

        Args:
            entity: The entity to check.
            result: SaveResult with action results.

        Returns:
            Event type string: "created", "updated", or "section_changed".
        """
        # Import here to avoid circular imports
        from autom8_asana.persistence.models import ActionType

        # Check action_results for section changes
        for action in result.action_results:
            action_op = action.action
            if (
                action_op.task.gid == entity.gid
                and action_op.action == ActionType.MOVE_TO_SECTION
                and action.success
            ):
                return "section_changed"

        # Check entity state for new entities
        if hasattr(entity, "_is_new") and entity._is_new:
            return "created"

        # Check for temp GID pattern (indicates newly created)
        if entity.gid and entity.gid.startswith("temp_"):
            return "created"

        return "updated"

    def _build_event_context(
        self,
        entity: AsanaResource,
        event: str,
        result: SaveResult,
    ) -> dict[str, Any]:
        """Build context dict for event matching.

        Args:
            entity: The entity that triggered the event.
            event: The event type detected.
            result: SaveResult with action results.

        Returns:
            Context dict with event details.
        """
        # Import here to avoid circular imports
        from autom8_asana.persistence.models import ActionType

        context: dict[str, Any] = {"event": event}

        if event == "section_changed":
            # Find section from action results
            for action in result.action_results:
                action_op = action.action
                if (
                    action_op.task.gid == entity.gid
                    and action_op.action == ActionType.MOVE_TO_SECTION
                ):
                    # Per ADR-0107: target is NameGid with gid and name
                    if action_op.target:
                        context["section_gid"] = action_op.target.gid
                        if action_op.target.name:
                            context["section"] = action_op.target.name.lower()
                    break

        # Add entity-specific context attributes
        if hasattr(entity, "process_type"):
            process_type = entity.process_type
            if hasattr(process_type, "value"):
                context["process_type"] = process_type.value
            else:
                context["process_type"] = process_type

        return context
