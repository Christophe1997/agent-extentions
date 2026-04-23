---
name: ascii2img
description: This skill should be used when the user asks to "render ASCII diagram", "convert this ASCII to image", "turn this diagram into a PNG", or when the user pastes an ASCII-art diagram (boxes drawn with +, -, |, /, \), or when Claude or another agent produces an ASCII diagram in its own response. Auto-renders to PNG.
argument-hint: optional file (e.g., "/path/to/diagram.bob")
allowed-tools: [Bash, Read, AskUserQuestion, Write]
---

## Purpose

Convert an ASCII-art diagram to a PNG image using `svgbob` (ASCII → SVG) and
`rsvg-convert` (SVG → PNG). The rendering pipeline is encapsulated in
`scripts/render.sh`; this skill's job is to recognize when rendering is appropriate,
invoke the script correctly, and handle missing dependencies gracefully.

## When to render

Render whenever the conversation contains an ASCII-art *diagram* — specifically:

- The user pastes content with box-drawing characters (`+`, `-`, `|`, `/`, `\`,
  `.`, `'`, `*`, arrows like `->` or `-->`) arranged to form shapes.
- The user explicitly asks to "render", "convert", "turn into an image",
  "make a picture of", or "visualize" an ASCII diagram.
- Claude itself produces an ASCII diagram in a reply (e.g., while explaining
  architecture or flow). In that case, use `AskUserQuestion` to offer rendering
  and proceed only on confirmation.

Do **not** render:

- Ordinary fenced code blocks of source code.
- Markdown tables (the `|` column separators look superficially similar).
- Plain tree output from `tree` / `ls` unless the user explicitly asks.

When unsure, ask once before rendering.

## How to render

### Step 1 — write the diagram to a file

Use the `Write` tool to save the ASCII art verbatim to a `.bob` file. Pass the
raw string exactly as received — do not reformat whitespace or normalize
characters, since svgbob parses a rigid cell grid.

- If the diagram came from an existing file, skip this step and use that path directly.
- For pasted or self-generated diagrams, write to a descriptive name based on
  the diagram's subject (e.g., `architecture.bob`, `auth-flow.bob`).
- **Where to write**: prefer the user's current working directory so the
  resulting PNG lands beside the `.bob` source and is easy to find. Fall back
  to `/tmp/ascii2img/` only if CWD is read-only or is outside the user's
  project (e.g., inside `node_modules/` or a system directory).
- Preserve trailing whitespace and blank lines exactly as received — svgbob's
  parser is column-sensitive and even a stripped trailing space can change
  the rendered shape.

### Step 2 — detect the script and pick a font family

`svgbob`'s default `monospace` font has no glyphs for CJK, Cyrillic, Arabic, or
other non-Latin scripts, so those characters render as `□` ("tofu"). Before
invoking the render script:

1. Scan the diagram contents for the dominant non-Latin script. Look at
   *labels and text inside boxes*, not the box-drawing glyphs themselves.
   Common cases:
   - **CJK** — Han ideographs (中文), Hiragana/Katakana (ひらがな・カタカナ), Hangul (한글)
   - **Cyrillic** — Russian, Ukrainian, Bulgarian, etc. (Привет)
   - **Arabic** — Arabic, Persian, Urdu (مرحبا)
   - **Latin only** — no non-ASCII letters → skip the flag
2. Detect the host OS with `uname -s` (`Darwin` vs `Linux` matters because
   pre-installed fonts differ).
3. Pick a font family CSS string from the table below and pass it to the
   render script with `--font-family`.

| Script   | Darwin (macOS) | Linux | Other |
|----------|----------------|-------|-------|
| cjk      | `"PingFang SC, Hiragino Sans, Apple SD Gothic Neo, monospace"` | `"Noto Sans CJK SC, Noto Sans CJK JP, WenQuanYi Micro Hei, monospace"` | `"Noto Sans CJK SC, monospace"` |
| cyrillic | `"Menlo, Helvetica, monospace"` | `"DejaVu Sans Mono, Liberation Mono, monospace"` | `"DejaVu Sans Mono, monospace"` |
| arabic   | `"Geeza Pro, Apple Symbols, monospace"` | `"Noto Sans Arabic, DejaVu Sans, monospace"` | `"Noto Sans Arabic, monospace"` |
| latin    | *(omit flag)*  | *(omit flag)* | *(omit flag)* |

Each cell should be a CSS `font-family` value with fallbacks, e.g.
`"PreferredFont, FallbackFont, monospace"`. Always end with `monospace` so
svgbob still produces a usable diagram if no preferred font is installed.

### Step 3 — invoke the render script

Run via `Bash`:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ascii2img/scripts/render.sh <input.bob>
```

With a font family selected from Step 2:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ascii2img/scripts/render.sh \
  --font-family "PingFang SC, monospace" <input.bob>
```

The script:

- Prints the absolute PNG path on stdout on success.
- Writes output next to the input file (e.g., `diagram.bob` → `diagram.png`).
- Applies zoom factor 2 (`rsvg-convert -z 2`) for crisp results.
- Forwards `--font-family` to svgbob when provided; otherwise svgbob's
  built-in `monospace` default is used.

Optionally override output path and zoom (positional, after any flags):

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ascii2img/scripts/render.sh in.bob out.png 3
```

### Step 4 — handle missing dependencies

The script uses distinct exit codes to signal dependency issues. Read stderr
for the install command, then use `AskUserQuestion` to ask the user whether
to install before retrying.

| Exit code | Meaning                      | Response                                                              |
|-----------|------------------------------|-----------------------------------------------------------------------|
| `0`       | Success                      | Report the PNG path to the user                                       |
| `10`      | `svgbob` missing             | Ask user to install via the stderr-provided command, then retry       |
| `11`      | SVG→PNG converter missing    | Ask user to install `librsvg` via the stderr-provided command, retry  |
| `20`      | svgbob parse failure         | Show the input to the user; likely malformed art                      |
| `21`      | Converter failure            | Report the converter error; do not auto-install another               |

**Example of the `AskUserQuestion` flow** for a missing dependency:

```
Question: "svgbob is not installed. Install it now via `brew install svgbob`?"
Options:
  - "Yes, install now" → run `brew install svgbob`, then retry render
  - "No, skip rendering" → stop, link user to the install command
```

Never install dependencies silently. Always confirm first.

### Step 5 — report the result

On success, tell the user the PNG path. Use `AskUserQuestion` to offer opening
it (`open <path>` on macOS, `xdg-open` on Linux). Do not auto-open and do not
embed the file — the path is enough.

## Quoting glyphs that look like lines

svgbob interprets `/`, `\`, `-`, `|`, `+` as line segments. Text ending in a
slash (e.g., `references/`) may be parsed as a diagonal line and detach from
its word. To keep a glyph literal, wrap the run in double quotes inside the
diagram:

```
+----------------+
|  "src/api/"    |
+----------------+
```

Only rewrite the source if the user explicitly asks for a fix — otherwise
render as-is and flag the rendering quirk in the response.

## Scripts

- **`scripts/render.sh`** — the full render pipeline. Handles dependency
  detection, fallback between `rsvg-convert` / `magick` / `sips`, temp-file
  cleanup, and exit-code-based error reporting.
