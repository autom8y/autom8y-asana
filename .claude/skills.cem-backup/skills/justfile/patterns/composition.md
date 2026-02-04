# Composition Patterns

> Meta-tasks, recipe chaining, and dependency management

## Meta-Task Pattern

A meta-task is a recipe that composes other recipes without adding logic.

### Basic Meta-Task

```just
# Default lint runs all linters
lint: lint:ruff lint:mypy lint:format-check

lint:ruff:
    uv run ruff check .

lint:mypy:
    uv run mypy src/

lint:format-check:
    uv run ruff format --check .
```

**Benefits**:
- `just lint` runs everything
- `just lint:ruff` runs only ruff
- Easy to add/remove checks

### Meta-Task with Ordering

Dependencies run left-to-right:

```just
# Format, then lint, then type-check
check: fmt:fix lint:ruff lint:mypy
```

### Nested Meta-Tasks

```just
# Top-level aggregates domains
ci: env:check fmt lint test build
    @just _log "CI pipeline complete"

# Domain-level aggregates tasks
lint: lint:ruff lint:mypy
test: test:unit test:int
```

---

## Dependency Declarations

### Basic Dependencies

```just
# build depends on lint and test completing first
build: lint test
    uv build

# deploy depends on build
deploy: build
    ./deploy.sh
```

### Dependency with Arguments

```just
# Pass argument through dependency chain
deploy env: (build env)
    ./scripts/deploy.sh {{env}}

build env:
    ENV={{env}} uv build
```

### Optional Dependencies

Use conditionals for optional dependencies:

```just
# Only run integration tests if not in quick mode
test quick="false":
    @just test:unit
    @if [ "{{quick}}" != "true" ]; then just test:int; fi
```

---

## Recipe Chaining

### Sequential Execution

```just
# Run in order using dependencies
full-check: fmt lint test
```

### Conditional Chaining

```just
# Different paths based on environment
deploy env:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{env}}" in
        stage) just deploy:stage ;;
        prod)  just deploy:prod ;;
        *)     echo "Unknown env: {{env}}" && exit 1 ;;
    esac
```

### Early Exit Pattern

```just
# Stop pipeline on failure (default behavior with safe shell)
pipeline:
    just lint
    just test
    just build
    just deploy
```

Each `just` call inherits the safe shell settings, failing the pipeline on any error.

---

## Argument Passing

### Default Arguments

```just
# Empty default means "all"
test file="":
    uv run pytest {{file}}

# With default value
build tag="latest":
    docker build -t {{APP}}:{{tag}} .
```

### Required Arguments

```just
# No default = required
deploy env:
    ./deploy.sh {{env}}

# Usage: just deploy stage
# Error if: just deploy (missing argument)
```

### Variadic Arguments

```just
# Pass remaining args to command
test *args:
    uv run pytest {{args}}

# Usage: just test -v -k "test_user"
```

### Positional + Named Mix

```just
# env is required, tag has default
deploy env tag="latest":
    docker tag {{APP}}:{{tag}} {{REGISTRY}}/{{APP}}-{{env}}:{{tag}}
    docker push {{REGISTRY}}/{{APP}}-{{env}}:{{tag}}
```

---

## Parameterized Dependencies

### Pass Arguments to Dependencies

```just
# Parentheses invoke with argument
deploy env: (_require_env "AWS_PROFILE") (build env)
    ./deploy.sh {{env}}

build env:
    ENV={{env}} uv build
```

### Multiple Parameterized Dependencies

```just
deploy env: (_require "aws") (_require_env "AWS_PROFILE") (_confirm "Deploy to " + env + "?")
    ./deploy.sh {{env}}
```

---

## Matrix Patterns

### Test Matrix

```just
# Run tests across multiple Python versions
test:matrix:
    just _test_version 3.10
    just _test_version 3.11
    just _test_version 3.12

[private]
_test_version version:
    UV_PYTHON={{version}} uv run pytest
```

### Platform Matrix

```just
# Build for multiple platforms
docker:build:all: docker:build:amd64 docker:build:arm64

docker:build:amd64:
    docker build --platform linux/amd64 -t {{APP}}:amd64 .

docker:build:arm64:
    docker build --platform linux/arm64 -t {{APP}}:arm64 .
```

---

## Composition Patterns

### Pipeline Pattern

```just
# Named pipeline stages
pipeline: pipeline:lint pipeline:test pipeline:build pipeline:deploy

pipeline:lint:
    @just _log "Stage: Lint"
    @just lint

pipeline:test:
    @just _log "Stage: Test"
    @just test

pipeline:build:
    @just _log "Stage: Build"
    @just build

pipeline:deploy:
    @just _log "Stage: Deploy"
    @just deploy:stage
```

### Wrapper Pattern

Wrap a recipe with before/after logic:

```just
# Wrapper adds timing
timed recipe:
    #!/usr/bin/env bash
    start=$(date +%s)
    just {{recipe}}
    end=$(date +%s)
    echo "Completed in $((end-start))s"

# Usage: just timed test
```

### Fallback Pattern

```just
# Try primary, fall back to secondary
setup:
    #!/usr/bin/env bash
    if command -v uv > /dev/null; then
        just setup:uv
    else
        just setup:pip
    fi

setup:uv:
    uv sync

setup:pip:
    pip install -r requirements.txt
```

---

## Best Practices

### Do: Use Meta-Tasks for Discoverability

```just
# Users see: just lint, just test, just build
# They can drill down: just lint:mypy
lint: lint:ruff lint:mypy
test: test:unit test:int
```

### Do: Keep Dependencies Explicit

```just
# Clear what runs before deploy
deploy: lint test build
    ./deploy.sh
```

### Avoid: Hidden Dependencies

```just
# BAD: deploy calls build internally
deploy:
    just build  # Hidden in script
    ./deploy.sh

# GOOD: Explicit dependency
deploy: build
    ./deploy.sh
```

### Avoid: Circular Dependencies

```just
# BAD: Will fail
a: b
b: a

# GOOD: Clear direction
prepare: clean
build: prepare
deploy: build
```

### Do: Document Complex Compositions

```just
# CI Pipeline
# 1. Check environment
# 2. Install dependencies
# 3. Run all quality checks
# 4. Build artifacts
# 5. Run full test suite
ci: env:check bootstrap lint test:all build
    @just _log "CI complete"
```
