# TDD Plugin

Test-Driven Development guidance based on Kent Beck's *Test Driven Development: By Example* (2002). Provides the complete Red/Green/Refactor workflow, a reference for all 40+ named TDD patterns from the book, and autonomous test quality review.

## Features

### Skills

- **tdd:tdd** - Complete TDD workflow — the two rules, Red/Green/Refactor cycle, how to start, how to choose strategies (Fake It, Triangulate, Obvious Implementation). Triggers: "use TDD", "write this test-first", "help me do TDD", "red green refactor"
- **tdd:patterns** - Reference for all 40+ patterns from Part III of the book. Triggers: "TDD patterns", "mock object", "fake it til you make it", "starter test", "triangulate", "fixture", "learning test"
- **tdd:review** - Structured review of tests against TDD principles. Triggers: "review my tests", "check my TDD", "test smell", "fragile tests", "is this good TDD"

### Agents

| Agent | Description |
|-------|-------------|
| `tdd-reviewer` | Autonomous review of test files for TDD compliance, test smells, isolation, and design signals |

## Examples

```
# Start implementing a feature with TDD
/tdd:tdd implement a stack data structure

# Look up a specific pattern  
/tdd:patterns how do I use Mock Object?

# Review existing tests
/tdd:review @src/cart/cart.test.js
```

## Installation

**Requirements**: Claude Code CLI

```
/plugin install tdd@agent-extentions
```

## Usage

### TDD Workflow (`/tdd:tdd`)

Guides you through the complete TDD cycle for a feature:
1. Write the Test List
2. Pick the first test (Starter Test + One Step Test)
3. Write assert-first (Assert First pattern)
4. Make it green (Fake It / Triangulate / Obvious Implementation)
5. Refactor from green
6. Repeat

### Pattern Lookup (`/tdd:patterns`)

Quick lookup for any of the 40+ patterns organized by chapter:
- **Chapter 25** — TDD Core Patterns (Isolated Test, Test List, Assert First, Evident Data...)
- **Chapter 26** — Red Bar Patterns (One Step Test, Starter Test, Learning Test, Regression Test, Do Over...)
- **Chapter 27** — Testing Patterns (Child Test, Mock Object, Self Shunt, Log String, Broken Test...)
- **Chapter 28** — Green Bar Patterns (Fake It, Triangulate, Obvious Implementation, One to Many)
- **Chapter 29** — xUnit Patterns (Assertion, Fixture, External Fixture, Exception Test...)
- **Chapter 30** — Design Patterns (Value Object, Null Object, Template Method, Composite...)
- **Chapter 31** — Refactoring (Reconcile Differences, Migrate Data, Extract Method, Isolate Change...)
- **Chapter 32** — Mastering TDD (step size, when to delete tests, switching midstream...)

### Test Review (`/tdd:review`)

Analyzes tests for:
- Test smells (long setup, fragile tests, over-specification)
- Isolation issues
- Coverage gaps
- Design signals (what the tests reveal about production code quality)

## License

MIT
