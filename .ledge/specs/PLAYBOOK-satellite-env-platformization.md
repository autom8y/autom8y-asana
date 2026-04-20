---
type: spec
spec_subtype: playbook
id: PLAYBOOK-0001
artifact_id: PLAYBOOK-satellite-env-platformization
schema_version: "1.0"
status: proposed
version: "v2"
revision_spec: REVISION-SPEC-playbook-v2-2026-04-20
lifecycle_status: frozen-for-wave-2-consumption
date: "2026-04-20"
rite: hygiene
initiative: "Fleet env/secret platformization rollout (CFG-005 fanout)"
session_id: session-20260415-010441-e0231c37
author: architect-enforcer (hygiene-asana, RES-003)
consumes:
  - .ledge/reviews/HANDOFF-hygiene-asana-to-hygiene-fleet-2026-04-20.md
  - .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
  - .ledge/reviews/HANDOFF-RESPONSE-hygiene-to-eunomia-2026-04-20.md
source_audits:
  - .ledge/reviews/AUDIT-env-secrets-sprint-A.md
  - .ledge/reviews/AUDIT-env-secrets-sprint-B.md
  - .ledge/reviews/AUDIT-env-secrets-sprint-C.md
  - .ledge/reviews/AUDIT-env-secrets-sprint-C-delta.md
source_artifacts:
  - .ledge/decisions/ADR-env-secret-profile-split.md
  - .ledge/decisions/ADR-bucket-naming.md
  - .ledge/specs/TDD-cli-preflight-contract.md
  - .know/env-loader.md
canonical_loader_reference: "/Users/tomtenuta/Code/a8/scripts/a8-devenv.sh:310-417 (_a8_load_env)"
evidence_grade: strong
supersedes: []
superseded_by: []
revision_protocol: critique-iteration-protocol
---

# Playbook — Satellite Env/Secret Platformization

## A. Preamble

### Purpose

Codify the autom8y-asana Sprint-A / Sprint-B / Sprint-C template so each Wave 1-3 satellite executor can run a full env/secret hygiene sprint without re-deriving any structural decision. This is a **template**, not the spec of a new system: all architectural decisions were already made in autom8y-asana and ratified through four PASS audits. The satellite executor applies the template; they do not relitigate it.

### Evidence basis

Four audits form the PASS chain that grounds this playbook:

| Audit | Scope | Verdict |
|-------|-------|---------|
| `AUDIT-env-secrets-sprint-A.md` | CFG-001 (`.env/defaults` population), CFG-002 (`.env/local.example` 6-layer header) | PASS |
| `AUDIT-env-secrets-sprint-B.md` | CFG-003 (`secretspec.toml` `[profiles.cli]`), CFG-006 (CLI preflight) | PASS |
| `AUDIT-env-secrets-sprint-C.md` | CFG-004 (bucket ADR), CFG-007 (CLI dedup), CFG-008 (`.know/env-loader.md`) | REVISION-REQUIRED (CI-parity test regression) |
| `AUDIT-env-secrets-sprint-C-delta.md` | REMEDIATE commit `7e5b8687` | PASS |

All four are cited verbatim in subsequent sections. The Sprint-C REVISION-REQUIRED cycle is as important as the PASSes: it is the single empirical lesson on test-isolation that informs step 5 of the template sequence.

### Authorship status

**Frozen-for-Wave-1-consumption.** Revisions to this playbook follow the `critique-iteration-protocol`: a satellite sprint that discovers a structural defect in the playbook (e.g., a step is infeasible for its state) must ESCALATE rather than silently diverge. The playbook author (hygiene-asana architect-enforcer) owns revisions; satellite executors consume.

### How to cite from a satellite sprint

Satellite sprints reference this playbook in their own inventories and audits using three canonical anchors:

1. `PLAYBOOK-satellite-env-platformization.md` — this file (the template).
2. `ADR-env-secret-profile-split.md` (ADR-0001) — the profile-split architectural decision.
3. `ADR-bucket-naming.md` (ADR-0002) — the canonical-vs-alias bucket decision (applies only if the satellite uses S3).
4. `.know/env-loader.md` — the 6-layer loader contract with worked example.

A satellite's smell inventory must cite all three as the source-state anchors against which its gap analysis is performed.

---

## B. Prerequisite Check (STOP-GATE)

**The executor runs this check BEFORE any satellite work begins. If any check fails, STOP. Do not proceed to section C.**

### Three prerequisite gates

1. **`.envrc` uses autom8y loader.**
   - Command: `grep -E '^use autom8y' .envrc`
   - Expected: at least one match.
   - Failure mode: `.envrc` either does not exist, does not source the ecosystem loader, or uses a non-standard pattern (direct `source` calls, hand-rolled env-loading, different loader entirely).

2. **Ecosystem config inherited.**
   - Command: `test -f /Users/tomtenuta/Code/a8/.a8/autom8y/ecosystem.conf && echo PRESENT || echo ABSENT`
   - Expected: `PRESENT`.
   - Failure mode: the monorepo checkout is missing the ecosystem config, which means the 6-layer loader cannot resolve Layers 1-2.

3. **Satellite is in the fleet handoff's Wave 1-3 table.**
   - Source of truth: `HANDOFF-hygiene-asana-to-hygiene-fleet-2026-04-20.md` §"Fleet Survey — Snapshot".
   - The current Wave 1-3 in-scope list: `autom8y-ads`, `autom8y-scheduling`, `autom8y-sms`, `autom8y-dev-x`, `autom8y-hermes`, `autom8y-val01b`, `autom8y-api-schemas`, `autom8y-workflows`, `autom8y-data`.

### What to do on failure

| Failure | Route |
|---------|-------|
| Gate 1 fails (no `use autom8y`) | Cross-rite handoff to **ecosystem rite**. The satellite either pre-dates fleet loader adoption or has intentionally decoupled — both cases require ecosystem governance, not hygiene execution. Example: `autom8y-hermes` (per fleet survey). |
| Gate 2 fails (ecosystem.conf absent) | STOP. Report the missing inheritance as an environment setup defect to the user — hygiene cannot proceed on a monorepo checkout that is itself mis-assembled. |
| Gate 3 fails (not in Wave table) | STOP. The satellite is either opt-out (by design: pure-library repos, workflow DAGs) or new since the fleet handoff. Route to fleet Potnia for inclusion. Examples: `autom8y-api-schemas`, `autom8y-workflows` (per fleet survey). |

### Fourth prerequisite branch — Satellite IS the canonical source of truth

**Trigger condition.** The satellite under evaluation is structurally upstream
of the fleet contract rather than a consumer of it. The playbook's 7-step
template sequence is structurally inapplicable because the steps presuppose a
consumer role that does not hold: the satellite **authors** Layer 1-2 of the
canonical env loader (or the equivalent fleet primitive) rather than consuming
it.

**Detection heuristics** (any single condition is strong signal; multiple
conditions trigger automatic routing to this branch):

1. `.git` is a worktree pointer whose parent directory contains the canonical
   loader implementation (e.g., `.a8/scripts/a8-devenv.sh`).
2. `pyproject.toml` declares `[tool.uv.workspace]` (or equivalent workspace
   declaration) and lists fleet satellites as workspace members.
3. `services.yaml` (or equivalent service registry) declares canonical
   infrastructure names referenced by downstream satellites.
4. `tools/` contains cross-satellite validators (e.g., a secretspec
   cross-validator, a fleet-wide config linter).
5. The playbook's `canonical_loader_reference` frontmatter path resolves to a
   file inside the satellite's own worktree.

**Routing action on trigger.** STOP the template-consumer sequence. Do NOT
execute Steps 1-7 as a consumer. Instead, execute the **source-of-truth
closure path** (parallel to §G.5 opt-out, but semantically opposite):

1. Author an ADR at `{satellite}/.ledge/decisions/ADR-NNNN-source-of-truth-reclassification-{date}.md`
   documenting the reclassification with grep-reproducible evidence for each
   detection heuristic that fired. Exemplar: `autom8y-val01b-fleet-hygiene/.ledge/decisions/ADR-val01b-source-of-truth-reclassification-2026-04-20.md`.
2. Author `{satellite}/.know/env-loader-source-of-truth.md` (NOT `.know/env-loader.md`
   — the filename difference is load-bearing: it signals authorship, not
   consumption). Required content per the val01b ADR Appendix A template:
   frontmatter declaring `fleet_role: contract-definition-source`, top-of-file
   banner explicitly distinguishing source-of-truth from Wave 3 opt-out,
   pointer to the satellite's existing `.know/env-architecture.md` (if
   present), canonical loader cross-reference with absolute line range,
   downstream consumer inventory table.
3. Emit a fleet-replan HANDOFF draft at `{satellite}/.ledge/reviews/HANDOFF-{satellite}-to-fleet-replan-{date}.md`
   scoping any deferred materialization work (missing canonical artifacts,
   downstream gaps) to a separate sprint.

**Semantic distinction (binding).** Source-of-truth reclassification is **NOT**
a Wave 3 opt-out. Opt-out (§G.5) is a declination — a peer satellite with no
runtime env surface. Source-of-truth is an authorship — the worktree that
defines the fleet contract. Both outcomes skip Step 6's `.know/env-loader.md`
authorship, but their meanings are opposite: opt-out produces
`.know/env-loader-optout.md`; source-of-truth produces
`.know/env-loader-source-of-truth.md`. Any downstream consumer (fleet Potnia
dashboards, future satellite executors, cross-rite handoffs) MUST preserve the
distinction.

**Fleet dashboard terminal status.** Satellites closed via this branch receive
the terminal status `reclassified-source-of-truth` (distinct from `completed`,
`aligned`, `opted-out`, `deferred-to-ecosystem`) in the fleet coordination
dashboard.

**Reference.** See `ADR-val01b-source-of-truth-reclassification-2026-04-20.md`
(at `/Users/tomtenuta/Code/a8/repos/autom8y-val01b-fleet-hygiene/.ledge/decisions/`)
for the originating case and the generalizable semantic argument.

### Additional routing signals (informational, not stop-gate)

- If the satellite has **no** `secretspec.toml` AND a substantial env surface, route to architect-enforcer prescription before proceeding to step 4 (see section F escalation triggers).
- If the satellite uses `production.example` instead of `local.example` (e.g., `autom8y-val01b`), step 3 is modified — see section G known-variance notes.

---

## C. Template Sequence (7 Steps)

Each step below is a self-contained unit: purpose, predecessor, exemplar, acceptance, decision branch. A satellite executor runs steps 1-7 in order. A step may be **skipped** only if a decision branch says so explicitly. Never reorder.

### Step 1 — Smell inventory

**Purpose.** Produce a per-satellite baseline that documents what the satellite has, what it lacks, and what drifts from the ecosystem loader contract. Non-negotiable: no template-copy shortcut is permitted. Each satellite has unique drift patterns that a generic template cannot anticipate.

**Predecessor.** Section B STOP-GATE passed.

**Exemplar.** `.ledge/reviews/smell-inventory-env-secrets-2026-04-20.md` (autom8y-asana baseline, referenced throughout the Sprint-A/B/C audits).

**Specialist.** code-smeller.

**Acceptance criterion.** A smell inventory at `{satellite}/.ledge/reviews/smell-inventory-env-secrets-{date}.md` with at minimum: (a) enumerated drifts per layer (which of Layers 1-6 the satellite populates, and what is missing); (b) secretspec.toml profile analysis (does `[profiles.cli]` exist? is `required` flag truthful across consumer modes?); (c) CLI-surface analysis (is there a `__main__.py` or `[project.scripts]` entry? does it hit S3 or file-system cache?); (d) S3 binding inventory (grep for `s3.bucket`, `BUCKET`, `boto3.client("s3")` — any hits at all?). Confidence grade: `moderate` for observed-state claims; `strong` for grep-verified claims.

**Decision branch.** None. Step 1 is mandatory for every satellite.

### Step 2 — `.env/defaults` population

**Purpose.** Populate Layer 3 (committed project non-secrets) so fresh-clone developers get a zero-touch working env for non-secret paths. Add the loader-precedence header comment so future readers know what layer this file occupies.

**Predecessor.** Step 1 smell inventory identifies which project-specific non-secrets belong in Layer 3.

**Exemplar.** `.env/defaults` at autom8y-asana post-CFG-001 (commit `b231314b`). Header block at lines 1-21 cites `scripts/a8-devenv.sh:_a8_load_env` with the Layer 3 line range (377) and enumerates the bucket-naming rationale.

**Specialist.** janitor.

**Acceptance criterion.** `{satellite}/.env/defaults` exists and contains: (a) Layer 3 header comment referencing `scripts/a8-devenv.sh:_a8_load_env` (lines 310-417 in the ecosystem monorepo); (b) project-specific non-secret defaults (bucket names, region, environment name, etc., as identified by Step 1); (c) no secrets (tokens, keys) — those belong in Layer 4. A fresh-clone acceptance test: `env -i bash -c 'set -a; source .env/defaults; set +a; env | grep ^{SATELLITE}_'` returns the expected defaults without any `export` statement.

**Layer 3 content sub-rubric (advisory).** When populating `.env/defaults`,
distinguish two classes of project non-secret: **(a) safe-to-commit structural
defaults** — port numbers, database-name-as-placeholder, region identifiers,
service-name strings; these declare the shape of the runtime contract without
leaking deployment topology. **(b) Secret-adjacent identifiers that leak infra
topology** — production RDS hostnames, KMS key ARNs, VPC IDs, account numbers,
S3 bucket names bound to specific AWS accounts; these are not secrets in the
credential sense, but committing them reveals infrastructure layout to any
repo-read-access actor. Class (a) belongs in `.env/defaults`; class (b) belongs
in `.env/local.example` (as a commented placeholder) or in the satellite's
secret-management surface. This is **advisory, not gating**: no satellite
audit fails on this distinction alone, but Step 1 smell inventory should flag
class (b) candidates for per-satellite adjudication. **Exemplar**:
`autom8y-data/.env/defaults.example:26-29` deliberately omits `DB_HOST` with an
inline G-9 security preamble citing this rubric — reference pattern for
CLI-less satellites with a sensitive infra-topology surface.

**Decision branch.**
- If `.env/defaults` already exists and is non-empty (e.g., `autom8y-data`, `autom8y-dev-x`, `autom8y-hermes`): **extend, do not replace**. Merge missing assignments into the existing file; preserve all existing assignments verbatim.
- If `.env/defaults` does not exist (e.g., `autom8y-ads`): create it from scratch using the autom8y-asana header as template.
- If the satellite has a legacy `.env/shared.example` pattern (e.g., `autom8y-sms`): see section G — the migration path is step 2 plus a deprecation of the legacy file.

### Step 3 — `.env/local.example` with 6-layer header

**Purpose.** Give developers a Layer 5 template with the canonical 6-layer precedence header documented inline. The header is identical across the fleet; only the placeholder list customizes per satellite.

**Predecessor.** Step 2 complete (Layer 3 content exists; Layer 5 override targets are known).

**Exemplar.** `.env/local.example` at autom8y-asana post-CFG-002 (commit `8f9a2fd2`). Header block at lines 16-28 renders the full 6-layer table; placeholders for Layer-3-override vars appear in the commented-out section.

**Specialist.** janitor.

**Acceptance criterion.** `{satellite}/.env/local.example` exists and contains: (a) a `cp .env/local.example .env/local` instruction at the top; (b) the 6-layer precedence table (verbatim from exemplar, no per-satellite edits to the table itself); (c) placeholders (commented out) for every Layer-3 default that a developer might personally override; (d) a brief enumeration of which vars override Layer 3 vs which introduce Layer-5-only values. Shell-sourceability check: `bash -c 'set -a; source .env/local.example; set +a && echo OK'` returns `OK`.

**Decision branch.**
- If satellite uses `production.example` instead of `local.example` (e.g., `autom8y-val01b`): adapt — the 6-layer header still applies, but the filename and default-environment-name need satellite-specific resolution. Check `.env/current` or the `_A8_ENV_CANONICAL` setting. See section G.
- If satellite already has `.env/local.example` (e.g., `autom8y-hermes`, `autom8y-data`): **extend the header only; preserve existing placeholder content**. The 6-layer header block is the mandatory addition.

### Step 4 — `secretspec.toml` `[profiles.cli]` (conditional)

**Purpose.** Split `secretspec.toml` into `[profiles.default]` (lib-mode permissive) and `[profiles.cli]` (CLI-mode strict) so required-field declarations reflect real consumer contracts. This step is **conditional** on the satellite having a CLI/offline entrypoint; without one, the profile split serves no consumer and is scope creep.

**Predecessor.** Step 3 complete. Step 1 smell inventory has confirmed CLI surface presence.

**Exemplar.** `secretspec.toml` at autom8y-asana post-CFG-003 (commit `6fa1afc4`) + `ADR-env-secret-profile-split.md` (ADR-0001). The TOML header comment at lines 5-30 documents the convention; the `[profiles.cli]` block at lines 172-174 redeclares only the vars whose `required` flag differs from `[profiles.default]`.

**Specialist.** janitor (execution); architect-enforcer (prescription if CLI surface is non-trivial — e.g., multiple CLI entrypoints with different required-var sets, or a CLI that uses a transport other than S3).

**Acceptance criterion.** `{satellite}/secretspec.toml` has: (a) a header comment block documenting the profile convention (cite ADR-0001 by path); (b) `[profiles.cli]` block listing only the vars whose `required` flag differs from the default profile; (c) every var in `[profiles.cli]` has `required = true` for real-contract enforcement; (d) TOML parses cleanly (`python3 -c 'import tomllib; tomllib.load(open("secretspec.toml","rb"))'` exits 0). If the `secretspec` binary is available: `secretspec check --config secretspec.toml --provider env --profile cli` fails non-zero when required vars are unset and passes when they are set. If the binary is unavailable: compensating verification via TOML parse + the CFG-006 inline fallback (step 5) must exercise the same required-vars tuple.

**Decision branch — BRANCH: does this satellite have a CLI entrypoint?**

- **Check**: `test -f src/*/__main__.py || grep -q '\[project.scripts\]' pyproject.toml`

- **If YES**: execute step 4 and step 5. Identify which vars the CLI path
  requires strict. Author `ADR-NNNN-env-secret-profile-split.md` if the split
  introduces a non-trivial architectural decision (most satellites will
  reference ADR-0001 by cross-link rather than authoring a new ADR; write a
  new ADR only when the satellite's profile semantics diverge from
  autom8y-asana's).

- **If NO** (CLI-less satellite): **emit an empty `[profiles.cli]` block with
  inline rationale comment** documenting the CLI-surface grep and citing
  `ADR-env-secret-profile-split.md` (ADR-0001) by path — do NOT skip the block
  entirely. Fleet grep-discoverability (`rg '\[profiles.cli\]' repos/`)
  requires structural uniformity: every satellite's `secretspec.toml`
  contains a `[profiles.cli]` block regardless of CLI surface, differing only
  in content. The rationale comment must name (a) the grep that confirmed no
  CLI entrypoint (`test -f src/*/__main__.py || grep -q '\[project.scripts\]' pyproject.toml`
  returned no matches), (b) the ADR-0001 truthful-contract test ("no
  consumer, therefore no required-vars to enforce"), and (c) the fact that
  the block is structurally present for fleet parity and will accept
  override-on-top promotions if a CLI entrypoint is added in a future sprint.
  Step 5 (CLI preflight) remains **skipped** per this branch — preflight has
  no contract to check against and would create a false fail-fast surface.

  **Canonical exemplar** (empty-block-with-rationale): `autom8y-data/secretspec.toml:143-161`
  — empty `[profiles.cli]` block preceded by 17-line inline rationale comment
  citing ADR-0001 path, the CLI-surface grep, and the "no runtime consumer"
  disclaimer. This pattern was ratified via Pythia Disposition B during the
  FLEET-data alignment audit (2026-04-20).

  **Transitional-accept exemplar** (rationale-in-header, pre-ratification):
  `autom8y-dev-x/secretspec.toml:1-19` — rationale appended to the file-header
  comment block citing ADR-0001 + `cli.py:357-363` graceful-degradation line
  range, with no `[profiles.cli]` block body. This pattern honors ADR-0001
  truthful-contract but breaks fleet grep-discoverability. Satellites that
  adopted this pattern before v2 ratification are **not required** to
  retroactively convert. NEW satellites executing this playbook at v2 or
  later MUST use the canonical empty-block pattern.

- **If the satellite has no `secretspec.toml` at all** (e.g., `autom8y-val01b`
  prior to reclassification): see section F escalation — this requires
  architect-enforcer prescription on whether to author one. If the satellite
  is reclassified as source-of-truth via §B's fourth prerequisite branch,
  the `secretspec.toml` authoring decision routes to fleet-replan rather
  than in-sprint.

### Step 5 — CLI preflight (conditional)

**Purpose.** Fail fast at the CLI boundary when the `[profiles.cli]` contract is violated, replacing the current deep-transport generic error with a structured, actionable error that cites `.env/defaults`, `.env/local.example`, and `secretspec.toml`.

**Predecessor.** Step 4 complete. `[profiles.cli]` exists to check against.

**Exemplar.** `src/autom8_asana/metrics/__main__.py` preflight block (commit `f5fe16b4`, CFG-006) + `TDD-cli-preflight-contract.md` (TDD-0001, Alternative C). Pattern: subprocess-first shell-out to `secretspec check --profile cli`, with inline-fallback when the binary is absent, exit code 2 on contract violation, structured error template citing all three config sources with absolute paths.

**Specialist.** janitor.

**Acceptance criterion.** Preflight runs before the first network/filesystem call on the CLI path. Test points (from TDD-0001): (a) preflight fires before the S3 load on a missing-var path; (b) preflight is silent on happy path; (c) `--list` or equivalent discovery paths structurally bypass preflight; (d) fresh-clone integration works end-to-end when Layer 3 is populated. **Critical test-isolation requirement** (surfaced via Sprint-C REVISION-REQUIRED, `AUDIT-env-secrets-sprint-C.md` §1): any unit test that mocks the data loader MUST also monkeypatch the CLI-required env vars via an autouse class-scoped fixture, OR the tests will fail in CI-equivalent no-env shells. The autom8y-asana REMEDIATE commit `7e5b8687` is the template for this fixture.

**Decision branch.** Skipped if step 4 was skipped (no CLI entrypoint). If the satellite has multiple CLI entrypoints: each gets its own preflight, or a shared `{satellite}/src/{package}/_cli_preflight.py` module is factored out (architect-enforcer decision — do not factor out reflexively).

### Step 6 — `.know/env-loader.md` in satellite

**Purpose.** Document the 6-layer loader contract in the satellite's knowledge base with a worked example for one load-bearing variable. This makes the satellite self-documenting for future onboarding without requiring cross-repo lookup to the ecosystem monorepo.

**Predecessor.** Steps 1-5 complete (or skipped per branch). The worked example draws on the satellite's actual config surface.

**Exemplar.** `.know/env-loader.md` at autom8y-asana post-CFG-008 (commit `1a13cafe`). Contains: frontmatter with `domain: env-loader`, source-scope paths, confidence grade; 6-layer precedence table with ecosystem loader line-number citations; cross-links to `secretspec.toml` profiles, ADR paths, canonical loader location; worked example for `ASANA_CACHE_S3_BUCKET` walking through each layer's role; canonical-bucket-name section (if step 7 applies).

**Specialist.** janitor.

**Acceptance criterion.** `{satellite}/.know/env-loader.md` exists with the full 6-layer table (verbatim from exemplar is acceptable — the table is ecosystem-invariant), cross-links to the satellite's own `secretspec.toml` and (if step 7 applies) the satellite's bucket ADR, and a worked example for **one** satellite-specific variable that the smell inventory identified as load-bearing. Frontmatter follows the `.know/` schema (domain, source_scope, confidence, format_version).

**Worked-example variable selection (advisory).** The step-1 smell inventory
typically surfaces multiple load-bearing variables; the acceptance criterion
requires "one" but does not prescribe which. Pick the variable with **either**
(a) the most complex layer interaction (e.g., a var whose resolved value
depends on Layer 3 default + Layer 5 override + a transport-specific fallback
path), **or** (b) the highest fresh-clone friction (a var whose absence causes
the most confusing error for a new developer). Both criteria produce an
example with documentation leverage; either choice is acceptable.
**Exemplars**: `autom8y-data/.know/env-loader.md:60-96` (DB_HOST chosen —
criterion (b), highest fresh-clone friction given the DuckDB/MySQL dual-binding
surface); `autom8y-dev-x/.know/env-loader.md` (DEVCONSOLE_LLM_API_KEY chosen —
criterion (a), walks `config.py:37-40` fallback path from primary key to
ANTHROPIC_API_KEY).

**Decision branch — BRANCH: canonicalization ownership (per incoming fleet handoff tradeoff_points[2]).**
- **Option (a) [DEFAULT for Wave 1-3]**: copy as-is from autom8y-asana, customize the worked-example section. Accepts short-term DRY violation; Wave 4 ECO-001 will promote the canonical doc to `.a8/autom8y/` later.
- **Option (b) [DEFERRED]**: satellite's `.know/env-loader.md` is a thin cross-link to `.a8/autom8y/env-loader.md`. Requires ECO-001 (Wave 4) to complete first. Do not block a Wave 1-3 satellite on ECO-001; use option (a).

### Step 7 — Bucket ADR (conditional, if S3 is used)

**Purpose.** Document the canonical-vs-alias bucket decision for satellites that bind S3 bucket names. Prevents the "developer guesses the org-branded name and gets an empty bucket" friction documented in the autom8y-asana Sprint-C context.

**Predecessor.** Step 1 smell inventory has enumerated S3 bindings.

**Exemplar.** `ADR-bucket-naming.md` (ADR-0002, Sprint-C). Option A pattern: choose the load-bearing canonical name, document the non-canonical alias as an empty bucket that should not receive writes, enumerate every code site that binds the canonical name (grep audit table).

**Specialist.** architect-enforcer.

**Acceptance criterion.** `{satellite}/.ledge/decisions/ADR-NNNN-bucket-naming.md` exists with: (a) decision clearly stating which bucket name is canonical; (b) grep-audited table of every code reference to the canonical name (single-repo + cross-repo if applicable); (c) option-enumeration (Options A/B/C from ADR-0002 is the canonical slate — the satellite adapts rationale, not the option set); (d) cross-reference to the satellite's `.know/env-loader.md` (step 6) which will cite this ADR.

**Decision branch — BRANCH: does this satellite have an S3 bucket reference?**
- **Check**: `grep -rnE 's3\.bucket|BUCKET|boto3\.client\("s3"\)' --include='*.py' --include='*.yml' --include='*.toml'`
- **If YES**: execute step 7. Author the ADR.
- **If NO**: **skip step 7**. Document the skip in the smell inventory. Proceed to closure.
- **If bucket naming is contested at fleet scope** (the same canonical name is load-bearing across multiple satellites): route to fleet-level ADR, not per-satellite. See section F escalation.


---

## D. Per-Satellite Decision Tree

Use the fleet survey in `HANDOFF-hygiene-asana-to-hygiene-fleet-2026-04-20.md` §"Fleet Survey — Snapshot" as the starting state. Each satellite's prescribed step subset is derived from that snapshot and the decision branches in section C.

### D.1 autom8y-ads (Wave 1, HIGH)

**Observed state**: no `.env/` directory; has `secretspec.toml`; loader active.
**Prescribed steps**: 1, 2, 3, 6 mandatory. 4, 5, 7 conditional on investigation.
**Investigation required before step 4/5**: CLI-surface check (step 4 decision branch). Grep for `__main__.py` under `src/` and for `[project.scripts]` in `pyproject.toml`.
**Investigation required before step 7**: S3-binding grep.
**Notes**: this is the **highest-delta** satellite in the fleet — the loader runs but has no Layer 3/5 content to load, so all project config currently comes from the shell's ambient env. Silent-failure class.

### D.2 autom8y-scheduling (Wave 1, HIGH)

**Observed state**: only `.env/local` exists; no `defaults`, no `local.example`; has `secretspec.toml`; loader active.
**Prescribed steps**: 1, 2, 3, 6 mandatory. 4, 5, 7 conditional on investigation.
**Notes**: step 2 must populate `.env/defaults` with project non-secrets inferred from the existing `.env/local` (take the non-personal subset). Step 3 creates a new `.env/local.example` as template — do not overwrite the developer's `.env/local`.

### D.3 autom8y-sms (Wave 1, HIGH)

**Observed state**: `.env/defaults`, `.env/local.example`, **plus legacy `.env/shared.example`**; has `secretspec.toml`; loader active.
**Prescribed steps**: 1, 2, 3, 6 mandatory. 4, 5, 7 conditional. **Plus legacy-migration substep** (see section G).
**Notes**: step 2 must migrate the content of `.env/shared.example` into `.env/defaults` and/or `.env/local.example` as appropriate. The `.env/shared` pattern is the backward-compat fallback documented at `scripts/a8-devenv.sh:397-404`; new repos must not use it, and existing repos should migrate. After migration, either delete `shared.example` or retain it with a deprecation-header comment. May warrant a cross-rite signal to ecosystem rite to formalize the deprecation of the `.env/shared` block in `a8-devenv.sh`.

### D.4 autom8y-dev-x (Wave 2, MEDIUM)

**Observed state**: has `.env/current`, `.env/defaults`, `.env/local`; missing `.env/local.example`; has `secretspec.toml`; loader active.
**Prescribed steps**: 1, 3, 6 mandatory. 2 optional (extend only if Step 1 finds gaps). 4, 5, 7 conditional.
**Notes**: step 3 is the primary delta — add `.env/local.example` as the committed template counterpart to the existing `.env/local`.

### D.5 autom8y-hermes (Wave 2, MEDIUM) — PREREQUISITE LIKELY FAILS

**Observed state**: `.env/defaults`, `.env/local`, `.env/local.example`; has `secretspec.toml`; **`.envrc` does NOT use autom8y loader**.
**Prescribed action**: section B Gate 1 fails. Route to **ecosystem rite** before any template execution.
**Investigation question**: is `.envrc` pre-migration (never adopted autom8y loader) or intentionally decoupled? If pre-migration: low-risk migration to standard loader. If intentional: document the decoupling rationale in `.know/` and confirm the 6-layer contract is manually maintained.
**Notes**: this satellite's `.env/` layout is already good. The gap is the loader entry point, not the env files.

### D.6 autom8y-val01b (Wave 2, MEDIUM) — NON-STANDARD ENV-FILE CONVENTION

**Reclassified**: source-of-truth (per §B fourth prerequisite branch).
Worktree IS the `autom8y` monorepo which authors Layer 1-2 of the fleet
contract. Playbook Steps 1-7 are structurally inapplicable. See
`ADR-val01b-source-of-truth-reclassification-2026-04-20` for reclassification
evidence; see `.know/env-loader-source-of-truth.md` for fleet-role declaration.
**Historical note**: pre-reclassification, this satellite was characterized
as "Wave 2 MEDIUM, non-standard env-file convention, no secretspec.toml."
The Sprint-A inventory falsified the characterization; see
ECO-BLOCK-004 in `FLEET-COORDINATION-env-secret-platformization.md` for
governance-gap context.

### D.7 autom8y-api-schemas (Wave 3, LOW) — LIKELY OPT-OUT

**Observed state**: no `.env/`, no `secretspec.toml`, `.envrc` not standard.
**Prescribed action**: section B Gate 1 fails. Confirm opt-out: is this a pure-library / schema-generation repo with no runtime env surface? If YES: document opt-out rationale in `.know/` and close. If NO: return to fleet Potnia for scope adjustment.

### D.8 autom8y-workflows (Wave 3, LOW) — LIKELY OPT-OUT

**Observed state**: no `.env/`, no `secretspec.toml`, `.envrc` not standard.
**Prescribed action**: same as D.7. Confirm workflow-orchestration repo has no runtime env surface; document opt-out or escalate.

### D.9 autom8y-data (Wave 3, LOW) — REFERENCE-PATTERN AUDIT

**Observed state**: `.env/current`, `.env/defaults`, `.env/defaults.example`, `.env/local`; has `secretspec.toml`; loader active. Most-complete `.env/` layout in fleet.
**Prescribed action**: **ALIGNMENT AUDIT, not remediation.** Compare this satellite's existing `.env/defaults.example` and `secretspec.toml` against ADR-0001 and `.know/env-loader.md`. If divergence: align autom8y-data as reference implementation or document the intentional difference. If already aligned: produce a short audit artifact and close.
**Prescribed steps**: 1 mandatory (as audit). 6 mandatory (create `.know/env-loader.md` even if config is already aligned — knowledge propagation is still owed). 2, 3, 4, 5, 7 only if audit surfaces gaps.

### Summary table

| Satellite | Wave | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 | Step 7 |
|-----------|------|--------|--------|--------|--------|--------|--------|--------|
| autom8y-ads | 1 | YES | YES (create) | YES (create) | COND | COND | YES | COND |
| autom8y-scheduling | 1 | YES | YES (create) | YES (create) | COND | COND | YES | COND |
| autom8y-sms | 1 | YES | YES (migrate) | YES (extend) | COND | COND | YES | COND |
| autom8y-dev-x | 2 | YES | OPT | YES (create) | COND | COND | YES | COND |
| autom8y-hermes | 2 | STOP-GATE (ecosystem rite) | — | — | — | — | — | — |
| autom8y-val01b | 2 | RECLASSIFIED (source-of-truth per §B 4th branch) | — | — | — | — | — | — |
| autom8y-api-schemas | 3 | STOP-GATE (opt-out verify) | — | — | — | — | — | — |
| autom8y-workflows | 3 | STOP-GATE (opt-out verify) | — | — | — | — | — | — |
| autom8y-data | 3 | YES (audit) | OPT | OPT | OPT | OPT | YES | OPT |

Legend: YES = mandatory; OPT = optional (execute if step-1 smell inventory finds gaps); COND = conditional per step's decision branch (CLI surface / S3 binding); MOD = modified per section G; ESCALATE = route to architect-enforcer or other rite per section F; STOP-GATE = section B gate fails.


---

## E. Audit Gates per Sprint Batch

Each satellite sprint mirrors the autom8y-asana three-sprint structure. Batches are:

| Sprint | Scope (maps to template steps) | Audit artifact |
|--------|-------------------------------|----------------|
| **Sprint-A** | Steps 1, 2, 3 (inventory + Layer 3 + Layer 5 template) | `{satellite}/.ledge/reviews/AUDIT-env-secrets-sprint-A.md` |
| **Sprint-B** | Steps 4, 5 (profile split + CLI preflight) — SKIP if no CLI surface | `{satellite}/.ledge/reviews/AUDIT-env-secrets-sprint-B.md` |
| **Sprint-C** | Steps 6, 7 + any residual (knowledge doc + bucket ADR) | `{satellite}/.ledge/reviews/AUDIT-env-secrets-sprint-C.md` |

### Gate mechanics

- **Audit-lead runs a PASS gate between batches.** Sprint-B cannot start until Sprint-A PASSes. Sprint-C cannot start until Sprint-B PASSes (or is formally skipped).
- **Critique-iteration-protocol two-iteration cap applies per sprint.** A BLOCKING audit verdict triggers REMEDIATE dispatch (narrow scope: fix what the audit identified, nothing else). The next audit is DELTA-scope (did REMEDIATE address the original issues? any new issues introduced?). Two iterations of REMEDIATE + DELTA without PASS → ESCALATE to user.
- **Test-integration lesson from Sprint-B → Sprint-C (autom8y-asana)**: any sprint that introduces a preflight or validation boundary MUST run the full test suite in a no-env subshell as part of its own audit, not defer that to the next sprint's audit. Sprint-B's "pytest not run against this repo as part of Sprint-B" declaration created the latent regression that Sprint-C surfaced. Satellite Sprint-B audits must include: `env -u <REQUIRED_VARS> uv run pytest <relevant_test_path> -q` as a mandatory evidence block.

### Closure criterion per satellite

A satellite is considered closed when:
- Sprint-A, Sprint-B (or formal skip), Sprint-C all PASS.
- A satellite HANDOFF-RESPONSE is emitted back to hygiene-fleet Potnia.
- The satellite's `.know/env-loader.md` is in place (step 6) regardless of which other steps were skipped.

---

## F. Escalation Triggers (Fleet-Aware)

These are triggers that arise DURING execution (distinct from the section B STOP-GATE which fires BEFORE execution). A satellite executor hitting any of these pauses the sprint and routes as described.

### F.1 Non-standard `.envrc` discovered mid-sprint

- **Symptom**: Step-1 smell inventory reveals `.envrc` does not use `use autom8y`, but the satellite was not caught by section B Gate 1 (e.g., Gate 1 was run but the `.envrc` has since drifted, or the satellite was miscategorized in the fleet survey).
- **Route**: Cross-rite handoff to **ecosystem rite**. This is the autom8y-hermes class of finding.

### F.2 No `secretspec.toml` + substantial env surface

- **Symptom**: satellite lacks `secretspec.toml` but step-1 smell inventory reveals a non-trivial env-var surface (e.g., > 5 project-specific vars, tokens/credentials in env, CLI entrypoints that read env).
- **Route**: **architect-enforcer prescription** required before step 4 can be evaluated. The question: author a new `secretspec.toml` (authoritative contract for validation tools), or document opt-out (env surface managed by direnv + shell-level discipline)? This is the autom8y-val01b class of finding.

### F.3 Contested bucket naming at fleet scope

- **Symptom**: step-7 grep reveals the satellite binds a bucket name that is ALSO bound by another satellite, and the two satellites disagree on canonicalization.
- **Route**: **fleet-level ADR** required, not per-satellite. Coordinate via hygiene-fleet Potnia. Do not author a per-satellite ADR that would conflict with a sibling satellite's canonical choice.

### F.4 CLI surface exceeds single-entrypoint pattern

- **Symptom**: step-4 investigation reveals the satellite has multiple CLI entrypoints with different required-var sets, or a CLI that uses a transport other than S3 (e.g., Postgres, Redis, SQS) where the `[profiles.cli]` pattern needs extension.
- **Route**: **architect-enforcer prescription** before step 4 can proceed. The template was calibrated against a single CLI entrypoint with S3 as the strict transport. Multi-entrypoint or non-S3 cases require design before execution.

### F.5 Test regression under preflight introduction

- **Symptom**: step-5 preflight wiring causes unit tests to fail in no-env subshells (the Sprint-C REVISION-REQUIRED class).
- **Route**: **in-sprint REMEDIATE**, not escalation. Apply the autom8y-asana commit `7e5b8687` pattern: autouse class-scoped monkeypatch fixture, zero production-code change. Only escalate if REMEDIATE iteration 1 fails its DELTA audit.

### F.6 Iteration cap reached without PASS

- **Symptom**: sprint has run REMEDIATE + DELTA twice without achieving PASS.
- **Route**: **ESCALATE to user** per `critique-iteration-protocol`. Do not attempt a third REMEDIATE iteration. The signal is that either the plan is flawed (revise playbook — trigger playbook REVISION per section A authorship discipline) or the satellite has state the template did not anticipate (produce a `KNOW-CANDIDATE` note and escalate).

---

## G. Known-Variance Notes (Satellite-Specific)

Expected deltas per satellite. These notes adapt the generic template to known state; they are NOT new branches — they are concrete instructions for the branches already defined in section C.

### G.1 autom8y-sms — legacy `.env/shared.example` migration

Step 2 must perform this migration:

1. Read `{satellite}/.env/shared.example` contents.
2. Partition variables into: (a) project non-secrets → Layer 3 (`.env/defaults`); (b) personal overrides → Layer 5 template (`.env/local.example`).
3. Write Layer 3 assignments into `.env/defaults` (with the loader-precedence header per step 2 acceptance).
4. Write Layer 5 placeholders (commented out) into `.env/local.example`.
5. Delete `.env/shared.example` OR retain it with a deprecation header citing the ecosystem monorepo's deprecation note at `scripts/a8-devenv.sh:397-404`.

Commit message pattern: `chore(env): migrate shared.example to defaults+local.example split [step-2-playbook]`.

### G.2 autom8y-hermes — prerequisite check fails by default

See section D.5. Do not attempt to execute the template; route to ecosystem rite for `.envrc` migration or decoupling documentation.

### G.3 autom8y-data — reference-pattern alignment audit

Per section D.9, execute the template as an audit, not a remediation. Step 1 produces an alignment report rather than a drift inventory. Steps 2-5, 7 are executed only if the alignment report identifies gaps. Step 6 is always produced — even a compliant reference satellite owes a `.know/env-loader.md` so future readers know where to look.

### G.4 autom8y-val01b — no `secretspec.toml`, `production.example` convention

Two adaptations:

1. **Step 3 filename adaptation**: the satellite's Layer-5 template is `.env/production.example` rather than `.env/local.example`. This suggests `_A8_ENV_CANONICAL` is set to something like `production` instead of `local`, or `.env/current` selects a different environment name. Investigate which before writing the template. The 6-layer header still applies; only the filename and default-environment identifier differ.
2. **Steps 4-5 require architect-enforcer prescription** (section F.2). The satellite has no `secretspec.toml` to extend. Prescription answers: author one, or document opt-out?

### G.5 autom8y-api-schemas and autom8y-workflows — opt-out verification

Per sections D.7 / D.8, section B Gate 1 fails by default. The opt-out verification substep is:

1. Confirm no runtime env surface (no `__main__.py`, no `[project.scripts]`, no FastAPI/Lambda entrypoint).
2. Confirm no S3 / DB / external-service clients instantiated at runtime.
3. Author a minimal `{satellite}/.know/env-loader-optout.md` (not `env-loader.md`) with frontmatter `domain: env-loader-optout` documenting why this satellite does not participate in the 6-layer contract.
4. HANDOFF-RESPONSE back to hygiene-fleet confirming opt-out.

### G.6 autom8y-ads — no `.env/` directory at all

Per section D.1, the highest-delta satellite. Adaptation for step 2: the executor is not extending; they are creating the whole layer-3 surface from scratch. Use the autom8y-asana `.env/defaults` as structural template (header block, comment style) and populate with satellite-specific values derived from step 1 smell inventory + any ambient-env observations the developer currently relies on.

---

## H. Artifact Trail Template

Each satellite sprint emits the following artifacts (relative to THAT satellite's repo, not autom8y-asana). The list below is the complete canonical set; items guarded by a step's decision branch are conditional.

| Path | Required? | Produced by step | Notes |
|------|-----------|------------------|-------|
| `.ledge/reviews/smell-inventory-env-secrets-{date}.md` | ALWAYS | Step 1 | Every satellite emits this. No exceptions. |
| `.ledge/decisions/ADR-NNNN-env-secret-profile-split.md` | IF step 4 applies AND the satellite's profile semantics diverge from ADR-0001 | Step 4 | Most satellites will cross-link autom8y-asana's ADR-0001 rather than author a new one. |
| `.ledge/decisions/ADR-NNNN-bucket-naming.md` | IF step 7 applies | Step 7 | Grep-audit table is mandatory content; see ADR-0002 exemplar. |
| `.ledge/specs/TDD-NNNN-cli-preflight-contract.md` | IF step 5 applies AND the preflight differs materially from TDD-0001's Alternative C | Step 5 | Most satellites cross-link TDD-0001; author a new TDD only for divergent preflight patterns. |
| `.ledge/reviews/AUDIT-env-secrets-sprint-A.md` | ALWAYS | Audit-lead (between Sprint-A and Sprint-B) | — |
| `.ledge/reviews/AUDIT-env-secrets-sprint-B.md` | ALWAYS (even if steps 4/5 skipped — audit records the skip) | Audit-lead (between Sprint-B and Sprint-C) | If steps 4/5 were skipped, the audit verdict is a one-section PASS-with-skip-documented. |
| `.ledge/reviews/AUDIT-env-secrets-sprint-C.md` | ALWAYS | Audit-lead (closure) | — |
| `.ledge/reviews/AUDIT-env-secrets-sprint-C-delta.md` | IF Sprint-C REVISION-REQUIRED | Audit-lead (REMEDIATE cycle) | Follows `critique-iteration-protocol` delta-scope format. |
| `.ledge/reviews/HANDOFF-RESPONSE-hygiene-{satellite}-to-hygiene-fleet-{date}.md` | ALWAYS | Satellite sprint closure | Returns status to hygiene-fleet Potnia. |
| `.know/env-loader.md` | ALWAYS (or `.know/env-loader-optout.md` for opt-out satellites) | Step 6 | Every participating satellite OR every opt-out satellite emits one of these. |

### Commit conventions

Commits use conventional-commits with a `[playbook-step-N]` trailer tag so audit tools can map commits back to template steps. Examples:

- `chore(env): populate .env/defaults with S3 cache config [playbook-step-2]`
- `docs(config): add 6-layer precedence header to .env/local.example [playbook-step-3]`
- `config(secretspec): add [profiles.cli] with required S3 vars [playbook-step-4]`
- `feat(metrics): add CLI preflight before load_project_dataframe [playbook-step-5]`
- `docs(know): document 6-layer env loader contract in .know/env-loader.md [playbook-step-6]`

Each commit is atomic (single file or tightly-coupled set) and independently revertible. This mirrors the autom8y-asana commit chain `b231314b..7e5b8687`.

---

## I. Evidence Ceiling and Closing

Per `self-ref-evidence-grade-rule`, this playbook's self-assertions cap at MODERATE. Externally-reproducible claims (e.g., "the 6-step E2E chain at autom8y-asana passes at commit `7e5b8687`") are STRONG because any observer can reproduce them. The step prescriptions themselves are MODERATE — they derive from a single empirical sprint (autom8y-asana) and will be validated or refined as Wave 1-3 satellites apply them.

The first satellite sprint (Wave 1) is the empirical stress test for this playbook. If step sequencing or acceptance criteria prove insufficient, the satellite executor is expected to ESCALATE rather than silently diverge, producing a playbook revision event per section A authorship discipline.

## Changelog

### v2 — 2026-04-20 — Layer-1 closeout (ECO-BLOCK-003 + ESC-2 resolution)

Consolidates three upstream-feedback items from ECO-BLOCK-003 (autom8y-data +
autom8y-dev-x dual-satellite evidence) and three revision-spec items from the
val01b cross-rite escalation (ESC-2). Revision authored per
`REVISION-SPEC-playbook-v2-2026-04-20.md`.

- **§B STOP-GATE 4th branch** — source-of-truth reclassification closure path,
  parallel to §G.5 opt-out but semantically opposite. Generalized from the
  val01b case per `ADR-val01b-source-of-truth-reclassification-2026-04-20`.
- **§C Step 4 Disposition B ratification** — empty-`[profiles.cli]`-block-with-rationale
  is canonical for CLI-less satellites; rationale-in-header (dev-x) accepted
  as transitional. Closes UPSTREAM-001.
- **§C Step 2 Layer 3 sub-rubric** — advisory on safe-to-commit structural
  defaults vs. secret-adjacent infra-topology identifiers. Closes UPSTREAM-002.
- **§C Step 6 worked-example selection advisory** — dual criterion
  (layer-interaction complexity OR fresh-clone friction). Closes UPSTREAM-003.
- **§D.6 + §D summary table** — val01b row re-labeled reclassified;
  historical characterization moved to a footnote.

No behavior change in any satellite code; this revision is documentation-only.
Satellites closed pre-v2 (autom8y-ads, autom8y-scheduling, autom8y-sms,
autom8y-dev-x, autom8y-hermes, autom8y-val01b, autom8y-api-schemas,
autom8y-workflows, autom8y-data) are NOT required to re-execute — their
closures remain valid under v1 semantics with the dev-x Step 4 pattern
accepted transitionally.

References: `ESC-2 HANDOFF` at
`autom8y-val01b-fleet-hygiene/.ledge/reviews/HANDOFF-hygiene-val01b-to-hygiene-asana-playbook-revision-2026-04-20.md`;
`val01b ADR` at `autom8y-val01b-fleet-hygiene/.ledge/decisions/ADR-val01b-source-of-truth-reclassification-2026-04-20.md`;
ECO-BLOCK-003 row in `FLEET-COORDINATION-env-secret-platformization.md:54`.

## Links

- Incoming fleet handoff: `.ledge/reviews/HANDOFF-hygiene-asana-to-hygiene-fleet-2026-04-20.md`
- Original incoming handoff (CFG-001..CFG-008 scope): `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md`
- HANDOFF-RESPONSE (per-item resolution): `.ledge/reviews/HANDOFF-RESPONSE-hygiene-to-eunomia-2026-04-20.md`
- PASS chain: `AUDIT-env-secrets-sprint-A.md`, `...-sprint-B.md`, `...-sprint-C.md`, `...-sprint-C-delta.md`
- Architectural anchors: `ADR-env-secret-profile-split.md` (ADR-0001), `ADR-bucket-naming.md` (ADR-0002), `TDD-cli-preflight-contract.md` (TDD-0001)
- Knowledge anchor: `.know/env-loader.md`
- Canonical loader (ecosystem, read-only reference): `/Users/tomtenuta/Code/a8/scripts/a8-devenv.sh:310-417`
