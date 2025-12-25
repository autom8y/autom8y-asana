# Complexity Matrix

> When to use which complexity level

---

## Universal Complexity Signals

| Signal | Suggests Lower | Suggests Higher |
|--------|---------------|-----------------|
| File count | 1-2 files | 5+ files |
| Dependencies | None/few | Many external |
| Risk | Low | High |
| Reversibility | Easy to undo | Hard to undo |
| Stakeholders | Just me | Multiple teams |
| Duration | Hours | Days/weeks |

---

## 10x-dev-pack Complexity

| Level | When to Use | Phases |
|-------|-------------|--------|
| **SCRIPT** | Single file, utility function, no new APIs | requirements, implementation |
| **MODULE** | New component, internal service, moderate scope | All 4 phases |
| **SERVICE** | New service, external APIs, infrastructure changes | All 4 phases |
| **PLATFORM** | Cross-cutting concerns, architectural shifts | All 4 phases + extra review |

### Signals for Each Level

**SCRIPT**:
- "Just a quick function"
- "Helper utility"
- "Small fix with test"
- No design decisions needed

**MODULE**:
- "New component"
- "Add feature to existing module"
- Some design decisions
- Tests required

**SERVICE**:
- "New API endpoint"
- "External integration"
- Database changes
- Performance considerations

**PLATFORM**:
- "Affects entire system"
- "Breaking change"
- "New architecture pattern"
- "Major dependency update"

---

## doc-team-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **PAGE** | Single doc page, README update | Single file |
| **SECTION** | Related pages, module docs | Directory |
| **SITE** | Full documentation refresh | Entire docs |

---

## hygiene-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **SPOT** | Single file cleanup, quick fix | 1-2 files |
| **MODULE** | Component refactor, pattern fix | Directory |
| **CODEBASE** | Full audit, systematic cleanup | Entire repo |

---

## debt-triage-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **QUICK** | Known debt items, fast wins | Targeted |
| **AUDIT** | Full debt inventory, strategic planning | Comprehensive |

---

## sre-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **TASK** | Single operational task | One system |
| **PROJECT** | Multi-step operational work | Related systems |
| **PLATFORM** | Infrastructure-wide changes | Entire platform |

---

## security-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **PATCH** | Single file, no auth/crypto | Minimal |
| **FEATURE** | New endpoints, data handling | Feature scope |
| **SYSTEM** | Auth, crypto, external integrations | Full system |

---

## intelligence-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **METRIC** | Single metric, existing events | One measurement |
| **FEATURE** | New feature instrumentation | Feature scope |
| **INITIATIVE** | Cross-feature analysis | Multi-feature |

---

## rnd-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **SPIKE** | Quick feasibility check | Time-boxed |
| **EVALUATION** | Full technology evaluation | Thorough |
| **MOONSHOT** | Paradigm shift exploration | Extensive |

---

## strategy-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **TACTICAL** | Single decision, existing data | Short-term |
| **STRATEGIC** | New market entry, major bet | Medium-term |
| **TRANSFORMATION** | Business model change | Long-term |

---

## Complexity Escalation Rules

### Always Escalate When:
- Security implications (any → FEATURE+)
- Breaking changes (any → SERVICE+)
- External API changes (any → SERVICE+)
- Data model changes (any → MODULE+)
- Multiple teams affected (any → SERVICE+)

### Safe to Stay Low When:
- Internal-only changes
- Test-only changes
- Documentation-only
- Config changes
- Purely cosmetic

---

## Questions to Determine Complexity

1. **How many files will change?**
   - 1-2: Lower level
   - 3-5: Middle level
   - 6+: Higher level

2. **Does this touch security/auth/crypto?**
   - Yes: At least FEATURE/MODULE
   - No: Continue assessment

3. **Are there external dependencies?**
   - Yes: At least SERVICE
   - No: Continue assessment

4. **Is this reversible easily?**
   - Yes: Can use lower level
   - No: Use higher level

5. **Who needs to review this?**
   - Just me: Lower level
   - My team: Middle level
   - Multiple teams: Highest level
