---
title: "Sprint 5 Probe A — Env Surface Discovery (0474a60c)"
type: review
artifact_type: review
review_subtype: env-surface-probe
artifact_id: sprint5-env-surface-discovery-2026-04-21
schema_version: "1.0"
status: proposed
owner_rite: 10x-dev
owner_agent: principal-engineer
date: "2026-04-21"
rite: 10x-dev (principal-engineer proxy)
initiative: "total-fleet-env-convergance"
sprint: "S16 Phase 3A (Probe A)"
workstream: WS-6
potnia_checkpoint: PT-16
session_parent: session-20260421-020948-2cae9b82
sprint_parent: sprint-20260421-total-fleet-env-convergance-sprint-a
consumes:
  - .ledge/specs/TDD-sprint5-post-deploy-adversarial-2026-04-21.md
  - .ledge/specs/PRD-sprint5-post-deploy-adversarial-2026-04-21.md
consumes_tdd: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-sprint5-post-deploy-adversarial-2026-04-21.md
target_commit: 0474a60c
target_commit_date: 2026-04-20T21:06+02:00
repo: autom8y-asana
probe_type: env_surface_discovery_v1
evidence_grade: "[MODERATE]"
---

# Sprint 5 Probe A — Env Surface Discovery (commit 0474a60c)

## §1 Probe Overview

- **Target commit**: `0474a60c` (WS-B1 canonical error envelope + WS-B2 security headers convergence)
- **Target files (in-scope)**:
  - `src/autom8_asana/api/errors.py`
  - `src/autom8_asana/api/main.py`
  - `src/autom8_asana/api/routes/webhooks.py`
- **Secondary audit files**: `pyproject.toml`, `secretspec.toml`
- **Methodology**: TDD §3 Steps A.1–A.6 executed verbatim
- **Execution mode**: Read-only grep sweep; zero code/config/branch/commit mutations

## §2 Step A.1 — Commit Diff Capture

- Command executed: `git show 0474a60c -- 'src/autom8_asana/api/errors.py' 'src/autom8_asana/api/main.py' 'src/autom8_asana/api/routes/webhooks.py' 'pyproject.toml' 'secretspec.toml'`
- Diff byte size: **19,169 bytes**
- Files present in diff (from `git show --stat 0474a60c`):
  - `CHANGELOG.md` (documentation — out of src/ scope)
  - `pyproject.toml` (autom8y-api-schemas pin bump 1.6 → 1.9; version 1.1.0 → 1.2.0; editable path source switch)
  - `src/autom8_asana/api/errors.py` (+48 lines — fleet_error_handler added)
  - `src/autom8_asana/api/main.py` (+33/-some — register_validation_handler service_code_prefix + security middleware install)
  - `src/autom8_asana/api/routes/webhooks.py` (+161/- lines — webhook ingress FleetError subclass migration)
  - `tests/integration/api/test_envelope_convergence.py` (new test file — out of src/ scope)
  - `tests/unit/api/routes/test_webhooks.py` (updated — out of src/ scope)
  - `tests/unit/api/test_error_helpers.py` (updated — out of src/ scope)
  - `tests/unit/api/test_tasks.py` (updated — out of src/ scope)
  - `uv.lock` (dependency lock — out of src/ scope)
- `secretspec.toml` NOT modified by this commit (0 bytes in `git show 0474a60c -- secretspec.toml`)

## §3 Step A.2 — Python env-var patterns (PA1-PA5)

All 5 patterns applied via Grep tool against the 3 in-scope src files. No scope expansion beyond the 3 files.

### PA1 — `os.environ[` OR `os.getenv(`
- errors.py: 0 matches
- main.py: 0 matches
- webhooks.py: 0 matches
- **Total: 0**

### PA2 — `settings.[a-z_]+` (Pydantic Settings access)
- errors.py: 0 matches
- main.py: 2 matches
  - L344: `if settings.cors_origins_list:`
  - L346: `allow_origins=settings.cors_origins_list,`
- webhooks.py: 1 match
  - L240: `expected_token = settings.webhook.inbound_token`
- **Total: 3** — pre-existing settings surface (see §6 Delta Analysis)

### PA3 — ALL_CAPS env-var identifier namespaces `(AUTOM8Y_|SERVICE_|AWS_|SLACK_|STRIPE_|CALENDLY_|GRAFANA_|AMP_|OTEL_|ASANA_)[A-Z_]+`
- errors.py: 0 matches
- main.py: 1 match
  - L545: `" ASANA_WEBHOOK_INBOUND_TOKEN."` (error-message embedded identifier in existing code path)
- webhooks.py: 2 matches
  - L75: `` ``ASANA_WEBHOOK_INBOUND_TOKEN``. `` (docstring)
  - L416: `` ``ASANA_WEBHOOK_INBOUND_TOKEN``. Requests without a valid token receive `` (docstring)
- **Total: 3** — all references to the pre-existing `ASANA_WEBHOOK_INBOUND_TOKEN` identifier (see §6 Delta Analysis)

### PA4 — Env-var suffix conventions `(_API_KEY|_TOKEN|_URL|_SECRET|_PASSWORD|_HOST|_PORT|_ARN|_CLIENT_ID|_CLIENT_SECRET)`
- errors.py: 0 matches
- main.py: 1 match (subsumed by PA3 match at L545)
- webhooks.py: 3 matches (subsumes PA3 matches + L55 legacy `MISSING_TOKEN`/`INVALID_TOKEN` docstring reference)
- **Total: 4** — no new suffix identifiers introduced

### PA5 — R-0/R-1 rotation pattern `[A-Z_]+_(R0|R1)`
- errors.py: 0 matches
- main.py: 0 matches
- webhooks.py: 0 matches
- **Total: 0**

## §4 Step A.3 — Secretspec delta

- `git show 0474a60c -- secretspec.toml`: 0 bytes (empty diff output)
- **`secretspec_modified_by_commit: false`** — commit did not touch secretspec.toml
- No new `[profiles.*]` keys introduced; delta analysis n/a

## §5 Step A.4 — Service entry-point discovery (SA1-SA6)

All 6 patterns applied via Grep tool against the 3 in-scope src files; `git show --stat 0474a60c` confirmed no NEW router files introduced.

### SA1 — `router.(get|post|put|delete|patch|options)(`
- errors.py: 0 matches
- main.py: 0 matches
- webhooks.py: 1 match
  - L392: `@router.post(` — pre-existing decorator (verified via `git show 0474a60c^:src/autom8_asana/api/routes/webhooks.py` at L304)
- **Total: 1 pre-existing**

### SA2 — `@app.(get|post|put|delete|patch|options)`
- errors.py: 0 matches
- main.py: 0 matches
- webhooks.py: 0 matches
- **Total: 0**

### SA3 — `APIRouter(`
- errors.py: 0 matches
- main.py: 0 matches
- webhooks.py: 1 match
  - L126: `router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])` — pre-existing (verified at L39 of pre-commit file)
- **Total: 1 pre-existing**

### SA4 — `add_api_route(`
- All in-scope files: 0 matches
- **Total: 0**

### SA5 — `def lambda_handler(`
- All in-scope files: 0 matches
- **Total: 0**

### SA6 — `register_[a-z_]+(.*app.*)`
- errors.py: 1 match
  - L704: `def register_exception_handlers(app: FastAPI) -> None:` — function DEFINITION (not a call); existed pre-commit (verified at L162 of pre-commit file)
- main.py: 3 matches
  - L447: `register_exception_handlers(app)` — pre-existing call (L179 of pre-commit file)
  - L457: `register_validation_handler(app, service_code_prefix="ASANA")` — **CONFIGURATION-ARGUMENT CHANGE ONLY** on pre-existing call; pre-commit form was `register_validation_handler(app)` at L191
  - L472: `# More specific handlers registered by register_exception_handlers(app)` — comment (excluded as comment)
- webhooks.py: 0 matches
- **Total: 4 pre-existing (1 comment); no new entry points**

**Classification per TDD §3.8**: `register_validation_handler(app, service_code_prefix="ASANA")` is a handler CONFIGURATION call on an existing app — NOT a new service entry point. Excluded from `new_services` with rationale recorded inline.

**`git show --stat 0474a60c`**: No new router files created. All 3 src files existed pre-commit and were modified in place. No new Lambda handlers introduced.

## §6 Step A.5 — Secretspec.toml presence audit

- `test -f /Users/tomtenuta/Code/a8/repos/autom8y-asana/secretspec.toml`: **EXISTS**
- Commit did not modify this file (see §4)
- Verdict: `secretspec_exists_in_repo: true`; pre/post-commit delta is empty; no action required.

## §7 Delta Analysis — "New env key?" test

Every PA2/PA3/PA4 match was verified against pre-commit source:
- `settings.cors_origins_list` (main.py L344, L346) — present in pre-commit main.py at L344 identically
- `settings.webhook.inbound_token` (webhooks.py L240) — present in pre-commit webhooks.py at L144 identically
- `ASANA_WEBHOOK_INBOUND_TOKEN` identifier (main.py L545; webhooks.py L75, L416) — identifier present in pre-commit webhooks.py at L328 (docstring carried over)

**Net new env keys introduced by 0474a60c: 0**
**Net new services introduced by 0474a60c: 0**

The commit's nature (WS-B1 + WS-B2 envelope/header convergence) is consistent with this finding: the scope is HANDLER REGISTRATION and MIDDLEWARE INSTALL, not env-surface or new-service surface expansion.

## §8 Hermes-relevance assessment (AP-G1 fire-condition)

Greps for `IRIS_|hermes|iris_ssm|platform/iris` across the 3 in-scope files (case-insensitive): **0 matches**.

No env key found in Probe A scope touches the hermes loader surface. Therefore:
- **AP-G1 fire-condition: NOT FIRED**
- S9 (hermes ADR Option 1 sanction-variance) requires no re-ratification addendum based on this probe's surface.
- `hermes_relevant_env_keys_found: 0`

Caveat: This assessment is bounded to the 3 touched src files per TDD §3 scope-lock. The commit's middleware install pulls in `autom8y_api_schemas.middleware` (a cross-repo dependency via editable path switch in pyproject.toml). Deeper hermes-loader reachability analysis is out of Probe A scope and, if needed, belongs to a separate cross-rite probe.

## §9 probe-a-output-v1 (normative YAML)

```yaml
probe_a_output_v1:
  commit: 0474a60c
  files_swept:
    - src/autom8_asana/api/errors.py
    - src/autom8_asana/api/main.py
    - src/autom8_asana/api/routes/webhooks.py
  diff_byte_size: 19169
  patterns_applied:
    PA1_os_environ:
      matches: 0
      samples: []
    PA2_settings_access:
      matches: 3
      samples:
        - {file: src/autom8_asana/api/main.py, line: 344, text: "if settings.cors_origins_list:"}
        - {file: src/autom8_asana/api/main.py, line: 346, text: "allow_origins=settings.cors_origins_list,"}
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 240, text: "expected_token = settings.webhook.inbound_token"}
    PA3_all_caps_identifiers:
      matches: 3
      samples:
        - {file: src/autom8_asana/api/main.py, line: 545, text: "\" ASANA_WEBHOOK_INBOUND_TOKEN.\""}
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 75, text: "``ASANA_WEBHOOK_INBOUND_TOKEN``."}
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 416, text: "``ASANA_WEBHOOK_INBOUND_TOKEN``. Requests without a valid token receive"}
    PA4_suffix_patterns:
      matches: 4
      samples:
        - {file: src/autom8_asana/api/main.py, line: 545, text: "ASANA_WEBHOOK_INBOUND_TOKEN (suffix _TOKEN)"}
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 55, text: "``MISSING_TOKEN`` (no ``?token=``) and ``INVALID_TOKEN`` (docstring legacy refs)"}
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 75, text: "ASANA_WEBHOOK_INBOUND_TOKEN (suffix _TOKEN)"}
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 416, text: "ASANA_WEBHOOK_INBOUND_TOKEN (suffix _TOKEN)"}
    PA5_rotation_pattern:
      matches: 0
      samples: []
    SA1_router_methods:
      matches: 1
      samples:
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 392, text: "@router.post("}
    SA2_app_decorators:
      matches: 0
      samples: []
    SA3_apirouter_decl:
      matches: 1
      samples:
        - {file: src/autom8_asana/api/routes/webhooks.py, line: 126, text: "router = APIRouter(prefix=\"/api/v1/webhooks\", tags=[\"webhooks\"])"}
    SA4_add_api_route:
      matches: 0
      samples: []
    SA5_lambda_handler:
      matches: 0
      samples: []
    SA6_register_funcs:
      matches: 4
      samples:
        - {file: src/autom8_asana/api/errors.py, line: 704, text: "def register_exception_handlers(app: FastAPI) -> None:  (DEFINITION — pre-existing)"}
        - {file: src/autom8_asana/api/main.py, line: 447, text: "register_exception_handlers(app)  (pre-existing call)"}
        - {file: src/autom8_asana/api/main.py, line: 457, text: "register_validation_handler(app, service_code_prefix=\"ASANA\")  (configuration-arg change on pre-existing call; NOT new service)"}
        - {file: src/autom8_asana/api/main.py, line: 472, text: "# More specific handlers registered by register_exception_handlers(app)  (comment)"}
  secretspec_modified_by_commit: false
  secretspec_exists_in_repo: true
  new_env_keys: []
  new_services: []
  verdict: EMPTY_SURFACE
  verdict_rationale: |
    Zero NEW env keys introduced by 0474a60c (PA1=0, PA5=0; PA2/PA3/PA4 matches all verified
    as pre-existing via `git show 0474a60c^:<file>`). Zero NEW service entry points (SA1/SA3
    matches pre-existing; SA6 matches are pre-existing registration points with one
    configuration-argument change — `service_code_prefix="ASANA"` — which is explicitly
    excluded from `new_services` per TDD §3.8). Commit nature (envelope/header convergence)
    matches the empty-surface finding: handler-registration and middleware-install scope,
    not env-surface expansion.
  hermes_relevance_assessment: |
    No IRIS_*, hermes, iris_ssm, or platform/iris references found in the 3 in-scope files
    (case-insensitive sweep, 0 matches). AP-G1 fire-condition NOT FIRED: S9 hermes ADR
    Option 1 sanction-variance requires no re-ratification addendum based on this probe.
    Caveat: middleware install pulls `autom8y_api_schemas.middleware` via editable path
    (pyproject.toml switch); deeper cross-repo hermes-loader reachability is out of
    Probe A scope-lock.
  out_of_scope_flags: []
```

## §10 Verdict resolution (TDD §3.8)

Applying the decision tree:
- `new_env_keys == []` → TRUE
- `new_services == []` → TRUE
- `secretspec_modified_by_commit == false` → TRUE
- **→ Verdict: `EMPTY_SURFACE`**

## §11 Residuals for main-thread

Observations carried forward for Phase 4 synthesis:

1. **Cross-repo middleware coupling**: pyproject.toml delta switches `autom8y-api-schemas` from indexed `>=1.6.0` to editable path source at `../autom8y-api-schemas`. This is a WS-D1/D2-adjacent dependency-topology signal but within Probe A's documented scope for pyproject.toml audit. No action required for this probe; flagged for fleet-coordination visibility.
2. **Docstring-embedded env identifier**: `ASANA_WEBHOOK_INBOUND_TOKEN` appears in docstrings at 3 of the 4 PA3/PA4 match sites. Docstring-only references are not an active env-surface delta but are recorded here for completeness.
3. **Configuration-argument change**: `register_validation_handler(app, service_code_prefix="ASANA")` is a BEHAVIORAL change (emits `ASANA-VAL-001` instead of `FLEET-VAL-001`), NOT a new service entry. This is the proper home for Probe B's `ASANA-VAL-001` endpoint assertion. Flagged here for the qa-adversary Phase 3B artifact cross-reference.
4. **Editable-path dependency**: The `autom8y-api-schemas = { path = "../autom8y-api-schemas", editable = true }` line in pyproject.toml is a development-mode source switch. Out-of-scope for Probe A's env-surface remit; may be a hygiene/build concern to route post-synthesis if not already captured elsewhere.

## §12 Execution hygiene attestation

- Read-only: CONFIRMED (no src edits, no branches, no commits, no pushes)
- Scope: LOCKED to the 3 src files + 2 audit files per TDD §3
- No cross-rite scope-creep executed; residuals FLAGGED per §11
- Scratch file `/tmp/0474a60c-diff.txt` retained ephemerally for probe reference; not committed
- Methodology: TDD §3 Steps A.1–A.6 executed verbatim; no methodology extension or renegotiation

## §13 Evidence grade

`[MODERATE]` — self-ref cap per self-ref-evidence-grade-rule (authored within 10x-dev rite;
principal-engineer proxy). Upgrade path to STRONG requires cross-rite HANDOFF-RESPONSE
corroboration in Phase 4 synthesis or subsequent review-rite pass.
