---
name: tdd:patterns
description: This skill should be used when the user asks about "TDD patterns", "what pattern should I use", "mock object pattern", "fake it til you make it", "triangulate", "fixture setup", "test isolation", "xUnit patterns", "one step test", "starter test", "learning test", "regression test", "child test", "self shunt", "log string", "green bar patterns", "red bar patterns", "testing patterns", or any named pattern from Kent Beck's TDD book. Reference for all 40+ patterns from Part III of 'Test Driven Development: By Example'.
---

# TDD Patterns Reference

Complete pattern catalog from Part III of Kent Beck's *Test Driven Development: By Example*. These patterns answer the "how" and "when" of TDD at a granular level.

## Pattern Map

Patterns are grouped by the phase of TDD they address:

| Group | Purpose | Reference |
|-------|---------|-----------|
| **TDD Patterns** (Ch.25) | Core strategy — what and when to test | `references/tdd-core-patterns.md` |
| **Red Bar Patterns** (Ch.26) | When/where to write tests, when to stop | `references/red-bar-patterns.md` |
| **Testing Patterns** (Ch.27) | Detailed test writing techniques | `references/testing-patterns.md` |
| **Green Bar Patterns** (Ch.28) | Strategies for making tests pass | `references/green-bar-patterns.md` |
| **xUnit Patterns** (Ch.29) | Using xUnit-family frameworks | `references/xunit-patterns.md` |
| **Design Patterns** (Ch.30) | OO patterns that emerge from TDD | `references/design-patterns.md` |
| **Refactoring** (Ch.31) | Refactoring moves for the Refactor step | `references/refactoring-patterns.md` |
| **Mastering TDD** (Ch.32) | Advanced Q&A — step size, limits, teams | `references/mastering-tdd.md` |

## Quick Pattern Lookup

### "I don't know where to start"
→ **Starter Test** — test a variant that doesn't do anything yet  
→ **One Step Test** — pick a test that teaches something you're confident you can implement

### "I don't know what to implement"
→ **Fake It ('Til You Make It)** — return a constant; generalize step by step  
→ **Triangulate** — write a second example that forces the real abstraction

### "My test is too big / stuck red too long"
→ **Child Test** — write a smaller test for just the broken part  
→ **Do Over** — throw away the code, start fresh

### "How do I deal with shared setup?"
→ **Fixture** — move common setup to `setUp()`  
→ **External Fixture** — use `tearDown()` to release external resources

### "How do I test external libraries/APIs?"
→ **Learning Test** — write a test for the API before first use  
→ **Mock Object** — replace expensive/unpredictable objects with fakes

### "How do I isolate my test objects?"
→ **Isolated Test** — each test is independent, no shared state  
→ **Self Shunt** — the TestCase itself acts as the collaborator  
→ **Null Object** — replace conditional behavior with a do-nothing object

### "My test is hard to read"
→ **Evident Data** — make expected/actual relationships visible in the assertion  
→ **Test Data** — use minimal, meaningful data (not realistic noise)

### "When do I delete tests?"
→ See **Mastering TDD** reference — delete only when tests are fully redundant (subsumed by another test)

## Loading References

Load the relevant reference file when you need pattern details:

- Broad strategy → `references/tdd-core-patterns.md`  
- Writing/placing tests → `references/red-bar-patterns.md`
- Test mechanics → `references/testing-patterns.md`
- Making tests pass → `references/green-bar-patterns.md`
- Framework usage → `references/xunit-patterns.md`
- Design decisions → `references/design-patterns.md`
- Refactoring moves → `references/refactoring-patterns.md`
- Advanced/team TDD → `references/mastering-tdd.md`
