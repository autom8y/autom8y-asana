# ADR-SDK-005: Pydantic Settings Standards

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: SDK Team
- **Related**: ADR-0014 (Example Scripts Env Config), ADR-0123 (Cache Provider Selection)

## Context

The autom8_asana SDK previously used scattered `os.environ.get()` calls throughout the codebase for configuration. This pattern led to:

1. **Inconsistent validation**: Some env vars were validated, others silently accepted invalid values
2. **Type coercion scattered**: Boolean parsing (`"true"`, `"1"`, `"yes"`) duplicated across modules
3. **No startup validation**: Invalid configuration discovered at runtime, not initialization
4. **Testing friction**: Tests required manual env var manipulation with no cleanup guarantees
5. **Documentation drift**: Env var names documented separately from usage

The SDK has migrated to a unified Pydantic Settings architecture in `src/autom8_asana/settings.py`. This ADR documents the standards and patterns established during that migration.

**Forces at play:**
- SDK-owned configuration should be type-safe and validated
- Dynamic configuration (ASANA_PROJECT_*) patterns cannot use Pydantic Settings
- AWS/ECS-injected variables are not SDK-controlled
- Test isolation requires deterministic settings reset
- Backward compatibility with existing env var names

## Decision

We establish the following standards for configuration management in the autom8_asana SDK:

### 1. When to Use Pydantic Settings

**Use Pydantic Settings when:**
- Environment variable names are fixed and known at compile time
- Values require validation or type coercion
- Configuration is SDK-owned (we define the contract)
- Configuration applies globally across the SDK

**Use direct `os.environ.get()` when:**
- Environment variables follow a dynamic pattern (e.g., `ASANA_PROJECT_{name}`)
- Configuration is injected by runtime environment (AWS ECS, Kubernetes)
- Values are passed through without SDK interpretation
- Configuration is module-specific and isolated

### 2. Composite Settings Architecture

Settings are organized using a **composite pattern**:

```python
class Settings(BaseSettings):
    asana: AsanaSettings = Field(default_factory=AsanaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    env: EnvironmentSettings = Field(default_factory=EnvironmentSettings)
```

Each subsetting class:
- Uses `env_prefix` for namespace isolation (e.g., `ASANA_`, `REDIS_`)
- Handles validation for its domain
- Can be instantiated independently for testing

### 3. Naming Conventions

**Settings Classes:**
- Pattern: `{Domain}Settings`
- Examples: `AsanaSettings`, `CacheSettings`, `RedisSettings`, `EnvironmentSettings`
- Each class owns a logical configuration domain

**Environment Variables:**
- Pattern: `{PREFIX}_{FIELD_NAME}` in `SCREAMING_SNAKE_CASE`
- Prefix defined by `env_prefix` in `SettingsConfigDict`
- Examples: `ASANA_PAT`, `ASANA_CACHE_ENABLED`, `REDIS_HOST`

**Accessor Functions:**
- `get_settings()` - Returns singleton Settings instance
- `reset_settings()` - Clears singleton for testing

### 4. Deprecation Pattern for Legacy Environment Variables

Use `@field_validator` with `warnings.warn()` for deprecated fields:

```python
@field_validator("deprecated_field", mode="before")
@classmethod
def handle_deprecated_field(cls, v: str | None) -> str | None:
    import warnings
    if v is not None:
        warnings.warn(
            "ASANA_DEPRECATED_FIELD is deprecated, use ASANA_NEW_FIELD instead",
            DeprecationWarning,
            stacklevel=2
        )
    return v
```

For renamed variables, check both old and new in the validator and emit a warning if the old name is used.

### 5. Dynamic Environment Variable Handling

Variables following patterns like `ASANA_PROJECT_{name}` cannot use Pydantic Settings because field names must be known at class definition time.

Pattern for dynamic env vars:

```python
def get_project_gid(project_name: str) -> str | None:
    """Get project GID from dynamic env var."""
    env_name = f"ASANA_PROJECT_{project_name.upper().replace('-', '_')}"
    return os.environ.get(env_name)

def get_all_project_gids() -> dict[str, str]:
    """Discover all ASANA_PROJECT_* env vars."""
    return {
        key[14:].lower(): value  # Strip ASANA_PROJECT_ prefix
        for key, value in os.environ.items()
        if key.startswith("ASANA_PROJECT_")
    }
```

### 6. Startup Validation Strategy

**Fail-fast for required configuration:**
- Use Pydantic's required fields (no default) for must-have config
- Validation errors surface at first `get_settings()` call
- Clear error messages identify which env vars are missing

**Graceful degradation for optional configuration:**
- Use `Field(default=...)` for configuration with sensible defaults
- Use `@field_validator` with fallback logic for backward compatibility
- Log warnings for invalid optional values, use defaults

**Strict mode option:**
- `ASANA_STRICT_CONFIG=true` enables strict validation
- Invalid values raise errors instead of falling back to defaults
- Recommended for production deployments

### 7. Test Isolation Pattern

**In `conftest.py`:**

```python
import pytest
from autom8_asana.settings import reset_settings

@pytest.fixture(autouse=True)
def reset_settings_fixture():
    """Ensure clean settings state for each test."""
    reset_settings()
    yield
    reset_settings()
```

**For tests needing specific configuration:**

```python
def test_with_custom_config(monkeypatch, reset_settings_fixture):
    monkeypatch.setenv("ASANA_CACHE_ENABLED", "false")
    reset_settings()  # Force re-read after env change

    settings = get_settings()
    assert settings.cache.enabled is False
```

**Key principles:**
- Always reset before AND after tests (fixture handles this)
- Use `monkeypatch.setenv()` for test-specific values (auto-cleanup)
- Call `reset_settings()` after env changes to force re-read
- Never rely on global settings state between tests

## Rationale

### Why Composite Pattern Over Flat Settings?

| Criterion | Flat Settings | **Composite Pattern** |
|-----------|--------------|----------------------|
| Namespace clarity | Poor (all fields mixed) | **Good** (domain grouping) |
| Independent testing | Poor | **Good** (test subsettings alone) |
| Documentation | Medium (long list) | **Good** (grouped by concern) |
| Type hints | Same | Same |
| Runtime overhead | Slightly less | **Negligible** |

The composite pattern groups related configuration logically. `settings.cache.enabled` is clearer than `settings.cache_enabled` when there are many cache-related fields.

### Why Singleton with Reset Over Dependency Injection?

The singleton pattern with `reset_settings()` was chosen because:

1. **SDK simplicity**: Users call `get_settings()` without managing instances
2. **Consistent view**: All code sees the same configuration
3. **Test compatibility**: `reset_settings()` provides clean isolation
4. **Backward compatible**: Can be replaced with DI later if needed

Dependency injection would require threading settings through the entire call stack, which is invasive for an SDK designed for ergonomic use.

### Why Warn Instead of Fail for Invalid Optional Values?

Per the SDK's philosophy of graceful degradation:

- Invalid `ASANA_CACHE_TTL_DEFAULT="foo"` logs warning, uses 300
- Invalid `REDIS_PORT="invalid"` would fail (required for Redis)
- Missing `REDIS_HOST` disables Redis cache, doesn't crash

This balances robustness (don't crash on typos) with visibility (warnings alert operators).

## Alternatives Considered

### Alternative 1: Direct os.environ Throughout

- **Description**: Continue using `os.environ.get()` calls at point of use
- **Pros**: No abstraction, explicit, zero learning curve
- **Cons**: No validation, duplicated parsing logic, no test isolation
- **Why not chosen**: Led to bugs from inconsistent validation and type coercion

### Alternative 2: Configuration File (YAML/TOML)

- **Description**: Load configuration from `.asana.yaml` or `pyproject.toml`
- **Pros**: Rich structure, checked into source control
- **Cons**: File I/O at startup, new dependency pattern, 12-factor violation
- **Why not chosen**: Environment variables are the standard for deployment configuration

### Alternative 3: Single Flat Settings Class

- **Description**: One `Settings` class with all fields
- **Pros**: Simpler structure, single validation point
- **Cons**: No logical grouping, unwieldy with many fields, poor testability
- **Why not chosen**: 20+ settings benefit from domain grouping

### Alternative 4: Per-Module Settings Instances

- **Description**: Each module (cache, client, etc.) has its own settings class
- **Pros**: Module independence, can evolve separately
- **Cons**: No unified view, coordination burden, potential conflicts
- **Why not chosen**: SDK needs consistent global configuration view

## Consequences

### Positive

- **Type safety**: All configuration is typed and validated at startup
- **Centralized documentation**: Settings module is the source of truth for env vars
- **Test isolation**: `reset_settings()` fixture ensures clean state
- **IDE support**: Autocompletion for `settings.cache.enabled`
- **Consistent parsing**: Boolean, integer, string parsing handled once
- **Startup validation**: Misconfigurations fail fast with clear messages
- **Backward compatible**: Existing env var names unchanged

### Negative

- **Learning curve**: Developers must understand Pydantic Settings
- **Dynamic limitation**: Pattern-based env vars still use `os.environ`
- **Module dependency**: All modules that need config import settings module
- **Initialization order**: Settings must be resettable for test isolation

### Neutral

- **Documentation requirement**: Settings module docstrings must be maintained
- **Deprecation ceremony**: Removing env vars requires deprecation cycle
- **Singleton pattern**: Standard pattern, but limits certain DI patterns

## Compliance

How do we ensure this decision is followed?

1. **Code review checklist**: New env vars must use Settings, not direct os.environ
2. **Grep for os.environ**: Periodic audit for unauthorized direct access
3. **Test coverage**: Settings module has comprehensive tests
4. **Documentation**: Settings docstrings kept in sync with usage
5. **Linting rule**: Consider custom rule flagging `os.environ.get()` in non-settings modules

## Implementation Reference

The canonical implementation is in `src/autom8_asana/settings.py`. Key patterns:

```python
# Composite settings container
class Settings(BaseSettings):
    asana: AsanaSettings = Field(default_factory=AsanaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    env: EnvironmentSettings = Field(default_factory=EnvironmentSettings)

# Subsetting with env_prefix
class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASANA_CACHE_",
        extra="ignore",
        case_sensitive=False,
    )
    enabled: bool = Field(default=True)
    provider: str | None = Field(default=None)
    ttl_default: int = Field(default=300)

# Singleton pattern
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reset_settings() -> None:
    global _settings
    _settings = None
```

## Related Decisions

- **ADR-0014**: Environment Variable Configuration for Example Scripts
- **ADR-0123**: Cache Provider Selection Strategy (uses these settings)
- **ADR-0124**: Client Cache Pattern (consumes settings)
