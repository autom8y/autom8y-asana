---
type: review
status: accepted
initiative: asana-realization-tail-convergence
workstream: C — Credential-Topology Closure
sprint: C1
reviewed_at: 2026-07-07
reviewed_by: security rite (threat-modeler → compliance-architect → security-reviewer)
self_assessment_cap: MODERATE
discharges_predicate_leg: "(d) CREDENTIAL-RECEIPTS"
token_discipline: "NO credential value appears in this artifact — all references redacted. This is defensive hygiene on the operator's own org."
---

# RECEIPT — Credential-Topology Closure (C1): predicate leg (d) DISCHARGED-VIA-RECEIPTS

Leg (d) requires: the leaked-PAT line carries a rotation/escalation receipt **with owner**;
`autom8y/autom8y#927` closed-or-escalated; the Future-4 credential-SSOT sequencer escalated.
**All three are satisfied with named owners below.** This discharges the RECEIPT leg — it does
**NOT** close the underlying exposure: the leaked token **stays live until the operator rotates
it** (a SOVEREIGN action this rite cannot perform). Both truths are stated, neither rounded up.

## The kill chain (why these three compound)

Leaked PAT is the **weapon** (read history → authenticate to Asana as the bot principal, no
further auth); **#927** blinds **detection** (chronic-red metrics-export SEAL → anomalous Asana
usage less likely to surface); **Future-4** slows **containment** (no retirement sequencer → the
fleet is structurally reluctant to kill the credential — it literally "stays live until E").

## Receipts

### R-C1-T21 — Leaked ASANA_PAT in shared history · **Critical** · OWNER: **operator (SOVEREIGN)**
- STRIDE: Information Disclosure → Spoofing/EoP. CWE-798 / CWE-540 / CWE-312. Bug Bar Critical.
- Exposure: a live native Asana PAT is present in the diffs of main-history commits
  `a578ca85`, `525431de`, `15cffee1` (`.claude/settings.local.json`); **absent + gitignored at
  HEAD** (`.gitignore:79`) — the exposure is HISTORY + any clone/fork/secret-scan, not the
  current payload (redacted per `RECEIPT-station-b-asana.md:46`).
- **Directive (rotation, owner = operator):** ROTATE-FIRST (revoke → mint → store), which
  invalidates every copy in history immediately; history-scrub is SECONDARY (see runbook).
  Store: AWS Secrets Manager `autom8y/asana/asana-pat` (ARN suffix `…asana-pat-qJ5AVX`) —
  **rotation is currently DISABLED** on this secret (recurrence risk; enable post-rotation).
- Evidence-of-done (what proves it): the leaked PAT authenticates to Asana **no longer**
  (revoked), the SM secret carries a new version, consumers read the new version, `.gitleaks`
  history scan finds no LIVE credential. **STATUS: OPERATOR-PENDING (token LIVE).**

### R-C1-927 — S2S self-mint 401 / metrics-export SEAL RED · **Moderate** · OWNER: **sre/infra**
- `SERVICE_CLIENT_ID=asana` (bare name, not a valid `sa_`-prefixed ServiceAccount) → S2S
  self-mint 401 `AUTH-TEB-001` → metrics-export SEAL RED on every Satellite Receiver run.
  Route-functionality intact (task RUNS); regression isolated to the observability-EXPORT path.
- **Verified live this session — do NOT close:** the SEAL is STILL firing RED; the
  `if:failure()` alert **auto-files a fresh issue per red run** → an OPEN duplicate-storm
  `#927 → #962` (latest `#962`, run `28888584626`, 2026-07-07). Two owed fixes: (a) set a valid
  `sa_`-prefixed ServiceAccount on the ECS env, re-verify SEAL green; (b) dedup the auto-filer.
- **Directive:** ESCALATE to sre/infra (root cause = deploy-env identity config). **STATUS: ESCALATED.**

### R-C1-FUTURE4 — Fleet credential-retirement sequencer absent · **Important [STRUCTURAL]** · OWNER: **strategy/ecosystem (leadership)**
- No SSOT sequencer for credential retirement; trigger FIRED — bypass-holders grew **15→16**
  (migration-033 + uncoordinated fossil-key retirements). Dual risk: lockout DoS (retire a
  still-depended-on key) + bypass-sprawl EoP (long-lived standing bypass credentials). R-C1-T21
  is a concrete instance ("stays live until E" *because* no coordinated retirement path exists).
- **Directive:** cross-rite HANDOFF → strategy/ecosystem (governance decision, NOT a build) —
  see `HANDOFF-security-to-strategy-future4-credential-sequencer-2026-07-07.md`. **STATUS: ROUTED.**

## NEW FINDING — GATE-GAP-1 (recurrence-prevention, BUILDABLE, not sovereign)
The leak was never caught in-band because the defenders' own `.gitleaks.toml` was **blind to the
native Asana PAT shape** (`1/<user_gid>:<hex>`) AND CI gitleaks ran **non-blocking** (`|| true`).
Recommended control (prevents the NEXT leak, mirrors the A2 register-drift guard's "make it
unrepeatable" pattern): add the native-Asana-PAT rule to `.gitleaks.toml` + make the CI gitleaks
step **blocking**. This is authorable in-repo (NOT sovereign) — offered as a Track-C hardening.

## Sovereign runbook (operator-only — this rite hands it over, never executes; token never printed)
0. IDENTIFY (no-print): the leaked PAT is the T21 native Asana PAT in `.claude/settings.local.json`
   across `a578ca85`/`525431de`/`15cffee1`. Identify the owning Asana user via the Developer
   Console — do NOT reconstruct the token.
1. ROTATE (invalidate FIRST): Asana Developer Console → the owning user → Personal Access Tokens →
   REVOKE the leaked PAT (every history copy is now inert) → MINT a fresh PAT.
2. STORE: put the new PAT as a new version in AWS SM `autom8y/asana/asana-pat`; use file-based,
   `0600`, shred-after handling — never echo/paste/log the value.
3. UPDATE CONSUMERS: point the asana service(s) at the new secret version; redeploy.
4. VERIFY: the old token 401s against Asana; the service reads the new one; a `.gitleaks` history
   scan finds no LIVE credential.
5. HISTORY-SCRUB (SECONDARY, post-rotation, operator decision): rewriting shared history
   (`525431de`, `15cffee1`) is HIGH blast-radius — coordinate with the fleet; do NOT run blind.
   A dead (rotated) token in history is low-urgency.
6. SHRED: remove the on-disk untracked plaintext `.claude/settings.local.json` (`0600`/shred).
7. (optional) enable rotation on the SM secret (recurrence prevention); `aws login` to bank a
   STRONG live-witness of the rotation at PT-E.

## Owner ledger
- **operator (SOVEREIGN)** → R-C1-T21 rotation + history-scrub decision + local-plaintext shred.
- **sre/infra** → R-C1-927 (the whole `#927…#962` family = one unresolved seal) + auto-filer dedup.
- **strategy/ecosystem** → R-C1-FUTURE4 sequencer owner.
- **eunomia (rite-disjoint, PT-E)** → durable attestation of these receipts + `verified_realized`
  (this rite self-caps MODERATE; it does not self-attest realization).

## Honest residual exposure (NOT rounded up)
Leg (d) is DISCHARGED-VIA-RECEIPTS. The **exposure is OPEN**: the leaked ASANA_PAT is **not yet
rotated → LIVE** (Critical); history-scrub undecided; `#927` unresolved + duplicate-storm; Future-4
unowned; GATE-GAP-1 open. `verified_realized` remains eunomia's at PT-E.
