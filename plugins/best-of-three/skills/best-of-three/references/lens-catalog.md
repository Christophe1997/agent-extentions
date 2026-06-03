# Lens Catalog

A **lens** is the design bias a candidate optimizes for. Three candidates given
the *same* spec but *different* lenses produce genuinely different solutions —
that divergence is what makes the comparison worth running. Identical prompts
would yield three near-identical implementations and waste the fan-out.

## Deriving task-specific lenses

Do not present this catalog verbatim. Read the task first, then propose 5-6
lenses that actually pull in different directions *for this task*. A lens earns a
slot only if choosing it would visibly change the code.

Derivation heuristics:

- **Name the axes of real tension** in the task (e.g. correctness-under-
  concurrency vs. readability; migration safety vs. delivery speed). Each pole is
  a candidate lens.
- **Map the risk profile.** Data migration → a `safety` and a `reversibility`
  lens matter more than `performance`. A hot read path → `performance` earns a
  slot. A throwaway script → `simplicity` dominates and `coverage` may not.
- **Drop lenses that collapse.** If two proposed lenses would produce the same
  code for this task, keep one and find a genuinely different second.
- **Prefer 3 divergent over 5 similar.** The user picks N (default 3); give them
  options that trade off against each other, not variations on a theme.

## Canonical lenses (seed menu)

Use these as starting points, renamed/retuned to the task:

| Lens | Optimizes for | The candidate will tend to… |
|------|---------------|------------------------------|
| **Safety / rigor** | Correctness, invariants, failure handling | Add guards, fencing, assertions, exhaustive edge-case handling; accept more code |
| **Simplicity / idiomatic** | Readability, least code, framework idioms | Lean on stdlib/framework conventions; minimize abstractions and LOC |
| **Test-coverage / TDD** | Verifiability, regression safety | Write tests first, cover branches, design for testability over brevity |
| **Performance** | Latency, allocation, query count | Reduce round-trips, batch, pick tighter data structures; accept complexity |
| **Minimal-diff / surgical** | Small blast radius, easy review | Touch the fewest files; reuse existing patterns over introducing new ones |
| **Extensibility** | Future change, clean seams | Define interfaces and extension points for the next N features |
| **Migration / reversibility** | Safe rollout, rollback | Backfill-then-cutover, dual-write, feature-flag, leave an undo path |

## Presenting the choice

After deriving the menu, ask the user to pick N with `AskUserQuestion`
(`multiSelect: true`). State, in one line per lens, *how it will change the
result for this task* — not the generic definition above. Let the user free-type
a lens the menu missed.
