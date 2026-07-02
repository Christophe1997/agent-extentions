# ship

Take a goal from working change to pushed branch on a git repository — as one
gated pipeline. Ship defers to your project's own conventions: it reads
`CLAUDE.md` / `AGENTS.md` as the source of truth for gates and commit style,
and respects any existing push policy.

## Features

- **Four gated phases, abort-on-failure** — apply → verify related tasks →
  commit → sync. A failure stops the pipeline cleanly instead of leaving a
  half-shipped state.
- **Branch-off-trunk safety** — never commits directly to `main`/`master`;
  creates a working branch first.
- **Convention-driven** — reads `CLAUDE.md` / `AGENTS.md` for the project's
  gates and commit style and follows them; never overrides what you defined.
- **Gate discovery fallback** — where conventions are silent, finds and runs
  your project's linters, type checks, tests, build, or pre-commit hooks.
- **Confirmed commits** — stages deliberately and gets human confirmation on
  the message before committing.
- **Best-effort remote sync** — pushes the branch, respecting any push policy
  (e.g. `yapermission`) already in place.

## Examples

```
/ship add a retry with backoff to the fetch client
/ship fix the off-by-one in pagination and cover it with a test
```

## Installation

Add this marketplace and install the plugin:

```
/plugin marketplace add Christophe1997/agent-extentions
/plugin install ship@agent-extentions
```

Define your project's gates and commit style in `CLAUDE.md` (or `AGENTS.md`) —
ship reads them and follows them.

## Usage

Invoke `/ship` with a goal. Ship will:

1. Apply the changes that meet the goal (following project conventions / TDD).
2. Surface any related tasks (TODOs, tickets, failing tests) and let you decide
   whether to resolve or defer them.
3. Commit — branching off trunk if needed, running project gates first.
4. Try to sync the current branch to the remote.

Any hard failure aborts the run and reports what completed and what remains.

## License

MIT
