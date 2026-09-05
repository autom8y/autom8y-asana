---
artifact_id: hosted-deck-product-epoch-DP-1-brand-seam
schema_version: "1.0"
type: decision
status: ratified                  # RATIFIED by the OPERATOR 2026-09-05 (typed word, wave 3 Phase 0.2); was: proposed
door: DP-1
owner: OPERATOR
initiative: hosted-deck-product-epoch
session_id: session-20260905-014608-787b7977
sprint: S4
rite: ui
rung: authored
evidence_grade: moderate
self_ref_cap: MODERATE
delta_pass: 2                      # two-iteration loop CLOSED; iteration 2 returned PASS-WITH-CONDITIONS (mechanical). This packet does NOT attest the conditions cleared.
adversary_verdict: "PASS-WITH-CONDITIONS (CONCUR-WITH-FLAGS) — C-1 RESOLVED; M-1..M-14 applied mechanically at this pass"
completeness_attester: "arch-adversary at leg 5; PT-04 hard gate after S4"
leg5_critique:
  path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md"
  lines: 562
  sha256: "bcf5ffd8d185084db61841b1e5fe9f1cdff4e19e53cd55f17aff367f517bb2e4"
  verdict: "BLOCK (iteration 1 of 2) — CH-01 enumeration gap; 11 FLAGs; 9 ADVISORY"
  disposition_here: "C-1 discharged by adding B-8 at full depth; C-2..C-12 addressed; A-1..A-9 where mechanical."
leg5_delta_critique:
  path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/ADVERSARY-REPORT-S4-DP-1-brand-seam-DELTA-2026-09-05.md"
  lines: 277
  sha256: "1ddd502775c33e38ca476332daaeed35632ec39e1d828eb6fc629a4ef434ee45"
  verdict: "PASS-WITH-CONDITIONS (CONCUR-WITH-FLAGS) — iteration 2 of 2; the loop CLOSES here, no third critique exists"
  disposition_here: "M-1..M-14 applied verbatim from that report's §7 and §4 as a MECHANICAL pass — no authoring judgment exercised; every edit had a determinate supplied source. Notable reversal: M-1/CH-13 returns K-6 to VIABLE (a re-served frozen artifact is a produced OUTPUT, not code crossing). Verify by the §7 greps, NEVER by §13.3."
answers_forks: ["F-BRAND: B-0 (SLOT A)", "WHICH-PAIR: (c) neither (SLOT B)", "F-DECK: K-3 component-set layer IN DECK-KIT (SLOT C)", "F-ENGINE: E-1 (SLOT D)"]   # RULED by the OPERATOR at the /interview sitting 2026-09-05; transcribed + ratified wave 3; was: [] (HOSTED, none ANSWERED)
ratification: { by: "OPERATOR (typed word, 2026-09-05)", at: "2026-09-05T18:42:43Z", session: "session-20260905-014608-787b7977", transcribed_sha256: "69b62c05cb99a261a5e8c1d4608fff187cfff3264cb7b43c89533dd208b4350f", scribe: "dispatcher (wave 3 Phase 0.1/0.2)", checkpoint: "PT-04 PASS recorded by the dispatcher at ratification" }
ground_branch: "s3/ws-c-fence-baseline @8d063ba (declared branch-sprint override of origin/main; S2/S3 receipts are unmerged and live only on the stack)"
inputs:
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg1.md", sha256_16: "85f70e313380600f", lines: 778, leg: "1 (propose) — F-BRAND slate B-0..B-8, three axes, G-15, row schema [DELTA: +B-8 at 15 rows; C-3 axis convention; §5.3 sequencing upheld]" }
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg2-engine.md", sha256_16: "22bf114aae2dc5f9", lines: 380, leg: "2 (rendering-architect) — F-ENGINE slate E-1..E-5 [DELTA: E-2 split into (i)/(ii); §A direction sentence corrected]" }
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg2-deck.md", sha256_16: "8f0b5264d45079f0", lines: 644, leg: "2 (component-engineer) — F-DECK slate K-1..K-6 [DELTA: K-6 import re-read PRESENT -> NON-VIABLE; §A.5 layer exclusions]" }
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg2-css.md", sha256_16: "770b9b6db813ec4e", lines: 368, leg: "2 (stylist) — CSS-emission characterization [NOTE: dispatch brief said 314; on-disk count is 368 — discrepancy recorded, §1 PL-11]" }
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg3-subtractive.md", sha256_16: "60e1f4eae8bb94f7", lines: 483, leg: "3 (frontend-fanatic) — subtractive audit + served-surface measurement" }
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg3-a11y.md", sha256_16: "97252d2d9ab85eb4", lines: 1142, leg: "3 (a11y-engineer) — contrast matrices, 20 a11y rows, deferred terminal gate [DELTA: C-5 fraction corrected; B-0/B-8 rows added; §F carriage manifest]" }
  - { path: "/Users/tomtenuta/Code/a8t/deck-host/.ledge/spikes/dp1-drafts/DP-1-draft-leg3-publish-path.md", sha256_16: "fde2ad078051f7b2", lines: 989, leg: "3 (publish-path) — SOR located, three change mechanisms, UV-P discharges" }
source_note: >
  The seven drafts above are DURABLE, REPO-REACHABLE copies under
  .ledge/spikes/dp1-drafts/ (re-pointed at DELTA iteration 2, M-13/A-7; each carries its
  sha256 prefix per that directory's README.md). THIS PACKET MUST STAND ALONE for the
  operator: every claim it makes is restated here with its receipt id, never left behind
  a path the operator cannot open. Receipt ids (S4-*-P-NN) resolve into these copies.
---

# DP-1 — the brand-seam one-way door (F-BRAND primary; F-DECK and F-ENGINE ride)

## §0 OPERATOR PACKET

> **This page is the door and it is rulable without the appendix.** Everything from §1
> down is support. This packet **ANSWERS NOTHING**: three forks are hosted, all four
> ruling slots are EMPTY, no option is ranked, and there is no "recommended" column
> anywhere in this artifact. RUNG = `authored`; no code, no prod, no schema edit.

### The three forks, and the prior sub-question

| Fork | The question | Slot |
|---|---|---|
| **F-BRAND** (primary) | Where does authority over the shared token contract live — and whose change-cadence then governs every future profile? | **A** |
| *prior sub-question* | DP-1's second question presupposed **two envelope schemas of the same kind**. There is **one** envelope schema (a8t) and **one package tokens schema** (a8). Before "what reconciles them," rule **which pair is being reconciled**. | **B** |
| **F-DECK** | At which layer of the deck's construction stack is per-profile variance first admitted? | **C** |
| **F-ENGINE** | What KIND of object crosses the a8→a8t boundary for a profile to be rendered? | **D** |

### The three axes, one line each (full statements §2)

- **F-BRAND** — the **locus of authority** over the token contract both engines honour.
- **F-DECK** — the **artifact layer at which profile-variance is first admitted**.
- **F-ENGINE** — the **kind of object that crosses** the a8→a8t boundary.

### The option roster, one line each (full rows §3/§4/§5)

**F-BRAND (9).** `B-0` **[TRUE NULL]** do nothing; write no ratifying sentence; the identical leaf layer is a fact, not a contract · `B-1` a8t envelope sovereign, a8 conforms · `B-2` a8's published package schema is the contract; a8t conforms to its 122-leaf tree · `B-3` a third co-signed artifact, joint authority · `B-4` **[MINIMAL GOVERNANCE ACT — re-labelled, see §1 PL-08]** ratify the already-identical leaf layer, govern nothing · `B-5` no reconciliation; the divergence is the ruling · `B-6` **[NOT-FIRST-INSTINCT]** authority at the serving predicate — the contract is the served bytes · `B-7` **[DELEGATION]** delegate to the external DTCG standard · `B-8` **[ADDED AT DELTA]** content-addressed authority — no repo's *file* is sovereign; the shared `definitions` **value** is, pinned in both repos' existing pin files and enforced by both existing sync-gates. **The only position under which the ungated in-place vendored fork becomes detectable.**

**F-DECK (6).** `K-1` **[TRUE NULL]** no layer admits variance · `K-2` design-system-namespace layer · `K-3` component-set layer (namespace stays shared) · `K-4` template layer (the frame's first-named position) · `K-5` render-invocation layer — **two readings, one axis position**: (a) novel a8-side seam, (b) promote deck-kit's already-built `--profile-root` · `K-6` **[NOT-FIRST-INSTINCT]** post-render projection layer — a value-rewrite over the frozen export. **VIABLE but REFUSAL-EXPOSED**: a permanent K-6 strategy is INHERITED construction and fires legacy-floor §2 REFUSAL; its import reading is CONTESTED (PL-17) and the operator rules.

**F-ENGINE (5; E-2 split (i)/(ii)).** `E-1` **[TRUE NULL]** nothing crosses — the standing, already-shipped architecture · `E-2(i)` a declarative artifact contract crosses **a8t→a8** (build-time) · `E-2(ii)` the same contract crossing **a8→a8t** — deck-kit consumes the Contente tokens contract; the direction G-29 explicitly permits · `E-3` a produced artifact crosses (a8→a8t, reuses the existing staging rail) · `E-4` **[NOT-FIRST-INSTINCT]** a running process's output crosses (serve-time) · `E-5` **[NON-VIABLE — G-24/G-29]** source code crosses.

### The five findings that change the price of everything

1. **The leaf contract is already identical FOUR ways, not two.** `definitions` sha256 `8831da27…` matches across a8t brand-tokens, the a8 SOR envelope, the vendored `v1.0.0` package schema, AND fe-skeleton `origin/main` — the common ancestor (S4-D-P-34). At leaf altitude **there is nothing to reconcile**; the wrappers differ only in `$id`/`title`/`description` (S4-D-P-35).
2. **There is NO upstream publish.** `npm publish` appears nowhere; distribution is a **git tag** consumed as a git dependency (`github:autom8y/contente-tokens#v1.0.0`), by the **same human operator** who edits the a8t side (S4-D-P-13/15/20/24). And a **second, ungated mechanism exists**: in-place patch of the git-tracked vendored copy, invisible to every guard in the system (S4-D-P-10/14/28).
3. **The producer has no build-time schema consumer.** `grep -rn 'tokens.schema.json' vendor/deck-producer` → **zero rows**; no ajv, no validator, `tokens.json` never read (S4-D-P-28). A schema change on the a8 side today has **no build-time enforcement anywhere**.
4. **deck-kit's CSS variable names bind ONLY tenuta.** `deck.css`'s `var(--surface-page)`-class references match tenuta's declared names verbatim; of the 13 colour-role names, **0** are declared by any non-tenuta profile (a8t shares 4 of 8 typography names only) (S4-A-P-1..S4-A-P-7). Pointing `--profile-root` at a8t / fixture / lotusun today resolves against **undefined custom properties** — collapse of the colour relationship, not a poor ratio.
5. **Contrast is unenforced on both sides, and 10 of 18 measured literal pairs already fail.** No contrast check exists in deck-kit's closed 12-id claim vocabulary nor anywhere in the Contente build tree (S4-A-P-10/S4-A-P-11). Below AA on token literals today: tenuta caption-on-sunken **4.13** (the SHIPPED profile), a8t muted **3.41**, fixture outline **2.68**, fixture link/CTA **3.67**, and a cross-profile swap collapsing lotusun's own 5.75 CTA to **2.76** (§9).

### BUILD-SPRINT PRECONDITION — the deferred a11y terminal gate

**Binding on any build sprint that follows DP-1, under whichever option combination is ruled.** It is **D0 — hard, zero-tolerance, all postures**; no posture, scope, or door ruling exempts it. Four testing-pyramid layers must RUN and PASS against the **actually rendered surface**, not against declared tokens: static lint · axe-core audit · interaction/keyboard · manual review. **Nothing in this initiative has rendered; zero of the four layers has run.** The §9 numbers are token-literal arithmetic with no browser open — a **floor, not a ceiling**, on what a live run would find. **SILENCE IS NOT A PASS**: the gate has not fired because it has no surface to fire on, not because a surface was checked and found conformant. *(Full inscription pasted VERBATIM at §7 — deliberately not inlined here, stated reason: it runs ~45 lines and would breach this page's 120-line cap. The five sentences above are the rulable content; §7 is one page away.)*

### Standing assumptions (inputs, not open questions)

- **T7 is UNRULED** — S4 assumes **neither** reading. No option below is stated differently under either.
- **LEG-3 is REFUSED** (**H2** §6 — H2 = `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/spikes/hosted-deck-product-epoch-10xdev-handoff.md`, path resolved at DELTA per C-9; all later "H2 §N" citations resolve to this file) — **no build branch may open on this lineage.** Every option here is a design whose build the operator gates separately.
- **RUNG = `authored`.** This packet advances no telos leg. `.know/telos/hosted-deck-product-epoch.md` keeps `shipped: MISSING` / `verified_realized: UNATTESTED`.
- **`a8 → a8t` imports are NON-VIABLE, not costly** (G-24/G-29). **Exactly one option carries `PRESENT`: E-5.** *(At DELTA iteration 1 K-6 was also marked PRESENT; the arch-adversary REVERSED that at iteration 2 — a re-served frozen artifact is a produced OUTPUT, not code crossing, and the same `_ds_bundle.js` marker already sits in deck-host's served `public/761ebfd8…/index.html`. K-6 is VIABLE and REFUSAL-EXPOSED; see PL-17.)* **G-29 is silent on a8t→a8** — a gap for the operator, **not a permission this packet grants**; that silence is priced explicitly at **E-2(i)**, while **E-2(ii)** is the direction G-29 *explicitly permits*.
- **`legacy-floor-isolation` §2, stated once for the whole packet:** the Contente inliner is a **FLOOR to clear and a REFERENCE to consult — never a BENCHMARK to match nor an IMPLEMENTATION to inherit.** Where the CONSULTED/INHERITED test fires REFUSAL (B-2's key-tree inheritance; E-5; K-6 as a permanent strategy), **the refusal is a POSITIVE result**, not a defect of the option.

### RULING SLOTS — TRANSCRIBED 2026-09-05 (STAGED, NOT RATIFIED — the ratification stamp is the operator's separate act)

```
DP-1 / SLOT A — F-BRAND. Which of B-0..B-8 (§3), or none?
  RULING: B-0 — OPERATOR, /interview sitting 2026-09-05; transcribed by the dispatcher; source HANDOFF-wave2 §8

DP-1 / SLOT B — WHICH PAIR is being reconciled?   ** RULE THIS FIRST **
  (a) envelope-to-envelope   (b) envelope-to-package-tokens   (c) neither
  WARNING (§1 PL-09, corrected at DELTA): SLOT B's three readings do not span
  SLOT A's slate. B-2 = (b) decided for Contente; B-1 = (b) decided the OTHER
  way — DOUBLE-HOMED, not homeless; B-5 = (c) verbatim. B-0, B-3, B-4, B-6,
  B-7 have no home. B-8 is HOMELESS BY CONSTRUCTION and says so: it reconciles
  neither pair of FILES, pinning the VALUE they already share. **If SLOT A is
  ruled B-8, SLOT B as posed has no correct answer** — the packet states this
  rather than forcing a fit. Presented, never recommended.
  RULING: (c) neither — OPERATOR, /interview sitting 2026-09-05; transcribed by the dispatcher; source HANDOFF-wave2 §8

DP-1 / SLOT C — F-DECK. Which of K-1..K-6 (§4), or none?
  RULING: K-3 component-set layer IN DECK-KIT (a8t grows it; producer untouched) — OPERATOR, /interview sitting 2026-09-05; transcribed by the dispatcher; source HANDOFF-wave2 §8

DP-1 / SLOT D — F-ENGINE. Which of E-1, E-2(i), E-2(ii), E-3, E-4, E-5 (§5), or none?
  ORDER WARNING (§6, corrected at DELTA): SLOT D is materially order-dependent
  on SLOT A; SLOT C is very nearly order-INDEPENDENT. Not equivalent.
  SLOT D ALSO SELECTS K-5's READING: ruling E-2(i) selects K-5(a); ruling E-1
  selects K-5(b). An operator ruling "K-5" alone has not chosen a reading.
  RULING: E-1 — OPERATOR, /interview sitting 2026-09-05; transcribed by the dispatcher; source HANDOFF-wave2 §8

RULING ORDER (stated, not recommended — the operator may depart from it):
  B (the form) -> A (the locus) -> D (the crossing, via the ruled B's §6.1 column).
  C is independent of all three (§6.2: 3 of 54 cells, all K-6, all weak).
```

> **TRANSCRIPTION NOTE (scribal act, attributed).** The four rulings above were spoken by the OPERATOR at the
> /interview sitting of 2026-09-05 (session session-20260905-014608-787b7977) and recorded in
> `/Users/tomtenuta/Code/a8t/deck-host/.ledge/handoffs/HANDOFF-wave2-hosted-deck-product-epoch-2026-09-05.md` §8 :297.
> The dispatcher transcribed them here on 2026-09-05 (wave 3, Phase 0.1) and authored none of them. This is a
> STAGING act: the packet is TRANSCRIBED and NOT RATIFIED until the operator types the reserved word and the
> ratification stamp is written (shape §7 reserved levers :1187). Until then `status: proposed` and
> `answers_forks: []` in the frontmatter stand unchanged, and the §0 sentence at :53 ("all four ruling slots
> are EMPTY") describes the packet as it was authored and is superseded by these four lines only.
> Packet sha256 BEFORE this transcription: `6a716450c5fc47266a0e5f100ae663bca6a8ec085415f0251d15bfbf5bad4028` (1354 lines).
> Sha chain: 3d76d4fb… (leg-4 synthesis; per HANDOFF-wave2 frontmatter :21, inherited not re-derived) →
> c2c8ab19… (1265 lines; the arch-adversary DELTA verdict binds here, §13.4 :1342) → 5b300176… (1332 lines;
> PT-04 recorded against this sha, 15:57:11Z) → 6a716450… (1354 lines; R1 mechanical pass, 16:01:06Z) → THIS.

> **RATIFICATION STAMP.** RATIFIED by the OPERATOR on 2026-09-05 (typed word; wave 3, Phase 0.2; session
> session-20260905-014608-787b7977). The four transcribed rulings above are the operator's and are now BINDING:
> SLOT A = B-0 · SLOT B = (c) neither · SLOT C = K-3 component-set layer IN DECK-KIT · SLOT D = E-1.
> The stamp binds to the transcribed packet sha256 `69b62c05cb99a261a5e8c1d4608fff187cfff3264cb7b43c89533dd208b4350f` (1367 lines). Written by the dispatcher on the
> operator's word; the dispatcher authored no ruling. Consequences recorded elsewhere, not here: PT-04 recorded PASS
> (closing the 15:57:11Z staged PASS at sha 5b300176…); S7 entry :537 SATISFIED; the adversary co-sign still binds
> c2c8ab19… (R5 residual carried, not cured); K-6 stays CONTESTED (PL-17); the a11y terminal gate (§7) is inherited,
> not waived, by any build sprint that follows — none opens in wave 3 (T7 reading (i)).

### Reading order for a ten-minute ruling

§0 (this page) → §1 PREMISE LEDGER (what changed since the slates were written) → §2 axes + row schema → §3 F-BRAND rows → §6 cross-product. §4, §5, §7-§13 are support.

### Honest self-assessment

**MODERATE, capped** (`self-ref-evidence-grade-rule`). **This packet does not attest its own completeness** — that is the arch-adversary's at **leg 5** (`delta_pass: 1`), and **PT-04**'s hard gate after S4, whose own question is whether the slates are *"exhaustive, or a recommendation wearing a slate's costume."* Every `dissent` cell carries an **EMPTY labelled leg-5 slot**.

---

## §1 PREMISE LEDGER — corrections propagate, never silently

> **Rule.** Every correction below carries three fields: **what the slate carried →
> what the probe found → which rows re-price.** No correction is applied to a row
> without appearing here first. Legs 2 and 3 were authored in a parallel block and
> could not see each other; several corrections are one leg falsifying another's
> premise. That is the block working, not failing.

| id | what the slate carried | what the probe found | which rows re-price |
|---|---|---|---|
| **PL-01** | D-2: *"the a8 side has no editable source-of-record in this tree; its schema is a PUBLISH ARTIFACT; a contract change there is an **UPSTREAM PUBLISH** — different actor, different cadence, different revocability."* | **HALF-RIGHT; operative clause REFUTED.** SOR **FOUND** at `/Users/tomtenuta/Code/a8/a8/repos/autom8y-contente-tokens`, clean at `7e64fcd` on `main` (S4-D-P-16/17). **`npm publish` appears nowhere**; CI is guards-only with a read-only token (S4-D-P-20). Distribution is a **git tag** (exactly one, `v1.0.0`, never moved) consumed as a **git dependency** — `vendor/deck-producer/package.json:17` → `github:autom8y/contente-tokens#v1.0.0`, lock-resolved `git+ssh://…#1d8c8c0` while every other lock entry resolves to `registry.npmjs.org` (S4-D-P-13/15/18). **Same operator both sides** (S4-D-P-24). | **B-1, B-2, B-3, B-7** (all "share a contract" rows); **E-2**; css **E2/E5**. The `contract-change mechanism` cell changes value in every one. |
| **PL-02** | Leg-1 §3.5 **F5**: *"the change-authority asymmetry … is paid **forever**, not once. No engineering retires it."* Read as **actor vs actor** (a8 publisher vs a8t engineer). | **The asymmetry is REAL but is NOT actor-vs-actor.** There is one human operator with commit rights on all four repos; no registry account, no publish credential, no external maintainer, no approval body (S4-D-P-24). The true asymmetry is **legitimating-change vs silent-edit**: a change that keeps the artifact honest to the tag its manifest names requires commit+tag+re-vendor (mechanism i); a change that silently forks it from that tag requires **one file edit** (mechanism ii) — and **nothing in the system distinguishes the two** (no vendor-site lockfile, no `integrity`, no CI check against `v1.0.0`, and the package's own `--check` guard was never published) (S4-D-P-05/10/14/28). | **B-1, B-2, B-3, B-7** cost cells; F5's own text at §2. The cost survives; its *name* changes. |
| **PL-03** | Row-schema column: `contract-change mechanism: file-edit \| upstream-publish` (leg-1 §4). | Two values are insufficient and one of them names a mechanism that does not exist. | **EXPANDED to four values, binding on every row in this packet:** `file-edit` · `git-tag+re-vendor` · `in-place-vendored-patch (ungated)` · `none`. Re-priced in place at §3/§4/§5. |
| **PL-04** | **UV-P-S4-1** (leg-1 `:680`): *"the frame's G-15 second hash `e15ea4db` identifies a real artifact under some name on the a8 side"* — leg-1 found zero `dtcg-envelope.schema.json` in the a8 tracked tree and recorded the hash **UNRESOLVED-THIS-SESSION**. | **DISCHARGED.** `e15ea4db9c42cea2…` **is** the DTCG envelope, with two byte-identical referents: the a8 SOR's own `dtcg-envelope.schema.json`, and fe-skeleton `origin/main:src/lib/components/core/dtcg-envelope.schema.json`. Both hash to git blob `f9ea4c44…` — exactly the `pinned_blob_sha` in `contente-tokens/dtcg-envelope.pin.json:3` (S4-D-P-26). **Leg-1's negative result was correct and its scope was the reason**: the file was added to the SOR *after* `v1.0.0`, so it is absent from the vendored copy — the only surface leg-1 could see. | §2 G-15 restatement; **B-1, B-3, B-7**. The frame's G-15 "two hashes" is now fully resolved: same substance, different nameplate. |
| **PL-05** | **UV-P-S4-2** (leg-1 `:681`): *"a shared token contract with an a8-side obligation would in practice be changeable **only** by an upstream publish."* | **DISCHARGED — REFUTED on its operative word "only."** What survives: mechanism (i) is a genuine multi-step round-trip, so the intuition that this is not a one-file edit *at the consumption site* was sound. What is refuted: "only" (mechanism ii exists, in-tree, ungated) and "publish" (the wrong noun — it is `git tag`, same operator) (S4-D-P-10/11/13/15/20/28). | Same set as **PL-01**. Leg-1 `:348` should read *"upstream commit + tag + re-vendor (no registry), by the same operator."* |
| **PL-06** | **css-draft UV-P #1 and #2** (`:330-341`): the SOR's location, and whether the package publishes to a public registry, a private registry, or "some other mechanism." | **BOTH DISCHARGED, without a network call.** #1: the SOR **is** a sibling a8-org repo and **is** checked out — two directories from the vendored copy the leg inspected (S4-D-P-16/17). #2: **the third branch** — neither public nor private registry; distribution is git tag over `git+ssh`, then a committed vendored copy. `package.json:4 "private": false` is confirmed **non-probative** (S4-D-P-04/13/14/15/20). | css draft's `:163-164` and `:170-171` corrected; **B-1, B-2, B-3, B-7** cost cells inherit PL-01. |
| **PL-07** | **UV-P-F-1** (subtractive `:E.3`): the served Contente artifacts' byte-identity to the ledger `frozen_sha256` was **string-matched against an already-computed digest**, never re-derived — that leg had no hashing tool. | **DISCHARGED by the dispatcher (SVR, 2026-09-05), receipt `S4-DISP-P-1`.** `shasum -a 256 public/761ebfd8a7e1ae5bb7442c8dc2154f6d/index.html` = `0adebd0f779d6040f2a3061f7b6829677d335fac58f0ba6c75606cde8c624960`, **equal** to `config/deck-manifest.json:81` `frozen_sha256` for slug `761ebfd8…` (`:77`) and **equal** to the S1 VERDICT record (`.ledge/reviews/VERDICT-cloudflare-pages-host-decks-2026-09-05.md:274`). `--space-4: 16px` confirmed present in those served bytes (1 occurrence). `deck-kit/dist/deck-kit-fixture.html` = `a35207252c780f1d04b755794104068012a61352b643cd211edf8ab9ca2ef9dd` — **no ledger entry exists for it; none is invented here.** | §9 measurements appendix; **B-6, E-3, K-6** (all served-artifact-altitude rows). |
| **PL-08** | Leg-1 tagged **B-4** as the slate's `[NULL]` ("share a contract, unify nothing"). | **B-4 is NOT the true null.** Its own mechanism cell is *"ratify … as the entire shared surface"* and its own cost cell is *"one sentence of ratification"* — an **authored act** that did not exist before it is written. An independently-drafted do-nothing null contains no such sentence (subtractive §A.1). B-5 is closer to nothing but is a **permanent foreclosure**, not silence. | **B-0 ADDED at full depth** (§3, empty dissent slot); **B-4 RE-LABELLED** from `[NULL]` to `[MINIMAL GOVERNANCE ACT]`. `K-1` and `E-1` are confirmed **TRUE nulls** by the same test and keep their tags. |
| **PL-09** | The ruling-slots box invites SLOT A and SLOT B to be filled independently. | **SLOT B's three readings do not cover SLOT A's slate.** Only 2 of 8 map cleanly: **B-2** is reading (b) decided in Contente's favour; **B-5** IS reading (c) verbatim. **B-0, B-1, B-3, B-4, B-6, B-7 have no home** — B-1 is reading (b) decided the *other* way, which (b)'s text does not distinguish from B-2's direction; B-3 posits a third artifact no reading names; B-4/B-0 operate at leaf altitude only, a scope none of (a)/(b)/(c) addresses; B-6 relocates the contract outside the schema-vs-schema framing SLOT B is posed in; B-7 delegates to a fourth party (subtractive §D.3). | **SLOT B warning inscribed in §0.** No reading is added or removed by this packet — the operator rules the form. |
| **PL-10** | Leg-2-engine's **E-4** F-BRAND-coherence row names tension with B-1/B-2/B-3/B-7 and is **silent on B-5**. Leg-2-deck's **K-6** names the structurally identical tension with B-5 explicitly. | **Same logical need, dispositioned inconsistently across two independently-authored slates.** A live serve-time render (E-4) needs *some* per-profile token source exactly as a value-rewrite (K-6) does; B-5's "nothing shared" premise supplies neither (subtractive §D.2). | **E-4's coherence line is FIXED in this packet** (§5) to carry the same weak tension with B-5 that K-6 carries. This is a correction, not a new claim. |
| **PL-11** | Dispatch brief recorded the stylist leg-2 draft at **314 lines**. | On-disk count is **368 lines** (`wc -l`, this leg). Content is intact and fully read; only the count differs. | Nothing re-prices. Recorded so the discrepancy is not discovered later as a silent substitution. |
| **PL-12** | Leg-1 §3.3 read the a8 `tokens.schema.json` as a contract whose change would be enforced somewhere on the a8 side. | **The producer never reads it.** `grep -rn 'tokens.schema.json' vendor/deck-producer` (excluding node_modules) → **zero rows**; no ajv, no JSON-schema validator, `tokens.json` never read. The producer consumes exactly ONE of the package's three surfaces: `src/css/*.css`. The schema is **inert cargo at this consumption site** (S4-D-P-28). | **B-1, B-2, B-3, B-7** — every option whose enforcement story assumed an a8-side build-time schema consumer. The only live guard is `generate.mjs --check` in the SOR's own CI, which the vendored copy **cannot run** (S4-D-P-05). |
| **PL-13** | Leg-1's §5 B-row a11y cells read the focus-token gap as a **naming divergence** across five profiles (S4-P-8); the leg-4 packet then wrote *"of the 13 colour-role names, **0** are declared by any non-tenuta profile (a8t shares 4 of 8 typography names only)"*. | **OVERSTATED — CORRECTED AT DELTA (C-5), and the correction is the a11y seat's own, carried verbatim:** *"only tenuta's naming actually matches deck-kit's template FOR COLOUR ROLES (§A.1; a8t shares 4/8 non-colour typography names, corrected per arch-adversary C-5, but 0/13 colour names, same as fixture/lotusun-brand/lotusun-cream)."* Precisely: `deck.css` exposes **21** profile-facing names — **13 colour-bearing + 8 non-colour**. **tenuta 13/13 + 8/8. a8t 0/13 colour + 4/8 typography** (`scale.css:8,13-14,16`). **fixture, lotusun-brand, lotusun-cream: 0/13 + 0/8.** The blanket *"zero of the other four"* is **WITHDRAWN**. **The colour-collapse claim HOLDS UNCONDITIONALLY** — a8t's four shared names are typography-only and *"do not touch any colour role and do not weaken the colour-collapse claim"*. Unresolved `var()` colour references still fall back to inherited/initial values: **collapse of the intended colour relationship, not a poor ratio.** | **Every cell citing the naming finding is re-scoped to "COLOUR roles"**: K-5(b), E-1, and the a11y cells in §3/§4/§5. **CANDIDATE-DEFER-S4-06** restated. §0 finding 4 and §9.2 corrected. |
| **PL-14** | Both leg-1 and leg-2-css treat the a8 schema as **one stable contract**. | **The SOR has already drifted past the shipped tag.** `git diff --numstat v1.0.0 HEAD -- tokens.schema.json` → **122 insertions, 205 deletions**; 397 → 314 lines; the inline `definitions` block is **gone at HEAD**, restructured toward a remote `$ref` at `tokens.autom8y.dev` (S4-D-P-22/23). The vendored copy is byte-exact `v1.0.0` (13/13 files, S4-D-P-21) — so consumption is pinned while the source has moved. | **Every "share a contract" row must name WHICH contract**: `v1.0.0` inline-definitions, or SOR HEAD's remote-`$ref` form. Recorded as **CANDIDATE-DEFER-S4-03**. |

| **PL-16** | **The DELTA's own new premise, and this seat's correction of the critique that produced it.** The arch-adversary described B-8's substrate as *"the canonical `definitions` hash … checked by `sync-gate.mjs` AND `proof-sync-gate.mjs`"* — i.e. as machinery **already enforcing a shared value**. | **PROBED BEFORE AUTHORING; the description is materially wrong, and B-8 survives the correction.** (1) **Both gates hash the WHOLE FILE, not the `definitions` subtree** — each computes `sha1("blob "+len+"\0"+bytes)` over its own `dtcg-envelope.schema.json` and compares to its own `pinned_blob_sha` (S4-P-16 `sync-gate.mjs:30-33,70-72`; S4-P-17 `sync-gate.mjs:35-38,63-65`). (2) **The two pins therefore hold DIFFERENT values by construction** — a8t `0967c77d…`, a8 `f9ea4c44…` (S4-P-18) — because the whole-file bytes differ in exactly the `$id`/`title`/`description` nameplate §2.3 identified as the *only* divergence. **Each gate enforces a LOCAL invariant; neither enforces a SHARED one.** (3) **`proof-sync-gate.mjs` is NOT a second gate — it is a discriminating canary** over `tests/fixtures/sync-gate/{match,tampered,absent}` whose own comment says it deliberately **never points at `PKG_ROOT`**; a8 CI (`ci.yml:47`) runs **the canary**, not the gate against the live pin (S4-P-19). (4) **The vendored copy has no pin, no scripts and no envelope schema** — 7 entries, zero gate coverage of the artifact the producer actually consumes (S4-P-20). | **B-8's `mechanism` and `cost` cells** (§3). The §9.2(b) collapse test **fails both limbs** — the gates are *not* structurally unable (both `runSyncGate`s are exported functions with a parameterized root and a 3-line local hash, so re-pointing is an **in-place edit of existing scripts**, not a new co-owned artifact ⇒ not B-3), and WHO/cadence/revocability all change vs B-4. **So B-8 is real; the correction moves its COST, not its EXISTENCE.** |
| **PL-17** | K-6's `a8→a8t import` cell read **NONE** at leg 4, on the ground that no `import`/`require` statement is written. | **RE-READ AS PRESENT by the component-engineer seat at DELTA (C-12).** The frozen export K-6 rewrites embeds Contente's `_ds_bundle.js` **verbatim, inline** — the bundle's own marker `/* @ds-bundle: {"format":3,"namespace":"ContenteDesignSystem_9ed584",…` appears exactly once inside `export/1217867773183924.html` (S4-K-P-18). **G-29's operative text governs on its THIRD verb**: *"nothing was imported, required, or **pasted** from `~/Code/a8`"* (`deck-kit README.md:350-352`, S4-K-P-19). Read as the permanent construction strategy K-6 is authored to be, it is a **paste**. That seat's own words: *"This amendment does not soften."* | **K-6 becomes NON-VIABLE, marked exactly like E-5** (§4). Its `cost` and `forecloses` cells are **re-priced under NON-VIABLE with the original text retained as a subordinate note** — pricing implies viability. **§0, the import summary, §6's cross-product tables and §8's depth table were updated accordingly at iteration 1.** **REVERSED AT DELTA ITERATION 2 (M-1/CH-13), and the reversal is the adversary's own:** *"a re-served frozen artifact is not 'code crossing'; K-6 returns to VIABLE."* Three facts the packet already held decide it — **(a)** E-3's own import cell reads a compiled HTML artifact as *"a produced OUTPUT, neither contract nor code"* and returns NONE for the identical artifact class; **(b)** the `@ds-bundle` marker occurs once in the producer export **and once in deck-host's already-served `public/761ebfd8…/index.html`** — re-probed at this pass, both `grep -c` → `1` — so **the standing rail already carries it into an a8t tree under E-1/E-3**; **(c)** G-29 as carried in the shape speaks of **code entering a8t**, not of the brand on a served artifact. **Under the iteration-1 reading, E-1, E-3 and the nine live slugs would all be NON-VIABLE — the packet cannot hold both.** The load-bearing objection to a permanent K-6 is the one the row already states: **legacy-floor §2 REFUSAL** (INHERITED construction — a POSITIVE result) plus the INV-11 silent-gap hazard. **The component-engineer seat's PL-17 reading is retained above as CONTESTED; the operator rules.** |

### §1.1 Drift ledger, carried forward unchanged (D-1 … D-4)

Re-probed 2026-09-05 by the dispatcher; **frame anchors preserved beside them**. This
packet does not edit the frame.

- **D-1** — frame pin `@a8t/deck-kit @ bfc2f41` (G-24) **still resolves**; branch has advanced to `d8c7794` on `feat/dk-001-dk-005-render-check-and-negative-fixtures`, `bfc2f41` still ancestor. DK-001/DK-005 landed; DK-002/003/004 **remain SKETCH**. **Cite `bfc2f41` as THE pin; never read the newer state as the ruled substrate.** Corroborated three ways (S4-P-6, S4-E-P-2, S4-K-P-14). Consequence: an F-ENGINE option premised on *"deck-kit is a fixture-gate prototype"* is **stale** — the readiness gate is now CI + opt-in render check + negative fixtures. **Countervailing, and priced:** the same delta is a maturity **ceiling** for what has NOT landed (UV-P-S4-E-1).
- **D-2** — superseded in its operative clause by **PL-01/PL-02/PL-05**. What still holds: the vendored artifact **is** a publish-shaped artifact produced by dependency resolution, not by hand (S4-D-P-05/11), and it **is** git-tracked (`git ls-files --error-unmatch` exit 0; 13 tracked files under the package, 190 under `vendor/deck-producer/node_modules`).
- **D-3** — frame cited `_ds_manifest.json` at `templates/*/`; it is at `vendor/deck-producer/_ds_manifest.json` — **ONE file, producer-wide** — carrying `"namespace":"ContenteDesignSystem_9ed584"` and 11 components (S4-P-4, S4-K-P-4). **The claim holds; the path does not.** Consequence, carried per-row in §4: **per-profile templating buys NO namespace isolation.**
- **D-4** — the a8t exhibit contract holds **24** entries (not 23), key `ex` (not `id`), all grade `OBSERVED` (S4-K-P-16). **Context only; S6 owns it.** Not load-bearing on any option in this packet.

---

## §2 THE THREE AXES, THE ROW SCHEMA, AND G-15 RESTATED

### §2.1 The axes, verbatim

**Axes precede options by design.** `option-enumeration-discipline` §3 names the failure:
a slate whose options *"all share the same primary mechanism category"* is a
mechanism-category blind spot, and sequential labelling makes a truncated slate look
complete because *"completeness is a structural property of the options, not a property
of the labeling"* (§5). An option that cannot be placed at a **distinct position** on its
fork's axis is a parametric variant, not a structurally distinct option.

**F-BRAND**
> **THE LOCUS OF AUTHORITY over the token contract that both engines must honour: which
> artifact, in which repo, is the source of record — and therefore WHO can unilaterally
> change the contract, on whose cadence, with what revocability.**

Positions occupied, each exactly once — including **the pinned canonical value (B-8)**: nobody-and-nothing-said (**B-0**) · a8t (**B-1**) ·
a8 (**B-2**) · joint/third (**B-3**) · nobody-but-named (**B-4**) · nobody-and-ruled-so
(**B-5**) · the serving predicate (**B-6**) · external to both repos (**B-7**).

**F-DECK**
> **THE ARTIFACT AT WHICH PROFILE-VARIANCE IS FIRST ADMITTED: which single layer of the
> deck's construction stack — design-system namespace / component set / template / render
> invocation / post-render projection — is the FIRST layer that differs between two
> profiles. Choosing a layer makes that layer and every layer DOWNSTREAM of it per-profile
> by consequence; every layer UPSTREAM of it remains shared by consequence.**

**VERTICAL CONVENTION — corrected at DELTA (C-3/CH-03), stated once, binding on every
K-row.** The prior wording read *"every layer ABOVE … per-profile; every layer BELOW …
shared"*, which **inverts** against K-2 and K-5: three sentences in the packet were
carrying **two incompatible vertical metaphors** for one load-bearing consequence rule.
**The five layers are listed in CONSTRUCTION ORDER, earliest first.** `design-system
namespace` is the most **UPSTREAM**; `post-render projection` the most **DOWNSTREAM**.
*Above* and *below* are **retired** from this axis. Checked against the rows it governs:
**K-2** (most upstream) makes all four downstream layers per-profile — hence "most
expensive by construction"; **K-5** leaves namespace, component set and template shared;
**K-6** (most downstream) leaves all four upstream layers exactly as shared as D-3 finds
them. **D-3's frame text is quoted verbatim elsewhere and uses the opposite vertical
sense** (*"leaves the layer BELOW it shared"*, where *below* = namespace = **upstream**
here) — the quote is preserved unaltered; apply this gloss to it.

"One template vs five templates" is a **count** and therefore parametric; naming a
different **layer** is categorical.

**F-ENGINE**
> **THE KIND OF OBJECT THAT CROSSES the a8→a8t boundary in order for a given profile to be
> rendered: nothing / a declarative artifact contract / a produced artifact / a running
> process's output / source code.**

Naming an engine is **not** a position on this axis — it is a consequence of one.

**DIRECTION — CORRECTED AT DELTA (C-2/CH-02; this is the §5-head sentence, copied here so
the axis statement and the slate agree).** Direction is load-bearing at **two** positions,
for **two different reasons**: at **source code (E-5)** it decides **VIABILITY** — a8→a8t
is NON-VIABLE, a8t→a8 is not fenced by G-29; at **declarative contract (E-2)** it decides
**COST and GOVERNANCE** — **a8t→a8 is the direction G-29 is SILENT on** (a gap, priced,
never a permission this packet grants), while **a8→a8t is the direction G-29 EXPLICITLY
PERMITS** (*"contracts may be shared"*, shape `:1183`). Direction still does **not mint an
axis position**, which is exactly why E-2 is split into **labelled sub-rows**.

### §2.2 The row schema — EXPANDED per PL-03, binding on every row

```
| mechanism | what it costs | what it forecloses | a8→a8t import: NONE|PRESENT |
| contract-change mechanism: file-edit | git-tag+re-vendor |
                             in-place-vendored-patch (ungated) | none |
| INV-11/17/19 disposition | a11y consequence | dissent |
```

**Per-fork additions** (each fork's rows carry one extra line): B-rows carry a
**CSS-emission consequence**; K-rows carry a **D-3 namespace-cost** line; E-rows carry a
**C9 collision** line.

| Column | Rule |
|---|---|
| **mechanism** | The option's **axis position**, not its benefit. |
| **what it costs** | Engineering AND governance; cites the §2.4 fix ids (F1..F5) it requires. |
| **what it forecloses** | What the operator can no longer choose after the door closes. A one-way door foreclosing nothing is mis-classified. |
| **a8→a8t import** | `NONE` or `PRESENT`. **`PRESENT` ⇒ NON-VIABLE, not costly** (G-24/G-29) — *pricing implies viability*, so a `PRESENT` row's cost and forecloses cells are re-framed, not weighed. **Exactly one row carries it: E-5.** **Rider, scoped to SOURCE (leg 5, DELTA):** G-29's operative text has three verbs — *"imported, required, or **pasted**"* (`deck-kit README.md:350-352`, S4-K-P-19) — and its referent is **deck-kit's own source** (*"`src/engine.js` and `src/deck.css` are independent implementations"*). It does **not** classify a re-served produced artifact by the brand it carries; E-3's own cell reads a compiled HTML artifact as *"a produced OUTPUT, neither contract nor code"* (:797). |
| **contract-change mechanism** | Four values per PL-03. **`in-place-vendored-patch (ungated)` is named wherever it is structurally available**, because no gate detects it (S4-D-P-10/14/28). |
| **INV-11/17/19 disposition** | Required on every row. The S3 fence is **RAIL-SCOPED** and by design **REFUSES a legitimate non-Contente deck** (INV-11 template absent from the pinned producer map; INV-17 zero routing addresses; INV-19 no `<x-dc>` region). `NOT ENGAGED` is a legitimate disposition but must be **stated**. `config/producer-audience-map.json` holds exactly **two** templates, so a new `deck_template` **DEFAULT-DENIES** (DEFER-2026-W1-007; S4-P-5, S4-K-P-1). |
| **a11y consequence** | **VERBATIM EXCERPTS from the a11y leg's 20 rows**, carried from that leg's own **§F CARRIAGE MANIFEST** (20 blocks × 8 lines), never paraphrased. **EXCERPT RULE, stated once at DELTA (C-8/CH-08):** every quoted fragment is a **literal substring** of the source cell, **cut only at a clean word/markdown boundary**, with `[…]` marking a truncation. Bullets are flattened to a single cell and separated by `·`; quote marks are normalised. **Dark-mode and Print bullets are RESTORED** — the leg-4 synthesis silently dropped them from several cells, plus one K-1 print fragment. The full paragraph in the a11y leg's §B is the authoritative source if more depth is wanted. WCAG approaches remain a11y-engineer's; these are token-layer consequences, flagged not ruled. |
| **dissent** | Where a leg self-authored one it is carried. **Every row additionally carries an EMPTY labelled leg-5 slot** — the arch-adversary's, filled at leg 5 for 19 rows; B-8 and E-2(ii) reserved (DS-6), filled at DELTA iteration 2. |

**There is NO "recommended" column and none may be added.** Ranking is the operator's at
DP-1; a slate that ranks is *"a recommendation wearing a slate's costume"* (shape PT-04).

### §2.3 G-15 RESTATED — the KIND/ALTITUDE asymmetry, now fully resolved

The frame read G-15 as a **value** difference (`fba8476c` vs `e15ea4db`). Three legs have
now resolved it completely.

| | a8t `envelope/dtcg-envelope.schema.json` | a8 vendored `tokens.schema.json` (`v1.0.0`) | a8 SOR `dtcg-envelope.schema.json` (HEAD) |
|---|---|---|---|
| **Kind** | leaf-**SHAPE** contract | key-**TREE** + inline leaf-shape | leaf-**SHAPE** contract |
| **Whole-file sha256** | `fba8476c…` | `8f913ecc…` | **`e15ea4db…`** — the frame's second hash, **RESOLVED** (PL-04) |
| **Root assertion keywords** | none (`definitions` only) | `type`/`properties`/`required`/`additionalProperties` | none |
| **`definitions` canonical sha256** | **`8831da27…`** | **`8831da27…`** | **`8831da27…`** |
| **Repo role** | source of record | **git-tracked vendored artifact**, byte-exact to tag (13/13, S4-D-P-21) | source of record |

**Plus a fourth copy:** fe-skeleton `origin/main` — the **common ancestor** — also
`8831da27…` (S4-D-P-34). **FOUR byte-identical copies across THREE organizations.**

**What does not differ.** At leaf altitude, **nothing**. Same 9 types (`border, color,
cubicBezier, dimension, duration, fontFamily, fontWeight, number, shadow`), identical
shapes; all five a8t profiles use exactly those 9 and no others (S4-P-10/11, S4-D-P-34).
The wrappers differ only in `$id`/`title`/`description` (S4-D-P-35). **The contract's
substance is identical; only its nameplate differs.**

**What does differ**, at three altitudes: **key namespace** (Contente's 15 groups /122
leaves vs a8t per-profile 44-63, three group names coinciding); **expression mechanism**
(nested draft-07 `properties` tree vs flat `required_key_paths` + `leaf_types` +
`$envelope_ref` URN, all non-standard keywords); **enforcement locus** (schema-bound vs
**tool-bound** via a bespoke zero-dep validator) — and now, per **PL-12**, a fourth:
**on the a8 side there is no build-time schema consumer at all.**

**SLOT B, re-posed and annexed (never substituted).** The shape's verbatim Q2 stands:
*"What reconciles the two DTCG envelope schemas (fba8476c vs e15ea4db, G-15) — or is the
divergence itself the ruling?"* The re-posed form asks first **which pair**: (a)
envelope-to-envelope — **both now exist and their `definitions` are identical**, so
"reconcile" means reconcile two nameplates; (b) envelope-to-package-tokens — different
kind at different altitudes, so "reconcile" means **decide which altitude the shared
contract lives at**; (c) neither — the divergence is the ruling. **The operator rules the
form (SLOT B); see the PL-09 warning.**

### §2.4 What a shared contract must fix — F1..F5, RE-PRICED

| # | Fix | Cost, re-priced against §1 |
|---|---|---|
| **F1** | **Nothing, at leaf altitude.** Already identical **four ways** (S4-D-P-34). | **Zero engineering.** Cost is purely governance: naming a governor for a surface that has none, converting a **convergent inheritance from a common ancestor** into a commitment. Each side pins only **its own** copy; **no guard spans the pair** (S4-D-P-25/38). |
| **F2** | **Expression mechanism** — one side adopts the other's, or a third. | High, asymmetric, **unchanged** by §1. a8t→nested-draft-07 loses set-equality (a **detection regression**; the shape floors evidence quality at "may never REGRESS"). a8→flat-path is a `git-tag+re-vendor` round-trip plus a new validator on a side that **has no validator today** (PL-12). |
| **F3** | **Key namespace** — a shared vocabulary across two disjoint vocabularies. | Highest. 122 Contente leaves; 44-63 per a8t profile; plus each profile's `css/` projection and `projection.config.mjs`. **Re-priced DOWN on one leg and UP on another**: the a8-side leg is `git-tag+re-vendor` by one operator, not a multi-party publish (PL-01) — cheaper than stated; but **no build-time consumer exists to enforce the result** (PL-12) — so the fix buys less enforcement than stated. |
| **F4** | **Enforcement locus** — one validator, or a declared two-validator regime. | Moderate, structural. **Re-priced UP:** the a8 side has **zero** enforcement at the consumption site today (PL-12), so "two validators" is aspirational — it is currently **one validator and one absence**. |
| **F5** | **The change-authority asymmetry.** | **RE-NAMED per PL-02.** Not actor-vs-actor. It is **legitimating-change vs silent-edit**, with **no mechanism distinguishing them**. Still paid forever; the price is not a slower actor but an **undetectable fork**. |

---

## §3 F-BRAND — THE OPTION SLATE (SLOT A)

**Axis:** locus of authority (§2.1). Nine options, each at a distinct position.

**Slate composition against `option-enumeration-discipline` §5:** ≥3 structurally distinct
→ **9** (B-0..B-8); one requiring no new mechanism (the null) → **B-0** *(corrected per
PL-08; B-4 re-labelled)*; one not the author's first instinct → **B-6**; a delegation
option → **B-7**; data-driven option → **n/a**, this fork mints no classification.

**THIS SLATE HAS BEEN EXTERNALLY AUDITED FOR COMPLETENESS AND ONE OPTION WAS ADDED.**
The rite-disjoint arch-adversary's pre-merit enumeration audit (leg 5, iteration 1) found
one structurally distinct class the slate had not enumerated — **content-addressed
authority** — and returned **BLOCK** on `option-enumeration-discipline` §6 step 3
grounds. **B-8 is that option, added at full depth and evaluated with identical
methodology** (§4 Step 3). The leg-1 seat's own §5.3 self-audit had listed the substrates
it considered as carriers and **the pin/sync-gate pair was not among them**, despite that
leg having read and cited a pin file at S4-P-2. **Recorded as a hit, not smoothed over.**

**Collapse test carried forward (subtractive §B.1), named by B-7's own author:** **B-7 ⇄
B-4** collapse if the distinguishing test answers NO. **The test: is a DTCG conformance
validator ever actually built (F4 work)?** If NO, B-4 and B-7 are mechanically identical —
an unenforced coincidence, differently narrated. If a validator is built, B-7 gains teeth
B-4 structurally cannot have. **Under present conditions the answer is NO** (nobody is
scheduled to build one), so **this is a live collapse candidate.** **B-0 is distinct from
both**: it writes no sentence at all.

**B-4 vs B-5 re-tested and found DISTINCT** (subtractive §B.1): *does an a8t leaf-type
change tomorrow count as drift (an obligation broken) or correct behaviour (no obligation
existed)?* B-4 → drift; B-5 → correct by construction. The test is articulable and holds.

---

### B-0 — DO NOTHING; RECORD NO CONTRACT  **[TRUE NULL — added at leg 4 per PL-08]**

| Column | |
|---|---|
| **mechanism** | The operator closes the door by **declining to constitute any authority and writing no ratifying sentence**. The four-way-identical leaf layer (`8831da27…`, S4-D-P-34) is recorded as **a fact, not a contract**. Axis position: **nobody, and nothing said.** |
| **distinct from B-4 and B-5** | **B-4** performs the smallest possible governance act (a ratifying sentence naming the shared surface). **B-5** performs a **foreclosure** (rules future reconciliation out permanently). **B-0 performs neither**: no sentence, no obligation, no foreclosure — and therefore, uniquely, **leaves B-1/B-3/B-4/B-6/B-7 fully available later at unchanged cost**. |
| **what it costs** | **Zero engineering, zero governance, zero sentences.** The only cost is **optionality forgone in the present tense**: a future consumer asking "what contract do the two sides share?" is answered "none has been declared" rather than "the leaf layer, ungoverned." |
| **what it forecloses** | **Nothing — and that is the finding, not the evasion.** It is the only row in the slate that forecloses nothing at all. **This is also the sharpest objection to it as a DOOR ruling**: a one-way door whose chosen option forecloses nothing may be mis-classified as a door. Stated so the operator sees it before ruling, not after. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **none.** The only row in the slate taking on no change mechanism of any kind, on either side — because there is no contract to change. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** No deck is produced or routed by this option; the rail-scoped invariants evaluate nothing. |
| **a11y consequence** *(verbatim excerpt, a11y leg B-0, `318-336`)* | **Where decided**: “Exactly where it is decided today — per-profile CSS authoring, independently. B-0 takes LESS action than B-4: B-4 at least ratifies the leaf identity in a sentence; B-0 does not even do that. Contrast stays fully unaddressed at every altitude, identical to B-4/B-5's finding.” · **Enforce**: “Neither side names anything to enforce — but "neither side enforces" is not the same claim as "the surface is ungoverned." **Both repos already carry an independent pin file + CI sync-gate for this exact envelope**: `brand-tokens/envelope/dtcg-envelope.pin.json` (pinned against a8t's own […]” · **Palette-swap silent-fail**: “**YES**, identical structural reason to B-4/B-5, with a sharper edge specific to B-0. Both pin/gate pairs watch **whole-file blob drift** (leaf-shape schema drift) — neither SHA is computed over anything at CSS altitude, so a primitives.css hex edit is invisible to both gates, exactly as under […]” · **Required constraint if built**: “None possible under B-0's own construction — a stricter NULL than B-4. If the operator wants the two EXISTING pin/gate pairs to cross-check EACH OTHER (not merely their own blob), that is new mechanism: a THIRD check comparing the two pins' resolved content, not merely bigger versions of the two […]” · **Dark-mode**: “Unaffected; parity-by-absence continues, identical to B-4/B-5.” · **Print**: “Unaffected, identical to B-4/B-5.” |
| **CSS-emission consequence** | **Nothing re-emits, either side.** B-0 is below even JSON-schema altitude; CSS is canonical and JSON is generated on both sides (S4-C-P-1/2), so no ruling here reaches any CSS byte. |
| **dissent (leg-1 convention: self-authored)** | It answers a one-way door with silence, and a door that forecloses nothing is arguably not a ruling at all — the operator may be recording a non-event and calling it a decision. It also **declines a zero-cost asset**: the leaf identity is free today (four ways over), and B-0 neither governs it nor even names it, so a future reader has no artifact telling them the identity was ever noticed. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:223` — 100w, VERBATIM)* B-0 records a four-way identity as "a fact, not a contract" while both repos already carry a pin file and a CI sync-gate for that very envelope (`brand-tokens/envelope/dtcg-envelope.pin.json`; `contente-tokens/dtcg-envelope.pin.json`). Saying nothing does not leave the surface ungoverned — it leaves it governed twice, separately, by machinery that will fire on the next nameplate edit with no shared account of what fired. B-0 also forecloses nothing, which its own row concedes may disqualify it as a door ruling; a one-way door answered with silence is a deferral wearing a ruling's label, and the honest form of that is "none", not B-0. |

---

### B-1 — a8t-SOVEREIGN ENVELOPE

| Column | |
|---|---|
| **mechanism** | Declare a8t's `urn:a8t:brand-tokens:dtcg-envelope:1` the sovereign **leaf-shape** contract for both sides; the a8 side is required to reference/conform to it. Axis position: **a8t.** |
| **what it costs** | **F1** (governance) + **F5** (re-named per PL-02) + part of **F4**. Engineering at leaf altitude is **near zero** — identical four ways (S4-D-P-34). **RE-PRICED (PL-01):** the a8-side conformance step is **not** an upstream publish; it is **one commit + one git tag + one re-vendor commit, all by the same operator** — materially cheaper than the slate carried. **RE-PRICED UP (PL-12):** there is **no build-time schema consumer on the a8 side**, so conformance buys **no build-time enforcement** — the only live guard is the SOR's own `generate.mjs --check`, which the vendored copy cannot run (S4-D-P-05). |
| **what it forecloses** | B-2, B-3, B-7 (authority settled on a8t). Forecloses a8t adding a 10th leaf type without a cross-repo event. Does not foreclose F2/F3 later — **which is why the door may be larger than the option's text**. |
| **a8→a8t import** | **NONE** — a schema is a contract; contracts may be shared (shape §7 Prescribed). |
| **contract-change mechanism** | **file-edit** (a8t: edit + re-pin `dtcg-envelope.pin.json`, CI sync-gate RED on drift) **+ git-tag+re-vendor** (a8 side, PL-01) **+ in-place-vendored-patch (ungated)** — structurally available and **undetected by any gate** (PL-02, S4-D-P-10/14/28). |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** A leaf-type contract routes no deck onto the Contente rail. |
| **a11y consequence** *(verbatim excerpt, a11y leg B-1, `:285-301`)* | *"**Where decided**: Nowhere new. Leaf-shape/type governance (`{$type,$value}`) says nothing about which hex a profile author picks; contrast stays decided at CSS-authoring time, per-profile, exactly as measured in §A today. **Enforce**: Neither side — no leaf-shape validator inspects a color relationship. **Palette-swap silent-fail**: **YES.** Leaf-shape governance never compares a foreground to a background; any conformant hex passes regardless of what it is paired with. **Required constraint if built**: None contributed by B-1 itself; a fix would require F3 (purpose-level required keys) or CSS/served-bytes altitude work B-1 does not do."* · **Dark-mode**: “None — leaf-shape has no color-scheme axis; parity-by-absence (css draft E4) unaffected.” · **Print**: “None — B-1 doesn't touch print CSS; the structural-only `deck.print-one-slide-per-page` check and its silence on paper-media focus indicators (paper has no `:focus-visible`) are untouched either way.” |
| **CSS-emission consequence** *(css leg §C B-1)* | **Nothing re-emits, either side** — leaf-shape governance is JSON-altitude and the pipeline runs CSS→JSON. **Zero CSS bytes move.** hex-free coverage **A8T-ONLY**, unchanged; scoping collision (`--space-4`) **UNCHANGED**. |
| **dissent (leg-1, self-authored)** | It **ratifies a coincidence as a commitment while buying nothing that is not already true**; the leaf layer is identical today at zero cost, so B-1's entire delta is obligation. If the intent is to make F3 reachable later, the door actually being ruled is bigger than the option's text. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:227` — 107w, VERBATIM)* B-1 declares a8t's envelope sovereign over a side that cannot enforce it: PL-12 shows the producer never reads any schema, and PL-02 shows the vendored copy can be forked in one file edit no gate detects. Sovereignty without a consumer is a sentence, not a contract — B-1's entire delta over B-4 is the obligation it imposes on a8 plus the a8t-only sync-gate a8t already runs. Its foreclosure cell admits the door "may be larger than the option's text" (F2/F3 later); an option that cannot state its own foreclosure boundary is not rulable as a one-way door, and the operator would be signing a blank second page. |

---

### B-2 — a8-PACKAGE-SOVEREIGN

| Column | |
|---|---|
| **mechanism** | Contente's `tokens.schema.json` (122 leaves, 15 required top-level groups) is the contract; the five a8t profiles conform to its key tree. Axis position: **a8.** |
| **what it costs** | **F2 + F3 + F4 + F5, at maximum.** Rewrite all five a8t profile schemas; retire the flat `required_key_paths` mechanism and its zero-dep validator; adopt nested draft-07. a8t's own vocabulary (`emphasis`, `leading`, `size`, `weight`) is **deleted**; per-profile leaf counts move 44-63 → 122. **RE-PRICED (PL-14): the option must first name WHICH contract** — `v1.0.0`'s inline-`definitions` form (what is vendored) or SOR HEAD's remote-`$ref` form (122 insertions / 205 deletions past the tag, `definitions` block **gone**). These are different contracts and the slate treated them as one. |
| **what it forecloses** | Everything else on the axis, and **permanently forecloses profile-local key sets** — the property `brand-tokens` states as its design centre. Forecloses non-Contente brand vocabularies as a class. |
| **a8→a8t import** | **NONE** — adopting a schema is adopting a contract, not importing code. **This row is where the contract/code line is thinnest**: a8t's contracts are tool-enforced, so adopting Contente's schema means adopting **draft-07 validation semantics**. Flagged in dissent; **not ruled here.** |
| **contract-change mechanism** | **git-tag+re-vendor** (the contract lives on the a8 side) **+ in-place-vendored-patch (ungated)**. **RE-PRICED (PL-01/PL-02):** the slate read this as "upstream-publish only, a8t holds no file-edit path." Corrected: it is a same-operator tag round-trip, and an **ungated in-place fork of the vendored bytes is available to anyone with write access to `autom8y-asana`** — so a8t's dependence is on **convention, not on a gate**. |
| **INV-11/17/19 disposition** | **NOT ENGAGED at token altitude.** **Named hazard:** this is the option that most invites a follow-on where a8t decks render through the Contente producer. **If that follow-on is taken, all three ENGAGE and all three currently REFUSE** a legitimate non-Contente deck; a new `deck_template` **DEFAULT-DENIES** (S4-P-5, S4-K-P-1). This option does not take that follow-on and **must not be read as having dispositioned it**. |
| **a11y consequence** *(verbatim excerpt, a11y leg B-2, `:302-323`)* | *"**Where decided**: At the JSON-schema-CONFORMANCE layer, for the key's EXISTENCE only — not at CSS-authoring, where the actual hex is still chosen freely… a required KEY can be satisfied by an unrelated existing CSS declaration or a dummy value added solely to pass… **Enforce**: a8's build … can enforce KEY PRESENCE. **Neither** side's build enforces VALUE CONTRAST… **Palette-swap silent-fail**: **YES**, and the sharpest form in the slate — B-2 supplies FALSE CONFIDENCE: 'the key exists' reads as 'accessible' but is not the same claim. **Required constraint if built**: A VALUE-level check (contrast computed against the paired background token) added separately — JSON Schema key-presence cannot express a contrast predicate; this is a structural, not an effort, gap."* · **Dark-mode**: “None — Contente's 122-leaf schema has no color-scheme-conditional leaf type; parity-by-absence continues.” · **Print**: “None — B-2 is JSON-altitude; the print/focus gap travels unaddressed.” |
| **CSS-emission consequence** *(css leg §C B-2)* | **Not the CSS files — the projection configs.** Each profile's `projection.config.mjs` re-targets `namespaceRules`/`aliasGroups`/`typeRules`; the human-authored CSS custom-property NAMES can stay as authored. **Materially cheaper at CSS altitude than the JSON-altitude "rewrite 5 schemas" cost implies.** |
| **dissent (leg-1, self-authored)** | `legacy-floor-isolation` **fires as REFUSAL.** Contente is a **FLOOR and a REFERENCE — never a BENCHMARK to match nor an IMPLEMENTATION to inherit**; adopting its key tree as a8t's contract is the textbook **INHERITED** disposition. **The refusal is a positive result, not a stall.** The correct handling of B-2's a11y advantage (Contente requires `color.focus.ring`) is to **re-derive it at a higher bar** — require a focus token because WCAG 2.2 requires focus visibility — **not to inherit it** because Contente happened to have one, which drags the whole 122-leaf premise along. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:231` — 103w, VERBATIM)* B-2 inherits Contente's 122-leaf key tree as a8t's contract — the textbook INHERITED disposition under legacy-floor-isolation §2, whose REFUSAL is a positive result. Worse, PL-14 shows there is no single "a8 contract" to adopt: the vendored v1.0.0 carries inline definitions; the SOR at HEAD has deleted them for a remote $ref whose resolvability is unprobed (UV-P-pub-1). B-2 therefore binds five profiles to whichever of two diverging artifacts the operator happens to name, deletes a8t's own vocabulary, and buys key-presence checks the a11y leg shows produce false confidence. It is the most expensive row and the only one that permanently forecloses profile-local key sets. |

---

### B-3 — THIRD SOVEREIGN ARTIFACT (joint authority)

| Column | |
|---|---|
| **mechanism** | A new contract artifact owned by **neither engine's repo**, co-signed, that both sides conform to. Axis position: **joint.** |
| **what it costs** | **F1 + F2 + F4 + F5.** Process cost highest in the slate: a new artifact, a new home, and a **governance body that does not exist**. **RE-PRICED (PL-01):** the "two-party coordination" premise weakens — there is **one operator** with commit rights on all four repos (S4-D-P-24), so "joint authority" would be a **self-imposed procedural constraint**, not a negotiation between parties. That makes it cheaper to establish and **correspondingly easier to abandon silently**. |
| **what it forecloses** | Unilateral change by **either** side; fast iteration on both; a8t's stated envelope sovereignty and Contente's package self-containment simultaneously. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **file-edit** (third artifact) **+ git-tag+re-vendor** (a8 re-conformance) **+ in-place-vendored-patch (ungated)**. All three legs present; none sufficient alone. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** Routes no deck onto the Contente rail. |
| **a11y consequence** *(verbatim excerpt, a11y leg B-3, `:324-341`)* | *"**Where decided**: Wherever the joint artifact's (unbuilt) authors choose — F3-altitude IF they choose purpose-level required keys, but the option's own text does not decide this… **Enforce**: Whichever side implements the joint artifact's own validator — unbuilt, ungoverned… **Palette-swap silent-fail**: **YES**, for B-2's structural reason PLUS an enforcement gap: even if a contrast rule were authored, no standing body executes anything at the joint altitude… **Required constraint if built**: A new validator, on a new artifact, with a new governance body — three new things, not one."* · **Dark-mode**: “Unset by the option, same gap as contrast.” · **Print**: “Unset by the option, same gap.” |
| **CSS-emission consequence** *(css leg §C B-3)* | **Nothing re-emits automatically, either side.** Scoping risk **UNCHANGED unless** the third artifact is separately given an opinion on CSS scoping — **B-3's mechanism as stated has none; this is a gap in the option.** |
| **dissent (leg-1, self-authored)** | **There is no third repo, no governance body, and no forum.** New mechanism the problem has not earned. It carries **all of F5's cost with none of F5's clarity**: with a co-signed artifact and a tag round-trip on one side, "who is accountable when conformance breaks" has no answer, whereas under B-1 or B-2 it plainly does. Joint authority over a surface identical for free is ceremony purchased with coordination cost. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:235` — 106w, VERBATIM)* B-3 creates a third artifact, a third home and a governance body for a surface already byte-identical four ways and governed by one human. PL-02 collapses "joint authority" into a self-imposed procedure the same operator can abandon silently — the row admits this. It inherits all three change legs (file-edit, tag+re-vendor, ungated in-place patch) with none sufficient alone, so it maximises coordination cost while leaving the undetectable-fork problem exactly where it was. Its CSS-emission cell concedes it has no opinion on scoping. B-3 is ceremony that purchases accountability ambiguity: when conformance breaks, nobody's repo is at fault, and the "body" that would adjudicate does not exist. |

---

### B-4 — SHARE A CONTRACT, UNIFY NOTHING  **[MINIMAL GOVERNANCE ACT — re-labelled from `[NULL]` per PL-08]**

| Column | |
|---|---|
| **mechanism** | **Ratify** the leaf layer that is already byte-identical (`8831da27…`, four ways) as the **entire** shared surface. Key trees remain profile-local and brand-local **by construction**. Axis position: **nobody — shared by identity, governed by no one, but NAMED.** |
| **why the label changed** | Its own cost cell reads *"one sentence of ratification"* — **an authored act that did not exist before it is written**. An independently-drafted do-nothing null contains no such sentence (subtractive §A.1). B-4 is the **cheapest possible governance act**, one rung above nothing. **B-0 is the true null.** |
| **what it costs** | **F1 only; F1's engineering cost is zero.** The cost is one sentence. The governance cost is **deliberately not taken**: no governor is named, so the sharing stays a **described fact**, not an enforced commitment. |
| **what it forecloses** | Little. It forecloses later claiming a shared contract was never available. Does **not** foreclose B-1, B-3, B-6, B-7 as a subsequent step. **Does** foreclose B-2 rhetorically. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **file-edit** (a8t side only). **The only option besides B-0 and B-5 with no a8-side leg** — the a8 side takes on no obligation. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** |
| **a11y consequence** *(verbatim excerpt, a11y leg B-4, `:342-358`)* | *"**Where decided**: Exactly where it is decided today — per-profile CSS authoring, independently. Tenuta's own `semantic.css:9-18` is the only profile documenting its own contrast math in a comment. **Enforce**: Neither side — B-4 takes on no governance by its own construction. **Palette-swap silent-fail**: **YES**, unconditionally… nothing in B-4 would notice a profile's primitives.css hex edited to a lower-contrast value. **Required constraint if built**: None possible under B-4's own construction — there is no shared surface to attach a constraint to."* · **Dark-mode**: “Unaffected; parity-by-absence continues.” · **Print**: “Unaffected.” |
| **CSS-emission consequence** *(css leg §C B-4)* | **Nothing re-emits.** hex-free coverage **A8T-ONLY** and **stays** so — B-4 takes on no governance, so it can never be the option that closes the enforcement-parity gap. The **`--space-4` bare-name collision is exactly as ungoverned at CSS altitude** as the leaf identity is at JSON altitude. |
| **dissent (leg-1, self-authored)** | It **answers the door with "the door was already open."** Sharper: **an ungoverned shared surface can drift silently.** `dtcg-envelope.pin.json` pins the a8t envelope against **itself**; **nothing pins it against Contente** — and per S4-D-P-25/38 each side pins only its own copy, so **no guard spans the pair**. a8t may add a 10th leaf type tomorrow and **no gate anywhere fires**. B-4 buys its cheapness by declining the one mechanism that would notice it stopped being true. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:239` — 102w, VERBATIM)* B-4 ratifies an identity and then declines the one act that would notice the identity ending. Both repos already run a sync-gate against a pin (`scripts/sync-gate.mjs`; `scripts/proof-sync-gate.mjs`), each pinning a different blob; B-4 leaves that pair unspanned by choice. Its own dissent concedes a tenth leaf type fires no gate anywhere. The B-7⇄B-4 collapse test cuts against it too: absent a validator, B-4 and B-7 are the same unenforced coincidence differently narrated — so B-4 is not a distinct commitment, it is B-7 without the external dependency. Ruling B-4 is ruling that the four-way identity is worth one sentence and nothing else. |

---

### B-5 — NO RECONCILIATION; THE DIVERGENCE IS THE RULING

| Column | |
|---|---|
| **mechanism** | Rule that there is **no shared token contract at any altitude**; the two systems are permanently unrelated; DP-1's schema commitment is answered **"no commitment."** Axis position: **nobody, and nothing shared.** |
| **distinct from B-4 and B-0** | **B-4** ratifies the identity (describes and blesses it). **B-5** rules it **incidental and obligation-free** — a8t may change a leaf type tomorrow with no cross-repo event and that is **correct behaviour, not drift**. **B-0** does neither and **forecloses nothing**; B-5 **forecloses permanently**. Three distinct answers to *"is there a shared contract at all?"* — no / described / ruled-never. |
| **what it costs** | **Zero engineering, zero governance.** The cost is **optionality**: any future need to move an artifact between the systems is paid **per case, at full price**, because no shared surface accumulates. **RE-PRICED (PL-04):** B-5 now rules against an identity confirmed **four ways across three organizations**, descended from a **common ancestor whose own commit subject names the relationship** (*"single-owned leaf-shape envelope + Contente parity gate"*). Declining is still available; it is declining **more** than the slate knew. |
| **what it forecloses** | **The sharpest foreclosure in the slate.** It forecloses the third branch of the shape's own Q1 — *"or both under a shared contract"* — as an answer to F-ENGINE. Does **not** foreclose either engine rendering either profile via a **non-schema** crossing. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **file-edit**, each side independently — there is no shared contract to change. No a8-side leg, for a **different reason** than B-4: under B-4 the a8 side has no obligation; under B-5 there is no contract to have one to. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** |
| **a11y consequence** *(verbatim excerpt, a11y leg B-5, `:359-374`)* | *"**Where decided**: Per-profile, permanently, by ruling. **Enforce**: Neither side, permanently, BY DESIGN — B-5 forecloses ever building a SHARED contrast obligation (either side may still build one unilaterally…). **Palette-swap silent-fail**: **YES**, permanently — with no shared contract at any altitude there is no seam at which a cross-profile check could even be proposed as an obligation. **Required constraint if built**: None possible under B-5's own axis position — a structural NO, not a missing item."* · **Dark-mode**: “Permanently parity-by-absence; no shared surface will ever require it.” · **Print**: “Permanently unaddressed by any shared mechanism; each side's print CSS (`deck.print-one-slide-per-page` on the a8t side) stays exactly as-is, unilaterally.” |
| **CSS-emission consequence** *(css leg §C B-5)* | **Nothing re-emits, by construction, forever** — and at CSS altitude this is **already today's status quo**: no shared scoping, no shared hex-free check, no shared namespace exists today either. hex-free coverage **A8T-ONLY permanently, by ruling.** |
| **dissent (leg-1, self-authored)** | It makes the epoch's throughline harder at the margin: *"designed once, rendered per brand profile"* is a **sharing** claim, and ruling that nothing is shared moves the entire burden onto the render layer with **no token-layer support underneath**. It **discards a zero-cost asset** — now known to be free **four ways over**. |
| **counter-dissent (leg-1, for depth symmetry)** | The identity is free **precisely because it is ungoverned**; governing it *is* the cost (B-1, B-3), and B-5 is the only option that declines to pay a recurring price for a benefit already enjoyed de facto. Its a11y weakness is also **honest**: B-0, B-4 and B-7 deliver the same zero a11y outcome while sounding as though a contract exists. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:243` — 110w, VERBATIM)* B-5 permanently rules unrelated two systems that descend from one ancestor, share one operator, and carry byte-identical definitions in four places — it declines more than any prior slate knew (PL-04). It forecloses the shape's own Q1 third branch ("both under a shared contract") and, by the a11y leg's verbatim finding, forecloses ever building a shared contrast obligation: a structural NO, not a missing item. The counter-dissent's "the identity is free because it is ungoverned" is true today and false the day either side edits a leaf type; B-5 makes that edit "correct behaviour" with no record that anything was ever shared. It answers a door by welding it shut. |

---

### B-6 — AUTHORITY AT THE SERVING PREDICATE  **[NOT-FIRST-INSTINCT]**

| Column | |
|---|---|
| **mechanism** | **No schema relationship at any altitude.** The crossing contract is the **rendered output**: a two-sided predicate over served bytes — the profile's own primitive values present N/N, sibling profiles 0/N. Authority: **the predicate at the serving boundary**, held by neither token repo. |
| **why not first instinct** | A design-system steward's default is that the contract is the **token source**. B-6 inverts it: the contract is the **served artifact**. Surfaced by asking *"what would the most skeptical external critic add?"* (`option-enumeration-discipline` §5 item 3). |
| **grounding — already exists, already two-sided** | G-38 (8/8 tenuta primitive values present; Contente markers 0) and G-38b (sibling profiles 0/7, 0/7, 0/18). **Now byte-corroborated (PL-07, S4-DISP-P-1 + §9):** the served Contente artifact carries **122** `:root` custom properties, 63 hex tokens (31 in-root / 32 out), `--space-4: 16px`, **0 external refs**; the deck-kit build carries **77** properties, **8** hex, all in-root, no `--space-4`, **0 external refs**. The predicate is discriminating on real bytes. |
| **what it costs** | **F4 only, relocated** — enforcement moves from schema-validation to output-validation. **Zero at F1/F2/F3/F5**: no schema change, no namespace work, **no a8-side round-trip of any kind**. Real cost: an output predicate **cannot catch a source error that never reaches the bytes**. **RE-PRICED UP (PL-13):** extending it to contrast requires the predicate to know **which custom-property NAME plays which ROLE** — and that knowledge is **not free across 4 of 5 profiles**, because only tenuta's names match. A per-profile role-mapping table would have to be built **and maintained**, or the naming gap closed first. |
| **what it forecloses** | Forecloses treating **a schema** as the interop contract; a later request for "one token schema" must reopen this door. Does not foreclose either side keeping its own source validator. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **file-edit** — the predicate is a test, editable where it lives. **No a8-side leg at all**, and uniquely it **needs no cooperation from either CSS-authoring pipeline** (css leg §C). |
| **INV-11/17/19 disposition** | **ENGAGED — one of the few rows in the packet where they are** (with K-5(a), K-6 and E-4). A serve-time predicate hosted **by the Contente rail's fence** REFUSES a legitimate non-Contente deck: **INV-11** (template absent from the pinned producer map), **INV-17** (zero routing addresses), **INV-19** (no `<x-dc>` region) — correct rail-scoped behaviour, and exactly the profile-scope/rail-scope collision H2 §4.3 names. **Disposition required:** host the predicate **profile-scoped, off the Contente rail** (→ all three NOT ENGAGED), **or** dispose all three individually. **This packet states the requirement and does not dispose them.** |
| **C9 interaction** | **C9 RESPONSE-SHAPING-ONLY** applies: a serve-time component **MAY decide WHETHER to respond**, **NEVER rewrite bytes**. A predicate that **gates** a response is C9-compatible; one that **repairs** bytes is **not**. Any elaboration must stay on the gating side. |
| **a11y consequence** *(verbatim excerpt, a11y leg B-6, `:375-402`)* | *"**Where decided**: At the SERVED-BYTES layer — the only F-BRAND option whose mechanism can test ACTUAL rendered custom-property VALUES rather than a declared token's mere existence… **Enforce**: Buildable on EITHER side, or as a third engine-agnostic script… **Palette-swap silent-fail**: **CONDITIONAL.** AS-DESCRIBED-BUT-UNBUILT TODAY: **YES**… **IF BUILT** as a contrast-computing extension: **NO** — this is the one option in the 18-row set where the honest built-state answer differs from the honest as-written-today answer. **Required constraint if built**: The served-bytes predicate must be extended from presence-only to computed-contrast over NAMED role-pairs — which requires the predicate to know which custom-property NAME plays which ROLE. §A.1's naming-mismatch finding means this role-knowledge does NOT come for free across 4 of 5 profiles."* · **Dark-mode**: “If a dark palette is ever built (E4, unaddressed today), B-6's predicate would need to run PER color-scheme, doubling its role-pair matrix — a cost the option's own text does not price.” · **Print**: “B-6 as described tests the inlined on-screen `<style>` block generically; it does not distinguish `@media print` overrides. A screen-contrast pass says nothing about print-specific values if any differ — flagged, not […]” |
| **CSS-emission consequence** *(css leg §C B-6)* | **The only option whose mechanism operates directly on the CSS-emission surface** rather than one altitude above it. It is **the option that makes closing the hex-free enforcement gap cheapest** — a served-bytes hex-scan could close it **without touching `vendor/deck-producer`'s build code at all**. |
| **dissent (leg-1, self-authored)** | It **answers a schema door with a test.** If the operator's question is *"what schema do we commit to,"* B-6 **declines the question** — possibly a category error dressed as a reframing. It places the contract at the **far end of the pipeline**, where failure is discovered latest and attribution is most expensive. And its **INV engagement is real work no other B-row carries**, on a fence that is publisher-side and mid-flight (freeze PENDING, H2 §4.1). |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:247` — 111w, VERBATIM)* B-6 answers a schema question with a test at the far end of the pipeline, where failure is discovered latest and attribution costs most. Its predicate is presence-only today (G-38); extending it to contrast needs role-knowledge that PL-13 shows exists for one profile in five. It is the only B-row engaging INV-11/17/19, on a fence that is mid-flight, and it composes with E-4 into the packet's most C9-loaded corner. A served-bytes predicate also cannot catch a source error that never reaches the bytes — so B-6 governs symptoms, not the contract the operator was asked to commit to. It may be a good gate; it is not a locus of authority. |

---

### B-7 — DELEGATE TO THE EXTERNAL DTCG STANDARD  **[DELEGATION]**

| Column | |
|---|---|
| **mechanism** | **Neither repo owns the contract.** Both declare conformance to the external **W3C DTCG** specification. Authority: **outside both repos, changeable by neither.** |
| **grounding** | Already the acknowledged parent on both sides: the a8t envelope *"Re-implements the DTCG 2025.10 string-leaf profile"*; Contente's title reads *"Token KEY Contract (DTCG-draft)"*. **Both point at the same authority; neither cites it as binding.** **PL-04 sharpens this:** the four-way identity descends from a **single common ancestor** (fe-skeleton `7d7edfa`), so today's agreement is **convergent inheritance**, not independent conformance to a standard. |
| **what it costs** | **F1 + F4.** Engineering low. The cost is **loss of control**: the spec's cadence is neither repo's, DTCG is a moving draft, and a revision becomes an unplanned obligation. Also, the a8t envelope **deliberately declares itself sovereign and non-dereferenceable** (URN, RFC 8141, *"needs nothing served, zero edge-os coupling"*) — delegating outward partly **undoes a stated design intent**. **New, and load-bearing (PL-14):** the a8 SOR HEAD is already restructuring toward a **remote `$ref` at `tokens.autom8y.dev`** — a network-resolved contract. Whether that URL resolves is **UV-P** (§11). B-7 would be delegating outward at the same moment the a8 side is already doing so, to a *different* external. |
| **what it forecloses** | a8t's sovereignty claim over its own envelope; either side extending leaf types without forking the standard or waiting for it. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **none, strictly** — the contract changes when **the standard** changes. In the row's grammar this is the **weakest form of control** of any row: the upstream is a standards body, cadence slower than any git tag, revocability **nil**. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** |
| **a11y consequence** *(verbatim excerpt, a11y leg B-7, `:403-415`)* | *"**Where decided**: Nowhere — DTCG's string-leaf profile types VALUES, not PURPOSES, structurally identical to B-1. **Enforce**: Neither side; the standards body has no stake in either deck product … and the DTCG spec has no contrast-checking clause. **Palette-swap silent-fail**: **YES**, for the same structural reason as B-1/B-4. **Required constraint if built**: None possible under B-7's mechanism — DTCG conformance and contrast conformance are orthogonal properties."* · **Dark-mode**: “Unaffected.” · **Print**: “Unaffected.” |
| **CSS-emission consequence** *(css leg §C B-7)* | **Nothing re-emits.** DTCG has no opinion on CSS custom-property naming or scoping; the `--space-4` collision and the scoping gap **remain open regardless of this ruling**. |
| **dissent (leg-1, self-authored)** | It delegates authority to a body with **no stake in either deck product**. *"Both conform to DTCG"* is **already true de facto** — and, per PL-04, true by **shared descent** rather than by conformance. Making it de jure buys enforcement **only if someone validates against the standard**, which is **F4 work nobody is scheduled to do**. **This is the B-7 ⇄ B-4 collapse test** (§3 head): absent that validator, B-7 risks being **B-4 with extra ceremony plus an external dependency**. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:251` — 108w, VERBATIM)* B-7 delegates to a moving draft whose cadence neither repo controls and whose text contains no contrast, naming or scoping clause — every open gap in this packet survives it untouched. PL-04 shows today's agreement is shared descent, not conformance, so "both conform to DTCG" is already true and de jure adds only an unplanned obligation on revision. The a8t envelope declares itself a sovereign, non-dereferenceable URN by design; B-7 partly undoes that intent at the moment the a8 SOR is already delegating outward to a different external (`$ref` at tokens.autom8y.dev, unresolved). Without the F4 validator nobody is scheduled to build, B-7 is B-4 plus an external dependency. |

---

### B-8 — CONTENT-ADDRESSED AUTHORITY (the pinned canonical hash IS the contract)  **[ADDED AT DELTA — external enumeration audit, CH-01/C-1]**

> **Provenance.** Found by the rite-disjoint arch-adversary at leg 5 (§1.1 candidate
> **G-B1**); added per `option-enumeration-discipline` §4 Step 3. **The gap was real and
> the leg-1 seat concedes it.** **Mechanism corrected before authoring (PL-16)** — the
> critique described the pair as already checking a shared `definitions` hash; it does
> not. B-8 is priced against the real substrate.

| Column | |
|---|---|
| **mechanism** | **The contract is a VALUE, not a file.** The canonical `definitions` hash — `8831da27ace33db1c621b58404b93bae2b09039595c65e7314e35f4d84f5d2fb`, identical **four ways** (S4-D-P-34) — is recorded as the pinned value in **both** repos' **already-existing** `dtcg-envelope.pin.json`, and **both** repos' **already-existing** sync-gate scripts are re-pointed to compute and compare **that** value. Neither repo's *file* is sovereign; the *shared hash* is. A change requires moving the pin **in both repos**. Axis position: **the pinned canonical value itself — content-addressed, repo-independent.** |
| **what the substrate ACTUALLY does today (PL-16, receipted)** | **Both gates hash the WHOLE FILE.** `brand-tokens/scripts/sync-gate.mjs:30-33,70-72` and `autom8y-contente-tokens/scripts/sync-gate.mjs:35-38,63-65` each compute `sha1("blob "+len+"\0"+bytes)` over their own schema file and compare to their own pin (S4-P-16/17). **The two pins hold DIFFERENT values by construction** — `0967c77d…` vs `f9ea4c44…` (S4-P-18) — because the whole-file bytes differ in exactly the nameplate §2.3 isolated. **Each enforces a LOCAL invariant; neither a SHARED one.** **`proof-sync-gate.mjs` is a discriminating canary**, not a second gate: it asserts `match/`→ok, `tampered/`→RED, `absent`→skip over fixtures and **never points at `PKG_ROOT`**; a8 CI (`ci.yml:47`) runs the canary (S4-P-19). **The vendored copy has no pin, no scripts, no envelope schema** (S4-P-20). |
| **what it costs** | **F1 + F4 — an EDIT, not a NEW ARTIFACT.** (a) Re-point both gates from whole-file blob SHA to the canonical subtree hash (`jq -S '.definitions'` → sha256, the canonicalization the packet used four times). Both `runSyncGate`s are **exported functions with a parameterized root** (`envelopeDir`; `--root`) and the hash is a 3-line local — a **bounded in-place edit of two scripts that already exist and already run.** (b) Re-pin both files to the shared value. (c) **The a8-side gate must actually run against the live pin** — today only the canary runs; this is the honest majority of the cost and it is a8-side. (d) **THE HARD ONE (PL-14):** the SOR at HEAD **has no `definitions` key at all** (restructured to a remote `$ref`; 122/205, S4-D-P-22/23), so **a subtree hash is not computable against SOR HEAD.** B-8 must pin the `v1.0.0`-era shape — which is what is vendored and what all four copies share — **and accept that the SOR has already left it**, or resolve `tokens.autom8y.dev` first (UV-P-pub-1, unresolved). **[leg-5 correction, DELTA: SOR HEAD `dtcg-envelope.schema.json` still carries `definitions` (9 types; canonical `8831da27…`); only SOR HEAD `tokens.schema.json` dropped the inline copy, and it now `$ref`s that envelope file. B-8's a8-side pin target is computable at HEAD; the shape was not left, the duplication was.]** |
| **what it forecloses** | Forecloses **file-sovereignty as the governing idea** — after B-8 "which repo owns the schema" is no longer the question, so **B-1 and B-2 both become unavailable later** without reopening the door. Forecloses unilateral leaf-type change (the pin move is two-sided by construction). Does **not** foreclose B-6 (different altitude, composes) or F3 key-namespace work later. |
| **distinctness — by the packet's OWN tests** | **vs B-1/B-2:** neither file is the source of record; the WHO test returns **"nobody, unilaterally"** — a different answer from "a8t" or "a8". **vs B-3:** **no new artifact, no governance body** — two pin files, two gate scripts, two CIs already exist and already run. B-3's defining cost is **absent**. **vs B-4:** B-4 is *"governed by no one"*; B-8 is **machine-enforced** — and by the packet's **own B-7⇄B-4 collapse logic**, enforcement-presence **is** the distinctness criterion it already committed to. **vs B-5:** B-5 rules nothing shared; B-8 rules a specific value is. **vs B-6:** source altitude, not served bytes. **vs B-7:** a value both repos pin, not an external body. **vs B-0:** B-0 writes nothing. |
| **the discriminating consequence** | **B-8 is the ONLY position under which PL-02's silent in-place vendored fork becomes DETECTABLE.** No gate covers the artifact the producer consumes (S4-P-20). Under B-8, extending the pinned-value check to the vendored `tokens.schema.json`'s `definitions` subtree makes mechanism (ii) — the one-file edit that *"nothing in the system distinguishes"* — **fire RED.** Every other row leaves that fork invisible. **This is what makes B-8 a position rather than a paraphrase.** |
| **a8→a8t import** | **NONE.** Each repo edits **its own** script and **its own** pin to hold a value both independently compute. The shared object is a **64-character hex string** — neither code nor contract-as-file. Lightest import posture in the slate. |
| **contract-change mechanism** | **file-edit (both sides, symmetric) + none-at-the-vendor-site-today.** **`git-tag+re-vendor` is NOT required for the pin** — it lives in the SOR, not the published package — so B-8 escapes PL-01's round-trip. **`in-place-vendored-patch (ungated)` is the mechanism B-8 exists to CLOSE**, and it is the only row that can say so. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** A source-altitude value contract; produces no deck, routes nothing onto the Contente rail. Stated, not assumed. |
| **a11y consequence** *(verbatim excerpt, a11y leg B-8, `486-506`)* | **Where decided**: “Nowhere new — the load-bearing point for B-8 specifically. The pinned artifact is the `definitions` BLOCK: the 9 DTCG LEAF TYPES' `{$type,$value}` shape governance, the SAME altitude as B-1's leaf-shape mechanism — confirmed byte-identical across both repos' copies (sha256 `8831da27…`, leg-1 […]” · **Enforce**: “Both sides' EXISTING sync-gates — `brand-tokens/scripts/sync-gate.mjs` and `contente-tokens/scripts/proof-sync-gate.mjs` (both already running, per arch-adversary's §4.7 re-probe this session) — but ONLY for LEAF-SHAPE drift (does the `definitions` block still match its pinned blob SHA), never for […]” · **Palette-swap silent-fail**: “**YES, unconditionally**, and this is the row where the potnia's framing is most exact. Content-addressing pins the SHAPE a profile's values must conform to (a `color` leaf must be a `{$type:"color",$value:"#hex"}` tuple), not the CONTRAST any two such tuples produce when paired. A hash is a […]” · **Required constraint if built**: “A SEPARATE, VALUE-level check — hashing cannot express a contrast predicate any more than a JSON-Schema required-key can (B-2's structural gap, restated); the two EXISTING sync-gates would need an entirely different mechanism, not a bigger hash, since hash-equality is binary (matches/doesn't) and […]” · **Dark-mode**: “None — the pinned `definitions` block has no color-scheme-conditional leaf type; parity-by-absence (E4) continues exactly as under B-1/B-4/B-5/B-7.” · **Print**: “None — the pinned block doesn't touch print CSS; the structural-only `deck.print-one-slide-per-page` finding is unaffected.” **[PL-16 rider: the phrase 'both already running, per arch-adversary's §4.7' carries the critic's iteration-1 error; both gates enforce local whole-file pins today — see PL-16.]** |
| **CSS-emission consequence** | **Nothing re-emits, either side.** CSS is canonical and JSON generated on both sides (S4-C-P-1/2), so a value-pin at JSON-leaf altitude reaches **zero CSS bytes**. The `--space-4` collision and the scoping gap survive B-8 **untouched**. |
| **coherence with K-\* and E-\*** | **K:** neutral to all six — no K-row's mechanism reads or writes a pin. Closest is **K-6**, which needs a per-profile value source: B-8 supplies a *shape* contract but **no values**, so it helps K-6 no more than B-4 does. **E:** most coherent with **E-2(ii)** — the rendering-architect seat records B-8 as **"Strong"** for that sub-row: *"the four-way-identical `definitions` hash … is exactly the kind of content-address a B-8 world would pin against, and E-2(ii) is the mechanism that would let deck-kit CHECK against that pin at build time."* Also coherent with **E-2(i)**. Coherent-but-unmotivated with **E-1** (nothing crosses, so nothing tests the shared value at render time — B-1's critique, recurring). Forecloses no E-position. |
| **SLOT-B home ((a)/(b)/(c))** | **NONE of the three — B-8 is the clearest evidence SLOT B's enumeration is incomplete (PL-09).** Not (a), not (b), and emphatically not (c). B-8 says: **reconcile neither pair of FILES; pin the VALUE they already share and let the files keep their nameplates.** **If the operator rules SLOT A = B-8, SLOT B as posed has no correct answer** — surfaced in the §0 box rather than forced to fit. |
| **dissent (leg-1 seat, against its own late addition)** | **It governs the one layer that needed governing least.** The `definitions` block has been identical **four ways across three organizations for ten weeks** with zero enforcement and zero observed drift; B-8 spends two script edits, two pin moves and a CI wiring change to machine-enforce a fact never once violated — while everything that HAS drifted (the SOR's 122/205 restructure; the vendored fork path; `--space-4`; four of five profiles' colour names) is **outside what B-8 pins.** Second: **its headline benefit is conditional on work B-8 does not itself schedule** — the vendored-copy check, the entire discriminating consequence, requires adding a pin and a gate to a `node_modules` subtree that has neither. Absent that step B-8 is B-4 with two extra files edited, and **by its own B-7⇄B-4 logic it would collapse into B-4.** Third: cost row (d)'s SOR-HEAD hazard is **CORRECTED at DELTA** — **[leg-5 correction, DELTA: SOR HEAD `dtcg-envelope.schema.json` still carries `definitions` (9 types; canonical `8831da27…`); only SOR HEAD `tokens.schema.json` dropped the inline copy, and it now `$ref`s that envelope file. B-8's a8-side pin target is computable at HEAD; the shape was not left, the duplication was.]** The residual cost is the canonicalisation agreement and the unbuilt vendored check, not a vanished pin target. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-DELTA-2026-09-05.md` §4 — 116w, VERBATIM)* B-8 machine-enforces the one layer that has never drifted, and its price exceeds the two-script edit the row implies: both gates hash whole files today, the a8 gate is not wired into CI (only its fixture canary runs, `ci.yml:47`), the vendored copy carries no pin or script, and both repos must first agree a canonicalisation (`jq -S` and compact JSON give different digests). Its discriminating benefit — catching the silent vendored fork — lives entirely in that unbuilt vendored check; without it B-8 is B-4 with a CI job. It governs SHAPE only: F3's key namespace, `--space-4`, and four profiles' colour names stay ungoverned. A pinned hash of nine leaf types is a contract nobody authored. |

---

## §4 F-DECK — THE OPTION SLATE (SLOT C)

**Axis:** the artifact layer at which profile-variance is first admitted (§2.1). Six
options: one per admissible layer (K-2..K-6) plus the **TRUE NULL** (K-1, confirmed by the
subtractive test, PL-08).

**Precondition riding every row — the two-engine asymmetry** (leg-2-deck §A.2, its own
primary finding). The axis's five-layer vocabulary is **not neutral between the engines**:
the Contente producer has all five layers; `@a8t/deck-kit` has **no design-system namespace**
(`GOAL.md:28` — *"Not a design system."*) and **no component set** (one runtime file,
`src/engine.js`, 129 lines, vanilla JS). **An option authored at the namespace or
component-set layer has no deck-kit-side referent at all** — it is Contente-producer-scoped
by construction (S4-K-P-3/8).

**D-3 rides every producer-touching row:** the design-system namespace is **producer-wide**
— ONE `_ds_manifest.json`, `"namespace":"ContenteDesignSystem_9ed584"`, 11 components
(S4-K-P-4). **Per-profile templating buys NO namespace isolation.**

**K-5's two readings — WHY ONE ID IS RIGHT** *(per the synthesis rule: split only if the
axis position differs)*. The axis position **does not differ**: both readings sit at
**render invocation**. They differ in **which engine's stack the position is exercised in**,
and that is **F-ENGINE's question** (what kind of object crosses), not F-DECK's (which layer
admits variance). Splitting them into K-5a/K-5b would import F-ENGINE's axis into F-DECK's
slate and **double-count one position**. **One id is therefore correct** — and because the
two readings' `INV`, `contract-change` and `a11y` cells diverge materially, they are
presented as **labelled sub-rows inside K-5** so nothing is hidden. **Flagged for leg 5**
(subtractive §B.3 named this as the one place a single id does double duty).

**Dissent asymmetry — RAISED AT LEG 4, DISCHARGED AT DELTA.** The F-DECK leg's charge
reserved dissent authorship downstream, so **0 of 6** K-rows carried an authored dissent
against 8/8 and 5/5 elsewhere — flagged as **DS-1**, the packet's only structural depth
flag. **The arch-adversary authored all six at leg 5** (*"the leg-2 F-DECK seat left its
six slots EMPTY by charge; DS-1 (F-DECK 0/6) is discharged by K-1..K-6 below"*), each
93-110 words, carried **verbatim** below. **SLOT C is no longer being ruled against a
slate with zero adversarial pressure.**

**Two layer classes were considered and EXCLUDED before drafting** (A-1; the
component-engineer seat's §A.5, added at DELTA — `option-enumeration-discipline` §5 item 3
wants "options I rejected before drafting" stated, not silently omitted):

- **Source / frontmatter layer** — profile identity carried in the deck's own content,
  upstream of every named layer. **Excluded**: under WS-A's charge *"designed once,
  rendered per brand profile"* (frame `:54`) the content is shared **by definition** — two
  frontmatters are two decks, i.e. K-1 with duplication. A frontmatter that merely
  *selects* a profile is consumed at the render invocation → **K-5, parametric**.
- **Delivery layer** — profile decided at the rail (capability slug / request).
  **Excluded**: **C9 RESPONSE-SHAPING-ONLY** (DP-2 `:2535-2547`) forbids the serve-time
  component from rewriting bytes, so delivery can only **SELECT among artifacts**, and
  selection presupposes variance already admitted upstream — **delivery is never the FIRST
  layer that differs.** Serve-time rewrite is E-4's territory and K-6's stated C9 boundary.

---

### K-1 — NO LAYER ADMITS VARIANCE  **[TRUE NULL]**

| Column | |
|---|---|
| **mechanism** | One namespace, one component set, one template, one render invocation, one post-render artifact — **shared identically across every profile.** Profile identity is **not admitted into the construction stack at all.** Axis position: **none — the NULL reading.** |
| **what it costs** | **Zero engineering.** The governance cost is naming what is declined: any future "this deck should look like profile X" request has **no seam anywhere** to enter through. |
| **what it forecloses** | K-2..K-6 simultaneously, until reopened. Forecloses the throughline's *"designed once, rendered per brand profile"* as a mechanically true statement of the **construction** stack. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **none** — no contract, because no crossing. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** No non-Contente deck is produced to route anywhere. |
| **D-3 namespace cost** | **NOT APPLICABLE** — touches no part of `vendor/deck-producer`; nothing to generalize. |
| **a11y consequence** *(verbatim excerpt, a11y leg K-1, `:418-436`)* | *"**Where decided**: Nowhere new… **Palette-swap silent-fail**: **N/A in the swap sense** — there is only one profile-shape to ever render, so there is nothing to swap. **This does not mean contrast is safe**: K-1 is the FLOOR every other option is measured against (leg-2-deck's own framing), and §A.4's tenuta caption-on-sunken finding (4.13:1, fails 4.5) occurred UNDER exactly this kind of single-profile architecture — K-1 does not guard against a WITHIN-profile contrast miss, only a CROSS-profile one. **Required constraint if built**: A per-profile-of-one contrast check is still needed; K-1 removes the cross-profile version of the need, not the need itself."* · *"**Dark-mode**: Parity-by-absence, unaffected."* · *"**Print**: Unaffected — `deck.print-one-slide-per-page` continues to apply to the one shape."* **(Dark-mode and Print restored at DELTA — C-8; the leg-4 synthesis dropped both, and the K-1 print fragment was the unmarked drop the adversary named.)** |
| **disambiguation (load-bearing)** | The charge's NULL text read *"profile is a render-time token binding only, OR is not admitted at all."* These are **two axis positions, not one**: admitting **any** token binding at render time is **K-5**. **K-1 is reserved for the second reading only.** |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:255` — 100w, VERBATIM)* K-1 forecloses the epoch's throughline — "designed once, rendered per brand profile" — as a mechanical truth of the construction stack, while the substrate already contradicts it: deck-kit's `--profile-root` has rendered a non-Contente profile in production (G-33/G-37/G-38). Ruling K-1 would declare unadmitted a variance that is already served. Its "zero engineering" cost cell hides that the tenuta deck exists; K-1 is not the status quo, it is a rollback of it. And the a11y cell's own point cuts against it: single-profile architecture did not prevent the 4.13 caption failure, so K-1 buys no safety, only the loss of every seam. |

---

### K-2 — DESIGN-SYSTEM NAMESPACE LAYER VARIANCE

| Column | |
|---|---|
| **mechanism** | Generalize the ONE producer-wide `_ds_manifest.json`/`_ds_bundle.js` into **N per-profile namespace instances**. Axis position: **design-system namespace** — topmost, most expensive. **Contente-producer-scoped only** (no deck-kit referent). |
| **what it costs** | Component set, template, render invocation and post-render projection **all become per-profile by the axis's own consequence rule** — N parallel component-set builds, N template sets, N render paths, N artifacts. **The most expensive position on the axis by construction.** |
| **what it forecloses** | A single shared component identity across profiles. Forecloses K-3 as a separately cheaper position (K-3's premise is subsumed once namespace itself is generalized). |
| **a8→a8t import** | **NONE** on the direction G-29 names. **Flagged, not ruled:** if per-profile instances are populated by reading a8t conventions as input, that is **a8t→a8**, which G-29 is **silent** on — a gap for the operator, not a permission. |
| **contract-change mechanism** | **file-edit**, a8 side (`vendor/deck-producer` is a git-tracked tree). Adds a **git-tag+re-vendor** leg only if a per-profile namespace also pulls a new token package per profile. |
| **INV-11/17/19 disposition** | **ENGAGED if the resulting per-profile decks route via the Contente rail.** Each namespace instance implies a deck resolving to SOME `deck_template`; if not one of the two map entries, **INV-11 DEFAULT-DENIES** (fail-closed; DEFER-2026-W1-007). **Disposition required, not performed.** |
| **D-3 namespace cost** | **This IS the "categorically different, more expensive position"** D-3 names: namespace isolation is available **only** at or below the namespace layer, and K-2 chooses exactly that layer, at maximum cost. |
| **a11y consequence** *(verbatim excerpt, a11y leg K-2, `:437-456`)* | *"**Where decided**: Per-profile, in whichever CSS each of N new namespace instances' component library authors. K-2 has no deck-kit-side referent…, so it inherits the Contente inliner's confirmed ZERO hex/contrast tooling. **Enforce**: Contente build — a null capability until built. **Palette-swap silent-fail**: **YES** — N per-profile namespace instances multiplies independently-authored component-library surfaces against a governance baseline of zero. **Required constraint if built**: A new per-namespace-instance contrast receipt inside a pipeline that currently has NO receipt vocabulary at all."* · **Dark-mode**: “Unaddressed; each of N instances would independently need to price E4.” · **Print**: “ […]” |
| **`legacy-floor-isolation` §2** | **oracle-OK if each per-profile component set is authored fresh; REFUSAL-worthy if produced by forking/copying the existing 11 `.jsx` files** — the §1.2 "transcribing legacy code, including its accidental structure" leak. Both paths named; neither ruled. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:259` — 110w, VERBATIM)* K-2 generalises a producer-wide namespace into N instances and, by the axis's consequence rule, makes every downstream layer per-profile — the most expensive position by construction, on the one engine (Contente's) the a8→a8t rule fences off from a8t code and that has no deck-kit referent. It is Contente-producer-scoped only, so it delivers a8t nothing a8t can consume without crossing the boundary. Its INV disposition is required and unperformed; its legacy-floor result forks on whether component sets are forked or fresh, and the row rules neither. K-2 buys namespace isolation — the one benefit D-3 says only this layer delivers — at a price no charge has asked anyone to pay. |

---

### K-3 — COMPONENT-SET LAYER VARIANCE (namespace stays shared)

| Column | |
|---|---|
| **mechanism** | Keep the ONE namespace string unchanged; swap in a **per-profile 11-component library** registered under it. Axis position: **component set** — one layer below namespace. Contente-producer-scoped only. |
| **what it costs** | N parallel component libraries (11 × N) while the namespace **label stays generic and Contente-named**. Template, render invocation and post-render projection become per-profile by consequence. |
| **what it forecloses** | A namespace string that accurately names what it contains — once non-Contente components live under `ContenteDesignSystem_9ed584`, **the label is fiction for those profiles**. Forecloses treating K-2 as a strictly cheaper later alternative without also relabeling. |
| **a8→a8t import** | **NONE** on a8→a8t; same a8t→a8 silence-flag as K-2. |
| **contract-change mechanism** | **file-edit**, a8 side only, at the component-source layer. |
| **INV-11/17/19 disposition** | **ENGAGED under the same condition as K-2** — a routed deck still needs a recognized `deck_template`; absence DEFAULT-DENIES. **Disposition required, not performed.** |
| **D-3 namespace cost** | K-3 sits **at the layer directly below namespace** and therefore buys **partial** isolation (component behaviour/markup diverge) while the **namespace label stays shared and now inaccurate** — a named cost D-3's own text does not spell out, because it contrasts template-vs-namespace only. |
| **a11y consequence** *(verbatim excerpt, a11y leg K-3, `:457-470`)* | *"**Where decided**: Per-profile, in whichever CSS each of the N swapped-in 11-component libraries authors — same Contente-only scope as K-2, one layer lower. **Enforce**: Contente build, same null-capability finding as K-2. **Palette-swap silent-fail**: **YES**, same reasoning as K-2. K-3's own leg-2-deck a11y note calls this option 'most exercisable for a focus-visible affordance' — true, but exercisability is not enforcement; nothing FORCES correct exercise. **Required constraint if built**: Same as K-2, now priced per-component: 11 components x N profiles, in a pipeline with no receipt vocabulary today."* · **Dark-mode**: “Unaddressed, same as K-2.” · **Print**: “Same UV-P as K-2.” |
| **`legacy-floor-isolation` §2** | Same conditional disposition as K-2. The sharper risk here is that the namespace **string** staying literal while contents diverge is **not** a code-inheritance violation (a label is not behaviour) — it is a **separate naming-integrity concern**, not conflated with the legacy-floor test. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:263` — 101w, VERBATIM)* K-3 keeps a namespace string that becomes fiction the moment non-Contente components live under `ContenteDesignSystem_9ed584` — a naming-integrity debt the row names and then carries. It costs eleven components times N profiles inside a pipeline with zero receipt vocabulary and zero contrast tooling, on the Contente engine only. Its D-3 cell concedes "partial isolation" while the label stays shared and inaccurate; its INV disposition is unperformed. K-3 is K-2's cost with K-2's benefit removed: per-profile behaviour and markup diverge under a shared name that can no longer be trusted to describe what it contains, and no row says who relabels it. |

---

### K-4 — TEMPLATE LAYER VARIANCE (the frame's own first-named position)

| Column | |
|---|---|
| **mechanism** | ONE namespace, ONE component set — but a **distinct template** (`.dc.html` + `deck-stage.js` + `ds-base.js` + `support.js`) authored **per brand profile** rather than per deck-type. Axis position: **template.** |
| **what it costs** | Moderate, and the **least novel mechanism below K-2/K-3** — the producer already has a working two-template pattern to extend (S4-K-P-5). It adds a **per-brand** templating axis **orthogonal** to the existing per-deck-type one; the two must be reconciled (does a profile get one template per deck-type — a full cross-product?). |
| **what it forecloses** | Per D-3: **namespace isolation as a benefit of this option.** Forecloses treating the two-entry audience map as exhaustive — a new template **categorically requires** a new map entry. |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **file-edit**, a8 side (new template directory + assets). A **git-tag+re-vendor** leg only if the template pulls a different token package per profile — **not required** by the mechanism as stated. |
| **INV-11/17/19 disposition** | **ENGAGED — the sharpest and most literal instance in the whole packet.** DEFER-2026-W1-007 names this hazard verbatim: *"a NON-Contente deck with a new `deck_template` DEFAULT-DENIES at the fence."* A per-profile template **is by definition** a new `deck_template` value; **INV-11 fires GUARD_BLOCK reason `absent`** unless the producer-taxonomy map is extended cross-repo first. INV-17/INV-19 are not distinguishing here (they evaluate served-body content, not template identity). **Disposition required for all three, not performed.** |
| **D-3 namespace cost** | **Verbatim:** *"Choosing template as the variance layer leaves the layer BELOW it shared, so per-profile templating buys NO namespace isolation. Any option that claims isolation as a benefit of per-profile templates is claiming something the substrate does not deliver."* **K-4 is precisely that option.** |
| **a11y consequence** *(verbatim excerpt, a11y leg K-4, `:471-495`)* | *"**Enforce**: Contente build (null capability, as K-2/K-3) OR, if invented on the a8t side, deck-kit's build — which HAS a receipt vocabulary (12 closed ids) but confirmed ZERO of them is contrast-related. **Palette-swap silent-fail**: **YES on both possible sides** — Contente has no check at all; deck-kit's check SET exists but does not cover contrast, so even the 'better-governed' side cannot catch a contrast regression from a new per-profile template. **Print**: `deck.print-one-slide-per-page` is STRUCTURAL-ONLY… a print-specific contrast regression … would PASS `deck.print-one-slide-per-page` while remaining an a11y regression for a printed reader."* · **Dark-mode**: “Unaddressed.” · **Print**: “`deck.print-one-slide-per-page` is STRUCTURAL-ONLY (checks `@page`/ `break-after`/`print-color-adjust` PRESENCE, `deck-kit/docs/receipt-schema.md:53`) — it does not compute print-media contrast. A new per-profile […]” |
| **D-4 note** | A new per-profile template **is** the natural home for the exhibit/source-line convention question — the two meet at this layer. **Not disposed; S6 owns the reader-facing consequence.** |
| **`legacy-floor-isolation` §2** *(RESTORED AT DELTA — C-4/CH-04; the leg-4 synthesis dropped this cell although leg 2 had authored it)* | **Not directly engaged** at the producer-self-extension level — a8 extending its **own** template set is not a modern-vs-legacy relationship. **The discipline WOULD engage** if a new per-profile template's markup were produced by **copying deck-kit's slide markup or `engine.js` behaviour into the Contente producer** — the unruled **a8t→a8** direction — rather than being authored fresh in the producer's own idiom. **Flagged as a live risk, not evaluated further:** this packet does not know which authorship path a build would take. *(The adversary's K-4 dissent names this omission explicitly; the cell is restored so the dissent has its referent.)* |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:267` — 93w, VERBATIM)* K-4 is the frame's first-named position and the least novel below K-2/K-3 — which is exactly the danger: it extends the Contente producer's two-template pattern to carry a foreign brand, and the packet's K-4 row carries no legacy-floor test even though leg 2 authored one (`DP-1-draft-leg2-deck.md:315-322`). It is the sharpest INV-11 hazard in the packet — a per-profile template is by definition a new `deck_template` that DEFAULT-DENIES. It buys no namespace isolation (D-3, verbatim) and must reconcile a per-brand axis against a per-deck-type one, a cross-product the row raises and does not size. |

---

### K-5 — RENDER-INVOCATION LAYER VARIANCE  *(two readings, ONE axis position — see §4 head)*

| Column | |
|---|---|
| **mechanism** | ONE namespace, ONE component set, ONE template — the **render invocation itself** takes a profile parameter swapping only the CSS/token binding at build time. Axis position: **render invocation.** **(a) novel a8-side seam:** parameterize `resolve-deck.mjs:43`'s hardcoded `import.meta.resolve('@autom8y/contente-tokens')` so the package resolved is an INPUT. **(b) promote existing a8t substrate:** deck-kit's `bin/build.mjs:232` **already accepts** `--profile-root`, and this is **the substrate LEG-1 measured** (G-33/G-37/G-38). |
| **what it costs** | **(a)** moderate a8-side engineering plus a genuinely open question of what is passed in. **(b) near zero — the seam exists.** Per **LEG-3 REFUSED**, no further build may be scheduled on this lineage regardless, and **LEG-1 must be measured, never re-scheduled as build**. |
| **what it forecloses** | **(a)** forecloses treating brand-binding-by-package-name as immutable. **(b)** forecloses nothing new — it is a measurement of what already exists. |
| **a8→a8t import** | **NONE** either reading. **(a)** risks the **a8t→a8** direction if the new seam is built by **copying** deck-kit's `--profile-root` implementation rather than consulting it as a pattern — G-29 is silent there; a gap, not a permission. |
| **contract-change mechanism** | **(a) file-edit**, a8 side. **(b) file-edit**, a8t side, **already made**. |
| **INV-11/17/19 disposition** | **(a) NAMED, VERIFIED, UNDISPOSED HAZARD.** `classify()` keys **ONLY on the `deck_template` string**, never on rendered CSS or bytes (S4-K-P-13, a verified structural fact, not a supposition). So a profile-swapped deck served through an EXISTING pinned template **passes INV-11 without ever being classified as a new template**, while being a different profile's render. Whether that is intended, permitted under WS-GUARD C-3 (*"values are consumed from the producer, never minted locally"*), or a silent gap is **not this packet's call**. **(b) NOT ENGAGED** — deck-kit's serving path does not route through the audience map or the Contente fence at all; **this is precisely why LEG-1 was served on the a8t rail.** |
| **D-3 namespace cost** | **(a)** inherits D-3 exactly as K-4 does — render invocation sits BELOW template, so it inherits every layer-above's "shared by consequence" status, **including the template**, which stays the SAME single template. **(b) NOT APPLICABLE** — touches no part of `vendor/deck-producer`; deck-kit has no namespace to generalize. |
| **a11y consequence** *(verbatim excerpt, a11y leg K-5, `:496-525`)* | *"Reading (b) … is the LIVE, MEASURED architecture this artifact's §A is built from… **This is the clearest-grounded row in the entire 18-row set** because it is not hypothetical… **Enforce**: deck-kit's receipt vocabulary — confirmed ZERO of its 12 claim ids is contrast-related. `deck.brand-css-hex-free` … explicitly EXEMPTING the profile's primitives/semantic CSS as 'the canonical color source' — **the ONE place a hex color actually lives is the ONE place the ONE existing color-adjacent check does not look.** **Palette-swap silent-fail**: **YES, with direct numeric proof, not inference.** §A.4's tenuta caption-on-sunken finding (4.13:1, fails 4.5) occurred under the CURRENT, ALREADY-SHIPPED profile … via the ALREADY-LIVE `--profile-root` seam this reading promotes. No hypothetical swap was needed to find it."* · **Dark-mode**: “Unaddressed (E4, css draft).” · **Print**: “Structural-only, as K-4; unaddressed for print-media contrast specifically.” |
| **PL-13 rider** | Reading **(b)** additionally carries the naming finding: deck-kit's `deck.css` `var()` targets match **only tenuta**; pointing `--profile-root` at the other four profiles today resolves against **undefined custom properties** (S4-A-P-1..7), and deck-kit's hardcoded **3-file** layer contract is matched by **only tenuta** (S4-C-P-5). **Two independent naming contracts, both satisfied by exactly one of five profiles.** |
| **`legacy-floor-isolation` §2** | **(b) is the slate's strongest POSITIVE, already-receipted instance of the discipline working**: `engine.js` — *"Authored fresh for deck-kit after reading (not copying) the fleet's deck conventions… Zero code copied"* (S4-K-P-3). **(a) is where the bite would land** if a new a8-side seam were built by copying deck-kit's implementation rather than consulting the pattern. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:271` — 105w, VERBATIM)* K-5 carries two readings under one id, and the packet concedes their INV, contract-change and a11y cells "diverge materially". Reading (a) is a new a8-side seam that passes INV-11 unclassified (S4-K-P-13) and risks a8t→a8 copying; reading (b) is a measurement of what already shipped, on a seam whose CSS-variable contract binds one profile in five (a8t satisfies 4 of 22 names, the rest 0 of 22). The operator ruling "K-5" has not chosen a reading — SLOT D chooses it for them, which the box never says. And (b)'s "near zero" cost is near zero only for tenuta; every other profile resolves against undefined properties. |
| **leg-5 disposition of the one-id question** | **UPHELD** — *"Correct by the stated rule (A-2). The axis position does not differ."* The under-stated consequence the adversary adds, now carried: **the operator ruling "K-5" has not chosen a reading — SLOT D chooses it** ((a)↔E-2(i), (b)↔E-1). Stated in the §0 box at DELTA. |

---

### K-6 — POST-RENDER PROJECTION LAYER VARIANCE  **[NOT-FIRST-INSTINCT · VIABLE — REFUSAL-EXPOSED (legacy-floor §2)]**

| Column | |
|---|---|
| **mechanism** | ONE namespace, component set, template and render invocation — all Contente, all shared, all frozen. Variance is admitted **only in a post-render pass over the already-produced artifact**: a value-rewrite of served CSS custom-property declarations in the frozen export, swapping token VALUES without touching markup, components, or namespace. Axis position: **post-render projection.** |
| **why not first instinct** | Every other option changes something **upstream** of the artifact's production. K-6 inverts that — it lets the Contente pipeline run to completion unmodified and treats its **output** as raw material. |
| **what it costs** | **Zero upstream engineering** — no producer file is edited (no namespace, component, template, or render-invocation change). The cost moves entirely downstream: a rewrite pass must reliably locate and replace CSS custom-property VALUES in an opaque, already-serialized artifact without corrupting markup, and it inherits the exact fragility any string/regex rewrite over baked HTML carries — **a producer-side markup change silently breaks the rewrite pass with no compile-time signal.** *(Restored as primary text at DELTA iteration 2, M-1/CH-13: the iteration-1 NON-VIABLE framing is reverted; pricing is restored because viability is.)* |
| **what it forecloses** | Forecloses treating the rewrite pass as a source of TRUTH for the profile's design intent — **it can only reproduce values already known elsewhere** (some token source must still supply what to rewrite TO). Does not foreclose K-2..K-5 as later independent choices; the rewrite operates entirely downstream of all of them. *(Restored as primary text at DELTA iteration 2, M-1/CH-13.)* |
| **a8→a8t import** | **NONE as a module import — QUALIFIED (leg 5, DELTA): the frozen export embeds Contente's `_ds_bundle.js` verbatim (S4-K-P-18) — the same artifact deck-host already serves at `public/761ebfd8…/index.html` under E-3's "produced OUTPUT, neither contract nor code" reading (:797). A permanent K-6 strategy is INHERITED construction and fires legacy-floor §2 REFUSAL (:696); it is not G-29 NON-VIABLE. Contested by the component-engineer seat (PL-17); the operator rules.** |
| **contract-change mechanism** | **file-edit** — the rewrite script would be homed on the **serving** side (deck-host). No a8-side leg. |
| **INV-11/17/19 disposition** | **ENGAGED, with the sharpest silent-gap risk in the packet.** The rewrite preserves the ORIGINAL template's identity (only byte VALUES change) — so `deck_template` is unchanged and **INV-11 would not fire**, even though the deck's brand now differs from what that template was pinned for. **Sharper than K-5(a)'s hazard, because K-6 makes no claim to be a legitimate new template at all — it is explicitly a re-skin.** Grounded on the verified `classify()` signature (S4-K-P-13). **Disposition required, not performed.** |
| **C9 boundary** | K-6 as authored is **build/export-time only**. **If ever inverted into a request-time rewrite it collides directly with C9 RESPONSE-SHAPING-ONLY** — *"a serve-time component may decide WHETHER to respond, never rewrite bytes."* The boundary is stated; crossing it is not proposed. |
| **D-3 namespace cost** | **NOT TOUCHED** — K-6 operates entirely downstream of namespace, component set, template AND render invocation, so all four stay exactly as shared as D-3 finds them today. |
| **a11y consequence** *(verbatim excerpt, a11y leg K-6, `:526-553`)* | *"**Palette-swap silent-fail**: **YES as written** — a value-rewrite swapping token values in frozen CSS has no built-in contrast check on the incoming values…; structurally the same failure mode as every JSON-schema-altitude option (B-1/B-3/B-4/B-7), instantiated at the CSS-byte layer instead. **Required constraint if built**: The rewrite step must itself compute contrast on each incoming (foreground, background) pair BEFORE emission… 'available' means no more available than any other unbuilt check, since no contrast-computation code exists anywhere in this tree today. **Dark-mode**: UNUSUALLY WELL-SUITED … The one row in the K-slate where dark-mode is a natural extension of the option's own mechanism."* |
| **`legacy-floor-isolation` §2** | **The option most exposed to REFUSAL, and that is a positive result of applying the test.** A "non-Contente" deck produced by re-skinning Contente's own rendered structure — same markup, same internals, same namespace, only values swapped — is **inheriting Contente's construction as the modern deck's own**. The discipline says: *consult* Contente's frozen output for what a deck must look like; do **not** inherit its bytes as the deck's own construction. **Not ruled out here**; the disposition the test would apply is named. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:275` — 104w, VERBATIM)* K-6 re-skins Contente's frozen output and calls the result a non-Contente deck: same markup, same namespace, same inlined component JS (`_ds_bundle.js`; 17 inline-script hex literals, S4-F-P-6), with only values rewritten. The row's own legacy-floor cell reaches REFUSAL for a permanent strategy, yet its import cell says bare NONE — the least true NONE in the packet. It preserves `deck_template` identity so INV-11 never fires on a deck whose brand no longer matches the template it was pinned for. It is a regex over baked HTML that a producer markup change breaks silently, and it needs a per-profile value source B-0 and B-5 cannot supply. |

---

## §5 F-ENGINE — THE OPTION SLATE (SLOT D)

**Axis:** the kind of object that crosses the a8→a8t boundary (§2.1). The axis is
**CLOSED** — it names its own five positions — so this slate's enumeration task is
**COVERAGE, not discovery**: one option per named position, no double-occupancy, no
smuggled sixth. **E-1 is the TRUE NULL** (confirmed by the subtractive test, PL-08) and is
also the **standing, already-shipped architecture**.

**A delegation option was tested and found to COLLAPSE, not to be missing:** a
third-party-operated live renderer differs from E-4 only in **who operates the process**,
not in **what kind of object crosses**. Operator-identity is a consequence, not an axis
position — recorded as an ownership variant of E-4, not a sixth option.

**DIRECTION — CORRECTED AT DELTA (C-2/CH-02).** §2.1 previously said direction is
load-bearing on **exactly one** position (source code). **That is falsified by E-2's own
cost cell**, which prices a direction. Direction is load-bearing at **two** positions, for
**two different reasons**: at **source code (E-5)** it decides **VIABILITY** — a8→a8t is
NON-VIABLE, a8t→a8 is not fenced by G-29; at **declarative contract (E-2)** it decides
**COST and GOVERNANCE** — **a8t→a8 is the direction G-29 is SILENT on** (a gap, priced
here, never a permission this packet grants), while **a8→a8t is the direction G-29
EXPLICITLY PERMITS** (*"contracts may be shared"*, shape `:1183`). Direction still does
**not mint an axis position**, which is exactly why E-2 is split into **labelled sub-rows**
— the same treatment K-5's two readings already receive, *"so nothing is hidden"*.
**The adversary's consequence, accepted in full: without (ii), an operator ruling B-2
while deck-kit renders had no E row at all.**

---

### E-1 — NOTHING CROSSES  **[TRUE NULL — the standing architecture]**

| Column | |
|---|---|
| **mechanism** | Each engine renders its own profiles from its own native token source: the a8 inliner via package-alias resolution; deck-kit via `--profile-root` pointed at `brand-tokens/profiles/`. **No object of any kind crosses the a8→a8t boundary for rendering.** |
| **what it costs** | **Zero new engineering — this IS the architecture LEG-1 already exercises in production** (G-33/G-37/G-38). The cost is maintaining **two independent engines** with two vocabularies — a duplication cost paid in engineering surface, not cross-boundary risk. |
| **what it forecloses** | A single shared render surface — any future desire for visual/DOM parity between a Contente deck and a non-Contente deck must be achieved by maintaining two engines to the same external spec. Does **not** foreclose adopting a later F-BRAND ruling at the token-contract layer (orthogonal axes). |
| **a8→a8t import** | **NONE.** |
| **contract-change mechanism** | **file-edit**, independently on each side — no shared render-time contract exists to change. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** deck-kit's output is served by deck-host's own non-Contente publish path, not the pipeline the rail-scoped invariants police. |
| **C9 collision** | **NO.** No serve-time component is introduced; nothing for C9 to gate. |
| **a11y consequence** *(verbatim excerpt, a11y leg E-1, `:556-574`)* | *"**Where decided**: Exactly where §A measured it — independently, per engine, per profile — because E-1 IS the architecture G-38/G-38b already exercises. **Enforce**: Neither side, cross-engine… **Palette-swap silent-fail**: **YES, per-engine, independently** — §A.4's tenuta caption-on-sunken FAIL (4.13:1) and §A.3's a8t muted-on-surface FAIL (3.41:1) BOTH occurred under E-1's own standing architecture, with no engine-crossing required to produce either. **Required constraint if built**: E-1 contributes NONE by itself…: the focus-token-naming gap and this leg's measured contrast gaps are `brand-tokens`-layer AND CSS-authoring-layer facts, orthogonal to whether anything crosses a render boundary."* · **Dark-mode**: “Unaffected — E4 is a per-engine cost regardless of which F-ENGINE option is ruled.” · **Print**: “Unaffected, per-engine, as today.” |
| **F-BRAND coherence** | Most naturally coherent with **B-0/B-4/B-5/B-6** (no crossing needed to exercise an ungoverned or absent contract). Coherent-but-**unmotivated** with **B-1/B-2/B-3/B-7**: those rulings put a shared contract in force, but E-1 exercises it **nowhere at render time** — a shared authority with no crossing that ever tests it. |
| **`legacy-floor-isolation` §2** | **CONSULTED — already established prior art**, not newly decided by choosing this option (deck-kit's own provenance accounting, S4-E-P-3). |
| **dissent (leg-2, self-authored)** | It **ratifies duplication as permanent.** If the throughline is read as ONE render surface, E-1 answers *"no, two, forever."* Sharper: its apparent zero-cost stability is not fully earned — **DK-002/003/004 remain SKETCH** (D-1), so E-1 assumes deck-kit's current landed surface can carry **every** future profile, not only the tenuta pilot. Priced as **UV-P-S4-E-1**, not asserted. **PL-13 sharpens this further:** deck-kit's template binds only tenuta's names today. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:279` — 104w, VERBATIM)* E-1 ratifies two engines forever and calls the duplication zero-cost; the cost is two vocabularies, two validators (one of which does not exist, PL-12), and two contrast gaps the a11y leg measured under this very architecture (4.13 and 3.41). Its stability rests on deck-kit carrying every future profile, but DK-002/003/004 are SKETCH (UV-P-S4-E-1) and deck-kit's template binds tenuta's names only (PL-13). E-1 is coherent-but-unmotivated with every "share a contract" ruling — a shared authority no render path ever tests. It is the null the operator can reach by not ruling, which is precisely why ruling it settles nothing the operator was asked to settle. |

---

### E-2(i) — A DECLARATIVE ARTIFACT CONTRACT CROSSES  (**a8t → a8**, build-time)  *(split at DELTA — C-2)*

| Column | |
|---|---|
| **mechanism** | The a8 inliner gains a second resolution mode — resolve an a8t profile contract instead of, or alongside, the Contente package — so one engine can render **any** profile whose token contract it is handed. |
| **what it costs** | Direction is **a8t→a8**, which G-29 is **SILENT** on — priced here, **not granted as a permission**. Engineering: a second resolution mode; decide whether package-name-only is retired or dual-pathed. Leaf altitude is **cheap** (identical four ways). What remains is F2/F3/F4 — key namespace, expression mechanism, enforcement locus — **none of which this option resolves**; it only decides that SOME contract of that shape now crosses. **RE-PRICED (PL-12):** the receiving side has **no build-time schema consumer today**, so "the inliner accepts a contract" means **building that consumer from nothing**, not extending one. |
| **what it forecloses** | Forecloses treating deck-kit as the sole non-Contente renderer — a future profile could route to **either** engine, reopening rather than settling "which engine renders which profile" per profile. |
| **a8→a8t import** | **NONE.** The crossing is a8t→a8, and the object is a contract, not code — doubly outside the FORBIDDEN class. |
| **contract-change mechanism** | **git-tag+re-vendor** on the a8 side **+ file-edit** on the a8t side **+ in-place-vendored-patch (ungated)**. **RE-PRICED (PL-01):** the slate carried "upstream-publish"; corrected to a same-operator tag round-trip, with the ungated in-place fork available alongside it. |
| **INV-11/17/19 disposition** | **ENGAGED IF** the resulting a8-rendered non-Contente artifact is staged through the existing Contente floodgates pipeline; **NOT ENGAGED IF** staged through a separate path. **Required, unperformed.** The two-template DEFAULT-DENY bites identically if a new `deck_template` is needed. |
| **C9 collision** | **NO.** Purely build-time. |
| **a11y consequence** *(verbatim excerpt, a11y leg E-2, `:575-594`)* | *"**Where decided**: By whichever CONTRACT crosses — E-2's own text does not specify… If the crossing contract is a8t's EXISTING flat `required_key_paths` schema, this leg's B-2-equivalent finding applies directly: key-presence is not value-contrast. **Palette-swap silent-fail**: **YES, unconditionally** — no schema in this tree (a8t's OR Contente's) encodes a contrast predicate… **Required constraint if built**: A contrast-bearing new contract … runs directly into §A.1's naming-convergence finding: 4 of 5 profiles don't share ROLE NAMES with deck-kit's template, so a new contract crossing at E-2 would ALSO need to solve the naming mismatch before a contrast predicate could even be EXPRESSED generically."* · **Dark-mode**: “Unaddressed by E-2's mechanism.” · **Print**: “Unaddressed.” |
| **F-BRAND coherence** | Most strongly coherent with **B-1** — E-2 is the natural **enactment** of B-1's own dissent (*"if the intent is to make F3 reachable later…"*); this is that "later." Also coherent with **B-3** and **B-7**. **In tension with B-5** (no reconciliation): E-2 requires exactly the governed crossing B-5 rules out. **In tension with B-0**: B-0 declares no contract exists to cross. |
| **`legacy-floor-isolation` §2** | **Test does not fire in its stated direction** (the mechanism is a8-side authorship; no a8t-side engineering consults or inherits). **Flagged:** the analogous risk in the OTHER direction — does the legacy inliner silently assume its own token-substitution premises apply to a foreign a8t contract? — is real and is **NOT what this discipline as scoped tests.** Named so it is not mistaken for a cleared check. |
| **dissent (leg-2, self-authored)** | **It solves a problem E-1 already solves for free.** The only reason to prefer it is wanting ONE render engine — a preference no charge has established. It hands the a8 inliner a new build-time dependency on an a8t artifact whose cadence it does not control, while leaving deck-kit's own unresolved maturity (DK-002/003/004 SKETCH) **completely unaddressed** — progress that is orthogonal to what deck-kit actually needs next. **Composition note:** E-2 is the **precondition E-3 presupposes** when the inliner is the renderer; it is not free-standing progress toward E-3. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:283` — 114w, VERBATIM)* E-2 hands the a8 inliner a second resolution mode for a contract in the a8t→a8 direction G-29 is silent on — a gap the row prices but cannot close — while the receiving side has no schema consumer to extend (PL-12), so "accepts a contract" means building a validator from nothing. It solves what E-1 solves for free, leaves deck-kit's maturity untouched, and is the precondition E-3 silently presupposes. The row also fixes a direction the axis claims is not load-bearing here, and enumerates only one: the mirror — a8's contract consumed by deck-kit, the direction G-29 explicitly permits — is absent, so an operator ruling B-2 with deck-kit rendering has no E row. |

---

### E-2(ii) — A DECLARATIVE ARTIFACT CONTRACT CROSSES  (**a8 → a8t**, build-time; deck-kit consumes the Contente tokens contract)  **[MINTED AT DELTA — C-2]**

> **Same axis position as E-2(i); opposite direction.** Direction does not mint an axis
> position (§5 head), so this is a **labelled sub-row**, not a sixth option — the treatment
> K-5's two readings already receive. **This is the direction G-29 EXPLICITLY PERMITS.**

| Column | |
|---|---|
| **mechanism** | deck-kit is extended to accept a NEW build-time input mode — mirroring its own `--profile-root` flag in **shape**, but pointed at a8's Contente token artifact (the vendored `@autom8y/contente-tokens` package's `tokens.schema.json` / its token VALUES) instead of a `brand-tokens/profiles/{profile}` directory — so **deck-kit becomes able to validate against, and potentially render under, the Contente contract.** E-2(i)'s mirror: the CONTRACT crosses **a8→a8t**, consumed by the a8t engine rather than produced by it. |
| **what it costs** | **No VIABILITY gap to price** — this is the permitted direction, not the silent one. Cost is engineering plus **WHICH-ARTIFACT governance**, on two on-disk facts. **PL-12:** the a8 producer **never reads `tokens.schema.json` anywhere in its own source** (0 rows), so **there is no existing a8-side schema-consumption logic to point deck-kit at as a reference implementation** — deck-kit builds its own consumer from nothing, symmetric to E-2(i)'s cost, mirrored. **PL-14:** the artifact is **not a single stable target** — the vendored `#v1.0.0` still carries `definitions` INLINE; the SOR at HEAD has **deleted** it for a remote `$ref` (`tokens.autom8y.dev`, resolvability UNPROBED, UV-P-pub-1). **E-2(ii) therefore does not merely decide "a contract crosses" — it decides WHICH of two diverging schema states deck-kit points at**: the vendored, self-contained-but-stale `v1.0.0`, or the current-but-not-self-contained SOR HEAD. |
| **what it forecloses** | Forecloses deck-kit's independence from the Contente package's key namespace for whatever profile is validated this way — a build-time dependency on an artifact whose SOR is a **third repo** outside this leg's scope. Does **not** foreclose deck-kit's native `--profile-root` CSS consumption for non-Contente profiles; **the two input modes can coexist.** |
| **a8→a8t import** | **NONE — contract, not code.** The crossing is a8's `tokens.schema.json` / package token VALUES (**data**), not the producer's or SOR's rendering/build source. **This is the one E-2 direction G-29 explicitly names as permitted, not merely silent-on** (contrast E-2(i)). |
| **contract-change mechanism** | **git-tag+re-vendor — in a git-pinned-dependency shape, not a registry-publish shape.** The SOR's CI runs four guards with **no publish step**; distribution is a git dependency pinned to a tag (`#v1.0.0`). A contract change deck-kit consumes is therefore a **TAG BUMP (or HEAD-tracking re-vendor) on a third repo**, not a registry version bump — **a more brittle cadence than the generic `upstream-publish` label implies**, named precisely so the operator sees it. |
| **INV-11/17/19 disposition** | **NOT ENGAGED.** deck-kit consuming a schema at build time routes no deck through the Contente floodgates pipeline the invariants police; this crossing stops at validation/build input, not staging or serving. |
| **C9 collision** | **NO.** Purely build-time; no serve-time component introduced. |
| **a11y consequence** *(seat-authored — rendering-architect; no a11y-leg row exists for E-2(ii); §F manifest has 20 blocks)* | **Conditional, and weaker than it looks.** If deck-kit validated against the SOR's current schema, `color.focus.ring` could in principle gate deck-kit's own profile CSS as it gates Contente's — **but PL-13 shows deck-kit's own `deck.css` colour-role bridge satisfies 0/13 for every non-tenuta profile today.** A new schema-consumption mode **does not retroactively fix that gap; it only adds a second place the SAME gap could be checked.** |
| **F-BRAND coherence** | **Strong with B-2** — this sub-row **IS B-2's natural enactment when deck-kit is the render engine**: B-2 requires a8t profiles to conform to Contente's key tree, and E-2(ii) is the crossing that lets deck-kit actually perform that conformance check at build time. **This closes exactly the gap the adversary named.** **Strong with B-8 IF the hash is what gets pinned** — the four-way-identical `definitions` hash *"is exactly the kind of content-address a B-8 world would pin against, and E-2(ii) is the mechanism that would let deck-kit CHECK against that pin at build time rather than merely cite it."* **Tension with B-5** — for the identical reason E-2(i) is: it requires exactly the governed crossing B-5 rules out. |
| **`legacy-floor-isolation` §2** | **Bifurcates cleanly on WHAT is consumed — the sharpest instance of this test in the slate.** If deck-kit **CONSULTS** the Contente contract — reads the schema / token VALUES as an oracle for what a conformant token set must supply, while its own component and layout code stays independently authored — **CONSULTED / oracle-OK.** If deck-kit instead **INHERITS a Contente TEMPLATE** — reproduces the namespace-scoped component shape or markup conventions because that is what the consumed package implies a "conformant" deck looks like — **INHERITED / REFUSAL fires**, the identical class E-5 and K-6 already occupy. **This sub-row's own mechanism sits on the CONSULTED side by construction**; a builder letting consumption slide into component/markup shape crosses into K-6/E-5 territory — **named here so the boundary is visible before any build.** |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-DELTA-2026-09-05.md` §4 — 111w, VERBATIM)* E-2(ii) makes deck-kit the only enforcer of a schema its own producer never reads (PL-12): the consumer polices a contract the author ignores, and every RED it raises is a8t's problem to explain. It must pick one of two diverging artifacts — the vendored `v1.0.0` with inline definitions, or SOR HEAD's remote `$ref` whose host is unprobed (UV-P-pub-1) — and a tag bump on a third repo is its change cadence. It is B-2's enactment, so it inherits B-2's legacy-floor REFUSAL one layer down: the moment "conformant" comes to mean Contente-shaped markup, it is K-6. And it fixes none of PL-13 — a second place to check names that resolve 0/13. |

---

### E-3 — A PRODUCED ARTIFACT CROSSES  (a8 → a8t, build/stage-time; reuses the EXISTING rail)

| Column | |
|---|---|
| **mechanism** | Whichever engine renders a profile produces a completed, FROZEN HTML artifact; that **produced artifact** — not source, not a live process — crosses a8→a8t through the **same staging mechanism the rail already uses** for Contente decks (frame §7.1 SETTLED — no sprint re-invents it). For an a8-rendered non-Contente profile this **presupposes E-2**; if deck-kit renders instead, E-3 narrows to *"route the already-produced a8t artifact through the same staging predicate"* — a claim about unifying **STAGING**, not rendering. |
| **what it costs** | Reuses 100% of the existing staging/serve rail — **the cheapest INTEGRATION cost in the slate**, because the crossing OBJECT (a frozen HTML file) is **identical in kind to what already crosses today**. The REAL cost is borne **upstream**, by whichever precondition produces the artifact. **Must not be read as cheap in isolation** — only as the cheapest possible crossing once a produced artifact exists. |
| **what it forecloses** | Forecloses any serve-time dependency on a live a8-side process for this crossing — the artifact is frozen before it crosses, matching the WS-GUARD byte-parity invariants' assumption of a FIXED `frozen_sha256`. **Now byte-corroborated (PL-07):** served body sha256 == ledger `frozen_sha256` == S1 VERDICT record, for slug `761ebfd8…` (S4-DISP-P-1). |
| **a8→a8t import** | **NONE** — a compiled HTML artifact is a produced OUTPUT, neither contract nor code. |
| **contract-change mechanism** | **file-edit**, on whichever side produces the artifact — no recurring contract to renegotiate once an artifact exists. |
| **INV-11/17/19 disposition** | **ENGAGED, identically to how they are engaged today for Contente decks, IF** staged through the Contente floodgates path — a non-Contente `deck_template` must then clear the two-template DEFAULT-DENY. **NOT ENGAGED IF** staged through deck-host's own non-Contente publish path — **which is what LEG-1 actually did.** **Required, unperformed:** which staging path an a8-rendered non-Contente artifact takes is exactly the fork this row surfaces. |
| **C9 collision** | **NO.** The artifact is FROZEN before serving; a static host does not reach C9's bar. |
| **a11y consequence** *(verbatim excerpt, a11y leg E-3, `:595-620`)* | *"**Where decided**: BEFORE the crossing, at whichever engine PRODUCED the artifact… G-38/G-38b's EXISTING gate is PRESENCE-only, not CONTRAST — extending it is exactly B-6's mechanism, not something E-3 supplies on its own. **Enforce**: Whichever side stages the artifact … — a contrast gate inserted here would be a PRE-DEPLOY check, **structurally the EARLIEST possible enforcement point in this 18-row set.** **Palette-swap silent-fail**: **YES as written** … but this is the row with the CHEAPEST retrofit path to NO, because the gate infrastructure (the runner) already exists and already gates something (staging), unlike B-3's 'no forum exists' problem."* · **Dark-mode**: “Unaddressed; a staging-time gate COULD check both light AND dark palettes if E4 is ever built, at zero additional crossing cost — an early-pipeline advantage similar in spirit to K-6's.” · **Print**: “Unaddressed; the staging gate operates on the ARTIFACT, not the print stylesheet specifically — same structural-only caveat as K-4/K-5/K-6.” |
| **F-BRAND coherence** | Most strongly coherent with **B-2** (if a8's schema is sovereign, the natural render path is the a8 inliner with a produced artifact crossing — matching the EXISTING crossing shape). Also coherent with **B-0/B-4/B-5/B-6** when deck-kit is the renderer: by the time an artifact exists, the contract question is already resolved upstream. |
| **`legacy-floor-isolation` §2** | **CONSULTED / oracle-OK, most cleanly of the five.** The existing staging predicate treats a produced HTML file **generically** (`deploy_root_guard.py`'s no-orphan SUPERSET predicate is not Contente-specific), so extending it CONSULTS the staging contract without inheriting anything Contente-specific. Nothing about the inliner's internal rendering logic is touched or copied. |
| **dissent (leg-2, self-authored)** | It is **the option most likely to be mistaken for "no decision needed"** — it reuses an existing rail so completely it can look like ratifying the status quo (E-1's territory) when it is not: it silently **presupposes** the a8 inliner renders the non-Contente profile (requiring E-2). If deck-kit is actually the renderer, E-3 shrinks to "unify staging" — possibly unnecessary, since deck-kit's artifacts already stage successfully **without touching the Contente floodgates path at all**. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:287` — 103w, VERBATIM)* E-3 is the crossing most likely to be mistaken for no decision: it reuses the rail so completely it reads as status quo while silently presupposing E-2 whenever the a8 inliner renders a non-Contente profile. When deck-kit renders, it shrinks to "unify staging" — a change LEG-1 already showed unnecessary, since deck-kit artifacts stage without touching the floodgates path. Its "cheapest integration" claim is true only after someone else pays the upstream cost, and its INV disposition depends on a staging-path fork the row surfaces and does not rule. E-3's frozen-artifact virtue is real; it is also E-1's, already, at no additional decision. |

---

### E-4 — A RUNNING PROCESS'S OUTPUT CROSSES  (a8 → a8t, serve-time)  **[NOT-FIRST-INSTINCT]**

| Column | |
|---|---|
| **mechanism** | Rendering happens on-demand, per request, on a live a8-side process; its live OUTPUT crosses the boundary **at serve time** — the a8t rail proxies to, or is fronted by, that renderer rather than serving a pre-staged frozen file. |
| **why not first instinct** | The other four positions resolve the crossing **before** a request arrives (or never). "What if the crossing happens live, per request" is the position reached for **last**. |
| **what it costs** | **Highest operational cost in the slate:** a live cross-org runtime dependency at the moment of serving, for **every** request. It collides with the WS-GUARD byte-parity invariants' assumption of a FIXED `frozen_sha256`: a live-rendered response has **no single frozen value to compare against** unless the first render is captured and frozen — **at which point it has degenerated into E-3**, captured lazily. |
| **what it forecloses** | Forecloses deck-kit's own byte-determinism fitness function from applying to what is actually SERVED. Forecloses treating telos L1's *"served 200 byte-identical to its frozen export"* as trivially satisfied — it becomes an **additional invariant this option must newly prove**. |
| **a8→a8t import** | **NONE** — response bytes on the wire are data, not source code. |
| **contract-change mechanism** | **file-edit** on the a8 side, with **no fixed cadence** — a change takes effect on the NEXT request, with no staging or re-vendor step. **Faster to change, correspondingly HARDER to attest**, because there is no artifact boundary at which to freeze a version. |
| **INV-11/17/19 disposition** | **ENGAGED IF** fronted by the Contente rail — a legitimate non-Contente deck at a live a8-side endpoint would be REFUSED by INV-11, INV-17 and INV-19. **NOT ENGAGED IF** served through a wholly separate surface. **Required, unperformed.** |
| **C9 collision** | **YES — direct collision, and the reason it is priced at all.** C9 permits a serve-time component to decide **WHETHER** to respond; it explicitly FORBIDS it to *"rewrite, inject, template, wrap, or re-render the response body."* **A live rendering process that GENERATES the body IS a re-render by definition.** This option's core mechanism is the exact shape C9 was minted to REFUSE — unless the output is captured and frozen before the request path, at which point it is E-3. |
| **a11y consequence** *(verbatim excerpt, a11y leg E-4, `:621-646`)* | *"**Enforce**: Neither side today — SPECULATIVE… it is ALSO gated behind the C9 RESPONSE-SHAPING-ONLY constraint… A live CONTRAST CHECK that BLOCKS a bad response is C9-compatible (a gating decision); a live contrast FIX that adjusts a color before serving is NOT (a bytes-rewrite) — meaning **E-4's theoretical a11y strength is available ONLY in its GATING form, never its REPAIR form**, mirroring B-6's own C9 caveat exactly. **Palette-swap silent-fail**: **CONDITIONAL**, same shape as B-6… **Dark-mode**: … the only row in the ENTIRE 18-row set where dark-mode could be a PER-REQUEST decision rather than a build-time fork."* |
| **F-BRAND coherence** *(CORRECTED at leg 4 per PL-10)* | Most strongly coherent with **B-6** — both put their governing mechanism AT the edge; together they compose the **most invariant-and-C9-loaded corner of the whole space** (B-6 is the only B-row engaging INV-11/17/19; E-4 the only E-row colliding with C9). **Naming both at once is ONE combined risk, not two independent ones.** In tension with **B-1/B-2/B-3/B-7**'s build-time-schema stories. **ADDED THIS PACKET: also in weak tension with B-5 and B-0** — a live serve-time render needs *some* per-profile token source to render from, exactly as K-6's value-rewrite does; **B-5's "nothing shared" premise and B-0's "no contract declared" both fail to supply one.** The leg-2-engine row was silent on B-5 while leg-2-deck's K-6 named the identical need; **this corrects the asymmetry.** |
| **`legacy-floor-isolation` §2** | **Mixed — the one option where a8t-side authorship genuinely references existing a8-side machinery.** `office_runner.py` is an **operator-gated, batch, produce-then-halt** pipeline, not designed for synchronous per-request invocation. **CONSULTED / oracle-OK** if queried purely for BEHAVIOR and a new serve-time contract is authored independently. **INHERITED / REFUSAL fires** if its build-time-shaped internals are reused as-is for serve-time invocation *"because that's the runner we have."* The fork is stated, not resolved. |
| **dissent (leg-2, self-authored)** | **The option the author would most want to reject outright, said plainly:** it collides with C9 by its own core mechanism, undermines the telos's byte-identity clause unless degenerated into E-3, and introduces a live cross-org runtime coupling for an epoch whose throughline prizes *"zero regression on what already works."* Its only honest argument is **freshness** — a benefit the telos never asks for (L1 says *"byte-identical to its frozen export,"* not *"always current"*). |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:291` — 108w, VERBATIM)* E-4's core mechanism is the shape C9 RESPONSE-SHAPING-ONLY was minted to refuse: a serve-time process that generates the body is a re-render by definition. It has no `frozen_sha256` to attest until the first render is captured — at which point it is E-3 done lazily. It introduces a live cross-org runtime coupling for every request, needs a per-profile token source B-0/B-5 cannot supply, and its a11y strength exists only in gating form, never repair. Its only honest benefit is freshness, which telos L1 does not ask for ("byte-identical to its frozen export"). E-4 is enumerated so it can be seen and declined, not so it can be chosen. |

---

### E-5 — SOURCE CODE CROSSES  **[NON-VIABLE — G-24/G-29]**

| Column | |
|---|---|
| **mechanism** | The a8 inliner's source is imported, required, or copied into an a8t repo, so a8t code executes a8-authored rendering logic in-tree. |
| **what it costs** | **N/A — not priced as an engineering tradeoff, because it is NON-VIABLE, not costly.** Priced here only so the operator sees why it is excluded: it requires either an `import`/`require` of a8 source into an a8t dependency graph, or a file-copy into an a8t tree — the exact shape deck-kit's own `GOAL.md:21` names and refuses. |
| **what it forecloses** | Nothing — foreclosing is a property of a CHOSEN option; this row exists to be excluded. |
| **a8→a8t import** | **PRESENT.** Per the column rule, **PRESENT ⇒ NON-VIABLE, not costly** (G-24/G-29). **The only row in the entire packet carrying PRESENT.** |
| **contract-change mechanism** | **N/A** — the crossing object IS code, which the schema does not contemplate as a governed contract. |
| **INV-11/17/19 disposition** | **NOT ENGAGED — moot.** Excluded before any staging or serve-time question arises. |
| **C9 collision** | **N/A — moot.** |
| **a11y consequence** *(verbatim excerpt, a11y leg E-5, `:647-660`)* | *"**Where decided**: N/A — moot, for the same reason the mechanism itself is non-viable… PT-04's own checkpoint question ('is every option that imports a8 code into a8t marked NON-VIABLE rather than merely expensive?') is satisfied by E-5 carrying no priced a11y consequence at all."* · **Dark-mode**: “N/A.” · **Print**: “N/A.” |
| **F-BRAND coherence** | **Orthogonal to all eight B-rows — itself a useful finding.** No F-BRAND ruling rescues E-5; it is foreclosed by a **different axis entirely** (shape §7 Prescribed), not by F-BRAND. |
| **`legacy-floor-isolation` §2** | **INHERITED, definitionally — REFUSAL fires.** The textbook case §1.3 names. **The refusal firing is a POSITIVE result**, not a gap in this slate. |
| **dissent (leg-2, self-authored)** | There is no dissent to author FOR excluding a non-viable option; the dissent **against** the exclusion is named so the operator sees it was considered: *"it's just build tooling, not production code"* / *"a dev-dependency, not a runtime import."* deck-kit's `GOAL.md` draws **no such distinction** — *"ZERO code was copied"* applies to build-time tooling exactly as much as runtime code, and **no textual carve-out for build-only crossings exists** in G-24/G-29, `GOAL.md:21`, or `README.md:351`. |
| **dissent (leg 5)** | *(arch-adversary, leg 5, `ADVERSARY-REPORT-S4-DP-1-brand-seam-2026-09-05.md:295` — 103w, VERBATIM)* E-5 is the boundary the shape prescribes as absolute, priced only so the operator sees why it is excluded — and the dissent against the exclusion ("just build tooling") is answered by deck-kit's own `GOAL.md:21`, which draws no runtime/build-time carve-out. Its residual danger is not that anyone rules it but that it arrives unlabelled: K-6 serves a8-authored inline JS under an a8t brand and calls its import NONE; a K-5(a) seam built by copying deck-kit is E-5's mirror in the direction G-29 does not name. E-5 is the class every other row must be tested against, and this packet applied the test unevenly. |

---

## §6 CROSS-PRODUCT COHERENCE — B × K × E

**Derivation.** Built strictly from the three slates' own F-BRAND-coherence lines (§3/§4/§5),
plus the two corrections this packet applied: **B-0 added** (PL-08) and **E-4's B-5 silence
fixed** (PL-10). Legend: **C** = coherent · **~** = conditional / cost-compounding ·
**X** = in tension (not logically impossible; architecturally opposed) · **O** = orthogonal.

### §6.1 B × E (54 cells)

| | B-0 | B-1 | B-2 | B-3 | B-4 | B-5 | B-6 | B-7 | **B-8** |
|---|---|---|---|---|---|---|---|---|---|
| **E-1** nothing crosses | C | ~ | ~ | ~ | C | C | C | ~ | **~** |
| **E-2(i)** contract crosses a8t→a8 | **X** | **C** | ~ | C | ~ | **X** | ~ | C | **C** |
| **E-2(ii)** contract crosses a8→a8t | **X** | ~ | **C** | ~ | ~ | **X** | ~ | ~ | **C** |
| **E-3** artifact crosses | C | C | **C** | C | C | C | C | C | C |
| **E-4** live output crosses | **X** | **X** | **X** | **X** | ~ | **X** | **C** | **X** | **X** |
| **E-5** source crosses | O | O | O | O | O | O | O | O | O |

- **E-1's `~` against B-1/B-2/B-3/B-7/B-8** is *coherent-but-unmotivated*: those rulings put a shared contract in force that E-1 exercises **nowhere at render time**.
- **E-2(ii) is the row the slate previously lacked** — it is **B-2's natural enactment when deck-kit renders** (`C`), and **strong with B-8 if the hash is what gets pinned** (`C`). Before the DELTA, an operator ruling B-2 with deck-kit rendering **had no E cell at all**.
- **B-8's column is the mildest in the table**: it forecloses no E-position, because a content-addressed *value* contract is orthogonal to *what kind of object crosses*.
- **E-4 is in tension with 6 of 8 B-rows** — every row except B-4 (`~`) and B-6 (`C`).
- **E-5 is orthogonal to all eight**: foreclosed by G-24/G-29, a different axis. No F-BRAND ruling rescues it.
- **The B-6 × E-4 cell is the single most loaded cell in the packet**: B-6 is the only B-row engaging INV-11/17/19; E-4 is the only E-row colliding with C9. **Ruling both is ONE combined risk, not two independent ones.**

### §6.2 B × K (**54 cells** after B-8) — **NEARLY DEGENERATE, and that is the finding**

**K-6 returned to VIABLE at DELTA iteration 2 (M-1/CH-13)**, so its column is live again
and the counts below stand as originally derived. Of **54** cells, **zero** carry a hard
contradiction; only **3** carry a stated tension, and **all three are K-6's**:

| pair | disposition | why |
|---|---|---|
| **K-6 × B-5** | **X (weak)** | A value-rewrite needs *some* source of per-profile values to rewrite TO; B-5's "nothing shared" premise does not cleanly supply one. |
| **K-6 × B-0** | **X (weak)** — *added at leg 4* | Same need, same failure to supply it: B-0 declares no contract at all. |
| **K-6 × B-8** | **X (weak)** — *added at DELTA* | Same again: B-8 pins a **shape**, supplies **no values**, so it helps K-6 no more than B-4 does. **All three are weak; K-6 is viable, so none is moot.** |
| **K-2 × B-2** | **~** | Not contradiction — **cost-compounding**: generalizing the namespace AND adopting the full 122-leaf tree per profile is the most expensive additive cell in the space. |
| *all other 50 cells* | **C** | stated coherent, or at most cost-compounding, never contradictory. **B-8's six K-cells are all `C`** — neutral, since no K-row's mechanism reads or writes a pin. |

> **DEGENERACY TELL, STATED PLAINLY AS THE SYNTHESIS RULE REQUIRES.** The B × K table
> **degenerates**: 51 of 54 cells are coherent, and no cell is a hard contradiction. That
> is the anti-collapse signal the rule asks me to surface, and it cuts **two ways**, both
> of which the operator should see:
>
> 1. **The benign reading** — F-DECK genuinely is nearly orthogonal to F-BRAND. Which
>    construction layer admits variance is largely independent of who owns the token
>    contract. If so, **SLOT C is safely ruleable in any order relative to SLOT A.**
> 2. **The adversarial reading — RULED OUT AT LEG 5 (A-3), by the rite-disjoint seat, not
>    by this packet.** The concern was that a uniform table signals an under-differentiated
>    slate. The adversary's §1.2 G-K4 disposition, accepted: **45/48 coherent is evidence
>    the two axes are ORTHOGONAL, which is what independent axes SHOULD produce.** Within
>    K the rows differ materially on their own dimensions — cost (K-2 maximum → K-6
>    zero-upstream), engine scope (K-2/K-3 producer-only vs K-5(b) a8t-side), INV
>    disposition, D-3 cost. **The one dimension that tests identically across K-2..K-6 is
>    `palette-swap silent-fail: YES`** — and the packet already names why
>    (CANDIDATE-DEFER-S4-08: no contrast check exists anywhere), while **the option that
>    disrupts that dimension lives on the B/E axes (B-6/E-4), not K.** So the a11y
>    dimension is **K-irrelevant by construction, not a sign of a missing K option.**
>    The leg-4 "this packet cannot settle which" line is **withdrawn**; the seat that could
>    settle it did.
>
> **Compounding factor the adversary should weigh together with the above:** F-DECK is also
> the slate with **0/6 authored dissents** (§4 head). A uniformly-coherent table and a
> zero-dissent slate are two independent reasons to look harder at the same slate.

### §6.3 K × E (30 cells)

Derived, and **also near-degenerate** — the two axes govern different questions (which
construction layer varies vs. what crosses the boundary), so most cells compose freely.
Three cells carry real structure:

| pair | disposition | why |
|---|---|---|
| **K-5(b) × E-1** | **C — the same landed fact, twice** | Both promote the already-built `--profile-root` seam that LEG-1 measured. **Not two independent options that happen to agree**: one fact viewed through two fork-lenses. Ruling both is one decision, not two. |
| **K-5(a) × E-2(i)** | **C — the same relation, named at DELTA (A-2)** | The leg-4 packet named only the (b)/E-1 pairing as "one fact, two lenses" and left this one unnamed. **It is the identical relation**: a novel a8-side seam (K-5(a), F-DECK's construction-layer lens) and a contract crossing a8t→a8 to feed it (E-2(i), F-ENGINE's crossing-object lens) are **one decision seen twice.** |
| **K-6 × E-4** | **X** | K-6 is explicit that inverting itself to request-time collides with **C9** exactly as E-4 does. Both at request time is the C9 collision twice over. |
| **K-2/K-3/K-4 × E-1** | **~** | These are Contente-producer-scoped layers; E-1 says nothing crosses. Coherent, but the per-profile work lands entirely on the a8 side with no a8t-side benefit — cost-compounding, not contradiction. |

### §6.4 Order-dependency — the asymmetry the ruling-slots box does not otherwise show

| Slot pair | Risk | Basis |
|---|---|---|
| **SLOT D ruled BEFORE SLOT A** *(relabelled at DELTA iteration 2 — M-9/CH-19: the row's BASIS is the risky order, and the label now matches it)* | **MATERIAL** | Both E-2 sub-rows oppose B-5/B-0; E-4 opposes **7 of 9** B-rows. **Ruling SLOT D before SLOT A materially narrows the later F-BRAND choice** — which is why the §0 box now states the order **B → A → D**. |
| **SLOT C ruled AFTER SLOT A** | **VERY LOW** | 3 of 54 cells, **all three K-6**, **all weak**. **Effectively order-independent — C may be ruled at any point.** |
| **SLOT A with SLOT B** | **COUPLED, and under-flagged** | **B-0/B-3/B-4/B-6/B-7/B-8 have no home; B-1 double-homed in SLOT B's three readings** (PL-09). Filling A and B independently can produce an internally incoherent pair. |
| **SLOT C with SLOT D** | **COUPLED IN ONE DIRECTION — SLOT D SELECTS K-5's READING** (A-2). | §6.3. Ruling **E-2(i)** selects **K-5(a)**; ruling **E-1** selects **K-5(b)**. An operator ruling "K-5" alone has not chosen a reading. Otherwise LOW. |

**Safely ruleable in any order:** SLOT A with {E-1, E-3, E-5}; SLOT A with any of
{K-1..K-5}. **Order-sensitive:** SLOT D with {E-2, E-4}; SLOT C's K-6 relative to B-5/B-0.

---

## §7 THE DEFERRED a11y TERMINAL GATE — INSCRIPTION, VERBATIM

> **Pasted verbatim from the a11y leg's §C (`DP-1-draft-leg3-a11y.md:680-733`), unedited.**
> §0 carries the five rulable sentences; this is the full text.

---

> **Cross-referenced, not edited**: this inscription does not contradict, and is checked
> against, `.ledge/spikes/hosted-deck-product-epoch-F-EVIDENCE-slate.md` §4.3 "THE
> INHERITED a11y TERMINAL GATE — RECORDED, NOT WAIVED" (grep-confirmed present at that
> path, lines 863-893 of that artifact). §4.3 already establishes: the gate is D0, hard,
> zero-tolerance, all postures; it fires on rendered surfaces; nothing has rendered under
> S6; the gate is INHERITED by the DEFER-1 `/frame`, NOT WAIVED; and three a11y facts
> (sr-only receipt asymmetry, refutation-arm mislabelled-hash, print-only-affordance risk)
> travel forward with it. **This leg's inscription is DP-1-scoped (the F-BRAND/F-DECK/
> F-ENGINE build surface), a sibling gate to §4.3's WS-D-scoped one, not a restatement of
> it** — the two gates cover different eventual build surfaces off the same initiative and
> must both be satisfied independently wherever they apply.

**PRECONDITION.** Any build sprint that follows DP-1 — under whichever F-BRAND / F-DECK /
F-ENGINE option combination the operator rules — MUST NOT be considered complete,
mergeable, or servable until the ui rite's `a11y-engineer` has RUN and PASSED all four
testing-pyramid layers against the ACTUALLY RENDERED surface, not against declared tokens:

1. **Static lint** — zero tolerance: missing alt text, missing labels, invalid ARIA.
2. **Automated audit (axe-core)** — contrast ratios, landmark structure, ARIA validity,
   machine-verified against SERVED BYTES. This supersedes every number in this artifact's
   §A: §A's ratios are token-literal computations with no browser open; an axe-core run
   against a real render is the only artifact that may claim a contrast VERDICT.
3. **Interaction testing** — keyboard navigation, focus visibility/trap/return, APG
   patterns for any custom widget the chosen option introduces.
4. **Manual review** — alt-text quality, reading order, heading hierarchy, screen-reader
   announcement accuracy; the layer no automation reaches.

This is **D0**, hard, zero-tolerance, in **all** postures (`ui-ref` Quality Gate Summary:
"D0: Accessibility … Hard (always) … All"). No posture, scope, or door ruling exempts it.
The gate produces an **accessibility-report** at `.ledge/reviews/A11Y-{slug}.md` per the
a11y-engineer's standard output; that report — not this leg's §A tables — is the
attestable artifact for any future close/handoff gate.

**WHAT IS TRUE TODAY.** Nothing in this initiative has rendered. Zero of the four layers
above has run. This artifact's §A tables are file-read hex extractions plus deterministic
WCAG luminance arithmetic, explicitly flagged `[computed]` throughout, never `[live-axe]`.
Confirmed by direct inspection this session: **no contrast receipt exists in deck-kit's
closed 12-id claim vocabulary** (`deck-kit/src/receipts/receipt.js:47-60`) **nor anywhere
in the Contente build tree** (zero hex/contrast logic, grep-confirmed, S4-A-P-11). **10 of
18 measured cells in §A already fall below their applicable AA threshold on token literals
alone** — a floor, not a ceiling, on what a live axe-core run would find, since a rendered
DOM can introduce additional failures (font substitution, anti-aliasing, opacity/blend
compositing) that a static hex comparison cannot.

**SILENCE IS NOT A PASS.** The gate has not fired in S4 because it has no rendered surface
to fire on — not because a surface has been checked and found conformant. Per the S6
slate's own §4.3 framing (cross-referenced above), this absence must never be read
downstream as "a11y was checked and is fine." It was not checked. It cannot be checked
before something renders.

---

**Packet-level rider (leg 4, not part of the verbatim inscription).** The gate above is
registered as **CANDIDATE-DEFER-S4-05** (§10) so it survives into the wave register with a
watch-trigger, rather than living only inside this packet.

---

## §8 EVALUATION-DEPTH SYMMETRY

Per `option-enumeration-discipline` §6. **This is the packet author's own mechanical tally,
not an external audit** — §6 of that skill reserves the depth audit to the external critic.

| Option | Rows | Dissent (authoring seat) | Dissent (leg 5, verbatim) | Viability |
|---|---|---|---|---|
| **B-0** | 11 | yes (leg 4), ~75w | **100w** | viable |
| **B-1** | 10 | yes (leg 1), ~90w | **107w** | viable |
| **B-2** | 10 | yes (leg 1), ~111w | **103w** | viable |
| **B-3** | 10 | yes (leg 1), ~101w | **106w** | viable |
| **B-4** | 11 | yes (leg 1), ~122w | **102w** | viable |
| **B-5** | 12 | yes (leg 1) + counter, ~91w | **110w** | viable |
| **B-6** | 12 | yes (leg 1), ~105w | **111w** | viable |
| **B-7** | 10 | yes (leg 1), ~95w | **108w** | viable |
| **B-8** *(DELTA)* | 13 | yes (leg 1 seat), ~150w | **116w** (DELTA §4, `:519`, VERBATIM) | viable |
| **K-1** | 9 | no — by charge | **100w** | viable |
| **K-2** | 10 | no — by charge | **110w** | viable |
| **K-3** | 10 | no — by charge | **101w** | viable |
| **K-4** | 11 *(+1, C-4 restore)* | no — by charge | **93w** | viable |
| **K-5** | 12 *(+1, one-id disposition)* | no — by charge | **105w** | viable |
| **K-6** | 11 | no — by charge | **104w** | **viable — REFUSAL-exposed** (legacy-floor §2 :696) |
| **E-1** | 11 | yes (leg 2), ~96w | **104w** | viable |
| **E-2(i)** | 11 | yes (leg 2), ~88w | **114w** | viable |
| **E-2(ii)** *(DELTA)* | 10 | no — leg-5 slot by charge | **111w** (DELTA §4, `:767`, VERBATIM) | viable |
| **E-3** | 11 | yes (leg 2), ~91w | **103w** | viable |
| **E-4** | 12 | yes (leg 2), ~84w | **108w** | viable |
| **E-5** | 11 | yes (leg 2), ~78w | **103w** | **NON-VIABLE** (import PRESENT) |

**21 rows across three forks.** 19 carry a verbatim leg-5 dissent; **2 carry an EMPTY
reserved slot by design** (B-8, E-2(ii) — both minted at this DELTA, after the critique
that would have dissented against them).

### Flags (>2× asymmetry)

| # | Flag | Detail |
|---|---|---|
| **DS-1** | **DISCHARGED AT DELTA.** | It fired at leg 4: F-DECK carried **0/6** authored dissents against 8/8 and 5/5 — an infinite ratio. **The arch-adversary authored all six at leg 5** (93-110w), carried verbatim. Its own words: *"DS-1 (F-DECK 0/6) is discharged by K-1..K-6 below."* **SLOT C is no longer ruled against a slate with zero adversarial pressure.** |
| **DS-2** | does not fire | Within F-BRAND leg-5 dissents: floor **100w** (B-0), ceiling **111w** (B-6) = **90%**. Authoring-seat dissents: floor ~75w, ceiling ~150w = 50%, **at** the threshold, driven by B-8's length (mandated, see DS-5). |
| **DS-3** | does not fire | Within F-ENGINE: floor **103w**, ceiling **114w** = **90%**. Row counts 10-12. |
| **DS-4** | **PARTIALLY DISCHARGED** | Leg 4 flagged that B-0's only dissent was authored by the seat that added it. **The adversary independently authored B-0's** (100w) and states it is *"independent of the leg-4 self-authored one"*. **B-8 now inherits the same flag** — its only dissent is the leg-1 seat's, against its own late addition. **Priority target for the DELTA re-read.** |
| **DS-5** | **noted, does not fire as bias** | **B-8 carries 13 rows against B-1/B-2's 10.** The asymmetry is **mandated, not padding**: the DELTA condition required a gap option to carry the base schema **plus** CSS-emission, K/E coherence, a SLOT-B mapping, an explicit distinctness proof against all eight incumbents, and a receipted substrate correction. **No incumbent row was shortened**, and `option-enumeration-discipline` §6 tests for a **recommended** option being *under*-argued — B-8 is not recommended and the asymmetry runs the opposite way. |
| **DS-6** | **RAISED AT DELTA-1, SLOTS FILLED AT DELTA-2 — the flag STANDS as a structural note, not as absence** | B-8 (`:519`, 116w) and E-2(ii) (`:767`, 111w) now carry the arch-adversary's DELTA-authored dissents, verbatim. **What DS-6 continues to name is not absence but PROVENANCE:** both options were minted in response to the critique, and **both dissents were authored by the seat that demanded the options** — self-critique by proposer. **The operator weights accordingly.** Every option minted in response to a critique is, by construction, critiqued only by its own demander; that is the structural cost of the two-iteration protocol, and it is stated rather than hidden. |

**Cross-slate row-count symmetry holds** (9-13 rows everywhere). **The leg-4 asymmetry —
entirely in dissent authorship, entirely on F-DECK — is discharged.** What remains is
**DS-6**: the two DELTA-minted rows now carry dissents, authored by the seat that demanded them (self-critique by proposer — weight accordingly).

---

## §9 MEASUREMENTS APPENDIX

> By reference to receipt ids with `path:line`. **Probe transcripts are not reproduced** —
> the S4-*-P-NN ids below are the citable anchors. Every number here is a **measurement
> against a stated threshold, never a WCAG pass/fail VERDICT** on any rendered surface.

### §9.1 Served-surface table — UV-P-F-1 slot now FILLED

**Receipt `S4-DISP-P-1`** (dispatcher, SVR, 2026-09-05) discharges UV-P-F-1, which the
subtractive leg had to leave open (no hashing tool that session; its sha claims were
string-matches against already-computed digests, never re-derivations).

| # | Question | Contente deck (served, deck-host rail) | a8t / deck-kit deck (built) |
|---|---|---|---|
| (i) | artifact + sha256 | `public/761ebfd8a7e1ae5bb7442c8dc2154f6d/index.html` → **`0adebd0f779d6040f2a3061f7b6829677d335fac58f0ba6c75606cde8c624960`**, **independently re-derived** by `shasum -a 256` (S4-DISP-P-1). **Equals** `config/deck-manifest.json:81` `frozen_sha256` for slug `761ebfd8…` (`:77`) **and equals** the S1 VERDICT record at `/Users/tomtenuta/Code/a8/a8/repos/autom8y/.ledge/reviews/VERDICT-cloudflare-pages-host-decks-2026-09-05.md:274`. | `deck-kit/dist/deck-kit-fixture.html` → **`a35207252c780f1d04b755794104068012a61352b643cd211edf8ab9ca2ef9dd`** (S4-DISP-P-1). **NO ledger entry exists for this path in any artifact read across all seven legs. None is invented here.** |
| (ii) | which profile, how known | **Contente** — `--navy-*`/`--blue-*` names; zero tenuta/a8t signature hexes (S4-F-P-5) | **tenuta** — from the artifact's own inlined provenance comment (*"group = 'tenuta' in identity.json"*) and its "Slate & Madder" palette (S4-F-P-10/11), **despite the file's name saying "fixture"** — a naming/content mismatch, flagged not ruled |
| (iii) | `:root` custom properties | **122** across 5 `:root{}` blocks (S4-F-P-5) | **77** across 4 `:root{}` blocks (S4-F-P-11) |
| (iii) | bare-hex tokens | **63 total — 31 INSIDE the `:root` blocks, 32 OUTSIDE** (17 in inline `<script>` JS literals, 15 in `style=""` attributes and `var(--x, #hex)` fallbacks) (S4-F-P-6) | **8 total, ALL 8 inside the single primitives `:root` block; ZERO outside** (S4-F-P-12) |
| (iii) | `--space-4` in served/built bytes | **`16px`** — confirmed in the served artifact at `:3265` (S4-F-P-8) **and independently re-confirmed by the dispatcher, 1 occurrence** (S4-DISP-P-1) | **absent entirely** (S4-F-P-13); deck-kit bridges layout via its own `--dk-*` tokens |
| (iv) | `http(s)://` in `src`/`href` | **0** (S4-F-P-7) | **0** (S4-F-P-14) |

**Parity caveat, carried VERBATIM as the dispatcher requires.** The VERDICT's own record
proves *"the rail is faithful to deck-host's ledger, **NOT** the ancestor arm-2 predicate
(producer-frozen Asana attachment), which **S1 REFUTED at N=2**."* Any citation of parity
in this packet is scoped to the former and never the latter.

**Related, and still open:** `advantage-rc` carries **no built deck HTML at all**
(S4-F-P-9). The `--space-4` **collision** — `1rem` (a8t `scale.css:22`) vs `16px` (Contente
`spacing.css:10`) — is a **token-source** fact; only the Contente half is observable in
built/served bytes, because deck-kit's artifact declares no `--space-4` (S4-C-P-10 +
S4-F-P-8/13). Numerically coincident today at a 16px root font-size; **not the same
declaration**, and resolved by plain cascade last-rule-wins if both `:root` blocks ever
co-occupy one document.

### §9.2 Contrast matrices — by reference

**Method** (a11y leg §A.0): WCAG 2.2 relative-luminance arithmetic via a Node one-liner over
hex literals **file-read** from `brand-tokens/profiles/*/css/*.css`. **No browser. No live
render. No verdict.** Receipts **S4-A-P-1 … S4-A-P-12**.

**Within-profile failures (5)** — a11y leg §A.3:

| id | pair | ratio | threshold | note |
|---|---|---|---|---|
| **T-5** | tenuta caption `#616C87` on sunken `#E7E4DB` | **4.13** | 4.5 | **The sharpest finding.** Structurally certain, not a guess: `figure.exhibit` is `background: var(--dk-bg-sunken)`; `figcaption.source` is `color: var(--dk-caption)` with no background override — and `deck.source-line-per-exhibit` **REQUIRES** exactly one `figcaption.source` per `figure.exhibit` (S4-A-P-9). **This is the CURRENTLY-SHIPPED, production-served profile.** Tenuta's own in-file comment documents 4.6 against **PAPER** — verified correct — but the template places the caption on **PAPER-DEEP**, a background the profile's own contrast table never evaluates. |
| **A-2** | a8t muted `#8A8680` on `#F9F8F7` | **3.41** | 4.5 | below for normal text; a8t's CSS documents no size restriction |
| **F-2** | fixture `--outline-default` `#9E9E9E` on `#FFFFFF` | **2.68** | 3.0 | below, **in the token's own real non-analog role** |
| **F-3** | fixture link `#009688` on `#FFFFFF` | **3.67** | 4.5 | below for normal text |
| **F-4** | fixture CTA `#FFFFFF` on `#009688` | **3.67** | 4.5 | the Material teal-500/white caveat, verbatim in this profile |

**Cross-profile swap failures (5)** — a11y leg §A.5. The cleanest demonstration:
**tenuta text-on-accent `#F3F1EB` on lotusun accent-bg `#F26722` → 2.76**, versus lotusun's
**own** CTA pairing at **5.75**. Swapping **only the foreground half**, keeping everything
else fixed, collapses a passing pair to a severe fail **with no code change, only a value
substitution.** Also failing: fixture-link→tenuta-surface **3.25**; a8t-muted→tenuta-surface
**3.20**; fixture-muted-analog→tenuta-surface **2.37**; fixture-focus-analog→tenuta-surface
**2.37**.

**Total: 10 of 18 cells below their applicable AA threshold, on token literals alone.**

**GAPs where no token exists** (no number fabricated): lotusun-brand and lotusun-cream
declare **no** muted-text, **no** caption, and **no** focus token. The two profiles'
`colors.css` are **byte-identical except one source-comment line** (S4-A-P-8), so every
lotusun finding applies identically to both.

**The naming finding that is sharper than the arithmetic** (PL-13): deck-kit's `deck.css`
`var()` colour-role targets are **tenuta's semantic key names verbatim**; of the 13
colour-role names, **0** are declared by any non-tenuta profile (a8t shares 4 of 8
typography names only) (S4-A-P-1..7, S4-A-P-13). Unresolved `var()` references fall back to
inherited/initial values — **total collapse of the intended colour relationship, not a
numerically-poor one.** What a browser actually paints under that mismatch is **UV-P** (§11).

---

## §10 CANDIDATE DEFER ENTRIES — `status: DRAFT`

> **S4 does NOT append to the wave register.** These are **candidates only**, authored in
> the full 7-field grammar so the seam can append them **LAST, after S6's**. No id below is
> minted, watched, or owned until that append happens.

**Grammar:** `{ id · statement · watch-trigger · owner · consumer-action · receipt ·
status }`

| # | id | statement | watch-trigger | owner | consumer-action | receipt | status |
|---|---|---|---|---|---|---|---|
| 1 | **CANDIDATE-DEFER-S4-01** | deck-kit's hardcoded **3-file** profile-CSS layer contract (`build.mjs:91` reads exactly `primitives.css`, `semantic.css`, `type.css`) is matched by **only 1 of 5** profiles (tenuta). a8t lacks `type.css`; fixture and both lotusun profiles share none of the three names. | Any attempt to build a non-tenuta profile with deck-kit, OR any change to `readProfileCss()`'s file list. | ui rite (stylist) | Before pointing `--profile-root` at a non-tenuta profile, run the build and observe the exit code/stderr — the predicted failure is **not** yet executed-and-observed. | S4-C-P-4, S4-C-P-5 | **DRAFT** |
| 2 | **CANDIDATE-DEFER-S4-02** | `--space-4` is declared on **both** sides with different literals — `1rem` (a8t `scale.css:22`) vs `16px` (Contente `spacing.css:10`) — under the **same bare name**, with **no namespace prefix and no scoping mechanism on either engine**. Coincident today only at a 16px root font-size. | Any change to either side's base font-size, OR any surface that loads both `:root` blocks in one document (a brand-comparison tool, a preview gallery). | ui rite (stylist) | Resolve by plain CSS cascade last-rule-wins, **silently** — there is no gate. Treat any dual-profile surface as requiring E1/E3 scoping work first. | S4-C-P-10, S4-F-P-8, S4-DISP-P-1 | **DRAFT** |
| 3 | **CANDIDATE-DEFER-S4-03** | The a8 source-of-record has **already drifted past the shipped tag**: `git diff --numstat v1.0.0 HEAD -- tokens.schema.json` → **122 insertions / 205 deletions**, 397 → 314 lines, and the inline `definitions` block is **gone at HEAD**, restructured toward a remote `$ref` at `tokens.autom8y.dev`. Consumption is pinned to `v1.0.0`; the source has moved. | Any re-vendor, any new tag on `autom8y/contente-tokens`, OR any option ruling that names "the a8 contract" without specifying which. | 10x-dev rite / operator | **Any "share a contract" ruling must name WHICH contract** — `v1.0.0` inline-definitions or SOR-HEAD remote-`$ref`. They are different contracts. | S4-D-P-21, S4-D-P-22, S4-D-P-23 | **DRAFT** |
| 4 | **CANDIDATE-DEFER-S4-04** | **In-place patch of the git-tracked vendored copy is a real, available, and completely UNGATED change mechanism.** No lockfile at the vendor site, no `integrity` field, no `autom8y-asana` CI check against `v1.0.0`, and the package's own `--check` guard **was never published** — so a patch that silently forks the bytes from the tag their manifest still names would be **structurally invisible to every guard in the system**. Never exercised to date (the vendored path has one commit, a pure add). | First `M` (modify) on any path under `vendor/deck-producer/node_modules/@autom8y/contente-tokens/`. | 10x-dev rite / operator | **Any option treating the a8 side as immutable is relying on convention, not on a gate.** A byte-comparison check against `v1.0.0` is the smallest closing mechanism. | S4-D-P-05, S4-D-P-10, S4-D-P-11, S4-D-P-14, S4-D-P-28 | **DRAFT** |
| 4b | **CANDIDATE-DEFER-S4-04 — cross-reference added at DELTA** | **B-8 (§3) is the F-BRAND position that CLOSES this defer.** It is the only option in the slate under which the ungated in-place vendored fork becomes detectable — by extending the pinned-value check to the vendored copy's `definitions` subtree. **Cross-reference only: nothing is scheduled, B-8 is not ruled, and B-8's own dissent notes the vendored-copy check is work B-8 does not itself schedule.** | — | — | — | — | **cross-ref** |
| 5 | **CANDIDATE-DEFER-S4-05** | **The a11y terminal gate (D0, hard, zero-tolerance, all postures) is INHERITED by any build sprint following DP-1 and is NOT WAIVED.** Four testing-pyramid layers must run and pass against the actually-rendered surface. Zero have run; nothing has rendered. **Silence is not a pass.** | The first render of any surface under any DP-1 option ruling. | ui rite (a11y-engineer) | Produce `.ledge/reviews/A11Y-{slug}.md`; **that report, not §9's tables, is the attestable artifact** for any close/handoff gate. | §7 verbatim inscription; S4-A-P-10, S4-A-P-11 | **DRAFT** |
| 6 | **CANDIDATE-DEFER-S4-06** | deck-kit's `deck.css` `var()` targets match **tenuta's declared custom-property names only**; of the 13 colour-role names, **0** are declared by any non-tenuta profile (a8t shares 4 of 8 typography names only). Unresolved `var()` references fall back to inherited/initial values — **collapse of the colour relationship, not a poor ratio.** | Any build of a non-tenuta profile with deck-kit, OR any addition of a 6th profile. | ui rite (stylist + a11y-engineer) | Read computed styles from an actual render before trusting any cross-profile contrast number; **§9.2's cross-profile matrix presumes names resolve, which they do not.** | S4-A-P-1 … S4-A-P-7 | **DRAFT** |
| 7 | **CANDIDATE-DEFER-S4-07** | **INV-11's `classify()` keys ONLY on the `deck_template` string, never on rendered CSS or bytes** — a *verified* structural fact. A profile-swapped deck served through an existing pinned template therefore **passes INV-11 without ever being classified as a new template**. Bites K-5(a) and, more sharply, K-6 (which makes no claim to be a new template at all). | Any build under K-5(a) or K-6, OR any change to `src/audience/classify.js`. | security rite / operator (WS-GUARD C-1..C-5 reserved to operator/PT-01) | Determine whether this is intended, permitted under WS-GUARD **C-3** (*"values are consumed from the producer, never minted locally"*), or a silent gap. **Not this packet's call.** | S4-K-P-12, S4-K-P-13 | **DRAFT** |
| 8 | **CANDIDATE-DEFER-S4-08** | **No contrast check exists anywhere on either side.** deck-kit's closed 12-id claim vocabulary contains zero contrast-related id; the Contente build tree contains zero hex/contrast logic. **16 of 18 option-rows can silently fail a palette swap today**, independent of which fork option is ruled. | Any option ruling that cites an a11y benefit as a reason. | ui rite (a11y-engineer) | Treat every "a11y consequence" cell claiming an available benefit as **available-but-unbuilt**; only B-6 and E-4 have an axis position that could structurally prevent the failure, and **neither has built one**. | S4-A-P-10, S4-A-P-11, a11y leg §B.4 | **DRAFT** |

---

## §11 UV-P REGISTER

### §11.1 DISCHARGED this wave (7)

| id | origin | disposition | discharging receipt |
|---|---|---|---|
| **UV-P-S4-1** | leg-1 `:680` — `e15ea4db`'s referent | **DISCHARGED.** It **is** the DTCG envelope: the a8 SOR's `dtcg-envelope.schema.json` **and** fe-skeleton `origin/main`, byte-identical, both git blob `f9ea4c44…` = the `pinned_blob_sha` at `contente-tokens/dtcg-envelope.pin.json:3`. **Leg-1's negative result was correct and its scope was the reason** — the file postdates `v1.0.0` and is absent from the vendored copy, the only surface leg-1 could see. | **S4-D-P-26** |
| **UV-P-S4-2** | leg-1 `:681` — "changeable **only** by an upstream publish" | **DISCHARGED — REFUTED on its operative word.** "only" fails (mechanism (ii) exists, in-tree, ungated); "publish" is the wrong noun (it is `git tag`, same operator). What survives: it is genuinely not a one-file edit *at the consumption site*. | **S4-D-P-10/11/13/15/20/28** |
| **css UV-P #1** | css leg `:330-335` — the SOR's location | **DISCHARGED.** It **is** a sibling a8-org repo **and it is checked out**, two directories from the vendored copy the leg inspected. | **S4-D-P-16, S4-D-P-17** |
| **css UV-P #2** | css leg `:337-341` — registry or other mechanism | **DISCHARGED without a network call — the third branch.** Neither public nor private registry; git tag over `git+ssh`, then a committed vendored copy. `"private": false` confirmed **non-probative**. | **S4-D-P-04/13/14/15/20** |
| **UV-P-F-1** | subtractive §E.3 — served-artifact byte-identity | **DISCHARGED (dispatcher, SVR).** Hash **independently re-derived**, equals ledger `frozen_sha256` and the S1 VERDICT record; `--space-4: 16px` re-confirmed in served bytes. deck-kit's built artifact hashed; **no ledger entry exists for it and none is invented.** | **S4-DISP-P-1** |
| **UV-P-6** | shape S4 `uvp_home` | **NOT discharged by this packet** — listed here only to state that plainly, so its absence is not mistaken for closure. | — |
| **(recorded)** | leg-1 F5's actor-vs-actor reading | **Superseded, not discharged** — re-named per **PL-02**, not retired. The cost survives under a corrected name. | S4-D-P-24 |

### §11.2 OPEN — riding forward into leg 5 and beyond

**C-10 discharged: every row below carries the frozen `[UV-P: … | METHOD: … | REASON: …]`
syntax.** The leg-4 table carried claim + prose-reason but **no METHOD field**, which is
not conformant to `structural-verification-receipt` §1.

| id | frozen UV-P label |
|---|---|
| **UV-P-S4-E-1** | `[UV-P: deck-kit's landed surface (DK-001 + DK-005) suffices for every future profile, not only the tenuta pilot \| METHOD: deferred — read DK-002/003/004's scope definitions and map them against the epoch's five-profile list \| REASON: deck-kit is consult-never-inherit reference substrate for this wave, not a build target any leg may deepen; PL-13 makes the claim materially more doubtful, not less]` |
| **UV-P-S4-E-2** | `[UV-P: no a8-side infrastructure supports synchronous per-request rendering (E-4's precondition) \| METHOD: deferred — exhaustive search of autom8y-asana for a live HTTP-serving render endpoint (Worker, Lambda, always-on service) \| REASON: reads were scoped to the dispatch's named files; not load-bearing, since E-4's cost is dominated by the C9 collision regardless of whether such infra exists or must be built]` |
| **UV-P-S4K-1** | `[UV-P: a K-5(a) seam keeping the same deck_template while swapping token values would pass INV-11 unflagged \| METHOD: deferred — build the seam and run the fence against its output, or read a built instance \| REASON: structural inference from the VERIFIED classify() signature (S4-K-P-13, keys on deck_template only), not an observation of a live seam; nothing is built at RUNG authored]` |
| **UV-P-S4K-2** | `[UV-P: serving a per-profile deck through the Contente rail is a request WS-GUARD C-3 permits at all, independent of INV-11 \| METHOD: deferred — full read of the WS-GUARD C-1..C-5 contract text \| REASON: C-1..C-5 are RESERVED TO OPERATOR/PT-01 per shape §7 Prescribed and out of scope for every leg in this wave; the packet quotes C-3 only as it appears in config/producer-audience-map.json's own comment (A-6)]` |
| **UV-P-F-2** | `[UV-P: deck-kit/dist/deck-kit-fixture.html is the artifact served at any live capability URL \| METHOD: deferred — locate a ledger row mapping this path to a served slug, or fetch the live URL \| REASON: browser tooling unavailable and live fetch forbidden at this rung; S4-DISP-P-1 hashed the file but found NO ledger entry, and none is invented]` |
| **UV-P-F-3** | `[UV-P: the 31/32 in-root/out-of-root hex split in the served Contente artifact is exhaustive, not sampled \| METHOD: deferred — a scripted second-pass re-sum of the same deterministic grep query \| REASON: the tally was hand-reproduced from deterministic grep output by a leg with no Bash tool; residual risk is arithmetic transcription, not query nondeterminism]` |
| **UV-P-a11y-1** | `[UV-P: what a browser actually PAINTS when deck-kit's deck.css colour-role var() names fail to resolve against a non-tenuta profile \| METHOD: execute node deck-kit/bin/build.mjs --profile-root <profile-dir> per non-tenuta profile and read computed styles in a browser \| REASON: nothing renders at RUNG authored and browser tooling is unavailable this session; this is the HIGHEST-VALUE open UV-P in the packet — it gates how PL-13 and CANDIDATE-DEFER-S4-06 are read]` |
| **UV-P-a11y-2** | `[UV-P: WCAG 2.4.11 Focus Not Obscured compliance for any deck-kit-rendered slide, any profile \| METHOD: render, interact via keyboard, observe whether the focus indicator is ever covered by an overlapping element \| REASON: a layout property no CSS-literal read can confirm or refute; nothing renders at RUNG authored]` |
| **UV-P-a11y-3** | `[UV-P: any rendered/live WCAG pass-fail VERDICT, for any profile, any pair, on actually served bytes \| METHOD: axe-core or manual contrast measurement against a live browser render \| REASON: RUNG authored; every §9 number is a measurement against a stated threshold, explicitly never a verdict — the §7 terminal gate is the only artifact that may claim one]` |
| **UV-P-a11y-4** | `[UV-P: whether lotusun's rendered links carry a non-colour distinguishing cue satisfying WCAG 1.4.1 \| METHOD: read the component CSS that applies --primary to an <a> element, or render and inspect \| REASON: only colors.css was read; --primary and --foreground are the SAME literal #6B1B69, so a link can clear 4.5:1 (it does, 9.25) and still fail 1.4.1]` |
| **UV-P-a11y-5** | `[UV-P: whether any profile or engine's @media print block declares different colour values than the on-screen :root the §9 computations use \| METHOD: grep @media print across all profile CSS and deck-kit's deck.css; diff against on-screen values \| REASON: not performed this wave; flagged per-row under "print consequence" as a structural gap, not resolved]` |
| **UV-P-a11y-6** | `[UV-P: whether any brand-tokens CI step re-runs tenuta's own documented contrast math on every commit \| METHOD: search brand-tokens CI config and package.json scripts for a contrast-computation step \| REASON: no such step was named in the files read, but a dedicated CI-config grep was not run; a comment is not a machine gate]` |
| **UV-P-pub-1** | `[UV-P: whether https://tokens.autom8y.dev/dtcg-envelope.schema.json resolves to a live document \| METHOD: HTTP GET of that URL, or a DNS/hosting-config read for tokens.autom8y.dev \| REASON: network fetch is an explicit DO-NOT at this rung; the $ref is receipted at SOR HEAD but resolvability is UNRESOLVED-THIS-SESSION and asserted neither way. LOAD-BEARING for B-7, B-8 cost row (d), E-2(ii), and CANDIDATE-DEFER-S4-03]` |
| **UV-P-pub-2** | `[UV-P: whether inline.mjs's divergence from its design-system origin is intentional adaptation or unreconciled drift \| METHOD: read the commit that introduced each side and compare intent, or ask the operator \| REASON: the byte divergence is receipted but design intent is not recoverable from artifacts alone — an escalation-class question code evidence cannot settle]` |

| **Carried under Gate C** | **UV-P-1, UV-P-5, UV-P-7, UV-P-8** (H2 §5) | Ride unchanged. **UV-P-1 (DW-7) remains an OPEN SEND-BLOCKER**; **UV-P-5** (account ownership) is the operator's first question at DP-2, untouched here. |

---

## §12 RECEIPT INDEX

**Leg-local SVR receipt namespaces, NOT frame G-anchors.** Only the frame mints G-NN, and
**no wave in S4 edits the frame**. All probes run **2026-09-05** against
`s3/ws-c-fence-baseline @8d063ba` and the sibling repos at the heads recorded below.

| namespace | leg | count | scope |
|---|---|---|---|
| **S4-P-01 … S4-P-20** | leg 1 (design-system-steward) | 20 | brand-tokens profiles; both schemas' hashes and root keys; the byte-identical `definitions`; `_ds_manifest.json`; audience map; deck-kit head/ancestry; G-4 and G-29 anchor resolution **at the pin vs at head**. **DELTA (+5, PL-16):** `S4-P-16` a8t sync-gate hashes the WHOLE FILE (`sync-gate.mjs:30-33,70-72`) · `S4-P-17` a8 SOR runs the same whole-file algorithm on its own copy (`sync-gate.mjs:35-38,63-65`) · `S4-P-18` the two pins hold DIFFERENT values (`0967c77d…` vs `f9ea4c44…`) · `S4-P-19` `proof-sync-gate.mjs` is a fixture canary that never points at `PKG_ROOT`; `ci.yml:47` runs the canary · `S4-P-20` the vendored copy has no pin, no scripts, no envelope schema |
| **S4-E-P-1 … S4-E-P-8** | leg 2 (rendering-architect) | 8 | `resolve-deck.mjs` anchors; deck-kit head + `--profile-root`; C9 clause verbatim; `office_runner.py` reserved-lever boundary; the frame's two-engine table |
| **S4-K-P-1 … S4-K-P-19** | leg 2 (component-engineer) | 19 | audience map; `--profile-root`; `engine.js` provenance; `_ds_manifest.json` 11 components; templates; `export/`; **`classify()` keys only on `deck_template`** (S4-K-P-13); advantage-rc manifest 24/`ex`. **DELTA (+2, PL-17):** `S4-K-P-18` Contente's `_ds_bundle.js` marker appears **once, inline** inside the frozen `export/` artifact · `S4-K-P-19` G-29's operative text has **three verbs** — *"imported, required, or pasted"* (`README.md:350-352`) |
| **S4-C-P-1 … S4-C-P-14** | leg 2 (stylist) | 14 | CSS-canonical doctrine **both sides**; deck-kit's 3-file contract; **only tenuta matches**; `checkHexFree()`; **zero hex logic in the Contente tree**; `--space-4` collision; `prefers-color-scheme` absent both sides |
| **S4-F-P-1 … S4-F-P-15** | leg 3 (frontend-fanatic) | 15 | `public/` 9 slugs; manifest 9 decks; served-deck property/hex counts; zero external refs both artifacts; deck-kit fixture carries **tenuta** identity |
| **S4-A-P-1 … S4-A-P-13** | leg 3 (a11y-engineer) | 13 | `deck.css` bridge variables; all five profiles' alias tables; **lotusun brand/cream byte-identical but for one comment**; `deck.source-line-per-exhibit`; **zero contrast id in the closed 12-id vocabulary**. **DELTA (C-5):** `S4-A-P-13` the corrected per-profile name fractions — `deck.css` exposes **21** profile-facing names (13 colour-bearing + 8 non-colour); tenuta **13/13 + 8/8**; a8t **0/13 colour + 4/8 typography** (`scale.css:8,13-14,16`); fixture and both lotusun profiles **0/13 + 0/8** |
| **S4-D-P-01 … S4-D-P-38** | leg 3 (publish-path) | 38 | vendored artifact 13/13 byte-exact to `v1.0.0`; **SOR located**; no publish workflow; **four-way `definitions` match**; SOR drift 122/205; **producer never reads the schema**; coupling score; the change-mechanism triple |
| **S4-DISP-P-1** | dispatcher (SVR) | 1 | **UV-P-F-1 discharge** — served-artifact hash re-derived, equals ledger and VERDICT; `--space-4: 16px` in served bytes; deck-kit fixture hashed, **no ledger entry** |

**Total: 128 leg-local receipts + 1 dispatcher receipt** (+8 at the DELTA: S4-P-16..20, S4-K-P-18/19, S4-A-P-13). Probe transcripts are deliberately
not reproduced (§10 size rule); each id above is the citable anchor.

---

## §13 SCOPE FENCE AND SELF-ASSESSMENT

### §13.1 What this packet did NOT do

- **Answered no fork.** F-BRAND, F-DECK and F-ENGINE are all **HOSTED, none ANSWERED**. All four ruling slots are **EMPTY**.
- **No ranking, no recommendation, no "recommended" column** — and §2.2 forbids adding one.
- **Edited no draft.** The seven `.sos/wip/` drafts are read-only inputs; every correction is recorded in §1 as a **premise-ledger row**, never applied by editing the source.
- **Touched no file but this one** — and nothing else in `autom8y-asana`, whose tree carries uncommitted operator-pending edits.
- **No `git stash` / `checkout` / `reset`** anywhere. Every git call across every repo was a read.
- **No browser, no live fetch.** `tokens.autom8y.dev` is recorded **UNRESOLVED-THIS-SESSION** (UV-P-pub-1), asserted neither way.
- **Appended nothing to the wave register.** §10 entries are **CANDIDATE, `status: DRAFT`**, for the seam to append **last, after S6's**.
- **Ruled no T7 reading.** No option is stated differently under either.
- **Did not re-open** Option B / CH-01 / universal-deck / WS-GUARD (§7.1 settled), and did not enforce WS-GUARD C-1..C-5 (reserved to operator/PT-01).
- **Did not re-schedule LEG-1 as build.** It is measured (G-33/G-37/G-38, now byte-corroborated by S4-DISP-P-1), never re-scheduled.
- **Did not edit `brand-tokens` or any schema.** Authorizing a schema change **is precisely DP-1's ask**, and it is the operator's.

### §13.2 Self-assessment — **MODERATE, capped**

Per `self-ref-evidence-grade-rule`. **This packet does not attest its own completeness.**
That is the **arch-adversary's at leg 5** (`delta_pass: 2` — the two-iteration loop is CLOSED) and **PT-04**'s hard gate after
S4, whose question is whether the slates are *"exhaustive, or a recommendation wearing a
slate's costume."* Every option row carries an **EMPTY labelled leg-5 dissent slot**.

**Named for the adversary's attention, in priority order:**

1. **§6.2's degeneracy tell + §8's DS-1 flag land on the SAME slate.** B × K is 45/48
   coherent AND F-DECK carries 0/6 authored dissents. Two independent signals pointing at
   F-DECK. Either the axes really are orthogonal, or the K-slate is under-differentiated on
   the dimension F-BRAND varies. **This packet cannot settle which.**
2. **B-0 is a leg-4 addition with a leg-4-authored dissent (DS-4).** The seat that added
   the option also authored its only adversarial pressure — structurally weaker scrutiny
   than a peer's. **Priority target.**
3. **PL-09: 5 of 8 SLOT-A options have no home in SLOT B's three readings.** A "ten-minute
   ruling" filling A and B independently can produce an internally incoherent pair. This
   packet **adds no reading and removes none** — the operator rules the form.
4. **K-5's one-id determination** (§4 head). The axis position genuinely does not differ, so
   one id is right by the stated rule — but this is the one place a single id does double
   duty across two fork-lenses, and the sub-rows' cells diverge materially.
5. **PL-13 may be the most consequential finding in the wave and it arrived late**, from a
   leg (a11y) whose nominal remit was contrast. It re-prices K-5(b) and E-1 — the two rows
   that promote the already-built seam — and it is grounded in a **computed set comparison,
   not a render** (UV-P-a11y-1 is the discharge path).
6. **Every "a11y consequence" cell except B-0's is VERBATIM** from the a11y leg's 20 rows.
   **B-0's is DERIVED** (no a11y row exists for an option added at leg 4) and is labelled as
   such in its own cell — the one place the packet's a11y text is not quoted.

**RUNG = `authored`.** This packet advances no telos leg.
`.know/telos/hosted-deck-product-epoch.md` keeps `shipped: MISSING` /
`verified_realized: UNATTESTED`; **nothing in this packet alters it.** Per **LEG-3
REFUSED**, no build branch opens on this lineage — every option above is a design whose
build the operator gates separately, at DP-1.


---

### §13.3 DELTA disposition — C-1..C-12, A-1..A-9

**This packet does NOT attest that these conditions are cleared.** Only the rite-disjoint
arch-adversary may say so; it did, at iteration 2 — **PASS-WITH-CONDITIONS**, loop CLOSED.

> **DO NOT VERIFY THE MECHANICAL PASS BY THIS TABLE.** The DELTA re-read found this log
> **overstated discharge in five of twelve rows (C-2, C-5, C-7, C-8, C-11 — CH-18)**: it is
> the packet's own receipt of its own remediation and was not reliable at iteration 1.
> **Verify by the §7 verification greps in the DELTA report**, which are reproduced with
> their outputs at §13.4. The five overstated rows are corrected in place below.
> Iteration-2 corrections are marked **[DELTA-2]**.
What is claimed below is **what was done**, per condition, with its location.

| # | condition | disposition | where |
|---|---|---|---|
| **C-1** | **BLOCKING** — CH-01 add B-8 or record the collapse | **B-8 ADDED at full depth** (13 rows, > B-1/B-2's 10). The §9.2(b) collapse test was run and **fails both limbs** (PL-16). The §3 head records the slate as externally audited with one option added. | §3 B-8; §1 PL-16 |
| **C-2** | E-2 sub-row (ii) + §2.1 direction correction | **PARTIAL at iteration 1, COMPLETED [DELTA-2].** E-2 was split into (i)/(ii) and the §5 head was corrected — but **§2.1 still carried the single-position direction claim** until M-7. The corrected sentence is now copied into §2.1 so the axis statement and the slate agree. | §2.1; §5 head; §5 E-2(i), E-2(ii) |
| **C-3** | F-DECK axis convention | **Restated in ONE convention** — construction order, upstream/downstream, *above*/*below* retired; checked against K-2/K-5/K-6; D-3's opposite-sense quote preserved with a gloss. | §2.1 |
| **C-4** | restore K-4's legacy-floor cell | **RESTORED verbatim** from the deck draft, with a note that the leg-4 synthesis dropped it. | §4 K-4 |
| **C-5** | correct the withdrawn all-profiles naming claim | **PARTIAL at iteration 1, COMPLETED [DELTA-2].** PL-13 was corrected, but the withdrawn sentence **survived verbatim at three further sites** (§0, §9.2, DEFER-06) until M-10 replaced all three. **Colour-collapse HOLDS unconditionally.** | §1 PL-13; §0; §9.2; DEFER-06 |
| **C-6** | SLOT-B order + PL-09 count | **Ruling ORDER stated (B → A → D; C independent).** PL-09 corrected: **B-1 is DOUBLE-HOMED, not homeless**; B-8 is **homeless by construction** and says so. **"If A = B-8, SLOT B as posed has no correct answer"** folded into the box. Presented, never recommended. | §0 box; §1 PL-09; §3 B-8 |
| **C-7** | relabel §6.4; fix box order | **WRONGLY DISCHARGED at iteration 1, CORRECTED [DELTA-2].** The row's BASIS is the *risky* order, so the label had to name the *risky* order (D before A); iteration 1 relabelled it the other way and added a parenthetical misdescribing the prior label. M-9 fixes both. | §6.4 |
| **C-8** | relabel a11y cells; restore drops | **PARTIAL at iteration 1, COMPLETED [DELTA-2].** Cells were relabelled and the rule stated, but **Dark-mode/Print were re-carried into only a few cells** and **K-1's "(leg-2-deck's own framing)" parenthetical was never restored** — the print line alone was. M-5 re-carries all remaining cells from the §F manifest and restores the parenthetical. | §2.2; §3/§4/§5 a11y cells |
| **C-9** | resolve anchors | **VERDICT pathed** to `/Users/tomtenuta/Code/a8/a8/repos/autom8y/.ledge/reviews/…:274`; **H2 pathed at first use**; **`GOAL.md:29` → `:28`**. | §0; §9.1 |
| **C-10** | METHOD on every UV-P | **All 14 open UV-Ps re-authored in the frozen `[UV-P: … \| METHOD: … \| REASON: …]` syntax.** | §11.2 |
| **C-11** | a11y authors B-0's row | **NOT DISCHARGED at iteration 1, DONE [DELTA-2].** Iteration 1 claimed both cells were carried; in fact **B-0 still held the DERIVED placeholder and B-8's cell was a steward paraphrase labelled "verbatim excerpt"** (CH-16) — 0 of 8 fragments matched the a11y draft. M-3 and M-4 paste the seat's actual rows; M-4 attaches the PL-16 rider to the stale clause; M-6 labels E-2(ii)'s cell seat-authored. | §3 B-0, B-8; §5 E-2(ii) |
| **C-12** | K-6 import qualifier | **K-6 re-read as `PRESENT` → NON-VIABLE**, cost/forecloses re-framed with original text retained subordinate; S4-K-P-18/19 cited. | §1 PL-17; §4 K-6 |
| **A-1** | state F-DECK layer exclusions | **Both stated** (source/frontmatter; delivery) with their grounds. | §4 head |
| **A-2** | name K-5(a)/E-2(i) as one relation; SLOT D selects the reading | **Both done.** | §6.3; §6.4; §0 box |
| **A-3** | adversarial reading ruled out | **Carried; the leg-4 "cannot settle" line WITHDRAWN.** | §6.2 |
| **A-4** | B-0 ≈ "none" | **Stated** in the leg-1 §5.3 rider and carried in B-0's dissent. | §3 B-0 |
| **A-5..A-9** | advisory | **A-6** reconciled (C-3 quoted only as it appears in the audience-map comment). **A-7/A-8/A-9** acknowledged, not mechanically closed — recorded here rather than silently dropped. | §11.2; §10 |

**Named for the DELTA re-read, in priority order:**

1. **DS-6 — provenance of the two DELTA-minted dissents.** B-8 and E-2(ii) **both carry the arch-adversary's DELTA-authored dissent** (`:519`, 116w; `:767`, 111w, both VERBATIM). **DS-6 STANDS — not as absence, but as a structural cost of the two-iteration protocol:** both options were minted in response to the critique, so **both dissents are authored by the seat that demanded the options** — self-critique by proposer, with no third seat to test either. **The operator weights accordingly.**
2. **B-8's only dissent is the leg-1 seat's, against its own late addition** (DS-4 recurring). Weaker scrutiny than a peer's.
3. **B-8's cost row (d) — CORRECTED at DELTA iteration 2 (M-12/CH-17).** The premise was false: **[leg-5 correction, DELTA: SOR HEAD `dtcg-envelope.schema.json` still carries `definitions` (9 types; canonical `8831da27…`); only SOR HEAD `tokens.schema.json` dropped the inline copy, and it now `$ref`s that envelope file. B-8's a8-side pin target is computable at HEAD; the shape was not left, the duplication was.]** What remains sharp is the **canonicalisation agreement** both repos must reach and the **unbuilt vendored-copy check** on which B-8's discriminating benefit entirely depends.
4. **PL-16 corrects the critique that produced B-8.** If the adversary disputes the probe, B-8's cost changes — though the §9.2(b) collapse still fails on both limbs independently.
5. **Two `PRESENT` rows now** (E-5, K-6). If the K-6 re-read is judged over-broad — a frozen artifact is not source — the F-DECK slate returns to six viable rows and §6.2's counts shift back.

---

### §13.4 DELTA-2 mechanical pass — verification greps, run and reported

**This section, not §13.3, is the receipt for the mechanical pass** (the DELTA report's own
instruction: *"the S4 potnia verifies by the greps at the end of this section, not by
§13.3"*). All ten were run against this file after M-1..M-14 were applied.

| # | grep | expected | actual | verdict |
|---|---|---|---|---|
| 1 | `head -1 \| grep -c '^---$'` | 1 | **1** | PASS — frontmatter starts at `:1` and parses (M-2) |
| 2 | `zero\*\* of the other four\|zero of the other four` | 0, except PL-13's quoted history | **1** | PASS — the single hit is PL-13's own quoted history, the documented exception (M-10) |
| 3 | `B-0\.\.B-7\|F-BRAND \(8\)\|of 48\|\(40 cells\)\|Eight options\|delta_pass: 0\|18 rows` | 0 | **0** | PASS (M-8) |
| 4 | `TWO options now carry\|TWO rows carry it\|NON-VIABLE at DELTA` | 0 | **0** | PASS (M-1) |
| 5 | `NO a11y-leg row exists for B-0` | 0 | **0** | PASS (M-3) |
| 6 | `EMPTY — RESERVED FOR THE DELTA RE-READ` | 0 | **0** | PASS (M-14) |
| 7 | `load-bearing on exactly one position` | 0 | **0** | PASS (M-7) |
| 8 | `Dark-mode` | ≥ 21 | **22** | PASS (M-5) |
| 9 | `SLOT D ruled BEFORE SLOT A` | 1 | **1** | PASS (M-9) |
| 10 | `leg-5 correction, DELTA` | ≥ 1 | **3** | PASS (M-12) |
| 11 | the two absence-phrases R1 retired — the §8 depth-table placeholder (`EMPTY` + `reserved`) and the §13.3 residual-#1 wording (`carry` + `no external dissent`), each grepped as its literal | 0 | **0** and **0** | PASS (**R1**, staged pass) — neither the §8 depth table nor §13.3 residual #1 states the two DELTA-minted dissents as absent; both are filled and anchored (`:519`, `:767`). *(This row deliberately splits the two literals so the receipt does not re-introduce the strings it certifies absent — the same rephrase applied to greps 2/7/9 at the DELTA pass.)* |

**READ THIS BEFORE RE-RUNNING THE GREPS ABOVE.** Every count in the `actual` column was
taken **before this table existed**. The table's own `grep` column now contains the
patterns it certifies absent, so a naive re-run returns **the table's own rows** —
greps 3, 4, 6, 7 and 8 each match themselves here, and grep 9 matches both the live label
at `:911` and its own receipt row. **The certified counts are exclusive of §13.4.** To
reproduce them, exclude this section first — `sed '/^### §13.4/,$d' "$P" > /tmp/body` then
grep `/tmp/body`. **Note the heading is `###`, not `##`**; an exclusion written against
`^## §13.4` silently matches nothing and returns the self-matched counts, which is exactly
the trap this note exists to spare the next reader. Verified on that basis at this pass:
greps 1-11 all PASS (G2 = 1, PL-13's quoted history; G8 = 22; G9 = 1; all others 0 or ≥1
as specified).
This is a property of writing the receipts into the audited file, not a regression:
grep 11 and the §13.3 log rows were phrased to avoid it; the §13.4 pattern column was
not, and that is recorded here rather than corrected silently.

**Two greps required rephrasing this pass rather than a content fix**: the §13.3 log rows
for C-2, C-5 and C-7 originally reproduced the very literals greps 2, 7 and 9 test for,
which would have failed the check while describing its remedy. The rows now name the
condition without quoting the retired string. **No content claim changed.**

**Three genuine residuals were found by the greps and fixed** — they were NOT in the
M-list, and are recorded so the pass is not overclaimed: (i) a **fourth** instance of the
withdrawn naming sentence at §9.2, line-wrapped and therefore missed by M-10's three named
sites; (ii) B-8's INV cell still describing K-6 as NON-VIABLE after M-1 reverted it;
(iii) B-8's coherence cell carrying the same stale clause. **The greps caught what the
condition list did not — which is the argument for verifying by them.**

**R5 — the attestation boundary, stated plainly.** The adversary's DELTA verdict is bound
to sha `c2c8ab19…` at 1,265 lines; the M-1..M-14 pass (+67 lines, this sha) was
**adversary-sourced and author-grep-verified, NOT adversary-re-read**; no third pass
exists by protocol. **R1** (this staged-pass fix) is a further author edit on top of that
and is likewise unread by any critic.

**Scope of this pass:** mechanical only. Every edit had a determinate source supplied by
the DELTA report (§7 replacement text, §4 dissent text, the a11y archive rows, the §F
carriage manifest, the archive README shas). **No authoring judgment was exercised, no
fork was answered, no ranking introduced.** The one factual claim this seat re-probed
before applying — CH-13's basis, that the `@ds-bundle` marker already sits in deck-host's
served `public/761ebfd8…/index.html` — returned `grep -c` → **1**, confirming the revert's
ground. Self-assessment **MODERATE**; this packet does not attest the conditions cleared.

