"""Deprecation utilities for backward-compatible struc() wrapper.

Per TDD-0009 Phase 5: Provides factory for creating deprecated struc() method
that emits warnings and converts Polars -> Pandas for legacy compatibility.

Note: Pandas is an optional dependency. If not installed, struc() will raise
ImportError with guidance on how to install it.
"""

from __future__ import annotations

import inspect
import warnings
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

import polars as pl

if TYPE_CHECKING:
    import pandas as pd

    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver


def _ensure_pandas() -> Any:
    """Ensure pandas is available, raising ImportError if not.

    Returns:
        The pandas module.

    Raises:
        ImportError: If pandas is not installed.
    """
    try:
        import pandas as pd
        return pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for the deprecated struc() method. "
            "Install it with: pip install pandas "
            "Or migrate to to_dataframe() which returns Polars DataFrames."
        ) from exc


def create_struc_wrapper(
    to_dataframe_method: Callable[..., pl.DataFrame],
    class_name: str,
    migration_url: str = "https://docs.autom8.io/migration/struc-to-dataframe",
) -> Callable[..., "pd.DataFrame"]:
    """Create deprecated struc() wrapper from to_dataframe() method.

    Per TDD-0009 Phase 5: Factory function that creates a backward-compatible
    struc() method that:
    1. Emits DeprecationWarning with migration URL
    2. Logs caller location for migration tracking
    3. Calls to_dataframe() internally
    4. Converts Polars DataFrame to Pandas for legacy code

    Args:
        to_dataframe_method: The to_dataframe() method to wrap.
        class_name: Name of the class (e.g., "Project", "Section").
        migration_url: URL with migration documentation.

    Returns:
        Wrapped struc() method that returns pandas DataFrame.

    Raises:
        ImportError: If pandas is not installed.

    Example:
        >>> # In Project class:
        >>> struc = create_struc_wrapper(to_dataframe, "Project")
    """

    @wraps(to_dataframe_method)
    def struc(
        self: Any,
        task_type: str = "*",
        sections: list[str] | None = None,
        resolver: "CustomFieldResolver | None" = None,
        cache_integration: "DataFrameCacheIntegration | None" = None,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> "pd.DataFrame":
        """[DEPRECATED] Generate pandas DataFrame from tasks.

        This method is deprecated. Use to_dataframe() instead.

        Per TDD-0009 Phase 5: Backward-compatible wrapper that returns
        pandas DataFrame instead of Polars.

        Args:
            task_type: Task type filter ("Unit", "Contact", "*" for base).
            sections: Optional list of section names to filter by.
            resolver: Optional custom field resolver for dynamic fields.
            cache_integration: Optional cache integration for struc caching.
            use_cache: Whether to use caching (default True).
            lazy: If True, force lazy evaluation. If False, force eager.

        Returns:
            Pandas DataFrame with extracted task data.

        Raises:
            ImportError: If pandas is not installed.

        .. deprecated:: 1.0.0
           Use :meth:`to_dataframe()` instead. struc() returns pandas
           DataFrames for backward compatibility, but to_dataframe()
           returns more efficient Polars DataFrames.
        """
        # Ensure pandas is available
        _ensure_pandas()

        # Get caller information for migration tracking
        frame = inspect.currentframe()
        caller_info = "unknown"
        if frame is not None and frame.f_back is not None:
            caller_frame = frame.f_back
            caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"

        # Emit deprecation warning
        warnings.warn(
            f"{class_name}.struc() is deprecated and will be removed in a future version. "
            f"Use {class_name}.to_dataframe() instead. "
            f"struc() returns pandas DataFrames; to_dataframe() returns Polars DataFrames. "
            f"Migration guide: {migration_url} "
            f"(called from {caller_info})",
            DeprecationWarning,
            stacklevel=2,
        )

        # Build kwargs based on what the underlying method supports
        kwargs: dict[str, Any] = {
            "task_type": task_type,
            "resolver": resolver,
            "cache_integration": cache_integration,
            "use_cache": use_cache,
            "lazy": lazy,
        }

        # Only include sections if it's a Project (has sections parameter)
        if sections is not None:
            kwargs["sections"] = sections

        # Call the underlying to_dataframe method
        polars_df = to_dataframe_method(self, **kwargs)

        # Convert Polars -> Pandas for backward compatibility
        return polars_df.to_pandas()

    return struc


def struc_project(
    self: Any,
    task_type: str = "*",
    sections: list[str] | None = None,
    resolver: "CustomFieldResolver | None" = None,
    cache_integration: "DataFrameCacheIntegration | None" = None,
    use_cache: bool = True,
    lazy: bool | None = None,
) -> "pd.DataFrame":
    """[DEPRECATED] Generate pandas DataFrame from project tasks.

    This method is deprecated. Use to_dataframe() instead.

    Per TDD-0009 Phase 5: Backward-compatible wrapper that returns
    pandas DataFrame instead of Polars.

    Args:
        task_type: Task type filter ("Unit", "Contact", "*" for base).
        sections: Optional list of section names to filter by.
        resolver: Optional custom field resolver for dynamic fields.
        cache_integration: Optional cache integration for struc caching.
        use_cache: Whether to use caching (default True).
        lazy: If True, force lazy evaluation. If False, force eager.

    Returns:
        Pandas DataFrame with extracted task data.

    Raises:
        ImportError: If pandas is not installed.

    .. deprecated:: 1.0.0
       Use :meth:`to_dataframe()` instead. struc() returns pandas
       DataFrames for backward compatibility, but to_dataframe()
       returns more efficient Polars DataFrames.
    """
    # Ensure pandas is available
    _ensure_pandas()

    # Get caller information for migration tracking
    frame = inspect.currentframe()
    caller_info = "unknown"
    if frame is not None and frame.f_back is not None:
        caller_frame = frame.f_back
        caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"

    # Emit deprecation warning
    warnings.warn(
        "Project.struc() is deprecated and will be removed in a future version. "
        "Use Project.to_dataframe() instead. "
        "struc() returns pandas DataFrames; to_dataframe() returns Polars DataFrames. "
        "Migration guide: https://docs.autom8.io/migration/struc-to-dataframe "
        f"(called from {caller_info})",
        DeprecationWarning,
        stacklevel=2,
    )

    # Call the underlying to_dataframe method
    polars_df = self.to_dataframe(
        task_type=task_type,
        sections=sections,
        resolver=resolver,
        cache_integration=cache_integration,
        use_cache=use_cache,
        lazy=lazy,
    )

    # Convert Polars -> Pandas for backward compatibility
    return polars_df.to_pandas()


def struc_section(
    self: Any,
    task_type: str = "*",
    resolver: "CustomFieldResolver | None" = None,
    cache_integration: "DataFrameCacheIntegration | None" = None,
    use_cache: bool = True,
    lazy: bool | None = None,
) -> "pd.DataFrame":
    """[DEPRECATED] Generate pandas DataFrame from section tasks.

    This method is deprecated. Use to_dataframe() instead.

    Per TDD-0009 Phase 5: Backward-compatible wrapper that returns
    pandas DataFrame instead of Polars.

    Args:
        task_type: Task type filter ("Unit", "Contact", "*" for base).
        resolver: Optional custom field resolver for dynamic fields.
        cache_integration: Optional cache integration for struc caching.
        use_cache: Whether to use caching (default True).
        lazy: If True, force lazy evaluation. If False, force eager.

    Returns:
        Pandas DataFrame with extracted task data.

    Raises:
        ImportError: If pandas is not installed.

    .. deprecated:: 1.0.0
       Use :meth:`to_dataframe()` instead. struc() returns pandas
       DataFrames for backward compatibility, but to_dataframe()
       returns more efficient Polars DataFrames.
    """
    # Ensure pandas is available
    _ensure_pandas()

    # Get caller information for migration tracking
    frame = inspect.currentframe()
    caller_info = "unknown"
    if frame is not None and frame.f_back is not None:
        caller_frame = frame.f_back
        caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"

    # Emit deprecation warning
    warnings.warn(
        "Section.struc() is deprecated and will be removed in a future version. "
        "Use Section.to_dataframe() instead. "
        "struc() returns pandas DataFrames; to_dataframe() returns Polars DataFrames. "
        "Migration guide: https://docs.autom8.io/migration/struc-to-dataframe "
        f"(called from {caller_info})",
        DeprecationWarning,
        stacklevel=2,
    )

    # Call the underlying to_dataframe method
    polars_df = self.to_dataframe(
        task_type=task_type,
        resolver=resolver,
        cache_integration=cache_integration,
        use_cache=use_cache,
        lazy=lazy,
    )

    # Convert Polars -> Pandas for backward compatibility
    return polars_df.to_pandas()
