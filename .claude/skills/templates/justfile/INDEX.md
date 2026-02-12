---
name: justfile
description: "Justfile task automation patterns. Use when: creating or editing justfiles, designing task runner recipes, setting up build automation. Triggers: justfile, just, task runner, make alternative, build automation, ci recipes, task dependencies."
---

# Justfile Task Automation

> Modular, composable task runner patterns for project automation

## Naming Conventions

### Recipe Names

| Pattern | Example | Use |
|---------|---------|-----|
| `domain:task` | `test:unit`, `docker:build` | Standard task naming |
| `_helper` | `_log`, `_require` | Internal helpers (not listed) |
| `domain` (no suffix) | `test`, `lint`, `build` | Meta-task calling subtasks |

### File Names

| Pattern | Purpose |
|---------|---------|
| `Justfile` | Root entry point (thin router) |
| `_globals.just` | Constants, paths, env variables |
| `_helpers.just` | Utility recipes |
| `_env.just` | Environment bootstrap/checks |
| `{domain}.just` | Domain-specific recipes |

---

## Quick Reference

### Root Justfile Pattern

```just
# Justfile - thin router only
set dotenv-load := true
set export := true
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

import "just/_globals.just"
import "just/_helpers.just"
import "just/_env.just"
import "just/dev.just"
import "just/test.just"
import "just/fmt.just"
```

### Common Recipe Patterns

| Pattern | Example |
|---------|---------|
| Simple command | `test: uv run pytest` |
| With dependency | `build: lint test` |
| With args | `test file="": uv run pytest {{file}}` |
| Meta-task | `lint: lint:ruff lint:mypy` |
| Env-aware | `deploy env: _require_env env` |
| Confirmed | `db:reset: (_confirm "Reset database?")` |

### Variable Interpolation

```just
# In _globals.just
APP := "myapp"
PY := "uv run python"

# In recipes
build: {{PY}} -m build
run: docker run {{APP}}:latest
```

---

## Structure Principles

1. **Thin root** - Justfile contains only `set` policies and `import` statements
2. **Primitives in `_*.just`** - Constants, helpers, env checks in underscore-prefixed files
3. **Domain isolation** - Each domain in its own file, no cross-dependencies
4. **Composition over duplication** - Recipes call other recipes
5. **CI parity** - `just ci` runs same checks as CI pipeline
6. **10-line rule** - Recipes > 10 lines move to scripts/

---

## Progressive Disclosure

### Structure & Organization
- [structure.md](structure.md) - File layout, module organization, import patterns

### Patterns
- [patterns/primitives.md](patterns/primitives.md) - _globals, _helpers, _env patterns
- [patterns/composition.md](patterns/composition.md) - Meta-tasks, chaining, dependencies
- [patterns/safety.md](patterns/safety.md) - Confirmations, env checks, guards

### Domain Recipes
- [domains/dev.md](domains/dev.md) - Development lifecycle
- [domains/test.md](domains/test.md) - Test orchestration
- [domains/fmt.md](domains/fmt.md) - Format and lint
- [domains/docker.md](domains/docker.md) - Container operations
- [domains/db.md](domains/db.md) - Database operations
- [domains/deploy.md](domains/deploy.md) - Deployment patterns
- [domains/ci.md](domains/ci.md) - CI pipeline

### Templates
- [templates/Justfile.template](templates/Justfile.template) - Root thin router
- [templates/_globals.just.template](templates/_globals.just.template) - Project constants
- [templates/_helpers.just.template](templates/_helpers.just.template) - Utility recipes
- [templates/domain.just.template](templates/domain.just.template) - Generic domain starter

---

## Cross-Skill Integration

- [standards](../../guidance/standards/INDEX.lego.md) - Repository structure, where just/ directory goes
- [documentation](../documentation/INDEX.lego.md) - Document task runner decisions in TDD/ADRs
