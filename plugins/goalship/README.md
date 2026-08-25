# goalship

Hand a goal to this plugin and get merge-ready pull requests back, without babysitting each individual change. The goal is decomposed into a tracked, dependency-ordered `tk` ticket graph and driven to completion unattended: each ready ticket is implemented, gated against the target repo's own checks, branched, committed, pushed, and opened as a pull request.

## Features

### Skills
- **goalship** - Decomposes a goal into a `tk` ticket graph (inline for small goals, or via `ce-plan`/`ce-brainstorm` escalation for large ones), then runs a self-pacing loop that implements, gates, and ships each ready ticket as its own pull request until the graph is exhausted, deadlocked, a run cap is hit, or the user stops it.

## Installation

### Requirements
- [`tk`](https://github.com/wedow/ticket) (ticket) installed and on `PATH`
- A git repository with a configured remote
- `gh` or `glab`, reachable and authenticated, when pull request creation will run
- Python 3, for the plugin's backing script

```bash
/plugin install goalship@agent-extentions
```

## Usage

Invoke the skill with a goal:

```
/goalship add input validation to the login form
```

The skill classifies the goal, builds a ticket graph, and self-paces through implementation under the harness's `/loop` mechanism. It never merges, approves, force-pushes, or publishes — only opens pull requests for human review. Stop a run between tickets with the `/loop` wrapper's own interrupt mechanism.

## License

MIT
