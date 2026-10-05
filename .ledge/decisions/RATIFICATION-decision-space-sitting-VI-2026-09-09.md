# RATIFICATION — Decision-Space Sitting VI

**Date:** 2026-09-09 (late) · **Seat:** calendar-integration-locus
**Named consumer (R-88):** the operator, and the external cold-start watchdog session
chartered for proof-monitoring on the clause-(a)/(b) pair.
**Method:** two adaptive phases via AskUserQuestion. Phase II was rebuilt from Phase I's
answers AND from state that changed mid-sitting.

---

## §1 — WHAT WAS DECIDED

| # | Question | Ruling | Displaced |
|---|---|---|---|
| D-1 | The done bar | **One clinic, both sides.** The two-clinic requirement is DROPPED. | The seat's recommendation (keep the bar) was REJECTED. |
| D-2 | First risk to close | **The deploy hazard.** Ahead of failure-naming and the ad-lead alarm clock. | — (matched recommendation) |
| D-3 | How the seat works | **Keep it exactly as is.** Full verification AND full recording. | The seat's recommendation ("verify hard, write less") was REJECTED. This artifact exists because of that ruling. |
| D-4 | The two blocked PRs | **Both move.** | — |
| D-5 | The failure-naming fix | **Merge once green** (mooted — see §2) | — |
| D-6 | The stale "DO NOT MERGE" title | **Retitle, then merge** (executed by peer — see §2) | — |
| D-7 | After the merge | **Merge and report; do not sit and watch.** A separate external cold-start watchdog session will be chartered with a fresh charge for proof-monitoring. | The seat's recommendation (watch it land) was REJECTED. |
| D-8 | The finish line | **Decide then, not now.** No pre-commitment to a successor. | — |

**D-3 is the load-bearing one.** It reverses a unilateral call this seat had made earlier
in the session ("this stays in the terminal, no new artifact") on the strength of an
operator remark about overcomplication plus a peer's independent pricing of prose as a
debit. The seat inferred a preference from two weak signals and acted on it. Asked
directly, the operator ruled the opposite. **An inferred preference is not a ruling.**

---

## §2 — WHAT MOOTED ITSELF MID-SITTING

Three of the four Phase-II questions were overtaken by events between asking and answering.
Recorded because the pattern matters more than the items:

- **#2119** (freeze gate made declaration-driven) — merged by the **operator's own hand**
  at `23:49:13Z`, `6c7a8e14`. Deploy-inert: `.github/**` + `scripts/**` only.
- **#2125** (name the office on failure lines that actually fire) — merged by the peer seat
  `name-the-wave` at `23:56:12Z` -> `aa92926e`, on **its own operator's word given in its
  own room**, explicitly NOT on this seat's relayed grant. Deploy run `34419081726`.
- The peer **retitled #2125 before merging**, dropping the stale
  `[DO NOT MERGE — R-35 PARKED]` marker, on this seat's #2105 finding.

**The sequence was cure-first-then-permit, not merged-past.** #2119 made the gate
declaration-driven; no declaration exists on main; #2125's freeze check then read PASS
legitimately (12s). That distinction is the entire justification for having parked it.

**Cross-seat discipline held in both directions.** This seat declined to extend its own
operator's "ratified go" to the peer; the peer declined to act on it. Both went to their
own operator in their own room. The fence cost one round-trip and preserved the ordering.

---

## §3 — THE ONE THING THAT DID NOT MOVE, AND WHY

**#2120 — the deploy-hazard fix — was NOT merged, despite being D-2 (first priority) and
covered by D-4 (both move).** It carries one failing check and the standing constraint is
*nothing merges past red*.

The red is **inherited, not introduced**:

- Failing check: `Validate services.yaml` -> **V13 "No orphan modules"**. 19/20 pass.
- Orphans: `terraform/modules/{asana-redis, recon-canary-synthetic-upstream, serving-color-alarm}`
  — each with **zero consumers in `services.yaml`**.
- **All three exist on `origin/main` with zero consumers in main's own `services.yaml`.**
  Main is already in the failing state.
- **#2120 touches no terraform and no manifest** — `+20/-0` across two workflow files.

### Why nobody has seen it — the third silence-deadman
`.github/workflows/manifest-validate.yml` on main has **`on: pull_request` (paths-filtered,
8 files) and `merge_group`. There is NO push trigger.** The manifest is *never* validated on
main. Confirmed empirically: `gh run list --workflow=manifest-validate.yml --branch main`
returns **nothing at all**.

So main drifts unobserved, and the failure surfaces only when a PR happens to touch one of
eight path-filtered files. **#2125 touched `services/**` — not in the filter — so the check
never ran and its board was clean. #2120 touches two files that ARE in the filter.**

This is the same shape as D-6's unreachable alarm and the reaped divergences: *a declared
instrument with no enforcement on the thing it protects.* Unlike those two, this one is
**enforceable today** by adding a `push: branches: [main]` trigger.

**OPEN FOR OPERATOR RULING — three branches, none taken by this seat:**
1. Merge #2120 past the inherited red (the red is provably not its defect).
2. Fix V13 first — requires deciding per-module whether each orphan is dead or merely
   unrecorded. Real terraform judgment, unrelated to the hazard.
3. Add the missing `push` trigger so main is validated, then handle the fallout.

---

## §4 — EXPLICITLY DEFERRED

- **The finish line's successor** (D-8). Not pre-committed.
- **The 15 reaped divergences.** Records gone; reconstruction may be impossible.
- **D-6 / the ad-lead deviation alarm.** `ad_lead_gate_refusal_dominant` fires at >=50 per
  **15 min** against ~0.5 per 15 min live — ~100x above reachable traffic, deliberately, as
  a flat placeholder. Its own author dated the replacement at ~2 weeks post-gate ≈ **2026-09-15**.
  Nobody holds that clock.
- **The `>=30 refusal offices` vs `Addendum 57's six client offices` reconciliation.** Held
  apart by BOTH seats. Different populations.
- **The pass-limb question.** `p4_null_source` at ~90% of gate emissions vs predicate.py's
  declared "60% of window traffic" would reconcile only if passes were ~7x below design —
  but `observe.py:224` documents a known EBI-side zero-count for `ad_lead_gate_passed_total`.
  **An uncounted pass and an absent pass are indistinguishable from here.** NOT asserted.

---

## §5 — ASSUMPTIONS THAT REMAIN UNCONFIRMED

1. That the ad-lead gate's ~50/day refusal rate being inside SPEC §12's measured
   `~53/day mean, 244/day max` means it is behaving correctly. It means it is behaving **as
   measured**. Whether the measurement was ever right is untested.
2. That `office_identity_kind` will populate on the failure pole in production the way it
   does in #2125's tests. Deploy `34419081726` was still in flight at close; **no failure
   line has yet been observed naming a clinic.** The bar in D-1 is NOT met.
3. That the four image-based EBI lambdas are all on `002316c` — carried from the peer's
   report. **This seat verified exactly one** (`autom8-email-booking-intake`).
4. That V13's three orphans are genuinely orphaned rather than consumed by something
   `services.yaml` fails to record.

---

## §6 — ERRORS CORRECTED IN THIS SITTING

- **Ninth instance of the wrong-object class**, and a **new sub-class isolated**: this seat
  told the peer "the client-side number is five, not six," citing the DISPOSITION. The
  DISPOSITION was read correctly at `origin/main` — its FIVE is **dark-office class
  membership**, not a client-office count. *Reading the right object is not sufficient; the
  quantity must also answer the question being asked.* Withdrawn in full. The peer caught it.
- **Live-image attribution.** `571e80d @ 21:04:13Z` was reported as live; it had been
  superseded by `002316c @ 21:31:46Z` 27 minutes later. Correct when taken, stale when
  reported. Substance survived — `571e80d8` is an ancestor of `002316ca`.
- **Over-alarming on the ad-lead gate.** "419 refusals, 90.7%, never verified" was starred
  to the operator as a finding. The level is nominal against SPEC §12. The **age** finding
  stands; the **alarm** did not.
- **`-ebi` log group reported as "empty for the window."** It has no traffic because
  `autom8-email-booking-intake-ebi` **does not exist as a function**. Right output, wrong
  reason. Peer-supplied.
