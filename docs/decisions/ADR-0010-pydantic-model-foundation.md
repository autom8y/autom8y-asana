# ADR-0010: Pydantic Model Foundation

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0005, ADR-SDK-005
- **Related**: reference/DATA-MODEL.md

## Context

The autom8_asana SDK needs robust model validation for Asana API resources while maintaining forward compatibility with Asana's evolving API. The SDK must handle:

1. **API Evolution**: Asana regularly adds new fields to API responses without notice
2. **Configuration Management**: SDK requires type-safe settings across multiple domains (Asana, cache, Redis, environment)
3. **Field Aliases**: API uses both camelCase and snake_case naming conventions
4. **Production Resilience**: Minor API changes should not cause production outages

Without proper configuration, the SDK would break when:
- Asana adds experimental or permission-based fields
- Environment variables contain invalid values
- Field names change between API versions

## Decision

Use Pydantic v2 as the foundational model layer with **`extra="ignore"` for forward compatibility** and **composite settings architecture for configuration management**.

### Model Configuration Standards

All Asana API resource models inherit from `AsanaResource` with standardized configuration:

```python
from pydantic import BaseModel, ConfigDict

class AsanaResource(BaseModel):
    model_config = ConfigDict(
        extra="ignore",           # Forward compatibility - new API fields don't break
        populate_by_name=True,    # Support field aliases (API vs Python names)
        str_strip_whitespace=True # Normalize string inputs
    )

    gid: str
    resource_type: str
```

### Settings Architecture

Configuration uses composite Pydantic Settings with domain-specific subsettings:

```python
class Settings(BaseSettings):
    asana: AsanaSettings = Field(default_factory=AsanaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    env: EnvironmentSettings = Field(default_factory=EnvironmentSettings)

class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASANA_CACHE_",
        extra="ignore",
        case_sensitive=False,
    )
    enabled: bool = Field(default=True)
    provider: str | None = Field(default=None)
    ttl_default: int = Field(default=300)

# Singleton pattern with reset for test isolation
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

### Configuration Standards

**Use Pydantic Settings when:**
- Environment variable names are fixed and known at compile time
- Values require validation or type coercion
- Configuration is SDK-owned (we define the contract)
- Configuration applies globally across the SDK

**Use direct `os.environ.get()` when:**
- Environment variables follow dynamic patterns (e.g., `ASANA_PROJECT_{name}`)
- Configuration is injected by runtime environment (AWS ECS, Kubernetes)
- Values are passed through without SDK interpretation

## Rationale

### Why `extra="ignore"`?

Provides optimal balance for an API client library:

1. **Forward compatibility**: When Asana adds new fields, SDK continues working without upgrades
2. **Graceful degradation**: Missing model fields mean that feature isn't supported yet, not that SDK is broken
3. **Clean models**: Only expose fields explicitly modeled and tested - no surprise attributes
4. **Production safety**: Minor API changes from Asana won't cause production outages

Example scenario:
```python
api_response = {
    "gid": "123",
    "resource_type": "task",
    "name": "My Task",
    "new_experimental_field": "some value",  # Unknown to model
}

task = Task.model_validate(api_response)  # Succeeds
# task.new_experimental_field raises AttributeError
# But model creation didn't fail
```

### Why Composite Settings Architecture?

| Criterion | Flat Settings | Composite Pattern |
|-----------|--------------|-------------------|
| Namespace clarity | Poor (all fields mixed) | Good (domain grouping) |
| Independent testing | Poor | Good (test subsettings alone) |
| Documentation | Medium (long list) | Good (grouped by concern) |
| Type hints | Same | Same |

The composite pattern groups related configuration logically: `settings.cache.enabled` is clearer than `settings.cache_enabled` when there are many cache-related fields.

### Why Singleton with Reset?

The singleton pattern with `reset_settings()` provides:

1. **SDK simplicity**: Users call `get_settings()` without managing instances
2. **Consistent view**: All code sees the same configuration
3. **Test compatibility**: `reset_settings()` provides clean isolation
4. **Backward compatible**: Can be replaced with dependency injection later if needed

## Alternatives Considered

### Alternative 1: `extra="forbid"` (Strict Mode)

- **Description**: Raise `ValidationError` if response contains unknown fields
- **Pros**: Immediately aware of API changes; forces model updates to stay current
- **Cons**: SDK breaks when Asana adds any new field; users must upgrade immediately; production outages from benign API additions
- **Why not chosen**: Too fragile for a client library - API additions shouldn't break consumers

### Alternative 2: `extra="allow"` (Permissive Mode)

- **Description**: Store unknown fields in `__pydantic_extra__` dict
- **Pros**: No data loss; can access unknown fields via `model.__pydantic_extra__["field"]`
- **Cons**: Inconsistent access patterns (known vs unknown fields); extra memory; serialization complexity; type safety lost for extra fields
- **Why not chosen**: Mixed access patterns are confusing - if we need a field, model it explicitly

### Alternative 3: Configuration File (YAML/TOML)

- **Description**: Load configuration from `.asana.yaml` or `pyproject.toml`
- **Pros**: Rich structure; checked into source control
- **Cons**: File I/O at startup; new dependency pattern; violates 12-factor app principles
- **Why not chosen**: Environment variables are the standard for deployment configuration

### Alternative 4: Single Flat Settings Class

- **Description**: One `Settings` class with all fields
- **Pros**: Simpler structure; single validation point
- **Cons**: No logical grouping; unwieldy with 20+ fields; poor testability
- **Why not chosen**: Composite pattern provides better organization and testability

## Consequences

### Positive

- **Resilient**: SDK survives API additions without code changes
- **Type safety**: All configuration is typed and validated at startup
- **Simple**: One behavior to understand and document for model validation
- **Safe**: Production systems don't break from new API fields
- **Clean**: Models only expose explicitly defined fields
- **Centralized documentation**: Settings module is source of truth for environment variables
- **Test isolation**: `reset_settings()` fixture ensures clean state
- **IDE support**: Autocompletion for `settings.cache.enabled`
- **Startup validation**: Misconfigurations fail fast with clear messages

### Negative

- **Silent data loss**: Unknown fields are discarded (but we don't need them)
- **Delayed awareness**: May not notice new useful API fields immediately
- **Incomplete representation**: Model doesn't capture full API response
- **Learning curve**: Developers must understand Pydantic Settings
- **Dynamic limitation**: Pattern-based env vars still use `os.environ`
- **Singleton pattern**: Limits certain dependency injection patterns

### Neutral

- **Explicit modeling**: Must add new fields to models to use them
- **Version awareness**: Should periodically review API changes and update models
- **Documentation requirement**: Settings module docstrings must be maintained
- **Deprecation ceremony**: Removing env vars requires deprecation cycle

## Compliance

### Model Validation

1. **Base class enforcement**: All models inherit from `AsanaResource` with `extra="ignore"`
2. **Code review**: Check that models don't override to `extra="forbid"`
3. **Test coverage**: Tests verify models handle unknown fields gracefully
4. **API drift detection**: Periodic script compares models to API responses, logs unknown fields

### Settings Management

1. **Code review checklist**: New env vars must use Settings, not direct `os.environ`
2. **Grep audit**: Periodic audit for unauthorized direct access
3. **Test coverage**: Settings module has comprehensive tests
4. **Linting rule**: Consider custom rule flagging `os.environ.get()` in non-settings modules

### Test Isolation Pattern

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
