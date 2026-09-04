---
type: review
subtype: uv-p-reground-receipt
status: accepted
artifact_id: VERIFY-f1a-d11ae574-reground
re_grounds: CUSTODY-f1a-flip-ac4-ac5-2026-07-21   # F-C3-01 (registration-only) + AC-4/AC-5
initiative: F1a — asana cross-consumer rate-limit budget allocator
sprint: S4 — F-C3-01 re-ground (BUDGET, satellite autom8y-asana)
node: "informs NODE 8 — GO-LIVE (OPERATOR-ONLY). VERIFY-only; never flips, never enforces."
author: sre observability-engineer (VERIFY-not-build, satellite dispatch)
date: 2026-07-22
code_ref: "origin/main @ b3da9d8c7d44e3f748d2788e336ca3f3994b2c44 (contains d11ae574; ALL code claims read via `git show origin/main:<path>`; the dirty working tree d544b094 was NEVER read for code state)"
grade_cap: "MODERATE (self-ref-evidence-grade-rule; single-analyst satellite VERIFY; rite-disjoint critic = eunomia verification-auditor @ autom8y-asana). Lighter rigor: BUILT<MERGED normal-review is expected, not a defect."
fences: "VERIFY ONLY. Zero enforcement acts. ASANA_BUDGET_ALLOCATOR_ENABLED not flipped anywhere; ECS-gated + 3rd (-section) warmer not activated; nothing merged to enforcement. The node-8 flip-to-enforcement stays operator-sovereign. This file + the durable landing of the CUSTODY finding are the only writes."
---

# VERIFY — F-C3-01 re-ground against origin/main d11ae574 (warmer-floor wiring)

> Re-runs the CUSTODY finding's OWN collapse-checklist against the post-wiring
> tree. The finding's binding lesson — **registered ≠ enforced** — is carried
> forward one altitude: **wired ≠ realized**. Every claim below carries a
> file:line + git-ref.

## 0. Verdict summary (one screen)

1. **F-C3-01 warmer-half: COLLAPSED-to-RESOLVED** at the wiring/deployed-image
   altitude. `d11ae574` (PR #256; an ancestor of origin/main `b3da9d8c`, and a
   descendant of the custody read-surface `2362cd37`) supplies exactly the
   file:line receipt the finding's falsification pathway demanded
   (CUSTODY :128-134): a production call path from the gap-warm loop into
   `WarmerFloorGate.admit()`. The `registered ≠ enforced` lesson now recurs as
   `wired ≠ realized`: RESOLVED means the floor is **armed and paying-capable at
   the deployed source**, NOT that the cure (sawtooth collapse) is realized —
   realization is routed to the live watch (CUSTODY §5; WATCH §4).
2. **ENFORCED-posture:** floor **WIRED** (`hierarchy_warmer.py:381/:388/:400`) +
   **DEPLOYED** (UV-P-2 discharged, WATCH §1) + **ENABLED on 2/3 warmer Lambdas**
   (cite WATCH; `-section` held INERT; ECS untouched) — after a clobber/restore
   cycle now **durable-in-IaC**. The per-chunk banking at `hierarchy_warmer.py:278`
   **structurally defuses** the §3.3 bank-on-abort→lose-on-timeout inversion. What
   a static read CANNOT confirm — and a live watch-window must — is that the floor
   PAYS under truncation in production (sawtooth collapse + uncached convergence).
3. **Clause (c) still owes:** the **ECS 1390 self-cap is UNWIRED** (S5's build —
   `_floor_paced` gates only on `running_in_warmer_lane()`, so the FAIR_SHARE/ECS
   path takes the unchanged fetch); the **write-side three-writer arbitration is
   UNRESOLVED**; and **AC-5 near-zero sizing discharges ONLY via the W-A/W-B
   measurement windows** (CUSTODY :272-274), NOT via allocator telemetry —
   `observe_admission` is now wired but **warmer-lane-only**, the wrong lane for
   the near-zero (FAIR_SHARE) principals.
4. **SVR-7 landing:** the CUSTODY finding was working-tree-only (untracked at HEAD,
   absent from origin/main). It is landed durably in this same branch alongside
   this receipt (§4). Staged for review; NOT merged (merge = operator/reviewer's
   call; merge auto-deploys, WATCH :65 — out of VERIFY scope).

## 1. Item 1 — re-run the CUSTODY collapse-checklist (§2 falsification pathway)

**The checklist (CUSTODY :128-134, verbatim intent):** F-C3-01 collapses to
RESOLVED on "a file:line receipt on the deployed ref showing a production call
path from the gap-warm loop (or the transport hot path) into
`WarmerFloorGate.admit()` / an in-path 1390 self-cap — e.g., a commit between
`f6a72824` and the deployed image that wires it." The custody was authored
against `origin/main @ 2362cd37` (CUSTODY :11), where the census found
**zero** production call sites (CUSTODY receipts 2-3, :94-95).

**Re-run against origin/main d11ae574 — the receipt the checklist demanded:**

| # | Collapse condition | Post-wiring anchor (origin/main @ b3da9d8c, contains d11ae574) | Met? |
|---|---|---|---|
| a | Gap-warm loop resolves a floor-paced fetch | `src/autom8_asana/dataframes/builders/hierarchy_warmer.py:256` — `fetch_one, cure_active = self._floor_paced(_fetch_gap_parent)` | ✓ |
| b | Production call path into `WarmerFloorGate.admit()` | `hierarchy_warmer.py:381` `gate = allocator.warmer_floor_gate()` → `:388` `await gate.admit()` (inside `_floor_paced_fetch`, driven per gap GET) | ✓ |
| c | The AC-2 admission-observation site the custody found ABSENT | `hierarchy_warmer.py:400` `allocator.observe_admission(Lane.WARMER)` | ✓ |
| d | On the DEPLOYED ref (not just source) | WATCH §1 (:60-71): Lambda `CodeSha256 dcd96528…` EXACT-matches ECR digest for tag `d11ae57` (= `d11ae574` short SHA); LastModified `2026-07-21T13:51:30Z` | ✓ |
| e | The call sites are genuinely NEW (not pre-existing) | `git show d11ae574~1:…/hierarchy_warmer.py \| grep -E 'warmer_floor_gate\|gate\.admit\|observe_admission'` → **zero matches**; same tokens present at origin/main (5 matches). Probe run this session. | ✓ |

**VERDICT (warmer-half): COLLAPSED-to-RESOLVED.** The finding's own falsification
pathway is satisfied by `d11ae574` at the deployed ref. Per the finding's closing
clause (CUSTODY :133-134), "§5's checklist applies as written against the wired
mechanism" — i.e., the decision surface moves off F-C3-01 and onto the AC-4
tripwire + live watch.

**Residual named (the `wired ≠ realized` carry-forward, binding per the finding's
own discipline):** RESOLVED here is **source/deployed-image grade**, not
**production-realized** grade. Three legs still separate "armed" from "cured," and
they are NOT part of F-C3-01's claim (they are its §5 downstream): (i) the flip
must be durably ENABLED (was clobbered once — §2 below); (ii) the banking must
PAY under truncation; (iii) the sawtooth must collapse in a live peak. None is
verifiable by this static read.

## 2. Item 2 — ENFORCED-posture, precisely

**Floor WIRED ✓** — `hierarchy_warmer.py:381` (`warmer_floor_gate()`), `:388`
(`gate.admit()`), `:400` (`observe_admission(Lane.WARMER)`); guarded by
`running_in_warmer_lane()` (`:376`) AND `allocator.enabled` (`:379`). When either
guard is false the returned callable IS the bare fetch — byte-identical baseline,
no per-GET branch (`hierarchy_warmer.py:361-363`, comment).

**Deployed ✓ (UV-P-2 DISCHARGED).** The CUSTODY §5.0 pre-flip check (CUSTODY
:318-321, "confirm the deployed images carry the allocator commits BEFORE
flipping") is discharged by WATCH §1 (:40-78): container-Lambda `CodeSha256` ==
ECR image digest for tag `d11ae57`, tag == `d11ae574` short SHA. The residual is
bounded and honest: the image carries no OCI `revision` label, so the
image→git-tree binding rests on the CI short-SHA tag convention (WATCH :73-78,
logged UV-P-A). Grade: MODERATE.

**ENABLED — 2 of 3 warmer Lambdas [infra-config UV-P, CITED not re-probed].**
Per WATCH frontmatter `targets_flipped` (:15-17) = `autom8-asana-cache-warmer` +
`autom8-asana-cache-warmer-bulk`; `targets_NOT_flipped` (:18-19) =
`autom8-asana-cache-warmer-section` (held INERT per the two-Lambda fence). ECS
NOT flipped (WATCH :21). **Precision note — the enable had a scare:** a subsequent
`b3da9d8c` auto-deploy CLOBBERED the manual env flip (`true → ABSENT`, allocator
reverted `active → inert`, WATCH §13.2 :365-369) because the flip key was not in
monorepo IaC (`terraform apply` reverted the manual mutation, WATCH :370-375). It
was then RESTORED **durably-in-IaC** via autom8y-monorepo PR #1189 (merged
`9db54cad`), which encodes `ASANA_BUDGET_ALLOCATOR_ENABLED = "true"` into
`module.cache_warmer` + `module.cache_warmer_bulk` — now clobber-proof (WATCH §14
:415-428). So "enabled" is durable as of the WATCH close, but the enablement was
demonstrably fragile before IaC — a live `allocator_boot state=active` on a
post-restore invoke is still owed (below). [These counts/states are the WATCH
doc's own-hands `aws` reads — an infra-config UV-P I cite per dispatch, not a
re-probe.]

**§3.3 inversion — DEFUSED at the code altitude.** The CUSTODY §3.3 warning
(CUSTODY :190-202) was: wiring the floor WITHOUT fixing the banking cadence
converts a slow-but-durable failure (bank-on-abort) into a fast-but-evaporating
one (lose-on-900s-timeout) for gap sets in (~1,650, 3,291]. `d11ae574` moved the
banking INSIDE the chunk loop: `hierarchy_warmer.py:278`
(`if cure_active and chunk_dicts and not await self._bank_gap_chunk(chunk_dicts)`),
inside the loop opened at `:258`. The custody placed the same call AFTER the loop
at `:278`-of-`2362cd37` (CUSTODY :150, :159). The in-code comment names the
inversion by number: "a 900s Lambda-wall truncation … loses at most one chunk …
the §3.3 inversion" (`hierarchy_warmer.py:269-275`). Critically, `cure_active`
co-gates BOTH floor pacing and per-chunk banking (`hierarchy_warmer.py:253-256`),
so the fix arms WITH the flip — "one lever, two co-required behaviours" — and the
inert path keeps single end-of-sweep banking (`:299-308`).

**What a LIVE watch-window must confirm (this read CANNOT) — WATCH §4 (:104-119):**
1. `allocator_boot state=active/enabled=true` on post-restore invokes — that the
   durable-IaC flip actually re-armed after the §13.2 clobber (WATCH §4 crit-2,
   :110-112).
2. `OfferFrameAgeSeconds{1143843662099250}` RAW datapoints sustained **< 3600 s**
   through ≥1 diurnal peak 09:00-12:00Z 2026-07-22 — the sawtooth collapse that
   IS the cure (WATCH §4 crit-1, :107-109; CUSTODY §5.1 :332).
3. `uncached_count` converging from the ~3191 baseline across ticks — that the
   per-chunk banking PAYS durably under truncation, not just structurally in code
   (WATCH §4 crit-3, :113-119).
4. Confounds to clear first: redis `CurrItems` was **0.0** in-window (no writes
   observed; UV-P-C, WATCH :387-394, :412) and a transient "Too many connections"
   client-pool limit (UV-P-D, WATCH :413). Until the cache demonstrably fills, a
   non-collapse would be a confounded false-negative (the exact "verdict
   contamination" the custody warned of, CUSTODY :124-126).

## 3. Item 3 — clause (c) STILL OWES

1. **ECS 1390 self-cap — UNWIRED (S5's build).** F-C3-01's second clause ("no
   code path self-caps ECS at 1390", CUSTODY :36-38) is untouched by `d11ae574`.
   `_floor_paced` returns the fetch UNCHANGED off the warmer lane
   (`hierarchy_warmer.py:376-377`); the only production `Lane.FAIR_SHARE`
   references are fail-open bookkeeping (`client.py:84,:89`), and `1390` lives as
   a config constant + docstring only (`config.py:859`, `settings.py:610`) — no
   in-path `gate.admit()` on the ECS request path. The `1390` remains an
   advisory telemetry threshold (CUSTODY :257-259; overage emitted as
   `budget_floor_overage`, `budget_allocator.py:423`), not an enforcer. **ECS half
   OPEN.**
2. **Write-side three-writer arbitration — UNRESOLVED.** The floor/cap governs the
   warmer + fair-share GET/read path only. The legacy monolith's always-on
   `asana_handler` write-storm (the storm producer) is not arbitrated by this
   allocator; `autom8y-asana/lifecycle/webhook.py` is unmounted dead code;
   asana-mcp #242 (merged 07-20) and the ads-actioning future writer are the other
   two. "F1a sizing is visible to one, blind to two." Out of scope for the
   warmer-floor wiring; owed.
3. **AC-5 near-zero sizing — DEFER, discharges ONLY via W-A/W-B (NOT telemetry).**
   Per CUSTODY §4.2 (:272-274): **W-A** = ≥1 CWLI window containing a Sunday
   07:00Z `conversation-audit` firing (candidates 2026-07-26, 2026-08-02);
   **W-B** = ≥1 window over the 11:00Z `insights-export` + `onboarding-walkthrough`
   collision in the 09:00-12:00Z peak. **Not an allocator-telemetry discharge**
   (CUSTODY :281-284): even now that `observe_admission` is wired, its ONLY
   production call site is `hierarchy_warmer.py:400` — `Lane.WARMER`. The
   near-zero principals are FAIR_SHARE, not WARMER; their draw is not what the
   warmer admission counter measures. The custody's original rationale
   ("observe_admission unwired") is superseded, but its CONCLUSION stands for a
   stronger reason: wired-but-warmer-lane-only. Also STILL no near-zero cap
   SURFACE: the settings expose exactly four fields — enabled/floor/window/
   fair_share (CUSTODY :256-257; `settings.py:581-618`); a small follow-up
   settings PR is intrinsic to the discharge (CUSTODY :279).

## 4. Item 4 — SVR-7 durable landing of the CUSTODY finding

`CUSTODY-f1a-flip-ac4-ac5-2026-07-21.md` was untracked at HEAD (`git ls-files
--error-unmatch` → not-found) and absent from origin/main (`git cat-file -e
origin/main:… ` → does-not-exist) — working-tree-only, at risk. It is reproduced
byte-for-byte at its path (`.ledge/reviews/CUSTODY-f1a-flip-ac4-ac5-2026-07-21.md`)
in this branch (`f1a-custody-durable-land`, off origin/main b3da9d8c) and committed
alongside this receipt. Staged for normal review; NOT merged (merge auto-deploys
the asana image per WATCH :65 — strictly out of this VERIFY's fence).

## 5. SVR tuples (load-bearing platform-behavior claims)

```yaml
- claim: "the gap-warm loop routes every gap GET through WarmerFloorGate.admit() in a production path at origin/main"
  verification_method: file-read
  verification_anchor:
    source: "git show origin/main:src/autom8_asana/dataframes/builders/hierarchy_warmer.py"
    line_range: "L386-L388"
    marker_token: "await gate.admit()  # earned-token admission at the static floor rate"
    claim: "the floor gate is consulted per outbound gap GET inside _floor_paced_fetch — the production call site F-C3-01's falsification pathway demanded and the custody census found absent"
- claim: "per-chunk banking is folded inside the chunk loop under cure_active, defusing the §3.3 truncation inversion"
  verification_method: file-read
  verification_anchor:
    source: "git show origin/main:src/autom8_asana/dataframes/builders/hierarchy_warmer.py"
    line_range: "L269-L278"
    marker_token: "loses at most one chunk. Stable ordering (maintain_order) then drops each"
    claim: "durable banking now happens per ~200-GET chunk, bounding a 900s-wall truncation loss to one chunk instead of the whole sweep"
- claim: "the ECS/FAIR_SHARE 1390 self-cap has no in-path admission gate at origin/main"
  verification_method: bash-probe
  verification_anchor:
    source: "git grep -nE 'warmer_floor_gate|\\.admit\\(|observe_admission' origin/main -- 'src/**/*.py' | grep -v budget_allocator.py"
    command_output_verbatim: "hierarchy_warmer.py:381 …warmer_floor_gate(); :388 …gate.admit(); :400 …observe_admission(Lane.WARMER)  (all three ONLY in hierarchy_warmer.py)"
    exit_code: 0
    claim: "every in-path admission primitive lives solely in the warmer sweep; the ECS path carries only Lane.FAIR_SHARE fail-open bookkeeping (client.py:84,:89), so the 1390 cap is unwired"
```

## 6. UV-P register (re-grounded)

- [UV-P-2 STATUS: DISCHARGED — deployed images carry d11ae574 | METHOD: WATCH §1 CodeSha256==ECR-digest, tag d11ae57=d11ae574 | REASON: was CUSTODY §5.0 pre-flip gate; WATCH own-hands aws read @ 2026-07-21T16:38Z closes it (residual: no OCI revision label → tag-convention binding, MODERATE)]
- [UV-P: ASANA_BUDGET_ALLOCATOR_ENABLED=true on exactly 2/3 warmer Lambdas, now durable-in-IaC | METHOD: WATCH §2/§14 aws env audit + monorepo PR #1189 (9db54cad) | REASON: infra-config state cited from WATCH, not re-probed this session per dispatch]
- [UV-P: the floor PAYS under truncation in production (sawtooth collapse, uncached convergence) | METHOD: live watch over ≥1 diurnal peak 09:00-12:00Z 2026-07-22, WATCH §4 | REASON: unprovable by static read; this is the wired≠realized leg]
- [UV-P: redis cache-fill realizes with the flip restored | METHOD: re-observe CurrItems/uncached_count with flip ON + connection-pool cleared | REASON: in-window CurrItems 0.0 + "Too many connections" transient confounded the clean test, WATCH §13.3/UV-P-C/D]

---
*sre observability-engineer, S4 F-C3-01 re-ground, 2026-07-22. VERIFY-only against
origin/main b3da9d8c; the dirty working tree was never read for code state; zero
enforcement acts; the node-8 flip stays the operator's alone. This receipt
characterizes posture — it never changes it.*
