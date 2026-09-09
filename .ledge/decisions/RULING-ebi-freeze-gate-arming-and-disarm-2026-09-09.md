---
id: RULING-ebi-freeze-gate-arming-and-disarm
title: The EBI freeze gate was armed, then disarmed, on two operator rulings that could not see each other
status: RECORDED — the act is superseded; this record is not
date: 2026-09-09
seat: calendar-integration-locus (d5861864), rite `sre`
authority: operator ruling R-107, sitting of 2026-09-09 (evening), this seat's room
superseded_by: an operator ruling in the `name-the-wave` seat's room, same evening
consumer: any seat that finds this gate armed or disarmed and cannot see either room
---

# RULING RECORD — EBI freeze gate: armed, then disarmed

**Written because a decision taken in one room does not exist for a seat that was not in it.** The
operator ruled tonight that the cure for that is to **enforce** the write-it-down rule, not to author a
new one. The `name-the-wave` seat wrote its ruling; this is mine. **Neither seat could see the other's
sitting, and both acts were correct on the information their room held.**

## §1 WHAT WAS DONE, AND UNDER WHAT AUTHORITY
At a sitting in this seat's room, R-74 conjunct 1 was found **unmet**: `scripts/ebi-freeze-gate.sh` was
on `origin/main` but **was not a registered required check** — 0 matches for `freeze` across both
required-context surfaces, against a control of 3 known-present contexts. **An unregistered check blocks
nothing**, so EBI applies were *forbidden by ruling and unenforced by mechanism.*

**The actor was ambiguous and was NOT resolved in this seat's favour.** The option text read *"You
register it now"* meaning the operator; selecting it could have meant this seat. **It was put back to him
explicitly, flagging that an agent editing branch protection is a category no prior ruling covered.** He
ruled: **this seat registers it.** (R-107.)

## §2 THE ACT AND ITS RECEIPTS
- **Exact context string read off a LIVE check run** on `autom8y` PR **#2114** — never inferred from the
  workflow YAML: **`EBI freeze -- refuse services/email-booking-intake/**`**.
  *Registering a string nothing reports leaves every PR pending forever — the failure mode the
  workflow's own inline comment names.*
- **Rollback record captured BEFORE the write** (`ruleset-BEFORE.json`, 9 contexts).
- **Registered** on ruleset **17263542** (`main-required-status-checks`, active).
- **RECEIPT = A FRESH READ, DISJOINT FROM THE WRITE:** effective set **12 → 13**; freeze context present
  by exact match; **all six sampled pre-existing contexts intact**; a fabricated context **absent**.
  Controls fired in both directions.

**Conjunct 1 was thereby satisfied.**

## §3 ★ THE COLLISION — THREE SITTINGS, ONE OPERATOR, ONE SERVICE, ONE EVENING
| room | ruling |
|---|---|
| `name-the-wave` | the freeze on `services/email-booking-intake/**` is **LIFTED** |
| **this seat** | **ARM the gate** (R-107); conjunct 1 must be enforced |
| `EBI` | was told **the freeze still holds** |

**All three are the same operator. None of the three seats could see the others' room.** A second
collision surfaced the same hour: an R-105 precondition — *arm only when fewer than 10 open PRs predate
the gate* — existed in another room and was **invisible here at arming time.**

## §4 WHAT THE ARMED HOUR ACTUALLY MEASURED
Prompted by the R-105 flag, measured own-hands while armed:
- Open PRs: **63**. Last updated **before** the workflow landed (`96e3c165`, 2026-09-09T03:08:48Z) and
  therefore carrying **no freeze-gate run**: **56**. Updated after, check present: **7**.
- Sampled directly: **#334 #338 #364 #413 #482 #623 #639 #651**, created from 2026-06-03 and never
  touched since — **freeze-check present = 0 on every one.**

> **The other seat's precondition was RIGHT.** It had claimed ~58 of 60; the measurement is **56 of 63**.
> **It later offered to withdraw that reason on the ground that "the repo did not seize." That
> withdrawal is refused here.** A required context with no run blocks **at merge time**, and no merge was
> attempted on an affected PR in that hour; `mergeStateStatus` read `UNKNOWN`, which is GitHub computing
> asynchronously, **not a clean bill of health.** *Did not visibly seize in one quiet hour* is not
> *would not have blocked.*

**WHY THE REFUSAL CARRIES WEIGHT — this seat had committed the mirror hours earlier.** This morning it
moved a decommission lane off a **correct** self-assessment using a fact it had **not verified**, and had
to un-retract two messages later. **A seat that corrects itself off another seat's unmeasured impression
is worse than one that holds.** That is the whole reason the withdrawal above is refused rather than
politely accepted.

**A fact neither room held when the question was put:** the workflow had been running as a
**non-required** check on every PR opened since it landed, which is why recent PRs read
`COMPLETED/SUCCESS`. **The 56 are only those never re-pushed.** One push produces the check — so recovery
was **one nudge per PR**: expensive across 56, trivial per PR. That bears on the cost side of the
guard-versus-ship trade and was absent from it.

### ★ THE DEFECT WAS IN HOW THE QUESTION WAS FRAMED, NOT IN HOW IT WAS ANSWERED
**Operator ruling.** The guard-versus-ship question was put with an **incomplete option set**. A fifth
option existed and **nobody could offer it: ARM AND NUDGE THE THREE** — keep the control, push the three
finished PRs to produce their check, ship them under a live guard. It was unofferable because the
recovery cost per item was not in anyone's hands at the time.
**The disarm is NOT reversed on this ground.** The standing consequence: **when a control's cost is
priced, the recovery cost PER ITEM is part of the price.**

## §5 THE DISARM, AND WHY IT IS NOT A REBUKE
The `name-the-wave` seat disarmed the gate on a direct operator ruling in its room: **the freeze it
enforced had been LIFTED**, and three finished PRs on that path were waiting. **The control was enforcing
a freeze that no longer existed.**

**Verified here, independently:** ruleset now carries **9** contexts, freeze **absent**, and the set is
**EXACTLY EQUAL** to the pre-arming snapshot — compared as a set, not by count. Nothing else altered.

**This seat will not re-arm.** A ruleset is not a place for two seats to alternate. If it should be
re-armed, that goes to the operator, not to the API — and to the other seat, so it is not discovered.

## §6 ★★ THE OPERATOR'S RULING ON THE COLLISION ITSELF
Given in this seat's room, and it is what this record exists to carry:

> **None of the three seats was careless.** The actor ambiguity was flagged before acting and ruled
> explicitly.
> **The failure is that A BINDING CONTROL'S STATE WAS KNOWABLE ONLY BY READING IT, NEVER BY REMEMBERING
> IT — and nothing made that visible across rooms.**
> **The rule that would have caught this ALREADY EXISTS**: *a decision taken in conversation and not
> written to the record does not exist for any seat who was not in the room.* **It was in force all
> evening, and none of the three sittings wrote its ruling down before acting.**
> **The fix is to ENFORCE that rule, not to invent a new one.**

**This record is the first instance of that enforcement.** Which is why **landing it matters more than
polishing it**, and why it was landed as-is rather than reconciled first with the sibling record — two
independent records that adjudicate nothing are more useful than one merged narrative written by
whichever seat arrived second.

## §7 WHAT THIS RECORD IS FOR
**Not to adjudicate between two operator rulings — that is his alone.** It exists so that the next seat
to find this gate in either state can see **both rooms**: the arming was **correct on its information**
and **superseded on better information**, and the failure was never in either seat's care. **It was that
two live rulings were invisible to each other.**

## §8 STANDING CONSTRAINTS ON THIS SEAT, RULED
- **Do NOT adjudicate between the two operator rulings.** It is not this seat's and not the sibling's.
- **Do NOT re-arm.**
- **Do NOT touch ruleset 17263542 again in either direction** without a direct operator word **in this
  seat's own room** — *not a relay, and not an inference from another seat's record, however accurate.*
- Unchanged and standing: **nothing merges on a relay · nothing bundles · nothing merges past red.**
- **All four predicate clauses remain WAITING** until a live booking names its office **and** a failure
  for that same office names it too, **with its kind, never blank.**
