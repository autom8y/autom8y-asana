"""GFR dynamic-tail resolver — the ``is_identity=False``, NAME-keyed contract.

This is the sprint-2 tail (TDD-delta gfr-dynvocab sprint-2 §0, §3, §4). It resolves
a requested field that has NO resolvable dataframe schema owner (the planner routed
it to ``ResolutionPlan.dynamic_fields``, sprint-2 D-T1a) directly off the hydrated
``EntryAnchor.entry_task`` cf manifest (sprint-1's seam). It NEVER touches the
identity spine — ``_resolve_identity_plan_async``, the planner's identity plans, or
``assert_rows_tenant_identity`` — and it issues ZERO new Asana calls (cache-only;
the entry read already produced the task).

The CONTRACT (the load-bearing surface sprint-3 / sprint-4 attach to) is the
three-state result model, expressed in the EXISTING result types with zero schema
churn (§4.2):

* **PRESENT** — the cf is on the task's manifest AND carries a non-null typed value.
  -> ``FieldWithProvenance(value=<typed>, status=FRESH, source=CACHE)``.
* **PRESENT_BUT_NULL** — the cf is on the manifest but its typed value slot is
  null/empty. -> ``FieldWithProvenance(value=None, ...)`` that IS present in the
  returned rows.
* **ABSENT** — the cf is genuinely not on the manifest. -> contributes to
  ``UnresolvedError(reason="unknown-field")`` (governed-strict, all-or-nothing
  within the dynamic subset). The closed reason vocabulary is NOT widened.

**The structural guarantee** (§4.2, what S3/S4 depend on):

    If a field NAME appears as a key in a returned ``ResolvedFields`` row, the cf
    EXISTS on the task (PRESENT or PRESENT_BUT_NULL). If it is genuinely absent the
    whole call already raised ``unknown-field`` and there is no row. A ``value=None``
    in a returned row therefore ALWAYS means present-but-null, NEVER absent.

NAME-keying grain (§0.3): a field is matched against the manifest by
``NameNormalizer.normalize(<requested>) == NameNormalizer.normalize(cf["name"])``. The
cf ``gid`` is a runtime intra-task value handle only — used to locate the cf dict
AFTER the name match, never to key the request.

Typing seam (§5): once a cf is name-matched, its typed value is extracted by
``DefaultCustomFieldResolver._extract_raw_value(cf)`` (``default.py:234-287``) —
REUSED, not reimplemented. That method dispatches on ``resource_subtype``
(text/number/enum/multi_enum/date/people + ``display_value`` fallthrough) and reads
nothing from ``self``, so the tail instantiates one cheap resolver and calls in.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.dataframes.resolver.normalizer import NameNormalizer
from autom8_asana.resolution.gfr.dynvocab_overrides import apply_override
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import (
    FieldStatus,
    FieldWithProvenance,
    ResolvedFields,
    TruthTier,
    TypingOrigin,
)

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.resolution.gfr.entry import EntryAnchor

logger = get_logger(__name__)

# Known Asana cf ``resource_subtype`` values the reused ``_extract_raw_value``
# typing table dispatches on explicitly (``default.py:252-284``). A subtype NOT in
# this set falls through the ``case _`` ``display_value`` arm — heuristically a
# weaker typing, so the tail stamps ``typing_origin='fallback'`` and increments an
# observable counter (FRAME-003 / GAP-8 S5a observability). Kept in lockstep with
# the reused match block; a new Asana subtype that gains a case there is added here.
_KNOWN_CF_SUBTYPES: frozenset[str] = frozenset(
    {"text", "number", "enum", "multi_enum", "date", "people"}
)

# FRAME-003 fallthrough counter. Module-level so S5a (Asana's yearly new cf
# subtypes silently degrading to strings) is OBSERVABLE rather than invisible.
# Read via ``fallthrough_count()``; incremented on each ``case _`` extraction.
_FALLTHROUGH_COUNT: int = 0


def fallthrough_count() -> int:
    """Return the running count of unknown-cf-subtype fallthroughs (FRAME-003).

    Each time the tail extracts a cf whose ``resource_subtype`` is not in
    ``_KNOWN_CF_SUBTYPES`` (the ``case _`` ``display_value`` arm), this counter is
    incremented and the field is stamped ``typing_origin='fallback'``. Operability
    surface for S5a: a rising count signals Asana shipped a cf subtype the typing
    table does not yet handle explicitly.
    """
    return _FALLTHROUGH_COUNT


class DynFieldState(StrEnum):
    """The governed-strict three-state discriminator (TDD §4.1).

    Names the distinction the live platform actually exhibits (PT-01: Asset ID
    present 15/15, populated 0/15 — present-but-null is real, not hypothetical).
    Sprint-3 enriches PRESENT_BUT_NULL -> PRESENT (date hole) and PRESENT.value
    (override) without re-opening this enum; sprint-4 reads the same manifest. The
    enum is FROZEN as the contract surface — neither S3 nor S4 may widen it.
    """

    PRESENT = "present"  # cf on manifest, typed value non-null
    PRESENT_BUT_NULL = "present-but-null"  # cf on manifest, typed value null/empty
    ABSENT = "absent"  # cf not on manifest -> unknown-field


def _is_null(raw: object) -> bool:
    """Present-but-null predicate — the inverse of the GAP-1 probe's ``_is_populated``.

    Mirrors ``scripts/gfr_dynvocab/gap1_probe.py`` so the live PT-01 verdict and the
    production tail judge "populated" identically: ``None``, the empty string, and
    the empty list/collection all count as null (present-but-null), so a cf whose
    value slot is unfetched or empty is PRESENT_BUT_NULL, never silently dropped.
    """
    if raw is None:
        return True
    if isinstance(raw, str):
        return raw == ""
    if isinstance(raw, (list, tuple, set, dict)):
        return len(raw) == 0
    return False


def _typed_value(cf: dict[str, Any], resolver: Any) -> tuple[object, str | None]:
    """Extract the typed value for a name-matched cf by REUSING the typing table.

    ``DefaultCustomFieldResolver._extract_raw_value`` (``default.py:234-287``) is the
    heuristic typing table — it dispatches on ``resource_subtype`` and reads only the
    passed ``cf`` dict (nothing from ``self``). The tail does NOT author its own table
    (TDD §5); it calls into the existing dispatch via the descriptor-selected resolver.

    Returns ``(raw_value, cf_type)`` where ``cf_type`` is the cf's
    ``resource_subtype`` (FRAME-004 provenance). The date arm of the reused table
    reads ``date_value`` (FRAME-003 closes the LIVE hole by adding
    ``custom_fields.date_value`` to the opt-fields so the live fetch carries it).

    UV-P resolution (TDD §5.2): the call to a leading-underscore method is the
    lower-risk form here — promoting ``_extract_raw_value`` to a module-level pure
    function would touch shared dataframe code (``default.py``) for no behavioral gain.
    The CONTRACT (reuse the existing dispatch, do not reimplement) holds.
    """
    cf_type = cf.get("resource_subtype")
    return resolver._extract_raw_value(cf), cf_type


def _apply_override(field_name: str, entity_type: str, raw: object) -> object:
    """Apply a registered NAME-keyed, EntityType-scoped override (FRAME-002).

    Delegates to the override registry (``dynvocab_overrides``). For a field with no
    registered override the raw value passes through unchanged (the default-identity
    contract sprint-2 left). The worked example: ``asset_id`` text "a, b ,c" ->
    ``{"a","b","c"}`` (SET) on an Offer entry. A SECOND override is a DATA addition
    to ``OVERRIDE_REGISTRY``, not a change to this function.
    """
    return apply_override(field_name, entity_type, raw)


def _resolve_custom_field_resolver(entity_type: str) -> Any:
    """Select the cf resolver descriptor-driven (TDD §6, D-T4).

    Reads ``EntityDescriptor.custom_field_resolver_class_path`` (``entity_registry``
    :136/:189) for the entry entity type and instantiates that class — keeping the
    typing/override policy descriptor-driven so sprint-4 generality is "register an
    EntityConfig + set the resolver-class-path", NOT an engine edit. Sprint-2 adds or
    changes NO descriptor value; it only READS the hook. Falls back to
    ``DefaultCustomFieldResolver`` when no path is set on the descriptor.

    UV-P resolution (TDD §6): the 3-line descriptor->import->instantiate is inlined
    here rather than reusing ``UniversalResolutionStrategy._get_custom_field_resolver``
    to avoid pulling the heavy ``universal_strategy`` dependency graph into the thin
    GFR tail. The descriptor-driven CONTRACT (selection via the ``:136`` hook) holds.
    """
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver

    descriptor = get_registry().get(entity_type)
    class_path = descriptor.custom_field_resolver_class_path if descriptor is not None else None
    if class_path:
        import importlib

        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()
    return DefaultCustomFieldResolver()


def _build_manifest(custom_fields: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Build the NAME-keyed cf manifest — the governed-strict absence oracle (§3.1).

    Index ``normalize(cf["name"]) -> cf_dict``, first-match-wins (mirrors
    ``default.py:84-90``). The manifest's key SET is the authoritative present-set:
    a requested field whose normalized name is NOT a key is genuinely absent
    (ABSENT -> unknown-field); a field that IS a key has its cf located here, then
    typed. cfs with no/empty name are skipped (cannot be name-matched).
    """
    manifest: dict[str, dict[str, Any]] = {}
    for cf in custom_fields or ():
        if not isinstance(cf, dict):
            continue
        name = cf.get("name")
        if not name:
            continue
        norm = NameNormalizer.normalize(name)
        if not norm:
            continue
        # First-match-wins (mirrors the resolver index): a later duplicate name does
        # not clobber the earlier cf.
        manifest.setdefault(norm, cf)
    return manifest


class DynVocabResolver:
    """The ``is_identity=False`` NAME-keyed dynamic tail (TDD §3.1).

    Builds the NAME-keyed manifest off ``entry_task.custom_fields``; resolves each
    requested field to the three-state model; reuses ``_extract_raw_value`` for
    cf-type -> value extraction; emits the GAP-10 structured logging + manifest
    metric. Holds no field-specific code — the typing table lives in the reused
    resolver, the absence oracle is the manifest key set.
    """

    def __init__(self, anchor: EntryAnchor) -> None:
        self._anchor = anchor
        entry_task = anchor.entry_task
        custom_fields = getattr(entry_task, "custom_fields", None) if entry_task else None
        build_start = time.perf_counter()
        self._manifest = _build_manifest(custom_fields)
        build_us = (time.perf_counter() - build_start) * 1_000_000
        self._cf_count = len(custom_fields) if custom_fields else 0
        self._resolver = _resolve_custom_field_resolver(anchor.entity_type.value)
        # GAP-10: manifest-build + len(custom_fields) metric at the entry seam.
        logger.debug(
            "GFR tail: manifest built",
            extra={
                "gid": anchor.gid,
                "entity_type": anchor.entity_type.value,
                "custom_fields_count": self._cf_count,
                "manifest_size": len(self._manifest),
                "build_us": round(build_us, 2),
            },
        )

    def _resolve_one(
        self, field: str
    ) -> tuple[DynFieldState, object, TypingOrigin | None, str | None]:
        """Resolve a single requested field against the manifest (TDD §4.1).

        Returns ``(state, value, typing_origin, cf_type)``. NAME-keyed: matches on
        ``normalize(field)``; the cf ``gid`` is never the key. ABSENT carries a
        ``None`` value and ``None`` provenance (it never reaches a returned row);
        PRESENT_BUT_NULL carries ``None`` value but DOES carry ``cf_type`` +
        ``typing_origin`` (present in the row); PRESENT carries the typed
        (override-applied) value with full provenance.

        Provenance (FRAME-004): ``typing_origin`` reflects how the RETURNED value
        was actually derived. Precedence (an applied override is the last transform
        that produced the value, so it wins):
          * ``override``  — a NAME-keyed, EntityType-scoped override ACTUALLY
            transformed the raw value (e.g. asset_id text -> SET). Stamped iff the
            override applied (a distinct object came back), NOT merely registered;
            a declined/no-op override (boundary discipline returns raw unchanged)
            does NOT claim 'override'. Wins even under fallthrough;
          * ``fallback``  — no override transformed the value AND the cf
            ``resource_subtype`` is unknown (``case _`` ``display_value`` arm). The
            FRAME-003 fallthrough counter increments on the unknown subtype
            regardless of the stamp (decoupled — S5a observability);
          * ``heuristic`` — a known-subtype extraction with no applied override.
        """
        global _FALLTHROUGH_COUNT
        norm = NameNormalizer.normalize(field)
        cf = self._manifest.get(norm)
        if cf is None:
            return DynFieldState.ABSENT, None, None, None

        raw, cf_type = _typed_value(cf, self._resolver)
        entity_value = self._anchor.entity_type.value

        # FRAME-003 fallthrough observability: an unknown subtype was typed via the
        # case _ display_value arm. Stamp 'fallback' and increment the counter.
        is_fallthrough = cf_type not in _KNOWN_CF_SUBTYPES
        if is_fallthrough:
            _FALLTHROUGH_COUNT += 1
            logger.info(
                "GFR tail: unknown cf subtype fallthrough (display_value)",
                extra={
                    "gid": self._anchor.gid,
                    "field": field,
                    "cf_subtype": cf_type,
                    "fallthrough_count": _FALLTHROUGH_COUNT,
                },
            )

        # PRESENT_BUT_NULL is judged on the RAW extracted value, BEFORE the override
        # (the override never manufactures a value from an empty raw — boundary
        # discipline in dynvocab_overrides). This keeps the null predicate stable
        # whether or not a field carries an override.
        if _is_null(raw):
            origin: TypingOrigin = "fallback" if is_fallthrough else "heuristic"
            logger.debug(
                "GFR tail: present-but-null",
                extra={
                    "gid": self._anchor.gid,
                    "field": field,
                    "cf_subtype": cf_type,
                },
            )
            return DynFieldState.PRESENT_BUT_NULL, None, origin, cf_type

        value = _apply_override(field, entity_value, raw)
        # Provenance precedence (honest derivation, FRAME-004 self-defect fix): the
        # stamp must reflect how the RETURNED value was actually derived, not merely
        # which transforms were registered. ``apply_override`` returns the SAME object
        # it was handed (``return raw``) when it declines — either no override is
        # registered OR the override's boundary discipline no-ops (e.g. asset_id
        # whitespace/comma-only '  ,  ' returns raw UNCHANGED). It returns a DISTINCT
        # object (a fresh SET) only when a transform actually ran. So ``value is not
        # raw`` is the precise "an override actually transformed the value" predicate.
        #
        #   * an APPLIED override produced the returned value -> 'override' (it is the
        #     last transform in the chain, so it wins even under fallthrough);
        #   * else an unknown subtype (``is_fallthrough``) -> 'fallback';
        #   * else a known-subtype straight extraction -> 'heuristic'.
        #
        # The fallthrough COUNTER (above) is decoupled from this stamp: it already
        # incremented on the unknown subtype for S5a observability, regardless of
        # whether an override later transformed the value.
        if value is not raw:
            origin = "override"
        elif is_fallthrough:
            origin = "fallback"
        else:
            origin = "heuristic"
        return DynFieldState.PRESENT, value, origin, cf_type

    def resolve(
        self,
        fields: list[str],
        *,
        source: TruthTier,
        as_of: datetime | None,
    ) -> ResolvedFields:
        """Resolve the dynamic field subset to a single-row ``ResolvedFields``.

        Governed-strict, all-or-nothing within the dynamic subset: if ANY requested
        field is genuinely ABSENT from the manifest, the WHOLE dynamic call raises
        ``UnresolvedError(reason="unknown-field")`` carrying every absent field
        (consistent with INVARIANT I4 and the planner's prior unknown-field
        semantics). Otherwise every requested field — PRESENT or PRESENT_BUT_NULL —
        appears as a key in the single returned row (the §4.2 structural guarantee).

        The entry task is one entity, so the tail produces exactly one row
        (``row_count == 1``; INVARIANT I5 row-set-native-safe).
        """
        resolved_row: dict[str, FieldWithProvenance] = {}
        absent: list[str] = []
        for field in fields:
            state, value, typing_origin, cf_type = self._resolve_one(field)
            logger.debug(
                "GFR tail: field resolved",
                extra={
                    "gid": self._anchor.gid,
                    "field": field,
                    "state": state.value,
                    "typing_origin": typing_origin,
                    "cf_type": cf_type,
                },
            )
            if state is DynFieldState.ABSENT:
                absent.append(field)
                continue
            # PRESENT or PRESENT_BUT_NULL: the field NAME IS a key in the row. A
            # value=None here therefore ALWAYS means present-but-null (§4.2). The
            # provenance tags (FRAME-004) ride along additively.
            resolved_row[field] = FieldWithProvenance(
                value=value,
                status=FieldStatus.FRESH,
                source=source,
                as_of=as_of,
                typing_origin=typing_origin,
                cf_type=cf_type,
            )

        if absent:
            # Governed-strict absence: judged against the real manifest, not guessed
            # from schema-absence. The closed reason vocab is NOT widened.
            logger.info(
                "GFR tail: unknown field (governed-strict)",
                extra={
                    "gid": self._anchor.gid,
                    "absent_fields": absent,
                    "manifest_size": len(self._manifest),
                },
            )
            raise UnresolvedError(fields=absent, reason="unknown-field")

        return ResolvedFields(gid=self._anchor.gid, rows=[resolved_row], row_count=1)


def resolve_dynamic_fields(
    *,
    anchor: EntryAnchor,
    fields: list[str],
    source: TruthTier = TruthTier.CACHE,
    as_of: datetime | None = None,
) -> ResolvedFields:
    """Tail entry the engine calls for the dynamic (no-schema-owner) field subset.

    Cache-only (TDD §8.2): reads ``anchor.entry_task`` — the object the entry fetch
    already produced and sprint-1 threaded — with ZERO new Asana calls. NAME-keyed
    end-to-end; the closed ``unknown-field`` vocabulary is preserved on genuine
    absence (governed-strict, all-or-nothing within the subset).

    Args:
        anchor: The entry anchor; ``anchor.entry_task`` carries the cf manifest.
        fields: The dynamic field subset (``ResolutionPlan.dynamic_fields``).
        source: Provenance tier to stamp (CACHE — the tail is cache-only).
        as_of: Optional frame watermark to stamp on each resolved field.

    Returns:
        A single-row ``ResolvedFields`` for the dynamic subset.

    Raises:
        UnresolvedError(reason="unknown-field"): if any field is genuinely absent
            from the manifest (governed-strict; closed vocab unchanged).
    """
    return DynVocabResolver(anchor).resolve(fields, source=source, as_of=as_of)
