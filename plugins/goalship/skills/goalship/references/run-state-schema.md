# Run-State Ledger Schema

The backing script (`scripts/loop_runner.py`) persists one JSON file per run
under `<repo_root>/.goalship/<run_id>.json`. One file per `run_id` — not a
single shared file keyed internally — so two runs against the same repo
(a resumed session, or a second concurrent invocation) never contend for the
same file and can't lose an update to a concurrent write.

## Fields

```json
{
  "run_id": "a1b2c3d4e5f6",
  "shipped_count": 3,
  "consecutive_failures": 1,
  "claimed_ticket_ids": ["T-12", "T-14", "T-15"],
  "goal": "ship the widget",
  "ticket_mode": "branch",
  "terminal_state": null,
  "trunk_branch": "main"
}
```

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | Opaque identifier for this run. Generated once per fresh invocation (`generate_run_id()`), then reused for every subsequent self-pacing turn of the same run. |
| `shipped_count` | int | Tickets shipped this run — their commit landed on the run's PR, whether this ticket opened it or reused one an earlier ticket opened (commit mode). Compared against `SHIP_CAP` (10, fixed). |
| `consecutive_failures` | int | Gate failures and blocks, counted together, since the last successful ship. Compared against `FAILURE_CAP` (3, fixed). Resets to `0` on a successful ship; does not reset on a block. |
| `claimed_ticket_ids` | array of string | Tickets already processed (shipped, failed, or blocked) this run. `tk ready` lists both open and in-progress tickets, so this set — not `tk`'s own status field — is what stops the loop from re-picking a ticket it already handled this run. |
| `goal` | string | The original goal text, set on the first `ledger` call of the run (`--goal`). Empty on a ledger that predates this field. |
| `ticket_mode` | string or null | `"branch"` or `"commit"` (Shipping mode, `execution-loop.md`), set once on the first `ledger` call of the run (`--ticket-mode`) and never re-derived. `null` on a ledger that predates this field or hasn't set it yet. |
| `trunk_branch` | string or null | The resolved trunk branch, set on the first `ledger` call of the run (`--trunk-branch`). `null` on a ledger that predates this field. |
| `terminal_state` | string or null | One of `exhausted`, `deadlocked`, `capped`, `user_stop` once the run has ended (`--terminal`); `null` while the run is still resumable. This is what `find_resumable_runs` filters on — see Resuming a cold invocation, below. |

## Lifecycle

- **Fresh run**: no ledger file exists for the run_id yet. `load_run_state` returns a zeroed `RunState`.
- **Resumed run** (same run_id, later self-pacing turn): `load_run_state` reads the existing file and preserves its counts.
- **Every write** goes through `save_run_state`, which writes to a `.tmp` sibling and renames it into place — a crash mid-write never leaves a corrupt ledger.
- **Excluded from git**: `ensure_ledger_excluded` adds `/.goalship/` to `.git/info/exclude` (not the target repo's own `.gitignore` — this plugin runs against repos it doesn't own). The working-tree-clean check (`dirty_paths`) already ignores this directory by name, so writing the ledger never trips the dirty-tree guard.

## Resuming a cold invocation

A wakeup prompt carries `run_id`, `goal`, and `ticket_mode` forward
explicitly (Self-pacing model, `execution-loop.md`), so a session resumed
that way never needs to guess them. A *cold* re-invocation — no
`ScheduleWakeup` on this harness, or a session that died before a
scheduled wakeup fired — has none of that context and, before this
section's fields existed, had no way to find the run at all: the ledger
file is named by `run_id`, an opaque value nothing on disk pointed back
to.

`find_resumable_runs(repo_root)` (`resume-candidates` on the CLI) closes
that gap by scanning `.goalship/*.json` directly rather than relying on a
single well-known pointer file — a pointer file would reintroduce the
shared-file contention `resolve_ledger_path`'s one-file-per-run_id design
exists to avoid (Lifecycle, above). It returns every ledger whose
`terminal_state` is still `null`: a run that ended (exhausted, deadlocked,
capped, or user-stopped) is filtered out, so a finished run is never
offered back up as resumable.

## Caps

Fixed in v1, not user-configurable, and never persisted across separate
invocations — every fresh `run_id` starts both counters at zero regardless
of how many prior runs shipped tickets against the same repo.
