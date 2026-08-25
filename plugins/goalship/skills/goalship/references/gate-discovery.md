# Gate Discovery

A **gate** is any project-defined check that must pass before a ticket's
implementation is committed: linters, formatters, type checkers, unit tests,
build steps, pre-commit hooks. Discover gates from the target repo itself —
never assume a fixed command.

This restates the same policy, sourced from the `ship` plugin's own
gate-discovery policy (`git show a9e42ea~1:plugins/ship/skills/ship/references/gates.md`,
before `ship` was removed from this repo) — there is no live cross-plugin
reference to point to instead, so the algorithm lives here as goalship's own
copy. One change from `ship`'s original: `ship` asked the user when a gate
was ambiguous. goalship's execution loop is unattended once it starts;
an ambiguous case below always resolves to a documented default instead of a
question.

## Discovery order

The target repo's `CLAUDE.md` / `AGENTS.md` is the authoritative gate
definition — if it names the commands to run before commit, run exactly
those and skip the rest of this list. Use auto-discovery below **only**
where those files are silent on gates.

Probe in this order and run the first matching mechanism found:

1. **Pre-commit framework** — `.pre-commit-config.yaml` present
   → `pre-commit run --all-files`.

2. **Task runner / Makefile** — conventional targets:
   - `Makefile` → `make lint`, `make test`, `make check`, `make ci`
   - `Justfile` → `just check` / `just test`

   Run only targets that exist (`make -n <target>` to probe before running).

3. **Ecosystem manifests** — match the target repo's language:

   | Manifest | Typical gates |
   |----------|---------------|
   | `package.json` | `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` (only scripts present in `scripts`) |
   | `pyproject.toml` / `setup.cfg` | `ruff check .`, `mypy .`, `pytest`, or `tox` |
   | `Cargo.toml` | `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test` |
   | `go.mod` | `gofmt -l .`, `go vet ./...`, `go test ./...` |
   | `pom.xml` / `build.gradle` | `mvn verify` / `./gradlew check` |

4. **CI as source of truth** — if still unsure what "green" means, read the
   CI workflow (`.github/workflows/*.yml`, `.gitlab-ci.yml`) and mirror the
   commands it runs. CI is the authoritative gate definition when reached.

**When multiple mechanisms coexist** (e.g. a Makefile *and* a pre-commit
config), prefer whichever the target repo's own docs or CI actually invoke.
When that's still unclear, run every mechanism found rather than guessing
which one to skip — over-gating a ticket is safe; under-gating it isn't.

## Scope: staged vs whole-tree

Prefer gating the ticket's own committed surface — run lint/test on the
changed files when the tooling supports scoping; fall back to whole-tree
when it doesn't. Note which scope was used in the ticket's failure note (if
any) so the result isn't over-trusted later.

## Failure policy

- **Any gate fails → no commit.** Record the failing command and a redacted,
  length-capped output excerpt as the ticket's failure note (common
  secret-shaped patterns like `KEY=value` env assignments and bearer-token
  strings are stripped before the note is written), leave the ticket open,
  and move to the next ready ticket. Do not retry the same ticket again this
  run — see `execution-loop.md`.
- **No gate found** → state that plainly ("no project gates detected for
  `<repo>`") and treat it as a pass — the ticket proceeds to commit. Silence
  would read as "gates ran and passed" when they never ran at all.
