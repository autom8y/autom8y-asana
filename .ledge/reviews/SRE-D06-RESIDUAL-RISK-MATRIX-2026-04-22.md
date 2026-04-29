---
type: review
status: proposed
artifact_type: risk-matrix
rite: sre
initiative: service-api-key-retirement-phase-d06
date: 2026-04-22
author: chaos-engineer
input_source: hygiene-rite HANDOFF-RESPONSE §5 (D-06 residual enumeration)
input_file_count: 11
service_group_count: 6
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-ref cap MODERATE per self-ref-evidence-grade-rule (in-rite classification
  without external-rite corroboration). Grade upgrades to STRONG on fleet-potnia
  Phase B/C/D routing with concurring external critic (hygiene or 10x-dev).
fan_out_discipline: per-service (6 natural axes); NOT collapsed into single residuals bucket
anti_theater_check: APPLIED — sms-performance-report + calendly-intake recommended
                    DEFER-INDEFINITELY per Potnia §7 escape hatch; reasoning in §3.
---

# SRE D-06 Residual SERVICE_API_KEY Risk Matrix

> **Purpose**: Classify 11 residual files grouped across 6 service boundaries; produce per-service blast-radius + failure-mode + retirement-urgency classification; route to fleet-potnia for Phase B/C/D disposition.
> **Input**: hygiene-rite `HANDOFF-RESPONSE §5 D-06` enumeration, evidence of file-level SERVICE_API_KEY references confirmed via `grep -n "SERVICE_API_KEY\|service_api_key"` 2026-04-22.
> **Output**: §1 executive summary → §2 classification table → §3 per-service detail cards → §4 routing recommendation → §5 cross-service dependencies → §6 chaos-experiment stubs for ACTIVE_RISK services.

---

## §1 Executive Summary

Eleven files across six service boundaries reference `SERVICE_API_KEY` in one of three dispositions:

- **ACTIVE_RISK (2 services, 8 files)**: `reconcile-spend` (5 tests + 1 docker-compose) and `auth-justfile` + `auth-scripts` (2 scripts). These still actively USE SERVICE_API_KEY as a functional env-var; they will break when the OAuth migration lands fleet-wide or they will silently mask broken paths under OAuth.
- **PASSIVE_CRUFT (2 services, 2 files)**: `sms-performance-report` conftest (reference-only in a comment on already-migrated code) and `scripts-global` (`validate_credential_vault.py` — misleadingly-named function but content is Asana-key, not SERVICE_API_KEY).
- **REFERENCE_DOC (1 service, 1 file)**: `calendly-intake` fixture (V6 replay fixture — historical defect replay; the string is a DOCSTRING describing a historical ValueError, not live config).

**Routing recommendation top-line**: Two services HIGH-urgency (reconcile-spend + auth-{justfile,scripts}) → **Phase C operationalize**. Three LOW/DEFER (sms, validate-vault, calendly) → **Phase D catch-all or defer-indefinitely**. Anti-theater check fires on sms + calendly: DEFER-INDEFINITELY per Potnia §7.

**Cross-service dependency call-out**: `provision_iris_service_account.py` at auth-scripts still prints "SERVICE_API_KEY stored at SSM {path}" although the stored value is `client_secret`. This is a **semantic-leakage bug** in messaging, not functional risk. Flag for auth-scripts group.

---

## §2 Per-Service Classification Table (6 rows × 4 axis columns)

```
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| Service boundary               | Blast-radius  | Failure-mode        | Retirement urgency  | Effort     | Files |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| 1. reconcile-spend             | test-only +   | ACTIVE_RISK         | HIGH                | M (4-6h)   | 6     |
|                                | dev-only      |                     | (block release      |            |       |
|                                |               |                     |  if OAuth lands)    |            |       |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| 2. calendly-intake             | test-only     | REFERENCE_DOC       | DEFER INDEFINITELY  | XS (0h)    | 1     |
|                                | (fixture      | (V6-replay          | (historical         | if defer;  |       |
|                                |  docstring)   |  fixture docstring) |  docstring, not     | S (1h)     |       |
|                                |               |                     |  code)              | if rewrite |       |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| 3. sms-performance-report      | test-only     | PASSIVE_CRUFT       | DEFER INDEFINITELY  | XS (0h)    | 1     |
|                                |               | (comment on         | (misleading grep    | if defer;  |       |
|                                |               |  already-migrated   |  match; code is     | S (15min)  |       |
|                                |               |  code)              |  already clean)     | if strip   |       |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| 4. auth-justfile               | CI-only +     | ACTIVE_RISK         | HIGH                | S (1-2h)   | 1     |
|                                | dev-only      | (validation recipe  | (dev-env gate still |            |       |
|                                |               |  still gates on     |  breaks on unset    |            |       |
|                                |               |  SERVICE_API_KEY)   |  SERVICE_API_KEY    |            |       |
|                                |               |                     |  post-OAuth)        |            |       |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| 5. auth-scripts                | prod-adjacent | ACTIVE_RISK         | MEDIUM              | S (1-2h)   | 1     |
|  (provision_iris_service_      | (SSM path +   | (semantic-leakage   | (next sprint;       |            |       |
|   account.py)                  |  script       |  in messaging +     |  functional         |            |       |
|                                |  output)      |  SSM-path naming)   |  migration done,    |            |       |
|                                |               |                     |  just cleanup)      |            |       |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
| 6. scripts-global              | CI-only       | PASSIVE_CRUFT       | LOW                 | S (30min)  | 1     |
|  (validate_credential_vault.py)| (e2e          | (function named     | (Phase D rename     |            |       |
|                                |  validation)  |  get_service_api_   |  for consistency)   |            |       |
|                                |               |  key, but reads     |                     |            |       |
|                                |               |  ASANA_CREDENTIAL_  |                     |            |       |
|                                |               |  KEY — naming       |                     |            |       |
|                                |               |  drift only)        |                     |            |       |
+--------------------------------+---------------+---------------------+---------------------+------------+-------+
```

Totals: 2 HIGH, 1 MEDIUM, 1 LOW, 2 DEFER-INDEFINITELY.

---

## §3 Per-Service Detail Cards

### §3.1 reconcile-spend — **ACTIVE_RISK | HIGH | M (4-6h)**

**Files (6)**:
- `services/reconcile-spend/tests/test_instrumentation.py` (2 sites: lines 160, 632)
- `services/reconcile-spend/tests/test_handler.py` (1 site: line 34)
- `services/reconcile-spend/tests/test_defect_remediation.py` (1 site: line 31)
- `services/reconcile-spend/tests/test_data_service_circuit_breaker.py` (1 site: line 30)
- `services/reconcile-spend/tests/test_config.py` (4 sites: lines 52, 65, 88, 101)
- `services/reconcile-spend/docker-compose.override.yml` (1 site: line 25 — `SERVICE_API_KEY: sk_local_test_key_for_reconcile_spend`)

**Why ACTIVE_RISK**: The test files are not just referring to SERVICE_API_KEY in comments — they are actively calling `monkeypatch.setenv("SERVICE_API_KEY", "test_key")` inside test-setup blocks for `reconcile_spend.config.Settings()` instantiation. If the fleet SERVICE_API_KEY retirement (ADR-0001 at autom8y-core, 2026-04-21) propagates and the reconcile-spend `Settings()` field is removed or renamed, ALL nine test-setup sites break simultaneously. The docker-compose override is the local-dev counterpart — if a developer pulls, the lambda container starts with SERVICE_API_KEY but the code no longer reads it, producing silent test-passes with functional drift.

**Why HIGH urgency**: reconcile-spend is a production Lambda with a reconciliation-critical code path (overbilled/underbilled detection). OAuth migration cannot land across the fleet while reconcile-spend `Settings()` still declares a `service_api_key` field or the circuit-breaker test fixture is SERVICE_API_KEY-pinned. This directly blocks any Phase-B/C-OAuth-propagation sprint.

**Estimated effort M (4-6h)**: Nine test setenv sites + 1 docker-compose override + `reconcile_spend.config.Settings()` field migration + CI run to verify. Conventional SDK migration pattern; no exotic failure modes expected if migrator uses `AUTOM8Y_DATA_SERVICE_CLIENT_ID/SECRET` substitution (per project_service_api_key_retirement.md ADR-0001). The 4-6h range accounts for the 9 test fixture rewrites being mechanical (sed-pattern), but each one must be verified against `Settings()` alias-choices to ensure the test still exercises the intended circuit-breaker semantic.

**Chaos-experiment stub**: See §6.1.

---

### §3.2 calendly-intake — **REFERENCE_DOC | DEFER INDEFINITELY | XS (0h)**

**Files (1)**:
- `services/calendly-intake/tests/fixtures/bootstrap_parity/fixture_v6_credentials_required.py` (1 site: line 15)

**Why REFERENCE_DOC**: The sole grep match is inside a module docstring describing the V6 historical production failure ("Credentials required: provide client_id+client_secret or service_key. Set SERVICE_API_KEY, or CLIENT_ID+CLIENT_SECRET environment variables"). This is a quoted ValueError message the fixture replays. Removing the string breaks the V6-replay historical context; altering it to pretend SERVICE_API_KEY never existed is **revisionist documentation** and erodes incident-learning.

**Why DEFER INDEFINITELY (Potnia §7 escape hatch)**: This fixture's VALUE is in replaying the historical defect. The SERVICE_API_KEY string is load-bearing FOR THE HISTORICAL CONTEXT, not for current behavior. If SERVICE_API_KEY is retired fleet-wide, this docstring becomes historical archaeology — which is exactly what V6-replay fixtures are for. **Not worth a sprint.**

**Anti-theater check**: The fixture is explicitly a REPLAY of a pre-remediation state. Scrubbing SERVICE_API_KEY here manufactures hygiene work that contradicts the fixture's documented purpose.

**Chaos-engineer ruling**: DEFER INDEFINITELY. Do not route. If fleet-potnia or hygiene disagrees, the only acceptable alternative is to UPDATE the docstring with a post-ADR-0001 footnote ("historical as of REM-006 2026-04-21"), which is XS effort but still not urgent.

---

### §3.3 sms-performance-report — **PASSIVE_CRUFT | DEFER INDEFINITELY | XS (0h)**

**Files (1)**:
- `services/sms-performance-report/tests/conftest.py` (1 site: line 22)

**Why PASSIVE_CRUFT**: The grep match is a COMMENT: `# ServiceAccount credentials post-REM-006 (commit 96aa97ed) -- SERVICE_API_KEY removed.` The code BELOW the comment already uses `SMS_PERFORMANCE_REPORT_CLIENT_ID` / `SMS_PERFORMANCE_REPORT_CLIENT_SECRET`. This conftest has **already been migrated**; the comment is a breadcrumb explaining the migration.

**Why DEFER INDEFINITELY**: The comment is ACCURATE and HELPFUL. It tells a reader "we used to have SERVICE_API_KEY, we removed it in commit 96aa97ed for REM-006". Scrubbing it produces a file that looks untouched by the migration, which is **worse** from a readability standpoint. The grep tool surfaced this file as a false-positive; the hygiene inventory is correct to list it (grep doesn't distinguish comments from code), but the classification is clean.

**Anti-theater check**: Stripping this comment is scope-manufacture. The hygiene inventory's grep is tool-agnostic — it doesn't parse AST. This is the expected false-positive rate of string-based inventory.

**Chaos-engineer ruling**: DEFER INDEFINITELY. Optionally, at next Phase D catch-all sweep, the comment can be tightened from "SERVICE_API_KEY removed" to "SERVICE_API_KEY retired per ADR-0001 2026-04-21" — but this is aesthetic, not functional.

---

### §3.4 auth-justfile — **ACTIVE_RISK | HIGH | S (1-2h)**

**Files (1)**:
- `services/auth/just/auth.just` (6 sites: lines 94, 98, 100, 105, 111, 201)

**Why ACTIVE_RISK**: The `auth-check-key` recipe is a dev-env gate that validates `SERVICE_API_KEY` format (regex `^(a8ak_|a8sa_|sk_(prod|staging|local)_)[A-Za-z0-9_-]+$`). If a developer's .envrc no longer exports SERVICE_API_KEY (because iris/ace provisioning moved to client_id/client_secret), this recipe **fails with exit code 1** and breaks `direnv reload` smoke-testing. The recipe is load-bearing for local dev sanity and the CI/CD dev-env parity check.

**Why HIGH urgency**: Two failure modes:
- (a) Developer pulls latest, runs `just auth-check-key`, gets "SERVICE_API_KEY not set", and spins wheels thinking they have a broken env when the fleet has actually moved on.
- (b) A downstream recipe depending on `auth-check-key` (via `just` recipe composition) inherits the failure, cascading into wider dev-env breakage.

The 6 sites must be replaced with a `auth-check-credentials` recipe validating `AUTOM8Y_DATA_SERVICE_CLIENT_ID` and `AUTOM8Y_DATA_SERVICE_CLIENT_SECRET` presence + format.

**Estimated effort S (1-2h)**: Single-file edit, regex update, smoke-test `direnv reload`, confirm `just auth-check-credentials` passes. Moderate because the regex needs to cover OAuth client-id/client-secret format conventions (which may not be documented yet — potential cross-reference to autom8y-core `.envrc` conventions required).

**Chaos-experiment stub**: See §6.2.

---

### §3.5 auth-scripts (provision_iris_service_account.py) — **ACTIVE_RISK | MEDIUM | S (1-2h)**

**Files (1)**:
- `services/auth/scripts/provision_iris_service_account.py` (1 site: line 291 — `print(f"  SERVICE_API_KEY stored at SSM {SSM_API_KEY_PATH}")`)

**Why ACTIVE_RISK (with nuance)**: The script already migrates the VALUE correctly — it stores the OAuth `client_secret` at the SSM path `/autom8y/platform/iris/service-api-key`. The bug is **semantic leakage in TWO places**:

1. The printed message at line 291 claims "SERVICE_API_KEY stored" but the actual value stored is `client_secret`.
2. The SSM path CONSTANT is literally named `/autom8y/platform/iris/service-api-key` (line 54: `SSM_API_KEY_PATH = "/autom8y/platform/iris/service-api-key"`).

The operator running this script sees "SERVICE_API_KEY stored at SSM /.../iris/service-api-key" and reasonably believes a SERVICE_API_KEY was provisioned. Downstream consumers (autom8y-hermes `.envrc _iris_ssm_fetch`) may have code paths that expect the SSM value to be a SERVICE_API_KEY format, not a client_secret format — this is a **latent bug waiting to surface** when a consumer attempts to use the value as a SERVICE_API_KEY.

**Why MEDIUM urgency (not HIGH)**: The functional migration is DONE — the script writes client_secret, not SERVICE_API_KEY. Only the messaging + SSM-path-naming lies. Actual failure requires a downstream consumer that type-checks the value's format, which has not been observed in the grep-evidence but is latent.

**Estimated effort S (1-2h)**: Rename `SSM_API_KEY_PATH` → `SSM_CLIENT_SECRET_PATH`, update the SSM key path from `/autom8y/platform/iris/service-api-key` → `/autom8y/platform/iris/client-secret` (this is a **PROD SSM write path change** requiring migration: both paths written during transition, old path deprecated after 7-day grace window). Fix print statement. Effort is S because the change is mechanical, but deployment requires coordination (SSM path migration is prod-adjacent).

**Cross-service dependency call-out**: autom8y-hermes `.envrc` at line 295 references `_iris_ssm_fetch` — verify whether this function reads the old or new SSM path before migration.

---

### §3.6 scripts-global (validate_credential_vault.py) — **PASSIVE_CRUFT | LOW | S (30min)**

**Files (1)**:
- `scripts/validate_credential_vault.py` (2 sites: function name `get_service_api_key()` lines 57, 96)

**Why PASSIVE_CRUFT**: The function named `get_service_api_key()` actually reads from `os.environ.get("ASANA_CREDENTIAL_KEY")` (line 60) with fallback to `just secret-asana-key`. The function body handles the **Asana API key**, NOT a SERVICE_API_KEY. The naming is misleading — it's a symbol-level leakage of the legacy SERVICE_API_KEY term into a function that has nothing to do with the retired credential.

**Why LOW urgency**: No functional risk — the function works correctly. The defect is purely onomastic: a grep for `SERVICE_API_KEY` surfaces this file as a residual, but the actual content is Asana-credential-vault validation. No downstream code is confused because the function body clearly reads ASANA_CREDENTIAL_KEY.

**Estimated effort S (30min)**: Rename `get_service_api_key()` → `get_asana_credential_key()`. Update the 1 call-site at line 96. Update the RuntimeError message at line 82-83 to say "Asana credential key" instead of "service API key". Single-file edit, no cross-service impact.

**Chaos-engineer ruling**: LOW urgency. Route to Phase D catch-all (batch with other cosmetic renames). Do NOT block the next release on this.

---

## §4 Routing Recommendation for Fleet-Potnia

```
+--------------------------------+---------------------+--------------------------------+
| Service group                  | Recommended phase   | Rationale                      |
+--------------------------------+---------------------+--------------------------------+
| reconcile-spend (6 files)      | Phase C             | Blocks OAuth propagation       |
|                                | operationalize      | across production Lambdas.     |
|                                |                     | HIGH urgency.                  |
+--------------------------------+---------------------+--------------------------------+
| auth-justfile (1 file)         | Phase C             | Blocks dev-env parity smoke    |
|                                | operationalize      | test. HIGH urgency.            |
+--------------------------------+---------------------+--------------------------------+
| auth-scripts/provision_iris    | Phase C             | Semantic-leakage + latent SSM  |
|  (1 file)                      | (bundled with       | path naming defect. MEDIUM     |
|                                |  auth-justfile)     | urgency; bundle with §3.4 to   |
|                                |                     | land auth-rite work in one PR. |
+--------------------------------+---------------------+--------------------------------+
| scripts-global/validate_       | Phase D             | Cosmetic rename. LOW urgency.  |
|  credential_vault (1 file)     | catch-all           | Batch with other renames.      |
+--------------------------------+---------------------+--------------------------------+
| calendly-intake (1 file)       | DEFER INDEFINITELY  | Historical V6-replay docstring.|
|                                |                     | Scrubbing is revisionist.      |
+--------------------------------+---------------------+--------------------------------+
| sms-performance-report         | DEFER INDEFINITELY  | Breadcrumb comment on already- |
|  (1 file)                      |                     | migrated code. Grep            |
|                                |                     | false-positive.                |
+--------------------------------+---------------------+--------------------------------+
```

**Summary**: 2 services → Phase C (HIGH), 1 service → Phase C bundled (MEDIUM), 1 service → Phase D (LOW), 2 services → DEFER INDEFINITELY.

**Phase-C bundle proposal**: A single PR titled `chore(d06): retire residual SERVICE_API_KEY surfaces — reconcile-spend + auth` containing:
- 9 reconcile-spend test fixture migrations + 1 docker-compose override
- auth-justfile `auth-check-credentials` recipe replacement
- auth-scripts provision_iris messaging + SSM-path rename (with 7-day dual-write transition)

Total: ~10 file edits + 1 production SSM path migration, estimated 7-10 hours.

**Phase-D catch-all**: 1-line function rename at `scripts/validate_credential_vault.py`. Batch with unrelated Phase-D renames.

**DEFER rationale (Potnia §7 anti-theater)**: 2 of 6 services (sms + calendly) have grep-surfaced residuals that are either breadcrumb comments or historical-replay docstrings. Neither has functional risk. Manufacturing sprint work to scrub these comments would be **ceremonial hygiene theater** — it preserves appearance-of-thoroughness at the cost of erasing useful historical context. Chaos-engineer explicitly exercises the Potnia §7 escape hatch: DEFER INDEFINITELY.

---

## §5 Cross-Service Dependency Call-Outs

### §5.1 auth-scripts ↔ autom8y-hermes SSM consumer (MEDIUM risk)

The `provision_iris_service_account.py` writes to SSM path `/autom8y/platform/iris/service-api-key`. The script preamble (line 294) mentions "autom8y-hermes .envrc will auto-fetch via _iris_ssm_fetch on next direnv reload." Before renaming the SSM path (§3.5), verify `_iris_ssm_fetch` in autom8y-hermes reads the path correctly and plan a **dual-write transition** (old + new path both written for 7 days, old path deletion after consumer migration verified).

**Pre-flight check for fleet-potnia**: Before approving Phase C auth-scripts work, a 10-minute grep across autom8y-hermes for `/autom8y/platform/iris/service-api-key` is required. If the reference exists, it must be updated in lockstep.

### §5.2 reconcile-spend docker-compose ↔ auth-justfile dev-env (LOW risk)

Both reconcile-spend `docker-compose.override.yml` (§3.1) and auth-justfile `auth-check-key` (§3.4) assume SERVICE_API_KEY exists in the local dev environment. If a developer picks up auth-justfile fix first (and migrates local env to OAuth vars), reconcile-spend local lambda will still start with the hardcoded `sk_local_test_key_for_reconcile_spend` — **no functional coupling**, but the two fixes should land in one PR to avoid a window where dev-env is half-migrated.

Recommendation: Bundle reconcile-spend + auth-justfile in the same Phase C PR (per §4 Phase-C bundle proposal).

### §5.3 auth-scripts printed-message ↔ operator mental model (MEDIUM risk)

An operator running `python scripts/provision_iris_service_account.py` today sees "SERVICE_API_KEY stored at SSM {path}". The operator may then attempt to consume this value as if it were a SERVICE_API_KEY (e.g., setting it in an .envrc as `SERVICE_API_KEY=$(aws ssm get-parameter ...)`). This would **silently produce a broken OAuth flow** because the value is a client_secret, not a SERVICE_API_KEY.

**Mitigation**: The §3.5 fix explicitly updates the printed message. Priority MEDIUM — latent operator-confusion bug, not an active production incident.

---

## §6 Chaos-Experiment Stubs for ACTIVE_RISK Services

### §6.1 reconcile-spend — SERVICE_API_KEY-to-OAuth migration resilience experiment

**Hypothesis**: When reconcile-spend `Settings()` is migrated from `service_api_key` to `client_id`/`client_secret`, the 9 test fixtures currently using `monkeypatch.setenv("SERVICE_API_KEY", "test_key")` update in lockstep, OR the test suite fails loudly at fixture-load time (not at silent runtime).

**Injected failure**: Remove `service_api_key` field from `reconcile_spend.config.Settings` in a feature branch WITHOUT updating test fixtures. Observe:
- Expected: 9 test failures at fixture-load, each pointing to the unmigrated setenv site.
- Observed-if-fragile: Tests pass with a silent fallback (e.g., if pydantic swallows the unknown env var) — indicates OAuth migration will SILENTLY break reconcile-spend production lambda without test-level detection.

**Blast radius**: Feature-branch-only; no production impact. Experiment aborts if main-branch CI accidentally picks up the branch state.
**Abort criteria**: Main CI green state changes within experiment window → abort + revert.
**Success**: Loud failure at fixture-load. Upgrade confidence that §3.1 test-migration is mechanical.
**Failure**: Silent test-pass. Escalate: reconcile-spend Settings is too permissive in alias resolution — requires architect-enforcer intervention before OAuth migration proceeds.

### §6.2 auth-justfile — dev-env parity experiment

**Hypothesis**: When `SERVICE_API_KEY` is unset (simulating post-OAuth-migration developer env), `just auth-check-key` fails with exit code 1 AND no downstream recipe cascades into a harder-to-diagnose failure.

**Injected failure**: `unset SERVICE_API_KEY; just auth-check-key` on a dev machine. Measure:
- Expected: Fast exit-1 with the authored error message "SERVICE_API_KEY not set. Load it via: direnv reload (fetches from SSM)".
- Observed-if-fragile: Any downstream just-recipe that CALLS auth-check-key and doesn't handle the exit-1 cleanly. Grep across `auth.just` for recipes invoking `auth-check-key`.

**Blast radius**: Single dev machine; zero production impact.
**Success**: Clean exit + clear message. Confirms the §3.4 migration can be mechanical (swap regex + rename recipe).
**Failure**: Downstream recipe cascade. Expand §3.4 scope to include recipe-dependency fix.

### §6.3 auth-scripts — dry-run naming-leakage experiment

**Hypothesis**: When `provision_iris_service_account.py --dry-run` is invoked by an operator unfamiliar with REM-006, the printed output ("SERVICE_API_KEY stored at SSM {path}") does NOT mislead the operator into treating the stored value as a SERVICE_API_KEY.

**Injected experiment (human-factors, not fault-injection)**: Present the dry-run output to a fresh operator (or CC instance with no prior REM-006 context) and ask "what credential is stored at that SSM path?" Expected answer after §3.5 fix: "client_secret". Observed pre-fix: "SERVICE_API_KEY" (the printed word).

**Blast radius**: Dry-run only; zero production impact.
**Success**: Post-fix output correctly identifies the stored value as client_secret.
**Failure**: Operator still mistakes the value → expand §3.5 scope to include autom8y-hermes `.envrc _iris_ssm_fetch` rename as well (cross-cutting rename).

---

## §7 Evidence & Reproducibility

```
# Reproduction: grep-confirm all 11 files
$ cd /Users/tomtenuta/Code/a8/repos/autom8y
$ grep -n -i 'SERVICE_API_KEY\|service_api_key' \
    services/reconcile-spend/tests/test_instrumentation.py \
    services/reconcile-spend/tests/test_handler.py \
    services/reconcile-spend/tests/test_defect_remediation.py \
    services/reconcile-spend/tests/test_data_service_circuit_breaker.py \
    services/reconcile-spend/tests/test_config.py \
    services/reconcile-spend/docker-compose.override.yml \
    services/calendly-intake/tests/fixtures/bootstrap_parity/fixture_v6_credentials_required.py \
    services/sms-performance-report/tests/conftest.py \
    services/auth/just/auth.just \
    services/auth/scripts/provision_iris_service_account.py \
    scripts/validate_credential_vault.py

# Per-file site counts
reconcile-spend/test_instrumentation.py:         2
reconcile-spend/test_handler.py:                 1
reconcile-spend/test_defect_remediation.py:      1
reconcile-spend/test_data_service_circuit_breaker.py: 1
reconcile-spend/test_config.py:                  4
reconcile-spend/docker-compose.override.yml:     1 (functional env-var)
calendly-intake/fixture_v6_credentials_required.py:  1 (docstring only)
sms-performance-report/tests/conftest.py:        1 (comment only; code migrated)
auth/just/auth.just:                             6 (all inside auth-check-key recipe + help)
auth/scripts/provision_iris_service_account.py:  1 (print statement only; SSM path const separate)
scripts/validate_credential_vault.py:            2 (function name only; reads ASANA_CREDENTIAL_KEY)
TOTAL:                                          21 sites across 11 files
```

---

## §8 Evidence-Grade Self-Audit

Per self-ref-evidence-grade-rule, this matrix caps at **MODERATE** until external corroboration lands. Corroboration paths:
1. Fleet-potnia accepts routing recommendation → MODERATE → STRONG on route-acceptance.
2. Hygiene-rite external critic concurs on DEFER-INDEFINITELY classifications → MODERATE → STRONG on hygiene-rite sign-off.
3. 10x-dev implements Phase-C bundle and tests pass → MODERATE → STRONG on implementation validation.

Chaos-engineer does NOT self-upgrade to STRONG without one of these three paths clearing.

---

**End D-06 residual risk matrix. Load-bearing for fleet-potnia Phase B/C/D routing at next CC restart.**
