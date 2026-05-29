---
name: tdd
description: This skill should be used when the user asks to "use TDD", "write this test-first", "apply test-driven development", "help me do TDD", "red green refactor", "write failing test first", "start with a test", or asks how to implement a feature using TDD. Provides the complete Red/Green/Refactor workflow from Kent Beck's 'Test Driven Development: By Example'.
---

# TDD: Test-Driven Development

Guide the user through Test-Driven Development using Kent Beck's methodology from *Test Driven Development: By Example*. TDD's goal is **clean code that works** — achieved through two rules:

1. **Write new code only if an automated test has failed**
2. **Eliminate duplication**

## The Red/Green/Refactor Cycle

Every TDD session follows this rhythm — never skip a step:

```
RED    → Write a little test that doesn't work (doesn't even compile is fine)
GREEN  → Make the test work quickly — commit whatever sins necessary
REFACTOR → Eliminate all duplication created in merely getting the test to work
```

The cycle should take **minutes**, not hours. If a step takes longer than ~10 minutes, the step is too big — break it down.

## Starting a TDD Session

### 1. Write the Test List

Before writing any code, write down every test that needs to pass. This is a scratch list — not formal, just on paper or a comment block:

```
// Test List
// - plus(3,1) returns 4
// - plus(3,4) returns 7  
// - handles negative numbers
// - handles zero
```

Include:
- Examples of every operation that needs implementation
- Null/empty versions of operations that don't exist yet
- Refactorings needed for clean code at the end

### 2. Pick the Next Test

Apply **One Step Test**: pick a test that will teach you something AND that you are confident you can implement quickly. Start with **Starter Test** — a variant that doesn't do anything, just establishes where the operation belongs.

Use this decision guide to pick the next test:

| Situation | Pick |
|-----------|------|
| First test of a new operation | **Starter Test** — trivial input (empty/zero/single), output same as input or trivially obvious |
| Familiar problem, confident in implementation | Largest step you're sure you can make green in < 5 min |
| Unfamiliar problem or algorithm | Smallest step that teaches you one new thing |
| Red bar > 10 min on current test | **Child Test** — break it into a smaller test for just the broken part |
| Nothing on the list feels implementable | Add simpler sub-tests to the list; pick the smallest one |

**Rule of thumb**: scan the list, mentally note "obvious, obvious, no idea, obvious..." — pick the last *obvious* one that still teaches you something new. Never pick a test that requires solving two unknowns simultaneously.

### 3. Write the Test (Assert First)

Write the **assert** first, then work backwards to fill in what's needed:

```java
// Start here — what should be true when done?
assertEquals(4, plus(3, 1));

// What produced the result?
int result = plus(3, 1);
assertEquals(4, result);

// Where does plus() belong? Create the context.
Calculator calc = new Calculator();
assertEquals(4, calc.plus(3, 1));
```

Use **Test Data** that makes intent obvious. Never use the same constant to mean two different things (use `plus(3, 4)` not `plus(2, 2)` — avoids masking swapped-argument bugs).

Use **Evident Data** — put the calculation in the assertion so the relationship is obvious:
```java
// Bad
assertEquals(49.25, bank.convert(100, "USD", "GBP"));

// Good  
assertEquals(100 / 2 * (1 - 0.015), bank.convert(100, "USD", "GBP"), 0.001);
```

### 4. Make It Green (Three Strategies)

Choose based on confidence level:

| Strategy | When to use |
|----------|-------------|
| **Fake It** | Uncertain — return a constant, then generalize incrementally |
| **Triangulate** | Very uncertain — require two+ examples before abstracting |
| **Obvious Implementation** | Confident — just type the correct code |

**Fake It example**:
```python
# Test
assert result.summary() == "1 run, 0 failed"

# Fake it (GREEN immediately)
def summary(self):
    return "1 run, 0 failed"

# Then generalize (still GREEN)
def summary(self):
    return "%d run, 0 failed" % self.run_count

# Then generalize again (still GREEN)  
def summary(self):
    return "%d run, %d failed" % (self.run_count, self.failure_count)
```

**Triangulate** — only abstract when you have 2+ examples forcing it:
```java
assertEquals(4, plus(3, 1));
assertEquals(7, plus(3, 4));  // Now abstraction is forced
// → return augend + addend;
```

### 5. Refactor

Once GREEN, eliminate all duplication — between the test and the code, and within the code. Do NOT add features. Refactor only within a green bar.

Key refactorings (see `/tdd:patterns` for full list):
- **Extract Method** — pull duplicated logic into a named method
- **Reconcile Differences** — make two similar code paths identical, then eliminate one
- **Migrate Data** — when changing representation, temporarily duplicate then delete old

### 6. Repeat

- Pick the next test from the list
- Add new tests to the list as they occur to you during implementation
- Cross off completed tests

## Managing the Rhythm

**When the bar stays red too long** (more than ~10 minutes):
- Apply **Child Test**: write a smaller test for just the broken part
- Apply **Do Over**: throw away the code and start fresh (seriously — this works)
- Apply **Break**: take a physical break, wash hands, walk away

**When leaving a solo session**: leave the last test broken (Broken Test) — gives you an immediate restart point next time.

**When checking in on a team**: all tests must pass (Clean Check-in) — never comment out tests.

## Regression Tests

When a bug is reported:
1. Write the **smallest possible test** that reproduces the failure
2. Confirm it's red
3. Fix the code
4. Confirm it turns green
5. Never delete this test

## TDD Mantra for Courage

> "Tests are the teeth of the ratchet. Once we get one test working, we know it is working, now and forever. We are one step closer to having everything working than we were when the test was broken."
> — Kent Beck

TDD manages fear during programming. Instead of being tentative, it forces concrete learning. The heavier the problem, the smaller each test should be.

## Applying to the Current Task

When the user provides a feature or task:

1. Identify the first, simplest operation to implement
2. Write the Starter Test for it
3. Apply Red/Green/Refactor
4. Build up through the Test List
5. Retrospect: check code metrics, test quality, and design after finishing

## Additional Resources

- **`/tdd:patterns`** — All 40+ patterns from Part III of the book (Red Bar, Testing, Green Bar, xUnit, Design, Refactoring patterns)
- **`/tdd:review`** — Review existing code or tests for TDD compliance and quality
