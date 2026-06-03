---
name: best-of-three
description: This skill should be used when the user asks to "best of 3", "best-of-three", "run 3 competing agents", "try N implementations and compare", "spin up parallel worktree agents to compete", "compete implementations and pick the best", or wants several independent attempts at the same task judged head-to-head. Gathers the task, derives design lenses, runs N isolated worktree agents in parallel, then compares, picks a winner, and grafts the best ideas from the runners-up.
argument-hint: "[task description] [--n N]"
allowed-tools: [Read, Edit, Write, Bash, Agent, AskUserQuestion]
---

# Best-of-Three: Competitive Implementation

Run the same task as N independent implementations — each with a different design
bias — then compare them head-to-head, pick a winner, and merge the best ideas
from the rest. Use this when a task has **multiple defensible approaches** and the
right one is clearer once you can compare real implementations than by arguing up
front.

This is **redundant-compete** (N full solutions to the *same* spec, then judge),
not split-by-slice parallelism (different files, one solution). If the task just
needs to be done once, this is the wrong tool — it is N× the cost for the value of
comparison.

## Process

### Phase 1: Gather the task

1. **Capture the task** from the argument or by asking. Pin down: the goal,
   scope (what's in / out), the **acceptance bar** (what "done" means — which
   tests pass, build/lint gates, behavior to preserve), constraints, and any
   plan/spec files to hand the candidates.
2. **Surface blockers** that cap what "green" can mean. If the environment limits
   verification (no DB, no DDL, no network), state the realistic bar now — e.g.
   "integration tests will skip; green = unit tests pass + integration tests
   well-written". Candidates must be judged against an honest bar.
3. **Resolve N** — default 3; honor `--n` if given. (The Phase 2 lens selection
   count overrides this if they differ — explicit selection wins.)
4. **Check git state**: confirm a git repo and note the base commit each
   candidate will fork from (`git rev-parse --short HEAD`, `git status --short`).
   If the tree is dirty, candidates would fork from uncommitted work — stop and
   ask the user to commit/stash first, or to confirm they accept that the
   uncommitted changes are baked into every candidate.

### Phase 2: Derive & choose lenses

Read `references/lens-catalog.md`. Derive 5-6 lenses that genuinely pull in
different directions **for this task** (not the generic catalog). Present them and
ask the user to pick N:

```json
{
  "questions": [{
    "question": "Pick the design lenses for the competing candidates:",
    "header": "Lenses",
    "multiSelect": true,
    "options": [
      {"label": "<lens>", "description": "How it will change the result for THIS task"},
      {"label": "<lens>", "description": "..."}
    ]
  }]
}
```

If the user picks more or fewer than N, treat their selection count as the
effective N (it overrides any `--n` from Phase 1).

### Phase 3: Draft the design plan — and gate on approval

Before spawning anything, write a short plan and get explicit approval. The plan
states: the task summary, the N chosen lenses, the acceptance bar, the per-
candidate prompt outline (see `references/subagent-prompt.md`), the isolation
model (one worktree each, commit-in-worktree, **no push**), how candidates will be
compared, and the merge strategy (winner-base + graft).

Spawning N worktree agents is expensive and hard to undo cleanly — **this gate is
the cheap place to course-correct.** Confirm before Phase 4:

```json
{
  "questions": [{
    "question": "Launch N candidates with this plan?",
    "header": "Plan gate",
    "options": [
      {"label": "Launch", "description": "Spawn the N worktree agents as planned"},
      {"label": "Revise", "description": "Adjust lenses, acceptance bar, or prompts first"}
    ]
  }]
}
```

"Revise" → loop back to the unsatisfactory phase before spawning.

### Phase 4: Generate prompts & launch

Read `references/subagent-prompt.md`. Instantiate the prompt template once per
lens — identical task + acceptance bar, only the lens block differs. Launch all N
in a **single message** so they run concurrently:

- `Agent(isolation: "worktree", run_in_background: true)` per lens, labeled by lens.
- Each candidate commits in its own worktree, does **not** push, and returns the
  structured report from the template — including its **branch name and HEAD SHA**
  (the merge in Phase 6 needs concrete refs, not just a diff).

**Record the bookkeeping** so the merge has targets: after launch, capture
`git worktree list` and map each candidate (lens) → worktree path + branch. Pair
that with the branch/SHA each candidate reports. Without this, Phase 6 has nothing
concrete to cherry-pick from or remove.

Do not instruct candidates to invoke interactive orchestrators (e.g. `ce:work`) —
they stall waiting for headless approval. Hand them the concrete spec directly.

### Phase 5: Collect & compare

Wait for the candidates to report (each notifies on completion). If one is stopped
or errors, record it as a non-finisher and compare the survivors — never block on
a dead candidate.

Read `references/comparison-rubric.md`. Normalize the reports into the head-to-head
table and apply the scoring rubric to identify a recommended winner.

### Phase 6: Pick & merge

Present the comparison table + recommended winner + one-line rationale, then
confirm the pick (one option per candidate; the user may override):

```json
{
  "questions": [{
    "question": "Which candidate to merge as the base? (recommended: <lens>)",
    "header": "Winner",
    "options": [
      {"label": "<lens A>", "description": "<one-line why / score>"},
      {"label": "<lens B>", "description": "<one-line why / score>"},
      {"label": "<lens C>", "description": "<one-line why / score>"}
    ]
  }]
}
```

Then merge **winner-base + graft** per `references/comparison-rubric.md`: adopt the
winner's commits as the base, graft each runner-up's standout idea as a discrete
reviewable change, re-verify the acceptance bar, and clean up the loser worktrees.
Report the final state: base adopted, ideas grafted from whom, acceptance status.

## Cost & caveats

- Worktree isolation is real overhead (~200-500ms + disk per candidate). Worth it
  for genuinely competing approaches; wasteful for cheap fan-out.
- Keep candidates **flat** — no nested fan-out inside a candidate, or worktree
  cost multiplies.
- The contest only pays off when lenses diverge (Phase 2). Three lenses that
  collapse to the same code produce three near-identical results.

## Resources

- `references/lens-catalog.md` — canonical lenses + how to derive task-specific ones
- `references/subagent-prompt.md` — candidate prompt template, launch form, report schema
- `references/comparison-rubric.md` — head-to-head table, winner scoring, winner-base + graft merge
