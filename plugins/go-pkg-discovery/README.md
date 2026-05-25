# go-pkg-discovery

Discover Go packages, modules, versions, vulnerabilities, reverse dependencies, and exported symbols via [pkg.go.dev](https://pkg.go.dev/). A thin Claude Code wrapper around the upstream [`pkgsite-cli`](https://pkg.go.dev/golang.org/x/pkgsite/cmd/internal/pkgsite-cli) client.

## Features

### Skills

| Skill | Description |
|-------|-------------|
| `gpd:discovery` | Knowledge base for Go package discovery — when to reach for `pkgsite-cli`, which subcommand answers which question, and the shared install-on-first-use bootstrap |
| `gpd:search` | Search pkg.go.dev for packages by keyword or exported symbol |
| `gpd:package` | Inspect a specific package — metadata, docs, exported symbols, reverse dependencies, licenses |
| `gpd:module` | Inspect a specific module — versions, vulnerabilities, packages, README, licenses |

## Examples

```bash
# Find packages mentioning "uuid"
/gpd:search uuid

# Find packages that export a function named Marshal
/gpd:search -symbol Marshal json

# Inspect a package, list its exported symbols
/gpd:package -symbols github.com/google/go-cmp/cmp

# See who depends on go-cmp
/gpd:package -imported-by github.com/google/go-cmp/cmp

# Render package docs as Markdown
/gpd:package -doc md github.com/google/go-cmp/cmp

# List all versions of a module
/gpd:module -versions github.com/google/go-cmp

# Check a module for known vulnerabilities
/gpd:module -vulns golang.org/x/crypto

# Conversational use (auto-triggered via gpd:discovery skill):
# "What versions of go-cmp are available?"
# "Are there any known vulnerabilities in x/crypto?"
# "Who imports github.com/google/uuid?"
```

## Installation

```bash
/plugin install go-pkg-discovery@agent-extentions
```

## Prerequisites

- **Go toolchain** (1.21+ recommended) on `PATH`
- **`pkgsite-cli`** — auto-installed on first use, with your confirmation, via:

  ```bash
  go install golang.org/x/pkgsite/cmd/internal/pkgsite-cli@latest
  ```

Make sure `$(go env GOBIN)` (or `$(go env GOPATH)/bin`) is on your `PATH`.

## Usage

- **Conversational discovery** → ask anything about Go packages; `gpd:discovery` activates automatically
- **Search** → `/gpd:search <query> [-symbol NAME] [-limit N]`
- **Package inspect** → `/gpd:package [flags] <path>[@version]`
- **Module inspect** → `/gpd:module [flags] <path>[@version]`

Flag syntax mirrors `pkgsite-cli` exactly — run `pkgsite-cli <command> -h` for the full list.

## License

MIT
