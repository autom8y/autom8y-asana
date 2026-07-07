"""
Register-drift guard — @pytest.mark.scar keystone.

RATIFIED FORK (PT-A-FORK): Mode-2 genuine-gap guard realized as a
@pytest.mark.scar TWO-SIDED KEYSTONE in TEST SPACE only.

CRUSADE: asana-realization-tail-convergence, Sprint A2-guard (Track A,
GUARD-TEETH predicate leg b).

Two-sided contract (discriminating-canary doctrine):
  RED  — broken fixture INPUT fed to detector → DRIFT violations returned.
  GREEN — both the matching green fixture AND the real .know/ register →
           zero violations.

G-THEATER impossibility: `git diff origin/main..HEAD -- ':!tests/**'` is EMPTY.
Zero changes under .know/ or src/; the entire landing is under tests/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.knowledge.register_drift_checks import (
    INVARIANT_TABLE,
    InvariantRow,
    git_is_ancestor,
    run_detector,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Identical depth to tests/unit/canary/test_deploy_gate_content_binding.py:32
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "drift"

pytestmark = pytest.mark.scar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_fixture(name: str) -> str:
    path = _FIXTURE_DIR / name
    assert path.exists(), f"Fixture file missing: {path}"
    return path.read_text(encoding="utf-8")


def _read_register(row: InvariantRow) -> str:
    path = _REPO_ROOT / row.register_path
    assert path.exists(), f"Register file missing from repo: {path}\n  (row: {row.claim_id})"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Meta-vacuity guard
# ---------------------------------------------------------------------------


def test_every_invariant_row_is_two_sided() -> None:
    """
    Every INVARIANT_TABLE row must reference existing stale AND green fixtures.
    A row with no fixtures means it can never be proven two-sided → FAIL collection.

    Mirrors the anti-vacuity discipline at test_seam1_callsite_inventory.py.
    """
    for row in INVARIANT_TABLE:
        stale_path = _FIXTURE_DIR / row.stale_fixture
        green_path = _FIXTURE_DIR / row.green_fixture
        assert stale_path.exists(), (
            f"[{row.claim_id}] stale fixture missing: {stale_path}\n"
            "Row has no RED proof — vacuity guard fires."
        )
        assert green_path.exists(), (
            f"[{row.claim_id}] green fixture missing: {green_path}\n"
            "Row has no GREEN proof — vacuity guard fires."
        )


# ---------------------------------------------------------------------------
# Two-sided parametrized keystone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", INVARIANT_TABLE, ids=[r.claim_id for r in INVARIANT_TABLE])
def test_stale_fixture_produces_drift(row: InvariantRow) -> None:
    """
    RED side: stale fixture INPUT fed to the detector MUST return ≥1 violations.

    The broken thing is a TEST-FIXTURE INPUT, never a broken production surface
    (defect-injection into working registers = G-THEATER, FORBIDDEN).
    """
    text = _read_fixture(row.stale_fixture)
    violations = run_detector(row.detector_name, text)
    assert violations, (
        f"[{row.claim_id}] detector '{row.detector_name}' returned NO violations "
        f"on stale fixture '{row.stale_fixture}' — guard has no teeth (RED side fails).\n"
        f"Fixture path: {_FIXTURE_DIR / row.stale_fixture}"
    )


@pytest.mark.parametrize("row", INVARIANT_TABLE, ids=[r.claim_id for r in INVARIANT_TABLE])
def test_green_fixture_produces_no_drift(row: InvariantRow) -> None:
    """
    GREEN side (fixture): green fixture INPUT fed to the detector MUST return 0 violations.
    """
    text = _read_fixture(row.green_fixture)
    violations = run_detector(row.detector_name, text)
    assert not violations, (
        f"[{row.claim_id}] detector '{row.detector_name}' returned violations "
        f"on green fixture '{row.green_fixture}' — guard is over-firing (false positive):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


@pytest.mark.parametrize("row", INVARIANT_TABLE, ids=[r.claim_id for r in INVARIANT_TABLE])
def test_real_register_produces_no_drift(row: InvariantRow) -> None:
    """
    GREEN side (real register): the actual .know/ register at HEAD must produce 0 violations.

    The truthful state = origin/main HEAD e95a9de6 (A1 landing).
    If this assertion fails, the real register has drifted — the guard bites.
    """
    text = _read_register(row)
    violations = run_detector(row.detector_name, text)
    assert not violations, (
        f"[{row.claim_id}] REGISTER DRIFT DETECTED in '{row.register_path}':\n"
        + "\n".join(f"  - {v}" for v in violations)
        + f"\n\nrevalidate_when: {row.revalidate_when}"
    )


# ---------------------------------------------------------------------------
# Git corroboration (guarded — SKIP not FAIL when SHA is unreachable)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "row",
    [r for r in INVARIANT_TABLE if r.git_corroboration is not None],
    ids=[r.claim_id for r in INVARIANT_TABLE if r.git_corroboration is not None],
)
def test_git_corroboration(row: InvariantRow) -> None:
    """
    Corroboration (best-effort): re-derive shipping truth from git ancestry.

    SKIP when the SHA is unreachable (shallow clone / branch-only checkout) — the
    content-semantic detector carries the teeth; git-ancestry is additional grounding.

    Guard against 'skip miscounted as PASS': the skip reason is explicit and the
    test is never counted as a passing assertion when skipped.
    """
    gc = row.git_corroboration
    assert gc is not None  # parametrize filter guarantees this; satisfies type checker

    is_ancestor = git_is_ancestor(gc.landing_sha, _REPO_ROOT)
    if is_ancestor is None:
        pytest.skip(
            f"[{row.claim_id}] SHA {gc.landing_sha!r} is unreachable "
            "(shallow clone or branch-only checkout) — git corroboration skipped; "
            "content-semantic detector carries the guard teeth."
        )

    # Also assert agreement with content predicate: the content detector on the real
    # register must agree with what git ancestry tells us.
    real_text = _read_register(row)
    violations = run_detector(row.detector_name, real_text)
    content_clean = len(violations) == 0

    assert is_ancestor == gc.expected_ancestry, (
        f"[{row.claim_id}] git ancestry mismatch for SHA {gc.landing_sha!r}: "
        f"is_ancestor={is_ancestor}, expected={gc.expected_ancestry}.\n"
        f"  register_path: {row.register_path}\n"
        f"  revalidate_when: {row.revalidate_when}"
    )
    # Cross-check: content predicate and git ancestry must agree.
    if gc.expected_ancestry:
        # If SHA is an ancestor, the work has landed → content must be clean.
        assert content_clean, (
            f"[{row.claim_id}] git says {gc.landing_sha!r} is an ancestor (work landed) "
            f"but content detector finds drift:\n" + "\n".join(f"  - {v}" for v in violations)
        )
    # Note: for expected_ancestry=False (seam2), content detector should show MISSING
    # which is also clean (no violations). We don't need a separate assertion here
    # since test_real_register_produces_no_drift already covers the clean path.


# ---------------------------------------------------------------------------
# Substance-not-shape: unfaithful positive control
# ---------------------------------------------------------------------------


def test_unfaithful_positive_control_is_rejected() -> None:
    """
    Substance-not-shape: a fixture with RESOLVED present but strikethrough stripped
    MUST be rejected (DRIFT).

    This proves the detector bites on the discriminating token (open-status text
    outside strikethrough), not just file presence or the RESOLVED substring.

    A naive 'OR RESOLVED on same line' check would incorrectly pass this fixture GREEN.
    Our detector strips ~~...~~ first, then checks for bare open-status tokens —
    correctly catching the unfaithful pattern.
    """
    text = _read_fixture("scar_reg001_unfaithful_positive.stale.md")
    violations = run_detector("detect_scar_narration_drift", text)
    assert violations, (
        "Unfaithful positive control (RESOLVED present, strikethrough stripped) "
        "was NOT rejected — detector is biting on RESOLVED substring only, not "
        "the full predicate. This means a re-introduction of the disease with "
        "'RESOLVED' appended would slip through."
    )


# ---------------------------------------------------------------------------
# fm5 hardening: commented MISSING value must be caught (trailing-comment gap)
# ---------------------------------------------------------------------------


def test_fm5_shipped_missing_with_trailing_comment_is_caught() -> None:
    """
    Hardened fm5 detector: 'shipped: MISSING  # trailing comment' MUST return
    DRIFT.

    The old end-anchored regex (\\s*$) silently passed this variant because the
    trailing '  # stale comment survives' prevented the end-anchor from firing.
    The hardened detector matches the VALUE TOKEN 'MISSING' and allows an
    optional trailing '#' comment, closing the gap.
    """
    text = _read_fixture("fm5_shipped_commented.stale.yaml")
    violations = run_detector("detect_telos_shipped_not_missing", text)
    assert violations, (
        "Hardened fm5 detector did NOT catch 'shipped: MISSING  # comment' — "
        "the trailing-comment gap is still open.  The regex must match the "
        "shipped VALUE token (MISSING) regardless of any trailing '#' comment."
    )


# ---------------------------------------------------------------------------
# Scoped non-false-positive: different scar id must not trigger
# ---------------------------------------------------------------------------


def test_different_scar_id_does_not_trigger() -> None:
    """
    The predicate is scoped to enumerated resolved scar-IDs only.
    A genuine production blocker for a DIFFERENT, non-enumerated scar-id
    must pass GREEN — the guard must not over-fire on unrelated open issues.
    """
    snippet = (
        "- SCAR-NEW-999: Production blocker — "
        "some genuinely-open unrelated issue not yet resolved\n"
    )
    violations = run_detector("detect_scar_narration_drift", snippet)
    assert not violations, (
        "Guard fired on SCAR-NEW-999 (not in RESOLVED_SCAR_IDS) — "
        "predicate is not properly scoped to enumerated resolved scar-IDs.\n"
        "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Lane membership self-check
# ---------------------------------------------------------------------------


def test_scar_marker_not_excluded_from_ci() -> None:
    """
    Verify 'scar' is NOT in the test.yml:74 test_markers_exclude expression.

    This ensures the guard is collected by the standard sharded consumer-gate
    (it rides the existing scar lane, not a new CI YAML lane).
    """
    test_yml = _REPO_ROOT / ".github" / "workflows" / "test.yml"
    if not test_yml.exists():
        pytest.skip("test.yml not present — cannot verify lane membership")

    content = test_yml.read_text(encoding="utf-8")
    # Find the test_markers_exclude line
    for line in content.splitlines():
        if "test_markers_exclude" in line and "not" in line:
            # 'scar' must not appear in the exclude expression
            assert "scar" not in line, (
                f"'scar' found in test_markers_exclude expression:\n  {line}\n"
                "The guard is being excluded from CI — it has no lane coverage."
            )
