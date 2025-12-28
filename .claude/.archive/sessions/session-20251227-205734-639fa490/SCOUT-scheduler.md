# SCOUT: Scheduler Integration for Daily Polling

## Problem Statement

The pipeline automation feature needs reliable daily job execution for:
- Polling Asana for tasks matching trigger conditions
- Evaluating time-based conditions (stale, deadline, age)
- Daily cadence (not real-time webhooks)

**Key Constraints** (from stakeholder requirements):
- Log and continue on failure (no single-task failure should stop the run)
- Drop and log on API outage (graceful degradation)
- 30-day log retention (external concern, but scheduler must emit proper logs)
- Boring technology, Python-first

## Options Evaluated

| Option | Maturity | Ecosystem | Fit | Risk |
|--------|----------|-----------|-----|------|
| **APScheduler** | High (2009+) | Strong | High | Low |
| **schedule** | Medium (2013+) | Moderate | Medium | Low |
| **OS cron** | Excellent (1975+) | Universal | High | Medium |
| **systemd timers** | High (2010+) | Linux-only | Medium | Medium |

## Analysis

### Option 1: APScheduler (Advanced Python Scheduler)

**Pros:**
- Feature-rich: cron syntax, interval, date-based scheduling
- Job persistence (SQLAlchemy, Redis, MongoDB stores)
- Built-in retry and failure handling
- Observability: job events, listeners
- 5K+ GitHub stars, actively maintained
- Async support (AsyncIOScheduler)

**Cons:**
- Heavier than needed for single daily job
- Requires understanding of job stores, executors
- In-process: scheduler dies when process dies (unless daemon mode)

**Fit Assessment:** Strong fit for in-process scheduling with observability. Overkill if only external cron is used.

### Option 2: schedule (Simple Python Scheduling)

**Pros:**
- Dead simple API: `schedule.every().day.at("06:00").do(job)`
- Zero configuration
- Pure Python, no dependencies
- 11K+ GitHub stars, actively maintained

**Cons:**
- No built-in persistence
- No job failure handling (must wrap yourself)
- Requires long-running process
- No async support (blocks thread)

**Fit Assessment:** Good for development/simple deployments. Not suitable for production without additional infrastructure.

### Option 3: OS-level cron

**Pros:**
- Battle-tested (50 years of production use)
- Zero Python dependencies
- Runs regardless of application state
- Universal: every Unix/Linux/macOS system
- Natural separation: cron triggers, Python executes

**Cons:**
- Configuration outside Python (ops burden)
- No built-in observability (logs to syslog/cron.log)
- Limited error handling (exit codes only)
- Requires deployment infrastructure

**Fit Assessment:** Strong fit for production. Natural separation of concerns. Requires wrapper script for structured logging.

### Option 4: systemd timers

**Pros:**
- Integrated with systemd ecosystem
- Persistent timers (survives reboots)
- Good logging (journald integration)
- Dependency ordering with services

**Cons:**
- Linux-only (not macOS/Windows)
- Configuration is external (unit files)
- Learning curve for systemd syntax
- Overkill for single timer

**Fit Assessment:** Good for Linux-only deployments. Platform lock-in is acceptable only if Linux is committed.

## Recommendation

**Verdict**: Adopt

**Choice**: Hybrid approach - APScheduler for development/testing, cron for production

**Rationale:**

1. **Matches stakeholder requirements:**
   - Daily polling: Both APScheduler and cron handle daily schedules trivially
   - Log and continue: APScheduler has job listeners; cron wrapper handles this
   - Graceful degradation: Job wrapper catches API outages, logs, exits cleanly
   - Boring technology: cron is as boring as it gets; APScheduler is well-established

2. **Architecture:**

   ```
   Production:
   cron (06:00 daily) --> python -m autom8_asana.automation.cli run-triggers
                                    |
                                    v
                          Structured logging to stdout --> journald/CloudWatch

   Development:
   APScheduler (in-process) --> Trigger evaluation
                                    |
                                    v
                          Console logging for debugging
   ```

3. **Implementation sketch:**

   ```python
   # cli.py - Entry point for cron
   import sys
   import structlog

   logger = structlog.get_logger(__name__)

   def run_triggers():
       """Main entry point for daily trigger evaluation."""
       try:
           logger.info("trigger_run_started")
           engine = AutomationEngine.from_config()
           results = engine.evaluate_all_triggers()

           for result in results:
               if result.success:
                   logger.info("trigger_evaluated", trigger=result.trigger_id, matched=result.matched_count)
               else:
                   logger.warning("trigger_failed", trigger=result.trigger_id, error=result.error)

           logger.info("trigger_run_completed", total=len(results), failed=sum(1 for r in results if not r.success))

       except APIOutageError as e:
           logger.error("api_outage", error=str(e))
           sys.exit(1)  # Cron can retry on next run or alert on repeated failures

   if __name__ == "__main__":
       run_triggers()
   ```

   ```cron
   # /etc/cron.d/autom8-triggers
   0 6 * * * autom8 /usr/bin/python -m autom8_asana.automation.cli run-triggers >> /var/log/autom8/triggers.log 2>&1
   ```

4. **Development mode with APScheduler:**

   ```python
   # For local development/testing
   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   from apscheduler.triggers.cron import CronTrigger

   scheduler = AsyncIOScheduler()
   scheduler.add_job(run_triggers, CronTrigger(hour=6, minute=0), id="daily_triggers")
   scheduler.start()
   ```

5. **Dependency profile:**
   - Production: Zero additional dependencies (cron is OS-level)
   - Development: `apscheduler>=3.10.0` (optional dev dependency)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cron misconfiguration | Medium | Medium | Infrastructure-as-code, test in staging |
| Long-running job blocks next | Low | Low | Add timeout (e.g., 30 min max), alerting |
| Timezone confusion | Medium | Low | Use UTC everywhere, document clearly |
| Missed runs (server down) | Low | Low | Catchup logic: check last_run timestamp on startup |
| Dev/prod parity gap | Medium | Medium | Integration tests run full trigger evaluation |

## Decision Summary

| Criterion | Hybrid (cron+APScheduler) | Pure APScheduler | Pure cron |
|-----------|---------------------------|------------------|-----------|
| Production reliability | Excellent | Good | Excellent |
| Dev experience | Good | Excellent | Poor |
| Dependency footprint | Minimal (prod) | APScheduler always | Zero |
| Observability | Structured logs | Job events | Exit codes only |
| Ops complexity | Low (familiar) | Medium | Low |

**Bottom line:** Use cron for production (zero dependencies, universal, proven) with APScheduler as optional dev dependency for local testing. The CLI entry point is the common interface that both invoke.

## Alternative Considered: schedule library

While simpler than APScheduler, the schedule library provides no meaningful advantage:
- Still requires long-running process
- No persistence or failure handling
- Not suitable for production without additional infrastructure

If cron is available (which it is on all target platforms), there's no reason to prefer in-process scheduling in production.
