---
type: prd
initiative: project-asana-pipeline-extraction
phase: 1
sprint: sprint-1
created: 2026-04-28
rite: 10x-dev
specialist: requirements-analyst
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
upstream_artifacts:
  - .sos/wip/frames/project-asana-pipeline-extraction.md
  - .sos/wip/frames/project-asana-pipeline-extraction.shape.md
  - .sos/wip/frames/project-asana-pipeline-extraction.workflow.md
  - .ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md
  - .sos/wip/inquisitions/phase1-orchestration-touchstones.md
downstream_consumer: architect (Sprint 2)
verification_deadline: "2026-05-11"
rite_disjoint_attester: theoros@know
impact: high
impact_categories: [api_contract, auth, data_model]
---

# PRD — Phase 1 Pipeline Export Contract

## 1. Inception Context

### 1.1 Telos Pulse (verbatim, do not paraphrase)

> "A coworker's ad-hoc request to extract actionable account lists from
> Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana
> service: there is no first-class BI export surface, and any response today
> would be a one-off script with zero reusability. This initiative transitions
> from observation (Iris snapshot) to repeatable, account-grain, CSV-capable
> data extraction codified in the service's dataframe layer."

Source: `.sos/wip/frames/project-asana-pipeline-extraction.md:15`.

### 1.2 Throughline (Phase 1 contribution)

Phase 1 ships single-entity, dual-mount, parameterized export verifiable by
Vince reproducing his original Reactivation+Outreach CSV ask by 2026-05-11.
Phase 2 cross-entity work is deferred behind the HYBRID spike verdict; Phase 1
must not foreclose it.

Throughline carrier:
`.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:34-36`.

### 1.3 Spike Handoff Anchors (binding, cited path:line)

This PRD is the immediate downstream of the Phase 0 spike inquisition. The
binding verdict carrier and its load-bearing sections:

- **§3 verdict (HYBRID; boundary_predicate):**
  `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:111`
  (decision: hybrid; boundary_predicate at L157-184).
- **§5.1 Worked Example #1 (CASCADE-PATH inception-anchor):**
  `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:333-404`
  (Vince's Reactivation+Outreach query is the Phase 1 fixture).
- **§6 phase_1_constraints (P1-C-01..P1-C-07, FULL):**
  `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:514-637`.
- **§9 entry_conditions (EC-03 binds this PRD specifically):**
  `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:801-849`.

### 1.4 Stakeholder Map

| Role | Identity | Function in Phase 1 |
|---|---|---|
| Inception caller | Vince | Issued the original Reactivation+Outreach CSV ask; ultimate user-report attester for verified-realized telos at 2026-05-11. |
| Cross-rite attester | theoros@know | Rite-disjoint attestation per frame.telos.verified_realized_definition. |
| Downstream service caller (S2S) | Iris (and equivalent S2S tooling) | Co-equal first-class caller per dual-mount throughline. |
| Downstream user caller (PAT) | Vince's tooling and equivalent PAT clients | Co-equal first-class caller per dual-mount throughline. |
| Implementation specialists | architect (Sprint 2) → principal-engineer (Sprint 3) → qa-adversary (Sprint 4) | Read this PRD as their contract input. |


## 2. Scope (Single-Entity Hard-Lock)

### 2.1 In Scope (Phase 1)

A first-class export surface — mounted under both PAT and S2S routers — that
accepts a parameterized request scoped to a **single business entity**
(Phase 1 inception-anchor: `entity_type=process`), applies a caller-supplied
predicate over fields resolvable against that entity's warmed schema, and
returns the result in a caller-negotiated format (CSV, Parquet, JSON) with
account-grain rows deduped by the canonical identity key
`(office_phone, vertical)` and an `identity_complete` flag column on every
output row.

### 2.2 Out of Scope (Phase 2 territory; binding refusal)

The following are **explicitly Phase 2** per spike handoff
§6 P1-C-01 (`...:514-531`):

- Cross-entity joins. The ExportRequest contract MUST NOT include any field
  expressing cross-entity joins — no `join` field, no `target_entity` field,
  no `predicate_target_resolution` field.
- Engine dispatch classifier (`boundary_predicate` at handoff §3 L157-184).
  Phase 1 calls into the existing eager engine at
  `src/autom8_asana/query/engine.py:159-161`; no new dispatch logic.
- Modifications to `src/autom8_asana/query/engine.py:139-178`,
  `src/autom8_asana/query/engine.py:181`, or any line of
  `src/autom8_asana/query/join.py` (handoff §4 phase_1_must_not_touch
  at `...:311-321`).
- LEFT-preservation guard implementation (handoff §3 L201-237). Phase 1 does
  not implement it; Phase 1 contract reserves room for it (see §6 of this
  PRD — `predicate_join_semantics` reservation).
- PredicateNode AST shape changes beyond the date-operator extension lifted
  from `query/temporal.py` per shape §2 Sprint 2; per P1-C-03 the AST stays
  free-form (Comparison.field at `models.py:47` stays free-form string).
- CascadingFieldResolver behavior, cascade additions, or
  `_CASCADE_SOURCE_MAP` edits (parked SPIKE; out of scope).
- `reconciliation/section_registry.py` (SCAR-REG-001 out of scope per
  shape §7 emergent_behavior.out_of_scope).
- Scheduling/automation of CSV export.
- Cross-pipeline analytics beyond Reactivation+Outreach (Phase 1 anchor;
  generalization to other entities is structurally admitted by the
  entity-parameterized contract but not exercised in Phase 1 fixtures).

### 2.3 Single-Entity Discipline

Phase 1's contract is **entity-parameterized but single-entity per request**.
The `entity_type` field is required on every ExportRequest. The Phase 1
inception-anchor exercises `entity_type=process`. The contract does not
introduce a join surface (P1-C-01); each request resolves predicates against
exactly one entity's warmed schema.


## 3. ExportRequest Contract

### 3.1 Field Specification

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `entity_type` | string | yes | — | Canonical business-entity identifier. Phase 1 inception-anchor value: `"process"`. Entity-parameterized (any registered entity admissible) but single-entity per request (P1-C-01). |
| `project_gids` | list[int] | yes | — | minItems:1. Phase 1 anchor: `[1201265144487549, 1201753128450029]` (Reactivation, Outreach). Provider performs per-project load + union upstream of predicate. |
| `predicate` | PredicateNode \| null | no | null | Caller-supplied AST per existing union at `src/autom8_asana/query/models.py:27-123` (Comparison \| AndGroup \| OrGroup \| NotGroup). `Comparison.field` stays free-form per `models.py:47` (P1-C-03). null = no filter. |
| `format` | enum | no | `json` | Values: `json`, `csv`, `parquet`. Negotiated at `_format_dataframe_response` (`src/autom8_asana/api/routes/dataframes.py:111`); consumer-facing output is eager `pl.DataFrame` (P1-C-06). |
| `options` | object (**OPEN / ADDITIVE** — §6) | no | `{}` | Substructure MUST stay open per P1-C-02. Closed enums FORBIDDEN. Phase 1 names members below; Phase 2 may add additive members. |

**`predicate` operators:**
- Phase 1: all current `Op` enum values at `models.py:27-39`
  (EQ, NE, GT, LT, GTE, LTE, IN, NOT_IN, CONTAINS, STARTS_WITH).
- Sprint 2 additive (per shape §2 Sprint 2): BETWEEN, DATE_GTE, DATE_LTE,
  lifted from `src/autom8_asana/query/temporal.py`. AST shape unchanged;
  only Op enum gains additive members.
- Phase 1 forbidden in `Comparison.field`: cross-entity field references
  (e.g., `"offer.section"`); new PredicateNode subclasses; closed enums on
  `Comparison.field`.

**`options` Phase 1 members:**

| Member | Type | Default | Semantics |
|---|---|---|---|
| `include_incomplete_identity` | bool | `true` | When true, null-key rows surface with `identity_complete=false`. When false, those rows are filtered pre-serialization. Default `true` preserves SCAR-005/006 transparency (P1-C-05); opt-in suppression admitted but not engineering default. |
| `dedupe_key` | list[str] | `["office_phone", "vertical"]` | Account-grain dedup key matching frame Workstream II canonical identity. Caller-overridable for alternative grain. |

**`options` Phase 2 reservation:** `predicate_join_semantics` — NOT
present in Phase 1 (P1-C-02; see §6). Phase 2 type
`enum {preserve-outer, allow-inner-rewrite}`, default `preserve-outer`,
controls LEFT-preservation guard per spike handoff §3 L201-237.

**Fields explicitly ABSENT (P1-C-01 hard-lock):**
- `join` — Phase 2 cross-entity surface (handoff §4 phase_2_DSL_extensions
  at L305-309). Including in Phase 1 forecloses the boundary_predicate
  classifier (handoff §3 L157-184).
- `target_entity` — same rationale; P1-C-01 single-entity hard-lock.

### 3.2 Worked Example — Vince's Inception-Anchor Request

This is the verification fixture Sprint 3 PT-04 must reproduce
(spike handoff §5.1 at `...:333-404`):

```yaml
ExportRequest:
  entity_type: process
  project_gids: [1201265144487549, 1201753128450029]   # Reactivation, Outreach
  predicate:
    and:
      - field: section
        op: in
        value: ["ACTIVE", "EXECUTING", "BUILDING", "PROCESSING",
                "OPPORTUNITY", "CONTACTED"]   # ACTIVE-only per Q1 default
      - field: completed
        op: eq
        value: false
  format: csv
  options:
    include_incomplete_identity: true
    dedupe_key: ["office_phone", "vertical"]
```


## 4. Activity-State Parameterization

### 4.1 Vocabulary Source-of-Truth

The canonical activity-state vocabulary lives at
`src/autom8_asana/models/business/activity.py:282`
(`PROCESS_PIPELINE_SECTIONS`). The four classes are:

| Class | Section names (per `_DEFAULT_PROCESS_SECTIONS` at activity.py:282-303) |
|---|---|
| `active` | ACTIVE, EXECUTING, BUILDING, PROCESSING, OPPORTUNITY, CONTACTED |
| `activating` | SCHEDULED, REQUESTED, DELAYED |
| `inactive` | INACTIVE, DID NOT CONVERT, MAYBE, UNPROCESSED |
| `ignored` | TEMPLATE, TEMPLATES, COMPLETED, CONVERTED, TASKS, FREE MONTH, VIDEO ONLY, Untitled section |

### 4.2 Parameterization Discipline (NOT a server-side hardcoded constant)

**Binding rule:** the activity-state filter is a **caller-supplied subset over
the activity.py:282 vocabulary**, not a server-side hardcoded constant.

The route handler MUST NOT:
- Hardcode `active` as the only admissible class.
- Substitute its own activity-state predicate when the caller provides one.
- Silently drop sections the caller explicitly named.

The route handler MAY:
- Expose a default predicate when the caller omits the activity-state filter
  entirely (proposed default: `section IN active-class-sections`).
- Validate that section values supplied by the caller are members of the
  activity.py:282 vocabulary (with a clear error envelope if not — see §9).

### 4.3 Default Proposal (Q1 — see DEFER-WATCH-3)

Engineering proposal pending Vince elicitation (DEFER-WATCH-3, §10):

- **Default:** ACTIVE-only (frame.md L122-128 — the technically-defensible default).
- **Elective:** ACTIVATING (SCHEDULED, REQUESTED, DELAYED) inclusion is
  **caller-elective** — admissible when caller adds those sections to the
  predicate's `IN` list, but NEVER injected by the server.
- **Forbidden by default:** INACTIVE, IGNORED. Caller MAY override
  (e.g., to audit silently-ignored sections), but the default predicate
  excludes both classes.

This proposal is NOT engineering-authoritative — Q1 is in the DEFER-WATCH
list pending stakeholder confirmation.

### 4.4 Default-Suppression Detection: Whole-AST Walk (OR/NOT branches honored)

**Origin:** review rite Phase 1.1 remediation R-2 (DEF-05). This subsection
documents the existing implementation behavior so callers can predict the
default-injection decision when authoring composite predicates.

**Binding semantic:** when the caller-supplied predicate contains **any**
``Comparison(field="section", ...)`` clause **anywhere in the AST** —
including under ``OrGroup`` and ``NotGroup`` branches — the server-side
ACTIVE-only default is **NOT injected**, and the caller's full predicate is
honored as-given. Detection is implemented by
``predicate_references_field`` at
``src/autom8_asana/api/routes/_exports_helpers.py:213-225``, which walks the
predicate tree recursively across ``AndGroup``, ``OrGroup``, and
``NotGroup`` boundaries.

**Why this matters:** the §4.2 binding rule ("Substitute its own
activity-state predicate when the caller provides one" is forbidden)
applies to **any** caller-supplied section reference, not only
top-level ``AND``-joined references. A predicate like
``OR(section IN [INACTIVE], office_phone = "555")`` declares the caller's
intent to query INACTIVE sections; if the server detected only top-level
``AND`` references and injected ACTIVE on the OR branch, it would
**silently broaden** the result set in ways the caller did not write — a
P1-C-01-adjacent violation.

**Worked example A — OR branch:**

```yaml
predicate:
  or:
    - {field: section, op: in, value: [INACTIVE]}
    - {field: office_phone, op: eq, value: "555-0100"}
```

- ``predicate_references_field(predicate, "section")`` returns ``True``
  (the OR branch contains a section comparison).
- ``apply_active_default_section_predicate`` short-circuits at line
  ``_exports_helpers.py:240-241`` and returns
  ``(predicate, default_applied=False)``.
- The caller's predicate is forwarded verbatim. The result set includes
  INACTIVE rows AND rows matching ``office_phone = "555-0100"``,
  per the caller's OR semantics.
- The server **does not** wrap the predicate as
  ``AND(section IN [ACTIVE...], OR(...))``. Doing so would suppress the
  caller-named INACTIVE branch — exactly the P1-C-01-adjacent violation.

**Worked example B — NOT branch:**

```yaml
predicate:
  not:
    {field: section, op: in, value: [TEMPLATE, COMPLETED]}
```

- ``predicate_references_field`` recurses into the ``NotGroup`` and
  detects the section reference (line 223-224).
- Default-injection is suppressed; the caller's "every section EXCEPT
  TEMPLATE/COMPLETED" semantic is honored without server augmentation.

**Worked example C — section reference omitted (default fires):**

```yaml
predicate:
  and:
    - {field: office_phone, op: eq, value: "555-0100"}
    - {field: vertical, op: eq, value: "saas"}
```

- ``predicate_references_field`` returns ``False`` (no ``section``
  reference anywhere).
- ``apply_active_default_section_predicate`` injects
  ``AND(section IN [ACTIVE...], original predicate)`` and returns
  ``(new_predicate, default_applied=True)``. The caller's response meta
  echoes ``default_applied: true`` per §4.3 transparency.

**Caller guidance:** if the caller wants the ACTIVE-only default applied
**in addition to** an OR/NOT-scoped section query, they MUST express that
intent explicitly via top-level AND composition, e.g.
``AND(section IN [ACTIVE-class], OR(section IN [INACTIVE], ...))``. The
server will not synthesize this composition on the caller's behalf — the
parameterization discipline at §4.2 forbids it.

**Implementation citation:**
``apply_active_default_section_predicate`` at
``src/autom8_asana/api/routes/_exports_helpers.py:228-250`` +
``predicate_references_field`` at lines 213-225 (whole-AST walk).

## 5. ExportResponse / Output Schema

### 5.1 Row Grain

Account-grain rows. Deduplication applies the `dedupe_key` from
`ExportRequest.options.dedupe_key` (default `["office_phone", "vertical"]`
per frame Workstream II — frame.md L186-198). When multiple input rows
collapse to the same dedupe key, **a deterministic policy selects the
winning row** (DEFER-WATCH-1 — see §10).

### 5.2 Columns

Phase 1 minimum output columns (column projection is partially deferred —
see DEFER-WATCH-2):

| Column | Type | Source | Purpose |
|---|---|---|---|
| `office_phone` | str \| null | warmed `process` schema | Identity component 1 |
| `vertical` | str \| null | warmed `process` schema | Identity component 2 |
| `name` | str | warmed `process` schema | Account name (outreach hand-target) |
| `pipeline_type` | str | warmed `process` schema | Reactivation \| Outreach (or other entity-equivalent) |
| `section` | str | warmed `process` schema | Current funnel position |
| `gid` | str | warmed `process` schema | Asana task GID (provenance) |
| `identity_complete` | bool | **computed at extraction time** | See §5.3 |

Additional columns are caller-elicitable (DEFER-WATCH-2).

### 5.3 `identity_complete` Column (P1-C-05 binding)

**Semantics:**

```
identity_complete := (office_phone IS NOT NULL) AND (vertical IS NOT NULL)
```

**Source-of-truth (load-bearing per P1-C-05):** the column is computed at
**extraction time**, in the route handler or its formatter helper.

The column source-of-truth is **NOT** in any of:
- `src/autom8_asana/dataframes/extractors/cascade_resolver.py` (parked SPIKE).
- `src/autom8_asana/dataframes/builders/cascade_validator.py:46-176`
  (warmup-time only per P1-C-05; PROTO Evidence Trail #7).
- `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191`
  (`_CASCADE_SOURCE_MAP` — adding a new cascade column would touch this and
  destabilize the warmed-cache invariant; explicitly refused per P1-C-05).

**Transparency invariant (SCAR-005/006 throughline-binding):** rows with
`identity_complete=false` are NEVER silently dropped. They appear in the
output with the flag set false. The default `include_incomplete_identity`
is `true`. Opt-in suppression (caller sets `include_incomplete_identity:
false`) IS admitted, but is a caller-elected behavior — never an
engineering default.

### 5.4 Response Envelope (illustrative — final shape is architect's domain)

```yaml
ExportResponse:
  meta:
    request_id: <uuid>
    entity_type: <echo of request>
    format: <echo of request>
    row_count: <int>
    incomplete_identity_count: <int>   # observability for SCAR-005/006
    pagination:
      limit: <int>
      has_more: <bool>
      next_offset: <str | null>
  data:
    # CSV: text/csv body with header row including identity_complete
    # Parquet: application/vnd.apache.parquet binary body
    # JSON: list of objects, each with the columns from §5.2
```

The exact envelope shape (e.g., whether row_count and meta wrap CSV bodies
via headers vs. multipart) is the architect's domain (Sprint 2). The PRD
binds: every output row carries `identity_complete`, regardless of format.


## 6. `predicate_join_semantics` Reservation (P1-C-02 — load-bearing CRITICAL)

This section is binding. Closing the `options` substructure on a fixed enum
in Phase 1 is FORBIDDEN.

### 6.1 Phase 1 Position

Phase 1 does NOT include the `predicate_join_semantics` field in the
ExportRequest contract. The Phase 1 inception-anchor (Vince's
Reactivation+Outreach query) classifies as CASCADE-PATH per spike handoff
§5.1 — no join, no LEFT-rewrite risk, no field needed.

### 6.2 Forward-Compatibility Clause (BINDING)

The `options` substructure MUST remain open and additive. Acceptable
implementation patterns (architect chooses):

1. **Pydantic model with `extra='allow'`** — additive members admitted by
   the model without breaking-change validation errors.
2. **Open `dict[str, Any]`** — fully open substructure with documented
   member names.
3. **Pydantic model with documented forward-compatibility note** — closed
   schema BUT versioning policy explicitly admits additive members in a
   minor version without breaking change.

Whichever pattern is chosen, the contract documentation MUST state that
adding a new optional member to `options` is a non-breaking change.

### 6.3 Phase 2 Field Specification (FOR REFERENCE; NOT IN PHASE 1)

Per spike handoff §3 L227-237 (`...:227-237`) and §3 L201-237:

```yaml
options.predicate_join_semantics:
  type: enum
  values: [preserve-outer, allow-inner-rewrite]
  default: preserve-outer
  controls: |
    LEFT-preservation guard activation in the Phase 2 C5 path engine
    dispatch. preserve-outer enables post-EXPLAIN assertion + anti-join
    restoration; allow-inner-rewrite is the explicit caller opt-out.
```

### 6.4 Closed-Enum Refusal (BINDING)

A Phase 1 contract that uses a closed enum on `options` (e.g., a Pydantic
`model_config = ConfigDict(extra='forbid')` on the options model OR a
union-type `options` field with `extra='forbid'` semantics) FAILS PT-02
hard gate (shape §3 PT-02 question 4 implicit binding via P1-C-02).

The contract review checkpoint (PT-02) MUST verify: a future addition of
`options.predicate_join_semantics` does NOT require a new model version,
a contract-breaking change, or any caller migration path.

## 7. Dual-Mount Auth Surface (P1-C-07)

### 7.1 Binding Rule

The Phase 1 export route MUST mount under BOTH the PAT-secured and
S2S-secured routers. Asymmetric mounting (PAT-only or S2S-only) violates
the throughline ("every future PAT or S2S caller" — handoff §1 L34-36).

### 7.2 Precedent Citation (FleetQuery)

The dual-mount pattern is the FleetQuery precedent. Two anchor file:line
references:

- **FleetQuery dual-mount include site:** `main.py:414-415` (cited at
  spike handoff §6 P1-C-07 at `...:626-627`; shape §2 Sprint 2 prescribed
  emergent behavior).
- **Router factories:** `src/autom8_asana/api/routes/_security.py:37`
  (`pat_router`) and `src/autom8_asana/api/routes/_security.py:45`
  (`s2s_router`). The factories are the canonical construction point —
  the export route MUST be built by adding the route to a router instance
  produced by each factory, then including both router instances under the
  same path prefix in `main.py`.

### 7.3 Caller Identity Both First-Class

| Caller class | Auth scheme | Example consumer |
|---|---|---|
| PAT | PersonalAccessToken (PAT_BEARER_SCHEME at `_security.py:21-29`) | Vince's tooling, end-user clients |
| S2S | ServiceJWT (SERVICE_JWT_SCHEME at `_security.py:30-34`) | Iris and equivalent service-to-service callers |

Phase 1 MUST verify (via Sprint 4 QA fixture matrix) that both auth schemes
reach the export route and produce identical output for identical
ExportRequest inputs.


## 8. Format Negotiation Surface

### 8.1 Seam Anchor

Format negotiation MUST extend `_format_dataframe_response` at
`src/autom8_asana/api/routes/dataframes.py:111` (per P1-C-06 and shape §2
Sprint 2). A 3-line branch addition (CSV + Parquet branches alongside the
existing JSON / Polars-binary branches) is the prescribed shape; the
architect (Sprint 2) finalizes the exact branching structure.

### 8.2 Eager-Only Consumer Surface (P1-C-06 binding)

Format branches MUST operate on the eager `pl.DataFrame` returned by the
existing engine path. NO route handler may call into the engine to request
a `LazyFrame` output. Phase 1 does not introduce LazyFrame consumer
surfaces.

Rationale: Phase 2 C5 lazy chain materializes inside the engine (single
`.collect()` at engine.py:222 per spike handoff §4 phase_C5-3 reference).
A Phase 1 LazyFrame consumer surface would be both (a) a contract change
and (b) a Phase 2 forecloser per P1-C-06.

### 8.3 Format Selection Mechanism

Two viable mechanisms (architect chooses, Sprint 2):

1. **`format` query parameter** on the URL (e.g.,
   `?format=csv`) — caller-explicit, easily inspectable in logs.
2. **`Accept` header negotiation** — RESTful, follows the existing
   ADR-ASANA-005 pattern at `dataframes.py:100-108`.

Both mechanisms are admissible. The PRD does not bind one over the other.
Whichever is chosen, a missing format selection MUST default to JSON
(matching existing dataframes route default).

### 8.4 Format → MIME Mapping

| Format | MIME | Body shape |
|---|---|---|
| `json` | `application/json` | List of objects per §5.4 envelope |
| `csv` | `text/csv` | Header row + data rows; `identity_complete` is a column header |
| `parquet` | `application/vnd.apache.parquet` | Binary Parquet body; `identity_complete` is a Parquet field |

## 9. Error Envelope

### 9.1 Standard Error Contract

The export route uses the existing service error envelope shape (PRD does
not introduce a new error contract). Errors carry:

- HTTP status code (per failure class below)
- `error.code` — stable machine-readable token
- `error.message` — human-readable description
- `error.details` — optional structured payload (e.g., the offending field)
- `request_id` — for correlation

### 9.2 Failure Modes (Phase 1 explicit)

| Failure | HTTP status | `error.code` | Trigger |
|---|---|---|---|
| Unknown `entity_type` | 400 | `unknown_entity_type` | `entity_type` not in registered SchemaRegistry entities |
| Empty `project_gids` | 400 | `empty_project_gids` | `project_gids` list is empty (minItems:1 violation) |
| Malformed predicate AST | 400 | `malformed_predicate` | PredicateNode union parse failure (compiler.py raises) |
| Unknown field in predicate | 400 | `unknown_field` | `Comparison.field` not resolvable against entity's warmed schema (`compiler.py:220-225` `UnknownFieldError`) |
| Unsupported operator | 400 | `unsupported_operator` | Op enum value not admitted in Phase 1 (e.g., a Sprint 2 date op called pre-Sprint-2-merge) |
| Unsupported format | 400 | `unsupported_format` | `format` is not one of {json, csv, parquet} |
| Activity-state value not in vocabulary | 400 | `unknown_section_value` | Caller passes a section name not present in `PROCESS_PIPELINE_SECTIONS` (§4.2 validation) |
| Auth failure | 401 / 403 | per existing PAT / S2S handlers | Standard auth envelope; behavior inherited |
| Internal extraction failure | 500 | `extraction_failure` | Provider load, predicate compile, or formatter raises |

### 9.3 Empty-Result is NOT an Error

Zero-row results (predicate matches no rows) return HTTP 200 with an
empty data body and `meta.row_count: 0`. Empty results are a valid query
outcome, not an error condition.


## 10. DEFER-WATCH List (load-bearing — surfaces for stakeholder elicitation)

These items are surfaced as **explicit stakeholder elicitation prompts**,
NOT silent defaults. The PRD does NOT presume answers. Architect and
principal-engineer specialists MUST NOT proceed without explicit Vince
(or designated stakeholder) input on each. Engineering placeholders
(noted as "proposed default") are starting positions for negotiation
only.

| ID | Item | Origin | Question for stakeholder | Engineering placeholder |
|---|---|---|---|---|
| **DEFER-WATCH-1** | Dedupe winner policy on multi-hit accounts | frame Q4 (frame.md L340-345) | When an account has rows in both Reactivation and Outreach (post-union), which row wins — most recent by `modified_at`? Highest lifecycle priority? Reactivation-precedes-Outreach? | Most-recent-by-modification-timestamp; deterministic; no explicit policy hardcoded today. |
| **DEFER-WATCH-2** | Column projection minimum viable set | frame Q5 (frame.md L347-351) | Which fields land in the CSV? Phase 1 minimum is `office_phone, vertical, name, pipeline_type, section, gid, identity_complete` per §5.2. Are additional fields needed (assignee, due_date, last_modified_at, lead source)? | Phase 1 columns per §5.2 above. |
| **DEFER-WATCH-3** | ACTIVATING-state default inclusion | frame Q1 (frame.md L324-328) | Should DELAYED, SCHEDULED, REQUESTED rows appear in the default outreach CSV? Vince-elective, NOT engineering default. | ACTIVE-only default; ACTIVATING is caller-elective. |
| **DEFER-WATCH-4** | Null-key handling beyond the flag | frame Q2 (frame.md L329-333) | Beyond setting `identity_complete=false`, does Vince want null-key rows in a separate CSV section, suppressed by default, or surfaced in a separate downloadable artifact? | Inline with flag column; `include_incomplete_identity=true` by default per P1-C-05 transparency. |
| **DEFER-WATCH-5** | Format default | shape §7 emergent_behavior.emergent | What format does an unspecified-format request return — JSON (matches existing dataframes route), CSV (matches Vince's stated need)? | JSON default, matching `dataframes.py` precedent. |
| **DEFER-WATCH-6** | Pagination behavior on CSV | architect domain | Does CSV stream page-by-page, or return the full result body? CSV-with-pagination is unusual for BI consumers. | Full body for CSV (BI-tool friendly); JSON keeps existing pagination. |
| **DEFER-WATCH-7** | Maximum result size threshold | shape §3 PT-05 implicit (large-dataframe behavior) | Is there a Phase 1 row-count cap that triggers a structured "too large; refine predicate" error? | No cap in Phase 1; rely on caller predicate to bound result. |

Each DEFER-WATCH item includes a placeholder so Sprint 2 architecture work
can proceed if Vince elicitation slips — but the placeholder is engineering
hypothesis, not stakeholder confirmation. PT-02 reviewer SHOULD flag any
DEFER-WATCH item that has not been explicitly confirmed by Vince before
Sprint 3 begins.


## 11. Acceptance Criteria

Each criterion is binary pass/fail. Sprint 4 qa-adversary uses these as
the verification matrix; Sprint 3 PT-04 hard gate binds to AC-1 in
particular.

### Functional

- **AC-1 (inception-anchor reproduction; PT-04 binding):** Vince's
  Reactivation+Outreach query (§3.2) reproduces against the new export
  endpoint with `format=csv`. The output is account-grain, deduped by
  `(office_phone, vertical)`, with `identity_complete` on every row,
  scoped to ACTIVE-class sections.

- **AC-2 (PAT reaches endpoint):** A PAT-authenticated request to the
  export route succeeds and returns the same row set as the equivalent
  S2S request.

- **AC-3 (S2S reaches endpoint):** An S2S-authenticated request to the
  export route succeeds and returns the same row set as the equivalent
  PAT request.

- **AC-4 (identity_complete on every row):** Every row in every Phase 1
  output (across all formats: JSON, CSV, Parquet) carries the
  `identity_complete` boolean column.

- **AC-5 (null-key surfacing; SCAR-005/006 transparency):** A fixture
  containing at least one row with `office_phone IS NULL` returns that
  row with `identity_complete=false` (NOT silently dropped) when
  `include_incomplete_identity=true` (the default).

- **AC-6 (null-key suppression on opt-out):** When `include_incomplete_identity=false`,
  rows with `identity_complete=false` are absent from the response body.

- **AC-7 (format negotiation matrix):** All three format values
  (`json`, `csv`, `parquet`) produce a 2xx response with the
  appropriate MIME type and a body containing the same logical row set.

- **AC-8 (parameterized activity-state predicate):** A request where the
  predicate's `section IN [...]` list is `["SCHEDULED", "DELAYED",
  "REQUESTED"]` (ACTIVATING) returns ACTIVATING rows. The server does
  NOT inject ACTIVE rows. (P1-C-01-adjacent: server-side hardcoded
  predicate is forbidden.)

- **AC-8b (whole-AST default-suppression detection — DEF-05 remediation):**
  A request whose predicate is `OR(section IN [INACTIVE], office_phone =
  "555-0100")` returns the caller-defined OR result set verbatim
  (INACTIVE-section rows OR matching-phone rows). The server does NOT
  inject the ACTIVE-only default — neither at top level nor inside any
  branch. Equivalently: a request whose predicate is `NOT(section IN
  [TEMPLATE])` honors the caller's "every section except TEMPLATE"
  semantic without server augmentation. Per §4.4: any
  `Comparison(field="section")` anywhere in the AST suppresses the
  default. Implementation anchor: `predicate_references_field` walks
  `AndGroup` / `OrGroup` / `NotGroup` recursively at
  `src/autom8_asana/api/routes/_exports_helpers.py:213-225`.

- **AC-9 (unknown entity_type error):** A request with `entity_type:
  "nonsense_value"` returns HTTP 400 with `error.code:
  "unknown_entity_type"`.

- **AC-10 (malformed predicate error):** A request with a structurally
  invalid predicate AST returns HTTP 400 with `error.code:
  "malformed_predicate"`.

- **AC-11 (unsupported format error):** A request with `format: "xml"`
  returns HTTP 400 with `error.code: "unsupported_format"`.

### Contract integrity (PT-02 binding)

- **AC-12 (P1-C-01 single-entity):** The ExportRequest contract has NO
  `join` field, NO `target_entity` field, NO `predicate_target_resolution`
  field. Verifiable by inspection of the contract artifact.

- **AC-13 (P1-C-02 forward-compat):** Adding an OPTIONAL
  `predicate_join_semantics` member to `options` in a Phase 2 contract
  iteration does NOT require a contract-breaking change. Verifiable by
  authoring a hypothetical Phase 2 ExportRequest with the new field and
  showing Phase 1 schema validation rejects it as unknown OR accepts it
  via `extra='allow'` — either is acceptable; closed-enum rejection that
  blocks future addition is NOT acceptable.

- **AC-14 (P1-C-05 source-of-truth):** Inspection of the implementation
  shows `identity_complete` computation lives in the route handler /
  formatter helper, NOT in `cascade_resolver.py` and NOT in
  `cascade_validator.py`.

- **AC-15 (P1-C-06 eager surface):** No Phase 1 implementation exposes
  a `LazyFrame` to the route handler or formatter — eager `pl.DataFrame`
  only.

- **AC-16 (P1-C-07 dual-mount):** The export route is registered under
  BOTH a PAT-secured router and an S2S-secured router, both built via
  the factories at `_security.py:37,45`, mounted in `main.py` per the
  FleetQuery precedent.

## 12. Success Metrics — Phase 1 Verified-Realized Criterion

Per `frame.telos.verified_realized_definition`
(`.sos/wip/frames/project-asana-pipeline-extraction.md:19-26`):

- **Verification method:** `user-report`.
- **Verifier:** Vince (or equivalent caller).
- **Rite-disjoint attester:** `theoros@know`.
- **Verification deadline:** **2026-05-11**.

The ultimate measure of Phase 1 success is Vince's report that the
inception-anchor (Reactivation+Outreach actionable-account CSV) reproduces
against the new endpoint, end-to-end, without custom scripting. This is
the cross-stream-concurrence event that lifts the throughline to STRONG
per `self-ref-evidence-grade-rule`.

## 13. P1-C-NN Constraint → PRD Section Map

Reverse index of where each spike-handoff Phase 1 constraint is addressed
in this PRD. Each row cites both the PRD section and the spike handoff
path:line for the originating constraint.

| Constraint | Spike handoff anchor | PRD section(s) |
|---|---|---|
| P1-C-01 (single-entity hard-lock) | `...:517-531` | §2.2, §2.3, §3.1 (no `join`/`target_entity`), AC-12 |
| P1-C-02 (predicate_join_semantics reservation) | `...:533-549` | §3.1 options.members_reserved_phase_2, §6 (full), AC-13 |
| P1-C-03 (PredicateNode AST stability) | `...:551-567` | §3.1 predicate.forbidden_in_phase_1, §3.1 operators_admitted_sprint_2 |
| P1-C-04 (engine seam isolation) | `...:569-585` | §2.2 out-of-scope (engine.py:139-178 + join.py refusal), referenced by §8.2 |
| P1-C-05 (identity_complete source-of-truth) | `...:587-603` | §5.3 (full), AC-14 |
| P1-C-06 (format negotiation extension shape; eager) | `...:605-622` | §8.1, §8.2, AC-15 |
| P1-C-07 (dual-mount fidelity) | `...:624-636` | §7 (full), AC-16 |

## 14. Handoff Criteria (Self-Verification)

- [x] All user stories / functional requirements present (§3, §4, §5).
- [x] Functional requirements prioritized via single-entity hard-lock and
      DEFER-WATCH separation; MoSCoW-equivalent: §3-§9 are MUST; §10
      DEFER-WATCH items are SHOULD-pending-elicitation; Phase 2 surfaces
      are WON'T per §2.2.
- [x] Non-functional requirements (auth, format negotiation, error
      envelope) have specific seam anchors and measurable targets.
- [x] Edge cases enumerated (§9 failure modes; AC-5/AC-6 null-key handling;
      §8.4 format mapping; "empty result is not an error").
- [x] No unresolved stakeholder conflicts (DEFER-WATCH items surface
      pending elicitation; not conflicts).
- [x] Open questions list (DEFER-WATCH §10) explicit and routed.
- [x] Success criteria testable by qa-adversary (§11 binary AC-1..AC-16).
- [x] Out-of-scope documented (§2.2; preventing scope creep).
- [x] Impact assessment included: `impact: high`, categories
      `[api_contract, auth, data_model]`. New API surface (api_contract);
      dual-mount auth touch (auth); identity_complete column adds to
      output schema (data_model).
- [x] All artifacts verified via Read tool prior to authoring.
- [x] Spike handoff cited path:line at minimum 3 times: §1.3 (verdict
      §111, worked example §333-404, phase_1_constraints §514-637, entry
      conditions §801-849); §13 (each P1-C-NN row).
- [x] Telos pulse quoted verbatim at §1.1.
- [x] options substructure forward-compat clause in §6.2; closed enum
      refusal at §6.4.
- [x] identity_complete column source-of-truth named (§5.3).
- [x] Dual-mount surface named with FleetQuery precedent (§7.2).
- [x] Format negotiation seam at `dataframes.py:111` (§8.1).

## 15. Attestation Table

| Artifact | Absolute path | Role |
|---|---|---|
| This PRD | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-pipeline-export-phase1.md` | Phase 1 contract spec (Sprint 1 exit artifact) |
| Frame | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/frames/project-asana-pipeline-extraction.md` | Telos source-of-truth (L15 verbatim pulse) |
| Shape | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/frames/project-asana-pipeline-extraction.shape.md` | Sprint procession (§2 Sprint 1 binding; §3 PT-02 gate) |
| Workflow | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/frames/project-asana-pipeline-extraction.workflow.md` | requirements-analyst recipe |
| Spike handoff (verdict carrier) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md` | Binding constraints (P1-C-01..P1-C-07 at L514-637) |
| Inquisition touchstones | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/inquisitions/phase1-orchestration-touchstones.md` | Anti-pattern guards (§4) |
| Activity vocabulary source | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/models/business/activity.py:282` | `PROCESS_PIPELINE_SECTIONS` canonical 4-state vocabulary |
| PredicateNode AST source | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/query/models.py:27-123` | AST kept stable in Phase 1 (P1-C-03) |
| Format-negotiation seam | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/dataframes.py:111` | `_format_dataframe_response` extension point (P1-C-06) |
| Router factories | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/_security.py:37,45` | `pat_router` / `s2s_router` (P1-C-07) |

---

End of PRD. No pending markers. Sprint 1 exit-artifact criteria
satisfied per shape §2 Sprint 1 exit_criteria; PT-02 hard-gate
questions covered at §3 (parameterized predicate), §5.3
(identity_complete source-of-truth), §7 (dual-mount with
FleetQuery), §2.2 + §3.1 (no joins in contract scope), §6 (P1-C-02
options open-extension).
