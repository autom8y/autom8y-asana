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
title: Cross-rite handoff dossier schema (10x-dev → thermia, sre fallback)
status: accepted  # the surviving HANDOFF-10x-dev-to-thermia-2026-04-27.md is an EXEMPLAR of this schema
companion_prd: verify-active-mrr-provenance.prd.md
companion_adr: ADR-002-rite-handoff-envelope-thermia.md
exemplar_artifact: .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md
reconstruction:
  status: RECONSTRUCTED-2026-04-27
  reason: original lost to **/.ledge/* gitignore during predecessor 10x-dev sprint
  reconstructed_by: thermia procession P0 pre-flight (general-purpose dispatch)
  source_evidence:
    - .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md (surviving — exemplar of schema)
    - .ledge/handoffs/2026-04-27-section-mtimes.json (sidecar — exemplar of §3 histogram artifact)
    - .ledge/handoffs/INDEX.md (surviving — exemplar of §4 INDEX entry)
    - cross-rite-handoff skill (canonical type contract, implementation variant)
    - external-critique-gate-cross-rite-residency skill (refusal-clause heritage)
    - .ledge/reviews/QA-T9-verify-active-mrr-provenance.md (cites §4.3, §4.4, §5.1)
    - conversation memory of architect-phase authoring
---

# TDD — handoff-dossier-schema

> [RECONSTRUCTED-2026-04-27] — The surviving handoff dossier
> `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` is an
> **exemplar** of this schema; where this TDD differs from that artifact,
> the exemplar's structure wins (the dossier was force-added before sprint
> wrap and is the load-bearing surviving evidence).

## §1 Frontmatter (12 required fields per cross-rite-handoff implementation type)

The `cross-rite-handoff` skill canonical contract for type=`implementation`
defines the following frontmatter fields. All are **required** for a
valid dossier:

| #  | Field                   | Type     | Description                                                      |
|----|-------------------------|----------|------------------------------------------------------------------|
| 1  | `type`                  | string   | constant: `handoff`                                              |
| 2  | `handoff_type`          | string   | one of: `implementation`, `discovery`, `assessment`              |
| 3  | `originating_rite`      | string   | rite identifier (e.g., `10x-dev`)                                |
| 4  | `receiving_rite`        | string   | primary attesting rite (e.g., `thermia`)                         |
| 5  | `fallback_rite`         | string   | fallback attester if primary unregistered (e.g., `sre`)          |
| 6  | `originating_session`   | string   | session ID of authoring engineer                                 |
| 7  | `authored_on`           | date     | YYYY-MM-DD                                                       |
| 8  | `authored_by`           | string   | agent class (e.g., `principal-engineer`)                         |
| 9  | `worktree`              | path     | originating worktree path                                        |
| 10 | `branch`                | string   | originating branch                                               |
| 11 | `prd_anchor`            | path     | `.ledge/specs/{slug}.prd.md`                                     |
| 12 | `attestation_required`  | boolean  | always `true` for cross-rite handoff                             |

### §1.1 Additional fields (recommended, not strictly required)

| Field                   | Type        | Description                                                |
|-------------------------|-------------|------------------------------------------------------------|
| `schema_version`        | integer     | starts at `1`; bumped per §6                                |
| `attestation_chain`     | string      | `"primary (rite.agent), fallback (rite.agent)"`            |
| `verification_deadline` | date        | YYYY-MM-DD; <= 30 days from `authored_on` recommended      |
| `design_references`     | list[path]  | PRD + TDDs + ADRs                                          |
| `tdd_anchor`            | path        | `.ledge/specs/{slug}.tdd.md`                               |
| `adr_anchor`            | path        | `.ledge/decisions/ADR-NNN-...md`                           |
| `index_entry_appended`  | boolean     | `true` if `.ledge/handoffs/INDEX.md` was updated           |
| `initiative_slug`       | string      | machine-readable slug                                      |
| `status`                | string      | one of: `ATTESTED-PENDING-{rite}`, `ATTESTED`, `STALE`     |

### §1.2 Status state machine

```
DRAFT → ATTESTED-PENDING-{receiving_rite} → ATTESTED        (primary path)
                                          → ATTESTED-FALLBACK-{fallback_rite}  (fallback path)
                                          → STALE           (deadline missed; reactivation requires new dossier)
```

## §2 Eight required body sections (per US-6 AC-6.1)

Every implementation-type dossier MUST contain the following 8 sections,
in this order. Section headings are `## N. Title` (h2, numbered).

### §2.1 Section 1 — Classifier ACTIVE-Section List

- Verbatim list of section names that the offer classifier maps to
  `AccountActivity.ACTIVE`.
- **Required**: file:line anchor to the classifier definition (e.g.,
  `src/autom8_asana/models/business/activity.py:76`).
- **Required**: `CLASSIFIERS` dict anchor (e.g., `activity.py:317`).
- **Required**: capture-method note (verbatim Python or shell command
  used to produce the list).
- **Required**: capture timestamp (ISO-8601 UTC).

### §2.2 Section 2 — Parquet Section List (as of handoff date)

- **Required**: verbatim capture command (e.g.,
  `aws s3 ls s3://autom8-s3/dataframes/{project_gid}/sections/ --recursive`).
- **Required**: capture timestamp (ISO-8601 UTC).
- **Required**: row count.
- **Required**: table with columns: `section_gid`, `parquet_path`,
  `LastModified` (ISO-8601 UTC), `size_bytes`.

### §2.3 Section 3 — Per-Section Mtime Histogram (Artifact)

The histogram is authored as a **sidecar JSON artifact**, not inline:

- **Sidecar path** (relative to worktree root):
  `.ledge/handoffs/{date}-section-mtimes.json`.
- **Required reference timestamp** `now_iso` (against which
  `age_seconds_at_handoff` is computed).

JSON schema — array of objects with these four keys per row:

```json
[
  {
    "section_gid": "string",
    "parquet_path": "s3://{bucket}/dataframes/{project_gid}/sections/{section_gid}.parquet",
    "last_modified_iso": "YYYY-MM-DDTHH:MM:SSZ",
    "age_seconds_at_handoff": 12345
  }
]
```

The dossier body MUST cite `min` and `max` `age_seconds_at_handoff` with
the corresponding parquet identifiers.

### §2.4 Section 4 — Bucket→Env Stakeholder Affirmation

Carries the bucket→env affirmation forward verbatim from the originating
session — **NO new claims appended**.

- **Required citation header**: `source` (session ID), `event` (interview
  question / decision ID), `user`, `date`.
- **Required**: verbatim quote of the affirmation.
- **Required**: cross-reference anchor to PRD §6 C-1 lines.
- **Required**: cross-reference to `.know/env-loader.md` Stakeholder
  Affirmation Addendum (line range).

### §2.5 Section 5 — cache_warmer Schedule (Open Question, D10)

- **Required**: verifiable predicate question (NOT aspirational prose).
- **Required**: file:line structural pointer to the unmodified Lambda
  (e.g., `src/autom8_asana/lambda_handlers/cache_warmer.py:1`).
- **Required**: deferral rationale citing PRD D10 + relevant NG.

### §2.6 Section 6 — Section-Coverage Deferral Rationale (D5)

- **Required**: verbatim quote of PRD §6 C-6 (empty-sections-are-expected).
- **Required**: cross-references to PRD §2 NG5, PRD §6 C-6, PRD §9 D5.
- **Required**: structural justification — e.g., "cache_warmer Lambda
  writes parquet only for sections that contain tasks; an empty section
  is by-design and is NOT a coverage gap."

### §2.7 Section 7 — Env-Matrix Legacy-Cruft Inventory (D7)

- **Required**: verbatim capture command (e.g.,
  `rg -n 'AUTOM8Y_ENV|autom8-s3-(staging|dev|prod)' src/`).
- **Required**: capture timestamp.
- **Required**: total match count.
- **Required**: table with columns: `file_path`, `line_number`,
  `matched_text`.
- **Required**: discovery-only declaration (NO remediation proposal at
  this altitude).

### §2.8 Section 8 — Telos Handoff and Attester Fallback Condition (D8)

- **Required**: primary attester (rite.agent).
- **Required**: fallback attester + activation predicate.
- **Required**: verification deadline.
- **Required**: PRD telos §7 cross-reference (line range).
- **Recommended**: §8.1 latent decisions surfaced for engineer-discretion
  disposition.
- **Recommended**: §8.2 pre-existing observations surfaced from QA.

## §3 Eleven-line refusal-clause checklist

Before any commit that lands a handoff dossier, the engineer agent runs
the following 11-line refusal-clause checklist. If ANY line fails, the
commit is REFUSED:

1. **No aspirational tokens** — no `should`, `will`, `eventually`,
   `TODO`, `FIXME`, `[placeholder]`, `[TBD]` in the dossier body.
2. **All file anchors are `file:line`** — `path/to/file.py:NN`, not
   `path/to/file.py` alone (unless the entire file is the anchor and
   the §5 §1 structural pointer convention is invoked).
3. **All open questions are verifiable predicates** — phrased so a
   downstream agent can mechanically determine whether they have been
   answered (e.g., "What is the EventBridge rule cron expression?", not
   "How does the warmer schedule work?").
4. **All capture commands are verbatim** — exactly the shell or Python
   command that was run, not a paraphrase.
5. **All capture timestamps are ISO-8601 UTC** — `YYYY-MM-DDTHH:MM:SSZ`,
   not human-friendly.
6. **All §3 sidecar paths are workspace-relative** — `.ledge/handoffs/...`,
   not absolute.
7. **All §4 stakeholder citations carry the 4-tuple** — source, event,
   user, date — NO bare quotes without provenance.
8. **All §7 inventories are discovery-only** — no remediation proposals
   inside the originating-rite dossier (the receiving rite proposes).
9. **All §8 fallback conditions are mechanically verifiable** —
   `Read('.claude/agents/{rite}/')` ENOENT or absence from
   `.knossos/KNOSSOS_MANIFEST.yaml`, not a judgment call.
10. **`.ledge/handoffs/INDEX.md` has been updated** with a single-line
    entry for this dossier — `index_entry_appended: true` in frontmatter.
11. **`design_references:` enumerates ALL companion artifacts** — PRD,
    every TDD, every ADR — using their canonical `.ledge/...` paths.

## §4 Attester invocation contract

### §4.1 Naming convention

`HANDOFF-{originating_rite}-to-{receiving_rite}-{YYYY-MM-DD}.md`

Examples:
- `HANDOFF-10x-dev-to-thermia-2026-04-27.md` (this initiative)
- `HANDOFF-10x-dev-to-sre-2026-05-15.md`        (hypothetical)
- `HANDOFF-thermia-to-hygiene-2026-05-30.md`    (forward fork)

### §4.2 INDEX.md single-line entry

`.ledge/handoffs/INDEX.md` is a fleet-level discoverability artifact. Each
dossier appends one line:

```
- {YYYY-MM-DD} | {originating_rite} → {receiving_rite} | {initiative_slug} | {dossier_filename} | status={status}
```

The INDEX is grep-friendly:
- `grep "→ thermia"` lists all incoming-thermia handoffs.
- `grep "status=ATTESTED-PENDING"` lists all in-flight handoffs.

### §4.3 Receiving rite acceptance heading

When the receiving rite engages the dossier (procession kickoff or
session start), it appends a `## Attester Acceptance` h2 heading to the
dossier body. This heading contains:

- **Accepting rite** (rite identifier).
- **Activation predicate result** (PRIMARY engaged | FALLBACK activated).
- **Engaging agent(s)** with role disambiguation if pantheon-fit
  substitution applied.
- **Acceptance timestamp** (ISO-8601 UTC).
- **Receiving session** ID.
- **Receiving worktree + branch** path.
- **Initiative slug** (downstream slug if a new initiative is framed).
- **Pantheon-role mapping note** (if substituting an agent for the
  primary-named role).
- **Scope acknowledgement** — explicit list of D-IDs / NG-IDs accepted.
- **Initial-pass scope question for Potnia** (optional).

### §4.4 Verification attestation heading

At verification time (or `verification_deadline`, whichever first), the
discharging agent appends a `## Verification Attestation` h2 heading
containing:

- **Discharging agent** (rite.agent).
- **Discharge timestamp** (ISO-8601 UTC).
- **Verification method** (per PRD §7 telos block).
- **Evidence pointers** (file paths, commit SHAs, log artifacts).
- **Verdict** (`ATTESTED` | `ATTESTED-WITH-FLAGS` | `REJECTED-REOPEN`).
- **Forward-handoff** (if work continues into a downstream rite).

### §4.5 INDEX.md merge-time scope (latent decision, dossier §8.1 #1)

At merge-to-main, the worktree's `.ledge/handoffs/INDEX.md` should be
**merged** into the main-branch `.ledge/handoffs/INDEX.md` (creating the
directory if absent). Per-worktree INDEX entries append to a project-wide
INDEX. Rationale: a per-rite or per-receiving-rite INDEX would fragment
discoverability across the fleet; a single project-wide INDEX matches the
established artifact-locality pattern (one `.ledge/decisions/`, one
`.ledge/specs/` per repo).

Decision holder: Potnia at merge time.

## §5 Fallback predicate (mechanically verifiable)

The fallback rite activates iff the primary rite is **not registered** at
the platform/manifest level. This must be **mechanically verifiable** —
no judgment calls.

### §5.1 Activation predicate

```python
def fallback_activates(primary_rite: str, project_root: Path) -> bool:
    """Returns True iff the fallback rite must take the attestation."""
    agents_dir = project_root / ".claude" / "agents" / primary_rite
    manifest = project_root / ".knossos" / "KNOSSOS_MANIFEST.yaml"

    # Predicate A: agents directory absent or empty
    agents_absent = not agents_dir.exists() or not any(agents_dir.iterdir())

    # Predicate B: rite not declared in manifest
    if manifest.exists():
        with manifest.open() as f:
            manifest_text = f.read()
        rite_unregistered = primary_rite not in manifest_text
    else:
        rite_unregistered = True

    return agents_absent or rite_unregistered
```

The predicate is **disjunctive** (either condition triggers fallback) and
uses ENOENT / file-content checks — no rite-state introspection.

### §5.2 Fallback Activation Record (heading)

When the fallback predicate fires, the substituting agent appends a
`## Fallback Activation Record` h3 heading to the dossier body. This
heading contains:

- **Predicate result** (which clause fired: A, B, or both).
- **Substituting rite** (e.g., `sre`).
- **Substituting agent** (e.g., `sre.observability-engineer`).
- **Engagement timestamp** (ISO-8601 UTC).
- **Disambiguation note** (per dossier §8.1 #2 — observability-engineer
  for SLO-shaped surface, incident-commander for degraded-state response).

### §5.3 Pantheon-fit substitution (distinct from fallback activation)

Note: when the **primary** rite is registered but does not have an agent
of the exact name specified in the dossier frontmatter, the receiving
rite has authority to substitute its closest pantheon-fit agent. This is
**NOT** fallback activation — fallback only fires per §5.1 disjunctive
predicate.

Example: this initiative's dossier names `thermia.verification-auditor` as
primary. The thermia pantheon does not contain `verification-auditor`, but
DOES contain `thermal-monitor` whose charter includes "cross-architecture
validation". Per receiving-rite authority, `thermal-monitor` discharges
the verification gate. This is **semantic-fit substitution**, recorded in
§Attester Acceptance §Pantheon-role mapping. Fallback (sre) is NOT
activated.

## §6 Schema versioning

- **schema_version: 1** (this TDD).
- **Minor changes** (additive optional fields, new recommended sections,
  refusal-clause clarifications): NO schema-version bump. Changes
  recorded in this TDD's git history are sufficient.
- **Breaking changes** (rename or remove a required field, change a
  required section's structure, change refusal-clause from 11 to N
  lines): bump `schema_version`. The bump REQUIRES an ADR documenting
  the rationale.

## §7 Schema validity rationale (load-bearing structural justifications)

### §7.1 Why 8 sections?

The 8 sections correspond bijectively to the deferred concerns enumerated
in PRD §3 boundary table + the read-only static-artifact requirements
of US-6 AC-6.1. Each section is **load-bearing** for the receiving rite:

- §1+§2+§3 give thermia the cache state at handoff time.
- §4 gives thermia the load-bearing stakeholder evidence for the
  bucket→env mapping.
- §5+§6+§7 give thermia the deferred concerns (D10, D5, D7) with
  enough context to scope without round-tripping.
- §8 declares the telos discharge gate + fallback predicate.

Removing any section breaks the schema.

### §7.2 Why a sidecar JSON artifact for §3?

The mtime histogram is structured data; embedding it inline as a markdown
table would (a) bloat the dossier body, (b) make programmatic consumption
harder, (c) couple the artifact's machine-readable shape to markdown
table syntax. The sidecar is parsed independently and the body cites
`min`/`max` summary statistics.

### §7.3 Why the 11-line refusal-clause?

Inherited from `external-critique-gate-cross-rite-residency` skill
discipline: cross-rite residency demands **mechanically verifiable**
predicates and **anchored** evidence. The 11 lines collectively rule
out the failure modes the predecessor cross-rite handoffs experienced
(aspirational prose, missing anchors, judgment-call open questions).

### §7.4 Why the fallback predicate uses ENOENT + manifest-grep?

Both signals are **machine-checkable** at handoff time without invoking
any agent or rite state. A judgment-call predicate ("does thermia exist
yet?") would require the originating rite to make an authority claim
about another rite's existence; ENOENT + manifest-grep is authority-free.

---

*Authored by principal-architect, session-20260427-154543-c703e121,
2026-04-27. Reconstructed by thermia procession P0 pre-flight,
session-20260427-185944-cde32d7b, on 2026-04-27. Ground truth: the
surviving exemplar at
`.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md`.*
