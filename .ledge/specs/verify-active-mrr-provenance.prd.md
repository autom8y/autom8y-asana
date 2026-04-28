---
type: spec
artifact_type: PRD
initiative_slug: verify-active-mrr-provenance
session_id: session-20260427-154543-c703e121
phase: requirements
authored_by: requirements-analyst
authored_on: 2026-04-27
branch: feat/active-mrr-freshness-signal
worktree: .worktrees/active-mrr-freshness/
title: Verify active_mrr metric provenance and freshness
status: draft  # staged for architect review prior to engineer-phase T7 commit
impact: high
impact_categories: [data_model, cross_service]
attesters:
  primary: thermia (ATTESTED-PENDING-THERMIA)
  fallback: sre  # invoked if thermia rite is not registered at handoff time per D8
reconstruction:
  status: RECONSTRUCTED-2026-04-27
  reason: original lost to **/.ledge/* gitignore during predecessor 10x-dev sprint
  reconstructed_by: thermia procession P0 pre-flight (general-purpose dispatch)
  source_evidence:
    - .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md (cites §1, §3, §6 C-1+C-2+C-4+C-6, §7, §8, NG5, NG7, D5, D6, D7, D8, D10)
    - .ledge/handoffs/2026-04-27-section-mtimes.json (sidecar)
    - .ledge/reviews/QA-T9-verify-active-mrr-provenance.md (cites US-1..US-6, AC-1.2, AC-2.3, AC-2.4, AC-3.1..AC-3.4, AC-4.1..AC-4.5, AC-5.2, SM-6, C-2)
    - src/autom8_asana/metrics/freshness.py (T3 TDD implementation)
    - src/autom8_asana/metrics/__main__.py (T3 TDD CLI integration)
    - src/autom8_asana/metrics/definitions/offer.py:23 (dedup_keys empirical cross-check anchor)
    - conversation memory of authoring (predecessor session-20260427-154543-c703e121)
---

# PRD — Verify active_mrr metric provenance and freshness

> [RECONSTRUCTED-2026-04-27] — Original on-disk source destroyed when the
> `.worktrees/active-mrr-freshness/` worktree was removed at sprint wrap.
> Frontmatter `reconstruction:` block records the recovery provenance.
> The merged code at `src/autom8_asana/metrics/freshness.py` and the
> surviving handoff dossier are the load-bearing ground truth; this PRD
> describes the requirements those artifacts satisfy.

## §1 Problem Statement

The `active_mrr` metric (currently `$94,076.00`, computed by
`python -m autom8_asana.metrics active_mrr`) is derived from a cached S3
parquet dataset whose freshness is **opaque to the consumer at runtime**.

Section parquet `LastModified` timestamps observed today (2026-04-27) at
`s3://autom8-s3/dataframes/1143843662099250/sections/` span:

- newest: `1143843662099257.parquet` @ 2026-04-27T14:01:10Z (same-day)
- oldest: `1155403608336729.parquet` @ 2026-03-26T04:17:44Z (≈32 days stale)

There is **no runtime signal** allowing the consumer — human or machine — to
assess whether the dollar figure represents current Asana state or a snapshot
from weeks ago. **Decision-grade financial metrics cannot ride on
opaque-freshness data.**

The defect class is **provenance-gap, not computational error**. The dedup
logic at `src/autom8_asana/metrics/definitions/offer.py:23`
(`dedup_keys=["office_phone", "vertical"]`) is verified correct via
empirical cross-check: identical 71-row / `$94,076.00` result vs `parent_gid`
dedup; zero over- or under-counting cells. The gap is the **missing freshness
signal** between cache and consumer.

## §2 Goals / Non-Goals

### Goals

- **G1**: Consumers receive a freshness signal (oldest mtime, newest mtime,
  max_age) by default on every CLI invocation.
- **G2**: Configurable staleness threshold (default `6h`) emits WARNING to
  stderr when exceeded.
- **G3**: Opt-in `--strict` promotes WARNING to **non-zero exit**. Strict
  applies to:
  - (a) max parquet mtime exceeds threshold;
  - (b) IO/auth errors against the freshness probe;
  - (c) zero-result-set after filter+dedup.
  Strict does **NOT** apply to section-count diff (per D3 / C-6).
- **G4**: Opt-in `--json` flag emits a single structured JSON envelope to
  stdout (warnings still go to stderr).
- **G5**: Stakeholder-affirmed bucket→env mapping documented in
  `.know/env-loader.md` (`autom8-s3 = production`, by user
  `tom@tenuta.io`, 2026-04-27).
- **G6**: Complete handoff dossier for the thermia rite covering deferred
  concerns (D5, D7, D10, D8 telos verification gate).
- **G7**: Backwards compatibility — default-mode output is a **strict
  superset** of current; the existing `\n  active_mrr: $NN,NNN.NN\n` line
  is preserved byte-for-byte.

### Non-Goals

- **NG1**: NO modifying `src/autom8_asana/lambda_handlers/cache_warmer.py`.
- **NG2**: NO Asana-side section-drift reconciliation.
- **NG3**: NO terraform/IaC reading for bucket-tagging.
- **NG4**: NO force-warm CLI affordance.
- **NG5**: NO section-coverage signal in freshness output (deferred to
  thermia per D5).
- **NG6**: NO env-matrix audit (deferred to thermia per D7).
- **NG7**: NO documenting cache_warmer Lambda schedule (deferred to thermia
  per D10).
- **NG8**: NO freshness SLA enforcement (publish-blocking gates).

## §3 Decision Boundary (10x-dev | thermia)

The boundary table below is binding: any concern in the right column is
**out of scope** for the 10x-dev sprint and must be carried forward in the
handoff dossier (per §8).

| 10x-dev (in scope this sprint)                                                            | thermia (deferred)                                                                                |
|-------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| Metrics CLI freshness output (`src/autom8_asana/metrics/__main__.py`)                     | cache_warmer Lambda schedule + per-section TTL (`src/autom8_asana/lambda_handlers/cache_warmer.py`) |
| New module `src/autom8_asana/metrics/freshness.py` (FreshnessReport + S3 mtime read)      | Re-warm orchestration + freshness SLA enforcement                                                 |
| `.know/env-loader.md` stakeholder-affirmation addendum                                    | AWS bucket-tagging IaC + legacy `AUTOM8Y_ENV` cleanup                                             |
| Static handoff dossier with section-classifier-vs-parquet diff (read-only)                | Section-coverage telemetry + Asana drift reconciliation                                           |
| Telos `verified_realized` ATTESTED-PENDING-THERMIA declaration                            | Telos `verified_realized` attestation (or sre fallback per D8)                                    |
| QA per D11 — live prod + mocked edges                                                     | Production canary observation post-deploy                                                         |

## §4 User Stories

### US-1 — Default-mode freshness emission

**As** an operator running `python -m autom8_asana.metrics active_mrr`,
**I want** the dollar-figure line emitted verbatim PLUS a freshness block,
**so that** I can assess data currency without changing my invocation.

- **AC-1.1**: Default mode preserves the dollar-figure line byte-for-byte
  (`\n  active_mrr: $NN,NNN.NN\n`, leading newline, two-space indent).
- **AC-1.2**: Below the dollar figure, a single additive line appears:
  `parquet mtime: oldest=YYYY-MM-DD HH:MM UTC, newest=YYYY-MM-DD HH:MM UTC, max_age=Nd Nh Nm`.
- **AC-1.3**: When the threshold is not breached, exit code is `0`.

### US-2 — Stale-threshold WARNING + strict promotion

**As** a CI gate consumer,
**I want** stale data to surface as a non-zero exit under `--strict`,
**so that** stale invocations cannot pass green silently.

- **AC-2.1**: When `max_age > threshold`, stderr emits
  `WARNING: data older than {threshold_human} (max_age={observed_human})`.
- **AC-2.2**: Default mode exits `0` regardless of WARNING.
- **AC-2.3**: With `--strict`, WARNING promotes to exit `1`.
- **AC-2.4**: Invalid `--staleness-threshold` spec (e.g. `"6 hours"`,
  `"1h30m"`, `"6"`) emits `ERROR: invalid duration spec '...': expected
  formats Ns/Nm/Nh/Nd ...` to stderr and exits `1`. Boundary: equality
  (`max_age == threshold`) is **fresh**, not stale (strict `>` comparison).

### US-3 — `--json` envelope

**As** a downstream tool,
**I want** a single structured JSON envelope on stdout,
**so that** I can parse value + freshness + provenance without text-wrangling.

- **AC-3.1**: `--json` emits a single envelope:
  `{schema_version, metric, value, currency, freshness:{oldest_mtime,
   newest_mtime, max_age_seconds, threshold_seconds, stale, parquet_count},
   provenance:{bucket, prefix, env, evidence}}`.
- **AC-3.2**: Under `--json`, the human dollar-figure line is **suppressed**
  on stdout (per `__main__.py:243` guard); WARNING still goes to stderr.
- **AC-3.3**: Envelope is `json.dumps(..., sort_keys=True)` deterministic;
  ISO-8601 UTC datetimes formatted with `Z` suffix.
- **AC-3.4**: For a given S3 state at a given moment, repeated invocations
  produce byte-identical envelope (modulo `max_age_seconds` drift driven by
  per-invocation `datetime.now(tz=UTC)` capture — see TDD §5).

### US-4 — IO failure surfacing

**As** an operator,
**I want** auth/network/not-found failures to surface as actionable stderr
lines and non-zero exit,
**so that** I can fix the underlying issue without parsing tracebacks.

- **AC-4.1**: Auth failure (NoCredentialsError, AccessDenied, 403,
  InvalidAccessKeyId, SignatureDoesNotMatch) → stderr
  `ERROR: S3 freshness probe failed (auth): could not authenticate against
  s3://{bucket}/{prefix} — {underlying!r}`.
- **AC-4.2**: Not-found (NoSuchBucket, NoSuchKey, 404) → stderr
  `ERROR: S3 freshness probe failed (not-found): s3://{bucket}/{prefix}
  does not exist — {underlying!r}`.
- **AC-4.3**: Network (EndpointConnectionError, ReadTimeoutError,
  ConnectTimeoutError) → stderr
  `ERROR: S3 freshness probe failed (network): could not reach
  s3://{bucket}/{prefix} — {underlying!r}`.
- **AC-4.4**: All IO failures exit `1` regardless of `--strict`
  (IO failure is structurally non-strict-gated).
- **AC-4.5**: Under `--json`, IO failure emits stderr line and exits `1`
  with **no JSON envelope on stdout** (the FreshnessError catch-block
  precedes the json_mode emission branch in `__main__.py:288-294`).

### US-5 — Zero-result-set distinction

**As** an operator,
**I want** "no parquets found at prefix" and "parquets present but zero
rows after filter+dedup" to be distinguishable in stderr,
**so that** I can diagnose cache-population vs filter/dedup issues.

- **AC-5.1**: `parquet_count == 0` → stderr
  `ERROR: no parquets found at s3://{bucket}/{prefix}` and exit `1`
  unconditionally (regardless of `--strict`). This is structurally an
  IO-layer failure (per TDD §3.4).
- **AC-5.2**: Parquets present, `len(result) == 0` after filter+dedup →
  stderr `WARNING: zero rows after filter+dedup for metric '{metric.name}'`;
  default mode exit `0`; with `--strict` exit `1`.
- **AC-5.3**: The stderr text differs between AC-5.1 and AC-5.2 — operators
  can disambiguate from stderr alone.
- **AC-5.4**: When zero-result-set fires, the dollar-figure line still
  emits as `$0.00` (not `N/A`). `N/A (no data)` is reserved for the
  None-aggregation path (mean/min/max on empty DataFrame).

### US-6 — Thermia rite engineer opens dossier with confidence

**As** a thermia rite engineer engaging the handoff,
**I want** the dossier to contain the 8 sections enumerated below,
**so that** I can scope my work without round-tripping clarifying questions.

- **AC-6.1**: The handoff dossier at
  `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-{date}.md` contains, in this
  order:
  1. Classifier ACTIVE-section list (file:line anchor to `activity.py`)
  2. Parquet section list (verbatim `aws s3 ls` capture, ISO-8601 mtimes)
  3. Per-section mtime histogram (sidecar JSON)
  4. Bucket→env stakeholder-affirmation citation (PRD §6 C-1 cross-ref)
  5. cache_warmer schedule open question (D10)
  6. Section-coverage deferral rationale (D5; empty-sections-are-expected)
  7. Env-matrix legacy-cruft inventory (D7; `rg -n` capture)
  8. Telos handoff + attester fallback condition (D8)
- **AC-6.2**: The dossier conforms to the schema at
  `.ledge/specs/handoff-dossier-schema.tdd.md` (12-field frontmatter,
  11-line refusal-clause checklist, INDEX entry appended).

## §5 Success Metrics

- **SM-1**: 100% of CLI invocations under default + `--json` modes surface
  a freshness signal (oldest_mtime, newest_mtime, max_age) — verified by
  test suite (`tests/unit/metrics/test_freshness*.py`) and live-prod
  dogfood (QA Phase B).
- **SM-2**: Latency overhead of the freshness probe < 2 seconds against
  `s3://autom8-s3/dataframes/1143843662099250/sections/` (14 parquets, one
  `list_objects_v2` page).
- **SM-3**: Thermia rite engineer reads the dossier and proceeds without
  clarifying questions to the originating rite (verified by zero
  back-routes at procession kickoff).
- **SM-4**: `--json` envelope validates against the stable JSON Schema
  (`additionalProperties: false`, draft-2020-12) declared in TDD §4.2,
  with `schema_version: 1`.
- **SM-5**: QA-adversary edges (75 freshness-specific tests + 13
  adversarial classes per QA report Phase C/D/E) all pass.
- **SM-6**: Default-mode output preserves the existing
  `\n  active_mrr: $94,076.00\n` line **byte-for-byte** (verified by
  `od -c` byte-dump in QA Phase B.1 + regression test
  `tests/unit/metrics/test_freshness_s3.py::TestSm6BackwardsCompat`).

## §6 Constraints

- **C-1**: **CANARY-IN-PRODUCTION**. The ecosystem has standardized on a
  single production cache bucket (`autom8-s3`); there are no multi-env
  cache buckets. The legacy `AUTOM8Y_ENV` token is cruft of an earlier
  multi-env era and is scheduled for thermia/hygiene cleanup per D7.
  Bucket→env binding is established by stakeholder affirmation (D6), NOT
  by IaC introspection.

  **Structural verification receipt (D6 affirmation)**:
  - source: `session-20260427-154543-c703e121`
  - event: pre-PRD interview Q2.2 / D6
  - user: `tom@tenuta.io`
  - date: 2026-04-27
  - marker_token: "Bucket autom8-s3 IS the production cache bucket
    (stakeholder affirmation by user tom@tenuta.io on 2026-04-27)"

- **C-2**: **BACKWARDS COMPATIBILITY**. Default-mode output MUST be a
  strict superset of pre-T6 emission. The dollar-figure line must remain
  `\n  active_mrr: $NN,NNN.NN\n` verbatim — leading `\n`, two-space indent,
  lowercase `active_mrr`, colon, dollar amount. Regex-anchored downstream
  consumers must continue to parse correctly.

- **C-3**: **BRANCH ISOLATION**. All work occurs in the
  `.worktrees/active-mrr-freshness/` worktree on branch
  `feat/active-mrr-freshness-signal`. No cross-worktree mutations.

- **C-4**: NO `cache_warmer.py` modifications by 10x-dev. The Lambda owns
  cache population; the metrics CLI owns cache **read** + freshness
  signaling only.

- **C-5**: **DEDUP LOGIC PRESERVED VERBATIM**. The
  `dedup_keys=["office_phone", "vertical"]` setting at
  `src/autom8_asana/metrics/definitions/offer.py:23` is empirically
  verified (cross-check vs `parent_gid` dedup yields identical 71-row /
  `$94,076.00` result; zero over- or under-counting). This sprint does
  NOT touch dedup semantics.

- **C-6**: **EMPTY SECTIONS ARE NOT A FAILURE SIGNAL**. The cache_warmer
  Lambda writes parquet only for sections that contain tasks; an empty
  section is **by-design** behavior, not a coverage gap. Therefore
  `--strict` does NOT promote section-count-diff to non-zero exit (per D3).
  Classifier-vs-parquet diffs are informational, not failure conditions.

## §7 Telos Declaration

Per `telos-integrity-ref` §2 — three gates with rite-disjoint attestation:

- **inception**: INSCRIBED (this PRD, framed 2026-04-27).
- **frame_artifact**: `.ledge/specs/verify-active-mrr-provenance.prd.md`.
- **shipped_definition**:
  - `src/autom8_asana/metrics/freshness.py` (FreshnessReport, S3 listing,
    duration parser, output formatters)
  - `src/autom8_asana/metrics/__main__.py` (CLI integration: 3 new flags,
    additive lines, exit-code matrix)
  - `.know/env-loader.md` (stakeholder-affirmation addendum)
  - `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` (dossier)
  - `.ledge/handoffs/2026-04-27-section-mtimes.json` (sidecar)
  - `.ledge/handoffs/INDEX.md` (single-line entry)
- **verified_realized_definition**: in-anger-dogfood — the operator runs
  `python -m autom8_asana.metrics active_mrr --strict` against the
  `autom8-s3` production bucket and observes:
  - the freshness lines emitted on stdout below the dollar figure;
  - non-zero exit when stale (current data is ≈32d stale, threshold default
    is 6h, so `--strict` exits 1);
  - `--json` envelope validates against the schema in TDD §4.2;
  - the receiving thermia engineer reads the dossier and advances P1
    without clarifying questions.
- **verification_method**: in-anger-dogfood.
- **verification_deadline**: 2026-05-27.
- **rite_disjoint_attester**:
  - **primary**: `thermia.verification-auditor` (per D8 — see §3 boundary
    table). Receiving rite has authority to map this role to its closest
    pantheon-fit agent.
  - **fallback**: `sre.incident-commander` OR `sre.observability-engineer`
    (per D8 fallback predicate; activates iff thermia rite is not
    registered in the platform manifest at handoff time).
- **attestation_status**:
  - inception: **INSCRIBED**
  - shipped: **UNATTESTED** (will become ATTESTED at T7 commit by
    principal-engineer signing)
  - verified_realized: **UNATTESTED** (discharged by thermia primary OR
    sre fallback by `verification_deadline`)

## §8 Rite-Handoff Scaffold

The handoff envelope is a structured artifact, not an inline PRD section
(see ADR-002 for the locality decision).

- **Handoff artifact path**:
  `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-{YYYY-MM-DD}.md`.
- **Handoff type**: `implementation` per the `cross-rite-handoff` skill's
  type contract (12 frontmatter fields).
- **INDEX entry**: a single-line append to
  `.ledge/handoffs/INDEX.md` discoverable by `grep` or `cat` at the
  fleet level.
- **Required body sections**: 8 sections per US-6 AC-6.1 above.
- **Refusal-clause gate**: 11-line checklist per
  `.ledge/specs/handoff-dossier-schema.tdd.md` §3 (no aspirational tokens;
  all anchors `file:line`; all open questions verifiable predicates).

## §9 Decision Provenance (D1–D11)

All 11 decisions were resolved in the pre-PRD stakeholder interview; this
PRD does NOT contain an "open questions" phase.

| ID  | Decision                                                                          | Disposition         | Anchor                                |
|-----|-----------------------------------------------------------------------------------|---------------------|---------------------------------------|
| D1  | Should freshness be emitted by default or opt-in?                                 | DEFAULT (G1, US-1)  | §2 G1, §4 US-1                        |
| D2  | Configurable threshold or fixed?                                                  | CONFIGURABLE (6h)   | §2 G2, §4 US-2 AC-2.4                 |
| D3  | `--strict` semantics — what does it gate?                                         | (a)+(b)+(c) NOT section-diff | §2 G3, §6 C-6              |
| D4  | JSON envelope shape                                                               | nested per AC-3.1   | §4 US-3, TDD §4                       |
| D5  | Section-coverage signal in/out?                                                   | DEFERRED to thermia | §2 NG5, §3 boundary table             |
| D6  | Bucket→env mapping — IaC or stakeholder-affirmation?                              | STAKEHOLDER (D6)    | §6 C-1, §2 G5                         |
| D7  | Env-matrix legacy-cruft (AUTOM8Y_ENV, multi-env bucket pattern)                   | DEFERRED to thermia | §2 NG6, §3 boundary table             |
| D8  | Telos `verified_realized` attester — thermia primary, sre fallback?               | YES (primary+fallback) | §7 telos block                     |
| D9  | Default threshold value                                                           | 6h                  | §4 US-2 (default in `__main__.py:179`)|
| D10 | cache_warmer schedule + per-section TTL — document or defer?                      | DEFERRED to thermia | §2 NG7, §3 boundary table             |
| D11 | QA scope — full live-prod or sample?                                              | LIVE-PROD + MOCKED  | §3 boundary table, QA Phase B + C     |

## §10 Out-of-Scope (explicit non-decisions)

The following are explicitly **out of scope** for this PRD:

- Force-warm CLI affordance (deferred per NG4).
- Section-coverage signal (deferred per NG5 / D5).
- Env-matrix audit + AUTOM8Y_ENV cleanup (deferred per NG6 / D7).
- cache_warmer Lambda schedule documentation (deferred per NG7 / D10).
- Freshness SLA enforcement (publish-blocking gates) — deferred per NG8;
  this PRD ships the **signal**, not the enforcement.
- Asana-side section-drift reconciliation — deferred per NG2.
- Terraform/IaC reading for bucket-tagging — deferred per NG3.
- Documenting `cache_warmer` Lambda schedule — deferred per NG7.

---

*Authored by requirements-analyst, session-20260427-154543-c703e121,
2026-04-27. Reconstructed by thermia procession P0 pre-flight,
session-20260427-185944-cde32d7b, on 2026-04-27 from sources enumerated
in the frontmatter `reconstruction:` block.*
