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
   sometimes independent slices.
2. `tk create "<title>" -t <type> --acceptance "<criteria>"` for each piece.
   `<type>` is one of `bug|feature|task|epic|chore`.
3. `tk dep <id> <dep-id>` for every real ordering constraint — a ticket that
   genuinely can't start before another finishes. Don't invent dependencies
   between tickets that could ship in either order; an over-constrained
   graph serializes work the execution loop could otherwise run through
   faster.
4. Do not invoke `ce-plan` or `ce-brainstorm` for this path — that's
   what makes it "inline."

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
   - `tk create "<Unit title>" -t <type> --acceptance "<criteria>" --external-ref <U-ID>`
     — the `--external-ref` carries the Unit's ID from the plan document for
     traceability back to it.
   - Split a Unit into multiple tickets only when its own file list spans
     clearly independent concerns — not merely because it's large.
   - Carry the plan's own Unit dependency ordering into `tk dep` edges
     one-to-one.

## Acceptance criteria

Every created ticket's acceptance criteria must be specific enough for a
later, context-free pass to implement and verify it — not a restatement of
the title.

- **Where the target repo's gate suite includes a test runner** (see
  `gate-discovery.md`'s ecosystem-manifest table — `pytest`/`npm test`/
  `cargo test`/`go test`/etc. present): author the criteria as a specific
  failing test or enumerated test scenario the implementation must make
  pass. `tk create --acceptance "..."` — name the test file/case where one
  clearly maps, or the scenario in test-case terms otherwise.
- **Where no test gate exists**: criteria remain a checklist the implementer
  verifies manually as part of gate-passing (still specific — "the login
  form rejects an empty password field with a visible error", not "add
  validation").

This binding is what makes a ticket's acceptance criteria mechanically
verifiable rather than only descriptive — the execution loop (`execution-loop.md`) treats a
ticket's gate run as the arbiter of "done," and a vague acceptance criterion
gives that gate run nothing concrete to check.
