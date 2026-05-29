---
name: gpd:module
description: Inspect a specific Go module on pkg.go.dev — versions, known vulnerabilities, contained packages, README, licenses, go.mod contents. Use when the user asks to "list versions of module X", "check vulnerabilities in Y", "what packages does Z contain", "show go.mod for W", or invokes /gpd:module.
argument-hint: <path>[@version] [-versions] [-packages] [-vulns] [-readme] [-licenses] [-limit N] [-json]
allowed-tools: [Bash, AskUserQuestion, Skill]
---

Inspect a Go module via `pkgsite-cli module` and present the result.

## Prerequisite

Verify `pkgsite-cli` availability:

```bash
command -v pkgsite-cli >/dev/null 2>&1 && echo OK || echo MISSING
```

If `MISSING`, use the `Skill` tool with `skill="go-pkg-discovery:gpd-discovery"` to run the install bootstrap.

## Process

1. **Parse `$ARGUMENTS`** — pass through verbatim. Recognized flags:
   - `-versions` — list all released versions
   - `-packages` — list packages contained in the module
   - `-vulns` — list known vulnerabilities (govulncheck data)
   - `-readme` — include rendered README
   - `-licenses` — license details
   - `-limit <n>` — cap paginated results
   - `-json` — structured output

2. **Run**:
   ```bash
   pkgsite-cli module $ARGUMENTS
   ```

3. **Present**:
   - Always show the raw CLI output verbatim.
   - Tailor the summary:
     - `-versions` → highlight the latest stable, count of v0/v1+/pre-releases, and the most recent release date
     - `-vulns` → **lead with severity** — list each CVE/GHSA with affected version ranges and fixed versions; recommend an upgrade target if applicable
     - `-packages` → group by directory depth, highlight commonly-imported subpackages
     - `-readme` → render inline if short; otherwise summarize and point to the upstream URL
     - default → surface `Path`, latest `Version`, `RepoURL`, `IsLatest`

4. **Vulnerability follow-up**:
   - When `-vulns` returns any items, proactively suggest running `/gpd:module -versions <path>` to see what versions are available for upgrade.
   - Do NOT silently ignore vulnerabilities even when the user asked about something else — surface them if you noticed them during another inspection.

## JSON schema (for `-json`)

```
moduleResult {
  Module   *Module                                   // metadata
  Versions *PaginatedResponse[VersionResponse]       // with -versions
  Vulns    *PaginatedResponse[Vulnerability]         // with -vulns
  Packages *PaginatedResponse[ModulePackageResponse] // with -packages
}
Module { Path, Version, CommitTime, IsLatest, IsRedistributable,
         IsStandardLibrary, HasGoMod, RepoURL, GoModContents, Readme, Licenses }
```

## Example Usage

| Invocation | Translated to |
|------------|---------------|
| `/gpd:module github.com/google/go-cmp` | metadata |
| `/gpd:module -versions github.com/google/go-cmp` | full version history |
| `/gpd:module -vulns golang.org/x/crypto` | vulnerability scan |
| `/gpd:module -packages -versions github.com/spf13/cobra` | combined view |
| `/gpd:module -readme -licenses github.com/google/uuid@v1.6.0` | README + license at a version |

## Related

- `gpd:package` for package-level depth (symbols, reverse deps)
- `gpd:search` to find candidate modules first
- `gpd:discovery` for the broader subcommand decision tree
