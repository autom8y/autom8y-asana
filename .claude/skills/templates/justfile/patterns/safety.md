# Safety Patterns

> Confirmations, environment checks, guards, and CI detection

**Note**: Core helpers (`_confirm`, `_require`, `_require_env`) are defined in [primitives.md](primitives.md). This document shows usage patterns.

## Confirmation Pattern

```just
# Destructive operation requires confirmation
db:reset: (_confirm "Reset database? This will DELETE all data.")
    ./scripts/reset-db.sh

# Multiple guards compose naturally
deploy:prod: (_require_env "AWS_PROFILE") (_confirm "Deploy to PRODUCTION?")
    ./scripts/deploy.sh prod
```

### CI-Aware Behavior

The `_confirm` helper auto-confirms in CI (when `CI=true`). For operations that should block in CI:

```just
[private]
_confirm_or_block msg:
    #!/usr/bin/env bash
    if [ "${CI:-false}" = "true" ]; then
        echo "ERROR: {{msg}} - blocked in CI" >&2
        exit 1
    fi
    read -p "{{msg}} [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
```

---

## Environment Guards

```just
# Single variable
deploy: (_require_env "AWS_PROFILE")
    aws deploy ...

# Multiple variables via helper
[private]
_check_deploy_env:
    @just _require_env AWS_PROFILE
    @just _require_env AWS_REGION
    @just _require_env DEPLOY_KEY

deploy: _check_deploy_env
    ./deploy.sh
```

### Environment-Specific Guards

```just
# Block production deploys without explicit flag
deploy env force="false":
    #!/usr/bin/env bash
    if [ "{{env}}" = "prod" ] && [ "{{force}}" != "true" ]; then
        echo "Production deploy requires: just deploy prod force=true"
        exit 1
    fi
    ./deploy.sh {{env}}
```

---

## Tool Guards

```just
# Single tool
docker:build: (_require "docker")
    docker build .

# Multiple tools
k8s:deploy: (_require "kubectl") (_require "helm")
    helm upgrade ...
```

### Require with Version

```just
[private]
_require_version cmd min_version:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v {{cmd}} > /dev/null 2>&1; then
        echo "Required: {{cmd}} >= {{min_version}}" >&2
        exit 1
    fi
    current=$( {{cmd}} --version | grep -oE '[0-9]+\.[0-9]+' | head -1 )
    if [ "$(printf '%s\n' "{{min_version}}" "$current" | sort -V | head -1)" != "{{min_version}}" ]; then
        echo "{{cmd}} version $current < {{min_version}}" >&2
        exit 1
    fi
```

### Require File

```just
deploy: (_require_file ".env.production") (_require_file "dist/app.zip")
    ./deploy.sh
```

---

## CI Detection

### Basic CI Check

```just
CI := env_var_or_default("CI", "false")

# In recipes
build:
    #!/usr/bin/env bash
    if [ "{{CI}}" = "true" ]; then
        echo "Running in CI mode"
        # CI-specific behavior
    fi
    ...
```

### CI-Only Recipe

```just
# This recipe only runs in CI
[private]
_ci_only:
    @[ "${CI:-false}" = "true" ] || \
        (echo "This recipe only runs in CI" >&2 && exit 1)

ci:upload: _ci_only
    # Upload artifacts to CI
    ./scripts/upload-artifacts.sh
```

### Local-Only Recipe

```just
[private]
_local_only:
    @[ "${CI:-false}" != "true" ] || \
        (echo "This recipe only runs locally" >&2 && exit 1)

dev:interactive: _local_only
    # Interactive TUI that won't work in CI
    ./scripts/interactive-setup.sh
```

---

## Destructive Operation Guards

### Database Reset

```just
db:reset: (_confirm "This will DELETE all data. Are you sure?") (_require_env "DATABASE_URL")
    #!/usr/bin/env bash
    set -euo pipefail

    # Extra guard: block in production
    if [[ "${DATABASE_URL}" == *"prod"* ]]; then
        echo "ERROR: Cannot reset production database" >&2
        exit 1
    fi

    ./scripts/reset-db.sh
```

### Production Deploy

```just
deploy:prod: (_require_env "AWS_PROFILE") (_require "aws") (_confirm "Deploy to PRODUCTION?")
    #!/usr/bin/env bash
    set -euo pipefail

    # Require explicit confirmation in non-CI
    if [ "${CI:-false}" != "true" ]; then
        read -p "Type 'production' to confirm: " confirm
        if [ "$confirm" != "production" ]; then
            echo "Aborted"
            exit 1
        fi
    fi

    ./scripts/deploy.sh prod
```

### Clean with Protection

```just
clean:all: (_confirm "This will remove ALL generated files including .venv")
    rm -rf dist/ build/ .venv/ node_modules/
    @just _log "Deep clean complete"
```

---

## Dry Run Pattern

```just
# Preview what would happen
deploy env dry_run="false":
    #!/usr/bin/env bash
    set -euo pipefail

    if [ "{{dry_run}}" = "true" ]; then
        echo "DRY RUN - would deploy to {{env}}"
        ./scripts/deploy.sh {{env}} --dry-run
    else
        just _confirm "Deploy to {{env}}?"
        ./scripts/deploy.sh {{env}}
    fi

# Usage:
# just deploy stage dry_run=true  # Preview
# just deploy stage               # Actually deploy
```

---

## Idempotent Operations

```just
# Safe to run multiple times
setup:
    #!/usr/bin/env bash
    set -euo pipefail

    # Only create if missing
    [ -d ".venv" ] || uv venv

    # Always sync (idempotent)
    uv sync

    # Only init if needed
    [ -f ".env" ] || cp .env.example .env
```

---

## Guard Composition

### Layered Guards

```just
# Most restrictive first
deploy:prod: \
    _check_deploy_env \
    (_require "aws") \
    (_require_file "dist/app.zip") \
    (_confirm "Deploy to PRODUCTION?")

    ./scripts/deploy.sh prod

[private]
_check_deploy_env:
    @just _require_env AWS_PROFILE
    @just _require_env AWS_REGION
    @just _require_env DEPLOY_ROLE
```

### Guard Order

1. Environment variables (fast, no I/O)
2. Tools/commands (fast check)
3. Files/artifacts (filesystem I/O)
4. User confirmation (interactive, always last)

---

## Best Practices

### Do: Fail Fast

```just
# Check all requirements before starting work
build: (_require "uv") (_require_file "pyproject.toml")
    uv build
```

### Do: Provide Clear Error Messages

```just
[private]
_require_env var:
    @[ -n "${{{var}}:-}" ] || \
        (echo "ERROR: Environment variable '{{var}}' is not set" >&2 && \
         echo "Hint: Set it in .env or export {{var}}=value" >&2 && \
         exit 1)
```

### Do: Make Dangerous Operations Obvious

```just
# Name clearly indicates danger
db:DESTROY: (_confirm "DESTROY database? This cannot be undone!")
    dropdb myapp
```

### Avoid: Silent Failures

```just
# BAD: Fails silently
deploy:
    aws deploy ... 2>/dev/null || true

# GOOD: Explicit error handling
deploy:
    aws deploy ... || (echo "Deploy failed" >&2 && exit 1)
```
