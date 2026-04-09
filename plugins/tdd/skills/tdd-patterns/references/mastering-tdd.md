# Mastering TDD (Chapter 32)

Advanced questions and answers about TDD practice — step size, limits, teams, and the philosophy behind the methodology.

---

## How large should your steps be?

Steps should be as small as possible while remaining productive. If you find yourself making obvious mistakes (off-by-one errors, type errors), make steps smaller. If tests are passing without thought, make steps bigger.

The feedback loop: Obvious Implementation requires perfect code on the first try. The more times you're surprised by red, the smaller your steps should be.

There is no universal step size — it depends on your confidence with the specific problem, your experience with the language and domain, and your current mental state. Adjust dynamically throughout the session.

---

## What don't you have to test?

- **Existing framework code** you didn't write (but do write Learning Tests for APIs you're unfamiliar with)
- **Getters/setters** that are completely trivial (though if you write them test-first, you find they're faster to write than you'd think)
- **Code you're confident in** — TDD is about managing fear, not enforcing a ritual

The answer is pragmatic: test things that could break, things where the behavior needs to be specified, things where the design isn't clear. Skip tests for things you're certain about.

---

## How do you know if you have good tests?

Good tests are a positive indicator of good design. Bad tests signal design problems:

**Long setup code**: If creating objects for one simple assertion takes 100 lines, the objects are too large and need to be split.

**Setup duplication**: If you can't find a common place for setup code, too many objects are tightly intertwined.

**Long running tests**: Tests that take too long won't be run often. Difficulty testing individual pieces suggests a design problem. Rule of thumb: a 10-minute test suite is the maximum before developers start skipping runs.

**Fragile tests**: Tests that break unexpectedly suggest that one part of the application is surprising affecting another. The solution is design change, not test fixing.

---

## How does TDD lead to frameworks?

Paradox: by not designing for the future, TDD makes code more adaptable to the future.

The pattern:
1. First feature: simple, straightforward implementation
2. Second feature (variant of first): duplication goes in one place; differences go in another
3. Third feature: framework emerges from the pattern of the first two; goes in with minimal effort

Generality comes from working code, not from speculation. Code built from tests tends to be genuinely reusable because it was tested in isolation, which means the dependencies are explicit and the interfaces are clean.

---

## How much feedback do you need?

Enough to feel confident in your code and your design decisions. For experienced developers in familiar domains, Obvious Implementation needs very little feedback. For unfamiliar domains or complex algorithms, Triangulate and small steps provide more checkpoints.

TDD is not an absolute. XP says "here are things you must do." TDD says "here is an awareness of the gap between decision and feedback, and techniques to control that gap." How tightly you close that gap is your choice.

---

## When should you delete tests?

Delete a test when it is completely subsumed by another test — when the information it provides is fully captured by other tests. Two tests that exercise exactly the same code path can be reduced to one.

Never delete tests to make a test suite pass. Never delete tests to reduce maintenance burden while keeping the behavior untested.

The bar for deletion is high: only when you are certain the deleted test adds zero information value. If uncertain, keep it.

---

## How do you switch to TDD midstream?

Start writing tests for new code immediately. Don't wait for a "TDD rewrite" of existing code.

For existing untested code: write characterization tests (also called pinning tests) to document current behavior before changing it. These aren't tests you would have written test-first — they capture what the code actually does now. Then you can refactor/change with confidence.

The hardest part of switching midstream: the pressure to finish features. Start with the next new feature, apply TDD, and let the benefits accumulate organically.

---

## Who is TDD intended for?

"If you are a genius, you don't need these rules. If you are a dolt, the rules won't help. For the vast majority of us in between, following these two simple rules can lead us to work much more closely to our potential." — Kent Beck

TDD is intended for ordinary programmers who want to write code of higher quality than they currently produce. It is especially valuable under pressure, when ordinary programmers tend to skip steps that TDD makes mandatory.

---

## Is TDD sensitive to initial conditions?

Yes. A bad first test can lead you down a difficult path. But the consequence of a bad first test is just that you throw it away and try again. The cost of iteration in TDD is low — you've invested minutes, not days.

The iterative nature means initial conditions matter less than in big-design-upfront: if you start wrong, you discover it quickly.

---

## How does TDD relate to patterns?

Patterns describe the vocabulary of good designs. TDD creates pressure toward good designs by making certain designs easier to test. The same solutions appear repeatedly because they work, and they work partly because they're testable.

Knowing patterns helps you recognize what TDD is pushing you toward. TDD without pattern knowledge still produces better designs than no TDD, but pattern knowledge accelerates the journey.

---

## Why does TDD work?

TDD works because:

1. **Reduced defect density**: Writing tests first forces you to think about behavior before implementation. This catches misunderstandings early.

2. **Courage**: Tests are the ratchet. Once green, always green. You can make changes without fear of silent regressions.

3. **Design feedback**: Hard-to-test code is a signal of design problems. TDD surfaces these immediately, while the cost to fix is low.

4. **Rhythm**: The Red/Green/Refactor cycle creates a sustainable pace with regular small victories.

5. **Documentation**: Tests are executable specifications. They can't drift from the code the way comments do.

---

## How does TDD relate to Extreme Programming?

TDD is a practice within XP, but it stands alone. XP is prescriptive ("you must do X"). TDD is an awareness ("notice the gap between decision and feedback, then manage it").

Many developers who don't practice full XP still practice TDD. The two reinforce each other: TDD provides the quality foundation that makes XP's frequent-release rhythm possible.

---

## Darach's Challenge

Darach Ennis challenged Beck: "Show me something I don't know."

The answer: the rhythm. The daily experience of Red/Green/Refactor, the discipline of tiny steps, the practice of Test First — these are not ideas that can be understood from a description. They must be practiced until they become automatic.

Read the book, then practice for 30 days. After 30 days, decide if TDD is for you based on experience, not theory.
