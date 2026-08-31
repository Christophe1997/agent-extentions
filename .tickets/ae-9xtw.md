---
id: ae-9xtw
status: closed
deps: []
links: []
created: 2026-08-27T09:44:40Z
type: task
priority: 2
assignee: Christophe1997
external-ref: gh-3
---
# docs: add trunk_branch to run-state-schema.md's field table

ae-bw44 added a trunk_branch field to RunState (run_state.py) mirroring goal/ticket_mode, but run-state-schema.md's field table (the reference doc for the ledger's on-disk shape) was never updated to list it — discovered while implementing ae-05hv's docs pass over execution-loop.md/SKILL.md. Independent of ae-n0mo (version bump); no ordering constraint between them.

## Acceptance Criteria

- run-state-schema.md's field table gains a trunk_branch row alongside goal/ticket_mode's, describing its type (string or null), that it's set on the first ledger call of the run via --trunk-branch, and that it's null on a ledger that predates the field — mirroring the existing goal/ticket_mode row's phrasing exactly.
- No numbered section citations in the added text.


## Notes

**2026-08-27T09:47:13Z**

branch: goal/goalship-trunk-branch-override
claim_sha: 42c512f08a29dbdf6cfcff13258923d9bacfde2d

**2026-08-27T09:51:06Z**

branch: goal/goalship-trunk-branch-override
pr: https://github.com/Christophe1997/agent-extentions/pull/4
sha: f05323c6225589ee0049b0ea40b88bb3c4cdd9a9
