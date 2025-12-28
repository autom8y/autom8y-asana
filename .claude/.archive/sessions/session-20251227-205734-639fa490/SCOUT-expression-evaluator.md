# SCOUT: Expression Evaluator for Trigger Conditions

## Problem Statement

The pipeline automation feature needs to evaluate boolean expressions for trigger conditions:
- `section == "ACTIVE" AND days_in_section > 30`
- `due_date < today + 7 AND status != "COMPLETED"`
- Field whitelist enforcement (devs own schema)
- Boolean logic composition (start simple, expand later)

**Key Constraints** (from stakeholder requirements):
- Safety: No arbitrary code execution
- Simplicity: Boring technology, minimal dependencies
- Error quality: Clear messages for config authors (Ops owns values)
- Extensibility: Start simple, expand to OR/NOT later

## Options Evaluated

| Option | Maturity | Ecosystem | Fit | Risk |
|--------|----------|-----------|-----|------|
| **Custom parser (hand-rolled)** | N/A (DIY) | None | Medium | Medium |
| **pyparsing** | High (2003+) | Strong | High | Low |
| **lark-parser** | High (2017+) | Strong | Medium | Low |
| **simpleeval** | Medium (2013+) | Moderate | High | Low |
| **Python AST + safe eval** | High (stdlib) | Excellent | Low | High |

## Analysis

### Option 1: Custom Parser (Hand-rolled)

**Pros:**
- Full control over syntax and behavior
- Zero dependencies
- Can be exactly minimal as needed

**Cons:**
- Maintenance burden increases with complexity
- Easy to introduce parsing bugs
- Error messages require significant effort to make user-friendly
- Expression syntax must be documented separately

**Fit Assessment:** Acceptable for trivially simple expressions (single comparison). Becomes costly as boolean composition grows.

### Option 2: pyparsing

**Pros:**
- Extremely mature (20+ years in production use)
- Pure Python, no C extensions
- Excellent error reporting with `set_name()` and `explain()`
- Well-documented grammar definition
- Already proven for expression evaluators (many examples in docs)
- 14K+ GitHub stars, active maintenance

**Cons:**
- Learning curve for grammar definition
- More powerful than strictly needed for simple boolean logic
- Some overhead for very simple expressions

**Fit Assessment:** Strong fit. Battle-tested for exactly this use case. Error messages are production-quality out of the box.

### Option 3: lark-parser

**Pros:**
- Modern, fast (LALR/Earley algorithms)
- EBNF-like grammar syntax (familiar to many)
- Good error handling
- 4K+ GitHub stars, active maintenance

**Cons:**
- More complex than needed for simple expressions
- Grammar compilation adds startup overhead
- Better suited for full language parsing than simple DSLs

**Fit Assessment:** Medium fit. Overpowered for the use case. Would be better if we were building a full configuration language.

### Option 4: simpleeval

**Pros:**
- Designed exactly for "safe expression evaluation"
- Minimal API surface
- Explicit function/variable whitelisting
- 600+ GitHub stars
- Very simple to integrate

**Cons:**
- Lighter ecosystem than pyparsing
- Less control over error messages
- Limited extensibility for custom operators

**Fit Assessment:** Strong fit for the "start simple" phase. May need to graduate to pyparsing for advanced composition.

### Option 5: Python AST + Safe Eval

**Pros:**
- Zero dependencies (stdlib only)
- Full Python syntax available

**Cons:**
- Significant security surface area
- AST allowlist maintenance is error-prone
- `ast.literal_eval` too restrictive; custom walker needed
- Easy to accidentally allow dangerous constructs
- Multiple CVEs in homegrown "safe eval" implementations

**Fit Assessment:** Poor fit. Security risk too high for the minimal dependency savings.

## Recommendation

**Verdict**: Adopt

**Choice**: simpleeval (immediate), with pyparsing escalation path

**Rationale:**

1. **Matches stakeholder requirements:**
   - Safety: simpleeval is designed for exactly this use case with explicit whitelisting
   - Simplicity: Single-purpose library, 600 LoC, pure Python
   - Start simple: Perfect for Phase 1 (AND-only, comparison operators)
   - Boring technology: Stable, 10+ years of production use

2. **Implementation sketch:**
   ```python
   from simpleeval import simple_eval, EvalWithCompoundTypes

   # Whitelist allowed fields (devs own schema)
   ALLOWED_NAMES = {"section", "days_in_section", "due_date", "status", "today"}
   ALLOWED_FUNCTIONS = {"abs": abs, "len": len}

   def evaluate_condition(expr: str, context: dict) -> bool:
       """Evaluate trigger condition against task context."""
       # Filter context to only whitelisted fields
       safe_context = {k: v for k, v in context.items() if k in ALLOWED_NAMES}
       safe_context["today"] = date.today()

       return simple_eval(
           expr,
           names=safe_context,
           functions=ALLOWED_FUNCTIONS,
       )
   ```

3. **Escalation path:**
   - When: Need custom syntax, better error messages, or complex composition (OR with precedence, NOT, parentheses)
   - Action: Migrate to pyparsing with a grammar like:
     ```python
     comparison = field + operator + value
     term = comparison | "(" + expr + ")"
     expr = term + ZeroOrMore(("AND" | "OR") + term)
     ```

4. **Dependency profile:**
   - simpleeval: Pure Python, no transitive deps
   - Already in pip, conda, conda-forge
   - MIT license (compatible)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| simpleeval insufficient for future needs | Medium | Low | Escalation path to pyparsing is documented and straightforward |
| Security bypass in simpleeval | Low | High | Pin version, monitor releases, add integration test with malicious inputs |
| Error messages unclear to Ops | Medium | Medium | Wrap exceptions with user-friendly messages referencing field whitelist |
| Expression complexity creep | Medium | Medium | Enforce expression complexity limit (e.g., max 3 comparisons) |

## Decision Summary

| Criterion | simpleeval | Alternative |
|-----------|------------|-------------|
| Safety | Designed for it | Custom requires careful implementation |
| Dependencies | 1 pure-Python lib | pyparsing heavier but still acceptable |
| Error messages | Adequate, wrappable | pyparsing better out-of-box |
| Learning curve | Minimal | pyparsing: 1-2 days |
| Time to implement | 1-2 hours | Custom: 1-2 days; pyparsing: 1 day |

**Bottom line:** Use simpleeval for V1. It is the boring choice that matches our constraints. Graduate to pyparsing only if expression complexity demands it.
