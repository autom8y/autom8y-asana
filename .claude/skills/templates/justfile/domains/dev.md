# Development Lifecycle Recipes

> Dev server, watch mode, clean artifacts

## Standard dev.just

```just
# dev.just
# Development lifecycle recipes

# === Meta-task ===
# Start development environment
dev: dev:serve

# === Development Server ===
dev:serve:
    @just _log "Starting development server..."
    {{UV}} run python -m {{APP}}

# With auto-reload
dev:watch:
    @just _log "Starting with auto-reload..."
    watchexec -e py -r -- {{UV}} run python -m {{APP}}

# === REPL ===
dev:shell:
    {{UV}} run python

dev:ipython:
    {{UV}} run ipython

# === Documentation ===
dev:docs:
    @just _log "Starting docs server..."
    {{UV}} run mkdocs serve

dev:docs:build:
    {{UV}} run mkdocs build
```

---

## Pattern Variations

### FastAPI/Uvicorn

```just
dev:serve port="8000":
    {{UV}} run uvicorn {{APP}}.main:app --reload --port {{port}}

dev:serve:prod port="8000":
    {{UV}} run uvicorn {{APP}}.main:app --host 0.0.0.0 --port {{port}}
```

### Flask

```just
dev:serve port="5000":
    FLASK_APP={{APP}} FLASK_DEBUG=1 {{UV}} run flask run -p {{port}}
```

### Django

```just
dev:serve port="8000":
    {{UV}} run python manage.py runserver {{port}}

dev:shell:
    {{UV}} run python manage.py shell_plus
```

### CLI Application

```just
# Run CLI with args
dev:run *args:
    {{UV}} run python -m {{APP}} {{args}}

# Interactive CLI testing
dev:cli:
    {{UV}} run python -m {{APP}} --help
```

---

## Clean Patterns

### Basic Clean

```just
clean:
    @just _log "Cleaning build artifacts..."
    rm -rf dist/ build/ *.egg-info/
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    rm -rf .coverage htmlcov/ coverage.xml
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @just _log "Clean complete"
```

### Deep Clean

```just
clean:deep: clean
    @just _log "Deep cleaning (includes venv)..."
    rm -rf .venv/
    @just _log "Deep clean complete"
```

### Node.js Clean

```just
clean:node:
    rm -rf node_modules/ .next/ .nuxt/ dist/
```

### Docker Clean

```just
clean:docker:
    docker system prune -f
    docker volume prune -f
```

---

## Watch Patterns

### Using watchexec

```just
# Watch Python files
dev:watch:
    watchexec -e py -r -- {{UV}} run python -m {{APP}}

# Watch with specific paths
dev:watch:src:
    watchexec -w src/ -e py -r -- {{UV}} run python -m {{APP}}

# Watch tests
test:watch:
    watchexec -e py -- {{UV}} run pytest -x
```

### Using nodemon (Node.js)

```just
dev:watch:
    npx nodemon --watch src --ext ts,js --exec "npm run start"
```

### Using air (Go)

```just
dev:watch:
    air
```

---

## Setup/Bootstrap Patterns

```just
# First-time setup
setup: (_require "uv")
    @just _log "Setting up development environment..."
    {{UV}} sync
    @just _log "Creating local config..."
    [ -f ".env" ] || cp .env.example .env
    @just _log "Setup complete. Run 'just dev' to start."

# Refresh dependencies
refresh:
    @just _log "Refreshing dependencies..."
    {{UV}} sync
    @just _log "Dependencies refreshed"

# Update dependencies
update:
    @just _log "Updating dependencies..."
    {{UV}} lock --upgrade
    {{UV}} sync
    @just _log "Dependencies updated"
```

---

## Environment Management

```just
# Show current environment
env:
    @echo "ENV: {{ENV}}"
    @echo "Python: $({{PY}} --version)"
    @echo "UV: $({{UV}} --version)"
    @echo "Working Directory: $(pwd)"

# Validate environment
env:check:
    @just _require uv
    @just _require git
    @[ -f "pyproject.toml" ] || (echo "Missing pyproject.toml" && exit 1)
    @[ -f ".env" ] || echo "WARN: No .env file (using defaults)"
    @just _log "Environment OK"
```

