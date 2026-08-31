---
id: ae-bw44
status: closed
deps: [ae-ka07]
links: []
created: 2026-08-27T09:11:22Z
type: feature
priority: 1
assignee: Christophe1997
external-ref: gh-3
---
# goalship: persist the run's resolved trunk_branch on the ledger

Companion to the preflight override ticket: trunk_branch currently has no persistence on RunState (unlike goal/ticket_mode, which already survive a resumed turn per execution-loop.md's Self-pacing model section). Without this, an override supplied at run start is silently lost on a cold re-invocation or ScheduleWakeup wakeup, since neither inherits the prior turn's in-context memory, and the exact bug from issue #3 could recur mid-run. Add a trunk_branch field to RunState (run_state.py) and a --trunk-branch flag to loop_runner.py's ledger CLI subcommand, mirroring the existing --goal/--ticket-mode pattern exactly (see cmd_ledger in loop_runner.py).

## Acceptance Criteria

- RunState gains a trunk_branch: Optional[str] = None field that round-trips through to_dict()/from_dict() the same way goal/ticket_mode already do (test in tests/test_run_state.py: round-trip a RunState with trunk_branch set through save_run_state/load_run_state and confirm it survives).
- loop_runner.py's ledger CLI subcommand accepts a --trunk-branch VALUE flag; when given, it is written onto the run state before printing and appears under trunk_branch in the printed JSON; when omitted on a later call for the same --run-id, the previously persisted value is preserved untouched — mirrors --goal's carry-forward behavior exactly (test in tests/test_cli.py, mirroring existing goal/ticket_mode CLI coverage).
- The ledger usage/help text (USAGE in loop_runner.py and cmd_ledger's own no-args error message) documents the new --trunk-branch flag alongside --goal/--ticket-mode.


## Notes

**2026-08-27T09:24:53Z**

branch: goal/goalship-trunk-branch-override
claim_sha: 2e49a5f2a7dc253da44a4f14a9604a41cbcad29d

**2026-08-27T09:29:47Z**

branch: goal/goalship-trunk-branch-override
pr: https://github.com/Christophe1997/agent-extentions/pull/4
sha: c650ce5f92b4e6dbf27af3f765fd620475ccb781
