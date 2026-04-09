# TDD Core Patterns (Chapter 25)

Patterns for the fundamental strategy of TDD — what to test and when.

---

## Test (noun)

**Question**: How do you test your software if you don't have automated tests?

**Answer**: Write an automated test.

The stress/testing dynamic: stress reduces testing, less testing adds stress — a destructive positive feedback loop. Automated tests break this loop. Once a test passes, it passes forever. The ratchet never slips back.

---

## Isolated Test

**Question**: How should tests affect each other?

**Answer**: Not at all. Tests must be completely independent.

If a test breaks, you should be able to run it alone and immediately see the failure. Tests that depend on each other hide the source of failures. Isolated tests also force better design — objects with tangled dependencies are hard to test in isolation.

**Implication for design**: Objects should be highly cohesive and loosely coupled. If setup is expensive, it is a design smell. Split the object.

**Practical consequence**: Tests can run in any order. If order matters, there is shared state to eliminate.

---

## Test List

**Question**: What should you test?

**Answer**: Before beginning, write a list of all the tests you know you will have to write.

Keep the list on a slip of paper next to the keyboard. When a new test idea arises during implementation, add it to the list — do not interrupt current work. When a refactoring need arises, add it too.

What goes on the list:
- Examples of every operation to implement
- Null/empty versions of operations that don't exist yet
- Refactorings needed for clean code by end of session

Items left at session end: either carry forward (if mid-feature) or move to a "later" list. Never ignore.

---

## Test First

**Question**: When should you write your tests?

**Answer**: Before you write the code that is to be tested.

The virtuous cycle: Test-First reduces stress, lower stress makes you more likely to test, which further reduces stress. Testing after is skipped under pressure. Testing first cannot be skipped — it is the prerequisite to writing any code.

Additional benefit: tests serve as design and scope-control tools. Writing the test forces you to decide interface before implementation.

---

## Assert First

**Question**: When should you write the asserts?

**Answer**: Write the asserts first, then work backwards to fill in what's needed.

Start from the bottom of the test (what should be true when done) and build upward:

```java
// Step 1: what do I assert?
assertEquals("abc", reply.contents());

// Step 2: where does reply come from?
Buffer reply = reader.contents();
assertEquals("abc", reply.contents());

// Step 3: where does reader come from?
Socket reader = new Socket("localhost", defaultPort());
Buffer reply = reader.contents();
assertEquals("abc", reply.contents());

// Step 4: what needs to exist before that?
Server writer = new Server(defaultPort(), "abc");
Socket reader = new Socket("localhost", defaultPort());
Buffer reply = reader.contents();
assertEquals("abc", reply.contents());
```

This separates the problems "What is the right answer?" and "How am I going to check?" from "Where does this belong?" and "What should names be called?" — solving one problem at a time.

---

## Test Data

**Question**: What data do you use for test-first tests?

**Answer**: Data that makes tests easy to read and follow.

Rules:
- Use minimal data — a list of 3 items teaches the same lesson as a list of 10
- Never use the same constant to mean more than one thing — use `plus(3, 4)` not `plus(2, 2)` (can't detect swapped arguments)
- Make differences meaningful — if 1 and 2 have no conceptual difference, use 1

**Realistic Data** is an alternative when:
- Testing real-time systems with external event traces
- Parallel testing (matching output of current vs. previous system)
- Refactoring simulations where floating-point precision matters

---

## Evident Data

**Question**: How do you represent the intent of the data?

**Answer**: Include expected and actual results in the test itself, and make their relationship visible.

Bad (hides calculation):
```java
assertEquals(new Note(49.25, "GBP"), result);
```

Good (shows calculation):
```java
bank.addRate("USD", "GBP", 2);
bank.commission(0.015);
assertEquals(new Note(100 / 2 * (1 - 0.015), "GBP"), result);
```

Side benefit: evident data makes programming easier. Once you write `100 / 2 * (1 - 0.015)` in the assertion, you know exactly what operations to implement.

This is an exception to the "no magic numbers" rule — within the scope of a test method, the relationship between constants is obvious.
