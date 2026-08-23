---
type: decision
artifact_type: RUNBOOK
artifact_id: RUNBOOK-f2-cred-t21-rotation-2026-08-23
title: "RUNBOOK — F-2 cred-t21 ASANA_PAT rotation (STAGED, operator-sovereign; NOT executed)"
status: accepted  # accepted AS A STAGED RUNBOOK; see `executed: false` — the artifact is ratified, the ACT is not fired
execution_status: STAGED-NOT-EXECUTED
initiative: provably-landed
sprint: S-14 custody-tail-build (WS-F)
seat: security-reviewer@security (co-seated, inv-20260823-a35f74103374)
date: 2026-08-23
supersedes: none
extends: ".ledge/reviews/RECEIPT-credential-topology-closure-c1-2026-07-07.md (R-C1-T21 sovereign runbook)"
defer_watch_id: cred-t21-leaked-asana-pat-rotation-2026-07-07
self_assessment_cap: MODERATE
execution_authority: OPERATOR-ONLY (SOVEREIGN)
executed: false
cr5_compliance: "metadata-only. `describe-secret` invoked; `get-secret-value` NEVER invoked. No credential value read, reconstructed, transcribed, or logged. No token appears in this file."
---

# RUNBOOK — F-2 cred-t21 `ASANA_PAT` rotation

> **THIS RUNBOOK WAS NOT EXECUTED.** It is STAGED. Rotation is operator-sovereign
> per `RULING-cc8-item2-owner-2026-08-14.md:20-22` and
> `.know/defer-watch.yaml:393-394`. This seat authored it, verified the live
> topology it depends on, and stopped. Nothing below has been fired.

## §0 What this adds to the 2026-07-07 runbook

The sovereign runbook at `RECEIPT-credential-topology-closure-c1-2026-07-07.md:70-87`
is correct and remains authoritative on **sequence** (rotate-first, scrub-second).
It could not, at authorship time, name the **consumer set** — so step 3 ("UPDATE
CONSUMERS: point the asana service(s) at the new secret version; redeploy") was
under-specified: an operator firing it unattended would not know *which* services,
*whether* a task-definition change is required, or *how* to tell when propagation
finished.

This runbook closes exactly that gap. Every consumer below was enumerated
**own-hands against live AWS at 2026-08-23**, metadata-only.

## §1 Live pre-flight state (own-hands, 2026-08-23, metadata only)

| Fact | Value | Probe |
|---|---|---|
| Secret ARN | `arn:aws:secretsmanager:us-east-1:696318035277:secret:autom8y/asana/asana-pat-qJ5AVX` | `aws secretsmanager describe-secret` |
| ARN suffix vs. ledger | `qJ5AVX` — **MATCHES** `.know/defer-watch.yaml:394`. No drift. | same |
| `RotationEnabled` | **absent (rotation DISABLED)** — confirms the 2026-07-07 finding, still true | same |
| `LastChangedDate` | **2026-04-08T04:04:03-06:00** | same |
| `LastAccessedDate` | 2026-08-22T18:00:00-06:00 (actively read) | same |
| Version stages | `AWSCURRENT` = `3cd5be90-…`; `AWSPREVIOUS` = `c4dfbfc3-…` | same |

**The load-bearing inference — F-2 is genuinely still open.**
`LastChangedDate` is **2026-04-08**, which is *earlier* than the leak filing date
(2026-07-07, `.know/defer-watch.yaml:383`). A rotation would necessarily have
written a new version and moved that date forward. It has not moved. Therefore the
**leaked PAT is still the AWSCURRENT value and is still live**, and it was read as
recently as 2026-08-22. This is a live receipt, not an inference from the ledger's
`status:` field.

**CR-5 note:** the above is metadata only. `get-secret-value` was never invoked by
this seat. The token's value is unknown to this artifact and does not appear in it.

## §2 Consumer topology (own-hands, 2026-08-23) — what step 3 actually means

Four consumer classes (A/B runtime, C human, D CI), with **different propagation
semantics**. Classes A-C were enumerated in the first draft; **Class D was found
only at rite-disjoint critique** — see the UV-P at §6, which returned NOT NULL. The
runtime distinction below is
the reason the old step 3 was not unattended-fireable.

### Class A — ECS (1 service): needs a forced redeploy

| Field | Value |
|---|---|
| Cluster / service | `autom8y-cluster` / `autom8y-asana-service` |
| Task definition at probe time | `autom8y-asana-service:796` |
| Injection | container `autom8y-asana-service`, `secrets[].name = ASANA_PAT`, `valueFrom = …:secret:autom8y/asana/asana-pat-qJ5AVX` |

`valueFrom` carries **no version or stage suffix**. ECS resolves an unversioned
secret ARN to **AWSCURRENT at task start**, and injects it as a process env var for
the task's lifetime.

**Consequences (both matter):**
1. **No task-definition revision is required.** Rotating in place is sufficient;
   revision `:796` already points at the right secret. Do *not* mint a new task def.
2. **Running tasks will NOT pick up the new value on their own.** They hold the old
   string in memory until replaced. A `force-new-deployment` is **required**, and it
   is the step that actually completes the rotation for the API surface.

### Class B — Lambda (8 functions): no redeploy required

All eight carry `ASANA_PAT_ARN` = the same unversioned ARN and resolve it at
runtime via the `autom8y_config` lambda extension (`resolve_secret_from_env`), so
they pick up AWSCURRENT on next resolution after their extension cache expires.

```
autom8-asana-cache-warmer                 autom8-asana-cache-warmer-bulk
autom8-asana-cache-warmer-section         autom8-asana-insights-export
autom8-asana-onboarding-walkthrough       autom8-asana-conversation-audit
autom8-asana-unit-reconciliation          autom8-asana-scheduling-stratum-snapshot
```

**Caution — this is the sharpest edge in the whole rotation.** Between the moment
the old PAT is revoked and the moment each consumer picks up the new one, that
consumer is broken. Lambdas recover on cache expiry without intervention; the ECS
service does not recover until you redeploy it. **Revoke last, not first**, if you
want a zero-gap rotation (see §3 note on ordering).

### Class D — CI (`github-actions-deploy`): pre-revoke check REQUIRED

Added at rite-disjoint critique. This class was **missing** from the first draft of
this runbook, and it is the one most likely to break loudly *after* the operator
believes the rotation finished.

CloudTrail over `2026-08-13 → 2026-08-23` (40-event sample, `ResourceName =
autom8y/asana/asana-pat`) shows a CI principal actively touching this secret:

| Principal | Calls in window | Operation |
|---|---|---|
| `arn:aws:sts::696318035277:assumed-role/github-actions-deploy/GitHubActions` | **26** | `DescribeSecret` (`errorCode: none`) |
| `AWSReservedSSO_AdministratorAccess_…/tomtenuta` | 11 | `GetSecretValue` |
| `AWSReservedSSO_AdministratorAccess_…/tomtenuta` | 3 | `DescribeSecret` |

Two things follow.

1. **A pre-revoke check is required.** In this sample the CI role reads *metadata*
   only — no `GetSecretValue` by `github-actions-deploy` appears. If that holds, CI
   is unaffected by rotation. But the sample is 40 events over ~10 days, **not a
   full audit**, and a deploy path that reads the value on a less frequent trigger
   would not appear. **Before Step 4 (REVOKE), re-run the lookup below** and
   confirm CI is still metadata-only:

   ```bash
   aws cloudtrail lookup-events --region us-east-1 \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=autom8y/asana/asana-pat \
     --max-results 200 \
     --query 'Events[?EventName==`GetSecretValue`].[EventTime,Username]' --output table
   ```
   If `github-actions-deploy` appears in that output, CI **does** consume the value
   and a rotation will break deploys until the next successful run — sequence
   accordingly (and prefer the zero-gap ordering in §3).

2. **The human/admin path is the real value-reader here.** The 11 `GetSecretValue`
   calls are the SSO admin role — the `just fetch-secrets` class (Class C). That is
   the copy Step 7 shreds.

> **CR-5 note:** all of the above is CloudTrail *metadata* — event names, principals,
> timestamps. No secret value was retrieved by this seat at any point.

### Class C — local developer path (no action, but shred)

`justfile:316-318` (`just fetch-secrets`) writes the live PAT to `.env/local` in
plaintext. Any machine that has run it holds a copy of the **leaked** token on disk.
Step 7 covers this.

## §3 The staged sequence (operator fires; nothing here has been run)

> **Ordering note, and a deliberate divergence from the 2026-07-07 runbook.**
> That runbook says ROTATE-FIRST (revoke → mint → store) to invalidate history
> copies immediately. That is the right call when the priority is *stopping
> exposure now* and an outage is acceptable. If instead a zero-gap rotation is
> wanted, run **mint → store → propagate → verify → revoke**, which keeps the
> service up but leaves the leaked token live for the duration of the window.
> **This is an operator choice and this seat does not make it.** Both orderings
> are written below; pick one. The security-preferred default remains
> revoke-first, because a leaked credential in public git history is a live
> exposure and the outage is bounded and recoverable.

### Step 0 — IDENTIFY (no-print)
The leaked PAT is the T21 native Asana PAT committed in `.claude/settings.local.json`
at `525431de` and `15cffee1` (`a578ca85` is file-present / secret-absent — the
exposure is **2 commits, not 3**; see the T21 correction). Identify the owning Asana
user via the Asana Developer Console. **Do not reconstruct or print the token.**

### Step 1 — MINT the replacement
Asana Developer Console → owning user → Personal Access Tokens → **Create** a new
PAT. Keep it only in the clipboard/an ephemeral `0600` file. Never echo it.

### Step 2 — STORE as the new AWSCURRENT
Use a file, never argv (argv is world-readable via `ps`):

```bash
umask 077
NEW_PAT_FILE="$(mktemp)"
# paste the token into $NEW_PAT_FILE with an editor; do NOT echo it
aws secretsmanager put-secret-value \
  --secret-id autom8y/asana/asana-pat \
  --region us-east-1 \
  --secret-string "fileb://$NEW_PAT_FILE"
shred -u "$NEW_PAT_FILE" 2>/dev/null || rm -P "$NEW_PAT_FILE"
```

This moves the old version to `AWSPREVIOUS` and makes the new one `AWSCURRENT`.
**Verify without reading the value:**

```bash
aws secretsmanager describe-secret --secret-id autom8y/asana/asana-pat \
  --region us-east-1 --query '{changed:LastChangedDate,stages:VersionIdsToStages}'
```

`LastChangedDate` must now be today's date (it was `2026-04-08` at staging time).

### Step 3 — PROPAGATE to consumers
```bash
# Class A — ECS. Required; no task-def change.
aws ecs update-service --cluster autom8y-cluster \
  --service autom8y-asana-service --force-new-deployment --region us-east-1

# Wait for the replacement to stabilise before verifying.
aws ecs wait services-stable --cluster autom8y-cluster \
  --services autom8y-asana-service --region us-east-1
```
Class B (Lambda) needs no action. To force it, publish a no-op config update per
function; otherwise allow the extension cache to expire.

### Step 4 — REVOKE the leaked PAT

> **PRE-REVOKE CHECK (Class D, §2) — run this first.** Confirm CI is still
> metadata-only on this secret before revoking; the command is in §2 Class D. If
> `github-actions-deploy` appears under `GetSecretValue`, revoking here breaks
> deploys until the next successful run.

Asana Developer Console → owning user → PATs → **revoke** the OLD token.
Every copy in git history, in every clone and fork, becomes inert at this instant.
**This is the step that actually closes the exposure.** (Under revoke-first
ordering, this step runs before Step 1.)

### Step 5 — VERIFY (evidence-of-done)
All four must hold:
1. The old token **401s** against Asana. *(Requires holding the old value — if you
   do not have it, substitute: the Asana console shows the token revoked.)*
2. `describe-secret` shows `LastChangedDate` = rotation date and a new `AWSCURRENT`.
3. The ECS service is stable on a task started **after** Step 2, and the API serves
   a live Asana-backed read successfully.
4. A gitleaks history scan still finds the **fingerprints** (history is unchanged)
   but the credential they point at is now **dead**. See §4 — this is exactly where
   the "history clean" language does *not* become available.

### Step 6 — HISTORY-SCRUB (SECONDARY, optional, high blast radius)
Rewriting `525431de` / `15cffee1` rewrites shared history for every clone and fork
and is a **fleet-coordinated** act. A dead token in history is low-urgency. Do not
run blind. Operator decision, deliberately not recommended here either way.

### Step 7 — SHRED local plaintext
On every machine that ever ran `just fetch-secrets`:
```bash
shred -u .env/local 2>/dev/null || rm -P .env/local
```
Then re-run `just fetch-secrets` to repopulate with the new value.

### Step 8 — (optional) enable SM rotation
`RotationEnabled` is currently unset. Enabling scheduled rotation is the
recurrence-prevention control; it requires a rotation Lambda that can drive the
Asana PAT lifecycle, which does not exist today. Flagged, not specified.

## §4 The "history clean" language fence — BINDING

**No artifact produced by S-14 asserts that this repository's history is clean, and
none may until F-2 executes.**

Per `RULING-cc8-item2-owner-2026-08-14.md:20-22`, the "history clean" claim is
gated on this rotation **alone**. Per `DISCHARGE-dw-coc-03-locus-a-2026-08-14.md:84-85`,
the enforcing gitleaks gate proves *"no unbaselined finding"* — it **never** proves
*"history clean"*. Five history-only baseline fingerprints are the cred-t21 entries.

Precise statement of what is and is not true, at 2026-08-23:

- **TRUE:** cred-t21 fossils are absent at HEAD; the enforcing gate is green; there
  are no unbaselined findings.
- **TRUE:** the leaked PAT remains live and un-rotated (§1, own-hands).
- **NOT ASSERTED:** that history is clean. It is not. The fingerprints remain and
  the credential they point at is live.

After Step 4 the accurate statement becomes *"the credential exposed in history is
revoked and inert"* — which is **still not** "history clean" (the strings remain
until Step 6). This distinction is not pedantry: it is the exact conflation the
R-CC7-1 carry exists to prevent.

## §5 What the operator fires (one line)

> Steps 1→2→3→4→5 of §3 above, choosing an ordering per the §3 note, then
> optionally 6→7→8. Nothing in S-14's PR needs to merge first; this runbook is
> independent of the RE-2 build.

## §6 UV-Ps

[UV-P: the OLD token 401s against Asana after revocation | METHOD: authenticated probe with the old credential | REASON: verifying it requires holding the leaked credential value, which CR-5 forbids this seat from reading or reconstructing. Step 5.1 is written for the operator, who may hold it; the console-shows-revoked substitution is offered because it does not require the value.]

[UV-P: the eight Lambda consumers actually pick up AWSCURRENT within their extension cache TTL without a redeploy | METHOD: post-rotation invocation + CloudWatch confirmation of a successful Asana call per function | REASON: the propagation semantics are read from the `autom8y_config` lambda-extension contract and the observed `ASANA_PAT_ARN` wiring, NOT from a post-rotation observation — no rotation has occurred. The TTL value itself was not probed.]

**[UV-P — PARTIALLY DISCHARGED, returned NOT NULL]** The original claim was *"no
consumer outside the 1 ECS service + 8 Lambdas reads this secret"*, deferred to a
CloudTrail audit. The rite-disjoint critic ran that probe. It **returned NOT NULL**:
a CI principal (`github-actions-deploy`, 26× `DescribeSecret`) and a human admin
path (11× `GetSecretValue`) are both live consumers that the ECS/Lambda scan could
not see. Both are now enumerated as Classes D and C. The original UV-P's own stated
blind spot — *"a CI job, or a human shell would not appear in it"* — is precisely
what fired, which is the intended behaviour of a UV-P rather than a failure of it.

The residual, restated narrowly:

[UV-P: no consumer outside Classes A-D reads this secret | METHOD: CloudTrail audit over a full billing period (not a 40-event sample), keyed on the secret ARN, in every region | REASON: the Class-D discovery rests on a 40-event `lookup-events` sample spanning 2026-08-13 → 2026-08-23. A consumer that reads on a monthly or release-triggered cadence, or in another region, is still outside this window. The direction of the correction is instructive: the first enumeration UNDER-counted consumer classes by two, so the prior should be that more exist, not that the set is now closed.]

---

**Evidence grade:** live-topology facts in §1-§2 are own-hands metadata probes
[STRUCTURAL/LIVE | MODERATE — single-seat, self-capped per F-C]. The sequence in §3
is a design authored from those facts, unexecuted, and therefore carries no
execution evidence at all — by construction, since executing it is not this seat's
to do.
