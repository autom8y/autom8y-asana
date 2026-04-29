---
type: handoff
artifact_id: HANDOFF-fleet-potnia-to-sre-tfdrift-2026-04-21
schema_version: "1.0"
source_rite: fleet-potnia
target_rite: sre (sub-sprint in 10x-dev monorepo CC context)
handoff_type: execution
priority: medium
blocking: false
status: proposed
handoff_status: pending
initiative: "total-fleet-env-convergance"
sprint_source: S0 (Fleet-Potnia Launch)
sprint_target: S1 (ADV-1 Terraform Drift Reconciliation)
emitted_at: "2026-04-21T00:00:00Z"
expires_after: "30d"
parent_session: session-20260421-020948-2cae9b82
parent_sprint: sprint-20260421-total-fleet-env-convergance-sprint-a
shape_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.shape.md
frame_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.md
dashboard_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md
source_artifacts:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-0003-bucket-disposition-autom8y-s3.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-sre-to-hygiene-asana-2026-04-21.md (ADV-1 residual; §Residual advisories)
  - /Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared/main.tf (lines 140-174; VERIFIED 2026-04-21)
covers_residuals: [R2 ADV-1]
anti_pattern_guard: AP-G5
evidence_grade: strong
---

# HANDOFF — Fleet-Potnia → SRE (Terraform Drift Reconciliation — ADV-1)

## 1. Context

ADR-0003 (accepted 2026-04-21 by SRE rite, S-SRE-B sprint) applied `TAG-AND-WARN + IAM deny-all`
disposition to the empty `autom8y-s3` bucket via direct AWS API calls. AWS state now carries 5
deprecation tags + a `aws_s3_bucket_policy.autom8y_deprecated` equivalent deny-all policy
(applied via `aws s3api put-bucket-policy`), but **these changes are NOT reflected in Terraform
source**. A `terraform plan` against `autom8y/terraform/shared/` would report drift.

The SRE HANDOFF-RESPONSE (`HANDOFF-RESPONSE-sre-to-hygiene-asana-2026-04-21.md`, §Residual
advisories ADV-1) flagged this as a low-priority follow-up. The `total-fleet-env-convergance`
initiative routes it as **S1** — a bounded, single-PR sprint in the 10x-dev rite monorepo CC
context (`autom8y` repo) that codifies the drift into authoritative Terraform source.

### Rite note

S1 executes in **10x-dev rite CC context** (the `autom8y` monorepo is a 10x-dev rite worktree
per `autom8y/.claude/CLAUDE.md`). However, the WORK is SRE-scoped (terraform reconciliation of
an SRE-rite AWS disposition). The cross-rite-handoff skill accommodates this: the source rite
dispatching the work is `fleet-potnia`; the execution rite is `sre` logically but the
monorepo's CC rite is `10x-dev`. This is a documented pattern from the predecessor initiative
(SRE-FACILITATE-001 precedent in `HANDOFF-RESPONSE-sre-to-hygiene-asana-2026-04-21.md`).

### Verified line range (2026-04-21)

File inspection at S0 verifies target range:
- `aws_s3_bucket.autom8y` resource: **lines 140-148** (5 lines body, 3-line tagset at 143-147)
  - Current tags: `Name=autom8y-s3`, `Purpose="Platform storage for modern autom8y services"`, `ManagedBy=terraform`
- `aws_s3_bucket_versioning.autom8y`: lines 150-155
- `aws_s3_bucket_server_side_encryption_configuration.autom8y`: lines 157-165
- `aws_s3_bucket_public_access_block.autom8y`: lines 167-174

**No `aws_s3_bucket_policy.autom8y_deprecated` resource exists in TF source.** AWS has the
policy applied out-of-band. This is the drift to reconcile.

## 2. Dispatch Scope

Single-PR sprint against `autom8y/terraform/shared/main.tf`:

1. **Extend the tagset at lines 143-147** (aws_s3_bucket.autom8y) with 5 new deprecation tags
2. **Add a new resource** `aws_s3_bucket_policy.autom8y_deprecated` with the deny-all policy
   (principal-ARN exclusion for `admin-*` roles + `OrganizationAccountAccessRole` + account root)
3. **Verify AP-G5 bounded delta** via `terraform plan --target=aws_s3_bucket.autom8y` plus
   `--target=aws_s3_bucket_policy.autom8y_deprecated`
4. **File PR** to autom8y monorepo with the plan output pasted in body as evidence

## 3. Acceptance Contract (PT-01 Soft Gate)

### Tag additions (5 new keys, 3 preserved)

Final tagset on `aws_s3_bucket.autom8y`:

```hcl
tags = {
  # Pre-existing (preserve exactly):
  Name      = "autom8y-s3"
  Purpose   = "Platform storage for modern autom8y services"
  ManagedBy = "terraform"

  # New deprecation tags (ADR-0003 ratified out-of-band; now codifying):
  Status             = "DEPRECATED"
  DeprecationReason  = "DO NOT USE - see ADR-0002"
  CanonicalAlias     = "autom8-s3"
  DeprecatedAt       = "2026-04-21"
  ADRReference       = "autom8y-asana/.ledge/decisions/ADR-bucket-naming.md"
}
```

> Note: ADR-0003 §Decision applied-actions table carries the 5 new tag keys + values. This PR
> codifies those exact values without alteration. Do NOT edit values beyond what ADR-0003
> documents.

### New bucket policy resource

Add `aws_s3_bucket_policy.autom8y_deprecated` after the existing `aws_s3_bucket_public_access_block.autom8y`
resource (insert around line 174). Policy body matches the one applied at ADR-0003 execution
time (verifiable via `aws s3api get-bucket-policy --bucket autom8y-s3` from an admin principal).

Policy must include:
- `Effect: Deny` on `s3:*`
- Resources: `arn:aws:s3:::autom8y-s3` and `arn:aws:s3:::autom8y-s3/*`
- Condition: `StringNotLike` on `aws:PrincipalArn` for allowlist patterns (`*:role/admin-*`,
  `*:role/OrganizationAccountAccessRole`, account root ARN)

The exact JSON source of truth is `aws s3api get-bucket-policy --bucket autom8y-s3` at
execution time. Use it to reconstruct the Terraform resource.

### AP-G5 verification (PT-01 hard aspect)

Before merging PR:

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared
terraform plan \
  --target=aws_s3_bucket.autom8y \
  --target=aws_s3_bucket_policy.autom8y_deprecated
```

**Expected output**: exactly two resources changing:
- `aws_s3_bucket.autom8y` — tag additions (5 keys added; 0 removed; 0 changed beyond additions)
- `aws_s3_bucket_policy.autom8y_deprecated` — new resource creation (matching AWS state; zero diff)

**If plan reveals ANY unrelated drift** (other resources changing, unexpected tag alterations
elsewhere, any reference to resources outside `main.tf:140-174`) → **STOP**. File a separate
`IaC-hygiene-{date}` ECO-BLOCK; route to ecosystem or SRE rite for drift remediation; do NOT
expand S1 scope. **AP-G5 refusal condition is non-bypassable.**

### PR body requirements

- Links to ADR-0002 (bucket naming canonical) and ADR-0003 (TAG-AND-WARN disposition)
- Paste of `terraform plan` output showing bounded delta
- Link to this HANDOFF artifact_id
- Reference to `HANDOFF-RESPONSE-sre-to-hygiene-asana-2026-04-21.md` §Residual advisories ADV-1

## 4. Exit Artifacts

1. PR to autom8y monorepo modifying `terraform/shared/main.tf` (lines 140-148 tagset extension +
   new resource after line 174)
2. `terraform plan --target=...` output captured in PR body as evidence of AP-G5 bounded delta
3. Dashboard §8 Update Log entry: "S1 PR #{N} filed; PT-01 passed; AP-G5 verified bounded delta"
4. HANDOFF-RESPONSE back to fleet-Potnia on PR merge:
   `HANDOFF-RESPONSE-sre-tfdrift-to-fleet-potnia-{DATE}.md` to `autom8y-asana/.ledge/reviews/`

## 5. Entry Conditions

Before executing S1:

1. **CC context**: the `autom8y` monorepo (10x-dev rite). Either use the existing CC session in
   that repo (if available) OR sub-dispatch from fleet-Potnia session via platform-engineer
   specialist (sre pantheon) with absolute-path Read/Edit/Write access to `autom8y/terraform/shared/main.tf`
2. **Branch hygiene**: file the PR on a dedicated branch (e.g., `sre/s1-tfdrift-autom8y-s3-deprecation`)
3. **Critical prior context (from memory)**: **Terraform agent workflow MUST commit to branch.**
   Per AP-BIFROST-001 scar (memory: `project_release_scar_tissue.md` + `feedback_terraform_must_commit_to_branch.md`):
   > Agent `terraform apply` without commit → source-absent orphans (159 AWS resources, 3 workspaces previously orphaned)
   This S1 is NOT an `apply` sprint — it's a source-code authoring sprint. The TF source must
   land in Git BEFORE any future `terraform apply` reconciles the drift. Do NOT run `terraform
   apply` as part of S1. The scope is purely source-code alignment.
4. **AWS policy source-of-truth**: run `aws s3api get-bucket-policy --bucket autom8y-s3` from an
   admin-role principal (non-allowlisted principals get AccessDenied — that's the policy
   working) to retrieve the exact policy JSON. Use it to author the Terraform resource.

## 6. Escalation Triggers

| Trigger | Owner | Action |
|---------|-------|--------|
| `terraform plan --target` reveals unrelated drift | platform-engineer → ecosystem/SRE backlog | **AP-G5 refusal.** File separate IaC-hygiene ECO-BLOCK; do NOT absorb inline; close S1 without merge |
| AWS policy retrieval fails (admin principal unavailable) | platform-engineer → user | ESCALATE; cannot author policy resource without authoritative JSON source |
| Line range drift (if `main.tf` was edited between S0 verification and S1 execution) | platform-engineer | Re-verify range; update PR target lines accordingly; document in PR body |
| PR CI fails on test/lint (unrelated to this sprint's changes) | platform-engineer → 10x-dev Potnia | Soft-escalate; may need cross-rite coordination; do not force-merge |
| Critique-iteration cap (>2 REMEDIATE+DELTA) | platform-engineer → user | ESCALATE; do not attempt 3rd iteration |

## 7. AP-G Guards

### You enforce

**AP-G5** — the defining guard for this sprint. Scope is bounded: 2 resources modified, zero
unrelated drift. Refusal condition is `terraform plan` output showing ANY resource delta
outside the targeted two. On refusal:
- Do NOT merge PR
- File `IaC-hygiene-{date}` ECO-BLOCK with the unrelated-drift details
- Close S1 with status `ESCALATED` in dashboard tracker
- Notify fleet-Potnia via Update Log entry

## 8. Throughline Implications

- S1 does NOT fire as a throughline counting event (pure IaC alignment; no canonical-source
  authorship)
- S1 does not gate any throughline path — S6 (primary) and S12 (fallback) counting events are
  independent of S1
- `N_applied` remains at its **WIP-provisional entering state** (3 if sibling initiative
  `workflows-stack-env-tag-reconciliation` WIP-commits its Node 3; 2 if sibling reverts) at
  S1 exit — UNCHANGED by S1's bounded IaC work. See dashboard §6 Throughline Baseline for
  the full sibling-dependency context and re-verification protocol.

## 9. Response Protocol

On PR merge, emit `HANDOFF-RESPONSE-sre-tfdrift-to-fleet-potnia-{DATE}.md` to
`autom8y-asana/.ledge/reviews/` with:
- PR link + merge commit SHA
- `terraform plan` output (bounded-delta evidence)
- ADR-0003 drift reconciliation confirmed
- Dashboard update request (fleet-Potnia updates §2 S1 status → COMPLETE; §3 R2 ADV-1 status → CLOSED)

## 10. Evidence Ceiling

Per `self-ref-evidence-grade-rule`: platform-engineer work output caps at `[MODERATE]` intra-rite.
External corroboration at dashboard update (fleet-Potnia ratifies S1 COMPLETE) is the cross-check.
PR merge commit + `terraform plan` output are [STRONG] (externally reproducible via git + terraform
CLI).

## Links

- ADR-0003 (SRE-001 TAG-AND-WARN disposition; ratified 2026-04-21): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-0003-bucket-disposition-autom8y-s3.md`
- ADR-0002 (bucket-naming canonical): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-bucket-naming.md`
- SRE HANDOFF-RESPONSE (§ADV-1 residual flag): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-sre-to-hygiene-asana-2026-04-21.md`
- Target file: `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared/main.tf` (lines 140-174)
- Dashboard: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md`
- Shape §2 S1 spec: `/Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.shape.md`
- Frame §3 WS-1 + §5 Risk-4: `/Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.md`
