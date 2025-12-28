# Automation Layer

> Rule-based automation for pipeline conversion, field seeding, and custom business logic.

---

## Table of Contents

1. [Why Automation](#why-automation)
2. [Architecture Overview](#architecture-overview)
3. [AutomationRule Protocol](#automationrule-protocol)
4. [AutomationEngine](#automationengine)
5. [PipelineConversionRule](#pipelineconversionrule)
6. [TemplateDiscovery](#templatediscovery)
7. [FieldSeeder](#fieldseeder)
8. [Creating Custom Rules](#creating-custom-rules)
9. [Testing Automation](#testing-automation)
10. [Key Files](#key-files)

---

## Why Automation

The core business value of the platform is **pipeline advancement**. When a Process completes one stage, a new Process should automatically be created in the next stage. This is the "Salesforce-like" behavior that transforms Asana from a database into an automation platform.

**Before automation**: Manual process creation, field copying, template hunting.

**After automation**: Stage advancement triggers automatic Process creation with correct template and field values.

```
Process (SALES, COMPLETE)
        |
   [User moves to COMPLETE section]
        |
        v
SaveSession.commit()
        |
        v
AutomationEngine (post-commit hook)
        |
        v
PipelineConversionRule triggers:
  1. Detect: Process in COMPLETE, not terminal
  2. Discover: Find ONBOARDING template
  3. Create: New Process (ONBOARDING, BACKLOG)
  4. Seed: Propagate fields from source + hierarchy
        |
        v
Nested SaveSession.commit()
```

---

## Architecture Overview

```
+------------------------------------------+
|              SaveSession                  |
|  +------------------------------------+   |
|  | commit_async()                     |   |
|  |   Phase 1: CRUD                    |   |
|  |   Phase 2: Cascade                 |   |
|  |   Phase 3: Actions                 |   |
|  |   Phase 4: Post-Commit Hooks  <--------+-- Extension Point
|  +------------------------------------+   |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|            AutomationEngine               |
|  +------------------------------------+   |
|  | on_commit(session, result)         |   |
|  |   for entity in result.succeeded:  |   |
|  |     for rule in self.rules:        |   |
|  |       if rule.should_trigger():    |   |
|  |         rule.execute()             |   |
|  +------------------------------------+   |
+------------------------------------------+
                    |
        +-----------+-----------+
        |                       |
        v                       v
+----------------+    +------------------+
| PipelineRule   |    | CustomRule       |
| (built-in)     |    | (user-defined)   |
+----------------+    +------------------+
```

---

## AutomationRule Protocol

All automation rules implement this protocol:

```python
from typing import Protocol
from autom8_asana.persistence.session import SaveSession
from autom8_asana.persistence.models import SaveResult
from autom8_asana.models.base import AsanaResource

class AutomationRule(Protocol):
    """Protocol for automation rules."""

    @property
    def name(self) -> str:
        """Human-readable rule name for logging."""
        ...

    async def should_trigger(
        self,
        entity: AsanaResource,
        result: SaveResult,
    ) -> bool:
        """Evaluate whether this rule should execute for the entity.

        Args:
            entity: The entity that was just committed
            result: Full SaveResult with context

        Returns:
            True if rule should execute, False otherwise
        """
        ...

    async def execute(
        self,
        session: SaveSession,
        entity: AsanaResource,
        result: SaveResult,
    ) -> None:
        """Execute the rule's automation logic.

        Args:
            session: Parent session (for spawning nested sessions)
            entity: The entity that triggered the rule
            result: Full SaveResult with context
        """
        ...
```

---

## AutomationEngine

The engine orchestrates rule execution as a post-commit hook:

```python
from autom8_asana.automation.base import AutomationEngine, AutomationRule
from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.automation.config import AutomationConfig

# Create engine with rules
config = AutomationConfig()
engine = AutomationEngine(
    config=config,
    rules=[
        PipelineConversionRule(config.pipeline),
        # ... additional rules
    ],
)

# Register with session
async with client.save_session() as session:
    session.register_hook(engine)

    # Track and modify
    session.track(process)
    process.section = ProcessSection.COMPLETE

    # Commit triggers automation
    result = await session.commit_async()
```

### Engine Behavior

1. **Filter**: Only process entities that actually changed
2. **Evaluate**: Check `should_trigger()` for each rule
3. **Execute**: Run `execute()` for triggered rules
4. **Isolate**: Each rule gets its own nested session
5. **Report**: Log all rule executions and results

### Safety Features

```python
class AutomationEngine:
    def __init__(
        self,
        config: AutomationConfig,
        rules: list[AutomationRule],
    ):
        self.config = config
        self.rules = rules
        self._execution_count = 0

    async def on_commit(
        self,
        session: SaveSession,
        result: SaveResult,
    ) -> None:
        if not self.config.enabled:
            return

        for entity in result.succeeded:
            for rule in self.rules:
                # Safety limit
                if self._execution_count >= self.config.max_rules_per_commit:
                    logger.warning("Rule execution limit reached")
                    return

                if await rule.should_trigger(entity, result):
                    self._execution_count += 1

                    if self.config.dry_run:
                        logger.info(f"[DRY RUN] Would execute {rule.name}")
                        continue

                    await rule.execute(session, entity, result)
```

---

## PipelineConversionRule

The primary built-in rule for stage advancement:

```python
from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.automation.config import PipelineConfig
from autom8_asana.models.business.process import Process, ProcessSection

class PipelineConversionRule:
    """Converts Process to next pipeline stage on completion."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.template_discovery = TemplateDiscovery(config)
        self.field_seeder = FieldSeeder(config)

    @property
    def name(self) -> str:
        return "PipelineConversionRule"

    async def should_trigger(
        self,
        entity: AsanaResource,
        result: SaveResult,
    ) -> bool:
        # Only Process entities
        if not isinstance(entity, Process):
            return False

        # Only when section becomes COMPLETE
        if entity.section != ProcessSection.COMPLETE:
            return False

        # Not terminal stage
        if entity.process_type.is_terminal:
            return False

        # Stage must be enabled
        if entity.process_type not in self.config.enabled_stages:
            return False

        return True

    async def execute(
        self,
        session: SaveSession,
        entity: Process,
        result: SaveResult,
    ) -> None:
        # 1. Determine target stage
        target_type = entity.process_type.next()

        # 2. Find template
        template = await self.template_discovery.find_template(
            target_type=target_type,
            source_process=entity,
        )

        # 3. Create new Process
        new_process = await self._create_process(
            session=session,
            template=template,
            target_type=target_type,
            source=entity,
        )

        # 4. Seed fields
        await self.field_seeder.seed(
            source=entity,
            target=new_process,
        )

        # 5. Commit via nested session
        async with session.client.save_session() as nested:
            nested.track(new_process)
            await nested.commit_async()
```

---

## TemplateDiscovery

Finds template tasks in target stage projects using fuzzy matching:

```python
from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.config import PipelineConfig

class TemplateDiscovery:
    """Discovers templates for pipeline conversion."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def find_template(
        self,
        target_type: ProcessType,
        source_process: Process,
    ) -> Task | None:
        """Find matching template for target stage.

        Discovery algorithm:
        1. Find target project (by ProcessType)
        2. Look for templates section (named "Templates")
        3. Fuzzy match source name to template names
        4. Return best match above threshold, or None
        """
        # Find target project
        target_project = await self._find_target_project(target_type)

        # Find templates section
        templates_section = await self._find_templates_section(target_project)

        # Get template tasks
        templates = await self._get_section_tasks(templates_section)

        # Fuzzy match
        best_match = self._fuzzy_match(
            query=source_process.name,
            candidates=templates,
            threshold=self.config.fuzzy_match_threshold,
        )

        return best_match

    def _fuzzy_match(
        self,
        query: str,
        candidates: list[Task],
        threshold: float,
    ) -> Task | None:
        """Find best fuzzy match above threshold."""
        from difflib import SequenceMatcher

        best_score = 0.0
        best_match = None

        for candidate in candidates:
            score = SequenceMatcher(
                None,
                query.lower(),
                candidate.name.lower(),
            ).ratio()

            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate

        return best_match
```

### Template Naming Convention

Templates should be named to match the source Process pattern:

| Source Process Name | Template Name | Match Score |
|---------------------|---------------|-------------|
| "Acme Corp - Sales" | "Sales Template" | 0.45 |
| "Acme Corp - Sales" | "{Company} - Onboarding" | 0.72 |
| "Acme Corp - Sales" | "Standard Onboarding" | 0.35 |

For best results, use consistent naming patterns or explicit GID overrides.

---

## FieldSeeder

Propagates field values from source Process and hierarchy to new Process:

```python
from autom8_asana.automation.seeding import FieldSeeder
from autom8_asana.automation.config import PipelineConfig

class FieldSeeder:
    """Seeds fields on newly created Processes."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def seed(
        self,
        source: Process,
        target: Process,
    ) -> None:
        """Seed target with fields from source and hierarchy.

        Two propagation modes:
        1. Cascade: Direct copy from source (e.g., assigned_to, due_date)
        2. Carry-through: From parent hierarchy (e.g., vertical from Unit)
        """
        # Cascade fields from source
        for field_name in self.config.cascade_fields:
            value = getattr(source, field_name, None)
            if value is not None:
                setattr(target, field_name, value)

        # Carry-through from hierarchy
        for field_name in self.config.carry_through_fields:
            value = self._resolve_from_hierarchy(source, field_name)
            if value is not None:
                setattr(target, field_name, value)

    def _resolve_from_hierarchy(
        self,
        process: Process,
        field_name: str,
    ) -> Any:
        """Walk up hierarchy to find field value."""
        # Try process itself
        if hasattr(process, field_name):
            value = getattr(process, field_name)
            if value is not None:
                return value

        # Try unit
        if process.unit and hasattr(process.unit, field_name):
            value = getattr(process.unit, field_name)
            if value is not None:
                return value

        # Try business
        if process.business and hasattr(process.business, field_name):
            return getattr(process.business, field_name)

        return None
```

### Field Propagation Strategy

| Field Type | Mode | Example |
|------------|------|---------|
| Process-specific | Cascade | assigned_to, due_date |
| Contextual | Carry-through | vertical, platforms |
| Computed | Neither | pipeline_state (computed) |
| Template-defined | Template | default field values |

---

## Creating Custom Rules

Extend automation with custom rules:

```python
from autom8_asana.automation.base import AutomationRule

class NotificationRule:
    """Send notification when high-value process completes."""

    @property
    def name(self) -> str:
        return "NotificationRule"

    async def should_trigger(
        self,
        entity: AsanaResource,
        result: SaveResult,
    ) -> bool:
        if not isinstance(entity, Process):
            return False

        # Only high-value (MRR > threshold)
        if entity.mrr is None or entity.mrr < 10000:
            return False

        # Only on completion
        return entity.section == ProcessSection.COMPLETE

    async def execute(
        self,
        session: SaveSession,
        entity: Process,
        result: SaveResult,
    ) -> None:
        # Send notification (webhook, email, Slack, etc.)
        await self._send_notification(
            message=f"High-value process completed: {entity.name}",
            mrr=entity.mrr,
        )
```

### Register Custom Rules

```python
from autom8_asana.automation import AutomationEngine

engine = AutomationEngine(
    config=config,
    rules=[
        PipelineConversionRule(config.pipeline),
        NotificationRule(),  # Custom rule
        AuditLogRule(),      # Another custom rule
    ],
)
```

---

## Testing Automation

### Unit Testing Rules

```python
import pytest
from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.models.business.process import Process, ProcessType, ProcessSection

@pytest.fixture
def rule():
    config = PipelineConfig(enabled_stages=[ProcessType.SALES])
    return PipelineConversionRule(config)

@pytest.fixture
def completed_sales_process():
    process = Process(gid="123", name="Test Process")
    process.process_type = ProcessType.SALES
    process.section = ProcessSection.COMPLETE
    return process

async def test_should_trigger_on_completed_sales(rule, completed_sales_process):
    result = SaveResult(succeeded=[completed_sales_process], failed=[])
    assert await rule.should_trigger(completed_sales_process, result)

async def test_should_not_trigger_on_in_progress(rule, completed_sales_process):
    completed_sales_process.section = ProcessSection.IN_PROGRESS
    result = SaveResult(succeeded=[completed_sales_process], failed=[])
    assert not await rule.should_trigger(completed_sales_process, result)
```

### Integration Testing

```python
async def test_pipeline_conversion_creates_new_process(client):
    """Full integration test of pipeline conversion."""
    config = AutomationConfig(dry_run=False)
    engine = AutomationEngine(config, [PipelineConversionRule(config.pipeline)])

    async with client.save_session() as session:
        session.register_hook(engine)

        # Setup: sales process in review
        process = await fetch_process(client, "123")
        session.track(process)
        process.section = ProcessSection.COMPLETE

        # Act
        result = await session.commit_async()

        # Assert: new process created in onboarding
        # (Check via API or result inspection)
```

### Dry Run Testing

```python
# Enable dry run for safe testing
config = AutomationConfig(dry_run=True)
engine = AutomationEngine(config, rules)

# Rules evaluate but don't execute
# Check logs for "[DRY RUN]" messages
```

---

## Key Files

| File | Purpose |
|------|---------|
| `automation/base.py` | AutomationRule protocol, AutomationEngine |
| `automation/pipeline.py` | PipelineConversionRule |
| `automation/templates.py` | TemplateDiscovery (fuzzy matching) |
| `automation/seeding.py` | FieldSeeder (cascade + carry-through) |
| `automation/config.py` | AutomationConfig, PipelineConfig |
| `persistence/hooks.py` | PostCommitHook protocol |
