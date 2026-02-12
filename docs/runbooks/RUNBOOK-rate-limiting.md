# Rate Limiting Troubleshooting

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| HTTP 429 from Asana API | Exceeded Asana rate limits, burst traffic | [Asana Rate Limits](#problem-1-asana-rate-limits-exceeded) |
| HTTP 429 from API server | Client exceeded service-level limits | [Service Rate Limits](#problem-2-service-level-rate-limits-exceeded) |
| `RateLimitError` in logs | SDK hit Asana limits, retrying with backoff | [SDK Rate Limiter](#problem-3-sdk-rate-limiter-misconfigured) |
| Slow requests after burst | Token bucket depleted, waiting for refill | [Token Bucket Depletion](#problem-4-token-bucket-depleted) |
| 429 cascade during hierarchy warming | Micro-burst exceeds instantaneous limit | [Hierarchy Warming](#problem-5-hierarchy-warming-backpressure) |

## Background

This system has three layers of rate limiting:

| Layer | Component | Purpose | Limit |
|-------|-----------|---------|-------|
| **Asana API** | External | Protect Asana infrastructure | ~1500 req/min per PAT |
| **SDK (Client)** | `TokenBucketRateLimiter` | Respect Asana limits | 1500 req/60s (configurable) |
| **API Server** | SlowAPI middleware | Protect service infrastructure | 100 req/min per client (configurable) |

These are complementary, not competing. SDK layer prevents hitting Asana limits. Service layer prevents overload from external clients.

### Rate Limit vs. Concurrency Control

The SDK uses two complementary mechanisms:

- **TokenBucketRateLimiter**: Controls request RATE (tokens/second). Smooths sustained traffic over time windows.
- **AsyncAdaptiveSemaphore**: Controls CONCURRENCY (in-flight count). Uses AIMD to halve concurrency on 429, increment by 1 on success.

Both are active by default. The token bucket handles sustained-rate compliance. The semaphore handles burst protection via adaptive concurrency control.

## Problem 1: Asana Rate Limits Exceeded

### Symptoms

- HTTP 429 responses from Asana API (`api.asana.com`)
- Logs show `RateLimitError` with retry attempts
- Response headers include `Retry-After: <seconds>`
- Request latency spikes during retry backoff
- Multiple concurrent operations hitting API simultaneously

### Investigation Steps

1. **Check recent request volume**
   ```bash
   # Search logs for Asana API calls in last 5 minutes
   grep "GET\|POST\|PUT\|DELETE" application.log | grep api.asana.com | tail -100

   # Count requests per minute
   grep "api.asana.com" application.log | awk '{print $1}' | uniq -c
   ```

2. **Check rate limit headers from Asana responses**
   ```bash
   # Look for rate limit headers in debug logs (if enabled)
   grep "X-Asana-Rate-Limit" application.log | tail -10

   # Example response headers:
   # X-Asana-Rate-Limit-Remaining: 42
   # Retry-After: 30
   ```

3. **Check SDK rate limiter configuration**
   ```python
   # In config.py or settings
   # Default SDK rate limit: 1500 requests per 60 seconds
   rate_limit_config = RateLimitConfig(
       max_requests=1500,
       window_seconds=60
   )
   ```

4. **Identify concurrent operations**
   ```bash
   # Check for parallel batch operations, hierarchy warming, large section fetches
   grep "hierarchy_warming\|batch\|concurrent" application.log | tail -50
   ```

5. **Check retry backoff behavior**
   ```bash
   # Look for retry warnings with Retry-After values
   grep "rate_limit_429_received" application.log | tail -20
   # Example: "retry_after": 30, "attempt": 2
   ```

### Resolution

**If burst traffic (temporary spike)**:
- Wait for `Retry-After` duration. SDK retries automatically with exponential backoff.
- Monitor logs for `rate_limit_429_received` warnings to confirm retry success.
- No action needed if retries succeed within max attempts (default 5).

**If sustained over-limit (persistent 429s)**:
- Reduce SDK rate limit to stay below Asana threshold:
  ```python
  # In config
  rate_limit_config = RateLimitConfig(
      max_requests=1200,  # 80% of Asana limit for safety margin
      window_seconds=60
  )
  ```
- Verify rate limiter is shared across all client instances:
  ```python
  # Create shared rate limiter
  rate_limiter = TokenBucketRateLimiter(config=rate_config)

  # Inject into all clients
  client = AsanaHttpClient(config, auth, rate_limiter=rate_limiter)
  ```

**If concurrent operations causing bursts**:
- Reduce concurrency limits (AIMD ceiling):
  ```python
  # In ConcurrencyConfig
  concurrency = ConcurrencyConfig(
      read_limit=30,   # Lower ceiling (default 50)
      write_limit=10,  # Lower ceiling (default 15)
      aimd_enabled=True  # Ensure AIMD is active
  )
  ```
- AIMD will automatically halve concurrency on 429 and slowly recover.
- Monitor AIMD behavior: `grep "adaptive_semaphore" application.log`

**If circuit breaker opened**:
- Check circuit breaker status:
  ```python
  # CircuitBreakerConfig
  circuit_breaker = CircuitBreakerConfig(
      enabled=True,
      failure_threshold=5,  # Opens after 5 consecutive failures
      recovery_timeout=60.0,  # Seconds before half-open probe
  )
  ```
- Wait for `recovery_timeout` to allow half-open probes.
- If persistent failures, investigate root cause (not just rate limiting).

### Prevention

- Monitor rate limit consumption: track requests/minute over time
- Alert on 429 rate >1% of total requests
- Use AIMD adaptive concurrency (default enabled)
- Batch operations where possible to reduce total request count
- Enable circuit breaker for cascading failure protection
- Add jitter to scheduled/cron jobs to avoid thundering herd

## Problem 2: Service-Level Rate Limits Exceeded

### Symptoms

- HTTP 429 responses from your API server (not Asana)
- Error message: "Rate limit exceeded"
- Response headers include `Retry-After: <seconds>`
- Affects external clients calling your API
- Multiple requests from same IP or PAT prefix

### Investigation Steps

1. **Check SlowAPI rate limit configuration**
   ```bash
   # In settings or environment
   echo $RATE_LIMIT_RPM
   # Default: 100 requests per minute
   ```

2. **Identify rate-limited clients**
   ```bash
   # Check access logs for 429 responses
   grep "429" api_access.log | awk '{print $1}' | sort | uniq -c | sort -rn

   # Sample output:
   # 87 10.0.1.45
   # 23 10.0.1.67
   ```

3. **Check rate limit key type**
   ```bash
   # Rate limiting by PAT prefix (user isolation) or IP
   grep "rate_limit_key" application.log | tail -10
   # Example: "pat:01234567" or "ip:10.0.1.45"
   ```

4. **Verify limiter storage**
   ```python
   # In api/rate_limit.py
   # Default: in-memory (single instance only)
   # For multi-instance: Redis storage required
   limiter = Limiter(
       key_func=_get_rate_limit_key,
       default_limits=["100/minute"],
       # storage_uri="redis://..." for multi-instance
   )
   ```

### Resolution

**If legitimate traffic spike**:
- Increase service-level rate limit:
  ```bash
  # In environment or settings
  export RATE_LIMIT_RPM=200
  # Restart service to apply
  ```
- Verify PAT-based isolation working (different users get separate limits):
  ```bash
  grep "rate_limit_key" application.log | grep "pat:" | tail -20
  ```

**If single client abusing**:
- Identify client from logs (IP or PAT prefix)
- Contact client to reduce request rate or implement client-side caching
- Consider per-client custom limits if needed

**If multi-instance deployment**:
- Configure Redis storage for shared rate limit state:
  ```python
  # In api/rate_limit.py
  limiter = Limiter(
      key_func=_get_rate_limit_key,
      storage_uri="redis://redis-host:6379/0",
  )
  ```
- Without Redis, each instance has independent limits (effective limit × instance count)

**If rate limit too restrictive**:
- Review usage patterns: `grep "429" api_access.log | wc -l`
- Adjust limit based on capacity planning and infrastructure headroom
- Document new limits in API reference

### Prevention

- Monitor 429 rate per client/PAT
- Alert on sustained high 429 rate (>5% of requests)
- Use Redis storage for multi-instance deployments
- Document rate limits in API documentation
- Implement exponential backoff in client SDKs

## Problem 3: SDK Rate Limiter Misconfigured

### Symptoms

- Frequent 429s despite low overall request volume
- Token bucket empty messages in logs
- Requests artificially throttled
- Performance slower than expected
- Multiple rate limiter instances created

### Investigation Steps

1. **Check rate limiter configuration**
   ```python
   # In config.py
   rate_limit = RateLimitConfig(
       max_requests=1500,  # Token bucket capacity
       window_seconds=60,  # Refill window
   )
   # Effective rate: 1500/60 = 25 tokens/second
   ```

2. **Verify rate limiter sharing**
   ```bash
   # Check logs for rate limiter creation
   grep "RateLimiter" application.log | grep "created\|initialized"

   # Should see ONE instance, not multiple
   ```

3. **Check token bucket state**
   ```python
   # If logging enabled
   # Look for token acquisition in debug logs
   grep "token_bucket" application.log | tail -20
   ```

4. **Compare configured vs. actual Asana limits**
   - Asana limit: ~1500 requests/minute per PAT
   - SDK default: 1500 requests/60s (correct)
   - If misconfigured lower, SDK throttles unnecessarily

### Resolution

**If rate limit too conservative**:
- Increase to match Asana limits:
  ```python
  rate_limit = RateLimitConfig(
      max_requests=1500,
      window_seconds=60
  )
  ```
- Leave 10-20% safety margin to account for request timing variance

**If multiple rate limiter instances**:
- Create single shared instance and inject:
  ```python
  # Application initialization
  rate_limiter = TokenBucketRateLimiter(config=rate_config)

  # Inject into all clients
  client1 = AsanaHttpClient(config, auth, rate_limiter=rate_limiter)
  client2 = AsanaHttpClient(config, auth, rate_limiter=rate_limiter)
  ```
- Multiple instances defeat rate limiting (each has independent bucket)

**If window too small**:
- Asana limits are per-minute, not per-second
- Use `window_seconds=60` to match Asana's window
- Smaller windows can cause artificial throttling

### Prevention

- Always use shared rate limiter instance
- Match rate limit config to Asana's documented limits
- Log rate limiter initialization to verify single instance
- Test rate limiting behavior under load

## Problem 4: Token Bucket Depleted

### Symptoms

- Requests delayed even without 429s
- Logs show waiting for token acquisition
- Performance degradation after burst
- Gradual recovery as tokens refill
- No errors, just slow throughput

### Investigation Steps

1. **Check token refill rate**
   ```python
   # Refill rate = max_requests / window_seconds
   # Default: 1500 / 60 = 25 tokens/second
   rate = config.max_requests / config.window_seconds
   print(f"Token refill rate: {rate} tokens/second")
   ```

2. **Estimate time to recovery**
   ```python
   # If bucket fully depleted (rare)
   # Recovery time = max_requests / refill_rate
   recovery = config.max_requests / (config.max_requests / config.window_seconds)
   print(f"Full recovery time: {recovery} seconds")
   ```

3. **Check recent request burst**
   ```bash
   # Look for sudden spike in request volume
   grep "api.asana.com" application.log | awk '{print $1}' | uniq -c
   # High count in short window indicates burst
   ```

### Resolution

**If temporary burst (one-time event)**:
- Wait for token refill. Rate: 25 tokens/second (default config).
- Full bucket recovery: 60 seconds maximum.
- Monitor logs to confirm requests resume normal pace.

**If sustained high throughput needed**:
- Increase concurrency instead of rate limit:
  ```python
  # AIMD concurrency allows more in-flight requests
  # Token bucket still limits sustained rate
  concurrency = ConcurrencyConfig(
      read_limit=50,  # More concurrent requests
      aimd_enabled=True  # Adaptive control
  )
  ```
- Do NOT increase rate limit above Asana's threshold (1500/min)

**If batch operations depleting bucket**:
- Add inter-batch delays to spread load:
  ```python
  # For hierarchy warming (already implemented)
  HIERARCHY_BATCH_SIZE = 50
  HIERARCHY_BATCH_DELAY = 1.0  # seconds between batches

  # For custom batch operations
  for batch in chunks(items, batch_size=50):
      await process_batch(batch)
      await asyncio.sleep(1.0)  # Let tokens refill
  ```

**If frequent depletion during normal operations**:
- Review request patterns: unnecessary API calls, missing cache hits
- Add caching to reduce request volume
- Optimize query patterns (batch where possible)

### Resolution (continued)

**Emergency: bypass rate limiting temporarily**:
```python
# WARNING: Only for debugging/emergency
# Creates new client without rate limiter
client = AsanaHttpClient(
    config=config,
    auth_provider=auth,
    rate_limiter=None  # Disables rate limiting
)
# MUST re-enable after investigation
```

### Prevention

- Monitor token bucket utilization over time
- Alert on frequent bucket depletion
- Use caching to reduce API request volume
- Batch operations with inter-batch delays
- Prefer concurrent requests over rapid sequential requests

## Problem 5: Hierarchy Warming Backpressure

### Symptoms

- HTTP 429s during hierarchy warming phase
- Logs show `warm_hierarchy=True` followed by 429s
- Occurs after large section fetch (1000+ tasks)
- All 429s retry successfully but waste rate budget
- Example: "145 transient HTTP 429 responses during CONTACTS build"

### Investigation Steps

1. **Check hierarchy warming context**
   ```bash
   # Look for hierarchy warming operations
   grep "warm_hierarchy\|put_batch_async" application.log | tail -50

   # Check unique parent count
   grep "unique parent" application.log | tail -10
   # Example: "2,233 unique parent GIDs"
   ```

2. **Verify pacing configuration**
   ```python
   # In config.py
   HIERARCHY_PACING_THRESHOLD = 100  # Parents before pacing activates
   HIERARCHY_BATCH_SIZE = 50  # Parents per batch
   HIERARCHY_BATCH_DELAY = 1.0  # Seconds between batches
   ```

3. **Check 429 pattern**
   ```bash
   # Look for micro-burst pattern (many 429s in short window)
   grep "rate_limit_429_received" application.log | grep "hierarchy"

   # Check retry success
   grep "hierarchy.*retry.*success" application.log
   ```

4. **Verify semaphore configuration**
   ```python
   # hierarchy_semaphore limits concurrent parent fetches
   # Default: 10 concurrent requests
   # Check in cache/providers/unified.py
   ```

### Resolution

**If pacing disabled or threshold too high**:
- Verify pacing threshold appropriate for workload:
  ```python
  # Adjust in config.py
  HIERARCHY_PACING_THRESHOLD = 100  # Lower if needed
  ```
- For builds with 100+ unique parents, pacing auto-activates
- Below threshold, no pacing (micro-burst acceptable for small hierarchies)

**If batch size too large**:
- Reduce batch size to spread bursts:
  ```python
  HIERARCHY_BATCH_SIZE = 30  # Smaller batches (default 50)
  HIERARCHY_BATCH_DELAY = 1.5  # Longer delay (default 1.0s)
  ```
- Tradeoff: Adds `ceil(parents/batch_size) - 1` seconds to build time
- Example: 2,233 parents, batch=50, delay=1.0s → 44s overhead

**If semaphore too high**:
- Reduce concurrent hierarchy fetches:
  ```python
  # In cache/providers/unified.py
  hierarchy_semaphore = asyncio.Semaphore(5)  # Lower from 10
  ```
- Proportionally slows hierarchy warming (~2x slower)
- Only adjust if pacing alone insufficient

**If retries succeed (normal case)**:
- 429s during hierarchy warming are transient
- SDK retries with exponential backoff (automatic)
- All retries succeed: no data loss, just wasted time
- Cost: ~30s retry overhead + 145 wasted tokens
- If acceptable, no action needed

### Monitoring and Tuning

**Monitor hierarchy warming metrics**:
```bash
# Count 429s during hierarchy warming
grep "hierarchy.*429" application.log | wc -l

# Check total parents vs. batch threshold
grep "unique parent" application.log | tail -10

# Measure hierarchy warming duration
grep "hierarchy warming started\|hierarchy warming completed" application.log
```

**Calculate overhead**:
```python
# Inter-batch pause count
batches = ceil(unique_parents / HIERARCHY_BATCH_SIZE)
pauses = batches - 1

# Total added time
overhead_seconds = pauses * HIERARCHY_BATCH_DELAY

# Example: 2,233 parents, batch=50, delay=1.0s
# overhead = ceil(2233/50) - 1 = 44 pauses = 44 seconds
```

**Lambda timeout headroom**:
- Default Lambda timeout: 900 seconds (15 minutes)
- CONTACTS build: ~427s base + ~44s pacing overhead = 471s total
- Headroom: 429 seconds (7+ minutes)
- Safe for large builds within timeout limits

### Prevention

- Enable batch pacing for large hierarchies (default)
- Monitor 429 count during hierarchy warming
- Alert on excessive 429s (>50 per build)
- Tune batch size and delay based on entity type
- Review pacing threshold if small hierarchies affected

## Emergency Procedures

### Disable All Rate Limiting (Emergency Only)

**WARNING**: Only for critical debugging. Risks hitting Asana limits and account suspension.

```python
# Disable SDK rate limiting
client = AsanaHttpClient(
    config=config,
    auth_provider=auth,
    rate_limiter=None  # DANGEROUS: No rate limiting
)

# Disable AIMD adaptive concurrency
concurrency = ConcurrencyConfig(
    aimd_enabled=False  # Falls back to fixed semaphore
)
```

**When to use**:
- Diagnosing whether rate limiting is root cause
- Time-critical incident requiring maximum throughput
- Testing against Asana sandbox (not production)

**Impact**:
- High risk of 429s from Asana API
- Potential circuit breaker activation
- Possible account rate limit enforcement by Asana
- No backpressure protection

**Recovery**:
1. Re-enable rate limiting immediately after test
2. Monitor for 429s and circuit breaker state
3. Wait for rate limit window reset (60 seconds)
4. Resume normal operations

### Force AIMD Reset

**When concurrency stuck at low value after 429 cascade**:

```python
# AIMD state is internal to AsyncAdaptiveSemaphore
# No direct reset API (by design - self-healing)
# Recovery is automatic via additive increase

# Monitor recovery:
# grep "adaptive_semaphore.*current=" application.log | tail -20
```

AIMD recovers automatically:
- After multiplicative decrease (429), enters grace period (5s)
- After grace period, increments by 1 every 2s on success
- Example: Window=25 → Window=50 takes ~50s
- No manual intervention needed unless AIMD disabled

### Check Circuit Breaker State

```python
# Circuit breaker state is internal to CircuitBreaker instance
# No direct inspection API in v1

# Infer state from behavior:
# - Open: All requests fail immediately with CircuitBreakerOpenError
# - Half-open: Probes succeed/fail, state transitions
# - Closed: Normal operation

# Wait for recovery_timeout to pass (default 60s)
# Circuit breaker auto-transitions to half-open and probes
```

## Diagnostic Commands

### Check Rate Limit Configuration

```bash
# SDK rate limit config
grep "RateLimitConfig\|max_requests\|window_seconds" src/autom8_asana/config.py

# Service rate limit
grep "RATE_LIMIT_RPM\|rate_limit" api/config.py
echo $RATE_LIMIT_RPM
```

### Monitor Request Rate

```bash
# Count requests per minute
grep "api.asana.com" application.log \
  | awk '{print $1}' \
  | uniq -c \
  | awk '{print $2, $1 " req/min"}'

# Find peak request rate
grep "api.asana.com" application.log \
  | awk '{print $1}' \
  | uniq -c \
  | sort -rn \
  | head -1
```

### Analyze 429 Responses

```bash
# Count total 429s
grep "429\|RateLimitError" application.log | wc -l

# 429s by source (Asana vs. service)
grep "429" application.log | grep "api.asana.com" | wc -l
grep "429" application.log | grep -v "api.asana.com" | wc -l

# Retry-After values
grep "Retry-After" application.log \
  | awk -F: '{print $NF}' \
  | sort -n \
  | uniq -c
```

### Check Concurrency Limits

```bash
# AIMD configuration
grep "ConcurrencyConfig\|read_limit\|write_limit\|aimd_" src/autom8_asana/config.py

# AIMD state changes
grep "adaptive_semaphore" application.log \
  | grep "current=\|halving\|increment" \
  | tail -20
```

## Related Documentation

- [ADR: Hierarchy Backpressure Hardening](../design/ADR-hierarchy-backpressure-hardening.md) - Batch pacing design for hierarchy warming
- [PRD: AIMD Rate Limiting](../requirements/PRD-GAP-04-aimd-rate-limiting.md) - Adaptive concurrency control requirements
- [TDD: ASANA HTTP Migration](../architecture/TDD-ASANA-HTTP-MIGRATION-001.md) - SDK rate limiting architecture
- [SPIKE: Hierarchy Warming 429 Backpressure](../spikes/SPIKE-hierarchy-warming-429-backpressure.md) - Investigation of hierarchy warming 429s
- [API Reference](../api-reference/README.md) - Service-level rate limit documentation
