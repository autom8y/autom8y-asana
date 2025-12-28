# SCOUT: YAML Schema Validation for Pipeline Configuration

## Problem Statement

Pipeline automation configuration needs robust validation for:
- Field whitelist schemas (devs own schema)
- Trigger condition definitions (Ops own values)
- Strict validation with helpful error messages
- Restart for reload (no hot-reload complexity)

**Key Constraints** (from stakeholder requirements):
- Devs own schema, Ops own values - clear separation
- Error message quality is critical (Ops must understand failures)
- IDE support beneficial for config authoring
- Environment variable substitution may be needed for secrets

## Options Evaluated

| Option | Maturity | Ecosystem | Fit | Risk |
|--------|----------|-----------|-----|------|
| **JSON Schema + jsonschema** | Excellent | Universal | Medium | Low |
| **JSON Schema + Pydantic v2** | Excellent | Strong | High | Low |
| **strictyaml** | Medium (2016+) | Moderate | Medium | Medium |
| **Cerberus** | High (2012+) | Moderate | Medium | Low |
| **marshmallow** | High (2013+) | Strong | Low | Low |

## Analysis

### Option 1: JSON Schema + jsonschema library

**Pros:**
- Universal schema standard (RFC draft)
- Language-agnostic schemas (reusable in other tools)
- Strong IDE support (VSCode, JetBrains)
- Extensive validation keywords
- 4K+ GitHub stars (jsonschema library)

**Cons:**
- Verbose schema definitions
- Error messages are technical, not user-friendly
- Two-step: parse YAML, then validate against schema
- No Python object binding (just validation)

**Fit Assessment:** Medium fit. Universal but verbose and poor error UX.

### Option 2: JSON Schema + Pydantic v2

**Pros:**
- **Already in use in this project** (pydantic>=2.0.0 in dependencies)
- Python-native schema definition via type hints
- Excellent error messages (customizable, user-friendly)
- Automatic JSON Schema generation for IDE support
- `model_validate()` does parse + validate in one step
- Environment variable substitution via pydantic-settings
- 22K+ GitHub stars, Anthropic-backed development

**Cons:**
- Schema authoring is Python code, not declarative YAML/JSON
- Slight overhead compared to pure jsonschema

**Fit Assessment:** Strong fit. Already a dependency, excellent error messages, IDE support via generated JSON Schema.

### Option 3: strictyaml

**Pros:**
- YAML-only (no accidental JSON or complex YAML features)
- Type coercion built-in
- Good error messages with line numbers
- Pythonic schema definition

**Cons:**
- Smaller ecosystem (1K GitHub stars)
- Schema is a separate concept from Python types
- No native env var substitution
- Less IDE tooling support

**Fit Assessment:** Medium fit. Novel approach but adds new concepts. Error messages are good but not better than Pydantic.

### Option 4: Cerberus

**Pros:**
- Dict-based schema definition
- Flexible validation rules
- Extensible with custom validators
- Good documentation

**Cons:**
- Less Pythonic than Pydantic
- No automatic type hints
- Error messages less polished
- Another validation library on top of existing Pydantic

**Fit Assessment:** Low fit. Adds dependency without clear advantage over Pydantic.

### Option 5: marshmallow

**Pros:**
- Mature, well-documented
- Serialization and deserialization
- Strong ORM integration

**Cons:**
- Focused on API serialization, not config validation
- Separate from Python type hints
- Pydantic has largely superseded it for config use cases

**Fit Assessment:** Low fit. Wrong tool for the job.

## Recommendation

**Verdict**: Adopt

**Choice**: Pydantic v2 with JSON Schema export

**Rationale:**

1. **Matches stakeholder requirements:**
   - Devs own schema: Pydantic models in Python, version-controlled
   - Ops own values: YAML config files parsed and validated at startup
   - Strict validation: Pydantic v2 strict mode rejects type coercion
   - Error message quality: Pydantic's validation errors are excellent
   - IDE support: Export JSON Schema for YAML plugins

2. **Already a dependency:**
   - `pydantic>=2.0.0` and `pydantic-settings>=2.0.0` in pyproject.toml
   - Zero new dependencies
   - Team already knows Pydantic patterns

3. **Implementation sketch:**

   ```python
   # schema.py - Devs own this file
   from pydantic import BaseModel, Field, field_validator
   from typing import Literal

   class TriggerCondition(BaseModel):
       """Trigger condition schema - devs own this, Ops fill in values."""
       name: str = Field(..., description="Human-readable trigger name")
       expression: str = Field(..., description="Boolean expression to evaluate")
       schedule: Literal["daily", "hourly"] = "daily"
       enabled: bool = True

       @field_validator("expression")
       @classmethod
       def validate_expression(cls, v: str) -> str:
           # Validate expression syntax at config load time
           from .expression import parse_expression
           parse_expression(v)  # Raises if invalid
           return v

   class FieldWhitelist(BaseModel):
       """Allowed fields for expression evaluation."""
       task_fields: list[str] = Field(default_factory=list)
       custom_fields: list[str] = Field(default_factory=list)

   class PipelineConfig(BaseModel):
       """Top-level pipeline configuration."""
       version: Literal["1.0"] = "1.0"
       whitelist: FieldWhitelist
       triggers: list[TriggerCondition]

       model_config = {"extra": "forbid", "strict": True}
   ```

   ```python
   # loader.py - Load YAML, validate with Pydantic
   import yaml
   from pathlib import Path
   from .schema import PipelineConfig

   def load_config(path: Path) -> PipelineConfig:
       """Load and validate pipeline configuration.

       Raises:
           pydantic.ValidationError: With detailed field-level errors
           yaml.YAMLError: If YAML syntax is invalid
       """
       with path.open() as f:
           raw = yaml.safe_load(f)

       return PipelineConfig.model_validate(raw)
   ```

   ```yaml
   # config/triggers.yaml - Ops own this file
   version: "1.0"
   whitelist:
     task_fields:
       - section
       - days_in_section
       - due_date
       - status
     custom_fields:
       - deal_value
       - priority

   triggers:
     - name: "Stale opportunities"
       expression: 'section == "ACTIVE" AND days_in_section > 30'
       schedule: daily
       enabled: true
   ```

4. **IDE support via JSON Schema export:**

   ```python
   # Generate schema for IDE support
   import json
   schema = PipelineConfig.model_json_schema()
   Path("config/pipeline-schema.json").write_text(json.dumps(schema, indent=2))
   ```

   Then in VSCode settings:
   ```json
   {
     "yaml.schemas": {
       "./config/pipeline-schema.json": "config/triggers.yaml"
     }
   }
   ```

5. **Environment variable substitution:**

   For secrets or environment-specific values, use pydantic-settings pattern:

   ```python
   from pydantic_settings import BaseSettings

   class RuntimeConfig(BaseSettings):
       asana_pat: str  # From ASANA_PAT env var
       config_path: Path = Path("config/triggers.yaml")
   ```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pydantic v2 breaking changes | Low | Medium | Pin version, monitor changelogs |
| YAML syntax errors unclear | Medium | Low | Use ruamel.yaml for better YAML errors if needed |
| Schema changes break existing configs | Medium | Medium | Version field, migration scripts |
| Complex validation logic bloats schema | Medium | Low | Separate validators module |

## Decision Summary

| Criterion | Pydantic v2 | strictyaml | jsonschema |
|-----------|-------------|------------|------------|
| Already a dependency | Yes | No | No |
| Error message quality | Excellent | Good | Poor |
| IDE support | Via export | Limited | Native |
| Python integration | Native | Separate | Separate |
| Env var substitution | pydantic-settings | Manual | Manual |
| Learning curve | None (already used) | Low | Low |

**Bottom line:** Use Pydantic v2. It is already a dependency, provides excellent error messages, and offers the cleanest separation of schema (Python code, version-controlled by devs) from values (YAML files, managed by Ops).

## Bonus: Validation at Startup

Per stakeholder requirement "restart for reload":

```python
# main.py
def main():
    config = load_config(Path("config/triggers.yaml"))  # Validates on load
    logger.info("config_loaded", trigger_count=len(config.triggers))

    # If we get here, config is valid
    run_scheduler(config)
```

No hot-reload, no complexity. Restart the service to pick up config changes.
