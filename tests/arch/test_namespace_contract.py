"""StorageNamespaceContract alignment tests (t1-t5) — the contract's teeth.

These tests make the wrong-prefix read STRUCTURALLY UNADDRESSABLE: a misconfigured
consumer (a loose prefix literal, an IAM grant pointing at an unregistered
namespace, a phantom backend config, a fossil PUT grant) cannot pass CI.

Each test is paired with a deliberately-broken fixture proving it fires RED — the
G-THEATER mandate (a green test that cannot go red is theater). The RED fixtures
mutate a COPY of the registry / inject a bad literal in a tmp module / construct a
bad grant; they NEVER mutate the live registry.

t1 — every namespace has a writer owner (code anchor OR external name), and the
     registry covers a pinned COUNT (a hand-added 12th without registration fails).
t2 — every IAM grant in the gen.json maps to a registered namespace with matching
     verbs (and resolves to a real registry prefix).
t3 — no S3 prefix literal in src/ outside the registry's declared anchor set (the
     cure's old hand-pin is GONE; the literal now lives in the registry).
t4 — no config field advertises a backend that does not exist (no PHANTOM
     namespace in the registry; s3_enabled is gone from TieredConfig).
t5 — FOSSIL/QUARANTINED namespaces carry no PUT/DELETE verbs in the registry's IAM
     matrix; the live exception is recorded in KNOWN_DRIFTS (honest, not lying).
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

from autom8_asana import storage_namespace as sn
from autom8_asana.storage_namespace import (
    REGISTRY,
    REGISTRY_NAMESPACE_COUNT,
    IAMVerb,
    Lifecycle,
    StorageNamespaceContract,
    WriterOwner,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_AUTOM8 = _SRC / "autom8_asana"
_REGISTRY_MODULE_REL = "autom8_asana/storage_namespace.py"
_GEN_JSON = _REPO_ROOT / "terraform" / "services" / "asana" / "namespaces.gen.json"

_MUTATING_VERBS = frozenset({IAMVerb.PUT, IAMVerb.DELETE})


# ===========================================================================
# t1 — writer-owner completeness + pinned count
# ===========================================================================


def test_t1_every_namespace_has_a_writer_owner() -> None:
    """t1: every namespace is attributed (code anchor OR external name).

    An UNATTRIBUTED namespace (no code anchor AND no external name) is the AP-4
    writer-unknown defect. The registry may declare a writer UNKNOWN only by naming
    an external owner; it may NEVER leave a namespace with no owner at all.
    """
    for ns in REGISTRY:
        assert ns.writer_owner.is_attributed, (
            f"t1 violation: namespace {ns.name!r} has no writer owner "
            "(code_anchor is None AND external_name is None — AP-4 UNATTRIBUTED)."
        )


def test_t1_registry_covers_the_pinned_count() -> None:
    """t1: the registry covers exactly the pinned namespace count.

    A hand-added 12th namespace (or a removal) without updating
    REGISTRY_NAMESPACE_COUNT trips this — registration metadata is mandatory.
    """
    assert len(REGISTRY) == REGISTRY_NAMESPACE_COUNT, (
        f"t1 violation: REGISTRY has {len(REGISTRY)} namespaces but the pinned "
        f"count is {REGISTRY_NAMESPACE_COUNT}. A namespace was added/removed "
        "without updating REGISTRY_NAMESPACE_COUNT."
    )


def test_t1_RED_unattributed_namespace_fails() -> None:
    """RED fixture: an unregistered/unattributed namespace fails t1's assertion.

    Mutate a COPY of a namespace to have NO owner; assert is_attributed is False
    (the exact condition t1 asserts True for every live namespace).
    """
    orphan = dataclasses.replace(
        REGISTRY[0],
        name="LIVE_ORPHAN",
        writer_owner=WriterOwner(repo=WriterOwner.EXTERNAL, code_anchor=None, external_name=None),
    )
    # The live t1 assertion would fire on this row:
    assert orphan.writer_owner.is_attributed is False
    with pytest.raises(AssertionError, match="no writer owner"):
        assert orphan.writer_owner.is_attributed, (
            f"t1 violation: namespace {orphan.name!r} has no writer owner "
            "(code_anchor is None AND external_name is None — AP-4 UNATTRIBUTED)."
        )


def test_t1_RED_count_drift_fails() -> None:
    """RED fixture: a registry list one longer than the pinned count fails t1's count."""
    bloated = (*REGISTRY, REGISTRY[0])  # a hand-added 12th (here 13th) without re-pinning
    assert len(bloated) != REGISTRY_NAMESPACE_COUNT
    with pytest.raises(AssertionError, match="pinned"):
        assert len(bloated) == REGISTRY_NAMESPACE_COUNT, (
            f"t1 violation: REGISTRY has {len(bloated)} namespaces but the pinned "
            f"count is {REGISTRY_NAMESPACE_COUNT}."
        )


# ===========================================================================
# t2 — IAM grant <-> namespace alignment (via the gen.json)
# ===========================================================================


def _load_gen_json() -> dict:
    assert _GEN_JSON.exists(), (
        f"namespaces.gen.json missing at {_GEN_JSON}; run `python scripts/gen_namespace_config.py`."
    )
    return json.loads(_GEN_JSON.read_text())


def test_t2_every_gen_iam_resource_maps_to_a_registered_namespace() -> None:
    """t2: every IAM grant resource in the gen.json maps to a registered namespace.

    Each ``iam_resources[principal][].prefix`` must equal some registry namespace
    prefix, and the grant's verbs must match that namespace's declared verbs for
    that principal. A grant pointing at an unregistered prefix (or with verbs the
    registry does not declare) is the AP-3 IAM-drift defect.
    """
    gen = _load_gen_json()
    registry_prefixes = {ns.prefix for ns in REGISTRY}

    # Build the registry's (principal, prefix) -> verbs truth from the live registry.
    registry_grants: dict[tuple[str, str], set[str]] = {}
    for ns in REGISTRY:
        for grant in ns.iam_grants:
            key = (grant.principal_arn, ns.prefix)
            registry_grants.setdefault(key, set()).update(v.value for v in grant.verbs)

    for principal, entries in gen["iam_resources"].items():
        for entry in entries:
            prefix = entry["prefix"]
            assert prefix in registry_prefixes, (
                f"t2 violation: IAM grant for {principal} points at prefix "
                f"{prefix!r} which is not in the namespace registry (AP-3)."
            )
            declared = registry_grants.get((principal, prefix))
            assert declared is not None, (
                f"t2 violation: gen.json grant ({principal}, {prefix!r}) has no "
                "matching (principal, prefix) in the registry."
            )
            assert set(entry["verbs"]) == declared, (
                f"t2 violation: gen.json verbs {sorted(entry['verbs'])} for "
                f"({principal}, {prefix!r}) disagree with the registry "
                f"{sorted(declared)} (AP-3 verb drift)."
            )


def test_t2_RED_grant_on_unregistered_prefix_fails() -> None:
    """RED fixture: an IAM resource entry pointing at an unregistered prefix fails t2."""
    registry_prefixes = {ns.prefix for ns in REGISTRY}
    bad_entry = {
        "namespace": "GHOST",
        "prefix": "autom8-s3/UNREGISTERED/",
        "verbs": ["s3:GetObject"],
    }
    assert bad_entry["prefix"] not in registry_prefixes
    with pytest.raises(AssertionError, match="not in the namespace registry"):
        assert bad_entry["prefix"] in registry_prefixes, (
            f"t2 violation: IAM grant points at prefix {bad_entry['prefix']!r} "
            "which is not in the namespace registry (AP-3)."
        )


# ===========================================================================
# t3 — no S3 prefix literal in src/ outside the registry's declared anchor set
# ===========================================================================


def _registry_anchor_files() -> set[str]:
    """The src files the registry KNOWS touch its prefixes (writer + reader anchors).

    t3 allowlists these (plus the registry module itself): the prefix value is
    canonically DECLARED at these anchors, recorded in the registry. A prefix
    literal in ANY OTHER src file is an unregistered loose literal (AP-1/AP-6) and
    fails t3 — which is exactly FP-1 (a NEW literal in an unregistered file fails CI).
    """
    files: set[str] = {_REGISTRY_MODULE_REL}

    def _norm(anchor: str) -> str:
        # Strip the trailing ":line" / ":symbol" and normalize to a path relative
        # to src/ (i.e. prefixed with "autom8_asana/"). Registry anchors are written
        # relative to src/autom8_asana/ (e.g. "settings.py", "dataframes/storage.py").
        path = anchor.split(":")[0]
        return path if path.startswith("autom8_asana/") else f"autom8_asana/{path}"

    for ns in REGISTRY:
        if ns.writer_owner.code_anchor:
            files.add(_norm(ns.writer_owner.code_anchor))
        for r in ns.reader_apis:
            files.add(_norm(r))
    return files


def _src_prefix_literal_sites() -> list[tuple[str, int, str]]:
    """Every string-constant in src/ that EXACTLY equals a registry prefix.

    AST-based: only code string CONSTANTS count (comments/docstrings are not
    Constant nodes at statement level we care about — a module docstring IS a
    Constant, so we skip the first statement docstring of each module/class/func).
    """
    prefixes = {ns.prefix for ns in REGISTRY}
    sites: list[tuple[str, int, str]] = []
    for py in _AUTOM8.rglob("*.py"):
        rel = str(py.relative_to(_SRC))
        tree = ast.parse(py.read_text(encoding="utf-8"))
        docstring_nodes = _collect_docstring_nodes(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in prefixes
                and node not in docstring_nodes
            ):
                sites.append((rel, node.lineno, node.value))
    return sites


def _collect_docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    """Collect docstring Constant nodes (module/class/function) to exclude from t3."""
    docs: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docs.add(body[0].value)
    return docs


def test_t3_no_prefix_literal_outside_registry_anchor_set() -> None:
    """t3: every prefix literal in src/ lives in a registry-declared anchor file.

    The cure's OLD hand-pinned ``_DURABLE_TASK_CACHE_PREFIX = "asana-cache"`` literal
    is GONE (it now derives from ``TASK_CACHE.prefix``), so t3 passes BECAUSE the
    literal moved into the registry. A NEW prefix literal in an unregistered src
    file fails this (FP-1).
    """
    allow_files = _registry_anchor_files()
    offenders = [
        (rel, ln, val) for (rel, ln, val) in _src_prefix_literal_sites() if rel not in allow_files
    ]
    assert offenders == [], (
        "t3 violation: prefix literal(s) found in src/ outside the registry's "
        f"declared anchor set (AP-1/AP-6): {offenders}. Either derive the value "
        "from autom8_asana.storage_namespace, or register the file as a "
        "writer_owner.code_anchor / reader_apis entry in the registry."
    )


def test_t3_RED_unregistered_literal_in_tmp_module_fails(tmp_path: Path) -> None:
    """RED fixture: a tmp src-style module with an unregistered prefix literal fails t3.

    Writes a throwaway .py carrying a registry prefix as a code constant, scans it
    with the SAME AST predicate t3 uses, and asserts the offender is detected.
    """
    bad = tmp_path / "rogue_consumer.py"
    bad.write_text(
        '"""A rogue consumer that hand-pins a prefix instead of deriving it."""\n'
        'WRONG_PREFIX = "asana-cache"  # AP-1: loose literal, not derived\n',
        encoding="utf-8",
    )
    prefixes = {ns.prefix for ns in REGISTRY}
    tree = ast.parse(bad.read_text(encoding="utf-8"))
    docs = _collect_docstring_nodes(tree)
    found = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value in prefixes
        and n not in docs
    ]
    assert "asana-cache" in found, "the RED fixture's loose literal must be detected by t3's scan"


# ===========================================================================
# t4 — no config field advertises a non-existent backend (no PHANTOM)
# ===========================================================================


def test_t4_registry_has_no_phantom_namespace() -> None:
    """t4: no namespace is PHANTOM (config advertising a backend wired nowhere).

    The phantom S3 cold tier (mask #1) is retired — there is no Lifecycle.PHANTOM
    row in the registry.
    """
    phantoms = [ns.name for ns in REGISTRY if ns.lifecycle is Lifecycle.PHANTOM]
    assert phantoms == [], (
        f"t4 violation: PHANTOM namespace(s) in the registry: {phantoms} — a config "
        "field advertises a backend wired nowhere (AP-2)."
    )


def test_t4_tiered_config_s3_enabled_is_gone() -> None:
    """t4: TieredConfig (with its s3_enabled flag) no longer exists.

    The phantom flag + the false ASANA_CACHE_S3_ENABLED env claim are retired. The
    TieredConfig class is gone entirely; TieredCacheProvider takes no config.
    """
    import autom8_asana.cache.providers.tiered as tiered_mod

    assert not hasattr(tiered_mod, "TieredConfig"), (
        "t4 violation: TieredConfig still exists — the phantom s3_enabled config "
        "field advertises a non-existent S3 cold tier (AP-2)."
    )
    # The provider must not carry an s3_enabled attribute either.
    assert not hasattr(tiered_mod.TieredCacheProvider, "s3_enabled"), (
        "t4 violation: TieredCacheProvider still exposes s3_enabled (AP-2)."
    )


def test_t4_no_src_docstring_advertises_asana_cache_s3_enabled_env() -> None:
    """t4: no src code declares/reads the phantom ASANA_CACHE_S3_ENABLED env.

    The env that gated the phantom cold tier was set nowhere; any code that READS
    it (as an env lookup constant) re-advertises a non-existent backend. We scan for
    the env name appearing as a code string CONSTANT (not a comment) in src.
    """
    offenders: list[tuple[str, int]] = []
    for py in _AUTOM8.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        docs = _collect_docstring_nodes(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value == "ASANA_CACHE_S3_ENABLED"
                and node not in docs
            ):
                offenders.append((str(py.relative_to(_SRC)), node.lineno))
    assert offenders == [], (
        "t4 violation: code reads the phantom ASANA_CACHE_S3_ENABLED env "
        f"(advertises a non-existent backend, AP-2): {offenders}."
    )


def test_t4_RED_phantom_namespace_fails() -> None:
    """RED fixture: a PHANTOM-lifecycle namespace fails t4."""
    phantom = dataclasses.replace(REGISTRY[0], name="PHANTOM_TIER", lifecycle=Lifecycle.PHANTOM)
    bad_registry = (*REGISTRY, phantom)
    phantoms = [ns.name for ns in bad_registry if ns.lifecycle is Lifecycle.PHANTOM]
    assert phantoms == ["PHANTOM_TIER"]
    with pytest.raises(AssertionError, match="PHANTOM namespace"):
        assert phantoms == [], f"t4 violation: PHANTOM namespace(s): {phantoms} (AP-2)."


# ===========================================================================
# t5 — FOSSIL/QUARANTINED namespaces carry no PUT/DELETE in the registry matrix
# ===========================================================================


def test_t5_fossil_namespaces_have_no_mutating_grants() -> None:
    """t5: FOSSIL/QUARANTINED namespaces declare no PUT/DELETE verbs (TARGET state).

    The registry records the TARGET grant (read-only / none) for write-orphaned
    namespaces. The live exception (warmer roles still hold PUT/DELETE on
    project-frames today) is recorded in KNOWN_DRIFTS with a Phase-beta remediation
    pointer — so t5 passes HONESTLY without lying about live state.
    """
    for ns in REGISTRY:
        if ns.lifecycle not in (Lifecycle.FOSSIL, Lifecycle.QUARANTINED):
            continue
        for grant in ns.iam_grants:
            mutating = _MUTATING_VERBS.intersection(grant.verbs)
            assert not mutating, (
                f"t5 violation: {ns.lifecycle.value} namespace {ns.name!r} declares "
                f"mutating verb(s) {sorted(v.value for v in mutating)} for "
                f"{grant.principal_arn} in the registry's TARGET matrix (AP-5). If "
                "this reflects a live grant, record it in KNOWN_DRIFTS, not here."
            )


def test_t5_project_frames_drift_is_declared() -> None:
    """t5 companion: the live project-frames PUT/DELETE exception IS in KNOWN_DRIFTS.

    Proves t5 passes HONESTLY: the registry's TARGET says read-only, AND the live
    PUT/DELETE drift is explicitly recorded (not silently dropped).
    """
    declared = {d.namespace_name for d in sn.KNOWN_DRIFTS}
    assert "PROJECT_FRAMES_FOSSIL" in declared, (
        "the live project-frames PUT/DELETE drift must be recorded in KNOWN_DRIFTS "
        "so t5's TARGET-state assertion is honest about the live exception."
    )


def test_t5_RED_fossil_with_put_grant_fails() -> None:
    """RED fixture: a FOSSIL namespace with a PUT grant fails t5."""
    fossil = next(ns for ns in REGISTRY if ns.lifecycle is Lifecycle.FOSSIL)
    bad = dataclasses.replace(
        fossil,
        iam_grants=(sn.IAMGrant(fossil.iam_grants[0].principal_arn, (IAMVerb.GET, IAMVerb.PUT)),),
    )
    mutating = _MUTATING_VERBS.intersection(bad.iam_grants[0].verbs)
    assert mutating  # the bad grant DOES carry a mutating verb
    with pytest.raises(AssertionError, match="mutating verb"):
        for grant in bad.iam_grants:
            m = _MUTATING_VERBS.intersection(grant.verbs)
            assert not m, (
                f"t5 violation: {bad.lifecycle.value} namespace {bad.name!r} declares "
                f"mutating verb(s) {sorted(v.value for v in m)} (AP-5)."
            )


# ===========================================================================
# Sanity: the registry is importable and internally consistent (the import-time
# _validate_registry already ran; this is a belt-and-suspenders surface).
# ===========================================================================


def test_registry_internal_consistency() -> None:
    """The registry imports clean and its structural invariants hold."""
    assert isinstance(REGISTRY, tuple)
    assert all(isinstance(ns, StorageNamespaceContract) for ns in REGISTRY)
    # Unique names + prefixes (also enforced at import by _validate_registry).
    assert len({ns.name for ns in REGISTRY}) == len(REGISTRY)
    assert len({ns.prefix for ns in REGISTRY}) == len(REGISTRY)
