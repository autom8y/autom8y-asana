---
type: review
artifact_role: external-critic-verdict
slug: sre-critic-verdict
status: accepted
rite: EXTERNAL (rite-disjoint from sre)
critic_role: adversarial-verification (default-skeptical; tried to REFUTE)
head: f4f924d2684386093ef656ecde5e98613cdffce8
date: 2026-06-24
aws_account: 696318035277
aws_region: us-east-1
targets:
  - .ledge/reviews/sre-observability-design.md (N1, observability-engineer)
  - .ledge/reviews/sre-dark-subsystem-postmortem.md (N2, incident-commander)
discipline: "Default skeptical. No GREEN without an independently re-run receipt or a read of the actual file:line. Rungs checked for round-up. G-DENOM: no proven-zero accepted from silence."
verdict: CONCUR-WITH-FLAGS
---

# External Critic Verdict — SRE observability design + dark-subsystem postmortem

> **RITE-DISJOINT external critic (NOT sre).** All AWS calls re-run independently, read-only.
> All file:line claims re-read at HEAD `f4f924d2`. I tried to refute; I could not refute the
> load-bearing claims. Flags below are honesty/precision nits, not defects in the conclusions.

## Overall verdict: **CONCUR-WITH-FLAGS**

- GREEN: **18**  ·  RED: **0**  ·  FLAGS (amber, non-blocking): **4**
- **No BLOCKING item.** Every load-bearing receipt reproduced on my own re-run. The four flags are
  precision/under-claim issues that, if anything, *strengthen* the artifacts' theses.

---

## GREEN/RED matrix

| # | Claim under test | Source | Verdict | Independent receipt (my re-run) |
|---|---|---|---|---|
| C1 | HEAD = f4f924d2 | both | **GREEN** | `git rev-parse HEAD` = f4f924d2684386093ef656ecde5e98613cdffce8 |
| C2 | Commit SHAs/dates (42b7cb0b 06-17 12:24; dd8e43ab 06-19 10:07; af2b012a 06-16; 29b7c439 06-18) | N2 §1 | **GREEN** | `git show -s` all four match exactly incl. timestamps |
| C3 | AWS account 696318035277 / us-east-1 | both | **GREEN** | `sts get-caller-identity` = 696318035277; all probes ran in us-east-1 |
| C4 | insights-export Lambda Errors=0 ×7d; Invocations 06-17=2, 06-18..23=1/day | N1 §A-a | **GREEN** | re-ran `get-metric-statistics`: Errors `[0,0,0,0,0,0,0]`; Invocations `06-17=2, 06-18..23=1` — exact |
| C5 | recon rule State=DISABLED, cron(0 */4 * * ? *) | N1 §A-b, N2 §2 | **GREEN** | `describe-rule` State=DISABLED, ScheduleExpression cron(0 */4 * * ? *) — exact |
| C6 | recon 06-20..23 is a TRUE gap (non-silent flanks) not silence | N1, N2 (G-DENOM) | **GREEN** | re-ran Invocations: `06-18=3, 06-19=3, (no dp 20/21/22/23), 06-24=2` — true gap, G-DENOM valid |
| C7 | succeeded-gate code: per-wf `:319`, fleet `:330-339`, comment `:312-318` | N1 §A-a | **GREEN** | read workflow_handler.py — verbatim match incl. "silent-green dead-man" comment |
| C8 | BridgeFleet emit dimensions are `{workflow_id}` only; no `environment` | N1 S5/AL-4 | **GREEN** | read `:250-262, :330-337` — only `{workflow_id}`; `environment` absent from emit |
| C9 | list-metrics shows ONLY `{environment:staging, workflow_id:insights-export}` + undimensioned LST | N1 §B-2 AL-4 | **GREEN** | re-ran `list-metrics Autom8y/AsanaBridgeFleet` — exactly those 2 series, no production dim |
| C10 | 4 skip sites in gid_push.py (`:496` False, `:504` False, `:512` False, `:514-519` True) | N1 §B-1, N2 §2 | **GREEN** | read gid_push.py 485-519 — all 4 at exact lines, exact return values |
| C11 | `grep emit_metric gid_push.py` = NONE (skip seam metric-silent) | N1 S4, N2 §2 | **GREEN** | re-ran grep — zero hits |
| C12 | StatusPush emits only inside `if all_entries:` (`push_orchestrator.py:183`), no else | N1 S4 | **GREEN** | read orchestrator 179-200 — Success/Failure inside `if all_entries:`, no else branch |
| C13 | `three_way` has no prod src hits in asana | N2 §2 Symptom-3 | **GREEN** | `grep -rn three_way src/` = NONE |
| C14 | FORK-1 named groups MISSING; dead aliases + live groups EXIST | N1 §A-c | **GREEN** | `describe-log-groups`: `*_handler_router_prod` & `lambda-python-asana_handler-prod` MISSING; dead+live EXIST |
| C15 | FORK-1: live ECS non-silent (~18.9M), deprecated=0; legacy 951, deprecated=0; dead groups scanned=0 | N1 §A-c §D | **GREEN** | re-ran Logs Insights: ECS scanned=18,924,408 matched-deprecated=0; legacy=951 dep=0; both dead=0 |
| C16 | insights `succeeded:0` every day; AUTH-TEB-001 earliest 06-10 11:00:43.861 (scanned=18,007 non-silent) | N2 §1 §2 | **GREEN** | re-ran: AUTH-TEB-001 earliest = `2026-06-10 11:00:43.861` scanned=18,007; `succeeded:0` 06-10..06-23 every run |
| C17 | PutMetricData AccessDenied for `-insights-export-lambda-role` (verbatim) | N2 §2 CF-2 | **GREEN** | re-ran: verbatim `...autom8-asana-insights-export-lambda-role... not authorized... cloudwatch:PutMetricData` |
| C18 | recon Lambda LastModified 2026-06-24T09:05:27, rule still DISABLED after | N2 §1 §2 | **GREEN** | `get-function-configuration` LastModified = 2026-06-24T09:05:27; `describe-rule` still DISABLED |

**No RED rows.** I attempted to manufacture RED on C6 (silence-not-gap), C15 (proven-zero from
silence), and C16/C17 (postmortem inventing the failure) — all three refutation attempts failed:
the metrics are non-silent on the flanks, the FORK-1 zero is read off two independently non-silent
live denominators, and the `succeeded:0` + auth-failure stream is emphatically present in the logs.

---

## Brief's six checks — explicit dispositions

**(1) Spot-check the pasted receipts — re-run a probe or two.** Done — I re-ran NINE probes
(C4, C5, C6, C9, C11, C13, C15, C16, C17) plus four file reads. Every value the design/postmortem
pasted reproduced. **GREEN.** Drift note: FORK-1 ECS scan is now 18,924,408 (design pasted
18,888,562) — higher because more records logged since N1 ran; non-silence + zero-deprecated
conclusion is unaffected and *stronger*.

**(2) Is any rung rounded up?** **GREEN — no round-up found.** Push-seam skip metric is correctly
held at gap-`proven` / target-`emitting` (AI-4), never claimed emitting. FORK-1 usage is `proven`,
removal `authored` (N1 §D, N2 AI-8) — not rounded to `live`. AI-2 (insights auth) capped at `proven`
(a `succeeded>0` run), not `live`. No alarm claims `alerting` (all DESIGN/un-armed). StatusPushSuccess/
Failure are correctly `emitting` (I confirmed they are real `emit_metric` calls at orchestrator
:193/:198). G-RUNG holds.

**(3) Is FORK-1 retire justified ONLY on a proven non-silent denominator across ALL prod handler
groups (not just one)?** **GREEN.** Two live groups, each proven non-silent *before* reading the
zero: ECS (18.9M) and legacy monolith (951). The two brief-named groups were correctly identified as
non-existent, and the dead aliases (scanned=0) were correctly excluded as silence-from-death rather
than counted as zero-usage. This is the textbook G-DENOM-correct handling; the retire is not resting
on a single group nor on a dead group's silence.

**(4) Any 'proven-zero' or 'expected-idle' from silence rather than a positive receipt (G-DENOM)?**
**GREEN.** Every zero/gap is flanked by a positive non-silence receipt: recon gap (non-silent
06-18/19/24), FORK-1 deprecated=0 (non-silent 18.9M+951), AUTH-TEB-001/succeeded:0 (recordsScanned
18,007). The "EXPECTED" verdicts (recon-off, empty-push-on-low-traffic) are tied to a positive
mechanism (DISABLED rule; `gid_push.py:514-519` returns True by design), not to absence of data.

**(5) Did the postmortem correctly NOT pin the dark window on dd8e43ab given the governor is
observability-only?** **GREEN — and I independently strengthened it.** dd8e43ab landed 06-19 10:07;
the `succeeded:0` + AUTH-TEB-001 stream is present from **06-10** (my own scan), nine days earlier.
A cause cannot postdate its effect. The exoneration is sound on both the code-surface argument
(warm transport, not the auth/IAM/EventBridge path) and the temporal argument.

**(6) Are PROD-mutating actions correctly flagged operator-gated, not auto-licensed?** **GREEN.**
N2 §5 cleanly partitions: SAFE-AUTONOMOUS = AI-4, AI-5(code), AI-7(authoring); PROD-MUTATING
(operator-gated) = AI-1, AI-2, AI-3, AI-5(deploy), AI-7(arm), AI-8; CROSS-REPO = AI-6. Arming the
paging tier and the FORK-1 410-flip are both held behind explicit user confirm (G). Nothing
prod-mutating is auto-licensed.

---

## FLAGS (amber — non-blocking precision/honesty nits)

- **F1 (under-claim, strengthens N2): the PutMetricData AccessDenied is older than stated.** N2 §1
  timelines the IAM denial at "06-17 11:00:35". My earliest-sort scan finds it at **2026-06-10
  11:00:35.560** — co-temporal with the AUTH-TEB-001 onset, not first appearing 06-17. The IAM hole
  (CF-2) is therefore *more* latent than the postmortem states. This makes the multi-factor /
  latent-condition thesis stronger, not weaker. Recommend N2 correct the CF-2 onset to 06-10.
- **F2 (cite precision): `api/main.py:470`.** N1 §D and AI-8 cite the deprecated mount at
  `api/main.py:470`. At HEAD the `query_router` RouterMount sits in the mount block spanning ~`:468-471`;
  line 470 lands inside that block. The reference is load-bearing-correct (the query router mount),
  but it points at the block, not a single isolated line. Cosmetic.
- **F3 (G-DENOM residual, already disclosed): FORK-1 signal is a `logger.info`, not a metric.** N1 §D
  honestly flags that a caller hitting the route on a log-bypassing path would be invisible, and
  mitigates with the 410-canary. I concur the residual is correctly disclosed and gated; flagging only
  to keep it visible — the proven-zero is "zero per the log line," which is the best available signal.
- **F4 (scope honesty on Symptom-3 cross-repo): AI-6 rung depends on autom8y-data, unverified here.**
  N2 routes the three-way denominator classification to autom8y-data (`query_grain_guard.py:84`,
  `batch_grain_guard.py:174`). I confirmed the *absence* of `three_way` in asana src (C13) but did NOT
  open the autom8y-data repo to confirm those exact lines exist. The asana-side claim is GREEN; the
  data-side file:line is asserted, not critic-verified (correctly labeled CROSS-REPO / `authored`).

---

## Findings corroborated to STRONG by my independent read

1. **recon 06-20..23 gap = DISABLED rule, EXPECTED not defect** (C5+C6+C18) — rule DISABLED,
   true-gap with non-silent flanks, redeploy did not re-enable. STRONG.
2. **insights-export is a real latent INCIDENT (succeeded:0 since >=06-10), not a Lambda crash**
   (C4+C16) — Errors=0/invokes daily, yet every run posts succeeded:0 driven by AUTH-TEB-001. STRONG.
3. **"Dark since 06-18" = the dead-man succeeded-gate doing its job** (C7+C16) — gate landed 06-17
   12:24; first stale day 06-18; failure latent from 06-10. Detection event, not fault. STRONG.
4. **dd8e43ab EXONERATED** (C2+C16) — failing condition predates the commit by 9 days. STRONG.
5. **FORK-1 deprecated endpoint = 0 on two independently non-silent live denominators** (C14+C15) —
   G-DENOM-correct proven-zero; dead-group trap correctly avoided. STRONG.
6. **No prod BridgeFleetHealth dimension exists** (C8+C9) — emit dimensions `{workflow_id}` only.
   STRONG.
7. **Push-seam skip family is metric-silent** (C10+C11+C12) — all four skip reasons log-only,
   StatusPush emits only inside `if all_entries:`. STRONG.

---

## Bottom line

Both artifacts hold up under adversarial re-run. The discipline is genuine: every proven-zero is
flanked by a non-silence receipt, rungs are not rounded up, prod-mutating actions are operator-gated,
and dd8e43ab is exonerated on sound temporal grounds. The four flags are precision/under-claim nits —
F1 in particular makes the postmortem's latent-condition thesis *more* correct. **CONCUR-WITH-FLAGS.
No BLOCKING item.**
