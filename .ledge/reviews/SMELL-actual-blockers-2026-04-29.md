---
artifact_id: SMELL-actual-blockers-2026-04-29
schema_version: "1.0"
type: review
artifact_type: smell-report
slug: actual-blockers-2026-04-29
rite: hygiene
phase: 1-assessment
initiative: "Principled Actual-Blocker Remediation"
date: 2026-04-29
status: proposed
created_by: code-smeller
evidence_grade: MODERATE
self_grade_ceiling_rationale: "self-ref-evidence-grade-rule — code-smeller authoring within hygiene rite caps at MODERATE; STRONG would require cross-rite re-audit"
upstream_handoff: HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md
case_substrate: .ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md
verdict_substrate: .ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md
authority_boundary:
  may_recommend_disposition: false
  may_author_clause_text: false
  authority_for_disposition: architect-enforcer (Phase 2)
items_diagnosed:
  - HYG-001
  - HYG-002
out_of_scope_observations_count: 2
---

# SMELL — Actual-Blocker Diagnostic Report (2026-04-29)

## §0 Telos and Posture

This is a Phase-1 assessment artifact: per-item ROOT-CAUSE diagnosis of the 2 pre-named blockers in `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md` (L19-L84). The smeller does NOT discover smells; it does NOT recommend dispositions; it does NOT author clause text. Disposition (FIX/DELETE/ACCEPT) is architect-enforcer's authority in Phase 2; clause-text authoring for HYG-002 is architect-enforcer's authority in Phase 2. F-HYG-CF-A receipt-grammar applied throughout: every claim carries a `{path}:{line_int}` anchor or workflow-run URL within the same paragraph.

---

## §1 HYG-001 — Three Stale CI Gates (per-gate diagnosis)

The 3 named gates are jobs in the SHA-pinned reusable workflow `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd8d9bba883e6a42628bdc2bba6d30512b`, called by `autom8y-asana/.github/workflows/test.yml:45` (`uses:` line) with `autom8y_workflows_sha: c88caabd8d9bba883e6a42628bdc2bba6d30512b` at `test.yml:71`. Each gate name surfaces in PR checks as `ci / <Gate Name>`. All 3 gates share invariance under docs-only changes (PR #40 was docs-only and all 3 still failed) — see §1.4.

### §1.1 Gate A — Lint & Type Check

**Workflow definition**: `autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd:221-366` at SHA `c88caabd8d9bba883e6a42628bdc2bba6d30512b` (job key `lint-typecheck`, name on line `:221` `name: Lint & Type Check`). The job declares 11 steps including the failing `Check formatting` step at line `:319` (`uv run --no-sources ruff format . --check`) and `Run linting` at `:322`.

**Most-recent failing workflow-run URLs (cross-stream concurrence — both PR commits cited per F-HYG-CF-A)**:
- PR #40 (commit `848525b9`): https://github.com/autom8y/autom8y-asana/actions/runs/25107487624/job/73572352438 — `ci / Lint & Type Check` state FAILURE per `gh pr checks 40` JSON output captured 2026-04-29.
- PR #39 (commit `45a9e875`): https://github.com/autom8y/autom8y-asana/actions/runs/25085690587/job/73500659548 — `ci / Lint & Type Check` state FAILURE per `gh pr checks 39` JSON output captured 2026-04-29.

**Failure mechanism (log excerpt anchor — verbatim from PR #40 run)**:
> Step name: `Check formatting` (run-log step at workflow timestamp `2026-04-29T11:58:35.3021689Z`, anchored to satellite-ci-reusable.yml:319)
>
> Output (verbatim):
> ```
> Would reformat: src/autom8_asana/api/routes/_exports_helpers.py
> Would reformat: src/autom8_asana/api/routes/exports.py
> Would reformat: src/autom8_asana/models/business/detection/facade.py
> Would reformat: tests/unit/api/test_exports_format_negotiation.py
> Would reformat: tests/unit/api/test_exports_handler.py
> Would reformat: tests/unit/api/test_exports_helpers_walk_predicate_property.py
> Would reformat: tests/unit/services/test_discovery.py
> 7 files would be reformatted, 1050 files already formatted
> ##[error]Process completed with exit code 1.
> ```

**Root-cause classification**: **code-fixable** — the failure is `ruff format --check` exit code 1 against 7 specific source files in `src/autom8_asana/` and `tests/unit/`. It is NOT a stale baseline, NOT a tooling-version-skew, NOT a missing-config; the workflow step is operating exactly as designed and is correctly surfacing 7 unformatted files. Classification: **invariant-violation** (formatting convention violated in repo HEAD).

**Invariance evidence**: PR #40 was docs-heavy (changes mostly under `.ledge/`, `.knossos/`, `.know/`); the 7 unformatted files predate the PR. The gate fails identically on PR #39 commit `45a9e875` (job 73500659548 FAILURE) — the invariance signal is robust across a 2-PR window.

**Fixability signal**: **code-fixable** at the satellite-altitude (autom8y-asana repo HEAD). Running `uv run ruff format src/autom8_asana/api/routes/_exports_helpers.py src/autom8_asana/api/routes/exports.py src/autom8_asana/models/business/detection/facade.py tests/unit/api/test_exports_format_negotiation.py tests/unit/api/test_exports_handler.py tests/unit/api/test_exports_helpers_walk_predicate_property.py tests/unit/services/test_discovery.py` against the listed files and committing the result clears the gate; no reusable-workflow change required, no baseline refresh required.

---

### §1.2 Gate B — Semantic Score Gate

**Workflow definition**: `autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd:932-1010` at SHA `c88caabd8d9bba883e6a42628bdc2bba6d30512b` (job key `semantic-score`, name on line `:933` `name: Semantic Score Gate`). The job fetches the canonical `score_spec.py` from `autom8y/a8` repo (`:953-963`) and runs the gate at line `:970-984` invoking `python .tools-checkout/tools/semantic-score/score_spec.py <openapi-spec> --baseline <baseline>` with regression-gate logic at `:1006-1009` (`if regression_safe == "False" -> BLOCKED`).

**Most-recent failing workflow-run URLs**:
- PR #40 (commit `848525b9`): https://github.com/autom8y/autom8y-asana/actions/runs/25107487624/job/73572352423 — `ci / Semantic Score Gate` state FAILURE.
- PR #39 (commit `45a9e875`): https://github.com/autom8y/autom8y-asana/actions/runs/25085690587/job/73500659558 — `ci / Semantic Score Gate` state FAILURE.

**Failure mechanism (log excerpt anchor — verbatim from PR #40 run)**:
> Step name: `Run semantic score gate` (id `score`, anchored to satellite-ci-reusable.yml:970)
>
> Score-result.json output (verbatim slices captured at workflow timestamp `2026-04-29T11:58:18.43...`):
> ```
> "regression_safe": false,
> "regressions": [
>     {
>       "metric": "M-05_type_strictness",
>       ...
>       "delta": -0.0046
>     }
> ],
> "composite_delta": 0.0081
> ```
>
> Floor-violations indicator: `"M-07_constraint_coverage"` appears in the floor-violations list per the `floor_violations` key parsed at `:983` (`VIOLATIONS=$(python -c "import json; d=json.load(open('/tmp/score-result.json')); print(', '.join(d.get('floor_violations', [])) or 'none')")`).

**Root-cause classification**: **stale-baseline** primarily, with co-occurring **invariant-violation** at the M-05 regression delta. The handoff at `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md:34-37` names both signals: "M-07 constraint coverage floor + M-05 type strictness regression of -0.0046, invariant under docs-only changes". The M-07 signal is a floor-violation (the absolute coverage of constraint-typed fields in the openapi.json is below the configured floor); the M-05 signal is a delta-regression (strictness has decreased 0.0046 vs the baseline). Whether the baseline at `inputs.semantic_score_baseline` reflects current intent or is stale is an architect-enforcer Phase-2 question.

**Invariance evidence**: PR #40 had no changes to `docs/api-reference/openapi.json` (the file the gate reads at workflow input `openapi_spec_path`, configured at `test.yml:60`). The gate failed identically on PR #39 (job 73500659558) — both regression and floor signal are present without any code or spec mutation, confirming the gate is firing on pre-existing repo HEAD state, not on PR-introduced delta.

**Fixability signal**: **mixed — three plausible avenues, each at a different altitude**:
1. **Baseline-refreshable**: regenerate baseline at `inputs.semantic_score_baseline` if the current openapi.json reflects current intent and the baseline is stale.
2. **Code-fixable**: tighten openapi.json field types (raise M-05 type-strictness back above prior baseline) and add constraints to push M-07 above floor.
3. **Config-fixable**: lower the M-07 floor in the gate config if the floor was set aspirationally.

Disposition selection across (1)/(2)/(3) is architect-enforcer's authority (Phase 2 option-enumeration-discipline applies).

---

### §1.3 Gate C — Spectral Fleet Validation

**Workflow definition**: `autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd:824-870` at SHA `c88caabd8d9bba883e6a42628bdc2bba6d30512b` (job key `spectral-validation`, name on line `:825` `name: Spectral Fleet Validation`). The job fetches the canonical fleet ruleset `spectral-fleet.yaml` from `autom8y/autom8y-api-schemas` repo (`:847-859`) and lints with `spectral lint <openapi> --ruleset .fleet-schemas/spectral-fleet.yaml --fail-severity=error` at line `:869`.

**Most-recent failing workflow-run URLs**:
- PR #40 (commit `848525b9`): https://github.com/autom8y/autom8y-asana/actions/runs/25107487624/job/73572352495 — `ci / Spectral Fleet Validation` state FAILURE.
- PR #39 (commit `45a9e875`): https://github.com/autom8y/autom8y-asana/actions/runs/25085690587/job/73500659552 — `ci / Spectral Fleet Validation` state FAILURE.

**Failure mechanism (log excerpt anchor — verbatim from PR #40 run)**:
> Step name: `Lint OpenAPI spec` (anchored to satellite-ci-reusable.yml:862)
>
> Output (verbatim, run-log timestamp `2026-04-29T11:58:31.7600...`):
> ```
> /home/runner/work/autom8y-asana/autom8y-asana/docs/api-reference/openapi.json
>  3736:26    error  fleet-envelope-consistency   Response schema at #/paths/~1api~1v1~1exports/post/responses/200/content/application~1json/schema does not follow the {data, meta} envelope pattern.
>  8356:26    error  fleet-envelope-consistency   Response schema at #/paths/~1v1~1exports/post/responses/200/content/application~1json/schema does not follow the {data, meta} envelope pattern.
> ✖ 6 problems (2 errors, 4 warnings, 0 infos, 0 hints)
> ##[error]Process completed with exit code 1.
> ```

**Root-cause classification**: **invariant-violation** (the `/api/v1/exports.post` and `/v1/exports.post` response schemas in `docs/api-reference/openapi.json` do not conform to the fleet's `{data, meta}` envelope pattern enforced by the `fleet-envelope-consistency` rule in the cross-repo `spectral-fleet.yaml` ruleset). NOT a stale baseline (the ruleset is fetched fresh from `autom8y/autom8y-api-schemas` main per `:851`); NOT a tooling-version-skew (Spectral CLI pinned to `6.15.0` at `:861`); NOT a missing-config (`--fail-severity=error` is intentional). The local openapi.json carries 2 actual fleet-rule violations.

**Invariance evidence**: PR #40 had no changes to `docs/api-reference/openapi.json` (verified by spectral lint output reading the file at workflow checkout). The same 2 errors recur on PR #39 (job 73500659552 FAILURE). The errors anchor to specific JSON-pointer paths at `openapi.json:3736:26` and `openapi.json:8356:26` — these are pre-existing schema violations in the satellite repo's main-branch OpenAPI document.

**Fixability signal**: **code-fixable** at the satellite-altitude — modifying `docs/api-reference/openapi.json` at lines `3736` and `8356` to wrap the `200` response schemas in the canonical `{data, meta}` envelope structure clears both errors. The 4 warnings (oas3-unused-component at `1925:25`, info-contact at `3066:10`, path-keys-no-trailing-slash at `7859:26`, operation-tag-defined at `8424:11`) are non-blocking under `--fail-severity=error` and not part of the failure mechanism.

---

### §1.4 Cross-stream concurrence (F-HYG-CF-A invariance evidence)

| Gate | PR #39 (commit `45a9e875`) | PR #40 (commit `848525b9`) | Invariance under docs-only |
|------|---|---|---|
| Lint & Type Check | FAILURE — job 73500659548 | FAILURE — job 73572352438 | Confirmed: same step (`Check formatting` ruff) fails on both; PR #40 docs-heavy. |
| Semantic Score Gate | FAILURE — job 73500659558 | FAILURE — job 73572352423 | Confirmed: same M-05 regression + M-07 floor on both; openapi.json unchanged across PRs. |
| Spectral Fleet Validation | FAILURE — job 73500659552 | FAILURE — job 73572352495 | Confirmed: same 2 fleet-envelope-consistency errors on both; openapi.json unchanged across PRs. |

PR-checks data captured 2026-04-29 via `gh pr checks 39` and `gh pr checks 40` JSON output. Each failure persists across at least 2 distinct PR head commits with no relevant content delta — the gates are firing on repo HEAD state, NOT on PR-introduced changes.

---

## §2 HYG-002 — drift-audit-discipline Skill Location + Pattern 6 Evidence Trail

### §2.1 Skill location: NOT-FOUND (with search trace)

The `drift-audit-discipline` skill referenced in `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md:55` (acceptance criterion: *"drift-audit-discipline skill (locate via grep; likely at $KNOSSOS_HOME/skills/ or .claude/skills/)"*) and in `VERDICT-eunomia-final-adjudication-2026-04-29.md:135` (recommendation: *"Codify at `drift-audit-discipline` skill as a synthesis-altitude clause"*) **does NOT exist as a file or directory at any of the searched skill paths**.

**Search trace (exhaustive, executed 2026-04-29)**:

| Path searched | Command | Result |
|---|---|---|
| Repo-local skills | `find /Users/tomtenuta/Code/a8/repos/autom8y-asana/.claude/skills -type d -name "drift-audit*"` | empty (no match) |
| Knossos shared-mena | `find /Users/tomtenuta/Code/knossos -type d -name "drift-audit*"` | empty (no match) |
| Knossos shared-mena (file-scope) | `find /Users/tomtenuta/Code/knossos -type f -name "*drift-audit*"` | empty (no match) |
| a8 ecosystem | `find /Users/tomtenuta/Code/a8 -type d -name "drift-audit*"` | empty (no match) |
| Filesystem-wide | `find / -type d -name "drift-audit*"` | empty (no match) |
| Knossos content grep | `grep -rln "drift-audit-discipline" /Users/tomtenuta/Code/knossos` | empty (no match) |
| a8 content grep | `grep -rln "drift-audit-discipline\|drift-audit" /Users/tomtenuta/Code/a8` | matched only autom8y-asana review/handoff/scar artifacts (5 files; all reference, none define) |
| Knossos shared-mena dir listing | `ls /Users/tomtenuta/Code/knossos/rites/shared/mena/ \| grep -i drift` | empty (no match) |
| `$KNOSSOS_HOME` env var | `echo "$KNOSSOS_HOME"` | unset / empty in this session |

The 5 `a8` matches all reside in `autom8y-asana/.know/scar-tissue.md`, `autom8y-asana/.ledge/handoffs/HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md`, `autom8y-asana/.ledge/handoffs/HANDOFF-review-to-eunomia-final-adjudication-carry-forward-triage-2026-04-29.md`, `autom8y-asana/.ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md`, and `autom8y-asana/.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md`. All 5 *reference* the skill by name as a future codification target; none *define* the skill body.

### §2.2 Classification

**not-found** (with cross-repo implications). The eunomia VERDICT recommendation at `VERDICT-eunomia-final-adjudication-2026-04-29.md:135` and the SCAR-P6-001 entry at `.know/scar-tissue.md:228-231` both refer to `drift-audit-discipline` as if it were an existing artifact awaiting amendment with a synthesis-altitude clause; the actual skill body has not been minted at any altitude.

**Implications surfaced for architect-enforcer Phase 2 (not decisions — surfaced only)**:

1. The handoff at `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md:80-84` flags that "*if the drift-audit-discipline skill is at $KNOSSOS_HOME (outside this repo), this may need to escalate via satellite-primitive-promotion protocol*". Since the skill does not exist anywhere, the actual condition is **MINT-NOT-PROMOTE**: the skill body has to be authored from scratch (not promoted across repos). Whether the mint occurs at repo-local (`autom8y-asana/.claude/skills/drift-audit-discipline/`) or knossos shared-mena (`/Users/tomtenuta/Code/knossos/rites/shared/mena/drift-audit-discipline/`) altitude is an architect-enforcer disposition decision — `satellite-primitive-promotion` skill at `autom8y-asana/.claude/skills/satellite-primitive-promotion/` is the relevant procedural reference if knossos altitude is selected.
2. The handoff acceptance criterion at L55 reads "drift-audit-discipline skill (locate via grep…) **updated** with synthesis-altitude clause"; the empirical condition is "**created** with synthesis-altitude clause as the inaugural body". This is a framing delta architect-enforcer should disambiguate before janitor execution.

### §2.3 Originating evidence cited (file:line anchors)

The synthesis-altitude clause's evidentiary chain (per F-HYG-CF-A — 3-channel cross-stream concurrence):

| Channel | Anchor | What it establishes |
|---|---|---|
| VERDICT — institutional codification | `VERDICT-eunomia-final-adjudication-2026-04-29.md:101-143` (§5 Pattern-6 Recurrence Meta-Finding); recommendation L135-L137 names the clause text | Pattern 6 RECURS at PLAN-AUTHORING altitude; codification target identified |
| CASE — origin codification | `CASE-comprehensive-cleanliness-2026-04-29.md:296-300` (Pattern 6 SCAN-altitude framing); §8 Q-1 at `CASE:407-410` (initial promotion track to /go dashboard) | Pattern 6 first-codified at SCAN altitude as Meta-Observation; Q-1 names the originating recommendation track |
| SCAR — durable scar | `.know/scar-tissue.md:201-238` (SCAR-P6-001 body); cross-references at `:71` (table row) and `:481` (agent-relevance row) | Pattern recurrence promoted to durable scar; defensive discipline at L228-L231 names the synthesis-altitude clause text verbatim |

The verbatim clause text named in the originating evidence chain (cited only — code-smeller does NOT author):

> "Re-run drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated."
> — `VERDICT-eunomia-final-adjudication-2026-04-29.md:136-137` (cite-only)
> — `.know/scar-tissue.md:230-231` (cite-only)

The HANDOFF at `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md:56` carries an expanded form of the same clause: *"re-run drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated. Specifically: any plan-authoring step that consumes [UNATTESTED] inventory framing MUST verify ground truth against origin/main before propagating the framing forward."* — surfaced for architect-enforcer Phase 2 reconciliation between the two clause forms.

### §2.4 test_source_stub.py ground-truth re-confirmation (cross-stream verification per F-HYG-CF-A)

Per HANDOFF acceptance criterion at L65 (*"test_source_stub.py ground-truth: blob bf4f74180e15f07a698538afa14f6f82d47bf641 PR #174 commit f2dfc1c3"*) — **CONFIRMED via runtime probe**:

> Command: `cd /Users/tomtenuta/Code/a8/repos/autom8y && git ls-tree origin/main tools/lockfile-propagator/tests/test_source_stub.py`
> Output (verbatim, captured 2026-04-29):
> ```
> 100644 blob bf4f74180e15f07a698538afa14f6f82d47bf641	tools/lockfile-propagator/tests/test_source_stub.py
> ```
> Exit code: 0

Cross-stream concurrence (3 independent channels):
- **VERDICT §3 substantiation channel 2** at `VERDICT-eunomia-final-adjudication-2026-04-29.md:65-71` cites the same blob `bf4f74180e15f07a698538afa14f6f82d47bf641` at autom8y origin/main per PR #174 merge commit `f2dfc1c3`.
- **SCAR-P6-001 ground-truth row** at `.know/scar-tissue.md:222-226` cites the same blob and merge commit.
- **Live runtime probe** above (this artifact) re-verifies the blob at audit time.

The PLAN-consolidation §3 L101 + §9 L230 inverted-drift framing (file "absent on origin/main") is empirically falsified by all three channels.

### §2.5 Insertion-site identification (where the synthesis-altitude clause should land)

Since the skill does not exist, there is no extant section heading to amend. Code-smeller surfaces the structural-location signal only — the precise insertion site within a to-be-authored skill body is architect-enforcer Phase 2 authority and depends on the disposition decision in §2.2.

**Structural signal for architect-enforcer (recommendation NOT made; siting candidates surfaced only)**:

The synthesis-altitude clause is a *behavioral rule* (when-to-re-run-drift-audit), so the natural homing location within a typical knossos-shape skill body is:

| Candidate section | Rationale | Reference precedent (sibling skill structure) |
|---|---|---|
| `§2 HOW — Mechanics` of an authored `SKILL.md` | Behavioral rules typically reside in HOW (mechanical operations on triggering conditions). | Cf. `structural-verification-receipt/SKILL.md:§2` ("Four mechanical operations on every platform-behavior claim") — same rule-shape structure. |
| `§1 WHEN — Invocation Conditions` | The clause is triggered by a condition ("any altitude where mixed-resolution upstream substrates are being consolidated") — invocation-condition altitude. | Cf. `telos-integrity-ref §1` invocation triggers; `live-runtime-contradiction-triage §1` trigger conditions. |
| New `§N` synthesis-altitude section, after WHEN/HOW | If the skill needs both an inception-altitude rule (existing scan-altitude discipline) AND a synthesis-altitude rule (the new clause), a dedicated section preserves the altitude distinction. | Cf. `telos-integrity-ref §3` Three Gate-Points structure — gates at distinct lifecycle-altitudes get dedicated subsections. |

Architect-enforcer Phase 2 selects (a) the disposition (mint at repo-local vs. knossos shared-mena), (b) the section heading where the clause lands, and (c) the verbatim clause text (reconciling the two extant forms in the originating evidence chain).

---

## §3 Authority-Boundary Compliance

| Boundary | Compliance | Anchor |
|---|---|---|
| MAY NOT recommend disposition (FIX/DELETE/ACCEPT) | Compliant — all 3 gates' disposition deferred to architect-enforcer Phase 2; only fixability *signals* surfaced (§1.1, §1.2, §1.3). | task spec: "DO NOT recommend a disposition — that is architect-enforcer's authority in Phase 2" |
| MAY NOT author synthesis-altitude clause text | Compliant — clause text cited verbatim from VERDICT and SCAR; no authoring; reconciliation between two clause forms surfaced as a Phase-2 question (§2.3). | task spec: "DO NOT author the clause text — that is architect-enforcer's authority in Phase 2" |
| MAY NOT modify any file in this phase | Compliant — assessment is read-only; only this deliverable file written. | task spec: "MAY NOT: Modify any file in this phase (assessment is read-only)" |
| Receipt-grammar: every claim carries `{path}:{line_int}` or workflow-run URL anchor in same paragraph | Compliant — per-gate diagnoses (§1.1-§1.3) anchor each finding to satellite-ci-reusable.yml line range + run URL; HYG-002 anchors all clause-cite claims to file:line; ground-truth probe carries verbatim command output. | F-HYG-CF-A canonical at `RETROSPECTIVE-VD3-2026-04-18.md:145` (precedent inheritance) |
| No "wave-level" or "all 3 gates" tokens without per-item backing | Compliant — `§1.4 cross-stream concurrence table` provides per-gate file:line + run-URL receipts; §1 opening paragraph names "all 3 gates share invariance" but the supporting backing follows in per-gate sub-sections. | F-HYG-CF-A precedent at task spec |

---

## §4 Out-of-scope observations (quarantined per scope-guard)

Two observations surfaced during diagnosis that do NOT meet the "actual blocker" bar and are explicitly NOT integrated into the §1/§2 diagnoses. Surfaced here per task spec ("If you encounter other smells/issues during diagnosis, DO NOT absorb them. Surface them in a `## Out-of-scope observations` section at report tail for Potnia to relay to user").

### §4.1 OOS-1 — Node.js 20 deprecation warnings on all 3 failing job runs

All 3 failing jobs in PR #40 run 25107487624 emit identical deprecation warnings (verbatim slice):

> `##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5, actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065, astral-sh/setup-uv@38f3f104447c67c051c4a08e39b64a148898af3a, aws-actions/configure-aws-credentials@7474bc4690e29a8392af63c5b98e7449536d5c3a. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026.`

This is a fleet-altitude tooling-version-skew signal (the actions used by the satellite-ci-reusable.yml are pinned at SHA but those SHAs reference Node.js 20 runtime, deprecated 2026-06-02). NOT a blocker today; NOT among the 3 named gates; relevant to a future fleet-tooling-refresh engagement, not to actual-blocker remediation.

**Relay channel**: surface to user via Potnia for routing consideration to `/sre` or fleet-altitude tooling refresh; NOT absorbed into HYG-001.

### §4.2 OOS-2 — 4 Spectral warnings (non-blocking) co-located with the 2 errors

The Spectral Fleet Validation job emits 4 warnings alongside the 2 errors that drive the gate failure (verbatim from PR #40 log):

- `1925:25  warning  oas3-unused-component        Potentially unused component has been detected.   components.schemas.SuccessResponse`
- `3066:10  warning  info-contact                 Info object must have "contact" object.            info`
- `7859:26  warning  path-keys-no-trailing-slash  Path must not end with slash.                       paths./api/v1/workflows/`
- `8424:11  warning  operation-tag-defined        Operation tags must be defined in global tags.     paths./v1/exports.post.tags[0]`

Under `--fail-severity=error` (satellite-ci-reusable.yml:869), these warnings do NOT cause the gate to fail; they are signal-only. They are observable openapi.json hygiene gaps (unused component, missing contact, trailing slash, undeclared tag) that are NOT blockers per the cleanup HANDOFF's "actual blockers only" framing.

**Relay channel**: surface to user via Potnia for routing consideration to a future hygiene engagement at openapi.json altitude; NOT absorbed into HYG-001 Spectral diagnosis (which is scoped to the 2 *errors* that fail the gate).

---

## §5 Source Manifest

| Role | Artifact | Absolute path |
|---|---|---|
| Primary handoff | cleanup → hygiene | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md` |
| Upstream authority (cite-only) | eunomia VERDICT | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md` |
| Upstream authority (cite-only) | review CASE | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md` |
| Scar cross-reference | SCAR-P6-001 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/scar-tissue.md` (entry at L201-L238) |
| Satellite caller workflow | test.yml `ci` reusable invocation | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml` (L40-L72) |
| Reusable workflow definition (SHA-pinned) | autom8y-workflows@c88caabd | `/Users/tomtenuta/Code/a8/repos/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml` at SHA `c88caabd8d9bba883e6a42628bdc2bba6d30512b` (current local HEAD `55402d7` is divergent — line numbers in §1 cite the SHA-pinned content via `git show`) |
| Ground-truth probe target | autom8y origin/main | `/Users/tomtenuta/Code/a8/repos/autom8y` (probed via `git ls-tree origin/main tools/lockfile-propagator/tests/test_source_stub.py`; blob `bf4f74180e15f07a698538afa14f6f82d47bf641`) |
| THIS artifact | SMELL-actual-blockers | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SMELL-actual-blockers-2026-04-29.md` |

---

*Authored by code-smeller 2026-04-29 under hygiene rite Phase 1 (assessment) for the "Principled Actual-Blocker Remediation" initiative. MODERATE evidence-grade per `self-ref-evidence-grade-rule` (hygiene-rite specialist authoring within own rite). F-HYG-CF-A receipt-grammar applied throughout: every per-gate finding carries satellite-ci-reusable.yml line range + workflow-run URL anchor; HYG-002 carries 3-channel cross-stream concurrence (VERDICT + CASE + SCAR + live runtime probe). Authority boundaries observed: no disposition recommendations; no clause-text authoring; no file modifications outside this deliverable. 2 out-of-scope observations quarantined in §4 for Potnia user-relay. Phase-2 handoff to architect-enforcer ready.*
