# Gate Verdict — Deep Slop Triage

Date: 2026-02-19
Agent: gate-keeper
Scope: Full Codebase (`src/autom8_asana/`)
Upstream phases: hallucination-hunter, logic-surgeon, cruft-cutter, remedy-smith

---

## Verdict: CONDITIONAL-PASS

Three HIGH-severity findings are present. All three have clear, bounded remediation paths via remedy-smith — two are classified MANUAL with explicit step-by-step instructions (RS-M01, RS-M02) and one has been reclassified to MEDIUM after remedy review (LS-005 / RS-A02 is AUTO-patchable). The production import tree is clean, no CRITICAL findings exist, and all 17 temporal findings are advisory by rule. This must not merge without resolving the two MANUAL HIGH-severity items (RS-M01 and RS-M02); the third HIGH (LS-005 / TYPE_CHECKING imports) is AUTO-patchable and elevates to a condition rather than a hard block if auto-applied in the same PR.

---

## Blocking Findings

### Blocking Finding 1: Regex injection in `generate_entity_name()` — HIGH (0.95 confidence)

- **Detection**: Phase 2 logic-surgeon, finding LS-001 / SEC-002
- **Analysis**: `re.sub()` in `core/creation.py:82-96` uses unescaped `business_name` and `unit_name` as the replacement-string argument. Python's `re.sub` replacement strings interpret backreferences (`\1`, `\g<0>`, etc.). A business name containing `\1` causes either silent data corruption (wrong task name) or a `re.error` exception crashing task creation. Three production callers confirmed: `lifecycle/creation.py:163`, `lifecycle/creation.py:282`, `automation/pipeline.py:309`. Business names originate from Asana task data — user-supplied.
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py` lines 82–96
- **Remedy**: RS-M01 — MANUAL, effort S (<1hr). Wrap replacement strings with `re.escape()` or use `lambda m: business_name`. Write regression test with `r"Acme \1 Corp"` as business name. No auto-patch because judgment is required on whether `re.escape()` may double-escape upstream-processed strings; `lambda` form recommended as safer.

This must not merge until resolved.

---

### Blocking Finding 2: PII leakage in `gid_push.py` error log — HIGH (0.90 confidence)

- **Detection**: Phase 2 logic-surgeon, finding SEC-001
- **Analysis**: `services/gid_push.py:232` logs `response.text[:500]` directly into a structured warning log entry under key `"response_text"`. The `/api/v1/gid-mappings/sync` endpoint may echo back phone numbers from the request payload in error messages. The XR-003 PII redaction audit closed 5 leakage vectors in `clients/data/` but did not include `services/gid_push.py`. Remedy-smith also notes the exception log at lines 250–257 (`str(e)`) and the timeout handler should be reviewed for consistency.
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_push.py` line 232 (also ~250–257)
- **Remedy**: RS-M02 — MANUAL, effort S (<1hr). Add `from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string` and wrap `response.text[:500]` as `_mask_pii_in_string(response.text[:500])`. Extend XR-003 audit tracking to include this module.

This must not merge until resolved.

---

### Condition (not hard block if AUTO-applied): Stale TYPE_CHECKING imports referencing non-existent module — HIGH (0.95 confidence)

- **Detection**: Phase 1 hallucination-hunter L-002; confirmed Phase 2 logic-surgeon LS-005
- **Analysis**: `core/creation.py:21` and `automation/templates.py:17` both contain `from autom8_asana.models.core import Task` (and `Section`) inside `TYPE_CHECKING` blocks. `models/core.py` does not exist. The import is never executed at runtime (TYPE_CHECKING guard), so production is unaffected. However, mypy, IDEs, and any static analysis tool will report errors, and the mypy override (`ignore_missing_imports = true` for `autom8_asana.models.core`) masks the issue.
- **File**: `src/autom8_asana/core/creation.py:21`, `src/autom8_asana/automation/templates.py:17`
- **Remedy**: RS-A02 — AUTO, effort XS (<15 min). Change to `from autom8_asana.models.task import Task` and `from autom8_asana.models.section import Section`. Run `mypy` to confirm.
- **Classification decision**: This finding meets HIGH threshold on severity but the remediation is mechanical, zero-risk, and AUTO-classified. If applied in the same change set as Blocking Findings 1 and 2, this does not hold up the merge independently.

---

## Evidence Chains

### LS-001 / SEC-002 — Regex Injection

```
Detection  (HH):    Not flagged (hallucination scope is import/API existence)
Analysis   (LS):    LS-001 + SEC-002 — re.sub() replacement injection, 0.95 confidence
                    core/creation.py:82-96, 3 confirmed production callers
Decay      (CC):    Not applicable (not a temporal finding)
Remedy     (RS):    RS-M01 — MANUAL, S effort, re.escape() or lambda replacement
                    Regression test required for business names with backslash sequences
```

### SEC-001 — PII Leakage in gid_push.py

```
Detection  (HH):    Not flagged (file not in hallucination scope)
Analysis   (LS):    SEC-001 — structured log PII leakage, 0.90 confidence
                    gid_push.py:232, response_text logged unmasked
                    XR-003 audit gap identified
Decay      (CC):    Not applicable (not a temporal finding)
Remedy     (RS):    RS-M02 — MANUAL, S effort, import mask_pii_in_string, wrap response.text
                    Also review lines 250-257 (exception message)
```

### L-002 / LS-005 — Stale TYPE_CHECKING Imports

```
Detection  (HH):    L-002 — models/core.py does not exist; mypy override masks it
Analysis   (LS):    LS-005 — confirms with file system evidence; 2 files affected
Decay      (CC):    Not applicable
Remedy     (RS):    RS-A02 — AUTO, XS effort, correct paths confirmed unambiguously
```

---

## CI Output

```json
{
  "verdict": "CONDITIONAL-PASS",
  "exit_code": 0,
  "conditions": [
    "RS-M01: Fix regex injection in core/creation.py:82-96 before merge",
    "RS-M02: Mask PII in gid_push.py:232 error log before merge",
    "RS-A02: Apply AUTO patch for stale TYPE_CHECKING imports (recommended in same PR)"
  ],
  "summary": {
    "total_findings": 45,
    "blocking": 2,
    "conditional": 1,
    "advisory": 42,
    "auto_fixable": 8,
    "manual_required": 2,
    "by_category": {
      "hallucination": 0,
      "public_api_gap": 2,
      "logic_errors": 8,
      "copy_paste_bloat": 3,
      "test_degradation": 5,
      "security_anti_patterns": 4,
      "unreviewed_output_signals": 2,
      "temporal_debt": 17,
      "other": 4
    },
    "by_severity": {
      "CRITICAL": 0,
      "HIGH": 3,
      "MEDIUM": 13,
      "LOW": 12,
      "TEMPORAL": 17
    }
  },
  "blocking_findings": [
    {
      "id": "SEC-001",
      "phase": "logic-surgeon",
      "severity": "HIGH",
      "confidence": 0.90,
      "file": "src/autom8_asana/services/gid_push.py",
      "line": 232,
      "description": "PII leakage: response.text logged unmasked in error handler",
      "remedy_id": "RS-M02",
      "remedy_class": "MANUAL",
      "effort": "S"
    },
    {
      "id": "LS-001/SEC-002",
      "phase": "logic-surgeon",
      "severity": "HIGH",
      "confidence": 0.95,
      "file": "src/autom8_asana/core/creation.py",
      "lines": "82-96",
      "description": "Regex injection: re.sub() with unescaped user input on 3 production paths",
      "remedy_id": "RS-M01",
      "remedy_class": "MANUAL",
      "effort": "S"
    }
  ],
  "conditional_findings": [
    {
      "id": "LS-005",
      "phase": "logic-surgeon",
      "severity": "HIGH",
      "confidence": 0.95,
      "files": [
        "src/autom8_asana/core/creation.py:21",
        "src/autom8_asana/automation/templates.py:17"
      ],
      "description": "TYPE_CHECKING imports reference autom8_asana.models.core which does not exist",
      "remedy_id": "RS-A02",
      "remedy_class": "AUTO",
      "effort": "XS",
      "note": "Condition converts to PASS if RS-A02 AUTO patch is applied in same PR"
    }
  ],
  "advisory_findings_count": 42,
  "temporal_findings_count": 17,
  "temporal_blocked": false,
  "cross_rite_referrals": [
    {
      "target_rite": "security",
      "findings": ["SEC-001", "LS-001/SEC-002", "LS-007"],
      "reason": "PII leakage extension of XR-003 audit; regex injection threat model; PII-in-cache-key compliance decision"
    },
    {
      "target_rite": "hygiene",
      "findings": ["CC-012", "D-017-cluster"],
      "reason": "42-caller deprecated method migration; D-017 deprecated alias cluster sprint"
    },
    {
      "target_rite": "debt-triage",
      "findings": ["CC-017", "CC-005", "CC-004", "CC-014"],
      "reason": "D-014 ledger ghost closure; MVP-deferred stubs requiring product input; kill switch retention decision; HOLDER_KEY_MAP detection system maturity"
    }
  ]
}
```

---

## Finding Summary

| Phase | Critical | High | Medium | Low | Advisory (Temporal) |
|-------|----------|------|--------|-----|---------------------|
| Phase 1 — Hallucination Hunter | 0 | 0 | 2 | 4 | 0 |
| Phase 2 — Logic Surgeon | 0 | 3 | 10 | 9 | 0 |
| Phase 3 — Cruft Cutter | 0 | 0 | 0 | 0 | 17 |
| Phase 4 — Remedy Smith | n/a | n/a | n/a | n/a | n/a |
| **TOTAL** | **0** | **3** | **12** | **13** | **17** |

Note: Phase 1 MEDIUM findings M-001 (public API gap) and M-002 (dead stub) are advisory — no runtime failures confirmed, no callers broken. Phase 2 HIGH LS-005 is promoted from Phase 1 L-002 with confirming evidence; it shares the same finding slot.

Effective blocking count: **2** (SEC-001 and LS-001/SEC-002 — both MANUAL, no auto-fix available)
Conditional count: **1** (LS-005 — AUTO-fixable, condition lifts if RS-A02 applied)

---

## Cross-Rite Referrals

### Security Rite

| Finding | Context | Referral Reason |
|---------|---------|-----------------|
| SEC-001 / RS-M02 | `services/gid_push.py:232` — response.text logged unmasked | XR-003 audit extension: gid_push was out of scope. This is a new PII leakage vector confirmed by logic-surgeon. Assign to XR-003 follow-up. |
| LS-001 / SEC-002 / RS-M01 | `core/creation.py:82-96` — re.sub() with user data as replacement | Threat model review: confirm whether business names are fully user-controlled or constrained upstream. Fix is straightforward (`re.escape` / lambda) but the threat model determines urgency. |
| LS-007 / RS-M07 | `clients/data/_cache.py:42` — cache key contains raw canonical_key with E.164 phone | PII-at-rest compliance decision. Cache key format uses raw phone. Whether this violates HIPAA/SOC2 posture requires compliance owner input. Do not change cache key format unilaterally — coordinate cache warm-up window. |

### Hygiene Rite

| Finding | Context | Referral Reason |
|---------|---------|-----------------|
| CC-012 / RS-M16 | `models/task.py:256-281` — `get_custom_fields()` deprecated, 42 callers | Sprint-sized migration. 42 active callers across lifecycle, automation, and business models. Scope as a dedicated hygiene sprint sub-task. |
| D-017 cluster / RS-M20 | Multiple files — deprecated aliases, parameters, and properties | Full D-017 cluster is backlog hygiene debt. Estimated XL effort. Sequence: caller audit per symbol, remove in dependency order, one PR per symbol. |
| TD-001/TD-002 / RS-M09 | `test_settings.py` and `test_staleness_flow.py` — shallow `is not None` assertions | Shallow test assertion improvement is trigger-gated per D-027 (540 mock sites). Route to a test architecture initiative, not ad-hoc patching. |

### Debt Rite (Debt Triage)

| Finding | Context | Referral Reason |
|---------|---------|-----------------|
| CC-017 / RS-A07 | D-014 debt ledger entry — `PipelineAutoCompletionService` already removed | Documentation ghost. D-014 should be closed in the ledger. The code remediation is complete; only the ledger update is pending. |
| CC-005 / RS-M13 | `dataframes/extractors/unit.py:66-118` — MVP-deferred TODOs, 70+ days open | Business logic input from autom8 team required before implementation. File a product ticket with acceptance criteria, or formally close as "column reserved for future use." |
| CC-004 / RS-M12 | `clients/data/client.py` — `AUTOM8_DATA_INSIGHTS_ENABLED` kill switch | Operational decision: has the kill switch ever been activated? Is it in incident runbooks? This is a stakeholder decision, not a code decision. Escalate to ops/team lead. |
| CC-014 / RS-M17 | `models/business/business.py:235` — `HOLDER_KEY_MAP` DEPRECATED fallback | Requires detection system maturity assessment. Cannot remove fallback without metrics on detection failure rate. Route to team lead for data-driven decision. |

---

## Recommended Next Actions

Ordered by urgency:

1. **RS-M01 (this sprint, ~1hr)** — Fix regex injection in `generate_entity_name()`. Use `lambda m: business_name` as the replacement argument in both `re.sub()` calls at `core/creation.py:82-96`. Write regression test with backslash-containing business name. This is the highest-priority security fix.

2. **RS-M02 (this sprint, ~1hr)** — Mask PII in `gid_push.py` error log. Import `mask_pii_in_string` from `clients/data/_pii` and wrap `response.text[:500]` at line 232. Also wrap `str(e)` at lines ~250-257 for consistency. Add to XR-003 tracking.

3. **RS-A02 (same PR as above, ~15 min)** — Fix stale TYPE_CHECKING imports in `core/creation.py:21` and `automation/templates.py:17`. Change `models.core` to `models.task` / `models.section`. Run mypy to confirm. Include in the same PR as RS-M01 and RS-M02 to clear all three HIGH findings.

4. **Batch 2 AUTO patches (next sprint, ~2hrs total)** — Apply RS-A01 (add missing re-exports to `clients/data/__init__.py`), RS-A03 (remove dead `_parse_content_disposition_filename` from `client.py`), RS-A04 (strip SPIKE-BREAK-CIRCULAR-DEP tags), RS-A05 (strip HOTFIX labels from `cache_warmer.py`), RS-A06 (remove migration note from `freshness.py`), RS-A07 (close D-014 in ledger). All are zero-risk, comment or export changes.

5. **RS-M04 (next sprint, ~1hr)** — Update `test_pii.py` imports to use canonical path (`_pii` module) instead of private alias in `client.py`.

6. **RS-M08 (next sprint, ~1hr)** — Narrow `except (ValueError, Exception)` to `except (json.JSONDecodeError, ValueError)` in `batch.py:187` and `gid_push.py:211`.

7. **Security rite referrals (schedule)** — Route LS-007 / RS-M07 (PII in cache key) to security rite for compliance determination. Do not act without compliance owner input.

8. **Hygiene rite referrals (backlog)** — Route CC-012 (42-caller `get_custom_fields()` migration) and D-017 cluster to hygiene rite as a sprint-sized workstream.

9. **Debt triage referrals (as-available)** — Close D-014 ledger ghost (RS-A07, included in Batch 2). File product ticket for CC-005 MVP-deferred stubs. Escalate CC-004 kill switch decision to ops/team lead.

---

## Gate Keeper Notes

**Temporal debt rule applied**: All 17 cruft-cutter findings (CC-001 through CC-017) are classified TEMPORAL. They do not contribute to this verdict. The CONDITIONAL-PASS verdict rests solely on Phase 2 logic-surgeon HIGH findings.

**LS-007 reclassification acknowledged**: Remedy-smith correctly reclassified LS-007 from "unreachable stale fallback" to "PII-at-rest in cache key." The reclassification holds: the finding remains MEDIUM (not HIGH) because the PII is in a cache key (observable by cache backend operators/logs), not in user-facing output or an uncontrolled log sink. The compliance determination governs whether this elevates.

**Verdict threshold**: Two HIGH findings without AUTO-fix availability produce CONDITIONAL-PASS at MODULE scope (not FAIL), because remedy-smith has provided complete, verified, bounded remediation paths for each. FAIL would be warranted for HIGH findings with no clear remediation path. Both RS-M01 and RS-M02 have specific, actionable step-by-step instructions verified against actual code.

**PR comment ready**: The blocking section above is formatted for direct inclusion in a PR review comment. Link to this file for full context.
