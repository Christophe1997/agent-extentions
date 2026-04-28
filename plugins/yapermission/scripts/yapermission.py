#!/usr/bin/env python3
"""yapermission — PreToolUse policy engine for Claude Code.

Two entry points:
    python3 yapermission.py hook                  # run as PreToolUse hook (stdin/stdout JSON)
    python3 yapermission.py explain <tool> <json> # dry-run a tool call against the active config
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # handled in load_config

GLOBAL_CONFIG = Path.home() / ".yapermission.yaml"
PROJECT_CONFIG_NAME = ".yapermission.yaml"
LOG_PATH = Path.home() / ".yapermission.log"


@dataclass
class Decision:
    permission: str  # "allow" | "deny" | "ask"
    rule_name: Optional[str] = None
    reason: Optional[str] = None
    trace: list[str] = field(default_factory=list)


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
    if yaml is None:
        raise RuntimeError(
            "PyYAML not installed. Run: pip install --user pyyaml"
        )
    with path.open() as f:
        data = yaml.safe_load(f)
    return data or {}


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
        rule: parsed YAML rule dict with keys `name`, `tool`, `matches`, `reason`.
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


def decide(config: dict, tool_name: str, tool_input: dict) -> Decision:
    """Evaluate deny → approve → default order; return the resulting Decision."""
    trace: list[str] = []

    for rule in config.get("deny") or []:
        name = rule.get("name", "<unnamed>")
        if rule_matches(rule, tool_name, tool_input):
            trace.append(f"deny rule '{name}' matched")
            return Decision(
                permission="deny",
                rule_name=rule.get("name"),
                reason=rule.get("reason", "Denied by yapermission policy"),
                trace=trace,
            )
        trace.append(f"deny rule '{name}' skipped")

    for rule in config.get("approve") or []:
        name = rule.get("name", "<unnamed>")
        if rule_matches(rule, tool_name, tool_input):
            trace.append(f"approve rule '{name}' matched")
            return Decision(
                permission="allow",
                rule_name=rule.get("name"),
                reason=rule.get("reason"),
                trace=trace,
            )
        trace.append(f"approve rule '{name}' skipped")

    default = (config.get("default") or "ask").lower()
    trace.append(f"no rule matched — default: {default}")
    return Decision(permission=_normalize_default(default), trace=trace)


def _normalize_default(value: str) -> str:
    if value in ("approve", "allow"):
        return "allow"
    if value in ("block", "deny"):
        return "deny"
    return "ask"


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
# Entry points
# ---------------------------------------------------------------------------

def emit_hook_output(decision: Decision) -> None:
    out: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision.permission,
        }
    }
    if decision.permission == "deny" and decision.reason:
        out["hookSpecificOutput"]["permissionDecisionReason"] = decision.reason
    json.dump(out, sys.stdout)


def cmd_hook() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw or "{}")
    except json.JSONDecodeError:
        emit_hook_output(Decision("ask"))
        return 0

    tool_name = event.get("tool_name", "") or ""
    tool_input = event.get("tool_input") or {}
    cwd = event.get("cwd") or os.getcwd()

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
        decision = decide(config, tool_name, tool_input)
    except Exception as exc:
        log_decision({
            "ts": _now(), "tool": tool_name, "decision": "ask",
            "rule": None, "error": f"{type(exc).__name__}: {exc}",
            "input": tool_input, "cwd": cwd,
            "config_path": str(config_path),
        })
        emit_hook_output(Decision("ask"))
        return 0

    log_decision({
        "ts": _now(), "tool": tool_name,
        "decision": decision.permission,
        "rule": decision.rule_name,
        "reason": decision.reason,
        "input": tool_input, "cwd": cwd,
        "config_path": str(config_path),
    })
    emit_hook_output(decision)
    return 0


def cmd_explain(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    argv = [a for a in argv if a != "--verbose"]
    if len(argv) < 2:
        sys.stderr.write(
            "usage: yapermission.py explain [--verbose] <tool_name> <tool_input_json>\n"
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
        return 0

    try:
        config = load_config(config_path)
    except Exception as exc:
        print(f"config load failed: {exc}")
        print("decision: ask (fail-open)")
        return 0

    decision = decide(config, tool_name, tool_input)
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
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("usage: yapermission.py {hook|explain} [args...]\n")
        return 2
    cmd = sys.argv[1]
    if cmd == "hook":
        return cmd_hook()
    if cmd == "explain":
        return cmd_explain(sys.argv[2:])
    sys.stderr.write(f"unknown subcommand: {cmd}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
