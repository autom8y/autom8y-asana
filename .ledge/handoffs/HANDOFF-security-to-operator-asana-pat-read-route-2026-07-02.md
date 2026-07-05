---
type: handoff
artifact_subtype: security-close
initiative: asana-cutover-readiness-credential-topology
handoff_type: execution
from_rite: security
to: operator (FORK-R select + construct) → /iris (W-IRIS) → /10x (W-REG)
from_station: S6-SEAM (main-thread dispatcher, Potnia-gated DAG S0→S4)
created: 2026-07-02
status: proposed
rung: designed+gated (MODERATE; teeth-proven on paper + local harness; route NOT constructed)
telos: .know/telos/asana-readiness-hygiene.md (sibling) · root charge = .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md
---

# HANDOFF: security (close) — asana-cutover-readiness · token-safe ASANA_PAT READ route

> **Boundary**: security **designed + gated** (teeth-proven) the token-safe ASANA_PAT read
> route — the single credential seam gating **W-IRIS → W-REG → the 19 SCAR-REG-001 section-GIDs
> → safe cutover**. The route is **NOT constructed, NOT minted, NOT deployed**. Which option to
> materialize (**FORK-R**) and its construction are **user-sovereign**. Downstream: user constructs →
> `/iris` (live receipt) → `/10x` (W-REG). This finishes a design leg of the ORIGINAL cutover
> charge — it is not a new credential crusade.

## §1 · What security PROVED (Gate-C — per-item receipts inline; `.sos/wip/security/*` are gitignored WIP)

| Leg | Receipt (verbatim anchor) | Verdict |
|---|---|---|
| **Premise (S0-PV)** | 5/5 CONFIRMED. `section_registry.py:99` `VERIFY-BEFORE-PROD (SCAR-REG-001)` + 19 sequential placeholders (EXCLUDED `…600-603` @:105 · UNIT `…610-624` @:137-155). #148 `9b698280`/#149 `f795d7dc`/#135 `5e31bb48` all `git branch --contains → main`. | **GREEN** |
| **Residence (S0/S1)** | PAT in Secrets Manager `autom8y/asana/asana-pat` (ARN `…qJ5AVX`, prod/terraform, **rotation DISABLED**, no resource-policy). Lambda reads by **`ASANA_PAT_ARN`** ref (Parameters-and-Secrets ext + scoped exec role) on cache-warmer/insights-export/unit-reconciliation. Interactive/CLI has **no brokered read** → `--provider env` plaintext (`bot_pat.py:70`, `service_token.py:43-56`). No PAT value ever read (describe/list only; `jq keys`/ARN-filter containment held). | **GREEN** |
| **FORK-T** | **HIT (partial)** — the safe `_ARN`-first brokered read is proven+live for the **Lambda** topology; the **interactive/W-IRIS** path is uncovered (plaintext fallback). ⇒ S2 = harden-and-extend, not greenfield. | resolved |
| **Enumeration (S1)** | Matrix: the *same* PAT as two rows — Row A Lambda-ext (**Moderate**, needs RCE/mem-dump) vs Row B interactive-plaintext (**Important, top-of-queue**, the live cutover path); identical ultimate blast-radius (full-scope × rotation-off = indefinite validity). `-thnc` classified describe-only = 2nd human personal-identity PAT, **grep-zero consumers**, LastAccessed 2026-06-09 → DEFER-watch. | **GREEN** |
| **Design (S2)** | ≥3 **custody-distinct** options (axis = PAT-custody by interactive caller); 4th declined (non-distinct). **Recommended (b)**: read-only proxy exposing ONLY `GET /sections` — caller never touches the PAT; discharges F3 (silent fail-open) + F4 (over-privilege) *architecturally*. RECOMMEND-not-select (FORK-R unresolved). | **GREEN** |
| **Teeth (S3)** | Two-sided, non-theatrical. **Detection**: real `gitleaks 8.30.1` + real `.gitleaks.toml` → planted **fake** decoy (sha256 `e1ef2f65…`) in non-allowlisted sink = **RED exit 1** (rule `asana-client-secret`); clean section-JSON = **GREEN exit 0**. **Containment**: allowlist harness refused `POST/PUT/DELETE` + neutralized `X-HTTP-Method-Override: DELETE` (0 write egress); `GET /sections` passed. Real PAT never touched. | **GREEN (teeth PASS)** |
| **Certification (S4)** | Disjoint critic (⊥ S2 role, ⊥ S0 fresh-context) re-derived every claim (re-ran gitleaks both sides, re-grepped 19 GIDs + `-thnc` grep-zero, re-read `bot_pat.py:69-72`). All 8 gates GREEN. **CERTIFY-WITH-FLAGS**, capped **MODERATE** (self-ref). | **CERTIFY-WITH-FLAGS** |

## §2 · Rung ladder (honest — never rounded up)

`authored < emitting < alerting < proven < merged < live < protecting-prod`

Reached: **designed+gated** (route designed; its gate's teeth proven on paper + local harness). **NOT** constructed / minted / deployed / proven-in-prod. **SCAR-REG-001 stays OPEN.** `verified_realized` = **HELD** (cutover value unrealized). Evidence grade **MODERATE** — a within-rite critic cannot self-certify STRONG; STRONG requires a rite-disjoint attester (e.g. eunomia) **plus** construction evidence (deployed proxy, H1–H4 hard-gates satisfied, GATE-GAP-1 rule landed, teeth re-fired against the *deployed* proxy).

## §3 · Operator levers (FORK-R — user-sovereign; in sequence)

1. **SELECT + CONSTRUCT the read-route** (recommended **(b)**; (a) is the lighter runner-up; (c2) matches (b)'s containment at higher infra cost). Construction per option (you run these; security ran none):
   - **(b)** deploy a single-route read-only proxy (Lambda function-URL or ECS route) reusing the Row-A brokered read + scoped exec role; wire caller auth; re-point W-IRIS. `terraform apply` (or `aws lambda create-function` + `create-function-url-config`).
   - **(a)** scoped IAM role + trust policy (`GetSecretValue` on the one ARN) → `aws sts assume-role` → export `ASANA_PAT_ARN` → fail-closed wrapper.
   - **(c)** SSO/OIDC permission-set binding the section-read capability (c2→proxy, c1→role) → `aws sso login`.
   - **OUT OF BOUNDS (any option):** minting a NEW scoped Asana token — that is a user-sovereign FORK-R sub-lever + the forbidden crusade. All three route the *existing* PAT.
2. **`/iris` (W-IRIS)** — live `GET /projects/1201081073731555/sections` receipt, **READ-only**, diff vs the 19 frozen GIDs. (The live Asana WRITE stays user-sovereign.)
3. **`/10x` (W-REG)** — replace the 19 constants = **live-GID × monolith `BusinessUnits.SECTIONS` name→bucket** taxonomy; RED-first misroute fixture per shape §5. Closes SCAR-REG-001.

## §4 · Construction-time HARD-GATE obligations (from S4 — MUST ride with construction; do not silently skip)

| ID | Sev | Obligation |
|---|---|---|
| **H1** | Critical-if-misconfigured | function-URL `AuthType: AWS_IAM` + build-fail assertion if unauthenticated (else anonymous PAT oracle) |
| **H2** | Moderate | pin route to the 19-GID/project allowlist + integer-validate `{gid}` (closes BOLA/IDOR) |
| **H3** | Moderate | ignore method-override headers; exact-match normalized path; build outbound URL server-side |
| **H4** | Moderate | never log `Authorization`/PAT; disable trace-header capture; inject via `_ARN`, never bare `ASANA_PAT` |
| **H5/V6** | Moderate | caller-startup guard asserting bare `ASANA_PAT` unset; fail-closed the resolver for absent-ARN interactive context (`bot_pat.py:69-72` fallback still ships in the caller image) |
| **GATE-GAP-1** | Moderate (gate) | add a native Asana-PAT rule to `.gitleaks.toml` — the GREEN teeth are **not sound for native leaks** until this lands (`.gitleaks.toml` is blind to `1/gid:hex` / `2/…:hex`) |
| **H6** | Low→Moderate | short-lived caller identity (natural bridge to option c2) |

## §5 · DEFER register (watch-registered in `.know/defer-watch.yaml` — do NOT expand)

`credential-topology-nightly-smoke-iam-read-grant` (→ /sre) · `credential-topology-fleet-schema-governance-permissions` (→ /security; drift-guard candidate) · `asana-pat-thnc-sibling-secret-disposition` (→ /security/owner) · `asana-pat-rotation-disabled-indefinite-validity` (→ /security + lifecycle owner) · `gitleaks-native-asana-pat-rule-gap` (→ /security; also §4). The other two credential-topology faces + `-thnc` + rotation stay fenced — no crusade.

## §6 · SCAR status (recorded, not expanded — PV re-confirmed as current, no catalog churn)

- **SCAR-REG-001** — still **OPEN** (19 placeholders at `section_registry.py:105,137-155`). **Forward-path unblocked**: the token-safe read-route is now designed+gated → construct (FORK-R) → `/iris` → `/10x` closes it. This is the first movement of SCAR-REG-001 toward `proven` since the shape was authored 2026-06-24.
- **SCAR-IDEM-001** — PV re-confirmed at `api/middleware/idempotency.py:719` (unchanged; #149 `f795d7dc` landed finalize-failure S2S propagation). Bookkeeping only — no expansion (H-2 is off this sprint's blast radius).

## §7 · Artifacts (ephemeral WIP — gitignored `.sos/*`; receipts inlined above for durability)

`.sos/wip/security/{S1-ENUM,S2-ROUTE-DESIGN,S3-ADVERSARIAL,S4-REVIEW-VERDICT}-*.md` · `.know/defer-watch.yaml` (+5 rows).

---

*Security close. Route designed+gated (MODERATE, teeth-proven); SCAR-REG-001 OPEN; verified_realized HELD.
FORK-R selection + construction + `/iris` + `/10x` + any merge are the operator's. Do NOT dispatch iris/10x
specialists from security — the operator routes via construction → `/iris` → `/10x`.*
