---
name: yap-remember
description: Cache an approved `[[ask]]` decision for the rest of the current session — scoped to the command segment that triggered the rule, or to a word prefix the human approves (e.g. `git push origin --delete`) — so it stops re-prompting. Trigger only after the human has explicitly said yes to an offer to remember a yapermission decision — never on your own initiative, never on an assumption that they would want it.
allowed-tools: Bash
---

# Remember a yapermission decision

Persist one approved `[[ask]]` decision into the session cache so it silently resolves to `allow` for the rest of this session, without touching what any `[[deny]]` rule can still block.

## Confirm-first — never silent

This skill exists to enforce one rule: **the caching surface only ever expands after an explicit human "yes."** Never invoke `remember` speculatively, by default, or because a rule merely *could* be cached.

Only proceed when both are true:

1. A tool call was just blocked by an `[[ask]]` decision whose `additionalContext` said the matched rule is cacheable (it names a `session_id`).
2. An explicit offer was made to remember this decision for the rest of the session, and the human explicitly said yes **to a specific scope** — a real affirmative reply, not silence, not a guess, not "they'll probably want this every time."

If either is missing, do not invoke this skill. If the human says no, or doesn't answer, drop it — the tool call proceeds (or not) on its own merits and nothing gets cached.

## Choosing the scope to offer

The engine never remembers a whole `a && b | c` chain — only the segment that triggered the rule, which the cue names ("The part of the command that triggered it: `…`"). Whatever else was chained on is judged on its own next time. Agents rarely repeat that segment verbatim (branch names, refs, and paths change), so offer two scopes:

| Scope | Covers | Offer it as |
|---|---|---|
| exact (default) | That segment's exact words | "just `git push origin --delete feat/x`" |
| prefix | Any segment starting with those words | "any `git push origin --delete …`" |

To propose the prefix, take the gating segment and drop the trailing arguments that will vary — the branch, ref, tag, path, or package name — and nothing more. Keep it as narrow as still useful: `git push origin --delete`, not `git push`. Say plainly what the prefix *also* allows (`git push origin --delete` also covers `--delete main`), so the "yes" is informed. If the cue names no gating segment, only the exact call can be remembered — don't offer a prefix.

## Process

1. **Recover the session_id and token from the triggering call's `additionalContext` cue** — never from a guessed value or an environment variable. The cue looks like:

   > yapermission: rule 'git-push' is cacheable. The human has not yet been asked whether to remember this approval for the rest of the session. If they agree, the yapermission:yap-remember skill can record it with session_id=abc123 and token=eyJz...a1b2c3. The part of the command that triggered it: `git push origin --delete feat/x`.

   The token proves this exact call actually reached a genuine `ask` decision — it is not optional, and it cannot be reused for a different call, directory, or session.

2. **Re-use the exact `tool_name` and `tool_input`** from the call that triggered the cue — not a paraphrase or a re-typed approximation. The token only verifies against the exact fields it was minted for; the engine derives the segment from them itself.

3. **Shell out to the engine's `remember` subcommand** — add `--prefix` only when the human approved the prefix scope, with exactly the words they approved:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yapermission.py remember <session_id> <tool_name> '<tool_input_json>' <token> [--prefix '<approved words>']
   ```

4. **Report the result back to the human**:
   - Exit code `0`: relay the `remembered: rule '<name>' cached for session <id> (<scope>)` line — it states exactly what stops prompting.
   - Non-zero exit code: relay the refusal reason from stderr verbatim (e.g. the rule lost its `cacheable` flag, the prefix doesn't trigger the rule on its own, the segment also matches another rule, or the token is invalid/expired/mismatched). Do not retry silently or with a broader prefix — a refusal deserves the human's attention, not a second silent attempt.

## Example Usage

```
Agent: `git push origin --delete feat/x` matches the cacheable 'git-push' rule.
       Want me to remember that for this session — just this exact delete, or
       any `git push origin --delete …` (which would also cover deleting main)?
Human: any delete is fine
Agent: [invokes yap-remember with --prefix 'git push origin --delete']
       Remembered — `git push origin --delete …` won't prompt again this session.
```

## Common follow-ups

- If the human says "always" or "forever," clarify that this only covers the current session — editing the TOML rule itself (e.g. to `[[allow]]`) is the durable option, and that's outside this skill's scope.
- If `remember` refuses because the rule isn't cacheable, tell the human they'd need to add `cacheable = true` to that `[[ask]]` rule first — see `/yapermission:yap-rule-syntax`.
- A remembered segment never vouches for anything chained onto it, nor for a segment that also matches a `[[deny]]` or another `[[ask]]` rule (adding `--force` still asks). Scope details: `/yapermission:yap-rule-syntax`.
