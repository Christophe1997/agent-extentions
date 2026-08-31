---
id: ae-05hv
status: closed
deps: [ae-ka07, ae-bw44]
links: []
created: 2026-08-27T09:11:32Z
type: task
priority: 1
assignee: Christophe1997
external-ref: gh-3
---
# docs: make trunk-branch determination an explicit, blocking-eligible step before the execution loop starts

execution-loop.md's 'Once per run: preflight' section currently only says (advisory prose) to report the resolved remote_url/trunk_branch before touching any ticket. Strengthen this into an explicit determination step that (a) surfaces the new override channel built in the preflight ticket, (b) states plainly that this determination happens strictly before Phase 2's per-cycle loop starts, where blocking on human confirmation is legal (Preconditions and decomposition already block on ambiguity) — and is never legal once a cycle is running, since the per-cycle loop's 'never blocked on user input' guarantee (SKILL.md, structurally asserted by tests/test_branching.py) must not be touched or contradicted, and (c) documents that the resolved value is now persisted on the ledger's trunk_branch field (the ledger-persistence ticket) so every later turn reads it back rather than re-deriving it from git. Also update SKILL.md's Preconditions/Phase 1 to reference the same override channel. No numbered section citations (no section-N, no 'step N', external or same-document) anywhere touched, per this repo's root CLAUDE.md — name sections instead.

## Acceptance Criteria

- execution-loop.md's "Once per run: preflight" section describes accepting an explicit trunk-branch override before Phase 2's cycles begin, states blocking on it is legal there and never inside a cycle, and explains the resolved value (override or auto-detected) is persisted on the ledger's trunk_branch field so a cold re-invocation or ScheduleWakeup wakeup reads it back instead of re-deriving it from git.
- SKILL.md's Preconditions/Phase 1 references the same override channel, so a human stating a trunk branch (or a repo's own CLAUDE.md/AGENTS.md naming its real integration branch) in the goal has a concrete place to land, not just prose the orchestrating session may or may not act on.
- Neither file uses a numbered section citation (no section-N, no "step N") anywhere in the new or edited text.


## Notes

**2026-08-27T09:32:18Z**

branch: goal/goalship-trunk-branch-override
claim_sha: c650ce5f92b4e6dbf27af3f765fd620475ccb781

**2026-08-27T09:44:40Z**

Discovered: ae-9xtw — run-state-schema.md's field table lacks a trunk_branch row

**2026-08-27T09:45:00Z**

branch: goal/goalship-trunk-branch-override
pr: https://github.com/Christophe1997/agent-extentions/pull/4
sha: 42c512f08a29dbdf6cfcff13258923d9bacfde2d
