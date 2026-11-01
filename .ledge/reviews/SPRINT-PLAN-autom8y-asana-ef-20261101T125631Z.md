---
type: review
status: proposed
---

# SPRINT-PLAN: autom8y-asana-ef, 2026-11-01 (Pythia ROUTE)

**Seat preamble.**
- **What ran:** one read-only Pythia ROUTE consult, under the conductor's throughput brief 2c4a5071d572.
- **When:** on the clerk's START stamped 2026-11-01T12:52:06Z (register row 18018). Dispatched 12:52:2xZ; the seat read the result at about 12:56Z and sealed this file at 2026-11-01T12:56:31Z (date -u).
- **What it is:** the consult's text below, verbatim except that the seat removed its opening line, home paths, and its closing tool notes. The consult wrote no files.
- **Status:** this file authorizes no act. Each task still needs its own clerk START or GO, the bench's cert, and Tom's typed line where a floor applies. Merges of served code run under Tom's repo-scoped word e867ea33d989 (clerk rows 18000/18008).
- **Binding:** paste 77e004973e00 + ADDENDUM-1 9b30bae7eae4 (clerk row 17999). Item (a) of the paste (asana hook births) is CLOSED by the bench's REBIND v2 ADDENDUM-2 (13e209b5b142, 30/30 PASS on 10-26) and is not a task here.

**What changes the plan (all checked this consult, asana main d912fa0d3e59, api-schemas main 6c6078bfcd11):**
- **The asana fix is needed whichever side the bench rules wrong.** Run 41307532165 failed at step 1, which diffs every tier against a baseline with 0 entries. The log lists all five violations: ads 2, asana 3, sms 0. Step 2 never ran. The only ways asana passes step 1 are the annotations, or a baseline entry made on the api-schemas side. So the guard defect is a card, not a gate on A.
- **The full check cannot go green from this seat alone.** Step 1 fails on the two ads fields (BusinessOfferRecord, CampaignCreated), which belong to seat a8-ads. Today, LANDED for R-03 can only mean: a fresh run shows `0 violation(s) found in autom8y-asana`, and the AFTER is graded. A green check on main is MERGED-not-LANDED until a8-ads fixes its pair.
- **No calling code, tests or mypy need to change.** All four canonical types are `Annotated[str, ...]` (api-schemas 1.11.0 is locked), so mypy sees `str`. All three files use `from __future__ import annotations`, and TC002 is ignored repo-wide. The guard accepts a top-level `from autom8y_api_schemas import OfficePhoneField`: formatter.py and clients/data/models.py already import it that way and are not flagged.
- **The name pattern is anchored.** `appt_office_phone`, `lead_office_phone` and `campaign_office_phone` in landing_receipt.py correctly do not match, so the count stays at three.
- **Merge order matters.** main requires branches to be up to date (`strict: true`) and linear history. Whichever PR merges second must update its branch, which moves its head, re-runs CI and needs a new bench cert.
- **Tom's word resolves.** e867ea33d989 is filed at clerk rows 18000/18008: the repo-scoped asana deploy-on-merge, through 11-07 23:59 ET.

## (1) Tasks

| id | task | specialist | inputs | acceptance | blocked-by |
|---|---|---|---|---|---|
| A1 | Annotate three fields: `EnrollmentIntent.office_phone: OfficePhoneField` (intent_projection.py:452), `_ResolvedBusiness.office_phone: OfficePhoneField \| None` (leads_consumer.py:76), `Booking.contact_phone: E164PhoneField \| None` (landing_receipt.py:343, matching resolver_models.py:88). Add the imports. No logic changes. Run local gates. | janitor | d912fa0d3e59; guard at 6c6078bfcd11 | diff is 3 files and only annotations plus imports; ruff and mypy clean; tests pass (test_leads_consumer, test_grain_bridge_canary, enrollment tests); guard run locally on the tree in both modes (full, then `--strict-only`) reports 0 asana violations | none |
| A2 | Check visibility (`gh repo view --json visibility`), push the branch, open the PR | release-executor | A1 branch | PR open; ls-remote head matches | A1 |
| A3 | Watch CI: all 9 required contexts on the PR head (again after any branch update) | pipeline-monitor | A2 head | green rollup | A2 |
| A4 | Write the BEFORE line and the AFTER terms as window deltas, declared before the merge. Cover the ECS service (steady state, served image, Fast Burn / High Error Rate alarms, 5xx) and the enrollment-intent-bridge Lambda at its alias-served version, not $LATEST | observability-engineer | fleet deploy topology; the Lambda wrong-object trap | BEFORE record by sha; AFTER terms declared | none |
| A5 | Bench cert on the final PR head. It includes the ruling on which side is wrong (advice only; it does not gate A) and the type choice for `contact_phone` (E164 or Lead) | change-warden (bench) | A3 run, A4 BEFORE, final head | cert by sha | A3, A4, B7 (strict order, see edges) |
| A6 | Squash-merge under e867ea33d989 in dials' slot with `--match-head-commit`, then read back main. Never dispatch satellite-dispatch.yml | release-executor | A5 cert | clerk GO; main readback | A5, dials' slot |
| A7 | Deploy watch: Test@main, then Satellite Dispatch (workflow_run), then the ECS roll and Lambda publish | pipeline-monitor | A6 merge sha | green chain, or red with a diagnosis | A6 |
| A8 | AFTER read against the A4 terms; the bench grades it | seat-run kit | A4 terms, A7 | AFTER record; bench grade | A7 |
| A9 | Fresh R-03 run after A6. RTL re-runs 41307532165 or a new api-schemas PR runs it; the seat reads the log | pipeline-monitor (read); the re-run is RTL's act | run id, A6 sha | step-1 log shows `autom8y-asana: 0 violation(s)` | A6, RTL's re-run |
| B1 | soak_row.py from origin/main (python3.12), one read per day for 2026-10-11 through 10-31. Raw output goes to the git-ignored seat tree, not /tmp | seat-run kit | helper at d912fa0d3e59 | 21 outputs; check that 12-digit tokens are redacted | none |
| B2 | Write rows 27..47 in the current row format. No row where every cell is UNTAKEN | seat-run kit | B1 outputs | rows parse; table intact | B1 |
| C1 | Seal this plan as `.ledge/reviews/SPRINT-PLAN-autom8y-asana-ef-<stamp>.md` in the same commit as B2 | seat-run kit | this text | file scrubbed: no home paths, no session ids, no AWS account ids, no full GUIDs | none |
| B3 | Check visibility, push, open the PR (.ledge-only: SOAK plus SPRINT-PLAN) | release-executor | B2+C1 commit | PR open | B2, C1 |
| B4 | Watch CI on the B PR (pull_request is not path-filtered, so the full suite runs) | pipeline-monitor | B3 head | green rollup | B3 |
| B5 | W5 confirmation: parse test.yml paths-ignore at the merge base, confirm the diff is only `.ledge/**`, cert | change-warden (bench) | B3 head, test.yml | cert | B4 |
| B6 | A229 pre-merge notice to ASR | seat-run (clerk line) | B5 cert | notice sent | B5 |
| B7 | Squash-merge (W5) | release-executor | B5 cert | clerk GO; main readback | B6 |
| B8 | Post-merge run list for the merge sha (expect zero Test runs and zero Satellite Dispatch runs), sent to ASR. Soak lane closes | seat-run kit | B7 sha | run list sent | B7 |
| D1 | CARD to a8-ads: its two fields keep R-03 red at step 1 (evidence: run 41307532165) | seat-run (card) | run log | card filed with owner, deadline, next authority | none |
| D2 | Add evidence to the existing guard card (relayed to RTL 12:50:55Z, so no new card). Its docstring at :213 agrees with the code (other containers are strict); only the field comment at :190-191 says "dataclass/TypedDict/other" are lenient. TypedDict is also not detected, so it falls to strict | seat-run (card note) | guard at 6c6078bfcd11 | note appended | none |
| D3 | CARD to the conductor: board line L1494 still reads "hook births WAITING". The correction logged at L8070 (births ran 10-26, 30/30 PASS) was never applied to that line | seat-run (card) | board L1494, L8070 | card filed | none |

## (2) Dependency edges

- A1 → A2 → A3 → A5 → A6 → A7 → A8. A4 → A5. A6 → A9 (which also needs RTL's re-run).
- B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8. C1 → B3.
- **Order rule (strict):** merge B before A. A's final cert (A5) binds to A's head after B7 and the branch update. This costs one A3 re-run and avoids voiding a cert later. If B stalls on log retention (UV-P 1), reverse the order: the B update is .ledge-only, so its re-cert is cheap.
- D1, D2 and D3 depend on nothing.

## (3) Parallel groups (agent cap 2; seat-run kits and the bench use no slot)

- **G1, start now:** janitor on A1 and observability-engineer on A4. Kits alongside: B1 (21 reads), C1, D1, D2, D3.
- **G2:** release-executor on A2 and B3 (one dispatch, two PRs), then pipeline-monitor on A3 and B4 (one dispatch, both PRs).
- **Bench:** B5, then A5 after the update.
- **G3:** release-executor on B7 (after B6), then the A branch update; pipeline-monitor re-runs A3.
- **G4:** release-executor on A6 in dials' slot, with pipeline-monitor on A7.
- **Kits:** A8 and B8.
- **Waiting on other seats:** RTL's re-run for A9; a8-ads' fix for a full R-03 green.

## (4) UV-P list (unverified premises)

1. The office-floor log group keeps logs for at least 21 days. If it keeps less, the October 11 to roughly 17 rows lose their log-derived cells (UNTAKEN, never zero). B1's first read answers this.
2. A re-run of 41307532165 checks out the current asana main. The satellite checkouts pin no ref, but this is not proven for re-runs.
3. Who is allowed to re-run R-03 in api-schemas (a private repo the seat does not own): RTL, under R-C197 ADDENDUM-1?
4. Nothing passes EnrollmentIntent or _ResolvedBusiness through Pydantic. Pydantic would validate NamedTuple and dataclass fields there. enrollment_intent_bridge.py has no BaseModel or TypeAdapter; other consumers were not checked.
5. The asana deploy republishes the enrollment-intent-bridge Lambda (the hybrid stack), so the AFTER must read the alias-served version.
6. landing_receipt.py runs in an environment where autom8y_api_schemas can be imported. Moving the import under TYPE_CHECKING would also pass the guard, because it matches tokens; A1's local guard run proves whichever form is used.
7. How to number rows when a day is all UNTAKEN (skip the number, or record a gap note): the clerk or the bench rules.
8. dials has a slot today, and the A229 format and recipient are still current.
9. When a8-ads will fix its pair. That decides when the full green on main is possible.

## (5) Longest pole

**A, from fix to AFTER to fresh R-03 read.** Seven serial steps: PR CI, B merging first, then the update and CI re-run, bench cert, dials' slot, Test@main to Satellite Dispatch to ECS roll and Lambda publish, the AFTER window, then RTL's re-run. Two of those handoffs are outside the seat (dials, RTL).

What shortens it:
- Start A1 and A4 now.
- Ask the bench for the type ruling (E164 or Lead) before the cert.
- Have the clerk pre-book dials' slot.
- Pre-stage the RTL re-run request with the A6 sha placeholder, so A9 fires the minute A7 is green.

The full R-03 green on main is a tail that belongs to a8-ads (D1), not to this seat.
