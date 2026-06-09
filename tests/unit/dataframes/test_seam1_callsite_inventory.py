"""SEAM-1 NFR-2 structural call-site inventory — the falsifiable G-PROPAGATE guard.

ADR-SEAM1 NFR-2: post-cutover there must be ZERO readers/writers on the OLD
entity-AGNOSTIC ``dataframes/{gid}/`` path. A single call-site that invokes a
substrate function WITHOUT threading ``entity_type`` routes to (or reads from)
the legacy entity-agnostic key — the exact defect class that produced D-1
(writer orphan) and F-1 (reader orphan). A per-reader/per-writer test would have
to be remembered and added one at a time; THIS test enumerates EVERY call-site
of the substrate surface via the AST and asserts each one threads ``entity_type``
(or is on an explicit, rationale-bearing sanctioned-legacy allowlist).

Why AST (not grep): the test must survive line drift and refactors. It binds to
the call graph (callee name + argument structure), not to file:line coordinates.

Mutation proof (G-THEATER): ``test_inventory_FAILS_if_a_reader_drops_entity_type``
synthesizes a call-site that omits ``entity_type`` and asserts the checker reports
it as a violation. If that ever stops failing, this guard is theater.

The substrate surface (every reader/writer of ``dataframes/{gid}/``):
    get_manifest_async, load_dataframe, load_dataframe_with_metadata,
    save_dataframe, load_section, save_section, delete_dataframe,
    delete_section, write_final_artifacts_async, delete_manifest_async,
    delete_section_files_async, load_project_dataframe[_with_meta],
    from_manifest_async, read_manifest_sync.

``purge_project_all_entities`` is the SANCTIONED entity-agnostic SCAN (D-1b): it
deliberately has no entity_type because it must reach EVERY entity segment. It is
on the substrate surface as a *writer* but exempt from the entity_type assertion
by design (see ``_SCAN_ALL_CALLEES``).

NFR-2 HARDENING (F-2 + qa false-PASS closure):
    The TYPED-callee inventory above cannot see a reader/writer that bypasses the
    named substrate methods by constructing a RAW S3 key-string
    (``f"dataframes/{gid}/sections/"``) and listing it directly via
    ``from_s3_listing`` / ``list_objects_v2`` / a paginator. That is exactly the
    F-2 orphan class (metrics/__main__.py freshness reads on the legacy
    entity-AGNOSTIC prefix). ``TestSeam1RawKeyStringInventory`` adds a SECOND,
    USAGE-AWARE structural pass: it finds every legacy entity-AGNOSTIC
    ``dataframes/{gid}/sections/`` prefix that FLOWS INTO A LISTING SINK
    (``from_s3_listing`` / ``list_objects_v2`` / ``paginate``) and flags it,
    unless the prefix is entity-segmented (carries an ``{entity_type}`` /
    ``entity_type`` / ``_entity_segment`` reference between the project gid and
    ``/sections/``) or sits inside a sanctioned v2-aware resolver scope. Binding
    the check to USAGE (not to the literal in isolation) is what closes the
    display-string allowlist-SHADOW gap qa flagged -- a legacy display string
    that never reaches a sink is a non-orphan by construction, with no exemption
    needed and no shadow surface.

    Three qa-flagged false-PASS surfaces on the TYPED pass are closed here too:
      * kwargs-splat: ``f(gid, **opts)`` no longer auto-passes (a ``**kwargs``
        splat is NOT proof that entity_type was threaded).
      * substring-name decoy: a name merely *containing* ``entity_type`` as a
        substring (``not_entity_type``, ``entity_typed_flag``) no longer counts;
        the match is boundary-anchored (``entity_type`` exactly, or as a
        ``.entity_type`` / ``_entity_type`` suffix).
      * non-storage receiver decoy: a substrate-named call on a receiver that is
        provably NOT a storage/persistence object is excluded so it cannot be
        spoofed into the guarded count.
"""

from __future__ import annotations

import ast
from pathlib import Path

# asyncio_mode="auto" (pyproject) -> async defs run without an explicit marker.

# ---------------------------------------------------------------------------
# Substrate surface definition
# ---------------------------------------------------------------------------

# src/ root of the worktree-local package (this test file lives at
# tests/unit/dataframes/; src/ is three parents up + "src").
_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "autom8_asana"

# Callees that MUST thread entity_type. Keyed by the method/function NAME as it
# appears at the call site (the AST sees only the attribute/name, not the class).
# entity_type may be passed positionally or by keyword in every one of these.
_SUBSTRATE_CALLEES: frozenset[str] = frozenset(
    {
        "get_manifest_async",
        "load_dataframe",
        "load_dataframe_with_metadata",
        "save_dataframe",
        "load_section",
        "save_section",
        "delete_dataframe",
        "delete_section",
        "write_final_artifacts_async",
        "delete_manifest_async",
        "delete_section_files_async",
        "load_project_dataframe",
        "load_project_dataframe_with_meta",
        "from_manifest_async",
        "read_manifest_sync",
    }
)

# The entity-AGNOSTIC scan-all purge (D-1b). By design it carries NO entity_type
# because it must enumerate and delete EVERY entity segment under the project
# prefix. It is a substrate writer but exempt from the threading assertion.
_SCAN_ALL_CALLEES: frozenset[str] = frozenset({"purge_project_all_entities"})

# Callees whose NAME collides with a non-substrate method. ``delete_section``
# names BOTH the S3DataFrameStorage substrate method
# (``storage.delete_section(project_gid, section_gid, entity_type)``) AND the
# unrelated Asana-SDK ``SectionService.delete_section(client, gid)`` route
# operation. The substrate variant is ALWAYS invoked on a storage receiver
# (``storage`` / ``_storage`` / ``*.storage``); the API variant is invoked on a
# service receiver. Only count the call as substrate when its receiver chain
# resolves to a storage object -- otherwise the bare-name check raises a false
# positive on the Asana section-delete route.
_RECEIVER_DISAMBIGUATED: dict[str, frozenset[str]] = {
    "delete_section": frozenset({"storage", "_storage"}),
}

# Non-storage receiver denylist (qa false-PASS closure -- non-storage-receiver
# decoy). A substrate-NAMED method invoked on a receiver that is provably NOT a
# storage/persistence object MUST NOT be counted toward the guarded-site total
# (which would let a decoy inflate the count and mask a real shrink of the
# substrate surface). These receiver names denote Asana-SDK services, HTTP
# clients, and route handlers -- never the S3 substrate. Matched on the
# immediate receiver attribute/name (e.g. ``section_service.delete_section``,
# ``http_client.load_dataframe``).
_NON_STORAGE_RECEIVERS: frozenset[str] = frozenset(
    {
        "section_service",
        "sections",
        "service",
        "client",
        "_client",
        "http",
        "_http",
        "http_client",
        "api",
        "_api",
        "asana",
        "sdk",
    }
)


class _AllowlistEntry:
    """A single sanctioned-legacy call-site exemption with a file:line rationale."""

    __slots__ = ("rel_path", "callee", "rationale")

    def __init__(self, rel_path: str, callee: str, rationale: str) -> None:
        self.rel_path = rel_path
        self.callee = callee
        self.rationale = rationale


# Sanctioned-legacy allowlist: call-sites that INTENTIONALLY omit entity_type
# because the legacy-miss IS the trigger semantic. Each entry carries a rationale.
# Keyed by (relative-src-path, callee-name) so it is robust to line drift.
_SANCTIONED_LEGACY: tuple[_AllowlistEntry, ...] = (
    _AllowlistEntry(
        rel_path="api/preload/progressive.py",
        callee="get_manifest_async",
        rationale=(
            "v2 hot-path preload (progressive.py:~396): the legacy-miss "
            "(manifest is None) is the INTENTIONAL trigger to load the "
            "entity-keyed parquet via load_dataframe(project_gid, entity_type) "
            "on the very next branch. Threading entity_type here would change "
            "the trigger semantics. ADR-SEAM1 NOTE explicitly preserves this "
            "fallback; F-1 is about readers that NEVER pass entity_type at all."
        ),
    ),
    _AllowlistEntry(
        rel_path="lambda_handlers/cache_invalidate.py",
        callee="delete_section_files_async",
        rationale=(
            "Lambda invalidate back-compat belt-and-suspenders (cache_invalidate.py "
            ":~218): the PRIMARY purge is the scan-all purge_project_all_entities "
            "(:~211) which already reaches EVERY v2 entity segment. This entity- "
            "agnostic legacy delete runs AFTER, to purge artifacts predating the "
            "scan-all helper even where list permissions are constrained. It is "
            "sanctioned legacy cleanup (D-1b design), not a v2 reader/writer orphan."
        ),
    ),
    _AllowlistEntry(
        rel_path="lambda_handlers/cache_invalidate.py",
        callee="delete_manifest_async",
        rationale=(
            "Lambda invalidate back-compat belt-and-suspenders (cache_invalidate.py "
            ":~219): companion to the legacy delete_section_files_async above. The "
            "scan-all purge_project_all_entities (:~211) is the v2-covering primary; "
            "this entity-agnostic manifest delete is the predates-scan-all back-compat "
            "sweep. Sanctioned legacy cleanup (D-1b design), not an orphan."
        ),
    ),
)


def _is_allowlisted(rel_path: str, callee: str) -> _AllowlistEntry | None:
    norm = rel_path.replace("\\", "/")
    for entry in _SANCTIONED_LEGACY:
        if norm.endswith(entry.rel_path) and entry.callee == callee:
            return entry
    return None


# ---------------------------------------------------------------------------
# AST analysis
# ---------------------------------------------------------------------------


def _callee_name(call: ast.Call) -> str | None:
    """Extract the simple callee name from a Call node.

    ``a.b.method(...)`` -> ``"method"``; ``func(...)`` -> ``"func"``.
    """
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _receiver_attr(call: ast.Call) -> str | None:
    """Return the immediate receiver attribute/name for ``receiver.method(...)``.

    ``persistence.storage.delete_section(...)`` -> ``"storage"``;
    ``self._storage.delete_section(...)`` -> ``"_storage"``;
    ``section_service.delete_section(...)`` -> ``"section_service"``.
    Returns None when the callee is a bare ``Name`` (no receiver).
    """
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    value = func.value
    if isinstance(value, ast.Attribute):
        return value.attr
    if isinstance(value, ast.Name):
        return value.id
    return None


def _is_substrate_call(call: ast.Call, callee: str) -> bool:
    """True iff this Call targets the dataframes/{gid}/ substrate variant of ``callee``.

    For receiver-disambiguated callees (``delete_section``), the receiver chain
    must resolve to a storage object; otherwise the bare name is a collision
    (e.g. the Asana-SDK ``SectionService.delete_section``) and is NOT substrate.

    HARDENED (qa false-PASS closure -- non-storage-receiver decoy): for ALL
    substrate-named callees, a call whose immediate receiver is on the
    ``_NON_STORAGE_RECEIVERS`` denylist is excluded. This stops a decoy from
    inflating the guarded-site count by invoking a substrate method NAME on a
    provably non-storage object (an Asana service, HTTP client, route handler).
    """
    receiver = _receiver_attr(call)
    if receiver in _NON_STORAGE_RECEIVERS:
        return False
    required = _RECEIVER_DISAMBIGUATED.get(callee)
    if required is None:
        return True
    return receiver in required


def _call_threads_entity_type(call: ast.Call) -> bool:
    """True iff the Call passes entity_type (by keyword OR as a referencing positional).

    Threading is satisfied when EITHER:
      * a keyword ``entity_type=...`` is present, OR
      * any positional/starred argument's source references an ``entity_type``
        binding (covers ``f(gid, entity_type)``, ``f(gid, self._entity_type)``,
        ``f(gid, self.entity_type)``, ``f(gid, metric.scope.entity_type)``).

    HARDENED (qa false-PASS closure): a bare ``**kwargs`` splat (``kw.arg is
    None``) is NO LONGER treated as threaded. Previously
    ``f(project_gid, **opts)`` auto-passed because the splat *might* carry
    entity_type -- but "might" is exactly the orphan the guard exists to catch.
    A ``**{"entity_type": ...}`` dict-literal splat IS honored (we can prove the
    key is present); an opaque ``**name`` splat is NOT (we cannot prove it, and
    an orphan would otherwise hide behind it). The only way to GUARANTEE the v2
    key is threaded is an explicit ``entity_type=`` keyword or an
    entity_type-referencing positional.
    """
    for kw in call.keywords:
        if kw.arg == "entity_type":
            return True
        # **{...} dict-literal splat: honor only if it literally contains an
        # entity_type key (provable). Opaque **name splats fall through to the
        # positional check and do NOT auto-pass.
        if kw.arg is None and _dict_literal_has_entity_type(kw.value):
            return True
    return any(_references_entity_type(arg) for arg in call.args)


def _dict_literal_has_entity_type(node: ast.AST) -> bool:
    """True iff ``node`` is a dict literal with an ``entity_type`` string key."""
    if not isinstance(node, ast.Dict):
        return False
    for key in node.keys:
        if (
            isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and _name_is_entity_type(key.value)
        ):
            return True
    return False


def _name_is_entity_type(name: str) -> bool:
    """Boundary-anchored ``entity_type`` match (closes the substring-name decoy).

    Accepts ``entity_type`` exactly, or a name ENDING in ``entity_type`` at a
    word boundary (``_entity_type``, ``read_entity_type``, ``metric_entity_type``)
    -- the production threading idioms. REJECTS a name that merely CONTAINS the
    substring in the middle or as a prefix (``entity_typed_flag``,
    ``not_entity_type_marker``, ``entity_type_count``), which a malicious or
    accidental decoy could use to spoof the old ``"entity_type" in id`` check.
    """
    if name == "entity_type":
        return True
    # Suffix match at an underscore boundary: "<prefix>_entity_type".
    return name.endswith("_entity_type")


def _references_entity_type(node: ast.AST) -> bool:
    """True iff the expression sub-tree references an ``entity_type`` binding.

    HARDENED: boundary-anchored name/attr match via ``_name_is_entity_type``
    (was an unanchored ``"entity_type" in id`` substring test that a decoy name
    like ``entity_typed_flag`` would falsely satisfy).
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and _name_is_entity_type(sub.id):
            return True
        if isinstance(sub, ast.Attribute) and _name_is_entity_type(sub.attr):
            return True
    return False


def _iter_src_files() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if p.is_file())


class _Violation:
    __slots__ = ("rel_path", "lineno", "callee")

    def __init__(self, rel_path: str, lineno: int, callee: str) -> None:
        self.rel_path = rel_path
        self.lineno = lineno
        self.callee = callee

    def __repr__(self) -> str:  # pragma: no cover - only on failure
        return f"{self.rel_path}:{self.lineno} {self.callee}(...) [no entity_type]"


def _scan_source(src: str, rel_path: str) -> tuple[list[_Violation], int]:
    """Return (violations, guarded_callsite_count) for one source string.

    A guarded call-site is any substrate call that either threads entity_type
    OR is sanctioned-legacy-allowlisted. Violations are substrate calls that
    do neither (and are not the scan-all exempt callee).
    """
    tree = ast.parse(src, filename=rel_path)
    violations: list[_Violation] = []
    guarded = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _callee_name(node)
        if callee is None:
            continue
        if callee in _SCAN_ALL_CALLEES:
            # Sanctioned entity-agnostic scan; not counted as a threaded site,
            # not a violation.
            continue
        if callee not in _SUBSTRATE_CALLEES:
            continue
        if not _is_substrate_call(node, callee):
            # Name collision with a non-substrate method (e.g. the Asana-SDK
            # SectionService.delete_section route op). Not the substrate variant.
            continue
        if _is_allowlisted(rel_path, callee):
            guarded += 1
            continue
        if _call_threads_entity_type(node):
            guarded += 1
            continue
        violations.append(_Violation(rel_path, node.lineno, callee))
    return violations, guarded


def _scan_substrate() -> tuple[list[_Violation], int]:
    """Scan all of src/ and return (all_violations, total_guarded_callsites)."""
    all_violations: list[_Violation] = []
    total_guarded = 0
    for path in _iter_src_files():
        rel = str(path.relative_to(_SRC_ROOT))
        violations, guarded = _scan_source(path.read_text(encoding="utf-8"), rel)
        all_violations.extend(violations)
        total_guarded += guarded
    return all_violations, total_guarded


# ---------------------------------------------------------------------------
# Raw-key-string substrate detection (NFR-2 HARDENING -- F-2 blind-spot closure)
# ---------------------------------------------------------------------------
#
# The typed-callee pass above is blind to a reader/writer that constructs a RAW
# S3 key-string (``f"dataframes/{gid}/sections/"``) and lists it directly. This
# second pass walks every string literal / f-string in src/ and flags any
# ``dataframes/{...}/sections/`` prefix that is NOT entity-segmented.

# An f-string segment is entity-segmented when, between the project-gid
# interpolation and ``/sections/``, it carries an ``{entity_type}`` /
# ``entity_type`` / ``_entity_segment`` reference. We detect the legacy
# entity-AGNOSTIC shape: ``dataframes/{...}/sections/`` where the segment
# IMMEDIATELY before ``sections`` is the project gid (no entity dir between).

# Marker for the dataframes section substrate in a raw key-string.
_DATAFRAMES_LITERAL_PREFIX = "dataframes/"
_SECTIONS_SEGMENT = "/sections/"


# NOTE -- why there is NO per-literal raw-string allowlist:
#   An earlier design exempted sanctioned legacy literals via a
#   (file, needle) allowlist. That is SHADOW-VULNERABLE -- the display-only
#   error string in metrics/__main__.py:~775 (legacy prefix built purely for a
#   human-readable stderr line, NO S3 read) shares the identical needle
#   ``f"dataframes/{project_gid}/sections/"`` with a genuine reader. A coarse
#   (file, needle) exemption for the display string would then silently exempt a
#   re-introduced reader orphan in the same file -- the qa-flagged false-PASS.
#   The usage-aware pass (below) discriminates by USAGE instead: a legacy prefix
#   is an orphan only when it FLOWS INTO A LISTING SINK. Display strings (-> print
#   / FreshnessError), the project-level sidecar (sla_profile.SIDECAR_S3_KEY_TEMPLATE
#   -- no /sections/, project-scope by ADR-005 design), and the v2-aware
#   resolver's own legacy fallback (offline._resolve_section_keys,
#   freshness.from_s3_resolved -- _SANCTIONED_RESOLVER_FILES) are all
#   non-orphans by construction, with NO shadow surface.


def _joinedstr_to_template(node: ast.JoinedStr) -> str:
    """Render an f-string AST node to a stable template string.

    Constant parts are kept verbatim; ``{expr}`` interpolations are rendered as
    ``{<name>}`` using the deepest attribute/name in the expression so that
    ``{self._entity_segment(...)}`` -> ``{_entity_segment}`` and ``{entity_type}``
    -> ``{entity_type}``. This lets the segmentation check see whether an
    entity reference sits between the gid and ``/sections/``.
    """
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            parts.append("{" + _formatted_value_name(value.value) + "}")
        else:  # pragma: no cover - defensive
            parts.append("{?}")
    return "".join(parts)


def _formatted_value_name(node: ast.AST) -> str:
    """Best-effort short name for an f-string ``{expr}`` interpolation."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _formatted_value_name(node.func)
    return "?"


def _section_prefix_is_entity_segmented(template: str) -> bool:
    """True iff a ``dataframes/.../sections/`` template carries an entity segment.

    Entity-segmented (v2): there is an ``entity_type`` / ``_entity_segment``
    reference between the FIRST interpolation (the project gid) and
    ``/sections/`` -- i.e. ``dataframes/{gid}/{entity_type}/sections/`` or
    ``{_entity_segment}/sections/``. Entity-AGNOSTIC (legacy): the segment
    immediately before ``/sections/`` is the gid interpolation with nothing
    between (``dataframes/{gid}/sections/``).
    """
    sec_idx = template.find(_SECTIONS_SEGMENT)
    if sec_idx == -1:
        return True  # no /sections/ -> not a section-substrate prefix; not our concern
    head = template[:sec_idx]
    df_idx = head.find(_DATAFRAMES_LITERAL_PREFIX)
    if df_idx == -1:
        return True  # not a dataframes/ key -> out of scope
    between = head[df_idx + len(_DATAFRAMES_LITERAL_PREFIX) :]
    # ``between`` is the path between ``dataframes/`` and ``/sections/``.
    # Entity-segmented when an entity reference appears anywhere in it.
    lowered = between
    if "entity_type" in lowered or "_entity_segment" in lowered:
        return True
    # ``{gid}/{entity}`` shape (two interpolations) also counts as segmented
    # even if the entity placeholder isn't literally named entity_type.
    return between.count("{") >= 2


class _RawStringViolation:
    __slots__ = ("rel_path", "lineno", "template")

    def __init__(self, rel_path: str, lineno: int, template: str) -> None:
        self.rel_path = rel_path
        self.lineno = lineno
        self.template = template

    def __repr__(self) -> str:  # pragma: no cover - only on failure
        return f"{self.rel_path}:{self.lineno} legacy raw key {self.template!r}"


def _is_pathlike_section_span(text: str) -> bool:
    """True iff the dataframes/.../sections/ span looks like a real S3 key path.

    A genuine key construction has NO whitespace and NO newline between
    ``dataframes/`` and ``/sections/`` (e.g. ``dataframes/{project_gid}/sections/``).
    Prose that merely MENTIONS the path (a docstring or comment rendered as a
    string, a multi-line description) carries spaces/newlines in the span and is
    NOT a key construction. This keeps the usage-aware pass from misreading a
    layout-describing docstring as a section key flowing into a sink.
    """
    df_idx = text.find(_DATAFRAMES_LITERAL_PREFIX)
    sec_idx = text.find(_SECTIONS_SEGMENT, df_idx)
    if df_idx == -1 or sec_idx == -1:
        return False
    span = text[df_idx : sec_idx + len(_SECTIONS_SEGMENT)]
    # A real key path token has no whitespace anywhere in the dataframes->sections
    # span. Any space/newline/tab means this is prose, not a key.
    return not any(ch.isspace() for ch in span)


# ---------------------------------------------------------------------------
# Usage-aware sink detection (closes the display-string allowlist-SHADOW gap)
# ---------------------------------------------------------------------------
#
# A literal-centric pass that flags every legacy section prefix and exempts it
# via a per-file allowlist is SHADOW-VULNERABLE: the metrics/__main__.py display
# string at :775 is sanctioned, but a coarse (file, needle) allowlist entry then
# silently exempts ANY same-needle literal in that file -- including a genuine
# reader orphan re-introduced later. The qa-flagged failure mode.
#
# The robust discriminator is USAGE, not the literal in isolation: a legacy
# section prefix is an orphan ONLY when it FLOWS INTO A LISTING SINK
# (``from_s3_listing`` / ``paginate`` / ``list_objects_v2``). A display string
# that flows into ``print`` / ``FreshnessError(...)`` is never a sink argument,
# so it is safe by construction -- no allowlist shadow needed. ``from_s3_resolved``
# is NOT a sink (it is the sanctioned v2-aware resolver that OWNS the legacy
# fallback); legacy literals inside the resolver scopes (offline._resolve_section_keys,
# freshness.from_s3_resolved) are exempt because the resolver is the sanctioned
# dual-read owner.

# Listing sinks: passing a legacy section prefix to ANY of these is a read/write
# on the entity-agnostic path. ``from_s3_resolved`` is deliberately EXCLUDED.
_LISTING_SINKS: frozenset[str] = frozenset({"from_s3_listing", "list_objects_v2", "paginate"})

# Source files whose legacy section literals are the SANCTIONED v2-aware
# resolver fallback (v2-first happens first; the legacy literal is the dual-read
# fallback target / scan-all base). These own the legacy prefix by design.
_SANCTIONED_RESOLVER_FILES: frozenset[str] = frozenset(
    {
        "dataframes/offline.py",
        "metrics/freshness.py",
    }
)


def _legacy_section_literal_lineno(node: ast.AST) -> int | None:
    """If ``node`` is a legacy entity-AGNOSTIC section prefix literal, return its lineno.

    Returns None when ``node`` is not a section key literal, or is
    entity-segmented (v2), or is prose (not path-like).
    """
    if isinstance(node, ast.JoinedStr):
        template = _joinedstr_to_template(node)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        template = node.value
    else:
        return None
    if _DATAFRAMES_LITERAL_PREFIX not in template or _SECTIONS_SEGMENT not in template:
        return None
    if not _is_pathlike_section_span(template):
        return None
    if _section_prefix_is_entity_segmented(template):
        return None
    return node.lineno


def _resolve_prefix_arg(
    call: ast.Call,
    legacy_prefix_vars: dict[str, int],
    segmented_prefix_vars: set[str],
) -> tuple[str, int | None]:
    """Classify the prefix/Prefix argument of a listing-sink call.

    Returns one of:
      ("legacy", lineno)    -- inline legacy literal OR var bound to a legacy
                               literal (the orphan shape).
      ("segmented", None)   -- inline segmented literal OR var bound to one
                               (a guarded v2 read).
      ("none", None)        -- prefix is some other expression we cannot classify
                               (e.g. a function param); neither flagged nor counted.
    """
    candidates: list[ast.AST] = []
    for kw in call.keywords:
        if kw.arg in {"prefix", "Prefix"}:
            candidates.append(kw.value)
    # Positional: from_s3_listing(bucket, prefix, threshold) -> arg index 1.
    callee = _callee_name(call)
    if callee == "from_s3_listing" and len(call.args) >= 2:
        candidates.append(call.args[1])
    for cand in candidates:
        legacy_inline = _legacy_section_literal_lineno(cand)
        if legacy_inline is not None:
            return ("legacy", legacy_inline)
        if _is_segmented_section_literal(cand):
            return ("segmented", None)
        if isinstance(cand, ast.Name):
            if cand.id in legacy_prefix_vars:
                return ("legacy", legacy_prefix_vars[cand.id])
            if cand.id in segmented_prefix_vars:
                return ("segmented", None)
    return ("none", None)


def _collect_prefix_vars(func: ast.AST) -> tuple[dict[str, int], set[str]]:
    """Return (legacy-prefix vars -> lineno, segmented-prefix var names).

    Scans assignments within a function scope so a sink call that passes a
    previously-assigned ``prefix`` variable is resolvable. Covers the F-2 shape
    (``prefix = f"dataframes/{gid}/sections/"`` then
    ``from_s3_listing(prefix=prefix)``) AND the v2 shape
    (``prefix = f"dataframes/{gid}/{entity_type}/sections/"``).
    """
    legacy: dict[str, int] = {}
    segmented: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        legacy_lineno = _legacy_section_literal_lineno(node.value)
        seg = _is_segmented_section_literal(node.value)
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if legacy_lineno is not None:
                legacy[target.id] = legacy_lineno
            elif seg:
                segmented.add(target.id)
    return legacy, segmented


def _scan_raw_key_strings_source(src: str, rel_path: str) -> tuple[list[_RawStringViolation], int]:
    """Return (legacy-sink violations, guarded count) for one source string.

    USAGE-AWARE: a legacy entity-AGNOSTIC section prefix is a VIOLATION only when
    it flows into a listing sink (read/write on the old path). Entity-segmented
    sink reads AND legacy reads inside the sanctioned resolver scopes are guarded;
    legacy literals that never reach a sink (display strings) are neither.
    """
    norm = rel_path.replace("\\", "/")
    is_resolver = any(norm.endswith(f) for f in _SANCTIONED_RESOLVER_FILES)
    tree = ast.parse(src, filename=rel_path)
    violations: list[_RawStringViolation] = []
    guarded = 0
    # Per-function prefix-variable maps (function scope for var binding).
    func_nodes = [
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    prefix_var_maps = {id(f): _collect_prefix_vars(f) for f in func_nodes}

    def _vars_for(call: ast.Call) -> tuple[dict[str, int], set[str]]:
        # Find the nearest enclosing function's prefix-var maps.
        for f in func_nodes:
            for sub in ast.walk(f):
                if sub is call:
                    return prefix_var_maps[id(f)]
        return {}, set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _callee_name(node)
        if callee in _LISTING_SINKS:
            legacy_vars, segmented_vars = _vars_for(node)
            kind, offending = _resolve_prefix_arg(node, legacy_vars, segmented_vars)
            if kind == "legacy":
                if is_resolver:
                    # Sanctioned resolver fallback (v2-first owns the legacy read).
                    guarded += 1
                else:
                    violations.append(
                        _RawStringViolation(
                            rel_path,
                            offending or node.lineno,
                            "dataframes/{gid}/sections/ -> sink",
                        )
                    )
            elif kind == "segmented":
                # v2-segmented prefix flowing into a sink -> guarded v2 read.
                guarded += 1
        # from_s3_resolved is the sanctioned v2-aware entry; count as guarded.
        if callee == "from_s3_resolved":
            guarded += 1
    return violations, guarded


def _is_segmented_section_literal(node: ast.AST) -> bool:
    """True iff ``node`` is an ENTITY-SEGMENTED dataframes/.../sections/ literal."""
    if isinstance(node, ast.JoinedStr):
        template = _joinedstr_to_template(node)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        template = node.value
    else:
        return False
    if _DATAFRAMES_LITERAL_PREFIX not in template or _SECTIONS_SEGMENT not in template:
        return False
    if not _is_pathlike_section_span(template):
        return False
    return _section_prefix_is_entity_segmented(template)


def _scan_raw_key_strings() -> tuple[list[_RawStringViolation], int]:
    all_violations: list[_RawStringViolation] = []
    total_guarded = 0
    for path in _iter_src_files():
        rel = str(path.relative_to(_SRC_ROOT))
        violations, guarded = _scan_raw_key_strings_source(path.read_text(encoding="utf-8"), rel)
        all_violations.extend(violations)
        total_guarded += guarded
    return all_violations, total_guarded


# ---------------------------------------------------------------------------
# The structural guard
# ---------------------------------------------------------------------------


class TestSeam1CallSiteInventory:
    """NFR-2: every substrate reader/writer threads entity_type (G-PROPAGATE)."""

    def test_src_root_resolves(self) -> None:
        """Sanity: the AST scan is pointed at the real package (not an empty dir)."""
        assert _SRC_ROOT.is_dir(), f"src root not found at {_SRC_ROOT}"
        assert (_SRC_ROOT / "dataframes" / "section_persistence.py").is_file()

    def test_every_substrate_callsite_threads_entity_type(self) -> None:
        """The telos: ZERO substrate call-sites read/write the entity-agnostic path.

        Enumerates every call to the dataframes/{gid}/ substrate across src/ and
        asserts each threads entity_type or is sanctioned-legacy-allowlisted. A
        single orphan (a reader/writer that never passes entity_type) FAILS here
        -- this is the test that would have caught BOTH D-1 and F-1.
        """
        violations, guarded = _scan_substrate()
        assert violations == [], (
            "NFR-2 VIOLATED -- substrate call-site(s) read/write the legacy "
            "entity-AGNOSTIC dataframes/{gid}/ path without threading "
            "entity_type:\n  " + "\n  ".join(repr(v) for v in violations)
        )
        # The guard must actually be guarding something -- a zero-coverage scan
        # (e.g. wrong src root, all callees renamed) would vacuously pass.
        assert guarded >= 15, (
            f"inventory guards only {guarded} call-sites; expected >=15. "
            "If the substrate surface shrank legitimately, lower this floor; "
            "if it is 0 the scan is mis-pointed and the guard is vacuous."
        )

    def test_sanctioned_legacy_allowlist_is_live(self) -> None:
        """Every allowlist entry must match a REAL call-site (no dead exemptions).

        A stale allowlist entry would silently widen the sanctioned-legacy set.
        Each entry must correspond to an actual substrate call in the named file
        that genuinely omits entity_type (otherwise it should not be exempt).
        """
        for entry in _SANCTIONED_LEGACY:
            matches = list(_SRC_ROOT.rglob(entry.rel_path))
            assert matches, f"allowlist entry points at missing file: {entry.rel_path}"
            src = matches[0].read_text(encoding="utf-8")
            tree = ast.parse(src, filename=entry.rel_path)
            found_bare = False
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and _callee_name(node) == entry.callee
                    and not _call_threads_entity_type(node)
                ):
                    found_bare = True
                    break
            assert found_bare, (
                f"sanctioned-legacy allowlist entry {entry.rel_path}::{entry.callee} "
                "no longer matches a bare (entity_type-less) call-site. The legacy "
                "trigger was removed or fixed -- delete this allowlist entry so the "
                "exemption cannot mask a future orphan."
            )

    def test_inventory_FAILS_if_a_reader_drops_entity_type(self) -> None:
        """MUTATION PROOF (G-THEATER): a synthesized orphan IS reported as a violation.

        Drops entity_type from a substrate reader call in a synthetic source and
        asserts the checker flags it. This proves the guard's failure mode is real
        -- if this stops failing, the inventory test is inert.
        """
        # GREEN form: threads entity_type -> no violation.
        green = (
            "async def f(persistence, project_gid, entity_type):\n"
            "    return await persistence.get_manifest_async(project_gid, entity_type)\n"
        )
        green_violations, green_guarded = _scan_source(green, "synthetic_green.py")
        assert green_violations == []
        assert green_guarded == 1

        # RED form: drops entity_type -> exactly one violation on the reader.
        red = (
            "async def f(persistence, project_gid):\n"
            "    return await persistence.get_manifest_async(project_gid)\n"
        )
        red_violations, _ = _scan_source(red, "synthetic_red.py")
        assert len(red_violations) == 1, (
            "MUTATION PROOF FAILED: dropping entity_type from a get_manifest_async "
            "reader was NOT flagged -- the inventory guard is theater."
        )
        assert red_violations[0].callee == "get_manifest_async"

    def test_inventory_FAILS_if_a_writer_drops_entity_type(self) -> None:
        """MUTATION PROOF: a writer orphan (D-1 class) is also reported."""
        red = (
            "async def f(storage, project_gid, df, wm):\n"
            "    return await storage.save_dataframe(project_gid, df, wm)\n"
        )
        red_violations, _ = _scan_source(red, "synthetic_writer_red.py")
        assert len(red_violations) == 1
        assert red_violations[0].callee == "save_dataframe"

        green = (
            "async def f(storage, project_gid, df, wm, entity_type):\n"
            "    return await storage.save_dataframe("
            "project_gid, df, wm, entity_type=entity_type)\n"
        )
        green_violations, _ = _scan_source(green, "synthetic_writer_green.py")
        assert green_violations == []

    def test_api_delete_section_collision_is_not_flagged(self) -> None:
        """The Asana-SDK SectionService.delete_section is NOT the substrate variant.

        ``section_service.delete_section(client, gid)`` shares a name with the
        substrate ``storage.delete_section(project_gid, section_gid, entity_type)``
        but is an unrelated Asana API op with no entity_type. The receiver-
        disambiguation must exclude it; the substrate (storage-receiver) variant
        must still be checked.
        """
        # API variant on a service receiver -> excluded (no violation).
        api = (
            "async def f(section_service, client, gid):\n"
            "    await section_service.delete_section(client, gid)\n"
        )
        api_violations, api_guarded = _scan_source(api, "synthetic_api_delete.py")
        assert api_violations == []
        assert api_guarded == 0  # not counted as substrate at all

        # Substrate variant on a storage receiver, missing entity_type -> violation.
        substrate = (
            "async def f(storage, project_gid, section_gid):\n"
            "    await storage.delete_section(project_gid, section_gid)\n"
        )
        sub_violations, _ = _scan_source(substrate, "synthetic_substrate_delete.py")
        assert len(sub_violations) == 1
        assert sub_violations[0].callee == "delete_section"

        # Substrate variant threading entity_type -> guarded.
        substrate_ok = (
            "async def f(storage, project_gid, section_gid, entity_type):\n"
            "    await storage.delete_section(project_gid, section_gid, entity_type)\n"
        )
        ok_violations, ok_guarded = _scan_source(substrate_ok, "synthetic_substrate_ok.py")
        assert ok_violations == []
        assert ok_guarded == 1

    def test_scan_all_purge_is_exempt_not_flagged(self) -> None:
        """The entity-agnostic scan-all purge (D-1b) must NOT be flagged.

        purge_project_all_entities deliberately omits entity_type; the checker
        must treat it as sanctioned-by-design, not a violation.
        """
        src = (
            "async def f(storage, project_gid):\n"
            "    return await storage.purge_project_all_entities(project_gid)\n"
        )
        violations, guarded = _scan_source(src, "synthetic_purge.py")
        assert violations == []
        assert guarded == 0  # exempt callee is neither guarded-threaded nor a violation


class TestSeam1TypedFalsePassClosures:
    """qa-flagged TYPED-pass false-PASS surfaces are closed (G-THEATER hardening)."""

    def test_kwargs_splat_no_longer_auto_passes(self) -> None:
        """``f(gid, **opts)`` is NOT proof of threading -> flagged as a violation.

        Previously an opaque ``**kwargs`` splat made ``_call_threads_entity_type``
        return True (the orphan hid behind 'might carry entity_type'). The
        hardened guard requires an explicit ``entity_type=`` keyword or an
        entity_type-referencing positional.
        """
        red = (
            "async def f(persistence, project_gid, opts):\n"
            "    return await persistence.get_manifest_async(project_gid, **opts)\n"
        )
        violations, _ = _scan_source(red, "synthetic_kwargs_splat.py")
        assert len(violations) == 1, (
            "FALSE-PASS NOT CLOSED: an opaque **kwargs splat still auto-passes "
            "the entity_type threading check -- an orphan can hide behind it."
        )
        assert violations[0].callee == "get_manifest_async"

    def test_dict_literal_splat_with_entity_type_is_honored(self) -> None:
        """``f(gid, **{"entity_type": et})`` IS provably threaded -> guarded."""
        green = (
            "async def f(persistence, project_gid, et):\n"
            '    return await persistence.get_manifest_async(project_gid, **{"entity_type": et})\n'
        )
        violations, guarded = _scan_source(green, "synthetic_dict_splat.py")
        assert violations == []
        assert guarded == 1

    def test_substring_name_decoy_no_longer_passes(self) -> None:
        """A decoy name merely CONTAINING 'entity_type' does NOT count as threading.

        ``entity_typed_flag`` substring-matches the old ``"entity_type" in id``
        check. The boundary-anchored matcher rejects it, so the call is flagged.
        """
        red = (
            "async def f(persistence, project_gid, entity_typed_flag):\n"
            "    return await persistence.get_manifest_async("
            "project_gid, entity_typed_flag)\n"
        )
        violations, _ = _scan_source(red, "synthetic_substring_decoy.py")
        assert len(violations) == 1, (
            "FALSE-PASS NOT CLOSED: a substring-name decoy (entity_typed_flag) "
            "still satisfies the threading check."
        )
        assert violations[0].callee == "get_manifest_async"

    def test_suffix_boundary_name_is_honored(self) -> None:
        """A real threading idiom (``metric_entity_type``) IS honored -> guarded."""
        green = (
            "async def f(persistence, project_gid, metric_entity_type):\n"
            "    return await persistence.get_manifest_async("
            "project_gid, metric_entity_type)\n"
        )
        violations, guarded = _scan_source(green, "synthetic_suffix_name.py")
        assert violations == []
        assert guarded == 1

    def test_non_storage_receiver_decoy_not_counted(self) -> None:
        """A substrate-NAMED method on a non-storage receiver is NOT counted.

        ``http_client.load_dataframe(gid, entity_type)`` uses a substrate method
        NAME on a provably-non-storage receiver. It must not inflate the guarded
        count (which would mask a real substrate-surface shrink).
        """
        decoy = (
            "async def f(http_client, project_gid, entity_type):\n"
            "    return await http_client.load_dataframe(project_gid, entity_type)\n"
        )
        violations, guarded = _scan_source(decoy, "synthetic_nonstorage_decoy.py")
        assert violations == []
        assert guarded == 0, (
            "FALSE-PASS NOT CLOSED: a substrate-named call on a non-storage "
            "receiver (http_client) was counted as a guarded substrate site."
        )

    def test_storage_receiver_still_counted(self) -> None:
        """The real storage-receiver substrate call is still counted (no over-exclusion)."""
        ok = (
            "async def f(storage, project_gid, entity_type):\n"
            "    return await storage.load_dataframe(project_gid, entity_type)\n"
        )
        violations, guarded = _scan_source(ok, "synthetic_storage_ok.py")
        assert violations == []
        assert guarded == 1


class TestSeam1RawKeyStringInventory:
    """NFR-2 raw-key-string pass: ZERO legacy entity-AGNOSTIC section prefixes.

    Closes the F-2 structural blind spot: a reader/writer that bypasses the
    typed substrate methods by building ``f"dataframes/{gid}/sections/"`` and
    listing it directly. Every section key-string in src/ must be
    entity-segmented or rationale-allowlisted.
    """

    def test_no_unsanctioned_legacy_section_key_strings(self) -> None:
        """The telos for raw strings: no entity-AGNOSTIC section prefix orphans.

        F-2 reproduction: before the fix, metrics/__main__.py:458 and :836 built
        the bare ``dataframes/{gid}/sections/`` prefix and read it via
        from_s3_listing -- this test FAILS on those orphans. After routing them
        through from_s3_resolved (entity-segmented), the only legacy literals
        remaining are (a) display-only error strings that never reach a listing
        sink, and (b) the v2-aware resolver's own legacy fallback in the
        sanctioned resolver scopes -- neither is an orphan under the USAGE-aware
        pass.
        """
        violations, guarded = _scan_raw_key_strings()
        assert violations == [], (
            "NFR-2 RAW-STRING VIOLATED -- entity-AGNOSTIC dataframes/{gid}/"
            "sections/ key-string(s) flowing into a listing sink "
            "(from_s3_listing / list_objects_v2 / paginate) without an entity "
            "segment, outside the sanctioned resolver scopes:\n  "
            + "\n  ".join(repr(v) for v in violations)
        )
        # The raw-string pass must actually be guarding something (the two
        # from_s3_resolved entries + the resolver legacy-fallback sink reads).
        assert guarded >= 4, (
            f"raw-string pass guards only {guarded} section sink reads; "
            "expected >=4. If the surface shrank, lower this floor; if 0 the "
            "scan is mis-pointed and this pass is vacuous."
        )

    def test_display_string_does_not_shadow_a_sink_orphan(self) -> None:
        """Usage-aware: a display-only legacy string never shadows a real orphan.

        Closes the qa-flagged allowlist-SHADOW gap. In ONE file, a legacy prefix
        flows into FreshnessError (display) AND a separate legacy prefix flows
        into from_s3_listing (orphan). The display string must be silent; the
        sink orphan must be flagged -- the old (file, needle) allowlist would
        have exempted BOTH because they share a needle.
        """
        mixed = (
            "def cli(project_gid, bucket):\n"
            '    display = f"dataframes/{project_gid}/sections/"\n'
            "    if not bucket:\n"
            '        raise FreshnessError("unknown", "<unset>", display, ValueError("x"))\n'
            '    prefix = f"dataframes/{project_gid}/sections/"\n'
            "    return FreshnessReport.from_s3_listing(\n"
            "        bucket=bucket, prefix=prefix, threshold_seconds=21600\n"
            "    )\n"
        )
        violations, _ = _scan_raw_key_strings_source(mixed, "metrics/__main__.py")
        # Exactly ONE violation -- the sink orphan -- NOT the display string,
        # even though both share the identical legacy literal in the same file.
        assert len(violations) == 1, (
            "SHADOW GAP NOT CLOSED: expected exactly the sink orphan to be "
            f"flagged (display string must be silent); got {len(violations)} "
            f"violations: {[repr(v) for v in violations]}"
        )

    def test_raw_string_pass_FAILS_on_reintroduced_legacy_read(self) -> None:
        """MUTATION PROOF (G-THEATER): a re-introduced bare legacy prefix is flagged.

        Synthesizes the EXACT F-2 orphan shape -- a bare
        ``f"dataframes/{project_gid}/sections/"`` listed via from_s3_listing in a
        non-allowlisted file -- and asserts the raw-string pass reports it. If
        this stops failing, the raw-string pass is theater.
        """
        red = (
            "def read_freshness(project_gid, bucket):\n"
            '    prefix = f"dataframes/{project_gid}/sections/"\n'
            "    return FreshnessReport.from_s3_listing(\n"
            "        bucket=bucket, prefix=prefix, threshold_seconds=21600\n"
            "    )\n"
        )
        violations, _ = _scan_raw_key_strings_source(red, "metrics/orphan_reader.py")
        assert len(violations) == 1, (
            "MUTATION PROOF FAILED: a re-introduced bare legacy section prefix "
            "was NOT flagged -- the raw-string pass is theater."
        )
        assert "dataframes/" in violations[0].template
        assert "/sections/" in violations[0].template

    def test_raw_string_pass_PASSES_on_v2_segmented_prefix(self) -> None:
        """GREEN form: an entity-segmented v2 prefix is NOT flagged."""
        green = (
            "def read_freshness(project_gid, entity_type, bucket):\n"
            '    prefix = f"dataframes/{project_gid}/{entity_type}/sections/"\n'
            "    return FreshnessReport.from_s3_listing(\n"
            "        bucket=bucket, prefix=prefix, threshold_seconds=21600\n"
            "    )\n"
        )
        violations, guarded = _scan_raw_key_strings_source(green, "metrics/v2_reader.py")
        assert violations == []
        assert guarded == 1

    def test_segmentation_check_distinguishes_v2_from_legacy(self) -> None:
        """Unit-level: the segmentation predicate classifies templates correctly."""
        # Legacy entity-AGNOSTIC: gid directly before /sections/.
        assert not _section_prefix_is_entity_segmented("dataframes/{project_gid}/sections/")
        # v2 entity-segmented: explicit entity_type interpolation.
        assert _section_prefix_is_entity_segmented(
            "dataframes/{project_gid}/{entity_type}/sections/"
        )
        # v2 via _entity_segment helper rendering.
        assert _section_prefix_is_entity_segmented("{_entity_segment}/sections/")
        # Two interpolations between dataframes/ and /sections/ -> segmented.
        assert _section_prefix_is_entity_segmented("dataframes/{gid}/{ent}/sections/")
        # Non-section dataframes key -> out of scope (treated as segmented/ok).
        assert _section_prefix_is_entity_segmented(
            "dataframes/{project_gid}/cache-freshness-ttl.json"
        )
