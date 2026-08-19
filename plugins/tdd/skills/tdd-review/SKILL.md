---
name: tdd-review
description: This skill should be used when the user asks to "review my tests", "check my TDD", "is this good TDD", "review test quality", "check test design", "are my tests testing too much", "why is my test hard to write", "fragile tests", "slow tests", "test smell", "assess TDD compliance", or wants feedback on existing tests or test-driven code. Provides structured review of tests against Kent Beck's TDD principles.
---

# TDD Review

Review existing tests and test-driven code for quality and compliance with Kent Beck's TDD principles. Apply this review after reading the relevant files.

## Review Framework

Assess tests across four dimensions:

### 1. Test Design Quality

**Check for test smells** (each is a design signal, not just a test problem):

| Smell | Signal | Fix |
|-------|--------|-----|
| Long setup code (>20 lines) | Objects too large | Split objects; apply SRP |
| Setup duplication | Too many tightly coupled objects | Extract Fixture or redesign coupling |
| Tests longer than 10 lines | Testing too much at once | Apply Child Test; one assertion per test |
| Magic constants | Intent is hidden | Apply Evident Data |
| No assertions | Test is not testing anything | Add specific assertions |
| `assertTrue(x != null)` | Too weak | Assert the specific value |
| Testing private/internal state | Design problem | Test behavior, not implementation |

### 2. Isolation

**Each test should be isolated**:
- Can it run alone without other tests running first?
- Does it leave any shared state that affects other tests?
- Does it use real databases, network, or clocks? (Consider Mock Object or in-memory fakes)
- Are setUp/tearDown cleaning up all resources? (Especially External Fixture)

### 3. Coverage Completeness

**Check the Test List** was likely complete:
- Happy path tested?
- Edge cases (empty, null, zero, negative, single-element, max-element)?
- Error/exception paths tested? (Exception Test pattern)
- Boundary conditions tested?
- Are there regression tests for all known bugs?

### 4. TDD Process Evidence

**Assess whether tests were written test-first**:
- Tests focus on behavior, not implementation
- Tests are specific (not overly general)
- Test names describe scenarios, not implementation
- Tests didn't chase the implementation (no tests that say "verify the field is set")

## Review Output Format

Structure the review as:

```
## Test Quality Review

### Strengths
- [what's working well]

### Issues Found

#### Critical (block merge/checkin)
- [Issue]: [File:Line] — [Pattern to apply]

#### Warnings (should fix)  
- [Issue]: [File:Line] — [Suggestion]

#### Minor (consider fixing)
- [Issue]: [File:Line] — [Suggestion]

### Design Signals
[Any design problems revealed by the test smells]

### Missing Tests
[Important scenarios not covered]
```

## Applying the Review

When reviewing a file:

1. Read the test file completely
2. Identify the domain being tested
3. Apply the four-dimension framework
4. Look for patterns from `references/test-smells.md` for detailed diagnosis
5. Check the corresponding implementation file for design problems the tests reveal

## Quick Heuristics

**The single-assert guideline**: Each test should ideally have one assertion or check one behavior. Multiple assertions in one test make it hard to know which assertion failed.

**The "new programmer" test**: Could a new team member read this test and understand exactly what the system should do? If not, apply Evident Data and better naming.

**The "run alone" test**: Could you run just this test in isolation and have it pass? If not, there's hidden test coupling.

**The "design mirror" test**: Hard-to-test code almost always has a design problem. If setup is painful, the object is too large. If mocking is complex, there are too many dependencies.

## Additional Resources

- **`references/test-smells.md`** — Detailed catalog of test smells with diagnosis and fixes
