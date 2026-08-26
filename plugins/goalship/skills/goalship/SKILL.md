---
name: goalship
description: This skill should be used when the user asks to "turn this goal into tickets and ship it", "run goalship on this", "decompose this goal and implement it unattended", or "hand this goal off and open PRs for each piece". Decomposes a goal into a tk ticket graph, then runs a self-pacing loop that implements, gates, commits, pushes, and opens a pull request for each ready ticket until the graph is exhausted.
argument-hint: "<goal description>"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, Skill, Agent, AskUserQuestion, ScheduleWakeup]
---

Take a stated goal from a `tk` ticket graph to merge-ready pull requests,
unattended, across as many self-paced turns as the graph needs.

## Preconditions

Confirm before doing anything else:

- The invocation carries a concrete goal. If empty or too vague to
  decompose, ask the user to state it — do not invent one.
- Inside a git work tree with `tk` on `PATH` (`git rev-parse
  --is-inside-work-tree`, `which tk`). Report and stop if either is
  missing — the execution loop's own preflight (below) checks the rest.

## Process

### Phase 1: Decompose the goal into tickets

1. **Classify and decompose** the goal into a `tk` ticket graph — see
   `references/decomposition.md` for the size/ambiguity heuristic, the
   inline `tk create`/`tk dep` path, the `ce-plan`/`ce-brainstorm`
   escalation path, and how acceptance criteria get authored. This phase
   may block on `ce-plan`/`ce-brainstorm`'s own clarifying questions for a
   large or ambiguous goal — that's expected; the "never blocked"
   guarantee below applies only to Phase 2, which begins once
   decomposition has produced a ticket graph.

### Phase 2: Preflight and the self-pacing execution loop

2. **Run preflight once**, before claiming any ticket: `tk` present, a
   configured remote, a clean tree, and an authenticated `gh`/`glab`. Stop
   immediately on failure — see `references/execution-loop.md`'s Preflight
   section. This is never blocked on user input; a failure here is reported
   and the run stops rather than asking what to do.
3. **Run the self-pacing loop** — reconcile in-progress tickets against
   git/PR state, pick the highest-priority unclaimed ready ticket,
   implement it, run the target repo's own gates (`references/gate-discovery.md`),
   and on a pass branch/commit/push/open-or-reuse-a-PR/close-with-note or,
   on a failure, note the reason and move on — repeating across self-paced turns
   until a terminal state is reached. The full step-by-step protocol,
   including the exact `loop_runner.py` invocations for every git/`tk`/`gh`
   operation, is `references/execution-loop.md` — follow it exactly rather
   than improvising the sequence, since the ordering (claim in the ledger
   before touching git, branch before implementing, reset before the next
   claim) is what keeps a crash mid-run recoverable.

Once the loop starts, the user is never blocked on a per-ticket
confirmation — the only interruption it accepts is a stop request observed
between tickets (never mid-ticket), which ends the run cleanly with the
same summary format as any other terminal state.

## Terminal summary

Every run ends by reporting which of four terminal states was reached —
**exhausted** (no ready or blocked work left), **deadlocked** (remaining
tickets are mutually blocked with no forward path), a **run cap** reached
(ships or consecutive failures), or a **user stop** — plus a classification
of every ticket touched this run as shipped, failed/blocked, or not-reached.
See `references/execution-loop.md`'s Terminal states section for the exact
classification rules.

## Safety guardrails

Never merge or approve a pull request, force-push, delete a branch this
skill did not create, or take a package-registry publish action. Every
git/`tk`/`gh` operation goes through `${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py`
(see `references/execution-loop.md`), which exposes no code path for any of
those — this is asserted directly against the script's source in
`tests/test_branching.py`, not just documented here. The one exception is
the sub-agent that `execution-loop.md`'s implement step delegates
implementation to: it carries ordinary `Bash` access and is held to this
same boundary by instruction, not by the script's structural guarantee —
see that section for the exact restriction it's given.

## Bundled resources

- `references/decomposition.md` — size/ambiguity classification, the inline
  and `ce-plan`/`ce-brainstorm`-escalation paths (which also fixes the
  run's shipping mode — see `execution-loop.md`'s Shipping mode section),
  acceptance-criteria authoring.
- `references/gate-discovery.md` — how to find and run the target repo's
  own gates, and the pass/fail/no-gates-found policy.
- `references/execution-loop.md` — the full per-cycle protocol: preflight,
  reconciliation, ticket pick, claim/branch, implement, gate, ship-or-note,
  scope-creep handling, cap/stop checks, and the self-pacing wakeup
  mechanism.
- `references/run-state-schema.md` — the run-state ledger's on-disk shape
  and lifecycle, for anyone inspecting or debugging a run's `.goalship/`
  directory directly.
