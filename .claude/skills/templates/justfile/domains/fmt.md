# Format and Lint Recipes

> Code formatting, linting, and type checking composition

## Standard fmt.just

```just
# fmt.just
# Format and lint composition

# === Meta-tasks ===
# Format and fix all
fmt: fmt:ruff fmt:black

# Check all (no fixes)
lint: lint:ruff lint:mypy lint:format-check

# === Formatting ===
fmt:ruff:
    @just _log "Formatting with ruff..."
    {{UV}} run ruff format .
    {{UV}} run ruff check --fix .

fmt:black:
    @just _log "Formatting with black..."
    {{UV}} run black .

fmt:isort:
    {{UV}} run isort .

# === Linting ===
lint:ruff *args:
    @just _log "Linting with ruff..."
    {{UV}} run ruff check . {{args}}

lint:mypy *args:
    @just _log "Type checking..."
    {{UV}} run mypy src/ {{args}}

lint:format-check:
    @just _log "Checking format..."
    {{UV}} run ruff format --check .

# === Combined ===
check: lint test:unit
    @just _log "All checks passed"
```

---

## Pattern Variations

### Ruff-Only Stack

```just
# Modern Python: ruff does format + lint
fmt:
    {{UV}} run ruff format .
    {{UV}} run ruff check --fix .

lint:
    {{UV}} run ruff check .
    {{UV}} run ruff format --check .
```

### Black + Ruff Stack

```just
fmt: fmt:black fmt:ruff

fmt:black:
    {{UV}} run black .

fmt:ruff:
    {{UV}} run ruff check --fix .

lint: lint:ruff lint:format-check

lint:ruff:
    {{UV}} run ruff check .

lint:format-check:
    {{UV}} run black --check .
```

### Pre-Ruff Stack (Black + isort + Flake8)

```just
fmt: fmt:isort fmt:black

fmt:isort:
    {{UV}} run isort .

fmt:black:
    {{UV}} run black .

lint: lint:flake8 lint:mypy lint:format-check

lint:flake8:
    {{UV}} run flake8 .

lint:format-check:
    {{UV}} run black --check .
    {{UV}} run isort --check .
```

---

## Type Checking Patterns

### Basic MyPy

```just
lint:mypy:
    {{UV}} run mypy src/
```

### Strict MyPy

```just
lint:mypy:
    {{UV}} run mypy src/ --strict

lint:mypy:report:
    {{UV}} run mypy src/ --html-report mypy-report
```

### Pyright Alternative

```just
lint:types:
    {{UV}} run pyright src/
```

### Type Stubs

```just
# Generate stubs for untyped dependencies
types:stubs:
    {{UV}} run stubgen -p some_package -o typings/
```

---

## Security Scanning

```just
lint:security:
    @just _log "Security scan..."
    {{UV}} run bandit -r src/

lint:deps:
    @just _log "Checking dependencies..."
    {{UV}} run pip-audit
```

---

## Multi-Language Projects

### Python + JavaScript

```just
fmt: fmt:py fmt:js
lint: lint:py lint:js

fmt:py:
    {{UV}} run ruff format .

fmt:js:
    npm run format

lint:py:
    {{UV}} run ruff check .
    {{UV}} run mypy src/

lint:js:
    npm run lint
```

### Python + Go

```just
fmt: fmt:py fmt:go
lint: lint:py lint:go

fmt:py:
    {{UV}} run ruff format .

fmt:go:
    go fmt ./...
    goimports -w .

lint:py:
    {{UV}} run ruff check .

lint:go:
    golangci-lint run
```

---

## Pre-Commit Integration

```just
# Install pre-commit hooks
hooks:install:
    {{UV}} run pre-commit install

# Run all hooks
hooks:run:
    {{UV}} run pre-commit run --all-files

# Update hooks
hooks:update:
    {{UV}} run pre-commit autoupdate
```

---

## CI Patterns

```just
# CI lint job
lint:ci:
    @just _log "CI lint checks..."
    {{UV}} run ruff check . --output-format=github
    {{UV}} run ruff format --check .
    {{UV}} run mypy src/ --junit-xml=mypy-results.xml

# Fail-fast for PR checks
lint:pr:
    {{UV}} run ruff check .
    {{UV}} run ruff format --check .
    {{UV}} run mypy src/
```

---

## Fix Patterns

```just
# Auto-fix everything possible
fix: fmt
    @just _log "Auto-fix complete"

# Fix with unsafe fixes
fix:unsafe:
    {{UV}} run ruff check --fix --unsafe-fixes .
    {{UV}} run ruff format .
```

