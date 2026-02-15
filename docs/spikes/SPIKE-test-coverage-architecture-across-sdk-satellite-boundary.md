# SPIKE: Test Coverage Architecture Across SDK/Satellite Boundaries

**Date**: 2026-02-13
**Status**: Complete
**Decision Informed**: Where should test responsibilities live across the autom8y SDK ecosystem and its satellite repos?

---

## Question

From first principles: which tests in autom8_asana are testing SDK-level primitive behavior that should live in the platform repo? And how do modern systems architect coverage patterns across multi-repo SDK/consumer boundaries following DRY principles?

---

## The Two Ecosystems — Current State

### autom8y Platform (`~/code/autom8y`)

| SDK Package | Test Files | Key Coverage |
|-------------|-----------|--------------|
| autom8y-log | 50 | Backend conformance, processor pipeline, stdlib bridge, adversarial edge cases |
| autom8y-auth | 21 | JWT validation, resilience, token types, JWKS caching |
| autom8y-cache | 21 | Backend protocol compliance, tiered orchestration, Redis/S3 integration |
| autom8y-telemetry | 10 | State lifecycle, async handling |
| autom8y-config | 6 | Environment resolution, AWS SSM/Secrets |
| **Total** | **~424 files** | |

**What the SDK tests well:**
- Backend contract conformance (`test_output_parity.py` ensures structlog and loguru produce identical JSON schemas)
- Processor pipeline ordering and ContextVar isolation
- Adapter tolerance (`test_positional_args_compat.py` for `*args` hardening)
- 22 adversarial edge cases in autom8y-log alone

**What the SDK does NOT provide:**
- Zero exported `testing` subpackages
- Zero shared test fixtures in wheels (conftest.py excluded from builds)
- Zero conformance suites for consumers
- Zero mock factories for satellite integration testing

### autom8_asana Satellite (`~/code/autom8_asana`)

| Layer | Files | % | Focus |
|-------|-------|---|-------|
| Unit tests | 293 | 82.5% | Satellite business logic |
| Integration | 30 | 8.5% | Cross-component workflows |
| API tests | 18 | 5.1% | HTTP endpoints |
| SDK integration | 6 | 1.7% | autom8y-auth only |
| Other | 8 | 2.2% | Benchmarks, QA |
| **Total** | **355 files** | | **~10,014 tests** |

**SDK coverage breakdown:**
- autom8y-auth: 6 test files, 11 direct imports
- autom8y-log: 2 patches (mocking `get_logger`)
- autom8y-telemetry: 0 direct tests
- autom8y-cache: 0 direct tests
- autom8y-config: 0 direct tests

---

## The Structural Problem

### Tests That Don't Belong Where They Live

Examining autom8_asana's test suite from first principles, **three categories of tests are misplaced**:

#### Category 1: SDK Behavior Tests in Satellite Clothing

Tests that verify the SDK works correctly, not that the satellite uses it correctly.

| Test Area | What It's Actually Testing | Where It Should Live |
|-----------|---------------------------|---------------------|
| `test_structured_logger.py` — `caplog`→`capsys` migration | That SDK's `PrintLoggerFactory` routes to stdout, not stdlib | **autom8y-log** (backend output routing) |
| `test_structured_logger.py` — `core_logging._configured = False` resets | That SDK's idempotent guard can be reset for test isolation | **autom8y-log** (should export `reset_logging()` as test fixture) |
| `test_contract_alignment.py` — `InsightsRequest` schema validation | That the request/response contract matches autom8_data's expectations | **Shared contract** (neither repo alone) |
| Auth tests mocking `autom8y_auth.JWTValidator` internals | That the JWT validator behaves correctly with various tokens | **autom8y-auth** (validator behavior is SDK-defined) |

#### Category 2: Integration Seam Tests That Need SDK Support

Tests at the boundary that are harder than necessary because the SDK doesn't export test infrastructure.

| Test Area | Current Approach | What SDK Should Provide |
|-----------|-----------------|------------------------|
| Mocking `get_logger` return value | `patch('autom8_asana.core.logging.get_logger')` | `autom8y_log.testing.FakeLogger` with assertion methods |
| Resetting logging state between tests | Manual `_configured = False` hack | `autom8y_log.testing.reset_logging_state()` fixture |
| Verifying processor invocation order | No test exists (QA-001) | `autom8y_log.testing.ProcessorChainInspector` |
| Auth token generation for tests | Satellite conftest creates RSA keys + tokens | `autom8y_auth.testing.create_test_token(claims={...})` |
| Cache provider mocking | Each satellite builds its own MockCacheProvider | `autom8y_cache.testing.InMemoryTestProvider` (already exists but not exported) |

#### Category 3: Legitimate Satellite Tests

Tests that correctly live in autom8_asana because they test satellite-specific behavior.

| Test Area | Why It Belongs Here |
|-----------|-------------------|
| `_filter_sensitive_data` redacts `authorization` field | Satellite-defined security policy |
| `configure()` called with correct `level` and `format` from settings | Satellite-specific configuration choices |
| Entity resolution business logic | Pure satellite domain |
| API route behavior | Satellite endpoints |
| Cache key construction | Satellite-specific key patterns |

---

## How Modern Systems Solve This

### The Test Boundary Principle

> Tests should live at the level where the behavior is defined.

| Behavior Owner | Test Location | Example |
|---------------|---------------|---------|
| SDK defines it | SDK repo | "additional_processors are called after add_log_level" |
| Satellite defines it | Satellite repo | "field 'authorization' is redacted from logs" |
| Contract between two | Shared contract repo or SDK-shipped conformance suite | "InsightsRequest schema matches between producer and consumer" |

### Pattern 1: Exported Testing Subpackage

Used by: **OpenTelemetry SDK**, **pytest** itself, **Django REST Framework**, **FastAPI**

```
autom8y-log/
  src/autom8y_log/
    testing/              # Shipped in wheel
      __init__.py         # Public API
      fake_logger.py      # FakeLogger with .assert_logged()
      fixtures.py         # reset_logging(), capture_logs()
      processors.py       # InspectableProcessor, ProcessorSpy
```

Satellites install the SDK and import `from autom8y_log.testing import FakeLogger` — no re-implementation needed. The test utilities are versioned with the SDK, so they stay in sync.

### Pattern 2: Conformance Test Suite

Used by: **OpenTelemetry** (language-agnostic conformance), **AWS SDK** (protocol compliance), **Kubernetes** (CRI/CSI conformance)

The SDK ships a `ConformanceTestSuite` base class:

```python
# In autom8y_log/testing/conformance.py
class LoggingConformanceSuite:
    """Subclass in your satellite to verify SDK integration."""

    def test_configure_is_idempotent(self): ...
    def test_additional_processors_invoked(self): ...
    def test_stdlib_interception_works(self): ...
    def test_reset_allows_reconfigure(self): ...
```

Satellites subclass it:
```python
# In satellite tests/
class TestAutom8AsanaLogging(LoggingConformanceSuite):
    """Runs all SDK conformance tests in our context."""
    pass
```

### Pattern 3: Contract Testing (Pact-style)

Used by: **Pact**, **Spring Cloud Contract**, **AWS EventBridge Schema Registry**

For cross-service contracts (like `InsightsRequest` between autom8_asana and autom8_data):

1. **Provider** publishes a contract (schema + examples)
2. **Consumer** verifies against the contract
3. Contract lives in a shared artifact registry, not in either repo

Currently autom8_asana has 24 contract alignment tests that embed the expected schema. If the schema changes in autom8_data, these tests don't know about it until manual sync.

### Pattern 4: Test Fixture Packages

Used by: **pytest-django**, **pytest-asyncio**, **factory_boy**, **faker**

SDK ships pytest fixtures via entry points:

```toml
# In autom8y-log pyproject.toml
[project.entry-points."pytest11"]
autom8y_log = "autom8y_log.testing.fixtures"
```

Satellites get fixtures automatically when the SDK is installed:

```python
# In satellite tests — no import needed, fixtures auto-registered
def test_logging(reset_logging, capture_logs):
    configure()
    do_something()
    assert capture_logs.has("expected message")
```

---

## The DRY Anti-Pattern: When NOT to DRY Across Repos

DRY across repo boundaries has failure modes:

| Anti-Pattern | What Happens | Example |
|-------------|-------------|---------|
| **Version skew** | SDK ships v2 test fixtures, satellite pinned to v1 | Test fixtures reference APIs that don't exist in the satellite's locked version |
| **Phantom green** | Conformance suite passes but satellite's actual usage isn't covered | Conformance tests exercise happy path; satellite's edge case (sensitive field filter) is untested |
| **Brittle coupling** | Satellite tests import SDK internals that change without notice | Testing `_configured` flag directly instead of through public `reset_logging()` |
| **Wrong abstraction level** | Shared test code tries to cover all satellites, covers none well | Generic `FakeLogger` that doesn't support the specific assertion pattern each satellite needs |

**The principle**: DRY the test infrastructure (fixtures, helpers, mocks), not the test assertions. Each satellite defines what correctness means for its context.

---

## Recommendation: Three-Level Test Architecture

### Level 1: SDK-Owned (lives in autom8y platform repo)

| What | Ships In | Consumer Gets |
|------|----------|---------------|
| `autom8y_log.testing.FakeLogger` | Wheel | Capturable, assertable logger |
| `autom8y_log.testing.reset_logging()` | Wheel | Clean state between tests |
| `autom8y_log.testing.ProcessorSpy` | Wheel | Verify processor invocation + order |
| `autom8y_auth.testing.create_test_token()` | Wheel | JWT generation without RSA key management |
| `autom8y_cache.testing.InMemoryTestProvider` | Wheel | Already exists internally, just export |
| `LoggingConformanceSuite` | Wheel | Base class for satellite conformance |

### Level 2: Contract-Owned (shared artifact or SDK-published schema)

| What | Mechanism | Consumer Gets |
|------|-----------|---------------|
| `InsightsRequest` schema | JSON Schema in SDK or shared registry | Pact-style verification |
| `GidMapResponse` schema | Same | Same |
| Logging JSON output schema | Published by autom8y-log conformance | Output format validation |

### Level 3: Satellite-Owned (lives in each satellite repo)

| What | Why It's Satellite-Specific |
|------|-----------------------------|
| `_filter_sensitive_data` tests | Satellite defines which fields to redact |
| `configure()` called with correct settings | Satellite defines log level, format choices |
| Business logic tests | Pure satellite domain |
| API endpoint tests | Satellite-specific routes |
| Cache key pattern tests | Satellite-specific key construction |

---

## Impact on autom8_asana

### Tests to Remove After SDK Ships Testing Package

Once `autom8y_log.testing` exists:
- Remove `_configured = False` hacks in conftest (use `reset_logging()`)
- Remove `caplog`/`capsys` workarounds (use `FakeLogger` or `capture_logs`)
- Replace ad-hoc `get_logger` mocking with `FakeLogger`

### Tests to Keep

- `_filter_sensitive_data` (satellite security policy — but it needs to EXIST first, per QA-001)
- `configure()` integration tests (satellite configuration choices)
- All business logic tests (unchanged)

### Tests to Add (QA-001 Follow-up)

With SDK `ProcessorSpy`, the satellite test becomes trivial:

```python
def test_sensitive_fields_redacted(processor_spy):
    """Verify _filter_sensitive_data redacts auth headers."""
    configure(additional_processors=[_filter_sensitive_data])
    logger = get_logger("test")
    logger.info("request", authorization="Bearer secret123")
    assert processor_spy.last_event["authorization"] == "[REDACTED]"
```

Without SDK support, the satellite must build its own capture mechanism — which is exactly the DRY violation this spike identifies.

---

## Follow-Up Actions

1. **Platform repo**: Ship `autom8y_log.testing` subpackage (FakeLogger, reset_logging, ProcessorSpy)
2. **Platform repo**: Ship `autom8y_auth.testing` subpackage (create_test_token factory)
3. **Platform repo**: Export `autom8y_cache.testing.InMemoryTestProvider`
4. **Platform repo**: Add `pytest11` entry point for auto-registered fixtures
5. **This satellite**: After (1) ships, replace `_configured` hacks with `reset_logging()`
6. **This satellite**: After (1) ships, add QA-001 test using `ProcessorSpy`
7. **Cross-repo**: Evaluate Pact or JSON Schema contract testing for InsightsRequest
