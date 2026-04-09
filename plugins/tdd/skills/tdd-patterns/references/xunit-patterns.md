# xUnit Patterns (Chapter 29)

Patterns for using xUnit-family testing frameworks (JUnit, pytest, NUnit, etc.).

---

## Assertion

**Question**: How do you check that tests worked correctly?

**Answer**: Write boolean expressions that automate your judgment about whether the code worked.

Every bit of human judgment must be automated — push a button, get a pass/fail. This requires:
- Boolean decisions (true = OK, false = unexpected)
- Checking those booleans automatically via `assert*()` methods

Be specific. `assertTrue(rectangle.area() != 0)` passes for any non-zero area. `assertEquals(50, rectangle.area())` is the real check.

**Prefer behavioral assertions over implementation assertions**:

```java
// Bad — tests implementation (status field)
assertEquals(Running.class, contract.status.class);

// Better — tests behavior (what Running status enables)
assertEquals(today, contract.startDate());  // throws if not Running
```

White-box testing (checking private variables) is a design smell. If you want to check an internal variable, ask: "How can I restructure this so the behavior is observable from the outside?"

**Message parameters**: Include an explanatory string in assertions for complex tests:
```java
assertTrue("Should be running after begin()", contract.isRunning());
```

Some teams require explanatory strings on all assertions. Experiment to see if the investment pays off.

---

## Fixture

**Question**: How do you create common objects needed by several tests?

**Answer**: Convert local variables in tests into instance variables. Override `setUp()` and initialize those variables.

```java
// Without Fixture — duplicated setup
void testEmpty() {
    Rectangle empty = new Rectangle(0,0,0,0);
    assertTrue(empty.isEmpty());
}
void testWidth() {
    Rectangle empty = new Rectangle(0,0,0,0);
    assertEquals(0.0, empty.getWidth(), 0.0);
}

// With Fixture — extracted to setUp()
private Rectangle empty;

void setUp() {
    empty = new Rectangle(0,0,0,0);
}
void testEmpty() { assertTrue(empty.isEmpty()); }
void testWidth() { assertEquals(0.0, empty.getWidth(), 0.0); }
```

Trade-off: fixtures reduce duplication but require readers to remember what's in `setUp()` before understanding the test. Tests with setup inline are more readable top-to-bottom.

**When to create a new fixture class**: When you need a slightly different fixture (e.g., a non-empty Rectangle), create a new TestCase subclass. Don't shoehorn multiple fixtures into one class.

**Note**: Test class count roughly matches model class count in practice, but not because of a 1:1 rule — sometimes one fixture tests multiple classes, sometimes a class needs multiple fixtures.

---

## External Fixture

**Question**: How do you release external resources in the fixture?

**Answer**: Override `tearDown()` and release the resources.

For resources like files, database connections, or network sockets:

```python
def setUp(self):
    self.file = open("foobar", "w")

def testMethod(self):
    # test using self.file
    pass

def tearDown(self):
    self.file.close()  # always runs, even if test fails
```

`tearDown()` is guaranteed to run after the test method, regardless of what happens in the test. This eliminates `try/finally` noise from every test.

Key rule: each test must leave the world in exactly the same state as before it ran. If `setUp()` fails, `tearDown()` won't be called — design setUp to be atomic or handle partial failure.

---

## Test Method

**Question**: How do you represent a single test case?

**Answer**: A method that starts with `test` (in most xUnit implementations), takes no parameters, and returns nothing.

```java
void testSum() {
    assertEquals(4, plus(3, 1));
}
```

Each test method is independent. xUnit creates a new instance of the TestCase class for each test method — this is how Fixture isolation is guaranteed. The lifecycle per test is: `new TestCase` → `setUp()` → `testMethod()` → `tearDown()` → discard.

---

## Exception Test

**Question**: How do you test for expected exceptions?

**Answer**: Catch the expected exception and pass; if the exception isn't thrown, fail explicitly.

```java
// JUnit 3 style
void testDivideByZero() {
    try {
        divide(1, 0);
        fail("Should have thrown ArithmeticException");
    } catch (ArithmeticException expected) {
        // correct
    }
}

// JUnit 4+ style
@Test(expected = ArithmeticException.class)
void testDivideByZero() {
    divide(1, 0);
}
```

The `fail()` after the call-under-test is essential — without it, a missing exception silently passes.

---

## All Tests

**Question**: How do you run all the tests in a system?

**Answer**: Create a TestSuite that contains all other TestSuites.

```java
// Java
TestSuite suite = new TestSuite();
suite.addTest(MoneyTest.suite());
suite.addTest(ExchangeTest.suite());
// ...
```

Most modern frameworks (pytest, JUnit 4+, NUnit) auto-discover tests. The All Tests pattern emerged from manual test suite assembly in xUnit's early days, but the concept remains: there should be one command to run all tests in the system.
