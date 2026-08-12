---
type: decision
status: draft
artifact_id: FINDING-k0c-contract-has-no-durable-home-2026-08-12
initiative: offers-freshness-axis-contract
precondition: K-0c
date: 2026-08-12
found_by: main thread (operator-authorized overnight campaign), while assessing K-0c for execution
routes_to: OPERATOR — one ruling, then K-0c becomes a mechanical dispatch
blocks: K-0c → K-1 → the entire K-lane
---

# FINDING — K-0c cannot be executed as written: the contract it amends is not in git

## What K-0c requires

ADR-007 §7.2 `:1136`:

> **K-0c** | The §3 amendment landed in the contract, **one PR**, superseded text
> struck and standing | blocks K-1 onward | owner **10x-dev**

And ADR-007 §3 `:566-568` specifies the process:

> Process per precedent **[A-2026-08-03]** (charter amendment #298): amended
> **in place**, superseded text left standing and struck, **one PR**, ruled by
> the operator personally.

The ruling half is **done** — R-i AMENDED-RATIFIED, 2026-08-12, operator
personally, in interview sitting #2. What remains is the mechanical landing.

## Why it cannot be landed

The target — `CONTRACT-offers-freshness-axis-frozen-2026-08-11.md`, **1,214
lines** — lives at `.sos/wip/`, and `.sos/*` is gitignored:

```
$ git check-ignore -v .sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md
.gitignore:90:**/.sos/*    .sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md

$ git ls-files | grep -i "CONTRACT-offers-freshness"
(no output — untracked)
```

**There can be no PR against a file git cannot see.** K-0c is not blocked by
effort; it is blocked structurally.

## The precedent it cites does not have this problem

[A-2026-08-03] amended `CHARTER-decision-space-of-record-2026-07-30.md`, which
**is** tracked, in `.ledge/decisions/`, and landed as a real PR (#298). So does
every other contract and ADR of record in this repo — `DP-3-consumer-contracts`,
`ADR-storage-namespace-contract`, `ADR-field-provenance-population-contract`,
`ADR-dyn-enum-contract-shared-contract`, and the rest, all in
`.ledge/decisions/`.

**The offers freshness contract is the outlier.** K-0c was written to follow a
precedent whose mechanics its own target cannot support.

## The finding underneath the finding

This is the arc's recurring shape in a new place. Pythia named the family this
evening: *merged ≠ deployed · authored ≠ delivered · delivered ≠ read · built ≠
reachable.* This is the next member:

> **ratified ≠ durable.**

A document called *frozen*, carrying a contract the fleet gates on, amended by a
personally-ratified operator ruling, is one `rm -rf .sos` or one fresh clone away
from not existing. Nothing in the record would show it had gone. The same is
true of the whole `.sos/wip` evidence corpus this crusade produced — the W-1
measurement, the frames and shapes, the DETERMINATION and STAGE1 files. *(The
tick census produced tonight was promoted to `.ledge/reviews/` on discovering
this; it is the only one that was.)*

## What the operator must rule — one decision, then this unblocks

**Where does the contract of record live?**

- **(a) Promote to `.ledge/decisions/`** — matches every other contract of
  record in this repo, matches the precedent K-0c cites, makes K-0c a mechanical
  dispatch, and gives the amendment a real PR with struck-and-standing text
  under review. Cost: the file moves, and any citation of its `.sos/wip` path
  needs updating. **This is the reading the evidence supports**, but it is a
  governance decision about the seat of a frozen contract and is therefore not
  mine.
- **(b) Amend in place at `.sos/wip/`** — satisfies "amended in place, superseded
  text struck and standing" but **not** "one PR", and leaves the durability gap
  open. K-0c's exit criterion would have to be restated to match what is
  actually possible.
- **(c) The word "contract" in K-0c means a different artifact than I have
  identified** — in which case name it and this finding dissolves.

**Not ruled here in any direction.** Under the standing interview discipline —
*"nothing I don't explicitly rule on may be recorded as decided"* — this is
recorded as a routed question, not a recommendation acted upon.

## Scope of what was NOT done

No file was moved, promoted, amended, renamed or deleted. `.gitignore` was not
touched. The contract was read and its path checked; nothing else. K-0c remains
**undischarged**, and K-1 remains blocked on it — correctly, since the alternative
was to discharge it by a route the operator has not chosen.

## Status of the sibling preconditions, for sequencing

| id | state |
|---|---|
| **K-0a** | ✅ **PASS** — `CENSUS-k0a-manifest-observation-2026-08-12.md`, 27/27 resolve, 27/27 stamped, oldest 20.5 min, 45 versions swept |
| **K-0b** | ADR-007 is `ratified-provisional`; ratification record exists (`RULING-operator-adr007-ratification-2026-08-12.md`). Operator-owned — **whether that discharges K-0b is the operator's call, not mine** |
| **K-0c** | ⛔ **BLOCKED by this finding** |
