# Red Bar Patterns (Chapter 26)

Patterns about when to write tests, where to write tests, and when to stop writing tests.

---

## One Step Test

**Question**: Which test should you pick next from the list?

**Answer**: Pick a test that will teach you something and that you are confident you can implement.

Each test represents one step toward the goal. What counts as "one step" is relative to your experience with the problem — a beginner's one-step test may be ten steps for an expert.

When no test on the list feels like one step, add smaller tests to the list. Look for the test where you think: "That's obvious, that's obvious, I have no idea, obvious... ah, this one I can do."

Programs grown from tests can appear top-down or bottom-up — neither metaphor is accurate. The real direction is **known-to-unknown**: start with what you know and learn as you go.

---

## Starter Test

**Question**: Which test should you start with?

**Answer**: Start by testing a variant of an operation that doesn't do anything yet.

The first question for a new operation: "Where does it belong?" Starting with a realistic test forces you to solve too many problems at once (placement, inputs, outputs). Instead, start with a test where:
- Output is the same as input (or trivially easy to derive)
- Input is as small as possible (empty list, single item, zero)

Example for a polygon reducer:
```java
Reducer r = new Reducer(new Polygon());
assertEquals(0, r.result().npoints);
```

This establishes where `Reducer` belongs without tackling the hard algorithm. Once this passes, tackle the actual reduction logic.

---

## Explanation Test

**Question**: How do you spread the use of automated testing?

**Answer**: Ask for and give explanations in terms of test cases.

When someone explains something to you, rephrase it as a test: "So if I have a Foo like this and a Bar like that, the answer should be 76?"

When you explain something, use a test: "Here's how it works now. When I have a Foo like this and a Bar like that, the answer is 76."

Do not force TDD on teammates — demonstrate through results (fewer defects, simpler designs, easier explanations). Converting team conversations to test form naturally spreads the practice.

---

## Learning Test

**Question**: When do you write tests for externally produced software?

**Answer**: Before the first time you use a new facility in the package.

Before using a new API or library method, write a test that verifies the API behaves as you expect. Benefits:
- Confirms your understanding of the API is correct
- Documents how the API is used
- Provides regression protection when new library versions arrive

Process: run learning tests first after upgrading a dependency. If they pass, the application will almost certainly work. If they fail, the new version broke a contract — investigate before running the application.

---

## Another Test

**Question**: How do you keep a technical discussion from straying off topic?

**Answer**: When a tangential idea arises, add a test to the list and go back to the topic.

Greet new ideas with respect but don't let them divert attention from the current task. Write the idea on the test list, then return to the current work. This maintains rhythm without losing good ideas.

---

## Regression Test

**Question**: What's the first thing you do when a defect is reported?

**Answer**: Write the smallest possible test that fails and that, once fixed, will be repaired.

Regression tests are tests you would have written originally with perfect foreknowledge. Every regression test is a lesson: "What could I have tested to catch this earlier?" 

Also test at the application level — regression tests at that level give users a concrete way to communicate what went wrong and what they expect. Regression tests at smaller scale improve your test judgment going forward.

If you must refactor the system to isolate the defect, do it. The defect is telling you the design isn't finished.

---

## Break

**Question**: What do you do when you feel tired or stuck?

**Answer**: Take a break.

Walk away, drink water, take a nap. Physical separation from the problem clears emotional attachment to the decisions just made. The idea you need often arrives during the break.

Dave Ungar's Shower Methodology: if you know what to type, type it. If you don't, shower until you do. TDD refines this: if you know what to type, use Obvious Implementation. If not, Fake It. If the design is unclear, Triangulate. If still stuck, take that shower.

Break at multiple scales:
- Hours: keep water at keyboard (biology forces breaks)
- Days: end-of-day commitments force stopping
- Weeks: weekend activities decompress
- Yearly: mandatory vacation (minimum 3-4 weeks to fully refresh)

---

## Do Over

**Question**: What do you do when you are feeling lost?

**Answer**: Throw away the code and start over.

When the code is twisted, the next test seems impossible, and 20 new problems have appeared — the fastest path forward is often to discard the work and restart. Starting over from a fresh test list is faster than debugging a mess.

Pair programming makes Do Over natural: switching partners gives a fresh perspective. The new partner will often say, "I'm sorry for being dense, but what if we started like this..."

---

## Cheap Desk, Nice Chair

**Question**: What physical setup should you use for TDD?

**Answer**: Get a really nice chair, skimping on the rest of the furniture if necessary.

TDD requires sustained, focused concentration. Back pain destroys it. Invest in a good chair before a good desk.

For pair programming: clear enough desk space that the keyboard can slide between partners. Each person should be able to sit directly in front of the keyboard when driving.

Hardware corollary: cheap/old machines for email and browsing, fastest available machines for development.
