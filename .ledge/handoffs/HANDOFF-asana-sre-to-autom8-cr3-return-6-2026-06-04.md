---
type: handoff
status: draft
handoff_status: pending
source_rite: sre
target_rite: 10x-dev
from_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
to_repo: /Users/tomtenuta/Code/autom8
created: 2026-06-04
in_reply_to: HANDOFF-autom8-to-asana-sre-cr3-consumer-return-3-2026-06-04
initiative: cr3-clean-break-cutover
subject: CR-3 RETURN-6 — IC-GATE-7 = GO (operator/IC signed) → consumer AUTHORIZED to fire the unified project-first cutover (#55); rollback levers + soak watch + Stage-B/Secret-2 sequencing stated
ledge_status: AUTHORED-and-delivered
reversibility: READ-ONLY AUTHORSHIP — this artifact mutates nothing; it AUTHORIZES an irreversible bundle it does not fire. Cutover steps 1-2 reversible via the tested PRE-SB-1 flag-OFF lever; step 3 (Secret-2 decommission) IRREVERSIBLE, protected by sequencing (last).
evidence_ceiling: STRONG  # STRONG for the §D both-arms PASS (rite-disjoint live-AWS chaos verdict + disjoint observability re-read, §8.2/§9.2). MODERATE elsewhere (SRE-authored synthesis). The IC-GATE-7 = GO decision is the operator/IC's, recorded here.
discipline: This artifact AUTHORIZES but does NOT itself fire the cutover. The irreversible fire (#55 merge / Stage-B / Secret-2 decommission) is the consumer/IC's deliberate action. Reversible/read-only authorship by the SRE side. Secrets redacted (names/scope only). Verify-at-source.
---

# HANDOFF — autom8y-asana (SRE) → autom8 (consumer): CR-3 RETURN-6 — IC-GATE-7 GO → fire the unified project-first cutover

> In reply to your RETURN-3 (IC-GATE-7 staged, both halves green). The operator/IC has **signed off GO** on
> IC-GATE-7. Both arms cleared §D on a live SLI (rite-disjoint, disjoint-verified). **You (the consumer) are
> AUTHORIZED to fire the unified project-first cutover** per the sequence below. This handoff AUTHORIZES; it does
> **not** fire anything. The irreversible merge of #55 is yours/the IC's deliberate action — do not read this as
> the SRE side firing or instructing the producer to merge #55.

## §0. DECISION — IC-GATE-7 = GO

**IC-GATE-7 is signed off GO by the operator/IC.** Both halves are green and both arms cleared §D:

- **Chaos half — both arms §D PASS, on a live SLI, rite-disjoint-verified.**
  - **PROJECT 480/480 = 100.0%** (re-confirm; server_error series provably absent fleet-wide); `data_2xx=480`,
    `content_violations=0`; CPU 4-signal clean (peak ~12% / max ~18%, semaphore 4/0/0).
  - **SECTION 484/484 = 100.0%** (new arm, serve-stale knob=3000); **`capacity_502=0` dispositive (verified 3
    ways)**; `serving_stale_total{section}=458` genuinely exercised (all serves in the (900s,1800s] staleness
    band, ≤3000s ceiling, **zero breach**) — true LKG, not fresh-masquerade.
  - **Disjoint corroboration (the STRONG-lift):** a rite-disjoint observability re-read independently re-queried
    live AMP/CloudWatch and CONFIRMED every dispositive number at source, **zero mismatch, zero unreadable**;
    process did not restart; counters empty pre-load → minted real child series under the run (anti-theater held).
    Source: `CR3-SRE-PHASE-RESCOPED-D-VERDICT-2026-06-04.md` §8.2 / §9.2; raw capture
    `.sos/wip/chaos/crg3_dual_arm_raw_capture.json`.
- **Consumer half — confirmed.** QA-green (249 passed, ruff clean), resolver-auth contract suite 12/12, content-
  binding parity STRONG-PASS, **PRE-SB-1** Section rollback-lever test 2/2 (commit `14586df8`) — RETURN-3 §4/§5.
- **CQ-RETURN-3 = (a) accept-interim** + **UV-P #2 = all-or-nothing flag** (RETURN-3 §2/§3): 576s section freshness
  is NOT load-bearing for offer-join; both arms ride serve-stale together → a **UNIFIED both-arms cut is sufficient**
  (no arm-granular work required).

**→ The consumer is AUTHORIZED to fire the project-first cutover.** Evidence ceiling: **STRONG** for the §D both-arms
PASS (rite-disjoint live measurement); MODERATE for the surrounding SRE-authored synthesis. The GO decision itself is
the operator/IC's, recorded here — this artifact does not make it.

## §1. What YOU (the consumer) fire — in sequence

> **RE-BASELINED 2026-06-05** (per `cr3-cutover-qa-validation-2026-06-05.md`) — **STATUS:** #55 is **MERGED 2026-06-04**
> (`merged_at 2026-06-04T12:25:08Z`, merge_commit `aba7b93f`; also landed via #58 → origin/main HEAD `d7c0b1f4`) **but
> NOT DEPLOYED** — `monolith-prod` runs the **May-31 image** (ECR `autom8_monolith:prod` pushedAt 2026-05-31; task-def
> `:382`, deployment updatedAt 2026-05-31, ndeploys=1) and still authenticates via **Secret-2**. **→ the cutover is NOT
> live; the 7-day soak has NOT started.** "AUTHORIZED→merged" ≠ "deployed→live-verified→soaking." The steps below are
> RE-BASELINED accordingly: the real next action is **deploy the post-#55 image**, then live-verify, then soak.

> Authoritative sequence per `CR3-IC-GATE-7-LAND-PASS-2026-06-04.md` §2 and `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md`
> step-j. The all-or-nothing flag is **sufficient** for a unified both-arms cut because BOTH arms PASS §D.

1. **Merge + DEPLOY #55 — the both-arms repoint** `[merge IRREVERSIBLE; cutover begins only on DEPLOY]`
   Source receipt at authoring (REST, `gh api repos/autom8y/autom8/pulls/55`, pre-merge 2026-06-04):
   state `OPEN`, mergeable `clean`, merged `false`, head `feat/cr3-consumer-h2-cred-repoint` @
   `09e0f64b270fc504b9f5d2ce57d32afd41347fde`, base `main`,
   title *"feat(cr3): H-2 Section forced-fallback flag-parity + repoint resolver secret to authoritative store"*.
   **[RE-BASELINED — #55 has since MERGED 2026-06-04 but is NOT deployed; see §1 STATUS above.]**
   **CORRECTION (DOC DEFECT — the prior "flag flip" wording was FALSE):** #55 does **NOT** flip the global
   `satellite_get_df_enabled`. That flag was **ALREADY `bool = True`** in the parent (`config/satellite_config.py:175`),
   so the PROJECT arm was already routing once deployed — the merge commit makes ZERO change to the flag default. #55's
   real runtime delta is **(a)** SECTION forced-fallback **flag-parity** (`section/main.py:679` `if _flag_enabled is
   False` — the section arm now honors flag-OFF for rollback, matching project) **and (b)** the resolver-secret repoint
   **Secret-2 → Secret-1** (`autom8y/asana-dataframe-resolver`, JSON-envelope parse). **Pre-cutover gate (NOT yet
   performed — it requires the DEPLOY, not the merge):** consumer QA-adversary re-gate green on `main` + live monolith
   auth path fetches **Secret 1** (HTTP 200), not Secret 2.

   > **INERT-REPOINT SPOF (the crux — `cr3-cutover-qa-validation-2026-06-05.md` MAJOR finding):** the (b) repoint can be
   > **silently neutered** on deploy. `config/satellite_config.py:384` reads `os.environ.get("ASANA_RESOLVER_CLIENT_SECRET")`
   > FIRST and only runtime-fetches the authoritative Secret-1 `if not client_secret`. The `Dockerfile` `COPY .env ./`
   > bakes the build-context `.env` into the image; IF that baked `.env` sets `ASANA_RESOLVER_CLIENT_SECRET` (loaded into
   > `os.environ` at runtime), the Secret-1 fetch is short-circuited and auth stays on the baked/Secret-2 value → #55's
   > repoint is **INERT**. `.env` is gitignored, so its prod contents are unverifiable from the repo. This SPOF is being
   > made **robustly authoritative PR-ONLY this sprint** (`cr3-spof-rebaseline`), without breaking the local-dev override
   > or the fail-safe-to-legacy path.

2. **Deploy → live-verify → confirm both arms → THEN soak** (CORRECTED completion sequence) `[soak starts LAST]`
   The merge alone did **not** cut over; the prior "enter soak the moment #55 is live" wording assumed a deploy that
   has not happened. Corrected completion is: **(i) deploy the post-#55 monolith image to `monolith-prod`** (confirm the
   running digest is post-2026-06-04); **(ii) live-verify the repoint is effective** — monolith auth path on **Secret-1
   (HTTP 200)**, NOT Secret-2, and confirm no baked `ASANA_RESOLVER_CLIENT_SECRET` in the running container env
   (name-only) — this is the INERT-REPOINT gate from step 1; if inert, the SPOF fix lands first; **(iii) confirm BOTH
   arms route** to the receiver (project + section `/v1/query`); **(iv) THEN** enter the 7-day S7 soak: **PROJECT at
   production rate, SECTION on LKG/low-traffic** (serve-stale knob=3000). The SRE side WATCHES the soak — see §3 and the
   `soak_watch_plan`.

3. **Stage-B (project) — ONLY after a clean soak + the Platform ell-lag headroom review clears** `[IRREVERSIBLE — removes the legacy fallback]`
   Retire the legacy-SDK fallback for the PROJECT arm (project becomes satellite-only). **Gated behind**: clean 7-day
   soak (abort-criteria clean) **AND** the **§9.3 full-rate ell-lag caveat** cleared by the **Platform Engineer
   compound-load headroom review** (see §3/§4). Fires on a **deliberate human/IC sign-off**, not automatically.

4. **Secret-2 decommission — LAST** `[IRREVERSIBLE — credential destroyed]`
   Decommission resolver client **Secret 2** ONLY after **#55 repoint is live-verified** (Secret 1 serving 200)
   **AND** the **task-#73 baked-`.env` SPOF is resolved** (env-collision on `ASANA_RESOLVER_CLIENT_SECRET`,
   `Dockerfile:294`). Secret 2 is **actively consumed** (LastAccessedDate 2026-06-03); decommissioning it before that
   SPOF is resolved would strand the live auth path. `#343` declares the client_id-drift alarm, **NOT** the
   decommission. **NOT a same-window step with 1–3.**

## §2. Rollback levers — per step

| Step | Rollback lever | How it reverses | Tested |
|---|---|---|---|
| **1 — #55 repoint** | **PRE-SB-1 flag-OFF** | Drive `satellite_get_df_enabled` **OFF** → both `Project.get_df` and `Section.get_df` route to the legacy SDK path (satellite skipped before attempt). Surgical; no receiver redeploy. | **YES — 2/2** (commit `14586df8`) |
| **1 — #55 repoint** (safety net) | **serve-stale + section-paused safety net** | Receiver rides LKG (PROJECT 86400s / SECTION 3000s) — §D measured 0 builds, `capacity_502=0`, no build pressure under load. Section warm lane stays durably PAUSED (reserved=0 + DISABLED, #353) so no 429-storm / knob-inverted-502 recurs. | live (measured §D) |
| **2 — Stage-B (project)** | **flag-OFF re-enables fallback before retirement is irreversible** | Pre-Stage-B, flag-OFF restores the legacy fallback. Stage-B must NOT fire until PRE-SB-1 green (it is) AND soak abort-criteria clean AND Platform headroom review clears. | **YES — 2/2** (lever); soak+headroom-gated |
| **3 — Secret-2 decommission** | **No clean rollback once destroyed → mitigated by ORDERING** | Irreversible by nature. Protection = sequence LAST (after #55 live-verified + task-#73 SPOF resolved); `#343` drift alarm gives early warning of a client_id mismatch BEFORE decommission. | ordering-gated |

**Net posture:** Steps 1–2 are **reversible** via the tested (2/2) flag-OFF lever plus the serve-stale/section-paused
safety net. Step 3 is the genuinely irreversible one — its protection is **sequencing discipline**, which is why it is
sequenced LAST and behind the task-#73 SPOF. Keep the flag-OFF lever ready throughout the soak.

## §3. The SRE side WILL WATCH the soak

We run the S7 soak-watch (full plan in the attached `soak_watch_plan`). Signals, under **REAL production both-arms
traffic**:

- **Per-arm serve ratio** — `receiver_query_outcome_total{entity_type}` success ratio **≥99%** per arm.
- **`capacity_502`** — `receiver_query_fallback_cause_total{cause="capacity_502"}` **must stay 0** (section
  dispositive).
- **serve-stale behavior** — `serving_stale_total{section}` + `lkg_serve_age` **≤ 3000s ceiling** (no breach).
- **CPU / thread-pool** — ECS CPU ≪ 85%; `cpu_thread_semaphore_waiting` = 0.
- **502s / target health** — ALB `ELB_502` not above the pre-cut baseline; target healthy / no flap.
- **event-loop-lag (the headline watch item)** — p99 under compound REAL load. **This is where the §9.3 full-rate
  ell-lag caveat becomes LIVE:** the compound-load saturation that surfaced in chaos (A3 both-arms 2×40rpm → p99
  0.9475s transient, self-recovered, zero downstream impact) is now exercised by real both-arms traffic. **A sustained
  ell-lag breach under real load is the Platform-headroom-review / flag-OFF-rollback trigger.**

## §4. What stays HELD / with whom

- **Stage-B (project)** — HELD behind a clean 7-day soak **AND** the **Platform Engineer compound-load ell-lag
  headroom review** (§9.3). The ell-lag review **gates full-rate** both-arms production; the unified #55 flip routes
  both arms, but the production RATE ramps project-first while section rides its low-traffic serve-stale path until the
  headroom review clears the compound-load ceiling. Owner: consumer/IC fires Stage-B on sign-off; SRE + Platform own
  the soak watch + headroom review.
- **Secret-2 decommission** — HELD to LAST, gated on #55 live-verified + task-#73 baked-`.env` SPOF resolved
  (`Dockerfile:294`). Owner: IC/Platform.
- **§9.3 ell-lag Platform review** — gates full-rate both-arms production (not the project-first cut). Owner: Platform
  Engineer; escalation per the `soak_watch_plan`.

> **No overclaim.** The soak is **not done**; Stage-B is behind a clean soak + the Platform ell-lag headroom review.
> Nothing in this handoff has fired the cutover or mutated operational state.

---

*RETURN-6 from the autom8y-asana SRE rite, 2026-06-04. **AUTHORIZED-and-delivered**, reversible-per-step (steps 1–2 via
the tested 2/2 flag-OFF lever; step 3 protected by sequencing). Secrets redacted (names/scope only). #55 verified at
source this pass: OPEN/mergeable-clean/head `09e0f64b`. **The irreversible fire is the consumer/IC's deliberate
action — this artifact authorizes it, it does not perform it.***
