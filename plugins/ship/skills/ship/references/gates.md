# Gate Discovery

A **gate** is any project-defined check that must pass before code is committed:
linters, formatters, type checkers, unit tests, build steps, and pre-commit
hooks. Discover gates from the project itself — never assume a fixed command.

## Discovery order

The project's `CLAUDE.md` / `AGENTS.md` is the authoritative gate definition —
if it names the commands to run before commit, run exactly those and skip the
rest of this list. Use the auto-discovery below **only where those files are
silent**.

Probe in this order and run the first matching mechanism found. If several
coexist (e.g. a Makefile *and* a pre-commit config), prefer the one the
project's own docs/CI invoke; when unclear, ask the user which to run.

1. **Pre-commit framework** — `.pre-commit-config.yaml` present
   → `pre-commit run --all-files` (or `--from-ref/--to-ref` for staged only).
   Note: `git commit` may re-trigger these; running them first surfaces
   failures before message authoring.

2. **Task runner / Makefile** — look for conventional targets:
   - `Makefile` → `make lint`, `make test`, `make check`, `make ci`
   - `Justfile` → `just check` / `just test`
   Run only targets that exist (`make -n <target>` to probe).

3. **Ecosystem manifests** — match the project's language:

   | Manifest | Typical gates |
   |----------|---------------|
   | `package.json` | `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` (only scripts that exist in `scripts`) |
   | `pyproject.toml` / `setup.cfg` | `ruff check .`, `mypy .`, `pytest`, or `tox` |
   | `Cargo.toml` | `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test` |
   | `go.mod` | `gofmt -l .`, `go vet ./...`, `go test ./...` |
   | `pom.xml` / `build.gradle` | `mvn verify` / `./gradlew check` |

4. **CI as source of truth** — if unsure what "green" means, read the CI
   workflow (`.github/workflows/*.yml`, `.gitlab-ci.yml`) and mirror the
   commands it runs. CI is the authoritative gate definition.

## Scope: staged vs whole-tree

Prefer gating the **committed surface**. Run test/lint on changed files when the
tooling supports it; fall back to whole-tree when scoping is unavailable. Report
which scope was used so the result is not over-trusted.

## Failure policy

- **Any gate fails → abort the ship.** Report the failing command and its
  output verbatim. Do not commit, do not proceed to push.
- **No gate found →** state that plainly ("no project gates detected") and
  proceed. Silence reads as "gates passed" when they were never run.
- **Gate is ambiguous or slow →** ask the user whether to run it rather than
  guessing or skipping silently.
