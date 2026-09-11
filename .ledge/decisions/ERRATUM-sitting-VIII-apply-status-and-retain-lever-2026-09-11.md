# ERRATUM — Sitting VIII: #2165 apply status and the HealthCom retain lever

**Date:** 2026-09-11 (morning) · **Seat:** calendar-integration-locus · **Corrects:** `RATIFICATION-decision-space-sitting-VIII-2026-09-10.md` §6 (PR #2165 row) and §7 (RATIF-VIII-A4-EDGE row)
**Trigger:** cross-session correction from name-the-wave (autom8y-asana-59) on 2026-09-11, verified own-hands at the live plane before anything below was written. Nothing here is on relay.

## E-1 — #2165 was APPLIED, unattended, by #2169's auto-deploy

**Record said (§6):** merge is plan-only; one apply is the operator's word.

**Fact:** the alarm swap is live. `ebi-booking-liveness-dark` has `AlarmConfigurationUpdatedTimestamp 2026-09-10T20:15:50Z`; `ebi-sparse-tail-liveness-dark` is absent from a 26-row `ebi-` alarm listing. The applying run was `service-deploy-dispatch` for autom8y `3aa5c940` (#2169, a `services/email-booking-intake/**` merge; run started 20:08:43Z). That workflow triggers on `paths: ['services/**']` and `service-deploy-lambda.yml` runs an untargeted `terraform apply` over the whole EBI stack, so the terraform-only #2165 merge (19:42Z, `terraform/services/email-booking-intake/**`, not matched by the trigger) rode the next `services/**` merge into production.

**Consequence:** "apply is the operator's word" holds only for the interval until the next `services/email-booking-intake/**` merge by anyone. Carrier #2 (docs→auto-apply) of the ten-carrier map executed a governance change with no word. Benign here: the change was ruled (R-126 / R-134) and green. The operator word "apply #2165" is MOOT.

## E-2 — The HealthCom body-retain lever never reached traffic

**Record said (§7, RATIF-VIII-A4-EDGE):** the HealthCom body-retain lever (#2169, name-the-wave) answers the disposition before anyone writes a refusal.

**Fact (own-hands, 2026-09-11 morning, `autom8-email-booking-intake`):**

| object | LastModified | env vars | `EMAIL_BOOKING_INTAKE_PARK_BODY_RETAIN_SENDERS` |
|---|---|---|---|
| alias `live` → version **66** (no routing config) | 2026-09-10T20:15:51Z | 45 | absent |
| `$LATEST` | 2026-09-10T20:17:05Z | 46 | `healthcom.io` |

The peer's `update-function-configuration` landed on `$LATEST` 74 seconds AFTER version 66 was published from it by the same #2169 apply (`publish = true`, `main.tf:242`; TF-owned alias). Traffic serves 66. The lever's code is in the image; its config was never on the invoked version. Per name-the-wave (not re-verified here): two HealthCom parks arrived afterwards (20:31:11Z, 20:51:10Z), both on `[66]` streams, both matching `from_domain=healthcom.io`, zero rows retained.

**Consequence:** the A4-EDGE watcher was watching a lever with no effect. The HealthCom disposition is NOT in progress. It waits on a Terraform-declared var (name-the-wave's **#2170**, open: `variables.tf` default `""` = inert, `production.tfvars` opens the window) plus an apply. A `terraform/**`-only merge does not self-apply (E-1); the var goes live either by operator word (`service-deploy-dispatch` has a `workflow_dispatch` with a `service_name` input) or unattended on the next `services/email-booking-intake/**` merge. Until one of those, RATIF-VIII-A4-EDGE is deferred with **no effective watcher**. R-80 ROLL-FORWARD-ONLY holds; the `$LATEST` var will show as a removal on the next plan and is harmless drift, not to be hand-reverted (peer's word).

## E-3 — The seat's own wrong-object instance, named

This seat read `aws lambda get-function-configuration` with no `--qualifier` twice (2026-09-10 evening, 2026-09-11 morning) and reported the var "present" and "survived only because it was set after the apply". No-qualifier attests `$LATEST`. The served object is whatever alias `live` resolves to. Every `[NN]` in a log-stream name is a published version number. Same class as the incumbency lesson (control plane Active while old code serves), repeated in the config plane. **Fence, banked:** a Lambda config attestation names the alias-resolved version (`get-alias` → `get-function-configuration --qualifier <N>`), never the unqualified form.

## What does not change

R-126 / R-134 stand: the deadman swap is live and in OK. #2165's terraform is reconciled. The NULL-flip live receipt (0 refusals of any class, 40 `booking_success` since 19:11:14Z) is unaffected; it was read from logs, not from Lambda config.
