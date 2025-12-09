# Glossary

> Canonical definitions for domain terms. Use these terms consistently across all documentation and code.

## How to Use This Document

- **When writing**: Use the exact term defined here, not synonyms
- **When reading unfamiliar terms**: Check here first
- **When terms are ambiguous**: Add clarification here
- **When introducing new concepts**: Add them here before using in PRDs/TDDs

---

## Domain Terms

### {Term}
**Definition**: {Clear, concise definition}
**Also known as**: {Synonyms to avoid - use the canonical term instead}
**Example**: {Concrete example}
**Not to be confused with**: {Similar but different concepts}

---

<!--
TEMPLATE - Copy and fill for each term:

### Term
**Definition**:
**Also known as**:
**Example**:
**Not to be confused with**:

-->

## Example Entries (Replace With Your Domain)

### Campaign
**Definition**: A coordinated marketing effort with defined start/end dates, budget, and target audience.
**Also known as**: (Don't use) "ad set", "promotion", "initiative"
**Example**: "Q4 Holiday Campaign targeting returning customers"
**Not to be confused with**: Ad Group (a subset within a campaign)

### Lead
**Definition**: A potential customer who has expressed interest but not yet converted.
**Also known as**: (Don't use) "prospect", "contact"
**Example**: A user who submitted a contact form but hasn't booked an appointment
**Not to be confused with**: Customer (has completed a conversion), Visitor (anonymous, no contact info)

### Conversion
**Definition**: A completed desired action that represents business value.
**Also known as**: (Don't use) "sale", "signup"
**Example**: Booked appointment, completed purchase, signed contract
**Not to be confused with**: Lead (interest expressed but not converted), Engagement (interaction without conversion)

### Practice
**Definition**: A single business location operated by a client (e.g., one chiropractic office).
**Also known as**: (Don't use) "location", "clinic", "office"
**Example**: "Dr. Smith's Downtown Practice"
**Not to be confused with**: Organization (may own multiple practices), Provider (individual practitioner)

---

## Technical Terms

### Repository
**Definition**: An abstraction over data access that returns domain entities.
**Context**: Used when we need to decouple domain logic from storage implementation.
**See**: ADR-XXXX for when to use vs. direct queries

### Aggregate
**Definition**: A cluster of domain objects treated as a single unit for data changes.
**Context**: The aggregate root is the only entry point for modifications.
**Example**: Order (root) + OrderItems (children) form an aggregate

### Correlation ID
**Definition**: A unique identifier that traces a request across service boundaries.
**Format**: UUID v4
**Header**: `X-Correlation-ID`

---

## Acronyms

| Acronym | Expansion                     | Definition                                       |
| ------- | ----------------------------- | ------------------------------------------------ |
| PRD     | Product Requirements Document | Defines what and why                             |
| TDD     | Technical Design Document     | Defines how (architecture)                       |
| ADR     | Architecture Decision Record  | Captures why a decision was made                 |
| SLA     | Service Level Agreement       | Contractual performance targets                  |
| NFR     | Non-Functional Requirement    | Quality attributes (performance, security, etc.) |

---

## Anti-Glossary (Terms to Avoid)

| Don't Use          | Use Instead                              | Why                                 |
| ------------------ | ---------------------------------------- | ----------------------------------- |
| "User" (ambiguous) | Customer, Admin, Visitor, Lead           | Different behaviors and permissions |
| "Data" (vague)     | Specify: metrics, records, payload, etc. | Too generic                         |
| "System" (vague)   | Name the specific component              | Unclear scope                       |
| "Handle" (vague)   | process, validate, transform, route      | Unclear action                      |
| "Misc" / "Utils"   | Name by purpose                          | Becomes a dumping ground            |
