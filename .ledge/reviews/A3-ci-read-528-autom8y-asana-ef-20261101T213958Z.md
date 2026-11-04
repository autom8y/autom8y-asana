---
type: review
status: closed
clerk_start_row: 19791
---

# A3 receipt: CI on asana #528, read by check and by node

- Stamped 2026-11-01T21:39:58Z (date -u). First read 21:34:42Z (inside the window); settled 21:38:57Z. Light gh reads only; no rerun, push, comment or merge.
- Head a2ce998d6bd3. Test run 41352582670. Census SET; direnv hook defined, not wired.

## Every check by name

| Check | Result |
|---|---|
| Added lines of the merge surface | pass |
| Aegis Memory & Coverage Gate | pass |
| Analyze (actions) | pass |
| Analyze (javascript-typescript) | pass |
| Analyze (python) | pass |
| CodeQL | pass |
| CodeRabbit | pass |
| Fleet Schema Governance | pass |
| Fuzz Tests (Hypothesis/Schemathesis) | pass |
| Isolated tests (worker_isolated, non-blocking) | pass |
| Lint noqa Drift Guard (RUF100) | pass |
| MCP Island Suite (mcp/ own pyproject + teeth canary) | pass |
| Semgrep layer rules | pass |
| ci / Aggregate Coverage Gate | pass |
| ci / Fleet Conformance Gate | pass |
| ci / Lint & Type Check | pass |
| ci / Matrix Prep | pass |
| ci / OpenAPI Spec Drift | pass |
| ci / Semantic Score Gate | pass |
| ci / Spectral Fleet Validation | pass |
| ci / Test (shard 1/4) | pass |
| ci / Test (shard 2/4) | pass |
| ci / Test (shard 3/4) | pass |
| ci / Test (shard 4/4) | pass |
| dependency-review / Dependency Review | pass |
| gitleaks | pass |
| gitleaks / Secrets Scan | pass |
| ci / Convention Check | skipping |
| ci / Integration Tests | skipping |

27 pass, 2 skipping (ci / Integration Tests, ci / Convention Check), 0 fail.

## Shard totals (from the four shard logs)

```
===== 4265 passed, 11 skipped, 1 xfailed, 58 warnings in 273.27s (0:04:33) =====
===== 4264 passed, 11 skipped, 2 xfailed, 42 warnings in 277.08s (0:04:37) =====
=========== 4266 passed, 9 skipped, 44 warnings in 243.11s (0:04:03) ===========
===== 4267 passed, 8 skipped, 1 xfailed, 40 warnings in 294.04s (0:04:54) ======
```

## The four test files, by node (from the shard logs; xdist `[gwN] PASSED <node>` lines)

| File | Nodes | Result |
|---|---|---|
| tests/unit/automation/workflows/test_leads_consumer.py | 9 | PASSED |
| tests/unit/canary/test_grain_bridge_canary.py | 5 | PASSED |
| tests/unit/enrollment/test_intent_projection.py | 79 | PASSED |
| tests/unit/enrollment/test_r03_phone_field_contract.py | 8 | PASSED |

101 nodes, 0 FAILED, 0 ERROR, 0 SKIPPED. Every node of test_r03_phone_field_contract.py is PASS (8 of 8: 2 valid, 4 malformed, 2 wrap). The values `555-0100` and `not-a-phone` in node ids are the test's own malformed fixtures, not phone data.

### Node list

```
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_401_credential_error_halts_run
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_403_scope_error_halts_run
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_empty_active_set_no_mint_no_fallback
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_leads_path_uses_per_business_provider_never_fleet
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_no_office_phone_skips_inactive_without_mint
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_per_business_client_is_closed
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_reconciliation_invariant_across_mixed_batch
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_skip_before_mint_does_not_build_client
PASSED tests/unit/automation/workflows/test_leads_consumer.py::test_stale_cache_not_counted_as_success
PASSED tests/unit/canary/test_grain_bridge_canary.py::test_tc_green_owned_resolves_and_reads
PASSED tests/unit/canary/test_grain_bridge_canary.py::test_tc_red_cross_tenant_refused_no_mint_no_read
PASSED tests/unit/canary/test_grain_bridge_canary.py::test_tc_red_minter_raises_resolution_miss_directly
PASSED tests/unit/canary/test_grain_bridge_canary.py::test_tc_scope_no_arm_ever_requests_read_pii
PASSED tests/unit/canary/test_grain_bridge_canary.py::test_tc_teeth_gate_disabled_flips_red_to_mint_then_restores
PASSED tests/unit/enrollment/test_intent_projection.py::TestColumnPresenceGateIsIndependentOfData::test_gate_operates_on_column_names_only
PASSED tests/unit/enrollment/test_intent_projection.py::TestDeltaCeilingRefusal::test_GREEN_normal_delta_passes
PASSED tests/unit/enrollment/test_intent_projection.py::TestDeltaCeilingRefusal::test_RED_mass_change_refuses_the_whole_cycle
PASSED tests/unit/enrollment/test_intent_projection.py::TestDeltaCeilingRefusal::test_RED_unset_ceiling_refuses
PASSED tests/unit/enrollment/test_intent_projection.py::TestDeltaCeilingRefusal::test_refusal_is_at_the_boundary_not_approximate
PASSED tests/unit/enrollment/test_intent_projection.py::TestEmptyAndDegenerateFrames::test_empty_spine_projects_nothing_and_reports_zero
PASSED tests/unit/enrollment/test_intent_projection.py::TestEmptyAndDegenerateFrames::test_orphan_unit_holder_without_a_business_ancestor_is_dropped
PASSED tests/unit/enrollment/test_intent_projection.py::TestFrameKeyContract::test_frame_keys_are_derived_from_the_namespace_registry
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_GREEN_all_three_frames_fresh_passes
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_mixed_stale_and_unprovable_are_distinguished
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_any_single_stale_frame_refuses_the_cycle[business]
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_any_single_stale_frame_refuses_the_cycle[offer]
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_any_single_stale_frame_refuses_the_cycle[unit_holder]
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_every_stale_frame_is_named_not_just_the_first
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_unprovable_age_is_itself_a_refusal[business]
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_unprovable_age_is_itself_a_refusal[offer]
PASSED tests/unit/enrollment/test_intent_projection.py::TestFreshnessRefusal::test_RED_unprovable_age_is_itself_a_refusal[unit_holder]
PASSED tests/unit/enrollment/test_intent_projection.py::TestPhoneAuthority::test_normalization_is_strip_only_never_e164_canonicalizing
PASSED tests/unit/enrollment/test_intent_projection.py::TestPhoneAuthority::test_phoneless_spine_row_is_dropped_and_counted
PASSED tests/unit/enrollment/test_intent_projection.py::TestPhoneAuthority::test_write_key_comes_from_business_not_the_offer_stamp
PASSED tests/unit/enrollment/test_intent_projection.py::TestR11StampedCopyResidual::test_both_residual_directions_are_reported
PASSED tests/unit/enrollment/test_intent_projection.py::TestR11StampedCopyResidual::test_roster_only_phone_is_counted_not_silently_dropped
PASSED tests/unit/enrollment/test_intent_projection.py::TestR12UniverseFilterIsPhoneNotGuid::test_SIDE_A_guid_less_phone_bearing_office_survives_projection
PASSED tests/unit/enrollment/test_intent_projection.py::TestR12UniverseFilterIsPhoneNotGuid::test_SIDE_B_guid_cross_check_emits_on_ambiguity_without_excluding
PASSED tests/unit/enrollment/test_intent_projection.py::TestR12UniverseFilterIsPhoneNotGuid::test_unambiguous_guid_does_not_false_fire_the_cross_check
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_blank_status_is_bit_identical_to_none
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[0]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[1]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[active]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[disable]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[disabled]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[enable]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[enabled]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[Enabled]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[false]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[In
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[In-Active]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[inactive]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[Inactive]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[INACTIVE]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[None]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[off]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[on]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[pause]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[paused]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[pending]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[Some
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_provenance_never_changes_the_bit[true]
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_recognized_active_option_is_labelled_explicit
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_SIDE_A_unset_coerces_to_enabled_with_honest_provenance
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_SIDE_B_explicit_disabled_stays_out
PASSED tests/unit/enrollment/test_intent_projection.py::TestR1CoercionPoint::test_unknown_option_is_labelled_not_silently_enabled
PASSED tests/unit/enrollment/test_intent_projection.py::TestRefusalGrammarIsReusedNotInvented::test_enrollment_refusal_is_an_evaluation_refusal
PASSED tests/unit/enrollment/test_intent_projection.py::TestRefusalGrammarIsReusedNotInvented::test_required_column_tuples_are_exported_so_a_rename_trips_ci
PASSED tests/unit/enrollment/test_intent_projection.py::TestRefusalGrammarIsReusedNotInvented::test_schema_lag_reuses_the_normalizer_exception_type
PASSED tests/unit/enrollment/test_intent_projection.py::TestRepresentativeAndDrift::test_output_order_is_deterministic
PASSED tests/unit/enrollment/test_intent_projection.py::TestRepresentativeAndDrift::test_representative_is_max_last_modified_tie_broken_by_gid
PASSED tests/unit/enrollment/test_intent_projection.py::TestRepresentativeAndDrift::test_status_drift_is_metered_and_does_not_block_the_cycle
PASSED tests/unit/enrollment/test_intent_projection.py::TestRosterWall::test_completed_offer_is_terminal_override
PASSED tests/unit/enrollment/test_intent_projection.py::TestRosterWall::test_SIDE_A_sales_process_office_never_projects
PASSED tests/unit/enrollment/test_intent_projection.py::TestRosterWall::test_SIDE_B_active_and_activating_both_project
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_absent_columns_refuse_rather_than_projecting_null_intent
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_GREEN_complete_schema_projects
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_identity_column_refuses[company_id]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_identity_column_refuses[gid]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_identity_column_refuses[office_phone]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_intent_column_refuses[custom_cal_status]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_intent_column_refuses[gid]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_intent_column_refuses[last_modified]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_intent_column_refuses[parent_gid]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_roster_column_refuses[is_completed]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_roster_column_refuses[office_phone]
PASSED tests/unit/enrollment/test_intent_projection.py::TestSchemaLagRefusal::test_RED_missing_roster_column_refuses[section]
PASSED tests/unit/enrollment/test_intent_projection.py::TestUniverseFloorRefusal::test_a_one_row_floor_would_not_have_caught_the_observed_collapse
PASSED tests/unit/enrollment/test_intent_projection.py::TestUniverseFloorRefusal::test_GREEN_universe_at_or_above_floor_passes
PASSED tests/unit/enrollment/test_intent_projection.py::TestUniverseFloorRefusal::test_RED_collapsed_universe_refuses
PASSED tests/unit/enrollment/test_intent_projection.py::TestUniverseFloorRefusal::test_RED_unset_floor_refuses_rather_than_running_unbounded
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_malformed_refused[555-0100-Annotated0]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_malformed_refused[555-0100-Annotated1]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_malformed_refused[not-a-phone-Annotated0]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_malformed_refused[not-a-phone-Annotated1]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_newtype_wrap_is_identity_at_runtime[LeadPhone]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_newtype_wrap_is_identity_at_runtime[OfficePhone]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_valid_e164_passes[Annotated0]
PASSED tests/unit/enrollment/test_r03_phone_field_contract.py::TestPhoneFieldContract::test_valid_e164_passes[Annotated1]
```
