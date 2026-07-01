---
type: review
status: draft
artifact_subtype: arch-adversary-report
initiative: dyn-enum-contract
challenger_agent: arch-adversary
date: "2026-07-01"
iter: 1
delta_scope_attested: false          # iter=1 clean re-fire; no prior ADVERSARY-REPORT to delta against
target_handoff: ".ledge/handoffs/HANDOFF-arch-to-10x-dyn-enum-contract-2026-06-30.md"
target_handoff_sha: "sha256:6af7b54fdf7d8101fed0ece9d0a32788ed54f41c816349e181ac1c24d5ca33d0"
producer_truth_anchor_verified: "autom8y-asana origin/main ca28251d (HANDOFF declares ca28251d — MATCH; cwd f4f924d2 is 25 commits behind — producer cites verified at origin/main, NOT cwd)"
consumer_truth_anchor_verified: "autom8y-data HEAD 92d3606d branch main (HANDOFF declares 92d3606d — MATCH)"
verdict: PASS-WITH-CONDITIONS
adversary_disposition: CONCUR-WITH-FLAGS
ready_for_downstream_recommendation: true   # adversary gate CLEARS with flags; operator-sovereign Gate-A + PT-02 remain independent build-blockers (carried correctly by the HANDOFF)
evidence_grade_ceiling: "MODERATE — in-rite self-referential challenge per self-ref-evidence-grade-rule; STRONG is the downstream rite-disjoint review-rite critic's (PT-07), NOT this gate's"
tl_a_status: PASS
tl_b_status: CHALLENGE     # one AC-02 FLAG (non-load-bearing miscite) + one AC-02 ADVISORY
tl_c_status: PASS
hard_checks:
  G-RUNG: PASS
  G-CRITIC: PASS
  telos-Gate-C: PASS
  Gate-A-carried: PASS
  G-DEFER: PASS
  G-THEATER: PASS
challenges_raised:
  - id: CH-01
    taxonomy_id: AC-02
    tl_clause: B
    severity: FLAG
    target_element: "§2 Correction 3, parenthetical anchor `_platform.py:15-17`"
    rationale: "Cites _platform.py:15-17 for 'verticals = id/key/name only', but :15-17 is the Business model docstring (class Business at :9). The verticals schema is the Vertical model at :131-149 (fields :145 id / :146 key / :147 name). Mis-attributed line anchor."
    load_bearing: false
    why_not_blocking: "The claim 'verticals has no source column' is independently verified LIVE (grep source in Vertical body :131-149 = 0 hits) AND correctly cited in the SAME handoff at §7 TL-A-2 basis (`_platform.py:131-162`). The wrong anchor is redundant, not sole support."
    falsification_pathway: "Correct §2 Correction 3 anchor `:15-17` -> `:142-147` (verticals model fields). On correction, CH-01 clears and verdict revises toward clean PASS."
    remediation_hint: "Single-line edit in §2 Correction 3; naturally absorbed by the sprint-0 anchor re-verification the HANDOFF already mandates (Correction 7 / telos code_verbatim_match:false)."
  - id: CH-02
    taxonomy_id: AC-02
    tl_clause: B
    severity: ADVISORY
    target_element: "§2 Correction 1, anchor `grpc/handlers/vertical.py:128`"
    rationale: "Cites grpc/handlers/vertical.py:128 for the no-delete invariant, but :128 is the create_vertical RPC handler signature. It attests create-only-ness INDIRECTLY (by absence of a delete handler), not a delete-refusal directly."
    load_bearing: false
    why_not_blocking: "The no-delete invariant is robustly and directly confirmed at services/vertical.py:9 (docstring '- No Delete operation (verticals are permanent)') and proto/autom8/data/v1/__init__.py:667 ('Verticals are permanent reference data - no delete operation is provided'). The gRPC anchor is corroborative looseness, not error."
    falsification_pathway: "Re-anchor to the create-only surface or annotate that :128 attests create-only by absence-of-delete. ADVISORY — does not gate."
arch_ref_citations:
  - "AQ:SRC-006"   # Martin — package metrics / ADP / instability: grounds the hub-stability (I~0) + single-writer-locus reasoning behind REC-1 / TL-A-3
  - "DP:SRC-002"   # Martin — SOLID/SRP: a single canonical writer localizes the write responsibility (one reason to change); the second-writer challenge is an SRP argument
  - "AQ:SRC-004"   # Mo et al. — anti-pattern detection / cumulative error-proneness: grounds the second-writer + FK-parent-SPOF challenge frame
  - "AV:SRC-001"   # Messick — construct validity: grounds this verdict's own validity argument (what 'design-validated' measures, and the MODERATE ceiling)
---

# ADVERSARY-REPORT — dyn-enum-contract arch -> 10x-dev HANDOFF (iter 1)

> **VERDICT: PASS-WITH-CONDITIONS** · disposition CONCUR-WITH-FLAGS · in-rite ceiling MODERATE.
> The validated design is architecturally sound: all three TL-A predictions are genuinely
> falsifiable AND were verified LIVE against the real cross-repo tree (producer
> `autom8y-asana origin/main ca28251d`, consumer `autom8y-data HEAD 92d3606d`). All six dispatch
> hard checks PASS. One non-load-bearing TL-B citation FLAG (CH-01) and one ADVISORY (CH-02).
> No BLOCK-class finding. `ready_for_downstream: true` is recommended; the operator-sovereign
> Gate-A (telos countersign) and PT-02 fork remain independent build-blockers the HANDOFF
> carries correctly.

This challenge is a FALSIFIER pass, not an analysis. I did not re-map topology or re-derive the
design; I attacked the HANDOFF's load-bearing claims by reproducing their falsifiers live.

---

## 1 · Challenge Summary

**Target SHA**: `sha256:6af7b54fdf7d8101fed0ece9d0a32788ed54f41c816349e181ac1c24d5ca33d0`
(cwd working-tree draft; NOT committed to origin/main — `git show origin/main:<path>` returns
empty. A draft HANDOFF in the working tree is expected at this rung; recorded for the ledger.)

**Verdict**: PASS-WITH-CONDITIONS. Sound design; one FLAG; named enumerable conditions below (§5).

| Threat-line | Status | One-line |
|-------------|--------|----------|
| TL-A-1 (MySQL settlement) | PASS | 4/7 MySQL receipts reproduced verbatim; `ON DUPLICATE KEY UPDATE` exemplar live; PG canary 0 hits; `GET_LOCK` 0 hits (honest prospective tag). Falsifiable, not tautological. |
| TL-A-2 (no source column / orphan-risk) | PASS | Vertical body :131-149 = id/key/name only; 0 `source` occurrences; snapshot-replace DELETE genuinely unconditional-catastrophic if copied. Discriminates the account-status false-friend. |
| TL-A-3 (sole writer — REC-1 headline) | PASS | LIVE write-sweep across ALL `autom8y-data/src` = EXACTLY ONE write (`services/vertical.py:212`). REST `:283` + gRPC `:174` both route THROUGH `VerticalService.create`. No bespoke second writer. |
| TL-B (citations) | CHALLENGE (FLAG) | ~22 cites resolved at declared anchors (producer @ origin/main, NOT cwd-only). CH-01 AC-02 FLAG: §2 Correction 3 `:15-17` mis-attributed. CH-02 AC-02 ADVISORY: grpc `:128` looseness. |
| TL-C (disposition) | PASS | 3 least-certain points enumerated + UV-P-tagged; GET_LOCK 0-hits-today disclosed; U-1 row-counts UV-P; Gate-A OPEN disclosed. No buried load-bearing UV-P (no AC-04). |

**Dispatch hard checks** (BLOCK-class if violated — NONE violated):

| Check | Result | Evidence |
|-------|--------|----------|
| G-RUNG (no round-up to proven/merged/live) | PASS | frontmatter `rung: authored` + `ready_for_downstream: false`; §6 rung ladder; §13 scope disclaimers. Zero round-up language. |
| G-CRITIC (both critics named; arch self-grade <= MODERATE) | PASS | §6 names Critic 1 (in-rite adversary, MODERATE) + Critic 2 (rite-disjoint review critic, STRONG); frontmatter `evidence_grade_ceiling: MODERATE`. No self-STRONG. |
| telos-integrity §3 Gate-C (every shipped/verified token carries {path}:{line} OR DEFER tag) | PASS | §8 full TL-B receipt table; genuinely-unattested items carry explicit `[UNATTESTED — DEFER-POST-HANDOFF]` (GET_LOCK, ~43K rows, EC-2 cred, key-mismatch severity). No bare completion claim. |
| Gate-A carried (telos-DRAFT uncountersigned BLOCKING-before-build) | PASS | §5 + §1 + §12 carry it; telos file live-confirmed DRAFT-PENDING-OPERATOR-COUNTERSIGN. |
| G-DEFER (DEFER-1 recommended-as-deferred, N>=3, no scope-creep) | PASS | §4 R5 + §9 Option 3 + §13: registry escalate-only on N>=3 conjunction; one-way-door refusal explicit. |
| G-THEATER (no claim without a falsifier) | PASS | every TL-A prediction has a `How to falsify`; every R1-R8 carries RED->GREEN; I reproduced the falsifiers live. |

---

## 2 · TL-A Analysis — per-prediction falsifier reproduction (LIVE)

Each prediction was attacked by reproducing its named falsifier against the declared truth
anchors. A prediction that survives a live falsification attempt is disposition-forcing, not
theater [AQ:SRC-004 Mo et al. 2019 — anti-pattern detectability] [STRUCTURAL | MODERATE].

### TL-A-1 — MySQL settlement (real falsifier, NOT a tautology)

Spot-checked >= 2 of the 7 EC-1 receipts at `autom8y-data HEAD 92d3606d` (reproduced 4):

- R1 `core/config.py:217` -> `MySQL URL in format: mysql+asyncmy://user:pass@host:port/database` [MATCH]
- R2 `core/config.py:222` -> `return self.mysql_url.replace("mysql://", "mysql+asyncmy://")` [MATCH]
- R5 `services/base.py:387` -> `for prefix in ("mysql+asyncmy://", "mysql+aiomysql://", "mysql://"):` [MATCH]
- R6 `pyproject.toml:99` -> `"pymysql>=1.1.0",  # Direct MySQL driver ...` [MATCH]
- Shape-B exemplar `api/services/forwarding_binding_store.py:155/:218/:252/:315` -> all four reference
  `INSERT ... ON DUPLICATE KEY UPDATE` LIVE [MATCH]. (Exemplar is verticals-agnostic — `grep -i vertical` = 0 hits — correctly cited as an idiom exemplar, not a verticals writer.)

**Falsifier reproduced**: `grep -rn "pg_advisory\|ON CONFLICT\|asyncpg" autom8y-data/src` = **0 hits**.
The PostgreSQL canary the prediction forbids is genuinely ABSENT. `GET_LOCK` = **0 hits** today
(matching the honest `[UNATTESTED — DEFER-POST-HANDOFF: lock-intro-sprint-2]` prospective tag).

**Disposition**: Not a tautology — the settlement rests on reproducible live receipts and the
prediction would fire FALSE if the sprint-2 build emitted PG syntax. PASS.

### TL-A-2 — snapshot-replace DELETE / no source column (discriminates the false-friend)

- Vertical model body `_platform.py:131-149`: fields are `vertical_id`(:145 -> col `id`),
  `vertical_key`(:146 -> col `key`, unique), `vertical_name`(:147 -> col `name`, unique). **id/key/name only.**
- `grep -n source _platform.py` within the Vertical body (:131-149) = **0 hits**. Every `source`/
  `source_id` occurrence belongs to `Offer` (:235) or `account_status` (:550), NOT verticals.
- The account-status DELETE at `_platform.py:498` is `DELETE FROM account_status WHERE source = 'section_classifier'` — **scoped by a `source` column verticals does not possess.** Copying the
  idiom to verticals therefore requires an *unconditional* `DELETE FROM verticals`, which wipes
  the FK-parent hub. The false-friend discrimination is correct and live-grounded.

**Falsifier**: if the FR-008 dry-run passed a DELETE against an FK-referenced key (no ORPHAN-RISK),
the guard would be incomplete. The FK edges that make this catastrophic are real and confirmed:
Business FALLBACK `:72` (`foreign_key="verticals.id"`), Question `:451` (`foreign_key="verticals.id"`),
Offer STRING FK `:162` (`foreign_key="verticals.key"`). PASS.

### TL-A-3 — sole canonical writer (REC-1 headline; RUN LIVE as dispatched)

**The load-bearing grep, run live across ALL of `autom8y-data/src`:**

```
grep -rn 'add(Vertical(|add(vertical)|delete(vertical|delete(Vertical|DELETE FROM verticals|UPDATE verticals' src/
  -> src/autom8_data/services/vertical.py:212:        self._session.add(vertical)
  (EXACTLY ONE hit — the sole write)
```

I actively hunted candidate second-writers and disproved each:
- `api/routes/verticals_crud.py:283` — the `POST /api/v1/verticals` write endpoint — calls
  `service.create(...)`, routing THROUGH `VerticalService`. No direct `session.add(Vertical(...))`.
- `grpc/adapters/vertical.py:60/:174` — constructs `VerticalService(session)` and calls
  `self._service.create(...)`. Routes through. Not a direct writer.
- `grpc/handlers/vertical.py` — delegates to the adapter. No direct write.
- `forwarding_binding_store.py` — `ON DUPLICATE KEY UPDATE` present but verticals-agnostic (0 vertical refs).

`services/vertical.py:212` is `self._session.add(vertical)`; the service exposes list/get/get_by_key/
create only — **no update, no delete** (`:9` docstring; `:48` IMMUTABLE_FIELDS). REC-1's premise
(VerticalService is the canonical write locus; route the new endpoint through it) HOLDS at HEAD.
This is the single-responsibility / single-writer locus argument [DP:SRC-002 Martin SOLID/SRP]
[MODERATE] and the hub-stability rationale [AQ:SRC-006 Martin ADP/instability] [STRONG]. PASS.

> **Load-bearing result for the parent**: the sole-writer grep is GREEN. No second writer exists
> at `92d3606d`. If a `vocab_upsert`/`VocabUpsertStore` or any direct `verticals` write had appeared
> outside `services/vertical.py`, this would be a BLOCK. It did not.

---

## 3 · TL-B Analysis — citation resolution (G-PROVE)

~22 `{path}:{line}` cites spot-verified. **Producer ([P]) cites were verified at
`origin/main ca28251d` — the declared `producer_truth_anchor` — NOT at cwd** (cwd `f4f924d2` is
25 commits behind; a cwd-only resolution would have been a finding per dispatch). They resolve at
the correct anchor:

| Cite | Anchor | Resolved verbatim |
|------|--------|-------------------|
| `services/gid_push.py:62` [P] | origin/main | `GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"` |
| `services/gid_push.py:95` [P] | origin/main | `val = os.environ.get(GID_PUSH_ENABLED_ENV_VAR, "").lower()` |
| `services/gid_push.py:163` [P] | origin/main | `async def _push_to_data_service(` |
| `services/gid_push.py:328` [P] | origin/main | `return True  # Nothing to push is not a failure` |
| `services/gid_push.py:554` [P] | origin/main | `return True  # Nothing to push is not a failure` (gid_push.py = 571 lines; :554 in-EOF) |
| `services/gid_push.py:490` [P] | origin/main | `"vertical": str(vertical),` (untyped seam R8) |
| `models/custom_field.py:113` [P] | origin/main | `enum_options: list[CustomFieldEnumOption] | None = Field(` |
| `services/vertical.py:212` [C] | data HEAD | `self._session.add(vertical)` (sole writer) |
| `services/vertical.py:9` [C] | data HEAD | `- No Delete operation (verticals are permanent)` |
| `proto/.../__init__.py:667` [C] | data HEAD | `Verticals are permanent reference data - no delete operation is provided.` |
| `core/config.py:217/:222` [C] | data HEAD | MySQL URL + asyncmy normalization |
| `pyproject.toml:99` [C] | data HEAD | `"pymysql>=1.1.0"` |
| `_platform.py:146/:147/:162` [C] | data HEAD | vertical_key unique / vertical_name unique / offers.category STRING FK |
| `_platform.py:498` [C] | data HEAD | `DELETE FROM account_status WHERE source = 'section_classifier'` |
| `_platform.py:72/:451` [C] | data HEAD | Business + Question FK to verticals.id |
| `api/models_comparison.py:62` [C] | data HEAD | `vertical: str = Field(` (untyped consumer seam) |

**Correction 7 falsifiable claim verified**: `resolver_schema.py` is **475 lines** at origin/main,
so the stale `:491` IS genuinely past EOF. The stale-anchor remediation is sound.

**CH-01 (AC-02, FLAG, tl_clause B)** — §2 Correction 3 cites `_platform.py:15-17` for "verticals =
id/key/name only", but `:15-17` is inside the **Business** model docstring (class Business `:9`;
`:15-17` = guid/business_name/office_phone API field mapping). The verticals schema is the Vertical
model at `:131-149` (fields `:145/:146/:147`). **Mis-attributed anchor.** NON-LOAD-BEARING: the
underlying claim is independently verified live (0 `source` in the Vertical body) AND correctly
cited in the SAME document at §7 TL-A-2 basis (`_platform.py:131-162`). A 10x-dev sprint-0 architect
cross-referencing the `:15-17` parenthetical would land in the wrong model — hence FLAG, not silent.

**CH-02 (AC-02, ADVISORY, tl_clause B)** — §2 Correction 1 cites `grpc/handlers/vertical.py:128`
for the no-delete invariant; `:128` is the `create_vertical` handler signature (attests create-only
by absence-of-delete, indirect). Invariant directly confirmed at `vertical.py:9` + `proto:667`.
Corroborative looseness; does not gate.

No non-resolving cite, no stale-cwd-only cite, no mis-attribution that touches a load-bearing claim.

---

## 4 · TL-C Analysis — disposition honesty

§9 enumerates three least-certain points, each tagged or routed — no over-confidence, no buried
load-bearing UV-P (no AC-04):

1. **GET_LOCK/RELEASE_LOCK contention under concurrency** — honestly disclosed as NOT yet in the
   consumer tree (`[UNATTESTED — DEFER-POST-HANDOFF: lock-intro-sprint-2]`); I confirmed **0 hits**
   live. Routed to sre post-build. Correctly framed as runtime, not structural-correctness.
2. **First-sync key-mismatch severity** — `UNKNOWN-UNTIL-DRY-RUN`, tagged UV-P; the FR-008 dry-run
   is the correct guard ("arch cannot assess without a live DB read — no creds at this altitude").
3. **ads `VerticalNormalizer` intent** — routed CRR-002 to debt-triage; does not block the telos.

`U-1` FK row counts (~43K) are consistently UV-P-tagged in §8 and §12 (never asserted as fact).
Gate-A OPEN is disclosed in §1/§5/§12. The disposition is well-calibrated [AV:SRC-001 Messick —
construct validity: the artifact articulates what it measures and where its evidence stops]
[STRONG]. PASS.

---

## 5 · Remediation Pathway (PASS-WITH-CONDITIONS — enumerable conditions the 10x build must satisfy)

Ordered. C1 is the only adversary FLAG; C2–C6 are build-discipline conditions the HANDOFF already
carries and that I am binding as gate-conditions.

1. **C1 [adversary FLAG — CH-01]** — Correct §2 Correction 3 anchor `_platform.py:15-17` ->
   `_platform.py:142-147` (verticals model fields), to match the correct §7 `:131-162`. Single-line
   edit; absorbs naturally into the sprint-0 anchor re-verification. Non-blocking.
2. **C2 [operator-sovereign, HANDOFF-carried]** — Gate-A: operator countersigns
   `.know/telos/dyn-enum-contract.md` (live-confirmed DRAFT/OPEN) BEFORE build start. Build BLOCKING.
3. **C3 [operator-sovereign, HANDOFF-carried]** — PT-02 fork: operator resolves
   `autom8y-data ACTIVE_RITE=dre` (Option A 10x-synced-into-data vs Option B dre-native) before sprint-2.
4. **C4 [build-discipline, HANDOFF-mandated]** — sprint-0 architect re-verifies ALL `{path}:{line}`
   anchors at the sprint-0 build HEAD (per Correction 7 + telos `code_verbatim_match:false`). My
   verification anchored to `ca28251d` / `92d3606d`; origin/main moves and cwd is already 25 behind.
5. **C5 [sprint-2 review-gate]** — re-run the three resolved-watch conditions at sprint-2 PR review:
   R-EC1 (no `ON CONFLICT`/`pg_advisory`/`asyncpg` in the vocab chain), R-F1 (sole-writer grep stays
   GREEN), R-F3 (zero DELETE on `verticals`). I confirmed all three GREEN at current HEAD; they must
   hold at build HEAD.
6. **C6 [post-build, UV-P]** — GET_LOCK contention assessed by sre after the lock primitive is
   introduced in sprint-2 (correctly deferred; 0 hits today confirmed).

CH-02 is ADVISORY (re-anchor grpc `:128` or annotate); it is not a gate-condition.

---

## 6 · Falsification of This Report (anti-dogma — what observation revises THIS verdict)

This verdict is falsifiable by a concrete observation in either direction:

- **Revise to BLOCK** if, at the sprint-2 build HEAD, the live write-sweep
  `grep -rn 'add(Vertical(|INSERT INTO verticals|session.delete.*[Vv]ertical' autom8y-data/src`
  returns ANY hit outside `services/vertical.py` (a second writer materialized -> REC-1 falsified),
  OR `ON CONFLICT`/`pg_advisory`/`asyncpg` appears in the `/vocabularies/sync` service chain (EC-1
  settlement not propagated). Either fires the two-iteration cap: BLOCK -> ONE remediation revision.
- **Revise to clean PASS** if C1 (the §2 Correction 3 `:15-17` -> `:142-147` fix) lands AND Gate-A
  closes AND PT-02 is resolved — at which point the sole adversary FLAG clears.
- **This report itself is in-rite and caps at MODERATE** per `self-ref-evidence-grade-rule`. It does
  NOT confer STRONG. STRONG is the downstream rite-disjoint review-rite critic's at PT-07 (Critic 2),
  attesting the LIVE round-trip against the operator-countersigned telos — a different artifact, a
  different gate, a different scope. My PASS-WITH-CONDITIONS clears the in-rite adversary gate only.

**Acid test**: an adversary of this report can falsify my PASS-WITH-CONDITIONS with one command
(the sole-writer grep at build HEAD). The pathway is concrete, not dogma.

---

*arch-adversary · in-rite sprint-5 gate · iter 1 (clean re-fire) · CONCUR-WITH-FLAGS · MODERATE ceiling.*
*Read-only against all repos: no target mutation, no commit, no production-mutating lever executed.*
