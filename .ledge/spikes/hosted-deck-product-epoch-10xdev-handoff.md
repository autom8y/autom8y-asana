---
artifact_id: HANDOFF-10x-dev-to-ui-2026-09-05
schema_version: "1.0"
type: handoff
source_rite: 10x-dev
target_rite: ui
handoff_type: assessment
priority: high
blocking: false
initiative: hosted-deck-product-epoch
created_at: "2026-09-05T08:36:00Z"
status: pending              # cross-rite-handoff schema enum (pending|in_progress|completed|rejected)
lifecycle_status: proposed   # .ledge lifecycle vocabulary (advisory hook); distinct key, no collision — H1 precedent
session_id: session-20260905-014608-787b7977
sprint_id: S5
source_artifacts:
  - "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/hosted-deck-product-epoch-DP-2-publisher-envelope.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/decisions/hosted-deck-product-epoch-ledger-consequence.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.know/telos/hosted-deck-product-epoch.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/hosted-deck-product-epoch-eunomia-handoff.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ws-guard-fence-invariants-enumeration-2026-09-05.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ws-guard-fence-baseline-2026-09-05.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ws-guard-fence-baseline-VERDICT-2026-09-05.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ARCH-CRITIQUE-S3-fence-2026-09-05.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.sos/wip/frames/hosted-deck-product-epoch.shape.md"
provenance:
  - { source: ".know/telos/hosted-deck-product-epoch.md:30-71", type: artifact, grade: strong }
  - { source: ".sos/wip/frames/hosted-deck-product-epoch.shape.md:109-113", type: shape, grade: strong }
  - { source: "hosted-deck-product-epoch-DP-2-publisher-envelope.md (sha256 ca3e4af8…)", type: adr, grade: moderate }
  - { source: "hosted-deck-product-epoch-ledger-consequence.md (403 lines, LF-1..LF-4)", type: adr, grade: moderate }
  - { source: "ws-guard-fence-baseline-VERDICT-2026-09-05.md", type: artifact, grade: moderate }
  - { source: "ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md (DELTA-2 PASS-WITH-CONDITIONS)", type: artifact, grade: moderate }
  - { source: "hosted-deck-product-epoch-eunomia-handoff.md rev 2 (H1)", type: artifact, grade: moderate }
evidence_grade: moderate
---

# H2 — 10x-dev → ui cross-rite handoff (hosted-deck-product-epoch, S5)

> **This artifact TRANSFERS STATE. It RULES NOTHING.** It does not answer F-PUBLISH,
> does not rule T7, does not ratify DP-2, does not perform D2-R3/R4/R5, and does not
> assert the S3 baseline frozen (see §4.1 — the freeze is PENDING; the receipt custody
> note and its UV-P are at §4.2). Every disposition below is reported with its owner and
> its current status, honestly, including where that status is *not closed*. Full scope
> fence at §11; self-assessment at §12.

**Envelope per shape H2** (`.sos/wip/frames/hosted-deck-product-epoch.shape.md:1068-1080`).
**Consumed by:** the **ui Potnia at S4 / S7 entry**.
**Gate C binding** (`telos-integrity-ref` §3 handoff-gate): every claim-token in this body
carries a `{path}:{line}` anchor, a VERDICT / REVIEW / ADVERSARY-REPORT citation, or an
explicit `[UNATTESTED — DEFER-POST-HANDOFF]` tag with a defer-watch id. **No wave-level
tokens.**

---

## §0 — READ THIS FIRST (the five facts that scope everything below)

1. **T7 is NOT RULED.** PT-05 is **EVALUATED, NOT CLOSED** (§3). S7 cannot open on it.
2. **DP-2 is STAGED, NOT SHIPPED** and carries **no operator ratification** (§2).
3. **The S3 fence FREEZE is PENDING** — pre-freeze commits P1–P7 are in flight (§4).
   Nothing in this handoff calls the baseline *frozen*.
4. **LEG-3 is REFUSED** at S1 (H1 `:107`). No S7-ii / S8-ii build branch and no S10
   until the operator rules L3 (§8).
5. **The completeness_check the shape asks of H2 is NOT MET on 2 of 3 items** (§10).
   This handoff is transmitted anyway, with the failures named — an envelope that
   hid them would be worse than one that carries them.

---

## §1 — THE EPOCH TELOS (Gate C)

**Throughline, verbatim** (`.sos/wip/frames/hosted-deck-product-epoch.shape.md:109-113`
— the shape marks it *"Not amendable by any agent"*):

> A non-Contente-profile deck is served at a capability URL by the existing
> rail with zero regression on what already works, and both ancestor telos
> are closed by a rite-disjoint attester — nothing counts as done because a
> PR merged.

**Telos §2 YAML, verbatim** (`/Users/tomtenuta/Code/a8t/deck-host/.know/telos/hosted-deck-product-epoch.md:30-71`).
**Its `attestation_status` is carried UNCHANGED by this handoff** — H2 alters no field:

```yaml
telos:
  initiative_slug: hosted-deck-product-epoch
  inception_anchor:
    framed_at: 2026-09-05
    frame_artifact: ".sos/wip/frames/hosted-deck-product-epoch.md:1"
    why_this_initiative_exists: >
      The hosted-deck rail is LIVE for nine Contente offices via floodgates
      Option B (receipt:
      /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/walkthrough-relight-record-2026-08-27.html
      — SENT x2, DARK x1, parity verified; ledger commit f9f0af2 in
      /Users/tomtenuta/Code/a8t/deck-host), but it is single-brand,
      single-account, single-domain by construction; both ancestor telos are
      still verified_realized: UNATTESTED with no eunomia VERDICT on disk; and
      deck-host's own mint/verify path enforces a slug contract ruled
      SUPERSEDED-DEAD (CH-01). The epoch turns a working Contente rail into a
      per-profile deck product without breaking what works.
  shipped_definition:
    code_or_artifact_landed: []  # empty at inception — populated at build close, per-item file:line
    user_visible_surface: >
      a hosted deck URL for a NON-Contente profile (tenuta or lotusun, from
      /Users/tomtenuta/Code/a8t/brand-tokens/profiles/) served with that
      profile's brand, plus every existing Contente deck re-served through the
      same rail unchanged.
  verified_realized_definition:
    user_visible_evidence:
      - "a real non-Contente-profile deck SERVED 200 at a capability URL, byte-identical to its frozen export, with that profile's tokens in the served bytes"
      - "a real Contente office deck re-served with zero regression on the WS-GUARD invariants (noindex/no-store served, 32-hex slug, audience-deny, parity)"
      - "both ancestor telos closed by eunomia VERDICT — epoch-2 is not realized on top of an unattested epoch-1"
    verification_method: in-anger-dogfood
    verification_deadline: 2026-10-03
    rite_disjoint_attester: "eunomia (rite-disjoint; the build never self-attests)"
  attestation_status:
    inception: INSCRIBED
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors: []  # populated at close; Gate B/C discipline binds
    cross_stream_concurrence: false
    code_verbatim_match: false
```

**What the ui rite must take from this:** `shipped: MISSING` and
`verified_realized: UNATTESTED` at `.know/telos/hosted-deck-product-epoch.md:63-65`.
**Nothing in this epoch has landed** in the telos's own sense. A ui deliverable that
merges is not a telos advance; only the `user_visible_evidence` bullets are, and only
when a rite-disjoint attester says so.

**assessment_questions for the ui rite (TEL-Q):**
- **TEL-Q1** — the second `user_visible_evidence` bullet says *"a real Contente office
  deck **re-served with zero regression**"*. Which ui-owned surfaces are inside that
  regression envelope, and which are not?
- **TEL-Q2** — the first bullet requires *"that profile's tokens in the served bytes"*.
  What does the ui rite need from `brand-tokens/profiles/` for that to be checkable on a
  render, and does it already exist?
- **TEL-Q3** — `verification_deadline: 2026-10-03` is the only clock in the epoch. Does
  the ui rite's S4/S7 scope fit inside it, and if not, which item slips?

---

## §2 — THE DP-2 PACKET

| Field | Value |
|---|---|
| **Path** | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/hosted-deck-product-epoch-DP-2-publisher-envelope.md` |
| **sha256** | `ca3e4af8924613b5d81af318ca70825042b04e849bebc33c5c7c74901273eab4` |
| **Lines** | 3,183 |
| **status** | `proposed` (frontmatter) |
| **Disposition** | **STAGED, NOT SHIPPED — ships on FREEZE RECORDED + D2-R3 / D2-R4 / D2-R5** |
| **Operator ratification** | **ABSENT.** `owner: OPERATOR`, gate `hard`; no ratification event exists |
| **Adversary** | `ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md` — iter-1 **BLOCK** (CH-01), DELTA-2 **PASS-WITH-CONDITIONS**; two-iteration cap reached, gate clears, no escalation |

**§0 OPERATOR PACKET is the operator's page** — DP-2 `:15-217`. It is ≤120 lines of door
and states plainly that everything from §1 down is appendix. **The ui rite does not need
to read the 3,183 lines; it needs `:15-217`.**

**The three questions the door asks the operator** (DP-2 `:33-72`), none answered:
- **Q1 — UV-P-5:** WHICH Cloudflare account owns Pages project `deck-host` and
  `decks.cntently.com`? Candidate `a245df42893c85a8d96c71cfa46eec76` is a **file-read
  CLAIM, unverified** (DP-2 `:36-38`).
- **Q2 — T7:** does *"by the existing rail"* bind? Both readings scoped (DP-2 `:41-48`),
  **neither picked**.
- **Q3 — the contract:** which of `{header bytes, slug alphabet, parity receipt shape,
  audience DEFAULT-DENY, root-404, revocability (CC-1)}` are COMMON vs CONTRACT-LOCAL
  (DP-2 `:50-60`). Slug alphabet already ruled contract-local (SG-1, DEFER-3).

**The slate: 14 viable options + 1 refused class** (DP-2 `:117-133` table; §11 count at
`:1779`). Spanning four mechanism-times — stage / deploy / config / **serve** (DP-2
`:415-440`). Two NON-VIABLE: **P-9** on C7 **and** an independent C8/G-18 ground (DP-2
`:154-165`); **P-11** on G-29 prescribed.

**PRE-SHIP CONFIRMATIONS OWED** — DP-2 `:198-217`, three items **owed by other seats and
not performed by 10x-dev**: **D2-R3** (requirements-analyst — P-14's C1–C8 reading, the
"ninth clause", §12.8 w1, the Posture A/B unions); **D2-R4** (principal-engineer — P-14's
band, §13.2 "no C7 line item", §13.5 `--config` "only"); **D2-R5** (security co-seat —
P-14 dissent 3, the C-3 orphan-gate face).

### 2.1 The companion — deck-host's ledger-consequence artifact

`/Users/tomtenuta/Code/a8t/deck-host/.ledge/decisions/hosted-deck-product-epoch-ledger-consequence.md`,
**403 lines**, carrying **LF-1** (`:76` — `deck_file` holds Asana **TASK** gids, not
type-uniform), **LF-2** (`:116` — RECORD-OF-TRUTH DIVERGENCE: the ledger records the
**SERVED** artifact's sha), **LF-3** (`:167` — the ledger has **no** account / project /
domain / profile dimension), **LF-4** (`:190` — the revoked `od67` base32 row is the only
non-32-hex entry, and stays revoked).

**CONDITION 11 — companion P-14 coverage.** Probed at this handoff's write time:

```
2026-09-05T08:35:47Z   grep -c 'P-14' hosted-deck-product-epoch-ledger-consequence.md  →  0
```

**P-14 is ABSENT from the companion.** The probe above is the receipt: `grep -c 'P-14'`
over `hosted-deck-product-epoch-ledger-consequence.md` (403 lines) returned **0** at
`2026-09-05T08:35:47Z`. A requirements-analyst micro-addendum was in flight concurrently
and had not landed at that probe time — **that non-landing is itself carried as a defer
tag, not asserted as a settled state**:

> **[UNATTESTED — DEFER-POST-HANDOFF] `DEFER-COMPANION-P14-ROW`** — the companion carries
> no P-14 row. Its LF-3 finding (*the ledger has no account/project/domain/profile
> dimension*, `:167`) is **precisely the substrate P-14's routing predicate would need**,
> so the absent row is a real gap and not a formatting one. **Watch-trigger:** the RA
> micro-addendum lands. **Owner:** requirements-analyst. **Consumer action:** re-grep the
> companion for `P-14` before relying on its option coverage.

**assessment_questions for the ui rite (DP2-Q):**
- **DP2-Q1** — Q3's six contract terms are publisher-facing. Do any of them constrain a
  ui deliverable (header bytes at render time? root-404 in a preview surface?), or is Q3
  wholly outside the ui envelope?
- **DP2-Q2** — DP-2 is `proposed` and unratified. What ui work can legitimately start
  against an unratified door, and what must wait?
- **DP2-Q3** — LF-2's record-of-truth divergence (companion `:116`) says the ledger
  records the **served** sha. If the ui rite produces a render, which artifact does the
  ui rite consider the record — and does that agree with LF-2?

---

## §3 — PT-05 STATUS (this is what SCOPES S7)

**Carried VERBATIM from the checkpoint record (2026-09-05T08:34:39Z):**

> "EVALUATED, NOT CLOSED — Q1 T7 PENDING-OPERATOR (both readings scoped §5.2 :1345-1359
> incl. the P-14 row; not picked :1357-1358); Q2 NOT-IMPOSSIBLE-BY-PREDICATE-ALONE (G-7
> containment-only; converse unchecked — companion :62-67, S5-Q-1, RA F-3; impossibility
> only via C1-C8 conditioning; P-14 PROVISIONAL pending D2-R3); Q3 YES (P-9 NON-VIABLE on
> two grounds incl. C8/G-18; P-11 G-29; six options G-18 YES conditioned on C8; P-14 G-18
> face ROUTED-UNFULFILLED pending D2-R5); shape :803 on_fail HOLDS — S7/S8 do not proceed"

**The three consequences, stated plainly:**

1. **T7 is PENDING-OPERATOR.** The shape places the T7 ruling at PT-05 and makes it the
   thing that scopes S7 as MEASURE vs MEASURE+BUILD. It has **not been made**. Both
   readings are on the packet at DP-2 `:1345-1359` (including the P-14 row added at
   architect-staging-1); `:1357-1358` states neither is picked.
2. **`shape:803` `on_fail` HOLDS — S7/S8 do not proceed.** This is not advisory. It is the
   checkpoint's own recorded disposition.
3. **The rite-disjoint security coverage is INCOMPLETE BY ONE OPTION.** Said plainly:
   **the security critique of record PREDATES P-14.** P-14 was added to the slate at
   architect-remediation-1 in response to the arch-adversary's CH-01 (BLOCKING); the
   security review on file was authored before that option existed. Its G-18 / C-3
   orphan-gate face is therefore **ROUTED-UNFULFILLED** — routed to the security co-seat
   by the packet (DP-2 §4 P-14 dissent 3), unread by it. **D2-R5 is that gap.** No agent
   in the 10x-dev rite may close it; the architect explicitly did not.

**Q2's honest shape.** The recorded answer is **NOT-IMPOSSIBLE-BY-PREDICATE-ALONE**, not
"impossible". G-7 gives containment only; the converse is unchecked (companion `:62-67`;
S5-Q-1; the RA's F-3 fixture). Silent-404 impossibility is reachable **only** via C1–C8
conditioning, per-option. The ui rite should not read "the predicate protects us" into
this.

**assessment_questions (PT05-Q):**
- **PT05-Q1** — under reading (i) S7 is MEASURE + contract; under (ii) it keeps a build
  branch. **Does the ui rite's S7 scope differ between the two readings** — and if it
  does, what is the ui rite's cost of waiting versus the cost of guessing?
- **PT05-Q2** — P-14 is the slate's only serve-time mechanism and its clause face is
  PROVISIONAL. If the RA rejects it at D2-R3, does any ui assumption change?
- **PT05-Q3** — the security seat has not read P-14. Is there a ui-side surface that
  would also need re-reading if D2-R5 rules dissent 3 a C-3 violation?

---

## §4 — THE S3 FENCE BASELINE REFERENCE (what a future build branch must not break)

### 4.1 Freeze state — stated in the required words

**freeze PENDING (pre-freeze commit P1-P7 in flight on `s3/ws-c-fence-baseline` @`4562596`;
FC-1 operator RA-1 OP-9; FC-2 operator custody OP-11).**

The deck-host working tree is on branch `s3/ws-c-fence-baseline`, stacked on the S2
branch; the freeze commit chain is in flight from `4562596` and **the branch head advances
concurrently while S3 works** (observed moving during this handoff's authoring). **This
handoff never calls the baseline frozen** — see the freeze sentence above and the receipt
custody note at §4.2. A consumer that needs a frozen reference does not have one yet.
(Head advance on this branch is unrelated to `DEFER-SG1-REANCHOR`, which watches the S2
commit `828cea5` — §5.1.)

### 4.2 The receipt — PREMISE-VALIDATION §2 V1, custody note (HARD)

The S3 fence receipt `receipt-fence-baseline-2026-09-05.json` **is GITIGNORED** and is
therefore **NOT reachable from the repo by a downstream consumer**:

```
.gitignore:17                                          receipt-*.json
git ls-files --error-unmatch .ledge/reviews/receipt-fence-baseline-2026-09-05.json
  → error: pathspec '...' did not match any file(s) known to git
```

**Custody note.** A copy is held in the session directory —
`/Users/tomtenuta/Code/a8t/deck-host/.sos/sessions/session-20260905-014608-787b7977/artifacts/receipt-fence-baseline-2026-09-05.json`
(92 KB), **sha256 `867a318d4d88a6497814c397516b69eca9bf84f0581d236f9353190a610c9d4d`**.
That path is session-scoped, not a durable repo surface. Two routes exist:

- **Route A — the operator hands it over** (custody transfer; OP-11).
- **Route B — re-derive from the baseline artifact §2/§3.** **LOSSY: drops 8 of 13 header
  keys, including `content-type`.** A re-derivation is not the receipt.

> `[UV-P: the S3 fence receipt receipt-fence-baseline-2026-09-05.json is retrievable by
> the ui rite as a durable, repo-reachable artifact | METHOD: Route A — operator custody
> transfer of the session-dir copy (sha256 2d7157fb… (re-derived in place by the pre-freeze commit 8d063ba, zero network; superseded 867a318d…)), or Route B — re-derive from
> ws-guard-fence-baseline-2026-09-05.md §2/§3 accepting the documented 8-of-13 header-key
> loss | REASON: the file is gitignored at .gitignore:17 and `git ls-files
> --error-unmatch` reports it not known to git; the only copy this handoff can name is
> session-scoped and the session directory is not a durable consumer surface]`

### 4.3 PT-03 — recorded PASS-CONDITIONAL 2026-09-05T08:23:01Z

**The Q1 denominator sentence, VERBATIM:**

> "1/9 guid-checked + 9/9 structural; INV-07 skipped 8 of 9; INV-16 not probed"

**The S9/S10 gating rule — carry it exactly.** Gate on `meta.probe_count == 21 &&
meta.mode == "live"`. **NEVER on the shell exit code — the exit is MODE-BLIND.** A green
exit does not mean a live run happened.

**The cold-clone discriminator.** 20 FAIL cells arising from missing gitignored substrate
are **fail-closed behaviour, NOT a regression**. A consumer that reads them as regression
will chase a phantom.

**Profile-scope vs rail-scope labels.** **INV-11 / INV-17 / INV-19 / INV-10a** are
**rail-scoped**: a legitimate **NON-Contente** deck **is refused by them**. That is
**correct for the Contente-rail fence** — and it is exactly the collision the epoch's
LEG-1 walks into, because **LEG-1 is profile-scoped**. The fence is right; the scope
labels are the thing to carry.

**INV-14 embeds a hard-coded host.**

**T1 — a NAMED PRE-S8 BLOCKER.** `headers-contract.js:23-29` embeds
`HEADERS_FILE_CONTENT`; **the attribution runs backwards** (the fence asserts against a
copy it holds rather than against the publisher's constant). Named here as a blocker for
S8, not for the ui rite's own work.

**The two-template audience-map forward hazard** bites at **LEG-1 / S8**, not at S4.

**S3 artifacts — all four verified PRESENT in deck-host `.ledge/reviews/`:**
`ws-guard-fence-invariants-enumeration-2026-09-05.md`,
`ws-guard-fence-baseline-2026-09-05.md`,
`ws-guard-fence-baseline-VERDICT-2026-09-05.md`,
`ARCH-CRITIQUE-S3-fence-2026-09-05.md`.

**assessment_questions (FENCE-Q):**
- **FENCE-Q1** — the rail-scoped invariants refuse a legitimate non-Contente deck. **Does
  any ui deliverable produce an artifact those invariants would evaluate**, and if so,
  under which scope label should it be judged?
- **FENCE-Q2** — the receipt is gitignored and the freeze is PENDING. What is the minimum
  the ui rite actually needs from the baseline to proceed at S4 — the receipt, the
  artifact, or neither?
- **FENCE-Q3** — INV-14's hard-coded host and T1's backwards attribution are publisher-side.
  Confirm they carry **no** ui-side obligation, or name the one they do.

---

## §5 — THE UV-P REGISTER, CARRIED (Gate C RULE-2)

Every open UV-P rides this handoff with a defer-watch id. **The account-topology answer
the shape asks H2 to carry does NOT exist; its label is carried instead.**

| id | Status | Defer-watch | Anchor |
|---|---|---|---|
| **UV-P-1** (DW-7 closure) | **OPEN — rides from S3 as an OPEN SEND-BLOCKER.** No send-bearing action proceeds on an undisposed DW-7 | **`DEFER-DW7-CLOSURE-ARTIFACT`** | DP-2 `:1657`; shape `:1455` |
| **UV-P-2** (`PRD-cloudflare-pages-host-decks`) | **RESOLVED-NEGATIVE** — a dangling reference, not an unverified premise | — (disposed) | shape `:1456` |
| **UV-P-4** (`publish-tenuta.sh` + scratchpad tree) | **script half DISCHARGED** by S5-P-4 (consumed per SVR RULE-1). Tree half ephemeral by construction | — (script half consumed) | DP-2 `:1658` |
| **UV-P-5** (account ownership of `deck-host` + `decks.cntently.com`) | **OPEN — the operator's FIRST question.** Candidate `a245df42893c85a8d96c71cfa46eec76` is a **file-read CLAIM, unverified**; the credential on this machine lists only `tenuta-decks`; the DNS zone was never probed | rides under Gate C | DP-2 `:36-38`, `:1659` |
| **UV-P-6** (tenuta staging root + deploy command) | **DISCHARGED-WITH-A-FINDING** — both halves receipted; the finding is that the tenuta deploy is **not reproducible from any durable artifact** (its staging root is a `/private/tmp` scratchpad the environment retires) | — (discharged) | DP-2 `:1660` |
| **UV-P-7** (P-14 serve-time router runtime behaviour) | **OPEN — minted at architect-remediation-1, registered at architect-staging-1.** The toolchain half is receipted (S5-R-3); the **deployed-predicate half is not**. METHOD needs a custom-domain attach + a deploy — both **operator-reserved** | rides under Gate C | DP-2 `:1661` |
| **UV-P-8** (`--config`-supplied `account_id` honoured by `pages deploy`) | **OPEN — adopted verbatim from the arch-adversary** (`ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md` §3.2). Flag and resolution each receipted separately; their **composition is not** | rides under Gate C | DP-2 `:1662` |

**Gate C ride line** (DP-2 `:1669`): **UV-P-1, UV-P-5, UV-P-7 and UV-P-8 ride.** S10 will
not attest over an unrecorded UV-P.

### 5.1 DEFER-SG1-REANCHOR — trigger stated precisely

The slug clause (DP-2 §6) is anchored to `src/slug/shape.js:6-15` @ branch
`s2/ws-f-ch01-reconciliation` commit **`828cea5`** — **BRANCH-RESIDENT and UNMERGED**.

> **The trigger fires on MERGE, REJECT, or REWRITE of `828cea5`. It does NOT fire on head
> advance.** The S2 branch head moving to `ca381c3` **does not** fire
> `DEFER-SG1-REANCHOR`; only a merge, a rejection, or a rebase/squash/force-push that
> makes `828cea5` unresolvable does. A consumer that treats every head advance as a
> re-anchor event will thrash.

### 5.2 CANDIDATE DEFER-5 — routed, NOT ruled

**Record-of-truth for byte-parity**: which artifact *is* the record — deck-host's ledger
`frozen_sha256`, the Asana attachment, or the producer-frozen file? The three demonstrably
disagree (A-arm-2 REFUTED at S1: N=2 mismatch, +1,711 bytes, an `R1(b)` runtime fix; the
Foundation office has no HTML attachment at all; meanwhile the deck-host ledger matches
served 9/9). **Routed to the ancestor PT-04 hash-parity remit. NOT RULED here, and its
defer-watch entry is deliberately NOT minted** — only the disposing sprint mints it
(DP-2 §7.1). The companion's **LF-2** (`:116`) is the same finding at ledger altitude.

**assessment_questions (UVP-Q):**
- **UVP-Q1** — UV-P-5 is unanswered. Does any ui deliverable depend on knowing which
  account serves the rail, or is ui work account-agnostic?
- **UVP-Q2** — DEFER-5 asks which artifact is the parity record. **When the ui rite
  produces a render, what does it consider the record** — and can it say so before
  PT-04 rules?

---

## §6 — LEG-3 REFUSED (S1) — the lineage constraint

**H1** — `/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/hosted-deck-product-epoch-eunomia-handoff.md`,
**revision 2** (frontmatter `:4` — *"2 (DELTA — discharges ADVERSARY-REPORT CH-01..CH-03)"*),
589 lines.

- **`:107` — `## §2 LEG-3 DISPOSITION — REFUSED for BOTH ancestors`.** 1 of 5 arms
  ATTESTED; two arms measured and found FALSE.
- **`:494` — `## §7 PENDING-OPERATOR items`**, carrying the operator register
  **OP-1..OP-7**. Neither H1 item is decidable by any agent.

**The binding consequence:** **no S7-ii / S8-ii build branch and no S10 until the operator
rules L3.** The epoch does not proceed to build on an unattested lineage, and L3 is not to
be quietly downgraded.

---

## §7 — THE OPERATOR REGISTER (OP-1 .. OP-12)

Every item below is **operator-only**. No agent in any rite may perform one.

| id | One line |
|---|---|
| **OP-1 .. OP-7** | The seven PENDING-OPERATOR items carried by **H1 `:494`** — ratification of both S1 ancestor VERDICTs and the epoch-telos items that ride with them |
| **OP-8** | **Close PT-02.** |
| **OP-9** | **RA-1** — the S2 seam ruling reserved to the operator (**FC-1** for the S3 freeze). |
| **OP-10** | **Merge or reject the S2 PR** (`s2/ws-f-ch01-reconciliation`) — this is the event that fires `DEFER-SG1-REANCHOR`; a head advance does not. |
| **OP-11** | **Custody + push** — hand over the gitignored fence receipt (§4.2 Route A) and push the S3 branch (**FC-2** for the S3 freeze). |
| **OP-12** | **Close PT-03.** |
| **DP-2 / a** | **Answer UV-P-5** — which account owns Pages project `deck-host` and `decks.cntently.com` (the door's FIRST question). |
| **DP-2 / b** | **Rule T7** — reading (i) rail-agnostic, or reading (ii) "existing rail" binds. Scopes S7 and S8. |
| **DP-2 / c** | **Ratify DP-2** — **after the freeze**, and after D2-R3 / D2-R4 / D2-R5 land. |

---

## §8 — CONSUMER INSTRUCTIONS FOR THE ui POTNIA (S4 / S7 entry)

**S4 — OPENS NOW (design; DP-1).**
- S4 is the design sprint and is **not** gated on T7. It opens.
- **arch is co-seated** at S4.
- **security must be RELEASED FIRST** — a budget constraint, not a preference. Release
  the security co-seat before opening S4.

**S7 — CANNOT OPEN YET. Two conditions, both unmet:**
1. **DP-1** must be ruled, **and**
2. **PT-05's T7 ruling** must exist (§3 — it does not).

**S7 is MEASURE-FIRST when it does open.** The build branch is conditional, not default.
The shape's own reasoning: an S7 that reads only the frame will schedule build work that
is already on disk.

**S6 is OFF the critical path.**

**HARD FENCE — the ui rite must not touch:**
- `host_bundle.py` (the a8 publisher's staging/parity module), **and**
- **the fence** (deck-host `src/fence/**`).

Both are publisher-side and both are mid-flight (the fence's freeze is PENDING, §4.1).
A ui edit to either would collide with S3's in-flight commits and with S8's remit.

**assessment_questions (CONSUME-Q):**
- **CONSUME-Q1** — with T7 unruled, what is the **largest** ui deliverable that is
  T7-invariant (correct under both readings)? Start there.
- **CONSUME-Q2** — the security seat must be released before S4 opens, and D2-R5 needs
  that same seat to read P-14. **Does releasing it for budget conflict with owing it
  D2-R5** — and if so, that is a Potnia sequencing question, not a ui one. Name it.
- **CONSUME-Q3** — LEG-1 is **profile-scoped** while the fence's INV-11/17/19/10a are
  **rail-scoped** (§4.3). Which scope does the ui rite's S4 output belong to?

---

## §9 — ITEMS (cross-rite-handoff schema v1.0, `handoff_type: assessment`)

```yaml
items:
  - id: UI-H2-001
    summary: >
      The epoch telos and its throughline, carried verbatim with attestation_status
      UNCHANGED (shipped MISSING / verified_realized UNATTESTED). Gate C substrate.
    priority: high
    assessment_questions:
      - "TEL-Q1 — which ui-owned surfaces sit inside the 'zero regression' envelope of the second user_visible_evidence bullet?"
      - "TEL-Q2 — what does ui need from brand-tokens/profiles/ for 'that profile's tokens in the served bytes' to be checkable on a render?"
      - "TEL-Q3 — does the ui S4/S7 scope fit inside verification_deadline 2026-10-03, and if not, which item slips?"
    notes: "Anchor .know/telos/hosted-deck-product-epoch.md:30-71; throughline shape:109-113 (not amendable by any agent)."

  - id: UI-H2-002
    summary: >
      The DP-2 packet (sha256 ca3e4af8…, 3,183 lines, status proposed, STAGED-NOT-SHIPPED,
      unratified) + the companion ledger-consequence artifact (403 lines, LF-1..LF-4).
    priority: high
    assessment_questions:
      - "DP2-Q1 — do any of Q3's six contract terms constrain a ui deliverable, or is Q3 wholly publisher-side?"
      - "DP2-Q2 — what ui work can legitimately start against an unratified one-way door, and what must wait?"
      - "DP2-Q3 — per LF-2's record-of-truth divergence, which artifact does the ui rite consider the record for a render it produces?"
    notes: "Read DP-2 :15-217 (the door page) not the full 3,183 lines. CONDITION 11: companion P-14 count 0 at 2026-09-05T08:35:47Z — [UNATTESTED — DEFER-POST-HANDOFF] DEFER-COMPANION-P14-ROW."
    dependencies: [UI-H2-003]

  - id: UI-H2-003
    summary: >
      PT-05 status VERBATIM — EVALUATED, NOT CLOSED. T7 PENDING-OPERATOR; shape:803
      on_fail HOLDS; S7/S8 do not proceed. Security critique of record predates P-14.
    priority: critical
    assessment_questions:
      - "PT05-Q1 — does the ui S7 scope differ between T7 reading (i) and (ii); cost of waiting vs cost of guessing?"
      - "PT05-Q2 — if the RA rejects P-14 at D2-R3, does any ui assumption change?"
      - "PT05-Q3 — is there a ui-side surface that would need re-reading if D2-R5 rules P-14 dissent 3 a C-3 violation?"
    notes: "This item is the SCOPING item. UI-H2-002 and the S7 half of UI-H2-005 depend on it."

  - id: UI-H2-004
    summary: >
      The S3 fence baseline reference — freeze PENDING; the receipt is GITIGNORED with a
      custody note (Route A operator handover / Route B lossy re-derivation) and a UV-P;
      PT-03 PASS-CONDITIONAL with its verbatim Q1 denominator, the mode-blind gating rule,
      the cold-clone discriminator, the profile-vs-rail scope labels, INV-14, and T1.
    priority: high
    assessment_questions:
      - "FENCE-Q1 — does any ui deliverable produce an artifact the rail-scoped invariants would evaluate, and under which scope label?"
      - "FENCE-Q2 — what is the minimum the ui rite needs from the baseline at S4: the receipt, the artifact, or neither?"
      - "FENCE-Q3 — confirm INV-14's hard-coded host and T1's backwards attribution carry no ui-side obligation, or name the one they do."
    notes: "T1 (headers-contract.js:23-29) is a NAMED PRE-S8 BLOCKER. Never call this baseline frozen."

  - id: UI-H2-005
    summary: >
      Consumer instructions and the carried UV-P / defer register: S4 opens (arch
      co-seated; security released first); S7 blocked on DP-1 AND T7 and is MEASURE-first;
      S6 off the critical path; ui must not touch host_bundle.py or the fence.
    priority: high
    assessment_questions:
      - "CONSUME-Q1 — what is the largest T7-invariant ui deliverable? Start there."
      - "CONSUME-Q2 — does releasing the security seat for budget conflict with owing it D2-R5? (Potnia sequencing, not ui.)"
      - "CONSUME-Q3 — does the ui S4 output belong to the profile scope or the rail scope?"
    notes: "UV-P-1/5/7/8 ride under Gate C. DEFER-SG1-REANCHOR fires on merge/reject/rewrite of 828cea5, NOT on head advance. DEFER-5 routed to PT-04, not ruled."
    dependencies: [UI-H2-003]
```

---

## §10 — COMPLETENESS CHECK (shape `:1080`) — marked HONESTLY

The shape's completeness_check for H2 reads: *"PT-05 passed with T7 explicitly RULED;
DP-2 shows operator ratification; every carried UV-P has a defer-watch entry"*.

| # | Shape item | Mark | Why |
|---|---|---|---|
| 1 | **PT-05 passed with T7 explicitly RULED** | **NOT-MET** | PT-05 is **EVALUATED, NOT CLOSED** (§3, verbatim from the 08:34:39Z record). T7 is **PENDING-OPERATOR**; both readings scoped at DP-2 `:1345-1359`, neither picked `:1357-1358`. `shape:803` `on_fail` HOLDS |
| 2 | **DP-2 shows operator ratification** | **NOT-MET** | DP-2 frontmatter `status: proposed`; disposition **STAGED, NOT SHIPPED**; `owner: OPERATOR`, gate `hard`. No ratification event exists. Ratification is DP-2/c in §7 and is sequenced **after** the freeze and after D2-R3/R4/R5 |
| 3 | **Every carried UV-P has a defer-watch entry** | **PENDING** | The four riding UV-Ps (UV-P-1, UV-P-5, UV-P-7, UV-P-8) are each registered with a ride disposition at DP-2 `:1657-1669` and carried at §5 here. **UV-P-1 carries a named id** (`DEFER-DW7-CLOSURE-ARTIFACT`). **UV-P-5 / UV-P-7 / UV-P-8 ride under the Gate C clause but no `defer-watch-manifest` entry has been MINTED for them** — per DP-2 §7.1 and the H1 precedent, only the sprint that disposes an item mints its entry, and this handoff is not that sprint. **PENDING, not MET — and deliberately not upgraded by this envelope** |

**Transmission decision, stated openly.** Two of three checks are NOT-MET and the third is
PENDING. **H2 is transmitted anyway**, because the ui rite's S4 is not gated on any of
them and needs the design context now, while S7 **is** gated and must know exactly why.
An envelope that withheld the state, or that marked these MET to clear a checklist, would
be the failure this discipline exists to prevent. **The receiving Potnia should treat
items 1 and 2 as hard gates on S7 — not as paperwork.**

---

## §11 — SCOPE FENCE — what this handoff did NOT do

- **Did NOT rule T7.** Both readings carried; neither picked.
- **Did NOT answer F-PUBLISH.** The 14+1 slate is transmitted; no option is preferred.
- **Did NOT ratify DP-2.** Its status stays `proposed`; no field was flipped.
- **Did NOT perform D2-R3 / D2-R4 / D2-R5.** Listed by owner in §2 and §3, unperformed.
- **Did NOT assert the baseline frozen.** The required freeze wording is used verbatim at
  §4.1 (`freeze PENDING …`), and the word appears in this artifact only inside that
  wording or inside a refusal like this one.
- **Did NOT cite the fence receipt as reachable.** Custody note + UV-P at §4.2, grounded
  in `.gitignore:17` and a `git ls-files --error-unmatch` miss.
- **Did NOT edit DP-2 §12 or §13**, or any file other than this one.
- **Did NOT author the wave handoff or the charge.** The attestation plane (the charge) is
  emitted by `ari procession charge`, never hand-written (schema §Attestation plane).
- **Did NOT touch deck-host git state.** All deck-host reads were read-only (`sed -n`,
  `grep`, `ls`, `shasum`, `git ls-files --error-unmatch`, `git branch --show-current`);
  the tree is on `s3/ws-c-fence-baseline` and was neither stashed, checked out, nor reset.
  Its head advanced during authoring under S3's own hand, not this one (§4.1).

---

## §12 — SELF-ASSESSMENT

**Evidence grade: MODERATE** (ceiling, per `self-ref-evidence-grade-rule`). This envelope
**transfers state and rules nothing**; every disposition it reports is another seat's, and
is reported with that seat named.

**Where this handoff is weakest, stated plainly:**

1. **Two of three completeness checks are NOT-MET** (§10). The ui rite receives a design
   context whose scoping question (T7) is open. That is the true state, not a defect of
   the envelope — but a consumer that reads past §10 will mis-scope S7.
2. **CONDITION 11 resolved to ABSENT** (§2.1): the companion carries no P-14 row at
   08:35:47Z. An RA micro-addendum was in flight. **Re-grep before relying on the
   companion's option coverage.**
3. **The rite-disjoint security coverage is incomplete by one option** (§3). The security
   critique of record predates P-14. D2-R5 is unfulfilled and no 10x-dev seat may close it.
4. **The fence receipt is not reachable** (§4.2). Route B is documented-lossy (8 of 13
   header keys, including `content-type`). A consumer that re-derives has less than the
   receipt, and should say so when it does.

**Gate C self-audit** (`telos-integrity-ref` §3 handoff-gate): every claim-token in this
body carries a `{path}:{line}` anchor, a VERDICT / REVIEW / ADVERSARY-REPORT citation, or
an explicit `[UNATTESTED — DEFER-POST-HANDOFF]` tag with a defer-watch id. No wave-level
token appears. The one unbacked claim class — the companion's P-14 coverage — is tagged
`DEFER-COMPANION-P14-ROW` rather than asserted or dropped.

---

**END — H2.** 10x-dev → ui. `status: pending`; `blocking: false` (the ui rite's S4 opens
without a response). **State transferred; nothing ruled.**
