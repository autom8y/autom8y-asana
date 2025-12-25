# Playbook: Performance Optimization

> Identify and resolve performance issues

## When to Use

- Application is slow
- Scaling concerns
- User-reported latency
- Pre-launch optimization
- Resource consumption issues

## Prerequisites

- Performance metrics or user reports
- Profiling capability
- Baseline measurements

## Command Sequence

### Phase 1: Determine Scope

**Decision point**: What kind of performance issue?
- Code-level optimization → `/hygiene`
- Infrastructure/reliability → `/sre`
- Both → Start with `/sre`, then `/hygiene`

### Phase 2: Switch to Appropriate Team

For infrastructure issues:
```bash
/sre
```

For code optimization:
```bash
/hygiene
```

### Phase 3: Start Session

```bash
/start "Performance optimization for [area]" --complexity=MODULE
```
**Expected output**: Session created with appropriate team

### Phase 4: Assessment

**For SRE path**:
- Identify bottlenecks
- Review metrics and monitoring
- Assess infrastructure

**For Hygiene path**:
- Profile code
- Identify hot paths
- Assess algorithms

**Expected output**: Performance assessment report

### Phase 5: Remediation

Implement optimizations:
- Infrastructure changes (SRE)
- Code optimizations (Hygiene)
- Caching strategies
- Query optimization

**Expected output**: Optimized code/infrastructure

### Phase 6: Validation

Measure improvements against baseline.

**Expected output**: Performance comparison report

### Phase 7: Wrap Up

```bash
/wrap
```
**Expected output**: Optimization summary with metrics

## Variations

- **Quick wins**: Focus on obvious improvements
- **Deep dive**: Comprehensive profiling and optimization
- **Scaling prep**: Focus on capacity planning

## Success Criteria

- [ ] Baseline measurements taken
- [ ] Bottlenecks identified
- [ ] Optimizations implemented
- [ ] Improvements measured
- [ ] Regression tests added

## Team Coordination

```bash
# Full performance initiative:
/sre                           # Infrastructure assessment
/hygiene                       # Code optimization
/10x                          # Feature work if needed
```
