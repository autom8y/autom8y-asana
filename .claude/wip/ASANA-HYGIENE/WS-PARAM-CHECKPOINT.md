# WS-PARAM Checkpoint

## Session 1 (completed)

| ID | File | Before | After | Delta | Tests |
|----|------|--------|-------|-------|-------|
| LS-011 | test_unit_schema.py | 203 | 150 | -53 | 21 |
| LS-016 | test_normalizers.py | 257 | 229 | -28 | 35->37 |
| LS-012 | test_error_helpers.py | 816 | 810 | -6 | 71 |
| LS-013 | test_client_extensions.py | 495 | 441 | -54 | 35->43 |
| LS-019 | test_custom_field_descriptors.py | 1064 | 995 | -69 | 99 |
| LS-015 | test_executor.py | 354 | 330 | -24 | 19 |
| LS-020 | test_base_schema.py | 238 | 174 | -64 | 18->23 |
| LS-014 | test_models.py | -- | -- | skip | cluster absent |

**S1 Total**: -298 LOC, 390 passed, 1 skipped

---

## Session 2 (completed)

| ID | File | Before | After | Delta | Tests |
|----|------|--------|-------|-------|-------|
| LS-009 | test_cache.py | 869 | 799 | -70 | 23 |
| LS-010 | test_feature_flag.py | 437 | 285 | -152 | 17 |
| LS-017 | test_routes_admin_edge_cases.py | 280 | 225 | -55 | 12 |
| LS-018 | test_routes_dataframes.py | 1020 | 988 | -32 | 46 (pre-existing failures) |
| LS-021 | test_pii.py | 453 | 410 | -43 | 24 |
| LS-022 | test_session_healing.py | 798 | 780 | -18 | 48 |
| LS-023 | test_config.py | 189 | 187 | -2 | 17 |
| LS-024 | test_config_schema.py | 639 | 627 | -12 | 59 |

**S2 Total**: -384 LOC, 200 passed (7 green files), 46 pre-existing failures in test_routes_dataframes.py

---

## Combined Results

| Metric | S1 | S2 | Total |
|--------|----|----|-------|
| Clusters | 7 done, 1 skip | 8 done | 15 done, 1 skip |
| LOC Delta | -298 | -384 | -682 |
| Tests Verified | 390 | 200 | 590 |

**Full suite**: 9,611 passed, 2 skipped, 1 xfailed. 145 pre-existing failures in unrelated files (test_client_warm_cache.py, test_public_api.py, test_routes_dataframes.py).

## Observations

- **LS-010 yielded the largest S2 savings** (-152 LOC) from collapsing 8 env-var tests into 2 parametrized tests.
- **LS-018 has pre-existing test infrastructure failures**: All 42 non-limit tests return 422. Confirmed by running original from HEAD. Parametrization is correct but cannot verify independently.
- **Small clusters (LS-023, LS-024) yielded minimal savings** (-2 and -12 LOC respectively), as predicted in S1 observations. Still worth doing for consistency.
- **LS-021 removed 1 duplicate test** (two identical empty-string tests), reducing from 7 to 6 parametrized cases.
