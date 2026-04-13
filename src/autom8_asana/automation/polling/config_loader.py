"""Configuration loader for polling-based automation rules.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Loads YAML configuration files with
environment variable substitution and Pydantic validation.

Key responsibilities:
- Load YAML from disk
- Substitute ${VAR_NAME} patterns with environment variables
- Validate against Pydantic schema (strict mode)
- Raise ConfigurationError with clear messages on failure

Example:
    from autom8_asana.automation.polling import ConfigurationLoader
    from autom8_asana.automation.polling.config_schema import AutomationRulesConfig

    config = ConfigurationLoader.load_from_file(
        "/etc/autom8_asana/rules.yaml",
        AutomationRulesConfig,
    )
    print(f"Loaded {len(config.rules)} rules")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from autom8_asana.errors import ConfigurationError

__all__ = ["ConfigurationLoader"]

# Type variable for generic Pydantic model return type
T = TypeVar("T", bound=BaseModel)

# Regex pattern for environment variable substitution
# Matches ${VAR_NAME} where VAR_NAME starts with a letter or underscore,
# followed by letters, digits, or underscores
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


class ConfigurationLoader:
    """Loads YAML rule configuration with validation.

    This class provides static methods for loading and validating YAML
    configuration files. It handles:

    - File reading with clear error messages
    - YAML parsing with syntax error handling
    - Environment variable substitution (${VAR_NAME} pattern)
    - Pydantic validation with strict mode

    All methods are static since this class is stateless.

    Example:
        config = ConfigurationLoader.load_from_file(
            "rules.yaml",
            AutomationRulesConfig,
        )
    """

    @staticmethod
    def load_from_file(
        file_path: str,
        config_schema: type[T],
    ) -> T:
        """Load and validate configuration from a YAML file.

        This method:
        1. Reads the YAML file from disk
        2. Parses YAML syntax
        3. Substitutes environment variables (${VAR_NAME})
        4. Validates against the Pydantic schema

        Args:
            file_path: Path to the YAML configuration file.
            config_schema: Pydantic v2 BaseModel class for validation.

        Returns:
            Validated configuration object of type config_schema.

        Raises:
            ConfigurationError: If file is missing, YAML is invalid,
                environment variables are missing, or schema validation fails.

        Example:
            config = ConfigurationLoader.load_from_file(
                "/etc/autom8_asana/rules.yaml",
                AutomationRulesConfig,
            )
        """
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigurationError(
                f"Failed to read configuration file {file_path}: {e}"
            ) from e

        # Parse YAML
        try:
            raw_yaml = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in config file: {e}") from e

        # Handle empty file
        if raw_yaml is None:
            raw_yaml = {}

        # Substitute environment variables
        substituted = ConfigurationLoader.substitute_env_vars(raw_yaml)

        # Validate with Pydantic
        try:
            return config_schema.model_validate(substituted)
        except ValidationError as e:
            # Format Pydantic errors for clarity
            error_messages = []
            for error in e.errors():
                loc = ".".join(str(loc_part) for loc_part in error["loc"])
                msg = error["msg"]
                error_messages.append(f"{loc}: {msg}")
            error_detail = "; ".join(error_messages)
            raise ConfigurationError(f"Config validation failed: {error_detail}") from e

    @staticmethod
    def substitute_env_vars(
        raw_yaml: dict[str, Any],
        _path: str = "",
    ) -> dict[str, Any]:
        """Recursively substitute ${VAR_NAME} patterns with environment variables.

        Walks through the configuration dictionary and replaces all ${VAR_NAME}
        patterns with the corresponding environment variable values.

        Args:
            raw_yaml: Raw parsed YAML dictionary.
            _path: Internal parameter for tracking config path during recursion.

        Returns:
            Dictionary with environment variables substituted.

        Raises:
            ConfigurationError: If an environment variable is not found.

        Example:
            raw = {"api_key": "${ASANA_API_TOKEN}"}
            substituted = ConfigurationLoader.substitute_env_vars(raw)
            # substituted = {"api_key": "actual_token_value"}
        """
        result: dict[str, Any] = ConfigurationLoader._substitute_recursive(
            raw_yaml, _path
        )
        return result

    @staticmethod
    def _substitute_recursive(
        value: Any,
        path: str,
    ) -> Any:
        """Recursively substitute environment variables in any value type.

        Handles:
        - Strings: substitute ${VAR_NAME} patterns
        - Dicts: recurse into values
        - Lists: recurse into items
        - Other types: return unchanged

        Args:
            value: Any value from the configuration.
            path: Current path in the configuration (for error messages).

        Returns:
            Value with environment variables substituted.

        Raises:
            ConfigurationError: If an environment variable is not found.
        """
        if isinstance(value, str):
            return ConfigurationLoader._substitute_string(value, path)
        elif isinstance(value, dict):
            return {
                k: ConfigurationLoader._substitute_recursive(
                    v, f"{path}.{k}" if path else k
                )
                for k, v in value.items()
            }
        elif isinstance(value, list):
            return [
                ConfigurationLoader._substitute_recursive(item, f"{path}[{i}]")
                for i, item in enumerate(value)
            ]
        else:
            # Numbers, booleans, None, etc. - return unchanged
            return value

    @staticmethod
    def _substitute_string(value: str, path: str) -> str:
        """Substitute environment variables in a string value.

        Finds all ${VAR_NAME} patterns and replaces them with the
        corresponding environment variable values.

        Args:
            value: String that may contain ${VAR_NAME} patterns.
            path: Current path in the configuration (for error messages).

        Returns:
            String with environment variables substituted.

        Raises:
            ConfigurationError: If an environment variable is not found.

        Example:
            result = ConfigurationLoader._substitute_string(
                "Bearer ${API_TOKEN}",
                "auth.token"
            )
            # result = "Bearer actual_token_value"
        """

        def replace_match(match: re.Match[str]) -> str:
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            if env_value is None:
                raise ConfigurationError(
                    f"Environment variable '{var_name}' not found in config path {path}"
                )
            return env_value

        return ENV_VAR_PATTERN.sub(replace_match, value)
