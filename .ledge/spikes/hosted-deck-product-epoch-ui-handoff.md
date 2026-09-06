---
artifact_id: HANDOFF-ui-to-10x-dev-2026-09-05
schema_version: "1.0"
type: handoff
source_rite: ui
target_rite: 10x-dev
cross_rite: "ui -> 10x-dev"
handoff_type: assessment
priority: high
blocking: false
initiative: hosted-deck-product-epoch
created_at: "2026-09-05T19:10:00Z"
status: pending
lifecycle_status: proposed
session_id: session-20260905-014608-787b7977
sprint_id: S7
wave: 3
consumed_by: "10x-dev Potnia at S8 entry"
single_writer: design-system-steward
source_artifacts:
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/hosted-deck-product-epoch-leg1-render-remeasure-2026-09-05.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.know/telos/hosted-deck-product-epoch.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.sos/wip/frames/hosted-deck-product-epoch.shape.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.sos/wip/frames/hosted-deck-product-epoch.md"
  - "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/hosted-deck-product-epoch-DP-1-brand-seam.md"
  - "/Users/tomtenuta/Code/external/advantage-rc/.ledge/reviews/SHIP-RECEIPT-advantage-rc.md"
  - "/Users/tomtenuta/Code/a8t/deck-host/.ledge/reviews/DEFER-WATCH-hosted-deck-product-epoch-wave1-2026-09-05.md"
provenance:
  - { source: ".know/telos/hosted-deck-product-epoch.md:56-58", type: telos, grade: moderate }
  - { source: "hosted-deck-product-epoch-DP-1-brand-seam.md (sha256 6bf52c7b…, 1377 lines, status ratified)", type: adr, grade: moderate }
  - { source: "hosted-deck-product-epoch-leg1-render-remeasure-2026-09-05.md (S7 re-measure)", type: artifact, grade: moderate }
evidence_grade: moderate
self_ref_cap: MODERATE
---

# H3 — ui → 10x-dev cross-rite handoff (hosted-deck-product-epoch, S7)

> **This artifact TRANSFERS STATE. It RULES NOTHING.** S7 ran MEASURE-only. No branch, no PR, no build, no browser, no production GET by any seat. Envelope per shape `:1082-1095`. Gate C binding (`telos-integrity-ref` §3): every claim-token below carries a `{path}:{line}` anchor, a re-probed receipt, or the frozen UV-P syntax.

## §1 — The epoch telos (Gate C)

Quoted verbatim from `.know/telos/hosted-deck-product-epoch.md:56-58`:

- **L1** — "a real non-Contente-profile deck SERVED 200 at a capability URL, byte-identical to its frozen export, with that profile's tokens in the served bytes"
- **L2** — "a real Contente office deck re-served with zero regression on the WS-GUARD invariants (noindex/no-store served, 32-hex slug, audience-deny, parity)"
- **L3** — "both ancestor telos closed by eunomia VERDICT — epoch-2 is not realized on top of an unattested epoch-1"

**Attestation status, `:62-65`, UNCHANGED by S7:** `inception: INSCRIBED` · `shipped: MISSING` · `verified_realized: UNATTESTED`. S7 amended nothing in the telos; amending it is the operator's act, not a sprint's (frame `:630-631`).

## §2 — The frozen export and its byte-identity

| Item | Value | Receipt |
|---|---|---|
| Served capture (on disk) | `…/5b9fea54-…/scratchpad/s7/served/tenuta-served-2026-09-05.html` | dispatcher GET `2026-09-05T18:43:50Z`, HTTP 200, 63336 bytes (CAPTURE-RECEIPT.txt) |
| Served sha256 | `080768a3052c97c39442fad1e05bed64db1305499be6c151a38c89393127c918` | re-run `shasum -a 256` by the steward before any grep — MATCH (full) |
| RECORDED frozen sha (**located-ephemeral; custody unassigned; durability at S10 is a UV-P**) | `080768a3052c97c39442fad1e05bed64db1305499be6c151a38c89393127c918` | SHIP-RECEIPT `:19` ("sha256 (frozen = live)"); frame **G-37** `:482` records the same, independently |
| Byte-cmp today | **IDENTICAL** (`cmp` exit 0) | served vs the pinned ephemeral copy `…/s7/frozen/advantage-booking-assessment-2026-09-04.frozen-ephemeral-copy.html` |
| Guard headers | HTTP/2 200; `cache-control: no-store`; `x-robots-tag: noindex, nofollow`; `referrer-policy: no-referrer`; `x-content-type-options: nosniff`; root `/` HEAD → **404** | CAPTURE-RECEIPT.txt / headers-capability.txt / headers-root.txt; **G-36** |
| External http(s) `<script src>`/`<link href>` | **0** | CAPTURE-RECEIPT.txt; == SHIP-RECEIPT `:21`, G-37 |

The frozen arm carries this label wherever cited: **"located-ephemeral; custody unassigned; durability at S10 is a UV-P"**. The file is ABSENT from the advantage-rc tree — SHIP-RECEIPT `:18`'s cited path is ENOENT (the whole `scratchpad/` dir is ENOENT); `publish-tenuta.sh` likewise ENOENT. **Shape `:1090` disposition:** satisfied TODAY by byte-comparison against a located-ephemeral copy and PARTIALLY for S10 — `[UV-P: durable frozen export under named custody | METHOD: operator names the home (door (f)); one verified copy placed there with its sha | REASON: both copies live in reaped-able session scratchpads; UV-P-4 METHOD of record frame :644; G-41 :487]`

## §3 — The TWO-SIDED token receipt (shape `:1091` — G-38b's form is the floor, not the ceiling)

All counts RE-DERIVED at S7 from brand-tokens `@4679deb`, not inherited. **Denominator rule stated beside every count**: DENOM-A = distinct raw `#[0-9a-f]{3,8}` matches, uppercase-normalised; DENOM-B = the six-digit-only subset.

| Profile | Declared set | Scored on the SAME served bytes |
|---|---|---|
| **tenuta** (positive) | 8 (A) / 8 (B); `primitives.css` sha `dcff253b…` | **8/8 PRESENT.** By VAR-NAME each property is declared once (frame **G-38** `:483` "each var defined exactly once" HOLDS); **by VALUE 5/8** — `#F3F1EB`, `#14171C`, `#C4524F` are re-bound under the two dark-scheme blocks (L13/L14) as `--fg-deep`/`--bg`/`--accent`. Both rules stated; a denominator finding, not a defect. |
| **lotusun-brand** | 10 (A) / 7 (B) | **0/7 ; 0/10** |
| **lotusun-cream** | 10 (A) / 7 (B) | **0/7 ; 0/10** |
| **a8t** | 18 (A) / 18 (B) | **0/18 literal** — caveat carried, not excluded: `#000`/`#fff` (3-digit shorthand) occur once each at L48 in a generic `@media print` rule; colorimetrically equal to a8t's `#000000`/`#ffffff` but not literal 6-digit matches, and a print reset is not a brand-token declaration. |

**Beyond G-38b — the two positive controls G-38b lacked (both two-sided):**

- **(R4) Contente marker set.** On the control deck `/Users/tomtenuta/Code/a8t/deck-host/public/761ebfd8a7e1ae5bb7442c8dc2154f6d/index.html` (sha `0adebd0f779d6040f2a3061f7b6829677d335fac58f0ba6c75606cde8c624960`, re-derived): `ContenteDesignSystem_9ed584` = **26 matching lines / 27 occurrences**, `@ds-bundle` = **1**, `_ds_bundle` = **1**. On the tenuta served bytes: **0, 0, 0** (a case-insensitive `contente` sweep is also 0; the file has 0 HTML comment blocks, so nothing hides in one). The fourth marker `@contente/deck-inliner` is **DEMOTED — non-discriminating on served bytes** (0 on the control too); it is retained only in the §5 source grep.
- **(R5) G-29 pattern.** Hits `vendor/deck-producer/package.json` at `:2` (`"name": "@contente/deck-inliner",`) and `:17` (`"@autom8y/contente-tokens": "github:autom8y/contente-tokens#v1.0.0",`) — **2 hits** — and scores **0** on deck-kit `@d8c7794`. The grep bites where a crossing exists.

**`:root` on the TENUTA served bytes only:** 1 unqualified `:root{` block-opener / 3 raw `:root` tokens (L10 base; L13 `:root:not([data-theme="light"])`; L14 `:root[data-theme="dark"]`). Both denominators reported, **with the regex stated**: the tenuta count of 1 holds under BOTH `:root[[:space:]]*\{` and the exact literal `:root{`; the Contente control deck gives **5** under `:root[[:space:]]*\{` but **0** under the exact literal `:root{` (its blocks carry whitespace before the brace).

## §4 — The T7 branch actually taken (shape `:1092`)

**T7 reading (i); MEASURE-only; no build branch; component-engineer not seated** — ruled at telos `:142-144`. The S7 roster is shape `:530`; component-engineer's S7 role is "BUILD branch only" (`:533`) and the BUILD branch did not fire. frontend-fanatic is not on the roster; browser assumed down and labelled UV-P, never used as an excuse for a one-sided measure.

## §5 — The G-29 boundary receipt (shape `:1093`)

```
grep -rnE '@contente/|autom8y|contente-tokens|vendor/deck-producer|github:autom8y' \
  /Users/tomtenuta/Code/a8t/deck-kit \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=dist
```

- **Observed HEAD `d8c7794`** on `feat/dk-001-dk-005-render-check-and-negative-fixtures`; the frame pin **`bfc2f41`** cited BESIDE it, never in place of it (`git merge-base --is-ancestor bfc2f41 HEAD` → exit 0).
- **0 hits**, grep exit 1. Still 0 when re-run without `--exclude-dir=dist` and without excluding `.knossos/worktrees/` (which contains a `…bfc2f41` snapshot).
- **Positive control: 2 hits** (§3 R5). The zero is a measured absence, not an inert pattern.
- **Hex-free (G-26/G-27/G-28) — DECK-KIT ENGINE ONLY, not the landed render (C-1):** `src/deck.css` **0**, `examples/fixture/deck-local.css` **0**. Per §7 D1 the served bytes did not come from this engine; `render.mjs`, which did, is **not** hex-free (23 occurrences / 14 distinct). Direct reads: `bin/build.mjs:7` (`--profile-root` in the usage line), `bin/build.mjs:30` (`DEFAULT_PROFILE_ROOT`), `src/receipts/receipt.js:53` (`'deck.brand-css-hex-free',`).
- **README `:350-352` / GOAL `:21` intact:** "**Zero code was copied** … nothing was imported, required, or pasted from `~/Code/a8`" and "absolute: a8 → a8t imports are FORBIDDEN."
- **oracle-OK prose mentions listed** (`legacy-floor-isolation` §2 — CONSULTED, not INHERITED): GOAL.md `:20`, README.md `:345`, `:346`, `:352`, and `src/engine.js:12` (header comment: "after reading (not copying) … Zero code copied"); plus one derivative copy, `dist/deck-kit-fixture.html:776` (C-6). An `import|require|from` executable-statement probe across `src/`, `bin/`, `examples/` crossing to a8/contente/autom8y returns **0**.

## §6 — Not owed

**The ruled engine's PR (shape `:550`/`:1085`) is NOT OWED under reading (i); no branch, no PR, no build was opened in S7.**

## §7 — DIVERGENCE register — NAMED, not fixed

Copied from the S7 re-measure §7. Nothing here is scheduled, priced, designed or repaired.

- **D1 — THE SHIPPED RENDER IS ON NEITHER LAYER (re-authored ON BYTES; the earlier reading was FALSE on bytes).** SLOT C ruled "K-3 component-set layer IN DECK-KIT" (packet `:119`; stamp `:148`). Re-probed: the served bytes carry **0** deck-kit output markers — `inlined verbatim` 0 (fixture 5), `--dk-` 0 (167), `<script` 0 (2), `section class="slide` 0 (6), `--surface-page` 0 (2) — and never passed through `bin/build.mjs`. Their producer is an ephemeral `render.mjs` (`…-external-advantage-rc/75ee569d…/scratchpad/render/render.mjs`, sha `cc9acff5e34dd3aa…`, 137 lines, imports only `node:fs`+`marked`, 0 refs to deck-kit/brand-tokens/`--profile-root`) that **hard-codes** the primitives at `:55` and the dark blocks at `:58-59`; SHIP-RECEIPT `:33-34` names it. deck-kit's receipts record `42ddb3cc…`/`151ebee3…`/`d2d18522…`, never `080768a3`. **NAMED:** the landed render sits on **neither** the ruled K-3 layer **nor** the K-5(b) `--profile-root` layer, but on a **third, ephemeral, un-custodied path outside both engines**, where brand binding is **CODE** — the F-BRAND premise frame §9.4 declared refuted for deck-kit is **TRUE of what shipped**. L1's "with that profile's tokens in the served bytes" (frame `:124`) is satisfied **by VALUE, not by ENGINE** (8/8 present).
- **D2 — ONLY TENUTA RESOLVES (re-scoped).** **Deck-kit-only clause:** `deck-kit/src/deck.css` targets 13 colour-role names and tenuta declares **13/13**; a8t 0/13 (+4/8 typography); fixture and both lotusun 0/13 + 0/8 (W2-005 `:465`; packet `:86`) — a **deck-kit ↔ profile** fact, NOT a property of the served bytes. **Served-bytes clause (re-probed):** the served artifact carries **0/13** of those names. The WS-A charge is proven at **N=1**, and per D1 not through the engine the charge is about.
- **D3 — NOTHING is owed or present on the a8 side.** SLOT A = B-0, SLOT D = E-1. Under those rulings **any G-29 hit would be a BREACH, not a divergence**; §5 measured zero with a biting control. A constraint satisfied, not a gap carried.
- **D4 — the AA failure sits on the SHIPPED profile.** Register W2-006 `:488`: no contrast check exists on either side; 10 of 18 measured token-literal pairs already fail AA, including tenuta caption-on-sunken **4.13**. Re-anchored on served bytes (S7 §8 L1-b): both literals present unaltered; the direct pairing was not found in a single rule; cascade pairing is a layer-2+ question (UV-P). **Carried. No a11y benefit is claimed anywhere in this envelope. Nothing scheduled.**
- **D5 — the frozen-export byte-source is NON-DURABLE.** Half of L1's byte-identity clause (frame `:124`) rests today on an ephemeral copy plus a receipt (§2). **Extended (C-9): the non-durability reaches the RENDERER** — `render.mjs` lives only in two reaped-able session scratchpads, absent from the advantage-rc tree and from deck-kit.
- **D6 — TWO TENUTA ARTIFACTS EXIST, AND THE FRAME CONFLATED THEM (NEW).** advantage-rc holds **(1)** the served ASSESSMENT (SHIP-RECEIPT `:15-19`; the `render.mjs` product; the bytes S7 measured) and **(2)** an EXHIBITS DECK at `/Users/tomtenuta/Code/external/advantage-rc/.ledge/deck/` whose `README.md:3-4` says *"self-contained HTML built by the `@a8t/deck-kit` substrate (Tenuta profile)"*, `:15` names `deck-src/` as "the generated input directory deck-kit builds from", `:18` gives the `bin/build.mjs` build line — a deck-kit product with **NO served slug and NO frozen output** in that tree (re-probed: no frozen `.html`; slug grep → 0). **Provenance root:** frame `:501` ("First consumer … the Advantage assessment deck (G-33)") — G-33 anchors the SHIP-RECEIPT, so the receipt is for (1) while the deck-kit consumer is (2). **Consequence NAMED:** "LEG-1 LANDED on the a8t side (tenuta-decks)" holds for the **RAIL**; the T7 parenthetical "(tenuta-decks, deck-kit)" (telos `:142-143`) holds for tenuta-decks and **NOT** for deck-kit as producer of the served bytes — **the operator's to re-read, not S7's to amend.** Cross-reference only: S6's O-1 priced the exhibit contract of (2) (G-31/G-32), not of what is served.
- **Not opened as a separate divergence.** The presence-8/8 vs declared-once-by-value-5/8 split stays a **§3 finding** — a denominator finding against frame G-38 `:483`'s wording, not a divergence from what DP-1 ruled.

**FORK-ALPHA — named, not ruled; home operator (wording) / eunomia standard at S10.** Whether L1's "byte-identical to its frozen export" admits α-i sha-only / α-ii ephemeral cmp (**satisfied TODAY**) / α-iii durable custody / α-iv regenerate (**further from satisfied than earlier stated (C-9)** — the renderer itself is ephemeral and is not deck-kit).

## §8 — S8 status

**S8 stays BLOCKED: RA-1 HOLD; custody of the fence substrate unresolved; the S3 FREEZE unrecorded; the Contente account HELD (UV-P-5). The register :372 boundary_violation_observer is ADVISORY for potnia (10x-dev) at S8 entry and is never an entry criterion.**

## §9 — Doors raised at the 2026-09-05 sitting and NOT ruled (by id only)

(a) ancestor PT-04 record-of-truth — *beside it:* the ancestor-B deadline re-bind · (b) shape `:667` under ROUTE · (c) `:1034` R6→R4 · (d) FORK-ALPHA · (e) DW-7 jurisdiction · (f) custody of the frozen export. **Operator-only; S8 does not wait on them except (f) for `:1090`'s durable half.**

## §10 — PT-07

**PT-07: PASS recorded 2026-09-05T19:37:09.359Z by the dispatcher (`ari checkpoint record PT-07 PASS -s session-20260905-014608-787b7977`), STAGED by potnia (ui) as PASS-WITH-RESIDUALS (R-1 frozen arm located-ephemeral, custody unassigned; R-2 served bytes not deck-kit-produced — L1 by VALUE not ENGINE, T7 parenthetical the operator's to re-read; R-3 D6 two tenuta artifacts; R-4 M-1..M-3 author-applied, not adversary re-read; R-5 declared-once 5/8 by value vs G-38 by var-name; R-6 a11y scoped NON-GATE, W2-004 ACTIVE). Iteration 1 BLOCK → iteration 2 PASS-WITH-CONDITIONS (loop CLOSED). The OPERATOR closes; this record is evaluative. RUNG = REALIZED-pending-attestation under reading (i); NOT REALIZED; S10 attests.**

The rite-disjoint critic (10x-dev qa-adversary) BLOCKED iteration 1 on Q2 (`.ledge/reviews/ADVERSARY-REPORT-S7-PT-07-2026-09-05.md`); D1/D2 were re-authored on bytes and D6 added above. **M-pass provenance:** M-1..M-3 are **adversary-sourced, author-applied, and NOT adversary re-read** — the loop is CLOSED at iteration 2 with no third pass.

## §11 — completeness_check (shape `:1095`, each conjunct with its state)

**PT-07 PASS recorded 19:37:09Z (operator closes); token claim anchored on SERVED bytes (and on the FROZEN arm only in the α-ii sense — byte-`cmp` against a located-ephemeral copy, "located-ephemeral; custody unassigned; durability at S10 is a UV-P", NOT α-iii durable custody — C-7); DP-1 RATIFIED 2026-09-05 (PT-04 PASS 18:42:43Z)**

## §12 — RUNG and grade

> "exit_anchor: §1 predicate — LEG-1 render half. RUNG = REALIZED-pending-attestation under reading (i); merged+rendered under reading (ii). NOT REALIZED either way — S10 attests."
>
> — shape `:546`, verbatim

S7 ran under reading (i) only; the reading-(ii) branch was not entered, and this envelope makes no claim about it. Evidence grade **MODERATE** (self-ref capped). **S7 does not self-attest; S10 attests.**
