---
type: live-fire-receipt
initiative: gfr-dynvocab
axis: verified_realized
also_banks: contente-n1-pilot-step-1
fired_by: operator-grade / iris
fired_at: 2026-06-25T18:53:38Z
merge_ref: e49c30d7 (GFR stack merged to main)
worktree: /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr (HEAD 562ccab2, floor 216)
mode: LIVE (read-only)
rung: verified_realized EVIDENCE — to be ATTESTED by the rite-disjoint review critic (NOT self-attested STRONG)
---

# GFR dynvocab — verified_realized LIVE FIRE receipt

## Authority & discipline
- Operator-grade grant, READ-ONLY. Live API calls: project task lists + single-task gets + the in-process resolver. NO writes to Asana, NO code mutation, NO commit.
- Resolver exercised is the MERGED code path (no reimplementation): `resolution/gfr/dynvocab.resolve_dynamic_fields` -> `DynVocabResolver.resolve` -> `_apply_override` -> `dynvocab_overrides.apply_override`. A live-fetched task was wrapped in an `EntryAnchor` and resolved.
- Probe (throwaway, worktree, double-guarded GFR_VR_LIVE_FIRE=1): `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/.sos/wip/spikes/gfr-dynvocab/vr_live_fire.py`

## Credential path used
- ASANA_PAT genuinely ABSENT from shell / org SSM (org-secrets.conf) / encrypted project secrets / .env/local (no such file). Active env = `local`.
- Resolved via the SANCTIONED org secret store (AWS Secrets Manager), explicitly named in the grant and in `.env/local.example:38-39`:
  - `aws secretsmanager get-secret-value --secret-id autom8y/asana/asana-pat --query SecretString --output text`
  - `aws secretsmanager get-secret-value --secret-id autom8y/asana/asana-workspace-gid --query SecretString --output text`
- Fetched into PROCESS ENV ONLY (not written to disk, not committed). PAT len=68, prefix `2/` (Asana PAT shape). WORKSPACE_GID=1143357799778608. AWS identity: iam user tom.tenuta, acct 696318035277.
- AsanaClient constructed OK against live creds. STANDARD_TASK_OPT_FIELDS confirmed to carry `custom_fields` AND `date_value` (FRAME-003 live hole closed).

## Positively-selected real entity (denominator integrity, PRED-4)
- entity gid: **1209877818531716**
- source project: **1143843662099250 (OFFER)** — entity_registry.py:512-528, detected type `offer`
- verbatim live "Asset ID" raw text value: **`"38790, 38789, 38788"`** (text-typed, cf_type=text), 49 total custom_fields on the bare fetch
- denominator: OFFER project sampled n=80, Asset ID present=80/80, **populated=9/80** (NOT a blanket-present claim, NOT synthetic; a real populated minority). ASSET_EDIT project (1202204184560785) sampled n=80, present=80/80, populated=12/80.
- NOTE: the prior PARTIAL ("offer present-15/15 populated-0/15") was a SAMPLE-SIZE artifact of n=15; at n=80 populated OFFER Asset IDs exist. The populated entity is OFFER-typed, so the offer-scoped override fired NATIVELY — no entity-type seam was needed (asset-edit not required for the populated entity).
- PRED-4 denominator-integrity: **PASS**

## Realization predicates (LIVE evidence)

### PRED-1 — HYP-1 free-tail LIVE: PASS
Bare `STANDARD_TASK_OPT_FIELDS` fetch on gid 1209877818531716 returned "Asset ID" PRESENT and POPULATED (raw `"38790, 38789, 38788"`). Free-tail mechanism confirmed live: present=True, populated=True.

### PRED-2 — asset_id -> SET (NAME-keyed, EntityType-scoped override): PASS
Real resolver, entity_type=offer, field "asset_id":
- BEFORE (raw live text): `"38790, 38789, 38788"`
- AFTER  (resolver FieldWithProvenance.value): `{"38788","38789","38790"}` — a Python **set** (whitespace-agnostic comma split)
- typing_origin=**override**, cf_type=**text**
- The override fired on the live OFFER entity natively (registry key `("offer", normalize("asset_id"))`, dynvocab_overrides.py:61).

### PRED-3 — GOVERNED-STRICT (genuinely-absent -> truthful unknown-field): PASS
resolve(fields=["__definitely_absent_field_zzz__"]) against the 49-field live manifest raised `UnresolvedError(reason="unknown-field", fields=["__definitely_absent_field_zzz__"])`. UNKNOWN is distinguishable from present-but-null (see adversarial below). Not silently dropped.

## Adversarial /qa (attempts to break it)
- **present-but-empty Asset ID -> present-but-null, NOT empty set: PASS.** Live OFFER entity gid **1215109436919600**, Asset ID present but raw=null. resolve(["asset_id"]) returned the key "asset_id" with value=**None** (PRESENT_BUT_NULL) — NOT an empty set, NOT dropped, NOT unknown-field. The three-state contract (PRESENT / PRESENT_BUT_NULL / ABSENT) holds live.
- **date cf -> resolves to its value (date_value arm closed): PASS.** Live entity gid **1215282122918903**, cf "Edit Date" (resource_subtype=date) -> value=`"2026-06-11"`, cf_type=date, typing_origin=heuristic. The date arm reads date_value live (FRAME-003).
- **unknown-field vs present-but-null distinguishable: PASS** (absent -> raises unknown-field; present-but-null -> key present, value None).
- **wrong-tenant / cross-entity leak: none observed.** The tail does ZERO Asana calls — it reads only `anchor.entry_task.custom_fields` for the exact requested gid.

## Tenant safety
- gid-exact / fail-closed: resolver result gid (1209877818531716) == anchor gid. The dynamic tail originates no Asana read; it consumes only the gid's own already-fetched manifest. No value sourced from any other gid/tenant. **PASS.**

## Verdict
All four realization predicates and all adversarial /qa probes PASS on live Asana, on a positively-selected real OFFER entity with a populated multi-token Asset ID. The override fired natively (no synthetic input, no entity-type seam).

**Rung: verified_realized EVIDENCE produced.** iris does NOT self-attest STRONG. The rite-disjoint review critic attests `verified_realized`. Banks the Contente N=1 pilot Step-1 (one live resolve).

## Receipt grammar (per-probe)
| probe | live evidence | result |
|---|---|---|
| client construct | AsanaClient() OK, PAT prefix 2/, ws 1143357799778608 | OK |
| PRED-1 HYP-1 | gid 1209877818531716, present+populated, raw "38790, 38789, 38788" | PASS |
| PRED-2 SET | override -> {"38788","38789","38790"}, origin=override, cf_type=text | PASS |
| PRED-3 governed-strict | UnresolvedError(unknown-field) on absent field | PASS |
| ADV present-but-null | gid 1215109436919600 raw=null -> value None (not empty set) | PASS |
| ADV date cf | gid 1215282122918903 "Edit Date" -> "2026-06-11", cf_type=date | PASS |
| TENANT gid-exact | result gid == anchor gid, zero tail Asana calls | PASS |
