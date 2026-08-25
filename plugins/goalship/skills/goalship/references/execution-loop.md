# Execution Loop

Drives a decomposed ticket graph (`decomposition.md`) to merge-ready pull
requests, one ticket per cycle, until a terminal state is reached (R3, R6,
R7, R9, R13). Every git/`tk`/`gh` operation below goes through
`${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py <subcommand> ...` (KTD1) —
the skill classifies, decomposes, implements ticket content, and interprets
gate output; the script performs every deterministic operation. Generic
ticket bookkeeping (`tk create`, `tk dep`, `tk start`, `tk reopen`,
`tk add-note` for prose) is called directly, since it carries no
safety-critical git/gh risk and the script's `_parse_key_value_note` is
designed to ignore prose notes.

`will_create_prs` is always `true` for this loop — opening a PR is the
whole point — so every preflight call passes `true`.

## Self-pacing model (KTD10)

This skill does not run as one long call. After each cycle, schedule the
next turn with `ScheduleWakeup` (`delaySeconds: 60` — the floor; there is
real forward progress to make, not an external event to wait on) instead of
looping in-context. **The wakeup `prompt` must carry the run's identity
forward explicitly** — `repo_root`, the `run_id` from the last `ledger`
call, and the original goal — since a resumed turn does not inherit this
turn's in-context memory. A wakeup that drops `run_id` starts a fresh ledger
and re-picks already-shipped tickets; treat `run_id` as required state, not
a convenience.

## Once per run: preflight (KTD5, R11)

Before the first ticket claim only — not on every self-paced turn:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py preflight <repo_root> true
```

Prints `{"ok", "remote_url", "trunk_branch", "host_tool", "failures"}`.
`ok: false` stops the run immediately — report `failures` verbatim. This
failure is never counted against R9's failure cap; it fails the whole run,
not one ticket. On `ok: true`, report the resolved `remote_url` and
`trunk_branch` before touching any ticket, so a human watching notices
immediately if this is the wrong repo. Keep `trunk_branch` and `host_tool`
in context for every later step — they're passed explicitly to every
subcommand that needs them, never re-derived.

## Every cycle

### 1. Reconcile (KTD8, R12)

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py reconcile <repo_root>
```

Prints `{"actions": [{"ticket_id", "outcome", "detail", "pr_ref"}], "auth_failure"}`.
For `retarget_base_merged`, `pr_ref` is the ticket's own recorded `pr:`
field — read it directly from here instead of re-deriving it by hand.

`auth_failure` non-null means the same credential kept failing — stop with
a preflight-class report (not a per-ticket failure) naming the tool. Never
retry into this state per-ticket.

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
surviving in-context memory (KTD10). `reconcile()` emits this outcome for
*any* crash after the claim note was written (§5's `claim` writes it
before implementation starts, KTD4) but before a ship note exists — that
includes a crash mid-implementation, on a branch with no commits at all.
Check which case this actually is before assuming there's a PR to open:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py resolve-base <repo_root> <ticket_id> <trunk_branch> <host_tool>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py branch-has-commits <repo_root> <base> <branch>
```

- **`no`** → nothing was ever implemented on this branch. This is a fresh
  implementation cycle on the existing branch/base, not a PR retry — skip
  §5 (the branch and claim note already exist) and go straight to §6
  (implement), §7 (gate), and §8/§9 as normal.
- **`yes`** → the implementation and commit survived; only the push or PR
  creation failed. Push is safe to repeat (a no-op if it already
  succeeded), then retry creation:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py push <repo_root> <branch>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py create-pr <repo_root> <host_tool> <branch> <base> "<title>" "<body>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py head-sha <repo_root> <branch>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ship <repo_root> <ticket_id> <branch> "<pr_url>" "<sha>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --ship
```

`<title>`/`<body>` come from `tk show <ticket_id>` (Conventional Commits
subject as title); `<sha>` is `head-sha`'s output — no need to re-commit,
the commit already exists from the crashed attempt.

If the retried `push` or `create-pr` call itself fails (non-zero exit), the
branch and commit are still fine but this retry attempt failed — mirror
§9's gate-failure bookkeeping (without the reset; there's nothing to reset,
the working tree was never touched this cycle) so it counts toward the
run's failure cap:

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

`<pr_ref>` is this action's own `pr_ref` field from step 1's reconcile
output — no need to re-derive it via `tk show`. Retargeting doesn't close
the loop on this ticket — it still has its own gate/ship lifecycle; this
only repoints its open PR.

If `retarget-pr` itself fails (non-zero exit), mirror §9's gate-failure
bookkeeping the same way — the PR is unaffected, only the repoint failed:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --fail
```

so a persistently-failing retarget also counts toward `FAILURE_CAP` instead
of retrying unbounded every cycle.

### 2. Read the ledger and check caps (R9, KTD9)

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id>
```

(No mutation flags — a bare status read.) If `caps_exceeded` is non-null,
stop: report the classified summary (below) with that reason. Otherwise
keep `claimed_ticket_ids` for the pick step next.

### 3. Check for a stop request (R13, KTD10)

Between tickets only, never mid-ticket. If the user has asked to stop this
run since the last cycle, stop here and report the partial-run summary —
this is the only stop mechanism; there is no bespoke stop command.

### 4. Pick the next ticket (R3)

```
tk ready
```

Plain-text lines, already sorted highest-priority first (`P0` = highest).
Take the first ticket ID not in `claimed_ticket_ids` and not already
handled by this cycle's reconciliation pass (§1's table).

**Nothing left** — distinguish exhausted from deadlocked (AE6):

```
tk blocked
```

- `tk ready` empty **and** `tk blocked` empty → **exhausted**: report and
  stop.
- `tk ready` empty **and** `tk blocked` non-empty → **deadlocked**: every
  remaining ticket has an unresolved dependency and nothing can make
  forward progress (reconciliation already ran this cycle, so no
  currently-claimable ticket is merely "in flight" — a genuine cycle or an
  externally-unresolvable dependency is the only way this state occurs).
  Report and stop, naming it "deadlocked" distinctly from "exhausted."

### 5. Claim and branch (KTD4, KTD5)

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --claim <ticket_id>
```

Claim in the ledger *first* — before anything else touches git — so even a
crash on the very next step still keeps this ticket out of re-picking this
run (R5).

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py dirty <repo_root>
```

Non-empty → stop: report the dirty paths (KTD5 defense-in-depth; this
should never fire if the prior cycle reset cleanly, so a nonempty result
means something outside this loop's control touched the tree).

```
tk start <ticket_id>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py resolve-base <repo_root> <ticket_id> <trunk_branch> <host_tool>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py branch-name <repo_root> <type> "<ticket title>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py claim <repo_root> <ticket_id> <branch_name> <base_ref> <trunk_branch>
```

`claim` creates the branch off `base_ref` and records the claim note
(`branch:`, plus `base:` only when `base_ref` differs from trunk —
stacked) in one step, so a crash between the two never happens.

### 6. Implement (skill judgment)

Read the ticket (`tk show <ticket_id>`) for its acceptance criteria and
implement it following the target repo's existing conventions. This is
ordinary implementation work, not a re-invention of it.

### 7. Gate (KTD1, KTD3 — see `gate-discovery.md`)

Run and interpret the target repo's own gates directly — the script never
wraps gate execution, so gate output stays visible in the transcript.

**On pass** → §8 (ship). **On fail** → §9 (note and reset).

### 8. Ship (R4, R5)

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py commit <repo_root> "<type>: <subject>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py push <repo_root> <branch_name>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py create-pr <repo_root> <host_tool> <branch_name> <base_ref> "<title>" "<body>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ship <repo_root> <ticket_id> <branch_name> "<pr_url>" "<sha from commit>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --ship
```

`ship` writes the closing note (branch, PR URL, head SHA — R5) and closes
the ticket in one step. Continue to §10.

### 9. Note and reset on gate failure (R3, R5, KTD4)

```
tk add-note <ticket_id> "Gate failed: <failing command>
<redacted, length-capped output excerpt>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py reset <repo_root> <base_ref>
tk reopen <ticket_id>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_runner.py ledger <repo_root> --run-id <run_id> --fail
```

Redact common secret-shaped patterns (`KEY=value` env assignments,
bearer/API-token-shaped strings) and cap the excerpt's length before
writing it (KTD1) — target-repo gate failures routinely surface secrets in
stack traces or env dumps. Do not retry this ticket again this run — the
ledger claim from §5 already guarantees `tk ready` won't surface it as
unclaimed. Continue to §10.

### 10. Scope-creep check (R6)

If implementation surfaced clearly out-of-scope work, file it rather than
expanding the ticket just processed:

```
tk create "<new title>" -t <type> --acceptance "<criteria>"
tk dep <new_id> <ticket_id>          # only if the new work blocks/depends on it
tk add-note <ticket_id> "Discovered: <new_id> — <one-line reason>"
```

The back-reference note lets the relationship read from either ticket. A
new ticket filed here is picked up by a later cycle's own `tk ready` pass
like any other ticket — never implemented inline as part of this cycle.

### 11. Loop or stop

Re-check `caps_exceeded` from §2's ledger read after this cycle's `--ship`
or `--fail` (it was recomputed as part of that same call — no extra read
needed). If capped, stop and report. Otherwise schedule the next wakeup
(self-pacing model, above) with `noop: false` — this cycle shipped, failed,
or blocked a ticket, which is never a no-op tick.

## Terminal states and summary (R7)

Every terminal path — exhausted, deadlocked, a cap hit (R9), or a user stop
(R13) — ends with a summary classifying every ticket touched this run:

- **Shipped** — PR opened, ticket closed (§8, or `closed_merged` from
  reconciliation).
- **Failed / blocked** — gate failure (§9), or a reconciliation outcome
  that left it blocked (`failed_closed_unmerged`, `blocked_stale_base`).
- **Not reached** — remaining ready or blocked tickets never picked this
  run, explicitly including any ticket filed by §10's scope-creep check
  that never got its own cycle.

State which terminal condition ended the run by name (exhausted /
deadlocked / cap reached / user stop) — the four are distinct outcomes, not
interchangeable ways of saying "stopped."
