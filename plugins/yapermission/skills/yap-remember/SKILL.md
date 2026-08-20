---
name: yap-remember
description: Cache an approved `[[ask]]` decision for the rest of the current session so the same rule matching the same exact tool call stops re-prompting. Trigger only after the human has explicitly said yes to an offer to remember a yapermission decision — never on your own initiative, never on an assumption that they would want it.
allowed-tools: Bash
---

# Remember a yapermission decision

Persist one approved `[[ask]]` decision into the session cache so it silently resolves to `allow` for the rest of this session, without touching what any `[[deny]]` rule can still block.

## Confirm-first — never silent

This skill exists to enforce one rule: **the caching surface only ever expands after an explicit human "yes."** Never invoke `remember` speculatively, by default, or because a rule merely *could* be cached.

Only proceed when both are true:

1. A tool call was just blocked by an `[[ask]]` decision whose `additionalContext` said the matched rule is cacheable (it names a `session_id`).
2. An explicit offer was made to remember this decision for the rest of the session, and the human explicitly said yes — a real affirmative reply, not silence, not a guess, not "they'll probably want this every time."

If either is missing, do not invoke this skill. If the human says no, or doesn't answer, drop it — the tool call proceeds (or not) on its own merits and nothing gets cached.

## Process

1. **Recover the session_id and token from the triggering call's `additionalContext` cue** — never from a guessed value or an environment variable. The cue looks like:

   > If this call proceeds to execute, the matched rule is cacheable: you may offer to remember this exact call for the rest of this session. If the human explicitly says yes, invoke remember with session_id=abc123 and token=eyJz...a1b2c3.

   The token proves this exact call actually reached a genuine `ask` decision — it is not optional, and it cannot be reused for a different call, directory, or session.

2. **Re-use the exact `tool_name` and `tool_input`** from the call that triggered the cue — not a paraphrase or a re-typed approximation. The cache key is an exact match on the call; a slightly different `tool_input` will simply never hit. This also matters for the token: it only verifies against the exact fields it was minted for.

3. **Shell out to the engine's `remember` subcommand** (4 positional arguments — `session_id`, `tool_name`, `tool_input` JSON, `token`; there is no `rule_name` argument, the engine re-derives the matched rule itself via a live re-evaluation):

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yapermission.py remember <session_id> <tool_name> '<tool_input_json>' <token>
   ```

4. **Report the result back to the human**:
   - Exit code `0`: relay the `remembered: rule '<name>' cached for session <id>` line — the human now knows this exact call won't prompt again this session.
   - Non-zero exit code: relay the refusal reason from stderr verbatim (e.g. the rule lost its `cacheable` flag, resolves to something other than `ask` now, the config failed to load, or the token is invalid/expired/mismatched). Do not retry silently — a refusal here means something changed since the cue was issued, and it deserves the human's attention, not a second silent attempt.

## Example Usage

```
Agent: This deploy command matches a cacheable rule — want me to remember your
       approval so it stops asking for the rest of this session?
Human: yes
Agent: [invokes yap-remember]
       Remembered — 'deploy' won't prompt again this session for that exact command.
```

## Common follow-ups

- If the human says "always" or "forever," clarify that this only covers the current session — editing the TOML rule itself (e.g. to `[[allow]]`) is the durable option, and that's outside this skill's scope.
- If `remember` refuses because the rule isn't cacheable, tell the human they'd need to add `cacheable = true` to that `[[ask]]` rule first — see `/yapermission:yap-rule-syntax`.
- A cached entry only ever matches the *exact* `tool_name` + `tool_input` it was recorded against — a slightly different command still asks.
