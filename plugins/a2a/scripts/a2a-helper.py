#!/usr/bin/env python3
"""
A2A client helper — settings resolution, auth params, session tracking.

Usage:
  a2a-helper.py resolve <url-or-alias>
  a2a-helper.py auth <url>
  a2a-helper.py session add <task-id> <url> [--alias <alias>] [--message <msg>]
  a2a-helper.py session list
  a2a-helper.py session update <task-id> <status>
"""
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


# ── Settings ────────────────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter (supports string values and string lists)."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end < 0:
        return {}
    body = text[3:end]
    result: dict = {}
    current_key: str | None = None
    current_list: list | None = None

    for line in body.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        # List item
        if line.startswith("  - ") or line.startswith("    - "):
            if current_list is not None:
                current_list.append(line.strip()[2:].strip().strip('"'))
            continue
        # Key-value
        m = re.match(r'^(\s{0,2})(\S[^:]*)\s*:\s*(.*)', line)
        if not m:
            continue
        indent, key, val = m.group(1), m.group(2).strip(), m.group(3).strip()
        val = val.strip('"').strip("'")
        if indent == "":
            # Top-level key
            current_list = None
            if val == "":
                result[key] = {}
                current_key = key
                current_list = None
            else:
                result[key] = val
                current_key = key
        else:
            # Nested key under current_key
            if current_key and isinstance(result.get(current_key), dict):
                if val == "":
                    # This nested key has a list value
                    result[current_key][key] = []
                    current_list = result[current_key][key]
                else:
                    result[current_key][key] = val
                    current_list = None
    return result


def get_settings() -> dict:
    """Read .claude/a2a.local.md from cwd upward."""
    for base in [Path.cwd(), Path.home()]:
        p = base / ".claude" / "a2a.local.md"
        if p.exists():
            return _parse_frontmatter(p.read_text())
    return {}


# ── Session ──────────────────────────────────────────────────────────────────

def _session_path() -> Path:
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    h = hashlib.sha256(session_id.encode()).hexdigest()[:10]
    return Path(tempfile.gettempdir()) / f"a2a-session-{h}.json"


def _load_session() -> dict:
    p = _session_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"tasks": []}


def _save_session(data: dict) -> None:
    _session_path().write_text(json.dumps(data, indent=2))


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_resolve(args: list[str]) -> None:
    if not args:
        print("error: missing url-or-alias", file=sys.stderr)
        sys.exit(1)
    alias = args[0]
    settings = get_settings()
    agents = settings.get("agents", {})
    print(agents.get(alias, alias))


def cmd_auth(args: list[str]) -> None:
    """Print --svc-param flags for a URL, one per line.

    Uses longest-prefix matching: only the single longest matching URL prefix
    in the auth config is applied, preventing accidental multi-match injection.
    """
    if not args:
        print("error: missing url", file=sys.stderr)
        sys.exit(1)
    url = args[0]
    settings = get_settings()
    auth = settings.get("auth", {})
    # Longest-prefix match only
    best_pattern = ""
    for pattern in auth:
        if url.startswith(pattern) and len(pattern) > len(best_pattern):
            best_pattern = pattern
    if not best_pattern:
        return
    entries = auth[best_pattern]
    params: list[str] = entries if isinstance(entries, list) else [entries]
    # Output one token per line so callers can safely build an array:
    #   while IFS= read -r line; do AUTH_ARGS+=("$line"); done < <(a2a-helper.py auth "$URL")
    # This preserves values that contain spaces (e.g. "Authorization=Bearer my token").
    for p in params:
        print("--svc-param")
        print(p)


def cmd_session(args: list[str]) -> None:
    if not args:
        print("error: missing subcommand (add|list|update)", file=sys.stderr)
        sys.exit(1)
    sub = args[0]

    if sub == "add":
        # session add <task-id> <url> [--alias <a>] [--message <m>]
        if len(args) < 3:
            print("error: session add <task-id> <url>", file=sys.stderr)
            sys.exit(1)
        task_id, url = args[1], args[2]
        rest = args[3:]
        alias = ""
        message = ""
        i = 0
        while i < len(rest):
            if rest[i] == "--alias" and i + 1 < len(rest):
                alias = rest[i + 1]; i += 2
            elif rest[i] == "--message" and i + 1 < len(rest):
                message = rest[i + 1]; i += 2
            else:
                i += 1
        data = _load_session()
        data["tasks"].append({
            "id": task_id,
            "url": url,
            "alias": alias,
            "message": message,
            "status": "submitted",
            "started": datetime.now(timezone.utc).isoformat(),
        })
        _save_session(data)
        print(f"tracked task {task_id}")

    elif sub == "list":
        data = _load_session()
        tasks = data.get("tasks", [])
        if not tasks:
            print("No tasks in current session.")
            return
        # Table header
        w_id, w_status, w_alias, w_url, w_msg = 24, 12, 14, 40, 40
        header = (f"{'TASK ID':<{w_id}}  {'STATUS':<{w_status}}  "
                  f"{'ALIAS':<{w_alias}}  {'URL':<{w_url}}  {'MESSAGE':<{w_msg}}")
        print(header)
        print("-" * len(header))
        for t in reversed(tasks):
            msg = t.get("message", "")[:w_msg]
            url = t.get("url", "")[:w_url]
            print(f"{t['id']:<{w_id}}  {t.get('status','?'):<{w_status}}  "
                  f"{t.get('alias',''):<{w_alias}}  {url:<{w_url}}  {msg:<{w_msg}}")

    elif sub == "update":
        if len(args) < 3:
            print("error: session update <task-id> <status>", file=sys.stderr)
            sys.exit(1)
        task_id, status = args[1], args[2]
        data = _load_session()
        found = False
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["status"] = status
                t["updated"] = datetime.now(timezone.utc).isoformat()
                found = True
                break
        if not found:
            print(f"error: task '{task_id}' not found in session", file=sys.stderr)
            sys.exit(1)
        _save_session(data)
        print(f"updated {task_id} -> {status}")

    else:
        print(f"error: unknown subcommand '{sub}'", file=sys.stderr)
        sys.exit(1)


# ── Main ─────────────────────────────────────────────────────────────────────

USAGE = """Usage:
  a2a-helper.py resolve <url-or-alias>
  a2a-helper.py auth <url>
  a2a-helper.py session add <task-id> <url> [--alias <alias>] [--message <msg>]
  a2a-helper.py session list
  a2a-helper.py session update <task-id> <status>
"""

def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    cmd = args[0]
    rest = args[1:]
    if cmd == "resolve":
        cmd_resolve(rest)
    elif cmd == "auth":
        cmd_auth(rest)
    elif cmd == "session":
        cmd_session(rest)
    else:
        print(f"error: unknown command '{cmd}'\n{USAGE}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
