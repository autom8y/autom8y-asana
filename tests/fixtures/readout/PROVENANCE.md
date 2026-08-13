# readout fixtures — provenance

Both `rows_response_item1a.json` and `rows_response_item1a_truncated.json` are
**SYNTHETIC** `POST /v1/query/offer/rows` responses, hand-authored for EX-5
(WS-2). They are NOT captured from a live call: the live worked render is EX-5
exit criterion 1, which is operator/credential-gated (CR-5) and EXIT-HELD pending
Q-2. No authenticated call was fired to produce these.

They match the canonical double-envelope shape
(`SuccessResponse[RowsResponse]`, `src/autom8_asana/query/models.py:523-557`):
`{"data": {"data": [rows], "meta": {RowsMeta}}}`.

## Deterministic item-1a figure over these bytes

In-scope sections (the request's declared scope, `n`): `Discovery`,
`Negotiation`, `Onboarding`, `Closed Won` — so `n = 4`.

Per-section `max(last_modified)`:

| section     | max(last_modified)     | contributes to `k`? |
|-------------|------------------------|---------------------|
| Discovery   | 2026-08-12T09:00:00Z   | yes                 |
| Negotiation | 2026-08-11T14:30:00Z   | yes                 |
| Onboarding  | 2026-08-08T10:00:00Z   | yes (the min floor) |
| Closed Won  | (no rows)              | no                  |

So `k = 3`, `n = 4`, and the DR-2 `min` floor (the say-able `t_s`) is
**2026-08-08T10:00:00Z** — the oldest per-section max. `Closed Won` is in scope
but contributed nothing, which is exactly what the `k of n` denominator
discloses.

## The two fixtures differ ONLY in `meta`

* `rows_response_item1a.json` — `total_count == returned_count == 6`: NOT
  truncated. The F-2 truncation branch is declared-and-absent.
* `rows_response_item1a_truncated.json` — `total_count 20`, `returned_count 6`,
  `limit 6`: TRUNCATED. The F-2 truncation branch is present and contributes
  OVERSTATE_AGE (a dropped max-bearing row can only push the floor older). The
  rows are identical, so this isolates the truncation branch to the `meta`
  signal alone.
