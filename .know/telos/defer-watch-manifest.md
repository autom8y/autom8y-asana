# Defer-Watch Manifest — autom8y-asana

> DEFER is a verdict, not a silence. Every entry holds a refutable watch-trigger
> predicate and a named reactivation. Peer of the knossos-level manifest
> (DEFER-2026-001..005) and the data-repo manifest (006..). Append-only in
> deferred state; reactivation transitions state, never deletes.

**Anchor-return question**: *Does each DEFER item have a refutable watch-trigger
AND a named reactivation — and is the scope-creep guard firing on any item
drifting into SHIP scope without a reactivation event?*

Cross-pointer: **DEFER-2026-008** (vocab-corpus Opt2 CI-ratchet) is owned by the
asana cutover-readiness session — registered upstream; not re-minted here.

```yaml
defer_entry:
  id: DEFER-2026-012
  title: "Fossil AUTOM8Y_DATA_API_KEY S2S seam — fleet retirement (gid/account-status pushes still ride it)"
  source_decision:
    artifact: autom8y-asana PR #189 (fix(scheduling): mint SA token for stratum push) + shot-B2 receipt 2026-07-02T11:21Z
    verdict_id: "scheduling-posture I2 leg — 401 AUTH-TEB-003 'Not enough segments'"
    deferred_at: 2026-07-02
  deferral_rationale:
    why_not_now: >
      #189 cured ONLY the stratum push (SA-mint injected via the auth_token seam).
      gid_push._get_auth_token (gid_push.py) and DataServiceClient token_key default
      ("AUTOM8Y_DATA_API_KEY", clients/data/config.py:231) still resolve the fossil
      secret autom8y/asana/autom8-data-api-key whose LIVE value is an 11-char
      single-segment stub (not a JWT; sha256 40978892). The working ECS task-def
      carries no such env. The gid-mappings/account-status pushes are best-effort
      broad-catch — they may be silently 401ing TODAY with no visible failure.
    smaller_change_available: true
    smaller_change_reference: "#189's ServiceTokenAuthProvider injection pattern — replicate per push site"
  watch_trigger:
    trigger_type: composite
    trigger_definition: >
      (i) any *_push_failed with status_code=401 AUTH-TEB-003 in the asana service or
      lambda logs, OR (ii) account_status/gid_mappings staleness observed in prod data
      (synced_at age beyond one push cadence), OR (iii) the next initiative touching
      gid_push.py for any reason.
    evaluation_cadence: at-session-start
    last_evaluated_at: 2026-07-02
    last_evaluation_result: PARTIALLY-MET (the stratum instance MET and cured; the sibling pushes unaudited)
  escalation_path:
    reactivation_signal_recipient: "10x-dev/potnia"
    reactivation_artifact_path: ".ledge/spikes/DEFER-2026-012-reactivation-handoff.md"
    reactivation_invocation: "/frame asana-s2s-fossil-key-retirement"
  owner_rite: 10x-dev
  scope_boundary:
    must_not_collapse_into:
      - scheduling-posture-primitive (its leg is cured; the FLEET seam is this entry)
    boundary_violation_signal: >
      Any edit to gid_push auth resolution or the DataServiceClient token_key default
      landing inside another initiative's PR without this entry's reactivation.

defer_entry:
  id: DEFER-2026-013
  title: "Snapshot lambda per-run Asana dependencies — discovery-call 429 fragility + swr_build_no_workspace"
  source_decision:
    artifact: shot-B3 receipt 2026-07-02T12:09Z (scheduling_stratum_snapshot_discovery_failed HTTP 429; 5 retries exhausted) + swr_build_no_workspace 12:01Z
    verdict_id: "scheduling-posture I2 leg — FORK-2 diagnose-not-weaken"
    deferred_at: 2026-07-02
  deferral_rationale:
    why_not_now: >
      Two per-run external dependencies remain in an otherwise pure frame-read path:
      (a) the project-gid DISCOVERY makes one live Asana call that fails when the token
      bucket is drained (e.g., by the tick's own SWR full rebuild of ~4.1k offers);
      (b) the lambda's in-process SWR rebuild fails with swr_build_no_workspace (no
      workspace ctx), so it cannot self-heal the frame it depends on. Both are
      transient-shaped and the completeness contract refuses honestly — but every
      6h tick that lands in a drained window burns a cycle.
    smaller_change_available: true
    smaller_change_reference: "cache/env-pin the constant offer project_gid (zero Asana calls at discovery); provide workspace ctx to the lambda SWR path"
  watch_trigger:
    trigger_type: empirical-count
    trigger_definition: >
      >=2 consecutive SCHEDULED (cron) ticks ending in snapshot_refused with
      discovery_failed/429 OR no_offer_frame in the same 24h window.
    evaluation_cadence: at-session-start
    last_evaluated_at: 2026-07-02
    last_evaluation_result: NOT-MET (manual shots only so far; no consecutive scheduled-tick pair observed)
  escalation_path:
    reactivation_signal_recipient: "10x-dev/potnia"
    reactivation_artifact_path: ".ledge/spikes/DEFER-2026-013-reactivation-handoff.md"
    reactivation_invocation: "/frame stratum-snapshot-zero-asana-discovery"
  owner_rite: 10x-dev
  scope_boundary:
    must_not_collapse_into:
      - scheduling-posture-primitive I2-proven-live attestation (the proof stands on ticks that succeed; this entry hardens cadence reliability)
    boundary_violation_signal: >
      Weakening assert_complete_office_set or retry-inflation to paper over 429s
      instead of removing the per-run Asana dependency.

defer_entry:
  id: DEFER-2026-014
  title: "SchedulingStratumStatusDrift metric refinements — null-vs-value blind spot + case-fold false-drift"
  source_decision:
    artifact: N3 qa-adversary report (PR #186), findings LOW-1/LOW-2; pinned by test_qa_d_drift_blind_spot_null_vs_value_pinned
    verdict_id: "frame-first N3 QA — GO with non-blocking findings"
    deferred_at: 2026-07-02
  deferral_rationale:
    why_not_now: >
      (1) the drift filter drops nulls pre-n_unique, so {null,"Inactive"} — a MATERIAL
      enrollment disagreement — never meters (scheduling_stratum_snapshot.py:257);
      (2) drift compares RAW strings, not _normalize_status-folded — "Active" vs
      "active" fires false drift (real-scale run: drift=500, mostly case/alias noise).
      Representative selection stays deterministic; safety unaffected; metering-only.
    smaller_change_available: false
    smaller_change_reference: ""
  watch_trigger:
    trigger_type: external-event
    trigger_definition: >
      Any initiative proposing to ALARM on SchedulingStratumStatusDrift (the noise
      floor makes the metric unalarmable until folded), OR a real drift incident
      investigated via this metric.
    evaluation_cadence: at-session-start
    last_evaluated_at: 2026-07-02
    last_evaluation_result: NOT-MET
  escalation_path:
    reactivation_signal_recipient: "10x-dev/potnia"
    reactivation_artifact_path: ".ledge/spikes/DEFER-2026-014-reactivation-handoff.md"
    reactivation_invocation: "/frame stratum-drift-metric-fold"
  owner_rite: 10x-dev
  scope_boundary:
    must_not_collapse_into:
      - any sre alarm-wiring initiative (fold FIRST, then alarm)
    boundary_violation_signal: "an alarm wired on the unfolded metric"
```
