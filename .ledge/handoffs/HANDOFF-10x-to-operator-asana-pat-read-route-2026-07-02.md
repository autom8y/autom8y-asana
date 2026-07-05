---
type: handoff
artifact_subtype: 10x-dev-close
initiative: asana-cutover-readiness-credential-topology
handoff_type: execution
from_rite: 10x-dev
to: operator (rotate leaked PAT + merge + deploy) → iris (W-IRIS) → 10x-dev (W-REG-proper)
from_station: /qa GO (qa-adversary, disjoint)
created: 2026-07-02
status: proposed
rung: pre-deploy-construction-validated (GO; MODERATE; route NOT deployed; SCAR-REG-001 OPEN)
telos: root charge = .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md
---

# HANDOFF: 10x-dev (close) — token-safe GET /sections + W-REG join fix (PR #184)

> **Boundary**: 10x-dev BUILT + adversarially VALIDATED (**GO**) the FORK-R=REUSE read-route hardening
> + the W-REG join-logic fix. **PR #184 OPEN — NOT merged, NOT deployed.** Everything downstream
> (rotate the leaked PAT, merge, deploy, iris W-IRIS, W-REG-proper) is **user-sovereign**.
> SCAR-REG-001 stays **OPEN**; the 19 placeholder GIDs + all `VERIFY-BEFORE-PROD` markers are untouched.

## §1 · Delivered (PR #184 `feat/asana-pat-read-route-and-wreg`, off fresh origin/main; GO)
- **`51cc12fe`** — `GET /api/v1/projects/{gid}/sections` → JWT-only via `require_service_claims`; the plaintext-PAT mode is **impossible by construction**; PAT resolved server-side (brokered `_ARN`); H2 route pinned to project `1201081073731555`; `BotPATError`→503 fail-closed; H5/V6 caller-guard. All 7 hard-gates tested.
- **`90e61f2e`** — GATE-GAP-1: native Asana-PAT rule in `.gitleaks.toml` (two-sided verified).
- **`bd6adbc6`** — three-tier fail-closed W-REG join (`join_section_registry`) + `blocks_live_wiring`; **19 placeholders + `VERIFY-BEFORE-PROD` untouched** (diff-confirmed).
- **QA GO (disjoint):** P1 blast-radius **SAFE** (zero HTTP consumers of the endpoint fleet-wide, receipts); P2 no auth bypass; P3 allowlist airtight (traversal/encoding → 404, fetch never fires); P4 Tier-3 fail-closed; P5 teeth real (mutation-proven two-sided). Proof surface: 1577 passed, 0 regressions.

## §2 · HIGH out-of-band incident (surfaced by this PR's own new rule — action ASAP)
A **real native Asana PAT** `1/1200795353760666:8031…` (project `1200795353760666` — **DISTINCT** from the cutover project) is committed in `.claude/settings.local.json` at `15cffee1d7` (2025-12-17) + `525431de02` (2025-12-22), **reachable from origin/main history**. At HEAD the file is untracked+gitignored and the token absent from tracked files, but it persists in shared history. CI gitleaks is non-blocking (`|| true`, SARIF gated to public repos) so it will NOT turn CI red for this private repo. **→ ROTATE/REVOKE the PAT (security/user); then decide history-scrub vs `.gitleaksignore` fingerprint (post-rotation only).** Watch-registered in `.know/defer-watch.yaml` (`leaked-asana-pat-in-main-history-2025-12`).

## §3 · Downstream sequence (ALL user-sovereign)
1. **[HIGH, immediate]** Rotate the leaked PAT (§2).
2. **[LOW]** Regenerate `docs/api-reference/openapi.json` (JWT-only S2S + single-project scope; currently drifted) — `/build` or `/docs`.
3. **Merge PR #184.**
4. **Deploy** the hardened route (ECS/IaC).
5. **`/iris` W-IRIS** — live `GET /sections` receipt via the now-safe JWT route → `name → live-GID` map.
6. **`/10x` W-REG-proper** — replace the 19 GIDs (live-GID × monolith `BusinessUnits.SECTIONS` bucket), gated on the receipt PRESENT (shape PT-04). Closes SCAR-REG-001.

## §4 · Load-bearing constraints for W-REG-proper (from QA — do NOT skip)
- **MUST gate live-wiring on `blocks_live_wiring`/`blocking_findings`** — else the Tier-3 fail-closed guarantee is inert (`join_section_registry` has zero live callers today; the block is advisory-to-caller by design).
- **MUST wire `assert_no_plaintext_pat_in_caller` (`bot_pat.py:107`) into the W-IRIS caller startup** — else H5/V6 is inactive (no production call site yet).

## §5 · Rung (honest)
**pre-deploy-construction-validated (GO, MODERATE).** Route NOT deployed; **SCAR-REG-001 OPEN**; `verified_realized` HELD. Deploy / merge / rotation / the live section-GID fetch are user-sovereign. STRONG + closure require the live receipt + the 19-constant replacement (W-REG-proper) + a rite-disjoint attester.

*Artifacts: PR #184 · TDD `.ledge/specs/TDD-asana-pat-read-route-and-wreg.md` · ADR `.ledge/decisions/ADR-asana-pat-read-route-forkR-2026-07-02.md` · security handoff `.ledge/handoffs/HANDOFF-security-to-operator-asana-pat-read-route-2026-07-02.md`.*
