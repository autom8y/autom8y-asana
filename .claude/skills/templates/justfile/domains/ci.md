# CI Pipeline Recipes

> Single-entrypoint CI patterns and pipeline composition

## Standard ci.just

```just
# ci.just
# CI pipeline entrypoint

# === Main Entrypoint ===
# Single command that CI runs
ci: ci:setup ci:lint ci:test ci:build
    @just _log "CI pipeline complete"

# === Stages ===
ci:setup:
    @just _log "CI Setup..."
    {{UV}} sync --frozen

ci:lint:
    @just _log "CI Lint..."
    {{UV}} run ruff check . --output-format=github
    {{UV}} run ruff format --check .
    {{UV}} run mypy src/

ci:test:
    @just _log "CI Test..."
    {{PYTEST}} \
        --verbose \
        --junitxml=test-results.xml \
        --cov={{APP}} \
        --cov-report=xml \
        --cov-fail-under=80

ci:build:
    @just _log "CI Build..."
    {{UV}} run python -m build
```

---

## Design Principles

### Single Entrypoint

CI configuration should call one command:

```yaml
# .github/workflows/ci.yml
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: just ci
```

This provides:
- **Local parity**: `just ci` runs the same checks locally
- **Simplicity**: CI config stays minimal
- **Control**: Pipeline changes don't require CI config updates

### Stage Isolation

Each stage is a separate recipe:
- Can run stages independently (`just ci:lint`)
- Easy to add/remove stages
- Clear failure attribution

---

## Pipeline Patterns

### Full Pipeline

```just
ci: ci:setup ci:lint ci:test ci:build ci:publish
    @just _log "Pipeline complete"
```

### PR Pipeline (faster)

```just
ci:pr: ci:setup ci:lint ci:test:fast
    @just _log "PR checks complete"

ci:test:fast:
    {{PYTEST}} tests/unit -x --ff
```

### Nightly Pipeline (comprehensive)

```just
ci:nightly: ci:setup ci:lint ci:test:full ci:security ci:build
    @just _log "Nightly complete"

ci:test:full:
    {{PYTEST}} --slow
    just test:e2e

ci:security:
    {{UV}} run bandit -r src/
    {{UV}} run pip-audit
```

---

## Stage Patterns

### Setup Stage

```just
ci:setup:
    @just _log "Setting up CI environment..."

    # Install exact versions
    {{UV}} sync --frozen

    # Verify tools
    @just _require uv
    @just _require git

    @just _log "Setup complete"
```

### Lint Stage

```just
ci:lint:
    @just _log "Linting..."

    # Format check (fast fail)
    {{UV}} run ruff format --check .

    # Lint rules
    {{UV}} run ruff check . --output-format=github

    # Type check
    {{UV}} run mypy src/ --junit-xml=mypy-results.xml

    @just _log "Lint complete"
```

### Test Stage

```just
ci:test:
    @just _log "Testing..."

    {{PYTEST}} \
        --verbose \
        --tb=short \
        --junitxml=test-results.xml \
        --cov={{APP}} \
        --cov-report=xml \
        --cov-report=term-missing \
        --cov-fail-under=80

    @just _log "Tests complete"
```

### Build Stage

```just
ci:build:
    @just _log "Building..."

    # Python package
    {{UV}} run python -m build

    # Docker image
    {{DOCKER}} build \
        --build-arg VERSION={{VERSION}} \
        -t {{IMAGE}}:{{VERSION}} \
        .

    @just _log "Build complete"
```

### Publish Stage

```just
ci:publish: (_require_env "PYPI_TOKEN")
    @just _log "Publishing..."

    {{UV}} run twine upload dist/* \
        --username __token__ \
        --password "${PYPI_TOKEN}"

    @just _log "Published to PyPI"
```

---

## Artifact Patterns

### Test Artifacts

```just
ci:test:
    {{PYTEST}} \
        --junitxml=test-results.xml \
        --cov={{APP}} \
        --cov-report=xml

# GitHub Actions will pick up:
# - test-results.xml (test report)
# - coverage.xml (coverage report)
```

### Build Artifacts

```just
ci:build:
    {{UV}} run python -m build
    # Creates dist/*.whl and dist/*.tar.gz

ci:docker:
    {{DOCKER}} build -t {{IMAGE}}:{{VERSION}} .
    {{DOCKER}} save {{IMAGE}}:{{VERSION}} | gzip > {{IMAGE}}-{{VERSION}}.tar.gz
```

---

## Matrix Patterns

### Python Version Matrix

```just
ci:matrix:
    just ci:test:version 3.10
    just ci:test:version 3.11
    just ci:test:version 3.12

ci:test:version version:
    UV_PYTHON={{version}} {{UV}} run pytest
```

### Platform Matrix

```just
ci:docker:matrix:
    just ci:docker:platform linux/amd64
    just ci:docker:platform linux/arm64

ci:docker:platform platform:
    {{DOCKER}} build --platform {{platform}} -t {{IMAGE}}:{{VERSION}}-$(echo {{platform}} | tr '/' '-') .
```

---

## Caching Patterns

```just
# CI-friendly cache key generation
ci:cache-key:
    @echo "python-$(python --version | cut -d' ' -f2)-$(sha256sum uv.lock | cut -d' ' -f1)"

# Restore from cache
ci:cache:restore:
    @[ -d ".venv" ] && echo "Cache hit" || echo "Cache miss"
```

---

## Failure Handling

```just
ci: ci:setup ci:lint ci:test ci:build
    @just _log "CI complete"

# Each stage fails independently
# GitHub Actions sees which step failed

# For local debugging:
ci:debug: ci:setup
    just ci:lint || true
    just ci:test || true
    just ci:build || true
    @just _log "Debug run complete (failures ignored)"
```

---

## GitHub Actions Integration

### Minimal Workflow

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - uses: extractions/setup-just@v2
      - run: just ci
```

### With Caching

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - uses: extractions/setup-just@v2
      - run: just ci

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: |
            test-results.xml
            coverage.xml
```

