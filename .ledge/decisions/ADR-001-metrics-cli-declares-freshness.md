---
type: decision
artifact_type: ADR
adr_id: ADR-001
initiative_slug: verify-active-mrr-provenance
session_id: session-20260427-154543-c703e121
phase: design
authored_by: principal-architect
authored_on: 2026-04-27
branch: feat/active-mrr-freshness-signal
worktree: .worktrees/active-mrr-freshness/
title: Metrics CLI declares data-source freshness alongside scalar value
status: accepted
companion_prd: verify-active-mrr-provenance.prd.md
companion_tdd: freshness-module.tdd.md
reconstruction:
  status: RECONSTRUCTED-2026-04-27
  reason: original lost to **/.ledge/* gitignore during predecessor 10x-dev sprint
  reconstructed_by: thermia procession P0 pre-flight (general-purpose dispatch)
  source_evidence:
    - src/autom8_asana/metrics/freshness.py (T6 implementation — ground truth)
    - src/autom8_asana/metrics/__main__.py (T6 CLI integration — ground truth)
    - .ledge/specs/verify-active-mrr-provenance.prd.md (PRD §3, §6 C-1+C-2+C-4, §7)
    - .ledge/reviews/QA-T9-verify-active-mrr-provenance.md (cites companion_adr in frontmatter)
    - .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md (refers ADR-001 by initiative)
    - conversation memory of architect-phase authoring
---

# ADR-001 — Metrics CLI declares data-source freshness alongside scalar value

## Status

**Accepted** — 2026-04-27. Implemented in commits `09cc368e` (T6 — module
+ CLI integration) and `ce565759` (T7 — wiring polish).

## Context

The `active_mrr` metric (and, by extension, every metric in the
`autom8_asana.metrics` registry) is computed from cached parquet datasets
written by `src/autom8_asana/lambda_handlers/cache_warmer.py` to
`s3://autom8-s3/dataframes/{project_gid}/sections/`. The CLI consumer
sees only the resulting scalar — e.g. `$94,076.00` — with **no runtime
signal** indicating whether that scalar represents current Asana state or
a snapshot from weeks ago.

Empirically (PRD §1), the section parquets at handoff date span 32 days
of staleness:

- newest: `1143843662099257.parquet` @ 2026-04-27T14:01:10Z
- oldest: `1155403608336729.parquet` @ 2026-03-26T04:17:44Z

The defect class is **provenance-gap, not computational error**: the
dedup logic at `src/autom8_asana/metrics/definitions/offer.py:23`
(`dedup_keys=["office_phone", "vertical"]`) is empirically verified
correct (PRD §6 C-5). The gap is the missing freshness signal between
cache and consumer.

Decision-grade financial metrics cannot ride on opaque-freshness data.

## Decision

The metrics CLI (`src/autom8_asana/metrics/__main__.py`) emits a
data-source freshness signal alongside every scalar value, by default.

Concretely:

1. **New module** `src/autom8_asana/metrics/freshness.py` exposes a
   `FreshnessReport` dataclass + `from_s3_listing` factory that reads
   per-key `LastModified` from a `list_objects_v2` paginator (one round
   trip; SM-2 budget `<2s`).

2. **CLI integration** in `__main__.py` adds three flags:
   - `--strict` — promote stale-threshold / IO-failure / zero-result-set
     warnings to non-zero exit.
   - `--staleness-threshold <duration>` — configurable threshold; default
     `6h`. Duration spec: `Ns/Nm/Nh/Nd`.
   - `--json` — emit a single structured envelope to stdout instead of
     human-readable lines.

3. **Default-mode output** preserves the existing dollar-figure line
   `\n  active_mrr: $NN,NNN.NN\n` byte-for-byte (PRD C-2 / SM-6) and
   appends one additive line below it:
   `parquet mtime: oldest=YYYY-MM-DD HH:MM UTC, newest=..., max_age=...`.

4. **`--json` envelope** is a stable JSON Schema (TDD §4.2,
   `schema_version: 1`, `additionalProperties: false`) carrying the
   metric value, the freshness signal, and provenance (bucket, prefix,
   env, evidence-citation token).

5. **IO failures** (auth, not-found, network) surface as actionable
   stderr lines and exit `1`, regardless of `--strict`. The
   `FreshnessError.kind` attribute (one of `auth/not-found/network/unknown`)
   maps deterministically to AC-4.1 / AC-4.2 / AC-4.3 stderr text.

## Alternatives considered

### Rejected: Side-channel telemetry only

> Emit freshness exclusively as structured telemetry (e.g. Cloudwatch
> metric, Datadog tag); do not surface it on the CLI.

- Fails US-1 (human operator running the CLI ad hoc must read freshness
  without leaving the terminal).
- Fails the consultative principle that decision-grade output must carry
  provenance **at the point of consumption**, not in a side channel.
- Telemetry would still be valuable as a complement, but cannot replace
  the in-band signal.

### Rejected: `--show-freshness` opt-in flag

> Make the freshness signal opt-in behind a `--show-freshness` flag;
> default mode unchanged.

- Violates G7 in spirit: by default, the operator sees a number with
  unknown freshness — exactly the status quo defect.
- The cost of opting out for the rare consumer who genuinely doesn't
  want the signal is one extra line of stdout, far smaller than the
  cost of opaque-by-default for every other consumer.

### Rejected: Modify the dollar-figure line itself

> Encode freshness into the dollar-figure line (e.g.,
> `active_mrr: $94,076.00 (32d stale)`).

- Breaks PRD C-2 (BACKWARDS COMPATIBILITY): regex-anchored downstream
  consumers parsing the dollar figure would fail.
- The SM-6 byte-fidelity invariant (`\n  active_mrr: $NN,NNN.NN\n`)
  exists precisely to insulate downstream consumers from format churn.

### Accepted: Additive lines below dollar-figure (default) + structured envelope (`--json`) + strict promotion (`--strict`)

- Default mode: dollar-figure line preserved byte-for-byte; freshness
  appears as an **additive line below**. Backwards-compatible.
- `--json`: single envelope replaces the human format on stdout
  (warnings still go to stderr). Structured-consumer-friendly.
- `--strict`: opt-in semantic for CI gates that must reject stale data.

## Consequences

### Positive

- Every metrics CLI invocation surfaces a freshness signal — provenance
  no longer opaque.
- Stable JSON Schema (`schema_version: 1`) gives downstream tools a
  versioned contract.
- `--strict` enables CI gates without perturbing default-mode operators.
- Backwards-compat preserved (regex-anchored consumers continue to
  parse the dollar figure correctly).
- Implementation footprint is small: one new module + small CLI patch.

### Negative

- Every CLI invocation now makes one S3 `list_objects_v2` call — adds
  ≈100–300ms latency in the happy path.
- The `--json` schema becomes a public contract; future evolution is
  gated by `schema_version` bumps + ADRs (per TDD §6).
- The CLI now requires `s3:ListBucket` permission against the cache
  bucket — slight permission-surface increase. Empirically a non-issue
  for production-affirmed bucket per PRD §6 C-1 (the CLI already
  reads parquets via `load_project_dataframe`; listing is permission-
  adjacent to reading).

### Neutral

- Thermia receives a clean handoff dossier (per ADR-002) rather than an
  ad-hoc note. Cross-rite envelope formalized.
- The `verified_realized` telos gate cannot be self-attested by 10x-dev
  per Axiom 1; thermia (or sre fallback) discharges per PRD §7.

## Anchors

- PRD §3 Decision Boundary (10x-dev | thermia)
- PRD §6 C-1 (CANARY-IN-PRODUCTION + stakeholder affirmation)
- PRD §6 C-2 (BACKWARDS COMPATIBILITY / SM-6 byte-fidelity)
- PRD §6 C-4 (NO cache_warmer modifications by 10x-dev)
- PRD §7 (Telos declaration + verified_realized gate)
- TDD `freshness-module.tdd.md` §1 (Module API)
- TDD `freshness-module.tdd.md` §3.5 (Exit-code matrix)
- TDD `freshness-module.tdd.md` §4 (JSON envelope schema)
- `src/autom8_asana/metrics/freshness.py` (entire module — implementation)
- `src/autom8_asana/metrics/__main__.py` (CLI integration: flags lines
  165-189, freshness probe lines 271-294, exit resolution lines 309-342)
- `.ledge/reviews/QA-T9-verify-active-mrr-provenance.md` (Phase B
  in-anger-dogfood evidence)

---

*Authored by principal-architect, session-20260427-154543-c703e121,
2026-04-27. Reconstructed by thermia procession P0 pre-flight,
session-20260427-185944-cde32d7b, on 2026-04-27.*
