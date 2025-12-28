# TDD: Pipeline Automation Feature Expansion

## Metadata

- **TDD ID**: TDD-2025-001
- **Status**: Approved for Implementation
- **Author**: Architect
- **Created**: 2025-12-27
- **Last Updated**: 2025-12-27
- **PRD Reference**: PRD-2025-001 (Pipeline Automation Feature Expansion)
- **Related ADRs**: ADR-0018 through ADR-0024
- **Related TDDs**: TDD-AUTOMATION-LAYER

---

## Overview

This Technical Design Document specifies the system architecture for Pipeline Automation Feature Expansion, enabling time-based (daily polling) automation triggers with YAML configuration, structured JSON logging, and graceful error recovery. The design extends the existing event-driven AutomationEngine with a scheduled polling layer, adds configuration externalization via YAML with strict JSON Schema validation, and implements comprehensive structured logging for operational visibility and compliance.

**Key Architecture Decisions**:
- Daily polling via system cron (production) + APScheduler (development)
- Pydantic v2 for configuration validation with JSON Schema as source of truth
- structlog + JSON for standardized structured logging
- simpleeval for safe boolean expression evaluation
- Graceful degradation on API failures with no retry logic

---

## Requirements Summary

PRD-2025-001 defines four primary goals:

1. **Enable time-based automation**: Support stale detection, deadline proximity, and age-based triggers without code changes
2. **Externalize configuration**: Move rules from code to YAML with strict validation, enabling Ops ownership of values while Devs own schema
3. **Operational visibility**: Provide structured logs for debugging, auditing, and monitoring automation behavior
4. **Graceful degradation**: Maintain system stability when configuration is invalid or external APIs are unavailable

**Key Functional Requirements**:
- FR-001: Daily polling scheduler at configurable time (must run exactly once/day)
- FR-002: Stale detection on field (last_modified >= N days)
- FR-003: Deadline proximity (due_date <= today + N days)
- FR-004: Age since creation (created_at >= N days, still open)
- FR-005: Field whitelist per rule (which custom fields trigger)
- FR-006: Boolean AND composition (2-3 conditions)
- FR-007: YAML configuration loading at startup with env var substitution
- FR-008: JSON Schema validation (strict mode, invalid config = startup failure)
- FR-009: Structured JSON logging (queryable with jq/grep)
- FR-010: Partial failure handling (one rule fails, others continue)
- FR-011: API unavailability (drop and log, no retry)
- FR-012: Environment variable substitution (${VAR_NAME})

**Non-Functional Requirements**:
- NFR-001: Daily scheduler latency p95 < 2s per rule evaluation
- NFR-002: Config validation latency < 500ms at startup
- NFR-003: Log storage < 1GB per 10,000 rules/day
- NFR-004: 100% of errors logged
- NFR-005: Configuration changes require restart (no hot reload)

---

## System Context

The Pipeline Automation Feature Expansion builds on the existing AutomationEngine (event-driven, triggered on SaveSession commit) by adding:
1. A **polling scheduler layer** that runs daily at a configured time
2. A **configuration loading and validation layer** that reads YAML files at startup
3. A **structured logging layer** that captures all rule executions in JSON format

```
┌─────────────────────────────────────────────────────────────┐
│                    Asana Application                        │
│                                                              │
│  ┌──────────────┐         ┌──────────────────────┐         │
│  │ Event-Driven │         │   Polling Scheduler   │         │
│  │   Engine     │         │     (Daily Cron)      │         │
│  │   (V1)       │         │    (New - Phase 1)    │         │
│  └──────────────┘         └──────────────────────┘         │
│         │                          │                         │
│         └──────────┬───────────────┘                         │
│                    ▼                                          │
│         ┌──────────────────────┐                            │
│         │  Automation Engine   │                            │
│         │  Rule Evaluation &   │                            │
│         │   Execution          │                            │
│         └──────────────────────┘                            │
│                    │                                          │
│         ┌──────────┴──────────┐                             │
│         ▼                     ▼                              │
│   ┌──────────────┐   ┌──────────────┐                      │
│   │   Built-in   │   │    Custom    │                      │
│   │    Rules     │   │    Rules     │                      │
│   │(Pipeline     │   │(User-Defined)│                      │
│   │Conversion)   │   │              │                      │
│   └──────────────┘   └──────────────┘                      │
│                                                              │
│  ┌────────────────────────────────────────┐               │
│  │  Configuration Layer (New)             │               │
│  │  - YAML Loading                        │               │
│  │  - Pydantic Validation                 │               │
│  │  - Environment Variable Substitution   │               │
│  └────────────────────────────────────────┘               │
│                                                              │
│  ┌────────────────────────────────────────┐               │
│  │  Structured Logging Layer (Enhanced)   │               │
│  │  - structlog + JSON                    │               │
│  │  - 30-day retention (external)         │               │
│  │  - Grep/jq queryable                   │               │
│  └────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
   ┌──────────┐             ┌──────────────────┐
   │Asana API │             │Automation Logs   │
   │          │             │(JSON files)      │
   └──────────┘             └──────────────────┘
```

---

## Design

### 1.1 Component Architecture

| Component | Responsibility | Owner | Status |
|-----------|-----------------|-------|--------|
| **PollingScheduler** | Manages daily cron schedule, triggers rule evaluation at configured time | New (arch) | Design |
| **ConfigurationLoader** | Reads YAML files, performs env var substitution, raises ConfigurationError on invalid input | New (arch) | Design |
| **ConfigValidator** | Validates YAML against JSON Schema using Pydantic v2 dataclasses | New (arch) | Design |
| **TriggerEvaluator** | Evaluates time-based conditions (stale, deadline, age) against task data | New (arch) | Design |
| **ExpressionEvaluator** | Evaluates safe boolean expressions (AND logic) using simpleeval | New (arch) | Design |
| **StructuredLogger** | Captures rule execution with structured JSON (rule_id, timestamp, status, tasks_matched, action_taken) | Enhanced (arch) | Design |
| **AutomationEngine** | Orchestrates rule evaluation (existing), now receives input from both event-driven and polling sources | Existing (refactor) | Minor |
| **AutomationResult** | Result model for rule execution (existing), enhanced with trigger source and expression evaluation details | Existing (extend) | Minor |

### 1.2 Detailed Component Specifications

#### PollingScheduler

**Purpose**: Manages daily rule evaluation at a configured time.

**Responsibilities**:
- Initialize scheduler at application startup
- Run polling evaluation exactly once per day at configured time
- Handle timezone-aware scheduling
- Prevent concurrent execution (mutex/lock)
- Log scheduler invocations with timestamp

**Interface**:

```python
class PollingScheduler:
    """Daily polling scheduler for time-based automation rules."""

    def __init__(
        self,
        evaluation_time: str,  # "HH:MM" in configured timezone
        timezone: str,         # "UTC", "America/New_York", etc.
        engine: AutomationEngine,
        client: AsanaClient,
    ) -> None:
        """Initialize scheduler."""

    async def start_async(self) -> None:
        """Start scheduler (called at app startup)."""

    async def stop_async(self) -> None:
        """Stop scheduler (called at app shutdown)."""

    async def evaluate_rules_async(self) -> list[AutomationResult]:
        """
        Manually trigger rule evaluation (for testing, debugging, or manual runs).
        Returns results from all rules.
        """
```

**Implementation Strategy**:
- Production: Use system cron calling an HTTP endpoint or CLI command
- Development: Use APScheduler for in-process scheduling (easier testing)
- Both approaches call the same `evaluate_rules_async()` method
- Mutex/lock prevents concurrent evaluation (e.g., using asyncio.Lock)

**Error Handling**:
- If evaluation fails: Log error, continue (no retry)
- If scheduler fails N times: Alert (logged warning)
- Transient API errors: Logged as "skipped_no_retry"

#### ConfigurationLoader

**Purpose**: Loads and parses YAML configuration files with environment variable substitution.

**Responsibilities**:
- Load YAML from disk (specified path or environment variable)
- Perform ${VAR_NAME} substitution
- Validate structure using Pydantic
- Raise ConfigurationError if invalid or missing env vars
- Return structured config object

**Interface**:

```python
class ConfigurationLoader:
    """Loads YAML rule configuration with validation."""

    @staticmethod
    def load_from_file(
        file_path: str,
        config_schema: type[BaseModel],
    ) -> BaseModel:
        """
        Load config from YAML file.

        Args:
            file_path: Path to YAML file
            config_schema: Pydantic v2 dataclass for validation

        Returns:
            Validated config object

        Raises:
            ConfigurationError: If file missing, invalid YAML, invalid schema,
                                or missing environment variables
        """

    @staticmethod
    def substitute_env_vars(raw_yaml: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively substitute ${VAR_NAME} in config values.

        Raises:
            ConfigurationError: If variable not found in environment
        """
```

**Error Messages**:
- Missing file: "Configuration file not found: /path/to/file.yaml"
- Invalid YAML: "Invalid YAML syntax in config file: line 10: expected '<document start>'"
- Schema error: "Config validation failed: rules[0].trigger.stale.days must be integer >= 1"
- Missing env var: "Environment variable 'API_KEY' not found in config path rules[0].credentials.api_key"

#### ConfigValidator

**Purpose**: Validates YAML configuration structure using Pydantic v2.

**Responsibilities**:
- Define schema as Pydantic dataclasses (lives in code, owned by devs)
- Reject extra fields (strict mode)
- Enforce required fields
- Type-check all values
- Provide clear error messages

**Key Schema Concepts**:

```python
# Schema definition (lives in code, owned by devs)
class TriggerStaleConfig(BaseModel):
    """Stale detection trigger."""
    field: str           # e.g., "Section"
    days: int            # Must be >= 1
    model_config = ConfigDict(extra="forbid")

class TriggerDeadlineConfig(BaseModel):
    """Deadline proximity trigger."""
    days: int            # Due within N days
    model_config = ConfigDict(extra="forbid")

class TriggerAgeConfig(BaseModel):
    """Age since creation trigger."""
    days: int            # Created >= N days ago, still open
    model_config = ConfigDict(extra="forbid")

class RuleCondition(BaseModel):
    """A single condition (AND composition)."""
    stale: TriggerStaleConfig | None = None
    deadline: TriggerDeadlineConfig | None = None
    age: TriggerAgeConfig | None = None
    field_whitelist: list[str] | None = None

    @field_validator('stale', 'deadline', 'age')
    def at_least_one_trigger(cls, v, info):
        if all(info.data.get(f) is None for f in ['stale', 'deadline', 'age']):
            raise ValueError("At least one trigger type required")
        return v

class Rule(BaseModel):
    """A single automation rule."""
    rule_id: str         # Unique identifier
    name: str            # Human-readable name
    conditions: list[RuleCondition]  # AND composition of conditions
    action: ActionConfig # What to do when triggered
    enabled: bool = True
    model_config = ConfigDict(extra="forbid")

class AutomationRulesConfig(BaseModel):
    """Top-level configuration."""
    scheduler:
        time: str        # "HH:MM"
        timezone: str    # "UTC"
    rules: list[Rule]
    model_config = ConfigDict(extra="forbid")
```

**Values** (live in YAML, owned by ops):
```yaml
scheduler:
  time: "02:00"
  timezone: "UTC"

rules:
  - rule_id: "escalate-triage"
    name: "Escalate stale triage tasks"
    conditions:
      - stale:
          field: "Section"
          days: 3
        field_whitelist: ["custom_gid_123"]
    action:
      type: "add_tag"
      params:
        tag: "escalate"
    enabled: true
```

#### TriggerEvaluator

**Purpose**: Evaluates time-based trigger conditions against task data.

**Responsibilities**:
- Determine which tasks match stale condition (field >= N days)
- Determine which tasks match deadline condition (due_date <= today + N)
- Determine which tasks match age condition (created >= N days, still open)
- Combine multiple conditions with AND logic
- Return matching task IDs

**Interface**:

```python
class TriggerEvaluator:
    """Evaluates time-based trigger conditions."""

    async def evaluate_async(
        self,
        rule: Rule,
        project_gid: str,
        client: AsanaClient,
    ) -> list[str]:  # Matching task GIDs
        """
        Evaluate all conditions for a rule.
        Returns task GIDs that match ALL conditions (AND logic).
        """

    async def evaluate_stale_async(
        self,
        field: str,
        days_threshold: int,
        project_gid: str,
        client: AsanaClient,
    ) -> list[str]:
        """
        Find tasks in field for >= days_threshold.

        Algorithm:
        1. Get all tasks in field
        2. For each task: compare task.modified_at to (today - days_threshold)
        3. Return tasks where task.modified_at <= threshold_date
        """

    async def evaluate_deadline_async(
        self,
        days_threshold: int,
        project_gid: str,
        client: AsanaClient,
    ) -> list[str]:
        """
        Find tasks with due_date <= today + days_threshold.
        """

    async def evaluate_age_async(
        self,
        days_threshold: int,
        project_gid: str,
        client: AsanaClient,
    ) -> list[str]:
        """
        Find tasks created >= days_threshold ago, still open (not completed).
        """
```

**Performance Considerations**:
- Use Asana API collection/streaming for large task lists
- Cache project/section metadata at startup
- Implement timeout for slow API responses (default 30s)
- Log performance warnings if evaluation exceeds NFR-001 target (p95 < 2s)

#### ExpressionEvaluator

**Purpose**: Safely evaluates boolean expressions in rule conditions (AND logic).

**Responsibilities**:
- Parse and evaluate boolean expressions without code execution
- Support field comparisons, date math, numeric thresholds
- Provide clear error messages for malformed expressions
- Return True/False for condition matching

**Interface**:

```python
class ExpressionEvaluator:
    """Evaluates safe boolean expressions."""

    @staticmethod
    def evaluate(
        expression: str,
        context: dict[str, Any],
    ) -> bool:
        """
        Evaluate expression with provided context.

        Example expressions:
        - "tasks_stale > 0 and tasks_deadline > 0"
        - "field_value == 'Pending' and age_days >= 5"

        Args:
            expression: Boolean expression string
            context: Variables available in expression

        Returns:
            True if expression evaluates to True

        Raises:
            ExpressionEvaluationError: If expression is malformed
        """
```

**Library Choice**: simpleeval (ADR-0018)
- Safe evaluation (no code execution risk)
- Supports arithmetic, comparison, boolean operators
- Clear error messages
- Lightweight dependency

#### StructuredLogger

**Purpose**: Captures all automation rule executions in structured JSON format.

**Responsibilities**:
- Log every rule evaluation (success, failure, skip)
- Include context: rule_id, timestamp, task count, action taken, result
- Output JSON only (no text logs for automation)
- Redact sensitive data (env var values)
- Enable grep/jq queries

**Interface**:

```python
class StructuredLogger:
    """JSON-based structured logging for automation."""

    @staticmethod
    def log_rule_evaluation(
        rule_id: str,
        rule_name: str,
        status: str,  # "success", "error", "skipped_no_retry"
        conditions_evaluated: dict[str, int],
        tasks_matched: list[str],
        action_type: str,
        action_result: str,
        duration_ms: float,
        error_msg: str | None = None,
    ) -> None:
        """
        Log a single rule evaluation.

        Output format:
        {
            "timestamp": "2025-12-27T02:00:01.234Z",
            "rule_id": "escalate-triage",
            "rule_name": "Escalate stale triage tasks",
            "status": "success",
            "conditions": {
                "stale": 5,
                "deadline": 3,
                "age": 2
            },
            "tasks_matched": ["gid1", "gid2"],
            "action_type": "add_tag",
            "action_result": "2 tasks tagged",
            "duration_ms": 1234,
            "error": null
        }
        """

    @staticmethod
    def log_scheduler_invocation(
        invocation_count: int,
        total_rules: int,
        duration_ms: float,
        succeeded: int,
        failed: int,
    ) -> None:
        """
        Log daily scheduler invocation summary.
        """

    @staticmethod
    def log_config_load(
        file_path: str,
        rule_count: int,
        duration_ms: float,
        status: str,  # "success", "error"
        error_msg: str | None = None,
    ) -> None:
        """
        Log configuration load attempt.
        """
```

**Log Format** (JSON Lines, one record per line):
```json
{
  "timestamp": "2025-12-27T02:00:01.234Z",
  "level": "info",
  "event": "rule_evaluation",
  "rule_id": "escalate-triage",
  "rule_name": "Escalate stale triage tasks",
  "status": "success",
  "conditions": {
    "stale_days_3": 5,
    "field_whitelist": ["custom_gid_123"]
  },
  "tasks_matched": 5,
  "task_ids": ["gid1", "gid2", "gid3", "gid4", "gid5"],
  "action_type": "add_tag",
  "action_params": {"tag": "escalate"},
  "action_result": {"success": true, "count": 5},
  "duration_ms": 1234,
  "error": null
}
```

**Redaction Rules**:
- Never log ${VAR_NAME} substituted values
- Never log full API credentials
- Redact custom field GIDs that contain sensitive data
- Log endpoint names (not full URLs with credentials)

### 1.3 Data Model

#### Configuration Schema

```python
# Core trigger types
@dataclass(frozen=True)
class StaleCondition:
    """Monitor field for N+ days."""
    field: str  # Field name/GID
    days: int   # Must be >= 1

@dataclass(frozen=True)
class DeadlineCondition:
    """Task due within N days."""
    days: int   # Must be >= 1

@dataclass(frozen=True)
class AgeCondition:
    """Task created N+ days ago, still open."""
    days: int   # Must be >= 1

@dataclass(frozen=True)
class RuleCondition:
    """Single condition in a rule."""
    stale: StaleCondition | None = None
    deadline: DeadlineCondition | None = None
    age: AgeCondition | None = None
    field_whitelist: list[str] | None = None  # Custom field GIDs to monitor

    # Validation: at least one trigger required
    def __post_init__(self):
        if all(x is None for x in [self.stale, self.deadline, self.age]):
            raise ValueError("At least one trigger type required")

@dataclass(frozen=True)
class ActionConfig:
    """Action to execute when rule matches."""
    type: str  # "add_tag", "add_comment", "change_section", etc.
    params: dict[str, Any]

@dataclass(frozen=True)
class Rule:
    """Single automation rule."""
    rule_id: str
    name: str
    project_gid: str  # Which project to evaluate
    conditions: list[RuleCondition]  # AND composition
    action: ActionConfig
    enabled: bool = True

@dataclass(frozen=True)
class SchedulerConfig:
    """Polling scheduler configuration."""
    time: str  # "HH:MM"
    timezone: str  # "UTC"

@dataclass(frozen=True)
class AutomationRulesConfig:
    """Top-level configuration."""
    scheduler: SchedulerConfig
    rules: list[Rule]
```

#### Trigger Evaluation State

```python
@dataclass
class TriggerEvaluationResult:
    """Result of evaluating a single trigger condition."""
    condition_type: str  # "stale", "deadline", "age"
    matches: int  # Number of tasks matching this condition
    task_ids: list[str]
    evaluated_at: datetime
    duration_ms: float

@dataclass
class RuleEvaluationResult:
    """Result of evaluating all conditions in a rule."""
    rule_id: str
    conditions_results: list[TriggerEvaluationResult]
    matching_tasks: list[str]  # Tasks matching ALL conditions (AND)
    status: str  # "success", "error", "skipped"
    duration_ms: float
    error: str | None = None
```

#### Extended AutomationResult

The existing AutomationResult model is extended with:

```python
@dataclass
class AutomationResult:
    # ... existing fields ...

    # New fields for polling-based triggers
    trigger_source: str = "event"  # "event" or "polling"
    trigger_type: str | None = None  # "stale", "deadline", "age"
    conditions_evaluated: dict[str, int] = field(default_factory=dict)
    tasks_evaluated: int = 0
    expression_evaluation: dict[str, Any] = field(default_factory=dict)
```

### 1.4 Data Flow

#### Daily Polling Execution Flow

```
┌──────────────────────────────────────────────────────────┐
│  Scheduler triggers at configured time (daily)           │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  PollingScheduler.evaluate_rules_async()                 │
│  - Acquire lock (prevent concurrent execution)           │
│  - Log scheduler invocation start                        │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  For each enabled rule in config:                        │
│  1. Load rule definition from config                     │
│  2. TriggerEvaluator.evaluate_async(rule)                │
│     - For each condition in rule:                        │
│       - Fetch tasks from project/section                 │
│       - Evaluate condition (stale/deadline/age)          │
│       - Collect matching task IDs                        │
│     - AND condition results (only tasks matching ALL)    │
│  3. If matching_tasks > 0:                               │
│     - AutomationEngine.execute_rule_async(rule, tasks)   │
│     - Action applied to each matching task               │
│  4. StructuredLogger.log_rule_evaluation(...)            │
│     - Log rule_id, status, tasks_matched, duration       │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Collect results from all rules                          │
│  - Count successes, failures, skipped                    │
│  - StructuredLogger.log_scheduler_invocation(summary)    │
│  - Release lock                                          │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Return list of AutomationResult objects                 │
│  (for CLI/API inspection if needed)                      │
└──────────────────────────────────────────────────────────┘
```

#### Configuration Load Flow

```
┌──────────────────────────────────────────────────────────┐
│  Application startup (before AutomationEngine init)      │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  ConfigurationLoader.load_from_file(yaml_path)           │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Parse YAML file                                         │
│  Raises ConfigurationError if invalid YAML syntax        │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  ConfigurationLoader.substitute_env_vars(raw_dict)       │
│  - Recursively find ${VAR_NAME} patterns                 │
│  - Substitute with os.environ[VAR_NAME]                  │
│  - Raises ConfigurationError if VAR_NAME not found       │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  ConfigValidator.validate(substituted_dict)              │
│  - Initialize Pydantic v2 dataclasses with dict          │
│  - Pydantic validates type, required fields, enums       │
│  - Raises ValidationError if invalid                     │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  StructuredLogger.log_config_load(                        │
│      file_path, rule_count, duration_ms, "success"       │
│  )                                                        │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Return AutomationRulesConfig object                      │
│  (available to PollingScheduler and AutomationEngine)    │
└──────────────────────────────────────────────────────────┘
```

#### Trigger Evaluation Sequence (Single Rule)

```
Rule: { stale: { field: "Section", days: 3 }, deadline: { days: 7 } }

1. Evaluate Stale Condition:
   GET /projects/{gid}/tasks?section={section_gid}&opt_fields=modified_at
   For each task: if (today - modified_at) >= 3 days → add to stale_matches
   Result: [task_gid_1, task_gid_2, task_gid_3] (3 matches)

2. Evaluate Deadline Condition:
   GET /projects/{gid}/tasks?opt_fields=due_on
   For each task: if due_on and due_on <= (today + 7 days) → add to deadline_matches
   Result: [task_gid_2, task_gid_4, task_gid_5] (3 matches)

3. AND Composition:
   intersection(stale_matches, deadline_matches) = [task_gid_2]

4. Execute Action on matched tasks:
   For each task_gid in [task_gid_2]:
     POST /tasks/{task_gid}/... (apply action)

5. Log Result:
   {
     "rule_id": "rule_001",
     "status": "success",
     "conditions": {
       "stale_3_days": 3,
       "deadline_7_days": 3,
       "and_composition": 1
     },
     "tasks_matched": 1,
     "action_result": "success"
   }
```

### 1.5 API Contracts

#### Configuration YAML Format

**File Location**: Environment variable `AUTOM8_RULES_CONFIG` or default `/etc/autom8_asana/rules.yaml`

```yaml
# Configuration file for Pipeline Automation rules

scheduler:
  # Time to run daily evaluation (24-hour format)
  time: "02:00"

  # Timezone for scheduling (IANA timezone name)
  timezone: "America/New_York"

rules:
  # Escalate stale triage items
  - rule_id: "escalate-triage"
    name: "Escalate stale triage tasks"

    # Project to evaluate
    project_gid: "1234567890123"

    # Conditions (AND composition)
    conditions:
      - stale:
          field: "Section"        # Field to monitor
          days: 3                 # N+ days threshold
        field_whitelist:          # Optional: only trigger on these fields
          - "custom_gid_abc123"

      - deadline:
          days: 7                 # Due within N days
        field_whitelist: []       # Empty = any field

    # Action to execute
    action:
      type: "add_tag"
      params:
        tag: "escalate"

    enabled: true

  # Age-based archival
  - rule_id: "archive-old"
    name: "Archive very old completed tasks"
    project_gid: "9876543210987"

    conditions:
      - age:
          days: 90              # Created 90+ days ago

    action:
      type: "change_section"
      params:
        section: "Archive"

    enabled: true
```

#### CLI Interface

```bash
# Manual trigger of daily evaluation
autom8-asana run-polling-rules

# Check scheduler status
autom8-asana polling-status

# Validate configuration (optional)
autom8-asana validate-rules-config /path/to/rules.yaml

# View recent rule executions
autom8-asana logs-rules --since 24h --rule-id escalate-triage
```

#### Logging Query Examples

```bash
# All rule executions in last 24 hours
grep "2025-12-27" automation.json | jq '.[] | select(.event == "rule_evaluation")'

# Count successful executions per rule
jq -s 'group_by(.rule_id) | map({rule_id: .[0].rule_id, success_count: map(select(.status == "success")) | length})' automation.json

# Find failed rules
jq '.[] | select(.status == "error")' automation.json

# Tasks matched by specific rule
jq '.[] | select(.rule_id == "escalate-triage") | .task_ids' automation.json

# Performance analysis (tasks/second)
jq -s 'map(select(.event == "rule_evaluation")) | map(.duration_ms) | {p50: .[length/2], p95: .[length*0.95 | floor], p99: .[length*0.99 | floor]}' automation.json
```

#### Monitoring/Alerting Integration

```json
{
  "metrics": [
    {
      "name": "automation_rules_executed",
      "type": "counter",
      "labels": ["rule_id", "status"],
      "source": "automation.json"
    },
    {
      "name": "automation_rule_duration_ms",
      "type": "histogram",
      "labels": ["rule_id"],
      "source": "automation.json"
    },
    {
      "name": "automation_scheduler_failures",
      "type": "counter",
      "threshold": "> 3 in 24h",
      "alert": "true"
    }
  ]
}
```

### 1.6 Error Recovery & Failure Modes

#### Invalid Configuration (Startup Failure)

**Scenario**: YAML file has invalid schema or missing required field.

**Flow**:
1. ConfigurationLoader.load_from_file() is called at app startup
2. ConfigValidator raises ValidationError with details
3. Application logs error and exits with code 1
4. StructuredLogger.log_config_load(status="error", error_msg=...)
5. Operator must fix YAML and restart application

**Error Message Example**:
```
Configuration load failed:
  Error at rules[0].conditions[0]:
  At least one trigger type (stale, deadline, age) required.

  Fix: Add at least one condition to rules[0].conditions[0]
```

#### Missing Environment Variable

**Scenario**: Configuration references ${API_KEY} but env var not set.

**Flow**:
1. ConfigurationLoader.substitute_env_vars() is called
2. Finds ${API_KEY} pattern
3. Raises ConfigurationError: "Environment variable API_KEY not found"
4. Application fails to start
5. Operator must set environment variable and restart

**Error Message Example**:
```
Environment variable substitution failed:
  Variable 'ASANA_API_TOKEN' referenced in rules[0].action.params.token
  but not found in environment.

  Fix: export ASANA_API_TOKEN=<value> and restart application
```

#### Partial Rule Failure During Evaluation

**Scenario**: Rule A succeeds, Rule B fails (API error), Rule C succeeds.

**Flow**:
1. PollingScheduler.evaluate_rules_async() iterates rules
2. For Rule B: TriggerEvaluator.evaluate_async() raises exception (e.g., HTTP 500)
3. Exception is caught, logged as "error"
4. StructuredLogger.log_rule_evaluation() with status="error", error_msg=...
5. PollingScheduler continues to Rule C
6. Final summary logs: "2 succeeded, 1 failed, 0 skipped"
7. PollingScheduler returns all results (including failed)

**Error Handling Code**:
```python
async def evaluate_rules_async(self):
    results = []
    for rule in self.config.rules:
        try:
            result = await self.engine.execute_rule_async(rule)
            results.append(result)
        except Exception as e:
            # Log error but continue
            logger.error(f"Rule {rule.rule_id} failed: {e}")
            results.append(AutomationResult(
                rule_id=rule.rule_id,
                success=False,
                error=str(e),
            ))
    return results
```

#### API Unavailability (No Retry)

**Scenario**: Asana API returns 503 Service Unavailable.

**Flow**:
1. TriggerEvaluator attempts API call (GET /tasks)
2. HTTP 503 response received
3. Exception is caught (no retry logic)
4. Rule is skipped, logged as "skipped_no_retry"
5. Status: "skipped", error_msg: "API unavailable: GET /tasks returned 503"
6. Next daily poll will attempt again

**Log Entry**:
```json
{
  "timestamp": "2025-12-27T02:00:01.234Z",
  "rule_id": "escalate-triage",
  "status": "skipped_no_retry",
  "error": "Asana API /tasks returned 503 Service Unavailable",
  "error_endpoint": "/projects/gid/tasks",
  "error_code": 503
}
```

#### Timeout During Evaluation

**Scenario**: Evaluation takes > 30 seconds (timeout threshold).

**Flow**:
1. TriggerEvaluator sets timeout context (asyncio.timeout or similar)
2. If timeout expires: raise TimeoutError
3. Caught by PollingScheduler
4. Logged as "error" with status="timeout"
5. Rule is marked incomplete, partial results may be logged

**Mitigation**:
- Monitor evaluation time with NFR-001 (p95 < 2s per rule)
- Alert if any rule evaluation exceeds 30s
- Consider chunking large task lists into smaller batches

#### Field Not Found in Task

**Scenario**: Stale condition monitors "Section" field, but task doesn't have that field.

**Flow**:
1. TriggerEvaluator queries tasks for field
2. If field missing on task: skip that task (graceful)
3. Log: "Task {gid} has no Section field, skipping"
4. Continue evaluation with other tasks
5. Rule may have 0 matches, action not executed

**Error Handling**:
- Don't fail rule on missing field values
- Log warnings for visibility
- Only fail if field definition itself is invalid (non-existent GID)

### 1.7 Database Schema (if any)

**No database schema required for Phase 1**.

- Scheduler state: In-memory (APScheduler in dev) or kernel-managed (cron in prod)
- Configuration state: Read from YAML at startup, cached in memory
- Trigger execution history: Logged to JSON files only (30-day retention via logrotate or similar)
- No new database tables needed

**Future Considerations**:
- Phase 2 could add persistent scheduler state table (for better observability)
- Phase 2 could add rule execution history table (for long-term analytics)
- For now, JSON logs are the system of record

### 1.8 API Design

#### CLI Commands

```
Command: autom8-asana polling-rules evaluate
  Description: Manually trigger rule evaluation (for testing/debugging)
  Output: JSON list of AutomationResult objects
  Exit code: 0 if any rule succeeded, 1 if all failed

Command: autom8-asana polling-rules status
  Description: Check scheduler status
  Output:
    {
      "enabled": true,
      "next_run": "2025-12-28T02:00:00Z",
      "last_run": "2025-12-27T02:00:00Z",
      "last_run_status": "success",
      "last_run_results": {
        "total": 10,
        "succeeded": 8,
        "failed": 1,
        "skipped": 1
      }
    }

Command: autom8-asana polling-rules validate
  Description: Validate configuration without executing
  Arguments: [--config-file PATH]
  Output: "Configuration valid: 15 rules loaded" or error message
  Exit code: 0 if valid, 1 if invalid
```

#### Programmatic API

```python
# Initialize polling scheduler
from autom8_asana.polling import PollingScheduler
from autom8_asana.automation.config import ConfigurationLoader

config = ConfigurationLoader.load_from_file(
    "/etc/autom8_asana/rules.yaml",
    AutomationRulesConfig,
)

scheduler = PollingScheduler(
    evaluation_time=config.scheduler.time,
    timezone=config.scheduler.timezone,
    engine=automation_engine,
    client=asana_client,
)

await scheduler.start_async()  # Starts daily polling

# Manually trigger evaluation (for testing)
results = await scheduler.evaluate_rules_async()
for result in results:
    print(f"{result.rule_id}: {result.success}")

await scheduler.stop_async()  # Stops polling
```

### 1.9 Testing Strategy

#### Unit Tests

**ConfigurationLoader**:
- Load valid YAML
- Reject invalid YAML syntax
- Substitute environment variables
- Raise error on missing env var
- Reject invalid schema (missing required fields, wrong types)
- Test strict mode (reject extra fields)

**TriggerEvaluator**:
- Evaluate stale condition (field modified >= N days)
- Evaluate deadline condition (due_date <= today + N)
- Evaluate age condition (created >= N days, open)
- Combine conditions with AND logic
- Handle empty task list (0 matches)
- Handle tasks with missing fields (graceful skip)

**ExpressionEvaluator**:
- Parse and evaluate boolean expressions
- Reject malformed expressions with clear errors
- Support field comparisons (>, <, ==, !=)
- Support logical operators (and, or)
- Prevent code execution (no eval() or exec())

**StructuredLogger**:
- Verify JSON output format
- Verify redaction of secrets (env var values)
- Verify timestamp format (ISO 8601)
- Verify all fields present in log record

#### Integration Tests

**ConfigurationLoader + Validation**:
- Load valid rules from YAML file
- Execute rules with real Asana API mock
- Verify configuration is accessible to engine

**PollingScheduler + TriggerEvaluator + AutomationEngine**:
- Full end-to-end trigger evaluation
- Create test project with tasks in various states
- Define stale, deadline, age conditions
- Run evaluation, verify matching tasks identified
- Execute action on matching tasks
- Verify action applied correctly (task tagged, section changed, etc.)

**Partial Failure Handling**:
- Configure rule that will fail (invalid project GID)
- Configure rule that will succeed
- Run evaluation
- Verify failed rule is logged
- Verify successful rule completes
- Verify summary shows 1 success, 1 failure

**API Unavailability**:
- Mock Asana API to return 503
- Run evaluation
- Verify rule is skipped (not retried)
- Verify logged as "skipped_no_retry"
- Verify next poll will attempt again

#### Stress Tests

**Large Task List** (NFR-001 validation):
- Create project with 10,000+ tasks
- Define stale rule
- Measure evaluation time
- Verify p95 < 2s per rule
- Monitor memory usage (ensure no unbounded growth)

**Many Rules** (scalability):
- Configure 100+ rules
- Run daily evaluation
- Verify all rules complete within reasonable time
- Verify no memory leaks

**Log Storage** (NFR-003 validation):
- Run daily evaluation for 30 days
- Measure log file size
- Verify < 1GB for 10,000 rules/day

#### Test Data

**Fixture: Project with Tasks**:
- 20 tasks in "Triage" section, various modified dates
- 10 tasks with due dates in next 7 days
- 5 tasks created 90+ days ago (still open)
- 3 tasks without due dates
- 2 completed tasks

**Fixture: Configuration Files**:
- Valid rules.yaml with 5 rules
- Invalid rules.yaml (missing required field)
- rules.yaml with env var substitution (${API_KEY})
- rules.yaml with extra fields (should reject)

### 1.10 Migration Path

#### Phase 1: New Polling System (Parallel)

**Goal**: Add polling system without changing existing event-driven rules.

**Steps**:
1. Implement PollingScheduler (new component)
2. Implement ConfigurationLoader, ConfigValidator (new components)
3. Implement TriggerEvaluator (new component)
4. Deploy with polling **disabled** initially
5. Verify configuration loads correctly
6. Enable polling in staging
7. Run parallel with existing event-driven rules
8. Monitor for 2+ weeks before GA

**Deployment**:
```yaml
automation:
  enabled: true
  polling:
    enabled: false  # Initially disabled
  event_driven:
    enabled: true   # Existing rules continue
```

#### Phase 2: Migrate Hardcoded Rules to YAML

**Goal**: Move existing hardcoded PipelineConversionRule to YAML configuration.

**Timeline**:
1. Week 1: Document current hardcoded rules
2. Week 2: Create YAML equivalents for testing
3. Week 3-4: Run parallel (hardcoded + YAML)
4. Week 5: Deprecate hardcoded rules (log warnings)
5. Week 6+: Remove hardcoded rules

**Example Migration**:
```python
# Current: Hardcoded in code
rule = PipelineConversionRule(
    source_type=ProcessType.SALES,
    target_type=ProcessType.ONBOARDING,
    trigger_section=ProcessSection.CONVERTED,
)
engine.register(rule)

# Future: Loaded from YAML
# (Ops edits rules.yaml, no code change needed)
```

**Deprecation Warning**:
```
WARNING: PipelineConversionRule is deprecated.
Please migrate to YAML-based configuration in rules.yaml.
See: https://docs.example.com/migration-guide
Hardcoded rules will be removed in Q2 2026.
```

#### Rollback Strategy

**If polling causes issues**:
1. Set `polling.enabled: false` in configuration
2. Restart application
3. Event-driven rules continue normally
4. Polling rules do not execute
5. Investigate issue, fix, re-enable

**Configuration Syntax Error**:
1. Application fails to start with clear error message
2. Operator fixes YAML
3. Restart application
4. No data loss (config is read-only)

**Data Loss Protection**:
- All rule executions logged to JSON (immutable)
- No persistent state in database (clean slate on restart)
- Task changes are recorded in Asana (not in autom8 system)

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Expression Evaluator | simpleeval | Safe evaluation without code execution risk, lightweight | ADR-0018 |
| Scheduler Integration | System cron (prod) + APScheduler (dev) | Reliability, observability, ease of testing | ADR-0019 |
| Configuration Validation | Pydantic v2 | Already in dependencies, strong validation, clear errors | ADR-0020 |
| Logging Format | structlog + JSON | Standardized, queryable with jq/grep, aggregation-ready | ADR-0021 |
| Configuration File Location | Environment variable or `/etc/autom8_asana/rules.yaml` | Ops-friendly, standard Unix location | ADR-0022 |
| Schema vs Values Separation | Devs own schema (code), Ops own values (YAML) | Reduces human error, clear ownership | ADR-0023 |
| Trigger Composition | AND only (Phase 1), plan OR for Phase 2 | MVP scope, extensible parser design | ADR-0024 |

---

## Complexity Assessment

**Complexity Level**: **Service** (new, modular system with clear boundaries)

**Why This Level**:
- New scheduler component (moderate complexity)
- Configuration loading and validation (low-to-moderate complexity)
- Trigger evaluation logic (moderate complexity)
- Integration with existing AutomationEngine (low, well-defined interface)
- Structured logging (straightforward)

**Risk Factors**:
- Timezone handling (medium risk, mitigated by library choice)
- Large task list performance (medium risk, mitigated by performance targets and testing)
- Configuration schema evolution (low risk, Pydantic handles versioning)

**Team Capacity**: 2-3 engineers, 2-3 weeks (including testing and documentation)

---

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 1 | ConfigurationLoader + ConfigValidator + TDD/ADRs | ADR decisions | 3-5 days |
| 2 | TriggerEvaluator (stale, deadline, age conditions) | Phase 1 + Asana API mocks | 5-7 days |
| 3 | PollingScheduler + APScheduler integration | Phase 2 | 3-4 days |
| 4 | StructuredLogger + JSON logging integration | Phases 1-3 | 2-3 days |
| 5 | CLI commands (evaluate, status, validate) | Phases 1-4 | 2-3 days |
| 6 | Testing: Unit + Integration + Stress | All above | 5-7 days |
| 7 | Documentation + Migration Guide + Runbook | All above | 3-4 days |

**Total Estimate**: 4-5 weeks

### Milestones

- **Week 1**: Phases 1-2 complete (config + trigger evaluation working)
- **Week 2**: Phases 3-4 complete (scheduler + logging deployed to staging)
- **Week 3**: Phases 5-6 complete (CLI + testing, ready for pilot)
- **Week 4+**: Pilot in staging, monitor for 2+ weeks, GA

### Key Dependencies

- PRD approval (complete)
- ADR decisions (in progress, this TDD)
- Team capacity (engineering)
- Asana API availability (assumed)
- Testing environment (existing)

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Timezone handling bugs | Medium | Medium | Use APScheduler/pytz libraries, test DST transitions, monitor scheduler logs |
| Large task list timeout | Medium | Medium | Implement streaming/pagination, set reasonable timeout (30s), test with 10k+ tasks early |
| Configuration schema evolution | Low | Low | Use Pydantic, plan backward compatibility, deprecation warnings |
| Concurrent rule execution | Medium | Low | Implement mutex/lock, test concurrent access, log lock wait times |
| API rate limiting | Medium | Medium | Implement exponential backoff (Phase 2), batch requests where possible |
| Log storage growth | Low | Low | Implement log rotation (external), monitor disk usage, set up alerts |
| YAML syntax errors in ops environment | Low | Medium | Provide validation tool, clear error messages, runbook with examples |

---

## Observability

### Metrics

- `automation_polling_runs_total` (counter, by status: success/error)
- `automation_polling_duration_seconds` (histogram, p50/p95/p99)
- `automation_rules_executed_total` (counter, by rule_id and status)
- `automation_rule_duration_seconds` (histogram, by rule_id)
- `automation_tasks_matched_total` (counter, by rule_id)
- `automation_config_validation_duration_seconds` (histogram)

### Logging

- Configuration load: timestamp, file_path, rule_count, status, duration
- Scheduler invocation: timestamp, total_rules, succeeded, failed, skipped, duration
- Rule evaluation: timestamp, rule_id, status, conditions, tasks_matched, action_result, duration

### Alerting

- Rule evaluation fails > 3 times in 24 hours → Alert
- Scheduler invocation fails > 2 times in 7 days → Alert
- Configuration validation fails at startup → Alert
- Rule evaluation exceeds 30s timeout → Alert
- Log disk usage > 80% → Alert

---

## Testing Strategy

### Test Coverage Targets

| Component | Unit Coverage | Integration Coverage |
|-----------|----------------|----------------------|
| ConfigurationLoader | 95% | 100% |
| ConfigValidator | 95% | 100% |
| TriggerEvaluator | 90% | 100% |
| ExpressionEvaluator | 95% | 100% |
| StructuredLogger | 90% | 100% |
| PollingScheduler | 85% | 100% |

### Test Environment

- Docker-based Asana API mock
- Test YAML configuration files (valid, invalid, edge cases)
- Test project with known task states
- Log file assertions (JSON parsing, field validation)

### Continuous Testing

- Unit tests run on every commit
- Integration tests run on PR
- Stress tests run nightly (large task lists, long runs)
- Load tests in staging before GA

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Invalid field GID handling: fail at startup or skip at runtime? | Architect + Ops | Design phase | ADR-0022 specifies permissive (runtime skip) |
| Should cron jobs log to same JSON file as app? | Architect + SRE | Implementation | Yes, unified logging via wrapper script |
| Max rule count for Phase 1? | Requirements + Engineering | Implementation | No hard limit, but test with 100+ rules |
| Can rules reference same task multiple times? | Requirements | Implementation | Yes, each rule executes independently |
| Parallel rule execution or sequential? | Architect | Implementation | Sequential (simpler), parallel Phase 2 if needed |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-27 | Architect | Initial TDD from PRD-2025-001, all 10 sections, ready for implementation |

---

## Sign-Off

- **Architect**: Approved for implementation
- **Requirements Analyst**: Aligns with PRD-2025-001
- **QA**: Ready for test planning
- **Engineering Lead**: Ready for sprint planning
