---
type: telos
initiative_slug: asana-readiness-hygiene
authored_at: 2026-07-01T00:00:00Z
authored_by: hygiene-rite main-thread dispatcher — Gate-A transcription of the OPERATOR-DECLARED predicate (cross-rite-handoff 2026-07-01); myron/frame unavailable as a subagent this session, so the scope-fence + predicate are carried directly per the handoff's own instruction "transcribe; do NOT invent a predicate."
rite: hygiene
schema_version: 1
code_truth_anchor: origin/main cb4b42017b71f582e7bd09945e96730e6f81ec33
---

# Telos Declaration — asana-readiness-hygiene

> Fresh hygiene initiative whose Step-0 blocker (a stale, purpose-obsolete 4.6.0 tree) was
> cleared by a releaser remediation on 2026-07-01 (tree now `main` @ `cb4b4201`, core 4.9.0).
> Predicate transcribed VERBATIM-in-substance from the operator's cross-rite-handoff Grandeur
> Anchor + PV premise 5. Orienting inputs in lieu of a HANDOFF:
> `memory/asana-readiness-hygiene-parked.md` (re-entry contract + KEEP-floor) + `.know/scar-tissue.md`.

```yaml
telos:
  initiative_slug: asana-readiness-hygiene

  inception_anchor:
    framed_at: "2026-07-01"
    frame_artifact: "cross-rite-handoff prompt 2026-07-01 (scope-fence carried directly; myron/frame unavailable) + memory/asana-readiness-hygiene-parked.md"
    why_this_initiative_exists: >
      The autom8y-asana code is lint-clean (`ruff check src/` exit 0), so the ONLY genuine
      autonomous cruft surface is the suppression sites — the `# type: ignore` and `# noqa`
      comments accreted across the src tree — plus the `secretspec.toml` tracked-AND-ignored
      drift. A suppression is debt: it silences a tool for a reason that may have expired.
      Audited-for-future-proofing means each is proven either LOAD-BEARING (kept with an
      inline rationale anchored to a live scar) or DEAD (removed, with the tool re-armed).
      Left un-audited, an expired suppression hides a real defect the day the underlying
      condition returns. This initiative converts the suppression corpus from "silently
      trusted" to "each site adjudicated + the removed class drift-guarded so it cannot
      silently return."

  shipped_definition:
    code_or_artifact_landed:  # LANDED to main 2026-07-01 (releaser + eunomia)
      - "#176 squash dd63e667: 36 dead-noqa removals (comment-only) + R1 pyproject RUF100 per-file-ignore (idempotency.py) + R2 justfile lint-noqa-drift recipe"
      - "#178 squash caade003: .github/workflows/test.yml new job 'Lint noqa Drift Guard (RUF100)' (uvx ruff@0.15.4 check src/ --extend-select RUF100) — the L-001 CI enforcement"
    user_visible_surface: >
      [OPERATOR-DECLARED via cross-rite-handoff 2026-07-01.] The realization is developer-
      facing (readiness/quality), not end-user-facing: after the sprint, the audited
      suppression class is GONE where dead and DOCUMENTED where load-bearing, and
      `just check` stays GREEN — i.e. removing the cruft did not silence a real signal.

  verified_realized_definition:
    user_visible_evidence:
      - "DRIFT-GUARDED (the rung name): every removed suppression class CANNOT silently return — enforced by a ratchet (a ruff rule promoted from per-file-ignore to enforced, OR a ratcheted suppression-count budget, OR a CI drift-check) such that reintroducing the removed class is a RED, not a silent re-accretion."
      - "Per removed/narrowed suppression: a TWO-SIDED RED-then-GREEN receipt — the janitor's OWN observed break (pull the suppression → the tool [mypy for `type: ignore`, ruff for `noqa`] fires RED at a named `{path}:{line}`) → restore/fix → GREEN. A green `just check` alone is NOT a receipt (G-THEATER)."
      - "`just check` GREEN on the deterministic proof surface (`ruff format --check` + `ruff check` + `mypy src/ --strict`) after each increment, on the reconciled ref cb4b4201."
      - "Positive-selection denominator (G-DENOM): X of {reconciled suppression count} examined, Y removable, Z load-bearing-KEPT — the KEEP-floor (SCAR-LOG-001/TID251 ruff per-file logging ignores; the ~20 `except Exception` SCAR-IDEM-001 blocks) preserved with inline rationale, never removed."
    verification_method: two-sided-RED-then-GREEN + just-check-GREEN + drift-guard-ratchet
    verification_deadline: "2026-07-15"  # nominal outer bound; the binding verified-realized (drift-guarded + STRONG) is the rite-disjoint /review critic's at sprint close
    rite_disjoint_attester: "eunomia verification-auditor (product-altitude R1 PASS-ADVISORY) — rite-disjoint from hygiene; a legitimate /review substitution per @critic-substitution-rule (both disjoint from hygiene; eunomia≠hygiene → the never-self-attest semantic holds). NOTE: the original declaration named the review-rite critic, which DID re-fire cleanup-surface STRONG (36/36) earlier in the arc; the L-001 realization attestation was routed to eunomia's disjoint verification-auditor."

  attestation_status:
    inception: INSCRIBED
    shipped: LANDED  # #176 squash dd63e667 (36 dead-noqa removals + drift-guard) + #178 squash caade003 (RUF100 CI drift-guard job on main), 2026-07-01
    verified_realized: ATTESTED  # eunomia S5 verification-auditor, PRODUCT PASS-ADVISORY, rite-disjoint from hygiene. Canary proved teeth in REAL CI: dead noqa on used FastAPI (main.py:49) → check RED run 28530472880 → revert → GREEN 28530879958. Meets the bar (a CI drift-check making reintroduction "a RED, not a silent re-accretion"). TRANSPARENCY: current CI enforcement is visible-red-NON-BLOCKING; registering the job as a REQUIRED status check (operator lever) is the hardening to make drift merge-blocking — beyond the telos bar, which merge-only already satisfies.
    last_review_verdict: ".sos/wip/eunomia/VERDICT-l001-ci-drift-guard-closure.md (eunomia S5: EXECUTION PASS + PRODUCT PASS-ADVISORY, carried verbatim — not rounded to unqualified STRONG)"

  receipt_grammar:
    per_item_file_line_anchors:
      - "src/ suppression corpus @ cb4b4201: 318 `# type: ignore` + 357 `# noqa` = 675 (re-baselined at the reconciled ref; the stale f4f924d2 count was 643 — anti-SCAR-P6-001)"
      - ".know/scar-tissue.md:238 (SCAR-LOG-001/TID251 per-file-ignore KEEP)"
      - ".know/scar-tissue.md:92 (SCAR-IDEM-001 idempotency.py:719 KEEP)"
      - "justfile:138 (check: fmt lint typecheck test — the proof surface)"
    cross_stream_concurrence: true  # two rite-disjoint concurring streams: /review re-fired cleanup-surface STRONG (36/36 two-sided) + eunomia S5 product-altitude PASS-ADVISORY on the L-001 CI-enforcement
    code_verbatim_match: true  # suppression counts + KEEP anchors first-party re-fired at cb4b4201 this PV pass
```

## Gates (load-bearing, carried into the sprint)

1. **MODERATE ceiling is structural**: hygiene auditing its own cleanup is dispatcher-critic
   degenerate (`@self-ref-evidence-grade-rule`). audit-lead's signoff IS the in-rite ceiling.
   `drift-guarded` + STRONG is UNATTESTABLE in-rite — it routes to `/review`. Never round up.
2. **KEEP-floor re-derived at cb4b4201, not trusted**: the scar catalog is EXPIRED (2026-05-08
   +7d TTL). Minimum KEEP: SCAR-LOG-001/TID251 (do-NOT-migrate until autom8y-log ships the
   stdlib `logging.Logger` shim ~2026-Q3) + the `except Exception` SCAR-IDEM-001 blocks.
3. **Proof surface is deterministic**: `ruff` + `mypy --strict` (both GREEN at cb4b4201) are
   the direct suppression-removal proofs. The full pytest suite is the behavior guard, GREEN
   at 14,625 passing; its residual non-passes are ENVIRONMENTAL (live-API `@integration` tests
   CI-excludes + ambient-secret-sensitive adversarial tests), NOT code defects, and OUT of the
   suppression-audit blast radius (watch-registered, PV premise-2 receipt).
4. **Production-mutating levers are the operator's**: merges to `main`; the
   `docs/telos-ledge-sweep-preserve` push/PR; the `secretspec.toml` drift-DIRECTION;
   `.gitignore` edits; `stash@{0}` drop; rollback.

## DEFER / pending

| Item | Status |
|---|---|
| secretspec drift-DIRECTION (untrack vs un-ignore) | OPERATOR's call; staged in its own atomic commit only once called, else secretspec drops to watch and the sprint fences to suppression-audit only |
| verification_deadline real date | nominal 2026-07-15; binding date is design-at-/review-handoff |
| STRONG / drift-guarded attestation | PENDING `/review` (rite-disjoint critic) |
| core-4.9 convergence | DONE (main @ 4.9.0) |
| SCAR-DISCRIMINATOR-001 | hygiene-pass-2 (OUT of this sprint) |

## Evidence Grade

`[STRUCTURAL | MODERATE]` — inception declaration, hygiene-station self-ref ceiling; suppression
counts + KEEP anchors + proof-surface state first-party re-verified at cb4b4201 this PV pass;
the drift-guarded + STRONG realization attestation is the rite-disjoint `/review` critic's at close.
