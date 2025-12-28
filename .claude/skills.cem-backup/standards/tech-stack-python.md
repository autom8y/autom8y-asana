# Python Tech Stack

> Python ecosystem: runtime, frameworks, tooling, quality standards

**Core Policies**: See [tech-stack-core.md](tech-stack-core.md) for universal technology governance

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
