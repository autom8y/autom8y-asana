---
name: justfile
description: "Task automation with just command runner. Use when: creating justfiles, writing task recipes, organizing project commands, setting up dev/test/build automation, CI task orchestration. Triggers: justfile, just, task runner, make alternative, project commands, dev tasks, build automation, ci recipes, task dependencies."
---

# Justfile Task Automation

> Modular, composable task runner patterns for project automation

## Decision Tree

### Should this be a just recipe or a script?

```
Is it a task the user will invoke directly?
├─ YES: Just recipe (with clear name)
└─ NO: Is it reusable logic > 10 lines?
       ├─ YES: Script in scripts/, just launches it
       └─ NO: Helper recipe with `_` prefix
```

### Which domain module should this go in?

```
What does the recipe do?
├─ Start dev server, clean artifacts → dev.just
├─ Run tests (unit, int, watch) → test.just
├─ Format or lint code → fmt.just
├─ Build/run containers → docker.just
├─ Database operations → db.just
├─ Deploy to environments → deploy.just
├─ CI pipeline steps → ci.just
├─ Shared across domains → _helpers.just
└─ Project constants → _globals.just
```

### Primitive vs task?

```
Does it define reusable values or utilities?
├─ YES: Put in _globals.just or _helpers.just
└─ NO: Does it compose other recipes?
       ├─ YES: Meta-task (e.g., `lint` calls `lint:ruff`, `lint:mypy`)
       └─ NO: Leaf task in appropriate domain module
```

---

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

- [standards](../standards/SKILL.md) - Repository structure, where just/ directory goes
- [10x-workflow](../10x-workflow/SKILL.md) - Just as execution layer for session commands
- [documentation](../documentation/SKILL.md) - Document task runner decisions in TDD/ADRs
