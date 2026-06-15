---
type: decision
subtype: clear-readiness-bundle
status: accepted
title: "CLEAR-READINESS BUNDLE — the 2026-06-18 operator runbook (sentinel ritual → clear-day acceptance → eunomia STRONG → the unlock chain)"
date: 2026-06-11
clock_state: RUNNING
anchor_utc: 2026-06-11T15:24:21Z
target_clear_utc: 2026-06-18T15:24:21Z
evidence_grade: MODERATE   # sre authoring sre's own readiness (G-CRITIC self-cap). THE STRONG OVER THE SOAK IS EUNOMIA'S — rite-disjoint, simultaneous five-signal, AT CLEAR. This bundle prepares that dispatch; it cannot substitute for it.
rung: clear-readiness-AUTHORED (on a day-1-attested clock)   # NOT soak-CLEARED — that belongs to the clock + eunomia on 06-18
governing_records:
  - .ledge/decisions/IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md         # the clock
  - .ledge/decisions/SOAK-SENTINEL-PROTOCOL-telos-soak-2026-06-11.md           # the daily ritual
  - .ledge/decisions/SOAK-DAY-1-ATTESTATION-telos-soak-2026-06-11.md           # day 1/7 GREEN
  - .ledge/specs/CHAOS-DESIGN-post-soak-clear-blast-2026-06-11.md              # clear-day acceptance + post-clear blast
  - .ledge/reviews/OBS-EMF-FLAG-DECISION-SURFACE-receiver-sli-2026-06-11.md    # the EMF ruling input
  - .ledge/decisions/OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md    # RULING 3 (FM-5 post-soak)
---

# CLEAR-READINESS BUNDLE — what happens between now and 06-18, and the exact 06-18 sequence

## A. The daily ritual (days 2–7, 06-12 → 06-18)
One attestation per soak-day per `SOAK-SENTINEL-PROTOCOL-telos-soak-2026-06-11.md` — four receipt
sections (deploy-freeze · band content · alarm states · AC-6 cadence), RESET-vs-LOG by the codified
law, the iris pipe-smoke as the counter-absence instrument. LOG-class rulings are sre-delegated;
RESET-class are recommended-with-receipt, declared only by the operator. **The freeze:** no merge to
autom8y-asana main (Trap 6 — the merge IS the deploy); autom8y merges touching
`terraform/services/asana/**` fire `service-terraform.yml` push→Apply which PARKS at the
operator-held `production` env gate (reviewer: tomtenuta) — not silent, but a live-IAM mutation if
approved: leave un-approved until post-soak.

## B. The 06-18 clear-day sequence (in order; each step gates the next)
1. **Day-7 attestation + window audit** — the day-7 record per the protocol, PLUS the window check:
   asana main STILL `49099b12` (or every newer sha operator-authorized + src-identity-proven), ECS
   sole `:511` the whole window, no RESET-class entry in any day-N record.
2. **Clear-day re-game-day** (operator GO) — EXP-1 per `CHAOS-DESIGN-post-soak-clear-blast §4`
   (capture-first → one-lane revoke → Event-invoke unit warm → CONTENT at BOTH altitudes →
   finally-restore → Fork-2 re-heal). Read-only + IAM-revoke-scoped: does NOT reset the clock
   (the 06-11 precedent); a DEPLOY to fix a RED does.
3. **eunomia STRONG dispatch** (rite switch — the operator restarts CC into eunomia/framing; the
   seam HANDOFF `HANDOFF-sre-to-eunomia-soak-sentinel-clear-readiness-2026-06-11.md` is its input).
   **RATIFIED 2026-06-11 by eunomia from the attester's seat** —
   `EUNOMIA-RATIFIED-STRONG-DISPATCH-SPEC-soak-clear-2026-06-18-2026-06-11.md` SUPERSEDES the
   sketch below where they differ (adds: window-integrity via ECS event-diff, first-party
   gun/coherent, worktree preflight, the S2/S3-deferred verdict-scope pre-commitment, and the
   standing-evidence carry from the day-1 interim corroboration).
   The dispatch must demand: independent re-derivation (never the producer's numbers) of (i) the
   full 7-day attestation chain (re-pull spot receipts), (ii) the band by fresh parquet counts,
   (iii) the AC-6 7-day cadence from AMP query_range, (iv) alarm-state history, (v) the
   **simultaneous five-signal** ruling: S1 active_mrr 62-class stable · S2/S3 SEAM-2
   deferred-not-observed (rule explicitly on whether deferred signals cap the verdict) · S4 the
   named unit-floor calibration exception · S5 eunomia itself. Verdict vocabulary:
   **soak-CLEARED(STRONG) / soak-CLEARED-WITH-CONDITIONS / RESET-recommended** — no adjectives.
4. **The unlock chain** (each on its own GREEN receipt, never speculatively):
   a. **SEAM-2 rebind** (C1/C2/C3, cross-repo monolith): offer substrate READY (62/$79,485);
      Consumer-2 is null-gated on unit economics; the fallback-flip is a CODE change, not env.
   b. **CR-3 Stage-B → Secret-2** (operator, IRREVERSIBLE — sequence per the CR-3 records).
   c. **FM-5 /frame** → 10x-dev/framing per RULING 3 (`SPEC-fm5-consumer-column-declaration-shape`
      is the input; derivation gates on #114).
5. **The held-merge + post-soak deploy bundle** — the FIRST deliberate post-soak asana deploy
   should carry (one deploy, one reset-free bundle, then re-anchor whatever soak follows):
   - **PR #130 merge** (canary section-arm selector fix, AUTHORED-HELD):
     `env -u GITHUB_TOKEN gh api -X PUT repos/autom8y/autom8y-asana/pulls/130/merge -f merge_method=squash`
   - **EMF flag** ONLY as the conditional bundle per the S2 ruling (CW sink + consumer alarm first;
     bare flip rejected — it writes to a namespace with ZERO consumers today).
   - **Floor codification** (#58 / SRE-N1): monorepo `main.tf:158-159` still declares cpu=1024/mem=2048
     vs live 2048/8192 — latent TF-drift (three deploys today preserved the floor empirically, but
     codify before it bites).
   - **β-3 IaC codification** — routed to the `autom8y/a8` `service-stateless` module repo (S3
     finding: NO in-repo source lever in autom8y; the asana TF exposes no policy-override input).
   - Node20 deploy-coupled residue (48 pin-lines incl. `satellite-dispatch.yml` repository-dispatch v3).

## C. DEFER register (updated this procession)
| # | Item | State / route |
|---|---|---|
| 6 | β-2/β-3 IaC drift-lock | **PARTIALLY CLOSED**: 3 warmer policies byte-CONVERGED source≡live (no-op receipt); β-3 ECS task-s3 → **re-routed to the a8 service-stateless module repo** (no autom8y lever) |
| 10 | monolith AC-6 cadence gap | **CLOSED** — organic resume 16:30Z=98.8; gap = deploy-boundary counter-reset artifact (S2 appendix) |
| 11 | `RECEIVER_SLI_EMF_ENABLED` | **RULED (recommendation)**: leave-dark-keep-optionality; flip only as the post-soak conditional bundle |
| 12 | canary section-arm fix | **AUTHORED-HELD**: asana PR #130, scripts-only, auto-merge null; merge = operator post-soak |
| 13 | gen.json guard in CI | **CLOSED — MERGED-AND-ENFORCING**: autom8y #515 → `c8c397f2`, check live ("Vendored namespaces.gen.json matches canonical") |
| NEW-15 | **AC-6 domain counter is alert-orphaned** — FastBurn/SlowBurn/HeartbeatAbsent all consume the platform HTTP histogram, NOT `autom8y_asana_receiver_query_outcome_total`; its only guardian is the manual sentinel | post-soak observability pass: an AMP alert on the domain counter's burst cadence |
| NEW-16 | TF floor drift `main.tf:158-159` (1024/2048 vs live 2048/8192) | = #58 SRE-N1, fold into the post-soak deploy bundle |
| carried | FM-5 (RULING 3) · SEAM-2 · Stage-B · UK-2 · #127 qa obs ×2 · CHANGE-001 · fleet-export N≥2 · 128k legacy cache · #97 · Node20 deploy-coupled + 9-satellite propagation · legacy entity-blind `metrics` CLI sighting (day-1 LOG) | watch-registered |

## D. What this bundle is NOT
Not a clearance. Not a STRONG. The clock clears itself on 06-18T15:24:21Z only if the daily
attestations stay clean; eunomia alone grades the window STRONG; the telos five-signal stays
NOT-verified-realized until SEAM-2 + AC-6-sustained + valid-clear + fallback-flip all land.
