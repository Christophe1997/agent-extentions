#!/usr/bin/env python3
"""List recent Claude Code sessions with their first user message.

Output (one line per session, tab-separated):
  date<TAB>project-slug<TAB>first-message<TAB>/full/path/to/session.jsonl

Usage:
  python3 list-sessions.py [--days N] [--limit N]
"""

import argparse
import json
import os
import subprocess
from datetime import datetime


def first_user_message(path, max_chars=100):
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
                        c = c.strip()
                        if len(c) > 10 and not c.startswith("/"):
                            return c[:max_chars]
                    elif isinstance(c, list):
                        for item in c:
                            if isinstance(item, dict) and item.get("type") == "text":
                                t = item.get("text", "").strip()
                                if len(t) > 10 and not t.startswith("/"):
                                    return t[:max_chars]
                except Exception:
                    pass
    except Exception:
        pass
    return "(no messages)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    parser.add_argument("--limit", type=int, default=20, help="Max sessions to list (default: 20)")
    args = parser.parse_args()

    projects_dir = os.path.expanduser("~/.claude/projects/")

    raw = subprocess.check_output(
        [
            "find", projects_dir,
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
        project = os.path.basename(os.path.dirname(path))
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
        msg = first_user_message(path)
        print(f"{mtime}\t{project}\t{msg}\t{path}")


if __name__ == "__main__":
    main()
