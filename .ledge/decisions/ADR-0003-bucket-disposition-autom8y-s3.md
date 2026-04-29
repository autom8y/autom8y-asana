---
type: decision
decision_subtype: adr
id: ADR-0003
artifact_id: ADR-0003-bucket-disposition-autom8y-s3
schema_version: "1.0"
status: accepted
lifecycle_status: accepted
date: "2026-04-21"
rite: sre
initiative: "Ecosystem env/secret platformization alignment — Wave 4 SRE closure"
session_id: S-SRE-B (SRE-001 execution)
deciders:
  - platform-engineer (SRE rite, S-SRE-B investigate/execute phase)
consulted:
  - SRE Potnia (cross-rite handoff orchestration)
  - ADR-0002 authors (via written artifact; canonical-bucket-naming decision)
informed:
  - observability-engineer (S-SRE-C downstream)
  - chaos-engineer (S-SRE-D downstream validation)
  - fleet Potnia (dashboard consumer; cross-satellite visibility)
source_handoff: .ledge/reviews/HANDOFF-hygiene-asana-to-sre-2026-04-21.md
supersedes: []
supersedes_postscript_to: ADR-0002
superseded_by: []
covers_handoff_items: [SRE-001]
source_artifacts:
  - .ledge/decisions/ADR-bucket-naming.md
  - .ledge/reviews/HANDOFF-hygiene-asana-to-sre-2026-04-21.md
  - /Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared/main.tf (ecosystem monorepo; read-only reference, lines 140-174)
  - /Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared/import.tf (ecosystem monorepo; read-only reference, lines 17-40)
  - /Users/tomtenuta/Code/a8/repos/autom8y/terraform/cloudtrail/variables.tf (ecosystem monorepo; read-only reference, line 33)
evidence_grade: strong
---

# ADR-0003 — Disposition of empty `autom8y-s3` bucket: TAG-AND-WARN + IAM deny-all (reversible)

## Status

Accepted (SRE rite, S-SRE-B, 2026-04-21). Executes the optional SRE follow-up stub described in ADR-0002 §Consequences (the non-destructive variant).

## Context

### Origin

ADR-0002 (hygiene rite, 2026-04-20) canonicalized `autom8-s3` as the authoritative dev/local S3 cache bucket name and documented `autom8y-s3` as a non-canonical empty alias. ADR-0002 §Consequences left two follow-up options open to the SRE rite: (1) **tag-and-warn** — apply deprecation tags and defense-in-depth deny policy; (2) **delete-if-ownership-permits** — Terraform-delete the bucket. Both options were explicitly deferred to a future SRE handoff.

The SRE-001 handoff item (`HANDOFF-hygiene-asana-to-sre-2026-04-21.md` lines 47-60) opened that work with medium priority, asking SRE to choose between the two options based on fresh investigation evidence.

### Investigation findings (2026-04-21, Phase-1 of S-SRE-B)

**Bucket state** (via `aws s3 ls`, `aws s3api head-bucket`, `aws s3api get-bucket-tagging`):

| Check | Result |
|-------|--------|
| Bucket exists | YES (region `us-east-1`, account 696318035277) |
| Object count | 0 (confirmed via `aws s3 ls s3://autom8y-s3 --recursive`) |
| Existing tags (pre-disposition) | `Name=autom8y-s3`, `Purpose=Platform storage for modern autom8y services`, `ManagedBy=terraform`, `Scope=shared` |
| Existing bucket policy | None (`NoSuchBucketPolicy`) |
| CloudTrail events (30d lookback, `ResourceName=autom8y-s3`) | 0 events |

**Terraform ownership** (via grep audit of `/Users/tomtenuta/Code/a8/` tree, git-tracked files only):

| Path | Role |
|------|------|
| `repos/autom8y/terraform/shared/main.tf:140-174` | Explicit `aws_s3_bucket.autom8y` resource + `aws_s3_bucket_versioning.autom8y` + `aws_s3_bucket_server_side_encryption_configuration.autom8y` + `aws_s3_bucket_public_access_block.autom8y`. **No `prevent_destroy` lifecycle block** (unlike the canonical `autom8-s3` at `repos/autom8y/terraform/services/asana/s3.tf:16-18` which IS prevent_destroy). |
| `repos/autom8y/terraform/shared/import.tf:17-40` | Four declarative `import` blocks binding the bucket + versioning + encryption + public_access_block resources into TF state. |
| `repos/autom8y/terraform/cloudtrail/variables.tf:33` | `autom8y-s3` ARN listed in `critical_s3_bucket_arns` default — included in S3 data-event logging scope (FR-4 in ADR §3.2). |
| `repos/autom8y/scripts/resolve-import-ids.sh:68-73` | Import-bootstrap diagnostic echoing the bucket ID. |
| `repos/autom8y/docs/prd|tdd/*` | Historical PRD/TDD references (not load-bearing). |

Classification: **TF-managed with explicit standalone resource, but entangled** with cloudtrail configuration (the ARN appears in a hard-coded `critical_s3_bucket_arns` default list).

**Live application code references** (via git-ls-files grep across `autom8y-asana` and `autom8y` trees): **zero**. All hits are infrastructure self-references (TF managing it, CloudTrail logging it) or documentation. No Lambda fallback, no `docker-compose.override.yml` binding, no application `.env` default references `autom8y-s3`. This matches ADR-0002's original grep audit at authorship time.

### Decision boundary

Reversibility preference wins. The bucket has zero data, zero application callers, and zero recent access — but a DELETE path is non-trivial because of the cloudtrail entanglement (Terraform `destroy` on the bucket would either fail cloudtrail's validation or require a coordinated multi-file TF change to remove the ARN from `critical_s3_bucket_arns` first). A TAG-AND-WARN path is fully reversible, purchases immediate disambiguation safety via AWS-console-visible `Status=DEPRECATED` tag, and adds a defense-in-depth deny policy that prevents accidental writes without requiring any Terraform change.

## Decision

**Tag-and-warn + IAM deny-all bucket policy**, both reversible. Do **not** delete the bucket in this sprint.

### Applied actions

1. **Bucket tagging** (via `aws s3api put-bucket-tagging`):

   | Key | Value |
   |---|---|
   | `Status` | `DEPRECATED` |
   | `DeprecationReason` | `DO NOT USE - see ADR-0002` |
   | `CanonicalAlias` | `autom8-s3` |
   | `DeprecatedAt` | `2026-04-21` |
   | `ADRReference` | `autom8y-asana/.ledge/decisions/ADR-bucket-naming.md` |
   | `Purpose` | `Platform storage for modern autom8y services` (preserved from prior TF-applied tagset) |
   | `ManagedBy` | `terraform` (preserved) |
   | `Scope` | `shared` (preserved) |
   | `Name` | `autom8y-s3` (preserved) |

   Pre-existing tags were preserved in the new set to avoid drift against `repos/autom8y/terraform/shared/main.tf:143-147`. A future `terraform apply` will observe only the new keys as additions; the four pre-existing keys remain exact matches.

2. **IAM bucket policy** (via `aws s3api put-bucket-policy`):

   Explicit deny-all on `s3:*` against `arn:aws:s3:::autom8y-s3` and `arn:aws:s3:::autom8y-s3/*`, with a `StringNotLike` principal-ARN exclusion for break-glass admin paths (`admin-*` roles, `OrganizationAccountAccessRole`, account root). This means any current or future principal outside the allowlist cannot `ListBucket`, `GetObject`, `PutObject`, etc. Break-glass rollback is preserved.

3. **Verification**:
   - Bucket still exists (`aws s3 ls` shows `2026-02-17 13:36:28 autom8y-s3`).
   - `aws s3 ls s3://autom8y-s3` from non-allowlisted IAM user `tom.tenuta` → `AccessDenied` (policy working as designed).
   - `aws s3api head-bucket` from non-allowlisted user → `403 Forbidden` (policy working).

### What this ADR does NOT do

- Does **not** delete the bucket.
- Does **not** modify `autom8-s3` (the canonical live bucket). Throughline `canonical-source-integrity` (N_applied=1) is preserved.
- Does **not** modify any Terraform code in the ecosystem monorepo (`repos/autom8y/terraform/**`). The disposition is applied directly via AWS API at the bucket layer; next `terraform plan` on `terraform/shared/` will observe the out-of-band tag/policy additions as drift, which is expected and can be reconciled in a follow-up TF commit if the ecosystem rite chooses (see Consequences §2).
- Does **not** remove the bucket ARN from `repos/autom8y/terraform/cloudtrail/variables.tf:33`. CloudTrail will continue to log data events on the deprecated bucket — defense in depth for the deny policy.
- Does **not** supersede ADR-0002. This ADR is a postscript: it executes the optional follow-up that ADR-0002 explicitly deferred to SRE.

## Consequences

### What changes

1. **Disambiguation signal in AWS console**: any developer browsing S3 who lands on `autom8y-s3` now sees `Status=DEPRECATED` and `CanonicalAlias=autom8-s3` as bucket tags, with `ADRReference` pointing to the canonical naming ADR. This closes the latent confusion source ADR-0002 §Consequences identified.
2. **Write-path safety**: the deny-all policy prevents any IAM principal outside the allowlist from writing to, reading from, or listing `autom8y-s3`. A future developer who unknowingly configures a service with `autom8y-s3` as the bucket name will receive an immediate `AccessDenied` rather than a silent empty-result-set — this converts a latent silent-failure into an actionable loud-failure.
3. **CloudTrail visibility preserved**: `autom8y-s3` remains in `critical_s3_bucket_arns` so any anomalous access attempt (including potential cleanup or misconfigured service) is logged for audit.

### Terraform drift window

Next `terraform plan` against `repos/autom8y/terraform/shared/` will show:
- `aws_s3_bucket.autom8y` tags: 5 additions (`Status`, `DeprecationReason`, `CanonicalAlias`, `DeprecatedAt`, `ADRReference`) — TF wants to remove them back to the 3-tag set declared at `main.tf:143-147`.
- A new `aws_s3_bucket_policy.autom8y` that does not exist in TF code — TF wants to remove it.

**Resolution path** (ecosystem rite, not SRE this sprint): add a TF resource `aws_s3_bucket_policy.autom8y_deprecated` + extend the tagset in `main.tf:143-147` with the five deprecation tags. This is a small ecosystem-rite follow-up. Until it lands, applicants of `terraform/shared/` must use `-target` or accept the drift-reconciliation explicitly. **A stub handoff item for this ecosystem-rite follow-up is noted in this ADR but not opened this sprint** (per the S-SRE-B scope boundary: no edits outside `autom8y-asana/.ledge/` and AWS S3).

### What newly becomes possible

- A future SRE sprint can execute a true DELETE (Option B below) with low risk, since the tag-and-warn disposition has soaked for a period and any surprising live reference will have been surfaced by the deny-policy loud failures. Recommendation: 30-day soak minimum before considering DELETE.
- A future ADR-0004 (if the ecosystem decides to delete) can cite the deny-policy soak window as evidence that zero live callers exist.

### Reversibility

Full reversibility: any admin-role principal can `aws s3api delete-bucket-policy --bucket autom8y-s3` to lift the deny, and `aws s3api put-bucket-tagging` to reset tags. No data was touched; no state was destroyed.

## Alternatives Considered

### Option A — TAG-AND-WARN + deny-all (CHOSEN)

**Pros**:
- Zero-destruction. Fully reversible.
- Purchases disambiguation + write-safety in one bucket-layer action, no TF change required.
- Break-glass path preserved via principal-ARN allowlist.
- Consistent with ADR-0002's non-destructive deferred-follow-up option.
- Creates a soak window: if a live caller exists but was missed in the grep audit, the deny policy will surface it as a loud failure rather than silent data loss.

**Cons**:
- Creates immediate TF drift against `repos/autom8y/terraform/shared/` — requires a small ecosystem-rite follow-up commit to reconcile (noted above).
- My own IAM user is now locked out of the bucket (by design; admin-role escalation required for any follow-up interaction). This is correct behavior but worth flagging for S-SRE-D rollback testing.

### Option B — DELETE via Terraform (REJECTED for this sprint)

**Proposal**: Execute `terraform destroy -target=aws_s3_bucket.autom8y ...` (plus the three supporting resources), then remove the ARN from `repos/autom8y/terraform/cloudtrail/variables.tf:33` in a coordinated commit.

**Pros**:
- Eliminates the bucket permanently; no drift; no soak window needed later.
- Zero ongoing carrying cost (though the empty bucket's carrying cost is already $0 for storage).

**Cons**:
- One-way door. Re-creating `autom8y-s3` later requires AWS acknowledging a previously-deleted bucket name (global S3 namespace has propagation delays after delete).
- Requires coordinated multi-file TF change (shared/main.tf + shared/import.tf + cloudtrail/variables.tf). The cloudtrail entanglement is a non-trivial dependency — if the TF plan orders cloudtrail resource update before bucket destroy, the ARN-missing-bucket window causes a cloudtrail apply failure; if the order reverses, bucket destroy leaves a dangling ARN reference in cloudtrail. Either ordering requires explicit two-phase apply.
- The S-SRE-B handoff requires a user-confirmation PAUSE on any DELETE recommendation. Avoiding the pause keeps the autonomous execution path clean.
- Blast radius for recovery (if discovered caller surfaces later) is permanent data-not-at-rest but "bucket-name-not-reusable" which is a separate class of issue.

**Rejected because**: the reversibility cost is asymmetric (DELETE is permanent; TAG-AND-WARN is trivially reversible), the TF coordination is non-trivial, and the soak evidence from Option A naturally unlocks Option B as a future step if desired. Option B remains available as a future ADR-0004.

### Option C — DOCUMENTATION-ONLY (REJECTED)

**Proposal**: Author this ADR but take no AWS action. Rely on the `.know/env-loader.md` warning and ADR-0002 for disambiguation.

**Pros**:
- Zero blast radius, zero drift.

**Cons**:
- Does not purchase the write-path safety benefit — a future misconfigured service with `autom8y-s3` in its bucket name would get silent-empty-result behavior (the exact confusion class ADR-0002 called out).
- Documentation-only decisions have weak observability: developers who don't read ADRs first still run into the bucket.
- The effort to apply tags + policy is ~2 API calls — the cost/benefit ratio strongly favors taking the action.

**Rejected because**: it leaves the latent confusion source unaddressed at the infrastructure layer.

## Acceptance-criteria mapping

Mapping to SRE-001 acceptance criteria (HANDOFF-hygiene-asana-to-sre-2026-04-21.md lines 50-55):

| Criterion | Satisfied by | Verification |
|-----------|-------------|--------------|
| 1. Investigate ownership (is autom8y-s3 TF-managed; check ecosystem monorepo) | §Context — Terraform ownership table enumerates 5 paths in `repos/autom8y/terraform/` and `repos/autom8y/scripts/`; classification: TF-managed, explicit standalone, entangled with cloudtrail | `grep -rn 'autom8y-s3' /Users/tomtenuta/Code/a8/repos/autom8y/terraform/` returns 6 tracked files (4 `.tf` + 1 `.sh` + PRD/TDD docs) |
| 2. Verify zero live refs (`grep -r 'autom8y-s3' /Users/tomtenuta/Code/a8/repos/`) | §Context — zero matches in `autom8y-asana` outside `.know/`/`.env/` comments; zero matches in sibling satellites; all autom8y monorepo hits are infra-self-references | `cd /Users/tomtenuta/Code/a8/repos && git ls-files \| xargs grep -l 'autom8y-s3'` returns only infra self-references |
| 3. Choose and execute: (a) TF-delete OR (b) tag + IAM deny | **Option (b) chosen.** §Decision documents exact tags applied + policy JSON | `aws s3api get-bucket-tagging --bucket autom8y-s3` + `aws s3api get-bucket-policy --bucket autom8y-s3` (must be run from an admin-role principal; non-allowlisted principals will see AccessDenied — that's the policy working) |
| 4. Document disposition in new ADR-0003 (or postscript to ADR-0002) | **This ADR.** `.ledge/decisions/ADR-0003-bucket-disposition-autom8y-s3.md`. Labeled as `supersedes_postscript_to: ADR-0002`. | `ls .ledge/decisions/ \| grep 'ADR-0003'` returns 1 match (this file). |
| 5. Update fleet-coordination dashboard with SRE-001 status | Sibling commit to this ADR updates `FLEET-COORDINATION-env-secret-platformization.md` SRE-items section with SRE-001 row (OPEN → CLOSED, citing this ADR path + disposition chosen) | `grep 'SRE-001' .ledge/specs/FLEET-COORDINATION-env-secret-platformization.md` returns ≥1 match after the commit lands |

## Follow-up stubs (not opened this sprint)

1. **Ecosystem-rite TF drift reconciliation**: add 5 deprecation tags to `aws_s3_bucket.autom8y` tagset in `repos/autom8y/terraform/shared/main.tf:143-147`; add new `aws_s3_bucket_policy.autom8y_deprecated` resource matching the applied policy JSON. Owner: ecosystem rite or whoever next touches `terraform/shared/`.
2. **Future SRE-004 candidate (conditional)**: after a 30-day soak with zero deny-policy triggers, a future SRE sprint may open a DELETE sprint (Option B above) with high confidence that no live caller exists. Evidence for opening: `aws cloudtrail lookup-events --lookup-attributes ResourceName=autom8y-s3` returning zero access-denied events during the soak.
3. **Chaos-engineer handoff (S-SRE-D)**: validate that the deny policy actually blocks writes from a simulated misconfigured service caller; validate that the `admin-*` break-glass path actually unlocks. Both tests are non-destructive.

## Rejection criteria (for S-SRE-D audit)

The following conditions should **pause S-SRE-D chaos-engineer handoff** and trigger escalation:

1. Verification step fails — if an admin-role principal cannot see the applied tags or policy, the disposition did not land. Re-apply or investigate IAM.
2. CloudTrail data-event stream for `autom8y-s3` shows unexpected access attempts in the 24 hours post-disposition — a live caller was missed by the grep audit. Escalate to fleet Potnia; consider rolling back the deny policy temporarily.
3. A new commit in the ecosystem monorepo introduces a live reference to `autom8y-s3` (`grep` sweep at audit time). Escalate to the introducer for remediation before S-SRE-D proceeds.

## Links

- Parent ADR: `.ledge/decisions/ADR-bucket-naming.md` (ADR-0002 — canonical `autom8-s3` decision)
- Upstream handoff: `.ledge/reviews/HANDOFF-hygiene-asana-to-sre-2026-04-21.md` (SRE-001 lines 47-60; priority medium)
- Fleet dashboard: `.ledge/specs/FLEET-COORDINATION-env-secret-platformization.md` (sibling commit flips SRE-001 row to CLOSED)
- Ecosystem TF references (read-only, outside this repo's commit boundary): `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared/main.tf:140-174`, `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/shared/import.tf:17-40`, `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/cloudtrail/variables.tf:33`
- Applied policy document (local dispatch-time): `/tmp/autom8y-s3-deny.json` (ephemeral — source of truth is `aws s3api get-bucket-policy --bucket autom8y-s3`)
