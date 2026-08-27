# Execution Loop

Drives a decomposed ticket graph (`decomposition.md`) to merge-ready pull
requests, one ticket per cycle, until a terminal state is reached. Every
git/`tk`/`gh` operation below goes through
`${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py <subcommand> ...` —
the orchestrating loop classifies, decomposes, and interprets gate output;
a fresh sub-agent implements each ticket's content; the script
performs every deterministic operation. Generic ticket bookkeeping
(`tk create`, `tk dep`, `tk start`, `tk reopen`, `tk add-note` for prose) is
called directly, since it carries no safety-critical git/gh risk and the
script's `_parse_key_value_note` is designed to ignore prose notes.

`will_create_prs` is always `true` for this loop — opening a PR is the
whole point — so every preflight call passes `true`.

## Shipping mode

Two ways a ticket's work reaches a pull request, chosen once by
`decomposition.md`'s classification and never re-derived mid-run:

- **branch mode** — one ticket, one branch, one commit, one PR. A
  dependent ticket's branch stacks on its predecessor's. Used by
  `decomposition.md`'s escalation path (large or ambiguous goals).
- **commit mode** — one *run* gets one shared branch and one PR; each
  ticket still contributes exactly one commit, but to that shared branch,
  always based on `trunk_branch` directly (no stacking). Dependency
  ordering falls out of commit ancestry for free — `tk ready` already only
  surfaces tickets whose dependencies are closed, so the pick order is
  already a valid topological sort. Used by `decomposition.md`'s inline
  path (small, single-outcome goals).

Every step below that differs by mode says so explicitly; anything not
marked applies to both.

## Self-pacing model

This skill does not run as one long call — each cycle ends at a decision
point (Loop or stop, below) that either schedules the next turn or ends
this one. Which it does depends on whether `ScheduleWakeup` is available
in this session, checked once in preflight (below); nothing about a
cycle's own mechanics changes either way.

**The first `ledger` call of a run** — preflight's resume check finding no
candidate, then the ledger-and-caps read's first call — has no `run_id` yet and
also passes `--goal "<goal>" --ticket-mode <branch|commit> --trunk-branch
<resolved trunk branch>` (Shipping mode, above, and the trunk-branch
determination step in Once per run: preflight, below), persisting all
three on the ledger's `goal`, `ticket_mode`, and `trunk_branch` fields
from the start. Every later call for this run passes `--run-id` alone;
all three carry forward from the persisted ledger rather than needing to
be resupplied.

**Where `ScheduleWakeup` is available**: schedule the next turn at the end
of every cycle (`delaySeconds: 60` — the floor; there is real forward
progress to make, not an external event to wait on) instead of looping
in-context. **The wakeup `prompt` must carry the run's identity forward
explicitly** — `repo_root`, the `run_id` from the last `ledger` call, the
original goal, and `ticket_mode` — since a resumed turn does not inherit
this turn's in-context memory. A wakeup that drops `run_id` starts a fresh
ledger and re-picks already-shipped tickets; treat `run_id` and
`ticket_mode` both as required state, not a convenience.

**Where it isn't** (e.g. Amazon Bedrock, and AWS/GCP/Azure-hosted Claude
Platform variants): end the turn after this cycle instead of attempting to
loop through more tickets in-context. Report that continuing this run
requires a fresh invocation of this skill in the same repo, and rely on
the resume check (preflight, below) to pick it up without needing
`run_id`, the goal, or `ticket_mode` restated — that's exactly what
persisting `goal` and `ticket_mode` on the ledger (above) is for.

A wakeup or cold re-invocation that arrives without `ticket_mode` set on
the ledger (a run started before this field existed, or an older wakeup
prompt authored before this run's tooling knew about it) must recover it
before picking anything, not guess:

- Two or more of `claimed_ticket_ids` (kept from the ledger-and-caps read,
  below) sharing an identical `branch:` note → commit mode, unambiguously —
  branch mode never lets two tickets share a branch.
- Two or more with *different* `branch:` notes → branch mode,
  unambiguously.
- Fewer than two tickets claimed so far → not yet observable from `tk`
  state alone (a single ticket looks the same under either mode when its
  base happens to be trunk). Fall back to applying `decomposition.md`'s
  own size/ambiguity classification to the original goal again — the same
  judgment call decomposition already made, not a fresh guess.

Even where `ScheduleWakeup` is available, a scheduled wakeup only fires
into a session whose process is still alive to receive it — closing the
terminal (or otherwise ending a local CLI session) pauses the run rather
than continuing it. This is safe, not fatal, and no different in effect
from `ScheduleWakeup` being unavailable in the first place: reconciliation
(below) and the resume check pick up cleanly from the ledger the next time
the skill runs, whether that's a surviving wakeup or a human manually
re-invoking it later. State this plainly in the run's opening report —
"unattended" means self-resuming only where `ScheduleWakeup` is available
and the session stays reachable; everywhere else it means no per-ticket
confirmation is needed, but continuing past a paused turn takes one fresh
invocation, which the resume check makes a plain re-run rather than
something requiring any special phrasing.

## Once per run: preflight

Before the first ticket claim — and, for the resume check specifically,
before Phase 1's decomposition even starts (SKILL.md), since a resumable
run's ticket graph must not be decomposed a second time — not on every
self-paced turn:

**Check for a resumable run:**

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py resume-candidates <repo_root>
```

Empty → this is a fresh run; proceed to decomposition (`decomposition.md`)
as normal. One candidate → resume it instead: skip decomposition
entirely (its ticket graph already exists in `tk`), carry its `run_id`,
`goal`, and `ticket_mode` into the cycle below, and say so plainly in the
opening report rather than silently continuing as if this were a fresh
run. More than one candidate — two incomplete goalship runs left in the
same repo — is an ambiguous edge case: list them and ask which to resume,
or whether to start a new run alongside them, the same way
`decomposition.md`'s own escalation path already blocks on an ambiguous
call before a run is underway; the "never blocked" guarantee (SKILL.md)
applies only once one is.

**Check whether `ScheduleWakeup` is available** in this session — the same
passive check `decomposition.md` uses for `ce-plan`: look for it among the
tools available this session. Never call it speculatively to find out —
a successful call ends the turn immediately, and an unsupported harness
may silently no-op rather than error, so neither outcome gives a usable
signal. Carry the result forward for every cycle's Loop-or-stop step
(below) — Self-pacing model, above, covers both paths.

**Decide whether to supply a trunk-branch override** before calling
`preflight`, next. Its optional third positional argument, when given,
replaces its own autodetection (`origin/HEAD`, then a local
`main`/`master`, then the current branch) outright rather than feeding
into it — preflight never guesses beyond that fixed heuristic on its own.
Supplying an override is entirely the orchestrating session's call, drawn
from context preflight doesn't have: a human stating the trunk branch
explicitly in the goal, or this session reading the target repo's own
`CLAUDE.md`/`AGENTS.md` for a named integration branch before the run
starts. Confirming which applies, when neither source settles it, is
legal here — strictly before Phase 2's cycles begin — the same way the
resume check above already blocks on an ambiguous case rather than
guessing; the "never blocked" guarantee (SKILL.md) applies only once a
cycle is running, and nothing here relaxes it inside one.

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py preflight <repo_root> true [<trunk_branch>]
```

Omit `<trunk_branch>` to autodetect as above; pass it to override. Prints
`{"ok", "remote_url", "trunk_branch", "host_tool", "failures"}` — an
override that doesn't resolve to `refs/heads/<name>` or
`refs/remotes/origin/<name>` lands in `failures`, naming the missing
branch, rather than silently falling back to autodetection. `ok: false`
stops the run immediately — a fixable environment problem, not
one another invocation can retry past on its own, so mark it terminal
before reporting `failures` verbatim (skip this on a fresh run with no
`run_id` yet — there's no ledger for it to apply to):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --terminal aborted
```

This failure is never counted against the failure cap; it fails the whole
run, not one ticket. On `ok: true`, report the resolved `remote_url` and
`trunk_branch` before touching any ticket — naming whether `trunk_branch`
came from an override or autodetection — so a human watching notices
immediately if this is the wrong repo or the wrong branch. Keep
`trunk_branch` and `host_tool` in context for every later step — they're
passed explicitly to every subcommand that needs them, never re-derived.

This resolved value is what the run's first `ledger` call persists onto
the ledger's `trunk_branch` field (Self-pacing model, above). A resumed
turn's own ledger-and-caps read (below) then gets `trunk_branch` back from
that same persisted ledger, the same way it already does for `goal` and
`ticket_mode`, rather than this run needing to re-invoke preflight's
git-based autodetection on every resumed turn.

## Every cycle

### 1. Reconcile

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py reconcile <repo_root>
```

Prints `{"actions": [{"ticket_id", "outcome", "detail", "pr_ref"}], "auth_failure"}`.
For `retarget_base_merged`, `pr_ref` is the ticket's own recorded `pr:`
field — read it directly from here instead of re-deriving it by hand.

`auth_failure` non-null means the same credential kept failing — a broken
credential won't fix itself on the next invocation either, so mark it
terminal (skip this on a fresh run's first cycle — Reconcile runs before
the ledger-and-caps read that mints `run_id` there, so on a fresh run
there's no ledger yet for it to apply to; a resumed run already has
`run_id` from the resume check, above):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --terminal aborted
```

then stop with a preflight-class report (not a per-ticket failure) naming
the tool. Never retry into this state per-ticket.

Otherwise, handle each action by `outcome` before moving to picking:

| outcome | script already did | this cycle also does |
|---|---|---|
| `closed_merged` | closed the ticket, wrote the note | nothing — record it "shipped externally" in this run's eventual summary |
| `closed_ship_note_orphaned` (`detail` = branch, `pr_ref` = this ticket's own PR) | closed the ticket | nothing — the ship note had already completed (`pr:`/`sha:` both recorded) before a crash interrupted the close that should have followed it; this cycle just finishes it |
| `failed_closed_unmerged` | reopened the ticket, wrote the note | nothing — it's a normal `tk ready` candidate again; its stale `branch:` note is superseded automatically the next time it's claimed (claim notes merge oldest→newest) |
| `no_recoverable_state` | nothing (signal only) | nothing special — treat `ticket_id` as an ordinary fresh pick when it surfaces from `tk ready` (it has no branch, so there's no git state to lose) |
| `retry_pr_creation` (`detail` = branch) | nothing (signal only) | retry PR creation now, before picking anything new (below) |
| `retarget_base_merged` (`detail` = old base, `pr_ref` = this ticket's own PR) | nothing (signal only) | retarget that ticket's already-open PR now (below) |
| `blocked_stale_base` (`detail` = old base) | wrote a blocked note | nothing further — leave it; it's excluded from `tk ready` picking below by virtue of staying `in_progress` with no forward path |
| `pr_state_unresolved` | nothing | treat like a transient lookup failure — leave it for the next cycle's reconcile pass rather than guessing at its state |

**Retry PR creation** (`retry_pr_creation`, `detail` = branch): re-derive
everything fresh — across self-paced turns there is no guarantee of
surviving in-context memory. `reconcile()` emits this outcome for
*any* crash after the claim note was written (the claim-and-branch step's
`claim` call writes it before implementation starts) but before a ship
note exists — that includes a crash mid-implementation, on a branch with
no commits at all. Check which case this actually is before assuming
there's a PR to open. Read this ticket's own `claim_sha` from `tk show
<ticket_id>`'s notes, then:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py commit-landed <repo_root> <branch> <claim_sha>
```

Ticket-scoped, not branch-wide: in commit mode `branch` also carries every
earlier ticket this run already shipped, so a "does this branch have any
commits at all past its base" check would misattribute their work to this
ticket. Same check for both shipping modes; only what happens next differs.

- **`no`** → nothing was implemented on this branch since this ticket's
  own claim. This is a fresh implementation cycle on the existing branch,
  not a PR retry — skip claiming again and go straight to implementation,
  then gate, then ship (or note-and-reset on a gate failure), as normal.
- **`yes`** → the implementation and commit survived; only the push or PR
  creation failed. Push is safe to repeat (a no-op if it already
  succeeded):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py push <repo_root> <branch>
```

  then retry PR creation exactly as the Ship step (below) does — `find-pr`
  first, `create-pr` only on a miss, using `base_ref` (branch mode:
  resolve it via `resolve-base`, the same call the claim step makes;
  commit mode: always `trunk_branch`, no `resolve-base` call) — then
  finish the same way:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py head-sha <repo_root> <branch>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ship <repo_root> <ticket_id> <branch> "<pr_url>" "<sha>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --ship
```

`<title>`/`<body>` come from `tk show <ticket_id>` (Conventional Commits
subject as title); `<sha>` is `head-sha`'s output — no need to re-commit,
the commit already exists from the crashed attempt.

If the retried `push` or `create-pr` call itself fails (non-zero exit), the
branch and commit are still fine but this retry attempt failed — mirror the
gate-failure step's bookkeeping (without the reset; there's nothing to
reset, the working tree was never touched this cycle) so it counts toward
the run's failure cap:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --fail
```

Leave the ticket as-is (still `in_progress`, still no `pr:` note) — the
next cycle's reconcile pass will surface this same `retry_pr_creation`
outcome again. Without this call, a persistently-failing retry (bad
credentials, a network partition to the host) would never increment
`consecutive_failures`, so `FAILURE_CAP` would never fire for this failure
class.

**Retarget a stale-base PR** (`retarget_base_merged`):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py retarget-pr <repo_root> <host_tool> <pr_ref> <trunk_branch>
```

`<pr_ref>` is this action's own `pr_ref` field from the reconcile step's
output — no need to re-derive it via `tk show`. Retargeting doesn't close
the loop on this ticket — it still has its own gate/ship lifecycle; this
only repoints its open PR.

If `retarget-pr` itself fails (non-zero exit), mirror the gate-failure
step's bookkeeping the same way — the PR is unaffected, only the repoint
failed:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --fail
```

so a persistently-failing retarget also counts toward `FAILURE_CAP` instead
of retrying unbounded every cycle.

### 2. Read the ledger and check caps

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id>
```

(A bare status read on every call but the run's very first, which also
carries `--goal`/`--ticket-mode`/`--trunk-branch` — Self-pacing model,
above.) If
`caps_exceeded` is non-null, stop:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --terminal capped
```

then report the classified summary (below) with that reason. Otherwise
keep `claimed_ticket_ids` for the pick step next, plus `trunk_branch` for
the claim step on a turn that didn't itself run preflight (Once per run:
preflight, above).

### 3. Check for a stop request

Between tickets only, never mid-ticket. If the user has asked to stop this
run since the last cycle, stop here:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --terminal user_stop
```

then report the partial-run summary — this is the only stop mechanism;
there is no bespoke stop command.

### 4. Pick the next ticket

```
tk ready
```

Plain-text lines, already sorted highest-priority first (`P0` = highest).
Take the first ticket ID not in `claimed_ticket_ids` and not already
handled by this cycle's reconciliation pass (the table above).

**Nothing left** — distinguish exhausted from deadlocked:

```
tk blocked
```

- `tk ready` empty **and** `tk blocked` empty → **exhausted**:
  `ledger <repo_root> --run-id <run_id> --terminal exhausted`, then report
  and stop.
- `tk ready` empty **and** `tk blocked` non-empty → **deadlocked**: every
  remaining ticket has an unresolved dependency and nothing can make
  forward progress (reconciliation already ran this cycle, so no
  currently-claimable ticket is merely "in flight" — a genuine cycle or an
  externally-unresolvable dependency is the only way this state occurs).
  `ledger <repo_root> --run-id <run_id> --terminal deadlocked`, then report
  and stop, naming it "deadlocked" distinctly from "exhausted."

### 5. Claim and branch

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --claim <ticket_id>
```

Claim in the ledger *first* — before anything else touches git — so even a
crash on the very next step still keeps this ticket out of re-picking this
run.

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py dirty <repo_root>
```

Non-empty → stop: mark it terminal —

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --terminal aborted
```

— then report the dirty paths (defense-in-depth; this should never fire
if the prior cycle reset cleanly, so a nonempty result means something
outside this loop's control touched the tree, which a bare re-invocation
can't clean up on its own).

```
tk start <ticket_id>
```

Branch name and `base_ref` depend on this run's shipping mode (Shipping
mode, above):

- **branch mode**:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py resolve-base <repo_root> <ticket_id> <trunk_branch> <host_tool>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py branch-name <repo_root> <type> "<ticket title>"
```

  `resolve-base`'s output is `base_ref`.

- **commit mode**: `base_ref` is always `trunk_branch` — no `resolve-base`
  call. Reuse the run's branch if one already exists, discovered from
  `claimed_ticket_ids` (kept from the ledger-and-caps read, above — the
  tickets this run has already claimed) rather than a new ledger field, so
  a lost/corrupted ledger doesn't strand this discovery:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py run-branch <repo_root> <claimed_ticket_ids...>
```

  A result is `branch_name` — reuse it. No result means this is the run's
  first ticket: compute a fresh name off the *goal itself*, not this
  ticket, since every later ticket this run will share it — on a run
  resumed cold (preflight's resume check, above), `<goal title>` is the
  ledger's own `goal` field, not anything restated by this invocation —

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py branch-name <repo_root> goal "<goal title>"
```

Either way, `base_ref` and `branch_name` are now defined; claim:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py claim <repo_root> <ticket_id> <branch_name> <base_ref> <trunk_branch>
```

`claim` creates the branch off `base_ref` — or, on an already-existing
branch (always the case for commit mode's second-and-later tickets), checks
it out instead — and records the claim note (`branch:`, plus `base:` only
when `base_ref` differs from trunk — stacked; never written in commit
mode, where `base_ref` is always trunk) in one step, so a crash between
branch setup and the note never happens.

### 6. Implement (delegated to a fresh sub-agent)

Delegate the actual code change to a fresh, non-fork `Agent` call scoped to
this ticket alone — not `isolation: "worktree"`, since the gate step and
the ship step's commit need the change to land as uncommitted edits
directly in `repo_root`'s own working tree (already checked out to
`branch_name` by the claim step's `claim` call), not an isolated worktree
copy. This keeps each ticket's exploration, false starts, and diffs out of
the orchestrating loop's own context instead of letting them accumulate
across a multi-ticket run — the crash-recovery design throughout this
document already assumes no cycle can rely on a prior cycle's in-context
memory, so a stateless sub-agent changes nothing about the protocol's
correctness.

```
Agent(
  description: "Implement <ticket_id>",
  subagent_type: "general-purpose",
  prompt: "<self-contained brief, see below>",
)
```

The prompt must be self-contained — the sub-agent has no memory of this run
or this conversation — and must carry:

- `repo_root`, stated explicitly as the working directory to edit in; the
  branch is already checked out, so the sub-agent neither creates nor
  switches branches.
- The ticket's title, description (if present), and acceptance criteria
  (`tk show <ticket_id>`).
- An instruction to implement it following the target repo's existing
  conventions — ordinary implementation work, not a re-invention of it.
- **The same boundary this skill holds itself to**: edit files only. Never
  commit, push, open or touch a pull request, or run any `tk`/`git`/`gh`/
  `glab` mutation — those stay exclusively in the gate, ship, and
  gate-failure steps below. A general-purpose sub-agent has ordinary
  `Bash` access and is not structurally prevented from crossing this line
  the way `loop_runner.py` is (see `SKILL.md`'s Safety guardrails) — state
  the boundary explicitly rather than assume it's inferred.
- A request for a short final report: files touched, a one-line summary of
  what changed, and any clearly out-of-scope work noticed while
  implementing (feeds the scope-creep check below). The base `Agent` tool
  has no structured-output enforcement — ask for this in plain prose and
  read it back rather than assume a fixed schema.

Gate execution stays with the orchestrating loop, next, rather than
also being delegated — the target repo's gate output needs to stay visible
in *this* transcript, not summarized second-hand inside a sub-agent's
report.

### 7. Gate (see `gate-discovery.md`)

Run and interpret the target repo's own gates directly — the script never
wraps gate execution, so gate output stays visible in the transcript.

**On pass** → ship (below). **On fail** → note and reset (below).

### 8. Ship

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py commit <repo_root> "<type>: <subject>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py push <repo_root> <branch_name>
```

Check for a PR this run already opened before creating a new one — a no-op
lookup in branch mode (always empty there, since no other ticket shares
this branch), and the mechanism that lets commit mode's second-and-later
tickets land on the run's one shared PR instead of opening their own:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py find-pr <repo_root> <host_tool> <branch_name>
```

A URL → reuse it, skip `create-pr`. Empty → create one, using `base_ref`
from the claim step above:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py create-pr <repo_root> <host_tool> <branch_name> <base_ref> "<title>" "<body>"
```

Either way, finish the same:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ship <repo_root> <ticket_id> <branch_name> "<pr_url>" "<sha from commit>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --ship
```

`ship` writes the closing note (branch, PR URL, head SHA) and closes
the ticket in one step. Continue to the scope-creep check.

### 9. Note and reset on gate failure

```
tk add-note <ticket_id> "Gate failed: <failing command>
<redacted, length-capped output excerpt>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py reset <repo_root> <base_ref>
tk reopen <ticket_id>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --fail
```

Redact common secret-shaped patterns (`KEY=value` env assignments,
bearer/API-token-shaped strings) and cap the excerpt's length before
writing it — target-repo gate failures routinely surface secrets in
stack traces or env dumps. Do not retry this ticket again this run — the
ledger claim already guarantees `tk ready` won't surface it as
unclaimed. Continue to the scope-creep check.

### 10. Scope-creep check

If the implement step's sub-agent report flagged clearly out-of-scope
work — or it's otherwise apparent from reviewing the diff — file it rather
than expanding the ticket just processed:

```
tk create "<new title>" -t <type> --acceptance "<criteria>"
tk dep <new_id> <ticket_id>          # only if the new work blocks/depends on it
tk add-note <ticket_id> "Discovered: <new_id> — <one-line reason>"
```

`--acceptance` follows the same definable/testable/measurable, one-flag,
list-of-bullets rule as `decomposition.md`'s Acceptance criteria section —
scope-creep tickets get held to the same bar as tickets from decomposition,
not a lighter one just because they're filed mid-loop.

The back-reference note lets the relationship read from either ticket. A
new ticket filed here is picked up by a later cycle's own `tk ready` pass
like any other ticket — never implemented inline as part of this cycle.

### 11. Loop or stop

Re-check `caps_exceeded` from the ledger-and-caps read after this cycle's
`--ship` or `--fail` (it was recomputed as part of that same call — no
extra read needed). If capped:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --terminal capped
```

then stop and report. Otherwise, if `ScheduleWakeup` is available (checked
once in preflight, above), schedule the next wakeup (Self-pacing model,
above) with `noop: false` — this cycle shipped, failed, or blocked a
ticket, which is never a no-op tick. If it isn't available, end the turn
here instead: report this cycle's outcome and that continuing requires a
fresh invocation of this skill in the same repo — the resume check
(preflight, above) picks it up automatically from there.

## Terminal states and summary

Every terminal path — exhausted, deadlocked, a cap hit, or a user stop —
ends with a summary classifying every ticket touched this run:

- **Shipped** — its commit landed on the run's PR (opened by this ticket,
  or reused from an earlier ticket this run in commit mode) and the ticket
  closed (the ship step, or `closed_merged` from reconciliation).
- **Failed / blocked** — gate failure (the note-and-reset step), or a
  reconciliation outcome that left it blocked (`failed_closed_unmerged`,
  `blocked_stale_base`).
- **Not reached** — remaining ready or blocked tickets never picked this
  run, explicitly including any ticket filed by the scope-creep check
  that never got its own cycle.

State which terminal condition ended the run by name (exhausted /
deadlocked / cap reached / user stop) — the four are distinct outcomes, not
interchangeable ways of saying "stopped."
