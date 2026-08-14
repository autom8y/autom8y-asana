---
type: review
status: accepted
date: 2026-08-14
initiative: chain-of-custody-closure
subject: "PR #365 — CC-1 swap-detector closure (coc-cc1-reconverge @ 79d9f4a1)"
rung: PR-UP-MERGE-HELD (unchanged by this review)
verdict: GO-WITH-CONDITIONS
reviewer: audit-lead[hygiene]
rite_disjoint_from_author: true (author rite = 10x-dev)
self_assessment_cap: MODERATE
---

# PRE-MERGE NCSR REVIEW — PR #365 (CC-1 swap-detector closure)

Landing-time audit, 2026-08-14. Phase-1 build + NCSR verification occurred 2026-08-13;
this review asks: has anything decayed since, and is the diff merge-worthy today?
Read-only review. No gh write calls, no git write verbs, no approve/merge/comment.

## 0. Verdict

**GO-WITH-CONDITIONS.**

- **C-1 (mechanical, pre-merge):** mergeStateStatus is `BEHIND` (strict status checks;
  main advanced by #367 `2ea46474`). Update-branch + re-observe green is REQUIRED
  before merge. The update does not change the reviewed diff — main's sole new commit
  touches only `.ledge/` paper (zero file intersection with the PR's 12 entries;
  receipt §5).
- **C-2 (identity fence):** the merged content must be exactly
  `79d9f4a157b2c7ceed5f24e1a072f3b1b56213e5` (the sole authored commit). A
  branch-protection update-branch merge commit is acceptable; any NEW content-bearing
  commit voids this review and requires re-audit.
- **A-1, A-2:** two advisory (non-blocking) findings at §7.

## 1. Artifact identity + CI state (receipts)

| Probe | Result |
|---|---|
| `gh pr view 365 --json headRefOid` | `79d9f4a157b2c7ceed5f24e1a072f3b1b56213e5` — MATCHES the Phase-1 reviewed SHA; single commit; no force-push, no new commits |
| `gh pr checks 365` | ALL required checks pass at head (4 test shards, lint/type, coverage gates, CodeQL, gitleaks x2, dependency-review, fuzz, OpenAPI drift, fleet conformance). `ci / Convention Check` + `ci / Integration Tests` + `[code]smith` report `skipping` (conditional jobs; required set is green — `mergeable: MERGEABLE`) |
| `mergeStateStatus` | `BEHIND` (strict=true; procedural, not a content conflict) |
| Merge-base | `d7560153` (= the branch's declared cut point, CC-1-EXIT-NOTE.md L4) |

## 2. Scope discipline — 12 entries vs declared scope (predicate i)

Declared scope: swap-detector mechanism closure (REC-001 shared canonicalization,
REC-003 schema splice, clause 4→4a/4b split, clause-3 narrowing disclosure) + exit note.

| File | Maps to |
|---|---|
| `src/autom8_asana/observability/payload_hash.py` (new) | REC-001 |
| `src/autom8_asana/readout/generation.py` | REC-001 call site A |
| `src/autom8_asana/observability/rail_delivery/delivery_receipt.py` | REC-001 call site B |
| `src/autom8_asana/readout/template.py` (`render_fallback_text`) | REC-001 dependency (D-4 text surface — the `{blocks,text}` canon needs a generation-side `text`) |
| `src/autom8_asana/readout/__init__.py` | REC-001 export collateral |
| `src/autom8_asana/observability/rung_receipts/schema.py` | REC-003 + 4b enum + N1 docs |
| `src/autom8_asana/observability/rung_receipts/join.py` | 4a/4b split + N1/N2 contract-truth |
| `tests/unit/test_swap_detector_closure.py` (new) | two-sided teeth |
| `tests/unit/test_readout_generation.py`, `tests/unit/test_rung_receipts.py` | collateral of the token remap + import removal — consequence, not creep |
| `tests/fixtures/rung_receipts/PROVENANCE.md` | swap-fixture derivation |
| `CC-1-EXIT-NOTE.md` | exit note (placement advisory A-1) |

**SCOPE-DISCIPLINED.** No unrelated drive-bys. The clause-3 material is disclosure of a
carried finding (docs + pinning tests, wire token deliberately NOT renamed), not creep.

## 3. Behavior preservation (the fundamental criterion)

The change ADDS detection; adjudication of every semantic move in the diff:

1. **No emitter touched.** The live `report_posted` delivery emitter is not modified
   anywhere in the diff. Zero live emit-path changes.
2. **Generation-side hash value changes** (`content_hash_of(blocks)` → 
   `canonical_payload_hash(blocks, text)`, generation.py). Intentional — this IS
   REC-001. Live blast radius: the census recorded ZERO `report_generated` rows
   (PROVENANCE.md), so no live consumer and no persisted digest corpus. That census
   is un-reprobed and rides as **CF-2 UV-P, not fact** (GATE-coc-pt03 §CF-2) —
   correctly carried, not asserted.
3. **Reason-token remap** (join.py): bare block-count disagreement now emits
   `block_count_mismatch` instead of the pre-CC-1 mislabel `content_hash_mismatch`.
   Wire-visible label change on `rung_e_not_observable_reason` — but additive enum
   (no value renamed/removed; contrast the clause-3 refusal, which is consistent:
   RENAME breaking, ADD not), corrects a documented over-claim, no live consumer
   (limb-(a) attestation is eunomia's and blocked until both halves land — exit
   note §9), and carries documented Phase-1 sign-off (GATE-coc-pt03-2026-08-13.md
   §2 CC-1 row names the 4a/4b split). REQUIRES-APPROVAL category: approval present.
4. **Public symbol removal** (`content_hash_of` dropped from `readout/__init__`).
   Own-hands landing-time grep: at PR head, zero surviving code references (only a
   historical mention in the payload_hash.py module docstring — intentional prose);
   at TODAY's origin/main, the only `content_hash_of` sites are the 6 this PR
   removes/updates — **no new importer appeared on main in the 24h since build**
   (receipt §5). Internal package, not a published API; CI green corroborates.
5. **`DeliveryReceipt` gains `content_hash: str | None = None`** inserted before
   `trace_id` — positional-construction order shifts; all in-repo construction is
   keyword-based (`from_event`) and CI is green. Contained.
6. **`DELIVERY_LOGS_INSIGHTS_QUERY`** gains `content_hash` in the field list —
   Logs Insights tolerates absent fields; non-breaking for the live hashless emitter.
7. **JSON-schema splice**: `content_hash` in `delivery.properties` but deliberately
   NOT in `required` — the schema still accepts every receipt the live emitter
   actually produces. Preservation-correct choice, reasoned in-code (schema.py).

**Verdict: behavior preserved on all live paths; the intentional semantic moves are
scoped, documented, pinned by tests, and carry Phase-1 sign-off.**

## 4. Over-claim hunt (N1/N2 disclosure + rung honesty)

Hunted across PR body, commit message, exit note, and code docs for a live-emitter
closure claim. **None found.**

- Commit: "close swap-detector **at the canonicalization seam**" — mechanism-level.
- PR body: "closes the swap-detector **at the mechanism level**"; critic "graded
  STRONG **only on its own re-derived legs**" — grade discipline correct (builder
  MODERATE ceiling honored).
- **N1** (clause-3 frozen wire-token, conservative fail-side): disclosed in PR body,
  join.py docstring, `NotObservableReason` docstring, pinned by `TestClause3Narrowing`
  (both UNKNOWN and HUMAN → `not_observable`; never passes a bad payload). Matches
  HANDOFF-coc-wave-close §1 CC-1 row.
- **N2** (clause-4a residual, live emitter hashless, rides CF-2): disclosed in join.py
  docstring and pinned by the sharpest honest test in the suite —
  `test_swap_on_a_hashless_delivery_is_still_undetected`. The residual is asserted
  AS undetected, not swept.
- Two-sided teeth per discriminating-canary-doctrine: RED on pristine tree used only
  pre-existing symbols (no ImportError theater); GREEN includes honest-direction pass
  + single-variable causation (`{'content_hash'}` alone flips the verdict). No defect
  injected into production code; the swap is a deliberately-wrong INPUT.

## 5. Staleness (24h decay check)

- Main since merge-base `d7560153`: exactly ONE commit — `2ea46474` (#367,
  docs(coc), `.ledge/` paper only, 15 files).
- Intersection with the PR's 12 files: **empty** (`comm -12` of the two sorted
  name-only lists → zero lines).
- No new importer of any touched symbol appeared on main (grep receipt §3.4).
- CI observations at head remain bound to `79d9f4a1` (head unchanged since Phase-1).

**Nothing decayed.** BEHIND is purely the branch-protection strictness clock.

## 6. Commit quality + secret scan

- Single commit, atomic (one concern), conventional format (`feat(observability):`),
  message states rung honestly ("Built dark at Q-4 HALT; raised to PR on operator
  word, merge held"). Independently revertible.
- Secret-shaped content: none. The census UUID `7c59f3d8-…` is an invocation
  identifier, not credential material; digests are payload sha256s. gitleaks +
  Secrets Scan both green. CR-5 honored (no credential values reproduced here).
- Generated junk: none in the 11 code/test/doc entries. See A-1 for the 12th.

## 7. Advisory findings (non-blocking)

- **A-1 — repo-root exit-note placement** [TACTICAL | MODERATE]: `CC-1-EXIT-NOTE.md`
  lands at the repository ROOT; main's root carries only `CHANGELOG.md` + `README.md`
  (git ls-tree receipt), and this repo's convention routes work-product artifacts to
  `.ledge/`. Recommend a post-merge relocation to `.ledge/decisions/` or
  `.ledge/handoffs/` — NOT pre-merge, since amending the branch would break the
  reviewed-artifact-equals-merged-artifact fence (C-2) and void Phase-1 NCSR.
- **A-2 — undisclosed canonicalization delta (ensure_ascii)** [TACTICAL | MODERATE]:
  the old delivery-side `content_hash` used `ensure_ascii=False`; the new shared
  canon uses json.dumps' default (`ensure_ascii=True`). Because
  `render_fallback_text` always emits non-ASCII ("·", "—"), the new canon's digests
  differ from what the OLD delivery-side function would have produced for every real
  payload. Contained: both call sites now share ONE symbol (internal consistency is
  the contract), the live emitter emits no hash, and no persisted digest corpus
  exists (per the CF-2-riding census). But the exit-note claim that the kept wrapper
  leaves importers "undisturbed" is import-compatible only, not digest-value-
  compatible. Recommend a one-line disclosure in the payload_hash.py docstring at
  next touch; no action required for this merge.

## 8. Hygiene-lens summary (GATE-scope selection per rubric §3)

| Lens | Verdict |
|---|---|
| 1 Boy Scout | CLEANER (over-claiming mislabel ended; contract docstrings truthful; residuals pinned) |
| 2 Atomic-Commit | ATOMIC-CLEAN (1 commit, 1 concern) |
| 3 Scope Creep | SCOPE-DISCIPLINED |
| 4 Zombie Config | NO-ZOMBIES (`content_hash_of` zero code survivors at head AND at today's main) |
| 5 Self-Conformance | SELF-CONFORMANT (rung/grade vocabulary used correctly; MODERATE self-cap honored by author) |
| 9 Architectural Implication | STRUCTURAL-CHANGE-DOCUMENTED (new shared canon module + additive schema enum, both reasoned in-code) |
| 11 Non-Obvious Risks | 2 advisories (A-1, A-2) |

Aggregate: **CONCUR-WITH-FLAGS** → maps to **GO-WITH-CONDITIONS** at the merge gate.

## 9. Attestation

| Claim | Verified via | Grade |
|---|---|---|
| Head = 79d9f4a1, 1 commit | `gh pr view --json headRefOid,commits` | MODERATE (own-hands, self-cap) |
| CI green at head; BEHIND | `gh pr checks 365` / `mergeStateStatus` | MODERATE |
| Zero main-overlap with PR files | `git diff --name-only d7560153..origin/main` ∩ PR files = ∅ | MODERATE |
| No surviving `content_hash_of` importer | `git grep` at head + origin/main | MODERATE |
| N1/N2 disclosed, no over-claim | full-diff read + PR body + commit msg | MODERATE |

Self-assessment capped at MODERATE per self-ref-evidence-grade-rule; no STRONG is
asserted on the author's legs. STRONG on the mechanism belongs to the Phase-1
rite-disjoint critic's own-hands re-derivation, leg-scoped, and is cited, not inherited.
