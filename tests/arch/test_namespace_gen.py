"""namespaces.gen.json drift-detection test (the TF<->Python derivation guard).

Asserts that regenerating ``terraform/services/asana/namespaces.gen.json`` from the
storage registry yields BYTE-IDENTICAL content to the checked-in file. If a
developer edits ``src/autom8_asana/storage_namespace.py`` without regenerating the
JSON, this fails CI — the detection-grade enforcement channel for the TF derivation
edge (the prevention-grade boundary is the Python side; the TF side is CI-detected,
per the TDD's honest-limit note).

Also asserts the FP-2a byte-equality: the env-bearing namespaces' values in the
gen.json are byte-equal to the current live TF literals (Phase-alpha is
derivation-neutral, NOT a value fix).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GEN_JSON = _REPO_ROOT / "terraform" / "services" / "asana" / "namespaces.gen.json"
_SCRIPTS = _REPO_ROOT / "scripts"


def _load_generator():
    """Import the generator module (scripts/ is not a package)."""
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    mod = importlib.import_module("gen_namespace_config")
    return importlib.reload(mod)


def test_gen_json_is_not_stale() -> None:
    """Regenerating the gen.json yields zero diff against the checked-in file.

    This is the idempotence + drift guard: ``render()`` of the live registry must
    equal the committed JSON byte-for-byte.
    """
    gen = _load_generator()
    assert _GEN_JSON.exists(), (
        f"namespaces.gen.json missing at {_GEN_JSON}; run `python scripts/gen_namespace_config.py`."
    )
    expected = gen.render()
    actual = _GEN_JSON.read_text(encoding="utf-8")
    assert actual == expected, (
        "namespaces.gen.json is STALE: it differs from a fresh regeneration of the "
        "storage registry. Run `python scripts/gen_namespace_config.py` and commit "
        "the result."
    )


def test_gen_json_regeneration_is_idempotent() -> None:
    """Rendering twice yields identical output (no nondeterminism in the generator)."""
    gen = _load_generator()
    assert gen.render() == gen.render()


def test_gen_json_carries_the_full_registry() -> None:
    """The gen.json carries every registered namespace (so beta can derive IAM too)."""
    gen = _load_generator()
    data = json.loads(_GEN_JSON.read_text(encoding="utf-8"))
    from autom8_asana.storage_namespace import REGISTRY, REGISTRY_NAMESPACE_COUNT

    assert data["namespace_count"] == REGISTRY_NAMESPACE_COUNT
    assert len(data["namespaces"]) == len(REGISTRY)
    gen_names = {n["name"] for n in data["namespaces"]}
    assert gen_names == {ns.name for ns in REGISTRY}


def test_fp2a_env_values_byte_equal_to_known_tf_literals() -> None:
    """FP-2a: the env-bearing namespace values are byte-equal to the live TF literals.

    The live TF literals (verified against
    autom8/terraform/services/asana/main.tf this session):
      * ASANA_CACHE_S3_PREFIX (prod/project-frames lane) = "asana-cache/project-frames/"
      * CACHE_WARMER_CHECKPOINT_PREFIX (bulk lane)        = "cache-warmer/checkpoints/bulk/"
      * CACHE_WARMER_CHECKPOINT_PREFIX (section lane)      = "cache-warmer/checkpoints/section-fast/"

    These are pinned here as a frozen byte-equality assertion (an external-literal
    SVR receipt): a registry value change that broke byte-equality with live TF
    would fail this test (and FP-2a). The default checkpoint lane value
    (cache-warmer/checkpoints/) is DEFAULT_PREFIX (env unset in TF) and is carried
    for completeness.
    """
    data = json.loads(_GEN_JSON.read_text(encoding="utf-8"))
    blocks = data["env_blocks"]

    assert blocks["PROJECT_FRAMES_FOSSIL"]["ASANA_CACHE_S3_PREFIX"] == "asana-cache/project-frames/"
    assert blocks["CHECKPOINTS_BULK"]["CACHE_WARMER_CHECKPOINT_PREFIX"] == (
        "cache-warmer/checkpoints/bulk/"
    )
    assert blocks["CHECKPOINTS_SECTION_FAST"]["CACHE_WARMER_CHECKPOINT_PREFIX"] == (
        "cache-warmer/checkpoints/section-fast/"
    )
    # The unadorned task-cache prefix (the writer's actual prefix) and the default
    # checkpoint lane (DEFAULT_PREFIX) round-trip byte-equal too.
    assert blocks["TASK_CACHE"]["ASANA_CACHE_S3_PREFIX"] == "asana-cache"
    assert blocks["CHECKPOINTS"]["CACHE_WARMER_CHECKPOINT_PREFIX"] == "cache-warmer/checkpoints/"
