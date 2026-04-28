---
type: spec
artifact_type: ADR
status: accepted
adr_number: 004
adr_id: ADR-004
title: IaC engine choice for cache_warmer EventBridge schedule
authored_by: 10x-dev.architect
authored_on: 2026-04-27
session_id: session-20260427-205201-668a10f4
parent_initiative: cache-freshness-impl-from-thermia-2026-04-27
schema_version: 1
worktree: .worktrees/cache-freshness-impl/
branch: feat/cache-freshness-impl-2026-04-27
companion_handoff: .ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md
companion_specs:
  - .ledge/specs/cache-freshness-architecture.tdd.md
  - .ledge/specs/cache-freshness-capacity-spec.md
  - .ledge/specs/cache-freshness-observability.md
discharges:
  - thermia HANDOFF §1 work-item-6 (EventBridge schedule explicit in IaC)
  - P3 capacity-spec §1.1 D10 [DEFER — IaC schedule not found in worktree]
  - PRD C-1 (canary-in-prod posture preserved)
---

# ADR-004 — IaC engine choice for cache_warmer EventBridge schedule

## Status

**Accepted** — 2026-04-27. Engineer dispatch can proceed against this
decision; no BLOCKER raised.

## Context

The thermia procession P3 capacity-spec §1.1 ran a worktree-local `find`
probe for IaC files (`.tf`, `.tfvars`, `serverless*.yml`, `template*.yml`,
CDK artifacts) and found zero matches. The probe was deliberately scoped
to the autom8y-asana worktree because that is the single repository the
thermia rite carried into design. The capacity-spec verdict was [DEFER —
IaC schedule not found in worktree]: the cache_warmer Lambda's
EventBridge cron rule is managed in an IaC repository outside the satellite
worktree.

The handoff dossier §1 work-item-6 asks the 10x-dev rite to "declare
EventBridge rule with cron expression in IaC (Terraform/SAM/CDK —
engineer chooses based on existing fleet IaC topology)." Architect's
charter is to make that engine selection explicit so the engineer is not
re-deciding it inside the implementation phase.

The Potnia advisory for this dispatch widened the search scope to the
parent autom8y monorepo plus sibling repos under
`/Users/tomtenuta/Code/a8/repos/`. That probe surfaces the load-bearing
fact the worktree-local probe could not see.

### Fleet IaC topology probe (widened scope)

A widened `find` probe across the parent autom8y repository and the
fourteen sibling repositories under `/Users/tomtenuta/Code/a8/repos/`
yields:

| Repository | IaC artifacts found |
|---|---|
| `autom8y` (platform monorepo) | `terraform/` tree: `services/`, `modules/`, `environments/`, `cloudtrail/`, `shared/`, `workflows/` (HashiCorp Terraform with HCL ≥ 1.11, AWS provider ≥ 6.21.0) |
| `autom8y-val01b` | `terraform/` tree (val01b validation env, mirrors production layout) |
| `autom8y-asana`, `autom8y-data`, `autom8y-workflows`, `autom8y-scheduling`, `autom8y-sms`, `autom8y-hermes`, `autom8y-dev-x`, `autom8y-ads`, `autom8y-api-schemas` (all satellites) | None — satellites carry no IaC of their own |
| Anywhere | No SAM (`samconfig.toml`, `template.yaml`), no CDK (`cdk.json`), no Serverless Framework (`serverless.yml`) |

Verdict: **Terraform is the unambiguous incumbent IaC engine** for the
fleet. There is no second engine in flight; there is no choice to make
between SAM/CDK/Terraform/Serverless. The decision space is whether to
declare the cache_warmer schedule in the existing Terraform tree or to
introduce a foreign engine alongside it.

### The cache_warmer Lambda is ALREADY declared in Terraform

The widened probe also surfaced a load-bearing topology fact the
worktree-local probe could not see: the cache_warmer Lambda already
exists in Terraform, and so does its EventBridge schedule rule. The
production declaration lives at:

`/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/main.tf:232-295`

The shape of the declaration:

```hcl
module "cache_warmer" {
  source = "git::https://github.com/autom8y/a8.git//terraform/modules/stacks/service-lambda-scheduled?ref=v1.0.2"

  name        = "autom8-asana-cache-warmer"
  environment = var.environment
  description = "DataFrame cache warmer with chunked processing (TDD-lambda-cache-warmer)"

  ecr_repository_url = data.aws_ecr_repository.asana.repository_url
  image_tag          = var.image_tag
  handler_command    = ["autom8_asana.lambda_handlers.cache_warmer.handler"]

  schedule_expression = var.cache_warmer_schedule
  ...
}
```

The `service-lambda-scheduled` stack module wraps a primitive
`scheduled-lambda` module that owns an `aws_cloudwatch_event_rule`
resource (anchor: the platform module's `eventbridge.tf` declares
`resource "aws_cloudwatch_event_rule" "schedule"` with
`schedule_expression = var.schedule_expression`). The Lambda permission,
EventBridge target, retry policy, and DLQ are all already wired by the
shared module.

The current default value of `var.cache_warmer_schedule` is declared at
`/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/variables.tf:67-71`:

```hcl
variable "cache_warmer_schedule" {
  description = "EventBridge schedule for cache warmer (cron or rate)"
  type        = string
  default     = "cron(0 2 * * ? *)" # Daily at 2 AM UTC
}
```

Production does not override this default (probe of
`terraform/environments/production/main.tf` shows `asana = {}` with no
schedule field), so the live cache_warmer runs **once daily at 2 AM
UTC**.

### What the design substrate requires

P3 capacity-spec §2.2 declares the ACTIVE-class force-warm cadence target
as **every 4 hours** (line 88, derivation: 0.67 × 6h ACTIVE TTL provides
one full warm cycle of headroom before SLO-1 6h breach). HANDOFF
work-item-6 inherits this: "Cadence: 4h for ACTIVE-class entity warm
cycle (per P3 §2.2 force-warm cadence row). Schedule must satisfy SLO-1
(95% of ACTIVE sections < 6h max age over 7-day rolling window per P4 §2
SLO-1)."

The AC-6 acceptance criterion in HANDOFF §4 codifies this: "Cadence: 4h
for ACTIVE-class entity warm cycle. Cron expression engineer-chosen
(suggestion: `cron(0 */4 * * ? *)` for every 4 hours)."

The structural gap is therefore **NOT** that a cache_warmer schedule is
absent — it isn't, it's been daily-at-2am for some time. The structural
gap is that the existing schedule is a 24-hour cadence and SLO-1
requires 4-hour cadence. The cache_warmer Lambda's design (chunked
processing with checkpoint-resume) was sized for daily; the freshness
SLO requires it to run six times more frequently.

This reframes the work: AC-6 is a **single-line variable change** in an
existing Terraform declaration, not a new IaC declaration of a previously
absent rule.

## Decision

**Use Terraform as the IaC engine for the cache_warmer EventBridge
schedule. Specifically: edit
`/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/variables.tf`
to change the `cache_warmer_schedule` default from
`cron(0 2 * * ? *)` (daily at 2 AM UTC) to `cron(0 */4 * * ? *)`
(every 4 hours starting at 00:00 UTC).**

This is a one-line variable-default change in the existing canonical
Terraform declaration. No new module instantiation, no new EventBridge
resource declaration, no provider plumbing. The shared
`service-lambda-scheduled` module already owns the
`aws_cloudwatch_event_rule` lifecycle.

### Cross-repo work item shape

The Terraform code lives in the **autom8y parent repo**, NOT in the
autom8y-asana satellite repo where this worktree sits. The engineer's
P6 implementation work-item-6 therefore has two physical landings:

1. **autom8y-asana (this worktree)**: receipts only — capture the
   commit SHA from the autom8y change in the post-impl re-handoff
   `HANDOFF-10x-dev-to-thermia-{date}.md`. The CLI/Lambda code
   changes (work-items 1–5, 7–8) land here. No Terraform under this
   tree.

2. **autom8y (parent platform repo)**: the Terraform variable-default
   edit lands here as a separate PR. Engineer creates the PR against
   `main` in the autom8y repo at
   `terraform/services/asana/variables.tf` editing the
   `cache_warmer_schedule` default.

This split is structural — autom8y-asana is the application satellite;
autom8y holds infrastructure. The 10x-dev session must track the
cross-repo PR pair through to deploy.

### Production rollout sequence

The Terraform PR lands AFTER the cache_warmer Lambda code changes
required by other work items (TTL sidecar reads, MemoryTier invalidation
hooks per ADR-003) are deployed and observed-stable in production at the
current daily cadence. The 4h cadence is an amplification of the warmer's
duty cycle — landing it before code stability is verified would compound
risk. P7 thermal-monitor's in-anger probes (Probe-1, Probe-3) are
designed to run BEFORE the cadence increase, while there is still a
`stale = True` substrate against which to test force-warm behavior.

The engineer codifies this sequencing in the post-impl re-handoff §1
"Deferred to Terraform-PR window" subsection.

## Rationale

1. **Single-engine fleet topology removes choice ambiguity**. Terraform
   is in flight at 2 known repositories (autom8y, autom8y-val01b) with
   shared state in S3 (`autom8y-terraform-state` bucket per
   `services/asana/main.tf:38-44`); no other engine is anywhere near
   production. Introducing SAM, CDK, or Serverless alongside an active
   Terraform-managed Lambda would create a split-brain state-of-record
   and an unmanaged-resource hazard.

2. **The existing module is already canonical for this Lambda**. The
   `service-lambda-scheduled` shared stack at version `v1.0.2` is used
   for THREE Lambdas in the asana service alone (`cache_warmer`,
   `unit_reconciliation`, `conversation_audit`, `insights_export` —
   four total). Adding a fifth surface for the same Lambda would bypass
   the shared module's enforced features (DLQ, retry policy, X-Ray,
   secrets-extension wiring, OTEL traces, alarm wiring).

3. **The decision collapses to a one-line variable-default change**.
   The full work-item-6 reduces to: open PR against autom8y repo,
   change `default = "cron(0 2 * * ? *)"` to
   `default = "cron(0 */4 * * ? *)"` at `variables.tf:70`, run
   `terraform plan`, capture plan output, merge, deploy. No
   engineering or design surface.

4. **AC-6 verifiability is preserved**. HANDOFF §4 AC-6 demands "IaC
   declaration is grep-able; the rule name and target Lambda ARN are
   recorded in the re-handoff." Both are already grep-able in the
   existing declaration: rule name is
   `${local.name_prefix}-schedule` from the platform module; target
   Lambda ARN is `module.cache_warmer.function_arn`. The engineer
   captures these in the re-handoff via `terraform state show`
   output.

5. **PRD C-1 canary-in-prod posture is preserved**. There is no
   multi-env logic introduced. The default value applies uniformly;
   production uses the default; there is no per-env override matrix to
   maintain. C-1 is verified by absence of new branching.

## Consequences

### Positive

- The IaC engine question is closed at architectural altitude. The
  engineer does not re-decide it during P6.
- Work-item-6 is a one-line change in a single file in a different
  repository — the smallest-possible surface for the schedule cadence
  change.
- The cache_warmer Lambda's existing observability surface (Lambda
  permission, EventBridge target, DLQ, X-Ray, alarms) is unaffected;
  only its frequency changes.
- AC-6's grep-ability requirement is satisfied by the existing
  module declaration; the re-handoff captures the post-edit
  `terraform state show aws_cloudwatch_event_rule.schedule` output as
  the receipt.

### Negative

- The 10x-dev session crosses a repository boundary
  (autom8y-asana → autom8y). The post-impl re-handoff dossier must
  cite both repositories' commit SHAs to be complete. This is
  procedural, not architectural.
- Terraform PR review and apply cycle in the autom8y repo introduces
  a deploy gate the engineer does not control single-handedly.
  Mitigation: the variable change is mechanical and reviewable in
  seconds; expected review latency is negligible compared to the
  procession's 2026-05-27 verification deadline.
- The 4h cadence raises Lambda invocation cost from 1/day to 6/day —
  a 6× increase. Cost envelope is per P3 §4: at 14 sections × ~30
  seconds per warm cycle × 6 invocations/day, the new monthly cost
  is ≈ $0.30/month (estimate per P3 §4.1 multiplier). Negligible.

### Neutral

- DMS dead-man's-switch threshold at `cache_warmer.py:843-845` is
  24h, which provides 4× headroom over the new 4h cadence. No DMS
  threshold change needed.
- Existing daily-cadence operational observation history is
  invalidated for the new cadence; thermal-monitor P7 establishes a
  new 7-day baseline post-cutover.

## Alternatives considered

### REJECTED: Introduce SAM/CDK/Serverless for this single rule

- **Pro**: SAM has a more compact `Schedule:` shorthand than
  Terraform's `aws_cloudwatch_event_rule`.
- **Con**: Two-engine state-of-record. The Lambda function itself,
  the IAM role, the DLQ, and the EventBridge target are all already
  in Terraform state. Splitting the schedule rule into a different
  engine creates a four-resource Terraform graph with a fifth
  resource (the schedule) outside it, breaking `terraform destroy`
  hygiene and introducing a manual-coordination requirement on
  rule-vs-target ARN binding.
- **Con**: Violates fleet convention. Every other scheduled Lambda
  in the autom8y fleet (per
  `terraform/services/asana/main.tf:232-735` — four Lambdas in this
  one service file alone) uses Terraform via the
  `service-lambda-scheduled` shared stack.

### REJECTED: Declare a NEW EventBridge rule alongside the existing one (additive)

- **Pro**: Avoids touching the existing default value; safer rollback
  surface.
- **Con**: Two rules targeting the same Lambda would invoke the
  warmer twice on aligned cron windows, doubling cost and creating a
  thundering-herd hazard on Asana API rate limits during overlapping
  warms. The Lambda's idempotency-key-window (5-minute, per P3 §5.2)
  provides only weak protection at 4h cadence.
- **Con**: Diverges from the canonical "one rule per Lambda" pattern
  used elsewhere in the file (every other module declares exactly
  one schedule).

### REJECTED: Move the schedule into a per-environment override map

- **Pro**: Foreshadows multi-env support; `production.main.tf` could
  pass `cache_warmer_schedule = "cron(0 */4 * * ? *)"` while leaving
  the default unchanged for hypothetical lower envs.
- **Con**: Violates PRD C-1 explicitly. The PRD declares "canary-in-
  production discipline. Single bucket (`autom8-s3`); no multi-env
  deployment topology" (PRD §6 C-1). Adding multi-env logic to the
  schedule alone introduces an asymmetry between the bucket
  topology (single) and the schedule topology (per-env) that does
  not match any current operational requirement.
- **Con**: Engineer-discretion bait. A future contributor seeing
  per-env schedule override would naturally extend the pattern to
  per-env bucket override, defeating C-1 by accretion.

### REJECTED: Inline the cron expression at the module call-site

- **Pro**: Removes the variable indirection — the cron value would
  appear directly at `main.tf:251` instead of being indirected
  through `var.cache_warmer_schedule`.
- **Con**: Loses the variable's documentation comment ("Daily at 2
  AM UTC" / "every 4 hours") which provides operator context. The
  variable is the right level of abstraction; only its default value
  is wrong.
- **Con**: Diverges from the convention used by sibling modules in
  the same file (`var.unit_reconciliation_schedule` at line 407
  follows the same pattern). Removing the pattern from one module
  while leaving it in three sibling modules is an asymmetry without
  justification.

### REJECTED: BLK-IAC-ENGINE escalation (no IaC engine present)

- This option was held open until the widened probe completed. The
  probe falsified the BLOCKER condition: Terraform is canonical and
  the cache_warmer Lambda is already declared in it. No escalation
  to user is required.

## Anchors

### Existing Terraform declaration (the file the engineer edits)

- `var.cache_warmer_schedule` definition + current default:
  `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/variables.tf:67-71`
- `module "cache_warmer"` invocation passing the schedule:
  `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/main.tf:232-295`
- Schedule wiring at module call-site:
  `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/main.tf:250-251`
  (`# Schedule: Daily at 2 AM UTC (default)` + `schedule_expression = var.cache_warmer_schedule`)

### Shared module surface (do NOT modify; for context only)

- Stack module:
  `git::https://github.com/autom8y/a8.git//terraform/modules/stacks/service-lambda-scheduled?ref=v1.0.2`
- Primitive module EventBridge resources (cached in autom8y .terraform/modules/):
  `terraform/modules/lambda/scheduled-lambda/eventbridge.tf` declares
  `aws_cloudwatch_event_rule.schedule`, `aws_cloudwatch_event_target.lambda`,
  `aws_lambda_permission.eventbridge`

### Design substrate this discharges

- HANDOFF §1 work-item-6:
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:104-108`
- P3 capacity-spec §1.1 IaC probe + DEFER verdict:
  `.ledge/specs/cache-freshness-capacity-spec.md:26-43`
- P3 capacity-spec §2.2 ACTIVE-class 4h cadence derivation:
  `.ledge/specs/cache-freshness-capacity-spec.md:84-90`
- HANDOFF §4 AC-6 acceptance criterion:
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:448-461`

### PRD constraints honored

- PRD §6 C-1 canary-in-prod (no multi-env):
  `.ledge/specs/verify-active-mrr-provenance.prd.md:254-260`

---

*Authored by 10x-dev.architect, session-20260427-205201-668a10f4,
2026-04-27. Worktree
.worktrees/cache-freshness-impl/, branch
feat/cache-freshness-impl-2026-04-27. Discharges HANDOFF §1 work-item-6
IaC-engine-choice question via parent-repo Terraform fleet probe.*
