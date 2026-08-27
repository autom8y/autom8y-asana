---
type: adversary-report
subtype: arch-adversary-challenge
target_handoff: ".ledge/reviews/HANDOFF-arch-to-10xdev-entity-resolution-2026-07-08.md"
target_handoff_sha: "sha256:993c41f58a341d830f3264186fba355239ca4b0fc49caf75ae576cce18b74b29"
challenger_agent: arch-adversary
initiative: entity-resolution-primitive
date: "2026-07-08"
iter: 1
verdict: PASS-WITH-CONDITIONS
adversary_disposition: CONCUR-WITH-FLAGS
tl_a_status: PASS
tl_b_status: PASS
tl_c_status: PASS
delta_scope_attested: false
challenges_raised:
  - id: CH-01
    taxonomy_id: AC-UNMAPPED
    tl_clause: A
    severity: ADVISORY
    target_element: "ITEM-1..4 'TL-A falsifiable prediction' lines (HANDOFF :44, :55, :67, :79)"
    rationale: "The per-item TL-A predictions are build-verification gates (dry-run resolves; grep returns 0 lines) rather than >=180-day forward-looking falsifiable claims. They read acceptance-criteria-adjacent. AC-05 (acceptance-as-prediction conflation) does NOT fire because they are not placed in a predictions:[] frontmatter field masquerading as horizon predictions; each is honestly labeled and states a real falsification condition ('if X, the design is falsified'). Disposition-forcing for the build, so not a defeat of TL-A intent."
    falsification_pathway: "N/A for ADVISORY — does not drive the verdict. If a future re-issue promotes these into a predictions:[] frontmatter block with expiry fields, re-run AC-05; a binary sprint-end completion gate placed there would fire BLOCKING."
    remediation_hint: "None required. Optionally annotate each as 'build-gate (immediate), not horizon prediction' to pre-empt AC-05 confusion at CHALLENGED-2 if this ever iterates."
  - id: CH-02
    taxonomy_id: AC-UNMAPPED
    tl_clause: B
    severity: FLAG
    target_element: "ITEM-6 TL-B citation 'models/business/fields.py:271' (HANDOFF :99, via DEFECT :20-37)"
    rationale: "The citation anchors the claim 'STANDARD_TASK_OPT_FIELDS deliberately EXCLUDES memberships.section.* (LIST/sweep consumer, not a get()-path detection input)' at fields.py:271. At origin/main (e5402cbd) line 271 is 'DETECTION_MEMBERSHIP_OPT_FIELDS: frozenset[str] = frozenset('. The substantiating comment ('memberships.section.name is deliberately EXCLUDED -- LIST/sweep ... not a get()-path detection input') is at :268 and STANDARD_TASK_OPT_FIELDS itself is at :232. The claim is TRUE; the line anchor is off by ~3 lines. This is imprecision, not fabrication, and it lives in the DEFERRED SIBLING-1 leg (ITEM-6, DEFER-WATCH) — not in any load-bearing Phase-1 prediction."
    falsification_pathway: "Re-anchor the citation to fields.py:268 (the EXCLUDED comment) or fields.py:232 (STANDARD_TASK_OPT_FIELDS definition). When the anchor points at the exact substantiating line, this FLAG clears."
    remediation_hint: "Change 'models/business/fields.py:271' to 'models/business/fields.py:268' (comment) in ITEM-6 TL-B citations and the DEFECT cross-reference. Cosmetic; does not affect the deferral disposition."
arch_ref_citations:
  - "AV:SRC-001"
  - "AQ:SRC-006"
  - "AQ:SRC-004"
---

# ADVERSARY-REPORT — entity-resolution-primitive (iter 1 / CHALLENGED-1)

## 1. Challenge Summary

**Verdict: PASS-WITH-CONDITIONS** (`adversary_disposition: CONCUR-WITH-FLAGS`).

The outbound arch -> 10x-dev HANDOFF survives the four dispatch BLOCK-triggers
(re-mint, B5 get_gid_map reintroduction, missing 2-sided test, nonexistent
file:line). TL-A, TL-B, and TL-C all clear at PASS. Two non-BLOCKING challenges:

- **CH-01 (ADVISORY, AC-UNMAPPED, TL-A)** — per-item "TL-A falsifiable prediction"
  lines are build-verification gates, not >=180-day horizon predictions. Honestly
  framed; AC-05 does NOT fire. Does not drive the verdict.
- **CH-02 (FLAG, AC-UNMAPPED, TL-B)** — one DEFER-leg citation (`fields.py:271`)
  is off by ~3 lines from its substantiating comment (`:268`). Claim TRUE, anchor
  imprecise, in the deferred SIBLING-1 leg only.

Neither is load-bearing on the Phase-1 flagship. Verification framing per
construct-validity discipline [AV:SRC-001 Messick 1989] [MODERATE | self-ref cap].

## 2. TL-A Analysis (per-prediction structural-grounding audit)

Every claim in the HANDOFF body carries a `file:line` SVR and each shippable ITEM
(1..4) carries a labeled TL-A falsifiable prediction. Audit:

- **ITEM-1** (HANDOFF :44): "construct `HierarchyIndex()`, register 3 synthetic
  child->parent->BUSINESS-member nodes, walk resolves root at `ancestor_depth==2`
  WITHOUT a store handle; if it needs `UnifiedTaskStore`, falsified." Observable,
  disposition-forcing, immediate (unit test). The store-independence assertion is
  independently corroborated: `git grep get_ancestor_chain|get_parent_chain_async|
  UnifiedTaskStore` over `onboarding_walkthrough/` at origin/main returns ZERO hits
  (all three patterns, count=0). The self-warm mandate is therefore not a design
  preference but a verified structural necessity. **PASS.**
- **ITEM-2** (HANDOFF :55): "`post_template_comment(task_gid=1215766139321621,
  execute=False)` dry-run RESOLVES (no `ContactCardBusinessAmbiguous`) and composes
  office guid `7363c7ea-66f8-487f-9f6e-c7a12a63d33f`; if it still refuses ambiguous,
  falsified." The target guid matches spike:24-28 verbatim. Falsifiable against live
  Asana. **PASS.**
- **ITEM-3** (HANDOFF :67): "`post_contact_card(play_gid=1215766139321621,
  execute=False)` returns non-`no_holder` rather than raising
  `ContactCardBusinessAmbiguous`; if it still raises on TWC, falsified." Falsifiable.
  **PASS.**
- **ITEM-4** (HANDOFF :79): "`grep -n 'get_gid_map\|DataServiceClient'
  office_resolution.py` returns 0 lines AND T-1 resolves under `NullCacheProvider()`;
  if either fails, B5-safety/correctness falsified." Mechanical, binary, honest.
  **PASS.**

Depth arithmetic internal-consistency check: the walk spec (TDD §2.1 step 2)
increments `depth` after advancing to `parent`. TWC chain is PLAY(self) ->
`1214127290389479`(d1) -> `1214127219419742`[BUSINESS](d2). Match at grandparent =>
`ancestor_depth==2`. The T-1 prediction (`ancestor_depth==2`) is consistent with the
spec. No off-by-one.

**AC-05 non-fire rationale**: predictions are acceptance-adjacent but honestly labeled
and each states a genuine falsification condition. They are NOT smuggled into a
`predictions:[]` frontmatter field as horizon claims. Predictive-validity horizon
discipline [AQ:SRC-006 / Kane 2006 argument-based validity] is respected in intent.
Logged as CH-01 ADVISORY (AC-UNMAPPED), not BLOCKING. **TL-A: PASS.**

## 3. TL-B Analysis (per-citation resolution and invocation audit)

Verified against origin/main (`e5402cbd`, == the intact worktree
`wt.releaser.wholebody-fg.20260708-134539`; local main `f3d8eec1` is stale and was
NOT used, per the HANDOFF's own instruction at :19). Every load-bearing SVR resolves
AND supports its claim:

| Citation | Verified at origin/main | Supports claim? |
|---|---|---|
| `hierarchy.py:57` HierarchyIndex | class HierarchyIndex near :57 | YES |
| `hierarchy.py:87-90` HierarchyTracker wrap | HierarchyTracker delegation :87-90 | YES |
| `hierarchy.py:96` register | `def register(` at :96 | YES |
| `hierarchy.py:160-182` (`:175` empty-on-unregistered) | get_ancestor_chain; ":175" doc = "Empty list if task ... is not registered" | YES |
| `entity_registry.py:299` get_by_gid | `def get_by_gid(...) -> EntityDescriptor \| None` :299 | YES |
| `entity_registry.py:445-446` BUSINESS ROOT | category=EntityCategory.ROOT, primary_project_gid="1200653012566782" | YES |
| `entity_registry.py:1203` get_registry | `def get_registry()` :1203 | YES |
| `project_registry.py:21` BUSINESS_PROJECT | `BUSINESS_PROJECT = "1200653012566782"` :21 | YES |
| `template_comment.py:217-229` _company_id_from_task | reader present, reads "Company ID" cf | YES |
| `template_comment.py:232-261` _resolve_office_guid | phone-first body (the repoint target) | YES |
| `template_comment.py:319-327` TaskOfficeMismatch | crown-jewel supplied==resolved guard | YES |
| `contact_synthesis.py:374-414` _business_gid_by_phone (`:406-410` >1 raise) | phone bridge; "refusing to pick a receiver silently" | YES |
| `contact_synthesis.py:417-459` resolve_ranked_cards (`:434` phone call, `:435-436` no_holder) | signature + call + return | YES |
| `contact_synthesis.py:465-547` post_contact_card (`:468/:499` play_gid, `:503` call) | play_gid in scope; office_phone read; call | YES |
| `contact_synthesis.py:103` _BUSINESSES_PROJECT_GID | `= "1200653012566782"` literal parity | YES |
| `contact_synthesis.py:429` B5 get_gid_map comment | "the ratified get_gid_map path was falsified live at B5" | YES |
| `unified.py:709` get_parent_chain_async | store warm-path chain | YES |
| `cascade_validator.py:102-107` exemplar | pairs get_ancestor_chain + get_parent_chain_async (store-only) | YES |
| `intake_resolve.py:69-157` resolve_business | S2S phone-only via GidLookupIndex | YES |
| `intake_resolve_service.py:56-97` GidLookupIndex O(1) | resolve_gid_from_index | YES |
| `clients/tasks.py:209-235` cache hit path | completeness-canary hit-path region | YES |
| spike:9-19 / :24-28 / :29 / :46-48 | ambiguity / exact chain / one-ancestor invariant / monkeypatch driver | YES |
| defect:20-37 / :47-53 / :57-59 / F-2:40-43 | starvation / NullCacheProvider unblock / union-fix / env-knob non-bind | YES |

**Decisive-constraint verification**: the storeless-walkthrough premise (the entire
argument for why self-warm is PRIMARY, not optional) is empirically true at
origin/main — 0/0/0 hits for the three store-dependency patterns in
`onboarding_walkthrough/`. This is the single most load-bearing claim in the design,
and it holds.

**One imprecision (CH-02, FLAG)**: DEFECT-referenced `models/business/fields.py:271`
anchors the "STANDARD excludes memberships.section.*" claim; the substantiating
comment is at `:268` and `STANDARD_TASK_OPT_FIELDS` is at `:232`. Off by ~3 lines.
The claim is TRUE (the comment exists, the exclusion is real). This is a symbolic-
anchor precision defect [AQ:SRC-004 Mo et al. — auto-detectable citation drift],
confined to the DEFERRED SIBLING-1 leg (ITEM-6, DEFER-WATCH). It does not touch any
Phase-1 shippable prediction. FLAG, not BLOCKING.

**No nonexistent-file:line found.** `office_resolution.py` correctly does NOT exist
(it is the module to build). **TL-B: PASS** (one FLAG on a deferred leg).

## 4. TL-C Analysis (per-prediction disposition-force audit)

Every ITEM carries a genuine adversarial disposition naming a real failure mode:

- **ITEM-1**: names the COLD-INDEX trap (`get_ancestor_chain(play_gid)` returns `[]`
  on an unregistered gid, verified at hierarchy.py:175) and forecloses it via the
  self-warm AC-2. Disposition-forcing: qa-adversary must assert the walk NEVER calls
  `get_ancestor_chain(play_gid)` against a cold shared index. Honest.
- **ITEM-2**: names silent-fallback-masks-regression; mitigates via `method`
  provenance + DEFER-WATCH-1. Teeth: `DivergentOfficeResolution` on a mismatched
  fixture. Honest.
- **ITEM-3**: names the `office_phone->play_gid` signature flip touching the public
  `post_contact_card` contract; mitigates by noting callers already pass `play_gid`
  (verified: :465 param, :499 read). Honest.
- **ITEM-4**: names the self-referential-evidence problem and correctly assigns the
  MODERATE->STRONG lift to the target rite's independent 2-sided QA — NOT a re-cite of
  the spike driver. This is the honest inversion of inter-rater-reliability discipline
  [AV:SRC-001 Messick construct validity; AQ:SRC-006 argument-based validity].

**Supersession check (AC-03)**: the design supersedes the phone-only resolution
approach but does NOT silently invalidate it — the phone bridge is explicitly RETAINED
as a labeled fallback + crosscheck (ADR §Decision point 4; TDD §3 reuse ledger row
`_business_gid_by_phone` "LIFTED, not deleted"). Disposition on the prior approach is
explicit (fallback, not retraction). **AC-03 does NOT fire.**

**B5 engagement**: the ADR §"The B5 lesson" explicitly refuses to re-propose the
falsified `get_gid_map` path and the design reads the Asana tree directly. Verified:
the get_gid_map falsification comment is real (contact_synthesis.py:429), and T-3
mechanically gates its non-reintroduction. This is the honest converse of the
canonical BLOCK signal. **TL-C: PASS.**

## 5. Remediation Pathway (conditions to clear PASS-WITH-CONDITIONS -> PASS)

Ordered, specific, each pointing at the HANDOFF line/section to change:

1. **[CH-02, FLAG — clears the only verdict-driving condition]** Re-anchor the
   deferred-leg citation `models/business/fields.py:271` -> `models/business/fields.py:268`
   (the "deliberately EXCLUDED ... not a get()-path detection input" comment) in
   **HANDOFF ITEM-6 TL-B citations (:99)** and the DEFECT cross-reference. When the
   anchor lands on the substantiating line, TL-B is precision-clean.
2. **[CH-01, ADVISORY — optional, not verdict-driving]** In **HANDOFF ITEM-1..4**,
   annotate each "TL-A falsifiable prediction" as a build-gate (immediate), not a
   >=180-day horizon prediction, to pre-empt AC-05 confusion if this ever reaches
   CHALLENGED-2. No structural change required.

Condition (1) is sufficient to revise the verdict to PASS. Condition (2) is hygiene.

## 6. Falsification of This Report

This PASS-WITH-CONDITIONS verdict is falsified by any of the following concrete
observations (adversary-epistemic-integrity applies recursively):

- **The store-independence premise is false**: if `git grep -E
  "get_ancestor_chain|get_parent_chain_async|UnifiedTaskStore"` over
  `onboarding_walkthrough/` at origin/main returns ANY hit, the "self-warm is
  mandatory" design rationale weakens and ITEM-1's TL-A prediction becomes
  contestable. (Observed: 0 hits. If a re-run disagrees, revise.)
- **A load-bearing citation does NOT resolve at origin/main**: if any Phase-1 (ITEM-1..4)
  `file:line` I marked YES actually points at unrelated content at `e5402cbd`, the
  verdict must drop toward BLOCK. I checked each; a rite-disjoint re-grader running the
  same `git show origin/main:<path> | sed -n` probes should reproduce every YES.
- **The TWC chain/guid is wrong**: if the live parent chain of PLAY
  `1215766139321621` does NOT terminate at BUSINESS `1214127219419742` with Company ID
  `7363c7ea-66f8-487f-9f6e-c7a12a63d33f` at depth 2, ITEM-2/T-1 is falsified and the
  design's core claim collapses. (Corroborated only by spike:24-28, a self-authored
  same-rite artifact — the MODERATE ceiling is correct precisely because this is not
  yet independently confirmed. The target rite's live T-1 is the disjoint check.)
- **CH-02 is actually a fabrication, not imprecision**: if `models/business/fields.py`
  at origin/main contains NO "memberships.section deliberately EXCLUDED" comment at any
  nearby line, then CH-02 should escalate from FLAG toward BLOCKING (nonexistent
  citation). (Observed at :268; if absent on re-check, escalate.)
- **A BLOCK-trigger was missed**: if a rite-disjoint adversary finds a Phase-1 item
  that re-mints (rather than reuses) resolution, reintroduces get_gid_map, or ships
  without the 2-sided ITEM-4 plan, this verdict is wrong and must be BLOCK.

Self-citation discipline: this report grounds its framing in AV:SRC-001 (construct
validity), AQ:SRC-006 (argument-based validity horizon), AQ:SRC-004 (auto-detectable
citation drift). Self-ref evidence grade capped at MODERATE per
self-ref-evidence-grade-rule — no STRONG asserted without a rite-disjoint second
grader. iter=1; DELTA-scope not applicable (no prior report).
