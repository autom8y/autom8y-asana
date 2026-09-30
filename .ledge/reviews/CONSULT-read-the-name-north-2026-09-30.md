---
type: consult
initiative: read-the-name
consultant: pythia (read-only; governance read from origin/main after fetch; AWS read-only 04:10–04:40Z)
requested_by: the operator, 2026-09-30 ("a visionary stakeholder /consult pointing us north")
evidence_grade: MODERATE (one consult, own reads corroborating the seat's receipts)
note: this is a condensed record. Items the seat has since acted on are marked ✔.
---

# read-the-name — north consult, 2026-09-30

**North** (telos L34–36, as amended by §11 D3): every active client whose mail arrives and does not book is named to a human who **acts** on it, before the client has to ask.

**The split is right.** S-1 is DONE because it is armed and delivering (D2; proven). The ARC stays open until someone acts on a page (D3/D9). One fact belongs beside it:
- **every one of the three armed digests (09-27..09-29) named 0 offices below the floor**; the armed pager has not yet named an office to anyone.

## Ledger

**PROVEN:**
- armed 09-27T03:24Z, with 5 alarms on platform-alerts;
- delivering: receipt A plus three digests, each with a `page_message_id`;
- the fleet stop's three legs closed on real traffic;
- the conservation gate PASS (§3l).

**LANDED BUT UNPROVEN:**
- the reader's acknowledgement (READ observer; none recorded);
- a real office named by the armed pager;
- FLOOR-REFUSED on the live pager;
- `ebi-intake-silence-6h` has never fired (its teeth are unproven);
- the recovery floor after the arm (left open on purpose).

**NOT LANDED:**
- s1.6 (#2694);
- ✔ soak rows 13–15;
- ✔ `arming_state` in the receipt;
- ✔ the RF-1 precondition on a remote ref (now on this slate as §14; contente's push is pending);
- ✔ durable scripts in the repo (`soak_row.py`);
- R2 groundwork `b17a066c` exists only on a branch.

**Correction on the record:** the outage cause is autom8y OD-97 (a SendGrid billing hold; ~65–75 mails accepted as lost). OD-98 adds a 6 h silence alarm. ✔ §3m is closed.

## What the s1.6 bundle buys and costs

**It buys** an honest arrival count (24 % of deliveries were counted more than once), refusals as evidence, relay mail out of the arrivals, the residual measured in deliveries, and a `pinned_query_sha` on every run line.

**It costs** an epoch restart, which is now cheap because no gate depends on the row count (D4).

**Every item except the Condition-1 fix makes S-1 quieter.** So its failure is a *missed* page, which is invisible. That is why the consult asked for proof that the page still fires. ✔ Done: on window A, both true stalls stay ZERO. On W2, the 4 exits are all known non-actionable accounts.

## Horizon (seat and ASR, overnight; the operator in the morning)

1. ✔ The scoped Condition-1 fix, the pre-outage windows, and window A.
2. The name-split fix, then the live legs, then the critic's grade of the whole delta.
3. ASR merges and deploys **after the 09-30 11:27:17Z digest**.
4. The first s1.6 run line is the epoch boundary, recorded in SOAK.
5. Daily rows continue; 09-30 is a split day.

## Beyond, in order

1. **R1 realization:** a fair s1.6 replay (✔ the window-A replay covers this), then D9, then the first organic page on a real office.
2. **OD-79, re-scoped** to measure the A-18 governing rule, not the frozen `ad_attributable` predicate. It comes after table v3 and the OD-117 recompute, keeping OD-78's order. data-analyst co-seat.
3. **R3 coverage:** check what A-18/A-19's identity work already builds before building anything.
4. **R2 enforce** (it needs R3's join).
5. **R4.**
6. **Guard follow-ups:** make a non-zero digest's subject distinguishable from an empty day's; run a terminal-event-name drift census, because a new terminal event name silently leaves the arrival unit.
7. **Declare door conservation (per-office silence) as a named gap.** S-1 cannot see it.

## Decisions for the operator, ranked (the consult's recommendations)

1. **Record one act today, in about 30 seconds:** a dated reply on a digest thread in `#platform-alerts` (guid8 only). It closes the READ-observer gap and becomes the prototype for D9.
2. **Define D9, what an "act" is.** Recommended: a dated reply with a guid8 and one outcome (pipe fixed / client contacted / dismissed with a reason), plus "had the client already asked? y/n". R1 is realized on the first real-office page that gets an outcome.
3. **Re-scope OD-79** to the A-18 rule. Recommended: yes.
4. **RF-1 slice-4:** one line in the data seat's room, *"slice-4 ENFORCE waits on the S-1 precondition"*, and push `contente` so R5 lives on a remote. (This seat corrected the mechanism: a 403 means retry and then drop, not a park.)
5. **Telos amendment authority:** let the seat merge `.know/telos` amendments that only transcribe D-rows already ratified, with before and after. Recommended: yes.
6. **Door conservation:** name it now as a declared gap, and make it the arc after R1.
7. **s1.6 merge timing:** after today's digest, as the default above.
8. **D13 rotation:** ASR's inventory runs last.

## Doctrine earned

- **Insights `and` over a field that may be absent evaluates to NULL.** Flags must be nested `if(ispresent(...))`. This was caught live, before merge.
- **Count deliveries, not lines.**
- **A change that can only make a pager quieter needs proof that the page still fires.** A change that can create a page needs the opposite proof.
- **Replaying logs from before a field existed proves nothing** about a rule keyed on that field.
- **A pass measured inside an input outage is thin.** Check the window's input first.
- **A precondition that lives on no remote ref does not exist.**
- **Know the pager's blind spots:**
  - fleet silence (now covered by OD-98);
  - per-office silence (not built);
  - 401/403 retries (seen by `ebi-no-lead-stop-match-auth-retry`, and by S-1 at a digest).
