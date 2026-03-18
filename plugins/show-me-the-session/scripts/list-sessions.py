#!/usr/bin/env python3
"""List recent Claude Code sessions with their first user message.

Output (one line per session, tab-separated):
  date<TAB>first-message<TAB>session-id(short)<TAB>/full/path/to/session.jsonl

Usage:
  python3 list-sessions.py [--days N] [--limit N] [--project /abs/path]
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime


def strip_system_tags(text: str) -> str:
    """Remove system tags like <local-command-caveat>, <system-reminder>, etc."""
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    text = re.sub(r"<local-command-caveat>.*?</local-command-caveat>", "", text, flags=re.DOTALL)
    text = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-name>.*?</command-name>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-message>.*?</command-message>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-args>.*?</command-args>", "", text, flags=re.DOTALL)
    return text.strip()


def first_user_message(path: str, max_chars: int = 50) -> str:
    """Extract the first user message from a session file."""
    try:
        with open(path) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    msg = obj.get("message", obj)
                    if msg.get("role") != "user":
                        continue
                    c = msg.get("content", "")
                    if isinstance(c, str):
                        c = strip_system_tags(c)
                        if c and len(c) > 3:
                            # Flatten to single line by replacing newlines with spaces
                            single_line = " ".join(c.split())
                            return (single_line[:max_chars-3] + "...") if len(single_line) > max_chars else single_line
                    elif isinstance(c, list):
                        for item in c:
                            if isinstance(item, dict) and item.get("type") == "text":
                                t = strip_system_tags(item.get("text", ""))
                                if t and len(t) > 3:
                                    # Flatten to single line by replacing newlines with spaces
                                    single_line = " ".join(t.split())
                                    return (single_line[:max_chars-3] + "...") if len(single_line) > max_chars else single_line
                except Exception:
                    pass
    except Exception:
        pass
    return "(no messages)"


def get_session_id(path: str) -> str:
    """Extract short session ID (first 8 chars) from filename."""
    filename = os.path.basename(path)
    # Remove .jsonl extension
    session_id = filename.replace(".jsonl", "")
    # Return first 8 characters
    return session_id[:8] if len(session_id) >= 8 else session_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    parser.add_argument("--limit", type=int, default=20, help="Max sessions to list (default: 20)")
    parser.add_argument("--project", type=str, default=None, help="Absolute path to project directory (e.g. /Users/you/code/myproject)")
    args = parser.parse_args()

    projects_dir = os.path.expanduser("~/.claude/projects/")

    if args.project:
        project_path = os.path.abspath(args.project)
        project_slug = "-" + project_path.lstrip("/").replace("/", "-")
        search_dir = os.path.join(projects_dir, project_slug)
    else:
        search_dir = projects_dir

    raw = subprocess.check_output(
        [
            "find", search_dir,
            "-name", "*.jsonl",
            "!", "-name", "agent-*",
            "-type", "f",
            "-mtime", f"-{args.days}",
        ],
        text=True,
    ).strip().split("\n")

    files = sorted(
        [f for f in raw if f],
        key=os.path.getmtime,
        reverse=True,
    )[: args.limit]

    for path in files:
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
        msg = first_user_message(path)
        session_id_short = get_session_id(path)
        # Output: date<TAB>first-message<TAB>session-id<TAB>/full/path
        print(f"{mtime}\t{msg}\t{session_id_short}\t{path}")


if __name__ == "__main__":
    main()
