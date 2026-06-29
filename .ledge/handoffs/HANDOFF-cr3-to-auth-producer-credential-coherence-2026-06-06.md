---
type: handoff
handoff_type: assessment
status: draft
handoff_status: pending
from_thread: cr3-clean-break-cutover (autom8y-asana receiver + autom8 monolith consumer)
to_thread: auth-producer / credential-plane (autom8y/services/auth + terraform/services/auth; AUTH-TEB / fleet-human-rbac-genesis single-writer arc)
created: 2026-06-06
discipline: Read-only coherence handoff. Secret MATERIAL (values, rotation) is the auth-producer's single-writer domain; this doc asserts topology/consumption only. Secrets by name/sha256-prefix only — NO values.
---

# HANDOFF — CR-3 (resolver-credential CONSUMER) → auth-producer (credential-plane): contextual coherence + cross-thread alignment

> **⚠️ READ §7 FIRST (UPDATED 2026-06-06, post-`:161`):** a live token-exchange probe **INVERTS §2/§3** and **HALTS the CR-3 cutover** — Secret-1 (`261742c7`, what CR-3 consumes) returns **401**, Secret-2 AWSCURRENT (`f7868bf6`) returns **200**. The credential plane re-converged on Secret-2 at `:161`; Secret-1's envelope is now stale. §1–§6 below are the original coherence frame; **§7 is the current truth + the single-writer heal ask.**

> **Purpose:** give the credential-plane owner full coherence on CR-3's current state and align the two threads where they touch the resolver service-account credential. CR-3 *consumes* the `asana-dataframe-resolver` SA credential you produce; the CR-3 security certification (2026-06-06) surfaced findings squarely in your domain. You appear to be mid-flight on exactly this (`fix-auth-credential-topology-single-writer` worktree, #370/#379) — this aligns the two.

## §1. CR-3 current state (the rung — never round up)
- **Cutover = merged-NOT-live.** Consumer #55/#58/#60 merged to `autom8` origin/main `86bf029d`; monolith-prod still runs the May-31 image `:382` → the cutover code is NOT deployed. Receiver is deployed on the §D substrate (`autom8y-asana-service:481`/`asana:28ae50b`, both-arms §D PASS).
- **Go-live sequence** GO-1..GO-11 (shape frame `autom8y-asana/.sos/wip/frames/autom8y-receiver-consumer-cutover.shape.md`): merge gate-PR #61 → required-checks → DW-2 OIDC → **rotate DW-1 key** → deploy → AC-6 canary → soak → Stage-B → **Secret-2 decommission (GO-11, LAST)**.
- Gate-hardening PR `autom8y/autom8#61` open (gates for SPOF/cred-bake/deploy-scope); security verdict = **Request-Changes / MODERATE-RUNNER-CORROBORATED** (gate-remediation v2 in flight).

## §2. The credential linkage (what CR-3 did to your credential)
- **#60 repointed the consumer from Secret-2 → Secret-1.** Secret-1 = `autom8y/asana-dataframe-resolver` (authoritative JSON envelope, HTTP 200, sha256[:12] `261742c7`). Secret-2 = `autom8y/auth/service-api-keys/asana-dataframe-resolver` (your SA-namespace credential, HTTP **401 STALE — AUTH-TEB-001 / migration-028**, sha256[:12] `f7868bf6`). The consumer now resolves SM-first from Secret-1 (fail-secure gate; env override prod-disabled).

## §3. Findings in YOUR domain (from the CR-3 security cert — assess + own)
1. **Secret-2 lifecycle — a coherence CONFLICT to resolve.** CR-3's 2026-06-03 finding: Secret-2 is "consumed by neither monolith nor receiver → **vestigial**" (from CR-3's view: monolith SDK injects only `client_id`; receiver uses Secret-1). The 2026-06-06 security cert (CT-5): Secret-2 shows recent **access → "actively consumed"** (day-granularity LastAccessed; principal unattributed). **Reconciliation:** vestigial *from CR-3 consumption*, but accessed by *something* — plausibly your auth-plane internals or a non-CR-3 consumer. **You own the truth.** This GATES the GO-11 decommission.
2. **TM-IAM-WILDCARD (CRITICAL, your namespace's blast-radius).** The `autom8` monolith task role grants `secretsmanager:GetSecretValue` on `resources=["*"]` — it can read your **entire** `autom8y/auth/service-api-keys/*` SA-namespace, not just the resolver. Your own modules already scope correctly (`scheduled-lambda/iam.tf:65`, `iam-service-role/main.tf:86` → `…/service-api-keys/${name}-*`); the monolith role violates that least-privilege pattern. Amplifies the DW-1 kill-chain to full-store compromise.
3. **TM-RESOLVER-FAILOPEN.** The consumer fail-SAFEs to the legacy SDK path on ANY SM-fetch failure → traffic falls back toward the **stale Secret-2** you're trying to retire. An attacker inducing SM throttling forces a silent posture-downgrade onto your stale credential. (CR-3 will alarm the SM-fail→legacy transition during GO-9 soak.)
4. **Topology assertion (credential-scope 7-step):** Secret-1 resolver path is **conformant** (single protocol=JWT-bearer-exchange × scope=asana-dataframe-resolver × auth-routing-field; SM-envelope) — CT-2. Two LOW hardening notes for your review: CT-4 the DW-2 CI OIDC role is broader than its CI usage; CT-6 the consumer local-dev env-override doesn't cross-check the override `client_secret` against the SM envelope's `client_id` (your canary path does — divergence worth aligning).
5. **DW-1 (adjacent credential hygiene):** a live AWS IAM key (`AKIA…ANQ`) is baked into the monolith image layers — operator-deferred; single-writer rotation. Flagged for awareness; not your SA credential.

## §4. Shared single-writer arc (align, don't duplicate)
Your `fix-auth-credential-topology-single-writer` worktree (#370/#379, AUTH-TEB-001 / migration-028) and CR-3's credential findings are the **same arc** (`single-writer-credential-lifecycle`, custody security+sre+10x-dev). The single (human) writer of the resolver credential material is **you/the auth-plane**; CR-3 only asserts consumption/topology and never writes material.

## §5. Assessment questions (what CR-3 needs from you to close its gates)
- **A-1 (gates GO-11):** Is Secret-2 (`…/service-api-keys/asana-dataframe-resolver`) safe to decommission once CR-3 is live-verified, or is it still consumed by an auth-plane/other path? Who is the access-principal?
- **A-2 (TM-IAM-WILDCARD):** Will the single-writer-topology fix scope the `autom8` monolith task role to least-privilege (the `…/service-api-keys/${name}-*` pattern), or should CR-3 carry that IaC change?
- **A-3:** Does your migration-028 / AUTH-TEB-001 resolution affect Secret-1 (the authoritative envelope CR-3 now depends on)? Any planned rotation that CR-3's GO-sequence must coordinate with?
- **A-4 (DW-2):** Should the autom8-CI OIDC + CodeArtifact role be provisioned through your credential-plane (consistent with the SA-namespace model), or is it releaser/platform-owned?

## §6. Held — auth-producer single-writer domain
Secret-1 rotation · the SA-namespace lifecycle · Secret-2 decommission-truth + execution · migration-028/AUTH-TEB-001 resolution · the credential MATERIAL. CR-3 holds GO-11 (Secret-2 decommission) behind your A-1 confirmation + its own live-verify.

## §7. LIVE-PROBE CORRECTION (2026-06-06, post-`:161` attestation) — §2 is INVERTED; CUTOVER-CREDENTIAL-GATE = HALT
The cutover-credential live token-exchange gate (mandated G-THEATER proof) **inverts §2's Secret-1/Secret-2 framing.** Reproduced **independently** via the §D harness `_acquire_token` (CR-3's actual SSM-pointer→Secret-1 path), status/len/sha-prefix only:
- **Secret-1 `261742c7` (what #60 repointed the consumer TO) → JWT exchange FAILS** (`AUTH-TEB-001`, "invalid/expired/revoked"). **CR-3's consumed credential does NOT mint.**
- **Secret-2 AWSCURRENT `f7868bf6` (§2 called "401 STALE") → 200** — the WORKING credential; the reconciler converges the DB hash to it (`sa_reconciler.py:522`, `repaired:0`). (Secret-2 AWSPREVIOUS `5cba30a6` → 401, inert.)
- **Topology confirmed (contente pattern):** client_id = DB-minted `sa_1a9…` (SSM `…/oauth-client-id`), NOT the yaml id; envelope secret-only; `asana-dataframe-resolver` is a catalogued, matched SA (service-accounts.yaml:360, migration 028).
- **State moved:** the auth-plane `:161` deploy (06-05) re-converged the DB to Secret-2; the prior 06-03 OQ-4 (Secret-1=200) was true-then, stale-now.

**Answers/reframes:** **A-3 = YES** — migration-028/AUTH-TEB-001 directly affects Secret-1: its envelope no longer matches the DB-converged hash → 401. **A-1 REFRAMED** — Secret-2 is the **WORKING** credential, NOT vestigial/decommission-able; **do NOT decommission Secret-2.**

**Single-writer heal needed BEFORE the cutover-flip (auth-producer owns the material):** (1, preferred) re-mint Secret-1's envelope (`autom8y/asana-dataframe-resolver`) to carry the live-mintable `client_secret` (= Secret-2 AWSCURRENT material) so CR-3 stays on Secret-1 as wired; OR (2) repoint the consumer + the SSM secret-pointer back to Secret-2; OR (3) rotate the SA and write the new material coherently into BOTH the DB hash and Secret-1's envelope. Then **re-run the cutover-credential gate → GO only on a live 200 on CR-3's path.**

*CR-3 → auth-producer coherence handoff, 2026-06-06 (§7 live-probe correction appended same day). Read-only; topology/consumption + live status asserted, no material handled. Deliver to the auth-producer thread. Reply via A-1..A-4 (A-3 answered, A-1 reframed by §7).*
