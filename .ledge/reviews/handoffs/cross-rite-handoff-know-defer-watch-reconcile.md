---
type: handoff
status: draft
from: review
to: know
created: 2026-06-24
slug: asana-coherence
head: f4f924d2
origin_artifact: .ledge/reviews/asana-coherence-case-file.md
preflight_artifact: .ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md
---

# Cross-Rite Handoff: review → know

## 1. Grandeur Anchor (restated)

Pick up the torch on autom8y-asana — the ecosystem's CRM-UI / datastore-frontend / workflow-orchestration layer composing into autom8y-{data,ads,sms,scheduling} flows — by driving the review-rite deep-dive from glint-detected signal to a graded, cross-rite-routed case file, advancing the two production-blockers (SCAR-REG-001; SCAR-IDEM-001) from `authored` toward `proven`; proven ONLY by a live receipt — never by a green dashboard or an optimistic merge. Production-mutating levers stay the user's.

Source: `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md` (Grandeur anchor block, prose verbatim).

---

## 2. Finding: Lapsed Deadlines with No Disposition

The following findings carry past or near-term deadlines and have no recorded disposition in the current codebase or `.know/` corpus. They are surfaced here so the know rite can re-baseline, close, or formally defer each entry.

**Present/future tense — these are open items as of 2026-06-24.**

### EC-013 — `2026-05-11` (lapsed)

- **What it is**: An ecosystem-coherence constraint dated 2026-05-11 referenced in the review artifact context. The deadline has passed with no recorded closure, re-stamp, or disposition in the `.know/` corpus or in `design-constraints.md`.
- **Current state**: Lapsed — no disposition on record.
- **Know action needed**: Re-baseline or close. If still relevant, author a new target date and record rationale. If resolved, mark closed with evidence.

### TRADE-008 — Sunset `2026-06-01` (lapsed 23 days as of 2026-06-24)

- **What it is**: The `POST /v1/query/{entity_type}` endpoint carries `Sunset: 2026-06-01` (`api/main.py:470`, `routes/query.py:881`). The sunset date has lapsed. Usage is UNVERIFIABLE from metrics alone — the only usage signal is a log line (`routes/query.py:885`); `Autom8y/AsanaWorkflows` publishes 0 CloudWatch metrics [UNATTESTED — DEFER-POST-HANDOFF: see FORK-1 in case file; iris Logs Insights gate must pass before retire decision].
- **Current state**: Route is live and serving past its declared sunset. The retire-vs-extend decision is blocked on a Logs Insights query (G-DENOM: absence of log evidence is not proof of zero usage).
- **Know action needed**: Once iris runs the Logs Insights gate on `deprecated_query_endpoint_used.caller_service` (aggregated since 2026-06-01), record the disposition here: retire confirmed OR sunset re-stamped with new date + notified-callers evidence.

### defer-watch `watch_trigger: 2026-05-29` (lapsed)

- **What it is**: A defer-watch entry with a `watch_trigger` date of 2026-05-29. This trigger has fired — the watch window has elapsed — and no disposition (fire/close/re-defer) is recorded in the defer-watch manifest.
- **Current state**: Trigger date past; fire/disposition state absent [UNATTESTED — DEFER-POST-HANDOFF: disposition requires the defer-watch.yaml manifest entries to be audited by know rite].
- **Know action needed**: Audit defer-watch.yaml for this entry. Record fire state and disposition. If the underlying concern is resolved, close. If still open, re-register with a new trigger date and rationale.

### TENSION-006 — Cross-repo deadline `2026-09-29` (active DEFER — do not advance)

- **What it is**: Interop orphan adapter (`automation/workflows/protocols.py:32-44`) — `get_reconciliation_async()` / `get_export_csv_async()` belong in the shared SDK substrate. Dispatch-asserted trigger date 2026-09-29; owner = SDK-repo owner.
- **Current state**: DEFER — watch registered. This entry is in scope for know awareness only; it is NOT a lapsed deadline and does NOT require re-basing at this time.
- **Know action needed**: None before 2026-09-29. Record that this entry is tracked. At trigger date, re-evaluate and assign disposition.

---

## 3. Suggested Command

```
/know
```

Surface only — do NOT run. The know rite operator decides when and with what scope to invoke.

---

## 4. Realization Rung

**Current rung**: `authored`

The handoff artifact is authored and the lapsed deadlines are surfaced. No downstream specialist has been executed.

**Advancement path**:
- know rite re-baselines or closes EC-013, TRADE-008 (post-iris gate), and defer-watch `2026-05-29` entries
- defer-watch.yaml entries carry recorded fire/disposition state
- lapsed design-constraints dates are re-baselined or formally closed with evidence

**Next rung on advancement**: `know re-baselines/closes` — the rung advances when know records disposition for each lapsed entry and defer-watch.yaml carries fire/disposition state for the 2026-05-29 trigger.

---

## 5. Acceptance Receipt

What would advance the realization rung from `authored` to the next rung:

1. **defer-watch.yaml entries** for EC-013, TRADE-008, and the `2026-05-29` watch-trigger each carry a `fire` and `disposition` field (not null/absent). Acceptable dispositions: `closed` (with evidence), `re-deferred` (with new trigger date and rationale), or `escalated` (with routing target).

2. **Lapsed design-constraints dates** (EC-013 and TRADE-008 sunset) are re-baselined or formally closed. Re-baseline requires a new target date with recorded rationale. Close requires evidence of resolution (e.g., iris Logs Insights receipt for TRADE-008; explicit owner sign-off for EC-013).

3. **TENSION-006** is recorded as DEFER-active in know's watch register with trigger date 2026-09-29 and owner noted — no further action required until trigger date.

---

## 6. Inherited Live Receipts

The following evidence is inherited from the upstream PV-PREFLIGHT and review case file. These are cited verbatim; no new claims are introduced by this handoff.

### From PV-PREFLIGHT (`PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md`)

- **TRADE-008 / Sunset lapsed**: Route live at `api/main.py:470` — `RouterMount(router=query_router)` [PV-PREFLIGHT:33]. Sunset header set at `routes/query.py:881` [PV-PREFLIGHT:33]. Usage telemetry is a log line only at `routes/query.py:885` [PV-PREFLIGHT:33]. `Autom8y/AsanaWorkflows` namespace publishes **0 CloudWatch metrics** — `list-metrics` count=0 [PV-PREFLIGHT:33]. G-DENOM: absence of log evidence is not proof of zero usage. Evidence rung: route `live`; usage `UNVERIFIABLE` from metrics.

- **defer-watch / .know/ corpus**: `git rev-list --count 8980bcd7..HEAD` = 90 commits [PV-PREFLIGHT:24]. Census date 2026-05-06; HEAD 2026-06-24 → 49 days stale [PV-PREFLIGHT:24-25]. All `.know/` 7d-expiry domains expired. `feat/INDEX.md` grep: `cure=0`, `governor=0`, `dead-man=0`, `honest-empty=0`, `serve-stale=0`, `PRESERVE=0`, `StorageNamespace=0` (AIMD=2 partial) [PV-PREFLIGHT:35].

- **iris tooling state at PV-PREFLIGHT authoring**: iris agent file not yet active (`~/.claude/agents/iris.md` MISSING at time of preflight); iris Logs Insights gate for TRADE-008 deferred to post-CC-restart [PV-PREFLIGHT:45-46]. AWS creds LIVE (`arn:aws:iam::696318035277:user/tom.tenuta`) [PV-PREFLIGHT:46].

### From case file (`asana-coherence-case-file.md`)

- **TENSION-006 / FORK-2**: Interop orphan at `protocols.py:44`; DEFER watch registered, trigger 2026-09-29 [case-file:171]. Dangling `INTEGRATE-ecosystem-dispatch §1.4` phased-plan reference confirmed absent at `design-constraints.md:321` [case-file:171]. Filed: Cassandra complaint `COMPLAINT-20260624-*-pythia.yaml` [UNATTESTED — DEFER-POST-HANDOFF: Cassandra complaint file path is dispatch-asserted; no file:line receipt attached at authoring time].

- **M-2 / .know/ regeneration**: .know/ corpus 90-commit stale; P5 cache features absent from `feat/INDEX.md` [case-file:139]. Recommended action: `/know --all` [case-file:193].

- **Evidence grade on all findings**: Self-assessed MODERATE per G-CRITIC ceiling (external corroboration PENDING for all HIGH findings) [case-file:235-236].

---

## 7. Out-of-Scope / User-Sovereign Levers

The following are explicitly out of scope for this handoff and remain user-sovereign decisions:

- **Retiring `POST /v1/query/{entity_type}`**: The retire decision is gated on the iris Logs Insights query result. This handoff does not authorize or recommend retirement — it registers the lapsed sunset for know tracking only.

- **Live Asana GID verification (SCAR-REG-001)**: The `GET /projects/1201081073731555/sections` call is an iris action, not a know action. Know tracks the lapsed deadline; iris provides the receipt; the GID constant replacements are a `10x-dev` action post-receipt.

- **SCAR-IDEM-001 remediation**: CloudWatch error metric wire-up and S2S propagation fix are `sre` + `10x-dev` actions. Know tracks the finding but does not remediate.

- **cache_warmer.py decomposition (H-4)**: A `10x-dev` sprint action. Out of scope for know.

- **TENSION-006 SDK upstream PR**: Deferred to 2026-09-29. User decides when and whether to initiate the coordinated SDK PR.

- **Any production-mutating action**: Production levers stay with the user. This handoff is observation and disposition-registration only.

---

*Handoff type: cross-rite | from: review | to: know | authored: 2026-06-24 | HEAD: f4f924d2 | rung: authored*
