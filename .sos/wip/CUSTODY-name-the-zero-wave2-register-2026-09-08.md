# CUSTODY REGISTER — name-the-zero WAVE 2 ("the containment wave")
Main thread is the writer (potnia holds no Write grant on this lane).

## ENTRY — envelope W2-ENTRY · 2026-09-08 · PT-07
- **envelope id:** W2-ENTRY (dispatch envelope; lands nothing)
- **payload class:** artifact authoring + two code BUILDS with merges HELD
- **declared kind + posture:** posture is PER WORKSTREAM, never inherited by proximity.
  S-13 governance · S-14 remediation · S-15 observability · S-16 diagnosis(read-only) · S-17 instrument-consumer · S-18 extraction. H2 NOT DISPATCHED (HELD, build AND land).
- **image-event law:** C-1 PRESERVED PER ENVELOPE. Envelope 1 = S-14 alone. Envelope 2 = S-15. Bundling = REFUSAL. Folding the cure into #1941 is FORBIDDEN.
- **disjointness ruling, VERBATIM as re-verified:** `service-deploy-dispatch.yml` triggers on `push:[main] paths:['services/**']` + `workflow_dispatch`, NEVER on `pull_request`. **Opening a PR deploys nothing.**

## FENCE-CHECK (own-hands, 2026-09-08, main thread)
| fence | reading | verdict |
|---|---|---|
| head `b9bbfadc` frozen | `git ls-remote` → `b9bbfadc` | **FROZEN** — no third lapse |
| base `057e2727` frozen | `git ls-remote` → `057e2727` | **FROZEN** |
| R-35 scope | `RATIFICATION-post-wave1-sitting-2026-09-05.md:26` verbatim — *"W0 image: HOLD the EBI freeze (no apply either way) until D. answers what `salkin-safe-routing` changes."* | **UNCHANGED** |
| EBI footprint, `6870d97c`→`origin/main cc88b75e` (135 commits) | `services/email-booking-intake` = **0 files**; `terraform/services/email-booking-intake` = **3 files, +58/−31** | unchanged vs Addendum L; image source untouched |
| new span `71bf8c17`→`cc88b75e` | 1 commit, EBI footprint **0 files** | immaterial |
| Blocker C, own-hands | intake `Code.ImageUri` = `…@sha256:76c21a00bcb122b264e8623d181f70a081198f86faf5d1e75d4964df77600dfe`, LastModified **2026-09-05T16:31:56Z**; reconcile + nudge `:67d89d7` (2026-09-05T00:11:11Z); retro-redrive **absent** | **UNCHANGED** since 09-05T16:53Z |
| deploy-on-PR (two-sided) | only `service-deploy-lambda.yml` + `terraform-apply-reusable.yml` carry an executable `terraform apply`; **both `workflow_call` only**. Control: 7 workflows contain a real mutation (non-vacuous); 58 carry `pull_request` | **PR DEPLOYS NOTHING** |

## PT-07 VERDICT: **PASS** — the FREE set may dispatch. Every merge/deploy and H2 remain HELD.

## FINDINGS RAISED AT ENTRY (not obstacles to remove)
1. **★ M-4 IS RED. `merge-surface-sweep` against `origin/main...origin/assembly/name-the-zero` exits 1 with 3 hits.** Two-sided: self-test positive control **hits=8 (expected 8)**, negative control 0; clean-range control (`main...main`) **CLEAN, exit 0**. Hits inspected at the head:
   - `tests/test_df40_read_kind_corpus.py:80` — `_OFFICE = "+14079068111"` beside `_GUID = "ca70baa8-1111-…"`. **GENUINE:** `ca70baa8` is a REAL production office prefix (`ebi_witness_ledger.py` `_TIER_H`), and the number is real-format with a live area code.
   - `tests/test_loss_witness_floor.py:778` — `synthetic[at]example.invalid` — benign (reserved TLD).
   - `tests/test_retro_redrive_wall.py:86` — `fixture[at]example.invalid` — benign.
   **Consequence:** the merge WILL go RED at word-time unless the one genuine hit is addressed and the reserved-TLD class is allowlisted. Found today at zero cost, per P-1.
2. **★ R-65 SUPERSEDES the G-P5 clock and the kit does not carry it.** `RATIFICATION-post-close-sitting-2026-09-06.md` R-65: the premise moved TWICE (appointment ABSENT in our table at 06:50Z; appointment date PAST; receiver handler `/calendar/reviewwave` on the legacy Heroku app exists in NO repo on disk). Operator reads the receiver's handler FIRST. **Cut = 2026-09-09T18:00Z — if no handler read is receipted by then, the row RESOLVES AS LOST automatically**, then the 09-10T05:28:46Z reap runs. The operative clock is ~24 h, not ~35 h.
3. **R-72 narrows R-35 and the charge does not carry it:** *"The plan lane runs read-only; the R-35 EBI freeze forbids applies, not plans."* C-10's never-run `terraform plan` may be less blocked than Addendum L assumes. **Surfaced, not acted on.**
4. **R-67:** the cofounder snippet is the operator's act, FIRST ACT, six rulings keyed to it (R-35, R-39, R-40, R-42, R-46/R-55, R-57). **No ratification through 2026-09-08 records an ANSWER.** R-39 half (i) still open.
5. Local `autom8y` checkout is on `fix/wss-wildcard-scope-bypass-closure` @ `29e59e81` with **351 porcelain entries** — stale-tree trap ACTIVE. Every read this entry cites came from the object DB at explicit refs.

---

## PT-08 — THE CONTAINMENT GATE · 2026-09-08 · HARD (decides whether the operator is asked)
All six FREE sprints returned. Two PRs open and unmerged: **autom8y #2071** (S-14, `fix/decline-marker-class-audit`) and **#2073** (S-15, `feat/booking-client-attribution`). Nothing merged, deployed, applied, or spoken.

### Q1 — Does the predicate admit S-14 BY ITS OWN WRITTEN TERMS? **YES**, re-checked against the ACTUAL diff, which is larger than the exemplar S-13 adjudicated (3 sites cured, not 1; +613 lines).

| conjunct | verdict | own-hands basis |
|---|---|---|
| **FL-1 SURFACE** | PASS | `gh pr diff 2071 --name-only` = exactly 2 files, both under `services/email-booking-intake/` (one `src/`, one `tests/`). No terraform, tfvars, workflow, Dockerfile, manifest, IAM, allowlist. |
| **FL-2 VOCABULARY** | PASS — **and this was the close call** | `normalized_name_empty` and `initials_normalization_invalid` have **ZERO pre-existing hits at `origin/main`** (control: 40 files carry `TerminalDecline`, so the probe works). They ARE new strings. But they are **label values on an OPEN dimension**, not new symbols: `ParkKind` is a closed `StrEnum` and is untouched; `decline_class` is a free string. **CT-22's back-door trap was checked and does NOT fire** — `CONTRACT-name-the-zero-kind-vocabulary-2026-09-05.md` closes V-1 at eight outcomes (`:196`), L-1 at four loss kinds (`:596`), L-2 at three dispositions (`:636`); **`decline_class` is governed by none of them.** The idiom already appears at five sites in the same file. |
| **FL-3 DIRECTION** | PASS **with a recorded caveat** | All three cured sites today produce `FAILED`→502, and `handler.py:1157` states verbatim that records NOTHING. **Caveat:** the aggregate `PIPELINE_TOTAL{status}` distribution shifts ≈52/day from `failed` to `declined`. Each *individual* outcome that changes was previously unrecorded, so no recorded outcome changes — but the counter shape does, and a reader of that series must be told. |
| **FL-4 FLOOR** | PASS | One-commit revert, no migration, no backfill, no external state. No customer-visible outbound act — the changed byte is the status on a reply to an *inbound* webhook (S-13 ruled this inside the lane; §5(b)/R-A4 govern outbound). |

### ★ THE FACE-4 HAZARD WAS TESTED AND DOES NOT FIRE
A new `decline_class` that nothing counts would be **built-and-unconsumed — face 4 — shipped by the wave that extracted the law.** Checked: `semantic_alarms.tf:69-70` is **"Dimensioned by decline class"** generically; every class name in EBI terraform appears only in **comments** (observed histograms at `parked_suppressed_surface.tf:12-14`, `unrecovered_level_surface.tf:45-46`), never in a filter pattern. **New classes ride the existing dimension and ARE counted. No terraform is owed.**

### Q2 — Does it REFUSE H2 by the same terms? **YES, three independent ways** (S-13): wrong surface (`production.tfvars`); wrong direction (an off-allowlist office is ALREADY recorded in the dry_run keyspace, so H2 changes a recorded outcome); and the floor absolutely — `production.tfvars:154` verbatim *"the ONE policy flip that turns the 17 activated offices' live contente POST on"*, with R-A4 putting customer-visible outbound on a floor no grant phrasing lifts. Delete any one conjunct and it still refuses. **H2 is the predicate's regression test.**

### Q3 — Is G-P3 spoken, or explicitly defaulted-with-its-name-recorded? **NO. NEITHER.**
S-14 surfaced it verbatim in the PR body and did not close it. At ≈52/24 h the **first post-deploy invocation exercises the defaulted branch**. Additionally: **G-P3's own text does not exist in this repo** (S-14: `grep -rn "G-P3"` → zero, with a positive control returning unrelated hits) — this lane has been carrying the main thread's wording without attestation.

> ## PT-08 VERDICT: **PASS — AND THE OPERATOR IS ASKED.**
> The predicate admits S-14 by its own terms and refuses H2 by the same terms. The gate that blocks is **G-P3**, which is a precondition of the cure and is not this lane's to close.

### FINDINGS AT PT-08
1. **M-4 RED belongs to #1941 ONLY.** The 3-hit sweep was against `origin/main...origin/assembly/name-the-zero`. **Both wave-2 PRs sweep CLEAN** — S-15 with an independent poisoned-copy positive control (700 added lines → 1 hit), S-14 after the engine correctly fired twice on its own fixture.
2. **A PRE-EXISTING RED IS ON MAIN.** `test_ebi_level_detectors_terraform.py` ×2: `dead_letter_level_surface.tf`'s `alarm_description` renders **1001 chars against a 1000 cap** and lost its `ARMED AND DELIVERING` token. Proven pre-existing **four ways**: pristine `cc88b75e` worktree fails the same node-ids; #2071 and #2073 fail the same two with identical assertion text; the offending text is dated from the `fix(ebi): correct the SEV-1 delivery claim` lane. **Owner: that lane. Curing it here would be bundling.**
3. **The main thread's own PII instruction was WRONG.** `example.invalid` would have RED-ed the sweep — `person[at]corp.invalid` is the engine's own positive-control fixture (`merge-surface-sweep.sh:90`) and the exclusion covers only bare `example.com|org|net` and `localhost`. Both build seats probed empirically instead of trusting the charge.
4. **S-14 caught a real defect in its own suite:** mutant M6 SURVIVED first run because its fixture raised on the AI's *first* call, so both parametrize rows hit one line and `extract_fields.py:406` was never reached — a passing parametrize blind to half the transient class. Rebuilt with a call-indexed double and per-row positive controls; M6 then died. **12/12 killed.**
5. **Leg-1 denominator delta, unreconciled and reported as such:** LLM-transient 24 matches exactly; `missing_contact_name` 52 vs 53; **parse-class 30 vs 10 — UNRECONCILED.** The AFTER figure (41.6% → 21.2%) is a **PROJECTION**, never a measurement — nothing is deployed.

---

## PT-09 — MERGE RECEIPT: the calendar-integration-locus session responsibilities LANDED

**Instant:** 2026-09-09T02:04:47Z · **PR:** autom8y-asana #416 · **squash-merge commit:** `20eef5e8`
**Branch:** `docs/calendar-integration-locus-interop` (deleted on merge) · **pre-merge head:** `558dd510`

### What landed (exactly two files, re-verified on the final head)
| file | lines | what it is |
|---|---|---|
| `.ledge/decisions/INTEROP-calendar-reviewwave-external-boundary-2026-09-08.md` | 124 | The external `/calendar/reviewwave` boundary record. Externally owned (Legacy NHC, cofounder-associated); operator-ratified on four points. |
| `.ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md` | 56 | C-1..C-18, the §2 defer register (incl. ★ G-FL1 recorded as my own omission), §3 the substrate lane's refutation, §4 six unconfirmed assumptions carried forward UNRESOLVED. |

### CI verdict — settled, not inferred
All 28 checks `COMPLETED`. 0 failing, 0 running, `mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`.
Three `SKIPPED` (Integration Tests, Convention Check, `[code]smith`) are conditional jobs, not failures.
**The gate was stated in advance and honoured:** merge on a real verdict — not on `UNSTABLE`, not on "not failing."

### ★ DEPLOY-INERTNESS — VERIFIED IN FACT, TWO-SIDED (not asserted from the deny-list text)
The claim before the merge was: `.ledge/**` sits in `paths-ignore` on `test.yml`'s `push:` trigger, so the
merge cannot reach `Test → Satellite Dispatch → asana ECS roll`. After the merge, measured:

| leg | observation |
|---|---|
| **Negative** | `gh run list --branch main` on `20eef5e8` shows exactly three runs: `Post-Merge Coverage`, `Push on main` (dynamic), `Secrets Scan (Gitleaks)`. **`Test` DID NOT FIRE.** |
| **Unreachability** | `satellite-dispatch.yml:6-9` gates `workflow_run` on `workflows: ["Test"]`, `branches: [main]`. No Test run ⇒ no `workflow_run` ⇒ no dispatch. Its only other doors are `repository_dispatch{sdk-published}` and manual. |
| **★ Positive control** | In the SAME run list, on `389c59bc`: `Test` fired (17:37:50Z, workflow_dispatch) and `Satellite Dispatch` followed via `workflow_run` at 17:45:03Z. **The absence is the guard biting, not a blind query.** |
| **The one AWS role** | `post-merge-coverage.yml:54-67` assumes `role/github-actions-deploy` — the role NAME contains "deploy", but the step's sole use is `aws codeartifact get-authorization-token` for `uv sync`. Read, not assumed. No deploy. |

This closes the untaken-zero fence for this act: a zero was reported only after a control proved the query
could return non-zero.

### OPEN AT PT-09 (carried, not closed by this merge)
- **`Post-Merge Coverage` on `20eef5e8` is IN FLIGHT.** It enforces `pyproject.toml:127 fail_under = 80` on the
  full single-shard suite — the floor the sharded PR job explicitly disables (`coverage_threshold: 0`). A docs-only
  merge should not move coverage, but the gate has not returned and **is not claimed green.** Watch is live.
- **The pre-existing main RED** (finding 2 above, `test_ebi_level_detectors_terraform.py` ×2) is still on main and
  still owned by the `fix(ebi): correct the SEV-1 delivery claim` lane. This merge neither cured nor worsened it.
- **The outbound-deck query on the six dark offices was NOT taken.** The diagnosis that authored it reserved it to
  the operator or the sre lane and stopped. A standing general authority grant is not a reason to cross a boundary
  a prior seat drew deliberately. It remains the operator's.

---

## PT-09b — THREE POST-MERGE FINDINGS

### F-1 ★ THE TWO REFUSALS ARE INDEPENDENT AND MUST NOT BE MERGED
The `identity-activity-substrate` lane corrected its own framing, unprompted, after it had already
propagated. The version in circulation quoted `autom8y-data config.py` truncated at an ellipsis:
*"FALSE by default: the roster is an un-ruled population…"*. The full text is a **conjunction plus an
operator clause**: *"…un-ruled population **AND the ledger is append-only. Enabling is a separate
operator lever.**"*

| lane | ground for declining to invent the predicate |
|---|---|
| `name-the-client` (PT-02) | The predicate is **UNFALSIFIABLE** — no artifact holds the set, its cardinality, or its generator. |
| `identity-activity-substrate` | A wrong answer would be **IRREVERSIBLE** — an append-only ledger cannot un-write a wrong population. And enabling is a **wall act**, not an engineering call. |

**Same action, independent cost functions.** Two lanes converging on one refusal is strong evidence
*only while the reasons stay disjoint*; a sentence that merges them turns two observations into one
counted twice. Recorded separately here, deliberately.

**Where it is currently merged:** `.ledge/decisions/ADR-ws-denom-seam-2026-09-09.md` §0a (UNTRACKED
draft, catchable) reproduces the ellipsis verbatim and then pull-quotes *"same wall, same refusal…
It is unfalsifiable because the population has never been ruled"* — attributing the substrate lane's
ground to the unfalsifiability finding. **Not my artifact; not edited by me.** Routed to the substrate
lane to correct at its source rather than through a third hop, since hop-loss is how the truncation
entered. Open sub-item: the ADR anchors `config.py:203-205`, the substrate lane `:204-206` — **the
blob discriminator has NOT been applied** (no `autom8y-data` checkout in this seat); unresolved, not guessed.

### F-2 THE INTEROP RECORD IS LANDED BUT NOT DISCOVERABLE — face 4 at the record layer
Measured on the merged tree: `grep -ril "reviewwave\|review_wave" .know/` → **ZERO hits.**
Positive control on the same corpus: `grep -ril "unit_holder" .know/` → **5 files**, so the probe works.

The repo CLAUDE.md tells every agent to read `.know/architecture.md` *before code changes*. The boundary
record now lives in `.ledge/decisions/` — correct, merged, and **invisible to the layer agents actually
read**. That is precisely face 4: a correct, written, unread record causing independent re-derivation —
the failure this arc extracted and then reproduced on its own output within the hour.

**NOT CURED TONIGHT, and the reason is F-3.** Recommendation only: a one-line pointer from
`.know/architecture.md` (and/or `.know/feat/intake-pipeline.md`, which already carries `unit_holder`)
to the INTEROP record. Deploy-inert — `.know/**.md` sits in the same `paths-ignore` deny-list proven
in PT-09. Operator's call whether it is in this session's scope; I did not widen into it unilaterally.

### F-3 ★ THIS WORKING TREE IS SHARED, AND I MOVED A BRANCH THAT IS NOT MINE
`/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana` is checked out on **`sre/ws-smoke-activation-hook`**,
not `main` — despite session-start context reporting `main`. My `git pull --ff-only origin main`
fast-forwarded that branch `389c59bc → 20eef5e8`.

**Assessed benign, on evidence, not on assumption:** the branch is local-only (`git ls-remote --heads
origin` → empty), tracks `origin/main`, and its entire reflog is two entries — *"Created from
origin/main"* then my fast-forward. It held **zero commits of its own**, and `--ff-only` refuses rather
than discards. Nothing was lost.

**But the standing lesson applies:** I acted on an assumed branch identity instead of a measured one,
in a tree that `git worktree list` shows is one of ~20 sharing this repo, with several sibling sessions
`busy`. **No further mutation of this tree tonight** — which is why F-2 is a recommendation and not a PR.
