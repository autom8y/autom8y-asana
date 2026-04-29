---
type: review
review_subtype: smell-inventory
artifact_id: smell-inventory-env-secrets-2026-04-20
schema_version: "1.0"
status: proposed
rite: hygiene
phase: scan
initiative: "Ecosystem env/secret platformization alignment"
created_at: "2026-04-20T00:00:00Z"
source_handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
cfg_items_covered: [CFG-001, CFG-002, CFG-003, CFG-004, CFG-006, CFG-007, CFG-008]
cfg_items_out_of_scope: [CFG-005]
source_artifacts:
  - .env/defaults
  - .env/local.example
  - secretspec.toml
  - src/autom8_asana/metrics/__main__.py
  - scripts/calc_mrr.py
  - docker-compose.override.yml
  - .know/conventions.md
  - scripts/a8-devenv.sh (ecosystem, read-only; verified via worktree copy)
evidence_grade: strong
author: code-smeller
---

# Smell Inventory — Env/Secrets Platformization (autom8y-asana)

## Purpose

Baseline scan of the 7 in-scope CFG items in `HANDOFF-eunomia-to-hygiene-2026-04-20.md`. Each row captures a before-state assertion with `file:line` citations, an expected-after assertion audit-lead can mechanically verify, and a concrete diff-check command. Architect-enforcer consumes this inventory for planning; audit-lead consumes the Before-state Snapshot Manifest as its diff baseline.

**Scope**: autom8y-asana only. Fleet-wide audit (CFG-005) is explicitly deferred per handoff line 167 (Wave 4).

**Classification**: All findings are [TACTICAL] — bounded sprint work editing files in-repo. No structural/architectural findings surfaced at scan time; CFG-003/CFG-006 introduce a new validation contract at the CLI boundary but the change is confined to this repo (architect-enforcer will formalize that contract in the planning phase).

---

## CFG-keyed Findings Table

### CFG-001 — `.env/defaults` omits CLI/offline-profile S3 cache variables

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-001 |
| `smell_category` | CX-Incomplete-Config / AR-Contract-Gap (Layer 3 underpopulated) |
| `before_state` | `.env/defaults` is 3 lines long. Its only non-comment variable is `ASANA_CW_ENVIRONMENT=development` at `.env/defaults:3`. Layer 3 of the `_a8_load_env` 6-layer contract (`scripts/a8-devenv.sh:377-383` per worktree copy) expects project non-secrets for this repo here. `ASANA_CACHE_S3_BUCKET` and `ASANA_CACHE_S3_REGION` are absent — they exist in `docker-compose.override.yml:33` (`autom8-s3`) and `docker-compose.override.yml:35` (`us-east-1`) only, so host-side CLI workflows inherit nothing. Current defaults content byte-for-byte: `# Project non-secrets for autom8y-asana (committed).` / `# Ecosystem defaults loaded from .a8/autom8y/env.defaults (Layer 1).` / `ASANA_CW_ENVIRONMENT=development`. |
| `expected_after_state` | `.env/defaults` contains `ASANA_CACHE_S3_BUCKET=autom8-s3` and `ASANA_CACHE_S3_REGION=us-east-1` as literal assignments. Header comment explains Layer 3 precedence and cross-links `scripts/a8-devenv.sh:_a8_load_env`. Fresh clone + `direnv allow` yields a shell where `python -m autom8_asana.metrics active_mrr` succeeds without any manual `export`. |
| `acceptance_criteria_pointer` | HANDOFF lines 51-55 |
| `severity` | **High** (P2) — blocks fresh-clone onboarding; empirically produces a runtime transport error that the preflight cannot catch. Score band 11-15 per platform heuristic. |
| `audit_diff_command` | `grep -c '^ASANA_CACHE_S3_BUCKET=' .env/defaults` (expect `1`); `grep -c '^ASANA_CACHE_S3_REGION=' .env/defaults` (expect `1`); `( cd "$(mktemp -d)" && git clone <this-repo> repo && cd repo && direnv allow && python -m autom8_asana.metrics active_mrr )` (expect exit 0, no `export` needed). |

### CFG-002 — `.env/local.example` omits the 6-layer precedence header and S3 placeholders

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-002 |
| `smell_category` | NM-Documentation-Drift / PR-Onboarding-Gap |
| `before_state` | `.env/local.example` is 11 lines (`.env/local.example:1-11`). It documents only `ASANA_PAT` (`.env/local.example:10`) and `ASANA_WORKSPACE_GID` (`.env/local.example:11`). There is no header block describing Layers 1-6, no mention of `ASANA_CACHE_S3_*` placeholders, and no guidance on which vars override Layer 3. Byte-level content captured in Snapshot Manifest below. |
| `expected_after_state` | Header comment block enumerates all 6 layers with path, committed/gitignored, encrypted/plain, per the `_a8_load_env` contract. Placeholders present for `ASANA_CACHE_S3_BUCKET`, `ASANA_CACHE_S3_REGION`, `ASANA_CACHE_S3_ENDPOINT_URL` (LocalStack). Instructions explicitly direct `cp .env/local.example .env/local` and list which vars override Layer 3 defaults. |
| `acceptance_criteria_pointer` | HANDOFF lines 59-63 |
| `severity` | **Medium** (P3) — documentation completeness issue; does not cause runtime failures but leaves devs without a map. Score band 6-10. |
| `audit_diff_command` | `grep -cE '^# (Layer [1-6]\|.env/(defaults\|secrets\|local)\|.envrc.local)' .env/local.example` (expect ≥6); `grep -cE '^# ?ASANA_CACHE_S3_(BUCKET\|REGION\|ENDPOINT_URL)' .env/local.example` (expect ≥3). |

### CFG-003 — `secretspec.toml` has no CLI profile; `required=false` is a lie for CLI surface

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-003 |
| `smell_category` | AR-Contract-Gap / CX-Validation-Absent |
| `before_state` | `secretspec.toml:14` has only `[profiles.default]`. No `[profiles.cli]` section exists anywhere in the file (verified: file is 138 lines total; all variables sit under the single default profile from line 14 onward). `ASANA_CACHE_S3_BUCKET` is declared at `secretspec.toml:59` with `required = false`, which is correct for lib-mode but wrong for CLI/offline workflows (handoff lines 152-154). `secretspec check --config secretspec.toml --provider env` cannot differentiate lib-mode and CLI callers, so missing-bucket surfaces only as a runtime transport error at `scripts/calc_mrr.py:132-134` and inside `load_project_dataframe` at `src/autom8_asana/metrics/__main__.py:83`. |
| `expected_after_state` | `secretspec.toml` contains a `[profiles.cli]` section that marks `ASANA_CACHE_S3_BUCKET` with `required = true`. Header comment section documents the profile convention. `secretspec check --config secretspec.toml --provider env --profile cli` passes when CFG-001 is applied and fails with an actionable message (file pointer + the variable name) when the bucket is unset. |
| `acceptance_criteria_pointer` | HANDOFF lines 67-73 |
| `severity` | **High** (P2) — machine-checkable contract gap; current state makes the validator silent where it should be loud. Score band 11-15. Co-occurs with CFG-001 in the same variable (`ASANA_CACHE_S3_BUCKET`), which per `smell-detection` compound-signal guidance elevates attention. |
| `audit_diff_command` | `grep -cE '^\[profiles\.cli\]' secretspec.toml` (expect `1`); `secretspec check --config secretspec.toml --provider env --profile cli` (expect exit 0 when bucket set, non-zero with actionable message when unset). |

### CFG-004 — `autom8-s3` vs `autom8y-s3` bucket-naming drift unresolved in repo docs

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-004 |
| `smell_category` | NM-Naming-Drift / AR-Undocumented-Canonical-Name |
| `before_state` | `docker-compose.override.yml:33` references `ASANA_CACHE_S3_BUCKET: autom8-s3` (legacy name, no `y`). No ADR or `.ledge/decisions/` entry records whether `autom8-s3` or `autom8y-s3` is canonical for dev/local. `.know/conventions.md` (verified via grep) contains no `autom8-s3`, `autom8y-s3`, or S3-bucket-naming entry. `.know/architecture.md` (not audited at byte level here; verify at gate time) similarly has no canonical-name entry per handoff lines 156-158. |
| `expected_after_state` | A decision artifact exists (either `.ledge/decisions/ADR-NNNN-bucket-canonical-name.md` or an equivalent noted location) recording the canonical name. If `autom8-s3` is canonical: note in `.env/defaults` header. If migration to `autom8y-s3` is planned: dated migration note with owner. `.know/architecture.md` or `.know/conventions.md` reflects canonical name and legacy alias. |
| `acceptance_criteria_pointer` | HANDOFF lines 77-82 |
| `severity` | **Medium** (P3) — silent-no-data failure mode (empty `autom8y-s3` bucket) is worse than loud failure, but only trips devs who guess the org-branded name. Score band 6-10. |
| `audit_diff_command` | `ls .ledge/decisions/ \| grep -i 'bucket\|s3-name'` (expect ≥1 match); `grep -l 'autom8-s3\|autom8y-s3' .know/architecture.md .know/conventions.md .env/defaults 2>/dev/null` (expect at least one canonical-name-bearing file); `git log --all --oneline --grep='bucket canonical\|autom8-s3'` (expect commit trail). |

### CFG-006 — `metrics/__main__.py` has no boundary preflight; missing bucket surfaces as generic transport error

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-006 |
| `smell_category` | CX-Error-Localization-Poor / AR-Missing-Boundary-Check |
| `before_state` | `src/autom8_asana/metrics/__main__.py:82-86` wraps `load_project_dataframe(project_gid)` in a `try` that catches `(ValueError, FileNotFoundError)` and prints the exception string to stderr. No preflight runs before line 83. When `ASANA_CACHE_S3_BUCKET` is unset, the error bubbles up from deep inside the transport layer as `No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.` (handoff line 106) — generic, with no file pointer to `.env/local.example`, `.env/defaults`, or `secretspec.toml`. Lines 82-86 literal bytes: `try:` / `    df = load_project_dataframe(project_gid)` / `except (ValueError, FileNotFoundError) as e:` / `    print(f"ERROR: {e}", file=sys.stderr)` / `    sys.exit(1)`. |
| `expected_after_state` | `metrics/__main__.py` runs a lightweight preflight **before** the `load_project_dataframe` call at line 83. Error message on missing bucket names `.env/local.example`, `.env/defaults`, and `secretspec.toml` with explicit file paths. The generic `No S3 bucket configured…` error no longer surfaces from the CLI path. |
| `acceptance_criteria_pointer` | HANDOFF lines 103-107 |
| `severity` | **Medium** (P3) — UX/diagnostic issue, not correctness. Depends on CFG-003 (preflight leverages the new CLI profile). Score band 6-10. |
| `audit_diff_command` | `grep -nE 'preflight\|secretspec\|check_cli_profile' src/autom8_asana/metrics/__main__.py` (expect ≥1 match at a line number less than the current line 83 equivalent); integration test: `unset ASANA_CACHE_S3_BUCKET && python -m autom8_asana.metrics active_mrr 2>&1 \| grep -cE '\.env/(defaults\|local\.example)\|secretspec\.toml'` (expect ≥2 file-path mentions in error output). |

### CFG-007 — `scripts/calc_mrr.py` duplicates inline classification logic subsumed by metrics CLI

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-007 |
| `smell_category` | **DRY-Parallel-Implementation** (primary) + DC-Redundant-Script |
| `before_state` | `scripts/calc_mrr.py` exists, is executable (chmod +x), 196 lines. Inline `OFFER_ACTIVE_SECTIONS` at `scripts/calc_mrr.py:38-60` duplicates the classifier-groups contract maintained canonically inside the SDK (`from autom8_asana.models.business.activity import CLASSIFIERS` per `src/autom8_asana/metrics/__main__.py:19`). Three classification sets re-declared inline: `OFFER_ACTIVE_SECTIONS` (`:38-60`, 21 entries), `OFFER_ACTIVATING_SECTIONS` (`:62-68`, 5 entries), `OFFER_INACTIVE_SECTIONS` (`:70-74`, 3 entries). Comment at `scripts/calc_mrr.py:37` acknowledges: `# Kept inline to avoid importing the full SDK (platform deps not required).` The script duplicates S3 list/load + dedup + aggregation logic already implemented behind `python -m autom8_asana.metrics active_mrr`. |
| `expected_after_state` | Parity verified: `python -m autom8_asana.metrics active_mrr --verbose` output matches `python scripts/calc_mrr.py --verbose` output within formatting deltas. `scripts/calc_mrr.py` deleted. Any README or runbook references replaced with the canonical `python -m autom8_asana.metrics active_mrr` invocation. |
| `acceptance_criteria_pointer` | HANDOFF lines 112-116 |
| `severity` | **Medium** (P3) — DRY violation with known sync hazard; classification list drift is the failure mode. Score band 6-10. Co-occurrence with CFG-001 (both revolve around `ASANA_CACHE_S3_BUCKET` contract ergonomics) adds a compound-signal tick. |
| `audit_diff_command` | `test -f scripts/calc_mrr.py && echo EXISTS \|\| echo DELETED` (expect `DELETED`); `grep -rn 'calc_mrr\.py' README.md docs/ justfile 2>/dev/null` (expect 0 matches or only historical/changelog entries); parity command (pre-delete) `diff <(python -m autom8_asana.metrics active_mrr --verbose) <(python scripts/calc_mrr.py --verbose)` (inspect for non-formatting deltas). |

### CFG-008 — 6-layer loader contract undocumented in `.know/`

| Field | Value |
|-------|-------|
| `cfg_id` | CFG-008 |
| `smell_category` | PR-Knowledge-Gap / NM-Undocumented-Convention |
| `before_state` | `.know/conventions.md` contains **no** coverage of the 6-layer env loader, `.env/` file inventory, or `secretspec.toml` profile convention. Verified via grep (`env\|loader\|layer\|secretspec\|.env/` with `-i`): only matches are unrelated "layer" mentions (`service layer`, `API-layer exceptions`, etc. at lines 49, 70, 107, 112, 161, 170, 242). No file `.know/env-loader.md` exists (confirmed via directory listing). `scripts/a8-devenv.sh` itself is ecosystem-level (not present under `autom8y-asana/scripts/` — verified) and is explicitly out of scope per handoff line 180. |
| `expected_after_state` | A layer-by-layer table documents the 6 layers (layer number, file path, committed/gitignored, encrypted/plain, typical contents) in either `.know/conventions.md` or a new `.know/env-loader.md`. Cross-links to `scripts/a8-devenv.sh:_a8_load_env` (by path reference, not inclusion) and `secretspec.toml`. Worked example: where does `ASANA_CACHE_S3_BUCKET` belong, and why. |
| `acceptance_criteria_pointer` | HANDOFF lines 120-125 |
| `severity` | **Low** (P4) — pure documentation; no runtime impact. Score band 1-5. Depends on CFG-001, CFG-002, CFG-003 (the worked example needs them settled). |
| `audit_diff_command` | `(test -f .know/env-loader.md) \|\| grep -qE '^#+ .*(6-layer\|env loader\|Layer [1-6])' .know/conventions.md && echo DOC_PRESENT \|\| echo DOC_MISSING` (expect `DOC_PRESENT`); `grep -cE 'ASANA_CACHE_S3_BUCKET' .know/env-loader.md .know/conventions.md 2>/dev/null \| awk -F: '{s+=$2} END {print s}'` (expect ≥1 — the worked example). |

---

## Cross-cutting Observations

- **`required=false` pattern is the central lie**: `secretspec.toml:15-138` marks **every** variable `required = false`. That was defensible when only the default profile existed, but it erases the CLI-profile contract and turns `secretspec check` into a glorified `toml lint`. CFG-003 is the keystone of this inventory — CFG-006's preflight relies on a CLI profile existing to check against.
- **Layer 3 (`.env/defaults`) is the sparsest commit-layer in the loader**: with only `ASANA_CW_ENVIRONMENT` present, it under-represents the real contract. Four other loader surfaces (`docker-compose.override.yml:33-50`, `secretspec.toml`, `.env/local.example`, handoff-documented `.a8/autom8y/env.defaults`) each carry parts of the env surface. This distributed-knowledge anti-pattern is the structural reason CFG-001, CFG-002, CFG-004, CFG-008 all exist.
- **CLI vs container vs lib-mode contract triple**: `docker-compose.override.yml:24-50` is the de facto CLI profile (it carries `ASANA_CACHE_S3_BUCKET`, `ASANA_CACHE_S3_REGION`, `ASANA_CACHE_S3_ENDPOINT_URL`). CFG-001 promotes the first two to Layer 3; CFG-002 puts the third (LocalStack endpoint) as a placeholder in `local.example`. Compose file stays as the container-runtime source of truth for the endpoint override.
- **Co-occurrence on `ASANA_CACHE_S3_BUCKET`**: CFG-001, CFG-003, CFG-006, CFG-007 all intersect this single variable. Per CS:SRC-005 Palomba et al. 2018 [STRONG | 0.72 @ 2026-04-01], co-occurrence across multiple smell categories within one locus elevates attention — fix the config, the validator, the preflight, and the duplicate script in that order and the locus is clean.
- **Legacy backward-compat shim at `scripts/a8-devenv.sh:397-404`** (worktree-verified) for `.env/shared` means any fleet-wide migration work (CFG-005, out of scope here) must preserve backward-compat semantics. Not autom8y-asana's problem at this sprint.
- **CFG-007 DRY violation is also a provenance-pattern observation**: three hand-maintained section classification sets inline in a script that imports nothing from the SDK it mirrors is structurally consistent with copy-paste-and-edit workflows [AI:SRC-001 Cotroneo et al. 2025] [STRONG | 0.72 @ 2026-04-01]. Classification-only; authorship-neutral.
- **No security-severity secrets-in-plaintext findings** in the 7 in-scope files. `ASANA_PAT` and `ASANA_WORKSPACE_GID` are correctly placed in `.env/local.example:10-11` as `REPLACE_WITH_…` placeholders, and Layer 4 encrypted-secrets handling is routed through `_a8_source_encrypted` at the ecosystem level (out of scope).

---

## Smell Severity Roll-up

| Severity | Count | CFG IDs |
|----------|-------|---------|
| Critical (P1) | 0 | — |
| High (P2) | 2 | CFG-001, CFG-003 |
| Medium (P3) | 4 | CFG-002, CFG-004, CFG-006, CFG-007 |
| Low (P4) | 1 | CFG-008 |
| **Total** | **7** | |

**Escalation triggers evaluated**:
- **SRE / ops** — CFG-004 bucket-naming drift edges ops territory (live data lives in `s3://autom8-s3/`; `autom8y-s3` is empty). Handoff line 181 explicitly scopes live-data migration **out** of hygiene. No escalation opened by this inventory — the CFG-004 acceptance criteria cover only the documentation/ADR artifact, not any bucket-migration action. Architect-enforcer should note this boundary.
- **Security** — No plaintext-secret leaks, no credential drift. No escalation.
- **Ecosystem rite** — `scripts/a8-devenv.sh` loader changes are non-goal per handoff line 180; `.a8/autom8y/` ecosystem config restructure is non-goal per handoff line 182. No escalation opened.
- **Debt-triage** — No debt re-routing warranted; this inventory already consumes a debt-adjacent handoff.

High-severity findings (CFG-001, CFG-003) are the architect-enforcer's Wave-2 focus per handoff line 165. Audit-lead should treat CFG-001's fresh-clone test (handoff line 176) as the keystone verification.

---

## Known Scope Boundaries

Explicitly **not** inspected by this inventory (per handoff non-goals, lines 178-182, and per Wave-4 deferral on line 167):

1. **Sibling repos**: `autom8y-ads`, `autom8y-scheduling`, `autom8y-sms`, `autom8y-hermes`, `autom8y-data`, `autom8y-dev-x`. CFG-005 catalogs the observed fleet drift across those 7 satellites (handoff lines 91-99) but the CFG-005 work is a separate sprint. This inventory makes no claims about their state and records no before-state snapshots of their files.
2. **`.a8/autom8y/` ecosystem config** (Layer 1 and Layer 2 files — `env.defaults`, `secrets.shared`): non-goal per handoff line 182. Not inspected.
3. **`scripts/a8-devenv.sh` loader itself**: non-goal per handoff line 180. Treated as a fixed contract. The normative 6-layer shape at lines 310-417 was read (via worktree copy at `/Users/tomtenuta/Code/a8/repos/.knossos/worktrees/agent-a3d837ee/scripts/a8-devenv.sh`, since no copy exists under `autom8y-asana/scripts/`) for reference only.
4. **Live data migration** (`s3://autom8-s3/` → `s3://autom8y-s3/`): ops/sre concern per handoff line 181. CFG-004 decides the name in-repo; the migration-if-any is out of hygiene.
5. **`.know/architecture.md`** at byte level: not snapshotted here. CFG-004 acceptance criteria allow either conventions.md or architecture.md; audit-lead will verify at gate time, and either file edited satisfies the criterion.

---

## Before-state Snapshot Manifest

This is the **audit diff baseline**. Audit-lead compares the post-execution repo state against these snapshots.

### `.env/defaults` (3 lines, captured 2026-04-20)

```
# Project non-secrets for autom8y-asana (committed).
# Ecosystem defaults loaded from .a8/autom8y/env.defaults (Layer 1).
ASANA_CW_ENVIRONMENT=development
```

### `.env/local.example` (11 lines, captured 2026-04-20)

```
# Local secrets -- copy to .env/local and fill in real values.
# This file is committed; .env/local is gitignored.
#
# Fetch from AWS:
#   just fetch-secrets
#
# Or manually:
#   aws secretsmanager get-secret-value --secret-id "autom8y/asana/asana-pat" --query SecretString --output text
#   aws secretsmanager get-secret-value --secret-id "autom8y/asana/asana-workspace-gid" --query SecretString --output text
ASANA_PAT=REPLACE_WITH_ACTUAL_ASANA_PAT
ASANA_WORKSPACE_GID=REPLACE_WITH_ACTUAL_WORKSPACE_GID
```

### `secretspec.toml` — `[project]` + `[profiles.default]` header block (lines 1-15, captured 2026-04-20)

```toml
# Secret inventory for autom8y-asana.
# Documents the complete env var surface across all Pydantic Settings subsections.
# Documentation-only: no runtime behavior.
#
# Validate: secretspec check --config secretspec.toml --provider env

[project]
name = "autom8y-asana"
revision = "1.0"

# ---------------------------------------------------------------------------
# Ecosystem identity (Autom8yBaseSettings / SDK)
# ---------------------------------------------------------------------------
[profiles.default]
AUTOM8Y_ENV = { description = "Active deployment environment (local|staging|production|test). Canonical ecosystem var.", required = false, default = "local" }
```

And for CFG-003 verification, the key ASANA_CACHE_S3_BUCKET declaration at line 59:

```toml
ASANA_CACHE_S3_BUCKET = { description = "S3 bucket name for cache storage", required = false }
```

File is 138 lines total; only `[project]` and `[profiles.default]` sections exist — no `[profiles.*]` subsections beyond default.

### `src/autom8_asana/metrics/__main__.py` (114 lines, captured 2026-04-20) — key region lines 80-90

```python
    # Load data
    try:
        df = load_project_dataframe(project_gid)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df)} rows from project {project_gid}")

    # Compute
    result = compute_metric(metric, df, verbose=args.verbose)
```

No preflight exists before line 83. Full file sha snapshot not captured here; audit-lead can derive via `git rev-parse HEAD:src/autom8_asana/metrics/__main__.py` at baseline commit.

### `scripts/calc_mrr.py` — existence and size status (captured 2026-04-20)

```
path: /Users/tomtenuta/Code/a8/repos/autom8y-asana/scripts/calc_mrr.py
status: EXISTS
permissions: -rwxr-xr-x (executable)
size: 6.6k
line_count: 196
inline_classification_blocks: 3 (lines 38-60, 62-68, 70-74)
imports_from_sdk: 0 (explicitly avoided per comment at line 37)
```

Verification command baseline: `test -f scripts/calc_mrr.py && echo EXISTS || echo DELETED` → currently `EXISTS`; expected `DELETED` after CFG-007.

### `docker-compose.override.yml:33` (reference, not edited by this sprint)

```yaml
      ASANA_CACHE_S3_BUCKET: autom8-s3
```

Confirms `autom8-s3` as the legacy/current compose-runtime bucket name. CFG-004 decides whether this remains canonical.

### Baseline commit pointer

Snapshot taken against working-tree state on branch `hygiene/sprint-b-item-9-phonenumbers-declaration` on 2026-04-20. Audit-lead should capture the exact commit SHA at the start of the janitor execution phase and diff against that SHA.

---
