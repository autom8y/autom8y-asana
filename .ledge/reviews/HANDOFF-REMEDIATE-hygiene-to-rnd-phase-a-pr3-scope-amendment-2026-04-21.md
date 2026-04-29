---
type: handoff
artifact_id: HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21
schema_version: "1.0"
source_rite: hygiene (execution-downstream of rnd Phase A close)
target_rite: rnd (Phase A author — autom8y-core-aliaschoices-platformization)
handoff_type: assessment  # hygiene assesses scope coherence; returns REMEDIATE verdict on HANDOFF §2 PR-3
priority: high
blocking: true  # PR-3 cannot execute until rnd-Phase-A amends HANDOFF §2
status: proposed
handoff_status: pending
verdict: REMEDIATE+DELTA  # per critique-iteration-protocol
response_to: /Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md
initiative: autom8y-core-aliaschoices-platformization
parent_initiative: total-fleet-env-convergance (parked session-20260421-020948-2cae9b82)
sprint_source: "hygiene-session 2026-04-21 execution"
sprint_target: "rnd-Phase-A HANDOFF amendment (future session; CC-restart required)"
emitted_at: "2026-04-21T~14:10Z"
expires_after: "30d"
adr_under_execution: /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md
operator_rulings_inherited:
  - "Q1 RETIRE verdict [STRONG via Q1 operator ratification]"
  - "Q2 Uniform retire (Zero Trust)"
  - "Q3 Parent amend at Phase A close"
  - "Q4 Narrow retire (SDK-core boundaries only)"
operator_ruling_this_cycle: "2026-04-21 AskUserQuestion: Option D (cross-rite-handoff back to rnd for HANDOFF amendment)"
t1_evidence_anchor: /Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md
evidence_grade: strong  # cross-rite boundary + direct-source-verified F-1 + 5-option structured analysis + operator ratification
---

# HANDOFF-REMEDIATE — Hygiene → rnd Phase A (PR-3 Scope Amendment Request)

## 1. Executive Summary

Hygiene rite (execution-downstream of rnd Phase A dispatch) surfaced a structural under-specification in HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md §2 PR-3 at T-1 consciousness touchpoint during Phase 0 pre-flight. Operator ruling 2026-04-21T~14:00Z invokes Option D per hygiene-Potnia's preference order: **cross-rite-handoff back to rnd Phase A for formal HANDOFF §2 amendment**.

**Verdict**: `REMEDIATE+DELTA` per `critique-iteration-protocol` skill.

**Scope impact**:
- PR-1 (autom8y-core) and PR-2 (autom8y-auth `client_config.py`) remain IN-SCOPE for hygiene execution this session (deletion-only scope; no F-2-class structural break risk)
- PR-3 (autom8y_auth_client `service_client.py`) is DEFERRED pending rnd-Phase-A amendment
- Hygiene session emits `PARTIAL-MERGE` verdict in its HANDOFF-RESPONSE (2/3 PRs merged; PR-3 deferred)

**Amendment requested**: expand PR-3 scope from "delete env-reads" to full OAuth client_credentials refactor of `ServiceAuthClient`, OR route PR-3 to Option B (deprecate-ServiceAuthClient) pattern, OR other rnd-Phase-A authorial ruling.

## 2. Context — Why T-1 Fired

Hygiene rite adopted rnd-Phase-A's HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md via rite-switch (review → hygiene) at session entry. The inherited Potnia-proxy orchestration plan formalized 3 consciousness touchpoints: T-1 (post-Phase-0-preflight), T-2 (Node 1 → Node 2 DAG boundary), T-3 (pre-HANDOFF-RESPONSE emit).

Phase 0 pre-flight executed 4 gate checks:
- BQ-1 X-API-Key server-dead re-verify (F-1): **GREEN** ✅
- BQ-2 uv.lock private-registry blind-spot: **CLEAN** ✅
- BQ-3 target-file existence: **ALL 4 PATHS EXIST** ✅
- R-4 shared-monorepo pre-empt: **CONFIRMED** (all 3 packages in ONE repo; commits must serialize) ⚠️

T-1 touchpoint also surfaced F-2 (structural under-specification of PR-3 scope) via direct Read of `service_client.py` (353 lines) against HANDOFF §2 PR-3's 3-range deletion spec.

## 3. F-2 Finding — Structural Under-Specification Detail

See durable evidence at `/Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md` for full 5-finding catalog.

HANDOFF §2 PR-3 specifies:
- Delete env reads at lines 161-163 (`os.environ.get("SERVICE_API_KEY")`)
- Delete `missing.append("SERVICE_API_KEY")` at line 171
- Update docstrings at 106, 153

Direct read of `autom8y/services/auth/client/autom8y_auth_client/service_client.py` (canonical path, confirmed via BQ-3) shows the retirement target is the **entire X-API-Key auth flow**:

| Line | Symbol | HANDOFF scope? | Retirement-coherent action |
|------|--------|----------------|----------------------------|
| 118 | `api_key: str` constructor param | ❌ NO | Must refactor to `client_id`+`client_secret` |
| 139 | `self.api_key = api_key` attribute | ❌ NO | Must refactor |
| 161-163 | env reads | ✅ YES | Replace with CLIENT_ID+CLIENT_SECRET reads |
| 171 | `missing.append` | ✅ YES | Update env names |
| 181 | `api_key=key` in factory call | ❌ NO | Update constructor signature |
| 243 | `headers={"X-API-Key": self.api_key}` | ❌ NO | Convert to POST `client_credentials` body |
| 106, 153 | docstrings | ✅ YES | Update |
| `tests/test_sprint2_regressions.py:388-444` | M-002 regression tests | ❌ NO | Delete or rewrite for OAuth flow |

**Literal HANDOFF application leaves SDK structurally broken**:
- `from_environment()` cannot populate `api_key` (line 181 fails after deleting line 163)
- `self.api_key` unset → None
- Line 243 sends `X-API-Key: ""` header (empty value)
- M-002 tests fail mock assertions

**Coherent retirement requires ~3-4x HANDOFF's deletion scope**: full OAuth client_credentials refactor of `_exchange_token` + `from_environment()` factory + constructor signature + test migration.

## 4. Option Space Presented to Operator (2026-04-21)

| Opt | Action | Scope | Blast | Charter fit |
|-----|--------|-------|-------|-------------|
| A | Full OAuth refactor of ServiceAuthClient in-session | ~3-4x HANDOFF scope | Consumer env-var swap | Scope-bleed anti-pattern |
| B | Deprecate ServiceAuthClient; consumers migrate to autom8y-core | Large; 11+ consumer PRs | Huge blast | Exceeds hygiene mandate |
| C | Bifurcate — literal HANDOFF + follow-up PR-3b | HANDOFF-fidelity + debt | Transitional broken state | Hygiene-internal fallback |
| **D** | **Cross-rite-handoff to rnd for HANDOFF amendment** | **Pauses PR-3** | **Provenance-clean** | **Charter-correct** ✅ SELECTED |

Hygiene-Potnia preference order: D > C > A > B.

## 5. Amendment Request — What rnd-Phase-A Needs to Rule

### 5.1 Scope ruling (primary)

Choose one:

**Option A′** — Amend HANDOFF §2 PR-3 to full OAuth client_credentials refactor:
- Replace `api_key` constructor param with `client_id` + `client_secret`
- `from_environment()` reads `CLIENT_ID` + `CLIENT_SECRET` (with canonical-alias dual-lookup per ADR-0001 §2.3; same pattern as autom8y-core config.py:117-119)
- `_exchange_token` POSTs client_credentials body (form or JSON — specify which per server's canonical `/tokens/exchange-business` contract) instead of X-API-Key header
- Delete M-002 regression tests; add new tests asserting OAuth client_credentials emission
- Update consumer docs/examples

**Option B′** — Amend HANDOFF §2 PR-3 to deprecate-ServiceAuthClient:
- Mark `ServiceAuthClient` class `@deprecated` with hard-raise `RuntimeError` pointing consumers to `autom8y_core.Client.from_env()`
- Dispatch consumer-migration handoffs per A.2 consumer matrix (11+ services)
- Eventually delete class in a follow-up retirement PR

**Option C′** — Amend HANDOFF §2 PR-3 to a hybrid transitional:
- Keep ServiceAuthClient class signature stable (backward-compat)
- Rewire internal `_exchange_token` to use OAuth client_credentials via autom8y-core's `TokenManager` delegation (composition)
- Preserve `from_environment()` factory but read both SERVICE_API_KEY (raise deprecation warning) and CLIENT_ID/CLIENT_SECRET (preferred)

**Option D′** — Other rnd-Phase-A authorial ruling not in A′/B′/C′.

### 5.2 Server contract specification (blocking sub-question)

`service_client.py` currently POSTs to `/tokens/exchange-business` with `X-API-Key: {api_key}` header and no body (M-002 behavior). Under OAuth refactor, what does the server EXPECT?
- `application/x-www-form-urlencoded` body: `grant_type=client_credentials&client_id=...&client_secret=...`?
- `application/json` body: `{"client_id": "...", "client_secret": "...", "grant_type": "client_credentials"}`?
- `Authorization: Basic {base64(client_id:client_secret)}` header + body `grant_type=client_credentials`?

autom8y-core's `token_manager.py:460-477` shows Basic-auth-encoded approach. If `/tokens/exchange-business` accepts that same pattern, hygiene can match; otherwise rnd must specify.

### 5.3 Test migration scope

M-002 regression tests at `test_sprint2_regressions.py:388-444` assert X-API-Key header emission. Under OAuth refactor:
- Delete + replace with OAuth assertion tests?
- Delete without replacement (covered by autom8y-core tests if Option C′ delegation)?
- Keep as regression against legacy path (with mock server accepting X-API-Key)?

### 5.4 Consumer migration coordination

Per A.2 consumer blast-radius spike: 11 val01b services + autom8y_auth_client callers use `ServiceAuthClient.from_environment()`. Under OAuth refactor:
- Does rnd-Phase-A dispatch a separate consumer-migration HANDOFF to autom8y-val01b-fleet-hygiene?
- Does hygiene's eventual PR-3 (post-amendment) carry the consumer-side env-var migration too?
- Does OAuth client_credentials migration happen at `secretspec.toml` altitude first, then code?

## 6. Escalation Triggers (if rnd Phase A cannot amend)

If rnd-Phase-A returns BLOCKING on the amendment (cannot re-scope without parent-initiative re-dispatch):
- ESCALATE to fleet-Potnia at parent-initiative resume (CG-2 or operator-directed)
- OR reschedule PR-3 to a new initiative entirely (ecosystem-rite at parent-unpark)
- OR operator overrides with Option C (bifurcate) as fallback in this hygiene session

If rnd-Phase-A elects Option B′ (deprecate-ServiceAuthClient), the consumer blast-radius work exceeds hygiene's direct reach and routes via downstream handoff-outs (similar to rnd-Phase-A's original hygiene-sms + hygiene-val01b dispatches).

## 7. Concurrent Progress Markers (this session's deliverables)

Hygiene rite proceeds this session on:

**PR-1 autom8y-core** (janitor dispatching 2026-04-21T~14:15Z; audit-lead critic gate; ADR-0001 grade-upgrade commit post-merge)
- config.py: delete `_resolve_secret("SERVICE_API_KEY")` path (lines 15-54), delete `service_key` from `from_env()` (lines 112-161), update error message at line 101, add CLIENT_ID/CLIENT_SECRET canonical-alias dual-lookup at lines 117-119, docstring updates at lines 23/45/117
- token_manager.py:450: delete X-API-Key path
- pyproject.toml: bump 3.1.0 → 3.2.0
- CHANGELOG: entry citing ADR-0001
- ~13 test files: enumerate + delete/migrate
- ADR-0001 frontmatter commit: `evidence_grade: moderate → strong` with PR-1 merge SHA + audit-lead artifact citation

**PR-2 autom8y-auth** (sequential post-PR-1; shared monorepo serialization constraint)
- client_config.py:73: delete SERVICE_API_KEY direct-read
- client_config.py:43: delete error message referencing SERVICE_API_KEY
- client_config.py:59, 71: docstring updates
- test cleanup in autom8y-auth package

**PR-3 autom8y_auth_client** — BLOCKED pending this HANDOFF's amendment resolution.

**Hygiene HANDOFF-RESPONSE** (eventual session close): `PARTIAL-MERGE` verdict at `/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-to-rnd-sdk-deletion-prs-2026-04-21.md` with 2 merge SHAs + F-2 deferral explicitly cited.

## 8. Response Protocol

rnd-Phase-A (at next session resume — CC restart required) emits one of:

- **AMENDMENT-LANDED**: authors amended HANDOFF-rnd-to-hygiene-sdk-deletion-prs-pr3-amended-{date}.md with Option A′/B′/C′/D′ ruling + updated §2 scope + §3 acceptance criteria. Hygiene re-dispatches PR-3 in that future session.
- **REMEDIATE-DISPUTED**: rnd-Phase-A returns CONCUR with original HANDOFF §2; disputes hygiene's F-2 finding. Re-triggers critique-iteration-protocol; operator gate fires.
- **ESCALATE-TO-OPERATOR**: rnd-Phase-A surfaces authorial-scope question to operator + fleet-Potnia for ruling.
- **RETIRE-PR-3-ENTIRELY**: rnd-Phase-A rules PR-3 out-of-scope for this initiative; routes retirement to a different rite (ecosystem or an admin-CLI-style dedicated session).

Target path at response: `/Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-RESPONSE-rnd-phase-a-to-hygiene-pr3-scope-amendment-{date}.md`

## 9. Evidence Grade

This HANDOFF-REMEDIATE: `[STRONG]` at emission.

- Cross-rite boundary artifact (hygiene → rnd-Phase-A)
- Synthesizes: Phase 0 pre-flight direct-source grep (F-1 validated); Read of 353-line service_client.py (F-2 structural analysis); operator 4-option interview + ruling (2026-04-21); hygiene-Potnia non-binding preference (D > C > A > B); T-1 artifact durable provenance at .sos/wip/
- Self-ref cap honored: hygiene-rite does NOT promote own-finding; rnd-Phase-A's amendment response is the natural corroboration loop-close
- Orthogonal evidence: PR #119 Explore swarm verdict LOW collision risk at evaluated-by-Explore grade MODERATE (not STRONG — static-analysis only)

## 10. Artifact Links

- **Upstream HANDOFF (REMEDIATE target)**: `/Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md`
- **ADR under execution**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
- **rnd-Phase-A close artifact (precedent for response format)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-rnd-phase-a-to-fleet-potnia-2026-04-21.md`
- **T-1 touchpoint evidence (local-only, gitignored)**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md`
- **A.1-pv premise-validation spike**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/spikes/service-api-key-legacy-cruft-investigation.md`
- **A.2 consumer blast-radius spike**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/spikes/autom8y-core-consumer-blast-radius.md`

---

*Emitted 2026-04-21T~14:10Z hygiene main thread after T-1 consciousness touchpoint + AskUserQuestion stakeholder interview. rnd-Phase-A response expected at next rnd-session resume (CC restart). Hygiene proceeds concurrently on PR-1 + PR-2 per operator Q2 ruling; PR-3 blocked on this REMEDIATE cycle.*
