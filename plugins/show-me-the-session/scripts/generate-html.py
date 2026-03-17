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


# --- Solarized Light CSS ---
CSS = r"""
:root {
    /* Solarized Light palette */
    --base03:  #002b36;
    --base02:  #073642;
    --base01:  #586e75;
    --base00:  #657b83;
    --base0:   #839496;
    --base1:   #93a1a1;
    --base2:   #eee8d5;
    --base3:   #fdf6e3;
    --yellow:  #b58900;
    --orange:  #cb4b16;
    --red:     #dc322f;
    --magenta: #d33682;
    --violet:  #6c71c4;
    --blue:    #268bd2;
    --cyan:    #2aa198;
    --green:   #859900;

    --bg:         var(--base3);
    --bg-alt:     var(--base2);
    --fg:         var(--base00);
    --fg-dim:     var(--base1);
    --fg-emph:    var(--base01);
    --accent:     var(--blue);
    --border:     var(--base1);
}

* { box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--fg);
    margin: 0;
    padding: 16px;
    line-height: 1.6;
}

.container {
    max-width: 820px;
    margin: 0 auto;
}

h1 {
    font-size: 1.4rem;
    color: var(--fg-emph);
    border-bottom: 2px solid var(--accent);
    padding-bottom: 8px;
    margin-bottom: 24px;
}

.stats {
    font-size: 0.85rem;
    color: var(--fg-dim);
    margin-bottom: 20px;
}

/* --- Messages --- */
.message {
    margin-bottom: 14px;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 14px;
    background: rgba(0,0,0,0.03);
    font-size: 0.82rem;
}

.role-label {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 0.78rem;
}

time {
    color: var(--fg-dim);
    font-size: 0.78rem;
}

.message-content {
    padding: 12px 14px;
}

.message-content p { margin: 0 0 10px 0; }
.message-content p:last-child { margin-bottom: 0; }

/* User */
.message.user {
    background: var(--bg-alt);
    border-left: 4px solid var(--accent);
}
.message.user .role-label { color: var(--accent); }

/* Assistant */
.message.assistant {
    background: var(--bg);
    border-left: 4px solid var(--fg-dim);
    border: 1px solid var(--bg-alt);
}
.message.assistant .role-label { color: var(--fg-dim); }

/* System (tool replies) */
.message.tool-reply {
    background: #fef9ec;
    border-left: 4px solid var(--yellow);
}
.message.tool-reply .role-label { color: var(--yellow); }

/* --- Thinking --- */
.thinking {
    background: #fef9ec;
    border: 1px solid var(--yellow);
    border-radius: 6px;
    margin: 8px 0;
    font-size: 0.88rem;
    color: var(--fg-dim);
}
.thinking summary {
    cursor: pointer;
    padding: 8px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--yellow);
    user-select: none;
}
.thinking-body {
    padding: 0 12px 10px 12px;
}
.thinking-body p { margin: 6px 0; }

/* --- Tool Use --- */
.tool-use {
    background: #f3eef8;
    border: 1px solid var(--violet);
    border-radius: 6px;
    padding: 10px 12px;
    margin: 8px 0;
}
.tool-header {
    font-weight: 600;
    color: var(--violet);
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
}
.tool-icon { font-size: 1rem; }
.tool-description {
    font-size: 0.85rem;
    color: var(--fg-dim);
    font-style: italic;
    margin-bottom: 6px;
}

/* --- Tool Result --- */
.tool-result {
    background: #eef6ee;
    border-radius: 6px;
    padding: 10px 12px;
    margin: 8px 0;
}
.tool-result.tool-error {
    background: #fdecec;
}

/* --- Code --- */
pre {
    background: var(--base02);
    color: var(--base1);
    padding: 10px 12px;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 0.83rem;
    line-height: 1.5;
    margin: 6px 0;
    white-space: pre-wrap;
    word-wrap: break-word;
}

code {
    background: rgba(0,0,0,0.06);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.88em;
}
pre code { background: none; padding: 0; }

/* --- File Tool (Write/Edit) --- */
.file-tool {
    border-radius: 6px;
    padding: 10px 12px;
    margin: 8px 0;
}
.write-tool {
    background: linear-gradient(135deg, #eef6ee 0%, #f0f6ec 100%);
    border: 1px solid var(--green);
}
.edit-tool {
    background: linear-gradient(135deg, #fef5ec 0%, #fdeef0 100%);
    border: 1px solid var(--orange);
}
.file-tool-header {
    font-weight: 600;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
}
.write-header { color: var(--green); }
.edit-header { color: var(--orange); }
.file-tool-path {
    font-family: monospace;
    background: rgba(0,0,0,0.06);
    padding: 1px 6px;
    border-radius: 3px;
}

.edit-section { display: flex; margin: 3px 0; border-radius: 3px; overflow: hidden; }
.edit-label { padding: 6px 10px; font-weight: bold; font-family: monospace; display: flex; align-items: flex-start; }
.edit-old { background: #fdeef0; }
.edit-old .edit-label { color: var(--red); background: #f8d6da; }
.edit-new { background: #eef6ee; }
.edit-new .edit-label { color: var(--green); background: #c8e6c8; }
.edit-content { margin: 0; flex: 1; background: transparent; font-size: 0.83rem; }

/* --- Truncatable / Collapsible --- */
.truncatable { position: relative; }
.truncatable.truncated .truncatable-content {
    max-height: 200px;
    overflow: hidden;
}
.truncatable.truncated::after {
    content: '';
    position: absolute;
    bottom: 30px;
    left: 0; right: 0;
    height: 50px;
    background: linear-gradient(to bottom, transparent, var(--bg));
    pointer-events: none;
}
.expand-btn {
    display: none;
    width: 100%;
    padding: 6px 14px;
    margin-top: 3px;
    background: rgba(0,0,0,0.04);
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 5px;
    cursor: pointer;
    font-size: 0.82rem;
    color: var(--fg-dim);
}
.expand-btn:hover { background: rgba(0,0,0,0.08); }
.truncatable.truncated .expand-btn,
.truncatable.expanded .expand-btn { display: block; }

/* Gradient overrides per parent bg */
.message.user .truncatable.truncated::after { background: linear-gradient(to bottom, transparent, var(--bg-alt)); }
.tool-use .truncatable.truncated::after { background: linear-gradient(to bottom, transparent, #f3eef8); }
.tool-result .truncatable.truncated::after { background: linear-gradient(to bottom, transparent, #eef6ee); }
.message.tool-reply .truncatable.truncated::after { background: linear-gradient(to bottom, transparent, #fef9ec); }

/* --- Responsive --- */
@media (max-width: 600px) {
    body { padding: 8px; }
    .message { border-radius: 6px; }
    .message-content { padding: 10px; }
    pre { font-size: 0.78rem; padding: 8px; }
}

/* --- Pagination --- */
.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    margin: 24px 0;
    padding: 16px;
    background: var(--bg-alt);
    border-radius: 8px;
}
.pagination a, .pagination span {
    padding: 8px 16px;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 500;
}
.pagination a {
    background: var(--accent);
    color: white;
}
.pagination a:hover {
    opacity: 0.9;
}
.pagination span {
    color: var(--fg-dim);
}
.pagination .page-info {
    color: var(--fg);
    font-size: 0.9rem;
}
"""

# --- JavaScript ---
JS = r"""
// Timestamps: convert UTC to local
document.querySelectorAll('time[data-timestamp]').forEach(function(el) {
    var ts = el.getAttribute('data-timestamp');
    var d = new Date(ts);
    var now = new Date();
    var time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    if (d.toDateString() === now.toDateString()) {
        el.textContent = time;
    } else {
        el.textContent = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' + time;
    }
});

// Truncation
document.querySelectorAll('.truncatable').forEach(function(w) {
    var c = w.querySelector('.truncatable-content');
    var b = w.querySelector('.expand-btn');
    if (c.scrollHeight > 250) {
        w.classList.add('truncated');
        b.addEventListener('click', function() {
            if (w.classList.contains('truncated')) {
                w.classList.remove('truncated');
                w.classList.add('expanded');
                b.textContent = 'Show less';
            } else {
                w.classList.remove('expanded');
                w.classList.add('truncated');
                b.textContent = 'Show more';
            }
        });
    }
});

// Keyboard navigation for pagination
document.addEventListener('keydown', function(e) {
    var prev = document.querySelector('.pagination .prev');
    var next = document.querySelector('.pagination .next');
    if (e.key === 'ArrowLeft' && prev) prev.click();
    if (e.key === 'ArrowRight' && next) next.click();
});
"""


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


def render_message(msg):
    """Render a single JSONL message line to HTML."""
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
            body = f'<div class="user-content">{simple_markdown(clean)}</div>'
        elif isinstance(content, list):
            parts = []
            for block in content:
                btype = block.get("type", "")
                if btype == "tool_result":
                    parts.append(render_tool_result(block))
                elif btype == "text":
                    clean = strip_system_tags(block.get("text", ""))
                    if clean:
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


def extract_session_title(messages):
    """Extract a meaningful title from session messages.
    """
    for msg in messages:
        role = msg.get("message", {}).get("role", "")
        content = msg.get("message", {}).get("content", "")
        if role == "user" and isinstance(content, str):
            clean = strip_system_tags(content)
            if clean and len(clean) > 3 and not clean.startswith("/"):
                # Take the first line of the cleaned prompt as title, truncated to 80 chars
                first_line = clean.splitlines()[0]
                return (first_line[:77] + "...") if len(first_line) > 80 else first_line
    return "Claude Code Session"


def generate_html(filepath, output_path):
    """Generate a single HTML file from a JSONL session."""
    messages = parse_jsonl(filepath)
    user_msgs, assistant_msgs, tool_calls = compute_stats(messages)

    rendered = []
    for msg in messages:
        h = render_message(msg)
        if h:
            rendered.append(h)

    body = "\n".join(rendered)
    stats = f"{user_msgs} user messages · {assistant_msgs} assistant messages · {tool_calls} tool calls"
    title = escape(extract_session_title(messages))

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{CSS}</style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="stats">{stats}</div>
        {body}
    </div>
    <script>{JS}</script>
</body>
</html>"""

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
    user_msgs, assistant_msgs, tool_calls = compute_stats(messages)
    title = escape(extract_session_title(messages))
    stats = f"{user_msgs} user messages · {assistant_msgs} assistant messages · {tool_calls} tool calls"

    # Render all messages
    rendered = []
    for msg in messages:
        h = render_message(msg)
        if h:
            rendered.append(h)

    # Split into pages
    total_messages = len(rendered)
    total_pages = (total_messages + page_size - 1) // page_size

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate each page
    for page_num in range(1, total_pages + 1):
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, total_messages)
        page_messages = rendered[start_idx:end_idx]

        # Build pagination navigation
        pagination_parts = ['<div class="pagination">']
        if page_num > 1:
            pagination_parts.append(f'<a href="page-{page_num-1}.html" class="prev">← Previous</a>')
        else:
            pagination_parts.append('<span>← Previous</span>')

        pagination_parts.append(f'<span class="page-info">Page {page_num} of {total_pages}</span>')

        if page_num < total_pages:
            pagination_parts.append(f'<a href="page-{page_num+1}.html" class="next">Next →</a>')
        else:
            pagination_parts.append('<span>Next →</span>')

        pagination_parts.append('</div>')
        pagination = "\n".join(pagination_parts)

        body = "\n".join(page_messages)
        page_title = f"{title} (Page {page_num}/{total_pages})"

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>{CSS}</style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="stats">{stats}</div>
        {pagination}
        {body}
        {pagination}
    </div>
    <script>{JS}</script>
</body>
</html>"""

        page_path = output_dir / f"page-{page_num}.html"
        page_path.write_text(page_html, encoding="utf-8")

    # Generate index.html
    index_links = []
    for page_num in range(1, total_pages + 1):
        start_msg = (page_num - 1) * page_size + 1
        end_msg = min(page_num * page_size, total_messages)
        index_links.append(
            f'<li><a href="page-{page_num}.html">Page {page_num}</a> '
            f'(messages {start_msg}-{end_msg})</li>'
        )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Index</title>
    <style>{CSS}</style>
    <style>
    .index-content {{
        background: var(--bg-alt);
        padding: 24px;
        border-radius: 10px;
        margin-top: 16px;
    }}
    .index-content ul {{
        list-style: none;
        padding: 0;
        margin: 0;
    }}
    .index-content li {{
        padding: 12px 16px;
        margin: 8px 0;
        background: var(--bg);
        border-radius: 6px;
    }}
    .index-content a {{
        font-weight: 600;
        color: var(--accent);
        text-decoration: none;
    }}
    .index-content a:hover {{
        text-decoration: underline;
    }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="stats">{stats}</div>
        <div class="index-content">
            <h2>Session Contents ({total_pages} pages)</h2>
            <ul>
                {"".join(index_links)}
            </ul>
        </div>
        <p style="text-align: center; margin-top: 20px;">
            <a href="page-1.html" style="font-weight: 600;">Start Reading →</a>
        </p>
    </div>
</body>
</html>"""

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

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Default: use session ID as filename in current directory
        session_id = Path(args.session_file).stem
        if args.split:
            output_path = f"{session_id}-pages"
        else:
            output_path = f"{session_id}.html"

    # Generate output
    if args.split:
        result = generate_split_html(args.session_file, output_path, args.page_size)
        print(f"Generated split HTML: {result}")
        print(f"Total pages directory: {output_path}")
    else:
        result = generate_html(args.session_file, output_path)
        print(f"Generated: {result}")
