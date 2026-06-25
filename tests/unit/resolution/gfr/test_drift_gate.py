"""Tests for the model<->schema drift gate (FRAME-005) + generality (FRAME-006).

Per ADR-gfr-dynvocab-drift-gate (SPRINT-4). The gate DETECTS divergence between
an entity's task-model ``field_name`` set (materialized into ``cls.Fields`` from
the ADR-0082 ``_pending_fields`` registry) and that entity's DataFrame schema
cf/cascade-name coverage. It is NAME-keyed (model ``field_name`` <-> schema
``cf:Name``/``cascade:Name`` suffix), warn-first, and non-fatal at real import.

Two altitudes are exercised:

- **Pure detector** (``detect_model_schema_drift``): the RED-assertable surface.
  A deliberately-divergent fixture drives the detector to return a non-empty
  drift set, which these tests assert on directly. This is the behavioral
  activation probe -- a signal that PROVES the integrated path is functional
  (the detector catches a real divergence), not merely alive.
- **Emitter** (``SchemaRegistry._validate_model_schema_coverage``): the
  warn-first side effect. With the real (already-drifted: Offer "Asset ID")
  registry it emits a structured ``model_schema_drift_detected`` warning and a
  ``ModelSchemaDrift`` metric WITHOUT raising -- so the 184-test floor and prod
  startup stay GREEN.

FRAME-006 generality: the gate iterates ``get_registry().all_descriptors()`` with
zero entity-special-casing, so it covers Offer + Business + Unit (>=3 EntityTypes)
through the identical loop. Adding a NEW EntityType is honest code (an
EntityDescriptor entry + override-context addition) -- the generality claim is
"the same mechanism covers >=3 EntityTypes with no entity-special-casing", NOT
"a new EntityType needs no code".
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from autom8_asana.core.entity_registry import _resolve_dotted_path, get_registry
from autom8_asana.dataframes.models.registry import (
    DRIFT_EXCLUSIONS,
    SchemaRegistry,
    detect_model_schema_drift,
    model_field_names,
    model_fields_are_extractable,
    schema_cf_cascade_count,
    schema_covered_names,
)

pytestmark = [pytest.mark.xdist_group("gfr_drift_gate")]


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset the SchemaRegistry singleton around each test for isolation."""
    SchemaRegistry.reset()
    yield
    SchemaRegistry.reset()


def _run_validator_over(
    descriptors: list[SimpleNamespace],
    path_map: dict[str, object],
) -> list[tuple[str, dict]]:
    """Drive the REAL ``_validate_model_schema_coverage`` over synthetic descriptors.

    The validator imports ``get_registry`` + ``_resolve_dotted_path`` from
    ``entity_registry`` at call time, so patching those module attributes feeds it
    our synthetic descriptor set and resolution map. ``get_logger`` is patched on
    the registry module to capture the structured warnings. This exercises the REAL
    extraction + routing path (NOT a pre-built drift frozenset) -- the only way to
    reproduce the ``model_field_names`` empty-extraction blind spot end to end.

    Returns the ``(event_name, extra)`` tuples the gate emitted. The direct call
    here also asserts warn-first: ``_validate_model_schema_coverage`` MUST NOT raise.
    """
    fake_registry = SimpleNamespace(all_descriptors=lambda: list(descriptors))

    def _fake_resolve(path: str) -> object:
        return path_map[path]

    registry = SchemaRegistry.get_instance()
    with (
        patch(
            "autom8_asana.core.entity_registry.get_registry",
            return_value=fake_registry,
        ),
        patch(
            "autom8_asana.core.entity_registry._resolve_dotted_path",
            side_effect=_fake_resolve,
        ),
        patch("autom8_asana.dataframes.models.registry.get_logger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        registry._validate_model_schema_coverage()  # warn-first: must not raise
        return [
            (c.args[0], c.kwargs.get("extra", {}))
            for c in mock_logger.warning.call_args_list
            if c.args
        ]


def _desc(
    name: str,
    *,
    model_path: str | None = None,
    schema_path: str | None = None,
    entity_type_name: str | None = "OFFER",
) -> SimpleNamespace:
    """A minimal EntityDescriptor stand-in for the gate's loop (name + two paths)."""
    return SimpleNamespace(
        name=name,
        model_class_path=model_path,
        schema_module_path=schema_path,
        entity_type=(SimpleNamespace(name=entity_type_name) if entity_type_name else None),
    )


class _EmptyFieldsModel:
    """A model whose ``Fields`` class declares NO public str constants.

    ``Fields`` is present (not None) but ``model_field_names`` yields ``frozenset()``
    -- the residual silent-false-green the TERMINATING fix closes. Pre-fix this
    reported extractable=True (Fields-class present) and fell through to a silent
    ``ModelSchemaDrift=0.0``.
    """

    class Fields:
        pass


class _AllPrivateFieldsModel:
    """A model whose ``Fields`` class declares only private / non-str members.

    ``Fields`` is present, but every member is leading-underscore (skipped) or
    non-str (skipped), so ``model_field_names`` is empty -- another member of the
    same empty-extraction class that must route to UNANALYZABLE, not coherent.
    """

    class Fields:
        _x = 1
        _hidden = "private-so-skipped"


class _BaseEmptyFields:
    """An empty parent ``Fields`` base (declares no cf display constants)."""


class _BaseFieldsWithConstants:
    """A parent ``Fields`` base carrying real SCREAMING_SNAKE cf display constants.

    The cf names live ONLY on this base; a child ``Fields`` that subclasses it with
    no own members reaches them solely through the class MRO.
    """

    ASSET_ID = "Asset ID"
    OFFER_NAME = "Offer Name"


class _InheritedEmptyFieldsModel:
    """A model whose ``Fields`` is inherited-but-empty (subclasses an empty base).

    ``Fields`` declares no own members AND its base declares none either, so
    ``model_field_names`` is empty regardless of MRO traversal -- the inherited-empty
    member of the empty-extraction class the ``model_fields_are_extractable`` docstring
    claims is covered. Must route to UNANALYZABLE, never a silent coherent.
    """

    class Fields(_BaseEmptyFields):
        pass


class _InheritedRealFieldsModel:
    """A model whose ``Fields`` INHERITS real cf constants from a parent ``Fields`` base.

    ``Fields`` declares NO own members but subclasses ``_BaseFieldsWithConstants``,
    so the cf display names are reachable ONLY via the class MRO. ``model_field_names``
    iterates ``dir(fields_cls)`` (which walks the MRO), so it extracts the inherited
    names and this model is correctly EXTRACTABLE. This is the complement that makes
    the inherited-empty claim a real contract: a refactor swapping ``dir()`` -> ``vars()``
    (own-attrs only) would stop seeing the inherited constants, report this empty, and
    wrongly route a genuinely-analyzable model to UNANALYZABLE.
    """

    class Fields(_BaseFieldsWithConstants):
        pass


class _NonStrUpperConstFieldsModel:
    """A model whose ``Fields`` declares an UPPERCASE but NON-str constant.

    ``ASSET_ID = 12345`` is public + SCREAMING_SNAKE but not a ``str``, so the
    ``isinstance(value, str)`` filter in ``model_field_names`` skips it and extraction
    is empty -- the non-str-constant boundary of the empty-extraction class.
    """

    class Fields:
        ASSET_ID = 12345


# ---------------------------------------------------------------------------
# Pure detector -- the RED-assertable surface (no I/O, no logging)
# ---------------------------------------------------------------------------


class TestDetectorRedOnDivergence:
    """The detector fires (returns a non-empty drift set) on real divergence."""

    def test_deliberately_divergent_field_is_red(self) -> None:
        """A model field with NO schema coverage is reported as drift.

        This is the deliberately-divergent fixture: a planted field_name that no
        schema column covers MUST appear in the returned drift set. This is the
        assertable RED -- it proves the detector is behaviorally active, not inert.
        """
        model_names = frozenset({"Asset ID", "Office Phone", "Deliberately Missing"})
        schema_names = frozenset({"Office Phone"})

        drift = detect_model_schema_drift(model_names, schema_names, exclusions=frozenset())

        assert "Deliberately Missing" in drift
        assert "Asset ID" in drift
        assert "Office Phone" not in drift  # covered -> not drift
        assert len(drift) == 2

    def test_coherent_model_has_empty_drift(self) -> None:
        """When every model field is covered, the detector returns an empty set."""
        model_names = frozenset({"Office Phone", "Vertical"})
        schema_names = frozenset({"Office Phone", "Vertical", "Extra Column"})

        drift = detect_model_schema_drift(model_names, schema_names, exclusions=frozenset())

        assert drift == frozenset()

    def test_detector_is_name_keyed_not_gid_keyed(self) -> None:
        """Matching is by normalized NAME, never by gid.

        "Weekly AD Spend" (model casing) and "Weekly Ad Spend" (schema casing)
        normalize identically and MUST be treated as covered -- NAME-keyed, not
        gid-keyed, and case/whitespace-agnostic via the canonical NameNormalizer.
        """
        model_names = frozenset({"Weekly AD Spend"})
        schema_names = frozenset({"Weekly Ad Spend"})

        drift = detect_model_schema_drift(model_names, schema_names, exclusions=frozenset())

        assert drift == frozenset()

    def test_underscore_and_titlecase_normalize_equal(self) -> None:
        """snake_case schema names match Title Case model names (tail convention)."""
        model_names = frozenset({"Office Phone"})
        schema_names = frozenset({"office_phone"})

        drift = detect_model_schema_drift(model_names, schema_names, exclusions=frozenset())

        assert drift == frozenset()

    def test_explicit_exclusion_suppresses_drift(self) -> None:
        """An explicitly-excluded field is NOT counted as drift.

        Per the telos predicate -- drift fails "without an explicit exclusion".
        The named-deferral surface converts a silent gap into an owned decision.
        """
        model_names = frozenset({"Asset ID", "Genuinely Missing"})
        schema_names = frozenset({"Office Phone"})

        drift = detect_model_schema_drift(
            model_names, schema_names, exclusions=frozenset({"Asset ID"})
        )

        assert "Asset ID" not in drift
        assert "Genuinely Missing" in drift

    def test_exclusion_is_name_normalized(self) -> None:
        """Exclusions match by the same normalization as coverage."""
        model_names = frozenset({"Asset ID"})
        schema_names = frozenset()

        drift = detect_model_schema_drift(
            model_names, schema_names, exclusions=frozenset({"asset_id"})
        )

        assert drift == frozenset()


# ---------------------------------------------------------------------------
# Coverage/field extraction helpers (pure)
# ---------------------------------------------------------------------------


class TestCoverageExtraction:
    """schema_covered_names reads cf:/cascade: source suffixes + column names."""

    def test_schema_covered_names_reads_cf_and_cascade_sources(self) -> None:
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        schema = _resolve_dotted_path(offer_desc.schema_module_path)

        covered = schema_covered_names(schema)

        # cf: source -> the suffix is covered
        assert "Offer ID" in covered
        # cascade: source -> the suffix is covered (covered, just from an ancestor)
        assert "Office Phone" in covered
        # plain column name is covered too
        assert "name" in covered

    def test_model_field_names_reads_fields_registry(self) -> None:
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        model = _resolve_dotted_path(offer_desc.model_class_path)

        names = model_field_names(model)

        # The canonical drift instance: Offer model declares "Asset ID".
        assert "Asset ID" in names
        # And declares covered fields too.
        assert "Offer ID" in names


# ---------------------------------------------------------------------------
# Emitter -- warn-first, non-fatal (keeps the 184 floor GREEN)
# ---------------------------------------------------------------------------


class TestEmitterWarnFirst:
    """The validator emits a structured warning + metric and NEVER raises."""

    def test_validate_does_not_raise_on_real_drift(self) -> None:
        """Real registry (Offer "Asset ID" drift is present today) -> no raise."""
        registry = SchemaRegistry.get_instance()
        # Force initialization (which invokes the validator under try/except).
        registry.get_schema("Offer")
        # Direct invocation must also be non-fatal.
        registry._validate_model_schema_coverage()  # must not raise

    def test_offer_asset_id_drift_is_observed(self) -> None:
        """The structured warning carries Offer "Asset ID" in drifted_fields."""
        registry = SchemaRegistry.get_instance()
        registry.get_schema("Offer")

        with patch("autom8_asana.dataframes.models.registry.get_logger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            registry._validate_model_schema_coverage()

            # Find the model_schema_drift_detected warning for offer.
            offer_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if c.args
                and c.args[0] == "model_schema_drift_detected"
                and c.kwargs.get("extra", {}).get("entity") == "offer"
            ]
            assert offer_calls, "expected a model_schema_drift_detected warning for offer"
            extra = offer_calls[0].kwargs["extra"]
            assert "Asset ID" in extra["drifted_fields"]
            assert extra["drift_count"] > 0
            assert extra["metrics"]["ModelSchemaDrift"] == float(extra["drift_count"])

    def test_warn_mode_is_the_default(self) -> None:
        """Default DRIFT_GATE_MODE is "warn" -- the gate ships warn-first."""
        from autom8_asana.dataframes.models import registry as reg_mod

        assert reg_mod.DRIFT_GATE_MODE == "warn"

    def test_validator_runs_during_ensure_initialized(self) -> None:
        """The gate is wired into _ensure_initialized (the import-time path)."""
        registry = SchemaRegistry.get_instance()
        with patch.object(
            registry,
            "_validate_model_schema_coverage",
            wraps=registry._validate_model_schema_coverage,
        ) as spy:
            registry.get_schema("Offer")
            assert spy.called


# ---------------------------------------------------------------------------
# FRAME-006 -- generality across >=3 EntityTypes, no special-casing
# ---------------------------------------------------------------------------


class TestUnanalyzableNotSilentGreen:
    """PT-04 remediation: an entity the gate CANNOT analyze must fail loud.

    The drift gate exists to kill silent false-greens. But ``model_field_names``
    extracts cf-field names ONLY from ``cls.Fields`` (the BusinessEntity
    Fields-generation path). A ``*_holder`` entity inherits from ``HolderFactory``
    (NOT ``BusinessEntity``), so it has NO ``Fields`` class and yields an empty
    field set -- yet its schema can still declare a cf/cascade column (e.g.
    ``asset_edit_holder`` declares ``cascade:Office Phone``). Pre-remediation the
    detector returned ``frozenset()`` for it -> ``ModelSchemaDrift=0.0`` ->
    "coherent", a LATENT FALSE-GREEN identical in shape to the production KeyError
    class the gate was built to prevent.

    The fix: COHERENT (analyzed, no drift) and UNANALYZABLE (could not analyze the
    model's cf fields at all) must be DISTINGUISHABLE. An entity whose schema
    declares cf/cascade columns but whose ``model_field_names`` is empty emits a
    DISTINCT ``model_schema_coverage_unanalyzable`` signal with a distinct
    ``ModelSchemaCoverageUnanalyzable=1.0`` metric -- never a silent
    ``ModelSchemaDrift=0.0``.

    These tests drive the EXTRACTION layer end-to-end through
    ``_validate_model_schema_coverage`` (NOT by feeding the detector a pre-built
    frozenset), so they exercise the real ``model_field_names`` blind spot.
    """

    def test_holder_with_schema_cf_but_no_fields_is_unanalyzable_not_silent_green(
        self,
    ) -> None:
        """asset_edit_holder (0 Fields, schema 'cascade:Office Phone') -> UNANALYZABLE.

        This is the RED-assertable extraction-layer false-green. The real
        ``asset_edit_holder`` model has NO ``Fields`` class (it is a HolderFactory
        subclass, not a BusinessEntity), so ``model_field_names`` returns empty --
        but its schema declares ``cascade:Office Phone``. The gate MUST emit the
        distinct unanalyzable signal, and MUST NOT report it coherent via a silent
        ``model_schema_drift_detected`` with ``ModelSchemaDrift=0.0``.
        """
        # Precondition: this is the genuine extraction blind spot, asserted
        # structurally so the test fails loud if the model ever grows a Fields class.
        holder_desc = next(
            d for d in get_registry().all_descriptors() if d.name == "asset_edit_holder"
        )
        assert holder_desc.model_class_path and holder_desc.schema_module_path
        model = _resolve_dotted_path(holder_desc.model_class_path)
        schema = _resolve_dotted_path(holder_desc.schema_module_path)
        assert model_field_names(model) == frozenset(), (
            "fixture invariant: asset_edit_holder must have NO extractable cf fields"
        )
        cf_cascade_cols = [
            c.source
            for c in schema.columns
            if c.source and (c.source.startswith("cf:") or c.source.startswith("cascade:"))
        ]
        assert cf_cascade_cols, (
            "fixture invariant: asset_edit_holder schema must declare a cf/cascade column"
        )

        registry = SchemaRegistry.get_instance()
        registry.get_schema("AssetEditHolder")

        with patch("autom8_asana.dataframes.models.registry.get_logger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            registry._validate_model_schema_coverage()

            warning_calls = mock_logger.warning.call_args_list

            # The DISTINCT unanalyzable signal fires for the holder.
            unanalyzable_calls = [
                c
                for c in warning_calls
                if c.args
                and c.args[0] == "model_schema_coverage_unanalyzable"
                and c.kwargs.get("extra", {}).get("entity") == "asset_edit_holder"
            ]
            assert unanalyzable_calls, (
                "expected a model_schema_coverage_unanalyzable warning for "
                "asset_edit_holder (schema cf/cascade col + empty model fields) -- "
                "the gate MUST fail loud, not silently report coherent"
            )
            extra = unanalyzable_calls[0].kwargs["extra"]
            # Distinct metric, NOT a silent ModelSchemaDrift=0.0.
            assert extra["metrics"]["ModelSchemaCoverageUnanalyzable"] == 1.0
            assert "ModelSchemaDrift" not in extra["metrics"]
            # It names WHY it could not analyze (no Fields) and WHAT it could not check.
            assert extra["schema_cf_cascade_count"] >= 1

            # And the holder MUST NOT be reported as coherent via a drift signal
            # carrying ModelSchemaDrift=0.0 (the silent false-green shape).
            holder_drift_calls = [
                c
                for c in warning_calls
                if c.args
                and c.args[0] == "model_schema_drift_detected"
                and c.kwargs.get("extra", {}).get("entity") == "asset_edit_holder"
            ]
            assert not holder_drift_calls, (
                "asset_edit_holder must NOT emit a model_schema_drift_detected signal "
                "-- it is unanalyzable, not coherent"
            )

    def test_unanalyzable_emitter_does_not_raise_in_warn_mode(self) -> None:
        """The unanalyzable path is warn-first: it logs + returns, never raises."""
        registry = SchemaRegistry.get_instance()
        registry.get_schema("AssetEditHolder")
        # Direct invocation must also be non-fatal even with the unanalyzable holder.
        registry._validate_model_schema_coverage()  # must not raise

    def test_coherent_entity_control_stays_quiet_on_unanalyzable_signal(self) -> None:
        """Control: an ANALYZABLE entity (offer) never emits the unanalyzable signal.

        Offer has a ``Fields`` class (model_field_names non-empty), so it is
        analyzable. It may emit ``model_schema_drift_detected`` (real Asset ID
        drift), but it MUST NOT emit ``model_schema_coverage_unanalyzable``. This
        proves UNANALYZABLE is reserved for the could-not-analyze case and is not
        a noisy blanket signal.
        """
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        model = _resolve_dotted_path(offer_desc.model_class_path)
        assert model_field_names(model), (
            "control invariant: offer must be analyzable (non-empty model fields)"
        )

        registry = SchemaRegistry.get_instance()
        registry.get_schema("Offer")

        with patch("autom8_asana.dataframes.models.registry.get_logger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            registry._validate_model_schema_coverage()

            offer_unanalyzable = [
                c
                for c in mock_logger.warning.call_args_list
                if c.args
                and c.args[0] == "model_schema_coverage_unanalyzable"
                and c.kwargs.get("extra", {}).get("entity") == "offer"
            ]
            assert not offer_unanalyzable, (
                "offer is analyzable -- it must NOT emit the unanalyzable signal"
            )


class TestGeneralityAcrossEntityTypes:
    """The gate covers >=3 EntityTypes through the descriptor registry loop."""

    def test_at_least_three_entitytypes_are_checked(self) -> None:
        """Offer + Business + Unit (and more) all carry model+schema -> checked.

        The gate iterates all_descriptors() and checks every descriptor with BOTH
        a model_class_path and a schema_module_path. This is the same loop the
        schema auto-wire uses -- no entity is special-cased.
        """
        checkable = [
            d
            for d in get_registry().all_descriptors()
            if d.model_class_path and d.schema_module_path
        ]
        names = {d.name for d in checkable}

        assert {"offer", "business", "unit"} <= names
        assert len(checkable) >= 3

    def test_drift_detected_for_each_of_three_entitytypes(self) -> None:
        """Each of Offer/Business/Unit produces a drift set via the SAME path.

        No per-entity branch: the identical model_field_names + schema_covered_names
        + detect_model_schema_drift pipeline runs for each. This proves generality
        empirically -- the mechanism is entity-agnostic.
        """
        for name in ("offer", "business", "unit"):
            desc = next(d for d in get_registry().all_descriptors() if d.name == name)
            model = _resolve_dotted_path(desc.model_class_path)
            schema = _resolve_dotted_path(desc.schema_module_path)

            drift = detect_model_schema_drift(
                model_field_names(model),
                schema_covered_names(schema),
                exclusions=DRIFT_EXCLUSIONS.get(name, frozenset()),
            )
            # Each of these three has real, present drift today (no exclusions yet).
            assert isinstance(drift, frozenset)
            assert drift, f"expected present drift for {name} (real divergence)"

    def test_no_entity_special_casing_in_detector_signature(self) -> None:
        """The detector takes only name-sets + exclusions -- no EntityType arg.

        A detector that special-cased entities would need an entity/EntityType
        parameter to branch on. Its signature proves it cannot: it is purely a
        set operation over normalized names.
        """
        import inspect

        sig = inspect.signature(detect_model_schema_drift)
        params = set(sig.parameters)
        assert params == {"model_field_names", "schema_cf_names", "exclusions"}


# ---------------------------------------------------------------------------
# TERMINATING fix (item 1): extractability re-keyed on model_field_names
# NON-EMPTINESS, not Fields-class presence. The residual silent-false-green:
# a model with a present-but-empty (or all-private) Fields class extracts ZERO
# names, yet pre-fix reported extractable=True -> a silent ModelSchemaDrift=0.0
# "coherent" verdict for an entity no field name was ever compared from.
# ---------------------------------------------------------------------------


class TestExtractabilityKeyedOnNonEmptiness:
    """``model_fields_are_extractable`` is keyed on >=1 extracted name, not Fields presence."""

    def test_empty_fields_class_is_not_extractable(self) -> None:
        """A present-but-empty ``Fields`` class extracts no names -> NOT extractable.

        Pre-fix this returned True (Fields is not None). The TERMINATING fix keys
        extractability on ``model_field_names`` non-emptiness, so an empty Fields
        class is correctly NOT extractable.
        """
        assert model_field_names(_EmptyFieldsModel) == frozenset()
        assert model_fields_are_extractable(_EmptyFieldsModel) is False

    def test_all_private_fields_class_is_not_extractable(self) -> None:
        """An all-private / non-str ``Fields`` class extracts no names -> NOT extractable."""
        assert model_field_names(_AllPrivateFieldsModel) == frozenset()
        assert model_fields_are_extractable(_AllPrivateFieldsModel) is False

    def test_inherited_empty_fields_class_is_not_extractable(self) -> None:
        """An inherited-but-empty ``Fields`` (subclasses an empty base) -> NOT extractable.

        The docstring of ``model_fields_are_extractable`` claims the inherited-empty
        shape is in the empty-extraction class. Pins that unit-level claim: the child
        ``Fields`` has no own members and its base has none, so extraction is empty.
        """
        assert model_field_names(_InheritedEmptyFieldsModel) == frozenset()
        assert model_fields_are_extractable(_InheritedEmptyFieldsModel) is False

    def test_inherited_real_fields_extractable_via_mro_dir_traversal(self) -> None:
        """Inherited cf constants ARE extracted via the Fields-class MRO -> EXTRACTABLE.

        REGRESSION GUARD for the ``model_field_names`` extraction contract. The cf
        display names live ONLY on the parent ``Fields`` base; the child ``Fields``
        declares no own members and reaches them solely through ``dir(fields_cls)``
        walking the MRO. Asserting the inherited names are materialized pins that
        contract: a refactor swapping ``dir()`` -> ``vars()`` (own-attrs only) would
        extract ``frozenset()`` here, flip ``extractable`` to False, and silently route
        a genuinely-analyzable model to UNANALYZABLE. This test goes RED on that swap;
        the inherited-empty cases above cannot (empty under both ``dir`` and ``vars``).
        """
        assert model_field_names(_InheritedRealFieldsModel) == frozenset({"Asset ID", "Offer Name"})
        assert model_fields_are_extractable(_InheritedRealFieldsModel) is True

    def test_non_str_uppercase_constant_is_not_extractable(self) -> None:
        """An UPPERCASE but NON-str ``Fields`` constant is skipped -> NOT extractable.

        ``ASSET_ID = 12345`` is public + SCREAMING_SNAKE but not a ``str``; the
        ``isinstance(value, str)`` filter must skip it, so extraction is empty. Pins
        that the type filter (not just the name filter) gates extraction.
        """
        assert model_field_names(_NonStrUpperConstFieldsModel) == frozenset()
        assert model_fields_are_extractable(_NonStrUpperConstFieldsModel) is False

    def test_live_offer_model_stays_extractable(self) -> None:
        """Behavior-preserving: a real model with declared cf fields stays extractable."""
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        model = _resolve_dotted_path(offer_desc.model_class_path)
        assert model_field_names(model)  # non-empty
        assert model_fields_are_extractable(model) is True


class TestEmptyFieldsRoutesToUnanalyzable:
    """The residual silent-false-green: empty-extraction model + schema cf -> UNANALYZABLE.

    These drive the REAL ``_validate_model_schema_coverage`` extraction + routing
    path over a synthetic descriptor whose model has a present-but-empty ``Fields``
    class and whose schema declares cf/cascade columns (the real Offer schema). The
    gate MUST emit the DISTINCT ``model_schema_coverage_unanalyzable`` signal and
    MUST NOT report it coherent via a silent ``model_schema_drift_detected`` with
    ``ModelSchemaDrift=0.0``.
    """

    def _offer_schema(self) -> object:
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        return _resolve_dotted_path(offer_desc.schema_module_path)

    def test_empty_fields_with_schema_cf_is_unanalyzable_not_silent_green(self) -> None:
        """`class Fields: pass` + a schema cf column -> UNANALYZABLE, never silent coherent."""
        schema = self._offer_schema()
        assert schema_cf_cascade_count(schema) >= 1  # fixture invariant
        desc = _desc(
            "synthetic_empty_fields",
            model_path="synthetic.empty_fields.model",
            schema_path="synthetic.empty_fields.schema",
        )
        events = _run_validator_over(
            [desc],
            {
                "synthetic.empty_fields.model": _EmptyFieldsModel,
                "synthetic.empty_fields.schema": schema,
            },
        )

        unanalyzable = [
            extra
            for name, extra in events
            if name == "model_schema_coverage_unanalyzable"
            and extra.get("entity") == "synthetic_empty_fields"
        ]
        assert unanalyzable, (
            "empty Fields class + schema cf column MUST route to UNANALYZABLE "
            "(the distinct signal), not a silent coherent ModelSchemaDrift=0.0"
        )
        extra = unanalyzable[0]
        assert extra["metrics"]["ModelSchemaCoverageUnanalyzable"] == 1.0
        assert "ModelSchemaDrift" not in extra["metrics"]
        assert extra["schema_cf_cascade_count"] >= 1

        # And NEITHER a drift signal NOR a silent coherent ModelSchemaDrift fires.
        drift = [
            extra
            for name, extra in events
            if name == "model_schema_drift_detected"
            and extra.get("entity") == "synthetic_empty_fields"
        ]
        assert not drift, (
            "an entity no field name was extracted from must NOT emit a coherent "
            "model_schema_drift_detected signal (the silent false-green shape)"
        )

    def test_all_private_fields_with_schema_cf_is_unanalyzable(self) -> None:
        """`class Fields: _x=1` + a schema cf column -> UNANALYZABLE."""
        schema = self._offer_schema()
        desc = _desc(
            "synthetic_private_fields",
            model_path="synthetic.private_fields.model",
            schema_path="synthetic.private_fields.schema",
        )
        events = _run_validator_over(
            [desc],
            {
                "synthetic.private_fields.model": _AllPrivateFieldsModel,
                "synthetic.private_fields.schema": schema,
            },
        )

        unanalyzable = [
            extra
            for name, extra in events
            if name == "model_schema_coverage_unanalyzable"
            and extra.get("entity") == "synthetic_private_fields"
        ]
        assert unanalyzable, "all-private Fields class + schema cf MUST be UNANALYZABLE"
        assert unanalyzable[0]["metrics"]["ModelSchemaCoverageUnanalyzable"] == 1.0
        assert "ModelSchemaDrift" not in unanalyzable[0]["metrics"]

        drift = [
            extra
            for name, extra in events
            if name == "model_schema_drift_detected"
            and extra.get("entity") == "synthetic_private_fields"
        ]
        assert not drift

    def test_inherited_empty_fields_with_schema_cf_is_unanalyzable_not_silent_green(
        self,
    ) -> None:
        """Inherited-but-empty ``Fields`` + a schema cf column -> UNANALYZABLE, never silent.

        The DELIVERABLE: pins the previously-unpinned inherited-empty claim end to end
        through the REAL extraction + routing path. A model whose ``Fields`` subclasses
        an empty base extracts zero names; paired with a schema that declares cf columns
        it MUST emit the DISTINCT ``model_schema_coverage_unanalyzable`` signal, with
        NEITHER ``ModelSchemaDrift`` NOR a silent coherent ``model_schema_drift_detected``.
        """
        schema = self._offer_schema()
        assert schema_cf_cascade_count(schema) >= 1  # fixture invariant
        desc = _desc(
            "synthetic_inherited_empty_fields",
            model_path="synthetic.inherited_empty_fields.model",
            schema_path="synthetic.inherited_empty_fields.schema",
        )
        events = _run_validator_over(
            [desc],
            {
                "synthetic.inherited_empty_fields.model": _InheritedEmptyFieldsModel,
                "synthetic.inherited_empty_fields.schema": schema,
            },
        )

        unanalyzable = [
            extra
            for name, extra in events
            if name == "model_schema_coverage_unanalyzable"
            and extra.get("entity") == "synthetic_inherited_empty_fields"
        ]
        assert unanalyzable, (
            "inherited-but-empty Fields class + schema cf column MUST route to "
            "UNANALYZABLE (the distinct signal), not a silent coherent ModelSchemaDrift=0.0"
        )
        extra = unanalyzable[0]
        assert extra["metrics"]["ModelSchemaCoverageUnanalyzable"] == 1.0
        assert "ModelSchemaDrift" not in extra["metrics"]
        assert extra["schema_cf_cascade_count"] >= 1

        drift = [
            extra
            for name, extra in events
            if name == "model_schema_drift_detected"
            and extra.get("entity") == "synthetic_inherited_empty_fields"
        ]
        assert not drift, (
            "an inherited-empty model no field name was extracted from must NOT emit a "
            "coherent model_schema_drift_detected signal (the silent false-green shape)"
        )

    def test_empty_fields_path_is_warn_first(self) -> None:
        """The empty-extraction routing is warn-first -- it logs + returns, never raises."""
        schema = self._offer_schema()
        desc = _desc(
            "synthetic_empty_fields",
            model_path="synthetic.empty_fields.model",
            schema_path="synthetic.empty_fields.schema",
        )
        # _run_validator_over invokes _validate_model_schema_coverage directly;
        # reaching this assertion at all proves it did not raise.
        _run_validator_over(
            [desc],
            {
                "synthetic.empty_fields.model": _EmptyFieldsModel,
                "synthetic.empty_fields.schema": schema,
            },
        )


# ---------------------------------------------------------------------------
# Item 2: single-path (unpaired) descriptors carrying cf/cascade substance are
# OBSERVABLE, not silently skipped. Drift analysis is undefined (no counterpart
# to compare), but a present side with substance is a coverage gap the gate
# exists to surface -> a DISTINCT model_schema_coverage_unpaired signal.
# ---------------------------------------------------------------------------


class TestUnpairedSinglePathObservable:
    """A single-path descriptor with cf/cascade substance emits the unpaired signal."""

    def _offer_schema(self) -> object:
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        return _resolve_dotted_path(offer_desc.schema_module_path)

    def _offer_model(self) -> object:
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        return _resolve_dotted_path(offer_desc.model_class_path)

    def test_schema_only_cf_bearing_descriptor_emits_unpaired(self) -> None:
        """schema-only (cf columns, no model) -> unpaired signal naming the missing model side."""
        schema = self._offer_schema()
        assert schema_cf_cascade_count(schema) >= 1
        desc = _desc("synthetic_schema_only", schema_path="synthetic.schema_only.schema")
        events = _run_validator_over([desc], {"synthetic.schema_only.schema": schema})

        unpaired = [
            extra
            for name, extra in events
            if name == "model_schema_coverage_unpaired"
            and extra.get("entity") == "synthetic_schema_only"
        ]
        assert unpaired, (
            "a schema-only descriptor with cf columns MUST emit model_schema_coverage_unpaired "
            "-- it is a coverage gap, not a silent skip"
        )
        extra = unpaired[0]
        assert extra["missing_side"] == "model"
        assert extra["present_side"] == "schema"
        assert extra["substance_count"] >= 1
        assert extra["metrics"]["ModelSchemaCoverageUnpaired"] == 1.0

        # Unpaired is NOT drift and NOT unanalyzable -- those require a counterpart.
        assert not [n for n, _ in events if n == "model_schema_drift_detected"]
        assert not [n for n, _ in events if n == "model_schema_coverage_unanalyzable"]

    def test_model_only_field_bearing_descriptor_emits_unpaired(self) -> None:
        """model-only (>=1 cf field, no schema) -> unpaired signal naming the missing schema side."""
        model = self._offer_model()
        assert model_field_names(model)
        desc = _desc("synthetic_model_only", model_path="synthetic.model_only.model")
        events = _run_validator_over([desc], {"synthetic.model_only.model": model})

        unpaired = [
            extra
            for name, extra in events
            if name == "model_schema_coverage_unpaired"
            and extra.get("entity") == "synthetic_model_only"
        ]
        assert unpaired, "a model-only descriptor with cf fields MUST emit unpaired"
        extra = unpaired[0]
        assert extra["missing_side"] == "schema"
        assert extra["present_side"] == "model"
        assert extra["substance_count"] >= 1
        assert extra["metrics"]["ModelSchemaCoverageUnpaired"] == 1.0

    def test_non_substantive_single_path_descriptor_stays_silent(self) -> None:
        """A single-path descriptor with NO cf/cascade substance is correctly silent.

        A model-only descriptor whose model extracts zero field names (e.g. a
        ``*_holder``) carries nothing to surface -- the unpaired signal is gated on
        substance, so it must NOT fire.
        """
        desc = _desc("synthetic_empty_model_only", model_path="synthetic.empty.model")
        events = _run_validator_over([desc], {"synthetic.empty.model": _EmptyFieldsModel})

        assert not [
            extra
            for name, extra in events
            if name == "model_schema_coverage_unpaired"
            and extra.get("entity") == "synthetic_empty_model_only"
        ], "a single-path descriptor with no substance must NOT emit unpaired"

    def test_paired_descriptor_does_not_emit_unpaired(self) -> None:
        """Control: a both-path (paired) descriptor never emits the unpaired signal."""
        offer_desc = next(d for d in get_registry().all_descriptors() if d.name == "offer")
        model = _resolve_dotted_path(offer_desc.model_class_path)
        schema = _resolve_dotted_path(offer_desc.schema_module_path)
        desc = _desc(
            "synthetic_paired",
            model_path="synthetic.paired.model",
            schema_path="synthetic.paired.schema",
        )
        events = _run_validator_over(
            [desc],
            {
                "synthetic.paired.model": model,
                "synthetic.paired.schema": schema,
            },
        )

        assert not [
            n
            for n, e in events
            if n == "model_schema_coverage_unpaired" and e.get("entity") == "synthetic_paired"
        ], "a paired descriptor has a counterpart -- it must NOT emit unpaired"
