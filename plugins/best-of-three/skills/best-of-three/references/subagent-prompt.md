# Candidate Subagent Prompt

Each candidate is one `Agent` call with `isolation: "worktree"` and
`run_in_background: true`. Every candidate gets the **same spec and acceptance
bar**; only the lens block differs. That symmetry is what makes the later
comparison fair.

## Launch

Fan out all N in a single message (parallel), one `Agent` call per lens:

```
Agent(
  description: "best-of-3: <lens> lens",
  subagent_type: "general-purpose",
  isolation: "worktree",
  run_in_background: true,
  prompt: <filled template below>
)
```

A candidate may invoke an interactive orchestrator skill (e.g. `ce:work`) or take
the spec directly — Claude Code disables `AskUserQuestion` inside subagents, so such
skills run autonomously instead of stalling on approval. Just note that an
orchestrator that fans out further multiplies worktree cost; keep nesting shallow.

## Prompt template

Fill the bracketed slots per candidate:

```
You are candidate "<lens>" in a best-of-N implementation contest. N other agents
are implementing the SAME task in isolated worktrees with different design biases.
You will NOT see them; just produce the strongest implementation under your lens.

## Task
<task summary, scope, and links to any plan/spec files>

## Acceptance bar (identical for every candidate)
<what "done" means: tests that must pass, build/lint gates, behavior to preserve>
<known blockers and the realistic bar — e.g. "integration tests skip without DB;
green = pure-unit tests pass + integration tests written and well-designed">

## Your lens: <lens>
Optimize for <lens-specific goal>. Concretely, bias toward <2-3 lens behaviors>.
When forced to trade off, resolve in favor of <lens> — but never below the
acceptance bar.

## Rules
- Work only in your worktree. Commit your work there. Do NOT push.
- Stay within the task scope; do not refactor unrelated code.
- If blocked, make the most defensible assumption, note it, and continue.

## Return (your final message IS the report — structured, no preamble)
1. Summary — what you built, in 3-5 lines.
2. Key design decisions — and how your lens drove each.
3. Acceptance status — exact test/build/lint results (commands + outcomes).
4. Diffstat & refs — files touched, ± lines; your worktree's branch name and
   HEAD SHA (report `git rev-parse HEAD` and `git branch --show-current`), plus
   each commit SHA. The orchestrator cherry-picks these by SHA during merge.
5. Risks & tradeoffs — what your lens cost; what you'd revisit.
6. Self-assessment — where this approach is strongest / weakest vs. likely rivals.
```

## Report schema (what to expect back)

Each candidate returns the 6 sections above. Normalize them into the comparison
table in `comparison-rubric.md`. If a candidate is stopped or errors, record it
as a non-finisher and compare the survivors — do not block on a dead candidate.
