# Tech Stack & Tooling Preferences

> Opinionated defaults for technology choices. These are strongly held preferences, loosely held—override when requirements demand it, but document why in an ADR.

---

## Philosophy

**Boring technology for infrastructure, modern tools for productivity.** We don't chase shiny things, but we don't cling to legacy tools when better options exist. The goal is fast iteration with production stability.

**Explicit dependencies, reproducible builds.** Anyone should be able to clone the repo and run the project with minimal setup. Lock files are committed. Versions are pinned.

**Type safety is not optional.** Static analysis catches bugs before runtime. Types are documentation that doesn't go stale.

---

## Python Stack

### Runtime & Version

| Choice | Tool | Why |
|--------|------|-----|
| Python Version | **3.12+** | Performance improvements, better typing, f-string improvements |
| Version Management | **pyenv** or **mise** | Multiple Python versions per project |

### Project Management

| Choice | Tool | Why |
|--------|------|-----|
| Package Manager | **uv** | 10-100x faster than pip/poetry, drop-in replacement, handles venvs |
| Lock File | `uv.lock` | Reproducible builds, committed to repo |
| Pyproject | `pyproject.toml` | Single source of truth for project config |

```bash
# Initialize new project
uv init my-project
cd my-project

# Add dependencies
uv add fastapi pydantic sqlmodel

# Add dev dependencies
uv add --dev pytest pytest-asyncio ruff mypy

# Run commands in venv
uv run python main.py
uv run pytest
```

### Web Framework

| Choice | Tool | Why |
|--------|------|-----|
| API Framework | **FastAPI** | Async-native, auto OpenAPI docs, Pydantic integration |
| ASGI Server | **uvicorn** | Fast, production-ready, good defaults |
| Production Server | **gunicorn + uvicorn workers** | Process management, graceful restarts |

### Data Validation & Serialization

| Choice | Tool | Why |
|--------|------|-----|
| Validation | **Pydantic v2** | Fast, intuitive, great error messages |
| Settings | **pydantic-settings** | Type-safe env var loading |
| ORM | **SQLModel** | Pydantic + SQLAlchemy, single model definition |
| Raw SQL | **asyncpg** (Postgres) | When ORM is overkill, raw performance |

### Data Processing

| Choice | Tool | Why |
|--------|------|-----|
| DataFrames | **Polars** | Faster than pandas, better API, lazy evaluation |
| Legacy/Interop | pandas (when required) | Some libraries still need it |

```python
# Prefer Polars
import polars as pl

df = pl.read_csv("data.csv")
result = (
    df.lazy()
    .filter(pl.col("status") == "active")
    .group_by("category")
    .agg(pl.col("amount").sum())
    .collect()
)
```

### Async

| Choice | Tool | Why |
|--------|------|-----|
| Async Runtime | **asyncio** (stdlib) | Standard, well-supported |
| Async Utilities | **anyio** | Backend-agnostic, better primitives than raw asyncio |
| HTTP Client | **httpx** | Async-native, requests-like API |

### Type Checking & Linting

| Choice | Tool | Why |
|--------|------|-----|
| Type Checker | **mypy** (strict mode) | Catches bugs, mature ecosystem |
| Linter + Formatter | **Ruff** | Replaces flake8/isort/black, 100x faster |
| Pre-commit | **pre-commit** | Automated quality gates |

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
disallow_untyped_defs = true
```

### Testing

| Choice | Tool | Why |
|--------|------|-----|
| Test Framework | **pytest** | Industry standard, great plugins |
| Async Testing | **pytest-asyncio** | Async test support |
| Coverage | **pytest-cov** | Coverage reporting |
| Factories | **factory_boy** or **polyfactory** | Test data generation |
| Mocking | **pytest-mock** | Clean mock interface |
| Benchmarks | **pytest-benchmark** | Performance regression detection |

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Specific markers
uv run pytest -m "not slow"
```

### Observability

| Choice | Tool | Why |
|--------|------|-----|
| Logging | **structlog** | Structured JSON logging, great DX |
| Metrics | **prometheus-client** | Industry standard, easy to expose |
| Tracing | **opentelemetry** | Vendor-neutral distributed tracing |

---

## Go Stack

### Version & Management

| Choice | Tool | Why |
|--------|------|-----|
| Go Version | **1.22+** | Range-over-func, better tooling |
| Version Management | **mise** or **goenv** | Multiple Go versions |

### Project Structure

```
/cmd
    /myapp          # Main applications
        main.go
/internal           # Private application code
    /domain         # Business logic
    /handlers       # HTTP/gRPC handlers
    /repository     # Data access
/pkg                # Public library code (if any)
/scripts            # Build/deploy scripts
go.mod
go.sum
```

### Web & API

| Choice | Tool | Why |
|--------|------|-----|
| HTTP Router | **chi** or **stdlib** | chi for features, stdlib (1.22+) for simplicity |
| Validation | **go-playground/validator** | Struct tag validation |
| Config | **envconfig** or **viper** | Environment-based config |

### Database Tooling

| Choice | Tool | Why |
|--------|------|-----|
| SQL Driver | **pgx** | Best PostgreSQL driver |
| Query Builder | **sqlc** | Generate type-safe code from SQL |
| Migrations | **goose** | Simple, SQL-based migrations |

### Testing

| Choice | Tool | Why |
|--------|------|-----|
| Testing | **stdlib testing** | Built-in is excellent |
| Assertions | **testify** (optional) | If you want assertions |
| Mocking | **mockery** | Generate mocks from interfaces |

### Tooling

| Choice | Tool | Why |
|--------|------|-----|
| Linting | **golangci-lint** | Aggregates all linters |
| Formatting | **gofmt** / **goimports** | Standard formatting |

---

## Database

### Primary Database

| Choice | Tool | Why |
|--------|------|-----|
| OLTP Database | **PostgreSQL 16+** | Reliability, features, JSON support |
| Connection Pool | **PgBouncer** (production) | Connection management at scale |

### Migrations

| Choice | Tool | Why |
|--------|------|-----|
| Python | **alembic** | SQLAlchemy integration |
| Go | **goose** | Simple SQL migrations |
| Standalone | **dbmate** | Language-agnostic |

### Caching

| Choice | Tool | Why |
|--------|------|-----|
| Cache | **Redis** or **Valkey** | Fast, versatile, pub/sub |
| Client (Python) | **redis-py** with async | Native async support |

### Search (When Needed)

| Choice | Tool | Why |
|--------|------|-----|
| Full-text | **PostgreSQL FTS** | Good enough for most cases |
| Heavy Search | **Meilisearch** or **Typesense** | When Postgres FTS isn't enough |

---

## Infrastructure & DevOps

### Containerization

| Choice | Tool | Why |
|--------|------|-----|
| Containers | **Docker** | Industry standard |
| Local Dev | **Docker Compose** | Multi-service development |
| Build | **Multi-stage Dockerfiles** | Small, secure images |

```dockerfile
# Python example
FROM python:3.12-slim as builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src ./src
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "src.main"]
```

### Cloud

| Choice | Tool | Why |
|--------|------|-----|
| Cloud Provider | **AWS** (primary) | Mature, comprehensive |
| Auth | **AWS SSO / IAM Identity Center** | Centralized access |
| IaC | **Terraform** or **Pulumi** | Reproducible infrastructure |
| Secrets | **AWS Secrets Manager** or **1Password** | Never in code |

### CI/CD

| Choice | Tool | Why |
|--------|------|-----|
| CI/CD | **GitHub Actions** | Integrated, good free tier |
| Alternative | **GitLab CI** | If using GitLab |

### Local Development

| Choice | Tool | Why |
|--------|------|-----|
| Version Manager | **mise** | Manages Python, Go, Node, etc. in one tool |
| Env Files | **.env** (gitignored) | Local-only secrets |
| Secrets (dev) | **direnv** | Auto-load env per directory |

---

## API Design

### REST APIs

| Preference | Standard |
|------------|----------|
| Naming | `snake_case` for JSON fields |
| Versioning | URL-based: `/v1/`, `/v2/` |
| Pagination | Cursor-based for large sets, offset for small |
| Errors | RFC 7807 Problem Details |

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "Email format is invalid",
  "instance": "/users/123"
}
```

### Documentation

| Choice | Tool | Why |
|--------|------|-----|
| API Docs | **OpenAPI 3.1** | Auto-generated from FastAPI |
| Interactive | **Swagger UI** (built into FastAPI) | Try endpoints in browser |

---

## CLI Tools

### Building CLIs

| Choice | Tool | Why |
|--------|------|-----|
| Python CLI | **Typer** | FastAPI-like DX for CLIs |
| Go CLI | **cobra** | Industry standard |
| Rich Output | **Rich** (Python) | Beautiful terminal output |

### Developer Tools We Use

```bash
# Essential
brew install mise           # Version management for everything
brew install direnv         # Auto-load env vars
brew install jq             # JSON processing
brew install httpie         # Better curl

# Database
brew install pgcli          # Better psql

# Containers
brew install docker
brew install lazydocker     # TUI for Docker

# Git
brew install gh             # GitHub CLI
brew install lazygit        # TUI for Git
```

---

## When to Deviate

These are defaults, not mandates. Override when:

| Situation | Example | Action |
|-----------|---------|--------|
| Client requirement | "Must use MySQL" | Use MySQL, document in ADR |
| Legacy integration | Existing pandas pipeline | Keep pandas for that module |
| Performance critical | Need every microsecond | Drop to lower-level tools |
| Team expertise | Team knows Django well | Consider Django over FastAPI |
| Ecosystem constraint | Library requires X | Use X, isolate the dependency |

**Always**: Document deviations in an ADR explaining why.

---

## Version Pinning Strategy

### Lock Everything

```toml
# pyproject.toml - specify minimum versions
dependencies = [
    "fastapi>=0.109.0",
    "pydantic>=2.5.0",
]

# uv.lock - exact versions (committed)
# This file is auto-generated, always commit it
```

### Update Strategy

- **Weekly**: Run `uv lock --upgrade` and test
- **Monthly**: Review and update major versions
- **Quarterly**: Audit for security vulnerabilities

```bash
# Check for updates
uv pip list --outdated

# Update all
uv lock --upgrade

# Update specific package
uv add package@latest
```

---

## Quick Reference

### New Python Project

```bash
# Create project
uv init my-service
cd my-service

# Add core dependencies
uv add fastapi uvicorn pydantic pydantic-settings sqlmodel httpx structlog

# Add dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy pre-commit

# Setup pre-commit
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
EOF

pre-commit install
```

### New Go Project

```bash
# Create project
mkdir my-service && cd my-service
go mod init github.com/org/my-service

# Add dependencies
go get github.com/go-chi/chi/v5
go get github.com/jackc/pgx/v5
go get github.com/rs/zerolog

# Setup linting
cat > .golangci.yml << 'EOF'
linters:
  enable:
    - gofmt
    - govet
    - errcheck
    - staticcheck
    - gosimple
    - ineffassign
    - unused
EOF
```

---

## ADR Triggers

Create an ADR when deviating from this stack:

- Using a database other than PostgreSQL
- Using an ORM other than SQLModel
- Using pandas instead of Polars for new code
- Using a different web framework
- Adding significant new infrastructure
- Choosing a different cloud provider
- Using synchronous I/O in an async context (even if justified)
