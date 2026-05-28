#!/usr/bin/env python3
"""Harvest a bounded prose digest from recent Claude Code session transcripts.

This is the first stage of the /zettel-sync "context funnel": it turns tens of
MB of raw JSONL into a compact, human-readable digest of *what was explored* —
user questions and assistant explanatory prose — so the model can extract
concepts without ingesting the raw transcripts.

What it keeps:  user-typed text, assistant text blocks, markdown headers.
What it drops:  thinking blocks, tool_use / tool_result blocks, fenced code
                (replaced with a `[code]` marker), and system/command tags.

Output (default text):
  # Transcript digest — last N days
  ## project: <slug>
  ### session <id8>  <date>
  [user] ...
  [asst] ...

Usage:
  python3 harvest_concepts.py [--days N] [--project /abs/path]
                              [--max-session-chars N] [--max-total-chars N]
                              [--min-chars N] [--format text|json] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

PROJECTS_DIR = os.path.expanduser("~/.claude/projects/")

# ----------------------------------------------------------------------------
# Cleaning helpers (strip_system_tags lifted from show-me-the-session)
# ----------------------------------------------------------------------------

_TAG_PATTERNS = [
    r"<system-reminder>.*?</system-reminder>",
    r"<local-command-caveat>.*?</local-command-caveat>",
    r"<local-command-stdout>.*?</local-command-stdout>",
    r"<command-name>.*?</command-name>",
    r"<command-message>.*?</command-message>",
    r"<command-args>.*?</command-args>",
    r"<command-input>.*?</command-input>",
]


def strip_system_tags(text: str) -> str:
    for pat in _TAG_PATTERNS:
        text = re.sub(pat, "", text, flags=re.DOTALL)
    return text.strip()


def strip_code_blocks(text: str) -> str:
    """Replace fenced code blocks with a marker — code is noisy for concept
    discovery, while prose and headers carry the signal."""
    return re.sub(r"```.*?```", "[code]", text, flags=re.DOTALL)


def collapse_blanks(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean(text: str) -> str:
    return collapse_blanks(strip_code_blocks(strip_system_tags(text)))


# ----------------------------------------------------------------------------
# Transcript parsing
# ----------------------------------------------------------------------------

def extract_text_blocks(content) -> list[str]:
    """Pull text from a message's content (string or block list).

    Keeps only `text` blocks; skips thinking / tool_use / tool_result so the
    digest stays focused on conceptual prose.
    """
    blocks: list[str] = []
    if isinstance(content, str):
        blocks.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                blocks.append(item.get("text", ""))
    return blocks


def iter_turns(path: str, min_chars: int):
    """Yield (role, cleaned_text) for substantive user/assistant turns."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message", obj)
                role = msg.get("role")
                if role not in ("user", "assistant"):
                    continue
                for raw in extract_text_blocks(msg.get("content", "")):
                    text = clean(raw)
                    if len(text) >= min_chars:
                        yield role, text
    except OSError:
        return


def session_id8(path: str) -> str:
    name = os.path.basename(path).replace(".jsonl", "")
    return name[:8] if len(name) >= 8 else name


def project_slug(path: str) -> str:
    return os.path.basename(os.path.dirname(path))


def find_sessions(search_dir: str, days: int) -> list[str]:
    try:
        raw = subprocess.check_output(
            ["find", search_dir, "-name", "*.jsonl", "!", "-name", "agent-*",
             "-type", "f", "-mtime", f"-{days}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    files = [f for f in raw.strip().split("\n") if f]
    return sorted(files, key=os.path.getmtime, reverse=True)


# ----------------------------------------------------------------------------
# Digest assembly
# ----------------------------------------------------------------------------

def digest_session(path: str, max_session_chars: int, min_chars: int) -> dict | None:
    turns = []
    used = 0
    for role, text in iter_turns(path, min_chars):
        if max_session_chars and used >= max_session_chars:
            break
        remaining = (max_session_chars - used) if max_session_chars else len(text)
        snippet = text[:remaining]
        turns.append({"role": role, "text": snippet})
        used += len(snippet)
    if not turns:
        return None
    return {
        "project": project_slug(path),
        "session_id": session_id8(path),
        "date": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M"),
        "chars": used,
        "turns": turns,
    }


def render_text(sessions: list[dict], days: int) -> str:
    total = sum(s["chars"] for s in sessions)
    projects = sorted({s["project"] for s in sessions})
    out = [
        f"# Transcript digest — last {days} days (generated {datetime.now():%Y-%m-%d})",
        f"# projects: {len(projects)}  sessions: {len(sessions)}  chars: {total}",
        "",
    ]
    by_project: dict[str, list[dict]] = {}
    for s in sessions:
        by_project.setdefault(s["project"], []).append(s)
    for project in projects:
        out.append(f"## project: {project}")
        out.append("")
        for s in by_project[project]:
            out.append(f"### session {s['session_id']}  {s['date']}")
            for t in s["turns"]:
                label = "user" if t["role"] == "user" else "asst"
                out.append(f"[{label}] {t['text']}")
            out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--project", type=str, default=None,
                        help="Restrict to one project (absolute path)")
    parser.add_argument("--max-session-chars", type=int, default=4000,
                        help="Cap prose kept per session (default: 4000; 0 = unbounded)")
    parser.add_argument("--max-total-chars", type=int, default=120000,
                        help="Cap total digest size; oldest sessions dropped first "
                             "(default: 120000; 0 = unbounded)")
    parser.add_argument("--min-chars", type=int, default=12,
                        help="Ignore turns shorter than this many chars (default: 12)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=str, default=None,
                        help="Write digest to PATH instead of stdout")
    args = parser.parse_args()

    if args.project:
        project_path = os.path.abspath(args.project)
        slug = "-" + project_path.lstrip("/").replace("/", "-")
        search_dir = os.path.join(PROJECTS_DIR, slug)
    else:
        search_dir = PROJECTS_DIR

    paths = find_sessions(search_dir, args.days)

    sessions: list[dict] = []
    total = 0
    for path in paths:  # already newest-first
        d = digest_session(path, args.max_session_chars, args.min_chars)
        if not d:
            continue
        if args.max_total_chars and total + d["chars"] > args.max_total_chars:
            break
        sessions.append(d)
        total += d["chars"]

    omitted = max(0, len(paths) - len(sessions))

    if args.format == "json":
        payload = {"days": args.days, "sessions": sessions,
                   "total_chars": total, "omitted_sessions": omitted}
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        rendered = render_text(sessions, args.days)
        if omitted:
            rendered += f"\n# note: {omitted} older/empty session(s) omitted (size cap)\n"

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"wrote {len(sessions)} sessions, {total} chars -> {args.output}", file=sys.stderr)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
