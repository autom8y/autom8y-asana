# Justfile Structure & Organization

> File layout, naming conventions, and module organization

## File Layout

```
project-root/
├── Justfile              # Thin router: set policies + imports only
└── just/
    ├── _globals.just     # Project constants (APP, PY, UV, paths)
    ├── _helpers.just     # Utility recipes (_log, _require, _confirm)
    ├── _env.just         # Environment checks, bootstrap
    ├── dev.just          # Development lifecycle
    ├── test.just         # Test orchestration
    ├── fmt.just          # Format and lint
    ├── docker.just       # Container build/run
    ├── db.just           # Database operations
    ├── deploy.just       # Deployment recipes
    └── ci.just           # CI pipeline entrypoint
```

**Key principle**: The root `Justfile` is a thin router. All logic lives in `just/` modules.

---

## Root Justfile Pattern

The root Justfile should contain only configuration and imports:

```just
# Justfile
# Project task runner - thin router only

# === Settings ===
set dotenv-load := true
set export := true
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# === Imports ===
# Primitives (always load first)
import "just/_globals.just"
import "just/_helpers.just"
import "just/_env.just"

# Domain modules (load as needed)
import "just/dev.just"
import "just/test.just"
import "just/fmt.just"
import "just/docker.just"
import "just/db.just"
import "just/deploy.just"
import "just/ci.just"
```

---

## Module Naming Conventions

### Underscore Prefix (`_*.just`)

Files prefixed with `_` contain primitives - shared constants, utilities, or setup that other modules depend on:

- `_globals.just` - Project-wide constants
- `_helpers.just` - Utility recipes
- `_env.just` - Environment bootstrap

These are loaded first and provide foundational capabilities.

### Domain Modules (`{domain}.just`)

Each domain module focuses on a single concern:

| Module | Focus |
|--------|-------|
| `dev.just` | Development server, clean, watch |
| `test.just` | Unit, integration, coverage |
| `fmt.just` | Format, lint, type check |
| `docker.just` | Build, run, push containers |
| `db.just` | Migrate, reset, seed |
| `deploy.just` | Stage, prod deployment |
| `ci.just` | Pipeline composition |

---

## Import Organization

### Order Matters

```just
# 1. Primitives first (other modules may depend on these)
import "just/_globals.just"
import "just/_helpers.just"
import "just/_env.just"

# 2. Domain modules (alphabetical or by dependency)
import "just/dev.just"
import "just/fmt.just"
import "just/test.just"
# ... etc
```

### Conditional Imports

For optional modules, you can comment them out:

```just
# Core modules (always present)
import "just/dev.just"
import "just/test.just"
import "just/fmt.just"

# Optional modules (uncomment as needed)
# import "just/docker.just"
# import "just/db.just"
# import "just/deploy.just"
```

---

## Recipe Naming Within Modules

### Namespace Pattern

Recipes in domain modules use `domain:task` naming:

```just
# In test.just
test:unit:
    uv run pytest tests/unit

test:int:
    uv run pytest tests/integration

test:watch:
    watchexec -e py -- uv run pytest
```

### Meta-Task Pattern

Each domain typically has a default meta-task:

```just
# In test.just
# Default runs all tests
test: test:unit test:int

test:unit:
    uv run pytest tests/unit

test:int:
    uv run pytest tests/integration
```

### Helper Recipes

Helpers start with `_` and don't appear in `just --list`:

```just
# In _helpers.just
[private]
_log msg:
    @echo "==> {{msg}}"

[private]
_require cmd:
    @command -v {{cmd}} > /dev/null || (echo "Required: {{cmd}}" && exit 1)
```

---

## Module Template

New domain modules should follow this structure:

```just
# {domain}.just
# {Description of what this module handles}

# === Meta-task ===
{domain}: {domain}:primary {domain}:secondary
    @echo "{{domain}} complete"

# === Primary Tasks ===
{domain}:primary:
    # Primary task implementation

{domain}:secondary:
    # Secondary task implementation

# === Helpers (if needed) ===
[private]
_{domain}_helper:
    # Internal helper
```

---

## Scaling Guidelines

### When to Split a Module

Split a domain module if:
- It exceeds ~100 lines
- It has distinct sub-domains (e.g., `docker.just` -> `docker-build.just`, `docker-run.just`)
- Different team members own different parts

### When to Create a New Domain

Create a new domain module when:
- A distinct operational concern emerges
- Recipes would clutter an existing module
- The domain has its own lifecycle

### Directory Structure for Large Projects

For larger projects, you can nest:

```
just/
├── _globals.just
├── _helpers.just
├── dev.just
├── test/
│   ├── _test-helpers.just
│   ├── unit.just
│   └── integration.just
└── deploy/
    ├── stage.just
    └── prod.just
```

Import nested files:

```just
import "just/test/unit.just"
import "just/test/integration.just"
```
