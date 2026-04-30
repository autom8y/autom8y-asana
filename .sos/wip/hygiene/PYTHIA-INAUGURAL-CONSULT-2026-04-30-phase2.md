---
artifact_id: PYTHIA-INAUGURAL-CONSULT-2026-04-30-hygiene-phase2
schema_version: "1.0"
type: design
artifact_type: charter
slug: phase2-2026-04-30
rite: hygiene
initiative: hygiene-phase2-hyg002-phase2-hyg004-phase2-discharge
complexity: INITIATIVE
phase_posture: PLAN
session_id: session-20260430-144514-3693fe01
predecessor_session: session-20260430-131833-8c8691c1
predecessor_charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint
parent_handoff: HANDOFF-eunomia-to-hygiene-2026-04-29
sprint_id: sprint-20260430-phase2-hyg2-hyg4
authored_by: pythia (consultative throughline) + main-thread (materialization)
authored_at: 2026-04-30
evidence_grade: MODERATE
self_grade_ceiling_rationale: "Pythia self-authoring; MODERATE per self-ref-evidence-grade-rule"
authoring_style: prescriptive-charter
governance_status: governing
inherits_from:
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint (direct predecessor — Phase 1 charter)
  - HANDOFF-eunomia-to-hygiene-2026-04-29 (governing item list; items_status post-PR #47)
  - AUDIT-VERDICT-hyg-002-phase1-2026-04-30 (Phase 1 HYG-002 verdict + paginator drift signal)
  - AUDIT-VERDICT-hyg-004-phase1-2026-04-30 (Phase 1 HYG-004 verdict + D1/D2 drift discipline)
status: governing
---

# PYTHIA INAUGURAL CONSULT — /hygiene Phase 2 (phase2-2026-04-30)

## §1 Telos Restatement

User invocation (verbatim, inherited from Phase 1 charter §1, capture timestamp 2026-04-30T14:45Z):

> *"max rigor max vigor taking no prisoners"* autonomous /sprint workflows — same posture as Phase 1 (PR #47 merged 2026-04-30T12:38Z). Discharge HYG-002 Phase 2 (1 next high-density consumer file) + HYG-004 Phase 2 (3 adversarial files completing the parametrize-promote campaign).

User authority grant for full-pantheon orchestration continues through engagement close. Halt only on hard-fail conditions per §8 inviolable constraints. The "taking no prisoners" intensification clause is entrenched from Phase 1 — no scope-creep absorption, no soft-close, no theater.

**Engagement-chain position**:
- PR #44 (perf, 2026-04-29T23:00Z): -49% wallclock
- PR #45 (HYG-001, 2026-04-30T09:30Z): 47 markers operational
- PR #46 (sre Sprint-2, 2026-04-30T11:08Z): 4 NO-LEVER ADRs + coverage gate
- PR #47 (hygiene Phase 1, 2026-04-30T12:38Z, merge commit `550ec57a`): HYG-002 Phase 1 (root fixtures + lifecycle_smoke, 47 sites) + HYG-003 (full discharge) + HYG-004 Phase 1 (test_config_validation.py, 27→6 functions)
- **THIS Phase 2 sprint**: closes HYG-002 multi-sprint increment (1 next file) + HYG-004 full discharge (3 of 4 adversarial files — tier1/tier2/batch)

**Post-Phase-1 HANDOFF status**:
- HYG-001: CLOSED (PR #45)
- HYG-002: in_progress — Phase 1 discharged root fixtures + `test_lifecycle_smoke.py`; Phase 2 targets next high-density consumer from remaining candidates
- HYG-003: CLOSED (PR #47)
- HYG-004: in_progress — Phase 1 discharged `test_config_validation.py`; Phase 2 targets `test_tier1_adversarial.py` + `test_tier2_adversarial.py` + `test_batch_adversarial.py`

**Anchor-return question** (per `telos-integrity-ref §5`): Three named user-visible outcomes verifiable by rite-disjoint measurement: (a) 1 next high-density consumer test file has `MagicMock(spec=)` applied across its unspec'd sites within Phase 2 scope envelope (HYG-002 Phase 2); (b) `tests/unit/test_tier1_adversarial.py` TestModelRequiredFields 14-test cluster collapsed via `@pytest.mark.parametrize` (HYG-004 Phase 2A); (c) `tests/unit/test_tier2_adversarial.py` signature validation cluster + `tests/unit/test_batch_adversarial.py` validation cluster collapsed via `@pytest.mark.parametrize` (HYG-004 Phase 2B + 2C), with SCAR-47 preserved and coverage delta >= 0 for each.

---

## §2 Engagement Scope

| Field | Lock |
|---|---|
| Track | Test/fixture surface — mock spec= adoption Phase 2 + parametrize-promote Phase 2 |
| Complexity | **INITIATIVE** (multi-sub-sprint; pantheon orchestration) |
| Phase posture | **PLAN** (this charter precedes Sub-sprint A code-smeller dispatch) |
| Sprint structure | A (HYG-002 Phase 2) → B (HYG-004 Phase 2A tier1) → C (HYG-004 Phase 2B tier2) → D (HYG-004 Phase 2C batch) → E (close) |
| Pantheon | potnia (orchestrator) \| code-smeller (HYG-002 scoping) \| architect-enforcer (per-sub-sprint plans) \| janitor (execution) \| audit-lead (verification) |
| Authority | in-rite full on test surface; refusal posture entrenched on production code + CI shape |
| Inviolable constraints | drift-audit re-dispatch, SCAR preservation (≥47 operational), refusal posture (§8) |
| Branch | `hygiene/sprint-phase2-2026-04-30` (cut from main@`550ec57a` = PR #47 merge) |

---

## §3 Inheritance Audit (per `inherited-charter-audit-discipline`)

### §3.1 INHERITED (preserved verbatim from Phase 1 charter)

- Pattern-6 drift-audit re-dispatch (grandparent perf §4.1 → Phase 1 §3.1 → Phase 2 §3.1)
- SCAR cluster preservation OPERATIONAL (≥47 markers post-HYG-001; verified at 47 post-Phase-1 via AUDIT-VERDICT-hyg-004-phase1-2026-04-30 §3.3)
- Halt-on-fail discipline (per perf charter §8.3 → Phase 1 §8.3)
- Refusal posture (production code + CI shape out-of-scope per perf charter §3.2 → Phase 1 §8.4)
- Drift-audit-discipline skill synthesis-altitude clause
- Atomic-revertibility per commit (per perf charter §8 → Phase 1 §8.5)
- D1/D2 discipline: re-probe AC line ranges at plan authoring time (AUDIT-VERDICT-hyg-004-phase1 §5 — D1/D2 pattern likely recurs at adversarial files)
- PARAMETRIZE-PARTIAL-CLOSE as valid close path for HYG-004 Phase 2 files
- Per-sub-sprint ADR discipline
- HYG-001 audit pattern (~200-line plan + ~200-line verdict per /task)
- Audit-lead verification gate per HYG-001 pattern

### §3.2 APPENDED (new at Phase 2 altitude)

- **HYG-002 Phase 2 file-selection adjudication** (Q1 — §4.1 below)
- **HYG-004 Phase 2 commit-shape adjudication** (Q2 — §6.1 below): 3 atomic commits (one per adversarial file) or 1 consolidated?
- **Sprint structure adjudication** (Q3 — §2 above): 5 sub-sprints (A=HYG-002P2, B=tier1, C=tier2, D=batch, E=close)
- Empirical re-probe requirement for adversarial file line ranges (D1/D2 carry-forward from Phase 1)
- Phase 2 sub-sprint sequencing: B/C/D are HYG-004-only and may proceed in order (each independent per HANDOFF); A (HYG-002P2) is independent of B/C/D — may proceed concurrently in worktree split if pantheon supports it, but default is serial A→B→C→D→E
- HANDOFF final discharge gate at Sub-sprint E: HYG-002 and HYG-004 both close to `closed` status (Phase 2 is the campaign terminus for HYG-004; HYG-002 is multi-sprint so `closed` on the Phase-2 increment, with `in_progress` retained for overall campaign if further phases needed)

### §3.3 DELTA'd

- Branch changes from `hygiene/sprint-residuals-2026-04-30` (Phase 1) to `hygiene/sprint-phase2-2026-04-30` (Phase 2). All commits go to the new branch; PR base is main@`550ec57a`.
- HANDOFF items_status at Phase 2 close: HYG-004 → `closed` (all 4 files done after Phase 2 completes AC#1/2/3/4); HYG-002 → `in_progress` continues (multi-sprint campaign; Phase 2 discharges 1 more file)

---

## §4 Sub-sprint A Charter — HYG-002 Phase 2 (BLOCKING)

### §4.1 Q1 Adjudication: File Selection

**Probe-time empirical counts (2026-04-30, post-PR #47 merge, branch hygiene/sprint-phase2-2026-04-30):**

| File | Total MagicMock/AsyncMock | Spec'd (post-Phase-1) | Unspec'd | Notes |
|---|---|---|---|---|
| `tests/unit/lambda_handlers/test_workflow_handler.py` | 273 | 0 | ~87 (MagicMock()/AsyncMock() bare) | SCAR-026 critical path; lambda handler entrypoint; `--dist=loadfile` isolation required |
| `tests/unit/lifecycle/test_engine.py` | 100 | 0 | 32 bare | 1,015 lines |
| `tests/unit/models/business/test_hydration.py` | 178 | 0 | ~178 | Path: `tests/unit/models/business/test_hydration.py` (not `tests/unit/lifecycle/test_hydration.py`) |
| `tests/unit/models/business/test_workspace_registry.py` | 4 | 0 | ~4 | Very low density |

**Note on HANDOFF Phase 2 candidate list**: HANDOFF cited `tests/unit/lifecycle/test_hydration.py` (62 mocks) and `tests/unit/cache/test_workspace_registry.py` (48 mocks) — these paths do not exist. Actual paths are `tests/unit/models/business/test_hydration.py` (178 mocks) and `tests/unit/models/business/test_workspace_registry.py` (4 mocks). D2-pattern (representative vs literal) applies — HANDOFF paths were directional anchors, not exact paths. Empirical probe at plan authoring time is authoritative.

**Locked path**: `tests/unit/lambda_handlers/test_workflow_handler.py`

**Rationale**:
1. **Highest SCAR-026 exposure**: lambda-handler entrypoint (`test_workflow_handler.py`) is the orchestration critical path — unspec'd mocks on this surface allow silent API drift through the lambda execution boundary. SCAR-026 mitigation thesis is most impactful here.
2. **HANDOFF recommendation confirmed empirically**: HANDOFF §HYG-002 notes item explicitly cites this file; user invocation recommends it; empirical re-probe confirms 87 bare mocks (the HANDOFF's "105 mocks" count was pre-Phase-1 total including fixtures cascaded from conftest; post-Phase-1 conftest fixtures are now spec'd, so the residual unspec'd count in this file is ~87).
3. **`--dist=loadfile` note**: `tests/unit/lambda_handlers/test_workflow_handler.py` is explicitly called out in `.know/test-coverage.md` as requiring `--dist=loadfile` for process-global state isolation. Architect-enforcer plan must note this constraint in its verification step.
4. **Alternatives assessed**:
   - `test_engine.py` (lifecycle, 32 unspec'd): Good candidate but lower SCAR-026 exposure than lambda handler
   - `test_hydration.py` (business models, 178 mocks): Higher total count but less critical path exposure
   - `test_workspace_registry.py` (business models, 4 mocks): Too low density; not worth a sub-sprint

### §4.2 Phase 2 Scope Envelope

Phase 2 envelope is NOT "all 87 unspec'd mocks." Scope is determined by code-smeller canonical-type resolution audit at Sub-sprint A dispatch time. Per Phase 1 pattern (PLAN-hyg-002-phase1 §3, §5), deferred-cluster categories apply:
- Clusters where canonical types cannot be resolved (no Protocol in `src/`) → DEFER with route
- Pydantic model mocks that interact with `_bootstrap_session` → DEFER (forward-ref risk)
- Per-method `AsyncMock()` attaches → DEFER where shape is unclear

**Expected outcome range**: 30-70 of 87 bare mocks specifiable in Phase 2 scope; code-smeller determines exact envelope.

### §4.3 Reproduce-first protocol (timebox 2-4hr per HYG-001 pattern)

1. **code-smeller** scopes mock surface with `Skill("smell-detection")` preload; enumerates all `MagicMock()\|AsyncMock()` sites with canonical-type binding candidates; produces SCOPE artifact at `.sos/wip/hygiene/SCOPE-hyg-002-phase2-2026-04-30.md`
2. **architect-enforcer** plans (~200 lines at `.sos/wip/hygiene/PLAN-hyg-002-phase2-2026-04-30.md`): ordered spec= application list; deferred-cluster table; SCAR preservation gate; `--dist=loadfile` requirement note; interface-drift routing rules
3. **janitor** executes: atomic single commit; `pytest tests/unit/lambda_handlers/test_workflow_handler.py --tb=short -q` exits 0; SCAR ≥47; verify with `pytest -m scar --collect-only -q | tail -3`
4. **audit-lead** verifies (~200 lines at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-002-phase2-2026-04-30.md`): per-AC ledger; interface-drift findings filed per HYG-002 AC 5; deferred-cluster verification

### §4.4 Outcome adjudications
- **PHASE-2-CLEAN-CLOSE**: workflow_handler spec'd within envelope; tests pass; SCAR preserved; no drift
- **PHASE-2-CLOSE-WITH-DRIFT-FINDINGS**: drift filed as sub-issues per HYG-002 AC 5; Phase 2 still closes
- **NO-LEVER**: canonical types unresolvable for sufficient sites; ADR partial close; Phase 2 close with deferred-site list

### §4.5 Paginator drift carry-forward (from Phase 1 AUDIT §8.2)

Phase 1 audit identified paginator stubs at `test_lifecycle_smoke.py:L105/L480/L523/L581/L1384` lacking canonical `PaginatorProtocol` in `src/autom8_asana/protocols/`. If `test_workflow_handler.py` has similar paginator-adjacent stubs: same disposition — route to /eunomia, do NOT attempt spec= on non-existent Protocol type.

---

## §5 Sub-sprint B Charter — HYG-004 Phase 2A: test_tier1_adversarial.py (BLOCKING)

### §5.1 Target cluster

**File**: `tests/unit/test_tier1_adversarial.py` (1,817 lines; 102 tests)

**Cluster**: `class TestModelRequiredFields` at line 54; test methods at lines 57, 65, 73, 81, 89, 97, 105, 113.

**Empirical count at probe time**: 8 `def test_*` methods in `TestModelRequiredFields` (lines 57-120 covering workspace, user, project, section, custom_field, custom_field_enum_option, custom_field_setting, namegid).

**HANDOFF AC#1 citation**: "14-test cluster at lines 54-96." D2-pattern: HANDOFF line range (54-96) is a directional anchor; actual class ends after line 113 (8th method). D1-pattern: HANDOFF says 14 tests; empirical probe shows 8 methods in `TestModelRequiredFields`. Architect-enforcer MUST re-probe `grep -n "def test_" tests/unit/test_tier1_adversarial.py | sed -n '1,20p'` at plan time and treat the result as authoritative. D1/D2 adjudication follows Phase 1 OPTION A pattern (HANDOFF counts approximate; empirical is authoritative).

**Collapse shape**: Each test validates that a Pydantic model raises `ValidationError` when a required field (`gid`) is missing. Pattern is structurally uniform — same assertion shape per test (construct without `gid` → expect `ValidationError` → assert `gid` in error). `@pytest.mark.parametrize` over model classes is the natural collapse.

**Expected outcome**: 8 tests → 1 parametrized function (7→1 function reduction) OR PARAMETRIZE-PARTIAL-CLOSE if any test has structurally non-conforming assertion.

### §5.2 Reproduce-first protocol

1. **architect-enforcer** re-probes actual cluster at plan time; plans (~200 lines at `.sos/wip/hygiene/PLAN-hyg-004-phase2a-2026-04-30.md`): parametrize table; assertion-specificity-preservation rules; coverage-delta verification; SCAR gate
2. **janitor** executes: atomic single commit; `pytest tests/unit/test_tier1_adversarial.py --tb=short -q` exits 0; coverage delta ≥0; SCAR ≥47
3. **audit-lead** verifies (~200 lines at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-004-phase2a-2026-04-30.md`): per-AC ledger; D1/D2 adjudication; specificity preservation 3-case sample

### §5.3 Outcome adjudications (mirror Phase 1 §6.3)

- **PHASE-2A-CLEAN-CLOSE**: cluster collapses cleanly; all tests pass; SCAR preserved; coverage ≥0
- **PARAMETRIZE-PARTIAL-CLOSE**: some tests resist collapse per R3 (structurally non-conforming assertion); retained standalone; valid close path
- **NO-OP-CLOSE**: cluster non-collapsible; ADR; defer

---

## §6 Sub-sprint C Charter — HYG-004 Phase 2B: test_tier2_adversarial.py (sequential post-B)

### §6.1 Q2 Adjudication: Commit Shape for HYG-004 Phase 2

**Q2: Single commit covering all 3 files OR 3 atomic commits per-file?**

**Locked path**: **3 atomic commits (one per file)**.

**Rationale**:
1. Phase 1 charter §8.5 entrenches atomic-revertibility per commit. Each file is independent per HANDOFF §HYG-004 notes ("Each file is one /task. Order doesn't matter; all 4 are independent."). A single 3-file commit bundles independent changes, reducing revertibility granularity.
2. If Phase 2A (tier1) produces an unexpected cascade (test failures in other files), atomic commits isolate the regression to the correct file. A bundled commit would require file-level surgery on revert.
3. Audit-lead verdict artifacts are naturally per-file; 3 separate verdicts with their own commit-SHA references are cleaner than a single verdict covering 3 files.
4. Cost: trivial (3 commits vs 1 is marginally more ceremony; no substantive extra work).

**Commit shape ruling**: Sub-sprint B, C, D each produce one atomic commit for their respective adversarial file. Sub-sprint E (close) produces the PR.

### §6.2 Target cluster

**File**: `tests/unit/test_tier2_adversarial.py` (1,582 lines; 102 tests by wc rough estimate)

**Cluster**: Per HANDOFF AC#2 "signature validation cluster (lines 144-241, 11 tests)" and empirical probe:
- `class TestWebhookSignatureVerificationValid` at line 141 (5 tests: lines 144-187)
- `class TestWebhookSignatureVerificationInvalid` at line 190 (6 tests: lines 193-250)

**D2-pattern**: HANDOFF range "144-241" approximates the Valid+Invalid cluster; actual boundary extends to ~L255 per `class TestWebhookSignatureTimingSafety:` at line 257. Architect-enforcer must re-probe at plan time.

**D1-pattern**: HANDOFF says "11 tests" — empirical count from probe: Valid (L144/153/162/171/180 = 5 tests) + Invalid (L193/202/212/220/232/241 = 6 tests) = 11. D1 matches. Valid as authoritative.

**Collapse shape**: Valid cluster — parametrize over (body, secret) input pairs with `hmac.compare_digest` verification assertion. Invalid cluster — parametrize over (body, secret, wrong_signature) tuples with failure assertion. These are two structurally distinct collapse targets (valid vs invalid path) → 2 parametrized functions OR architect-enforcer may propose 1 parametrized function with `expected_result` parameter (assess at plan time per R3 specificity rule).

### §6.3 Reproduce-first protocol

1. **architect-enforcer** re-probes actual cluster; plans (~200 lines at `.sos/wip/hygiene/PLAN-hyg-004-phase2b-2026-04-30.md`): valid vs invalid cluster collapse shape decision; test IDs; SCAR gate; coverage delta verification
2. **janitor** executes: atomic single commit for `test_tier2_adversarial.py` only; tests pass; SCAR ≥47; coverage ≥0
3. **audit-lead** verifies (~200 lines at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-004-phase2b-2026-04-30.md`)

---

## §7 Sub-sprint D Charter — HYG-004 Phase 2C: test_batch_adversarial.py (sequential post-C)

### §7.1 Target cluster

**File**: `tests/unit/test_batch_adversarial.py` (1,104 lines; 94 tests by wc)

**Cluster**: Per HANDOFF AC#3 "upload edge-case cluster (lines 356-438, 12 tests)" and empirical probe:
- `class TestBatchRequestValidationEdgeCases` at line 311 (10 tests at lines 315-430 per probe)
- Probe showed test methods at lines 315, 322, 327, 334, 348, 353, 361, 369, 376, 384 approximately

**D2-pattern**: HANDOFF range "356-438" is a directional anchor — actual class starts at L311. Architect-enforcer re-probes at plan time.

**D1-pattern**: HANDOFF says "12 tests" — empirical probe shows the `TestBatchRequestValidationEdgeCases` class. Exact count determined at architect-enforcer plan time. D1 adjudication follows Phase 1 OPTION A pattern.

**Collapse shape**: Batch request validation tests — tests for path validation (empty, slash-only, very long, special chars, unicode) and method validation (invalid variants, valid variants lowercase/uppercase/mixed), plus payload edge cases. Structurally this is a multi-dimension parametrize target; architect-enforcer must assess whether a clean collapse exists or whether PARAMETRIZE-PARTIAL-CLOSE is more appropriate.

### §7.2 Reproduce-first protocol

1. **architect-enforcer** re-probes actual cluster; plans (~200 lines at `.sos/wip/hygiene/PLAN-hyg-004-phase2c-2026-04-30.md`): collapse shape; parametrize candidates vs retained standalones per R3; SCAR gate; coverage verification
2. **janitor** executes: atomic single commit for `test_batch_adversarial.py` only; tests pass; SCAR ≥47; coverage ≥0
3. **audit-lead** verifies (~200 lines at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-004-phase2c-2026-04-30.md`)

---

## §8 Sub-sprint E Charter — Close PR + HANDOFF Amendment + Session Wrap

### §8.1 PR authoring

PR title: `hygiene(phase2): HYG-002 Phase 2 + HYG-004 Phase 2 discharge [sprint-phase2-2026-04-30]`

Branch: `hygiene/sprint-phase2-2026-04-30`. Base: main@`550ec57a`.

PR body embeds:
- Per-sub-sprint commit-SHA + verdict-artifact-path table
- HANDOFF item discharge state post-Phase-2
- SCAR-47 final count verification
- HYG-002 multi-sprint campaign residual surface (if any deferred sites from Phase 2)
- Cross-rite routing recommendations (paginator drift → /eunomia; any new drift findings from workflow_handler spec'ing)

Pattern mirrors PR #47 (Phase 1) and PR #46 (sre Sprint-2).

### §8.2 HANDOFF amendment

Amend `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` post-Phase-2 close:
- `HYG-001`: `closed` (unchanged; PR #45)
- `HYG-002`: `in_progress` → if Phase 2 exhausts the practical spec'ing surface on workflow_handler, note Phase 3 candidate files; campaign target is 500+ sites (Phase 1 = 47, Phase 2 = TBD from code-smeller scope). Do NOT force to `closed` unless the workflow_handler Phase 2 plus Phase 1 total represents a meaningful campaign milestone agreed with user.
- `HYG-003`: `closed` (unchanged; PR #47)
- `HYG-004`: `closed` — Phase 2 discharges AC#1/2/3 (the 3 remaining adversarial files); Phase 1 discharged AC#4. All 4 ACs satisfied. Mark `closed`.

### §8.3 Session wrap

Predecessor session `session-20260430-131833-8c8691c1` (Phase 1 Sprint, PARKED) is already confirmed PARKED. Phase 2 does not need to re-wrap it; it was wrapped separately per AUDIT log 2026-04-30T13:30:00Z (confirmed in audit log: `wrap_session ... state=PARKED->ARCHIVED`). Phase 2 session `session-20260430-144514-3693fe01` wraps via normal moirai protocol at Sub-sprint E close.

---

## §9 Inviolable Constraints (mirror Phase 1 §8, entrenched)

### §9.1 Pattern-6 drift-audit re-dispatch
Re-run drift-audit at every specialist dispatch.

### §9.2 SCAR cluster preservation (OPERATIONAL post-HYG-001)
- Pre/post each commit: `pytest -m scar --collect-only -q | tail -3` shows ≥47
- Pre/post each commit: `pytest -m scar --tb=short` exits 0
- ANY divergence → halt-on-fail per §9.3

### §9.3 Halt-on-fail discipline
- ANY local test failure pre or post commit → HALT, surface, route
- ANY out-of-scope file modification → HALT, refuse
- ANY drift-audit failure → HALT, re-validate
- ANY mock-spec interface drift NOT filed as separate sub-issue → HALT, refuse silent absorption (Phase 1 §8.6 "taking no prisoners" entrenches this)

### §9.4 Authority boundaries

**In-scope**:
- `tests/unit/lambda_handlers/test_workflow_handler.py` (HYG-002 Phase 2)
- `tests/unit/test_tier1_adversarial.py` (HYG-004 Phase 2A)
- `tests/unit/test_tier2_adversarial.py` (HYG-004 Phase 2B)
- `tests/unit/test_batch_adversarial.py` (HYG-004 Phase 2C)
- `.ledge/decisions/*.md` (ADR per sub-sprint, if NO-LEVER outcome)
- `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` (Sub-sprint E amendment)

**Out-of-scope** (MUST refuse and route):
- Production code (`src/autom8_asana/**`) — route /eunomia or /10x-dev
- CI shape (`.github/workflows/`) — route /sre
- `pyproject.toml` beyond markers section
- `.know/test-coverage.md` — defer to /know rite
- Other `.know/` files (read-only references permitted; no writes)
- SCAR markers on unrelated files — do not touch
- Any test file NOT listed above

### §9.5 Atomic-revertibility per commit
Each sub-sprint commit independently revertible. Q2 ruling (§6.1) enforces this: 3 atomic commits for HYG-004 Phase 2 files.

### §9.6 D1/D2 discipline (carry-forward from Phase 1 §5)
At architect-enforcer plan authoring time for EACH adversarial file sub-sprint:
1. Re-probe `grep -nE "^    def test_" <file>` to get exact test count within target cluster
2. Re-probe actual class boundary lines via `grep -n "class Test"` to confirm HANDOFF line ranges
3. If D1 (count mismatch) or D2 (line range mismatch) found: document in plan §2 and apply OPTION A (empirical authoritative) per Phase 1 §5 precedent
4. Do NOT defer D1/D2 adjudication to audit time — flag at plan authoring so janitor has correct scope

---

## §10 Verdict-Discharge Contract (Phase 2 close-gate)

### §10.1 Per-sub-sprint discharge (mirror Phase 1 §9.1)

After EACH sub-sprint:
- janitor commit lands on branch `hygiene/sprint-phase2-2026-04-30`
- audit-lead verdict at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-NNN-{phase}-2026-04-30.md` (~200 lines)
- SCAR ≥47 preserved
- Per-AC ledger (PASS/FAIL/DEFER with file:line evidence)

### §10.2 Phase 2 close-gate

Sub-sprint E opens PR; embeds:
- Per-sub-sprint commit-SHA + verdict-artifact-path table
- HANDOFF final item discharge state
- SCAR count at sprint close (expect ≥47)
- Paginator-drift carry-forward note for /eunomia (from Phase 1 AUDIT §8.2 + potential Phase 2 re-surface in workflow_handler)
- Multi-sprint residual surface for HYG-002 Phase 3 (if applicable)

### §10.3 Without close PR + HANDOFF amendment: Phase 2 engagement FAILS
Phase 2 does NOT close cleanly without (i) close PR landing on main, (ii) HANDOFF amendment per §8.2 marking HYG-004 as `closed`, (iii) Phase 2 session wrap via moirai.

---

## §11 Open Verification-Phase Risks

### §11.1 workflow_handler spec= cascade (MEDIUM)

`test_workflow_handler.py` has 273 total mocks across 1,403 lines and 8 test classes (TestCreateWorkflowHandler, TestHandlerEnumerateExecuteOrchestration, TestHandlerWorkflowRegistration, TestBridgeEventEmission, TestFleetObservability, TestSPOF1Detection, TestSPOF1FalsePositive, TestSPOF1Recovery). Spec'ing root mocks may cascade across orchestration chains.

**Mitigation**: Phase 2 scope is NOT "all 273 mocks" — code-smeller determines specifiable envelope per §4.2. PHASE-2-CLOSE-WITH-DRIFT-FINDINGS is an anticipated outcome (per Phase 1 AC 5 pattern).

### §11.2 `--dist=loadfile` requirement (LOW)

`.know/test-coverage.md` explicitly notes `test_workflow_handler.py` requires `--dist=loadfile` for process-global state isolation. janitor must run verification with `-n auto --dist=loadfile` to match CI behavior, NOT with `-n 0` (serial).

**Mitigation**: Architect-enforcer plan §9.4 must note this; janitor must use `pytest tests/unit/lambda_handlers/test_workflow_handler.py -n auto --dist=loadfile --tb=short` for verification. SCAR gate runs full suite but file-level confirmation uses loadfile mode.

### §11.3 D1/D2 at adversarial files (MEDIUM, EXPECTED)

Phase 1 §10 forward routing explicitly stated: "D1/D2 pattern likely recurs at the other 3 files." Phase 2 probe confirms:
- tier1: HANDOFF says 14 tests; empirical probe shows 8 in `TestModelRequiredFields` (D1 expected)
- tier2: HANDOFF says 11 tests; empirical probe shows 11 (5+6) — D1 MAY match; D2 is positional
- batch: HANDOFF says 12 tests; class starts at L311 not L356 (D2 confirmed); count TBD

**Mitigation**: §9.6 D1/D2 discipline mandates re-probe at architect-enforcer plan time for each file.

### §11.4 tier1 adversarial cluster size (MEDIUM)

HANDOFF says 14 tests; empirical probe shows 8 `def test_*` in `TestModelRequiredFields`. If the HANDOFF count included tests in adjacent classes, the architect-enforcer must decide scope boundary at plan time.

**Mitigation**: §9.6 re-probe; OPTION A adjudication (empirical authoritative).

### §11.5 SCAR collection regression (LOW)

HYG-004 Phase 2 modifies parametrize structure without touching SCAR decorators; risk is very low. Phase 1 precedent: SCAR count unchanged across all Phase 1 mutations.

**Mitigation**: §9.2 pre/post-commit gate per sub-sprint.

### §11.6 Coverage delta on adversarial files (LOW)

Parametrize collapse retains runtime-case count (phase 1 precedent: 27 source tests → 27 runtime cases). Coverage delta should be 0. Risk: architect-enforcer must verify plan doesn't inadvertently reduce branch coverage via collapse shape choice.

**Mitigation**: coverage report check in janitor verification step per §9.1.

---

## §12 Cross-Rite Routing at Phase 2 Close

| Target rite | Items | Rationale |
|---|---|---|
| **/hygiene** (future Phase 3) | HYG-002 Phase 3 (remaining unspec'd sites from Phase 2 deferred clusters + next high-density files) | Multi-sprint campaign continues; ~50+ sites likely deferred from Phase 2 |
| **/eunomia** | Paginator protocol gap (Phase 1 AUDIT §8.2 carry-forward + potential Phase 2 workflow_handler surface) | `PaginatorProtocol` absent from `src/autom8_asana/protocols/`; production-side fix |
| **/sre** | SRE-005 (M-16 Dockerfile) | Already-deferred at sre Sprint-2 close |
| **/10x-dev** | Only if HYG-002 Phase 2 workflow_handler spec'ing surfaces production-side schema unification need | Route as new HANDOFF if fires |

---

## §13 Source Manifest

| Role | Artifact | Absolute Path |
|---|---|---|
| HANDOFF (governing) | eunomia → /hygiene | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` |
| Phase 1 charter (direct predecessor) | INHERIT pattern | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/hygiene/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint.md` |
| Phase 1 HYG-002 verdict | Phase 2 substrate | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/hygiene/AUDIT-VERDICT-hyg-002-phase1-2026-04-30.md` |
| Phase 1 HYG-004 verdict | D1/D2 discipline source | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/hygiene/AUDIT-VERDICT-hyg-004-phase1-2026-04-30.md` |
| Test coverage knowledge | Mock-density data | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/test-coverage.md` |
| HYG-002 Phase 2 target | Q1a locked | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/lambda_handlers/test_workflow_handler.py` |
| HYG-004 Phase 2A target | HANDOFF AC#1 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/test_tier1_adversarial.py` |
| HYG-004 Phase 2B target | HANDOFF AC#2 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/test_tier2_adversarial.py` |
| HYG-004 Phase 2C target | HANDOFF AC#3 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/test_batch_adversarial.py` |
| Phase 2 session | governing session | `session-20260430-144514-3693fe01` |
| Phase 2 sprint | governing sprint | `sprint-20260430-phase2-hyg2-hyg4` |
| Branch | Phase 2 working branch | `hygiene/sprint-phase2-2026-04-30` (from main@`550ec57a`) |
| THIS artifact (governing Phase 2 charter) | inaugural Phase 2 consult | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/hygiene/PYTHIA-INAUGURAL-CONSULT-2026-04-30-phase2.md` |

---

*Authored 2026-04-30 by Pythia consultation + main-thread materialization. MODERATE evidence-grade per `self-ref-evidence-grade-rule`. All Phase 1 inviolable constraints inherited verbatim. Q1 adjudicated: `tests/unit/lambda_handlers/test_workflow_handler.py` (empirically confirmed 87 unspec'd mocks; SCAR-026 critical-path rationale; `--dist=loadfile` constraint noted). Q2 adjudicated: 3 atomic commits (one per adversarial file; independent-revertibility rationale per §6.1). Q3 adjudicated: 5 sub-sprints (A=HYG-002P2, B=tier1, C=tier2, D=batch, E=close; serial default). D1/D2 discipline codified at §9.6 — architect-enforcer MUST re-probe at plan authoring time for each adversarial file. HANDOFF path-correction noted (§4.1): hydration/workspace_registry files are in `tests/unit/models/business/` not `tests/unit/lifecycle/` or `tests/unit/cache/` — empirical paths are authoritative. HYG-004 Phase 2 close will mark HANDOFF HYG-004 as `closed`; HYG-002 remains `in_progress` (multi-sprint campaign). Phase transition recommendation: PLAN → SUB-SPRINT-A (first action: code-smeller scopes `test_workflow_handler.py` mock surface; produces SCOPE artifact; architect-enforcer plans within scope envelope; janitor executes; audit-lead verifies).*
