---
type: handoff
initiative: read-the-name
wave: 1 · seam · READ THE NAME
seat: calendar-integration-locus (autom8y-asana session d5861864)
operator: Tom Tenuta
date: 2026-09-14
charge: .sos/wip/CHARGE-read-the-name-wave1-seam-2026-09-14.md
spine: .sos/wip/SPINE-read-the-name-wave1-2026-09-14.md
shape: .sos/wip/frames/read-the-name.shape.md (living; statuses annotated)
sitting: .ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md (R-160..R-172) + ADR-read-the-name-s1-implementation-2026-09-14.md (D1–D8, erratum E-1..E-4)
realization_predicate: R1 only (charge §1)
verdict_line_one: "R1 NOT REALIZED this wave — the instrument is built, deployed, probed live and soaking; the READER is withheld by the operator's own word (R-168). Every page path terminates on a scratch topic with zero subscribers."
---

# HANDOFF — read-the-name · wave 1 seam · 2026-09-14

## §0 The three sentences

1. **S-1, the per-office booking floor, is LIVE on the EBI log plane as of 2026-09-14T05:52:27Z** (`autom8-email-booking-intake-office-floor`, image `21d4395`, hourly; two page classes ZERO and RATE; in-run control; own deadman) — and **nobody is subscribed to what it says** (R-168: "Nobody yet: build, prove, do not arm").
2. The deploy took three dispatch runs to land — a whole-stack apply that **published the intake alias and then failed** on an SNS tag charset, then a re-fire that failed on a path-filtered twin guard — and the stack was never rolled back: roll-forward only, singleton held, receipted below.
3. **R1 is not realized**; the wave exits at the honest floor the sitting chose: instrument proven two-sided on the mechanism, soak clock started, reader withheld; S1.7 REFUSED-CORRECTLY, S1.8 NOT-STARTED, and the next command line is a daily soak read, not an arming.

## §1 DAG state per node (SPINE §1 numbering; shape statuses are the source)

| node | state | receipt / instant | critic |
|---|---|---|---|
| S0a shape packet | DONE | `.sos/wip/SHAPE-PACKET-read-the-name-wave1-2026-09-14.md` (F10–F12 new; SPINE numbering canonical) | — |
| S0b SHAPE sitting | DONE | sitting XI, R-160..R-172 (#446), erratum E-1..E-4 (#451) | operator |
| W0 Calendly tripwire verify + route | DONE | autom8y #2203 → `f9f31957` (`W0-calendly-tripwire-verify-2026-09-14.md` + telos closure; account id redacted for the `digits12` sweep) | change-warden |
| S1.1 observe (replay, K1–K5) | DONE | asana #448; K1–K5 PASS; window C bookings = 2 (E-3) | qa-adversary |
| S1.2 runbook + consumer word | DONE / word WITHHELD | asana #450; R-168 | change-warden |
| S1.3 build | DONE | autom8y #2205 → `4e8e163f` 05:19:36Z (auto-merged with a NON-required guard red; cure #2207 → `e33157a3` 05:24:31Z, birth-state registry row) | integrity-architect (C-1..C-3 cured) |
| S1.4a probe, pre-deploy | DONE | asana #452, eight poles two-sided | integrity-architect |
| S1.5 deploy | DONE | chain `34809228564` FAILED (apply: SNS tag) → #2210 `d408a38c` → `34810338540` FAILED (tests: registry-pin twin) → #2211 `21d43951` → **`34810812077` SUCCESS 05:57:00Z**; alias `live` v69 (`0850228`) → v71 (`21d4395`); receipt asana #453 → `7d21391e` (06:26:57Z) `DEPLOY-read-the-name-s1-2026-09-14.md` (pipeline-steward; alias between runs v70 `4e8e163`; 4-grant policy; rule ENABLED targeting the function; deadman pair INSUFFICIENT_DATA at birth) | change-warden CERTIFIED-WITH-ERRATA (7 errata, none falsifying; GATE-1 satisfied on realized output; disjointness capped MODERATE — the main thread drove the dispatches and dispatched the critic) |
| S1.4b probe, post-deploy live | DONE (four legs live, two-sided) | asana #456 `PROBE-read-the-name-s1-4b-2026-09-14.md`: leg A control PASSED both queries (14,002 / 605,299 records, 31 offices with bookings, 39 evaluated, 3 ZERO / 0 RATE, `paged:false`); leg B `FLOOR-REFUSED` `records_scanned_below_floor` (60 records, second query `NotRun`), timestamp WITHHELD; leg C dry-run emitted nothing; leg D the scheduled fire 06:27:15Z observed with its own cold start and datapoint; `LastSuccessTimestamp` 0 → 2 from 4 invocations; the topic's 4 publishes are all alarm `INSUFFICIENT_DATA → OK` transitions, zero from the evaluator; IAM StartQuery/GetQueryResults/PutMetricData PROVEN, `sns:Publish` + self-group StartQuery UNPROVEN-LIVE until 11:27Z; F-3 → S1.3 seat: `e63bbbe0` (9 arrivals) and `8a9b1a84` (7) sit in CLASS UNKNOWN above the ZERO floor and the run line has no `offices_unclassified`; `ccb52f4c` quiet at 3.23 % | integrity-architect CERTIFIED-WITH-ERRATA (E-1..E-6, applied by the station); neither structural refusal fires — a success timestamp on a half-run is UNREPRESENTABLE by construction (`_lookback_control` reassigns the single `control` and the refusal early-returns before `put_metric_data`); DEFECT-1 routed: `_publish` discards the `MessageId` |
| S1.6 soak ≥ 7 d | IN SOAK · day 0 | `SOAK-read-the-name-s1-2026-09-14.md` row 0 filled 06:41Z: 4 evaluations (3 controlled invokes + the 06:27:15Z scheduled fire), 3 controlled / 1 refused, 2 `LastSuccessTimestamp` datapoints, prober gauge 8 samples max 2000.6 s, both deadman alarms OK, 4 topic publishes all alarm OK-transitions and 0 from the evaluator, 0 subscribers | — |
| T1 S-4 malformed-GUID triage | DONE (read-only; three escalations to a sitting) | asana #455 → `ed82c93e` (06:36:38Z; revised `731a06ec`, ERRATUM block E-1..E-6 at line one) `TRIAGE-read-the-name-s4-malformed-guid-2026-09-14.md`: 145 residual lines / ≈4.31 d (the `office_identity_kind` field exists only since 2026-09-09T22:12Z), four classes — S4-A UUID missing its first hex group 13/39 · S4-B 12-hex no dashes 3/9 · S4-C one char 3/9 · **S4-D (61 %) not a GUID defect at all: a parse-stage missing-body webhook defect**; the S-1 `***` >10 % tripwire — first-pass claim "not measuring S-4" REFUSED by the qa-adversary: the pinned query has one filter (`ispresent(office_guid)`), so the tripwire sees **136 of 145 (93.8 %)** of S-4 and cannot distinguish it from the other `***` populations (88 of the 136 are the webhook-body class — a firing page names no class; ADR D5.3 was right and the triage's charge against it is withdrawn); `NON_TERMINAL_OFFICE_EVENTS` (`query.py:87-93`) is tests-only dead code (hygiene defer, S1.3 seat); **`redact_uuid` is a prefix matcher → `e5a68603` is a phantom office that ADR D5.4 treats as real**; `kind=absent` conflates never-ran with died-at-validation; the envelope-to recovery fallback is BUILT and structurally unreachable (domain-only check); six metric filters emit, zero alarms subscribe (NO WATCHER measured) | qa-adversary first pass REFUSED (one premise: the tripwire's population), everything else reproduced and certified; errata E-1..E-5 applied by the station; delta pass CERTIFIED-WITH-ERRATA (E-6: the D5.3 UV-P discharge was inverted — true split 88 absent-at-the-line / 59 present-but-refused — two doors to the same `***` with opposite remediations; applied at `731a06ec`); two-iteration cap NOT exhausted |
| T2 `15caa02c` books-while-dark | DONE (measured; class ruled by pythia) | asana #454 → `24886bca` `READ-read-the-name-15caa02c-books-while-dark-2026-09-14.md`: H1 (non-Offer path) NOT SUPPORTED — identical KIND to control `4ec260bf`, no path field exists on booking lines; H2 (stale Asana section) STRONGLY SUPPORTED — 354 stories, no recorded move into INACTIVE, control `ca70baa8` shows the mechanism works; Unit `Paused` properly recorded; resolver control 4/4 active, `00000000` absent; **found in passing: `chiropractor_guid` is not stamped on booking lines before 2026-09-09 → every guid-attributed booking figure is 6-day, not 30-day, until 2026-10-09** | pythia CERTIFY-WITH-ERRATA (E-1 headline over-reach: the measured core is "the transition is UNRECORDED", not "stale"; E-2 fleet attribution floor = 2026-09-09). RULING: class `inactive` at the Offer grain with a named provenance defect, live on the wire; `15caa02c` is ABSENT from the 29-row snapshot → renders CLASS UNKNOWN; snapshot LEFT AS-IS (hand-insert rejected: it would move the office to EXPECTED SILENCE the day it stops booking); the pre-2026-10-09 lookback bias is a DATED CALIBRATION HAZARD cured by a COMPUTED attribution floor printed on the page (no re-tune); the soak may certify ACTIONABLE and CLASS UNKNOWN, NOT EXPECTED SILENCE before 2026-10-09 |
| T3 C6 arm push on manifest-validate | LANDED-BEFORE-WAVE (verify-not-build) | autom8y #2177 `bb485521` 2026-09-11; one push run GREEN `34647518960` | change-warden (n/a — nothing built) |
| T5 WS-2 read-only recon | DONE | asana #447 → `2ef49ff6` (`RECON-read-the-name-ws2-2026-09-14.md`); consumer commitment NOT YET PAID | change-warden |
| S1.7 arm | **REFUSED-CORRECTLY** and BLOCKED(on the S1.2 consumer word, operator; AND on S1.6 ≥ 7 d) | success-gap alarm deliberately absent; re-point staged as ONE variable `office_floor_page_topic_arn`, not applied | — |
| S1.8 R1 attest (eunomia) | NOT-STARTED (entry: S1.7 exit) | line one pre-written: R1 NOT REALIZED — instrument proven, reader withheld | verification-auditor |
| T4 `/handoff` | THIS DOCUMENT | Gate C PENDING — verification-auditor reviews this PR; verdict recorded by a follow-up commit before merge | verification-auditor |

### F1–F9 (+F10–F12) dispositions — the sitting-XI digest path

| fork (SPINE) | ruling | disposition this wave |
|---|---|---|
| F1 evaluator home | R-164 (ADR D4): dedicated Lambda in `services/email-booking-intake/` via `service-lambda-scheduled v1.0.2` | BUILT, DEPLOYED |
| F2 cadence and hour | R-163 (ADR D3): hourly evaluate, page gate `hour == 11` UTC | BUILT; first scheduled fire OBSERVED 2026-09-14T06:27:15Z (own-hands `filter-log-events`, one page): `control: passed`, `records_scanned: 13979`, 39 offices evaluated / 31 with bookings, `paged: false`, `page_class: none`, `dry_run: false`, cold start Init 1200 ms, 7.6 s of 300 s, 136 MB of 512 |
| F3 own silence deadman | R-162 (ADR D2): C4 + L4 — prober `lambda-freshness-deadman v1.4.1` (`declared_cadence_seconds=3600`, `buffer_multiplier=2`, `rate(5 minutes)`) + `LastSuccessTimestamp` withheld on FLOOR-REFUSED; success-gap alarm at S1.7 | prober alarms LIVE on the scratch topic (INSUFFICIENT_DATA at birth); withheld-timestamp half PROVEN LIVE (leg B: `FLOOR-REFUSED` on a measured insufficiency, `LastSuccessTimestamp` withheld — 0 → 2 datapoints from 4 invocations, only the two controlled runs emitted); both-ways proof = S1.7 |
| F4 consumer word | R-168: nobody yet | WITHHELD → NOT ARMED, R1 not realized |
| F5 negative pole + class label | R-165 (ADR D5, E-2): dated snapshot 2026-09-11 (29 rows), `unknown` fallback, STALE > 30 d; class is CONTEXT never a suppressor | BUILT |
| F6 smoke leads | R-169: real offices, no marker | replay ran with no exclusion + sensitivity; codified as no predicate |
| F7 scan scope | R-166 (ADR D6): G1 no narrowing | BUILT (one pinned query constant, sha256 `4b9d3534…`) |
| F8 WS-0 disposition | R-171: verify + route | DONE (W0) |
| F9 WS-2 sequencing | R-170: recon this wave, build next with a dated consumer commitment | DONE (T5); commitment operator-held |
| F10 floor shape / arrival unit | R-160 two floors (ZERO A=5; RATE A′=20, r=0.025) · R-161 U-3 | BUILT; K1–K5 PASS |
| F11 degraded-run posture | R-162: FLOOR-REFUSED, timestamp withheld | BUILT; PROVEN LIVE (leg B: `FLOOR-REFUSED` on a measured insufficiency, `LastSuccessTimestamp` withheld — 0 → 2 datapoints from 4 invocations, only the two controlled runs emitted) |
| F12 repeat policy | R-167: a page every day with a day count | BUILT (day-N from the widened lookback) |

## §2 Receipts (i)(ii)(iii) as SVR — own-hands command, unpiped rc

The conjunction gate (charge §2): (i) PROBE LIVE two-sided · (ii) SUBJECT LIVE with in-query control · (iii) the instrument's own silence deadman proven both ways.

- **(i) PROBE LIVE** — **PROVEN LIVE, two-sided** (S1.4b, asana #456; own-hands corroboration 06:41Z): the positive pole — a healthy invoke and the scheduled fire both evaluate 39 offices with the control PASSED and emit the success timestamp; the negative pole — a 10-minute window is REFUSED (`records_scanned_below_floor`) with the timestamp withheld, and a dry-run evaluates without emitting; page paths: zero evaluator publishes (hour ≠ 11) and the four topic publishes are alarm OK-transitions to a topic with 0 subscribers. The SNS delivery of a real digest (`sns:Publish`) stays UNPROVEN-LIVE until the 11:27Z evaluation
- **(ii) SUBJECT LIVE with control** — **PROVEN LIVE** (own-hands, 06:41Z, `aws logs filter-log-events --log-group-name /aws/lambda/autom8-email-booking-intake-office-floor --filter-pattern '"office_floor_evaluated"'`, one page, rc 0): the first SCHEDULED evaluation at **06:27:15Z** ran both pinned queries over the live 3-day window with its in-run control PASSED (`records_scanned: 13979`, `offices_with_bookings: 31`, 39 offices evaluated) and emitted `LastSuccessTimestamp` (datapoint at 06:27Z, `SampleCount 1`, `Maximum 1789367235`); the negative pole stands beside it — the S1.4b station's 06:00:48Z invoke over a 10-minute window (`records_scanned: 60`, `offices_with_bookings: 0`) had its control FAIL, no timestamp emitted; the dry-run at 06:01:07Z evaluated and emitted nothing. Subject live, control two-sided, no page (hour ≠ 11)
- **(iii) deadman both ways** — **NOT PROVEN THIS WAVE**: the prober's freshness alarm and the prober-liveness alarm exist with actions = scratch (INSUFFICIENT_DATA at birth; verified 05:57:40Z, `describe-alarms --alarm-name-prefix autom8-ebi-booking-floor`, rc 0); the withheld-timestamp half PROVEN LIVE (leg B: `FLOOR-REFUSED` on a measured insufficiency, `LastSuccessTimestamp` withheld — 0 → 2 datapoints from 4 invocations, only the two controlled runs emitted); stop → page → restore → clear is S1.7's, behind the ≥ 7-day soak. `[UV-P: the freshness dead-man `autom8-ebi-booking-floor-lambda-freshness` transitions to ALARM when the evaluator stops being invoked and restores when it resumes | METHOD: S1.7 three-step on the scratch topic (disable the rule → wait > 7200 s → read state; re-enable → read OK) | REASON: entry criterion S1.6 ≥ 7 d not yet met; and the success-gap alarm is not created until then by ADR D2]`

**Deploy receipt (S1.5), the irreversible node:** asana #453 `DEPLOY-read-the-name-s1-2026-09-14.md` (pipeline-steward; alias between runs v70 `4e8e163`; 4-grant policy; rule ENABLED targeting the function; deadman pair INSUFFICIENT_DATA at birth) — merge sha `4e8e163f` (#2205), deploy runs as chained above, alias `live` before v69 `0850228` / between v70 `4e8e163` (partial apply) / after **v71 `21d4395`** (qualified reads), pending set at the merge instant = {`a1f3ecf3` #2200, already applied} (R-143 visibility), one deploy at a time (push plan `34810213990` drained before the second re-fire; 0 EBI runs in flight at each fire), never a manual Service Terraform apply, roll-forward only. Unanimity at the `21d43951` build: intake alias-served `21d4395` == office-floor `$LATEST` `21d4395` == contente-reconcile / forwarding-nudge / contente-retro-redrive `21d4395` (05:57:40Z, rc 0).

## §3 The soak table (S1.6) — appended daily by the resuming seat

Lives at `.ledge/reviews/SOAK-read-the-name-s1-2026-09-14.md` (this PR). Row 0 = 2026-09-14 (partial day). Seven complete consecutive rows close S1.6; the commands are in its §2; the closing criteria in its §3.

## §4 Risk map (SPINE §4.3 + what bit today)

| risk | status | carrier / mitigation |
|---|---|---|
| R-136 untargeted whole-stack apply on `services/**` merge | ACCEPTED, RECEIPTED (three applies today, all untargeted) | pending set enumerated at the merge instant (`scripts/ebi_pending_terraform.sh`, anchored on the last succeeded EBI deploy job); singleton held |
| image-pin rollback | NEVER (both stacks) | EBI pin RETIRED at `a1f3ecf3` (#2200) — registry-resolved alias-served tag; asana still PINNED → the manual Service Terraform apply hard stop stays for asana |
| `office_phone` not widened (row 12) | HELD | no producer change this wave |
| orphaned Calendly tripwire IaC | OPEN | W0 routed to the monolith owner (nominated, nothing sent); 0 of 3,894 `.tf` |
| the F3 hole if prober-only were ruled | CLOSED BY RULING | R-162 = C4 + L4, not prober-only |
| state-lock singleton | HELD | push plan drained before each re-fire; 0 in flight at fire (log `refire-2026-09-14.log`, `refire3-2026-09-14.log`) |
| **NEW · a non-required check does not gate auto-merge** | BIT (#2205 merged with the registry guard RED) | cure #2207; rule: add the registry row in the same PR; read `gh pr checks` for every red |
| **NEW · a whole-stack apply publishes before it fails** | BIT (`34809228564`: alias moved to `4e8e163`, then SNS tag error) | read the run's conclusion AND the `Plan:` vs creation-complete lines; the alias flip is not success |
| **NEW · SNS tag values reject parentheses** | BIT | `Purpose` tag rewritten (#2210); terraform guard tests parse structure, not AWS charsets |
| **NEW · a scripts-only registry change is not tested by the path-filtered service CI it breaks** | BIT (`34810338540`) | #2211 gives the EBI twin the `pending:` grammar; run both guards before any registry-row merge |
| **NEW · the merge-surface sweep rejects the 12-digit account id inside quoted ARNs** | BIT (#2203) | `<ACCOUNT>` in every record; `grep -n -E '[0-9]{12,}'` before commit |
| **NEW · the deploy singleton is GATING, not a lock** (change-warden P-2: `service-deploy-dispatch.yml` and `service-terraform.yml` serialise on different concurrency groups; it held today only because every Service Terraform Apply was skipped) | NAMED | drain-before-fire discipline is the only guard; a shared concurrency group is an R-143 charge item |
| **NEW · the demoted guard was the load-bearing signal** (change-warden P-1: the non-required hermetic guard went RED 99 s before #2205 auto-merged and predicted both failed dispatches) | NAMED → sitting | re-examine the ruling that left it non-required |
| **NEW · the office-floor function has no alias** → no version-pin rollback lever; safety rests on containment (scratch, 0 subscribers, concurrency 1) | ACCEPTED at unarmed birth-state | must not be carried silently into the promotion that retires `pending:` |
| a page reaches `platform_alerts` before the word | HELD | one variable, scratch default; zero subscriptions verified 05:57:40Z |
| reserved concurrency 1 vs a manual invoke at the scheduled minute | NAMED | never invoke between :20 and :35 |
| **the freshness deadman reds at roughly the FOURTH missed fire** (`DatapointsToAlarm 2 of 3` at P3600 / > 7200 s): one, two and three missed hourly fires are invisible to it; the DLQ alarm (P300, 1 eval) is the faster floor; a stuck invoke cannot starve the schedule (300 s ≪ 3600 s) | NAMED (integrity-architect, S1.4b charge 5) | S1.7 both-ways proof must state the detection latency; all floors route to the 0-subscriber topic until the word |

## §5 Defer registry — owner · trigger · watcher

| item | owner | trigger | watcher |
|---|---|---|---|
| the S1.2 consumer word → S1.7 arm (re-point `office_floor_page_topic_arn` to `platform_alerts`, success-gap alarm creation, deadman both ways) | operator | the word, in this seat's room | NO WATCHER (by R-168's own choice) |
| promote `pending:autom8-email-booking-intake-office-floor` to a live registry member (`EBI_FNS` in `scripts/tests/test_apply_preserve_fuel.py`, `_EXPECTED_SOURCES` in the EBI twin, the TSV row) | S1.3 builder seat | the function is BORN (it is, 05:52:27Z) | the resolver's PENDING-BUT-BORN notice on every resolve; `test_pending_entries_are_not_yet_born_live` where live AWS is readable |
| S1.6 daily soak rows 1..7 | the resuming seat | each UTC day close | the soak table itself; a missing row is the finding |
| the 11:27Z digest's live SNS delivery (a real `MessageId` on the scratch topic; `sns:Publish` proven) | the resuming seat (day 1 read) | 2026-09-14T11:27Z scheduled evaluation | NO WATCHER until read |
| WS-2 build charge + dated consumer commitment | operator (next sitting) | — | NO WATCHER |
| WS-3 (c2) coverage behind the identity one-pager (R-110) | operator | — | NO WATCHER |
| WS-4 GHL contactId un-scaffold | operator | after WS-1..3 produce its control | NO WATCHER |
| R-143 charges (apply-visibility notice · Service Terraform rollback guard); asana pin drop on the #2200 precedent | to be seated | — | NO WATCHER |
| Calendly drafts #1561/#1563/#1564 + recon rule (R-153 untouched); orphaned tripwire IaC routing | operator (monolith owner nominated) | — | NO WATCHER |
| S-4 recoverable classes (if T1 names an unbuilt recovery) | next decision-space sitting (the tripwire cannot separate S-4 from the other `***` populations — re-ask against 94 %, not 11 % · the `e5a68603` phantom KEY (`guid8_of()` has no validation; not a snapshot row; cannot reach A=5 today at 3 lines) in D5.4 · split `absent` · arming any of the six unwatched metrics); the envelope-fallback local-part cure is a seat's once ruled | — | NO WATCHER (measured: 6 filters, 0 alarms) |
| `15caa02c` class ruling | pythia (critic on T2) | T2's read | SUPERSEDED by erratum E-2's wire-decides join (pythia R-3): (a) render `⚠ DARK-BUT-BOOKING` on the join E-2 already performs → S1.3/S1.4 builder seat; (b) provenance → the WS-2 offer-grain observer, trigger = a sourced refresh inserting `15caa02c: inactive` while its last `section_changed` is an active-class move |
| re-examine the non-required status of `Guard teeth tests (hermetic)` (change-warden P-1) and the split concurrency groups (P-2) | operator (next sitting) / R-143 charge | — | NO WATCHER |
| computed booking-attribution floor printed on every page (pythia R-2: the fleet stamping horizon is 2026-09-09; the 30-day lookback is 6 days effective today, whole on 2026-10-09; a constant is rejected — the computed floor is disclosure and regression-detector in one; folds into ADR §12 row 3 with the trigger widened beyond `residual_share > 10 %`) | WS-1 successor / S1.3 builder seat | next evaluator change; before any EXPECTED SILENCE is certified | the soak table's rule: no EXPECTED SILENCE certified before 2026-10-09 |
| snapshot `note` claims coverage of the named positive controls but the sole disconfirming control `15caa02c` is absent (pythia §12 row 1) | snapshot owner | next sourced refresh (due 2026-10-11) | NO WATCHER |
| `[UV-P: office_name is on booking lines before 2026-09-09 | METHOD: key inventory on pre-09-09 booking lines | REASON: T2's inventory came from 25 lines inside the stamped era]` | WS-1 successor | — | NO WATCHER |
| **DEFECT-1** (integrity-architect on S1.4b): the evaluator's `_publish` discards the SNS `MessageId` (0 `MessageId` events group-wide) — a publish leaves only a flipped boolean, so the S1.4a UV-P's demanded receipt cannot be produced by the deployed code and the 11:27Z `sns:Publish` discharge inherits the same-minute ambiguity with alarm OK-transitions | S1.3 builder seat, before the arming word | next evaluator change (log the `MessageId` on the run line) | NO WATCHER |
| UV-P-A: the five `day_n_*` lookback-control predicates (the DW-10 cure, the load-bearing half of D2) have zero live exercise — leg B hit 1 of the primary control's 6; the event contract may make a lookback-only refusal structurally unreachable live | change-warden (reachability seam) + S1.3 seat | before the arming word | NO WATCHER |
| UV-P-B: R-172 at-most-one-publish per UTC day is best-effort suppression with a named fail-open (`PageLedger.unread` publishes anyway); a two-sided proof needs the positive, the teeth, and the taken zero (self-log ingestion latency vs `MaximumRetryAttempts 2` / `MaxEventAge 3600` = up to three deliveries) | S1.3 seat + the day-1 read at 11:27Z | before the arming word | the soak's pages/day column |
| S1.4b F-3: two ZERO-floor offices (`e63bbbe0` 9 arrivals, `8a9b1a84` 7) sit in CLASS UNKNOWN on the first live run and the run line carries no `offices_unclassified` (C-4 coverage counter) | S1.3 builder seat, before the arming word | next evaluator change | the digest's CLASS UNKNOWN section (printed daily to scratch) |
| `sns:Publish` and self-group `logs:StartQuery` (idempotence lookback) UNPROVEN-LIVE | the resuming seat (day-1 read) | 2026-09-14T11:27Z digest | NO WATCHER until read |
| F7 ceiling (Insights scan cost if the plane grows ×10) | seat | a 3-day scan > 50 MB | NO WATCHER |
| stale worktrees of earlier seats under autom8y `.knossos/worktrees/` (8 listed, none this wave's) | hygiene | — | NO WATCHER |

## §6 Unresolved claims (frozen syntax)

- `[UV-P: the captured SNS publish is DELIVERED by the AWS SNS service to aws_sns_topic.office_floor_scratch and returns a real MessageId | METHOD: read the 2026-09-14T11:27Z digest's office_floor_evaluated line for the message id and NumberOfMessagesPublished=1 on the topic for hour 11 | REASON: no force-page lever exists by design; the page gate is hour == 11 only]`
- `[UV-P: the EventBridge rule fires the evaluator at most once inside the hour-11 window | METHOD: count office_floor_evaluated lines with 11:00 ≤ ts < 12:00 on day 1 (expect 1) | REASON: first day of life]`
- `[UV-P: the terraform office_floor_page_topic_arn re-point reaches BOTH consumers (Lambda env + every alarm_actions) with one variable | METHOD: plan diff on the word, then qualified env read + describe-alarms | REASON: R-168, not applied]`
- `[UV-P: sns:Publish from the evaluator's own role reaches the scratch topic and returns a MessageId; and logs:StartQuery on the evaluator's SELF log group (the date-keyed idempotence lookback) succeeds | METHOD: the 2026-09-14T11:27Z scheduled evaluation's run line (paged:true, MessageId, idempotence_status) and NumberOfMessagesPublished = 1 in hour 11 | REASON: both sit behind the page gate; no force-page lever exists by design]`
- `[UV-P: offices_unclassified (the C-4 coverage counter) is on the run line | METHOD: read the ADR D8 field list against the live run line | REASON: S1.4b F-3 — two ZERO-floor offices sit in CLASS UNKNOWN on the first live run; routed to the S1.3 seat before the arming word]`
- `[UV-P: the envelope `To:` on the 19 S4-A/B/C traces carried an intact GUID (decides whether the built fallback would recover 19 traces or 0 once its local-part check is cured) | METHOD: read the envelope field on those request ids in the intake log group | REASON: T1 time-box; masked shapes only]`
- `[UV-P: the `-contente-reconcile` log group (6.9 MB stored, unswept by T2) carries no unaccounted bookings for `15caa02c` | METHOD: the same U-3 Insights read over that group with recordsScanned | REASON: T2 time-box; H1's only surviving revival path]`

## §7 Standing re-verification, then the exact next command line (cold-resumable)

```bash
git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana fetch origin main && git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana rev-parse --short origin/main   # expect ≥ ed82c93e (this handoff's own merge will move it)
git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y fetch origin main && git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y rev-parse --short origin/main               # expect ≥ 21d43951
V=$(aws lambda get-alias --function-name autom8-email-booking-intake --name live --query FunctionVersion --output text); aws lambda get-function --function-name autom8-email-booking-intake --qualifier "$V" --query Code.ImageUri --output text   # expect v71 · :21d4395 unless a later deploy moved it (read, do not assume)
aws lambda get-function --function-name autom8-email-booking-intake-office-floor --query Code.ImageUri --output text   # unqualified IS served (no alias); expect the same tag
aws sns list-subscriptions-by-topic --topic-arn "arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch" --query 'length(Subscriptions)'   # expect 0 until the word
```

Then, each UTC day until seven complete rows stand:

```
# S1.6 · day N — append one row to .ledge/reviews/SOAK-read-the-name-s1-2026-09-14.md with its §2 commands, own-hands, rc unpiped; PR it (docs). On day 1 also read the 11:27Z digest (the live SNS leg) — see §6.
```

After row 7, and ONLY on the operator's word in this seat's room:

```
# S1.7 · Task(chaos-engineer, "arm S-1 per shape S1.7 on the word: re-point office_floor_page_topic_arn → platform_alerts (one variable, plan diff shows BOTH consumers), create the success-gap alarm, prove the deadman both ways on the live topic; critic integrity-architect")
# S1.8 · Task(verification-auditor, "R1 attestation per shape S1.8, rite-disjoint, none inherited")
```

Fences that bit this wave, verbatim for the resuming seat: `<ACCOUNT>` for the account id · no phone digits · guid8 only · `git show origin/main:<path>` and name the ref · qualified reads on aliased functions, unqualified on the office-floor (no alias) · rc unpiped · zsh no word-split · a non-required check does not gate auto-merge · a whole-stack apply publishes before it fails · never a manual Service Terraform apply on the pinned asana stack · nothing merges on a relay, nothing bundles, nothing past red · a peer's relay is never authorization.
