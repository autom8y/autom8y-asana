"""Packaging guard: the production image MUST install the ``redis`` extra.

Root cause of the warmer degraded-cache incident (D-6 forensics, 2026-07-21):
the production ``Dockerfile`` built the runtime venv with

    uv sync --no-sources --no-dev --extra api --extra auth --extra lambda

-- omitting ``--extra redis``. The ``redis`` package was therefore absent from
the shipped image, so ``RedisCacheProvider`` took its ``except ImportError``
branch and ran a NO-OP *degraded* cache in every deployed warmer (live cluster
CurrItems=0 always; ``get_versioned`` -> ``None``, ``set_batch`` -> void). All
hierarchy-warm banking was lost at process death and large gap sets never
converged.

These are two-sided regression guards on the exact defect. They FAIL (RED) when
the production ``uv sync`` extra-set omits ``redis`` and PASS (GREEN) once the
extra is present. If anyone drops ``--extra redis`` from the production image
again, this test goes red in CI before the warmers can silently degrade in prod.

The guard reads the committed ``Dockerfile`` directly (no image build required),
so it runs in the ordinary unit-test shard.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# The redis-backed cache is load-bearing for the warmer lane: the production
# image MUST resolve the ``redis`` extra so ``import redis`` succeeds at runtime
# and RedisCacheProvider constructs non-degraded. ``api``/``auth``/``lambda`` are
# the pre-existing dual-mode (ECS uvicorn + Lambda awslambdaric) runtime extras;
# they are guarded here too so no lane silently loses a dependency in a refactor.
REQUIRED_PROD_EXTRAS = frozenset({"api", "auth", "lambda", "redis"})

_EXTRA_RE = re.compile(r"--extra\s+([A-Za-z0-9_.-]+)")


def _repo_root() -> Path:
    """Walk up from this test file to the repo root (holds Dockerfile + pyproject)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "Dockerfile").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise AssertionError("repo root (with Dockerfile + pyproject.toml) not found")


def _prod_uv_sync_extras() -> set[str]:
    """Extract the ``--extra <name>`` set from the production Dockerfile sync line.

    The production ``Dockerfile`` has exactly one ``uv sync ... --extra`` line
    (the builder-stage dependency install); its resolved venv is COPYed into the
    runtime stage, so the extras on this line are precisely what ships.
    """
    dockerfile = (_repo_root() / "Dockerfile").read_text(encoding="utf-8")
    sync_lines = [
        line for line in dockerfile.splitlines() if "uv sync" in line and "--extra" in line
    ]
    assert sync_lines, "no `uv sync ... --extra` line found in production Dockerfile"
    assert len(sync_lines) == 1, (
        f"expected exactly one production `uv sync --extra` line, "
        f"found {len(sync_lines)}: {sync_lines}"
    )
    return set(_EXTRA_RE.findall(sync_lines[0]))


def test_prod_image_installs_redis_extra() -> None:
    """The production ``uv sync`` MUST include ``--extra redis`` (warmer root cause).

    RED before the packaging fix (extra absent) -> GREEN after.
    """
    extras = _prod_uv_sync_extras()
    assert "redis" in extras, (
        "production Dockerfile `uv sync` omits `--extra redis`; the deployed "
        "warmers will run a NO-OP degraded cache (D-6 forensics). Extras found: "
        f"{sorted(extras)}"
    )


def test_prod_image_installs_all_required_extras() -> None:
    """Guard the full required production extra-set (redis + dual-mode runtime)."""
    extras = _prod_uv_sync_extras()
    missing = REQUIRED_PROD_EXTRAS - extras
    assert not missing, (
        "production Dockerfile `uv sync` is missing required extras: "
        f"{sorted(missing)} (found: {sorted(extras)})"
    )


def test_redis_extra_is_defined_in_pyproject() -> None:
    """Sanity anchor: the ``redis`` optional-dependency extra exists to install."""
    pyproject = (_repo_root() / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"(?m)^redis\s*=\s*\[", pyproject), (
        "`redis` extra not defined under [project.optional-dependencies] in "
        "pyproject.toml -- the production image cannot install what is not declared"
    )


if __name__ == "__main__":  # pragma: no cover - convenience for local RED/GREEN
    raise SystemExit(pytest.main([__file__, "-v"]))
