---
type: spec
artifact_type: ADR
status: accepted
adr_number: 005
adr_id: ADR-005
title: TTL manifest YAML schema + S3 sidecar JSON contract
authored_by: 10x-dev.architect
authored_on: 2026-04-27
session_id: session-20260427-205201-668a10f4
parent_initiative: cache-freshness-impl-from-thermia-2026-04-27
schema_version: 1
worktree: .worktrees/cache-freshness-impl/
branch: feat/cache-freshness-impl-2026-04-27
companion_handoff: .ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md
companion_specs:
  - .ledge/specs/cache-freshness-capacity-spec.md
  - .ledge/specs/cache-freshness-architecture.tdd.md
companion_adrs:
  - .ledge/decisions/ADR-003-memorytier-post-force-warm-staleness.md
discharges:
  - thermia HANDOFF §1 work-item-3 (TTL persistence implementation)
  - thermia HANDOFF §3 LD-P3-1 layered persistence with override precedence
  - P3 capacity-spec §2.3 deferred-to-P2 persistence-mechanism question
---

# ADR-005 — TTL manifest YAML schema + S3 sidecar JSON contract

## Status

**Accepted** — 2026-04-27. Engineer dispatch can proceed; the schema
shapes below are normative for AC-3 in HANDOFF §4.

## Context

Thermia HANDOFF §3 LD-P3-1 resolves the per-section TTL persistence
question to "layered persistence with override precedence":

- **Default canonical persistence**: manifest at
  `.know/cache-freshness-ttl-manifest.yaml` (version-controlled, YAML)
- **Runtime override**: S3 sidecar at
  `s3://autom8-s3/dataframes/{project_gid}/cache-freshness-ttl.json`
- **Precedence**: S3 sidecar > manifest > built-in defaults (4-class
  table)

The HANDOFF declares the load-bearing fields ("per-section: `section_gid`,
`sla_class`, `threshold_seconds`") and assigns the engineer to "implement
both" (HANDOFF §1 work-item-3, §3 LD-P3-1, §4 AC-3). The decision the
HANDOFF defers to architect: **the precise schema shape, validation
contract, file-format conventions, and additive-evolution boundary
between the two formats**.

If the engineer is left to invent the schema during implementation, the
silent design choices made will be irreversible-without-migration. YAML
permits string-vs-int ambiguity for `threshold_seconds`. JSON permits
extension fields without warning. The list-of-records vs map-of-records
shape is a one-way door once consumers ship. This ADR closes the schema
question before the engineer touches a file.

### What the design substrate constrains

The 4-class TTL taxonomy is **frozen** by HANDOFF §3 FLAG-2 / LD-P2-1:
class enum = `active|warm|cold|near-empty` (lowercase, hyphenated for
`near-empty`). Default thresholds:

| Profile | Threshold seconds | Source |
|---|---|---|
| `active` | 21600 (6h) | P3 §2.2 ACTIVE-class |
| `warm` | 43200 (12h) | P3 §2.2 WARM-class |
| `cold` | 86400 (24h) | P3 §2.2 COLD-class |
| `near-empty` | 604800 (7d) | P3 §2.2 Near-empty-class |

Section identification is by Asana GID (string of decimal digits, e.g.
`1143843662099257`). The current production scope is a single project
GID (`1143843662099250` per HANDOFF §4 AC-3) with 14 sections.

Read-time constraints from HANDOFF §3 LD-P3-1:
- Warmer reads sidecar **at warm time** (per-warm S3 GET acceptable;
  not per-task)
- CLI reads manifest **at startup** (single read; cached for process
  lifetime)
- Sidecar absence MUST fall back to manifest cleanly (no error)

Per-warm GET cost is bounded: at 4h cadence × 1 project = 6 sidecar
GETs/day. At $0.0004/1,000 S3 GETs (us-east-1 standard tier), monthly
sidecar GET cost = `$0.0000007/month`. Negligible.

## Decision

**Two formats with a shared logical schema; explicit precedence rule;
forward-compatible additive evolution.**

The manifest file is YAML (human-edited, version-controlled in the
worktree). The S3 sidecar is JSON (machine-written, optimized for AWS
SDK round-tripping). Both formats encode the same logical schema. The
precedence rule is simple: any (project_gid, section_gid) pair present
in the sidecar overrides the same pair in the manifest; both fall back
to built-in 4-class defaults if absent.

### Logical schema (format-agnostic)

```
TtlManifest:
  schema_version: int   # 1 at this ADR; required
  generated_at:   str   # ISO-8601 UTC; required (manifest only — sidecar omits)
  generator:      str   # identifier of the tool that emitted the file; required (manifest only)
  default_class:  str   # one of {active, warm, cold, near-empty}; optional; default "active"
  projects:       map<project_gid_str, ProjectTtl>  # required, may be empty

ProjectTtl:
  project_gid:    str   # Asana GID, decimal digit string; required
  sections:       map<section_gid_str, SectionTtl>  # required, may be empty

SectionTtl:
  section_gid:        str   # Asana GID, decimal digit string; required
  sla_class:          str   # enum {active, warm, cold, near-empty}; required
  threshold_seconds:  int   # positive integer; required
  notes:              str   # free-text; optional
```

### Manifest format (YAML — `.know/cache-freshness-ttl-manifest.yaml`)

```yaml
# .know/cache-freshness-ttl-manifest.yaml
schema_version: 1
generated_at: "2026-04-27T14:00:00Z"
generator: "autom8_asana.metrics.sla_profile.bootstrap"
default_class: active

projects:
  "1143843662099250":
    project_gid: "1143843662099250"
    sections:
      "1143843662099257":
        section_gid: "1143843662099257"
        sla_class: active
        threshold_seconds: 21600
        notes: "active_mrr-driving section; force-warm cadence 4h"
      "1143843662099256":
        section_gid: "1143843662099256"
        sla_class: warm
        threshold_seconds: 43200
      "1204152425074370":
        section_gid: "1204152425074370"
        sla_class: near-empty
        threshold_seconds: 604800
        notes: "Near-empty (~2.4 KB) — weekly warm cycle"
```

### Sidecar format (JSON — `s3://autom8-s3/dataframes/{project_gid}/cache-freshness-ttl.json`)

```json
{
  "schema_version": 1,
  "project_gid": "1143843662099250",
  "sections": {
    "1143843662099257": {
      "section_gid": "1143843662099257",
      "sla_class": "active",
      "threshold_seconds": 21600
    },
    "1143843662099256": {
      "section_gid": "1143843662099256",
      "sla_class": "warm",
      "threshold_seconds": 43200
    }
  }
}
```

The sidecar is **single-project-scoped** by S3 path
(`{project_gid}/cache-freshness-ttl.json`), so the top-level JSON
object omits the multi-project `projects` map and instead carries the
project as a sibling key. This avoids redundancy between the path and
payload.

### Override precedence (normative)

For every (project_gid, section_gid, field) lookup at warm time or CLI
startup:

1. **If sidecar exists at `s3://autom8-s3/dataframes/{project_gid}/cache-freshness-ttl.json`
   AND it contains an entry for `section_gid` AND that entry's
   `schema_version` is `1`**: use the sidecar entry's
   `(sla_class, threshold_seconds)`.
2. **Else if manifest at `.know/cache-freshness-ttl-manifest.yaml` exists
   AND `projects[project_gid].sections[section_gid]` is present**: use
   the manifest entry.
3. **Else**: apply built-in default — `sla_class = manifest.default_class`
   (or `active` if manifest absent), `threshold_seconds` = the canonical
   4-class value (21600 / 43200 / 86400 / 604800).

Sidecar absence MUST NOT raise an error. Sidecar parse error MUST NOT
short-circuit the lookup chain — the warmer logs a `WARN` and falls
through to step 2 (treat sidecar as absent).

### Validation contract

Both files are validated against the schema at read time. The single
validator implementation lives at the engineer-chosen module (suggestion
per HANDOFF: `src/autom8_asana/metrics/sla_profile.py` or
`src/autom8_asana/cache/sla_profile.py`).

**Validator rules** (executable invariants):

V-1. `schema_version` MUST be present and MUST equal `1` at this ADR
     altitude. Future schema versions are additive (see "Additive
     evolution" below); a reader at version N reads files at versions
     ≤ N and errors loudly on N+1.

V-2. `sla_class` MUST be one of `active|warm|cold|near-empty`. Any
     other value MUST raise a parse error (NOT a warning). This is
     load-bearing per HANDOFF FLAG-2 4-class canonicalization.

V-3. `threshold_seconds` MUST be a positive integer (>0). Floats MUST
     be rejected at parse time (YAML `1.5` → error; even `21600.0` →
     error). Negative values MUST be rejected. Zero MUST be rejected
     (a zero-threshold section would always read as stale and produce
     spurious alerts).

V-4. `section_gid` and `project_gid` MUST be strings. YAML's int-vs-
     string ambiguity is a known foot-gun for Asana GIDs (16-digit
     decimal); engineer enforces by `str()` cast on read AND by
     quoting GIDs in YAML keys per the example above. Validator
     rejects bare-integer GIDs at parse time.

V-5. `(project_gid, section_gid)` pair uniqueness — duplicate keys in
     YAML/JSON map collapse to last-write-wins per format spec; the
     validator MUST log a warning if pre-collapse duplicates are
     detected (engineer adds duplicate-detection during YAML/JSON
     parse where the parser surface allows).

V-6. **Cross-validation** — if `threshold_seconds` deviates from the
     canonical 4-class value for the declared `sla_class`, the
     validator emits a `WARN` (NOT an error) noting the deviation.
     Operators may intentionally tune individual sections; the warning
     surfaces the asymmetry for review.

### Additive evolution

The schema MUST tolerate forward-additive evolution. Future ADRs
(post-2026-04-27) MAY add new optional fields or new top-level keys
without bumping `schema_version`. Examples:

- Adding a `last_classified_by` audit field to `SectionTtl` — additive,
  no version bump.
- Adding a `last_warmed_at` watermark to `SectionTtl` for self-describing
  manifest — additive, no version bump.
- Adding a `policies` block at the top level for future class-level
  overrides — additive, no version bump.

`schema_version` increments only when:
- A required field is added.
- An existing field's type changes (e.g., `threshold_seconds` becomes
  string).
- An enum value is removed (e.g., dropping `cold` would be a breaking
  change).
- The override-precedence rule changes.

The engineer codifies this in the validator's "unknown field" handling:
unknown fields are tolerated (YAML/JSON parse permits them; validator
does not reject them).

### Worked example — full lifecycle

**Initial state** (post-bootstrap, no operator override):

`.know/cache-freshness-ttl-manifest.yaml`:

```yaml
schema_version: 1
generated_at: "2026-04-27T14:00:00Z"
generator: "autom8_asana.metrics.sla_profile.bootstrap"
default_class: active

projects:
  "1143843662099250":
    project_gid: "1143843662099250"
    sections:
      "1143843662099257":
        section_gid: "1143843662099257"
        sla_class: active
        threshold_seconds: 21600
      "1143843662099256":
        section_gid: "1143843662099256"
        sla_class: warm
        threshold_seconds: 43200
      "1204152425074370":
        section_gid: "1204152425074370"
        sla_class: near-empty
        threshold_seconds: 604800
      "1209233681691558":
        section_gid: "1209233681691558"
        sla_class: cold
        threshold_seconds: 86400
```

No sidecar in S3.

CLI invocation `python -m autom8_asana.metrics active_mrr` reads the
manifest at startup, looks up section `1143843662099257` → sidecar
absent → manifest hit → `(active, 21600)`. The freshness probe uses
21600s as the staleness ceiling.

**Operator override** (operator wants section `1143843662099256` to be
warmed every 6h temporarily — pre-launch warmup window):

Operator writes to S3:

```bash
aws s3 cp - s3://autom8-s3/dataframes/1143843662099250/cache-freshness-ttl.json <<'EOF'
{
  "schema_version": 1,
  "project_gid": "1143843662099250",
  "sections": {
    "1143843662099256": {
      "section_gid": "1143843662099256",
      "sla_class": "active",
      "threshold_seconds": 21600,
      "notes": "Pre-launch warmup; revert to warm-class after 2026-05-01"
    }
  }
}
EOF
```

Next CLI invocation reads the sidecar first; lookup for
`1143843662099256` → sidecar hit → `(active, 21600)`. The manifest's
`(warm, 43200)` is overridden. Section `1143843662099257` is unaffected
(absent from sidecar; falls through to manifest).

The operator deletes the sidecar to revert:

```bash
aws s3 rm s3://autom8-s3/dataframes/1143843662099250/cache-freshness-ttl.json
```

Next read: sidecar absent → manifest hit → `(warm, 43200)`. Override
window is closed.

**All four classes worked example** (full taxonomy validation):

```yaml
projects:
  "1143843662099250":
    project_gid: "1143843662099250"
    sections:
      "1143843662099257":
        section_gid: "1143843662099257"
        sla_class: active
        threshold_seconds: 21600
      "1143843662099256":
        section_gid: "1143843662099256"
        sla_class: warm
        threshold_seconds: 43200
      "1209233681691558":
        section_gid: "1209233681691558"
        sla_class: cold
        threshold_seconds: 86400
      "1204152425074370":
        section_gid: "1204152425074370"
        sla_class: near-empty
        threshold_seconds: 604800
```

Validator passes — all four `sla_class` values are recognized, all
`threshold_seconds` match canonical defaults, all GIDs are quoted
strings, `schema_version` is 1.

## Rationale

1. **YAML manifest, JSON sidecar — formats matched to consumers**.
   The manifest is human-edited (operator declares per-section TTL
   classes once; reviewed in PR; lives in `.know/`). Humans read YAML
   better than JSON. The sidecar is machine-written (operator runs
   `aws s3 cp` or scripts use the AWS SDK). The AWS SDK serializes JSON
   natively without a YAML dependency. Format-per-consumer reduces
   implementation surface.

2. **Map-keyed-by-GID over list-of-records**. The schema uses
   `sections: map<section_gid_str, SectionTtl>` not
   `sections: list<SectionTtl>`. Map-keyed shape gives O(1) lookup
   without list-traversal in the hot path. It also makes
   "section X has TTL declared" and "this is the unique declaration
   for X" structurally identical (no need for runtime uniqueness
   validation on a list). The slight redundancy of the GID appearing
   as both key and field is intentional — the field permits the
   record to round-trip independent of map context.

3. **`schema_version: 1` at the top — explicit forward-evolution
   contract**. Without `schema_version`, any future field addition is
   ambiguous between "additive" and "breaking." With it, the rule is
   explicit: same-version readers tolerate unknown fields; cross-
   version readers error loudly. This is the standard contract for
   forward-compatible config.

4. **Override precedence is sidecar > manifest, NOT manifest >
   sidecar**. The runtime override semantic is "operators can
   temporarily change behavior without a code change." That requires
   the runtime artifact (sidecar) to win over the static artifact
   (manifest). The reverse precedence would make the sidecar useless
   for its stated purpose.

5. **Sidecar absence MUST NOT error**. The sidecar is the override
   case; the manifest is the canonical case. A missing sidecar is
   the normal state, not an error. The fallback chain is engineered
   so that the warmer survives all combinations of {sidecar present,
   manifest present, neither present}.

6. **Validator rejects floats and bare-int GIDs at parse time**. The
   YAML int-vs-string ambiguity for Asana GIDs is a documented
   project-wide foot-gun (16-digit decimal strings parse as ints in
   YAML 1.1, lose precision in some langs). The validator codifies
   string-only GIDs as a hard-stop rule at the persistence boundary,
   not the consumer boundary, to fail fast.

7. **Cross-validation is a WARN, not an error**. Operators may
   intentionally set `sla_class: warm, threshold_seconds: 6h` to
   pin a warm-classified section to active-class freshness. This is
   a legitimate operational pattern. Erroring on the deviation
   would over-constrain operators; warning preserves the signal
   without blocking.

## Consequences

### Positive

- Engineer's AC-3 work is unambiguous at the schema level. The
  validator implementation, the read paths, and the fallback chain
  are all specified. No re-decision during implementation.
- Forward-additive evolution is preserved. Future ADRs can extend
  the schema (add `last_warmed_at` audit field, add `policies`
  block, etc.) without breaking deployed readers at version 1.
- Operator override pattern is testable. The worked example above
  is directly runnable post-deploy as a P7 in-anger probe.
- Cost envelope is bounded. Sidecar GET cost ≈ $0.0000007/month at
  4h × 1 project; manifest read is per-CLI-invocation (file-system
  read; negligible).

### Negative

- Two read paths to maintain (S3 sidecar + filesystem manifest)
  instead of one. Mitigation: both go through a single
  `resolve_sla(project_gid, section_gid) -> (sla_class, threshold)`
  surface so consumers see one API.
- YAML int-vs-string foot-gun requires explicit defensive coding.
  Mitigation: validator V-4 catches it at parse time with a clear
  error message; example file in this ADR uses quoted GID keys
  consistently.
- Schema version field discipline depends on future ADRs respecting
  it. Mitigation: the rule is stated in this ADR's "Additive
  evolution" section; engineer's validator emits the rule
  verbatim in its docstring as a permanent reminder.

### Neutral

- Sidecar JSON has a different shape than manifest YAML at the top
  level (sidecar is single-project, omitting the `projects` map;
  manifest is multi-project). Mitigation: the worked example shows
  both shapes side-by-side; the validator's two paths handle this
  asymmetry.

## Alternatives considered

### REJECTED: Single format (YAML or JSON only)

- **Pro**: One parser, one validator, one read path.
- **Con**: YAML in S3 requires a YAML dependency in the warmer
  Lambda's deployment artifact (currently uses JSON via the AWS SDK
  by default). JSON in `.know/` produces friction for human editing
  (no comments, more punctuation noise).
- **Con**: Format-mismatch reduces clarity at the boundary. The
  manifest's "human-edited" intent is reinforced by YAML; the
  sidecar's "machine-round-trip" intent is reinforced by JSON.

### REJECTED: List-of-records shape (`sections: [{...}, {...}]`)

- **Pro**: Marginally simpler in YAML for hand-editing (no
  duplicated GID).
- **Con**: O(N) lookup on read; uniqueness validation must be
  manual.
- **Con**: Adds a uniqueness invariant the validator must enforce
  (list with two records having same `section_gid` is a silent bug
  if validator misses it).

### REJECTED: Embed TTL state in S3 object metadata

- **Pro**: Self-contained per-parquet; no separate file to manage.
- **Con**: S3 object metadata is mutable only via a full PUT (which
  rewrites the parquet). Operator override via metadata edit
  requires a parquet rewrite — defeats the cost model and adds a
  long-tail risk of metadata-vs-content drift.
- **Con**: P3 capacity-spec §2.3 already enumerated this option
  ("S3 metadata sidecar") and rejected it for the same write-
  amplification reason. This ADR honors that rejection.

### REJECTED: CloudWatch metric per section as the TTL store

- **Pro**: Integrates with existing observability stack.
- **Con**: CloudWatch is a metric store, not a configuration store.
  Round-tripping `(sla_class, threshold)` through metric dimensions
  is technically possible but semantically confused; the operator
  cannot easily reason about "what is the current TTL setting" by
  looking at CloudWatch.
- **Con**: P3 §2.3 enumerated this option and recommended it for
  monitoring (which is downstream — observability spec covers it),
  not for TTL persistence (which is upstream — this ADR's scope).

### REJECTED: No manifest, sidecar-only

- **Pro**: Simpler — one source of truth.
- **Con**: Loss of version-control discipline. The TTL classification
  for each section is a non-trivial design decision (which sections
  are ACTIVE-driving for active_mrr? which are near-empty?) that
  benefits from PR review and audit trail.
- **Con**: Bootstrap problem — first deploy must hand-write 14
  sidecars in S3 with no pre-validation; manifest enables CI-time
  validation.

### REJECTED: No sidecar, manifest-only

- **Pro**: Simpler — file-system source of truth, no S3 round-trip
  in the warmer.
- **Con**: Loses the runtime-override capability. Operators would
  need to PR + deploy to change a TTL, which is the opposite of the
  HANDOFF LD-P3-1 stated requirement.
- **Con**: Warmer Lambda would need to bundle the manifest into its
  deployment artifact, breaking the single-source-of-truth invariant
  (manifest in `.know/` has to be propagated to Lambda via build).
  Sidecar-in-S3 sidesteps this entirely.

## Anchors

### Substrate this discharges

- HANDOFF §1 work-item-3 (TTL persistence implementation):
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:71-77`
- HANDOFF §3 LD-P3-1 (layered persistence resolution):
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:280-303`
- HANDOFF §4 AC-3 (acceptance criteria):
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:389-403`
- P3 capacity-spec §2.2 4-class TTL derivation:
  `.ledge/specs/cache-freshness-capacity-spec.md:65-115`
- P3 capacity-spec §2.3 implementation options enumerated (this ADR
  selects "manifest + sidecar" hybrid):
  `.ledge/specs/cache-freshness-capacity-spec.md:117-128`

### FROZEN inheritances

- 4-class enum (FLAG-2 / LD-P2-1):
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:238-274`
- Default thresholds (21600/43200/86400/604800):
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:267-274`

### PRD constraints honored

- PRD §6 C-1 canary-in-prod (sidecar path is single-bucket,
  single-project at current scope):
  `.ledge/specs/verify-active-mrr-provenance.prd.md:254-260`

---

*Authored by 10x-dev.architect, session-20260427-205201-668a10f4,
2026-04-27. Worktree
.worktrees/cache-freshness-impl/, branch
feat/cache-freshness-impl-2026-04-27. Discharges HANDOFF §1 work-item-3
TTL-schema-shape question via two-format hybrid with single logical
schema and explicit additive-evolution contract.*
