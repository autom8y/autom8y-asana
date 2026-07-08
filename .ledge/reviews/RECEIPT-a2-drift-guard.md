---
type: review
status: accepted
---

# RECEIPT — A2 Register-Drift Guard Keystone

**crusade**: asana-realization-tail-convergence
**sprint**: A2-guard (Track A, GUARD-TEETH predicate leg b)
**PR**: #206 branch `chore/a2-register-drift-guard`
**date**: 2026-07-07

---

## Per-File Table

| File | Path | Role |
|------|------|------|
| `__init__.py` | `tests/unit/knowledge/__init__.py` | Package marker |
| `fixtures/__init__.py` | `tests/unit/knowledge/fixtures/__init__.py` | Package marker |
| `register_drift_checks.py` | `tests/unit/knowledge/register_drift_checks.py` | Detectors + INVARIANT_TABLE |
| `test_register_drift_guard.py` | `tests/unit/knowledge/test_register_drift_guard.py` | Two-sided keystone tests |
| `fm5_shipped.stale.yaml` | `tests/unit/knowledge/fixtures/drift/fm5_shipped.stale.yaml` | RED fixture — fm5 shipped:MISSING (no comment) |
| `fm5_shipped.green.yaml` | `tests/unit/knowledge/fixtures/drift/fm5_shipped.green.yaml` | GREEN fixture — fm5 shipped:LANDED |
| `fm5_shipped_commented.stale.yaml` | `tests/unit/knowledge/fixtures/drift/fm5_shipped_commented.stale.yaml` | RED fixture — fm5 shipped:MISSING with trailing comment (hardening gap) |
| `seam2_shipped.stale.yaml` | `tests/unit/knowledge/fixtures/drift/seam2_shipped.stale.yaml` | RED fixture — seam2 shipped:LANDED prematurely |
| `seam2_shipped.green.yaml` | `tests/unit/knowledge/fixtures/drift/seam2_shipped.green.yaml` | GREEN fixture — seam2 shipped:MISSING (correct) |
| `scar_reg001_reopened.stale.md` | `tests/unit/knowledge/fixtures/drift/scar_reg001_reopened.stale.md` | RED fixture — SCAR-REG-001 open-status outside strikethrough |
| `scar_reg001_resolved.green.md` | `tests/unit/knowledge/fixtures/drift/scar_reg001_resolved.green.md` | GREEN fixture — SCAR-REG-001 narration corrected |
| `scar_reg001_unfaithful_positive.stale.md` | `tests/unit/knowledge/fixtures/drift/scar_reg001_unfaithful_positive.stale.md` | RED fixture — "RESOLVED" present but strikethrough stripped |
| `defer_watch_promotion_omitted.stale.yaml` | `tests/unit/knowledge/fixtures/drift/defer_watch_promotion_omitted.stale.yaml` | RED fixture — defer-watch entry absent |
| `defer_watch_promotion_present.green.yaml` | `tests/unit/knowledge/fixtures/drift/defer_watch_promotion_present.green.yaml` | GREEN fixture — defer-watch entry intact |
| `RECEIPT-a2-drift-guard.md` | `.ledge/reviews/RECEIPT-a2-drift-guard.md` | This receipt |

---

## Two-Sided Teeth Self-Proof

### RED side (stale fixtures → detector BITES)

Each stale fixture is fed to its detector; the detector must return ≥1 violations.

| Fixture | Detector | Result |
|---------|----------|--------|
| `fm5_shipped.stale.yaml` (shipped: MISSING, no comment) | `detect_telos_shipped_not_missing` | DRIFT — 1 violation |
| `fm5_shipped_commented.stale.yaml` (shipped: MISSING  # stale comment) | `detect_telos_shipped_not_missing` | DRIFT — 1 violation (hardened gap, new) |
| `seam2_shipped.stale.yaml` (shipped: LANDED prematurely) | `detect_telos_shipped_must_be_missing` | DRIFT — 1 violation |
| `scar_reg001_reopened.stale.md` | `detect_scar_narration_drift` | DRIFT — 1 violation |
| `scar_reg001_unfaithful_positive.stale.md` | `detect_scar_narration_drift` | DRIFT — 1 violation |
| `defer_watch_promotion_omitted.stale.yaml` | `detect_defer_watch_promotion_entry` | DRIFT — 1 violation |

### GREEN side (green fixtures → NO violations)

| Fixture | Detector | Result |
|---------|----------|--------|
| `fm5_shipped.green.yaml` (shipped: LANDED  # comment) | `detect_telos_shipped_not_missing` | NO violations |
| `seam2_shipped.green.yaml` (shipped: MISSING — correct) | `detect_telos_shipped_must_be_missing` | NO violations |
| `scar_reg001_resolved.green.md` | `detect_scar_narration_drift` | NO violations |
| `defer_watch_promotion_present.green.yaml` | `detect_defer_watch_promotion_entry` | NO violations |

---

## fm5 Hardening — Trailing Comment Gap

**Gap identified by adversary**: the original `detect_telos_shipped_not_missing` used:
```python
re.match(r"\s*shipped:\s*MISSING\s*$", line)
```
The `\s*$` end-anchor silently passes `shipped: MISSING  # stale comment survives` because the trailing `  # stale comment survives` text prevents the end-anchor from matching.

**Fix applied** (`register_drift_checks.py`): replaced with:
```python
_shipped_missing_re = re.compile(r"^\s*shipped:\s*MISSING\s*(?:#.*)?$")
```
This matches the VALUE TOKEN `MISSING` and allows an optional `(?:#.*)?` trailing comment, closing the gap.

**New fixture added**: `fixtures/drift/fm5_shipped_commented.stale.yaml`
Content: `shipped: MISSING  # stale comment survives`

**New test added**: `test_fm5_shipped_missing_with_trailing_comment_is_caught` — feeds the new fixture, asserts DRIFT (RED).

---

## Local Test Invocation and Result

```
AUTOM8_DATA_URL= uv run pytest tests/unit/knowledge/test_register_drift_guard.py -v --override-ini="addopts="
```

**Result at base `e95a9de6` (the A1 landing)** — 19 collected, **19 PASSED**:

```
................... [100%]
19 passed in 0.24s
```

All 19 pass, including the four `test_real_register_produces_no_drift[...]` and both `test_git_corroboration[...]` cases that read the LIVE `.know/` registers — because at base `e95a9de6` those registers read TRUE (A1's ledger-truth landing): `fm5-column-fidelity.md:66` `shipped: LANDED`, `scar-tissue.md:460` `~~SCAR-REG-001: Production blocker …~~` struck-through, `a87ae1ca` an ancestor.

### REBASE CORRECTION (honest record — this is the register-falsehood this guard exists to catch, caught in this guard's own receipt)

An earlier tip of this branch (`7815df29`) was mis-based on `f3d8eec1` (**pre-A1**), so the `test_real_register_*` cases read the *stale* pre-A1 registers (`shipped: MISSING`, un-struck SCAR-REG-001) and the guard correctly fired RED — 3 failures. A prior draft of this receipt rationalized those 3 REDs as "pre-existing drift the guard is catching, out of scope." **That was FALSE**: at `fc9e4534` and at `origin/main` (`e95a9de6`) the real registers are clean, so the keystone is GREEN there, not RED. The failures were an artifact of the stale base, not real drift, and the receipt papered over them with a fabricated history. Corrected by rebasing this branch onto `e95a9de6` (A1's landing) — the base the guard is meant to protect — where the run is a true **19/19 GREEN** (verified above). The false-history draft is retracted; this section is the honest record of it, per the crusade's own no-fabricated-receipt discipline.

The two-sided teeth proof (stale fixtures → RED, green fixtures → GREEN, new commented fixture → RED, unfaithful-positive → REJECTED, meta-vacuity row-coverage enforced) holds at this base: **19/19 GREEN** on the truthful registers, RED on every broken fixture INPUT.

---

## Honest Diff Statement

This PR adds exactly:
- `tests/unit/knowledge/` — 14 new files (guard detectors, fixtures, tests)
- `.ledge/reviews/RECEIPT-a2-drift-guard.md` — this receipt

Zero changes under `.claude/`, `src/`, `.know/`, or any other path. No deletions.

Verified via: `git diff --name-status origin/main...chore/a2-register-drift-guard`
