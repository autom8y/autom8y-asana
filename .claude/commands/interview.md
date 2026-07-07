---
name: interview
description: "Interview methodology reference for structured requirements gathering. Use when: conducting a requirements interview, designing interview questions, calibrating interview depth. Triggers: interview patterns, question design, requirements gathering methodology."
invokable: skill
---

# Interview Methodology

> Reference material for conducting structured requirements interviews.

## The Inversion Principle

Traditional prompt engineering: user crafts the perfect prompt to get a good output.
Interview pattern: the model crafts the perfect questions to get a good spec.

This inversion works because:
- The model has seen thousands of specs and knows what's usually missing
- The user has domain knowledge the model can't infer
- Questions are cheaper than rework
- Structured options reduce cognitive load to seconds per decision

## Question Quality Heuristics

A good interview question:

1. **Couldn't be answered by reading the codebase.** If `grep` can answer it, don't ask it.
2. **Reveals a tradeoff the user hasn't considered.** "What happens when X fails?" not "Do you want X?"
3. **Has genuinely different options.** If one option is obviously correct, it's not a question — it's a recommendation. State it as such and move on.
4. **Narrows the solution space.** Each answer should eliminate possibilities, not add them.
5. **Is phrased for the user's level.** Don't ask implementation-level questions if the user is a PM. Don't ask product questions if the user is deep in the code.

## Phase Transition Signals

### UNDERSTAND → DESIGN
Move when you can answer: "What are we building, for whom, and what constraints exist?"
Signals: user has stated intent, success criteria are clear, scope boundaries exist.

### DESIGN → REVIEW
Move when you can answer: "How will we build it and what tradeoffs did we make?"
Signals: architecture is chosen, key decisions are made, edge cases are addressed.

### REVIEW → PLAN
Move when the user confirms: "Yes, that captures my intent."
Signals: synthesis presented, no contradictions, no new requirements surfaced.

## Schemas

### Question Pattern Schema
[question-patterns.md](schemas/question-patterns.md) - Structured question templates by category

### Spec Artifact Schema
[spec-format.md](schemas/spec-format.md) - Output format for interview artifacts
