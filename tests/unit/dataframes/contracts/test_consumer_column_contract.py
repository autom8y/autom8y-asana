"""FM-5 ARM-B — CI parity + freshness guard for the consumer-column contract.

Per ``TDD-fm5-armb-honest-refusal-contract`` §8 row 6. The contract's SOLE
propagation point is ``field_contract_maps.py``; these tests pin its derivation
(a declared column the served schema cannot satisfy is build-time VISIBLE, not a
prod KeyError) and exercise the WARN-first freshness guard.

A load-bearing assertion: ``offer_id`` on a ``project`` frame is INTENDED to fire
loud (it is ABSENT from the served PROJECT_SCHEMA and stays unwidened — widening a
100%-NULL column is explicitly rejected; the permanent loud signal is the SEAM-2
rebind driver). The parity test asserts that EXPECTED unservability — it does NOT
treat the loud signal as a build failure, and it WOULD go RED if the served
schema's satisfiability drifted unexpectedly.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from autom8_asana.dataframes.contracts import (
    VENDORED_MANIFEST_PATH,
    ConsumerManifestError,
    derive_required_columns,
    load_consumer_requirements,
    requirements_drift_check,
)
from autom8_asana.dataframes.schemas.project import PROJECT_SCHEMA
from autom8_asana.dataframes.schemas.section import SECTION_SCHEMA

if TYPE_CHECKING:
    from pathlib import Path

_PROJECT_ENDPOINT = "/v1/query/project/rows"
_SECTION_ENDPOINT = "/v1/query/section/rows"


class TestVendoredManifest:
    """The vendored seed loads and carries the SPEC's first two instances."""

    def test_vendored_manifest_is_valid_and_seeded(self) -> None:
        reqs = load_consumer_requirements()
        assert reqs.schema_version == 1
        assert reqs.declared_by == "autom8-monolith"
        by_id = {c.consumer_id: c for c in reqs.consumers}
        assert set(by_id) == {"business_offers.active_offers_frame", "fetch_section_rows"}

        offers = by_id["business_offers.active_offers_frame"]
        assert offers.query_shape.entity_type == "project"
        assert offers.query_shape.endpoint == _PROJECT_ENDPOINT
        assert offers.required_columns == ("offer_id",)
        assert offers.on_missing == "typed_incomplete"

        sections = by_id["fetch_section_rows"]
        assert sections.query_shape.entity_type == "section"
        assert sections.required_columns == ("project_gid",)


class TestDerivation:
    """``derive_required_columns`` is the per-query-shape union (RULING-1 subset)."""

    def test_project_required_set(self) -> None:
        assert derive_required_columns("project", _PROJECT_ENDPOINT) == frozenset({"offer_id"})

    def test_section_required_set(self) -> None:
        assert derive_required_columns("section", _SECTION_ENDPOINT) == frozenset({"project_gid"})

    def test_unmatched_query_shape_is_empty(self) -> None:
        # Contract-driven SUBSET, not eager parity: no consumer declares against
        # the offer shape, so the required set is empty (no over-firing).
        assert derive_required_columns("offer", "/v1/query/offer/rows") == frozenset()

    def test_entity_and_endpoint_must_both_match(self) -> None:
        # A project consumer must not bleed into a mismatched endpoint.
        assert derive_required_columns("project", "/v1/query/section/rows") == frozenset()


class TestServabilityParityGate:
    """Build-time gate: which declared columns the served schema can satisfy.

    This is the parity check that turns a non-servable consumer column into a
    build-time RED rather than a production KeyError.
    """

    def test_offer_id_is_intentionally_unservable_on_project_fires_loud(self) -> None:
        """offer_id declared-required on project is EXPECTED-unservable (loud, not block).

        This pins the design's intended permanent loud signal: offer_id stays
        ABSENT from PROJECT_SCHEMA (widen is useless — 100% NULL — and explicitly
        rejected). The assertion documents the SEAM-2 rebind driver and would go
        RED if the served schema unexpectedly changed satisfiability.
        """
        required = derive_required_columns("project", _PROJECT_ENDPOINT)
        served = set(PROJECT_SCHEMA.column_names())
        unservable = sorted(required - served)
        assert unservable == ["offer_id"]

    def test_project_gid_is_unservable_on_section_until_seam2(self) -> None:
        required = derive_required_columns("section", _SECTION_ENDPOINT)
        served = set(SECTION_SCHEMA.column_names())
        unservable = sorted(required - served)
        assert unservable == ["project_gid"]

    def test_no_unexpected_servable_drift(self) -> None:
        """Pin the FULL expected (entity, endpoint) -> unservable map.

        If a future change widened a schema (or a new consumer declared a column
        the schema cannot serve), this map diverges and the test goes RED at build
        time — the freshness/parity intent of FM-5 ARM-B.
        """
        cases = {
            ("project", _PROJECT_ENDPOINT): (PROJECT_SCHEMA, ["offer_id"]),
            ("section", _SECTION_ENDPOINT): (SECTION_SCHEMA, ["project_gid"]),
        }
        for (entity_type, endpoint), (schema, expected_unservable) in cases.items():
            required = derive_required_columns(entity_type, endpoint)
            served = set(schema.column_names())
            assert sorted(required - served) == expected_unservable


class TestFreshnessGuard:
    """``requirements_drift_check`` — WARN-first reversed-SNC freshness guard."""

    def test_schema_only_mode_when_source_absent(self) -> None:
        report = requirements_drift_check(monolith_source=None)
        assert report.mode == "schema-only"
        assert report.ok is True
        assert report.drift is False
        assert report.source_sha256 is None
        assert report.declared_at == "2026-06-11"
        assert len(report.vendored_sha256) == 64  # sha256 hexdigest

    def test_source_compared_matching_is_no_drift(self, tmp_path: Path) -> None:
        # An identical source (byte-for-byte) => no drift.
        source = tmp_path / "consumer_column_requirements.json"
        source.write_bytes(VENDORED_MANIFEST_PATH.read_bytes())

        report = requirements_drift_check(monolith_source=source)
        assert report.mode == "source-compared"
        assert report.drift is False
        assert report.ok is True
        assert report.source_sha256 == report.vendored_sha256

    def test_source_compared_divergent_is_drift_red(self, tmp_path: Path) -> None:
        # A diverged source => DRIFT, ok False (the CI-loud RED).
        source = tmp_path / "consumer_column_requirements.json"
        doc = json.loads(VENDORED_MANIFEST_PATH.read_text(encoding="utf-8"))
        doc["consumers"][0]["required_columns"].append("drifted_extra_column")
        source.write_text(json.dumps(doc), encoding="utf-8")

        report = requirements_drift_check(monolith_source=source)
        assert report.mode == "source-compared"
        assert report.drift is True
        assert report.ok is False
        assert report.source_sha256 != report.vendored_sha256


class TestFailLoud:
    """Malformed manifests fail loud at load time — never a silent partial parse."""

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "declared_by": "x",
                    "declared_at": "2026-06-11",
                    "consumers": [
                        {
                            # missing consumer_id / code_anchor
                            "query_shape": {
                                "endpoint": "/v1/query/project/rows",
                                "entity_type": "project",
                            },
                            "required_columns": ["offer_id"],
                            "population_expectation": "present_any",
                            "on_missing": "typed_incomplete",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ConsumerManifestError):
            load_consumer_requirements(path=bad)

    def test_unsupported_schema_version_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"schema_version": 99, "consumers": []}), encoding="utf-8")
        with pytest.raises(ConsumerManifestError):
            load_consumer_requirements(path=bad)

    def test_unknown_on_missing_token_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "declared_by": "x",
                    "declared_at": "2026-06-11",
                    "consumers": [
                        {
                            "consumer_id": "c",
                            "code_anchor": "a:1",
                            "query_shape": {
                                "endpoint": "/v1/query/project/rows",
                                "entity_type": "project",
                            },
                            "required_columns": ["offer_id"],
                            "population_expectation": "present_any",
                            "on_missing": "silent_drop",  # not in the v1 closed vocabulary
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ConsumerManifestError):
            load_consumer_requirements(path=bad)

    def test_not_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{ this is not json", encoding="utf-8")
        with pytest.raises(ConsumerManifestError):
            load_consumer_requirements(path=bad)
