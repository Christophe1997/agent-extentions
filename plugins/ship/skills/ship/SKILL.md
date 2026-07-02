---
name: ship
description: This skill should be used when the user asks to "ship this", "ship the change", "ship a goal", "/ship", or wants a goal taken end-to-end on a git repo — apply changes, check related tasks, commit, and push. Orchestrates apply → verify related tasks → commit (branch-off-trunk + gates) → sync to remote, aborting if any phase fails.
argument-hint: a goal or question (e.g. "add retry to the fetch client")
allowed-tools: [Bash, Read, Grep, Glob, Edit, Write, AskUserQuestion, Skill]
---

Take a stated goal from working change to pushed branch on a git repository,
gating each phase so a failure stops the pipeline cleanly instead of leaving a
half-shipped state.

## Preconditions

Confirm before doing anything else. If any fails, report and stop.

- Inside a git work tree: `git rev-parse --is-inside-work-tree`.
- The invocation argument (`$ARGUMENTS`) holds a concrete goal or question. If
  empty or too vague to act on, ask the user to state the goal — do not invent
  one.

## Execution model

Run the four phases **in order**. Treat each phase as a gate: on hard failure,
stop immediately, report which phases completed and what remains, and do **not**
enter the next phase. Never paper over a failure to keep the pipeline moving.

**Load project conventions first.** Before Phase 3, read the project's
`CLAUDE.md` (and `AGENTS.md` if present) — these are the authoritative source
for the project's **gates** and **commit style**. Ship follows what they define
and must not override or contradict them. Fall back to auto-discovery only where
they are silent.

---

## Phase 1 — Apply changes

Implement the goal following the project's existing conventions (style, test
approach, structure). This phase is thin delegation to normal implementation
work, not a re-invention of it:

- If the repository practices TDD or the user asks for it, work test-first.
- If the goal is actually a question (not an instruction), answer it and stop —
  there is nothing to ship. Confirm with the user before treating a question as
  a change request.

**Gate:** the change is complete and the working tree reflects the goal.
If the goal cannot be met (blocked, ambiguous mid-way, missing dependency),
stop here and report — do not commit a partial change silently.

## Phase 2 — Verify related tasks

After the change exists, scan the touched surface for related open work that the
change implies or exposes:

- `TODO` / `FIXME` / `XXX` markers introduced by, or adjacent to, the diff
  (`git diff` then `grep` the changed files).
- Issue / ticket IDs referenced in the goal or in changed code.
- Tests now failing or newly relevant to the change.
- Sub-items of the goal left unaddressed.

If related tasks exist, **notify the user and let them decide** via
AskUserQuestion — resolve now, or defer. Deferring is a valid choice and does
**not** abort the ship. Only stop if the user chooses to stop, or if a
discovered task reveals the current change is unsafe to ship.

If none are found, say so and continue.

## Phase 3 — Commit per project convention

1. **Determine the trunk and current branch:**
   ```bash
   git branch --show-current
   git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null   # trunk hint
   ```
   Treat `main` / `master` (or the resolved `origin/HEAD`) as trunk.

2. **Branch off trunk when needed.** If the current branch **is** trunk, create
   and switch to a new working branch before committing. Name it `<type>/<slug>`
   where `<type>` is the Conventional Commits type of the change (`feat`, `fix`,
   `docs`, `refactor`, …) and `<slug>` is the goal lowercased with every run of
   non-alphanumeric characters collapsed to a single `-`, trimmed to ~50 chars.

   Guard against name collisions before creating the branch — if the name
   already exists (locally or on the remote), append `-2`, `-3`, … until it is
   free, so `git checkout -b` cannot abort the ship:
   ```bash
   name="<type>/<slug>"; n=1; branch="$name"
   while git show-ref --quiet "refs/heads/$branch" \
      || git show-ref --quiet "refs/remotes/origin/$branch"; do
     n=$((n+1)); branch="$name-$n"
   done
   git checkout -b "$branch"
   ```

   If already on a non-trunk branch, commit there — do not create another.

3. **Run gates before committing.** Use the gates the project's `CLAUDE.md` /
   `AGENTS.md` defines. Only where they are silent, fall back to auto-discovery
   per `references/gates.md` (linters, type checks, tests, build, pre-commit).
   **Any gate failure aborts the ship** — report the failing command output and
   stop. If no gate is defined or discovered, state that and proceed.

4. **Create the commit** following the project's commit style as written in
   `CLAUDE.md` / `AGENTS.md` (message format, scope, footers/trailers, and
   any AI-attribution rule). Do not impose a style the project has not asked
   for. Where the project is silent, fall back to a single Conventional Commits
   message. Always stage deliberately and get human confirmation on the message
   before running `git commit`.

   If the project's conventions name a specific skill for committing or gating
   (e.g. `agd:commit`), prefer it: invoke it via the `Skill` tool and skip the
   manual staging/commit steps above rather than reimplementing them —
   following the convention beats duplicating it.

**Gate:** a commit exists on a non-trunk branch and all gates passed.

## Phase 4 — Sync to remote

Best-effort push of the current branch:

- If no remote is configured, report that and stop gracefully — this is not a
  failure to abort on, there is simply nowhere to sync.
- Push, setting upstream on first push:
  ```bash
  git push -u origin "$(git branch --show-current)"
  ```
- Respect any push policy already in place (e.g. a `yapermission` rule may
  gate pushes). If the push is denied or fails, report the exact error and the
  fact that everything up to the commit succeeded — do not retry blindly or
  force-push.

## Final report

Summarize what shipped: branch name, commit subject, gate results, deferred
tasks (from Phase 2), and remote sync status. Be explicit about anything
skipped or deferred so the outcome is not over-trusted.

## Additional resources

- **`references/gates.md`** — how to discover and run project gates per
  ecosystem, and the failure/scope policy.
