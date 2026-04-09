# Refactoring Patterns (Chapter 31)

Specific refactoring moves used during the Refactor step of TDD. These are small, safe, behavior-preserving transformations — always done from a green bar.

---

## Reconcile Differences

**Problem**: Two pieces of code look almost the same but differ in minor ways.

**Solution**: Make them identical, then eliminate one by replacing both with a single piece.

Approach: identify the differences, transform one to match the other (still green), then merge. Common in class hierarchies when the same method exists in two subclasses.

```java
// Before: two similar methods in subclasses
class Dollar { Money times(int m) { return new Dollar(amount * m, "USD"); } }
class Franc  { Money times(int m) { return new Franc(amount * m, "CHF"); } }

// Step 1: Reconcile — make both use currency field
class Dollar { Money times(int m) { return new Money(amount * m, currency); } }
class Franc  { Money times(int m) { return new Money(amount * m, currency); } }

// Step 2: Eliminate — move to superclass, delete from subclasses
class Money  { Money times(int m) { return new Money(amount * m, currency); } }
```

Only proceed when both implementations are genuinely identical — not just "similar enough."

---

## Isolate Change

**Problem**: Need to change part of a multi-part method or object.

**Solution**: Extract the part that will change, change the extracted part, then fold it back in (or leave it extracted if cleaner).

Process:
1. Extract Method on the part that will change
2. Change the extracted method
3. Fold back in (or keep as named method if it clarifies intent)

This is also the mechanism behind One to Many — add a parameter (isolate), change the implementation (safe), remove the old parameter (clean up).

---

## Migrate Data

**Problem**: Need to change the internal representation of data (or change an API).

**Solution**: Temporarily duplicate the data; migrate usages to the new representation; delete the old.

**Internal-to-external migration** (change internal first):
1. Add instance variable in new format
2. Set the new variable everywhere you set the old variable
3. Use the new variable everywhere you use the old variable
4. Delete the old variable
5. Change external interface to reflect new format

**External-to-internal migration** (change API first):
1. Add parameter in new format
2. Translate from new format parameter to old internal representation
3. Delete old format parameter
4. Replace uses of old format with new format
5. Delete old format

The temporary duplication keeps tests green throughout. Never leave duplication longer than necessary.

---

## Extract Method

**Problem**: A method is too long or a piece of code needs a name.

**Solution**: Turn the fragment into a method named after its intent.

```java
// Before
void printOwing() {
    // print header
    System.out.println("*****");
    System.out.println("** Customer Owes **");
    System.out.println("*****");
    // calculate outstanding
    double outstanding = ...;
}

// After
void printOwing() {
    printHeader();
    double outstanding = calculateOutstanding();
}
```

In TDD, Extract Method is used to eliminate duplication between test and code, and to give clear names to test data and operations.

---

## Inline Method

**Problem**: A method body is as clear as the method name; the indirection is not helping.

**Solution**: Replace calls to the method with the method body and delete the method.

The inverse of Extract Method. Use when a method was extracted to enable change, the change is complete, and the extracted method is now trivial and adds no clarity.

---

## Extract Interface

**Problem**: Multiple clients need the same protocol from different objects.

**Solution**: Extract the shared methods into an interface; both the original class and new classes implement it.

In TDD, Extract Interface appears naturally when writing Mock Objects — you need the mock to have the same interface as the real object, so you extract the interface that both implement.

---

## Move Method

**Problem**: A method is in the wrong class — it uses more features of another class than its own.

**Solution**: Move the method to the class it uses most; update callers.

TDD surfaces this when writing tests: if testing a method requires setting up objects it doesn't "belong to," it probably belongs elsewhere.

---

## Method Object

**Problem**: A long method uses several local variables, making Extract Method impossible.

**Solution**: Turn the method into an object. The method's local variables become instance variables. The method body becomes the `run()` method.

```java
// Before: long method with many locals
int calculate(int a, int b, int c) { ... 50 lines using a, b, c ... }

// After: turn into object
class Calculation {
    private int a, b, c;
    Calculation(int a, int b, int c) { this.a=a; this.b=b; this.c=c; }
    int run() { ... 50 lines now using fields ... }
}
```

Method Object enables further Extract Method calls on the new class, since all the locals are now fields.

---

## Add Parameter

**Problem**: A method needs more information from its caller.

**Solution**: Add a parameter to the method.

Simple but often necessary during Migrate Data and Isolate Change. When adding, introduce the parameter to existing callers with a default/safe value first, then migrate callers to provide real values.

---

## Method Parameter to Constructor Parameter

**Problem**: The same parameter is passed to multiple methods on the same object.

**Solution**: Move the parameter to the constructor; store as an instance variable; remove from individual methods.

```java
// Before
void doSomething(Context ctx) { ... }
void doSomethingElse(Context ctx) { ... }

// After
class MyClass {
    private Context ctx;
    MyClass(Context ctx) { this.ctx = ctx; }
    void doSomething() { ... }
    void doSomethingElse() { ... }
}
```

TDD surfaces this when the same setup parameter appears in many test calls.
