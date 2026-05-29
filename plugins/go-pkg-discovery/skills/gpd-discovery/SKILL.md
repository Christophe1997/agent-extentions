---
name: gpd:discovery
description: Knowledge for discovering Go packages and modules via pkg.go.dev. This skill should be used when the user asks to "find a Go package for X", "look up Go module Y", "search pkg.go.dev", "what versions of <go module> exist", "are there vulnerabilities in <go module>", "what does <go package> export", "who imports <go package>", or "show docs for Go package Z" — any question about discovering Go packages/modules whose answer lives on pkg.go.dev rather than in local code.
allowed-tools: [Bash, AskUserQuestion, Skill]
---

Discover Go packages and modules by routing the user's intent to the right `pkgsite-cli` subcommand. Run the CLI, show raw output, then synthesize.

This skill is also the shared owner of the install-on-first-use bootstrap — `/gpd:search`, `/gpd:package`, and `/gpd:module` delegate to it via the `Skill` tool when `pkgsite-cli` is missing.

## When to use this skill (vs. alternatives)

| User intent                                                                               | Use                        |
| ----------------------------------------------------------------------------------------- | -------------------------- |
| Read docs for a package already on disk / in the module graph                             | `go doc` (built-in)        |
| Browse local docs with a UI                                                               | `cmd/pkgsite` (web server) |
| **Discover an unfamiliar package, look up versions/vulns/reverse-deps, search by symbol** | **this skill**             |

If the user is working with code already vendored or in `go.mod`, prefer `go doc`. Reach for `pkgsite-cli` for *discovery* — when the answer requires reaching beyond the local module graph.

## Intent → subcommand decision

| User asks about                                        | Subcommand | Key flags                                                                                     |
| ------------------------------------------------------ | ---------- | --------------------------------------------------------------------------------------------- |
| Finding packages by keyword                            | `search`   | `-symbol NAME`, `-limit N`                                                                    |
| Package metadata, docs, symbols, reverse deps          | `package`  | `-symbols`, `-imported-by`, `-doc md`, `-imports`, `-licenses`, `-goos`, `-goarch`, `-module` |
| Module versions, vulnerabilities, package list, README | `module`   | `-versions`, `-vulns`, `-packages`, `-readme`, `-licenses`                                    |

When invoked as a slash command (`/gpd:search`, `/gpd:package`, `/gpd:module`), the dedicated skills handle parsing. When activated conversationally, pick the subcommand yourself, then either run the CLI directly or delegate to the matching `gpd:*` skill.

## Process

This step runs at most once per session — if you've already verified availability earlier in the conversation, skip it.

1. **Detect**:
   ```bash
   command -v pkgsite-cli >/dev/null 2>&1 && echo OK || echo MISSING
   ```

2. **If `OK`** → proceed to run commands. Done.

3. **If `MISSING`** → verify Go toolchain is present:
   ```bash
   command -v go >/dev/null 2>&1 && echo GO_OK || echo NO_GO
   ```
   - `NO_GO` → tell the user the Go toolchain is required and stop. Suggest [https://go.dev/dl/](https://go.dev/dl/).
   - `GO_OK` → continue to step 4.

4. **Ask the user before installing.** Call `AskUserQuestion` with the prompt designed below.
  ```json
  {
    "questions": [
      {
        "question": "The `pkgsite-cli` is not installed. Install it now with `go install golang.org/x/pkgsite/cmd/internal/pkgsite-cli@latest`?",
        "header": "Install CLI",
        "multiSelect": false,
        "options": [
          {
            "label": "Yes - install now",
            "description": "Installs to $(go env GOPATH)/bin. Takes ~10-30s on first run."
          },
          {
            "label": "No - skip",
            "description": "Stop here. Install manually later with `go install golang.org/x/pkgsite/cmd/internal/pkgsite-cli@latest`."
          }
        ]
      }
    ]
  }
  ```

5. **Act on the user's answer**:
   - Install accepted → run:
     ```bash
     go install golang.org/x/pkgsite/cmd/internal/pkgsite-cli@latest
     ```
     If the command succeeds but `command -v pkgsite-cli` still fails, the binary likely landed in `$(go env GOPATH)/bin` which isn't on `PATH`. Surface a one-line fix:
     ```
     export PATH="$(go env GOPATH)/bin:$PATH"
     ```
   - Install declined → respect the choice. Stop and tell the user how to install manually; do not retry.

## Running commands

Once `pkgsite-cli` is available, run the chosen subcommand and **always show the raw CLI output** before synthesizing. Trust the CLI's formatting — it is already human-readable. Use `-json` only when you need to extract specific fields programmatically (e.g., picking the latest non-prerelease version).

## Output handling

1. **Raw first, summary second.** Print the CLI output verbatim (in a fenced block if it's long), then a brief synthesis: 2-5 lines highlighting what matters for the user's question.
2. **Vulnerabilities are never silent.** If `-vulns` returns items — or if a `module` query incidentally surfaces them — lead with severity and suggest an upgrade target.
3. **Ambiguous package paths** → if the CLI reports multiple candidate modules, use `AskUserQuestion` to let the user pick, then re-run with `-module <chosen>`.
4. **Errors** → surface the CLI's stderr verbatim. Most errors are network-related or path typos; suggest the most likely fix in one sentence.

## Subcommand cheatsheet

```bash
# Search
pkgsite-cli search uuid
pkgsite-cli search -symbol Marshal json
pkgsite-cli search -limit 50 grpc gateway

# Package
pkgsite-cli package github.com/google/uuid
pkgsite-cli package -symbols github.com/google/go-cmp/cmp
pkgsite-cli package -imported-by github.com/google/go-cmp/cmp
pkgsite-cli package -doc md github.com/spf13/cobra@v1.8.0
pkgsite-cli package -goos windows -doc text golang.org/x/sys/windows

# Module
pkgsite-cli module github.com/google/go-cmp
pkgsite-cli module -versions github.com/google/go-cmp
pkgsite-cli module -vulns golang.org/x/crypto
pkgsite-cli module -packages -versions github.com/spf13/cobra
pkgsite-cli module -readme -licenses github.com/google/uuid@v1.6.0
```

## Reference

- Upstream tool: [`golang.org/x/pkgsite/cmd/internal/pkgsite-cli`](https://pkg.go.dev/golang.org/x/pkgsite/cmd/internal/pkgsite-cli)
- API: [pkg.go.dev API](https://pkg.go.dev/api), [OpenAPI spec](https://pkg.go.dev/v1beta/openapi.yaml)
- Issue tracking: [go.dev/issue/76718](https://go.dev/issue/76718)
