---
name: gpd:search
description: Search pkg.go.dev for Go packages by free-text query or exported symbol name. Use when the user asks to "search Go packages for X", "find Go libraries for Y", "which packages export symbol Z", or invokes /gpd:search.
argument-hint: <query> [-symbol NAME] [-limit N] [-json]
allowed-tools: [Bash, AskUserQuestion, Skill]
---

Run a search against pkg.go.dev via `pkgsite-cli search` and present the results.

## Prerequisite

Confirm `pkgsite-cli` is on `PATH`:

```bash
command -v pkgsite-cli >/dev/null 2>&1 && echo OK || echo MISSING
```

If `MISSING`, use the `Skill` tool with `skill="go-pkg-discovery:gpd-discovery"` — it owns the install-on-first-use bootstrap flow. Do not auto-install without confirmation.

## Process

1. **Parse `$ARGUMENTS`**:
   - Treat as pass-through CLI args. The user's input maps directly onto `pkgsite-cli search` flags.
   - If the user supplied natural language without flags, the entire input is the query string.
   - Common flags: `-symbol <name>`, `-limit <n>`, `-json`, `-x` (print URL).

2. **Run the search**:
   ```bash
   pkgsite-cli search $ARGUMENTS
   ```
   For the `-json` case, capture stdout and parse the `PaginatedResponse[SearchResult]` shape:
   - `Items[].PackagePath`, `ModulePath`, `Version`, `Synopsis`
   - `Total`, `NextPageToken`

3. **Present results**:
   - Show the raw CLI output verbatim (one search hit per line is already readable).
   - Add a brief synthesis below: top 3-5 most relevant results with one-line rationale, plus a note if `Total > shown count` suggesting `-limit` to widen.
   - For `-symbol` searches, highlight which packages actually re-export the symbol vs. transitive matches.

4. **Error handling**:
   - Non-zero exit → surface the CLI's error message verbatim, then suggest the most likely fix (e.g., network, typo in symbol name).
   - Empty results → suggest alternative spellings or related symbols before giving up.

## Example Usage

| Invocation | Translated to |
|------------|---------------|
| `/gpd:search uuid` | `pkgsite-cli search uuid` |
| `/gpd:search -symbol Marshal json` | `pkgsite-cli search -symbol Marshal json` |
| `/gpd:search -limit 50 grpc gateway` | `pkgsite-cli search -limit 50 grpc gateway` |

## Related

- `gpd:package` for inspecting a specific result in depth
- `gpd:module` for module-level metadata of a result's owning module
- `gpd:discovery` for the broader decision tree on which subcommand to use
