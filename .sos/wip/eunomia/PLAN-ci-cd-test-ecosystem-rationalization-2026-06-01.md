---
artifact_id: PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01
schema_version: "1.0"
type: plan
altitude: OPERATIONAL
status: active
---

# PLAN — CI/CD + Test Ecosystem Rationalization (Bounded Back-Route)

## Inheritance
- PT-α verdict applied: ASSESS-1 root = branch-protection-required-check-gap (not CI asymmetry)
- Operator-ratified policies: B3 (10x rearchitect mandate), B8 (per-endpoint xfail now)
- Frozen-set inherited per workflow FROZEN block

## Batch summary

| Batch | Status | Changes | Risk | Entropy delta |
|-------|--------|---------|------|---------------|
| **B0** | ready (added 2026-06-01 post-halt) | 2 | low | Unblocks B1/B2 actionlint gate. Eliminates 3 pre-existing shellcheck baseline warnings (SC2086 x6, SC2155 x2, SC2129 x1) at test.yml L122-127, L237-242, L291-305. Per operator-ratified Option-B (no-shortcuts root-fix mandate) following halt at B1 CHANGE-001. |
| **B1** | ready | 1 | medium | Eliminates 1 cross-repo artifact-name contract mismatch (B1 finding). Fuzz job artifact-not-found failure rate on consumer-gate dispatches: expected 100% -> 0%. CI minutes reclaimed: ~15min per fuzz job currently failing at download step (fuzz timeout-minutes=15 at test.yml:89). HANDOFF artifact (HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md:82) documents this as the canonical B1 symptom; this CHANGE resolves the underlying contract mismatch at source. Aegis-baseline drift: 1 known-broken cross-workflow dependency resolved. |
| **B2** | ready | 5 | low | Action-version-skew entropy reduced from 2 distinct setup-uv SHAs across 5 inline-job touchpoints (v4 38f3f104 ×3 + v6 6b9c6063 ×2) to 1 unified SHA aligned with fleet canonical (v8.1.0 08807647 ×5) — eliminates ASSESS-4 IN-REPO floating-deps signal for setup-uv per pipeline-inventory L467 row. Structural-invariant entropy: autom8y_workflows_sha input → @ref drift collapsed from 7-commit skew to 0-commit skew, restoring the input==@ref invariant violated since PR #64 (commit 6700c9d8) — eliminates ASSESS-4 staleness signal at test.yml:79 per pipeline-inventory L370-L373. Net: 6 of the 6 B2-class entropy touchpoints reduced to 0; aws-actions/configure-aws-credentials skew (2 SHAs) explicitly deferred to a follow-up batch (out of B2 scope). |
| **B3** | ready | 10 | low | CI value-per-minute improvement (operator B3 mandate): PR-gate slow-test coverage increases from 0 → 46 tests (post-rearchitecting + demarking; ~14 tests retain slow marker for legitimate Category A genuinely-slow subprocess and Category D memory-leak). Wall-time analysis (probed via uv run pytest -m slow --durations=60 -o addopts='' which measured 65.79s for 46 tests serial): Category B rearchitecting (CHANGE-001..003, 10 tests) eliminates retry-backoff wall time = ~25s saved (each test drops from 1.7-4.15s to <0.05s); Category D rearchitecting (CHANGE-005, 3 TTL tests) eliminates real time.sleep(1.1) = ~3.3s saved; Category C demarking (CHANGE-004, 006, 007, 008, ~18 tests) adds ~3s of net PR wall time (these tests run anyway on main; now also on PR). Net PR-shard wall time increase ≈ +12s (with xdist parallelism on 2 workers, +6s effective). Net value: catches the slow-test fault classes (timing-bound TTL regressions, HTTP error mapping breakage, health endpoint regressions, admin route 422 contract drift, circuit-breaker state transitions) on EVERY PR rather than fix-forward post-merge. Aligned with operator mandate "10x value-per-CI-minute" — ~6s parallel CI overhead unlocks 46 test signal sources per PR, where each currently-undetected regression would require a fix-forward commit cycle (typically 20+ min round-trip). |
| **B6** | ready | 1 | low | MockPageIterator proliferation index reduces from 4:1 (4 bespoke independent definitions, no shared canonical) to 1:1 CLEAN (1 canonical at automation/conftest.py, 4 import consumers). Net -3 class definitions; net +1 conftest module. Test function count preserved (baseline 131 across the 4 files; post-consolidation must remain >=131 per test_command assertion). DEFERRED (not addressed in B6, require separate per-mock superset analysis with test re-run gate): MockProcess 4:1 (test_assignee_resolution / test_onboarding_comment / test_pipeline / test_pipeline_hierarchy — divergent: rep property vs memberships vs business/unit/notes vs unit/process_holder); MockBusiness 3:1 (rep property vs name-only vs office_phone+company_id+primary_contact_phone); MockSection 3:1 (test_templates requires gid no-default vs test_integration/test_pipeline default gid='section_123'); MockProcessType 3:1 (test_base/test_integration: SALES+ONBOARDING vs test_pipeline: SALES+ONBOARDING+GENERIC — distinct enum identities); MockUnit 3:1 (rep vs vertical/platforms/booking_type vs process_holder); MockEntity 3:1 across automation/events/test_engine_integration, automation/events/test_rule, automation/test_base (different __class_name__ vs entity_type semantics). BLOCKED (intentional divergence): MockCacheProvider in tests/unit/cache/test_events.py:38 has a self-documenting docstring stating 'Cannot directly use SDK MockCacheProvider due to CacheMetrics class mismatch' — consolidation would break the satellite-vs-SDK CacheMetrics segregation. RISKY (changes test semantics): MockAuthProvider 3:1 — test_client.py:16 is hardcoded-token-return (no __init__), test_aimd_integration.py:21 / test_asana_http.py:23 inject token via __init__; root conftest auth_provider fixture is MagicMock(spec=AuthProvider) without token-injection contract. Substituting MagicMock fixture for the concrete-class custom_provider in test_client.py::test_init_with_custom_auth_provider would invert the contract the test asserts. Each deferred type requires a separate engineering task: (i) design the superset signature, (ii) replace one consumer at a time, (iii) re-run that file's tests, (iv) one commit per consumer — not appropriate for a single 'one CHANGE per mock type' atomic batch given the source-evidence-verified semantic divergence. |
| **B8** | ready | 1 | low | Module-level blanket xfail entries 1 to 0. Per-endpoint xfail entries 0 to 55 (45 violation plus 10 conforming-pinned). Premise-validation discharge of 47-narrative to empirical 45 plus 10. Pytest outcome shape preserved 45 xfailed plus 10 xpassed. |

## Per-batch detail

### B0 — Shellcheck baseline cleanup (root-fix gate precondition)

**Rationale**: B1 CHANGE-001 halted at the actionlint gate against 3 pre-existing shellcheck warnings in test.yml — SC2086 (unquoted `$GITHUB_ENV`/`$GITHUB_STEP_SUMMARY`), SC2155 (export + assign in single line masking return values), SC2129 (sequential redirects to same file). These are at-rest baseline debt unrelated to any planned edit. Per operator-ratified Option-B (2026-06-01 mandate "be unforgiving and ruthlessly aligned to fix the root problems within our test & CI/CD ecosystem"), the root-fix is to resolve the shellcheck warnings rather than scope-narrow the gate. Two atomic CHANGEs: CHANGE-001 fixes both byte-identical CodeArtifact-login `run:` blocks (L122-127 fuzz job + L237-242 workflow-handler-isolated job's setup step); CHANGE-002 fixes the Fleet Schema Governance `run:` block (L291-305) via `{ ... } >> "$GITHUB_STEP_SUMMARY"` grouping. Both CHANGEs are shell-script-style-only — zero semantic change to workflow behavior (token export still works, env var still set, step summary still appended).

**Frozen attestation**: Both CHANGEs touch ONLY `.github/workflows/test.yml`. The FROZEN worker_isolated quarantine semantics live at: (a) L64 `test_markers_exclude` clause (NOT TOUCHED — different region); (b) L206-216 quarantine job header + comment block (NOT TOUCHED — comment lines preserved verbatim); (c) L216 `continue-on-error: true` (NOT TOUCHED); (d) L260-262 `-p no:xdist -o addopts=""` pytest invocation (NOT TOUCHED). CHANGE-001's edit at L237-242 modifies the SETUP step (CodeArtifact login) inside the quarantine job, NOT the quarantine semantic itself. CHANGE-002 at L291-305 is in the SEPARATE fleet-schema-governance job (L264+), structurally disjoint from any quarantine. Sprint-1 IMPL-1 commits 3755551a..31f5e2c8 touch src/ only (not .github/workflows/) — confirmed disjoint. All other frozen surfaces (A1, require_business_scope, honest_contract, offer-domain, router mount-order, P1-C-04, HC-7, SA OAuth chain, OPERATIONAL altitude frontmatter) are non-workflow surfaces — vacuously disjoint.

**Changes**:

#### CHANGE-001 — fix shellcheck SC2086/SC2155 in CodeArtifact-login run blocks (test.yml L122-127 + L237-242)
- **Files**: .github/workflows/test.yml
- **Edit**: At test.yml:124-127 (fuzz job CodeArtifact login) AND test.yml:239-242 (workflow-handler-isolated job CodeArtifact login): apply the SAME byte-identical fix at both locations. Replace the 5-line `run:` body verbatim. BEFORE (both locations identical):
  ```
            export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
              --domain autom8y --domain-owner 696318035277 \
              --query authorizationToken --output text)
            echo "UV_EXTRA_INDEX_URL=https://aws:${CODEARTIFACT_AUTH_TOKEN}@autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/simple/" >> $GITHUB_ENV
  ```
  AFTER (both locations identical):
  ```
            CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
              --domain autom8y --domain-owner 696318035277 \
              --query authorizationToken --output text)
            export CODEARTIFACT_AUTH_TOKEN
            echo "UV_EXTRA_INDEX_URL=https://aws:${CODEARTIFACT_AUTH_TOKEN}@autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/simple/" >> "$GITHUB_ENV"
  ```
  Two style fixes per location: (1) split `export X=$(...)` into `X=$(...)` + `export X` (SC2155 — declare-and-assign separately so the subshell exit code is not masked by `export`); (2) quote `$GITHUB_ENV` → `"$GITHUB_ENV"` (SC2086 — defensive against globbing/word-splitting, even though GitHub-set vars are reliable). Zero semantic change: token is still exported, env var is still appended. Both locations modified in ONE atomic commit (single logical unit: harmonize CodeArtifact-login shell-script hygiene across the two inline jobs that use this pattern).
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml 2>&1 | grep -E '(SC2086|SC2155)' | grep -E ':(123|238):' ; [ $? -ne 0 ] && echo "OK: SC2086/SC2155 cleared at L123/L238"`
- **Commit**: `ci(workflows): fix shellcheck SC2086/SC2155 in CodeArtifact-login blocks`
- **Revert**: `git revert <sha-of-CHANGE-001>`

#### CHANGE-002 — fix shellcheck SC2086/SC2129 in fleet-schema-governance run block (test.yml L291-305)
- **Files**: .github/workflows/test.yml
- **Edit**: At test.yml:292-305 (fleet-schema-governance step `run:` block): replace the body to group the 4 sequential `>> $GITHUB_STEP_SUMMARY` redirects into a single `{ ... } >> "$GITHUB_STEP_SUMMARY"` block. BEFORE (L292-305):
  ```
            set +e
            python _autom8y-api-schemas/src/autom8y_api_schemas/governance/check_response_meta.py \
              --json ./src/ > /tmp/governance.json
            exit_code=$?
            set -e
            echo "## Fleet Schema Governance" >> $GITHUB_STEP_SUMMARY
            echo '```json' >> $GITHUB_STEP_SUMMARY
            cat /tmp/governance.json >> $GITHUB_STEP_SUMMARY
            echo '```' >> $GITHUB_STEP_SUMMARY
            if [ $exit_code -ne 0 ]; then
              echo "::error::V1-subclassing hazard detected. See governance output."
              exit 1
            fi
  ```
  AFTER:
  ```
            set +e
            python _autom8y-api-schemas/src/autom8y_api_schemas/governance/check_response_meta.py \
              --json ./src/ > /tmp/governance.json
            exit_code=$?
            set -e
            {
              echo "## Fleet Schema Governance"
              echo '```json'
              cat /tmp/governance.json
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
            if [ $exit_code -ne 0 ]; then
              echo "::error::V1-subclassing hazard detected. See governance output."
              exit 1
            fi
  ```
  Three style fixes in one atomic edit: (1) group 4 redirects into one block (SC2129); (2) quote `"$GITHUB_STEP_SUMMARY"` (SC2086 — resolves all 4 SC2086 instances since they were all the same variable across the 4 redirects). The `[ $exit_code -ne 0 ]` is NOT modified — it's not in the shellcheck warning report (shellcheck only flags $exit_code in `$( )` contexts, not `[ ]` tests). The 4 echo/cat statements emit identical content as before (just batched). Zero semantic change to the governance behavior.
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml 2>&1 | grep -E '(SC2086|SC2129)' | grep -E ':292:' ; [ $? -ne 0 ] && echo "OK: SC2086/SC2129 cleared at L292"`
- **Commit**: `ci(workflows): fix shellcheck SC2086/SC2129 in fleet-schema-governance block`
- **Revert**: `git revert <sha-of-CHANGE-002>`

### B1 — Fuzz artifact name mismatch

**Rationale**: Direct inspection of both workflow files confirms a literal-vs-templated artifact-name mismatch: `.github/workflows/test.yml:155` hardcodes `name: candidate-wheel`, while the upstream uploader at `autom8y/.github/workflows/sdk-publish-v2.yml:614` writes `name: consumer-gate-wheel-${{ matrix.sdk }}-${{ matrix.satellite }}`. Matrix.satellite is the full repo name `autom8y-asana` (verified at sdk-publish-v2.yml:536), so this satellite's artifact is `consumer-gate-wheel-{candidate_sdk_name}-autom8y-asana`. The dispatcher (consumer-gate CLI) passes `candidate_sdk_name` and `candidate_wheel_run_id` together (cli.py:259-261), so the templated name resolves correctly whenever the download step is gated-on (`inputs.candidate_wheel_run_id != ''`). Root fix is a single-line edit to template the artifact name from the existing `candidate_sdk_name` input plus the literal repo identity `autom8y-asana`.

**Frozen attestation**: Verified the following frozen surfaces are NOT touched by this plan: (1) Sprint-1 IMPL-1 commits 3755551a..31f5e2c8 — this CHANGE touches `.github/workflows/test.yml` only, which is not part of those commits' diff (those commits modified `src/`, the BuildCoordinator wiring, SA OAuth namespace, and Retry-After header — confirmed by git log range scope). (2) A1 body-parameterized contract (4822eaad) — src-only commit, not workflow. (3) require_business_scope=True — src setting, not workflow. (4) honest_contract derivation — UNTOUCHED. (5) offer-domain 27-entity non-regression — src, not workflow. (6) router mount-order discipline — src, not workflow. (7) query engine P1-C-04 — src, not workflow. (8) HC-7 contract — src, not workflow. (9) SA OAuth provisioning chain (SSM/SM paths) — infra, not workflow. (10) test_workflow_handler.py worker_isolated quarantine — test file, not workflow (and the quarantine is implemented via `test_markers_exclude: ... not worker_isolated` at test.yml:64, which this CHANGE does NOT modify — the edit is at L155 only). (11) altitude: OPERATIONAL — frontmatter declaration, not workflow body. The single-line edit is at test.yml:155 inside the fuzz-job download step (L151-159), structurally disjoint from any frozen surface.

**Changes**:

#### CHANGE-001 — fix fuzz job artifact name to match upstream upload pattern (consumer-gate-wheel-{sdk}-autom8y-asana)
- **Files**: .github/workflows/test.yml
- **Edit**: Edit /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml at line 155. Replace the literal `          name: candidate-wheel` with `          name: consumer-gate-wheel-${{ inputs.candidate_sdk_name }}-autom8y-asana`. No other lines change. The change is YAML-string-only, scoped to the download-artifact step within the `if: inputs.candidate_wheel_run_id != ''` guard (L152), so push/PR code paths are untouched. The templated name resolves to e.g. `consumer-gate-wheel-asana-autom8y-asana` when SDK=asana is dispatched from autom8y/sdk-publish-v2.yml:610-617. The `candidate_sdk_name` input is already declared at L14-18 and is guaranteed non-empty whenever `candidate_wheel_run_id` is non-empty (consumer-gate CLI dispatches both together, cli.py:259-261).
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml && grep -q 'name: consumer-gate-wheel-\${{ inputs.candidate_sdk_name }}-autom8y-asana' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml && echo OK`
- **Commit**: `fix(ci): align fuzz artifact name with consumer-gate upload pattern`
- **Revert**: `git revert <sha-of-CHANGE-001-commit>`

### B2 — Action version skew + autom8y_workflows_sha sync

**Rationale**: B2 has two independent sub-fixes both confirmed by direct source inspection. Sub-fix (a) — setup-uv pin skew: 3 files at v4 SHA 38f3f104, 2 inline jobs in test.yml at v6 SHA 6b9c6063, while the fleet reusable workflow (test.yml:45 @ref cbc3c58e) already pins v8.1.0 SHA 08807647 (PR #13). Harmonize all 5 occurrences to the fleet-current pin (08807647 # v8.1.0) — root-fix aligning satellite to fleet canonical rather than freezing a stale local pin. Sub-fix (b) — autom8y_workflows_sha staleness: test.yml:79 input c88caabd is 7 commits behind test.yml:45 @ref cbc3c58e (verified via git log); inventory L189 confirms zero functional impact (fleet-conformance-spec.yml unchanged between the two SHAs) but the structural invariant (input SHA == @ref SHA) is violated and PR #64 set the recurrence precedent. Sync input to cbc3c58e. Five atomic commits — each a single-file YAML pin edit, each independently `git revert`-safe.

**Frozen attestation**: Verified zero overlap with frozen surfaces: (a) commit range 3755551a..31f5e2c8 (PR #69) contains no .github/workflows/ edits — confirmed by `git log 3755551a..31f5e2c8 -- .github/workflows/` returning empty. (b) test_workflow_handler.py worker_isolated quarantine (test.yml:206-262 + pyproject.toml:112) is preserved verbatim — CHANGE-004 only edits the single setup-uv@ line at L245 inside the quarantine job; the `continue-on-error: true`, `worker_isolated` marker exclusion at L64, `-p no:xdist -o addopts=\"\"` invocation at L260-262, and the entire quarantine comment block are NOT touched (verification asserts `grep -q 'worker_isolated' test.yml` post-edit). (c) honest_contract, require_business_scope, HC-7, P1-C-04, router mount-order, SA OAuth provisioning chain, A1 body-parameterized contract, offer-domain 27-entity surfaces are all Python source-code surfaces in src/ — none are touched (changes are .github/workflows/*.yml only). (d) test.yml:45 @ref pin is INTENTIONALLY untouched; only test.yml:79 input is synced TO match it.

**Changes**:

#### CHANGE-001 — ci(workflows): bump setup-uv to fleet v8.1.0 pin in post-merge-coverage.yml
- **Files**: .github/workflows/post-merge-coverage.yml
- **Edit**: post-merge-coverage.yml:43 — replace 'astral-sh/setup-uv@38f3f104447c67c051c4a08e39b64a148898af3a # v4' with 'astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0'. Single-line YAML pin change inside the coverage job's `steps:` list. No other lines touched. Aligns to fleet canonical (autom8y-workflows/satellite-ci-reusable.yml:233,437,621,697,888 all pin 08807647 v8.1.0 per PR #13 commit 72eaee8).
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/post-merge-coverage.yml && grep -q '08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/post-merge-coverage.yml && ! grep -q '38f3f104447c67c051c4a08e39b64a148898af3a' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/post-merge-coverage.yml`
- **Commit**: `ci(workflows): align setup-uv to fleet v8.1.0 pin in post-merge-coverage`
- **Revert**: `git revert <sha>`

#### CHANGE-002 — ci(workflows): bump setup-uv to fleet v8.1.0 pin in aegis-synthetic-coverage.yml
- **Files**: .github/workflows/aegis-synthetic-coverage.yml
- **Edit**: aegis-synthetic-coverage.yml:40 — replace 'astral-sh/setup-uv@38f3f104447c67c051c4a08e39b64a148898af3a # v4' with 'astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0'. Single-line YAML pin change inside the aegis coverage job. No other lines touched.
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/aegis-synthetic-coverage.yml && grep -q '08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/aegis-synthetic-coverage.yml && ! grep -q '38f3f104447c67c051c4a08e39b64a148898af3a' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/aegis-synthetic-coverage.yml`
- **Commit**: `ci(workflows): align setup-uv to fleet v8.1.0 pin in aegis-synthetic-coverage`
- **Revert**: `git revert <sha>`

#### CHANGE-003 — ci(workflows): bump setup-uv to fleet v8.1.0 pin in durations-refresh.yml
- **Files**: .github/workflows/durations-refresh.yml
- **Edit**: durations-refresh.yml:36 — replace 'astral-sh/setup-uv@38f3f104447c67c051c4a08e39b64a148898af3a # v4' with 'astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0'. Single-line YAML pin change inside the durations-refresh job. Preserves the existing `with: enable-cache: true / cache-dependency-glob: 'uv.lock'` block on subsequent lines. No other lines touched.
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/durations-refresh.yml && grep -q '08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/durations-refresh.yml && ! grep -q '38f3f104447c67c051c4a08e39b64a148898af3a' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/durations-refresh.yml`
- **Commit**: `ci(workflows): align setup-uv to fleet v8.1.0 pin in durations-refresh`
- **Revert**: `git revert <sha>`

#### CHANGE-004 — ci(workflows): align setup-uv pins to fleet v8.1.0 in test.yml inline jobs
- **Files**: .github/workflows/test.yml
- **Edit**: test.yml:130 (fuzz job) and test.yml:245 (workflow-handler-isolated job) — replace both occurrences of 'astral-sh/setup-uv@6b9c6063abd6010835644d4c2e1bef4cf5cd0fca # v6' with 'astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0'. Two single-line YAML pin changes within the same file (logical unit: harmonize test.yml inline jobs to fleet canonical). DO NOT touch any other test.yml line — the workflow-handler-isolated quarantine semantics (test.yml:206-262 worker_isolated containment per ASSESS-5 FROZEN) remain untouched; only the setup-uv pin inside that job is bumped.
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml && [ "$(grep -c '08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml)" = "2" ] && ! grep -q '6b9c6063abd6010835644d4c2e1bef4cf5cd0fca' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml && grep -q 'worker_isolated' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml`
- **Commit**: `ci(workflows): align setup-uv pins to fleet v8.1.0 in test.yml inline jobs`
- **Revert**: `git revert <sha>`

#### CHANGE-005 — ci(workflows): sync autom8y_workflows_sha input to match @ref pin
- **Files**: .github/workflows/test.yml
- **Edit**: test.yml:79 — replace 'autom8y_workflows_sha: c88caabd8d9bba883e6a42628bdc2bba6d30512b' with 'autom8y_workflows_sha: cbc3c58e56f3e0adeaf57101c0400d8f5d7845ed'. The new value MUST equal the @ref pin at test.yml:45 ('autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@cbc3c58e56f3e0adeaf57101c0400d8f5d7845ed'). Structural invariant restored: input SHA == @ref SHA. Functional impact: zero per pipeline-inventory L189 (fleet-conformance-spec.yml unchanged between c88caabd and cbc3c58e). DO NOT touch test.yml:45 — the @ref pin itself is correct.
- **Test**: `actionlint /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml && REF=$(grep 'satellite-ci-reusable.yml@' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml | sed -E 's/.*@([0-9a-f]{40}).*/\1/') && INPUT=$(grep 'autom8y_workflows_sha:' /Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml | sed -E 's/.*: ([0-9a-f]{40}).*/\1/') && [ "$REF" = "$INPUT" ] && [ "$REF" = "cbc3c58e56f3e0adeaf57101c0400d8f5d7845ed" ]`
- **Commit**: `ci(workflows): sync autom8y_workflows_sha input to match @ref pin`
- **Revert**: `git revert <sha>`

### B3 — Slow-marker PR gate + 10x test value-per-CI-minute rearchitecting

**Rationale**: Inventory verified: 23 `@pytest.mark.slow` markers expanding to 46 test instances total wall-time 65.79s. Classification by direct timing probe: (A) 12 subprocess CLI tests genuinely ~0.7s each due to interpreter cold-start (KEEP slow + add to PR gate); (B) 10 tests `slow-by-convention` because `DataServiceClient()` default `RetryConfig(max_retries=2, base_delay=1.0, jitter=True)` causes real exponential-backoff wall-time on 502/503/504/timeout respx responses (REARCHITECT: inject `RetryConfig(max_retries=0)` — test purpose is error mapping, not retry behavior); (C) ~18 tests already <0.05s (mismarked defensively — DEMARK to restore PR coverage at zero CI cost); (D) 4 timing-bound tests use real `time.sleep(1.1)` against `time.time()`/`datetime.now()` — rearchitect 3 TTL tests via `unittest.mock.patch` (no new deps needed; freezegun not in uv.lock and adding it is separate atomic risk), keep `test_no_memory_leak_on_repeated_clear` slow (cycle-count semantic). Final atomic: add `slow` to PR marker selector in `test.yml:64`. Frozen surface `tests/unit/lambda_handlers/test_workflow_handler.py` is NOT touched by any change. Each CHANGE is one file = one commit = independently revertible (reverting any rearch leaves the file still passing under both old and new gate state).

**Frozen attestation**: Confirmed UNTOUCHED across all 10 CHANGEs: (1) tests/unit/lambda_handlers/test_workflow_handler.py — verified via grep -rn '@pytest.mark.slow' tests/unit/lambda_handlers/ which returned zero hits; this file has worker_isolated marker (test_workflow_handler.py:58) and xdist_group quarantine, NOT slow marker; (2) the worker_isolated exclusion in test.yml:64 preserved verbatim in CHANGE-009 (only `and not slow` clause removed); (3) Sprint-1 IMPL-1 commits 3755551a..31f5e2c8 untouched (no src/ modifications, no router/contract/HC-7 changes); (4) A1 body-parameterized contract (4822eaad) untouched (no api/router edits); (5) require_business_scope=True untouched (no auth changes); (6) honest_contract derivation untouched (no contract/derivation edits); (7) offer-domain 27-entity non-regression untouched (no offer module edits); (8) router mount-order untouched (no api/__init__.py or main.py edits); (9) query engine P1-C-04 untouched; (10) HC-7 contract untouched; (11) SA OAuth provisioning chain untouched (no terraform/SSM/SM edits). All 10 CHANGEs touch ONLY: 9 test files in tests/ + 1 ci file (.github/workflows/test.yml) + 1 docs file (.know/conventions.md). Test function count delta computed: zero net change across all 10 CHANGEs (every test preserved; only markers and body retry-config injection modified). 46 test instances stay 46.

**Changes**:

#### CHANGE-001 — test_insights.py: inject RetryConfig(max_retries=0) into 4 error-mapping tests and remove @pytest.mark.slow
- **Files**: tests/unit/clients/data/test_insights.py
- **Edit**: At tests/unit/clients/data/test_insights.py:385 (test_502_maps_to_service_error), :411 (test_503), :436 (test_504), :461 (test_timeout_maps_to_service_error): (a) remove the `@pytest.mark.slow` decorator from each of the 4 tests; (b) replace `client = DataServiceClient()` (one occurrence inside each test body) with `client = DataServiceClient(config=DataServiceConfig(retry=RetryConfig(max_retries=0)))`; (c) add import `from autom8_asana.clients.data.config import DataServiceConfig, RetryConfig` to the existing import at line 17 (DataServiceConfig is already imported — extend to add RetryConfig from same module). Test purpose is error code-to-exception mapping; retries-with-backoff is covered by test_circuit_breaker.py. Test function count delta: 0 (4 retained).
- **Test**: `uv run pytest tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_502_maps_to_service_error tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_503_maps_to_service_error tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_504_maps_to_service_error tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_timeout_maps_to_service_error -o addopts='' --no-cov -v --durations=10`
- **Commit**: `test(clients-data): disable retries in insights error-mapping tests; demark slow`
- **Revert**: `git revert <sha-of-CHANGE-001>`

#### CHANGE-002 — test_cache.py: inject RetryConfig(max_retries=0) into 4 stale-fallback tests and remove @pytest.mark.slow
- **Files**: tests/unit/clients/data/test_cache.py
- **Edit**: At tests/unit/clients/data/test_cache.py:275 (test_stale_fallback_on_server_error — parametrized 502/503/504) and :322 (test_stale_fallback_on_timeout): (a) remove the `@pytest.mark.slow` decorator from each; (b) inside each test body replace `client = DataServiceClient(cache_provider=mock_cache)` with `client = DataServiceClient(cache_provider=mock_cache, config=DataServiceConfig(retry=RetryConfig(max_retries=0)))`; (c) ensure `DataServiceConfig, RetryConfig` are imported at module top (check existing import at top of file; if missing, add `from autom8_asana.clients.data.config import DataServiceConfig, RetryConfig`). Test purpose is stale-cache-fallback behavior on transient server error / timeout — retry policy is orthogonal. Test function count delta: 0 (4 retained; one is parametrized expanding to 3 cases).
- **Test**: `uv run pytest tests/unit/clients/data/test_cache.py::TestStaleFallback::test_stale_fallback_on_server_error tests/unit/clients/data/test_cache.py::TestStaleFallback::test_stale_fallback_on_timeout -o addopts='' --no-cov -v --durations=10`
- **Commit**: `test(clients-data): disable retries in stale-fallback tests; demark slow`
- **Revert**: `git revert <sha-of-CHANGE-002>`

#### CHANGE-003 — test_observability.py: inject RetryConfig(max_retries=0) into timeout-metric test and remove @pytest.mark.slow
- **Files**: tests/unit/clients/data/test_observability.py
- **Edit**: At tests/unit/clients/data/test_observability.py:343 (test_error_metrics_emitted_on_timeout): (a) remove the `@pytest.mark.slow` decorator; (b) replace `client = DataServiceClient(metrics_hook=mock_hook)` with `client = DataServiceClient(metrics_hook=mock_hook, config=DataServiceConfig(retry=RetryConfig(max_retries=0)))`; (c) ensure `DataServiceConfig, RetryConfig` are imported at module top (check existing imports; extend or add). Test asserts metric `error_type=='timeout'` is emitted — retry policy orthogonal. Test function count delta: 0 (1 retained).
- **Test**: `uv run pytest tests/unit/clients/data/test_observability.py::TestObservabilityMetrics::test_error_metrics_emitted_on_timeout -o addopts='' --no-cov -v --durations=5`
- **Commit**: `test(clients-data): disable retries in observability timeout test; demark slow`
- **Revert**: `git revert <sha-of-CHANGE-003>`

#### CHANGE-004 — test_circuit_breaker.py: remove @pytest.mark.slow from 2 mismarked tests (already <0.02s)
- **Files**: tests/unit/clients/data/test_circuit_breaker.py
- **Edit**: At tests/unit/clients/data/test_circuit_breaker.py:67 (test_circuit_opens_after_threshold) and :109 (test_circuit_open_raises_immediately): remove the `@pytest.mark.slow` decorator. Both tests already use `RetryConfig(max_retries=0)` (confirmed at lines 85, 126) and run at 0.01s each per pytest --durations output. The slow marker was defensive but is inaccurate; these tests belong in the fast PR gate. Test function count delta: 0 (2 retained).
- **Test**: `uv run pytest tests/unit/clients/data/test_circuit_breaker.py::TestCircuitBreaker::test_circuit_opens_after_threshold tests/unit/clients/data/test_circuit_breaker.py::TestCircuitBreaker::test_circuit_open_raises_immediately -o addopts='' --no-cov -v --durations=5`
- **Commit**: `test(clients-data): demark slow on circuit-breaker tests already running fast`
- **Revert**: `git revert <sha-of-CHANGE-004>`

#### CHANGE-005 — test_memory_backend.py: rearchitect 3 TTL tests via time.time/datetime.now mock; remove @pytest.mark.slow
- **Files**: tests/unit/cache/test_memory_backend.py
- **Edit**: At tests/unit/cache/test_memory_backend.py:131 (test_ttl_expiration), :141 (test_explicit_ttl_override), :456 (test_versioned_ttl_expiration): (a) remove `@pytest.mark.slow`; (b) replace `time.sleep(1.1)` with patched-time mechanic — for `test_ttl_expiration` and `test_explicit_ttl_override` (which read via cache.get -> time.time): wrap the test body in `with patch('autom8_asana.cache.backends.memory.time.time') as mock_time:` setting `mock_time.return_value = time.time(); cache.set(...); mock_time.return_value += 2.0; assert cache.get('key') is None`; for `test_versioned_ttl_expiration` (which reads via cache.get_versioned -> CacheEntry.is_expired -> datetime.now): wrap with `with patch('autom8_asana.cache.models.entry.datetime') as mock_dt:` setting `mock_dt.now.return_value = datetime.now(UTC); cache.set_versioned(...); mock_dt.now.return_value += timedelta(seconds=2)`. Ensure `from unittest.mock import patch` is imported. Test semantics preserved: TTL expiration is asserted by simulating elapsed time. Test function count delta: 0 (3 retained).
- **Test**: `uv run pytest tests/unit/cache/test_memory_backend.py::TestInMemoryCacheProvider::test_ttl_expiration tests/unit/cache/test_memory_backend.py::TestInMemoryCacheProvider::test_explicit_ttl_override tests/unit/cache/test_memory_backend.py::TestEnhancedInMemoryCacheProvider::test_versioned_ttl_expiration -o addopts='' --no-cov -v --durations=5`
- **Commit**: `test(cache): mock time.time/datetime.now in TTL tests; demark slow`
- **Revert**: `git revert <sha-of-CHANGE-005>`

#### CHANGE-006 — test_routes_admin.py + test_routes_admin_edge_cases.py: demark slow on 4 mismarked tests
- **Files**: tests/unit/api/test_routes_admin.py, tests/unit/api/test_routes_admin_edge_cases.py
- **Edit**: At tests/unit/api/test_routes_admin.py:161 (test_admin_refresh_accepts_all_valid_entity_types) and :260 (test_admin_refresh_all_types): remove `@pytest.mark.slow`. At tests/unit/api/test_routes_admin_edge_cases.py:152 (test_force_full_rebuild_non_boolean_coerced) and :183 (test_multiple_rapid_requests_all_accepted): remove `@pytest.mark.slow`. All 4 tests run at <0.95s (per --durations probe); 3 of them at <0.05s. These are TestClient invocations with mocked registries — no genuine slow signal. Test function count delta: 0 (4 retained).
- **Test**: `uv run pytest tests/unit/api/test_routes_admin.py tests/unit/api/test_routes_admin_edge_cases.py -o addopts='' --no-cov -v --durations=10`
- **Commit**: `test(api): demark slow on admin-route tests already running fast`
- **Revert**: `git revert <sha-of-CHANGE-006>`

#### CHANGE-007 — test_health.py: replace class-level @pytest.mark.slow on TestDepsEndpoint with per-test marker only on slowest sub-test
- **Files**: tests/unit/api/test_health.py
- **Edit**: At tests/unit/api/test_health.py:250 (class TestDepsEndpoint): remove the class-level `@pytest.mark.slow` decorator. All 10 sub-tests run at <0.5s each per --durations probe and exercise critical /health/deps endpoint contract (JWKS probe, PAT configured/not-configured, error paths). Removing the class-level mark restores PR coverage for the health probe surface. Class structure preserved; no per-test markers added (none of the sub-tests warrant slow). Test function count delta: 0 (10 retained, all expanded as before but no longer slow-excluded on PR).
- **Test**: `uv run pytest tests/unit/api/test_health.py::TestDepsEndpoint -o addopts='' --no-cov -v --durations=15`
- **Commit**: `test(api): demark slow on health/deps endpoint test class`
- **Revert**: `git revert <sha-of-CHANGE-007>`

#### CHANGE-008 — test_startup_preload.py + test_performance.py + test_concurrency.py + test_edge_cases.py: demark slow on remaining mismarked tests; keep slow on memory-leak test
- **Files**: tests/unit/api/test_startup_preload.py, tests/validation/persistence/test_performance.py, tests/unit/cache/test_concurrency.py
- **Edit**: At tests/unit/api/test_startup_preload.py:122 (test_preload_loads_index_from_s3_and_does_incremental_catchup): remove `@pytest.mark.slow` (runs at 0.01s call time per durations). At tests/validation/persistence/test_performance.py:297 (test_memory_overhead_estimation): remove `@pytest.mark.slow` (runs at 0.43s; class TestMemoryOverhead exercises tracker memory invariant — fast enough for PR). At tests/unit/cache/test_concurrency.py:518 (test_concurrent_cleanup): remove `@pytest.mark.slow` (runs at 0.62s with 10 threads and 100 iterations; CI parallelism makes this trivial). NOTE: tests/unit/cache/test_edge_cases.py:272 (test_no_memory_leak_on_repeated_clear) is NOT touched here — it runs 10x100 cycles + repeated gc.collect at 1.88s; the cycle count is semantic (memory invariant under repeated pressure) and retaining slow marker is correct per Category D classification. Test function count delta: 0 (3 demarked + 1 retained).
- **Test**: `uv run pytest tests/unit/api/test_startup_preload.py::TestPreloadDataframeCacheFunction::test_preload_loads_index_from_s3_and_does_incremental_catchup tests/validation/persistence/test_performance.py::TestMemoryOverhead::test_memory_overhead_estimation tests/unit/cache/test_concurrency.py::TestModificationCheckCacheConcurrency::test_concurrent_cleanup -o addopts='' --no-cov -v --durations=10`
- **Commit**: `test: demark slow on fast preload/perf/concurrency tests`
- **Revert**: `git revert <sha-of-CHANGE-008>`

#### CHANGE-009 — test.yml: enable slow marker on PR gate (final atomic flip)
- **Files**: .github/workflows/test.yml
- **Edit**: At .github/workflows/test.yml:64 modify the `test_markers_exclude` ternary to no longer exclude `slow` on pull_request. Change from `${{ github.event_name == 'pull_request' && 'not integration and not benchmark and not slow and not fuzz and not worker_isolated' || 'not integration and not benchmark and not fuzz and not worker_isolated' }}` to the unified form `'not integration and not benchmark and not fuzz and not worker_isolated'` (both branches identical; ternary collapses). Update the comment block at lines 61-63 to add: `# slow tests included on BOTH PR and main push: post-rearchitecting (CHANGE-001..008) only ~14 tests retain slow marker; 32 mismarked/rearchitected tests now run on PR. See .know/conventions.md slow-marker policy.` Frozen: `worker_isolated` exclusion preserved verbatim (DO NOT touch). Test function count delta: 0 (gate selector only; no test files modified).
- **Test**: `yamllint .github/workflows/test.yml && grep -n 'test_markers_exclude' .github/workflows/test.yml`
- **Commit**: `ci(test): enable slow marker on PR gate after rearchitecting`
- **Revert**: `git revert <sha-of-CHANGE-009>`

#### CHANGE-010 — conventions.md: document slow-marker policy and Category A/B/C/D classification
- **Files**: .know/conventions.md
- **Edit**: Append a new H2 section `## Slow Test Marker Policy` to .know/conventions.md (after the existing `## Naming Patterns` section ending at line 448, before `## Experiential Observations`). Body documents: (1) `@pytest.mark.slow` is reserved for tests that CANNOT be made fast without losing semantic intent (timing-bound, subprocess-bound, cycle-count-bound); (2) classification taxonomy A-Genuinely-Slow / B-Slow-By-Convention / C-Mismarked / D-Timing-Bound with one canonical example per category from this codebase; (3) the rearchitecting rules: prefer `unittest.mock.patch` of `time.time`/`datetime.now` over `time.sleep`; inject `RetryConfig(max_retries=0)` when testing error mapping (not retry policy); use subprocess only when the production entry IS a CLI; (4) policy: slow tests now run on BOTH PR and main push as of CHANGE-009 — adding `@pytest.mark.slow` requires inline justification comment naming the Category A/D rationale. Length: ~40 lines. Pure documentation; no code semantics affected.
- **Test**: `head -1 .know/conventions.md && grep -n 'Slow Test Marker Policy' .know/conventions.md && wc -l .know/conventions.md`
- **Commit**: `docs(conventions): document slow-marker policy and A/B/C/D classification taxonomy`
- **Revert**: `git revert <sha-of-CHANGE-010>`

### B6 — automation/ domain conftest + MockCacheProvider/MockAuthProvider consolidation

**Rationale**: Direct inspection of the 13 automation/ test files reveals heavy semantic divergence among MockProcess (4), MockBusiness (3), MockSection (3), MockProcessType (3), MockProcess attributes vary per file (process_holder, unit, business, notes, memberships). Only MockPageIterator (4 instances) is byte-identical and can be consolidated without semantic risk. The HYG-003 1:1 pattern requires either byte-identity or verified-safe superset; neither holds for the divergent classes without per-file behavioral re-verification (separate engineering effort, not a structural consolidation). MockCacheProvider in cache/test_events.py is documented INTENTIONAL divergence (CacheMetrics class mismatch) — blocked. MockAuthProvider replacement would change test_client.py contract (custom-class-as-arg vs MagicMock fixture) — risky. Per operator mandate "no shortcuts, bandaids, or patching instead of resolving," the honest atomic plan is one safe consolidation and explicit deferrals naming the per-mock superset-design work required for the divergent cases.

**Frozen attestation**: Reviewed FROZEN list pre-planning. CHANGE-001 touches ONLY tests/unit/automation/{conftest.py,test_waiter.py,test_templates.py,test_integration.py,test_pipeline.py}. None of: Sprint-1 IMPL-1 commits 3755551a..31f5e2c8, A1 body-parameterized contract (4822eaad), require_business_scope, honest_contract, offer-domain 27-entity, router mount-order, query engine P1-C-04, HC-7 contract, SA OAuth provisioning chain, test_workflow_handler.py worker_isolated quarantine. The 4 modified test files are pure unit tests for automation domain (pipeline conversion, template discovery, integration wiring, subtask waiter) — not in any frozen surface. New conftest.py creation is additive infrastructure with no impact on production paths or quarantine policy.

**Changes**:

#### CHANGE-001 — create tests/unit/automation/conftest.py with canonical MockPageIterator and consolidate 4 byte-identical bespoke definitions
- **Files**: tests/unit/automation/conftest.py, tests/unit/automation/test_waiter.py, tests/unit/automation/test_templates.py, tests/unit/automation/test_integration.py, tests/unit/automation/test_pipeline.py
- **Edit**: 1) CREATE tests/unit/automation/conftest.py with module-level `class MockPageIterator` (verbatim copy of the byte-identical class from test_waiter.py:15-22 / test_templates.py:25-33 / test_integration.py:112-119 / test_pipeline.py:81-88: `__init__(self, items: list[Any])` storing self._items; `async def collect(self) -> list[Any]` returning self._items). Include `from __future__ import annotations` and `from typing import Any`. 2) DELETE local `class MockPageIterator` block from each of the 4 test files (test_waiter.py L15-22, test_templates.py L25-33, test_integration.py L112-119, test_pipeline.py L81-88). 3) ADD `from tests.unit.automation.conftest import MockPageIterator` to each of the 4 files in the existing import block (isort-respecting). All 4 classes are verified byte-identical via grep -A 6 inspection — no signature change, no attribute superset needed.
- **Test**: `uv run pytest tests/unit/automation/test_waiter.py tests/unit/automation/test_templates.py tests/unit/automation/test_integration.py tests/unit/automation/test_pipeline.py -x --no-header -q && test $(uv run pytest tests/unit/automation/test_waiter.py tests/unit/automation/test_templates.py tests/unit/automation/test_integration.py tests/unit/automation/test_pipeline.py --collect-only -q 2>&1 | grep -c '::test_') -ge 131`
- **Commit**: `refactor(tests): consolidate MockPageIterator into automation/conftest.py`
- **Revert**: `git revert HEAD`

### B8 — Schemathesis per-endpoint xfail (operator ratified)

**Rationale**: Blanket xfail at tests/test_openapi_fuzz.py:58 hides 10 conforming endpoints with zero regression coverage. Per-endpoint xfail via pytest_collection_modifyitems hook restores signal and makes violations grep-able. One atomic commit preserves CI semantics.

**Frozen attestation**: tests/test_openapi_fuzz.py NOT in FROZEN list. Last touching commit predates FROZEN PR 69 range. No frozen surface touched: BuildCoordinator, SA OAuth, Retry-After header, A1 contract, require_business_scope, honest_contract, offer-domain non-regression, router mount-order, query engine P1-C-04, HC-7, worker_isolated quarantine. Test function count GUARD-CP-001 preserved 1 to 1. Pytestmark fuzz and xdist_group retained. CI continue-on-error untouched. xfail strict-false semantics preserved per SAFETY.

**Changes**:

#### CHANGE-001 — Replace blanket schemathesis xfail with per-endpoint markers via collection hook
- **Files**: tests/test_openapi_fuzz.py
- **Edit**: Edits to tests/test_openapi_fuzz.py: append docstring para documenting B8 migration; keep S3 triage comment lines 30-57; replace pytestmark lines 58-71 with fuzz and xdist_group markers only dropping blanket xfail; insert KNOWN_VIOLATIONS dict before line 73 with 55 keys (45 violation suffixes plus 10 conforming suffixes); append pytest_collection_modifyitems hook at EOF applying xfail strict-false per dict lookup. Test function count preserved 1 to 1.
- **Test**: `cd /Users/tomtenuta/Code/a8/repos/autom8y-asana && SCHEMATHESIS_MAX_EXAMPLES=10 HYPOTHESIS_PROFILE=ci python -m pytest tests/test_openapi_fuzz.py -o addopts= --tb=no -q --no-header -rXxs`
- **Commit**: `test(fuzz): replace blanket xfail with per-endpoint markers via collection hook`
- **Revert**: `git revert HEAD --no-edit`
