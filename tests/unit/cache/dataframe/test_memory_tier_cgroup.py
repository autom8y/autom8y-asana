"""Tests for container-aware memory detection in MemoryTier.

Validates cgroup v1/v2 detection, env var overrides, and fallback behavior
for _get_container_memory_bytes() and its integration with _get_max_bytes().
"""

from __future__ import annotations

from unittest.mock import mock_open, patch

import pytest

from autom8_asana.cache.dataframe.tiers.memory import (
    MemoryTier,
    _get_container_memory_bytes,
)


class TestGetContainerMemoryBytes:
    """Tests for _get_container_memory_bytes()."""

    def test_env_var_override_takes_precedence(self) -> None:
        """CONTAINER_MEMORY_MB env var overrides all other detection."""
        with patch.dict("os.environ", {"CONTAINER_MEMORY_MB": "2048"}):
            result = _get_container_memory_bytes()
        assert result == 2048 * 1024 * 1024

    def test_env_var_invalid_ignored(self) -> None:
        """Non-numeric CONTAINER_MEMORY_MB falls through to cgroup/fallback."""
        with (
            patch.dict("os.environ", {"CONTAINER_MEMORY_MB": "not-a-number"}),
            patch("builtins.open", side_effect=FileNotFoundError),
        ):
            result = _get_container_memory_bytes()
        assert result == 1024 * 1024 * 1024  # 1GB fallback

    def test_cgroup_v2_detected(self) -> None:
        """Reads cgroup v2 memory.max and returns correct bytes."""
        cgroup_bytes = 536870912  # 512MB
        with (
            patch.dict("os.environ", {}, clear=False),
            patch(
                "builtins.open",
                mock_open(read_data=f"{cgroup_bytes}\n"),
            ),
        ):
            # Remove env var if present
            env = {
                k: v
                for k, v in __import__("os").environ.items()
                if k != "CONTAINER_MEMORY_MB"
            }
            with patch.dict("os.environ", env, clear=True):
                result = _get_container_memory_bytes()
        assert result == cgroup_bytes

    def test_cgroup_v1_detected(self) -> None:
        """Falls through to cgroup v1 when v2 not available."""
        cgroup_bytes = 1073741824  # 1GB

        call_count = 0

        def side_effect(path: str) -> mock_open:
            nonlocal call_count
            call_count += 1
            if "memory.max" in path:
                raise FileNotFoundError
            return mock_open(read_data=f"{cgroup_bytes}\n")()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("builtins.open", side_effect=side_effect),
        ):
            result = _get_container_memory_bytes()
        assert result == cgroup_bytes

    def test_cgroup_max_falls_through(self) -> None:
        """'max' value in cgroup v2 falls through to v1 or fallback."""
        call_count = 0

        def side_effect(path: str) -> mock_open:
            nonlocal call_count
            call_count += 1
            if "memory.max" in path:
                return mock_open(read_data="max\n")()
            raise FileNotFoundError

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("builtins.open", side_effect=side_effect),
        ):
            result = _get_container_memory_bytes()
        # Falls through to 1GB fallback (v1 file not found)
        assert result == 1024 * 1024 * 1024

    def test_no_cgroup_no_env_returns_1gb(self) -> None:
        """No cgroup files + no env var returns 1GB fallback."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("builtins.open", side_effect=FileNotFoundError),
        ):
            result = _get_container_memory_bytes()
        assert result == 1024 * 1024 * 1024

    def test_permission_error_falls_through(self) -> None:
        """PermissionError on cgroup files doesn't crash, falls to fallback."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("builtins.open", side_effect=PermissionError),
        ):
            result = _get_container_memory_bytes()
        assert result == 1024 * 1024 * 1024


class TestGetMaxBytesIntegration:
    """Tests for _get_max_bytes() using container memory detection."""

    def test_get_max_bytes_uses_container_memory(self) -> None:
        """_get_max_bytes() returns container_memory * heap_percent."""
        tier = MemoryTier(max_heap_percent=0.25, max_entries=50)

        with patch(
            "autom8_asana.cache.dataframe.tiers.memory._get_container_memory_bytes",
            return_value=1024 * 1024 * 1024,  # 1GB
        ):
            result = tier._get_max_bytes()

        assert result == int(1024 * 1024 * 1024 * 0.25)  # 256MB
