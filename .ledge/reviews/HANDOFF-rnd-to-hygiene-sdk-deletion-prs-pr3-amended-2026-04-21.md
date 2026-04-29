---
type: handoff
artifact_id: HANDOFF-rnd-to-hygiene-sdk-deletion-prs-pr3-amended-2026-04-21
schema_version: "1.0"
source_rite: rnd (Phase A' REMEDIATE cycle)
target_rite: hygiene
handoff_type: implementation  # research → dev per cross-rite-handoff skill decision tree
priority: high
blocking: false  # unblocks hygiene re-dispatch; not blocking other fleet work
status: accepted  # artifact is proposed for hygiene; rnd ratifies its emission
handoff_status: pending  # hygiene accepts at next CC-restart cycle
supersedes: "HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md §2 PR-3 + §3 PR-3 rows 3+4 ONLY"  # PR-1 and PR-2 rows remain as-landed
design_authority: /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001.1-amendment-pr3-scope-oauth-refactor.md
initiative: autom8y-core-aliaschoices-platformization
parent_initiative: total-fleet-env-convergance (parked)
sprint_source: "rnd-Phase-A' REMEDIATE session 2026-04-21"
sprint_target: "hygiene re-dispatch PR-3 execution (next CC-restart)"
emitted_at: "2026-04-21T~19:15Z"
expires_after: "30d"
evidence_grade: moderate  # inherits from ADR-0001.1; upgrades to STRONG at hygiene audit-lead PASS on amended PR-3
upstream_dependencies:
  - /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md  # parent ADR (STRONG)
  - /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001.1-amendment-pr3-scope-oauth-refactor.md  # THIS HANDOFF's design authority
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21.md  # trigger
  - /Users/tomtenuta/Code/a8/repos/.sos/wip/spikes/pr3-amendment-option-enumeration-2026-04-21.md  # scout A'-1 empirical evidence
  - /Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md  # T-1 gap analysis
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21.md  # PR-1 audit
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr125-autom8y-auth-2026-04-21.md  # PR-2 audit (PROVISIONAL layer-depth discriminator)
---

# HANDOFF — rnd Phase A' (REMEDIATE) → Hygiene (Amended PR-3 Re-Dispatch)

## 1. Context

**Primary design authority for this HANDOFF**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001.1-amendment-pr3-scope-oauth-refactor.md` (ADR-0001.1; amends ADR-0001 §2.1 item 4 + §5.1). This HANDOFF ports ADR-0001.1's scope specification verbatim for hygiene execution.

Hygiene rite surfaced F-2 (structural under-specification of PR-3 scope) at T-1 consciousness touchpoint 2026-04-21T~14:00Z during Phase 0 pre-flight. Operator Option D ruling routed the finding back to rnd-Phase-A as a `critique-iteration-protocol` REMEDIATE at authorial altitude via HANDOFF-REMEDIATE. rnd-Phase-A' REMEDIATE cycle executed:

- **A'-0 premise re-verification** (2026-04-21T~18:30Z): F-1 X-API-Key server-dead **RE-VERIFIED GREEN**. Zero hits at AUTH service routers. ADR-0001 premise intact.
- **A'-1 option enumeration** (technology-scout spike; same dispatch): Options A'/B'/C' evaluated across 5 axes. Option A' ranked 1st (full OAuth refactor in-session). **Empirical zero-external-consumer finding** de-risks blast radius.
- **A'-2 consumer-matrix delta** (same spike): class-consumer vs env-var-consumer surface disambiguation — `rg "from autom8y_auth_client|import autom8y_auth_client" --type py /repos/` returns **zero files**.
- **A'-3 ADR-0001.1 authoring** (2026-04-21T~18:45Z): Option A' ratified via T-R1 rnd-Potnia concurrence. ADR-0001.1 authored with `status: accepted`, `evidence_grade: moderate` (self-ref cap per `self-ref-evidence-grade-rule`).
- **A'-4 T-R2 coherence check** (2026-04-21T~19:00Z): PASSED with CONCUR-WITH-NOTE.

This HANDOFF is emitted at Phase A'-4 post T-R2 ratification. It supersedes ONLY the HANDOFF-rnd-to-review PR-3 rows (§2 PR-3 + §3 PR-3 rows 3+4). PR-1 and PR-2 rows remain as-landed in HANDOFF-rnd-to-review and are preserved via PR #120 (SHA `82ba4147b328a983eea30b4a4f40b798fdc313e0`) + PR #125 (SHA `34e1646cc9a51c8eb90c74fa9fd634ed99796037`).

This HANDOFF does NOT modify ADR-0001, ADR-0001.1, HANDOFF-rnd-to-review, or any prior artifact. It does NOT re-open Q1–Q4 operator rulings. It does NOT expand scope beyond ADR-0001.1 §4.

## 2. Scope (ported verbatim from ADR-0001.1 §4)

This HANDOFF supersedes HANDOFF-rnd-to-review §2 PR-3 narrowed scope. The amended PR-3 executes the following edits (hygiene re-dispatches janitor post adoption of this HANDOFF):

### 2.1 `autom8y/services/auth/client/autom8y_auth_client/service_client.py` — full refactor

**Remove**:
- `api_key: str` param from `ServiceAuthClient.__init__()` (line 118)
- `self.api_key = api_key` attribute assignment (line 139)
- `os.environ.get("SERVICE_API_KEY")` at line 163
- `missing.append("SERVICE_API_KEY")` at line 171
- `api_key=key` in factory call at line 181
- `headers={"X-API-Key": self.api_key}` at line 243 — **the load-bearing legacy emission point**
- All SERVICE_API_KEY docstring references (lines 106, 153, any inherited)

**Add** (mirror PR-1 canonical-alias pattern exactly):
- `client_id: str` + `client_secret: str` params to `ServiceAuthClient.__init__()`
- `self.client_id` + `self.client_secret` attributes
- `from_environment()` canonical-alias dual-lookup (canonical-first / legacy-fallback):
  ```python
  client_id = os.environ.get("AUTOM8Y_DATA_SERVICE_CLIENT_ID") or os.environ.get("CLIENT_ID", "")
  client_secret = os.environ.get("AUTOM8Y_DATA_SERVICE_CLIENT_SECRET") or os.environ.get("CLIENT_SECRET", "")
  ```
- Updated `missing: list[str]` validation — require both client_id AND client_secret
- Updated error message — reference CLIENT_ID+CLIENT_SECRET

### 2.2 `_exchange_token` HTTP refactor — **Basic+JSON server contract** (§2.3 spec)

Replace the X-API-Key header emission at line 243 with the Basic+JSON client_credentials flow matching autom8y-core `TokenManager._build_exchange_kwargs()` at `token_manager.py:440-477` (rehearsed reference implementation):

```python
import base64

credentials = f"{self.client_id}:{self.client_secret}"
encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")

response = self._client.post(
    f"{self.auth_service_url}/tokens/exchange-business",
    headers={"Authorization": f"Basic {encoded}"},
    json={
        "business_id": business_id,
        "requested_scopes": scopes,  # or whatever the existing signature specifies
    },
)
```

### 2.3 Server contract specification (empirically-grounded per A'-1 scout finding)

**Preferred variant** (PR-3 tests MUST use as primary path):
- `Authorization: Basic {b64(client_id:client_secret)}` header
- JSON body carries ONLY `business_id` + `requested_scopes` (credentials omitted from body)

**Legacy variant** (accepted-but-deprecated; regression guard coverage optional):
- JSON body with `{client_id, client_secret, business_id, requested_scopes}`, no Authorization header
- Server accepts but MUST NOT be exercised as canonical path going forward

**Excluded**: `application/x-www-form-urlencoded` body. `/tokens/exchange-business` is structurally distinct from RFC 6749 standard `/token` (which uses form).

**Rehearsed reference**: `autom8y/sdks/python/autom8y-core/src/autom8y_core/token_manager.py` lines 440-477 — this is the canonical implementation of the preferred variant; amended PR-3 mirrors this pattern in `autom8y_auth_client/service_client.py`.

### 2.4 `autom8y/sdks/python/autom8y-auth/src/autom8y_auth/token_manager.py` — auth-flow retirement

Classified as PR-3 scope per hygiene audit-lead FU-1 P1 (not in original HANDOFF §2 PR-2 scope). Retirement edits:
- Line 355 docstring: remove SERVICE_API_KEY reference; reflect OAuth client_credentials primacy
- Line 472 error message: remove "Check your SERVICE_API_KEY environment variable." and replace with CLIENT_ID/CLIENT_SECRET guidance
- Any `self.config.service_key` references (per audit-lead FU-1 P1 lines 375/378/382): delete the X-API-Key branch; retain ONLY the Basic+JSON client_credentials path
- Delete `_build_exchange_kwargs` branch that emits X-API-Key header if present (if any remains post-PR-1)

### 2.5 Test migration (`test_sprint2_regressions.py` M-002 + `test_service_client.py`)

M-002 regression tests (lines 388-444) assert X-API-Key header emission + no-JSON-body behavior. These enforce the retired auth-flow.

**Ruling: DELETE + REPLACE** per rnd-Potnia T-R1 ratification:
- Delete: `TestM002ExchangeTokenNoBody` class and all its test methods
- Add new test class (e.g., `TestOAuthClientCredentialsExchange`) asserting:
  - `_exchange_token` sends `Authorization: Basic {b64(client_id:client_secret)}` header
  - `_exchange_token` sends JSON body with `business_id`/`requested_scopes` (not credentials)
  - Legacy variant (body-carried creds) is NOT exercised as canonical path
  - Canonical-alias dual-lookup resolves (mirror PR-1 test pattern)

`test_service_client.py` refactor:
- Replace all `service_key=` kwargs with `client_id=` + `client_secret=`
- Replace `SERVICE_API_KEY` env-var monkeypatches with canonical-alias coverage
- Add at least one canonical-first-vs-legacy-fallback precedence test

### 2.6 Explicit out-of-scope for PR-3 (quarantine zone preserved)

- `autom8y_auth_client/client.py:492` (`revoke_api_key`) — admin-CLI path per ADR-0001 §2.2 item 3 Q4-out-of-scope; routes to admin-CLI-rite
- `autom8y_auth_client/cli.py:66, 123` — admin-CLI per Q4-out-of-scope
- Consumer-side env-var migration (the 11 val01b services in A.2 matrix) — **distinct surface** per §4 below
- `.know/` + `README.md` + docs/ SERVICE_API_KEY references — doc-drift follow-up per hygiene audit-lead FU-2

## 3. Amended Acceptance Criteria (ported verbatim from ADR-0001.1 §6)

Replaces and supersedes HANDOFF-rnd-to-review §3 PR-3 rows 3 + 4 (and extends row 2 partially). Full amended criteria for PR-3:

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | SERVICE_API_KEY absent from autom8y_auth_client src + tests (excluding admin-CLI client.py:492 + cli.py:66,123 which remain Q4-out-of-scope) | `rg SERVICE_API_KEY autom8y/services/auth/client/` excludes admin paths; zero matches in scope |
| 2 | SERVICE_API_KEY absent from autom8y-auth/src/autom8y_auth/token_manager.py | `rg SERVICE_API_KEY token_manager.py` returns zero |
| 3 | ServiceAuthClient OAuth client_credentials flow implemented per §2.1 + §2.2 + §2.3 (Basic+JSON preferred variant) | Direct Read + new test class assertions |
| 4 | M-002 regression tests deleted + replaced with OAuth assertion tests per §2.5 | Direct Read test_sprint2_regressions.py + test_service_client.py |
| 5 | Canonical-alias dual-lookup (AUTOM8Y_DATA_SERVICE_CLIENT_ID/SECRET canonical; CLIENT_ID/SECRET legacy) wired in from_environment() | Mirror PR #120 pattern; verify canonical-first precedence test |
| 6 | No touches to quarantine zone: client.py, cli.py, and downstream consumer services (A.2 matrix) | `git diff main...<branch> --stat` excludes these paths |
| 7 | Server contract variant used in _exchange_token is Basic+JSON-preferred (not legacy body-creds) | Direct Read + test assertion |
| 8 | CI green on amended tests; full test suite passes | CI status check |
| 9 | hygiene audit-lead 11-check PASS verdict | AUDIT-VERDICT-hygiene-11check-pr{N}-autom8y_auth_client artifact |
| 10 | PROVISIONAL layer-depth discriminator scar-tissue codification triggered (if PASS) | `.know/scar-tissue.md` entry at AUDIT-VERDICT §6 precedent fit |

**Field-mapping note** (criteria §2.1/§2.2/§2.3/§2.5 in rows 3 + 4 map to ADR-0001.1 §4.1/§4.2/§4.3/§4.5 respectively; content is identical — only the local section-number anchor changes to this HANDOFF's §2 structure).

## 4. Class-Consumer vs Env-Var-Consumer Surface Disambiguation (Q5.4 resolution; ported verbatim from ADR-0001.1 §5)

HANDOFF-REMEDIATE §5.4 conflated two distinct surfaces. This HANDOFF replaces that conflated text with the following disambiguation per scout empirical A'-2 finding.

### 4.1 Class-consumer surface (PR-3 scope)

Consumers that `import` or instantiate `ServiceAuthClient`. Scout empirical finding 2026-04-21T~18:30Z: **ZERO external consumers** outside the `autom8y_auth_client` package itself. Verification:
```bash
rg "from autom8y_auth_client|import autom8y_auth_client" --type py /Users/tomtenuta/Code/a8/repos/
# → zero files
```

Consequence: PR-3 refactor does NOT break any external importer. Blast radius is isolated to the `autom8y_auth_client` package's own tests.

**Scope-boundary note**: This finding is grep-bounded to `/repos/`. If unchecked-out repositories, vendored copies, or external-registry consumers exist outside `/repos/`, the blast-radius assumption requires re-verification. As of amendment-authoring time, no such consumers are known.

### 4.2 Env-var-consumer surface (A.2 matrix; NOT PR-3 scope)

The 26 consumers in A.2 consumer blast-radius spike use `SERVICE_API_KEY` as an environment variable independently of `ServiceAuthClient`. They read the env var through various paths (conftest.py fixtures, secretspec.toml, justfile, runbooks, autom8y-config AliasChoices, etc).

This surface proceeds independently at fleet-rollout altitude via existing handoffs:
- `HANDOFF-rnd-to-hygiene-sms-transition-alias-drop-2026-04-21.md` (sms satellite)
- `HANDOFF-rnd-to-hygiene-val01b-sdk-fork-retire-2026-04-21.md` (val01b fork + test fixtures)
- Per-service PRs at the COORDINATED-BUMP cohort level in A.2 §3

**PR-3 scope does NOT carry consumer-side env-var migration**. This disambiguation is load-bearing for scope discipline.

## 5. Entry Conditions (Hygiene Re-Dispatch Setup)

1. **Read ADR-0001.1 as primary design authority**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001.1-amendment-pr3-scope-oauth-refactor.md`
2. **Read this HANDOFF as execution scope**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-rnd-to-hygiene-sdk-deletion-prs-pr3-amended-2026-04-21.md`
3. **Read ADR-0001 as upstream foundation**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
4. **Re-verify F-1 X-API-Key server-dead at Phase 0 pre-flight** (R1 risk mitigation per ADR-0001.1 §10 step 1):
   ```bash
   rg "X-API-Key|x-api-key|APIKeyHeader" /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/autom8y_auth_server/routers/
   ```
   Expected: zero hits. If hits appear, ABORT and ESCALATE per §6 trigger (a).
5. **Confirm quarantine zone unchanged**: `autom8y_auth_client/client.py:492`, `autom8y_auth_client/cli.py:66,123`, and downstream consumer services (A.2 matrix) remain untouched at Phase 0.
6. **Hygiene-Potnia orchestrates** the re-dispatch pantheon (same janitor + audit-lead cycle as PR-1/PR-2). No new pantheon members required.

## 6. Escalation Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| (a) F-1 re-verify fires RED | X-API-Key hits re-emerge at AUTH service routers | ABORT; premise falsified; ESCALATE to rnd-Phase-A' + operator (ADR-0001 premise compromised) |
| (b) Scope expansion beyond ADR-0001.1 §4 | hygiene janitor or audit-lead attempts edits outside §2 enumerated scope | BLOCKING; escalation not permitted by hygiene-rite absent a new REMEDIATE cycle to rnd-Phase-A'' |
| (c) Hygiene audit-lead BLOCKING verdict cap 2 REMEDIATE | Second BLOCKING verdict at 11-check critique | ESCALATE to rnd-Phase-A' for further scope refinement or operator arbitration |
| (d) Amended scope still structurally insufficient | Unlikely given empirical scout evidence (zero external consumers + server contract empirically resolved); if surfaces anyway | Second REMEDIATE back to rnd-Phase-A' via new HANDOFF-REMEDIATE; not a BLOCKING-at-merge verdict |

## 7. Evidence Grade

This HANDOFF: **`[MODERATE]`** at emission. Inherits from ADR-0001.1 (`evidence_grade: moderate`) per self-ref cap (rnd-rite re-authoring its own HANDOFF scope; `self-ref-evidence-grade-rule` applies).

**Upgrade path to `[STRONG]`**: hygiene-rite audit-lead (rite-disjoint external critic) issues PASS verdict on amended PR-3 at merge-gate. Mirrors ADR-0001's own MODERATE→STRONG upgrade via PR #120 audit (SHA `82ba4147b328a983eea30b4a4f40b798fdc313e0`). The same rite that corroborated ADR-0001 corroborates its amendment — continuity of critic discipline.

## 8. Response Protocol

Hygiene emits HANDOFF-RESPONSE post-merge at:
- Path: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-to-rnd-pr3-amended-{date}.md`
- Verdict options: **ACCEPTED-WITH-MERGE** / **REMEDIATE+DELTA** / **ESCALATE**
- For ACCEPTED-WITH-MERGE: merge SHA + CI status + consumer-regrep evidence + audit-lead AUDIT-VERDICT artifact citation + ADR-0001.1 grade-upgrade trigger event block
- For REMEDIATE+DELTA: structured delta per `critique-iteration-protocol` skill + targeted amendment request back to rnd-Phase-A''
- For ESCALATE: cross-rite routing to operator + fleet-Potnia

Upon ACCEPTED-WITH-MERGE, ADR-0001.1 `evidence_grade` upgrades MODERATE → STRONG per §7 upgrade-path pattern. This CLOSES the SERVICE_API_KEY retirement initiative end-to-end (PR-1 + PR-2 + amended PR-3 all landed; canonical-source-integrity throughline LIVE at all SDK surfaces).

## 9. Artifact Links

- **Primary design authority (ADR-0001.1 amendment)**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001.1-amendment-pr3-scope-oauth-refactor.md`
- **Parent ADR (ADR-0001; STRONG post-PR #120)**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
- **Trigger artifact (hygiene REMEDIATE)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21.md`
- **Superseded-for-PR-3 source (HANDOFF-rnd-to-review; PR-1/PR-2 rows remain as-landed)**: `/Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md`
- **Scout A'-1 option enumeration (empirical evidence)**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/spikes/pr3-amendment-option-enumeration-2026-04-21.md`
- **T-1 gap analysis**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md`
- **Hygiene PR-1 audit**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21.md`
- **Hygiene PR-2 audit (layer-depth discriminator PROVISIONAL)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr125-autom8y-auth-2026-04-21.md`

---

*Emitted 2026-04-21T~19:15Z from rnd-Phase-A' REMEDIATE session main thread at Phase A'-4 post T-R2 coherence PASS (CONCUR-WITH-NOTE). Hygiene re-dispatch expected at next CC-restart cycle. PR-3 is the third data point for the PROVISIONAL layer-depth discriminator from AUDIT-VERDICT-pr125 §6 — PASS confirms with broader-layer scope, REMEDIATE falsifies at that depth cleanly. Either outcome advances fleet understanding.*
