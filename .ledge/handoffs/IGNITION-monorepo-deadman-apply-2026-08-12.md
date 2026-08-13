---
type: handoff
status: draft
handoff_type: execution
artifact_id: IGNITION-monorepo-deadman-apply-2026-08-12
initiative: option4 stage-1 residue — the ONE authored-not-applied item
source_rite: 10x-dev (this seam)
target_rite: sre (platform-engineer) — monorepo-side session
created_at: "2026-08-12T18:45:00Z"
scope: ONE terraform apply + one runbook correction. Not a wave. Not a sprint.
blocks: "Sitting A (soak-arm) of asana-native-insight-delivery — P-4: 'a soak measured against alarms that lie is not a soak'"
---

# IGNITION — monorepo success-deadman apply (the orphan)

**Why this kit exists:** it is the ONLY piece of authorized, authored, verified
work in the whole arc with **no carry vehicle**. Operator authorization P-7(c) is
already given. The change is written and sitting **uncommitted** in a tree that is
**on the wrong branch**. It gates the soak. Everything else has a kit or a clock;
this has neither.

## What is sitting there right now (verified 2026-08-12T18:38Z)

```
 M terraform/services/account-status-recon/success_deadman.tf   (+111/-15 region)
 M docs/reliability/runbooks/RUNBOOK-account-status-recon-freshness.md  (+39)
```
in `/Users/tomtenuta/Code/a8/a8/repos/autom8y`, whose working tree is on
**`fix/wss-wildcard-scope-bypass-closure`** — **NOT an ancestor of origin/main**.

## The change, and the one thing that must not be misunderstood

`MAX([m_pass, m_warn])` → **`FILL(MAX([m_pass, m_warn]), 0)`** on the
`autom8y-account-status-recon-success-deadman` metric-math expression, plus
latency-truth corrections to the runbook.

★ **The 12h ↔ 18h relationship is CONDITIONAL, and the authored comments already
say so — read them before touching any number.** The deadman's real detection
latency is **~18h (3 empty windows)** *without* the FILL, because CloudWatch's
missing-data evaluation range reaches back past the evaluation periods; **with**
the FILL it becomes the documented **12h (2 × 6h)**. So: apply the FILL and 12h
becomes TRUE; remove the FILL and 12h is a lie. The authored file carries the
verbatim guard — *"Do not remove the FILL and do not quote 12h if it is removed."*
**Do NOT mechanically rewrite 12h → 18h anywhere.**

★ **Only the SUCCESS deadman's claim was wrong.** `completion-event-darkness` and
`source-coverage-3of3` fire on real zeros at the close of the SECOND window —
their ≥12h claims are **TRUE and were left alone**. Do not "fix" them.

★ **W-2's original P9-FIX-4 was WITHDRAWN** — shortening the period would let a
healthy window come up empty against the 4h cadence and fire on a working system.
The fix is at the **expression**, not the period. Do not resurrect the period fix.

★ **Two-sided proof already done, read-only, before authoring**: on a total
blackout range `MAX([...])` returns NO DATAPOINTS while `FILL(MAX([...]), 0)`
returns `0.0` and holds the alarm dark. No new false-positive class — the
predicate is unchanged.

## Execute

1. **Preserve the work first.** It is uncommitted on a non-main branch. Move it
   onto a branch cut from `origin/main` (`git -C <abs> fetch origin` first) —
   stash/apply, or cherry-pick after committing locally. **Do not lose it and do
   not PR from `fix/wss-wildcard-scope-bypass-closure`.**
2. **`terraform init` is the FIRST state-touching act** in
   `terraform/services/account-status-recon/` — that backend is uninitialized,
   which is exactly why no plan exists yet and why this never shipped with the
   asana-side applies. **No `-backend-config` flags needed**: `backend.tf:6-13`
   fully specifies bucket `autom8y-terraform-state`, key
   `services/account-status-recon/production/terraform.tfstate`, region
   `us-east-1`, lock table `autom8y-terraform-locks`.
3. **Plan → show the operator → apply.** The live-alarm scar and P-7's own
   condition both require plan-before-apply. Target the alarm resource; do not
   run a bare apply.
   ⚠ **VAR TRAP, verified 2026-08-12** — the same class as the asana-side
   `-var` trap. `variables.tf` has exactly TWO variables with no default:
   `environment` and `meta_account_id`. `environments/production.tfvars`
   supplies **only `meta_account_id`** — `environment` is NOT in it. A bare
   `-var-file` run will prompt or fail. Pass it explicitly:
   ```bash
   terraform init
   terraform plan  -var-file=environments/production.tfvars -var 'environment=production' \
     -target='aws_cloudwatch_metric_alarm.reconciliation_success_deadman'
   # → SHOW THE OPERATOR. Expect: 1 to change, 0 to add, 0 to destroy.
   terraform apply -var-file=environments/production.tfvars -var 'environment=production' \
     -target='aws_cloudwatch_metric_alarm.reconciliation_success_deadman'
   ```
   ⚠ **TARGET PRECISION** — `success_deadman.tf` declares TWO alarm resources:
   `reconciliation_success_deadman` (`:131`, the live detector — the ONLY one the
   edit touches) and `reconciliation_success_deadman_proof` (`:272`). Target the
   first. Do not sweep both.
4. **Verify live** after apply: `aws cloudwatch describe-alarms --alarm-names
   autom8y-account-status-recon-success-deadman` — confirm the expression carries
   the FILL and that `StateValue` is coherent with the current 4-hourly cadence.
5. **PR + merge** using the monorepo's **merge-commit** convention (verified:
   #1516 `d60a6c5b`, #1539 `c21cab9d` both two-parent — the asana repo's squash
   convention does NOT apply here).
6. **Receipt** into `.sos/wip/STAGE1-observability-truth-2026-08-12.md` — that
   artifact's APPLY RECEIPT section currently records the asana-side apply and
   explicitly lists this one as outstanding.

## Fences

- `git -C <abs-path>` everywhere; PIN `origin/main` for every read.
- UTC only via `date -u`.
- Read `.sos/wip/DETERMINATION-w2-deadmen-al5-2026-08-12.md` for the full
  forensics — ⚠ it contains two stale premises its own later sections supersede
  (`#339 has NOT merged`; `re-baseline ≥7 days`). Read to the END.
- This is monorepo-only. Do NOT touch the asana repo, the K-lane, or any
  offers-gate code. Do not enter either live window's blast radius — this alarm
  is ASR-side and is not a producer deploy, so the windows do not bind it.
- P-7(c) authorization is ALREADY GIVEN; the operator gate here is the PLAN
  REVIEW, not a fresh authorization.

## Reference

@.sos/wip/STAGE1-observability-truth-2026-08-12.md — what shipped vs what did not
@.sos/wip/DETERMINATION-w2-deadmen-al5-2026-08-12.md — the ~18h derivation + both historical firings
@.ledge/decisions/RULING-operator-option4-interview-2026-08-12.md — P-7(c), P-4
