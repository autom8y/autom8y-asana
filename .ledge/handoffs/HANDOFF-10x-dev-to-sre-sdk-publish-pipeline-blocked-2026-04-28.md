---
schema_version: "1.0"
type: handoff
status: superseded
superseded_by: HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md
resolution_date: 2026-04-28
resolution_summary: "autom8y-config 2.0.1 (run 25052186961) + 2.0.2 (run 25062121802) both successfully published to CodeArtifact via emergency `allow_breaking_change=true` workflow_dispatch. Publish job itself fires green; consumer-gate failures on autom8y-data + autom8y-sms remain (pre-existing systemic CI breakage on those satellites, unrelated to autom8y-config). 'Notify Satellite Repos' (lockfile-propagator) step still fails on relative-path resolution (`Distribution not found at: file:///tmp/lockfile-propagator-*/autom8y-api-schemas`). Cache-warmer recovery (parent procession) is closed; lockfile-propagator tooling bug remains a separate fleet-level SRE concern."
handoff_type: assessment
source_rite: 10x-dev
target_rite: sre
date: 2026-04-28
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
related_repos:
  - /Users/tomtenuta/Code/a8/repos/autom8y
  - autom8y/autom8y-data (CI breakage source)
  - autom8y/autom8y-sms (CI breakage source)
authority: "User-granted: '3' = parallel re-dispatch + new handoff (2026-04-28)"
severity: SEV2 (fleet-wide blast radius; latent, currently masked because no consumer needs newly-published SDK versions urgently — until cache-warmer remediation needs autom8y-config 2.0.1)
posture: greenfield
trigger: "Discovered during principal-engineer triage of cache-warmer init-failure remediation. SDK 2.0.1 (containing critical IPv4 fix at autom8y-config/lambda_extension.py via PR #169 / commit 96efab03) cannot reach production CodeArtifact."
---

# HANDOFF: 10x-dev → SRE — SDK Publish Pipeline Blocked 10+ Days

## Source Findings (verbatim from principal-engineer triage)

**Critical path discovery**: `sdk-publish-v2.yml` publish job has been SKIPPED on every run for 10+ days. Root cause: `consumer-gate` step fails for two satellite consumers (`autom8y-data`, `autom8y-sms`) due to pre-existing systemic CI breakage on those satellites — failures unrelated to SDK 2.0.1 itself (lint, type-check, OpenAPI spec drift, all 4 test shards red).

The SDK publish workflow gates on consumer-gate as a fleet integrity protection (don't publish a new SDK version that would break consumers). That protection is doing the right thing structurally — the issue is that two consumers have *unrelated* breakage masking as gate failures, blocking publish for the entire fleet.

**Verified evidence**:
- `gh run list --workflow sdk-publish-v2.yml`: publish job state SKIPPED on every recent run
- Run `25049904206`: `consumer-gate` failed for `autom8y-data` and `autom8y-sms`
- `autom8y-data/actions/runs/25049989762`: own CI shows multiple red checks (Lint & Type Check, OpenAPI Spec Drift, Spectral Fleet Validation, all 4 test shards) — pre-existing, not 2.0.1-caused

## Why This Surfaces Now

Cache-warmer Lambda (`autom8-asana-cache-warmer`) is currently 100% erroring on init due to `Errno 97 EAFNOSUPPORT` from `autom8y-config` SDK calling `urlopen("http://localhost:2773/...")` (Python 3.12 prefers IPv6; Lambda microvm rejects AF_INET6). User merged the fix as PR #169 (commit `96efab03`) using literal `127.0.0.1`, but the fix is bottled in the SDK source tree because `sdk-publish-v2.yml` cannot publish 2.0.1 to CodeArtifact.

The cache-warmer Dockerfile uses `--no-sources` which forces CodeArtifact resolution. Until 2.0.1 publishes, every cache-warmer rebuild ships SDK 2.0.0 (with the broken `localhost` literal).

## Scope (assessment, not implementation)

This handoff is type `assessment` — SRE rite owns the diagnosis + remediation decision, then can choose whether to fix-forward in-place or hand back to 10x-dev for execution.

### Assessment Questions

**SQ-1: Are the autom8y-data and autom8y-sms CI breakages safe to bypass for one publish?**
- Decision: file emergency `allow_breaking_change=true` workflow_dispatch on `sdk-publish-v2.yml` to push 2.0.1 to CodeArtifact NOW (un-gated, audit-trail captured)
- Risk: if 2.0.1 truly does break a consumer, this proliferates the breakage
- Counter-evidence: 2.0.1 vs 2.0.0 diff is the IPv4 literal fix at one line in `lambda_extension.py`; extremely low risk of consumer regression

**SQ-2: What broke autom8y-data and autom8y-sms CI?**
- Inspect `autom8y-data` and `autom8y-sms` recent commit history; identify the regression author + scope
- Are these satellites in active development? Have they been ignored? Is it a shared-CI infra change?
- Whose responsibility (autom8y-data team vs satellite-CI-template ownership)?

**SQ-3: Does the consumer-gate design need redesign?**
- Current: ALL consumers must pass for publish to fire. One broken consumer blocks all SDK publish.
- Alternative: gate per-consumer; warn-but-don't-block if non-criticality consumer fails; trust consumer's own CI on their own breakage
- Trade-off: shifts integrity guarantees from SDK→fleet to fleet→consumer
- Decision: ADR candidate

**SQ-4: Is this incident fleet-isolated or are there hidden dependencies?**
- Are there other satellites depending on a newly-published SDK version that just haven't surfaced their bottling yet?
- `gh api repos/autom8y/autom8y-data/contents/pyproject.toml` per consumer to inventory pinned vs latest

### Reference Implementation (canonical patterns)

- `sdk-publish-v2.yml` lines 765-790 (publish job + gate logic)
- `consumer-gate` workflow file (subordinate)
- `autom8y-data` and `autom8y-sms` `.github/workflows/ci.yml` for per-satellite CI configuration

## Authority Boundary

SRE may:
- File emergency `workflow_dispatch` on `sdk-publish-v2.yml` with `allow_breaking_change=true` (audit-trail required)
- Open hotfix PRs in `autom8y-data` and/or `autom8y-sms` to unbreak their CI (may dispatch back to 10x-dev for execution)
- Reauthor consumer-gate logic if SQ-3 lands on redesign
- Open ADRs for any architectural decisions

SRE may NOT:
- Bypass branch protection on autom8y/main
- Touch the autom8y-config SDK source itself (PR #169 / commit 96efab03 is the canonical fix; unchanged)
- Force-push tags
- Alter the cache-warmer Lambda directly via AWS API

## Through-Line Impact on Cache-Freshness Procession

The cache-freshness procession's terminal Track-B cascade is **structurally landed** but **functionally blocked** until SDK 2.0.1 reaches CodeArtifact AND the cache-warmer satellite-receiver chain rebuilds with the fixed SDK.

T0 anchor `2026-04-28T08:35:32Z` is invalidated for functional observation. Observation window restarts after this incident closes + a fresh deploy lands.

D8 deadline (2026-05-27): 29 days runway — comfortable. No urgency on availability (greenfield posture). Take the time for a clean fix.

## Reference Paths

- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-sre-to-10x-dev-cache-warmer-init-failure-2026-04-28.md` (parent handoff; now superseded by this one)
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/SPIKE-staging-vs-canary-prod-gap-2026-04-28.md` (related procession context)
- `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-config/` (SDK source — not to be modified by SRE)
- `/Users/tomtenuta/Code/a8/repos/autom8y/.github/workflows/sdk-publish-v2.yml` (publish workflow)
- autom8y commit `96efab03` (PR #169 — IPv4 fix; merged 2026-04-28T11:21Z; bottled in source until publish unblocks)

## Verification Attestation (post-execution; populated by SRE)

To be filled by SRE rite with:
- Decision on SQ-1 through SQ-4
- Audit trail of any emergency publish
- PR URLs / commit SHAs for any fix-forward work
- Final state of consumer-gate (redesigned or preserved)
- Telos verdict: SDK pipeline restored to healthy; cache-warmer Lambda recovery path unblocked; cache-freshness procession ready to resume terminal cascade
