# Green Bar Patterns (Chapter 28)

Patterns for making a failing test pass as quickly as possible — even if the result is ugly. The goal is to reach green, then refactor.

---

## Fake It ('Til You Make It)

**Question**: What is your first implementation once you have a failing test?

**Answer**: Return a constant. Once the test passes, gradually transform the constant into an expression using variables.

```python
# Test
assert result.summary() == "1 run, 0 failed"

# Step 1: Fake it — return constant (GREEN immediately)
def summary(self):
    return "1 run, 0 failed"

# Step 2: Generalize — replace first constant with variable
def summary(self):
    return "%d run, 0 failed" % self.run_count

# Step 3: Generalize — replace second constant
def summary(self):
    return "%d run, %d failed" % (self.run_count, self.failure_count)
```

Why Fake It works:

**Psychological effect**: A green bar feels completely different from a red bar. From green you can refactor with confidence, knowing you haven't broken anything. From red you're still uncertain.

**Scope control**: Programmers imagine all sorts of future problems. Starting with one concrete example and generalizing prevents premature complexity. Each test is focused on exactly one thing.

**Duplication analysis**: Fake It doesn't violate the "don't write unnecessary code" rule. The constant in `return "1 run, 0 failed"` duplicates the data in the test assertion. Refactoring eliminates that duplication. The code you end up with is genuinely needed.

---

## Triangulate

**Question**: How do you most conservatively drive abstraction with tests?

**Answer**: Abstract only when you have two or more examples.

```java
// Test 1: only need one example for assertion
assertEquals(4, plus(3, 1));

// Fake it:
int plus(int a, int b) { return 4; }

// Test 2: forces real abstraction
assertEquals(7, plus(3, 4));

// Now must generalize:
int plus(int a, int b) { return a + b; }
```

Triangulation is attractive because the rules are clear. Fake It relies on a subjective sense of duplication; Triangulate is mechanically obvious.

The philosophical issue: once you have both assertions and have abstracted, you can delete one assertion (it's redundant). But then you can simplify back to a constant, which requires adding the assertion back. This is the triangulation loop — use it only when genuinely uncertain about the right abstraction.

**When to use**: Only when very uncertain about the correct abstraction. Otherwise prefer Fake It or Obvious Implementation.

---

## Obvious Implementation

**Question**: How do you implement simple operations?

**Answer**: Just implement them.

For operations whose implementation is clear and simple, don't waste time on Fake It or Triangulation. Just type the correct code.

```java
// Just write it
int plus(int a, int b) { return a + b; }
```

The risk: demanding perfection of yourself. If your Obvious Implementation turns out wrong (red bar), you were overconfident. The tell: getting surprised by red bars repeatedly. When that happens, shift down to Fake It or Triangulate.

The cycle: Obvious Implementation is second gear. Be ready to downshift when your brain is writing checks your fingers can't cash. Maintain the Red/Green/Refactor rhythm above all else.

---

## One to Many

**Question**: How do you implement an operation that works with collections?

**Answer**: Implement it without collections first, then make it work with collections.

```java
// Step 1: Single value
assertEquals(5, sum(5));
int sum(int value) { return value; }

// Step 2: Add collection parameter (Isolate Change — safe refactoring)
assertEquals(5, sum(5, new int[]{5}));
int sum(int value, int[] values) { return value; }

// Step 3: Use collection instead of single value
int sum(int value, int[] values) {
    int total = 0;
    for (int v : values) total += v;
    return total;
}

// Step 4: Delete unused single-value parameter
assertEquals(5, sum(new int[]{5}));
int sum(int[] values) {
    int total = 0;
    for (int v : values) total += v;
    return total;
}

// Step 5: Now test with multiple values
assertEquals(12, sum(new int[]{5, 7}));
```

Each step is small and safe. The Isolate Change moves (adding then removing a parameter) allow you to change test and code independently, never having both changing simultaneously.
