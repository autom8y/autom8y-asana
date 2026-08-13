---
type: handoff
status: draft  # .ledge lifecycle enum; fires when pasted into the fresh session
handoff_type: execution
artifact_id: IGNITION-option4-build-wave-2026-08-12
initiative: option4-verification-axis-gate — build wave 1
source_rite: 10x-dev (this seam)
target_rite: 10x-dev (fresh session, pre-seeded pantheon)
created_at: "2026-08-12T12:20:00Z"
purpose: >-
  Paste-grade ignition kit for a FRESH CC session to fire the build wave.
  Everything below the PASTE-BLOCK marker is the operator's copy&paste snippet.
  Nothing herein re-decides anything: all authority derives from the three
  ruling records referenced inline.
---

# IGNITION — option4-verification-axis-gate build wave 1

## Pre-flight (run in the terminal BEFORE pasting, ~30s)

```bash
cd ~/Code/a8/a8/repos/autom8y-asana
ari sync                                  # sync knossos state across the tree
ari rite current && ari rite pantheon     # EXPECT: 10x-dev native (potnia, requirements-analyst,
                                          # architect, principal-engineer, qa-adversary) + borrows:
                                          # sre, hygiene, arch, eunomia (~97% context budget)
```

Seeding is ALREADY DONE (invocations inv-20260812-{878871162ac5, 0a493338c616,
d4ff5c75c315, bf1d2896684a}). ⚠ Budget is at 97% of the 50k ceiling — do NOT
invoke additional rites. ONLY if a borrow is missing, re-seed the minimal set:

```bash
ari rite invoke eunomia --agents=verification-auditor          # K-0a census · soak attester (rite-disjoint)
ari rite invoke sre --agents=observability-engineer,platform-engineer  # deadman apply · re-baseline
# optional, budget permitting:
ari rite invoke hygiene --agents=audit-lead,janitor
ari rite invoke arch --agents=arch-adversary
```

---

## PASTE-BLOCK (copy everything below into the fresh session as message 1)

/sos start "option4-verification-axis-gate — SPRINT 1 of 3+2 (gate-open): census → contract promotion + §1.2 amendment → operator gate"

CRUSADE INGEST — pre-adjudicated; execute, do not re-litigate. This kit is
REVISION 2: adversarially corrected by pythia (C-1..C-16) and potnia (D1..D19,
SPLIT verdict) — their reports ride below the END marker; the DAG here is the
reconciled form. Orchestration: @"potnia (agent)" coordinates; @"pythia (agent)"
adjudicates dynamic forks (pre-flight verifies the seat resolves; if it does
not: design forks → architect, routing forks → potnia, operator-ruled forks →
ESCALATE). Fire /sprint ONCE, after /sos start, scoped to SPRINT 1 ONLY.

CHARTER (read in order; these ARE the decision space):
@.ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md   ← ratified-provisional; §7 IS the authoritative DAG (cite ONLY by full artifact_id — the bare number ADR-007 is triple-booked, its §8 O-9)
@.ledge/decisions/RULING-operator-adr007-ratification-2026-08-12.md  ← R-i..R-O8
@.ledge/decisions/RULING-operator-option4-interview-2026-08-12.md    ← P-1..P-12
@.ledge/decisions/RULING-operator-wave-close-realized-mechanism-2026-08-12.md
@.sos/wip/DESIGN-option4-verification-axis-annex-2026-08-12.md   ← its min()-denominator was SUPERSEDED by P-5; ADR §2 carries the corrected grain
@.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md + @.sos/wip/EVIDENCE-age-at-tick-v-sizing-2026-08-12.md
@.sos/wip/STAGE1-observability-truth-2026-08-12.md   ← ⚠ read to the END: its early "nothing applied" lines are SUPERSEDED by the APPLY RECEIPT section (AL-5 applied-to-AWS 11:41Z, verified 11:42:23Z)
@.sos/wip/DETERMINATION-w2-deadmen-al5-2026-08-12.md   ← ⚠ two stale premises inside: "#339 has NOT merged" and "re-baseline ≥7 days" are BOTH superseded (merged 10:24:31Z; ECS :762 complete 11:04:18Z; re-baseline ≥48h)
@.sos/wip/CARD-stray-publish-metric-contamination-2026-08-12.md
@.sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md   ← the amendment target — NOTE it is GITIGNORED at this path (see G2)
@.know/scar-tissue.md

REPO GROUND TRUTHS (absolute, per the miscut scar — use `git -C` everywhere):
- Producer: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana (HEAD ~4129ae7e; SQUASH merges, 6/6 single-parent)
- Monorepo: /Users/tomtenuta/Code/a8/a8/repos/autom8y — autom8y-core (sdks/python/autom8y-core) and ASR (services/account-status-recon, tf at terraform/services/account-status-recon/) live INSIDE it, not as siblings; merge-commit convention (#1516/#1539 two-parent)
- ⚠ The monorepo working tree sits on fix/wss-wildcard-scope-bypass-closure — NOT an ancestor of origin/main; combine_offer_axis, asana_freshness, core 4.14.0 and the QueryMeta axis fields DO NOT EXIST there. PIN origin/main (fresh fetch) for every monorepo read, build, or branch-cut, or you will "falsify" landed work (ADR §8 O-11).
- ⚠ terraform/services/asana: the AL-5 change is APPLIED TO AWS (receipted: describe-alarms 2026-08-12T11:42:23Z — period 3600, 3-of-4, missing, ok_actions=[]) but UNCOMMITTED in git. Until G2's PR commits it, any plan there shows REVERSE-DRIFT that must NOT be "corrected" by apply. Never bare `terraform apply` in that dir (untracked warmer_cache_degraded_alarm.tf + PROV state drift; always -target + BOTH -vars: ticket_sns_topic_arn, require_alarm_binding — omitting them REMOVES SNS routing).
- Monorepo success_deadman.tf + runbook edits are AUTHORED-NOT-APPLIED, uncommitted, sitting in the non-main tree — P-a's charge; do not lose them when pinning origin/main (worktree for P-a).

SPRINT 1 — GATE-OPEN (this session's /sprint scope):
G0  Telos declaration — author .know/telos/option4-verification-axis-gate.md:
    verification_method telemetry; deadline = soak close; rite-disjoint
    attester = eunomia verification-auditor. (The initiative spans sessions;
    the verified-realized event needs an inscribed attester before work starts.)
G1  K-0a census — eunomia verification-auditor, READ-ONLY. THE INSTRUMENT IS
    ONE S3 GET of the offer manifest + a jq reduction (ADR §7.2 — NOT an Asana
    API call). PASS needs ALL THREE criteria: (1) every name in
    OFFER_CLASSIFIER.sections_for(ACTIVE, ACTIVATING) — all 27, row-bearing and
    zero-row alike — resolves to a manifest section; (2) every one carries a
    non-null last_verified_at; (3) now − oldest_stamp is HOURS, not days.
    Same GET also answers B3-b (SectionInfo.name population — unblocks P-c).
    THREE EXIT ARMS: PASS → G2 · criterion-1 miss → OPERATOR (R-O8, theirs
    alone) · criterion-2/3 miss → producer-defect back-route as a P-5 REDESIGN
    item ("a successful detection and a blocker — a producer defect, not an
    Option-4 cost"), explicitly NOT a kill-switch (see fences).
G2  Contract promotion + §1.2 amendment — ARCHITECT seat, ONE PR on the
    producer repo: (a) PROMOTE the frozen contract from .sos/wip/ (gitignored —
    there is no tracked file to amend at its current path) to .ledge/specs/
    (tracked, allow-listed), byte-identical, fence md5 re-checked before and
    after; (b) apply the §1.2 amendment IN THE SAME PR — the ratified text from
    the ADR §3 block with R-i's modification (VERIFICATION GRAIN = ADVISORY;
    MONOTONICITY + non-aliasing extension as written), in-place,
    struck-and-standing; (c) the ADR-006 status-line edit rides ("executes at
    ratification", not yet done); (d) commit the applied-but-uncommitted AL-5
    terraform in this same PR so git re-converges with AWS. Update the ADR
    frontmatter amends: pointer and this kit's charter line.
G3  OPERATOR GATE (halt here; do not proceed into Sprint 2 without it):
    (1) the R-O8 ruling on G1's result; (2) the ONE-WAY DOOR acknowledgment —
    public RowsMeta/AggregateMeta field additions are irreversible and were
    NOT among the seven ratification rulings (binding note forbids assuming
    them); (3) schedule the soak-protocol ratification (the soak design is
    explicitly unratified — ratification record, Assumptions #1).
EXIT: K-0a PASS + amendment PR landed + all three operator items held.

ROADMAP (do NOT execute in Sprint 1; each gets its own ignition):
SPRINT 2 — PRODUCER (asana), all DARK: S1-rescoped = regression guard on the
  ALREADY-CLOSED FIX-1 zero-row path (verified live at progressive.py — do NOT
  re-cure it; do NOT weaken its coherence premise rows==0 AND gid_hash==hash(∅),
  which re-opens DEFECT-delta-path-empty-poison; qa-adversary two-sided teeth
  as the §7.6-criterion-3 fixture) + K-1 = the two ACTUALLY-open holes
  (mark_section_failed drops name AND last_verified_at, its sibling carries
  both; fetched-but-never-probed) + P-6 source-close + §1.4-pure build-time
  capture + G-1 monotone envelope AT THE PRODUCER (not the consumer — "absorbed
  at the producer rather than propagated") + G-3 VerificationSource provenance
  enum + CAP-SIG roster 12→15 + BOTH meta models (extra="forbid" coupling: a
  field on one and not the other RAISES). R-O3: the ARCHITECT (named seat, not
  the builder) decides the backfill-flag spelling at this PR — ADR §8 O-3
  recommends verification_backfill_used — inscribed in the PR body AND the
  naming fence amended in the SAME PR. Seats: principal-engineer builds,
  architect on R-O3 + design holds, qa-adversary teeth.
  EXIT = OBSERVED ON THE WIRE (a live consumer log line carrying the new
  fields) — a merge is NOT a discharge; this emission chain has silently
  killed fields twice before.
SPRINT 3 — FLEET (monorepo, origin/main pinned, worktrees): K-2 SDK surface
  (gated on K-1-observed; key-absence ≠ key-null; capability-tolerant
  dormancy; NO-COALESCE; #1516-guarded forced order SDK-merge → publish →
  consumer-merge) → S5a = K-3 dark carry → S5b = K-4 ALONE (the single
  behaviour-changing merge — "Never bundle K-4 with anything"; gated on one
  observed tick showing the number; V=14,400/28,800 PROVISIONAL per R-ii;
  per-constituent disclosure so clean-GATE is never forensically silent
  again) → S5c = K-5 content-age demotion + §2.7 anomaly rules → S5d =
  qa-adversary station discharging §7.6 criteria 1–6.
  ⚠ At gate-live (K-4): route D-5b + F-GUARD back to the OPERATOR (P-10's
  revisit trigger fires; new sub-question: does the verification axis need its
  own future-skew allowance — min() does not shield it).
SITTING A — SOAK-ARM: preconditions = P-a APPLIED (P-4: "a soak measured
  against alarms that lie is not a soak") + P-b's attribution dimension landed
  + the soak protocol RATIFIED (grid, healthy-tick definition, contamination
  fences — qa-adversary authors, operator ratifies).
SITTING B — SOAK-CLOSE at T+14d: own ignition kit; clock on the MAIN thread;
  R-ii auto-disposes provisional V; S7 operator handoff.

PARALLEL TRACKS (potnia-corrected dispositions):
P-a monorepo deadman apply (FILL fix + ~18h latency-truth): OWN WORKTREE off
    origin/main; terraform init is the FIRST state-touch there — plan shown
    before apply; carry the ok_actions-drop ruling. PRECEDES Sprint-3 branch
    cuts (tree contention) and is a HARD PRECONDITION of Sitting A — parallel
    to Sprints 1-2 only. platform-engineer.
P-b DEFECT-1 (ETag-less manifest RMW) + DEFECT-2 (backward jump) root causes —
    parallel per P-11; the ECS task-id log dimension lands BEFORE Sitting A so
    a soak miss is attributable. Include ADR §8 O-13: the source-coverage
    deadman UV-P is "the single cheapest falsifier", still unrun.
P-c CLI leg (R-O4 delegated) — blocked on B3-b, which G1's single S3 GET
    answers; start only after Sprint 1.
P-d stray-publish emitter gate per the CARD — truly free, any monorepo seat.
P-e AL-5 re-baseline — SINGLE-SHOT at ≥2026-08-14T11:04Z (48h from ECS
    rollout-complete, NOT from merge). Prediction referent: the post-#339
    created_at regime (NOT Sprint-2's verification stamps — do not conflate).
    Sample must be deploy-free or every producer-deploy timestamp recorded as
    a regime boundary — asana auto-deploys ~13-30min post-merge, so Sprint-2
    merges inside the window contaminate it (the V1-writer-changed-mid-window
    scar). observability-engineer.

OPERATOR-RULED FENCES (violating any = halt + escalate, never argue):
★ Kill-switches (P-9): (1) a verified-complete-and-recent snapshot produces a
  materially wrong published verdict traceable to data age; (2) verification
  errs FRESH against demonstrable Asana truth; (3) the soak misses the bar.
  Observe one → HALT + escalate.
★ CARVE-OUT, verbatim (ADR §6.0): "A seat that observes eligibility failure
  must NOT treat it as KS-1/2/3, must NOT halt the initiative, and must route
  it to the operator as a P-5 redesign item." Eligibility failure is the most
  likely failure point in this DAG — it is a redesign trigger, NOT a kill.
★ R-alt: denominator changes escalate-only-at-the-wall — attempt
  all-classified first; only demonstrated impossibility WITH RECEIPTS returns.
★ Interim posture (P-3): ASR offers ticks abort honestly until K-4 lands —
  EXPECTED, not defects; do not "fix" them.
★ Naming fence (P-12) + R-O3 architect-inscription duty.
★ Operator-personal, never delegable: R-O8 at G3 · the one-way door ·
  soak-protocol ratification · D-5b + F-GUARD at gate-live · any P-x
  amendment · kill-switch disposition · the wall.

SCARS (all receipted this arc):
- `git -C <abs-path>` everywhere (worktree miscut ×2 relying on cwd).
- UTC only via `date -u`; epoch math in aws logs windows.
- Match each repo's merge convention (asana SQUASH; monorepo merge-commit);
  verify by parent-count, never assume.
- Strict branch protection + HOT main (parallel operator sessions land
  mid-wave): `gh pr update-branch` → `gh pr merge --squash --auto` → watcher;
  expect BEHIND re-staling; just re-update.
- Subagent self-park is UNRELIABLE — keep every clock on the MAIN thread
  (background waker → SendMessage resume); "I'll wake at T" from a subagent
  means the work will not happen.
- moirai autopark: `ari session resume -s <id>`; lock→mutate→unlock atomically.
- Commit hooks ban AI co-author trailers + hyphenated commit scopes.
- .sos/wip frontmatter hook: type ∈ {audit,triage,qa,spec,scratch,design}.
- asana satellite auto-deploys ~13-30min post-merge; ECS rollouts carry long
  warm grace — converge before dependent merges (SPACE-THEM).
- Artifacts can carry stale premises that later sections supersede — read
  receipts to the END before acting on an early claim (this kit's own review
  cycle caught two instances).

GRANT: comprehensive user-grade permission to the pantheon and borrowed seats
on my behalf, all repos on the filesystem (above, below, or across the tree),
for everything short of strict impossibilities — BOUNDED BY the operator
rulings above, which this grant does NOT override.

## END PASTE-BLOCK

---

## REVISION 2 NOTE (2026-08-12 ~13:00Z, main seam)

The PASTE-BLOCK above is REVISION 2 — rewritten to absorb pythia's C-1..C-16
(below) and potnia's D-1..D-19 + SPLIT verdict (session record). One
correction-of-a-correction, receipted: pythia's C-5 ("AL-5 is NOT applied")
is FALSE in direction — the apply EXECUTED at 11:41Z under the operator's
word and was verified live (describe-alarms 11:42:23Z: period 3600, 3-of-4,
missing, ok_actions=[]); pythia read STAGE1's pre-apply lines and the dirty
tree. The TRUE hazard is the inverse: applied-to-AWS but uncommitted-in-git
→ reverse-drift on the next plan. G2(d) carries the fix. C-5's untracked-file
and ok_actions-ruling riders were correct and are absorbed.

## ADDENDUM — adversarial pre-carry adjudication (pythia, 2026-08-12T12:40:24Z)

**VERDICT: CARRY-WITH-CORRECTIONS.** Charter refs all resolve (12/12); pre-flight
matches live state exactly; the four probed ruling-citation axes are FAITHFUL.
But **S0 and S1 — the first two DAG nodes — both mis-execute as written.** The
cold-session test ("could a fresh session execute S0 correctly from the kit
alone?") **FAILS** on C-6. Apply C-1..C-6 before pasting; C-7..C-15 are
carry-along corrections.

Adjudicated against: producer HEAD `4129ae7e`; monorepo `autom8y` @ `4ffeb1cb`.

### What was falsified and held

| Probe | Result |
|---|---|
| (1) @ refs resolve | **PASS** — 12/12 resolve |
| (2) pre-flight vs live | **PASS** — `10x-dev` + sre/hygiene/arch/eunomia, 97.0% of 50k, all four inv-ids match |
| (3) ruling-citation fidelity | **PASS** on grain-ADVISORY/P-5-operative (R-i), V-PROVISIONAL auto-disposition (R-ii), R-alt wall, P-3, P-12. **FAIL** on P-9 (C-2) and R-O3 delegate (C-10) |
| (4) S1 hard-precondition load-bearing | **PASS as a precondition** (ADR §2.3(c) L266-280: 6.7-day window → 0/37 PASS) — but **the stage that discharges it is mis-specified** (C-1) |
| (5) cold-session executability | **FAIL** — C-4, C-6, C-3 |
| (6) scars | **PASS** on all verified — squash (6/6 single-parent), monorepo #1516/#1539 (both 2-parent), terraform drift. One material omission (C-3) |

### BLOCKING-CLASS corrections

**C-1 — S1 (kit L73-76) orders work that is ALREADY CLOSED at HEAD.**
S1 reads "zero-row classified sections become stampable (verified-empty is
verified)". That hole is **CLOSED**: ADR §2.3 L287 (FIX-1, `5d62d0b8`/PR #299),
verified live at `src/autom8_asana/dataframes/builders/progressive.py` L561-566
(`stamp_info.rows == 0 and stamp_info.gid_hash == _EMPTY_GID_HASH` falls through
to `stamp_info.last_verified_at = now`). The **actually-open** residue is two
different holes, ADR §2.3 L288-289:
- `mark_section_failed` rebuilds `SectionInfo` carrying neither `name` nor
  `last_verified_at` — verified OPEN at `section_persistence.py` L218-228
  (sibling `mark_section_complete` L208-215 carries both forward);
- a section fetched-but-never-probed has no stamp at all.
Both are assigned by ADR §7.3 L1180 to **K-1** (producer capture + P-6
source-close) = the kit's **S2**, not to a separate stage. **There is no "B-1"
stage in the ADR.** Correction: re-scope S1 to a **regression guard** on the
already-closed FIX-1 path (the qa-adversary two-sided teeth as written are
correct and worth keeping — per §2.3 L300 the scenario is now "a regression the
gate must be protected against rather than cured by this initiative"), and move
the two open holes into S2 under P-6 source-close.

**C-2 — the kill-switch fence (kit L123-126) omits the explicitly-NOT-registered
fourth case.** Interview P-9 (L27) and ADR §6.0 L994-1009 rule: *"'Eligibility
unfixable' was explicitly NOT registered — operator treats it as a redesign
trigger for P-5, not a pillar kill."* ADR L1006-1009 verbatim: **"A seat that
observes eligibility failure must NOT treat it as KS-1/2/3, must NOT halt the
initiative, and must route it to the operator as a P-5 redesign item."** As
written the kit's fence says "Observe one → HALT" with no carve-out, and
eligibility failure is the single most likely failure point in the DAG (it is
the ★hard precondition). Add the carve-out verbatim to the fence block.

**C-3 — the monorepo working tree is on a NON-MAIN branch, and the ADR records
this as a re-checking HAZARD the kit drops.** ADR §8 **O-11** L1291: the
`autom8y` tree sits on `fix/wss-wildcard-scope-bypass-closure`, **not an
ancestor of `origin/main`**; against it `combine_offer_axis`, `asana_freshness`,
`autom8y-core 4.14.0` and the `QueryMeta` axis fields **do not exist**. ADR: *"Any
seat verifying this ADR must pin `origin/main`; a local checkout will produce
false negatives that read like a falsification of the K lane."* Verified live
2026-08-12T12:40Z: still on `fix/wss-wildcard-scope-bypass-closure` @ `4ffeb1cb`
(drifted +3 commits from the ADR's `1bb00c3c`). S4, S5, P-a and P-d all land
monorepo-side. **Add to the fence block: pin `origin/main` before any monorepo
read, build or branch-cut.**

**C-4 — no absolute paths for the monorepo or ASR, against the kit's own scar.**
Kit L92/L95 say only "(monorepo, autom8y-core)" and "(monorepo, ASR)". The kit's
first scar (L137-138) demands explicit `git -C <abs-path>` because "a seat
miscut worktrees into the wrong repo TWICE relying on cwd" — yet the kit never
states the path. Resolved: monorepo = **`/Users/tomtenuta/Code/a8/a8/repos/autom8y`**;
`autom8y-core` and ASR are **packages/services inside it**, not sibling repos;
ASR terraform = `terraform/services/account-status-recon/`. Producer =
`/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana`. Inscribe all three.

**C-5 — the STAGE1 gloss (kit L61) is FALSE. AL-5 is NOT applied.**
Kit L61: "what is ALREADY APPLIED (AL-5) vs AUTHORED-NOT-APPLIED (monorepo
deadman)". STAGE1 L30 states verbatim: **"Four authorized items, all executed.
Nothing applied. Nothing committed."** L39/L40 both list disposition "operator
apply"; L49 marks `terraform/services/asana/observability_alarms.tf`
**"MODIFIED, uncommitted, unapplied."** Verified live: ` M terraform/services/asana/observability_alarms.tf`.
A cold session reading the kit's gloss will **skip the asana-side apply
entirely**. Two riders: (a) the change is **uncommitted working-tree state** on a
HOT main with parallel operator sessions — commit or stash-protect it before
anything else touches the tree; (b) there is an **untracked**
`terraform/services/asana/warmer_cache_degraded_alarm.tf` in the same directory
(STAGE1 L58: pre-existing, dated 23 Jul) which will be picked up by any
untargeted plan — this compounds the kit's own "NEVER bare terraform apply"
scar (L151-154). Also unlisted: STAGE1 L465 records an **`ok_actions` DROP as a
NEW operator ruling from that sitting** — carry it into P-a.

**C-6 — S0's K-0a instrument is WRONG, and two of three criteria are dropped.**
Kit L69-70 orders "do all 27 classified section names resolve **in Asana**
today". The measurement is **not** an Asana API call: ADR §7.2 L1158 *"Both
questions are answered by reading **one** S3 object"*; L1166-1167 *"one S3 GET
of the offer manifest plus a `jq` reduction"*. Criterion 1 is *resolves to a
**manifest** section* (L1145-1146). A cold session will reach for the Asana API —
wrong instrument, wrong answer. Further, K-0a PASS requires **three** criteria
(L1144-1149), of which the kit carries only one:
1. every name in `OFFER_CLASSIFIER.sections_for(ACTIVE, ACTIVATING)` — all 27,
   **row-bearing and zero-row alike** — resolves to a manifest section;
2. every one carries a **non-null `last_verified_at`**;
3. `now − oldest_stamp` over the full set is **hours, not days**.
Plus ADR L1151-1155: a days/weeks-old oldest stamp is **"a successful detection
and a blocker — route it as a producer defect, not as an Option-4 cost."**
Replace S0's criterion text wholesale with the above.

### STRUCTURAL corrections

**C-7 — K-0b identifier collision.** Kit L71-72 defines K-0b as the
`last_verified_at` population census. ADR §7.2 L1135 defines **K-0b = "This ADR
ratified (§3 amendment text + §4 V)", owner: operator** — already discharged by
the RATIFICATION RECORD. The kit's "K-0b" content is actually **K-0a criterion 2**
(L1147); the *name*-population question is **B3-b** (L1157), which blocks the
metrics CLI leg only (kit's P-c), not the lane. Renumber to avoid a cold session
cross-referencing §7.2 and reading a different gate. Note also K-0c (L1136, the
§3 amendment PR) = kit's S3, and it **blocks K-1 onward** — the kit's DAG places
S3 *after* S2, but ADR gates K-1 on K-0c. Reconcile the order or state the
divergence.

**C-8 — S5 bundles K-4 with K-5, violating an explicit ADR fence.** ADR §7.3
L1186: **"Never bundle K-4 with anything."** L1174-1176: K-1..K-3 are all DARK;
K-4 is the *single* behaviour-changing merge ("if the gate misbehaves, exactly
one merge is a candidate"); K-5 (content age demoted to disclosure + §2.7 anomaly
rules) is gated **on** K-4. Kit S5 (L95-101) merges the verification conjunct AND
the content-age demotion into one stage. Split S5 into S5a (=K-4, one predicate,
gated on one observed tick showing the number) and S5b (=K-5). Carry the DARK
property onto S2/S4 as well.

**C-9 — P-10 (D-5b) and O-2 (F-GUARD) are omitted, and S5 fires their trigger.**
Interview P-10 (L28) is a **HOLD, revisit trigger = gate-live**; ADR §8 O-1
L1268 and O-2 L1269 carry it, with a newly-surfaced sub-question (whether the
verification axis needs its own future-skew allowance — *"`min()` does not shield
it"*). S5/K-4 **is** gate-live. Add to the operator-personal fence: on gate-live,
route D-5b + F-GUARD back to the operator.

**C-10 — R-O3's delegate is the ARCHITECT, specifically.** Ratification R-O3
(L22): *"The **architect** decides at the producer-leg PR."* Kit L84-86 says only
"DECIDED AT THIS PR" and S2 names no agent (S1 names principal-engineer +
qa-adversary). A cold session will let the builder pick. Name the architect. Also
carry ADR §8 **O-3** (L1284), which **RECOMMENDS `verification_backfill_used`**
(prefix-consistency makes the §3 NON-ALIASING near-miss list enforceable; a bare
`backfill_used` collides with any future non-verification backfill flag).

### MINOR corrections

- **C-11** — S2/S4 omit **G-3 provenance enum** and **CAP-SIG** (§3.1 roster,
  twelve→fifteen names). ADR L1194: CAP-SIG *"is what makes this true and is
  therefore not optional."*
- **C-12** — ADR §5 L922-925: ADR-006's status line edit **"executes at
  ratification"** and is not yet done. Unlisted landing duty; attach to S3.
- **C-13** — ADR §8 **O-9** L1288: the bare number `ADR-007` is **triple-booked**
  (`ADR-007-cw-namespace-tri-partition`, `ADR-007-verify-denominator-congruence`).
  Kit L87 cites "ADR-007 §3" bare. Cite only by full `artifact_id`.
- **C-14** — P-e (kit L118-120) is **CORRECT and receipted** (ADR O-7a L1277:
  #339 merged `2026-08-12T10:24:13Z`, ECS `:762` `rolloutState COMPLETED`
  `2026-08-12T11:04:18Z`) — but note the 48h runs from **rollout-complete
  (11:04Z)**, not from merge (10:24Z), and that
  `DETERMINATION-w2-deadmen-al5` L471 ("#339 has NOT merged") and L501
  ("re-baseline **≥7 days**") are **both superseded** by O-7a. The kit sends the
  cold session to that artifact (L62); flag the supersession inline or it will
  read a stale premise and a contradictory gate.
- **C-15** — carry ADR §8 **O-13** L1300 (the `source-coverage-3of3-deadman`
  UV-P, *"the single cheapest falsifier"*, carried forward **unrun**) and **O-8**
  L1286 (recommend a distinct disclosure counter naming *which* classified
  section is unresolvable, so the abort is diagnosable in one log line).
- **C-16** — the re-seed block (L33-39) uses `--agents=` **subsets**, but the
  live borrows are **full rites** (sre 4, hygiene 4, arch 5, eunomia 6). Re-seeding
  from that block yields a *different, smaller* pantheon than the 97% figure
  describes. It is a fallback only; do not run it if `ari rite current` already
  shows the four borrows.

### Held as accurate (do not "fix")

Grain ADVISORY / P-5 OPERATIVE split (R-i) · R-alt escalate-only-at-the-wall ·
V PROVISIONAL with soak auto-disposition, no sitting (R-ii) · P-3 interim
aborts-are-expected · P-12 naming fence · the annex's `min()`-denominator
supersession note (annex L517 reduces over `served_sections`; P-5 requires
all-classified — the kit's caveat at L59 is correct) · CONTRACT §1.2/§1.4/§1.8
anchors (L150/L262/L527) · squash-vs-merge-commit scar (asana 6/6 single-parent;
monorepo #1516 `d60a6c5b5` and #1539 `c21cab9d8` both two-parent) · the
S1-as-precondition claim itself (ADR §2.3(c) L266-280).

*— pythia, ecosystem navigator. Adjudication only; no ruling minted, no gate
closed. R-O8, P-10, kill-switch disposition and the wall remain operator-personal.*
