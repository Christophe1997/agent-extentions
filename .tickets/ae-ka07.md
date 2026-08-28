---
id: ae-ka07
status: closed
deps: []
links: []
created: 2026-08-27T09:11:14Z
type: bug
priority: 1
assignee: Christophe1997
external-ref: gh-3
---
# preflight: accept an explicit trunk-branch override, bypassing autodetection

Root cause of issue #3: _resolve_trunk_branch() in plugins/goalship/scripts/preflight.py always trusts origin/HEAD (else local main/master, else current branch) with no way for a repo whose real dev-integration branch has diverged from that host default to override it. Add an optional trunk-branch override to run_preflight()/cmd_preflight that bypasses _resolve_trunk_branch() entirely when supplied, validated against refs/heads/<b> OR refs/remotes/origin/<b>. No heuristic auto-detection (divergence scanning, develop/release guessing) — git cannot know which branch is meant to be trunk; this is an explicit channel only.

## Acceptance Criteria

- run_preflight() accepts an optional trunk-branch override; given a branch that exists as refs/heads/<b> or refs/remotes/origin/<b>, PreflightResult.trunk_branch equals that branch exactly and _resolve_trunk_branch() is never invoked (test in tests/test_preflight.py: build a repo where origin/HEAD resolves to main, pass an override naming a second diverged local branch, assert trunk_branch is the override, not main).
- Given an override naming a branch absent from both refs/heads/ and refs/remotes/origin/, run_preflight() returns ok=False with a failure string naming the missing branch.
- Given an override that exists only as refs/remotes/origin/<b> (no local ref — e.g. a fresh clone), it is still accepted, not just refs/heads/<b>.
- With no override supplied, trunk_branch resolution is unchanged from current behavior — the existing test_reports_remote_url_and_trunk_branch_on_pass test still passes without modification.
- loop_runner.py's preflight CLI subcommand accepts the override as a new optional argument and forwards it to run_preflight(); its printed trunk_branch field reflects it (extend tests/test_cli.py's existing preflight coverage).
- tests/test_branching.py's safety-guardrail assertions against every scripts/*.py source still pass unmodified.


## Notes

**2026-08-27T09:13:30Z**

branch: goal/goalship-trunk-branch-override
claim_sha: 566242153b9921597c104517d4e52f195fdc7599

**2026-08-27T09:22:08Z**

branch: goal/goalship-trunk-branch-override
pr: https://github.com/Christophe1997/agent-extentions/pull/4
sha: 2e49a5f2a7dc253da44a4f14a9604a41cbcad29d
