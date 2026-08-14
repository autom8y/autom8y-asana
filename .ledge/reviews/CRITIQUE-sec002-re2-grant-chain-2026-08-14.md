---
type: review
status: accepted
rung: STRUCTURALLY-VERIFIED (static own-hands file:line + git blob-SHA reads + gh compare metadata; NO runtime probe)
second_reads: DOSSIER-sec002-re2-grant-chain-2026-08-14
self_assessment_cap: MODERATE
seat: qa-adversary (10x-dev rite) — rite-disjoint vs dossier's arch/dependency-analyst seat; falsifier role
authored: 2026-08-14
---

# CRITIQUE — SEC-002 RE-2 grant-chain dossier — adversarial second read

```yaml
critique: CRITIQUE-sec002-re2-grant-chain-2026-08-14
attacks: DOSSIER-sec002-re2-grant-chain-2026-08-14
charge: ATTACK the dossier; go one hop past where the author stopped; report nulls as evidence
disjointness: 10x-dev qa-adversary seat; shaped none of the traced work
fences_observed:
  - READ-ONLY; single write = this file
  - CR-5 honoured — no credential values read/printed/decoded, no token mint/decode,
    no AWS/Asana/OpenFGA API calls, no code-scanning-alert endpoints
  - git fetch / checkout / working-tree mutation NOT performed
  - gh api used for: (1) branch-SHA reads, (2) git blob-SHA reads via contents API
    (content HASH only — no file body fetched through the API), (3) commit metadata
    (SHA + first-line message). NO patch bodies pulled through the API.
self_assessment_cap: MODERATE (may not grade the author STRONG; own static trace is
  rite-disjoint but un-runtime-probed)
```

---

## §0 — Headline

**HIGH SURVIVES. SH-1 DISCHARGES CLEAN on the F-001 code chain (byte-identical on
origin/main), with TWO narrowings the author could not see because the object was
never fetched.** Every one of the four priority-target legs STANDS or
STANDS-WITH-NARROWING. Nothing FALLS. The dossier's central recommendation —
HIGH re-affirmed, Critical not warranted — is intact against the substrate of
record, not merely against the stale branch it was read from.

The one substantive correction: the dossier's NF-1 "**18 of 18**" population
integer is a read-surface snapshot that origin/main has already moved past
(main enrolled ≥1 additional exempt SA after the read point). The
population-level *property* stands and is arguably strengthened; the specific
count should be reclassified from asserted-fact to UV-P-bounded.

---

## §1 — Verdict table (per leg, with own-hands hop)

| Leg / Target | Verdict | Own-hands hop (command → result) |
|---|---|---|
| **SH-1** (branch-vs-origin/main staleness) | **DISCHARGED-CLEAN (code) / NARROWED (registry count)** | `gh api compare 868ead94...2159f967` → `diverged, ahead 76, behind 163`; blob-SHA equality on all charge-named anchors (below) |
| **T2** business-scope gate bypassed end-to-end for ace/iris | **STANDS** | own-eyes `middleware.py:278-280` (bypass→`return None`) + `internal.py:157-162` (logs, returns, no authz) |
| **T3** CF-1 widening = population-of-one, inert | **STANDS (two-sided)** | `service_jwt.py:231-234` catches; `main.tf:1533` legacy = no-asana does-not-falsely-flag |
| **T4** LEG-D refuted-by-accident (list-vs-str parse fail) | **STANDS** | `claims.py:164` `scope: str|None`; `:139` `extra:ignore`; `:187` plain method; pydantic **2.12.5** installed |
| Overall HIGH-stands recommendation | **SURVIVES** | union of the above |

---

## §2 — SH-1 discharge (highest priority) — the object the author could not diff

### 2.1 The charge's presupposed method is unexecutable; a fence-safe substitute was used

- Live `origin/main` (gh api, this session) = `868ead943bf4cf44b9f44458e7bf4d9574672fb5` — **matches the dossier §0 claim**. The dossier's staleness receipt is accurate.
- **`868ead94` is NOT present as a local git object** (`git cat-file -t 868ead94` → `fatal: could not get object info`). The local remote-tracking `origin/main` is stale at `db1262a8`, and `git fetch` is fenced. The charge's literal discharge form (`git diff 868ead94 2159f967 -- <path>`) therefore cannot run in this working tree.
- Fence-safe substitute actually executed: **git blob-SHA comparison** via the contents API (a content *hash*, never the file body) + gh `compare` **metadata** (ahead/behind counts) + `git log`-equivalent commit metadata (SHA + first-line message — the discharge form the charge explicitly blessed). No patch body, no credential value, no CR-5-forbidden endpoint touched.

### 2.2 The read surface is 163 commits behind origin/main

```
gh api repos/autom8y/autom8y/compare/868ead94...2159f967 →
  status=diverged  ahead_by=76  behind_by=163
```

The dossier read a branch **163 commits behind** the substrate of record. Staleness is real and larger than a feature-branch-tip delta.

### 2.3 Every charge-named severity-load-bearing anchor is BYTE-IDENTICAL

Blob-SHA at `868ead94` (origin/main) vs `2159f967` (read surface):

| Anchor file (charge-named) | main blob | read blob | Verdict |
|---|---|---|---|
| `terraform/modules/service-accounts/main.tf` (`:32-36`) | `bb6d61da` | `bb6d61da` | **IDENTICAL** |
| `services/auth/…/sa_reconciler.py` (`:794-796`) | `044bfcd0` | `044bfcd0` | **IDENTICAL** |
| `services/auth/…/boot_reconciler.py` (`:139`) | `da760215` | `da760215` | **IDENTICAL** |
| `services/auth/…/token_service.py` (`:780/:784/:420/:429/:617-622`) | `fb877e7c` | `fb877e7c` | **IDENTICAL** |
| `services/auth/…/app/config.py` (`:83`) | `35876c71` | `35876c71` | **IDENTICAL** |
| `sdks/…/autom8y_auth/middleware.py` (4.2.0-src `:278-281`) | `788cdeec` | `788cdeec` | **IDENTICAL** |

Also identical (trace-supporting): `token_service_resolution.py`, `routers/tokens.py`, `routers/oauth.py`, `terraform/services/auth/main.tf`, SDK `client.py`, SDK `_detection.py`.

`internal.py:83-172` is in **autom8y-asana on `main`**, not the wss branch — SH-1 (wss-branch staleness) does not apply to it; verified own-eyes below (T2).

**The single most load-bearing file — `token_service.py`, which carries every LEG-B and LEG-D `token_service.py` line-anchor — is byte-identical on both commits.** The entire F-001 chain (LEG A emitters → LEG B claim stamp → middleware precedence) is unchanged on the substrate of record.

### 2.4 The branch's "scope-bypass closure" is a DIFFERENT bypass — and it is not even on main

Two anchors DIFFER (the author, lacking the object, could not see this):

- **`services/auth/service-accounts.yaml`** — `e3371644` (main) vs `4ca7013e` (read). Cause: **origin/main is AHEAD**. Latest main commits touching it: `6933a512` (2026-08-11) *"enroll calendly-intake-service exempt SA"* and `78b3192c` (2026-08-10) *"de-fang canary-seed (yaml_id NULL)"*. The read surface stops at `89f787ee` (2026-08-06). → additive exempt-SA enrollment on main; see §3.
- **`sdks/…/autom8y_auth/claims.py`** (4.2.0 source) — `a3aaa66d` (main) vs `4faae9a5` (read). Cause: the read surface carries an **extra** commit `29d64182` (2026-08-09) *"close the wildcard scope-bypass sentinel in has_scope"* that is **NOT on origin/main**. That commit modifies `has_scope` (the `self.scope == "*"` wildcard, own-eyes `claims.py:221`), which is a **different bypass axis** than F-001's `bypass_scope_enforcement` claim, and it lives on a copy asana does not run (asana runs installed **4.1.0**).

**Both refute the charge's worst-case hypothesis.** The charge feared the branch "may already be remediated on the very axis this dossier reports HIGH → HIGH may be STALE." Reality is the inverse on both counts: (a) the branch's closure work targets a *different* bypass (wildcard `has_scope`), and (b) whatever closure the branch does carry is **ahead of, not behind,** origin/main — so origin/main is if anything *less* remediated, not more. **HIGH does not go stale against origin/main.**

### 2.5 SH-1 residual (honest null)

The ace/iris `business_scoped:false` determinant (§1) and the `iris`-lacks-asana scope set (C.3) are byte-verified only on the **read surface**. On origin/main, `service-accounts.yaml` differs — but the differing commits are **additive enrollments** (`calendly-intake-service`, `ws-a bridge`) and a canary de-fang; none names a modification to `ace` or `iris`. Under the read-only/no-fetch fence I cannot pull origin/main's file body to byte-confirm ace/iris are unchanged. Direction: determinant near-certainly holds on main; **not byte-proven**. This is a *thin* residual on the registry-derived facts only — the code chain has none.

---

## §3 — Reclassification: NF-1 "18 of 18" is stale (UV-P, not fact)

The dossier asserts (§1 NF-1, §7 Amendment 1) that **18 of 18** registered SAs are `business_scoped:false`, and leans on this exact integer to widen F-001 from "two SAs" to "population-level property."

- The count was taken on the read surface (`2159f967`), which origin/main has passed: main's `6933a512` *enrolls calendly-intake-service as an exempt SA* after the read point, and `78b3192c` de-fangs a canary seed (`yaml_id NULL`).
- Therefore **the substrate-of-record population is not 18** — it is at least one greater on the exempt side (net of the canary de-fang), and the registry is under active exempt-SA enrollment.

**Disposition:** the population-level *property* the dossier draws from NF-1 — an unfiltered `if !business_scoped` exemption path with **zero** business-scoped entries — STANDS and is **strengthened** (exempt enrollment is ongoing, not frozen). But the specific "**18 of 18**" should be reclassified from asserted current fact to **UV-P-bounded read-surface snapshot**. Recommend the dossier / consumer restate NF-1 as "≥18 exempt / 0 business-scoped as of `2159f967`; count is drifting upward on origin/main." This does not move severity.

This is the one hop past where the author stopped: the author flagged SH-1 as wholly-undischarged and feared *branch-adds-closure*; the actual divergence is *main-adds-exemptions* — staleness in the opposite direction from the one the dossier hedged against.

---

## §4 — T2: gate bypassed end-to-end — STANDS own-eyes

Read the installed 4.1.0 runtime (what asana actually runs), not inherited from the dossier:

- `middleware.py:278-280` (asana `.venv`, 4.1.0):
  `if getattr(claims, "bypass_scope_enforcement", False) is True: request.state.bypass_scope = True; return None`
  — Step 1 checks bypass **FIRST** and returns `None` (= allow). The docstring `:255-258` names it: *"Exempt SAs (e.g., Ace) carry this claim … MUST be allowed even when business_id is absent."*
- `internal.py:157-162` (`require_service_claims`): after `validate_service_token` (`:122`) it **logs caller + scope** (`:148-155`) and returns `ServiceClaims(...)`. **No business_id check, no bypass check, no scope/permission assertion, no tenant check, no caller allowlist.**
- Wiring confirmed: `main.py:445` `require_business_scope=True`.

**No control exists between mint and the asana S2S route beyond (a) the middleware, which stands down by design for bypass tokens, and (b) `require_service_claims`, which adds nothing.** For ace/iris tokens `require_business_scope=True` **does** reduce to the bypass short-circuit. The charge's probe finds no missed control. STANDS.

---

## §5 — T3: CF-1 two-sided — STANDS, no overclaim

**(a) must-catch:** `autom8y-hermes/plugins/autom8y/auth/service_jwt.py:231-234` posts `{client_id, client_secret}` to `f"{self._auth_url}/tokens/exchange-business"` — the **SA endpoint**, not the OAuth client_credentials token endpoint — and `:276-277` defaults TTL to *"300s (confirmed for exempt SAs)."* Hermes mints the exempt-SA species using OAuth credential material; the `asana:read` OAuth grant is **inert** for the token it obtains. Dossier's decisive finding C.3 confirmed own-eyes.

**(b) must-not-falsely-flag:** `terraform/services/auth/main.tf` (identical on both commits) — `module "oauth_clients_legacy_monolith"` carries `scopes = "data:read sms:write"` (`:1533`) — **no asana**; only `module "oauth_clients_hermes"` carries `"data:read asana:read"` (`:1581`). Terraform-declared asana-scoped OAuth clients = **1**.

**Undercount question:** the dossier does **not** assert population=1 as a hard fact — it labels the true DB population **UV-P-C1** ("terraform is a lower bound only … oauth_clients rows are DB-resident … `routers/admin.py:474-486`"). Correct discipline; no reclassification needed. The population-of-one is properly scoped to the terraform substrate with the DB population deferred.

---

## §6 — T4: LEG-D refuted-by-accident — STANDS (parse-failure is sound)

Read the installed 4.1.0 model + the runtime pydantic:

- `claims.py:164` — `scope: str | None = Field(default=None, …)`
- `claims.py:139` — `model_config = {"extra": "ignore"}` (inherited from `BaseClaims`); **no strict/lax override**
- `claims.py:187` — `validate_scope_scopes_invariant` is a **plain instance method** (docstring: *"Callers wanting fail-closed parsing call this explicitly after model construction"*), **not** a `@model_validator`. There is **no** `@field_validator(mode="before")` and **no** `@model_validator(mode="before")` on `scope` anywhere in `claims.py`/`BaseClaims`.
- Installed runtime: **pydantic 2.12.5 / pydantic_core 2.41.5**.

**Attack — could a validator or `mode='before'` coerce list→str?** No such hook exists (grep of the model surface returns only the plain after-method). pydantic v2 does not coerce a `list` into a `str` field even in lax mode: a list input to `str | None` fails the `str` member (`string_type`) and the `None` member, raising `ValidationError` at core field validation — *before* any user validator runs. `create_agent_token` stamps `scope` as a list (`token_service.py:429`, byte-identical on origin/main), so the decoded claim is a JSON array and the parse fails.

**The refutation is sound.** UV-P-D1's static inference holds under the actually-installed pydantic. CF-6 is **dormant, not live** — held shut by the `list`-vs-`str` accident, exactly as the dossier states. The dossier's "one type-normalisation commit away from live" hardening flag (normalise `token_service.py:429` to a space-delimited string → parse succeeds → bypass=False default → clears the route) is **correct and worth carrying** to the operator; it is the highest-leverage latent exposure surfaced, and it is untested (UV-P-D2). STANDS.

---

## §7 — What I did NOT find (nulls as evidence)

- **No stale-HIGH.** The F-001 code chain is byte-identical on origin/main; the branch does not remediate F-001's axis. The charge's headline hazard does not materialise.
- **No missed control** between mint and the asana write route (T2 probed own-eyes).
- **No false-negative in CF-1** (legacy_monolith correctly carries no asana; the widening catch is real-but-inert, correctly scoped with UV-P-C1).
- **No coercion escape** in LEG-D (no before-validator; pydantic 2.12.5 raises).
- **No overclaim to correct** on population=1 (already UV-P-C1) or on the runtime/source SDK split (already SH-2, both coordinate systems given).

---

## §8 — Disposition

| Item | Ruling |
|---|---|
| SH-1 | **DISCHARGED-CLEAN** on the F-001 code chain (six charge-named anchors byte-identical); **NARROWED** on the registry-count fact (main is ahead; NF-1 count stale) |
| T2 (end-to-end bypass) | **STANDS** |
| T3 (CF-1 population-of-one, inert) | **STANDS** (two-sided) |
| T4 (LEG-D refuted-by-accident) | **STANDS** |
| NF-1 "18 of 18" | **RECLASSIFY** asserted-fact → UV-P-bounded read-surface snapshot; property stands/strengthens |
| §1 ace/iris determinant, C.3 iris-lacks-asana | **STANDS on read surface; thin SH-1 residual** on origin/main (additive-only drift, not byte-confirmed under fence) |
| Overall recommendation (HIGH stands, not Critical) | **SURVIVES** |

**Not-Critical rationale re-tested and upheld:** exempt-token acquisition still requires the client secret (TB-4, `tokens.py` byte-identical); scope sets remain read-only with empty `authorized_organizations` (read-surface; additive drift does not change ace/iris); D5 300s TTL substantiated at `config.py:83` (byte-identical). None of the three Critical-triggers is met on the substrate of record.

**Consumer note (BR-6 rung discipline):** this critique is `STRUCTURALLY-VERIFIED` — static file:line + blob-SHA + compare metadata; **no runtime probe**. The dossier's UV-P-A1/A2/B1/C1/C2/C3/D1/D2/E1 remain open and are not discharged here. SH-1 is discharged to blob-SHA fidelity on the code anchors; the registry-count narrowing and the ace/iris origin/main byte-confirmation remain fetch-fenced. Do not upgrade to REALIZED-MECHANISM without the OpenFGA/task-definition/log probes the dossier enumerates.
