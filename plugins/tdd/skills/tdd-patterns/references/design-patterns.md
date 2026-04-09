# Design Patterns (Chapter 30)

OO design patterns that emerge naturally when practicing TDD. These are patterns that TDD pushes you toward through the pressure of testability and duplication elimination.

---

## Command

**Problem**: Computation invocation needs to be decoupled from computation itself.

**Solution**: Wrap the computation in an object with a single `run()` or `execute()` method.

```java
interface Command { void run(); }
class PrintCommand implements Command {
    void run() { System.out.println("hello"); }
}
```

xUnit's TestCase is the canonical example: each test is a Command that can be queued, scheduled, or run remotely.

---

## Value Object

**Problem**: Aliasing bugs — multiple references to the same object cause unexpected mutation.

**Solution**: Objects whose equality is defined by their value, not their identity. All operations return new instances; the object is never mutated.

```java
// Value Object — never mutated
Money five = new Money(5, "USD");
Money ten = five.plus(five);  // returns NEW Money, five unchanged
assertEquals(five, new Money(5, "USD"));  // value equality
```

In TDD, Money and similar domain objects are almost always Value Objects. The test `assertEquals(new Money(5), result)` only works if equality is value-based.

Requirement: implement `equals()` (and `hashCode()`). TDD naturally drives this — the first assertEquals on a domain object fails until you implement value equality.

---

## Null Object

**Problem**: Pervasive null checks obscure logic and are easy to forget.

**Solution**: Return a special-purpose object that implements the same interface but does nothing (or returns safe defaults).

```java
// Instead of: if (customer != null) customer.charge();
// Use a NullCustomer that safely does nothing:
customer.charge();  // always safe

class NullCustomer implements Customer {
    void charge() {} // no-op
    Money balance() { return Money.ZERO; }
}
```

TDD pressure: tests that require setting up null-check branches are harder to write clearly. Null Object makes those branches disappear, simplifying both code and tests.

---

## Template Method

**Problem**: Two operations share the same overall sequence but differ in specific steps.

**Solution**: Define the skeleton in a base class method; override specific steps in subclasses.

```java
abstract class TestCase {
    final void run(TestResult result) {
        result.testStarted(this);
        setUp();        // overridden by subclass
        testMethod();   // overridden by subclass
        tearDown();     // overridden by subclass
    }
    void setUp() {}     // default: do nothing
    void tearDown() {}  // default: do nothing
}
```

xUnit itself is built on Template Method. TDD drives you toward Template Method when you notice two subclasses with the same method structure but different implementations.

---

## Pluggable Object

**Problem**: Conditional logic (if/switch) that varies based on type pollutes many methods.

**Solution**: Create an object that encapsulates the variation; swap the object instead of checking the condition.

```java
// Before: if-else in every method
void draw() {
    if (selected) drawSelected();
    else drawNormal();
}

// After: pluggable object encapsulates the variation
SelectionMode mode;  // = SelectedMode or NormalMode
void draw() { mode.draw(this); }
```

TDD surfaces this when tests for the selected/unselected branches proliferate. Once you notice the pattern, replace the condition with a Pluggable Object.

---

## Pluggable Selector

**Problem**: A single method varies behavior based on an argument (often a string or enum).

**Solution**: Store the method name/selector as state; look it up dynamically.

```python
class TestCase:
    def __init__(self, name):
        self._name = name
    
    def run(self):
        method = getattr(self, self._name)
        method()
```

This is how xUnit discovers and runs test methods by name. Note: Pluggable Selector makes code harder to search statically. Use only when the benefit of dynamic dispatch clearly outweighs the navigation cost.

---

## Factory Method

**Problem**: Subclasses need to create objects whose type matches the subclass, but the creation logic lives in the superclass.

**Solution**: Override a factory method in each subclass to return the appropriate type.

```java
abstract class TestCase {
    abstract Money createMoney(int amount, String currency);
    
    void testMultiplication() {
        Money five = createMoney(5, "USD");
        assertEquals(createMoney(10, "USD"), five.times(2));
    }
}

class DollarTest extends TestCase {
    Money createMoney(int amount, String currency) {
        return new Dollar(amount, currency);
    }
}
```

TDD surfaces this when writing tests for hierarchies — the test wants to work with the abstract type but must construct concrete instances.

---

## Imposter

**Problem**: Need to introduce new behavior without changing existing tests.

**Solution**: Introduce a new object with the same protocol as an existing object, but with different behavior.

Examples: Mock Object is an Imposter (fake database with same interface as real). Null Object is an Imposter (no-op implementer of an interface). Test Doubles in general are Imposters.

TDD constantly uses Imposters in testing — the practice naturally surfaces situations where polymorphism provides better solutions than conditionals.

---

## Composite

**Problem**: Need to treat a collection of objects the same as a single object.

**Solution**: The collection implements the same interface as its elements.

```java
// TestSuite IS-A Test, contains Tests
interface Test { void run(TestResult result); }

class TestSuite implements Test {
    private List<Test> tests;
    void run(TestResult result) {
        for (Test t : tests) t.run(result);
    }
}
```

xUnit's TestSuite is the canonical Composite. TDD surfaces this when you notice "run all these things like they were one thing."

---

## Collecting Parameter

**Problem**: Results from multiple operations need to be collected into a single object.

**Solution**: Pass a parameter into which results are accumulated.

```java
// TestResult accumulates across many test runs
void run(TestResult result) {
    try {
        setUp();
        runTest();
    } catch (Throwable e) {
        result.addFailure(this, e);
    } finally {
        tearDown();
    }
    result.addSuccess();
}
```

TestResult in xUnit is a Collecting Parameter. TDD naturally leads here when multiple operations all need to contribute to a shared result.

---

## Singleton

**Problem**: Only one instance of an object should exist.

**Note**: TDD actively discourages Singletons. Global state makes tests order-dependent and impossible to isolate.

If you feel the need for a Singleton, ask first: "Can I pass this object as a parameter instead?" Usually yes. Tests with Singletons require careful teardown to reset global state — a design smell.
