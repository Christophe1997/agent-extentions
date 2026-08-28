---
id: ae-n0mo
status: closed
deps: [ae-05hv]
links: []
created: 2026-08-27T09:11:38Z
type: chore
priority: 2
assignee: Christophe1997
external-ref: gh-3
---
# chore: bump goalship plugin version for the trunk-branch override fix

plugins/goalship/.claude-plugin/plugin.json's version (currently 0.3.1) must be bumped once the trunk-branch override fix (preflight, ledger persistence, docs tickets) lands, per this repo's root CLAUDE.md validation checklist ('version field bumped in plugin.json/marketplace.json for changes'). Verified: the root .claude-plugin/marketplace.json entry for goalship carries no version field of its own (only name/source/homepage/description/category/keywords/tags) — only plugin.json needs bumping; do not invent a marketplace.json version field that does not exist.

## Acceptance Criteria

- plugins/goalship/.claude-plugin/plugin.json's version field is incremented from 0.3.1, consistent with this repo's existing version-bump convention (check prior goalship-touching commits' version deltas for patch vs. minor precedent before picking the next number).
- Test expectation: none -- version metadata change, no executable behavior to test.


## Notes

**2026-08-27T09:53:15Z**

branch: goal/goalship-trunk-branch-override
claim_sha: f05323c6225589ee0049b0ea40b88bb3c4cdd9a9

**2026-08-27T09:55:15Z**

branch: goal/goalship-trunk-branch-override
pr: https://github.com/Christophe1997/agent-extentions/pull/4
sha: f2d9bdee8706c6e93270d995225eb68c905f6b59
