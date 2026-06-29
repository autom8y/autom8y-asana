---
type: review
status: accepted
artifact_subtype: certification-correction
artifact_id: CORRECTION-t7-b-claim-2026-06-29
schema_version: "1.0"

initiative: forwarding-cutover-first-value
cycle: sprint-5
subphase: FLIP-GATE-honest-rung
author_role: platform-engineer
station: N2-prime
created_at: 2026-06-29T00:00:00Z
corrects: "N2 (T7) returned-text claim '(b) DISCHARGED-UPSTREAM'"
rite_disjoint_source: .ledge/reviews/CHAOS-sre-fcfv-sprint5-gate-resilience-2026-06-29.md
rung: honest-rung-correction (sre MODERATE)
evidence_grade: "[STRUCTURAL | MODERATE]"
self_ref_cap: MODERATE  # sre self-grade; STRONG lift = rite-disjoint eunomia attester

anchors:
  - (b) collision guard @ autom8y-data origin/main 5ab022f7 (business.py:164 _single_business_or_raise, :190 raise OfficePhoneCollisionError)
  - EBI forward guid source @ autom8y EBI resolve_office.py:88/:92 (email local-part, NOT office_phone)
  - N3 chaos report GAP-2 §3 + §8 (the rite-disjoint falsification being amended)
---

# CORRECTION — the "(b) DISCHARGED-UPSTREAM" T7 claim (honest rung)

## §0 — What is being corrected, and why this note exists

The N2 (T7 runtime-tenant-binding) station asserted in its returned text that the
office_phone-collision multiplicity guard **(b)** (`_single_business_or_raise` /
`OfficePhoneCollisionError`) **"DISCHARGED-UPSTREAM"** the wrong-tenant risk for the
forwarding-cutover flip-gate. There is **no in-repo T7 certification artifact** carrying
this claim (the N2 commit `50301444` has a single-line subject and an empty body; a
`grep -rni "discharged.upstream"` across the worktree returns zero hits), so this note is
the corrective record per the dispatch's "no in-repo cert → author a correction note"
clause.

The claim was **rite-disjointly falsified** by the N3 chaos station
(`CHAOS-sre-fcfv-sprint5-gate-resilience-2026-06-29.md` §3 GAP-2 + §8). N3 was correct in
its **conclusion** — "(b) does not discharge the wrong-tenant risk on the EBI forward path" —
but **one of its two supporting sub-claims (the "(b) is UNMERGED" premise) was itself stale**
at the time N3 authored it. This note (platform-engineer, N2′, building on N3) confirms N3's
conclusion via the **durable, merge-independent** reason and **sharpens** the stale premise
with present-tense verified receipts. The honest rung is preserved in BOTH directions: the
over-claim is **never restored**, and N3's stale "unmerged" receipt is **not blindly carried
forward** as a new over-claim in the opposite direction.

> **THE CORRECTED HONEST STATUS:** "(b) DISCHARGED-UPSTREAM" is **FALSE for the EBI forward**.
> The load-bearing reason is **not** that (b) is unmerged (it is **now merged** to
> autom8y-data `main`) — it is that **(b) guards the `office_phone → guid` direction, which
> the EBI reviewwave forward never traverses** (the forward keys on the email local-part guid).
> A direction-mismatched guard cannot discharge a risk on a path it does not sit on, merged or
> not. N=1 tenant-safety for the forward rests on **F-TP-1 + the pilot's collision-free phone +
> the (a) runtime exclusivity assertion**, not on (b).

---

## §1 — The merge-status sub-claim: STALE, now corrected (verified present-tense)

N3 §3 GAP-2 and §8 stated: *"(b) … is on the UNMERGED branch `feat/binding-verify-endpoint`;
autom8y-data `main` (`92d3606d`) … still uses bare `result.first()`; `git branch --merged
origin/main | grep -c binding-verify` → 0."*

**Direct present-tense inspection (post `git fetch origin main`) shows (b) is now ON
autom8y-data `main`:**

| fact | verification | receipt |
|------|-------------|---------|
| (b) guard present on autom8y-data **origin/main** | bash-probe (post-fetch) | `git show origin/main:src/autom8_data/core/repositories/business.py` → `:36` import `OfficePhoneCollisionError`, `:164 def _single_business_or_raise`, `:190 raise OfficePhoneCollisionError(...)`; origin/main = `5ab022f7` |
| it **merged 2026-06-26** (the day AFTER N3's snapshot) | git log | PR **#201** `feat/data-s2-collision-guard` — commits `4e36a545` (01:20Z), `de8ffa56` (02:44Z), `73e0d353` (03:42Z), all `2026-06-26` |
| N3's `92d3606d` was a **3-day-stale LOCAL main** | git merge-base | `git merge-base --is-ancestor 92d3606d origin/main` → **true** (local `main` HEAD `92d3606d`, dated `2026-06-25`, is an ANCESTOR of `origin/main 5ab022f7`); `92d3606d:business.py:192` genuinely had `result.first()` — N3's receipt was accurate **only against that stale checkout** |
| the `feat/binding-verify-endpoint` branch IS unmerged — but it is a **different artifact** | git branch | `git branch -a --merged origin/main | grep -c binding-verify` → `0` is true for that BRANCH; but it is the read-only office_phone↔guid **verify endpoint** (PR-1 `#206 dd4566e5`), NOT the collision **guard**. N3 conflated the unmerged endpoint branch with the guard — the guard landed independently via **#201**. |

**Net:** the "(b) is unmerged" premise is **no longer true** and must not be carried forward.
N3 read `git rev-parse HEAD` + a working-tree `grep` on a local autom8y-data checkout that was
~1 day behind the #201 merge and ~4 days behind today's origin/main. This is a textbook
frozen-snapshot staleness (the same class the SVR / premise-validation disciplines guard
against) — caught here precisely because the dispatch's G-PROVE demanded the
"autom8y-data main `.first()` proof," and going to PROVE it surfaced that origin/main had moved.

---

## §2 — The direction sub-claim: TRUE, merge-independent — this is the DURABLE reason

Even fully merged, **(b) cannot discharge the EBI forward's wrong-tenant risk**, because it
guards the **opposite direction** from the one the forward uses:

| path | tenant-identity source | does (b) sit on it? |
|------|------------------------|---------------------|
| **(b)'s guarded direction** | `office_phone → guid` resolve (a colliding phone → ≥2 guids fail-closes) | — (this IS (b)) |
| **the onboarding-walkthrough** (autom8y-asana) | `office_phone → guid` (B1 resolves the routing address from the phone) | **YES** — (b) is the right direction here, and is now merged. The `tenant_binding.py` module docstring's reference to (b) is **walkthrough-scoped and accurate**; it is NOT the over-claim. |
| **the EBI reviewwave forward** (the path being flipped) | the **email local-part guid** — `resolve_office.py:88 guid = parts[0].strip()` → `:92 ctx.chiropractor_guid = guid`; the only guid-keyed DB hop is `get_business_by_guid_async(guid)` (`:105`), a `guid → office_phone` **PRIMARY-KEY** lookup where multiplicity is impossible | **NO** — the forward never resolves by phone, so (b)'s `office_phone → guid` collision check is never on this path. |

A **mis-addressed forward** (office X's inbound carrying office Y's canonical, well-formed,
WRONG-tenant guid in the `to` address) is therefore **not caught by (b)** on the EBI forward —
regardless of (b)'s merge status. This is the merge-independent core of N3's finding, and it
**stands**.

---

## §3 — What N=1 tenant-safety on the EBI forward ACTUALLY rests on

Not (b). The three load-bearing legs (none of which is (b)):

- **(i) the F-TP-1 allowlist** — `book_reviewwave.py:194-199`: `dry_run OR guid ∉ allowlist → "dry_run"` keyspace. At N=1 only the **pilot guid** is allowlisted, so a forward mis-addressed to ANY other guid fails the `in` test and is demoted (fail-closed). N1-disjoint-proven (the certified-25 ∅-disjointness proof; 15 nodes GREEN).
- **(ii) the pilot's collision-free phone** — `+17156902466`, `match_count == 1` (sprint-1-verified; carried from N1). The pilot's own office_phone does not collide, so even the walkthrough resolve direction is clean for the pilot.
- **(iii) the (a) runtime exclusivity assertion** — `assert_exclusive_tenant_binding` (frozen == resolved): the producer-side artifact guard, now **case-fold-hardened by this same N2′ station** (GAP-1 closed; an uppercase-hex foreign address can no longer evade the harvester).

**(b)'s merge does NOT add a fourth leg to the EBI forward** — the direction mismatch (§2)
means it contributes nothing to forward-correctness on this path.

---

## §4 — GAP-2 reframed: the flip-gating condition for N>1 (operator/cross-repo-terminal)

N3's GAP-2 remediation item #1 was "merge (b) to autom8y-data main." **That is already done**
(§1). So the residual flip-gating condition for **N>1** is **not** "merge (b)" — it is the
narrower, correctly-aimed:

> **Add a FORWARD-DIRECTION tenant guard on the EBI path** — e.g., a `guid ↔ resolved-office`
> consistency assert before the reviewwave POST — because (b) (now merged, but `office_phone →
> guid`) is direction-irrelevant to the forward. The seam opens at **N>1** if a forward is
> mis-addressed to another **allowlisted, non-monolith-served** office (F3/F-TP-1 catch every
> other case; see N3 §1.4).

This is **operator / cross-repo-terminal**, **NOT a sprint-5 build**, and **NOT merge-blocking
for N1/N2**. PT-02 HALT stands above the render predicate regardless.

---

## §5 — Honest rung

- **RUNG = honest-rung-correction (sre MODERATE).** The over-claim "(b) DISCHARGED-UPSTREAM
  [for the EBI forward]" is **retracted and never restored**. The forward's N=1 tenant-safety
  rests on (i)/(ii)/(iii) (§3).
- **N3's conclusion is CONFIRMED** via the durable direction argument (§2); N3's stale
  "unmerged" sub-receipt is **corrected** with present-tense verified anchors (§1) rather than
  carried forward. Rite-disjoint cross-checking caught both the original over-claim (N3 over N2)
  AND the staleness in the falsifying receipt (N2′ over N3) — the discipline working in both
  directions.
- **sre self-grade ceiling = MODERATE** per `self-ref-evidence-grade-rule`; the STRONG lift is
  the rite-disjoint **eunomia** attester.
- **GAP-1 is CLOSED** by this station (case-fold at both guard boundaries, two-sided teeth);
  **GAP-2** is a flip-gating CONDITION for N>1 (§4), surfaced not papered.

## §6 — SVR receipts

| claim | method | anchor |
|-------|--------|--------|
| (b) present on autom8y-data origin/main | bash-probe | `git show origin/main:src/autom8_data/core/repositories/business.py` → `:36`, `:164`, `:190`; origin/main `5ab022f7` (post `git fetch origin main`) |
| (b) merged 2026-06-26 via PR #201 | git log | `4e36a545`/`de8ffa56`/`73e0d353` (all `2026-06-26`), `feat/data-s2-collision-guard` |
| N3's `92d3606d` is a stale ancestor of origin/main | bash-probe | `git merge-base --is-ancestor 92d3606d origin/main` → exit 0 (true); `92d3606d` dated `2026-06-25` |
| `92d3606d:business.py:192` had bare `.first()` (N3's receipt accurate for that SHA) | bash-probe | `git show 92d3606d:…/business.py` → `:192 row = result.first()`, no `_single_business_or_raise` |
| EBI forward keys on email local-part guid (not phone) | file-read | `services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py:88` `guid = parts[0].strip()` · `:92` `ctx.chiropractor_guid = guid` · `:105` `get_business_by_guid_async(guid)` |
| F-TP-1 fail-closed allowlist `in` gate | file-read (carried, N3 §8) | `book_reviewwave.py:194-199` |
| (a) exclusivity guard (now case-fold-hardened) | file-read | `…/onboarding_walkthrough/tenant_binding.py` `assert_exclusive_tenant_binding` + `CANONICAL_ROUTING_ADDR_RE` (`re.IGNORECASE`) |
| rite-disjoint source being amended | file-read | `.ledge/reviews/CHAOS-sre-fcfv-sprint5-gate-resilience-2026-06-29.md` §3 GAP-2, §8 |

## Sources

- `.ledge/reviews/CHAOS-sre-fcfv-sprint5-gate-resilience-2026-06-29.md` — the rite-disjoint N3
  chaos report whose GAP-2 §3/§8 this note amends (conclusion confirmed; merge-status premise
  corrected).
- `@structural-verification-receipt` — present-tense direct-inspection receipts (§1, §6);
  the staleness this note corrects is exactly the premise-propagation failure SVR exists to prevent.
- `@self-ref-evidence-grade-rule` — sre self-grade MODERATE ceiling; STRONG = rite-disjoint eunomia.

Evidence grade: **[STRUCTURAL | MODERATE]** (sre self-ref ceiling). **PT-02 HALT stands.**
