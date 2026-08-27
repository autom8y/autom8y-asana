---
type: adversary-report
subtype: arch-adversary-challenge
target_handoff: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-arch-to-10xdev-sibling-substrate-2026-07-08.md"
target_handoff_sha: "sha256:6e23cf43b46ded45778c1a218b6895c8069d243224a71eb30ac0bb67c7af3c3a"
challenger_agent: arch-adversary
initiative: sibling-substrate-phe-projection-coverage
date: "2026-07-08"
iter: 1
verdict: PASS-WITH-CONDITIONS
adversary_disposition: CONCUR-WITH-FLAGS
tl_a_status: PASS
tl_b_status: PASS
tl_c_status: CHALLENGE
delta_scope_attested: false
challenges_raised:
  - id: CH-01
    taxonomy_id: AC-01
    tl_clause: C
    severity: FLAG
    target_element: "ITEM-F acceptance criteria (root-hygiene fail-closed allowlist `^[0-9a-f]{32}$`) + TDD §8 step 3 + ADR fork (f); vs verified live deck-host public/ slug"
    rationale: "The proposed root-hygiene allowlist admits only `_headers` + dirs matching `^[0-9a-f]{32}$` (32-hex). The CURRENTLY-DEPLOYED / live-verified deck-host slug is `od67utt5a5gdbidn6b5dszjjoi` — 26-char base32, NOT 32-hex. A fail-closed allowlist would REFUSE the currently-live slug dir, and the operator-backfill precondition ('reconcile against the LIVE deployed slug set') must therefore also reconcile slug SHAPE, not just presence — otherwise the very guard designed to prevent a 404 would itself refuse-to-stage the live deck. The HANDOFF confronts the 404 class (ITEM-F TL-C names it) but does not name this slug-shape mismatch as a backfill obligation."
    falsification_pathway: "Observation that revises this FLAG: the ITEM-F spike/TDD (or the operator backfill precondition text) explicitly states how the live 26-char base32 slug (od67utt5…) is reconciled with the 32-hex allowlist — either (a) the live slug is re-minted to 32-hex before accumulation, (b) the allowlist is widened to admit the mint_slug historical shapes, or (c) the live slug is documented as retired/superseded (matches the SUPERSEDED-404 scar) and excluded from the accumulation set. Any of these closes CH-01."
    remediation_hint: "In the ITEM-F follow-on TDD (NOT this PR), add a backfill sub-step: enumerate live deployed slugs, classify each against `_SLUG_RE` (host_bundle.py:68), and specify the disposition of any non-conforming slug (re-mint / widen-allowlist / exclude-as-superseded) before the shared-root allowlist goes fail-closed."
  - id: CH-02
    taxonomy_id: AC-01
    tl_clause: A
    severity: FLAG
    target_element: "ITEM-C acceptance criteria + TDD §3 row 14 (loader.py:24 threading); vs loader.py:285 batch writer"
    rationale: "The ADR §(c) / ITEM-C writer census threads `opt_fields` into the single-task `load_task_entry` (loader.py:24) but the same module carries a SECOND generic `CacheEntry(entry_type=entry_type, ...)` write site — the batch `load_task_entries` at loader.py:285 (verified on fresh root) — which is NOT threaded. If that batch path ever writes TASK entries, it produces metadata-less UNKNOWN entries, identical to the autom8_adapter gap that ITEM-C treats as a same-PR MUST. The census claim 'both bare TASK writers in the adapter' is accurate for the adapter but the loader-batch writer is not dispositioned in-line."
    falsification_pathway: "Observation that revises this FLAG: ITEM-C (or DW-5) explicitly dispositions loader.py:285 `load_task_entries` — either (a) proof it never writes EntryType.TASK, (b) it is threaded identically to :24, or (c) it is fail-safe-only (UNKNOWN⇒miss-once) and named in DW-5's watch scope. Any closes CH-02."
    remediation_hint: "Extend the ITEM-C grep-assertion ('zero remaining CacheEntry( TASK constructions without projection metadata outside test fixtures') to explicitly cover loader.py:285, or fold loader.py:285 into DW-5's watch text so the census residue is visible-deferred rather than silently dropped."
  - id: CH-03
    taxonomy_id: AC-02
    tl_clause: A
    severity: ADVISORY
    target_element: "ITEM-A AC#4 + TDD §2.4 (requested-prefix WARN canary on trusted hits, UV-P labeled)"
    rationale: "The requested-prefix loud canary rests on the axiom 'Asana keys every requested top-level field, null/[] when valueless' — an unverified-live-API premise. The HANDOFF correctly labels it UV-P and makes it warn-only (falsification costs a spurious WARN, never a wrong serve), and routes the live probe to the qa-adversary P2 leg. This is the disciplined handling of a forward-looking claim, so it is ADVISORY not verdict-driving — but it IS the one place in ITEM-A where a load-bearing-adjacent claim depends on an unverified external axiom, so it is recorded for the qa live leg to close."
    falsification_pathway: "Observation that revises: qa-adversary's P2 live leg against live Asana confirms (or refutes) the top-level-key-presence axiom; if refuted, the prefix canary is demoted/removed (warn-only means no serve-correctness impact either way)."
    remediation_hint: "Keep the UV-P label through merge; ensure the P2 qa live-leg checklist explicitly includes the prefix-canary axiom probe (already named in TDD §10 P2)."
arch_ref_citations:
  - "AQ:SRC-004"
  - "DP:SRC-005"
  - "AV:SRC-001"
---

# ADVERSARY-REPORT — sibling-substrate PHE projection-coverage (iter 1 / CHALLENGED-1)

## 1. Challenge Summary

**Verdict: PASS-WITH-CONDITIONS** (adversary_disposition: CONCUR-WITH-FLAGS).

TL-A PASS, TL-B PASS, TL-C CHALLENGE (three FLAG/ADVISORY conditions, none load-bearingly BLOCKING).

- **CH-01** (AC-01, FLAG, TL-C): SIBLING-2 root-hygiene allowlist `^[0-9a-f]{32}$` would refuse the live 26-char base32 deck-host slug `od67utt5…`; the operator backfill precondition must reconcile slug SHAPE, not just presence.
- **CH-02** (AC-01, FLAG, TL-A): ITEM-C writer census threads `loader.py:24` but not the sibling batch writer `loader.py:285`; census residue undispositioned in-line.
- **CH-03** (AC-02, ADVISORY, TL-A): the UV-P requested-prefix canary rests on an unverified-live Asana key-presence axiom — correctly labeled and warn-only; routed to qa P2 live leg.

This HANDOFF is one of the cleanest TL-B showings in the corpus: every load-bearing file:line was independently re-derived on the declared fresh root and matched. None of the five operator-nominated BLOCK-triggers survived probing. The conditions are refinements to two deferred/sibling items, not defects in the flagship (ITEM-A) design.

Fresh-root discipline honored: verified against `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.arch.sibling-substrate.20260708T182700.d865d7` @ `5b5c249a` == `git rev-parse origin/main` (5b5c249a0cc71c8d95edda6728c282fc55f517f6), POST-#214. Local `main` is `f3d8eec1` (STALE — not read). Grounding: inter-rater/construct-validity discipline [AV:SRC-001 Messick 1989]; anti-pattern cumulative-error framing [AQ:SRC-004 Mo et al. 2019]; bounded-context / anti-corruption boundary lens for the SIBLING-2 cross-repo seam [DP:SRC-005 Evans 2003].

## 2. TL-A Analysis — per-item build-gate audit

Every ITEM carries a **BUILD-GATE** prediction (immediate, falsifiable at build/test time, halts-its-item on falsification) — the HANDOFF explicitly frames these as build-gates, not horizon predictions, and each names a concrete falsifier. This satisfies the TL-A "at least one structured, falsifiable, build-gate-labeled prediction" requirement per item.

- **ITEM-A** PASS. Prediction is a concrete two-reader HTTP-call-count experiment with a fake transport: pre-fix ONE call + section-less serve (RED), post-fix TWO calls + section-carrying serve (GREEN), plus ×10-alternation ⇒ exactly 2 calls (ping-pong bound) and requested⊆stored ⇒ ZERO extra calls (teeth). Falsifiable, mechanical, self-halting. The RED-before is mandated as an ARCHIVED run against the CURRENT hit path (AC#6) — a genuine production-gap canary, not an injected defect (discriminating-canary mode 2).
- **ITEM-B** PASS. Narrow-write-then-wide-read FAILS pre-fix on each of the 4 sibling clients; ≤1 widening fetch post-fix; HALT-and-watch if a client's flow breaks the 3-line graft.
- **ITEM-C** PASS with **CH-02 FLAG**. Warmer-honesty test RED-without / GREEN-with is falsifiable and correctly scoped same-PR. FLAG: the writer census threads loader.py:24 but not the sibling batch writer loader.py:285 (see §CH-02).
- **ITEM-D** PASS. `ASANA_CACHE_ENABLED=false` ⇒ NullCacheProvider is truthfully writable only as xfail/inverted pre-bind, passes post-bind; HALT if `from_env` reads a cached/singleton settings object. Verified: config.py:855 default_factory site is exactly as cited; from_env at :781-816 constructs fresh per-call.
- **ITEM-E** PASS. `batch.py:276` plain `AsanaClient()` VERIFIED live-exposed today ⇒ flagship protects it at merge with zero batch.py change; nonzero `method="phone"` on a well-parented office falsifies loudly (DW-1).
- **ITEM-F** PASS (as a SPIKE build-gate) with **CH-01 FLAG**. Accumulation-compatibility of `stage_deck_bundle` is the spike's falsifier; correctly scoped to its own TDD.
- **ITEM-G** PASS. Phone-only contract byte-identical pre/post is the additive-only falsifier.
- **CH-03 ADVISORY** (AC-02): the sole quasi-predictive claim resting on an unverified external axiom (the prefix-canary key-presence premise) is UV-P-labeled and warn-only — the correct handling, recorded for the P2 live leg.

No AC-05 conflation: the `predictions` here are genuine build-gate falsifiers with observable-at-build-time conditions, NOT acceptance-criteria masquerading. The acceptance_criteria are kept in explicit `Acceptance criteria` blocks, SEPARATE from the `TL-A falsifiable prediction (BUILD-GATE)` blocks. This is the correct structural separation AC-05 exists to enforce.

## 3. TL-B Analysis — per-citation resolution and invocation audit (verified on fresh root @ 5b5c249a)

Method: `git show origin/main:<path> | sed -n` per the autom8y-asana verification topology (local main STALE). Every load-bearing anchor RESOLVED and SUPPORTS its claim:

- **tasks.py**: :208 `_cache_get(task_gid, EntryType.TASK)` ✓; :216 guardless `data = cached_entry.data` ✓; :225 warn-only `if "custom_fields" not in data` ✓; :232 `return data` ✓; :264 `_resolve_opt_fields(opt_fields)` ✓; :265 `superset_opt_fields = sorted(set(...) | set(STANDARD...))` ✓; :270-271 `_resolve_entity_ttl` + `_cache_set` ✓; :292-326 `_resolve_opt_fields` body (None→STANDARD, merge at :325) ✓; :41 `_MINIMUM_OPT_FIELDS` ✓.
- **completeness.py:302** `"opt_fields_used": opt_fields or []` ✓ — the EXACT shape the predicate's UNKNOWN-normalization depends on; `create_completeness_metadata` :280-302, `infer_completeness_level` :190 ✓.
- **config.py:855** `cache: CacheConfig = field(default_factory=CacheConfig)` ✓ VERBATIM (the F-2 bind target); from_env :781-816, knobs :651-652 ✓.
- **base.py**: `_cache_get` :83, `_cache_set` :123, version derivation :148-149, `CacheEntry(` construct :155-161 (no metadata kwarg today), `set_versioned` :162 ✓.
- **entry.py**: metadata slot :107, to_dict metadata :212, from_dict :343, EntityCacheEntry typed `completeness_level`/`opt_fields` :380-381 ✓.
- **staleness_coordinator.py:253** `metadata={**entry.metadata, "extension_count": new_count}` ✓ — the KEYSTONE: it reconstructs a base CacheEntry preserving only the metadata dict, so `EntityCacheEntry` typed fields WOULD be silently dropped — this structurally justifies fork (a)'s "metadata dict, NOT typed fields" authority choice. Claim SUPPORTED.
- **mutation_invalidator.py:286** `replace(entry, freshness_stamp=...)` (metadata preserved) ✓.
- **autom8_adapter.py**: TWO bare `CacheEntry(TASK)` writes at :292 AND :382 (neither carries metadata) ✓ — census claim accurate; :393 `set_batch` ✓.
- **loader.py**: :24 `load_task_entry`, :95 `CacheEntry(`, :106 `set_versioned` ✓. (Sibling batch writer at :285 surfaced — see CH-02.)
- **unified.py:412/:474** `create_completeness_metadata(opt_fields)` ✓ (the already-honest writer); **hierarchy_warmer.py:246** `put_async(..., opt_fields=_HIERARCHY_OPT_FIELDS)` ✓.
- **sibling clients**: projects.py:105/:119, sections.py:113/:127, users.py:102/:116, custom_fields.py:108/:122 — all `_cache_get`/`_cache_set` guardless-serve ✓.
- **office_resolution.py:32-38** pin contract "This module makes no cache-provider decision" ✓ VERBATIM; :69 `_WALK_OPT_FIELDS`, :217 `resolve_business_gid`, :260 walk read ✓.
- **link_on_play.py:158-167** preflight `memberships.section.gid/name` projection ✓ (the proven starvation demand).
- **batch.py:276** `async with AsanaClient() as client:` plain ✓ (live-exposed).
- **office_runner.py:197** `office_deploy_root = deploy_base / play_gid` ✓; :137/:144 `_surface_wrangler_command` ✓ — NOTE: file lives at `.../floodgates/office_runner.py`; the ITEM-F/TDD cites elide the `floodgates/` prefix but the anchor is unambiguous (single office_runner.py in tree). Non-blocking path-prefix imprecision.
- **deck-host** (out-of-repo, `~/Code/a8t/deck-host`): `wrangler.toml` name=deck-host, `pages_build_output_dir=public` ✓; `config/deck-manifest.json` present ✓; `bin/verify.js` present ✓; `public/` holds `od67utt5a5gdbidn6b5dszjjoi` + `_headers` ✓ (the SUPERSEDED slug — grounds CH-01).

TL-B verdict: **PASS**. The adversary's own citations (AQ:SRC-004, DP:SRC-005, AV:SRC-001) resolve in the arch-ref INDEX registry and ground the challenge framing (self-subject to TL-B).

## 4. TL-C Analysis — adversarial-disposition honesty audit

The HANDOFF's per-item TL-C dispositions are genuinely adversarial, not self-congratulatory:
- ITEM-A pre-registers the qa attack surface (semantically-implied fields, merge-vs-replace, prefix-canary axiom, G-THEATER) and answers each — the merge-vs-replace REJECTION is load-bearing (torn-read class) and correctly non-negotiable.
- ITEM-E refuses the tempting same-PR unpin shortcut; ITEM-G refuses scope-creep gating.
- Supersession is NOT silent: prior receipts (DEFECT, FRAME, prior HANDOFF ITEM-5/6/7 reactivation, #212 miss-path fix) are named with explicit disposition ("#212 covers only the FIRST reader's projection; cross-reader starvation stands") — AC-03 does NOT fire.
- Per-item disposition IS present across ITEM-A..G, and the 9-row watch registry gives each DEFER an owner/trigger/escalation — AC-04 does NOT fire (this is the anti-pattern AC-04 exists to prevent, and it is satisfied).

TL-C is marked CHALLENGE only because CH-01/CH-02/CH-03 attach here (disposition-completeness on the two deferred/sibling items + the UV-P axiom), not because any disposition is dishonest.

## 5. Remediation Pathway (ordered — conditions, not blockers)

None of these block merge of the P1 flagship train. They are conditions on the deferred/sibling surfaces:

1. **CH-01 (ITEM-F spike/TDD, before allowlist goes fail-closed):** add a backfill sub-step reconciling the live 26-char base32 slug (`od67utt5…`) against the `^[0-9a-f]{32}$` allowlist — re-mint, widen-allowlist, or document-as-superseded-and-exclude. Do NOT let the fail-closed guard refuse the live deck. Target: ITEM-F acceptance criteria / TDD §8 step 3 + the HARD PRECONDITION text.
2. **CH-02 (ITEM-C, same PR or DW-5):** disposition `loader.py:285` `load_task_entries` — extend the grep-assertion to cover it, or fold it into DW-5's watch text. Target: ITEM-C acceptance criteria + Watch registry DW-5.
3. **CH-03 (P2 qa live leg):** keep the UV-P label through merge; ensure the P2 checklist includes the prefix-canary key-presence axiom probe. Target: TDD §10 P2 / ITEM-A AC#4.

Because these are FLAG/ADVISORY, the verdict is PASS-WITH-CONDITIONS: supply the three dispositions (in their respective deferred artifacts / watch entries) and the conditions clear. The P1 flagship (ITEM-A+B+C+D) may proceed on the 2-sided canary gate.

## 6. Falsification of This Report

This verdict is PASS-WITH-CONDITIONS, not BLOCK — so the anti-dogma burden is to state what would have made it a BLOCK, and what would revise it in either direction:

- **What would flip this to BLOCK:** any ONE of — (a) a load-bearing tasks.py hit/miss anchor NOT resolving on 5b5c249a (would break the flagship's own design premise); (b) `completeness.py:302` NOT emitting `opt_fields or []` (would mean the predicate's UNKNOWN-normalization is ungrounded and the None-vs-missing concern becomes real); (c) `staleness_coordinator.py:253` NOT reconstructing a base CacheEntry (would falsify the authority-slot choice and re-open silent typed-field drops); (d) `batch.py:276` actually pinning NullCacheProvider (would falsify the ITEM-E live-exposure premise); (e) no RED-before mandated in §6.1. I probed all five; none held. If a re-run on 5b5c249a shows any of them, this report is falsified — re-challenge at DELTA scope.
- **What would flip this to PASS (clean):** dispositioning CH-01/CH-02 in the ITEM-F TDD and ITEM-C/DW-5 respectively, and confirming the P2 prefix-canary probe is on the qa checklist. These are the exact conditions §5 enumerates.
- **Adversary self-check:** my CH-01 rests on a present-tense probe of `~/Code/a8t/deck-host/public/` (od67utt5… is 26 chars, not 32-hex) AND host_bundle.py:68 (`_SLUG_RE = ^[0-9a-f]{32}$`). If the live deployed slug set (PV'd against the actual Pages deployment, per the standing scar — NOT the local checkout) turns out to already be 32-hex and od67… is merely a stale local-checkout artifact, then CH-01 is itself falsified and should be downgraded to ADVISORY. That live-deployment PV is the operator-sovereign observation that adjudicates CH-01 — which is exactly the backfill precondition the HANDOFF already assigns to the operator. CH-01 is therefore a sharpening of an already-named precondition, not a new gap.

Self-referential evidence grade: MODERATE (self-ref cap; no rite-disjoint second grader on this report). No STRONG claims asserted.
