---
type: action-receipt
artifact_subtype: iris-attestation-receipt
initiative: asana-cutover-readiness-credential-topology
leg: W-IRIS
finding: SCAR-REG-001
attester: iris (operational bot)
created: 2026-07-02
disposition: 200-SUCCESS
rung: proven-by-live-receipt
gates_next: "/10x W-REG-proper (19-GID replacement); SCAR-REG-001 stays OPEN until /10x lands"
---

# W-IRIS Receipt — live section-GID map for project 1201081073731555

> **STATUS: 200-SUCCESS.** Live authenticated `GET /sections` obtained over the
> deployed JWT-only hardened route. This receipt is the **W-REG denominator** for
> `/10x`. READ-ONLY: no Asana WRITE, no plaintext-PAT handled, no mutation.

## §1 · Action receipt (the 200)

| field | value |
|-------|-------|
| endpoint | `https://asana.api.autom8y.io/api/v1/projects/1201081073731555/sections?limit=100` |
| http-status | **200** |
| timestamp | `2026-07-02T11:04:32.099917Z` (re-read verify @ `2026-07-02T11:06:20.638783Z` — identical map) |
| transaction-id | app `meta.request_id="unknown"` (RequestIDMiddleware unpopulated on S2S path — observability note, §6); server `meta.timestamp` is the transaction stamp |
| section_count | **17** (single page; `pagination.has_more=false`) |
| auth | S2S JWT, `token_type=service`, `aud=https://api.autom8y.io`, `iss=auth.api.autom8y.io`, `sub=00047e2c-6885-4053-96ef-be9a36e4af35`, TTL=300s; token sha256:`b17a276cb32b`… (never materialized in plaintext) |
| mint path | `POST https://auth.api.autom8y.io/tokens/exchange-business` (legacy TEB, Basic auth) — canonical `autom8y_auth.TokenManager` wire format |
| mint identity | ServiceAccount `sa_cbeff2956b20ef5e43a8031c7ab3f53c` (insights-export exemplar) + key `autom8y/auth/service-api-keys/asana-insights-export` (secret sha256:`d76e8befd13e`…) |
| brokered Asana PAT | resolved SERVER-SIDE via `get_bot_pat()` / `ASANA_PAT_ARN`; iris never handled it |

## §2 · Live name → live-GID map (the denominator, ALL 17)

| # | live section name | live GID | resource_type |
|---|-------------------|----------|---------------|
| 1 | Templates | `1201122816966634` | section |
| 2 | Unengaged | `1201239149602679` | section |
| 3 | Engaged | `1201081073731561` | section |
| 4 | Scheduled | `1201081073731562` | section |
| 5 | Delayed | `1201081073731567` | section |
| 6 | Next Steps | `1201081073731564` | section |
| 7 | Onboarding | `1201081073731565` | section |
| 8 | Implementing | `1201081073731566` | section |
| 9 | Preview | `1201081073731569` | section |
| 10 | Month 1 | `1201081073731570` | section |
| 11 | Consulting | `1201081073731568` | section |
| 12 | Active | `1201081073731571` | section |
| 13 | Account Review | `1201081073731572` | section |
| 14 | Account Error | `1201081073731573` | section |
| 15 | Paused | `1201081073731574` | section |
| 16 | Cancelled | `1201081073731575` | section |
| 17 | No Start | `1201087333420106` | section |

## §3 · DIFF vs the 19 frozen placeholders (`section_registry.py:105`, `:137-155`)

**Verdict: MISMATCH — 19/19 placeholder GIDs are WRONG.** Every sequential
placeholder (…600–603 EXCLUDED, …610–624 UNIT) is fabricated and matches NO live
GID. SCAR-REG-001 confirmed decisively: had these shipped, every section match
would have silently failed.

### (a) placeholder-GID → live-GID (all 19 MISMATCH)
EXCLUDED (`:105`):
- `Templates`      `1201081073731600` → live `1201122816966634`
- `Next Steps`     `1201081073731601` → live `1201081073731564`
- `Account Review` `1201081073731602` → live `1201081073731572`
- `Account Error`  `1201081073731603` → live `1201081073731573`

UNIT (`:137-155`):
- `Month 1`      `1201081073731610` → live `1201081073731570`
- `Consulting`   `1201081073731611` → live `1201081073731568`
- `Active`       `1201081073731612` → live `1201081073731571`
- `Onboarding`   `1201081073731613` → live `1201081073731565`
- `Implementing` `1201081073731614` → live `1201081073731566`
- `Delayed`      `1201081073731615` → live `1201081073731567`
- `Preview`      `1201081073731616` → live `1201081073731569`
- `Engaged`      `1201081073731617` → live `1201081073731561`
- `Scheduled`    `1201081073731618` → live `1201081073731562`
- `Unengaged`    `1201081073731619` → live `1201239149602679`
- `Paused`       `1201081073731620` → live `1201081073731574`
- `Cancelled`    `1201081073731621` → live `1201081073731575`
- `No Start`     `1201081073731622` → live `1201087333420106`
- `Account Review` `1201081073731623` → live `1201081073731572`  (dup — see §4)
- `Account Error`  `1201081073731624` → live `1201081073731573`  (dup — see §4)

### (b) expected placeholder names missing from live
**NONE.** All 17 distinct placeholder names have a live match.

### (c) live names not in EXCLUDED_NAMES ∪ UNIT names (Tier-3 `live_name_no_bucket`)
**NONE.** No live section is unknown to both sets → **zero blocking findings**.

## §4 · Dual-anchor JOIN preview (live-GID × monolith name→bucket)

Anchoring live GIDs to the monolith `BusinessUnits.SECTIONS` taxonomy
(`…/business_units/main.py:18-39`, READ-only) via `join_section_registry`
(Tier-1 local-exclusion-first). **This is a preview for /10x — NOT the
replacement.** `blocks_live_wiring = False`.

**excluded_section_gids (4)** — the 4 `EXCLUDED_SECTION_NAMES`:
- `Templates`      → `1201122816966634`
- `Next Steps`     → `1201081073731564`
- `Account Review` → `1201081073731572`
- `Account Error`  → `1201081073731573`

**unit_section_gids (13)**:
- `Unengaged` `1201239149602679` · `Engaged` `1201081073731561` · `Scheduled` `1201081073731562` · `Delayed` `1201081073731567` · `Onboarding` `1201081073731565` · `Implementing` `1201081073731566` · `Preview` `1201081073731569` · `Month 1` `1201081073731570` · `Consulting` `1201081073731568` · `Active` `1201081073731571` · `Paused` `1201081073731574` · `Cancelled` `1201081073731575` · `No Start` `1201087333420106`

**findings (3, all non-blocking `taxonomy_divergence`)**: `Next Steps`,
`Account Review`, `Account Error` present only in in-code `EXCLUDED_SECTION_NAMES`,
not in the monolith `ignore` set. Surfaced, NOT auto-reconciled (R-REG-4).

### §4.1 · Architect-flagged Account Review / Account Error double-membership — RESOLVED
The placeholder sets list `Account Review` + `Account Error` in **BOTH** EXCLUDED
(…602/…603) **and** UNIT (…623/…624) with different fabricated GIDs. Live truth:
each resolves to a **single** GID — `Account Review=1201081073731572`,
`Account Error=1201081073731573`. The Tier-1 join routes BOTH to **excluded**
(local exclusion wins, LBC-004). The monolith taxonomy does not bucket them as
units, so **no `double_membership` finding fires** — the exclusion is uncontested.
Net effect for /10x: the UNIT set shrinks **15 → 13** (the 2 dups leave UNIT and
live only in EXCLUDED); total live = **4 excluded + 13 unit = 17**.

## §5 · Procession trace (propose → emit → verify → audit)
- **propose**: scope = autom8y × asana-API × project 1201081073731555; action = idempotent READ (GET); success = 200 + section map. No ambiguity.
- **emit**: minted S2S JWT (TEB, `sa_cbeff…`) → 200; fired `GET /sections` → 200, 17 sections.
- **verify**: re-read @ 11:06:20Z returned the identical 17-map (idempotency confirmed, MM-003); 19/19 MISMATCH; 0 Tier-3 blocking.
- **audit**: §6.

## §6 · Guardrail attestation + honest-rung
- **G-SECRET honored**: plaintext ASANA_PAT never read/printed (a bare `ASANA_PAT` WAS present in the caller env — the `assert_no_plaintext_pat_in_caller` `bot_pat.py:107` trigger condition; NOT used, NOT materialized); minted JWT + client_secret referenced by sha256-prefix only. Section GIDs surfaced (non-secret Asana object IDs).
- **G-READONLY honored**: GET only; zero WRITE to Asana; zero credential/IAM mutation.
- **G-RUNG honored**: CAP = this receipt (route-reachable + name→GID map). iris did NOT replace the 19 constants, did NOT deploy, did NOT merge. **SCAR-REG-001 stays OPEN** until /10x lands W-REG.
- **PROVES**: (1) the hardened JWT-only route is LIVE + reachable + auth-enforcing (definitive route-reachability proof closing the un-attested PROD-HEALTHY gap for THIS route, per Pythia's ruling); (2) the W-REG denominator (17 name→live-GID pairs + dual-anchor join, 0 blocking).
- **REMAINS**: /10x W-REG replaces the 19 placeholders with the joined live GIDs (4 excluded + 13 unit), removes the 5 VERIFY-BEFORE-PROD markers, wires the fail-closed guard + `assert_no_plaintext_pat_in_caller`, RED-first two-sided wrong-bucket fixture, rite-disjoint critic → SCAR-REG-001 CLOSED. The live Asana section-GID WRITE stays user-sovereign (untouched).

## §7 · Ecosystem observation (NOT blocking this receipt — for audit/sre)
The deployed ECS `autom8y-asana-service:592` carries `SERVICE_CLIENT_ID=asana`
(a bare service name, NOT a valid `sa_`/`client_`-prefixed ServiceAccount id).
A TEB mint with (`asana`, `autom8y/auth/service-api-keys/asana-service`) is
rejected by the auth service: `401 AUTH-TEB-001 Invalid service account
credentials (sa_id_prefix=asana)`. The insights-export Lambda's valid
`sa_cbeff…` identity was required to mint. This is a plausible contributor to the
metrics-export SEAL / S2S dark-export regression (#927) and is routed to sre/10x
as a distinct finding — it did NOT block this READ (a valid fleet identity exists).
