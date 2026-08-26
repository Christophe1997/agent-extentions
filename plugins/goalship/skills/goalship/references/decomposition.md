# Decomposition

Turns a stated goal into a `tk` ticket graph (tickets plus `tk dep` edges).
This is prompt-authored judgment, not deterministic logic — no backing
script involvement.

## Classify size and ambiguity

A goal stays **lightweight** — decompose inline — when all three hold:

- One well-defined outcome (not several independent workstreams bundled
  together).
- No unresolved product ambiguity (the goal doesn't require a decision only
  a human or a planning pass can make).
- It decomposes into roughly five or fewer tickets.

A goal **escalates** to `ce-plan`/`ce-brainstorm` when it implies multiple
independent workstreams, unclear product scope, or a ticket count that would
clearly exceed five. This mirrors `ce-work`'s own Trivial/Small/Large routing
shape — not its exact thresholds, which are tuned for a different decision
(execution strategy, not decomposition size).

When genuinely unsure which side a goal falls on, prefer escalation — an
inline decomposition of an actually-large goal produces an under-specified
ticket graph the execution loop will fail on ticket-by-ticket; an escalation
of an actually-small goal costs one extra planning pass.

## Inline path

For a lightweight goal, decompose in a single reasoning pass:

1. Break the goal into its natural pieces — usually implementation order,
   sometimes independent slices — and the real ordering constraints between
   them: a piece that genuinely can't start before another finishes. Don't
   invent dependencies between pieces that could ship in either order; an
   over-constrained graph serializes work the execution loop could
   otherwise run through faster.
2. `tk create "<title>" -t <type> --acceptance "<criteria>"` for each piece.
   `<type>` is one of `bug|feature|task|epic|chore`. Add `-p 1` for a piece
   that blocks at least one other planned piece (per step 1) — it should be
   picked ahead of unrelated ready work once unblocked — and leave the rest
   at the default (`2`, omit `-p`). This is what makes the execution loop's
   "pick the highest-priority ready ticket" step (`execution-loop.md`)
   mean something beyond a tie: dependencies alone only say what must
   precede what, not which of several simultaneously-ready tickets to run
   first.
3. `tk dep <id> <dep-id>` for every ordering constraint identified in
   step 1.
4. Do not invoke `ce-plan` or `ce-brainstorm` for this path — that's
   what makes it "inline."

This path always runs in **commit mode** — one shared branch and PR for
the whole run (see `execution-loop.md`'s Shipping mode). Ticket dependency
ordering (step 1 and step 3's `tk dep` edges) is what the execution loop
turns into commit ancestry; there is no separate branch-per-ticket
decision to make here.

## Escalation path

For a large or ambiguous goal:

1. **Check availability first.** Look for `compound-engineering:ce-plan`
   in the skills available this session (the harness's skill listing, or a
   `Skill` tool invocation with `skill="ce-plan"` that fails to resolve). If
   absent, the target repo/session doesn't have `compound-engineering`
   installed — fall back to the inline path even for a large goal, and note
   the degradation explicitly in the eventual run summary. Do
   not silently produce a worse-than-inline decomposition without saying so.
2. **Invoke `ce-plan`** (via the `Skill` tool) with the goal. It may invoke
   `ce-brainstorm` itself for genuinely ambiguous goals, and either may block
   on their own clarifying questions — that's expected and does not violate
   the "never blocked" guarantee, which scopes to the execution
   loop that begins only after decomposition completes.
3. **Translate Implementation Units to tickets.** One Unit maps to
   one ticket by default:
   - `tk create "<Unit title>" -t <type> --acceptance "<criteria>" --external-ref <U-ID> --description "<compressed approach/context>"`
     — `--external-ref` carries the Unit's ID from the plan document for
     traceability back to it. `--description` carries a compressed version
     of the Unit's own approach and rationale, not its full text — the plan
     document isn't guaranteed to still be open by the time this ticket
     reaches implementation, and the sub-agent that implements it
     (`execution-loop.md`) only reads the ticket itself (`tk show`), never
     the plan document, so context that matters must be distilled into the
     ticket rather than left reachable only through the Unit ID.
   - Add `-p 1` for a Unit that blocks at least one other planned Unit, the
     default (`2`, omit `-p`) otherwise — same rule as the inline path.
   - Split a Unit into multiple tickets only when its own file list spans
     clearly independent concerns — not merely because it's large.
   - Carry the plan's own Unit dependency ordering into `tk dep` edges
     one-to-one.
   - Carry the Unit's Test Scenarios into `<criteria>` using the bulleted
     mechanics in Acceptance criteria below. Where the Unit already
     declares `Test expectation: none -- <reason>`, carry that marker
     forward as-is rather than inventing scenarios the Unit itself said
     don't apply — pull the ticket's other bullets from the Unit's own
     Verification field instead, since a no-test-scenario Unit still has
     an outcome-based way to know it's done.

This path always runs in **branch mode** — one branch, one commit, one PR
per ticket, stacked per the plan's own dependency ordering (see
`execution-loop.md`'s Shipping mode). A goal large or ambiguous enough to
escalate is large enough that a Unit's failure shouldn't block every other
Unit's PR from being independently reviewable, which a single shared
branch would force.

## Acceptance criteria

A ticket's acceptance criteria is a list, not a paragraph — one bullet per
independently-checkable behavior. A ticket with only one behavior is still
a list, just of length one; don't pad it, and don't merge two behaviors
into one bullet because the ticket is small.

Not every ticket has a behavior to test. A pure config, scaffolding,
dependency-bump, or formatting change has no observable behavior a test
scenario could name — judge this by whether the change alters what the
system does, not by the ticket's `-t` type alone (most `chore` tickets
qualify; an occasional mislabeled `feature` might not). For those, the
sole bullet is `Test expectation: none -- <reason>` — the same convention
`compound-engineering`'s `ce-plan` uses for a non-feature-bearing
Implementation Unit, adopted unchanged so a marker already carried by a
Unit round-trips onto its ticket without reinterpretation. Don't
manufacture a scenario just to satisfy the rule below.

Every other bullet must be:

- **Definable** — a competent reader can judge pass/fail without asking a
  follow-up question; not a restatement of the title or the ticket's own
  goal.
- **Testable** — names a specific input, action, and expected outcome
  ("the login form rejects an empty password field with a visible error",
  not "add validation").
- **Measurable** — where the behavior has a threshold, name it: the exact
  status code, count, timeout, string, or file/case — not a qualitative
  stand-in ("returns 429 after 5 failed attempts within 60s from the same
  IP", not "rate-limits repeated failures").

For a ticket with real behavior, consider each of the following and
include a bullet from every one that applies — right-sized to the
ticket's complexity and risk, not padded or skimped (a one-line config
toggle needs one bullet; a payment flow needs several):

- **Happy path** — core functionality with expected inputs and outputs.
- **Edge cases** (when the behavior has meaningful boundaries) — boundary
  values, empty input, nil/null state, concurrent access.
- **Error and failure paths** (when the behavior has failure modes) —
  invalid input, downstream failure, timeout, permission denial.
- **Integration** (when the behavior crosses layers) — an effect mocks
  alone wouldn't prove, e.g. "creating X triggers callback Y which
  persists Z."

Don't restate what the target repo's gate suite already checks for every
ticket regardless of content — build succeeds, lint is clean, the existing
suite still passes. A bullet earns its place only if it's specific to this
ticket's behavior.

- **Where the target repo's gate suite includes a test runner** (see
  `gate-discovery.md`'s ecosystem-manifest table — `pytest`/`npm test`/
  `cargo test`/`go test`/etc. present): phrase bullets in test-case terms —
  name the test file/case where one clearly maps.
- **Where no test gate exists**: bullets stay a checklist the implementer
  verifies manually as part of gate-passing — same bar, just without an
  automated check behind it.

`tk create --acceptance` takes the whole list as **one** flag holding a
multi-line string, one `- ` bullet per line — `tk` renders it verbatim
under the ticket's Acceptance Criteria section. Never pass `--acceptance`
more than once to add items: `tk create` keeps only the last occurrence
and silently drops the rest — no error, no warning, and this differs from
the accumulate-on-repeat pattern common in other CLIs. Build the full list
as one flag instead:

```
tk create "<title>" -t <type> --acceptance $'- <criterion 1>\n- <criterion 2>\n- <criterion 3>'
```

This binding is what makes a ticket's acceptance criteria mechanically
verifiable rather than only descriptive — the execution loop
(`execution-loop.md`) treats a ticket's gate run as the arbiter of "done,"
and a vague or merged-together bullet gives that gate run nothing concrete
to check.
