"""
Register-drift check helpers — test-space only.

Pure content-detector functions + declarative INVARIANT_TABLE.
Imported only by test_register_drift_guard.py; never imported by production code.

Design rationale (RATIFIED FORK PT-A-FORK):
  .know/ registers are NOT imported by production code, so the guard lives
  entirely in test space and rides the existing @pytest.mark.scar lane.
  Teeth live in pure-function-over-text detectors so that a broken fixture
  INPUT — never a broken production surface — produces the RED state.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
# A DRIFT result is a list of violation strings.
# Empty list  => NO_DRIFT (GREEN).
# Non-empty   => DRIFT (RED).
DriftResult = list[str]

# ---------------------------------------------------------------------------
# Resolved scar-IDs whose narration is guarded (Class 2 invariants).
# Add new IDs here when they are resolved.
# ---------------------------------------------------------------------------
RESOLVED_SCAR_IDS: frozenset[str] = frozenset({"SCAR-REG-001", "SCAR-IDEM-001"})

# Open-status tokens that must NOT appear outside ~~strikethrough~~ for
# a line that co-mentions a resolved scar-id.
_OPEN_STATUS_RE = re.compile(
    r"\b(production blocker|must be replaced)\b|(?<!\w)OPEN(?!\w)",
    re.IGNORECASE,
)

# Matches any ~~...~~ span (non-greedy).
_STRIKETHROUGH_RE = re.compile(r"~~.+?~~")


# ---------------------------------------------------------------------------
# Predicate 1 — SCAR narration drift
# ---------------------------------------------------------------------------

def detect_scar_narration_drift(
    text: str,
    scar_ids: Optional[frozenset[str]] = None,
) -> DriftResult:
    """
    For every line that:
      (a) co-mentions one of the enumerated resolved scar-ids AND
      (b) contains an open-status token outside ~~strikethrough~~

    → DRIFT.

    Algorithm: strip all ~~...~~ spans from the line; if an open-status
    token is still visible afterwards, the narration is unprotected → drift.

    Why this beats the naive OR-check:
      A line like "SCAR-REG-001: Production blocker RESOLVED" would pass an
      "OR RESOLVED on same line" check, but the old disease text remains
      readable. Stripping strikethrough first and then scanning for bare
      open-status tokens correctly rejects that pattern — ensuring the guard
      bites on the full discriminating predicate, not a single substring.
    """
    if scar_ids is None:
        scar_ids = RESOLVED_SCAR_IDS

    violations: DriftResult = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for scar_id in scar_ids:
            if scar_id not in line:
                continue
            # Remove all struck-through spans; what remains is "live" text.
            live_text = _STRIKETHROUGH_RE.sub("", line)
            if _OPEN_STATUS_RE.search(live_text):
                violations.append(
                    f"Line {lineno}: {scar_id} co-mentions open-status token "
                    f"outside ~~strikethrough~~: {line.strip()[:140]}"
                )
    return violations


# ---------------------------------------------------------------------------
# Predicate 2 — fm5 telos: shipped MUST NOT be MISSING
# ---------------------------------------------------------------------------

def detect_telos_shipped_not_missing(text: str) -> DriftResult:
    """
    The fm5-column-fidelity telos has attestation_status.shipped == LANDED.
    Returns DRIFT if the shipped scalar value is MISSING (regardless of any
    trailing YAML comment after a '#').

    Hardened to catch in-place drift like:
        shipped: MISSING  # stale comment survives
    where the old end-anchored regex (\\s*$) would silently miss the violation.
    The fix matches the shipped VALUE token, not the end of line, by consuming
    only up to an optional '#' comment or end-of-string.
    """
    # Match: optional leading whitespace, 'shipped:', optional whitespace,
    # then the value token 'MISSING', then either end-of-string, whitespace,
    # or a '#' comment character (YAML inline comment marker).
    _shipped_missing_re = re.compile(r"^\s*shipped:\s*MISSING\s*(?:#.*)?$")
    violations: DriftResult = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _shipped_missing_re.match(line):
            violations.append(
                f"Line {lineno}: shipped: MISSING found — expected LANDED "
                f"(a87ae1ca #161 landed fm5)"
            )
    return violations


# ---------------------------------------------------------------------------
# Predicate 3 — seam2 telos: shipped MUST be MISSING
# ---------------------------------------------------------------------------

def detect_telos_shipped_must_be_missing(text: str) -> DriftResult:
    """
    The seam2-consumer-realization telos has attestation_status.shipped == MISSING.
    Returns DRIFT if 'shipped: LANDED' is found in the text.
    """
    violations: DriftResult = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if re.match(r"\s*shipped:\s*LANDED\s*$", line):
            violations.append(
                f"Line {lineno}: shipped: LANDED found — expected MISSING "
                f"(47826fe4 not yet an ancestor of main)"
            )
    return violations


# ---------------------------------------------------------------------------
# Predicate 4 — defer-watch fleet-promotion entry integrity
# ---------------------------------------------------------------------------

_PROMOTION_ID = "drift-audit-discipline-fleet-promotion"
_PROMOTION_STATUS = "DEFERRED-pending-cross-repo-coordination"
_PROMOTION_TRIGGER = "2026-05-29"
_PROMOTION_ESCALATION_TOKEN = "ecosystem"


def detect_defer_watch_promotion_entry(text: str) -> DriftResult:
    """
    The defer-watch.yaml FIRED entry 'drift-audit-discipline-fleet-promotion'
    must be present and structurally stable:
      - id present
      - status: DEFERRED-pending-cross-repo-coordination
      - watch_trigger: 2026-05-29
      - escalation_target mentioning 'ecosystem'

    Omission or tamper with any of the four anchors → DRIFT.
    """
    violations: DriftResult = []
    if _PROMOTION_ID not in text:
        violations.append(
            f"Entry id '{_PROMOTION_ID}' absent from defer-watch — "
            "entry omitted or id tampered"
        )
        # No point checking sub-fields if the entry is entirely absent.
        return violations
    if _PROMOTION_STATUS not in text:
        violations.append(
            f"Entry status '{_PROMOTION_STATUS}' not found — "
            "status field tampered or changed"
        )
    if _PROMOTION_TRIGGER not in text:
        violations.append(
            f"Entry watch_trigger '{_PROMOTION_TRIGGER}' not found — "
            "watch_trigger field tampered or removed"
        )
    if _PROMOTION_ESCALATION_TOKEN not in text:
        violations.append(
            f"Entry escalation_target missing '{_PROMOTION_ESCALATION_TOKEN}' token — "
            "escalation_target field tampered or removed"
        )
    return violations


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_DETECTOR_MAP = {
    "detect_scar_narration_drift": detect_scar_narration_drift,
    "detect_telos_shipped_not_missing": detect_telos_shipped_not_missing,
    "detect_telos_shipped_must_be_missing": detect_telos_shipped_must_be_missing,
    "detect_defer_watch_promotion_entry": detect_defer_watch_promotion_entry,
}


def run_detector(detector_name: str, text: str) -> DriftResult:
    """Dispatch to a detector by name."""
    fn = _DETECTOR_MAP.get(detector_name)
    if fn is None:
        raise ValueError(f"Unknown detector: {detector_name!r}")
    return fn(text)


# ---------------------------------------------------------------------------
# Git corroboration helper (guarded — SKIP, not FAIL, when SHA is unreachable)
# ---------------------------------------------------------------------------

def git_is_ancestor(sha: str, repo_root: Path) -> Optional[bool]:
    """
    Return True if `sha` is an ancestor of HEAD, False if not, None if the
    SHA is unreachable (shallow clone or branch-only checkout).

    Callers must treat None as "skip, not fail" — the content-semantic
    detector carries the teeth; git-ancestry is corroboration only.
    """
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
            cwd=repo_root,
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        # Non-zero, non-one exit usually means the object is unreachable.
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# INVARIANT_TABLE — one row per guarded claim
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GitCorroboration:
    landing_sha: str
    expected_ancestry: bool  # True = must be ancestor; False = must NOT


@dataclass(frozen=True)
class InvariantRow:
    claim_id: str
    register_path: str          # Relative to repo root
    detector_name: str          # Key in _DETECTOR_MAP
    stale_fixture: str          # Filename under fixtures/drift/
    green_fixture: str          # Filename under fixtures/drift/
    git_corroboration: Optional[GitCorroboration]
    revalidate_when: str        # Human note on when to retire/update this row


INVARIANT_TABLE: list[InvariantRow] = [
    InvariantRow(
        claim_id="SCAR-REG-001-narration",
        register_path=".know/scar-tissue.md",
        detector_name="detect_scar_narration_drift",
        stale_fixture="scar_reg001_reopened.stale.md",
        green_fixture="scar_reg001_resolved.green.md",
        git_corroboration=None,
        revalidate_when=(
            "If SCAR-REG-001 or SCAR-IDEM-001 is re-opened, or new resolved "
            "scar-IDs are added to RESOLVED_SCAR_IDS."
        ),
    ),
    InvariantRow(
        claim_id="fm5-shipped-not-missing",
        register_path=".know/telos/fm5-column-fidelity.md",
        detector_name="detect_telos_shipped_not_missing",
        stale_fixture="fm5_shipped.stale.yaml",
        green_fixture="fm5_shipped.green.yaml",
        git_corroboration=GitCorroboration(
            landing_sha="a87ae1ca",
            expected_ancestry=True,
        ),
        revalidate_when=(
            "Retire when fm5 reaches verified_realized=ATTESTED and its telos "
            "file is archived. The guard becomes vacuous once the file no longer "
            "contains an attestation_status block."
        ),
    ),
    InvariantRow(
        claim_id="seam2-shipped-must-be-missing",
        register_path=".know/telos/seam2-consumer-realization.md",
        detector_name="detect_telos_shipped_must_be_missing",
        stale_fixture="seam2_shipped.stale.yaml",
        green_fixture="seam2_shipped.green.yaml",
        git_corroboration=GitCorroboration(
            landing_sha="47826fe4",
            expected_ancestry=False,
        ),
        revalidate_when=(
            "Flip to detect_telos_shipped_not_missing when seam2 lands "
            "(47826fe4 becomes an ancestor of main). Update green/stale fixtures "
            "accordingly."
        ),
    ),
    InvariantRow(
        claim_id="defer-watch-promotion-entry",
        register_path=".know/defer-watch.yaml",
        detector_name="detect_defer_watch_promotion_entry",
        stale_fixture="defer_watch_promotion_omitted.stale.yaml",
        green_fixture="defer_watch_promotion_present.green.yaml",
        git_corroboration=None,
        revalidate_when=(
            "Retire when A3 discharges the drift-audit-discipline-fleet-promotion "
            "entry (status changes to FIRED-DISCHARGED or equivalent). At that "
            "point the entry will still be present (APPEND-ONLY discipline) but "
            "the guard predicate may need updating."
        ),
    ),
]
