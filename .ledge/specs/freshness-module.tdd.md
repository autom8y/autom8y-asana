---
type: spec
artifact_type: TDD
initiative_slug: verify-active-mrr-provenance
session_id: session-20260427-154543-c703e121
phase: design
authored_by: principal-architect
authored_on: 2026-04-27
branch: feat/active-mrr-freshness-signal
worktree: .worktrees/active-mrr-freshness/
title: Freshness module — API surface, S3 access, CLI integration, JSON schema
status: accepted  # T6/T7 commits 09cc368e + ce565759 land this design
companion_prd: verify-active-mrr-provenance.prd.md
companion_adr: ADR-001-metrics-cli-declares-freshness.md
reconstruction:
  status: RECONSTRUCTED-2026-04-27
  reason: original lost to **/.ledge/* gitignore during predecessor 10x-dev sprint
  reconstructed_by: thermia procession P0 pre-flight (general-purpose dispatch)
  source_evidence:
    - src/autom8_asana/metrics/freshness.py (T6 implementation — ground truth)
    - src/autom8_asana/metrics/__main__.py (T6 CLI integration — ground truth)
    - tests/unit/metrics/test_freshness.py (T6 unit tests, 324 lines)
    - tests/unit/metrics/test_freshness_s3.py (T6 integration tests, 390 lines)
    - tests/unit/metrics/test_freshness_adversarial.py (T8 adversarial, 750 lines)
    - .ledge/reviews/QA-T9-verify-active-mrr-provenance.md (Phase B/C/D probes)
    - .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md (cites §1, §3.5, §4.2, §6.5)
    - conversation memory of architect-phase authoring
---

# TDD — freshness-module

> [RECONSTRUCTED-2026-04-27] — The merged code at
> `src/autom8_asana/metrics/freshness.py` is the load-bearing ground truth
> for this design. Where this TDD differs from the code, **the code wins**;
> any such drift is a TDD-update candidate, not a design intent.

## §1 Module API

The module `src/autom8_asana/metrics/freshness.py` exposes the following
public surface (all signatures verified against merged source):

### §1.1 `FreshnessReport` dataclass

```python
@dataclass(frozen=True)
class FreshnessReport:
    oldest_mtime: datetime          # tz-aware UTC
    newest_mtime: datetime          # tz-aware UTC
    max_age_seconds: int            # int(now - oldest_mtime).total_seconds(); clamped >= 0
    threshold_seconds: int          # carried from caller; used to derive `stale`
    parquet_count: int              # number of .parquet keys observed
    bucket: str
    prefix: str

    @property
    def stale(self) -> bool: ...    # max_age_seconds > threshold_seconds (strict >)
```

- **Frozen** + **hashable** — supports memoization and use in test parametrization.
- All datetimes are **timezone-aware UTC** (`datetime.now(tz=UTC)`).
- `stale` is a derived predicate, exposed as an attribute so consumers do
  not re-derive the comparison.
- **Boundary**: `stale` uses **strict `>`** comparison — equality is
  fresh, not stale. Verified by `test_freshness.py::TestFreshnessReportStaleProperty::test_at_threshold_fresh`.

### §1.2 Sentinel report for empty prefix

When the S3 listing yields zero `.parquet` keys, the factory returns a
**sentinel** report with:
- `oldest_mtime = newest_mtime = _EPOCH_UTC` (1970-01-01T00:00:00Z)
- `parquet_count = 0`
- `max_age_seconds = int((now - _EPOCH_UTC).total_seconds())` (numerically
  extreme staleness)

The CLI integration layer (§3.4) detects `parquet_count == 0` and emits the
empty-prefix error per AC-5.1, regardless of `--strict`.

### §1.3 Factory: `from_s3_listing`

```python
@classmethod
def from_s3_listing(
    cls,
    bucket: str,
    prefix: str,
    threshold_seconds: int,
    *,
    s3_client: Any | None = None,    # injectable for tests
    now: datetime | None = None,     # injectable for deterministic tests
) -> FreshnessReport:
```

- If `s3_client` is None, constructed via
  `boto3.client("s3", region_name=os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1"))`
  (same region resolution pattern as `dataframes/offline.py`).
- If `now` is None, `datetime.now(tz=UTC)` is captured at call time.
- Boto3 imported lazily inside the method to keep the module importable in
  environments where boto3 may not be available at import.

### §1.4 `FreshnessError` exception class

```python
class FreshnessError(Exception):
    KIND_AUTH = "auth"
    KIND_NOT_FOUND = "not-found"
    KIND_NETWORK = "network"
    KIND_UNKNOWN = "unknown"

    def __init__(self, kind: str, bucket: str, prefix: str, underlying: BaseException):
        ...
```

- Single exception class for all S3 access failures; the `kind` attribute
  is one of the four string constants above.
- The CLI integration layer (`__main__.py:_emit_freshness_io_error`) maps
  `kind` → AC-4.1 / AC-4.2 / AC-4.3 stderr lines.

### §1.5 Duration spec parser: `parse_duration_spec`

```python
def parse_duration_spec(s: str) -> int:
```

- Accepts: `Ns`, `Nm`, `Nh`, `Nd` where N is a positive integer.
- Examples: `"90s" → 90`, `"30m" → 1800`, `"6h" → 21600`, `"1d" → 86400`.
- Whitespace tolerance: leading/trailing whitespace stripped; whitespace
  between digits and unit tolerated (`"6 h" → 21600`).
- No support for composite forms (`"1h30m"` rejected).
- Case-sensitive: uppercase `"6H"` rejected.
- `N == 0` rejected (degenerate threshold makes every observation stale).
- Raises `ValueError` with actionable message: `invalid duration spec
  '{s}': expected formats Ns/Nm/Nh/Nd (e.g., '6h', '30m', '1d', '90s')`.

### §1.6 Duration formatter: `format_duration`

```python
def format_duration(seconds: int) -> str:
```

- `seconds < 60`           → `"Ns"`        (e.g., `"45s"`, `"0s"`)
- `60 <= seconds < 3600`   → `"Nm"`        (e.g., `"1m"`, `"59m"`)
- `3600 <= seconds < 86400`→ `"Nh Nm"`     (e.g., `"1h 0m"`, `"23h 59m"`)
- `seconds >= 86400`       → `"Nd Nh Nm"`  (e.g., `"32d 10h 36m"`)

**Arithmetic correction** (recorded as Eng-A in the QA report Phase D):
`2802960s = 32d 10h 36m` (not `32d 10h 56m` as a draft TDD example
incorrectly stated). The merged `test_freshness.py:117` binds to the
correct value `"32d 10h 36m"`.

### §1.7 Output formatters

```python
def format_human_lines(report: FreshnessReport) -> list[str]:
def format_json_envelope(
    report: FreshnessReport, value: float | None, metric_name: str,
    currency: str, env: str, bucket_evidence: str,
) -> dict[str, Any]:
def format_warning(report: FreshnessReport) -> str:
```

- `format_human_lines` returns a single-element list:
  `["parquet mtime: oldest=YYYY-MM-DD HH:MM UTC, newest=..., max_age=..."]`
  (datetimes at minute granularity).
- `format_json_envelope` returns a JSON-serializable dict (no datetime
  objects); the dict serializes deterministically via
  `json.dumps(envelope, sort_keys=True)`.
- `format_warning` returns the AC-2.1 stderr line:
  `"WARNING: data older than {threshold_human} (max_age={observed_human})"`.

## §2 S3 Access

### §2.1 Listing strategy: `list_objects_v2` paginator (NOT `head_object`)

The factory uses the `list_objects_v2` paginator to enumerate keys under
`{prefix}`. Per-key `LastModified` is read directly from the listing — no
`head_object` round-trip per key. This bounds the call to **one page** for
the observed cache (14 parquets), satisfying SM-2 (`<2s` overhead).

```python
paginator = s3_client.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        if not key.endswith(".parquet"):
            continue              # filter sub-directory markers, .json, etc.
        mtime = obj.get("LastModified")
        if mtime is None:
            continue
        # min/max accumulator
```

### §2.2 Error mapping

| boto3 / botocore exception                          | `FreshnessError.kind` | AC mapping |
|-----------------------------------------------------|-----------------------|------------|
| `NoCredentialsError`                                | `auth`                | AC-4.1     |
| `ClientError("AccessDenied" / "403" / "InvalidAccessKeyId" / "SignatureDoesNotMatch")` | `auth` | AC-4.1 |
| `ClientError("NoSuchBucket" / "NoSuchKey" / "404")` | `not-found`           | AC-4.2     |
| `EndpointConnectionError`                           | `network`             | AC-4.3     |
| `ReadTimeoutError`                                  | `network`             | AC-4.3     |
| `ConnectTimeoutError`                               | `network`             | AC-4.3     |
| `ClientError(<other code>)`                         | `unknown`             | catch-all  |
| `Exception` (catch-all)                             | `unknown`             | catch-all  |

Each `kind` is wrapped in `FreshnessError(kind, bucket, prefix, underlying)`
and re-raised from the factory.

### §2.3 Latency budget

- Observed cache: 14 parquets in one page.
- Single `list_objects_v2` round-trip latency: typically 100–300 ms.
- Budget: < 2 seconds (SM-2). No retry/backoff at the freshness layer —
  failures fail-fast to the operator.

## §3 CLI integration (`__main__.py`)

### §3.1 New argparse flags

```python
parser.add_argument("--strict", action="store_true", ...)
parser.add_argument("--staleness-threshold", default="6h", ...)
parser.add_argument("--json", action="store_true", dest="json_mode", ...)
```

**Latent decision #4** (recorded in QA Phase D): `dest="json_mode"` is
required to avoid shadowing the stdlib `json` module that was already
imported in the file. Tests in `test_main.py::TestArgsJsonShadow` verify
the dest mapping by source introspection.

### §3.2 Pre-S3 validation order

1. Parse `--staleness-threshold` via `parse_duration_spec` → `threshold_seconds`.
   If the spec is invalid: stderr `ERROR: {message}`, exit `1`.
2. Resolve metric registration; resolve project GID.
3. Run CLI preflight (`_preflight_cli_profile` per ADR-0001 / TDD-0001-cli-preflight-contract).
4. `load_project_dataframe(project_gid)`.
5. Compute metric (existing code path).
6. Emit dollar-figure line (default mode) or skip (json_mode).
7. **Build FreshnessReport** via `FreshnessReport.from_s3_listing(...)`.
8. **Empty-prefix check** (§3.4).
9. Emit envelope or human lines (§3.3).
10. Emit WARNINGs (§3.3).
11. Resolve exit code (§3.5).

### §3.3 Output ordering (default mode)

```
stdout:
  Loaded {N} rows from project {project_gid}
  Unique ({dedup_keys}) combos: {len(result)}
  \n
    {metric.name}: ${value:,.2f}                  ← preserved byte-for-byte (SM-6)
  parquet mtime: oldest=..., newest=..., max_age=...   ← additive (AC-1.2)

stderr (when stale):
  WARNING: data older than {threshold_human} (max_age={observed_human})
```

Under `--json`:
- Dollar-figure suppressed (`if not args.json_mode:` guard at line 243 + 268).
- Single envelope on stdout (`json.dumps(envelope, sort_keys=True, indent=2)`).
- WARNING still goes to stderr.

### §3.4 Empty-prefix vs zero-result-set distinction

Two structurally-distinct conditions, with **different stderr text** (per
QA Phase C.6):

| Condition                                       | stderr text                                                                         | Exit                       |
|-------------------------------------------------|-------------------------------------------------------------------------------------|----------------------------|
| `report.parquet_count == 0` (empty prefix)      | `ERROR: no parquets found at s3://{bucket}/{prefix}`                                | `1` always (no `--strict` gate) |
| `len(result) == 0` (parquets present, dedup empty) | `WARNING: zero rows after filter+dedup for metric '{metric.name}'`              | `0` default; `1` strict    |

Operators can disambiguate the two from stderr text alone (per AC-5.3).

### §3.5 Exit-code matrix (7 conditions × 2 modes)

| #  | Condition                                      | Default mode exit | Strict mode exit |
|----|------------------------------------------------|-------------------|------------------|
| 1  | Fresh (max_age <= threshold), parquets present | `0`               | `0`              |
| 2  | Stale (max_age > threshold)                    | `0` (WARNING)     | `1` (WARNING)    |
| 3  | Zero result set after filter+dedup             | `0` (WARNING)     | `1` (WARNING)    |
| 4  | Stale + zero result set                        | `0` (2 WARNINGs)  | `1` (2 WARNINGs) |
| 5  | Empty prefix (parquet_count == 0)              | `1` (ERROR)       | `1` (ERROR)      |
| 6  | IO error (auth/not-found/network/unknown)      | `1` (ERROR)       | `1` (ERROR)      |
| 7  | Invalid `--staleness-threshold` spec           | `1` (ERROR)       | `1` (ERROR)      |

**Exit code 2 is RESERVED for CLI preflight contract violations** (per
TDD-0001-cli-preflight-contract / ADR-0001 / CFG-006). The freshness module
NEVER emits exit code 2 — `2` exclusively means "preflight contract
violation" (e.g., missing `ASANA_CACHE_S3_BUCKET`).

**Latent decision #2** (QA Phase D): the exit-2-is-preflight-only
discipline is recorded in `__main__.py:64-117` (preflight emits 2);
freshness branches at lines 290 / 299 / 338 all emit `1`.

### §3.6 `--json` IO-failure rule (AC-4.5)

The `FreshnessError` catch-block at `__main__.py:288-294` runs **before**
the `if args.json_mode:` emission branch. Therefore an IO failure under
`--json` emits the stderr ERROR line and exits `1` with **no JSON envelope
on stdout**. Verified by code inspection in QA Phase C.8.

## §4 JSON envelope schema

### §4.1 Literal example (verified in QA Phase B.5)

```json
{
  "currency": "USD",
  "freshness": {
    "max_age_seconds": 2805956,
    "newest_mtime": "2026-04-27T12:01:10Z",
    "oldest_mtime": "2026-03-26T03:17:44Z",
    "parquet_count": 14,
    "stale": true,
    "threshold_seconds": 21600
  },
  "metric": "active_mrr",
  "provenance": {
    "bucket": "autom8-s3",
    "env": "production",
    "evidence": "stakeholder-affirmation-2026-04-27",
    "prefix": "dataframes/1143843662099250/sections/"
  },
  "schema_version": 1,
  "value": 94076.0
}
```

- Top-level keys (alphabetical under `sort_keys=True`):
  `currency, freshness, metric, provenance, schema_version, value`.
- Datetimes: ISO-8601 UTC with `Z` suffix, second granularity
  (`%Y-%m-%dT%H:%M:%SZ`).
- `value` is `null` (JSON) for the None-aggregation case
  (mean/min/max on empty DataFrame); `float` otherwise.

### §4.2 Draft-2020-12 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "metric", "value", "currency", "freshness", "provenance"],
  "properties": {
    "schema_version": {"type": "integer", "const": 1},
    "metric":         {"type": "string"},
    "value":          {"type": ["number", "null"]},
    "currency":       {"type": "string"},
    "freshness": {
      "type": "object",
      "additionalProperties": false,
      "required": ["oldest_mtime", "newest_mtime", "max_age_seconds",
                   "threshold_seconds", "stale", "parquet_count"],
      "properties": {
        "oldest_mtime":      {"type": "string", "format": "date-time"},
        "newest_mtime":      {"type": "string", "format": "date-time"},
        "max_age_seconds":   {"type": "integer", "minimum": 0},
        "threshold_seconds": {"type": "integer", "minimum": 1},
        "stale":             {"type": "boolean"},
        "parquet_count":     {"type": "integer", "minimum": 0}
      }
    },
    "provenance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["bucket", "prefix", "env", "evidence"],
      "properties": {
        "bucket":   {"type": "string"},
        "prefix":   {"type": "string"},
        "env":      {"type": "string"},
        "evidence": {"type": "string"}
      }
    }
  }
}
```

- `schema_version: 1`. Minor changes (additive optional fields) do NOT
  bump; breaking changes (rename/remove/required-add) bump → ADR.
- `additionalProperties: false` on top level + `freshness` + `provenance` —
  ensures no silent extras leak into downstream consumers.

### §4.3 Latent decision #3 — schema fields beyond the PRD AC

The PRD AC-3.1 enumerated the conceptual envelope shape, but during
architect phase three additional fields were added for downstream
operability:

- `schema_version` — versioning hook for future evolution.
- `parquet_count` — let downstream tools verify the cache populated as
  expected without re-listing.
- `provenance.prefix` — full S3 path reproducibility from the envelope alone.

All three are required (per QA Phase D Latent #3 verification).

## §5 Determinism

- **Invalid duration spec**: deterministic stderr message containing
  `invalid duration spec` and `Ns/Nm/Nh/Nd` substrings; exit `1`.
- **Repeated invocations against unchanged S3**: byte-identical envelope
  modulo `max_age_seconds` drift driven by per-invocation
  `datetime.now(tz=UTC)` capture (engineer's `__main__.py` does NOT pin
  `now` — this is by design; `--json` is decision-grade-fresh, not
  artifact-stable).
- **Fixed `now` parameter** (test path): byte-identical envelope. Verified
  by `test_freshness.py::TestFormatJsonEnvelope` and QA Phase C.11.
- **`json.dumps(envelope, sort_keys=True)`**: alphabetical key order;
  ISO-8601 UTC with `Z` suffix.
- **Clock-skew clamp**: when `now < min_mtime` (clock skew), the factory
  clamps `max_age_seconds = 0` (and therefore `stale = False`),
  preventing negative durations. Verified by QA Phase E.6.

## §6 Test surface

### §6.1 Unit tests (`tests/unit/metrics/test_freshness.py`, 324 lines)

- `TestFreshnessReportStaleProperty` — strict `>` comparison; equality is
  fresh; equality+1 is stale.
- `TestParseDurationSpec` — valid set (`"6h", "1d", "30m", "90s",
  " 6h ", "6 h", "\t1d\n"`) + invalid set (`"", "1h30m", "6 hours",
  "-6h", "6", "h", "6x", "0s", "0h", "0d", "6H", "6D", "abc", "h6",
  "6.5h"`).
- `TestFormatDuration` — all four bands (s/m/h+m/d+h+m); arithmetic
  correction `2802960s == "32d 10h 36m"` (line 117).
- `TestFormatHumanLines` — minute-granularity datetime formatting.
- `TestFormatJsonEnvelope` — sort_keys determinism + literal envelope.
- `TestFormatWarning` — AC-2.1 stderr line shape.

### §6.2 Integration tests (`tests/unit/metrics/test_freshness_s3.py`, 390 lines)

- `TestFromS3Listing` — moto/botocore.stub-backed S3; verifies min/max
  accumulator + non-parquet filtering + multi-page paginator.
- `TestErrorMapping` — `NoCredentialsError`, `AccessDenied`,
  `NoSuchBucket`, `EndpointConnectionError` → correct `kind`.
- `TestSm6BackwardsCompat` — runs the CLI as a subprocess against live S3
  + matches captured stdout against the SM-6 byte-fidelity regex.

### §6.3 Adversarial tests (`tests/unit/metrics/test_freshness_adversarial.py`, 750 lines, 52 tests)

13 test classes per QA Phase D coverage:

1. `TestDurationParserAdversarial` (Phase C.3)
2. `TestClockSkewAndExtremeFormatting` (Phase E.6 + format extremes)
3. `TestJsonEnvelopeSchemaValidation` (Phase C.4 jsonschema)
4. `TestLatentDecisionVerification` (#1 + #3 codification)
5. `TestIoErrorMappingAtCliIntegration` (Phase C.7 + C.8)
6. `TestEmptyPrefixVsZeroResultSet` (Phase C.5 + C.6)
7. `TestComposability` (Phase C.9 / B.6)
8. `TestEnvelopeDeterminism` (Phase C.11)
9. `TestExitCodeDistinction` (Phase D L#2 — preflight=2 vs freshness=1)
10. `TestArgsJsonShadow` (Phase D L#4)
11. `TestLatent5StderrDistinction` (Phase D L#5)
12. `TestLatent7SentinelPattern` (Phase D L#7)
13. `TestArithmeticCorrection` (Phase D Eng-A)

### §6.4 Live tests

Live S3 tests are gated behind `AUTOM8_LIVE_AWS_TESTS=1`. Default test
runs use moto / botocore.stub. The QA Phase B in-anger-dogfood probes are
the canonical live-prod evidence.

### §6.5 SM-6 byte-fidelity regression

The dollar-figure line `\n  active_mrr: $NN,NNN.NN\n` is regex-anchored
in `test_freshness_s3.py::TestSm6BackwardsCompat`:

```python
regex = re.compile(rb"\n {2}active_mrr: \$\d{1,3}(,\d{3})*\.\d{2}\n")
assert regex.search(captured_stdout) is not None
```

Verified live in QA Phase B.1 via `od -c` byte-dump.

## §7 Path Conventions Normalization

All file:line anchors throughout this TDD use the `src/autom8_asana/...`
prefix (per repository convention). Anchors that previously appeared as
`autom8_asana/...` (without the `src/` prefix) are normalized.

Verified anchors:
- `src/autom8_asana/metrics/freshness.py` — module under test
- `src/autom8_asana/metrics/__main__.py` — CLI integration
- `src/autom8_asana/metrics/definitions/offer.py:23` — dedup_keys (PRD §1)
- `src/autom8_asana/lambda_handlers/cache_warmer.py:1` — out-of-scope per C-4
- `src/autom8_asana/models/business/activity.py:76` — classifier sections_for
- `src/autom8_asana/models/business/activity.py:317` — CLASSIFIERS dict
- `src/autom8_asana/dataframes/offline.py` — region resolution pattern
- `tests/unit/metrics/test_freshness.py` — unit tests
- `tests/unit/metrics/test_freshness_s3.py` — integration tests
- `tests/unit/metrics/test_freshness_adversarial.py` — adversarial tests

---

*Authored by principal-architect, session-20260427-154543-c703e121,
2026-04-27. Reconstructed by thermia procession P0 pre-flight,
session-20260427-185944-cde32d7b, on 2026-04-27. Ground truth: the
merged code at `src/autom8_asana/metrics/freshness.py`.*
