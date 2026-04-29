---
type: handoff
artifact_id: HANDOFF-eunomia-to-hygiene-2026-04-20
schema_version: "1.0"
source_rite: eunomia
target_rite: hygiene
handoff_type: execution
priority: medium
blocking: false
initiative: "Ecosystem env/secret platformization alignment"
created_at: "2026-04-20T00:00:00Z"
status: proposed
handoff_status: pending
session_id: session-20260415-010441-e0231c37
source_artifacts:
  - .a8/autom8y/ecosystem.conf
  - scripts/a8-devenv.sh
  - secretspec.toml
  - .env/defaults
  - .env/local.example
  - src/autom8_asana/metrics/__main__.py
  - scripts/calc_mrr.py
provenance:
  - source: "scripts/a8-devenv.sh:_a8_load_env (lines 310-417)"
    type: code
    grade: strong
  - source: "secretspec.toml (autom8y-asana, autom8y-data, autom8y-ads, autom8y-hermes, autom8y-sms, autom8y-scheduling, autom8y-dev-x)"
    type: code
    grade: strong
  - source: "Observed .env/ layouts across 7 autom8y-* satellite repos"
    type: artifact
    grade: moderate
  - source: ".know/feat/business-metrics.md"
    type: artifact
    grade: moderate
evidence_grade: moderate
tradeoff_points:
  - attribute: "scope_breadth"
    tradeoff: "Fleet-wide rationalization vs single-repo fix"
    rationale: "Fixing autom8y-asana alone would re-create the same friction in autom8y-ads (no .env/ dir), autom8y-scheduling (only .env/local), and others. The friction is a fleet property, not a repo property."
  - attribute: "validation_strictness"
    tradeoff: "secretspec profile split makes some previously-optional vars required for CLI profile"
    rationale: "Current required=false for ASANA_CACHE_S3_BUCKET is a lie for CLI/offline workflows. Making CLI-profile checks strict at startup trades lax documentation for actionable preflight failure."
  - attribute: "migration_cost"
    tradeoff: "Delete scripts/calc_mrr.py vs keep as a boto3-only shim"
    rationale: "The script duplicates `python -m autom8_asana.metrics active_mrr` with inline classification logic. Keeping two paths means divergent section-membership lists must stay synced. Delete is cheaper long-term."
items:
  - id: CFG-001
    summary: "Populate autom8y-asana .env/defaults with ASANA_CACHE_S3_BUCKET and ASANA_CACHE_S3_REGION (Layer 3, non-secret)"
    priority: high
    acceptance_criteria:
      - "`.env/defaults` contains `ASANA_CACHE_S3_BUCKET=autom8-s3` and `ASANA_CACHE_S3_REGION=us-east-1`"
      - "Fresh clone + `direnv allow` yields a shell where `python -m autom8_asana.metrics active_mrr` succeeds without any `export` statements"
      - "Header comment explains Layer 3 precedence and links to scripts/a8-devenv.sh:_a8_load_env"
    estimated_effort: "15 minutes"
  - id: CFG-002
    summary: "Extend autom8y-asana .env/local.example to cover the full CLI/offline surface with a 6-layer precedence header"
    priority: high
    acceptance_criteria:
      - ".env/local.example documents Layers 1-6 in a header comment block"
      - "Placeholders present for ASANA_CACHE_S3_BUCKET, ASANA_CACHE_S3_REGION, ASANA_CACHE_S3_ENDPOINT_URL (LocalStack)"
      - "Header instructs devs to `cp .env/local.example .env/local` and lists which vars override Layer 3 defaults"
    estimated_effort: "20 minutes"
    dependencies: [CFG-001]
  - id: CFG-003
    summary: "Split secretspec.toml into [profiles.default] (lib-mode) and [profiles.cli] (CLI/offline) so required fields reflect real contracts"
    priority: medium
    acceptance_criteria:
      - "[profiles.cli] marks ASANA_CACHE_S3_BUCKET as required=true"
      - "`secretspec check --config secretspec.toml --provider env --profile cli` passes on a shell where CFG-001 is applied"
      - "`secretspec check --profile cli` fails with actionable message when bucket is unset"
      - "Document the profile convention in a new section of secretspec.toml header comment"
    estimated_effort: "45 minutes"
    dependencies: [CFG-001]
  - id: CFG-004
    summary: "Remediate autom8-s3 (legacy) vs autom8y-s3 (current naming) bucket drift"
    priority: medium
    acceptance_criteria:
      - "Decision recorded (ADR or .ledge/decisions/) on canonical bucket name for dev/local"
      - "If autom8-s3 is canonical: note in .env/defaults header. If migration to autom8y-s3 is planned: dated migration note with owner"
      - ".know/architecture.md or .know/conventions.md reflects the canonical name and the legacy alias"
    estimated_effort: "30 minutes investigation + 15 minutes docs"
  - id: CFG-005
    summary: "Fleet-wide .env/ layout audit — satellites have inconsistent coverage of the 6-layer contract"
    priority: medium
    acceptance_criteria:
      - "Audit report in .ledge/reviews/ for each of: autom8y-ads, autom8y-scheduling, autom8y-sms, autom8y-hermes, autom8y-data, autom8y-dev-x, autom8y-asana"
      - "Report identifies: missing .env/ dir, missing .env/defaults, missing .env/local.example, use of deprecated .env/shared.example"
      - "Per-repo remediation tickets created or grouped into a hygiene sprint"
    estimated_effort: "2 hours"
    notes: |
      Observed drift:
      - autom8y-ads: no .env/ directory at all (likely uses different loader path)
      - autom8y-scheduling: only .env/local, no .env/defaults or .example
      - autom8y-sms: uses .env/shared.example (legacy pattern flagged in a8-devenv.sh:397-404 as backward-compat)
      - autom8y-hermes: has defaults + local + local.example (good reference pattern)
      - autom8y-data: has current + defaults + defaults.example + local (most complete)
      - autom8y-dev-x: has current + defaults + local (no .example)
      - autom8y-asana: has defaults (minimal) + local.example (minimal) — the friction origin
  - id: CFG-006
    summary: "Add startup preflight to `python -m autom8_asana.metrics` that surfaces missing CLI-profile vars at the boundary, not on first transport call"
    priority: low
    acceptance_criteria:
      - "metrics/__main__.py runs a lightweight preflight before load_project_dataframe"
      - "Error message on missing bucket points to .env/local.example, .env/defaults, and secretspec.toml with explicit file paths"
      - "Error no longer appears as `No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.` (generic transport error)"
    estimated_effort: "45 minutes"
    dependencies: [CFG-003]
  - id: CFG-007
    summary: "Delete scripts/calc_mrr.py — subsumed by `python -m autom8_asana.metrics active_mrr`"
    priority: low
    acceptance_criteria:
      - "Parity verified: output of `python -m autom8_asana.metrics active_mrr --verbose` matches `python scripts/calc_mrr.py --verbose` within formatting deltas"
      - "calc_mrr.py deleted"
      - "Any README or runbook references replaced with the canonical metrics CLI invocation"
    estimated_effort: "1 hour"
    dependencies: [CFG-001]
  - id: CFG-008
    summary: "Document the 6-layer loader contract in .know/conventions.md or a dedicated .know/env-loader.md"
    priority: low
    acceptance_criteria:
      - "Layer-by-layer table with: layer number, file path, committed/gitignored, encrypted/plain, typical contents"
      - "Cross-link to scripts/a8-devenv.sh:_a8_load_env and secretspec.toml"
      - "Worked example: where does ASANA_CACHE_S3_BUCKET belong, and why"
    estimated_effort: "30 minutes"
    dependencies: [CFG-001, CFG-002, CFG-003]
---

## Context

Friction surfaced during an eunomia session (`session-20260415-010441-e0231c37`, initiative `asana-test-rationalization`): running `python -m autom8_asana.metrics active_mrr` failed with `No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.` after a fresh `direnv allow`. Investigation revealed the friction is not a per-repo bug but a **systemic gap between ecosystem env-loader contract and per-repo populating of that contract**.

This handoff scopes the remediation to hygiene because the root cause is structural drift across the autom8y-* satellite fleet, not a test or pipeline concern (eunomia's domain).

## Root Cause — Three Compounding Drifts

### Drift 1: `.env/` layer coverage is inconsistent across satellites

`scripts/a8-devenv.sh:_a8_load_env` defines a canonical 6-layer loader:

| Layer | Path | Committed? | Encrypted? |
|---|---|---|---|
| 1 | `.a8/{org}/env.defaults` | ✓ | ✗ |
| 2 | `.a8/{org}/secrets.shared` | ✓ | ✓ (dotenvx) |
| 3 | `{repo}/.env/defaults` | ✓ | ✗ |
| 4 | `{repo}/.env/secrets` | ✓ | ✓ (dotenvx) |
| 5 | `{repo}/.env/{env}` | ✗ (gitignored) | ✗ |
| 6 | `.envrc.local` | ✗ | ✗ |

But satellite coverage of Layer 3/5 is uneven: autom8y-ads has no `.env/` at all, autom8y-asana Layer 3 has 1 variable (`ASANA_CW_ENVIRONMENT`), autom8y-sms still ships the deprecated `shared.example` pattern. A developer onboarding to any satellite other than `autom8y-data`/`autom8y-hermes` gets an inconsistent experience.

### Drift 2: secretspec.toml documents surface without enforcing contracts

`secretspec.toml` is documentation-only. `ASANA_CACHE_S3_BUCKET` is marked `required = false`, which is accurate for lib-mode embedding (the SDK can work without cache S3) but wrong for the CLI/offline/metrics workflows. The validator can't catch missing vars before a runtime transport error because there's no profile distinguishing the contracts.

### Drift 3: Bucket naming conflict (`autom8-s3` vs `autom8y-s3`)

The live dev dataframes live in `s3://autom8-s3/dataframes/` (legacy, no `y`). The newer-named bucket `s3://autom8y-s3/` exists and is empty. `docker-compose.override.yml:33` uses `autom8-s3` for LocalStack. No repo file documents which is canonical. A developer who guesses the "org-branded" name gets an empty bucket and silent-no-data rather than an actionable error.

## Package Prioritization

Execute in waves to keep each change reviewable:

**Wave 1 (unblock developers)**: CFG-001, CFG-002
**Wave 2 (make contracts machine-checkable)**: CFG-003, CFG-006
**Wave 3 (rationalize and document)**: CFG-004, CFG-007, CFG-008
**Wave 4 (fleet rollout)**: CFG-005 — scope by per-satellite ticket

Waves 1-3 are self-contained in autom8y-asana. Wave 4 fans out.

## Notes for Hygiene Rite

- **code-smeller**: focus scan on `.env/` completeness vs `a8-devenv.sh` layer contract, `secretspec.toml` profile absence, `scripts/calc_mrr.py` duplication with `metrics/__main__.py`.
- **architect-enforcer**: Wave 2 (CFG-003, CFG-006) is the architectural piece — introducing profile-aware validation at a boundary (CLI entrypoint) changes the shape of the preflight contract. Before/after contracts worth formalizing.
- **janitor**: Waves 1 and 3 are largely mechanical. Wave 1 is two file edits; Wave 3 includes a verified deletion (CFG-007) and documentation work.
- **audit-lead**: verification hinges on the "fresh clone" test — after CFG-001+CFG-002, a clean workspace should run `python -m autom8_asana.metrics active_mrr` green with no manual `export`.

## Non-goals

- Not changing the a8-devenv.sh loader itself (ecosystem-wide change, out of hygiene scope).
- Not migrating live data between buckets (ops/sre concern).
- Not restructuring `.a8/autom8y/` ecosystem-level config (would need its own cross-rite handoff to ecosystem rite).

## Expected Outcomes

- Fresh-clone onboarding for autom8y-asana works zero-touch for non-secret paths.
- `secretspec check --profile cli` is a machine-checkable gate that catches contract gaps before runtime.
- Fleet-wide `.env/` layout consistency assessed (CFG-005); remediation scoped per satellite.
- One canonical metrics CLI path (CFG-007).
- The 6-layer contract is documented where future contributors will read it (CFG-008).

## Response

Hygiene accepts by producing `HANDOFF-RESPONSE-hygiene-to-eunomia-{date}.md` confirming the plan-phase outputs (typically an architect-enforcer refactoring plan covering CFG-003 and CFG-006), or rejects with resubmission guidance.
