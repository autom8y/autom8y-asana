---
type: spec
spec_subtype: revision-spec
status: proposed
lifecycle_state: proposed
date: "2026-04-20"
rite: hygiene
author: architect-enforcer (hygiene-asana, S3 Phase 3a)
links_to: PLAYBOOK-satellite-env-platformization
source_handoffs:
  - HANDOFF-hygiene-val01b-to-hygiene-asana-playbook-revision-2026-04-20
  - ECO-BLOCK-003
closes_upstream:
  - UPSTREAM-001
  - UPSTREAM-002
  - UPSTREAM-003
closes_eco_block:
  - ECO-BLOCK-003
  - ECO-BLOCK-004 (partial — ESC-2 only; ESC-1 dashboard vocab + ESC-3 ECO-001 obsolescence remain with fleet Potnia)
target_playbook: PLAYBOOK-satellite-env-platformization.md
target_playbook_version_bump: "unversioned → v2 (revision-tagged: REVISION-SPEC-playbook-v2-2026-04-20)"
throughline_binding: canonical-source-integrity (N_applied=1; no knossos edits in this spec's scope)
evidence_grade: strong
---

# REVISION-SPEC — PLAYBOOK v2 (Layer-1 closeout)

Mechanical revision contract for `PLAYBOOK-satellite-env-platformization.md`.
Janitor (S3 Phase 3b) applies this spec verbatim. Architect (S3 Phase 3a — this
artifact) authors the structural contract; janitor does not re-derive target
state.

---

## Section 1 — Source crosswalk

Six items total: 3 ESC-2 revision-spec items from the val01b cross-rite handoff
+ 3 UPSTREAM items from ECO-BLOCK-003.

| Item ID | Classification | Severity | Target PLAYBOOK section/line | Disposition |
|---------|---------------|----------|------------------------------|-------------|
| ESC-2-REV-1 | STRUCTURAL | MODERATE | §B STOP-GATE (lines 73-105) — add 4th branch | ACCEPT |
| ESC-2-REV-2 | STRUCTURAL | MODERATE | §B (new subsection) — formal closure path parallel to §G.5 opt-out | ACCEPT-WITH-MODIFICATIONS (fold into §B 4th branch + §G.7 new variance note; do not create free-standing section) |
| ESC-2-REV-3 | TACTICAL | WEAK | §D.6 (lines 265-269) + §D table row (line 296) — val01b row re-label | ACCEPT |
| UPSTREAM-001 | STRUCTURAL | MODERATE | §C Step 4 decision branch (lines 171-175) | ACCEPT (Disposition B ratified; dual-pattern admitted with empty-block as canonical, rationale-in-header as transitional-accept) |
| UPSTREAM-002 | TACTICAL | MODERATE | §C Step 2 acceptance (lines 126-142, specifically ~136) | ACCEPT-WITH-MODIFICATIONS (append sub-rubric to Step 2 acceptance; scoped as advisory not hard gate) |
| UPSTREAM-003 | TACTICAL | WEAK | §C Step 6 acceptance (lines 191-205, specifically ~201) | ACCEPT-WITH-MODIFICATIONS (append advisory paragraph; no acceptance-criterion change) |

### Deferral rationale

None — all six items are accepted (three verbatim, three with modifications).
No rejections, no deferrals. Rationale for no-deferral posture:

- **No scope creep**: all six items target the PLAYBOOK itself; no item crosses
  into ADR-0001, TDDs, or satellite code.
- **No throughline conflict**: the Disposition B ratification SUPPORTS
  canonical-source-integrity (truthful-contract enforcement) without requiring
  a knossos canonical edit.
- **No structural infeasibility**: all six target lines grep cleanly in the
  current PLAYBOOK.
- **TACTICAL items (UPSTREAM-002, UPSTREAM-003) are accepted now** because
  bundling them into the v2 revision costs ~15 lines of additional playbook
  text and avoids a second revision cycle. Janitor is authorized to defer
  either item to Phase 3b-optional if anchor-pattern grep fails (see §7).

---

## Section 2 — PLAYBOOK §B STOP-GATE 4th branch — full prescribed text

Janitor inserts this text as a **new subsection after §B "What to do on failure"
table (after line 99), BEFORE §B "Additional routing signals"**. The subsection
heading is a peer to "What to do on failure"; it does NOT nest under the table.

### Prescribed text (paste verbatim)

```markdown
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
```

### End of §B 4th branch prescribed text

---

## Section 3 — PLAYBOOK Step 4 Disposition B ratification — full prescribed text

Janitor REPLACES the Step 4 decision branch block (lines 171-175, the block
beginning `**Decision branch — BRANCH: does this satellite have a CLI
entrypoint?**`) with the following.

### Canonical choice (binding)

**Empty-`[profiles.cli]`-block-with-rationale is canonical.** Rationale-in-header
is a **transitional-accept** pattern — existing satellites that chose it (as
of v2: autom8y-dev-x) are not required to retroactively convert, but NEW
CLI-less satellites executing the playbook MUST emit the empty block per the
canonical pattern.

**Why empty-block is canonical**:

1. **Fleet grep-discoverability.** `rg '\[profiles.cli\]' repos/` returns every
   satellite regardless of CLI surface. The rationale-in-header pattern
   breaks this invariant — a grep for `[profiles.cli]` returns zero matches
   for dev-x, making the skip indistinguishable from "never considered".
2. **Structural uniformity.** Every satellite carries the same structural shape
   (differing only in content). This mirrors the §H artifact-trail discipline:
   structure is invariant; content adapts per satellite.
3. **ADR-0001 truthful-contract compatibility.** Both patterns honor the
   truthful-contract test (neither declares required-vars for a consumer that
   does not exist). The empty-block pattern additionally honors
   **declarative-uniformity** — a property the header-comment pattern cannot
   satisfy.

Rationale-in-header is accepted as transitional because (a) dev-x authored it
pre-ratification without awareness of Disposition B, (b) retrofitting dev-x
would be rework unrelated to any behavior change, and (c) the header comment
still cites ADR-0001 and thus still satisfies truthful-contract — the
divergence is in grep-discoverability only, not in truthfulness.

### Prescribed text (paste verbatim as replacement for lines 171-175)

```markdown
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
```

### End of Step 4 prescribed text

This replacement closes **UPSTREAM-001** explicitly: disposition ACCEPT per
Disposition B.

---

## Section 4 — UPSTREAM-002 + UPSTREAM-003 dispositions

Both accepted with modifications. Janitor applies the prescribed text below.

### Section 4.1 — UPSTREAM-002 (Step 2 Layer 3 sub-rubric)

Janitor APPENDS the following paragraph to the **end of Step 2's Acceptance
criterion block** (after the `env -i bash -c ...` fresh-clone test sentence
at line 136). Insertion is additive; it does not replace any existing text.

### Prescribed text (paste verbatim)

```markdown

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
```

### Section 4.2 — UPSTREAM-003 (Step 6 worked-example picker advisory)

Janitor APPENDS the following paragraph to the **end of Step 6's Acceptance
criterion block** (after the "frontmatter follows the `.know/` schema…"
sentence at line 201). Insertion is additive.

### Prescribed text (paste verbatim)

```markdown

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
```

---

## Section 5 — Janitor apply order

Ordered mechanical application. Each step has an anchor pattern (grep-reproducible)
and a precise insertion or replacement span.

### Step 5.1 — §B STOP-GATE fourth branch insertion

- **Anchor pattern**: `grep -n '^| Gate 3 fails' PLAYBOOK-satellite-env-platformization.md`
  → should return line 99 (the last row of the "What to do on failure" table).
- **Insertion point**: after the blank line following line 99, BEFORE the
  `### Additional routing signals` heading (line 101 in current file).
- **Action**: insert the §2 prescribed text block verbatim, preceded by a
  blank line. The inserted heading becomes `### Fourth prerequisite branch — Satellite IS the canonical source of truth`.
- **Expected post-insert grep**: `grep -c '^### ' PLAYBOOK-satellite-env-platformization.md`
  within §B — count increments by 1 (from 2 "What to do on failure" + "Additional
  routing signals" to 3 with the new fourth-branch subsection).

### Step 5.2 — §C Step 4 decision branch replacement

- **Anchor pattern**: `grep -n '^\*\*Decision branch — BRANCH: does this satellite have a CLI entrypoint' PLAYBOOK-satellite-env-platformization.md`
  → should return line 171.
- **Replacement span**: line 171 through the end of the current Step 4 decision
  branch block. The current block ends at line 175 (the `If the satellite has
  no secretspec.toml at all` bullet). Confirm span end with:
  `grep -n '^### Step 5' PLAYBOOK-satellite-env-platformization.md` → should
  return line 177; replacement span is lines 171-175 inclusive.
- **Action**: replace lines 171-175 with the §3 prescribed text block verbatim.
- **Expected post-replace grep**: `grep -c 'ADR-env-secret-profile-split' PLAYBOOK-satellite-env-platformization.md`
  → should increment (the new text cites ADR-0001 by path at least twice).

### Step 5.3 — §C Step 2 Layer 3 sub-rubric append (UPSTREAM-002)

- **Anchor pattern**: `grep -n "env -i bash -c 'set -a; source .env/defaults" PLAYBOOK-satellite-env-platformization.md`
  → should return line 136 (the fresh-clone acceptance test sentence inside
  Step 2's Acceptance criterion).
- **Insertion point**: end of the paragraph that contains line 136 (i.e.,
  after the closing period of "...returns the expected defaults without any
  `export` statement.").
- **Action**: insert blank line + §4.1 prescribed text block.
- **Expected post-insert grep**: `grep -c 'Layer 3 content sub-rubric' PLAYBOOK-satellite-env-platformization.md`
  → exactly 1.

### Step 5.4 — §C Step 6 worked-example advisory append (UPSTREAM-003)

- **Anchor pattern**: `grep -n 'frontmatter follows the .\.know/. schema' PLAYBOOK-satellite-env-platformization.md`
  → should return line 201 (end of Step 6's Acceptance criterion).
- **Insertion point**: end of line 201 (after the closing period of
  "...domain, source_scope, confidence, format_version).").
- **Action**: insert blank line + §4.2 prescribed text block.
- **Expected post-insert grep**: `grep -c 'Worked-example variable selection' PLAYBOOK-satellite-env-platformization.md`
  → exactly 1.

### Step 5.5 — §D.6 autom8y-val01b row re-label (ESC-2-REV-3)

- **Anchor pattern**: `grep -n '### D.6 autom8y-val01b' PLAYBOOK-satellite-env-platformization.md`
  → should return line 265.
- **Action**: REPLACE the §D.6 block body (lines 266-269 in current file —
  the `**Observed state**`, `**Prescribed steps**`, `**Escalation**` lines)
  with:

  ```markdown
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
  ```

- **Also**: in the §D summary table (line 296, the `autom8y-val01b` row),
  REPLACE the entire row body (the `YES | OPT | MOD | ESCALATE | ESCALATE |
  YES | COND` cells) with `RECLASSIFIED (source-of-truth per §B 4th branch) | — | — | — | — | — | —`.

### Step 5.6 — Frontmatter version bump

- **Anchor pattern**: `grep -n '^lifecycle_status: frozen-for-wave-1-consumption' PLAYBOOK-satellite-env-platformization.md`
  → should return line 8.
- **Action**: BEFORE line 8, INSERT two new lines:
  ```yaml
  version: "v2"
  revision_spec: REVISION-SPEC-playbook-v2-2026-04-20
  ```
  ALSO replace `lifecycle_status: frozen-for-wave-1-consumption` with
  `lifecycle_status: frozen-for-wave-2-consumption` (v2 is post-Wave-1
  empirical stress-test; frozen for Wave 2+).
- **Expected post-edit grep**: `grep -c '^version:' PLAYBOOK-satellite-env-platformization.md`
  → exactly 1 (the frontmatter version line).

### Step 5.7 — Changelog entry

The PLAYBOOK currently has NO changelog section. Janitor ADDS a new section
immediately before the `## Links` section (line 450 in current file). Anchor
pattern: `grep -n '^## Links' PLAYBOOK-satellite-env-platformization.md`
→ line 450.

Insert the following block BEFORE `## Links`:

```markdown
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
```

### Step 5.8 — Ordering constraint

Steps 5.1 through 5.5 can be applied in any order (they touch non-overlapping
spans). Steps 5.6 and 5.7 (frontmatter + changelog) SHOULD be applied LAST
because they commit the version bump — if an earlier step fails grep-anchor
verification (§7), the version bump MUST be rolled back. Recommended order:
5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7 → commit.

### Step 5.9 — Dashboard update (ECO-BLOCK-003 + ECO-BLOCK-004 partial closure)

After the PLAYBOOK commit lands, janitor ALSO updates the coordination dashboard:

- **File**: `FLEET-COORDINATION-env-secret-platformization.md`
- **Line 54 (ECO-BLOCK-003 row)**: change `Status: OPEN` to `Status: CLOSED`;
  append to the Scope cell: ` [CLOSED 2026-04-20 via REVISION-SPEC-playbook-v2-2026-04-20 — PLAYBOOK v2 ratifies Disposition B as canonical + admits rationale-in-header as transitional-accept].`
- **Line 53 (ECO-BLOCK-004 row)**: append to the Scope cell:
  ` [ESC-2 CLOSED 2026-04-20 via REVISION-SPEC-playbook-v2-2026-04-20 — PLAYBOOK §B 4th branch + §D.6 re-label landed. ESC-1 (dashboard vocab) + ESC-3 (ECO-001 obsolescence) remain with fleet Potnia.]`
  — do NOT change the OPEN status (ESC-1 + ESC-3 still outstanding).
- **Line 22 (autom8y-dev-x row)**: no edit required — the row already cites
  the rationale-in-header pattern as transitional; v2 ratification does not
  invalidate the dev-x closure.
- **Line 27 (autom8y-data row)**: no edit required — the row already cites
  Disposition B ratification; v2 formalizes it upstream.

### Step 5.10 — Commit

Single atomic commit per `conventions` skill:
- **Subject**: `docs(playbook): ratify v2 with §B 4th branch + Step 4 Disposition B + Steps 2/6 sub-rubrics`
- **Body**: cites REVISION-SPEC path, ESC-2 HANDOFF path, val01b ADR path,
  ECO-BLOCK-003 + ECO-BLOCK-004 row references. Lists the 7 edit steps
  (5.1-5.7) as bullet points for future-reader clarity.
- **Scope constraint**: git diff --stat shows ONLY `PLAYBOOK-satellite-env-platformization.md`
  and `FLEET-COORDINATION-env-secret-platformization.md`. Zero other files.

---

## Section 6 — Acceptance assertions for janitor

Janitor runs this checklist BEFORE returning. Every box must be checked.

- [ ] §B STOP-GATE has exactly **4 routing branches** after the "What to do
      on failure" table. Verify: `grep -c '^\*\*Routing action on trigger\*\*\|^| Gate' PLAYBOOK-satellite-env-platformization.md`
      or equivalent structural count confirms the new subsection is present.
- [ ] Step 4 decision branch replacement contains `ADR-env-secret-profile-split`
      citation. Verify: `grep -c 'ADR-env-secret-profile-split' PLAYBOOK-satellite-env-platformization.md`
      returns a count **strictly greater** than the pre-edit count.
- [ ] Step 4 admits empty-`[profiles.cli]` variant explicitly. Verify:
      `grep -F 'emit an empty \`[profiles.cli]\` block' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1 match (the canonical-pattern directive).
- [ ] Step 4 admits rationale-in-header as transitional. Verify:
      `grep -F 'Transitional-accept exemplar' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1 match.
- [ ] Step 2 sub-rubric present. Verify:
      `grep -c 'Layer 3 content sub-rubric' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1.
- [ ] Step 6 worked-example advisory present. Verify:
      `grep -c 'Worked-example variable selection' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1.
- [ ] §D.6 val01b row re-labeled. Verify: `grep -F 'Reclassified' PLAYBOOK-satellite-env-platformization.md`
      returns at least 1 match in §D.6 context.
- [ ] §D summary table val01b row shows `RECLASSIFIED`. Verify: `grep -F 'RECLASSIFIED' PLAYBOOK-satellite-env-platformization.md`
      returns at least 1 match inside the §D summary table.
- [ ] Frontmatter version bump visible. Verify: `grep -c '^version: "v2"' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1; `grep -c 'revision_spec:' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1.
- [ ] Changelog entry references ESC-2 + val01b ADR + ECO-BLOCK-003. Verify:
      `grep -F 'HANDOFF-hygiene-val01b-to-hygiene-asana-playbook-revision' PLAYBOOK-satellite-env-platformization.md`
      returns exactly 1 match (the changelog cite); similarly for
      `ADR-val01b-source-of-truth-reclassification` and `ECO-BLOCK-003`.
- [ ] Dashboard: ECO-BLOCK-003 row flipped to CLOSED. Verify:
      `grep -F 'ECO-BLOCK-003' FLEET-COORDINATION-env-secret-platformization.md | grep -F 'CLOSED'`
      returns at least 1 match.
- [ ] Dashboard: ECO-BLOCK-004 row annotated ESC-2 CLOSED (row remains OPEN).
      Verify: row 53 contains both `OPEN` (ESC-1/ESC-3 still outstanding) and
      `ESC-2 CLOSED 2026-04-20`.
- [ ] Dashboard: autom8y-data + autom8y-dev-x status cells do NOT gain any
      CONDITIONAL-latent qualifier (v2 ratification REMOVES any such
      qualifier rather than adding one). Verify: the data + dev-x rows are
      unchanged relative to pre-edit content (except for incidental
      whitespace).
- [ ] Scope discipline: `git diff --stat` shows exactly 2 files modified
      (PLAYBOOK + dashboard). No unrelated edits.
- [ ] Atomic commit with the prescribed subject + body. Verify: `git log -1
      --pretty=format:'%s'` matches the subject pattern.

---

## Section 7 — Rejection / PAUSE criteria for janitor

Janitor MUST STOP and re-consult architect-enforcer if any of the following hold.

### 7.1 Anchor-pattern grep failure

Any anchor pattern in §5 fails to match the expected line number (or returns
a line-number range inconsistent with the expected span). Example: if
`grep -n '^### Step 5' PLAYBOOK-satellite-env-platformization.md` does NOT
return line 177, the Step 4 replacement span is NOT lines 171-175 and the
assumption is falsified. Janitor stops; architect re-derives the span.

### 7.2 Frontmatter schema rejection

If the PLAYBOOK's `spec_subtype: playbook` lineage does not admit a `version`
key (i.e., the `.ledge/` advisory schema forbids arbitrary additive fields),
janitor adjusts: set `lifecycle_status: frozen-for-wave-2-consumption` as
the sole version signal and omit the explicit `version: "v2"` line. The
changelog entry (§5.7) still names "v2" in its heading — the version is
human-readable even if not frontmatter-encoded. No PAUSE required for this
case; it is a graceful degradation.

### 7.3 ECO-BLOCK-003 row structural divergence

If ECO-BLOCK-003's dashboard row (line 54) requires row-level restructuring
(not just status-cell edit) — e.g., if the row has been split or merged
since this revision-spec was authored — janitor PAUSES. Architect
re-evaluates the dashboard update spec.

### 7.4 UPSTREAM-002 or UPSTREAM-003 anchor failure

If the Step 2 or Step 6 anchor patterns fail to grep cleanly (e.g., the line
136 / line 201 anchors have drifted), janitor is authorized to DEFER
UPSTREAM-002 and/or UPSTREAM-003 to a Phase 3b-optional follow-up with a
changelog note: `UPSTREAM-002 deferred to v2.1 pending anchor-pattern
re-derivation`. This defers the tactical items without blocking the
structural ratification (§B 4th branch + Step 4 Disposition B).

Do NOT PAUSE for:
- Minor wording adjustments to match PLAYBOOK voice (janitor discretion).
- Whitespace normalization in inserted blocks (janitor discretion).
- Adding a trailing newline at end-of-file if tooling requires it.

### 7.5 Scope creep signal

If applying this spec would require touching any file OTHER than the PLAYBOOK
and the dashboard, janitor PAUSES. The spec's scope fence is strict: 2 files,
no more.

---

## Provenance

- **ESC-2 HANDOFF**: `/Users/tomtenuta/Code/a8/repos/autom8y-val01b-fleet-hygiene/.ledge/reviews/HANDOFF-hygiene-val01b-to-hygiene-asana-playbook-revision-2026-04-20.md`
  (3 revision-spec items + 5 detection heuristics)
- **val01b ADR**: `/Users/tomtenuta/Code/a8/repos/autom8y-val01b-fleet-hygiene/.ledge/decisions/ADR-val01b-source-of-truth-reclassification-2026-04-20.md`
- **Dual-satellite Disposition B evidence (autom8y-data)**:
  `/Users/tomtenuta/Code/a8/repos/autom8y-data-fleet-hygiene/.ledge/reviews/ALIGNMENT-MEMO-fleet-data-env-2026-04-20.md`
  §Residual risks §1 (empty-block-with-rationale pattern)
- **Dual-satellite Disposition B evidence (autom8y-dev-x)**:
  `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-dev-x-to-hygiene-fleet-2026-04-20.md`
  §6.1 (rationale-in-header pattern)
- **ADR-0001 (truthful-contract anchor)**:
  `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-env-secret-profile-split.md`
- **ECO-BLOCK-003 + ECO-BLOCK-004 row context**:
  `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-env-secret-platformization.md:53-54`
- **Current PLAYBOOK state**:
  `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PLAYBOOK-satellite-env-platformization.md`
  (unversioned; post-v2 label: v2)
- **Throughline binding**: canonical-source-integrity (N_applied=1). This spec
  SUPPORTS the throughline (truthful-contract enforcement in Step 4
  ratification) but does NOT increment N_applied — no knossos canonical edit
  is authored; that is reserved for S12 per the closeout shape.

## Evidence ceiling

Per `self-ref-evidence-grade-rule`: STRONG-graded claims rest on
grep-reproducible evidence (anchor patterns, line numbers, cited file:line
spans in the two dual-satellite exemplars). Interpretive claims (the
canonical vs transitional-accept judgment for Disposition B; the
classification of UPSTREAM-002/003 as TACTICAL) are MODERATE, single-author
architectural judgment. No STRONG claim rests on self-assessment of this
revision-spec's own correctness.
