# Primitive Patterns

> _globals.just, _helpers.just, and _env.just patterns

## _globals.just

Defines project-wide constants that other modules reference. Load first.

### Standard Template

```just
# _globals.just
# Project constants and paths

# === Application ===
APP := "myapp"
VERSION := `git describe --tags --always 2>/dev/null || echo "dev"`

# === Tooling ===
PY := "uv run python"
UV := "uv"
PYTEST := "uv run pytest"

# === Docker ===
DOCKER := "docker"
IMAGE := APP
REGISTRY := "ghcr.io/org"
TAG := VERSION

# === Paths ===
SRC := "src"
TESTS := "tests"
DOCS := "docs"

# === Environment ===
ENV := env_var_or_default("ENV", "development")
CI := env_var_or_default("CI", "false")
```

### Key Patterns

**Version from git**:
```just
VERSION := `git describe --tags --always 2>/dev/null || echo "dev"`
```

**Environment with default**:
```just
ENV := env_var_or_default("ENV", "development")
```

**Conditional paths**:
```just
VENV := if path_exists(".venv") == "true" { ".venv" } else { "venv" }
```

**Platform-specific**:
```just
OPEN := if os() == "macos" { "open" } else { "xdg-open" }
```

---

## _helpers.just

Utility recipes used by domain modules. Always private (hidden from `just --list`).

### Standard Template

```just
# _helpers.just
# Shared utility recipes

# === Logging ===
[private]
_log msg:
    @echo "==> {{msg}}"

[private]
_log_success msg:
    @echo "==> {{msg}}"

[private]
_log_warn msg:
    @echo "==> WARN: {{msg}}"

[private]
_log_error msg:
    @echo "==> ERROR: {{msg}}" >&2

# === Requirements ===
[private]
_require cmd:
    @command -v {{cmd}} > /dev/null 2>&1 || \
        (echo "Required command not found: {{cmd}}" >&2 && exit 1)

[private]
_require_env var:
    @[ -n "${{{var}}:-}" ] || \
        (echo "Required environment variable not set: {{var}}" >&2 && exit 1)

[private]
_require_file path:
    @[ -f "{{path}}" ] || \
        (echo "Required file not found: {{path}}" >&2 && exit 1)

# === Confirmation ===
[private]
_confirm msg:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "${CI:-false}" = "true" ]; then
        echo "CI detected, skipping confirmation"
        exit 0
    fi
    read -p "{{msg}} [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 1
    fi

# === Help ===
[private]
help:
    @just --list
```

---

## _env.just

Environment bootstrap, validation, and setup.

### Standard Template

```just
# _env.just
# Environment setup and validation

# === Bootstrap ===
# Install dependencies and set up environment
bootstrap: _check_tools
    @just _log "Bootstrapping environment..."
    {{UV}} sync
    @just _log "Environment ready"

# === Validation ===
[private]
_check_tools:
    @just _require uv
    @just _require git
    @just _require docker

[private]
_check_env:
    @just _require_env DATABASE_URL
    @just _require_env SECRET_KEY

# === Environment Info ===
env:
    @echo "ENV: {{ENV}}"
    @echo "CI: {{CI}}"
    @echo "VERSION: {{VERSION}}"
    @echo "Python: $({{PY}} --version)"
    @echo "UV: $({{UV}} --version)"

# === Clean ===
clean:
    @just _log "Cleaning build artifacts..."
    rm -rf dist/ build/ *.egg-info/
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    rm -rf .coverage htmlcov/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @just _log "Clean complete"

# === Deep Clean ===
clean:deep: clean
    @just _log "Deep cleaning (including venv)..."
    rm -rf .venv/
    @just _log "Deep clean complete"
```

---

## Usage Patterns

### From Domain Modules

```just
# In dev.just
dev: (_require "uv")
    @just _log "Starting development server..."
    {{UV}} run python -m {{APP}}

# In deploy.just
deploy:prod: (_require_env "AWS_PROFILE") (_confirm "Deploy to production?")
    @just _log "Deploying to production..."
    ./scripts/deploy.sh prod
```

### Chaining Helpers

```just
# Multiple requirements
deploy: (_require "aws") (_require_env "AWS_PROFILE") (_check_env)
    ./deploy.sh

# Log before and after
build:
    @just _log "Building..."
    {{UV}} build
    @just _log_success "Build complete"
```

---

## Anti-Patterns

**Avoid**: Duplicating constants across files
```just
# BAD: In dev.just
PY := "uv run python"
# BAD: In test.just
PY := "uv run python"
```

**Do**: Define once in _globals.just, reference everywhere

**Avoid**: Inline requirements
```just
# BAD
deploy:
    command -v aws > /dev/null || (echo "Need aws" && exit 1)
    ...
```

**Do**: Use _require helper
```just
# GOOD
deploy: (_require "aws")
    ...
```
