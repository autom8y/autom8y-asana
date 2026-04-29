---
type: review
status: final
artifact_subtype: sister-specialist-critique
artifact_id: IC-CRITIQUE-auth-runbooks-2026-04-22
schema_version: "1.0"
source_rite: sre
source_agent: incident-commander
target_rite: sre
target_agent: observability-engineer
critique_class: sister-specialist-in-rite
scope: "Wave 1 oncall runbook stubs (5 files): CW-5, CW-6, CW-7, CW-8, M-2"
lens: "Can on-call actually use this at 3am?"
axes:
  - cognitive-load
  - actionable-commands
  - escape-hatches
  - false-positive-handling
  - decision-gates
  - phantom-links
critique_verdict_scale: CONCUR | REMEDIATE | BLOCK
data_sources:
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-revocation-replay-completed-ms.md  # CW-5 subject
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-pkce-attempts.md  # CW-6 subject
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-device-attempts.md  # CW-7 subject
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-redirect-uri-rejected.md  # CW-8 subject
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/revocation-migration-024-rollback.md  # M-2 subject
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/autom8y_auth_server/  # code structure ground truth
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/migrations/versions/024_create_token_revocations_table.py  # migration anchor exists
evidence_grade: moderate  # self-ref cap — sister-specialist critique in-rite; STRONG only after external-critic
emitted_at: "2026-04-22T12:00Z"
---

# IC Critique — Wave 1 Auth Oncall Runbooks

> **Lens**: sre-Potnia §4 "3am on-call" test. Author (observability-engineer) designed these for the paging oncall with a laptop, a cup of coffee, and no coworker yet awake. This critique asks whether the runbooks honor that constraint OR whether they assume domain fluency the oncall will not have.

---

## 1. Aggregate Verdict

**4 × REMEDIATE (CW-5, CW-6, CW-7, CW-8) + 1 × CONCUR-with-stipulations (M-2)**

The content quality is **high across all 5 runbooks** — observability-engineer produced substantive, well-structured stubs that escape the frequent "placeholder" runbook trap. Triage sequences are numbered and bounded (max-10 discipline held); escalation ladders are concrete; CloudWatch commands are copy-pasteable in most places; ADR cross-references land on files that actually exist.

However, there is **one systematic defect that touches all 4 CW runbooks**: the "Metric emitted by" source-path references are phantom paths. The actual auth-server code layout is flat (`routers/oauth.py`, `services/revocation_service.py`) rather than the namespaced structure the runbooks claim (`oauth/pkce.py`, `oauth/device.py`, `revocation/backend.py`). A 3am oncall attempting to confirm a server regression by `grep`-ing the asserted path will find nothing and waste minutes of triage.

The M-2 rollback runbook is **the strongest artifact of the five** — decision gates are well-bounded, data-destructive ops require explicit IC approval, and the code-revert-before-DB-revert sequencing is correctly emphasized. It earns CONCUR with a single stipulation (see §6).

This is REMEDIATE not BLOCK because: (a) the runbooks are **materially useful** even with the phantom paths — the semantic intent is clear enough that an oncall can reach the right service via other references; (b) the defect pattern is **mechanical** and fixable in a short editorial pass; (c) none of the defects introduce **wrong guidance** (no "run this destructive command without approval" traps).

---

## 2. Per-Runbook Verdict (Quick-Read Table)

| # | File | Lines | Verdict | Primary Concern | Fix Magnitude |
|---|------|-------|---------|-----------------|---------------|
| CW-5 | `auth-revocation-replay-completed-ms.md` | 86 | **REMEDIATE** | Phantom metric-emitter path (`revocation/backend.py` does not exist; actual is `services/revocation_service.py`) + `psql` exec ergonomics | Small — path rewrite + 1 footnote |
| CW-6 | `auth-oauth-pkce-attempts.md` | 83 | **REMEDIATE** | Phantom path (`oauth/pkce.py` does not exist) + no false-positive suppression gate for attack-signal path | Small — path rewrite + 1 §addendum |
| CW-7 | `auth-oauth-device-attempts.md` | 87 | **REMEDIATE** | Phantom path (`oauth/device.py`) + flag `ENFORCE_INTERVAL_BACKOFF` not verified to exist in config | Small — path rewrite + flag verification |
| CW-8 | `auth-oauth-redirect-uri-rejected.md` | 90 | **REMEDIATE** | Phantom path (`oauth/authorize.py`) + "Do NOT do" section excellent but missing explicit comms ladder for security-rite cross-handoff | Small — path rewrite + 1 ladder line |
| M-2  | `revocation-migration-024-rollback.md` | 163 | **CONCUR-with-stipulations** | Pre-requisite checklist strong; §Elapsed-time table optimistic; one `pip install` inside ECS task is brittle | Stipulation — add "verify alembic pre-installed OR script the install" note |

---

## 3. CW-5 (Revocation Replay Completed MS) — REMEDIATE

### Strengths (keep these)
- **Plain-English impact** in §(a) is exactly what a groggy oncall needs ("admin-plane operators cannot revoke tokens… during the replay window"). This is a model for the other runbooks.
- **Signals this IS NOT** block explicitly disambiguates from issuance-path alerts — prevents oncall from chasing the wrong code path. [Cognitive-load: WIN.]
- Triage steps 2 and 3 are properly sequenced (scope → deploy correlation → data volume → query plan). Domain expertise is bounded; oncall follows breadcrumbs.
- Escalation ladder in §(c) is quantitative and paged correctly (SEV-1 on crash-loop is right).

### REMEDIATE issues

**R1. Phantom metric-emitter path** (severity: medium, fix: trivial)
- Runbook claims: `Metric emitted by: autom8y_auth_server/revocation/backend.py cold-start path`.
- Actual code location: there is NO `revocation/` subpackage. Relevant files are `autom8y_auth_server/services/revocation_service.py` and `autom8y_auth_server/models/token_revocation.py`.
- **Oncall cost**: a 3am oncall tracing "what emits this metric" runs `rg "replay_completed_ms" services/auth` and finds nothing at the cited path, losing 2–5 minutes to confusion.
- **Fix**: rewrite "Metric emitted by" to the actual path OR add a note "metric emission lives in the revocation-backend module (currently: `services/revocation_service.py`; path may shift during Wave 2 refactor)."

**R2. Step 3 "exec into an auth task" ergonomics** (severity: low-medium, fix: small)
- Step 3 says "Exec into an auth task (see PRODUCTION-DATABASE.md §Connect to Production Container), then `psql …`".
- The runbook gives the SQL but **does not give the exact exec command**. `PRODUCTION-DATABASE.md` exists (verified), so the delegation is legitimate, but at 3am an oncall benefits from the one-line `aws ecs execute-command` inlined.
- **Fix**: inline the exec command (1 line) OR reference the exact anchor in `PRODUCTION-DATABASE.md` (e.g., `§ Connect to Production Container via ECS Exec`).

**R3. Step 8 Redis failover "if warranted" is a weight-bearing judgment call with no gate**
- Step 8: "Failover if warranted." — this is a production-impacting action with no "consult IC" gate.
- Per IC doctrine: ANY action impacting production dependencies during an active incident requires either a documented precondition (e.g., "if X AND Y, then failover") OR explicit IC approval.
- **Fix**: change to "Failover ONLY if (a) node is UNAVAILABLE per CloudWatch, AND (b) IC has been notified. Redis failover during active replay is safe (Postgres is source of truth), but cross-coordination matters."

### Escape hatches — PRESENT
- §(c) escalation ladder provides the "call IC" path at the right thresholds.
- §(d) short-term mitigation is separated from root-cause fix — good.

### False-positive handling — PARTIAL
- Runbook covers "not a revocation regression" / "not an issuance alert" in §Signals this IS NOT, but does NOT give a "how to suppress if this was spurious" gate. Suggestion: add a short §(e) "If the triage suggests false-positive, document root-cause (e.g., ECS task-restart noise) and file an alert-tuning ticket; do not silence without documentation."

---

## 4. CW-6 (OAuth PKCE Attempts) — REMEDIATE

### Strengths (keep these)
- 3 hypotheses (attack / client regression / server regression) in §(a) are **exactly the mental model** a tired oncall needs. Model runbook for security-adjacent alerts.
- Step 4's failure-reason breakdown is elegant — `failure_reason` dimension routes to 4 different triage paths via step 5–7. This is high-quality triage design.
- Step 8 co-fire check with CW-7/CW-8 is a correct systems-thinking move — breadth of simultaneous OAuth anomalies suggests server regression [II:SRC-001 Cook 1998] [STRONG | 0.79 @ 2026-04-01]. Would not expect this level of cross-runbook discipline in a Wave 1 stub.
- Step 9 canary-pair check (success rate vs failure rate) correctly distinguishes total-flow-up from success-rate-down; this is the insight between "attack" and "legit users blocked".

### REMEDIATE issues

**R1. Phantom metric-emitter path** (same as CW-5 R1)
- Runbook claims: `Metric emitted by: autom8y_auth_server/oauth/pkce.py`.
- Actual: no `oauth/` subpackage exists. PKCE logic would currently live inline in `routers/oauth.py` or `services/token_service.py`. No dedicated `pkce.py` file.
- **Oncall cost**: same as CW-5 R1. Step 5 also says "compare against a known-good test vector (see `tests/test_pkce.py`)" — this file does NOT exist either. Double phantom.
- **Fix**: rewrite both paths. The `tests/test_pkce.py` claim is more concerning because step 5 uses it as a triage tool — if the oncall follows step 5 they hit a dead-end, not just a documentation nit.

**R2. Step 7 attack-path suppression is understated** (severity: low, fix: small)
- Step 7: "notify security-rite; do not mitigate auth-server. Confirm WAF rules allow rate-limiting of `/oauth/token`."
- Correctly says "do not mitigate" — good. But does NOT say "in the incident channel, clearly state 'SECURITY-CLASSIFIED; handing off'; security-rite is IC on this now."
- **Fix**: add: "(a) update incident channel with SECURITY tag; (b) security-rite oncall becomes IC for the response; (c) you remain available as auth-server subject-matter-expert."

**R3. Re false-positive handling**
- PKCE alerts are high-volume-risk — the threshold of 5% failure over 10 min is not high. A consumer-SDK mis-release could produce a spurious-looking spike that IS a real regression.
- Runbook should explicitly **call out**: "Do not suppress this alert without a confirmed benign root-cause. Attack-signal misclassified as suppressible is a security failure."
- **Fix**: add 1-line callout in §(d) "Do NOT suppress/silence without confirmed benign root cause + security-rite sign-off."

### Escape hatches — PRESENT
- §(c) escalation ladder is right. Co-fire path escalates to incident-commander.

### Actionable commands — MOSTLY PASS
- Deploy-correlation one-liner is copy-pasteable. ALB source-IP one-liner is copy-pasteable. Log-insights query for failure_reason breakdown is copy-pasteable.
- Step 6 "Identify offending client via client_id dimension" — **not** copy-pasteable; suggests the oncall should know how to click through CW Metrics UI. Add: "CW Logs Insights: `filter msg = \"pkce.verify.failed\" and failure_reason = \"verifier_length\" | stats count() by client_id | sort count() desc`."

---

## 5. CW-7 (OAuth Device Attempts) — REMEDIATE

### Strengths (keep these)
- Dual-condition alert (failure-rate OR poll-storm) is well-documented and **each condition has its own triage branch** in step 1 ("Which condition fired?"). Good design.
- Device-code TTL + NTP sync triage (step 4) is a specific-enough hypothesis to be actionable.
- Poll-storm mitigation with both server-side (ENFORCE_INTERVAL_BACKOFF flag) and client-side (version-pin) options covers both remediation vectors.
- Cross-flow degradation check in step 8 ("auth-server CPU attributable to device-flow") is correct systems-thinking. A poll-storm from a single client can poison unrelated flows — good detection.

### REMEDIATE issues

**R1. Phantom metric-emitter path** (same pattern as CW-5/CW-6)
- Runbook claims: `Metric emitted by: autom8y_auth_server/oauth/device.py (device-code poll + exchange endpoints)`.
- Actual: no `oauth/device.py`. Would currently be in `routers/oauth.py` once implemented.
- **Fix**: same as CW-5 R1.

**R2. `ENFORCE_INTERVAL_BACKOFF` flag existence not verified** (severity: medium, fix: verify-and-patch)
- §(d) poll-storm mitigation: "Server-side: enable aggressive `slow_down` responses (`autom8y_auth_server/oauth/device.py` `ENFORCE_INTERVAL_BACKOFF=true` flag)".
- If this flag does not yet exist in `app/config.py`, the runbook is prescribing a remediation that will not work. Observability-engineer needs to verify with platform-engineer that this flag exists or will ship with admin-CLI Wave 1.
- **Fix**: add a line "(As of 2026-04-22, this flag is a Wave 1 deliverable; confirm it has shipped before relying on this mitigation. If not shipped, use WAF rate-limit fallback.)"

**R3. Step 5 `authorization_pending` interpretation** (severity: low, fix: small)
- Step 5 says `authorization_pending` being elevated "indicates users are abandoning mid-flow or the `/device` verify page is degraded."
- Misses a third possibility: **elevated device-flow adoption** (admin-CLI rollout increasing volume on baseline-tuned alerts). During admin-CLI Wave 1 rollout this is a predictable source of noise.
- **Fix**: add "Third cause: recent admin-CLI adoption surge; check device-flow volume trend over last 7d. If the denominator has scaled, baseline needs re-tuning."

### Escape hatches — PRESENT
- Poll-storm cross-flow degradation (CPU >70%) escalates to incident-commander. Right gate.
- `/device` verify portal down triggers SEV-1 with correct page list.

### False-positive handling — PARTIAL
- Step 6 acknowledges consent-UX false-positives but offers no suppression path. Same recommendation as CW-5 R3: add §(e) suppression protocol.

---

## 6. CW-8 (OAuth Redirect URI Rejected) — REMEDIATE

### Strengths (keep these)
- §(a) 3 hypotheses ordered by severity (security-event first) is exactly the right framing. Security-adjacent alerts should lead with attack-hypothesis.
- §(d) **"Do NOT do"** subsection is the single strongest pattern in all 5 runbooks. "Do not temporarily loosen the validator to accept near-matches" is the right anti-pattern guard — stops the 3am-oncall-under-pressure from creating a security regression to silence the alarm.
- Step 8 `client_id` enumeration pattern detection is a sophisticated signal. Elevates the runbook beyond "follow the playbook" to "here is what to notice that the runbook didn't anticipate."
- Co-fire check with CW-6 (PKCE `challenge_mismatch`) is an excellent systems-thinking pattern — "coordinated probe" hypothesis [II:SRC-003 Reason 1997] [STRONG | 0.79 @ 2026-04-01].
- ADR-0006 cross-reference is legitimate — file exists.

### REMEDIATE issues

**R1. Phantom metric-emitter path** (same pattern)
- Runbook claims: `Metric emitted by: autom8y_auth_server/oauth/authorize.py validate_redirect_uri()`.
- Actual: `autom8y_auth_server/routers/authorize.py` exists, but not `oauth/authorize.py`. The router file may or may not have a `validate_redirect_uri()` function — needs verification.
- **Fix**: rewrite to `routers/authorize.py`; confirm function name.

**R2. Security-rite cross-handoff lacks comms ladder** (severity: medium, fix: small)
- §(c) and §(d) correctly say "engage security-rite oncall" on attack signal. But do NOT specify:
  - WHERE security-rite oncall is reached (which channel, which page target, which backup)
  - WHAT to post in the incident channel for the cross-rite-handoff to be legible
  - WHO remains IC during the handoff window (auth or security)
- At 3am the oncall doesn't want to invent this; they want a 4-line script.
- **Fix**: add §(e) "Security-rite handoff protocol:
  1. Page: `pagerduty schedule security-oncall`
  2. Post in incident channel: `SECURITY: redirect-uri hijack probe suspected. CW-8 runbook §3 attack path. Security-rite assuming IC; auth-rite on subject-matter-expert standby.`
  3. Preserve logs — do NOT rotate CloudWatch streams.
  4. IC handoff is explicit (document the transfer time)."

**R3. Step 5 "any auth-server deploy in last 1h"**
- Good. But misses: "any client registration change in the last 1h?" — clients table writes can produce the same symptoms if the write was wrong.
- **Fix**: add to step 5: "AND check for recent `clients` table writes: `SELECT * FROM clients WHERE updated_at >= now() - interval '1 hour';`."

### Actionable commands — MOSTLY PASS
- Logs Insights one-liner for rejected URIs is copy-pasteable.
- Revert path is concrete (task-definition rollback).
- WAF rule path is concrete (`autom8y/terraform/services/auth/waf/`).

### Phantom-link verification — CW-8
- ADR-0004, ADR-0006: both verified to exist in `.ledge/decisions/`.
- Related runbooks (CW-6, CW-7): verified to co-exist.
- Cloudwatch dashboard `auth-oauth-issuance`: can't verify from markdown; assumed provisioned by CW-1 Terraform resource.

---

## 7. M-2 (Migration 024 Rollback) — CONCUR-with-stipulations

### Strengths (this runbook is the strongest of the five)

- **Decision-gate discipline is excellent.**
  - §(a) Trigger Interpretation enumerates 4 specific conditions + requires IC approval. Correctly puts this on IC ledger, not oncall-unilateral [II:SRC-002 Dekker 2006] [STRONG | 0.79 @ 2026-04-01].
  - §(b) Triage step 1 confirms IC approval before ANY destructive action. Step 3 mandates snapshot BEFORE drop.
  - Preconditions checklist in §(d) is a 6-item gate — all must be true before execution begins.
  - The "Do NOT run DB downgrade before code revert" callout correctly flags the crash-loop trap.

- **Code-revert-BEFORE-DB-revert sequencing** is the crown jewel. A naive rollback runbook would do DB first (because "rollback the migration" is the natural noun-phrase). Observability-engineer correctly identifies that the intermediate state (code expects table, table gone) is catastrophic and orders the steps to avoid it.

- **Data preservation** via pg_dump + S3 upload is mandatory and scripted. Forward-recovery path (replay-forward) is documented.

- **Elapsed-time estimate** table gives P50 and P90 — this is the level of timing discipline IC wants when estimating outage windows to stakeholders.

- **"Revert of the revert"** section (forward-recovery path) anticipates a common oversight — once you've rolled back, you need a path to re-apply. Nicely done.

- Migration file exists (`024_create_token_revocations_table.py` confirmed); ADR-0004 cross-reference valid; `PRODUCTION-DATABASE.md` reference valid.

### Stipulations (before CONCUR lands)

**S1. §Execution sequence STEP 3 `pip install` inside ECS task is brittle** (severity: low-medium)
- "pip install alembic pydantic-settings sqlmodel psycopg2-binary (if image is lean)".
- At 3am during an incident, installing packages over the network inside an ECS task is: (a) slow, (b) failure-prone (pypi outage, VPC egress restrictions, proxy issues), (c) not auditable.
- **Stipulation**: either (a) verify that the auth Docker image already includes these (most likely — alembic is in pyproject.toml), OR (b) replace `pip install` with "the image SHOULD already contain these; if missing, STOP and escalate — do not pip-install during an incident." The incident-response stance is fail-fast, not workaround.

**S2. §Elapsed-time estimate may be optimistic on P50 code-revert** (severity: low)
- "ECS code revert (update-service + steady-state)": P50 8 min, P90 15 min.
- In my IC experience, ECS `update-service` followed by "steady state" on a 4+ task service with healthCheckGracePeriodSeconds of 60s typically takes 10-20 min on P50. 8 min is aggressive.
- **Stipulation**: bump P50 to 12 min, P90 to 25 min, OR add a note "steady-state time is healthCheckGracePeriod × task-count dependent; verify your service's grace period in TaskDefinition before relying on this estimate."

**S3. §Data preservation snapshot lands in S3 — clarify retention + access** (severity: low)
- pg_dump → `s3://autom8y-incident-artifacts/auth/migration-024-rollback/`.
- Does this bucket exist? Is it Terraform-managed? What's the retention policy (forensic = long; incidental = short)? Who has read access (security-rite? oncall? platform-engineer?)?
- **Stipulation**: either reference the bucket's Terraform definition OR add "Verify `autom8y-incident-artifacts` bucket exists with 1-year forensic retention before executing. If not, STOP and escalate to platform-engineer — the snapshot is mandatory and must land somewhere persistent."

### Escape hatches — STRONG
- Every destructive action has a revert path (code revert, DB revert, data replay-forward).
- IC approval gate is explicit and repeated.
- SEV-1 escalation for mid-sequence rollback failure.

### Phantom-link check — CLEAN
- ADR-0004: exists.
- CW-5 runbook cross-reference: exists.
- `PRODUCTION-DATABASE.md`: exists.
- Migration 024 file: exists.

### Decision-gate bounded timing — PASS
- IC approval required before step 1. Triage decision SLA: 10 min P50, 30 min P90.
- Outage window declared before execution. Updates every 15 min.
- Forward-revoke list exported BEFORE drop (irreversible-action timing gate).

**Verdict**: CONCUR once S1–S3 stipulations are patched (all are editorial fixes < 30 min of author time).

---

## 8. Systematic Findings (Cross-Runbook Patterns)

### F1. Phantom metric-emitter paths (CW-5, CW-6, CW-7, CW-8) — 4/4 affected
- Pattern: runbooks cite `autom8y_auth_server/{subsystem}/{file}.py` as the metric emission source, but the actual auth-server layout is flat (`routers/`, `services/`, `models/`) rather than nested.
- Root cause hypothesis: observability-engineer authored these stubs **against a forward-looking layout** (e.g., the post-refactor structure expected after admin-CLI Wave 1 ships the oauth/ subpackage). If that's the case, the runbooks are **pre-committing to a structure that doesn't yet exist**.
- **IC position**: either (a) runbooks ship with **current** paths and include a note "path may shift in Wave 2", OR (b) runbooks ship with **target** paths and include a note "AS OF 2026-04-22 these paths are NOT YET LANDED; ship when admin-CLI Wave 1 lands the refactor." Currently the runbooks claim the target paths as if they exist, which is the worst of both worlds.
- **Priority**: fix before Wave 1 ship. 4 files × ~1 path rewrite each = < 30 min.

### F2. No §(e) "false-positive suppression" protocol
- None of the 5 runbooks describe: "what if the alert was spurious — how do I document and tune without silencing legitimate signal?"
- This matters because silent-suppression is a known anti-pattern [SR:SRC-010 Google 2018] [STRONG | 0.72 @ 2026-04-01] — oncall under pressure silences an alarm they classify as noise, and the next incident of that class goes undetected.
- **Recommendation**: add a standard §(e) to each runbook: "If triage concludes false-positive: (1) document root-cause in incident channel; (2) file alert-tuning ticket with proposed threshold change; (3) do NOT silence the alert without documentation + owner sign-off; (4) schedule post-incident review for suppression-pattern accumulation."

### F3. Security-rite cross-handoff comms ladder is implicit
- CW-6 (attack-signal path), CW-8 (hijack probe path) correctly say "engage security-rite" but don't script the actual comms.
- At 3am, script-availability matters. "Engage security-rite" is a directive; the script is the affordance.
- **Recommendation**: add CW-6 and CW-8 §(e) security-handoff scripts (4-line paste-ready incident channel post).

### F4. No "first-2-minutes" checklist
- Runbooks assume oncall starts at §(a) and reads linearly. In practice, the first 2 minutes of an alert should be: (1) confirm ACK; (2) confirm scope (fleet-wide vs single instance); (3) open relevant CW dashboard; (4) open incident channel; (5) post "on it" with expected first-update time.
- This is a **page-one consistency pattern** that would benefit from a shared boilerplate block across all runbooks.
- **Recommendation**: observability-engineer adds a shared §(z) "First 2 Minutes" or opens a `runbook-boilerplate.md` companion file that all auth runbooks link from. Template:
  ```
  1. ACK page (target: <5 min from trigger).
  2. Open CloudWatch dashboard [link].
  3. Open incident channel; post: "Acking <ALARM>. Triage underway. First update in 15 min."
  4. Read §(a) to confirm trigger interpretation.
  5. Follow §(b) triage sequence.
  ```

### F5. No "how to find me" contact ladder
- Runbooks assume the oncall knows who to page (oncall-auth, incident-commander, security-rite). At 3am in a healthy rotation this is PagerDuty-resolvable. In a stressed rotation (someone called out sick, primary silent), the oncall needs the fallback ladder.
- **Recommendation**: runbook references `ON_CALL_ESCALATION.md` (which exists in the runbooks directory — good!) but does not link to it from each runbook's §(c). Add cross-reference.

---

## 9. What's Genuinely Good (The Keep List)

1. **CW-5 Plain-English impact** pattern — replicate to every future runbook.
2. **CW-6 3-hypotheses framing** for security-adjacent alerts — gold standard.
3. **CW-8 "Do NOT do" section** — the anti-pattern guard is exactly what IC wants in runbooks under pressure.
4. **M-2 IC-approval gate + code-before-DB sequencing** — this is the #1 reason I'm CONCUR on M-2.
5. **M-2 P50/P90 elapsed-time estimate** — timing discipline for stakeholder comms.
6. **Co-fire cross-runbook checks (CW-6 step 8, CW-8 step 9)** — systems-thinking reflex baked in.
7. **Triage-step cap at 10** — observability-engineer held the max-10 discipline. Cognitive-load-bounded.

---

## 10. Remediation Roadmap

| Priority | Item | Scope | Effort |
|----------|------|-------|--------|
| P1 | Fix phantom metric-emitter paths in CW-5/6/7/8 | 4 files × 1 line each | 20 min |
| P1 | Verify `ENFORCE_INTERVAL_BACKOFF` flag exists (CW-7 R2) | 1 verify + patch | 15 min |
| P1 | M-2 S1 pip-install brittleness note | 1 file, 1 paragraph | 10 min |
| P2 | Verify `tests/test_pkce.py` existence OR rewrite CW-6 step 5 reference | 1 file, 1 step | 10 min |
| P2 | M-2 S2/S3 time estimate + S3 bucket stipulations | 1 file, 2 paragraphs | 15 min |
| P2 | Security-rite handoff script (CW-6 §(e), CW-8 §(e)) | 2 files | 20 min |
| P3 | Shared "First 2 Minutes" boilerplate section | 1 new file + 5 cross-refs | 30 min |
| P3 | §(e) false-positive suppression protocol across all 5 runbooks | 5 files | 30 min |

**Total remediation effort**: ~2.5h author time. Well within sprint-scope.

---

## 11. Critic Verdict

**AGGREGATE**: 4× REMEDIATE + 1× CONCUR-with-stipulations.

**BLOCK**: no. None of the runbooks contain wrong guidance that would produce worse outcomes than no runbook at all. The defects are recoverable and the content is materially useful.

**REMEDIATE rationale**: the phantom-link pattern in CW-5/6/7/8 and the false-positive-suppression gap are both fixable in <1h author time but materially affect 3am-oncall usability. Ship-before-Wave-1 fix.

**CONCUR-with-stipulations rationale (M-2)**: the artifact is the strongest of the five on decision-gate discipline; the three stipulations are editorial and do not reshape the runbook's structure.

**Confidence**: MODERATE (0.72). Sister-specialist in-rite critique; cap at MODERATE per self-ref-evidence-grade-rule. STRONG requires external-critic (e.g., hygiene rite audit or chaos-engineer GameDay with live oncall).

## 12. References

- observability-engineer Wave 1 runbook stubs (5 files listed in frontmatter `data_sources`)
- ADR-0004 revocation backend dual-tier: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md`
- ADR-0006 internal-vs-admin-plane separation: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md`
- sre-catalog skill — incident-commander role definition
- self-ref-evidence-grade-rule skill — MODERATE ceiling for in-rite critique
- Cook 1998 "How Complex Systems Fail" [II:SRC-001] — multiple contributing factors framework
- Dekker 2006 "Field Guide to Human Error" [II:SRC-002] — local rationality; blameless postmortem
- Reason 1997 "Swiss Cheese Model" [II:SRC-003] — defense-in-depth failures
- Google 2018 SRE Workbook Ch. 5 [SR:SRC-010] — alerting on SLOs, alert-tuning discipline
