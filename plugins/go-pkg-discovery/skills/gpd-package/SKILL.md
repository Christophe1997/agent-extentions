---
name: gpd-package
description: Inspect a specific Go package on pkg.go.dev — metadata, rendered documentation, exported symbols, reverse dependencies, imports, licenses. Use when the user asks to "look up Go package X", "show docs for Y", "list symbols of Z", "who imports W", or invokes /gpd-package.
argument-hint: <path>[@version] [-symbols] [-imported-by] [-doc text|md|html] [-examples] [-imports] [-licenses] [-module M]
allowed-tools: [Bash, AskUserQuestion, Skill]
---

Inspect a Go package via `pkgsite-cli package` and present the result.

## Prerequisite

Verify `pkgsite-cli` availability:

```bash
command -v pkgsite-cli >/dev/null 2>&1 && echo OK || echo MISSING
```

If `MISSING`, use the `Skill` tool with `skill="gpd-discovery"` to run the install bootstrap.

## Process

1. **Parse `$ARGUMENTS`** — pass through to the CLI verbatim. Recognized flags (single-dash, Go-style):
   - `-symbols` — list exported symbols
   - `-imported-by` — list reverse dependencies
   - `-imports` — list packages this one imports
   - `-doc <text|md|html>` — render documentation
   - `-examples` — include examples (requires `-doc`)
   - `-licenses` — show license info
   - `-module <path>` — disambiguate when multiple modules contain this path
   - `-goos <os>`, `-goarch <arch>` — target a specific build
   - `-limit <n>` — cap paginated results (default 25)
   - `-json` — structured output (see `packageResult` schema below)

2. **Run**:
   ```bash
   pkgsite-cli package $ARGUMENTS
   ```

3. **Handle ambiguity**:
   - If the CLI reports the path exists in multiple modules, surface the candidate list to the user and call `AskUserQuestion` to let them pick the intended module. Re-run with `-module <chosen>`.
   - Common case: `github.com/foo/bar/baz` could belong to either the `bar` module or the `bar/baz` module.

4. **Present**:
   - Always show the raw CLI output verbatim.
   - Add a brief summary tailored to which flags were used:
     - `-symbols` → group symbols by kind (func/type/var/const) and surface the public API surface count
     - `-imported-by` → highlight notable importers (high-popularity modules, stdlib, well-known projects)
     - `-doc` → for `-doc md`, render inline; for `-doc html`, suggest the user open it in a browser
     - default (metadata) → call out the latest version, license, and `IsRedistributable` status

## JSON schema (for `-json`)

```
packageResult {
  Package    *Package                       // basic info
  Symbols    *PaginatedResponse[Symbol]     // with -symbols
  ImportedBy *PackageImportedBy             // with -imported-by
}
Package { Path, Name, Synopsis, ModulePath, Version, IsLatest,
          IsStandardLibrary, GOOS, GOARCH, Docs, Imports, Licenses }
```

## Example Usage

| Invocation | Translated to |
|------------|---------------|
| `/gpd-package github.com/google/uuid` | metadata |
| `/gpd-package -symbols github.com/google/go-cmp/cmp` | list exported API |
| `/gpd-package -imported-by github.com/google/go-cmp/cmp` | reverse deps |
| `/gpd-package -doc md github.com/spf13/cobra@v1.8.0` | render docs as Markdown |
| `/gpd-package -goos windows -doc text golang.org/x/sys/windows` | docs for Windows-only build |

## Related

- `gpd-module` for module-level info (versions, vulns)
- `gpd-search` to find candidate packages first
- `gpd-discovery` for the broader subcommand decision tree
