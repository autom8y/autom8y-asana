---
type: handoff
status: draft
from: review
to: know
created: 2026-06-24
slug: asana-coherence
head: f4f924d2
initiative: asana-ecosystem-coherence-deep-dive
---

# Cross-Rite Handoff: review → know

## 1. Grandeur Anchor (restated)

Pick up the torch on autom8y-asana — the ecosystem's CRM-UI / datastore-frontend / workflow-orchestration layer composing into autom8y-{data,ads,sms,scheduling} flows — by driving the review-rite deep-dive from glint-detected signal to a graded, cross-rite-routed case file, advancing the two production-blockers (SCAR-REG-001; SCAR-IDEM-001) from `authored` toward `proven`; proven ONLY by a live receipt — never by a green dashboard or an optimistic merge. Production-mutating levers stay the user's.

Source: `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md` (preamble block).

---

## 2. Finding Handed Off: P5 — Undocumented Cache Features + Corpus Drift

**Finding ID**: M-2 (case file) / P5 (PV-PREFLIGHT)
**Severity**: MEDIUM
**G-RUNG**: gap `proven` (grep receipts in PV-PREFLIGHT; source files confirmed present at HEAD)

### What the corpus is missing

Five feature domains present in the HEAD codebase are absent from `.know/feat/INDEX.md`:

| Feature | Source presence | INDEX.md count |
|---------|----------------|----------------|
| `PRESERVE` (#128) | `config.py`, `lambda_handlers/pipeline_stage_aggregator.py` | 0 |
| governor / AIMD (#141) | `lambda_handlers/cache_warmer.py` (AIMD logic, dd8e43ab) | 2 (partial only) |
| dead-man (#139) | `lambda_handlers/cache_warmer.py` | 0 |
| honest-empty / cure (#127) | `storage_namespace.py`, `metrics/freshness.py` | 0 |
| `StorageNamespace` (#123) | `src/autom8_asana/storage_namespace.py` | 0 |

Live telemetry for several of these is already emitting: `AsanaDataframeSource` namespace exposes `ColumnContractFailure`, `EmptyFrameTrip`, `RefreshFallbackCount`, `GetDfFallback` — signals belonging to the undocumented honest-empty/cure and serve-stale feature surface. The corpus gap means agents and engineers consulting `.know/` operate on a model that does not include these subsystems. [UNATTESTED — DEFER-POST-HANDOFF: cross-stream corroboration of feature completeness list pending know-rite regeneration]

### Corpus drift extent

- `.know/` last pinned at census `8980bcd7` (2026-05-06)
- HEAD at handoff: `f4f924d2` (2026-06-24)
- Lag: **90 commits / 49 days**
- All `.know/` 7d-expiry domains expired
- Source: `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md` (Corpus drift section, `git rev-list --count 8980bcd7..HEAD` = 90)

---

## 3. Suggested Command

Surface only — do NOT run.

```
/know --all
```

This regenerates all `.know/` domain files (architecture, scar-tissue, design-constraints, conventions, test-coverage) and rebuilds `feat/INDEX.md` from the live HEAD (`f4f924d2`). The `source_hash` in each domain file should be re-pinned to HEAD on completion.

---

## 4. Realization Rung

Current rung: **authored** (this handoff names the gap and routes it)

```
authored → (know advances corpus to current)
```

The next rung — `emitting` — is reached when `.know/feat/INDEX.md` is regenerated and the five absent feature terms are indexable at HEAD. The rung does not advance by this handoff alone; it advances when know executes and the acceptance receipt (§5) passes.

---

## 5. Acceptance Receipt

The realization rung advances from `authored` to `emitting` when ALL of the following hold:

1. **Feature terms present in `feat/INDEX.md`**: grep returns non-zero hits for each of:
   - `cure`
   - `governor`
   - `dead-man`
   - `honest-empty`
   - `serve-stale`
   - `PRESERVE`

   Command form: `grep -c "cure\|governor\|dead-man\|honest-empty\|serve-stale\|PRESERVE" .know/feat/INDEX.md` returns a value > 0 for each term (or a combined multi-pattern count confirming all are present).

2. **`.know/` source_hash re-pinned**: each regenerated `.know/` domain file carries `source_hash: f4f924d2` (HEAD at handoff date) or a later SHA — not `8980bcd7` (the stale census SHA).

Neither condition is satisfied by this handoff artifact. Both must be confirmed by the know rite post-execution.

---

## 6. Inherited Live Receipts

### PV-PREFLIGHT attestation

File: `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md`

- **P5 verdict** (line 35): "TRUE" — gap `proven`
- **Grep receipt** (line 35): `cure`=0, `governor`=0, `dead-man`=0, `honest-empty`=0, `serve-stale`=0, `PRESERVE`=0, `StorageNamespace`=0 confirmed against live `feat/INDEX.md`
- **Corpus drift receipt** (line 24–25): `git rev-list --count 8980bcd7..HEAD` = 90; census SHA dated 2026-05-06; HEAD 2026-06-24 → 49 days
- **Source file presence** (line 35): `src/autom8_asana/storage_namespace.py` exists; PRESERVE/serve-stale across `config.py`, `transport/asana_http.py`, `metrics/freshness.py`, `lambda_handlers/pipeline_stage_aggregator.py`
- **Live telemetry corroboration** (line 41): `AsanaDataframeSource` namespace live with `ColumnContractFailure`, `EmptyFrameTrip`, `RefreshFallbackCount`, `GetDfFallback` — signals belonging to the undocumented feature surface

### Iris attestation

File: `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md` (Tooling state section, line 46)

Iris was summoned but agent file not yet active at PV-PREFLIGHT time (`~/.claude/agents/iris.md` MISSING — requires CC restart). The live-Asana section-GID receipt (P1/SCAR-REG-001) and CloudWatch namespace enumeration were performed directly by the PV-PREFLIGHT agent via AWS SDK (`arn:aws:iam::696318035277:user/tom.tenuta` confirmed live at line 47). The corpus drift metric (`git rev-list`) was obtained in the same session.

No iris-specific attestation artifact exists for this initiative; the preflight itself is the live-receipt substrate. [UNATTESTED — DEFER-POST-HANDOFF: iris formal attestation file pending iris activation post-CC restart]

### Case file inheritance

File: `.ledge/reviews/asana-coherence-case-file.md`

- **M-2 finding** (line 139): ".know/ corpus 90-commit stale; P5 cache features absent from feat/INDEX.md" — severity MEDIUM, routing `know`
- **Next step #5** (line 213): "Regenerate .know/ corpus. `/know --all` — one command; all 90-commit drift resolved."
- **Metrics dashboard** (line 56): `.know/ corpus age: 90 commits / 49 days stale`

---

## 7. Out-of-Scope / User-Sovereign Levers

The following are explicitly outside the know rite's remit for this handoff. G-DEFER applies — watch-registered, not scoped in.

- **Production-correctness blockers** (H-1 SCAR-REG-001, H-2 SCAR-IDEM-001): live Asana GID verification and idempotency finalize repair are user-sovereign production decisions. Know does not touch these.
- **cache_warmer.py decomposition** (H-4): structural refactor requiring test fixture updates across 8+ files. Routed to `10x-dev`, not `know`.
- **Deprecated endpoint retire/extend** (M-5 / FORK-1): requires a live Logs Insights query gate. Routed to `iris` → `10x-dev`. Know does not decide endpoint lifecycle.
- **INTEGRATE-ecosystem-dispatch spike doc recovery** (M-1 / FORK-2): the missing spike doc referenced at `protocols.py:44` is a separate `know` concern (spike authorship), distinct from corpus regeneration. It is not satisfied by `/know --all` alone and requires a dedicated spike authoring pass. [UNATTESTED — DEFER-POST-HANDOFF: scope for that recovery is a separate handoff or user directive]
- **Bridge-fleet namespace investigation** (M-4): live CloudWatch query. Routed to `iris` + `sre`.
- **Source_hash pinning policy** for future reviews: the staleness gate question (whether to add a corpus-age check to the review pre-flight checklist) is a review-rite process decision, not a know-rite output.

---

*Handoff type: cross-rite | From: review | To: know | HEAD: f4f924d2 | 2026-06-24*
*Authored by: case-reporter | Initiative: asana-ecosystem-coherence*
