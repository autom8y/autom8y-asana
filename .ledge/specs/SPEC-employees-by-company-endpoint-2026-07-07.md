---
type: spec
status: draft
date: 2026-07-07
initiative: client-onboarding-delivery
slug: contact-synthesis-card-on-play
phase: 2 (endpoint must be LIVE before Phase-2 build begins)
rung: authored (design altitude only)
owner: autom8y-data (builds the endpoint); autom8y-asana (consumes via autom8y-core SDK)
adr_of_record: ADR-contact-synthesis-card-on-play-2026-07-07.md (F-3 ruling)
source_artifact: A2-dependency-map.md §FORK F-3
---

# SPEC — employees-by-company endpoint (cross-satellite, Phase-2 trigger)

This spec is the handoff seed to autom8y-data's lane. The contract is authored here
at design altitude; autom8y-data builds and owns the endpoint. autom8y-asana consumes
it only after the SDK bump is published and the consumer floor pin is bumped.

**OWNER**: autom8y-data (G-PROPAGATE — this artifact is the handoff seed for their lane).
**Phase-2 trigger**: endpoint live on autom8y-data + autom8y-core SDK minor bump published
+ autom8y-asana floor pin bumped + lockfile regenned.

G-RUNG: everything = `authored`. No production code authored here; target repos
unmodified.

---

## 1. Seam Invariant (non-negotiable)

The new endpoint MUST preserve the existing unidirectional seam: **autom8y-asana →
autom8y-data**. autom8y-data MUST NOT import, call, or receive data from autom8y-asana.
Reconciliation (dedup/corroboration) lives on the autom8y-asana plane, where both
Asana contacts and employee records co-reside after the GET response.

Grounding: A2 §0 coupling three-check; ADR §3 Seam Invariant.
[DP:SRC-002 Martin DIP, MODERATE | 0.70] [DP:SRC-005 Evans bounded context, MODERATE | 0.70]
[AQ:SRC-006 Martin Acyclic Dependencies Principle, STRONG | 0.75]

---

## 2. Endpoint Contract

```
ENDPOINT
  Method + Path : GET /api/v1/employees/by-company/{company_guid}
  Path param    : company_guid — UUID v4
                  == BusinessRecord.guid == Business.company_id
                  (resolved at B1: workflow.py:566-568; join key per LB-5)
  Query params  : limit  (int, default 100)
                  cursor (str|null, opaque forward cursor)
                  active (bool, optional; default unset = return all)
  Auth posture  : S2S, IDENTICAL to existing DataServiceClient pattern —
                  BaseClient automatic token management
                  (data_service.py:154-158,193-207), base URL AUTOM8Y_DATA_URL
                  (default https://data.api.autom8y.io, data_service.py:130,141).
                  Bearer token. No new auth surface introduced.
  Success       : HTTP 200 ALWAYS on a well-formed guid, even when the company
                  has zero employees (mirror by-guid: never 404 on valid guid —
                  data_service.py:637-639).
  Response body : {
                    "data": [ EmployeeRecord, ... ],
                    "meta": {
                      "request_id": str,
                      "cursor":     str | null,
                      "has_more":   bool,
                      "count":      int
                    }
                  }
```

### EmployeeRecord schema

Fields the card needs (LB-2 parity with Contact entity `contact.py:82-97`):

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | str | Stable employees-plane key; join hook (`contact.py:87` `Contact.employee_id`) |
| `full_name` | str | Mandatory; maps to ContactCard.full_name at Phase-2 corroboration |
| `preferred_name` | str\|null | Nickname/preferred name; maps to ContactCard.nickname |
| `email` | str\|null | Corroboration key (casefolded-email dedup rule; see §4) |
| `role` | str\|null | Maps to ContactCard.role/position; vocabulary = autom8y-data's to define |
| `active` | bool | For optional `?active` query filter; present if supported by schema |

**Open field-availability question (autom8y-data's to confirm)**: does the employees
table carry `preferred_name`, `active`, and a populated `role` vocabulary? If any field
is absent, the Phase-2 card tier degrades gracefully to `full_name + email + employee_id`
only. The ContactCard contract handles nulls already. This is the Phase-2 unknown
flagged in ADR §12.

### Error posture

Mirror `_fetch_business_envelope` classifier chain (`data_service.py:748-779`) verbatim:

| Condition | Error class |
|-----------|-------------|
| `company_guid` does not match UUID v4 format | `400 INVALID_COMPANY_GUID_FORMAT` → `DataServiceValidationError` |
| 5xx / transport / timeout | `DataServiceUnavailableError` (retryable) |
| Malformed 200 body | `DataServiceError` |

### Pagination

Cursor-based. `meta.has_more + meta.cursor`. Most companies fit one page (default 100);
autom8y-asana loops on `has_more` only if set. Degenerate case: zero-employee company →
`{ "data": [], "meta": { "has_more": false, "count": 0 } }`.

---

## 3. SDK Addition (autom8y-core `clients/data_service.py`)

New methods beside `get_business_by_guid_async` at `:631`. These are the only changes
to autom8y-core for Phase-2:

```python
async def get_employees_by_company_async(
    self,
    company_guid: str,
    *,
    limit: int = 100,
    cursor: str | None = None,
) -> EmployeesResponse:
    """GET /api/v1/employees/by-company/{company_guid}"""
    ...

def get_employees_by_company(
    self,
    company_guid: str,
    *,
    limit: int = 100,
    cursor: str | None = None,
) -> EmployeesResponse:
    """Sync wrapper via self._run_sync(...)"""
    return self._run_sync(
        self.get_employees_by_company_async(company_guid, limit=limit, cursor=cursor)
    )
```

New models in `autom8y_core.models.data_service`:

```python
@dataclass
class EmployeeRecord:
    employee_id: str
    full_name: str
    preferred_name: str | None = None
    email: str | None = None
    role: str | None = None
    active: bool | None = None

@dataclass
class EmployeesResponse:
    data: list[EmployeeRecord]
    meta: EmployeesResponseMeta

@dataclass
class EmployeesResponseMeta:
    request_id: str
    cursor: str | None
    has_more: bool
    count: int
```

Error posture: reuses the existing `_fetch_business_envelope` classifier chain
(`data_service.py:733-779`) verbatim. No new error classes needed.

**SDK bump note**: minor version bump of `autom8y-core` (additive method + 2 new models;
non-breaking per semver). Consumer floor pin bump + lockfile regen required in
autom8y-asana before Phase-2 build. Cross-satellite; not executed in this spec.

---

## 4. Asana-Side Corroboration Rule

Lives in `contact_synthesis.py` on the autom8y-asana plane. NOT in autom8y-data.
This is where both datasets (Asana contacts + employee records) co-reside after the
GET response; reconciliation belongs here (ADR §F-3 option (b) rejection grounds).

```python
def _corroborate(
    asana_cards: list[ContactCard],
    employees: list[EmployeeRecord],
) -> list[ContactCard]:
    """
    Dedup and corroborate across Asana contacts and employee records.
    Returns a merged list of ContactCards with updated provenance.
    NEVER fuzzy / name-only merge. All joins are deterministic over recorded facts.
    """
    # Build employee lookups
    by_employee_id = {e.employee_id: e for e in employees}
    by_email = {
        e.email.strip().casefold(): e
        for e in employees
        if e.email
    }

    result: list[ContactCard] = []
    matched_employee_ids: set[str] = set()

    for card in asana_cards:
        emp: EmployeeRecord | None = None

        # Priority 1: exact employee_id match (contact.py:87)
        # Available only on the 4% of contacts that carry employee_id (A0)
        # [This field is set at Phase-2; at Phase-1 it is always None]

        # Priority 2: casefolded-email exact match
        if card.contact_email:
            emp = by_email.get(card.contact_email.strip().casefold())

        if emp:
            matched_employee_ids.add(emp.employee_id)
            result.append(ContactCard(
                full_name=card.full_name,
                nickname=card.nickname or emp.preferred_name,
                contact_email=card.contact_email,
                role=card.role or emp.role,
                provenance=Provenance.CORROBORATED,
                rank=card.rank,
                rank_reason=card.rank_reason + " — corroborated w/ employees",
            ))
        else:
            result.append(card)  # provenance stays ASANA

    # Append unmatched employee rows as EMPLOYEES provenance tier
    for emp in employees:
        if emp.employee_id not in matched_employee_ids:
            result.append(ContactCard(
                full_name=emp.full_name,
                nickname=emp.preferred_name,
                contact_email=emp.email,
                role=emp.role,
                provenance=Provenance.EMPLOYEES,
                rank=len(result) + 1,  # appended after Asana-sourced; re-rank if needed
                rank_reason="employees record (unmatched in Contacts plane)",
            ))

    return result
```

**NEVER fuzzy**: name-similarity, phonetic matching, and model-inference-based joins
are explicitly forbidden per operator ruling ("ranking must be deterministic-over-
recorded-facts").

---

## 5. Phase-2 Activation Checklist

Before any Phase-2 build begins, ALL of the following must be true:

- [ ] `GET /api/v1/employees/by-company/{guid}` is live on autom8y-data (staging verified)
- [ ] autom8y-core SDK minor bump is published to the artifact registry
- [ ] autom8y-asana consumer floor pin bumped in `pyproject.toml`
- [ ] autom8y-asana `uv.lock` regenerated with `UV_DEFAULT_INDEX=CodeArtifact`
  (per fleet-codeartifact-lock-routing memory)
- [ ] employees-table field availability (`preferred_name`, `active`, `role` vocabulary)
  confirmed by autom8y-data schema owner
- [ ] Phase-2 SPOF fallback implemented in `ContactSynthesis`: if the employees
  endpoint is unavailable → degrade to `provenance=asana`; do NOT hard-fail the PLAY
  comment (AP-B, ADR §10)
