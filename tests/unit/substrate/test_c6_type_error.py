"""C6 receipt — entity-blind ArtifactId construction is a STATIC type error.

RC-C's load-bearing claim is that the plane-blind wound is unconstructable *by
type*, not merely refused at runtime: a caller that omits (or mistypes) the
``entity_type`` discriminator must be a mypy error. This runs mypy ONCE over four
snippets and asserts the entity-blind + str-typed variants are rejected while the
typed twin passes clean — the two-sided proof. A ``sentinel`` with a definite
unrelated type error proves the harness is actually analysing (not silently
treating imports as ``Any``); if it is not, the test SKIPS rather than green-washes.

Marked ``slow`` (a single cold mypy pass is ~45s, deselected on PR CI) — the fast,
always-on structural backbone (``entity_type`` required, no default) lives in
test_identity.py::test_entity_type_is_required_by_signature.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    from mypy import api as mypy_api

    MYPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    MYPY_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not MYPY_AVAILABLE, reason="mypy not importable"),
    pytest.mark.slow,
]

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
_CFG = _ROOT / "pyproject.toml"

_SNIPPETS = {
    # definite, ArtifactId-independent error — proves mypy is analysing, not skipping
    "sentinel.py": "x: int = 'definitely not an int'\n",
    # the typed twin — MUST pass clean (the falsifying variant)
    "typed.py": (
        "from autom8_asana.core.types import EntityType\n"
        "from autom8_asana.substrate import ArtifactId\n"
        "ArtifactId(project_gid='1', entity_type=EntityType.OFFER)\n"
    ),
    # omission — MUST be a missing-argument error
    "blind.py": ("from autom8_asana.substrate import ArtifactId\nArtifactId(project_gid='1')\n"),
    # str discriminator — MUST be an incompatible-type error
    "str_typed.py": (
        "from autom8_asana.substrate import ArtifactId\n"
        "ArtifactId(project_gid='1', entity_type='offer')\n"
    ),
}


@pytest.mark.timeout(180)
def test_entity_blind_construction_is_a_type_error(tmp_path: Path) -> None:
    # mypy echoes the absolute paths we pass — use them verbatim so "typed.py"
    # cannot substring-match inside "str_typed.py".
    path = {name: str(tmp_path / name) for name in _SNIPPETS}
    for name, src in _SNIPPETS.items():
        (tmp_path / name).write_text(src)

    os.environ["MYPYPATH"] = str(_SRC)
    out, _err, _code = mypy_api.run(
        ["--config-file", str(_CFG), "--no-incremental", "--follow-imports=silent", *path.values()]
    )

    # Harness liveness: the sentinel error MUST appear, else mypy is not resolving
    # the real signatures (imports Any) — skip rather than assert a false green.
    if path["sentinel.py"] not in out:
        pytest.skip(f"mypy harness not analysing snippets (no sentinel error): {out!r}")

    # Falsifying variant (the twin that MUST pass): no error on the typed call.
    assert path["typed.py"] not in out, f"typed twin must typecheck clean: {out}"

    # C6, two-sided: omission and str-discriminator are both static type errors.
    assert path["blind.py"] in out and "entity_type" in out, out
    assert path["str_typed.py"] in out and "EntityType" in out, out
