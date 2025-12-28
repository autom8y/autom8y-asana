# Architecture Decision Records: Pipeline Automation Feature Expansion

This document collects all Architecture Decision Records (ADRs) for the Pipeline Automation Feature Expansion initiative. Each ADR documents a significant technical decision, the alternatives considered, and the rationale for the choice made.

---

## ADR-0018: Expression Evaluator Library Choice

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, Technology Scout, Principal Engineer
- **Related**: PRD-2025-001, TDD-2025-001

### Context

The Pipeline Automation Feature Expansion requires evaluating boolean expressions for trigger conditions. Rules may need to compose multiple conditions (stale AND deadline AND age) using safe, provably-safe evaluation mechanisms.

**Problem**: How do we safely evaluate boolean expressions without allowing arbitrary code execution?

**Constraints**:
- Expression evaluation must be safe (no code execution risk)
- Must support basic boolean logic (AND, OR for Phase 2)
- Must provide clear error messages for malformed expressions
- Should be lightweight (minimal dependencies)
- Must be maintainable by ops teams reading/debugging logs

### Decision

We will use **simpleeval** library for expression evaluation.

**simpleeval** is a small Python library that safely evaluates mathematical and boolean expressions without allowing code execution. It supports:
- Arithmetic operations: `+, -, *, /, %`
- Comparisons: `>, <, ==, !=, >=, <=`
- Boolean logic: `and, or, not`
- Variable substitution from a context dictionary
- Explicit allowlisting of safe functions (e.g., `len`, `str`)

### Rationale

**Why simpleeval over alternatives**:

1. **Safety**: simpleeval uses a whitelist approach. It doesn't call `eval()` or `exec()`. It parses expressions into AST and only executes safe operations. This eliminates the risk of code injection or privilege escalation that would come from using Python's `eval()`.

2. **Simplicity**: simpleeval is ~500 lines of code. It's easy to audit, understand, and maintain. No complex configuration needed.

3. **Clear error messages**: When an expression is malformed, simpleeval provides helpful error messages like "Unknown identifier 'invalid_var'" or "Unknown operator '**'".

4. **Minimal dependencies**: simpleeval has zero runtime dependencies (only std lib). This reduces deployment complexity and security surface.

5. **Phase 2 readiness**: simpleeval already supports OR/NOT logic, so we're not painting ourselves into a corner when we add Phase 2 features.

6. **Already familiar pattern**: If team has used simpleeval elsewhere, it's a known-safe library.

### Alternatives Considered

#### Alternative 1: pyparsing

**Description**: pyparsing is a powerful parsing library that can parse and evaluate complex expressions. Would give us full control over grammar.

**Pros**:
- Extremely flexible for complex expressions
- Can handle nested parentheses, custom operators
- Good error messages
- Well-maintained and stable

**Cons**:
- Overkill for our use case (we only need boolean AND/OR)
- Larger dependency footprint
- Requires more complex setup (grammar definition, evaluation logic)
- Higher learning curve for future maintainers
- More code = more surface area for bugs

**Why not chosen**: We want simple AND/OR composition, not arbitrary expression grammar. pyparsing is overengineered for Phase 1 scope.

#### Alternative 2: Custom expression evaluator

**Description**: Write our own simple AND/OR evaluator from scratch.

**Pros**:
- Complete control over features
- Minimal code (could be ~100 lines)
- No external dependency
- Fast evaluation

**Cons**:
- Requires careful security review (risk of bugs)
- No battle-tested code (safety unproven)
- Future extensions (Phase 2 OR/NOT) require rework
- No good error messages
- Maintenance burden on team
- Hard to parallelize safely

**Why not chosen**: Security-critical code should be externally maintained and audited. Custom code introduces risk. simpleeval is proven, audited, and widely used.

#### Alternative 3: eval() with sandbox

**Description**: Use Python's `eval()` with restricted globals/locals (e.g., only allow safe vars).

**Pros**:
- Simple to implement
- Supports arbitrary expressions (future-proof)

**Cons**:
- Even with sandboxing, eval() is fundamentally unsafe
- Clever attackers can escape sandbox via `__import__`, `__builtins__`, etc.
- Security researchers regularly find eval escapes
- Not acceptable for ops-controlled configuration (principal of least privilege)

**Why not chosen**: eval() is never safe, even with sandboxing. This violates security best practices.

### Consequences

**Positive**:
- Safe expression evaluation without code execution risk
- Clear, maintainable code (team can audit if needed)
- Minimal dependencies (simpleeval, no additional libraries)
- Good error messages for debugging
- Ready for Phase 2 (OR/NOT logic already supported)
- Small attack surface (single small library to audit)

**Negative**:
- One additional dependency (simpleeval, but small)
- Slight performance overhead vs. native Python (negligible for daily polling)
- Phase 2 may need to extend grammar (no performance impact, simpleeval is flexible)

**Neutral**:
- Team must learn simpleeval documentation (minimal learning curve, ~5 min)

### Compliance

- Code review will verify simpleeval is used correctly
- Documentation will include example expressions (no dangerous patterns)
- Security audit will verify no code execution paths exist
- Test suite will include adversarial expressions (injection attempts)

---

## ADR-0019: Scheduler Integration Approach

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, SRE, Operations
- **Related**: PRD-2025-001, TDD-2025-001

### Context

Pipeline Automation requires daily polling at a configured time. Currently, the system is event-driven (triggers on SaveSession commit). We need to add a time-based trigger mechanism.

**Problem**: How do we reliably execute rule evaluation daily at a specific time?

**Constraints**:
- Must run exactly once per day at configured time
- Must be timezone-aware
- Must prevent concurrent execution (no duplicate evaluations)
- Must be observable (logs, metrics)
- Must work in development (for testing) and production
- Must survive application restarts
- Must integrate with existing AutomationEngine

### Decision

We will use **system cron for production** + **APScheduler for development/testing**.

**Production**: System cron executes a CLI command or HTTP endpoint at configured time.
**Development/Testing**: APScheduler (in-process) runs the scheduler within the application.

Both approaches call the same `evaluate_rules_async()` method on PollingScheduler.

### Rationale

**Why this approach**:

1. **Reliability**: System cron is the gold standard for Unix scheduled jobs. It's reliable, well-tested, and survives application restarts. Operations teams know cron intimately.

2. **Observability**: Both approaches log invocations. Cron logs go to syslog; APScheduler logs go to app logs. Both are visible for debugging.

3. **Simplicity**: No complex scheduler state management needed. Cron is external to app (no coordination overhead). APScheduler is embedded but simple (single daily job).

4. **Prevents concurrent execution**: Cron runs at exact time (once); APScheduler uses in-process lock. No risk of duplicate evaluations.

5. **Timezone handling**: Both cron and APScheduler support timezone-aware scheduling. Cron uses server TZ; APScheduler uses pytz.

6. **Testing**: APScheduler allows unit/integration testing without mocking system cron. Tests can manually trigger `evaluate_rules_async()` without waiting for cron.

7. **Operational model matches constraints**:
   - Production: Cron (external, ops-friendly, proven)
   - Development: APScheduler (embedded, test-friendly)
   - No difference in code path or results

### Alternatives Considered

#### Alternative 1: APScheduler everywhere (production + dev)

**Description**: Use APScheduler for both production and development. Single library, simpler codebase.

**Pros**:
- Single codebase (APScheduler in both prod and dev)
- Rich features (retry, misfire handling, timezone awareness)
- Easy to test (in-process)
- No dependency on system cron

**Cons**:
- Production relies on app being running (if app crashes, scheduler stops)
- State stored in-process memory (lost on restart)
- Ops team must understand APScheduler internals
- No clear separation between app and scheduling concerns
- Adds complexity to app (embedded scheduler)
- Harder to monitor with standard Unix tools (not in crontab)

**Why not chosen**: Production reliability requires cron. App shouldn't be responsible for its own scheduling (separation of concerns). If app crashes, cron will restart it; without cron, scheduling stops.

#### Alternative 2: System cron everywhere

**Description**: Use system cron for both production and development. No APScheduler dependency.

**Pros**:
- Single approach (operational consistency)
- No scheduler library dependency
- Proven reliability in production

**Cons**:
- Development must set up cron (overhead, not always possible)
- Unit tests can't easily mock cron
- Integration tests require waiting for scheduled time (slow)
- Developers on laptops may not have cron available (WSL/Windows)
- Harder to manually test rule evaluation during development

**Why not chosen**: Development experience suffers. APScheduler is too valuable for testing to give up.

#### Alternative 3: Kubernetes CronJob / managed scheduler

**Description**: If app runs on Kubernetes, use native CronJob to trigger evaluation.

**Pros**:
- Integrates with platform
- Kubernetes manages scaling, restarts
- Native observability (Kubernetes events)

**Cons**:
- Assumes Kubernetes deployment (may not be case)
- Not applicable to on-prem or traditional VM deployments
- Adds infrastructure dependency
- Platform lock-in

**Why not chosen**: Deployment model is not Kubernetes-only. Solution must work on traditional VMs, on-prem, or hybrid. Cron + APScheduler hybrid is deployment-agnostic.

#### Alternative 4: Webhook / external trigger

**Description**: External service calls webhook to trigger evaluation. No scheduler in app.

**Pros**:
- Complete separation of concerns
- Flexible (external scheduler could be anything)
- No app dependencies

**Cons**:
- Adds operational complexity (now need external service)
- Harder to debug (network latency, coordination issues)
- Ops must manage another service
- Single point of failure (if external service down, rules don't run)

**Why not chosen**: Increases operational burden. Cron + APScheduler is simpler and doesn't require additional services.

### Consequences

**Positive**:
- Production reliability: cron ensures evaluation happens even if app restarts
- Development convenience: APScheduler enables testing without cron setup
- Clear separation of concerns: app evaluates rules, cron triggers evaluation
- Observability: both cron and APScheduler log their actions
- Operational familiarity: ops teams know cron
- Timezone-aware: both approaches handle TZ correctly
- No concurrent execution: cron runs at exact time, APScheduler uses lock

**Negative**:
- Two different implementations (cron script vs. APScheduler code) to maintain
- Ops must understand both cron and app configuration
- APScheduler dependency (but small and widely used)

**Neutral**:
- App configuration specifies both cron schedule (for prod) and APScheduler config (for dev)
- Tests can mock or bypass scheduler entirely

### Compliance

- Cron job will be documented in deployment runbook
- APScheduler configuration will be in app config
- Both will log invocations with timestamp (for audit)
- Lock mechanism will prevent concurrent execution (mutex/asyncio.Lock)

---

## ADR-0020: Configuration Validation Library

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-2025-001, TDD-2025-001

### Context

Pipeline Automation requires strict YAML validation at application startup. Invalid configuration must cause startup failure with clear error messages. Configuration must be strongly typed (rules, conditions, actions).

**Problem**: Which library should validate YAML configuration against schema?

**Constraints**:
- Must reject invalid configuration at startup (fail fast)
- Must provide clear error messages (actionable for ops)
- Must enforce required fields and type constraints
- Must reject extra fields (strict mode)
- Must support environment variable substitution
- Pydantic v2 is already a project dependency
- Must be maintainable by team

### Decision

We will use **Pydantic v2** for configuration validation.

Configuration is defined as Pydantic v2 dataclasses with `extra="forbid"` to enforce strict schema. Schema lives in code (owned by devs), values in YAML (owned by ops).

### Rationale

**Why Pydantic v2**:

1. **Already in dependencies**: Pydantic is already used in the project. No additional dependency needed.

2. **Strong type checking**: Pydantic validates field types, required/optional, enums, nested models. Gives us type safety without boilerplate.

3. **Clear error messages**: Pydantic generates helpful validation errors. Example:
   ```
   rules[0].conditions[0]: At least one trigger type required
   ```
   This tells ops exactly where to look.

4. **Strict schema enforcement**: `ConfigDict(extra="forbid")` rejects unknown fields. Prevents silent misconfiguration (typos in YAML).

5. **Composition/nesting**: Rules contain conditions contain triggers. Pydantic nesting makes this natural and type-safe.

6. **Custom validators**: Pydantic v2 supports `@field_validator` for custom logic (e.g., "at least one trigger required").

7. **Serialization**: If we need to output config (debugging, audit), Pydantic has built-in serialization.

8. **Documentation**: Pydantic models generate JSON Schema automatically (useful for ops reference).

### Alternatives Considered

#### Alternative 1: jsonschema library

**Description**: Use standalone JSON Schema validation library. Define schema separately from code (JSON file).

**Pros**:
- Clear separation: schema in JSON file, code doesn't hardcode schema
- Standard JSON Schema format (portable, well-documented)
- No type assumptions in code (schema is source of truth)
- Can evolve schema without code changes (in theory)

**Cons**:
- Requires separate JSON Schema file to maintain
- Error messages less helpful than Pydantic
- Type checking not enforced at code level (runtime only)
- More boilerplate (load JSON, instantiate validator, manually check)
- Pydantic v2 generates JSON Schema anyway (so no real separation)
- Ops still need to understand JSON Schema (not simpler)

**Why not chosen**: Pydantic already provides JSON Schema generation + better DX. Additional JSON Schema file is redundant. Pydantic is already in use.

#### Alternative 2: YAML-specific schema language (e.g., Kwalify, YAML Schema)

**Description**: Use YAML-specific schema validation library.

**Pros**:
- Schema can be written in YAML (familiar format)
- Semantically specific to YAML (handles anchors, aliases)

**Cons**:
- Unknown/unfamiliar libraries (not widely used)
- Less mature than Pydantic/jsonschema
- Fewer resources, smaller community
- Adds new dependency
- Less integration with Python type system

**Why not chosen**: Not worth the additional dependency and learning curve. Pydantic is more established and already integrated.

#### Alternative 3: Custom validation code

**Description**: Write custom Python validation functions (no library).

**Pros**:
- Complete control
- No dependencies
- Simple code (for simple schemas)

**Cons**:
- Security burden (must validate all fields correctly)
- Error messages not as good (must write manually)
- Type checking not enforced (error-prone)
- Duplicates logic Pydantic already has
- Hard to evolve schema later

**Why not chosen**: Reinventing the wheel. Pydantic does this better and is proven.

#### Alternative 4: No validation (trust ops)

**Description**: Load YAML without validation, trust ops to write correct config.

**Pros**:
- No dependencies
- Simplest code

**Cons**:
- Silent failures (typos in YAML cause runtime errors, not clear failures)
- Hard to debug ("why isn't my rule running?")
- Violates "fail fast" principle
- Ops blame us for poor error messages
- Ops can't easily catch config errors before deploying

**Why not chosen**: Fails PRD requirement (FR-008: invalid config = startup failure with clear message). Not acceptable for ops experience.

### Consequences

**Positive**:
- Strong type safety (caught at startup, not runtime)
- Clear error messages (ops know exactly what to fix)
- Strict schema validation (typos rejected)
- JSON Schema auto-generated (ops reference)
- Pydantic already in project (no extra dependency)
- Extensible (custom validators for business logic)
- Community support (Pydantic widely used)

**Negative**:
- Team must understand Pydantic v2 (learning curve, minimal)
- Schema lives in Python code (not portable, but clearer integration)
- If moving to different language, Pydantic becomes liability (unlikely in near term)

**Neutral**:
- Pydantic generates JSON Schema as side-effect (useful for documentation, not required)

### Compliance

- Schema will be reviewed in PR (clear, well-documented)
- Example YAML configurations will be provided (ops reference)
- Validation tests will verify all edge cases (missing fields, wrong types, extra fields)
- Startup validation will be logged (audit trail)

---

## ADR-0021: Logging Format Standardization

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, SRE, DevOps
- **Related**: PRD-2025-001, TDD-2025-001

### Context

Pipeline Automation requires comprehensive logging for debugging, auditing, and compliance. Logs must be queryable with standard Unix tools (grep, jq) and aggregatable for monitoring. Existing logging may be inconsistent (text logs, unstructured format).

**Problem**: What logging format and library should we use for automation rule execution?

**Constraints**:
- Must output JSON (queryable with jq)
- Must be grep-compatible (newline-delimited JSON)
- Must include timestamp, level, event type
- Must redact sensitive data (API keys, credential values)
- Must integrate with existing app logging (if any)
- Must have minimal performance impact (no network calls for Phase 1)
- Should follow industry standards (OpenTelemetry, ECS, JSON Logs)

### Decision

We will use **structlog** with JSON output format for automation rule execution logs.

- Application logs to structured JSON (JSON Lines format)
- Each line is a complete JSON object with timestamp, level, event, fields
- Queryable with `jq` and `grep`
- 30-day retention policy (enforced by external logrotate or similar)

### Rationale

**Why structlog + JSON**:

1. **Structured logging**: structlog encourages logging structured data (dicts/objects) instead of formatted strings. This makes logs machine-readable and easily queryable.

2. **JSON output**: structlog has built-in JSON renderer. Outputs newline-delimited JSON (one log per line), which is standard for log aggregation.

3. **Clean API**: structlog has intuitive API:
   ```python
   log.info("rule_executed", rule_id="123", status="success", duration_ms=1234)
   # Output: {"timestamp": "...", "level": "info", "event": "rule_executed", "rule_id": "123", ...}
   ```

4. **Tooling support**: jq and grep work naturally with JSON Lines format:
   ```bash
   grep "2025-12-27" automation.json | jq '.[] | select(.status == "success")'
   ```

5. **Performance**: Synchronous JSON output to local file (fast). No network calls or async I/O in Phase 1.

6. **Redaction support**: structlog has processors that can redact sensitive fields before output.

7. **Integration ready**: structlog works with standard Python logging, so can integrate with existing app logging.

8. **No vendor lock-in**: JSON Lines is open format. Can parse with any tool or migrate to different logger later.

### Alternatives Considered

#### Alternative 1: OpenTelemetry (OTEL)

**Description**: Use OpenTelemetry for logging (with JSON exporter).

**Pros**:
- Industry standard (traces, metrics, logs unified)
- Rich context propagation (trace IDs across services)
- Vendor-agnostic exporters (can export to any backend)
- Future-proof (OTEL becoming de facto standard)

**Cons**:
- Overkill for Phase 1 (we only need local JSON logs)
- More complex API (more configuration needed)
- Additional dependencies
- Higher learning curve
- Needs backend receiver (Jaeger, Datadog, etc.) for value
- More infrastructure complexity

**Why not chosen**: Phase 1 doesn't need distributed tracing or metrics. OTEL adds complexity without immediate benefit. Can migrate to OTEL later if needed (JSON output compatible).

#### Alternative 2: Custom JSON logging

**Description**: Manually format and write JSON to log file.

**Pros**:
- Complete control
- Minimal dependencies
- Simple implementation (for simple schemas)

**Cons**:
- Error-prone (must handle JSON escaping, timestamp formatting)
- No levels/filters built-in
- Must re-implement logging best practices
- Harder to evolve log schema
- No integration with existing logging
- Maintenance burden

**Why not chosen**: structlog does this better, is proven, and is designed for exactly this use case.

#### Alternative 3: ECS (Elastic Common Schema) JSON

**Description**: Output JSON in ECS format (compatible with Elasticsearch/Kibana).

**Pros**:
- Standard schema (Elastic Common Schema)
- Compatible with Kibana dashboards (out of the box)
- Clear field names (industry standard)
- Can import ECS-formatted logs into Elasticsearch easily

**Cons**:
- ECS schema is extensive (many optional fields)
- Requires Elasticsearch infrastructure (not available Phase 1)
- Steers toward vendor solution (Elastic)
- More verbose JSON (higher storage)

**Why not chosen**: Phase 1 doesn't have Elasticsearch. Custom JSON schema is simpler. Can convert to ECS format later if needed (JSON is portable).

#### Alternative 4: Text-based logging (no JSON)

**Description**: Structured but human-readable text logs (e.g., logfmt).

**Pros**:
- Human-readable (easier to scan manually)
- Simple format (key=value pairs)

**Cons**:
- Not directly queryable with jq
- Grep searches less precise (string matching, not JSON)
- Harder to aggregate (need custom parsers)
- Violates PRD requirement (jq-queryable)
- Less suitable for compliance audits (harder to parse)

**Why not chosen**: PRD explicitly requires jq queryability (FR-009). JSON is better for compliance audits.

### Consequences

**Positive**:
- Machine-readable logs (easily queryable, aggregatable)
- Standard JSON Lines format (portable, future-proof)
- Clear schema (timestamp, level, event, fields)
- Sensitive data redaction (can mask secrets)
- Simple CLI queries (jq, grep)
- No external infrastructure needed (Phase 1)
- Good performance (local file I/O)
- Audit trail for compliance

**Negative**:
- One additional dependency (structlog, but lightweight)
- Team must learn structlog API (minimal learning curve)
- JSON logs larger than text (higher storage, mitigated by 30-day retention)
- No built-in dashboard (Phase 2 can add Kibana/Datadog if needed)

**Neutral**:
- File rotation (external responsibility via logrotate)
- Log aggregation (future enhancement, not Phase 1)

### Compliance

- All rule executions logged (100% coverage)
- Logs include rule_id, status, timestamp, action_taken
- Sensitive data redacted (no credential values in logs)
- Log format documented (schema with example)
- Retention policy enforced (30 days via logrotate or similar)
- Queryable examples provided in ops runbook

---

## ADR-0022: Configuration File Location & Change Management

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, Operations
- **Related**: PRD-2025-001, TDD-2025-001

### Context

Pipeline Automation configuration must live externally (not in code). Operations teams need to modify rule YAML without engineering intervention. Configuration must be findable at application startup and survive updates.

**Problem**: Where should rule configuration files live? How are they managed and updated?

**Constraints**:
- Operations teams (not engineers) should own configuration
- Configuration must be version-controlled or easily backed up
- Configuration must survive application updates/restarts
- Path must be consistent across environments (dev, staging, prod)
- Must support environment-specific overrides (different rules per env)
- Must not require code changes to update rules

### Decision

Configuration files will live at:
- **Default location**: `/etc/autom8_asana/rules.yaml` (production best practice for Unix)
- **Override via environment variable**: `AUTOM8_RULES_CONFIG=/custom/path/rules.yaml`
- **No hot reload**: Configuration changes require application restart

### Rationale

**Why this location**:

1. **Unix convention**: `/etc/` is standard for application configuration on Unix/Linux. Ops teams expect config there. This follows principle of least surprise.

2. **Separation of concerns**: Config separate from application code. Code updates don't touch config. Config updates don't require code merge.

3. **Permissions model**: `/etc/autom8_asana/` can be owned by service user (autom8, asana, etc.) with restricted permissions. Clear ownership.

4. **Version control**: Config can be managed separately:
   - Code repository: application code
   - Config repository or infrastructure-as-code: rule definitions
   - Both can be updated independently

5. **Environment-specific**: Environment variable allows override for dev/staging:
   - Dev: `AUTOM8_RULES_CONFIG=/home/developer/rules.yaml`
   - Staging: `AUTOM8_RULES_CONFIG=/opt/staging/rules.yaml`
   - Prod: Default `/etc/autom8_asana/rules.yaml` or explicit env var

6. **No hot reload**: Simpler implementation, safer. Config validated at startup. No runtime schema changes (reduces risk of inconsistent state). Restart is safe and expected in ops practices.

7. **Audit trail**: Each application start logs config load (file path, rule count, status). Deployments create audit trail.

### Alternatives Considered

#### Alternative 1: Config in environment variable (inline YAML)

**Description**: Entire configuration as env var value (e.g., `AUTOM8_RULES_YAML="{...}"`).

**Pros**:
- Single env var to set
- Works with containerized deployments (no file mounts needed)
- Easy for CI/CD (no file management)

**Cons**:
- YAML inline in env var is hard to read/edit
- Version control of env var is messy
- Large config exceeds shell limits
- Ops can't easily edit config on live system
- Not Unix convention (breaks principle of least surprise)

**Why not chosen**: Violates operational UX. Ops can't easily maintain large YAML in env var.

#### Alternative 2: Config in database

**Description**: Store rules in database (JSON column in rules table).

**Pros**:
- Centralized storage
- Can implement hot reload (read from DB at each evaluation)
- Can add UI for rule editing (Phase 2)
- Audit trail (DB timestamps, who changed what)

**Cons**:
- Adds database dependency
- Requires database connection at startup
- Hot reload adds complexity (cache invalidation)
- Database must be available for app to start
- Ops must learn DB instead of editing YAML
- Schema versioning complexity (JSON in DB is loose)
- Harder to backup (not filesystem-based)

**Why not chosen**: Phase 1 should be simple. Database adds complexity without benefit. YAML files are simpler, more portable, easier to backup.

#### Alternative 3: Config in application code (dataclasses)

**Description**: Define rules as Python dataclasses in application code.

**Pros**:
- Type-safe at code level
- No external file dependency
- Single source of truth (code)

**Cons**:
- Violates requirement: ops must own configuration
- Requires code change and deployment for rule updates
- No separation of concerns (code + config mixed)
- Difficult for ops to modify without engineer help

**Why not chosen**: Explicitly violates PRD requirement that ops owns configuration values.

#### Alternative 4: Config in multiple files (rules.d directory)

**Description**: Store each rule in separate file: `/etc/autom8_asana/rules.d/rule_001.yaml`, etc.

**Pros**:
- Granular file management
- Easier to enable/disable individual rules (remove file)
- Potential for future rule composition

**Cons**:
- More complex to load (must scan directory, merge rules)
- Coordination across files harder to manage
- Distributed config is harder to review as single document
- More operational complexity (managing many small files)

**Why not chosen**: Single `rules.yaml` is simpler. If granular management needed later, can refactor (not breaking change).

### Consequences

**Positive**:
- Standard Unix location (`/etc/` convention followed)
- Clear separation: config lives outside code repository
- Operations owns configuration (no code changes needed)
- Environment flexibility (env var override)
- Simple to understand and document
- No database dependency
- Easy to back up (file-based)
- Version control friendly (config file can be in separate repo)

**Negative**:
- No hot reload (requires restart to apply changes)
- File must exist at startup (clear error if missing)
- Permissions management (must ensure app can read `/etc/` path)
- Multi-server setup requires synchronizing files (separate concern)

**Neutral**:
- Requires ops to manage file system (expected responsibility)
- Restart is expected for config changes (industry standard)

### Compliance

- Configuration file location documented in deployment runbook
- Example rules.yaml provided in repository
- Permissions guidelines provided (file ownership, read-only for app)
- Startup validation logs file path and rule count (audit)
- Backup strategy documented (treat as critical config)

---

## ADR-0023: Schema vs. Values Separation

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, Requirements Analyst, Operations
- **Related**: PRD-2025-001, TDD-2025-001

### Context

Pipeline Automation requires split ownership: Developers define the schema (what triggers/actions are allowed), Operations provide values (which projects, thresholds, tags). This separation reduces human error and enables safe configuration evolution.

**Problem**: How do we enforce clear boundaries between schema (dev) and values (ops)?

**Constraints**:
- Schema must be version-controlled in code repository (owned by engineers)
- Values must be in configuration files (owned by operations)
- Developers can't require ops to write Python code
- Operations shouldn't need to understand internal code structure
- Schema evolution must not require ops changes (backward compatible)
- Schema validation must fail clearly if ops provide invalid values

### Decision

- **Schema** (owned by developers): Pydantic dataclasses in Python code
  - Define allowed triggers: stale, deadline, age
  - Define allowed actions: add_tag, change_section, add_comment, etc.
  - Define field constraints: days >= 1, field names must exist, etc.

- **Values** (owned by operations): YAML configuration files
  - Specify which rules to run
  - Specify which project GIDs to evaluate
  - Specify threshold values (N days for stale, deadline proximity, age)
  - Specify action parameters (tag name, section name, etc.)

**Enforcement Mechanism**: Configuration is validated against Pydantic schema at startup. Any value that violates schema causes startup failure with clear error message.

### Rationale

**Why this separation**:

1. **Reduces human error**: Developers test and review schema (one-time cost). Operations provide values (repetitive, high error risk). Clear schema prevents typos, invalid values.

2. **Enables self-service**: Operations can add new rules without engineering support. Schema defines what's allowed; ops stays within constraints.

3. **Safety**: Invalid configuration fails fast at startup. Operations knows immediately if they made a mistake (not discovered in production).

4. **Clarity**: Each team knows their responsibility:
   - Developers: Define what's possible (schema)
   - Operations: Choose what to actually run (values)

5. **Version control separation**: Code and config in separate repos:
   - Code repo: Schema definitions, validation logic
   - Config repo (or infrastructure-as-code): Rules YAML files
   - Deployments synchronize both independently

6. **Evolution**: Developers can extend schema (add new action types) without breaking existing ops rules. Schema must be backward compatible (old rules still work).

7. **Auditability**: Code changes tracked in git (who added new trigger type, when). Config changes tracked separately (who added/modified rule, when).

### Alternatives Considered

#### Alternative 1: Ops writes schema (JSON Schema files)

**Description**: Ops writes JSON Schema files directly, Developers review in PRs.

**Pros**:
- Ops has more direct control
- Smaller schema documents (less boilerplate)
- Can iterate without code review

**Cons**:
- Ops must understand JSON Schema (complex language)
- JSON Schema validation is fragile (easy to make mistakes)
- Errors in schema validation code not caught by static analysis
- Code review burden same as Python code (still needs eng review)
- No IDE support for JSON Schema
- Harder to test schema validity

**Why not chosen**: JSON Schema is too complex for ops teams. Python dataclasses with Pydantic are clearer, have IDE support, are testable.

#### Alternative 2: Developers provide hardcoded rules (no config)

**Description**: Engineers define all rules in code. Ops can't modify without code change.

**Pros**:
- Single source of truth (code)
- Type-safe (full static analysis)
- Clear ownership (code review required)

**Cons**:
- Violates PRD requirement (ops must own values)
- No self-service (ops can't add rules)
- Slower iteration (need eng to deploy rules)
- Reduces business agility

**Why not chosen**: Explicitly violates PRD goal of ops self-service.

#### Alternative 3: Dynamic schema (ops defines triggers and actions in config)

**Description**: Ops can define custom triggers/actions in YAML alongside rules.

**Pros**:
- Maximum flexibility
- Ops can add new trigger types without eng

**Cons**:
- No safety guardrails (ops can define invalid triggers)
- No static validation (errors found at runtime)
- Security risk (ops could accidentally enable dangerous features)
- Maintenance nightmare (trigger definitions scattered across rules files)
- Code review process broken (can't review triggers in isolation)

**Why not chosen**: Reduces safety. Schema must be centralized and reviewed by developers.

#### Alternative 4: Embedded schema in rules YAML

**Description**: Each rule file includes schema definition alongside values.

**Pros**:
- Decentralized (easier for ops to understand individual rules)
- Self-documenting (schema and values together)

**Cons**:
- Schema duplication (each rule repeats same definitions)
- Inconsistent validation (different versions of schema in different files)
- Hard to evolve schema (must update multiple files)
- Ops tempted to modify schema (violates separation)

**Why not chosen**: Schema duplication and inconsistency are maintenance nightmare. Schema must be centralized.

### Consequences

**Positive**:
- Clear ownership: devs own schema, ops own values
- Safe defaults: schema enforces constraints at startup
- Self-service: ops can modify rules without code changes
- Reduced errors: typos caught by validation
- Fast iteration: ops edit YAML, restart app, done
- Auditability: code and config change separately
- Evolution friendly: new schema versions can be backward compatible
- IDE support: Python dataclasses get autocomplete, type hints

**Negative**:
- Schema must be updated by developers (one-time cost per new trigger type)
- Startup validation required (adds to boot time, but trivial)
- Schema and config in two places (must sync, but git handles this)

**Neutral**:
- Developers must document schema clearly (best practice anyway)
- Operations must understand YAML and basic config concepts (reasonable expectation)

### Compliance

- Schema owned by developers (in code repo, require review)
- Values owned by operations (in config repo, lighter review)
- Pydantic validation enforced at startup (no bypass)
- Schema documentation provided to ops (runbook, examples)
- Code review checklist includes schema review
- Backward compatibility tested (new schema works with old rules)

---

## ADR-0024: Trigger Composition & Future Extensibility

### Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-27
- **Deciders**: Architect, Requirements Analyst
- **Related**: PRD-2025-001, TDD-2025-001

### Context

Pipeline Automation supports combining multiple trigger conditions (stale, deadline, age) on a single rule. Currently, Phase 1 requires AND composition (all conditions must match). Phase 2 may need OR (at least one condition matches) and nested parentheses.

**Problem**: How do we design trigger composition to support Phase 1 AND while preparing for Phase 2 OR?

**Constraints**:
- Phase 1 must support AND composition only
- Phase 1 must not implement OR (keep scope manageable)
- Must not require schema changes when OR is added in Phase 2
- Parser/evaluator must be extensible
- Must be understandable by operations teams

### Decision

- **Phase 1**: Implicit AND composition of conditions in a rule
  - Rule has `conditions` array
  - ALL conditions must evaluate to true for rule to trigger
  - No explicit boolean operators in YAML (AND is implicit)

- **Schema design**: Prepare for Phase 2 with expression field
  - Optional `expression` field in rule (not used Phase 1)
  - Stores boolean expression string (e.g., "condition_1 or condition_2")
  - Phase 2 will evaluate expression
  - Phase 1 ignores expression field (always uses AND)

```yaml
# Phase 1: Simple AND (no expression field used)
rule:
  conditions:
    - stale: { field: "Section", days: 3 }
    - deadline: { days: 7 }
  # Implicit AND: both conditions must match

# Phase 2: Explicit OR (expression field used)
rule:
  conditions:
    - stale: { field: "Section", days: 3 }
    - deadline: { days: 7 }
  expression: "condition_0 or condition_1"
  # Evaluate expression instead of implicit AND
```

### Rationale

**Why this approach**:

1. **Phase 1 simplicity**: AND is straightforward to implement. No expression parser needed. Simple semantics: all conditions must match.

2. **Backward compatible**: Phase 1 YAML doesn't use `expression` field. Adding it in Phase 2 doesn't break Phase 1 configs. Phase 1 just ignores the field.

3. **Extensible parser**: Expression evaluator (simpleeval) already supports OR and NOT. Phase 2 just needs to enable evaluation of expression field.

4. **Clear evolution path**: Phase 1 docs say "Phase 2 will add expression field for OR support". Ops teams can plan accordingly.

5. **Gradual migration**: Old Phase 1 rules continue working (implicit AND). New Phase 2 rules can use explicit `expression` field. No forced migration.

6. **Test-friendly**: Phase 1 can test implicit AND thoroughly. Phase 2 can add expression tests without touching Phase 1 logic.

7. **Ops experience**: Phase 1 YAML is simpler (no complex boolean strings). Phase 2 YAML is more powerful but opt-in.

8. **Safety**: Implicit AND is less error-prone than ops writing boolean expressions. Fewer opportunities for typos.

### Alternatives Considered

#### Alternative 1: Explicit AND in Phase 1, prepared for OR

**Description**: Phase 1 YAML includes explicit `expression` field (e.g., "condition_0 and condition_1"), prepared for OR in Phase 2.

**Pros**:
- Clear intent in YAML (expression visible)
- No semantic difference Phase 1→2 (only expression changes)
- Ops learns expression syntax early (less steep learning curve Phase 2)

**Cons**:
- More complex for Phase 1 YAML (ops must write "and" keywords)
- Error-prone (typos in expressions)
- Requires parser/evaluator in Phase 1 (more code)
- More opportunities for config errors
- Violates "simplest viable approach"

**Why not chosen**: Phase 1 should be simple. Adding expression parser in Phase 1 is unnecessary complexity. Phase 2 can add it when needed.

#### Alternative 2: Separate AND and OR rules (no mixing)

**Description**: Phase 1 rules support AND only. Phase 2 adds new `or_rules` field for OR-based rules. Each rule is either AND or OR, not mixed.

**Pros**:
- Clear semantics per rule
- No need for full boolean expression syntax
- Simple Phase 1 and Phase 2

**Cons**:
- Can't mix AND and OR in single rule (limiting)
- Phase 2 requires separate rule types (confusing)
- Ops must duplicate common conditions across AND/OR rules
- Less flexible (future nested logic harder)

**Why not chosen**: Limits expressiveness. Implicit AND with optional expression field is more flexible.

#### Alternative 3: Start with OR in Phase 1 (most flexible)

**Description**: Phase 1 supports full boolean expressions (AND, OR, parentheses).

**Pros**:
- Maximum flexibility from start
- No schema changes needed for Phase 2/3
- Powerful for complex rules

**Cons**:
- Overkill for Phase 1 (most rules only need AND)
- Ops can easily write incorrect/ambiguous expressions
- Parser/evaluator complexity in Phase 1 (more bugs)
- Test matrix explodes (combinations of AND/OR)
- Violates "fail fast" principle (complex expressions hard to debug)

**Why not chosen**: Violates YAGNI (You Aren't Gonna Need It). Keep Phase 1 simple, add complexity when requirements demand it.

#### Alternative 4: No composition support (single condition per rule)

**Description**: Each rule has exactly one condition (stale OR deadline OR age, not combinations).

**Pros**:
- Simplest implementation
- No composition logic needed
- Each rule has single responsibility

**Cons**:
- Rules with multiple conditions require multiple rules
- Duplicated actions (each rule applies same action)
- Large configuration files (repetitive)
- Violates FR-006 (boolean AND composition required)

**Why not chosen**: PRD explicitly requires boolean AND composition (FR-006).

### Consequences

**Positive**:
- Phase 1 is simple: conditions array, implicit AND
- Backward compatible: old rules work after adding expression field
- Extensible: Phase 2 can add expression evaluation without schema breaking changes
- Ops experience improves gradually: Phase 1 simple, Phase 2 more powerful
- Parser ready: simpleeval already supports OR/NOT (no library change needed)
- Clear migration path: docs explain Phase 2 transition

**Negative**:
- Unused `expression` field in Phase 1 (small schema overhead)
- Phase 2 requires code change (evaluation logic), not just config
- If Phase 2 never happens, expression field is technical debt

**Neutral**:
- Phase 2 scope will include: enabling expression evaluation, docs, tests

### Compliance

- Phase 1 documentation clearly states "AND only"
- Phase 1 YAML has `expression` field defined as optional/ignored (forward compatible)
- Phase 2 plan documented: how `expression` field will be used
- Schema version not incremented (backward compatible change)
- Tests verify implicit AND behavior Phase 1
- Docs include example Phase 2 YAML (for planning purposes)

---

## Index

| ADR | Title | Status | Key Decision |
|-----|-------|--------|--------------|
| ADR-0018 | Expression Evaluator Library Choice | Accepted | Use simpleeval (safe, lightweight, proven) |
| ADR-0019 | Scheduler Integration Approach | Accepted | System cron (prod) + APScheduler (dev) |
| ADR-0020 | Configuration Validation Library | Accepted | Use Pydantic v2 (type-safe, clear errors) |
| ADR-0021 | Logging Format Standardization | Accepted | structlog + JSON Lines (queryable, standard) |
| ADR-0022 | Configuration File Location | Accepted | `/etc/autom8_asana/rules.yaml` + env var override |
| ADR-0023 | Schema vs. Values Separation | Accepted | Devs own schema (code), Ops own values (YAML) |
| ADR-0024 | Trigger Composition & Extensibility | Accepted | Phase 1: AND only, Phase 2: optional expression field for OR |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-27 | Architect | All 7 ADRs for Pipeline Automation Feature Expansion |

---

## Sign-Off

- **Architect**: All decisions documented and approved
- **Technology Scout**: Recommendations incorporated (simpleeval, APScheduler, Pydantic v2, structlog)
- **Requirements Analyst**: Decisions support PRD requirements
- **Principal Engineer**: Ready for implementation with clear guidance
