# best-of-three

Run the same task as N independent implementations — each with a different design
bias — then compare them head-to-head, pick a winner, and graft the best ideas
from the runners-up. For tasks with multiple defensible approaches, comparing real
implementations beats arguing about them up front.

## Features

### Skills
- **best-of-three** — Triggers on "best of 3", "run 3 competing agents", "try N
  implementations and compare", "compete implementations and pick the best".
  Gathers the task and acceptance bar, derives design lenses and lets you pick N,
  gates on an approved plan, fans out N isolated worktree agents in parallel, then
  compares the reports, picks a winner, and merges via winner-base + graft.

## Examples

```bash
/best-of-three implement the M2 leader-election module from docs/plans/m2.md
/best-of-three --n 3 refactor the upsert dedup path in dao/job.go
```

## Installation

### Requirements
- Git repository (each candidate runs in its own `git worktree`).
- Claude Code (uses the `Agent` tool with worktree isolation and `AskUserQuestion`).

```bash
/plugin install best-of-three@agent-extentions
```

## Usage

Invoke `/best-of-three` with a task description. The skill walks six phases:

1. **Gather** — captures the goal, scope, acceptance bar, blockers, and base commit.
2. **Lenses** — proposes 5-6 task-specific design lenses; you pick N (default 3).
3. **Plan gate** — drafts the design plan and waits for your approval before spawning.
4. **Launch** — fans out N background worktree agents, same spec, different lens each.
5. **Compare** — normalizes the candidate reports into a head-to-head table.
6. **Pick & merge** — you confirm the winner; it adopts the winner as base and
   grafts the standout ideas from the runners-up, then cleans up the worktrees.

Candidates commit inside their own worktrees and never push. It is **redundant-
compete** (N full solutions to the same spec, then judge) — use it when a task has
real design tension, not for one-off work where it is N× the cost.

## License

MIT
