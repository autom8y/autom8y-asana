# Test Orchestration Recipes

> Unit, integration, coverage, and watch patterns

## Standard test.just

```just
# test.just
# Test orchestration

# === Meta-task ===
# Run all tests
test: test:unit test:int

# === Unit Tests ===
test:unit *args:
    @just _log "Running unit tests..."
    {{PYTEST}} tests/unit {{args}}

# === Integration Tests ===
test:int *args:
    @just _log "Running integration tests..."
    {{PYTEST}} tests/integration {{args}}

# === Specific File/Pattern ===
test:file file:
    {{PYTEST}} {{file}} -v

test:match pattern:
    {{PYTEST}} -k "{{pattern}}" -v

# === Watch Mode ===
test:watch:
    watchexec -e py -- {{PYTEST}} -x --ff

# === Coverage ===
test:cov:
    @just _log "Running tests with coverage..."
    {{PYTEST}} --cov={{APP}} --cov-report=term-missing

test:cov:html:
    {{PYTEST}} --cov={{APP}} --cov-report=html
    @just _log "Coverage report: htmlcov/index.html"

test:cov:xml:
    {{PYTEST}} --cov={{APP}} --cov-report=xml
```

---

## Pattern Variations

### Fast vs Full

```just
# Quick feedback loop
test:fast:
    {{PYTEST}} tests/unit -x --ff -q

# Full test suite with verbose output
test:full:
    {{PYTEST}} --verbose --tb=long

# Parallel execution
test:parallel:
    {{PYTEST}} -n auto
```

### By Marker

```just
# Run tests by pytest marker
test:slow:
    {{PYTEST}} -m slow

test:quick:
    {{PYTEST}} -m "not slow"

test:smoke:
    {{PYTEST}} -m smoke

test:e2e:
    {{PYTEST}} -m e2e tests/e2e
```

### By Type

```just
# Functional tests
test:functional:
    {{PYTEST}} tests/functional

# API tests
test:api:
    {{PYTEST}} tests/api

# UI tests
test:ui:
    {{PYTEST}} tests/ui
```

---

## Watch Patterns

### Basic Watch

```just
# Re-run on file change, stop on first failure
test:watch:
    watchexec -e py -- {{PYTEST}} -x --ff
```

### Focused Watch

```just
# Watch specific directory
test:watch:unit:
    watchexec -w tests/unit -w src -e py -- {{PYTEST}} tests/unit -x

# Watch with pattern
test:watch:match pattern:
    watchexec -e py -- {{PYTEST}} -k "{{pattern}}" -x
```

### Smart Watch

```just
# Only run tests related to changed files
test:watch:smart:
    {{PYTEST}} --picked --testmon
```

---

## Coverage Patterns

### Basic Coverage

```just
test:cov:
    {{PYTEST}} --cov={{APP}} --cov-report=term-missing
```

### Multiple Reports

```just
test:cov:all:
    {{PYTEST}} \
        --cov={{APP}} \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-report=xml
```

### Coverage with Threshold

```just
test:cov:check min="80":
    {{PYTEST}} --cov={{APP}} --cov-fail-under={{min}}
```

### Coverage Diff

```just
# Show coverage diff against main branch
test:cov:diff:
    {{PYTEST}} --cov={{APP}} --cov-report=term-missing
    diff-cover coverage.xml --compare-branch=origin/main
```

---

## Environment-Aware Testing

### Database Tests

```just
test:db:
    @just _require_env DATABASE_URL
    {{PYTEST}} tests/integration/db -v

test:db:fresh: db:reset
    @just test:db
```

### API Tests

```just
test:api port="8001":
    @just _log "Starting test server..."
    {{UV}} run uvicorn {{APP}}.main:app --port {{port}} &
    sleep 2
    {{PYTEST}} tests/api --base-url=http://localhost:{{port}}
    kill %1 2>/dev/null || true
```

### Docker-Dependent Tests

```just
test:docker:
    @just _require docker
    docker-compose -f docker-compose.test.yml up -d
    {{PYTEST}} tests/integration
    docker-compose -f docker-compose.test.yml down
```

---

## CI-Specific Patterns

```just
# CI test configuration
test:ci:
    {{PYTEST}} \
        --verbose \
        --tb=short \
        --junitxml=test-results.xml \
        --cov={{APP}} \
        --cov-report=xml \
        --cov-fail-under=80

# Separate test results
test:ci:unit:
    {{PYTEST}} tests/unit --junitxml=test-results-unit.xml

test:ci:int:
    {{PYTEST}} tests/integration --junitxml=test-results-int.xml
```

---

## Debugging Patterns

```just
# Run with debugger on failure
test:debug *args:
    {{PYTEST}} --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb {{args}}

# Show local variables in tracebacks
test:verbose *args:
    {{PYTEST}} -vvv --tb=long --showlocals {{args}}

# Run last failed tests only
test:failed:
    {{PYTEST}} --lf -v
```

