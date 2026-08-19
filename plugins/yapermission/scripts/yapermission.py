#!/usr/bin/env python3
"""yapermission — PreToolUse policy engine for Claude Code.

Two entry points:
    python3 yapermission.py hook                  # run as PreToolUse hook (stdin/stdout JSON)
    python3 yapermission.py explain <tool> <json> # dry-run a tool call against the active config
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

GLOBAL_CONFIG = Path.home() / ".yapermission.toml"
PROJECT_CONFIG_NAME = ".yapermission.toml"
LOG_PATH = Path.home() / ".yapermission.log"
# Ephemeral by design (KTD3): lives in the OS temp dir, not ~/, so the OS's
# own temp-file lifecycle is the cleanup this feature deliberately skips.
CACHE_PATH = Path(tempfile.gettempdir()) / "yapermission-cache.jsonl"


@dataclass
class Decision:
    # Mirrors Claude Code's PreToolUse `permissionDecision` field exactly:
    # "allow" skips the prompt, "deny" blocks the call, "ask" prompts the user,
    # "defer" hands the decision to a later hook in the chain.
    permission: str  # "allow" | "deny" | "ask" | "defer"
    rule_name: Optional[str] = None
    reason: Optional[str] = None
    trace: list[str] = field(default_factory=list)
    # Agent-facing only (never mirrored into `reason`, which is human-facing);
    # set when a cacheable `ask` rule matches with no cache hit yet.
    additional_context: Optional[str] = None
    # "cache" when this decision was resolved from a session cache hit rather
    # than direct rule evaluation — feeds the audit log's `source` field (R8).
    source: Optional[str] = None


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def active_config_path(cwd: str) -> Optional[Path]:
    """Project config wins; otherwise global; otherwise None."""
    project = Path(cwd) / PROJECT_CONFIG_NAME
    if project.is_file():
        return project
    if GLOBAL_CONFIG.is_file():
        return GLOBAL_CONFIG
    return None


def load_config(path: Path) -> dict:
    # tomllib (stdlib in Python 3.11+) requires binary mode.
    with path.open("rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Rule matching engine
# ---------------------------------------------------------------------------

def _match_tool(pattern: Optional[str], tool_name: str) -> bool:
    if not pattern:
        return True
    return re.search(pattern, tool_name) is not None


def rule_matches(rule: dict, tool_name: str, tool_input: dict) -> bool:
    """Return True if `rule` applies to this tool call.

    Semantics:
        1. `rule['tool']` (regex) must match `tool_name`. Missing tool = match any.
        2. `rule['matches']` is a list of "match entries". The rule fires if ANY
           entry matches (OR across entries).
        3. Within a single entry, EVERY field's regex must match the corresponding
           field in `tool_input` (AND across fields). An empty entry `{}` matches
           any input.
        4. Missing `matches` (or empty list) means "no input constraints" — the
           rule fires as long as the tool matches.

    Args:
        rule: parsed TOML rule dict with keys `name`, `tool`, `matches`, `reason`.
        tool_name: e.g. "Bash", "Edit", "mcp__github__list_issues".
        tool_input: tool-specific input dict, e.g. {"command": "git status"}.

    Returns:
        True if the rule should fire for this call.
    """
    if not _match_tool(rule.get("tool"), tool_name):
        return False

    matches = rule.get("matches") or []
    if not matches:
        return True

    for match in matches:
        if all(
            re.search(str(pattern), str(tool_input.get(field, ""))) is not None
            for field, pattern in match.items()
        ):
            return True

    return False


# Rule groups in evaluation order. Each entry is (toml_key, permissionDecision).
# More restrictive intent comes first: an absolute block beats a "make me think"
# beats an "auto-approve" beats a "pass to next hook". Reordering this list
# changes the policy semantics — every group beats every group below it.
_RULE_GROUPS = (
    ("deny", "deny"),
    ("ask", "ask"),
    ("allow", "allow"),
    ("defer", "defer"),
)


_CACHEABLE_CUE_TEMPLATE = (
    "If this call proceeds to execute, the matched rule is cacheable: you may "
    "offer to remember this exact call for the rest of this session "
    "(session_id={session_id})."
)


def decide(
    config: dict,
    tool_name: str,
    tool_input: dict,
    cache: Optional[dict] = None,
    config_path: Any = None,
    session_id: Optional[str] = None,
) -> Decision:
    """Evaluate rule groups in `_RULE_GROUPS` order; return the resulting Decision.

    `cache` is a pre-loaded session cache dict (from `load_cache`), keeping
    this function I/O-free (KTD4): the cache-check only ever consults what
    the caller already loaded. Only a matched `[[ask]]` rule with
    `cacheable = true` is checked against it (KTD5) — the check runs against
    the matched rule itself, not as an independent branch before `ask`, so a
    rule edited to drop `cacheable`, tightened, or deleted never produces a
    stale hit even if an old cache entry still exists.
    """
    trace: list[str] = []

    for group_key, decision_value in _RULE_GROUPS:
        for rule in config.get(group_key) or []:
            name = rule.get("name", "<unnamed>")
            if not rule_matches(rule, tool_name, tool_input):
                trace.append(f"{group_key} rule '{name}' skipped")
                continue

            trace.append(f"{group_key} rule '{name}' matched")
            # Strict `is True`, not truthiness: this flag converts prompts
            # into silent allows, so a stray non-boolean TOML value (e.g. a
            # typo'd string) must not accidentally opt a rule in.
            cacheable = group_key == "ask" and rule.get("cacheable") is True

            if cacheable:
                key = cache_key(rule.get("name"), tool_name, tool_input, config_path)
                if cache and key in cache:
                    trace.append(f"cache hit for rule '{name}' — resolving to allow")
                    return Decision(
                        permission="allow",
                        rule_name=rule.get("name"),
                        trace=trace,
                        source="cache",
                    )

            reason = rule.get("reason")
            if decision_value == "deny" and not reason:
                reason = "Denied by yapermission policy"

            additional_context = None
            if cacheable and session_id:
                # No session_id, no cue: an empty id would render into the
                # cue text and, if echoed back to a `remember` call, write an
                # entry under "" that the empty-session_id guard in cmd_hook
                # then refuses to ever look up again — a dead write plus a
                # cue inviting it.
                additional_context = _CACHEABLE_CUE_TEMPLATE.format(
                    session_id=session_id
                )

            return Decision(
                permission=decision_value,
                rule_name=rule.get("name"),
                reason=reason,
                trace=trace,
                additional_context=additional_context,
            )

    default = (config.get("default") or "ask").lower()
    trace.append(f"no rule matched — default: {default}")
    return Decision(permission=_normalize_default(default), trace=trace)


# The four valid `default:` values, mirroring Claude Code's permissionDecision field.
_VALID_DEFAULTS = {"allow", "deny", "ask", "defer"}


def _normalize_default(value: str) -> str:
    """Validate the configured default; unknown values fall back to `ask` (fail-open)."""
    return value if value in _VALID_DEFAULTS else "ask"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_decision(record: dict) -> None:
    """Append one JSONL record to ~/.yapermission.log. Never raises.

    The log can contain raw tool inputs (Bash commands, Write payloads), so it
    is created with mode 0600 to keep it readable only by the owner.
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        existed = LOG_PATH.exists()
        fd = os.open(
            LOG_PATH,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o600,
        )
        with os.fdopen(fd, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        if not existed:
            os.chmod(LOG_PATH, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Session cache
#
# Backs the `[[ask]]` opt-in caching feature: a session-scoped, fail-open
# JSONL store keyed on the matched rule plus the exact tool call. See
# docs/plans/2026-08-19-1444-feat-yapermission-cacheable-ask-rules-plan.md
# (KTD2, KTD3, KTD7, KTD8) for the design rationale.
# ---------------------------------------------------------------------------

def cache_key(rule_name: Any, tool_name: Any, tool_input: Any, config_path: Any) -> str:
    """Canonical-JSON hash identifying one (rule, call, config) triple.

    Sorted-key JSON, not concatenation (KTD7): the key gates a silent
    `allow`, so an ambiguous encoding would be a bypass vector — a crafted
    `tool_input` could otherwise collide with a different rule's or tool's
    key.
    """
    payload = {
        "rule": rule_name,
        "tool": tool_name,
        "input": tool_input,
        "config": str(config_path),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def _open_cache_path(flags: int, mode: int = 0) -> Optional[int]:
    """Open CACHE_PATH with O_NOFOLLOW and verify the owning uid.

    Returns a live fd on success. Returns None — and closes any fd it
    opened — on a missing file, a symlinked path, an owner mismatch, or any
    other OSError (KTD8: CACHE_PATH is a fixed name in the world-writable
    OS temp dir, so both the read and write paths distrust a pre-existing
    file until its ownership is confirmed).
    """
    try:
        fd = os.open(CACHE_PATH, flags | os.O_NOFOLLOW, mode)
    except OSError:
        return None
    try:
        if os.fstat(fd).st_uid != os.getuid():
            os.close(fd)
            return None
    except OSError:
        os.close(fd)
        return None
    return fd


def load_cache(session_id: str) -> dict[str, dict]:
    """Load this session's live cache entries, keyed by `cache_key(...)`.

    Fails open (returns `{}`) on a missing file, a failed ownership/symlink
    check, an `OSError`, or a malformed line (unparseable JSON, or JSON that
    doesn't decode to an object) — a corrupt or tampered cache degrades to
    "no cached decisions", never to a crash or a bypass.
    """
    fd = _open_cache_path(os.O_RDONLY)
    if fd is None:
        return {}

    entries: dict[str, dict] = {}
    try:
        with os.fdopen(fd, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("session_id") != session_id:
                    continue
                key = cache_key(
                    record.get("rule_name"),
                    record.get("tool_name"),
                    record.get("tool_input"),
                    record.get("config_path"),
                )
                entries[key] = record
    except OSError:
        return {}
    return entries


def append_cache_entry(
    session_id: str,
    rule_name: str,
    tool_name: str,
    tool_input: dict,
    config_path: Any,
) -> None:
    """Append one JSONL cache record for `session_id`. Never raises.

    Mirrors `log_decision`'s O_CREAT/0o600 pattern, plus the O_NOFOLLOW and
    owning-uid check `_open_cache_path` performs (KTD8).
    """
    existed = CACHE_PATH.exists()
    fd = _open_cache_path(
        os.O_WRONLY | os.O_APPEND | os.O_CREAT,
        0o600,
    )
    if fd is None:
        return

    try:
        record = {
            "session_id": session_id,
            "rule_name": rule_name,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "config_path": str(config_path),
        }
        with os.fdopen(fd, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        if not existed:
            os.chmod(CACHE_PATH, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def emit_hook_output(decision: Decision) -> None:
    out: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision.permission,
        }
    }
    # Per Claude Code spec, permissionDecisionReason is shown to the user on
    # `deny` and `ask` decisions; on `allow` and `defer` it would be ignored.
    if decision.permission in ("deny", "ask") and decision.reason:
        out["hookSpecificOutput"]["permissionDecisionReason"] = decision.reason
    # additionalContext is model-only (never shown to the human) — the
    # cacheable cue always goes here, never into permissionDecisionReason.
    if decision.additional_context:
        out["hookSpecificOutput"]["additionalContext"] = decision.additional_context
    json.dump(out, sys.stdout)


def cmd_hook() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw or "{}")
    except json.JSONDecodeError:
        emit_hook_output(Decision("ask"))
        return 0
    # Errors below (TOML decode, IO) are caught generically and the hook
    # falls back to "ask" — the audit log captures the exception type so
    # config-format mistakes are diagnosable without breaking the session.

    tool_name = event.get("tool_name", "") or ""
    tool_input = event.get("tool_input") or {}
    cwd = event.get("cwd") or os.getcwd()
    session_id = event.get("session_id") or ""

    config_path = active_config_path(cwd)
    if config_path is None:
        emit_hook_output(Decision("ask"))
        log_decision({
            "ts": _now(), "tool": tool_name, "decision": "ask",
            "rule": None, "input": tool_input, "cwd": cwd,
            "config_path": None,
        })
        return 0

    try:
        config = load_config(config_path)
        # An empty session_id would let load_cache("") match records stored
        # with an equally empty id, bleeding across sessions that failed to
        # report one (KTD2) — skip the lookup entirely rather than risk that.
        cache = load_cache(session_id) if session_id else {}
        decision = decide(
            config,
            tool_name,
            tool_input,
            cache=cache,
            config_path=config_path,
            session_id=session_id,
        )
    except Exception as exc:
        log_decision({
            "ts": _now(), "tool": tool_name, "decision": "ask",
            "rule": None, "error": f"{type(exc).__name__}: {exc}",
            "input": tool_input, "cwd": cwd,
            "config_path": str(config_path),
        })
        emit_hook_output(Decision("ask"))
        return 0

    record = {
        "ts": _now(), "tool": tool_name,
        "decision": decision.permission,
        "rule": decision.rule_name,
        "reason": decision.reason,
        "input": tool_input, "cwd": cwd,
        "config_path": str(config_path),
    }
    if decision.source == "cache":
        record["source"] = "cache"
    log_decision(record)
    emit_hook_output(decision)
    return 0


def _cache_state_line(session_id: Optional[str], decision: Optional[Decision]) -> str:
    """Describe cache state honestly for `cmd_explain`'s trace output.

    `cmd_explain` has no session context of its own (it's a manual dry-run,
    not the hook reading a live PreToolUse event), so without an explicit
    `--session` it must say so rather than imply a lookup happened. When a
    session is given, `decision` was produced by the same `decide()` call
    the hook makes with the same loaded cache — `decision.source == "cache"`
    is therefore the live-path answer, never a separately-derived guess.
    """
    if session_id is None:
        return "cache:    no --session given — cache state not checked"
    if decision is not None and decision.source == "cache":
        return f"cache:    hit — resolved from cache for session {session_id}"
    return f"cache:    no matching cache entry for session {session_id}"


def cmd_explain(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    argv = [a for a in argv if a != "--verbose"]

    session_id: Optional[str] = None
    if "--session" in argv:
        idx = argv.index("--session")
        # An empty value would otherwise fall through the `if session_id`
        # guards below as falsy — skipping the cache lookup while still
        # reporting "no matching cache entry", a false claim that a check
        # ran (mirrors cmd_hook/cmd_remember's own empty-session_id guards).
        if idx + 1 >= len(argv) or not argv[idx + 1]:
            sys.stderr.write("--session requires a non-empty value\n")
            return 2
        session_id = argv[idx + 1]
        argv = argv[:idx] + argv[idx + 2 :]

    if len(argv) < 2:
        sys.stderr.write(
            "usage: yapermission.py explain [--verbose] [--session <session_id>] "
            "<tool_name> <tool_input_json>\n"
            'example: yapermission.py explain Bash \'{"command":"git status"}\'\n'
        )
        return 2

    tool_name = argv[0]
    try:
        tool_input = json.loads(argv[1])
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"invalid tool_input JSON: {exc}\n")
        return 2

    cwd = os.getcwd()
    config_path = active_config_path(cwd)
    print(f"cwd:    {cwd}")
    print(f"config: {config_path or '(none — every call falls through to ask)'}")
    if config_path is None:
        print("decision: ask")
        print(_cache_state_line(session_id, None))
        return 0

    try:
        config = load_config(config_path)
    except Exception as exc:
        print(f"config load failed: {exc}")
        print("decision: ask (fail-open)")
        print(_cache_state_line(session_id, None))
        return 0

    # Same load_cache/cache_key path cmd_hook uses, so this dry run can
    # never disagree with what the live PreToolUse hook would do.
    cache = load_cache(session_id) if session_id else {}
    decision = decide(
        config, tool_name, tool_input, cache=cache, config_path=config_path, session_id=session_id
    )
    print(f"tool:   {tool_name}")
    print(f"input:  {json.dumps(tool_input)}")
    print()
    if verbose:
        for line in decision.trace:
            print(f"  · {line}")
        print()
    print(f"decision: {decision.permission}")
    if decision.rule_name:
        print(f"rule:     {decision.rule_name}")
    if decision.reason:
        print(f"reason:   {decision.reason}")
    print(_cache_state_line(session_id, decision))
    return 0


def _matched_ask_rule(config: dict, tool_name: str, tool_input: dict) -> Optional[dict]:
    """Return the first `[[ask]]` rule matching this call, or None.

    Mirrors `decide()`'s own ask-group scan so `cmd_remember`'s cacheable
    check inspects the exact rule object `decide()` matched — never a
    same-named lookalike (two `[[ask]]` rules may share a `name`).
    """
    for rule in config.get("ask") or []:
        if rule_matches(rule, tool_name, tool_input):
            return rule
    return None


def cmd_remember(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write(
            "usage: yapermission.py remember <session_id> <tool_name> <tool_input_json>\n"
            'example: yapermission.py remember S1 Bash \'{"command":"deploy prod"}\'\n'
        )
        return 2

    session_id, tool_name, tool_input_raw = argv
    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"invalid tool_input JSON: {exc}\n")
        return 2
    if not isinstance(tool_input, dict):
        sys.stderr.write("tool_input must be a JSON object\n")
        return 2

    cwd = os.getcwd()

    def refuse(reason: str, config_path: Any = None, rule_name: Optional[str] = None) -> int:
        sys.stderr.write(reason + "\n")
        log_decision({
            "ts": _now(), "decision": "remember-refused", "reason": reason,
            "tool": tool_name, "rule": rule_name, "input": tool_input,
            "cwd": cwd, "config_path": str(config_path) if config_path else None,
            "session_id": session_id,
        })
        return 1

    # A cache entry written under "" could never be looked up again by
    # cmd_hook's empty-session_id guard (KTD2) — a dead write plus, if the
    # cue that prompted it leaked, an invitation to retry it forever.
    if not session_id:
        return refuse("empty session_id — refusing to cache")

    config_path = active_config_path(cwd)
    if config_path is None:
        return refuse("no active yapermission config — nothing to remember")

    try:
        config = load_config(config_path)
    except Exception as exc:
        # Deliberate divergence from cmd_explain's fail-open-to-ask: a
        # revalidation gate that can't be evaluated must refuse, not allow.
        return refuse(f"config load failed: {exc}", config_path=config_path)

    # Empty cache: this call must exercise live rule evaluation, not a
    # pre-existing cache hit — otherwise a repeat `remember` for an
    # already-cached call would resolve to "allow" and skip the cacheable
    # check entirely.
    decision = decide(config, tool_name, tool_input, cache={}, config_path=config_path)

    if decision.permission != "ask":
        return refuse(
            f"call resolves to '{decision.permission}', not 'ask' — refusing to cache",
            config_path=config_path, rule_name=decision.rule_name,
        )

    matched_rule = _matched_ask_rule(config, tool_name, tool_input)
    if matched_rule is None:
        return refuse(
            "no ask rule matched this call — nothing to remember", config_path=config_path,
        )

    if matched_rule.get("cacheable") is not True:
        return refuse(
            f"rule '{decision.rule_name}' is not marked cacheable",
            config_path=config_path, rule_name=decision.rule_name,
        )

    # `name` is only "recommended" in the rule schema, so an unnamed
    # cacheable rule would otherwise cache under rule_name=None — collapsing
    # every unnamed cacheable rule onto the same cache-key component and
    # weakening the "rule + exact command" key (R2/R3) for that edge case.
    if not decision.rule_name:
        return refuse(
            "matched rule has no 'name' — cacheable rules must be named",
            config_path=config_path,
        )

    append_cache_entry(session_id, decision.rule_name, tool_name, tool_input, config_path)
    log_decision({
        "ts": _now(), "decision": "remember-granted",
        "tool": tool_name, "rule": decision.rule_name, "input": tool_input,
        "cwd": cwd, "config_path": str(config_path), "session_id": session_id,
    })
    print(f"remembered: rule '{decision.rule_name}' cached for session {session_id}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("usage: yapermission.py {hook|explain|remember} [args...]\n")
        return 2
    cmd = sys.argv[1]
    if cmd == "hook":
        return cmd_hook()
    if cmd == "explain":
        return cmd_explain(sys.argv[2:])
    if cmd == "remember":
        return cmd_remember(sys.argv[2:])
    sys.stderr.write(f"unknown subcommand: {cmd}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
