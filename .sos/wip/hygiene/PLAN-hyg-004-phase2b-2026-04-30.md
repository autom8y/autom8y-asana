---
type: design
artifact_type: refactor-plan
rite: hygiene
session_id: session-20260430-phase2b-architect
target: HYG-004 Phase 2B
evidence_grade: STRONG
audit_outcome_anticipated: PHASE-2B-CLEAN-CLOSE-WITH-CASE-SENSITIVITY-FOLD (G1+G2 two-group, 1 split-and-fold edge case)
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-phase2 §5 sub-sprint C
authored_by: architect-enforcer
substrate: dispatch directive (Phase 2 charter §5; Phase 2A predecessor) + direct Read of tests/unit/test_tier2_adversarial.py L1-L260 + pytest collection enumeration of TestWebhookSignatureVerificationValid + TestWebhookSignatureVerificationInvalid
evidence_basis: direct file inspection (tests/unit/test_tier2_adversarial.py L141-L254) + pytest --collect-only enumeration (11 tests across two classes) + class-boundary mapping (Valid L141-L187; Invalid L190-L254; TimingSafety begins L257)
predecessor_plans: PLAN-hyg-004-phase2a-2026-04-30.md (Phase 2A immediate predecessor; same mechanics; structural template) + PLAN-hyg-004-phase1-2026-04-30.md (Phase 1 baseline)
predecessor_audits: AUDIT-VERDICT-hyg-004-phase1-2026-04-30.md (D1/D2 drift adjudication precedent; ACCEPT ruling)
predecessor_commits: 0f4d0c56 (Phase 2A clean-close)
---

# PLAN — HYG-004 Phase 2B: Parametrize-Promote `tests/unit/test_tier2_adversarial.py` Webhook Signature-Validation Cluster

## §1 Plan Purpose

Collapse the webhook signature-validation cluster (TestWebhookSignatureVerificationValid + TestWebhookSignatureVerificationInvalid) in `tests/unit/test_tier2_adversarial.py` via two `@pytest.mark.parametrize` decorations (one per Valid/Invalid axis) over `(body, expected_sig, secret)` tuples while preserving HANDOFF AC 5 (assertion specificity) and AC 6 (coverage delta ≥ 0). Janitor executes mechanically; audit-lead verifies via cluster-collapse + 3-case specificity sample + coverage report. Plan honors charter §6.3 outcome adjudications: PHASE-2B-CLEAN-CLOSE preferred (anticipated with case-sensitivity SPLIT-AND-FOLD), PARAMETRIZE-PARTIAL-CLOSE acceptable, NO-OP-CLOSE only on hard non-collapsibility.

This is **Phase 2B** of HYG-004 multi-sprint residual: 2 of 3 adversarial files (tier2). Phase 2A (tier1) closed at commit `0f4d0c56`. Phase 2C (batch) deferred to subsequent sub-sprint D.

## §2 Pre-Flight Drift-Audit (Pattern-6 carry-forward, charter §8.1; D1/D2 pattern carry-forward from Phase 1+2A §2)

Re-probed at plan-authoring (2026-04-30, branch `hygiene/sprint-phase2-2026-04-30` HEAD `0f4d0c56`):

- File line count: **1582 lines** — VERIFIED via `wc -l`.
- HANDOFF cites **"lines 144-241, 11 tests"** under signature-validation pattern.
- Direct enumeration via `pytest --collect-only` returns:
  - `TestWebhookSignatureVerificationValid`: **5 tests** at L144-L187 (class declaration L141; first test L144; last test ends L187).
  - `TestWebhookSignatureVerificationInvalid`: **6 tests** at L193-L254 (class declaration L190; first test L193; last test ends L254).
  - Combined: **11 tests** spanning **L141-L254** (true cluster bounds, including class declarations).
- Pre-mutation collection count for the cluster: `pytest TestWebhookSignatureVerificationValid TestWebhookSignatureVerificationInvalid --collect-only -q` → **11 tests collected, all passing** (verified via `pytest -n0 --tb=short` → 11 passed in 1.08s).
- File-wide collection: 99 tests collected.
- SCAR ledger pre-mutation: **47** collected (charter §8.2 invariant; verified via `pytest -m scar --collect-only -q | tail`).
- Pre-mutation coverage baseline: `src/autom8_asana/clients` total = **26.62%**; `clients/webhooks.py` = **54%** (verified via `pytest --cov=src/autom8_asana/clients tests/unit/test_tier2_adversarial.py -n0`).

**Drift-finding D1 (CHARTER-vs-FILE count)**: HANDOFF cited 11 vs. file empirical 11. **NO COUNT DRIFT** (Phase 2A had off-by-six; Phase 2B is clean on count). The HANDOFF inventory captured this cluster faithfully.

**Drift-finding D2 (RANGE-vs-CLUSTER)**: HANDOFF cited L144-L241; actual cluster bounds L141-L254 (or L144-L254 if measuring from first test body line). HANDOFF range under-specified by 13 lines on the lower end (Invalid class extends to L254, not L241). **MINOR D2 drift** — smaller than Phase 2A's 23-line under-specification.

**Adjudication (architect-enforcer authority per AC interpretation, NOT AC amendment; precedent: Phase 1 audit §5 + Phase 2A §2 ACCEPT rulings)**: the **load-bearing intent** of HYG-004 Phase 2B AC is *"the signature-validation cluster spanning Valid + Invalid classes in test_tier2_adversarial"* — line range L144-L241 is illustrative anchor, not literal cluster bound. Plan operates on the operationally-real **11-test cluster across L141-L254 (two classes)**. Range divergence surfaced HERE for audit-lead transparency; precedent (Phase 1 §5 + Phase 2A §2) is ACCEPT.

**D1/D2 hypothesis on origin**: HANDOFF range L144-L241 likely captured L144 (first test line in Valid class) and L241 (start of `test_verify_signature_invalid_case_sensitivity` — the last test in Invalid class). The end-line truncation at L241 reflects line-of-test-declaration vs line-of-test-body-end — a probe-time observability bound, not a claim about cluster scope. ACCEPT operational empirical 11-test enumeration across L141-L254.

## §3 Cluster Enumeration (11 tests; HANDOFF cited 11 — D1 clean, D2 minor range drift)

**Class TestWebhookSignatureVerificationValid (5 tests; expected `is True`):**

| # | file:line | test_name | body | secret | signature derivation | assertion specifics |
|---|---|---|---|---|---|---|
| 1 | L144 | test_verify_signature_valid_empty_body | `b""` | `"test_secret"` | `hmac.new(secret.encode(), body, sha256).hexdigest()` | `result is True` |
| 2 | L153 | test_verify_signature_valid_json_body | `b'{"events":[{"resource":{"gid":"123"}}]}'` | `"my_webhook_secret_123"` | `hmac.new(secret.encode(), body, sha256).hexdigest()` | `result is True` |
| 3 | L162 | test_verify_signature_valid_large_body | `b"x" * 1_000_000` | `"secret"` | `hmac.new(secret.encode(), body, sha256).hexdigest()` | `result is True` |
| 4 | L171 | test_verify_signature_valid_unicode_secret | `b'{"test": "data"}'` | `"secret_with_unicode_"` | `hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()` | `result is True` |
| 5 | L180 | test_verify_signature_valid_binary_body | `bytes(range(256))` | `"secret"` | `hmac.new(secret.encode(), body, sha256).hexdigest()` | `result is True` |

**Class TestWebhookSignatureVerificationInvalid (6 tests; expected `is False` — except case_sensitivity which is dual-assertion):**

| # | file:line | test_name | body | tampered/secret manipulation | assertion specifics |
|---|---|---|---|---|---|
| 6 | L193 | test_verify_signature_invalid_wrong_signature | `b'{"events": []}'` | sig literal `"completely_wrong_signature"`, secret `"test_secret"` | `result is False` |
| 7 | L202 | test_verify_signature_invalid_truncated_signature | `b'{"test": "data"}'` | correct sig truncated to first 32 chars | `result is False` |
| 8 | L212 | test_verify_signature_invalid_wrong_secret | `b'{"test": "data"}'` | sig computed with `b"wrong_secret"`, verified against `"correct_secret"` | `result is False` |
| 9 | L220 | test_verify_signature_invalid_modified_body | original `b'{"events": []}'`, sig over original, verify against modified `b'{"events": [{"malicious": true}]}'` | sig mismatch via body tamper | `result is False` |
| 10 | L232 | test_verify_signature_invalid_empty_signature | `b'{"events": []}'` | sig literal `""`, secret `"test_secret"` | `result is False` |
| 11 | L241 | test_verify_signature_invalid_case_sensitivity | `b'{"test": "data"}'` | DUAL: lowercase sig (True branch) AND uppercase sig (False branch), secret `"test_secret"` | `assert ... is True` AND `assert ... is False` (TWO assertions) |

**Receipt-grammar attestation**: 11 enumerated; each row carries `file:line` anchor; expected return type uniform (`bool`); test target uniform (`WebhooksClient.verify_signature(body, sig, secret)`); assertion shape near-uniform (`result is True` for Valid; `result is False` for Invalid; row 11 dual).

**Structural homogeneity assessment**:
- Rows 1-5 (Valid): structurally identical modulo `(body, secret, sig-derivation-via-hmac)` tuple variation. Single parametrize G1 candidate.
- Rows 6-10 (Invalid): structurally identical modulo `(body, sig, secret, tamper-shape)` tuple variation. Single parametrize G2 candidate.
- Row 11 (case_sensitivity): **asymmetric outlier** — dual-assertion test exercising both directions of case sensitivity. Per Phase 1 §5 (kept `test_exponential_base_less_than_1` standalone) and Phase 2A §6 R3 (escape valve), this candidate triggers the SPLIT-AND-FOLD treatment: the True branch (lowercase sig) folds into G1 Valid set; the False branch (uppercase sig) folds into G2 Invalid set. This preserves both assertions across the parametrize boundary while collapsing to the single-axis G1/G2 shape.

## §4 Parametrize-Target Table (2 groups + 1 split-and-fold)

Cluster grouping is **two-group across Valid/Invalid axis with case_sensitivity SPLIT-AND-FOLD**. Rationale:

- Valid + Invalid classes have **opposite** expected return values (`True` vs `False`); collapsing them into one parametrize would require a per-tuple `expected: bool` axis — possible but obscures intent. Two-group preserves intent (verify-passes-on-correct-input vs verify-rejects-on-tampered-input) while collapsing within each axis.
- Row 11 case_sensitivity dual-assertion is preserved by splitting into TWO parametrize cases: `valid_lowercase_sig` (G1) + `invalid_uppercase_sig` (G2). The case-sensitivity intent is preserved structurally — both directions still exercised; only the per-test wrapping changes.

| Group | Target axis | Source rows (§3) | Parametrize tuple | Count IN | Count OUT |
|---|---|---|---|---|---|
| **G1 (Valid)** | `(body, secret)` per row | rows 1–5 + row 11 lowercase branch | `(body: bytes, secret: str)` — sig computed inside test via `hmac.new` | 5 + 1 = 6 cases | 1 parametrized test (6 cases) |
| **G2 (Invalid)** | `(body, sig, secret)` per row | rows 6–10 + row 11 uppercase branch | `(body: bytes, sig: str, secret: str)` — sig pre-computed in parametrize args (heterogeneous tamper shapes) | 5 + 1 = 6 cases | 1 parametrized test (6 cases) |

**Net counts**: 11 tests IN → **2 parametrized test functions OUT** (12 parametrize cases at runtime — note: 11 → 12 due to case_sensitivity SPLIT). Reduction: 11 → 2 functions = **81.8% function reduction**; runtime case count goes from 11 to 12 (+1 net case from SPLIT). HANDOFF AC target "collapsed via @pytest.mark.parametrize over (body, secret, signature) tuples" satisfied. Anticipated outcome: **PHASE-2B-CLEAN-CLOSE-WITH-CASE-SENSITIVITY-FOLD** (no retained standalone test; case_sensitivity split-and-folded into G1+G2).

**Why not single-group with `expected: bool` axis?** Considered. Rejected because:
1. The Invalid tests have heterogeneous **tamper shapes** (truncation, wrong-secret, body-tamper, empty-sig, case-shift) that are not naturally derivable from the body/secret pair — they require pre-computed `sig` strings in the parametrize args. The Valid tests derive sig FROM body+secret at test-time via `hmac.new`. Mixing these mechanics into one parametrize forces all sig computation out of the test body, which loses the readable "compute expected sig, verify accepts" pattern of the Valid tests.
2. Two-group preserves the documentary structure (two classes in source → two parametrized methods in target).

## §5 Mutation Pattern (single Edit)

Janitor performs ONE Edit replacing the contiguous L141-L254 source span (TestWebhookSignatureVerificationValid class body L141-L187 + blank line L188-L189 + TestWebhookSignatureVerificationInvalid class body L190-L254) with two classes each containing a single parametrized test method. Pattern:

```python
class TestWebhookSignatureVerificationValid:
    """Tests for valid webhook signature verification."""

    @pytest.mark.parametrize(
        ("body", "secret"),
        [
            (b"", "test_secret"),
            (b'{"events":[{"resource":{"gid":"123"}}]}', "my_webhook_secret_123"),
            (b"x" * 1_000_000, "secret"),
            (b'{"test": "data"}', "secret_with_unicode_"),
            (bytes(range(256)), "secret"),
            (b'{"test": "data"}', "test_secret"),
        ],
        ids=[
            "valid_empty_body",
            "valid_json_body",
            "valid_large_body",
            "valid_unicode_secret",
            "valid_binary_body",
            "valid_lowercase_sig_case_sensitivity",
        ],
    )
    def test_verify_signature_valid(self, body: bytes, secret: str) -> None:
        """verify_signature accepts correctly-derived signature for body+secret."""
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True


class TestWebhookSignatureVerificationInvalid:
    """Tests for invalid webhook signature rejection."""

    @pytest.mark.parametrize(
        ("body", "sig", "secret"),
        [
            (b'{"events": []}', "completely_wrong_signature", "test_secret"),
            (
                b'{"test": "data"}',
                hmac.new(b"test_secret", b'{"test": "data"}', hashlib.sha256).hexdigest()[:32],
                "test_secret",
            ),
            (
                b'{"test": "data"}',
                hmac.new(b"wrong_secret", b'{"test": "data"}', hashlib.sha256).hexdigest(),
                "correct_secret",
            ),
            (
                b'{"events": [{"malicious": true}]}',
                hmac.new(b"test_secret", b'{"events": []}', hashlib.sha256).hexdigest(),
                "test_secret",
            ),
            (b'{"events": []}', "", "test_secret"),
            (
                b'{"test": "data"}',
                hmac.new(b"test_secret", b'{"test": "data"}', hashlib.sha256).hexdigest().upper(),
                "test_secret",
            ),
        ],
        ids=[
            "invalid_wrong_signature",
            "invalid_truncated_signature",
            "invalid_wrong_secret",
            "invalid_modified_body",
            "invalid_empty_signature",
            "invalid_uppercase_sig_case_sensitivity",
        ],
    )
    def test_verify_signature_invalid(self, body: bytes, sig: str, secret: str) -> None:
        """verify_signature rejects mismatched/tampered signature."""
        result = WebhooksClient.verify_signature(body, sig, secret)
        assert result is False
```

**Mutation invariants**:
- G1 Valid: `(body, secret)` tuple is the parametrize axis; sig is **computed inside the test body** via the original `hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()` pattern — preserves the Valid-class semantic (test attests round-trip identity: secret + body → derived sig → verifies). Row 4's `secret.encode("utf-8")` is **functionally equivalent** to `secret.encode()` (Python 3 default encoding is utf-8); plan uses `.encode()` for uniformity. (Hard-stop on this collapse: if any reviewer surfaces concern about explicit-utf8 vs default encoding, escalate to PARAMETRIZE-PARTIAL-CLOSE retaining row 4 standalone. Confidence: HIGH that they are equivalent per CPython docs; accept the collapse.)
- G2 Invalid: `(body, sig, secret)` tuple — sig is **pre-computed in parametrize args** for each tamper shape. The tampering mechanic is encoded directly in the args list (`.upper()`, `[:32]`, body mismatch, etc.). Test body is uniform: `WebhooksClient.verify_signature(body, sig, secret)`.
- Case-sensitivity SPLIT-AND-FOLD: original test asserted `assert ... is True` (lowercase) AND `assert ... is False` (uppercase) within one function. SPLIT folds the True branch into G1 (id `valid_lowercase_sig_case_sensitivity`) and the False branch into G2 (id `invalid_uppercase_sig_case_sensitivity`). Both branches preserved; semantic intent (case-sensitivity matters) preserved structurally via the SPLIT id naming.
- `ids=` lists mirror the operative portion of original test function names (drop leading `test_verify_signature_` prefix per pytest convention; case_sensitivity gets a clarifying suffix `_case_sensitivity`). Preserves `pytest -k "valid_empty_body"` filter compatibility.
- Type hints `body: bytes, secret: str, sig: str` are added (file convention permits per Phase 2A §6 R6 precedent — broad-but-correct typing on parametrized methods).
- Docstrings: class docstrings preserved verbatim; per-test docstrings collapsed into single docstring per parametrized method (faithful generalization per Phase 2A §6 R7 precedent).

**Single Edit block**:
- **G1+G2 (signature validation)**: Edit replaces L141-L254 (11 tests + 2 class bodies, ~114 lines) with 2 classes + 2 parametrized methods (~75 lines). Net: **~−39 lines**.

There is only one Edit; no reverse-line-order discipline required (Phase 2A §5 single-Edit precedent applies; this is also single-Edit).

## §6 Assertion-Specificity-Preservation Rules (HANDOFF AC 5 hard gate)

R1 — **Per-case assertion shape uniform within group**: G1 every case asserts `result is True` (NOT `assert result` truthy-cast; NOT `result == True`). G2 every case asserts `result is False`. The `is`-identity assertion is the load-bearing specificity — confirms exactly the bool sentinel returned, not a truthy-casted intermediate.

R2 — **Test target binding**: every case calls `WebhooksClient.verify_signature(body, sig, secret)` — uniform across all 11 source tests (incl. row 11). No relaxation to a wrapper / helper.

R3 — **Structural outlier escape valve (FIRES on row 11 case_sensitivity)**: per Phase 1 §6 R3 precedent (kept `test_exponential_base_less_than_1` standalone) and Phase 2A §6 R3 (escape valve declared, not exercised), this phase **does fire R3** on row 11 — but in the SPLIT-AND-FOLD form rather than retain-standalone form. The dual-assertion test is split across the G1/G2 boundary, NOT retained as standalone. Rationale: retaining it standalone would forfeit the AC's "collapsed via @pytest.mark.parametrize" goal for one of the cited 11 tests (10/11 collapsed, 1 retained = PARAMETRIZE-PARTIAL-CLOSE shape). SPLIT-AND-FOLD achieves 11/11 collapse (with +1 case from the dual-assertion split); the True/False intent is preserved structurally across the two parametrized methods. If audit-lead refuses SPLIT-AND-FOLD interpretation, ESCAPE PATH: retain row 11 standalone → escalate to PARAMETRIZE-PARTIAL-CLOSE.

R4 — **Test-id preservation**: pytest collection ids (via `ids=`) match operative portion of original function names. `pytest -k "valid_empty_body"` continues to resolve via parametrize id substring match. Row 11's split is naming-disambiguated: `valid_lowercase_sig_case_sensitivity` + `invalid_uppercase_sig_case_sensitivity` retain the `case_sensitivity` substring for `-k` filter discoverability.

R5 — **No assertion-side relaxation**: the `is True` / `is False` identity-comparison is preserved verbatim. Janitor MUST NOT loosen to `assert result` / `assert not result` / `result == True`.

R6 — **HMAC computation parity**: the sig-derivation pattern `hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()` is preserved verbatim (modulo `.encode()` default vs `.encode("utf-8")` per row 4 — see §5 mutation invariants; Python 3 default is utf-8, semantically identical). Janitor MUST NOT substitute `hashlib.sha256(...).hexdigest()` (non-HMAC) — that would silently break the security invariant under test.

R7 — **Audit-lead 3-case specificity sample**: per charter §6.2, audit-lead samples 3 of the 12 collected cases and confirms the original assertion-shape is present. Janitor surfaces sample candidates: (G1 row 1 `valid_empty_body` — boundary), (G2 row 7 `invalid_truncated_signature` — middle of Invalid cluster, exercises sig-truncation), (G2 case_sensitivity uppercase fold `invalid_uppercase_sig_case_sensitivity` — verifies SPLIT-AND-FOLD preserves the False branch).

R8 — **Docstring preservation (cluster-level)**: class docstrings (`"Tests for valid webhook signature verification."` / `"Tests for invalid webhook signature rejection."`) preserved verbatim. The 11 individual test docstrings are collapsed into 2 docstrings (one per parametrized method). Lost-information surface bounded: each original docstring was a one-line restatement of the test name; collapse to `"verify_signature accepts correctly-derived signature for body+secret."` (G1) / `"verify_signature rejects mismatched/tampered signature."` (G2) is a faithful generalization.

## §7 Coverage-Delta Verification (HANDOFF AC 6 hard gate)

**Pre-mutation baseline** (captured at plan authoring; janitor re-confirms before mutation):
```
pytest --cov=src/autom8_asana/clients --cov-report=term tests/unit/test_tier2_adversarial.py -n0
→ src/autom8_asana/clients TOTAL: 26.62%
→ src/autom8_asana/clients/webhooks.py: 54%
```
Capture: total coverage % on `src/autom8_asana/clients` package + per-file webhooks.py.

**Post-mutation re-run** (janitor last action, pre-commit):
```
pytest --cov=src/autom8_asana/clients --cov-report=term tests/unit/test_tier2_adversarial.py -n0
```
Capture: same metrics on same package scope.

**Pass criterion**: post % ≥ pre % for `src/autom8_asana/clients` package AND `webhooks.py` per-file (strict ≥). Tolerance: 0.0%. If `< pre`: HALT, surface to audit-lead, route as PARAMETRIZE-PARTIAL-CLOSE. NO silent coverage loss (charter §8.3 + §11.5).

**Why clients-package + per-file webhooks.py**: the cluster exercises `WebhooksClient.verify_signature` (security-critical HMAC path). Per-file scoping on `webhooks.py` is the tightest gate — a 1% regression on this file is the only tactical signal that would matter to audit-lead. Package-wide is the broader sanity check. Project-wide is dominated by services/transport untouched by this file.

**SCAR ledger probe** (charter §8.2): pre/post `pytest -m scar --collect-only -q | tail -3` MUST show ≥47. Pre-mutation confirmed: **47 SCAR tests collected**.

**Full-suite verification** (charter §8.3 + dispatch protocol Step 3): post-mutation
```
pytest -n 4 --dist=load tests/unit/ --tb=short -q
```
MUST exit 0. Tolerate pre-existing flakies `test_performance_under_1ms` + `test_zero_window_immediate_execution` per Phase 2A finding §9 (those are unrelated to this work).

**Collection-count expectation**: pre-mutation 99 tests in tier2_adversarial; post-mutation = 99 − 11 + 12 = **100 tests** (11 source tests collapse into 2 parametrized functions producing 12 runtime cases due to row 11 SPLIT). Janitor verifies `pytest tests/unit/test_tier2_adversarial.py --collect-only -q | tail -3` shows exactly 100. If anything other than 100, HALT.

**Clarification on SPLIT case-count net**: Phase 2A had 8 source → 8 parametrize cases = 0 net. Phase 2B has 11 source → 12 parametrize cases = +1 net (row 11 dual-assertion split into two single-assertion cases). This is **expansion-by-design** to preserve specificity across SPLIT-AND-FOLD.

## §8 Atomic Commit Shape

**Single commit** per Q2 (charter §5 — atomic single commit per Phase 2 sub-sprint). Rationale: single Edit, single logical change, single semantic intent (parametrize the signature-validation cluster across two Valid/Invalid classes).

Commit message (per `conventions` skill — user-only attribution; NO Co-Authored-By per fleet conventions for git commits; the dispatch directive's Co-Authored-By line is overridden by `conventions` per Phase 2A §8 precedent):

```
refactor(tests): parametrize-promote tier2_adversarial signature-validation cluster (HYG-004 Phase 2B)

Sub-sprint C close per Phase 2 charter §5. Collapses 11 signature-validation
tests in tests/unit/test_tier2_adversarial.py (TestWebhookSignatureVerificationValid
+ TestWebhookSignatureVerificationInvalid classes) into 2 parametrized cases
across (body, secret) for Valid axis and (body, sig, secret) for Invalid axis
— 81.8% function-count reduction; 11→12 runtime case count via case_sensitivity
SPLIT-AND-FOLD (row 11 dual-assertion split across G1/G2 boundary preserves
both True/False branches).

Outcome: PHASE-2B-CLEAN-CLOSE-WITH-CASE-SENSITIVITY-FOLD (no retained
standalone; row 11 case_sensitivity preserved via structural SPLIT-AND-FOLD
into valid_lowercase_sig_case_sensitivity + invalid_uppercase_sig_case_sensitivity
ids per plan §6 R3).

Drift findings (D1: HANDOFF cited 11 tests, empirical 11 — CLEAN; D2: HANDOFF
cited L144-L241, actual cluster L141-L254 — minor 13-line range under-spec)
ACKNOWLEDGED per plan §2 Pattern-6 drift-audit-discipline; precedent: Phase 1
audit §5 + Phase 2A §2 ACCEPT rulings.

Coverage delta: ≥0 on src/autom8_asana/clients package and clients/webhooks.py
per-file (verified pre/post via plan §7).
SCAR ≥47 preserved; specificity preserved (is True / is False identity).

Discharges: HANDOFF-eunomia-to-hygiene HYG-004 Phase 2B
(2 of 3 adversarial files; batch_adversarial in subsequent sub-sprint D).
```

## §9 Out-of-Scope Refusal (charter §8.4 inviolable)

Janitor MUST NOT touch:
- Other clusters in `tests/unit/test_tier2_adversarial.py` outside the signature-validation cluster: TestWebhookSignatureTimingSafety (L257+; 2 tests), TestWebhookHandshakeSecretExtraction (L288+; 8 tests), TestAttachmentUploadEdgeCases / TestAttachmentUploadFromPath / TestAttachmentExternalCreation / TestAttachmentDownload (attachment cluster), TestGoalsSubgoalOperations / TestGoalsSupportingWork / TestGoalsFollowers / TestGoalsMetricHandling (goals cluster), TestPortfoliosItemManagement / TestPortfoliosMembers / TestPortfoliosCustomFields (portfolios cluster), TestModelEdgeCases* (models cluster), TestRawModeTier2 — UNCHANGED.
- `tests/unit/test_tier1_adversarial.py` (HYG-004 Phase 2A; closed at commit `0f4d0c56`)
- `tests/unit/test_batch_adversarial.py` (HYG-004 Phase 2C; sub-sprint D HANDOFF AC 3)
- `tests/unit/test_config_validation.py` (Phase 1 closed; commit `42ade735`)
- Any file under `src/autom8_asana/**` (production code; charter §8.4 out-of-scope)
- `pyproject.toml`, `.know/test-coverage.md`, CI shape

Any out-of-scope edit attempt → janitor HALTS per charter §8.3.

## §10 Risks (charter §11 cross-reference)

R-1 (§11.3) — **Assertion specificity loss via SPLIT-AND-FOLD** (low-medium likelihood, medium impact). Mitigation: §6 R1–R7 + audit-lead 3-case sample (§6 R7) explicitly including the case_sensitivity uppercase fold to verify SPLIT preserves the False branch. Detection: audit-lead refuses verdict on SPLIT-AND-FOLD → HALT, escalate to PARAMETRIZE-PARTIAL-CLOSE (retain row 11 standalone). Higher likelihood than Phase 2A because of SPLIT-AND-FOLD novelty; mitigated by explicit naming convention preserving `case_sensitivity` in both ids.

R-2 (§11.5) — **Coverage delta regression** (low likelihood, low impact). Mitigation: §7 pre/post measurement on clients-package + per-file webhooks.py + strict ≥ gate. Detection: post-run `<` pre-run → HALT, route PARAMETRIZE-PARTIAL-CLOSE. Lower impact because the 11 tests exercise a single function (`verify_signature`) — the coverage delta resolution is bounded by that function's branch count.

R-3 (§11.4) — **SCAR collection regression** (low likelihood, high impact). Mitigation: charter §8.2 ≥47 marker probe pre/post. Detection: collection count <47 → HALT immediately.

R-4 (carried from Phase 1+2A) — **AC interpretation challenge on D2 range drift** (low likelihood, low impact). HANDOFF cited L144-L241; plan operates on L141-L254. Smaller drift than Phase 2A (13 lines vs 23 lines). Mitigation: §2 D1/D2 transparent surfacing + precedent ACCEPT rulings.

R-5 — **Class-body Edit boundary error** (low likelihood, medium impact). The Edit replaces L141-L254 (TWO class bodies + interleaving blank lines). Janitor MUST verify the Edit's `old_string` match boundary stops at L254 (last `assert` of `test_verify_signature_invalid_case_sensitivity`) and does NOT include L257 `class TestWebhookSignatureTimingSafety` declaration or L255-L256 separator blank lines. Mitigation: pre-Edit Read of L141-L260 to confirm class-body bounds; post-Edit syntax-check via `python -m py_compile`.

R-6 — **`secret.encode("utf-8")` collapse to `.encode()` on row 4** (very low likelihood, very low impact). Per CPython docs, default `str.encode()` is utf-8. Mitigation: confidence is HIGH; if any reviewer surfaces concern, the parametrize args can be changed to a list comprehension with explicit `.encode("utf-8")` or row 4 retained standalone. Accept the collapse.

R-7 — **Pre-existing flakies `test_performance_under_1ms` + `test_zero_window_immediate_execution` flag again** (medium likelihood, low impact). Phase 2A finding §9 documented these as unrelated to refactor work. Mitigation: tolerate per Phase 2A precedent; full-suite verification distinguishes refactor-introduced regression from pre-existing flake.

**No HALT-required risks at plan-authoring time**. PHASE-2B-CLEAN-CLOSE-WITH-CASE-SENSITIVITY-FOLD is the anticipated outcome; PARAMETRIZE-PARTIAL-CLOSE escape valve preserved per charter §6.3 (retain row 11 standalone if SPLIT-AND-FOLD refused by audit-lead).

---

**Plan attestation table**:

| Artifact | Path | Verified-via |
|---|---|---|
| HANDOFF substrate | dispatch directive (Phase 2 charter §5 sub-sprint C) | dispatch text in-context |
| Phase 2A plan precedent | `.sos/wip/hygiene/PLAN-hyg-004-phase2a-2026-04-30.md` | Read tool L1-L249 |
| Phase 1 plan precedent | `.sos/wip/hygiene/PLAN-hyg-004-phase1-2026-04-30.md` | dispatch text reference |
| Phase 2A commit | `0f4d0c56` (current HEAD) | `git log -5 --oneline` |
| Source file | `tests/unit/test_tier2_adversarial.py` | Read tool L1-L260 |
| Cluster enumeration | 11 tests across L141-L254 | `pytest --collect-only -q` |
| Pre-mutation cluster pass | 11/11 PASS | `pytest TestWebhookSignatureVerification* -n0 --tb=short` |
| Pre-mutation file collection | 99 tests | `pytest --collect-only -q` |
| Pre-mutation SCAR | 47 collected | `pytest -m scar --collect-only -q` |
| Pre-mutation coverage | clients pkg 26.62%, webhooks.py 54% | `pytest --cov=src/autom8_asana/clients` |
| Branch state | `hygiene/sprint-phase2-2026-04-30` HEAD `0f4d0c56` | `git branch --show-current && git log -1` |

— architect-enforcer, 2026-04-30
