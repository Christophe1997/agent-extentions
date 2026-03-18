#!/usr/bin/env python3
"""Generate a single solarized-light themed HTML page from a Claude Code session JSONL file.

Supports:
- Single HTML output (default)
- Split output for large sessions (--split flag)
- Custom page size (--page-size N, default 50 messages per page)
"""

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path


# --- Template loading ---

_TMPL = Path(__file__).parent / "templates"

_CSS             = (_TMPL / "style.css").read_text(encoding="utf-8")
_JS              = (_TMPL / "script.js").read_text(encoding="utf-8")
_PAGE_TMPL       = (_TMPL / "page.html").read_text(encoding="utf-8")
_SPLIT_PAGE_TMPL = (_TMPL / "split-page.html").read_text(encoding="utf-8")
_INDEX_TMPL      = (_TMPL / "index.html").read_text(encoding="utf-8")


def _render(template: str, **kwargs) -> str:
    """Replace {{KEY}} placeholders in a template string."""
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


# --- HTML helpers ---

def escape(text):
    """HTML-escape a string."""
    return html.escape(str(text)) if text else ""


def simple_markdown(text):
    """Convert a subset of markdown to HTML: bold, italic, inline code, code blocks, links, paragraphs."""
    if not text:
        return ""
    t = escape(text)

    # Fenced code blocks: ```lang\n...\n```
    t = re.sub(
        r"```(\w*)\n(.*?)```",
        lambda m: f'<pre><code>{m.group(2)}</code></pre>',
        t,
        flags=re.DOTALL,
    )

    # Inline code: `...`
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)

    # Bold: **...**
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)

    # Italic: *...*
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)

    # Links: [text](url)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)

    # Paragraphs
    parts = re.split(r"\n{2,}", t)
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("<pre>"):
            result.append(part)
        else:
            result.append(f"<p>{part.replace(chr(10), '<br>')}</p>")
    return "\n".join(result)


def render_tool_use(block):
    """Render a tool_use content block."""
    name = escape(block.get("name", "Tool"))
    inp = block.get("input", {})
    tool_id = escape(block.get("id", ""))

    # Determine icon and specialized rendering
    if name == "Bash":
        desc = escape(inp.get("description", ""))
        cmd = escape(inp.get("command", ""))
        desc_html = f'<div class="tool-description">{desc}</div>' if desc else ""
        return (
            f'<div class="tool-use bash-tool" data-tool-id="{tool_id}">'
            f'<div class="tool-header"><span class="tool-icon">$</span> {name}</div>'
            f'{desc_html}'
            f'<div class="truncatable"><div class="truncatable-content">'
            f'<pre class="bash-command">{cmd}</pre>'
            f'</div><button class="expand-btn">Show more</button></div>'
            f'</div>'
        )
    elif name == "Write":
        path = escape(inp.get("file_path", ""))
        content = escape(inp.get("content", ""))
        short_path = path.split("/")[-1] if "/" in path else path
        return (
            f'<div class="file-tool write-tool" data-tool-id="{tool_id}">'
            f'<div class="file-tool-header write-header">Write <span class="file-tool-path">{short_path}</span></div>'
            f'<div class="truncatable"><div class="truncatable-content">'
            f'<pre>{content}</pre>'
            f'</div><button class="expand-btn">Show more</button></div>'
            f'</div>'
        )
    elif name == "Edit":
        path = escape(inp.get("file_path", ""))
        old_str = escape(inp.get("old_string", ""))
        new_str = escape(inp.get("new_string", ""))
        short_path = path.split("/")[-1] if "/" in path else path
        return (
            f'<div class="file-tool edit-tool" data-tool-id="{tool_id}">'
            f'<div class="file-tool-header edit-header">Edit <span class="file-tool-path">{short_path}</span></div>'
            f'<div class="edit-section edit-old"><div class="edit-label">-</div>'
            f'<pre class="edit-content">{old_str}</pre></div>'
            f'<div class="edit-section edit-new"><div class="edit-label">+</div>'
            f'<pre class="edit-content">{new_str}</pre></div>'
            f'</div>'
        )
    elif name == "Read":
        path = escape(inp.get("file_path", ""))
        short_path = path.split("/")[-1] if "/" in path else path
        return (
            f'<div class="tool-use" data-tool-id="{tool_id}">'
            f'<div class="tool-header">Read <span class="file-tool-path">{short_path}</span></div>'
            f'</div>'
        )
    elif name in ("Grep", "Glob"):
        pattern = escape(inp.get("pattern", ""))
        path = escape(inp.get("path", ""))
        desc = f"pattern: {pattern}" + (f" in {path}" if path else "")
        return (
            f'<div class="tool-use" data-tool-id="{tool_id}">'
            f'<div class="tool-header">{name}</div>'
            f'<div class="tool-description">{desc}</div>'
            f'</div>'
        )
    else:
        # Generic tool
        desc = escape(inp.get("description", ""))
        desc_html = f'<div class="tool-description">{desc}</div>' if desc else ""
        input_json = json.dumps(inp, indent=2, ensure_ascii=False)
        return (
            f'<div class="tool-use" data-tool-id="{tool_id}">'
            f'<div class="tool-header">{name}</div>'
            f'{desc_html}'
            f'<div class="truncatable"><div class="truncatable-content">'
            f'<pre>{escape(input_json)}</pre>'
            f'</div><button class="expand-btn">Show more</button></div>'
            f'</div>'
        )


def render_tool_result(block):
    """Render a tool_result content block."""
    content = block.get("content", "")
    is_error = block.get("is_error", False)
    error_cls = " tool-error" if is_error else ""

    if isinstance(content, list):
        # content can be a list of blocks (e.g., images)
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(escape(item.get("text", "")))
            else:
                parts.append(escape(json.dumps(item)))
        text = "\n".join(parts)
    else:
        text = escape(str(content))

    return (
        f'<div class="tool-result{error_cls}">'
        f'<div class="truncatable"><div class="truncatable-content">'
        f'<pre>{text}</pre>'
        f'</div><button class="expand-btn">Show more</button></div>'
        f'</div>'
    )


def render_content_blocks(blocks):
    """Render a list of content blocks to HTML."""
    parts = []
    for block in blocks:
        btype = block.get("type", "")
        if btype == "thinking":
            thinking_html = simple_markdown(block.get("thinking", ""))
            parts.append(
                f'<details class="thinking">'
                f'<summary>Thinking</summary>'
                f'<div class="thinking-body">{thinking_html}</div>'
                f'</details>'
            )
        elif btype == "text":
            text_html = simple_markdown(block.get("text", ""))
            parts.append(f'<div class="assistant-text">{text_html}</div>')
        elif btype == "tool_use":
            parts.append(render_tool_use(block))
        elif btype == "tool_result":
            parts.append(render_tool_result(block))
    return "\n".join(parts)


def strip_system_tags(text):
    """Remove or mute system tags like <local-command-caveat>, <system-reminder>, etc."""
    # Remove system-reminder blocks entirely
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    # Remove local-command tags but keep content for context
    text = re.sub(r"<local-command-caveat>.*?</local-command-caveat>", "", text, flags=re.DOTALL)
    text = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", text, flags=re.DOTALL)
    # Remove command-name tags entirely - the original slash command is already in the text
    text = re.sub(r"<command-name>.*?</command-name>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-message>.*?</command-message>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-args>.*?</command-args>", "", text, flags=re.DOTALL)
    return text.strip()


def is_skill_content(text):
    """Detect if text is expanded skill/command content loaded into context.

    Skills are loaded with a header like:
    'Base directory for this skill: /path/to/plugin/skills/skill-name'

    Returns (is_skill, skill_name) tuple.
    """
    if not text:
        return False, None

    # Pattern: "Base directory for this skill: /path/plugin/skills/skill-name"
    match = re.search(r"Base directory for this skill:.*?/skills/([^/\s]+)", text)
    if match:
        return True, match.group(1)

    return False, None


def render_skill_content(text, skill_name):
    """Render skill/command content as a collapsible details block.

    Uses different icons:
    - Commands (start with /): ⚡ icon
    - Skills: 📚 icon
    """
    # Remove the "Base directory" line for cleaner display
    clean_text = re.sub(r"Base directory for this skill:.*?\n", "", text, count=1)
    content_html = simple_markdown(clean_text)

    # Distinguish commands from skills
    if skill_name.startswith("/"):
        icon = "⚡"
        label = "Command"
        css_class = "command-content"
    else:
        icon = "📚"
        label = "Skill"
        css_class = "skill-content"

    return (
        f'<details class="{css_class}">'
        f'<summary>{icon} {label}: {escape(skill_name)}</summary>'
        f'<div class="skill-body">{content_html}</div>'
        f'</details>'
    )


def render_message(msg):
    """Render a single JSONL message line to HTML.

    Messages may have _skill_name annotation from preprocessing.
    """
    msg_type = msg.get("type", "")
    if msg_type == "file-history-snapshot":
        return ""

    message = msg.get("message", {})
    role = message.get("role", "")
    content = message.get("content", "")
    timestamp = msg.get("timestamp", "")

    ts_id = timestamp.replace(":", "-").replace(".", "-") if timestamp else ""
    time_html = (
        f'<a href="#msg-{ts_id}" class="timestamp-link">'
        f'<time datetime="{escape(timestamp)}" data-timestamp="{escape(timestamp)}">'
        f'{escape(timestamp)}</time></a>'
    ) if timestamp else ""

    if role == "user":
        if isinstance(content, str):
            clean = strip_system_tags(content)
            if not clean:
                return ""
            # Check if this is skill content
            is_skill, skill_name = is_skill_content(clean)
            if is_skill:
                body = render_skill_content(clean, skill_name)
            else:
                body = f'<div class="user-content">{simple_markdown(clean)}</div>'
        elif isinstance(content, list):
            parts = []
            for block in content:
                btype = block.get("type", "")
                if btype == "tool_result":
                    parts.append(render_tool_result(block))
                elif btype == "text":
                    text = block.get("text", "")
                    clean = strip_system_tags(text)
                    if clean:
                        # Check for skill annotation or marker
                        skill_name = block.get("_skill_name")
                        is_skill, detected_name = is_skill_content(clean)
                        if skill_name:
                            parts.append(render_skill_content(clean, skill_name))
                        elif is_skill:
                            parts.append(render_skill_content(clean, detected_name))
                        else:
                            parts.append(f'<div class="user-content">{simple_markdown(clean)}</div>')
            if not parts:
                return ""
            body = "\n".join(parts)
            # Tool results from user → use tool-reply style
            if any(b.get("type") == "tool_result" for b in content):
                return (
                    f'<div class="message tool-reply" id="msg-{ts_id}">'
                    f'<div class="message-header"><span class="role-label">Tool reply</span>{time_html}</div>'
                    f'<div class="message-content">{body}</div></div>'
                )
        else:
            return ""

        return (
            f'<div class="message user" id="msg-{ts_id}">'
            f'<div class="message-header"><span class="role-label">User</span>{time_html}</div>'
            f'<div class="message-content">{body}</div></div>'
        )

    elif role == "assistant":
        if isinstance(content, list):
            body = render_content_blocks(content)
        elif isinstance(content, str):
            body = f'<div class="assistant-text">{simple_markdown(content)}</div>'
        else:
            return ""

        if not body.strip():
            return ""

        return (
            f'<div class="message assistant" id="msg-{ts_id}">'
            f'<div class="message-header"><span class="role-label">Assistant</span>{time_html}</div>'
            f'<div class="message-content">{body}</div></div>'
        )

    return ""


def parse_jsonl(filepath):
    """Parse a JSONL session file into a list of message dicts."""
    messages = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def compute_stats(messages):
    """Compute basic stats about the session."""
    user_msgs = 0
    assistant_msgs = 0
    tool_calls = 0
    for msg in messages:
        role = msg.get("message", {}).get("role", "")
        content = msg.get("message", {}).get("content", "")
        if role == "user":
            if isinstance(content, str):
                user_msgs += 1
            elif isinstance(content, list):
                if any(b.get("type") == "tool_result" for b in content):
                    tool_calls += sum(1 for b in content if b.get("type") == "tool_result")
                else:
                    user_msgs += 1
        elif role == "assistant":
            if isinstance(content, list):
                for b in content:
                    if b.get("type") == "tool_use":
                        tool_calls += 1
                    elif b.get("type") in ("text", "thinking"):
                        assistant_msgs += 1
            else:
                assistant_msgs += 1
    return user_msgs, assistant_msgs, tool_calls


def annotate_skill_content(messages):
    """Preprocess messages to annotate skill/command content blocks.

    Detects skill content that follows:
    1. "Launching skill:" tool results (knowledge skills via Skill tool)
    2. "Base directory for this skill:" markers (knowledge skills)
    3. <command-name> tags followed by text block (commands)

    Returns a new list of annotated messages.
    """
    annotated = []
    pending_skill_name = None

    for msg in messages:
        msg_copy = msg.copy()
        message = msg_copy.get("message", {})
        role = message.get("role", "")
        content = message.get("content", "")

        # Pattern 1: Check if this is a tool_result with "Launching skill:"
        if role == "user" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str) and "Launching skill:" in result_content:
                        match = re.search(r"Launching skill: (\S+)", result_content)
                        if match:
                            pending_skill_name = match.group(1)
                        break

        # Pattern 2: Check if this is a command invocation (string with <command-name>)
        # The NEXT message will contain the command's skill content
        if role == "user" and isinstance(content, str) and "<command-name>" in content:
            match = re.search(r"<command-name>(/[^<]+)</command-name>", content)
            if match:
                pending_skill_name = match.group(1)

        # Pattern 3: Check if this user message contains skill content following a launch
        if role == "user" and pending_skill_name and isinstance(content, list):
            has_text_block = any(
                isinstance(b, dict) and b.get("type") == "text"
                for b in content
            )
            if has_text_block:
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        block["_skill_name"] = pending_skill_name
                pending_skill_name = None

        # Pattern 4: Detect skill content by "Base directory" marker
        if role == "user" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if "Base directory for this skill:" in text:
                        match = re.search(r"Base directory for this skill:.*?/skills/([^/\s]+)", text)
                        if match:
                            block["_skill_name"] = match.group(1)

        annotated.append(msg_copy)

    return annotated


def extract_session_title(messages, max_chars=50):
    """Extract a meaningful title from session messages."""
    for msg in messages:
        role = msg.get("message", {}).get("role", "")
        content = msg.get("message", {}).get("content", "")
        if role != "user":
            continue

        # Handle string content
        if isinstance(content, str):
            clean = strip_system_tags(content)
            if clean and len(clean) > 3:
                # Flatten to single line by replacing newlines with spaces
                single_line = " ".join(clean.split())
                return (single_line[:max_chars-3] + "...") if len(single_line) > max_chars else single_line

        # Handle list content (e.g., [{type: "text", text: "..."}])
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    clean = strip_system_tags(text)
                    if clean and len(clean) > 3:
                        # Flatten to single line by replacing newlines with spaces
                        single_line = " ".join(clean.split())
                        return (single_line[:max_chars-3] + "...") if len(single_line) > max_chars else single_line

    return "Claude Code Session"


def generate_html(filepath, output_path, page_size=50):
    """Generate a single HTML file from a JSONL session.

    For sessions with many messages, includes JavaScript-based pagination.
    """
    messages = parse_jsonl(filepath)
    messages = annotate_skill_content(messages)
    user_msgs, assistant_msgs, tool_calls = compute_stats(messages)

    rendered = [h for msg in messages if (h := render_message(msg))]
    body = "\n".join(rendered)
    stats = f"{user_msgs} user messages · {assistant_msgs} assistant messages · {tool_calls} tool calls"
    title = escape(extract_session_title(messages))

    page = _render(_PAGE_TMPL, TITLE=title, STATS=stats, BODY=body, CSS=_CSS, JS=_JS, PAGE_SIZE=str(page_size))
    Path(output_path).write_text(page, encoding="utf-8")
    return output_path


def generate_split_html(filepath, output_dir, page_size=50):
    """Generate split HTML files for large sessions.

    Creates:
    - index.html: Navigation page with all pages listed
    - page-1.html, page-2.html, ...: Individual pages

    Returns the path to index.html.
    """
    messages = parse_jsonl(filepath)
    messages = annotate_skill_content(messages)
    user_msgs, assistant_msgs, tool_calls = compute_stats(messages)
    title = escape(extract_session_title(messages))
    stats = f"{user_msgs} user messages · {assistant_msgs} assistant messages · {tool_calls} tool calls"

    rendered = [h for msg in messages if (h := render_message(msg))]

    total_messages = len(rendered)
    total_pages = (total_messages + page_size - 1) // page_size

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for page_num in range(1, total_pages + 1):
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, total_messages)

        # Build pagination navigation
        parts = ['<div class="pagination">']
        if page_num > 1:
            parts.append(f'<a href="page-{page_num-1}.html" class="prev">← Previous</a>')
        else:
            parts.append('<span>← Previous</span>')
        parts.append(f'<span class="page-info">Page {page_num} of {total_pages}</span>')
        if page_num < total_pages:
            parts.append(f'<a href="page-{page_num+1}.html" class="next">Next →</a>')
        else:
            parts.append('<span>Next →</span>')
        parts.append('</div>')
        pagination = "\n".join(parts)

        page_html = _render(
            _SPLIT_PAGE_TMPL,
            TITLE_TAG=f"{title} (Page {page_num}/{total_pages})",
            TITLE=title,
            STATS=stats,
            PAGINATION=pagination,
            BODY="\n".join(rendered[start_idx:end_idx]),
            CSS=_CSS,
            JS=_JS,
        )
        (output_dir / f"page-{page_num}.html").write_text(page_html, encoding="utf-8")

    # Generate index.html
    index_links = [
        f'<li><a href="page-{n}.html">Page {n}</a> '
        f'(messages {(n-1)*page_size+1}-{min(n*page_size, total_messages)})</li>'
        for n in range(1, total_pages + 1)
    ]

    index_html = _render(
        _INDEX_TMPL,
        TITLE=title,
        STATS=stats,
        TOTAL_PAGES=str(total_pages),
        INDEX_LINKS="".join(index_links),
        CSS=_CSS,
        JS=_JS,
    )
    index_path = output_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return str(index_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate HTML from Claude Code session JSONL files"
    )
    parser.add_argument("session_file", help="Path to the session JSONL file")
    parser.add_argument(
        "-o", "--output",
        help="Output path (file for single HTML, directory for split mode)"
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Split output into multiple HTML files with index"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="Number of messages per page when splitting (default: 50)"
    )

    args = parser.parse_args()

    if args.output:
        output_path = args.output
    else:
        session_id = Path(args.session_file).stem
        output_path = f"{session_id}-pages" if args.split else f"{session_id}.html"

    if args.split:
        result = generate_split_html(args.session_file, output_path, args.page_size)
        print(f"Generated split HTML: {result}")
        print(f"Total pages directory: {output_path}")
    else:
        result = generate_html(args.session_file, output_path, args.page_size)
        print(f"Generated: {result}")
