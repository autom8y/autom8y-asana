"""QA-adversary probes for TD-007 honest-observability prohibition.

ADVERSARIAL test (QA stream) targeting:
  R7  the PROHIBITION ("success_rate must not be read without serving_stale
      co-available"). The implementer enforces it via the co-reporting accessor
      success_rate_with_stale_context. This probe asks: can the prohibition be
      BYPASSED? i.e. is the bare receiver_query_success_rate() still publicly
      callable without the stale context? It is — so the enforcement is a
      CONVENTION (use the accessor), not a hard structural impossibility. We pin
      that reality so the verdict does not over-claim "structural".

ISOLATION NOTE: the receiver-query / serving-stale metrics are PROCESS-GLOBAL
Prometheus counters with no per-test reset. These probes therefore use DEDICATED
arm names (``qa_probe_*``) and assert only PER-ARM rates + monotonic deltas — they
never write the shared "project"/"section" arms, so they cannot pollute the
implementer's exact-ratio assertions under xdist. (The implementer's
test_success_rate_per_arm_and_combined asserts exact absolute values on the shared
"project"/"section" arms; that is a pre-existing xdist-order fragility, flagged in
the QA verdict — not re-created here.)
"""

from __future__ import annotations

from autom8_asana.api import metrics


def test_prohibition_is_convention_not_hard_enforcement() -> None:
    """The bare success-rate function remains callable WITHOUT stale context.

    success_rate_with_stale_context() co-returns the stale total, but
    receiver_query_success_rate() is still a public module function a dashboard
    or gate can call in isolation — obtaining a potentially-flattered rate with
    NO stale context. The prohibition is therefore a usage convention enforced by
    "use the accessor", not a structural guarantee. (Acceptable for an in-process
    metric module, but the re-gate/dashboard owner must actually call the
    co-reporting accessor; the code cannot force it.)
    """
    arm = "qa_probe_prohibition"
    metrics.record_receiver_query_outcome(arm, success=True)

    # Bare call succeeds and yields a float with no stale context attached.
    bare = metrics.receiver_query_success_rate(arm)
    assert bare is not None and isinstance(bare, float)

    # The sanctioned accessor returns the SAME rate PLUS the stale total.
    rate, stale = metrics.success_rate_with_stale_context(arm)
    assert rate == bare
    assert isinstance(stale, float)


def test_combined_rate_is_flattered_when_stale_serves_inflate_2xx() -> None:
    """Demonstrate the flattering the prohibition exists to surface.

    On a dedicated arm, record 1 server_error + 9 successes, then 5 stale serves.
    The bare per-arm rate reads 0.9 with no hint the 2xx were padded by stale
    serves; only the co-reported stale_total exposes it. The adversary's point:
    the receiver CANNOT stop a caller from reading the bare rate.
    """
    arm = "qa_probe_flattered"
    for _ in range(9):
        metrics.record_receiver_query_outcome(arm, success=True)
    metrics.record_receiver_query_outcome(arm, success=False)
    for _ in range(5):
        metrics.record_serving_stale(arm, 600.0)

    bare = metrics.receiver_query_success_rate(arm)
    rate, stale = metrics.success_rate_with_stale_context(arm)

    # Dedicated arm -> exact per-arm rate is safe regardless of global accumulation.
    assert bare == rate
    assert rate is not None and abs(rate - 0.9) < 1e-9
    assert stale >= 5.0  # only the accessor reveals the stale padding
