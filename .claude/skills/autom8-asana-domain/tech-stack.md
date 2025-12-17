# Tech Stack

> Dependencies and tools for autom8_asana SDK

---

## Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **httpx** | >=0.25.0 | Async HTTP client for API calls |
| **pydantic** | >=2.0.0 | Type-safe data models, validation |
| **asana** | >=5.0.3 | Official Asana SDK (used selectively) |
| **polars** | >=0.20.0 | DataFrame operations for bulk data |

### Optional Dependencies

| Package | Version | Purpose | Install |
|---------|---------|---------|---------|
| **redis** | >=5.0.0 | Redis cache backend | `pip install autom8-asana[redis]` |
| **hiredis** | >=2.0.0 | C parser for Redis performance | Included with redis extra |

---

## Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | >=7.0.0 | Test framework |
| **pytest-asyncio** | >=0.23.0 | Async test support |
| **pytest-cov** | >=4.0.0 | Coverage reporting |
| **pytest-timeout** | >=2.2.0 | Test timeout enforcement |
| **mypy** | >=1.0.0 | Static type checking |
| **ruff** | >=0.1.0 | Linting and formatting |
| **respx** | >=0.20.0 | httpx mocking for tests |
| **fakeredis** | >=2.20.0 | Redis mocking for tests |
| **moto** | >=5.0.0 | AWS/S3 mocking for tests |
| **boto3** | >=1.34.0 | AWS SDK (required for moto) |

---

## Python Version

**Required**: Python 3.10+

**Why 3.10+** (not 3.12+):
- Match autom8 runtime constraints
- Stable async/await support
- Full type hint support (including `X | Y` union syntax)
- Match patterns available but not required

---

## Build System

| Component | Tool |
|-----------|------|
| Build backend | hatchling |
| Package layout | `src/autom8_asana` |
| Version | `0.1.0` (prototype) |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, dependencies, tool config |
| `pytest.ini` / `[tool.pytest.ini_options]` | Test configuration |
| `[tool.mypy]` | Type checking configuration |
| `[tool.ruff]` | Linting configuration |

---

## Key Tool Settings

### pytest

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"        # Auto-detect async tests
testpaths = ["tests"]
timeout = 60                 # Per-test timeout
markers = [
    "integration: marks tests requiring live API",
]
```

### mypy

```toml
[tool.mypy]
python_version = "3.10"
strict = true                # Enable all strict checks
warn_return_any = true
warn_unused_ignores = true
```

### ruff

```toml
[tool.ruff]
line-length = 88             # Match Black
target-version = "py310"
```

---

## Why These Choices

### httpx over requests/aiohttp

- Native async support
- Same API for sync and async
- Modern, well-maintained
- Excellent for testing with respx

### Pydantic v2 over v1

- Significant performance improvements
- Better type inference
- Cleaner validation API
- `model_dump()` / `model_validate()` naming

### Polars over Pandas

- Lazy evaluation for large datasets
- Better memory efficiency
- Native async support
- Faster for typical SDK operations

### hatchling over setuptools

- Modern, standards-compliant
- Simple configuration
- Reproducible builds
- Good src-layout support

---

## Common Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=autom8_asana --cov-report=html

# Type check
mypy src/autom8_asana

# Lint
ruff check src/

# Format
ruff format src/

# Build package
python -m build
```
