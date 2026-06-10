#!/usr/bin/env python3
"""Generate ``terraform/services/asana/namespaces.gen.json`` from the storage registry.

This is the TF<->Python derivation edge of the StorageNamespaceContract. Terraform
cannot import Python at plan-time, so the registry
(``src/autom8_asana/storage_namespace.py``) is the SSOT and this script projects it
to a checked-in JSON file that TF reads via ``jsondecode(file(...))`` (Phase-beta
beta-1).

The emitted JSON carries:

  * ``namespaces``  — the full registry (prefix, semantic_plane, writer_owner,
    reader_apis, env_vars, env_default, iam_grants verb matrix, lifecycle,
    lifecycle_note) so beta-1 can derive BOTH env blocks AND IAM resources.
  * ``env_blocks``  — a flat ``{ENV_VAR: value}`` map of the env-bearing namespace
    defaults. CRITICAL (FP-2a): these values are BYTE-EQUAL to the current TF
    literals (Phase-alpha is derivation-neutral, NOT a value fix), so the beta-1
    refactor that wires TF to read this file is a no-op plan.
  * ``iam_resources`` — per-principal lists of ``{namespace, prefix, verbs}`` so
    beta can derive the IAM policy ``Resource`` ARNs + verb sets from the registry.
  * ``known_drifts`` — the declared TARGET-vs-live divergences (for beta-2/beta-3
    remediation tracking).

Determinism: keys are sorted and the output is pretty-printed with a trailing
newline so ``tests/arch/test_namespace_gen.py`` can assert a zero-diff regeneration
(drift detection). Re-running this script on an unchanged registry yields
byte-identical output.

Usage:
    python scripts/gen_namespace_config.py            # write the file
    python scripts/gen_namespace_config.py --check     # exit 1 if the file is stale
    python scripts/gen_namespace_config.py --stdout    # print to stdout (no write)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make the registry importable whether run from the repo root or elsewhere. The
# registry is pure-stdlib so this import pulls no application stack.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from autom8_asana.storage_namespace import (  # noqa: E402
    KNOWN_DRIFTS,
    REGISTRY,
    REGISTRY_NAMESPACE_COUNT,
    StorageNamespaceContract,
)

# The checked-in output path (relative to the repo root). Terraform reads this via
# jsondecode(file(...)) in Phase-beta beta-1.
GEN_JSON_REL_PATH = "terraform/services/asana/namespaces.gen.json"


def _namespace_to_dict(ns: StorageNamespaceContract) -> dict[str, Any]:
    """Project one namespace contract to a JSON-serializable dict (deterministic)."""
    return {
        "name": ns.name,
        "prefix": ns.prefix,
        "semantic_plane": ns.semantic_plane.value,
        "writer_owner": {
            "repo": ns.writer_owner.repo,
            "code_anchor": ns.writer_owner.code_anchor,
            "external_name": ns.writer_owner.external_name,
            "is_attributed": ns.writer_owner.is_attributed,
        },
        "reader_apis": list(ns.reader_apis),
        "env_vars": list(ns.env_vars),
        "env_default": ns.env_default,
        "iam_grants": [
            {
                "principal_arn": g.principal_arn,
                "verbs": [v.value for v in g.verbs],
            }
            for g in ns.iam_grants
        ],
        "lifecycle": ns.lifecycle.value,
        "lifecycle_note": ns.lifecycle_note,
    }


def _build_env_blocks() -> dict[str, dict[str, str]]:
    """Per-namespace ``{namespace_name: {ENV_VAR: value}}`` env-default blocks.

    The blocks are keyed PER NAMESPACE (which IS the lane for the checkpoint
    family) rather than as a single flat ``{ENV_VAR: value}`` map. This is the
    honest representation: ``CACHE_WARMER_CHECKPOINT_PREFIX`` carries THREE distinct
    live TF values (the default lane via DEFAULT_PREFIX, the bulk lane, the
    section-fast lane), and ``ASANA_CACHE_S3_PREFIX`` is the overloaded env (mask
    #2) bound by both TASK_CACHE (default ``asana-cache``) and the project-frames
    FOSSIL (prod value ``asana-cache/project-frames/``). A flat map would COLLAPSE
    those distinct per-lane / per-plane values; per-namespace keying preserves each
    byte-equal to its live TF literal.

    FP-2a byte-equality targets (verified against live TF
    autom8/terraform/services/asana/main.tf):
      * PROJECT_FRAMES_FOSSIL.ASANA_CACHE_S3_PREFIX          = "asana-cache/project-frames/"
      * CHECKPOINTS_BULK.CACHE_WARMER_CHECKPOINT_PREFIX      = "cache-warmer/checkpoints/bulk/"
      * CHECKPOINTS_SECTION_FAST.CACHE_WARMER_CHECKPOINT_PREFIX = "cache-warmer/checkpoints/section-fast/"
    """
    blocks: dict[str, dict[str, str]] = {}
    for ns in REGISTRY:
        if ns.env_default is None or not ns.env_vars:
            continue
        blocks[ns.name] = {ev: ns.env_default for ev in ns.env_vars}
    return dict(sorted(blocks.items()))


def _build_iam_resources() -> dict[str, list[dict[str, Any]]]:
    """Per-principal lists of ``{namespace, prefix, verbs}`` from the registry.

    Beta derives the IAM policy ``Resource`` ARNs (``arn:aws:s3:::{bucket}/{prefix}*``)
    and verb sets from this map. Sorted by principal ARN then namespace name for
    determinism.
    """
    by_principal: dict[str, list[dict[str, Any]]] = {}
    for ns in REGISTRY:
        for grant in ns.iam_grants:
            by_principal.setdefault(grant.principal_arn, []).append(
                {
                    "namespace": ns.name,
                    "prefix": ns.prefix,
                    "verbs": [v.value for v in grant.verbs],
                }
            )
    return {
        principal: sorted(entries, key=lambda e: e["namespace"])
        for principal, entries in sorted(by_principal.items())
    }


def build_config() -> dict[str, Any]:
    """Build the full generated-config object (deterministic, JSON-serializable)."""
    return {
        "_generated_by": "scripts/gen_namespace_config.py",
        "_source_of_truth": "src/autom8_asana/storage_namespace.py",
        "_note": (
            "DO NOT EDIT BY HAND. Regenerate via scripts/gen_namespace_config.py. "
            "Values are byte-equal to the live TF literals (Phase-alpha is "
            "derivation-neutral). tests/arch/test_namespace_gen.py asserts a "
            "zero-diff regeneration."
        ),
        "namespace_count": REGISTRY_NAMESPACE_COUNT,
        "namespaces": [_namespace_to_dict(ns) for ns in REGISTRY],
        "env_blocks": _build_env_blocks(),
        "iam_resources": _build_iam_resources(),
        "known_drifts": [
            {
                "namespace": d.namespace_name,
                "description": d.description,
                "remediation_pointer": d.remediation_pointer,
            }
            for d in KNOWN_DRIFTS
        ],
    }


def render() -> str:
    """Render the config to a deterministic JSON string (sorted keys, trailing newline)."""
    return json.dumps(build_config(), indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the checked-in file is stale (does not write)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the rendered JSON to stdout (does not write)",
    )
    args = parser.parse_args(argv)

    rendered = render()
    out_path = _REPO_ROOT / GEN_JSON_REL_PATH

    if args.stdout:
        sys.stdout.write(rendered)
        return 0

    if args.check:
        if not out_path.exists():
            sys.stderr.write(f"MISSING: {GEN_JSON_REL_PATH} does not exist; run the generator.\n")
            return 1
        current = out_path.read_text(encoding="utf-8")
        if current != rendered:
            sys.stderr.write(
                f"STALE: {GEN_JSON_REL_PATH} differs from the registry. "
                "Run `python scripts/gen_namespace_config.py` and commit.\n"
            )
            return 1
        sys.stdout.write(f"OK: {GEN_JSON_REL_PATH} is up to date.\n")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(f"WROTE: {GEN_JSON_REL_PATH} ({len(rendered)} bytes)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
