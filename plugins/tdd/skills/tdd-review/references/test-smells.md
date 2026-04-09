# Test Smells Reference

Detailed catalog of test smells from *Test Driven Development: By Example* and related practice. Each smell is a signal about the production code's design, not just the test.

---

## Long Setup Code

**Symptom**: Dozens of lines constructing objects before any assertion.

**Signal**: Objects are too big. A class that requires 50 lines to construct is probably doing too much.

**Fix**:
- Apply **Extract Method** to name setup chunks
- Apply **Fixture** pattern (move to setUp)
- Split the object being constructed — apply Single Responsibility Principle
- Consider Builder pattern for complex object construction

**Test smell vs. design problem**: The test is telling you the design is wrong. Don't fix the test — fix the class.

---

## Setup Duplication

**Symptom**: The same 10 lines of setup appear in multiple tests, but it's hard to extract to a single setUp method because each test needs slight variations.

**Signal**: Too many objects are tightly intertwined. When you can't easily share setup, it means objects have too many dependencies on each other.

**Fix**:
- Create focused test fixtures (one TestCase subclass per fixture variant)
- Apply **Method Parameter to Constructor Parameter** to reduce dependencies
- Refactor production code to reduce coupling

---

## Long Running Tests

**Symptom**: Individual tests take > 1 second. Test suite takes > 10 minutes.

**Signal**: Tests are reaching out to real external resources (databases, networks, filesystems, clocks) or the system has hard-to-unit-test dependencies.

**Fix**:
- Apply **Mock Object** to replace expensive dependencies
- Apply **In-Memory Fixtures** (use H2 instead of PostgreSQL, etc.)
- Split the test suite: fast unit tests run always, slow integration tests run on CI
- Redesign the application to separate I/O from logic (hexagonal architecture)

**Rule of thumb**: A test suite > 10 minutes will be skipped. It will drift. It will miss bugs.

---

## Fragile Tests

**Symptom**: Tests break when you change code that "shouldn't" affect them. Tests break in mysterious orderings. Tests pass on one machine, fail on another.

**Signal**: Tests are coupled to each other (shared mutable state) or coupled to implementation details.

**Causes and fixes**:
- **Shared static state**: Use setUp/tearDown to reset; avoid Singletons
- **Time-dependent tests**: Inject a clock; mock `System.currentTimeMillis()`
- **Order-dependent tests**: Each test must be Isolated
- **Testing internals**: Replace with behavioral tests; apply Extract Interface

---

## Testing Implementation Details

**Symptom**: Tests break every time you refactor internal structure, even when behavior is preserved.

**Example**:
```java
// Bad — tests the field name "status"
assertEquals(Running.class, contract.status.getClass());

// Good — tests observable behavior
assertNotNull(contract.startDate());  // only set when Running
```

**Fix**: Test through the public API only. If behavior isn't observable from outside, either it doesn't matter (delete the test) or you need to add behavior to make it observable.

---

## Mystery Guest

**Symptom**: Test uses a file, database row, or configuration that's set up somewhere else. Reader can't understand the test without hunting down the external resource.

**Fix**:
- Apply **Fixture** — create what the test needs in setUp
- Apply **Inline Resource** — embed test data directly in the test
- Apply **In-Memory DB** — don't use real external resources in unit tests

---

## Assertion Roulette

**Symptom**: Multiple assertions in one test; when one fails, unclear which one and what it means.

```java
void testOrder() {
    // Which one failed? What does it mean?
    assertEquals(3, order.lineCount());
    assertEquals("PENDING", order.status());
    assertEquals(customer, order.customer());
    assertTrue(order.isValid());
}
```

**Fix**:
- Split into separate test methods (one assertion = one test)
- Add descriptive failure messages to each assertion
- Use a descriptive test method name for the specific scenario

---

## Irrelevant Information

**Symptom**: Test contains data values that don't affect the outcome, obscuring what's actually being tested.

```java
// What does the customer name have to do with the sum?
void testSum() {
    Order order = new Order("John Doe", "New York", "USA", "10001");
    order.add(new Item("Widget", 5.00));
    assertEquals(5.00, order.total(), 0.001);
}
```

**Fix**: Apply **Test Data** — include only data that's relevant to the assertion.

---

## Sensitive Equality

**Symptom**: Test asserts on string representations or toString() output that changes when formatting changes.

```java
// Bad — breaks if toString format changes
assertEquals("Money(5 USD)", money.toString());

// Better — test the actual values
assertEquals(5, money.amount());
assertEquals("USD", money.currency());
```

**Fix**: Test specific observable values, not string representations. Override `equals()` for value comparisons.

---

## Conditional Logic in Tests

**Symptom**: `if`, `for`, `while`, `switch` in test code.

```java
// Bad
void testSomething() {
    if (result != null) {
        assertEquals("expected", result.getValue());
    }
    // But what if result IS null? Silent pass!
}
```

**Fix**: Each branch is a separate scenario — write separate tests. Use `assertNotNull` explicitly before accessing, or use `assertThrows` for null cases.

---

## Slow External Dependencies

**Symptom**: Tests that send HTTP requests, write real files, or query real databases.

**Patterns to apply**:
- **Mock Object** — fake the dependency with a controlled substitute
- **Fake** — lightweight in-memory implementation of the interface
- **Self Shunt** — the test case itself implements the collaborator protocol
- **Crash Test Dummy** — special object that forces error paths

---

## Over-Specified Tests

**Symptom**: Tests assert on every internal detail, making refactoring impossible.

**Signal**: Too much white-box testing. Tests written after code (not test-first) tend toward this.

**Fix**: Ask "What behavior must this operation preserve for callers?" Test only that. Allow the implementation to change freely as long as the behavior contract is preserved.
