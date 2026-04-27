"""Unit tests for src/autom8_asana/metrics/sla_profile.py (ADR-005).

Coverage:

- Validator V-1 (schema_version)
- Validator V-2 (sla_class enum)
- Validator V-3 (threshold_seconds positive int, no floats)
- Validator V-4 (string GIDs)
- Validator V-5 (duplicate detection)
- Validator V-6 (cross-validation WARN, not error)
- ``load_manifest`` happy / absent / corrupt
- ``parse_sidecar`` happy / invalid
- ``load_sidecar`` (moto-backed)
- ``resolve_ttl`` precedence: sidecar > manifest > default
- ``resolve_threshold_for_class``
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from autom8_asana.metrics.sla_profile import (
    BUILTIN_DEFAULT_CLASS,
    CURRENT_SCHEMA_VERSION,
    DEFAULT_THRESHOLDS,
    SLA_CLASSES,
    ProjectTtl,
    SectionTtl,
    TtlManifest,
    TtlManifestError,
    TtlSidecar,
    load_manifest,
    load_sidecar,
    parse_manifest,
    parse_sidecar,
    resolve_threshold_for_class,
    resolve_ttl,
)

# Try moto for sidecar S3 integration tests.
try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover
    MOTO_AVAILABLE = False
    mock_aws = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_GID = "1143843662099250"
SECTION_A = "1143843662099257"
SECTION_B = "1143843662099256"
SECTION_C = "1209233681691558"
SECTION_D = "1204152425074370"


def _valid_manifest_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "default_class": "active",
        "generated_at": "2026-04-27T14:00:00Z",
        "generator": "test_sla_profile",
        "projects": {
            PROJECT_GID: {
                "project_gid": PROJECT_GID,
                "sections": {
                    SECTION_A: {
                        "section_gid": SECTION_A,
                        "sla_class": "active",
                        "threshold_seconds": 21600,
                    },
                    SECTION_B: {
                        "section_gid": SECTION_B,
                        "sla_class": "warm",
                        "threshold_seconds": 43200,
                    },
                    SECTION_C: {
                        "section_gid": SECTION_C,
                        "sla_class": "cold",
                        "threshold_seconds": 86400,
                    },
                    SECTION_D: {
                        "section_gid": SECTION_D,
                        "sla_class": "near-empty",
                        "threshold_seconds": 604800,
                    },
                },
            }
        },
    }


def _valid_sidecar_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_gid": PROJECT_GID,
        "sections": {
            SECTION_B: {
                "section_gid": SECTION_B,
                "sla_class": "active",
                "threshold_seconds": 21600,
                "notes": "Pre-launch warmup override",
            }
        },
    }


# ---------------------------------------------------------------------------
# Constants smoke
# ---------------------------------------------------------------------------


class TestConstants:
    """Frozen constants from ADR-005 / HANDOFF FLAG-2."""

    def test_sla_classes_are_4_class_taxonomy(self) -> None:
        assert SLA_CLASSES == ("active", "warm", "cold", "near-empty")

    def test_default_thresholds_match_p3(self) -> None:
        # P3 §2.2: ACTIVE=6h, WARM=12h, COLD=24h, NEAR-EMPTY=7d.
        assert DEFAULT_THRESHOLDS["active"] == 21600
        assert DEFAULT_THRESHOLDS["warm"] == 43200
        assert DEFAULT_THRESHOLDS["cold"] == 86400
        assert DEFAULT_THRESHOLDS["near-empty"] == 604800

    def test_builtin_default_class_is_active(self) -> None:
        assert BUILTIN_DEFAULT_CLASS == "active"

    def test_schema_version_is_1(self) -> None:
        assert CURRENT_SCHEMA_VERSION == 1


# ---------------------------------------------------------------------------
# V-1 schema_version
# ---------------------------------------------------------------------------


class TestV1SchemaVersion:
    """Validator V-1: schema_version present, integer, == 1."""

    def test_missing_schema_version_raises(self) -> None:
        raw = _valid_manifest_dict()
        del raw["schema_version"]
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-1"

    def test_string_schema_version_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["schema_version"] = "1"
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-1"

    def test_bool_schema_version_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["schema_version"] = True
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-1"

    def test_future_schema_version_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["schema_version"] = 2
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-1"

    def test_zero_schema_version_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["schema_version"] = 0
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-1"


# ---------------------------------------------------------------------------
# V-2 sla_class
# ---------------------------------------------------------------------------


class TestV2SlaClass:
    """Validator V-2: sla_class in {active, warm, cold, near-empty}."""

    def test_unknown_sla_class_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["sla_class"] = "frozen"
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-2"

    def test_uppercase_sla_class_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["sla_class"] = "ACTIVE"
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-2"

    def test_underscore_in_near_empty_raises(self) -> None:
        # Hyphen, not underscore.
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["sla_class"] = "near_empty"
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-2"

    def test_default_class_validated(self) -> None:
        raw = _valid_manifest_dict()
        raw["default_class"] = "frozen"
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-2"

    def test_all_4_classes_accepted(self) -> None:
        # Already covered by _valid_manifest_dict, but make explicit.
        raw = _valid_manifest_dict()
        manifest = parse_manifest(raw)
        classes = {s.sla_class for s in manifest.projects[PROJECT_GID].sections.values()}
        assert classes == {"active", "warm", "cold", "near-empty"}


# ---------------------------------------------------------------------------
# V-3 threshold_seconds
# ---------------------------------------------------------------------------


class TestV3ThresholdSeconds:
    """Validator V-3: positive integer; no floats, no zero, no negative."""

    def test_float_threshold_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["threshold_seconds"] = 21600.0
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-3"

    def test_negative_threshold_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["threshold_seconds"] = -1
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-3"

    def test_zero_threshold_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["threshold_seconds"] = 0
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-3"

    def test_string_threshold_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["threshold_seconds"] = "21600"
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-3"

    def test_bool_threshold_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["threshold_seconds"] = True
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-3"


# ---------------------------------------------------------------------------
# V-4 string GIDs
# ---------------------------------------------------------------------------


class TestV4StringGids:
    """Validator V-4: section_gid / project_gid MUST be strings."""

    def test_int_section_gid_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"] = {
            1143843662099257: raw["projects"][PROJECT_GID]["sections"][SECTION_A]
        }
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-4"

    def test_int_project_gid_raises(self) -> None:
        raw = _valid_manifest_dict()
        section_payload = raw["projects"][PROJECT_GID]
        raw["projects"] = {1143843662099250: section_payload}
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-4"

    def test_empty_section_gid_raises(self) -> None:
        raw = _valid_manifest_dict()
        section_payload = raw["projects"][PROJECT_GID]["sections"][SECTION_A]
        raw["projects"][PROJECT_GID]["sections"] = {"": section_payload}
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-4"

    def test_non_string_notes_raises(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["notes"] = 42
        with pytest.raises(TtlManifestError) as exc_info:
            parse_manifest(raw)
        assert exc_info.value.rule == "V-4"


# ---------------------------------------------------------------------------
# V-6 cross-validation
# ---------------------------------------------------------------------------


class TestV6CrossValidation:
    """Validator V-6: WARN (NOT error) when threshold deviates from class default."""

    def test_deviation_is_warn_not_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        raw = _valid_manifest_dict()
        # warm class default is 43200; set to 21600 (active default) — legitimate
        # operator override per ADR-005 V-6 example.
        raw["projects"][PROJECT_GID]["sections"][SECTION_B]["threshold_seconds"] = 21600
        manifest = parse_manifest(raw)
        # Manifest parses cleanly.
        assert manifest.projects[PROJECT_GID].sections[SECTION_B].threshold_seconds == 21600
        assert manifest.projects[PROJECT_GID].sections[SECTION_B].sla_class == "warm"
        # WARN was emitted on stdout (structlog) — surface the deviation key.
        captured = capsys.readouterr()
        assert "ttl_manifest_v6_threshold_deviation" in captured.out

    def test_no_warning_when_threshold_matches_canonical(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Canonical thresholds → V-6 WARN MUST NOT fire.
        parse_manifest(_valid_manifest_dict())
        captured = capsys.readouterr()
        assert "ttl_manifest_v6_threshold_deviation" not in captured.out


# ---------------------------------------------------------------------------
# Manifest happy path
# ---------------------------------------------------------------------------


class TestParseManifestHappyPath:
    """Full 4-class manifest parses cleanly."""

    def test_all_4_classes_parse(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sections = manifest.projects[PROJECT_GID].sections
        assert len(sections) == 4
        assert sections[SECTION_A].sla_class == "active"
        assert sections[SECTION_A].threshold_seconds == 21600
        assert sections[SECTION_B].sla_class == "warm"
        assert sections[SECTION_C].sla_class == "cold"
        assert sections[SECTION_D].sla_class == "near-empty"
        assert sections[SECTION_D].threshold_seconds == 604800

    def test_optional_fields_preserved(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        assert manifest.generated_at == "2026-04-27T14:00:00Z"
        assert manifest.generator == "test_sla_profile"
        assert manifest.default_class == "active"

    def test_unknown_top_level_field_tolerated(self) -> None:
        raw = _valid_manifest_dict()
        raw["future_extension"] = "not-yet-defined"
        manifest = parse_manifest(raw)
        # Unknown top-level fields are silently ignored per ADR-005 additive
        # evolution rule.
        assert manifest.schema_version == 1

    def test_unknown_section_field_tolerated(self) -> None:
        raw = _valid_manifest_dict()
        raw["projects"][PROJECT_GID]["sections"][SECTION_A]["last_classified_by"] = "operator-x"
        manifest = parse_manifest(raw)
        # Tolerated; not parsed into the dataclass.
        assert manifest.projects[PROJECT_GID].sections[SECTION_A].sla_class == "active"


# ---------------------------------------------------------------------------
# load_manifest -- filesystem-backed
# ---------------------------------------------------------------------------


class TestLoadManifest:
    """Filesystem-backed manifest loading."""

    def test_absent_returns_none(self, tmp_path: Any) -> None:
        path = tmp_path / "nonexistent.yaml"
        assert load_manifest(path) is None

    def test_loads_valid_yaml(self, tmp_path: Any) -> None:
        import yaml

        path = tmp_path / "manifest.yaml"
        path.write_text(yaml.safe_dump(_valid_manifest_dict()))
        manifest = load_manifest(path)
        assert manifest is not None
        assert manifest.schema_version == 1
        assert PROJECT_GID in manifest.projects

    def test_corrupt_yaml_raises(self, tmp_path: Any) -> None:
        path = tmp_path / "manifest.yaml"
        path.write_text("not: valid: yaml: : :\n  - [unbalanced")
        with pytest.raises(TtlManifestError):
            load_manifest(path)

    def test_empty_yaml_raises(self, tmp_path: Any) -> None:
        path = tmp_path / "manifest.yaml"
        path.write_text("")
        with pytest.raises(TtlManifestError):
            load_manifest(path)

    def test_yaml_list_root_raises(self, tmp_path: Any) -> None:
        # Top level must be a mapping, not a list.
        path = tmp_path / "manifest.yaml"
        path.write_text("- not\n- a\n- mapping\n")
        with pytest.raises(TtlManifestError):
            load_manifest(path)


# ---------------------------------------------------------------------------
# Sidecar parsing
# ---------------------------------------------------------------------------


class TestParseSidecar:
    """parse_sidecar happy / invalid."""

    def test_happy_path(self) -> None:
        sidecar = parse_sidecar(_valid_sidecar_dict())
        assert sidecar.project_gid == PROJECT_GID
        assert SECTION_B in sidecar.sections
        assert sidecar.sections[SECTION_B].notes == "Pre-launch warmup override"

    def test_missing_schema_version_raises(self) -> None:
        raw = _valid_sidecar_dict()
        del raw["schema_version"]
        with pytest.raises(TtlManifestError) as exc_info:
            parse_sidecar(raw)
        assert exc_info.value.rule == "V-1"

    def test_bare_int_project_gid_raises(self) -> None:
        raw = _valid_sidecar_dict()
        raw["project_gid"] = 1143843662099250
        with pytest.raises(TtlManifestError) as exc_info:
            parse_sidecar(raw)
        assert exc_info.value.rule == "V-4"


# ---------------------------------------------------------------------------
# load_sidecar -- moto-backed S3
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestLoadSidecarMoto:
    """S3-backed sidecar reader against moto."""

    BUCKET = "autom8-s3"

    def _key(self, project_gid: str = PROJECT_GID) -> str:
        return f"dataframes/{project_gid}/cache-freshness-ttl.json"

    def test_absent_sidecar_returns_none(self) -> None:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            assert load_sidecar(client, self.BUCKET, PROJECT_GID) is None

    def test_present_sidecar_returns_record(self) -> None:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            client.put_object(
                Bucket=self.BUCKET,
                Key=self._key(),
                Body=json.dumps(_valid_sidecar_dict()).encode("utf-8"),
            )
            sidecar = load_sidecar(client, self.BUCKET, PROJECT_GID)
            assert sidecar is not None
            assert sidecar.project_gid == PROJECT_GID
            assert SECTION_B in sidecar.sections

    def test_corrupt_json_returns_none(self) -> None:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            client.put_object(
                Bucket=self.BUCKET,
                Key=self._key(),
                Body=b"{not valid json",
            )
            assert load_sidecar(client, self.BUCKET, PROJECT_GID) is None

    def test_invalid_schema_returns_none(self) -> None:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            bad = _valid_sidecar_dict()
            bad["sections"][SECTION_B]["sla_class"] = "frozen"  # V-2 violation
            client.put_object(
                Bucket=self.BUCKET,
                Key=self._key(),
                Body=json.dumps(bad).encode("utf-8"),
            )
            # Sidecar errors fall through to manifest per ADR-005 §1.4.
            assert load_sidecar(client, self.BUCKET, PROJECT_GID) is None

    def test_no_such_bucket_returns_none(self) -> None:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            # Don't create the bucket.
            result = load_sidecar(client, "does-not-exist", PROJECT_GID)
            assert result is None


# ---------------------------------------------------------------------------
# resolve_ttl precedence
# ---------------------------------------------------------------------------


class TestResolveTtlPrecedence:
    """Precedence: sidecar > manifest > default."""

    def test_default_when_both_absent(self) -> None:
        sla_class, threshold = resolve_ttl(PROJECT_GID, SECTION_A)
        # Falls through to BUILTIN_DEFAULT_CLASS = active.
        assert sla_class == "active"
        assert threshold == 21600

    def test_default_when_section_unknown(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sla_class, threshold = resolve_ttl(
            PROJECT_GID,
            "9999999999999999",
            manifest=manifest,
        )
        assert sla_class == "active"
        assert threshold == 21600

    def test_default_when_project_unknown(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sla_class, threshold = resolve_ttl(
            "0000000000000000",
            SECTION_A,
            manifest=manifest,
        )
        assert sla_class == "active"
        assert threshold == 21600

    def test_manifest_hit(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sla_class, threshold = resolve_ttl(
            PROJECT_GID,
            SECTION_C,
            manifest=manifest,
        )
        assert sla_class == "cold"
        assert threshold == 86400

    def test_sidecar_hit_overrides_manifest(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sidecar = parse_sidecar(_valid_sidecar_dict())
        # Manifest declares SECTION_B as warm/43200; sidecar overrides to active/21600.
        sla_class, threshold = resolve_ttl(
            PROJECT_GID,
            SECTION_B,
            manifest=manifest,
            sidecar=sidecar,
        )
        assert sla_class == "active"
        assert threshold == 21600

    def test_sidecar_miss_falls_through_to_manifest(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sidecar = parse_sidecar(_valid_sidecar_dict())
        # Sidecar has only SECTION_B; SECTION_A falls through to manifest.
        sla_class, threshold = resolve_ttl(
            PROJECT_GID,
            SECTION_A,
            manifest=manifest,
            sidecar=sidecar,
        )
        assert sla_class == "active"
        assert threshold == 21600

    def test_sidecar_for_other_project_ignored(self) -> None:
        manifest = parse_manifest(_valid_manifest_dict())
        sidecar = parse_sidecar(_valid_sidecar_dict())
        # Sidecar is scoped to PROJECT_GID; lookup for a different project
        # MUST NOT use this sidecar.
        sla_class, threshold = resolve_ttl(
            "9999999999999999",
            SECTION_B,
            manifest=manifest,
            sidecar=sidecar,
        )
        # Falls through to manifest.default_class (active).
        assert sla_class == "active"
        assert threshold == 21600

    def test_manifest_only_hit(self) -> None:
        # Manifest with no sidecar.
        manifest = parse_manifest(_valid_manifest_dict())
        sla_class, threshold = resolve_ttl(
            PROJECT_GID,
            SECTION_D,
            manifest=manifest,
        )
        assert sla_class == "near-empty"
        assert threshold == 604800

    def test_sidecar_only_hit(self) -> None:
        # Sidecar with no manifest.
        sidecar = parse_sidecar(_valid_sidecar_dict())
        sla_class, threshold = resolve_ttl(
            PROJECT_GID,
            SECTION_B,
            sidecar=sidecar,
        )
        assert sla_class == "active"
        assert threshold == 21600


# ---------------------------------------------------------------------------
# resolve_threshold_for_class (CLI flag mapping)
# ---------------------------------------------------------------------------


class TestResolveThresholdForClass:
    """CLI --sla-profile=<class> flag direct mapping."""

    @pytest.mark.parametrize(
        "sla_class,expected",
        [
            ("active", 21600),
            ("warm", 43200),
            ("cold", 86400),
            ("near-empty", 604800),
        ],
    )
    def test_known_classes(self, sla_class: str, expected: int) -> None:
        assert resolve_threshold_for_class(sla_class) == expected

    def test_unknown_class_raises(self) -> None:
        with pytest.raises(TtlManifestError) as exc_info:
            resolve_threshold_for_class("frozen")
        assert exc_info.value.rule == "V-2"


# ---------------------------------------------------------------------------
# Dataclass shapes
# ---------------------------------------------------------------------------


class TestDataclassShapes:
    """SectionTtl / ProjectTtl / TtlManifest / TtlSidecar are frozen dataclasses."""

    def test_section_ttl_is_frozen(self) -> None:
        section = SectionTtl(
            section_gid=SECTION_A,
            sla_class="active",
            threshold_seconds=21600,
        )
        with pytest.raises(Exception):
            section.threshold_seconds = 7200  # type: ignore[misc]

    def test_project_ttl_is_frozen(self) -> None:
        project = ProjectTtl(project_gid=PROJECT_GID)
        with pytest.raises(Exception):
            project.project_gid = "x"  # type: ignore[misc]

    def test_ttl_manifest_is_frozen(self) -> None:
        manifest = TtlManifest(schema_version=1)
        with pytest.raises(Exception):
            manifest.schema_version = 2  # type: ignore[misc]

    def test_ttl_sidecar_is_frozen(self) -> None:
        sidecar = TtlSidecar(schema_version=1, project_gid=PROJECT_GID)
        with pytest.raises(Exception):
            sidecar.project_gid = "x"  # type: ignore[misc]
