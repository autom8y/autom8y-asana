# WS-CLASS: Classification Rule Externalization (Conditional)

**Objective**: Externalize the 33 Offer and 14 Unit section classification rules
from hardcoded Python frozensets to YAML configuration -- but ONLY if change
frequency warrants it.

**Rite**: hygiene
**Complexity**: PATCH
**Recommendations**: R-004
**Preconditions**: U-002 must be resolved first (classification rule change frequency)
**Estimated Effort**: 1 day (if triggered)

---

## Gate: Resolve U-002 First

**Before executing this workstream**, determine classification rule change frequency:

```bash
cd /Users/tomtenuta/Code/autom8y-asana
git log --oneline --follow -p src/autom8_asana/models/business/activity.py \
  | grep -A2 -B2 "OFFER_SECTIONS\|UNIT_SECTIONS\|OFFER_CLASSIFIER\|UNIT_CLASSIFIER"
```

Also run:
```bash
git log --oneline src/autom8_asana/models/business/activity.py | head -20
```

**Decision rule**:
- If section names changed 3+ times in 6 months: EXECUTE this workstream
- If section names changed 0-2 times in 6 months: SKIP -- current design is appropriate
- Document the decision in MEMORY.md either way

---

## Problem (If Triggered)

`models/business/activity.py` lines 183-263 hardcode 33 Offer section names and
14 Unit section names as Python frozensets. Every classification change requires
a code change, PR review, CI, and deployment.

The `SectionClassifier.from_groups()` factory method already accepts a dict
format loadable from YAML. The lifecycle engine already uses YAML config for
analogous data (`config/lifecycle_stages.yaml`).

**Evidence**: ARCHITECTURE-REPORT.md R-004; ARCHITECTURE-ASSESSMENT.md Gap 4

---

## Artifact References

- Gap detail: `ARCHITECTURE-ASSESSMENT.md` Section 5.2, Gap 4
- Risk register: `ARCHITECTURE-ASSESSMENT.md` Section 8, Risk 8
- Existing YAML pattern: `config/lifecycle_stages.yaml`
- Classification source: `src/autom8_asana/models/business/activity.py`

---

## Implementation Sketch

### Step 1: Create YAML config

Create `config/classification_rules.yaml`:
```yaml
offer:
  groups:
    initial_contact: ["New Lead", "Cold Outreach", ...]
    # Mirror the dict structure from from_groups()
unit:
  groups:
    active: ["Active Unit", ...]
```

### Step 2: Add YAML loader

Modify `models/business/activity.py`:
- Load YAML at module level using existing config loading patterns
- Pass loaded dict to `SectionClassifier.from_groups()`
- Add Pydantic validation for the loaded YAML structure
- Replace hardcoded `OFFER_CLASSIFIER` and `UNIT_CLASSIFIER` with YAML-loaded versions

### Step 3: Preserve API contract

- `get_classifier(entity_type)` API must remain unchanged
- All consumers of `OFFER_CLASSIFIER` and `UNIT_CLASSIFIER` must work identically
- Add error handling for missing/malformed YAML (fail loud at startup)

### Step 4: Test

- Run: `pytest tests/unit/models/business/ -k classifier -x`
- Add test for YAML loading and validation
- Add test for invalid YAML error handling
- Run: `pytest tests/ -x` (full suite)

---

## Do NOT

- Change the SectionClassifier class interface
- Modify `get_classifier()` function signature
- Add hot-reload capability (module-level load is sufficient)
- Change how consumers use the classifiers

---

## Green-to-Green Gates

- `get_classifier()` returns identical classifiers as before
- All classification-related tests pass unchanged
- YAML validation catches malformed config at startup
- Full test suite green

---

## Definition of Done

- [ ] U-002 resolved with documented decision
- [ ] If EXECUTE: YAML config created, loader implemented, tests pass
- [ ] If SKIP: Documented "classification rules stable, YAML not needed" in MEMORY.md
- [ ] MEMORY.md updated with outcome
