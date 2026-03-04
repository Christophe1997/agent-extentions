---
name: init-agents
description: Scaffold an AGENTS.md file with project-specific content
argument-hint: optional path (default: ./AGENTS.md)
allowed-tools: [Bash, Read, Write, Glob]
---

Create an AGENTS.md file tailored to the current project by analyzing its structure and configuration.

## Process

1. **Analyze the project**:
   - Check for `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, etc.
   - Identify test commands from package scripts or config files
   - Detect linting/formatting tools (eslint, prettier, rustfmt, black)
   - Find build commands and development scripts

2. **Detect project type**:
   ```bash
   ls -la
   cat package.json 2>/dev/null | head -50
   ```

3. **Gather context**:
   - README.md for project description
   - Existing documentation
   - CI/CD configuration (.github/workflows, etc.)

4. **Generate AGENTS.md** with sections:

```markdown
# AGENTS.md

## Project Overview
[Brief description based on README or package.json]

## Setup Commands
- Install: [detected install command]
- Dev: [detected dev command]
- Build: [detected build command]

## Testing
- Run tests: [detected test command]
- [Additional test instructions]

## Code Style
[Detected conventions from config files]

## PR Guidelines
[Standard PR guidelines]

## Security
- [Security considerations]
```

5. **Write the file** to the specified path (default: `./AGENTS.md`)

6. **Ask about symlinks**:
   After creating AGENTS.md, ask: "Would you like me to create symlinks for other AI agents? (CLAUDE.md, .cursorrules, .windsurfrules)"

## Template Detection

| Config File | Detected Context |
|-------------|------------------|
| `package.json` | npm/pnpm/yarn commands, scripts |
| `Cargo.toml` | Rust: `cargo build`, `cargo test` |
| `go.mod` | Go: `go build`, `go test ./...` |
| `pyproject.toml` | Python: poetry/pip commands |
| `Makefile` | Make targets |

## Example Output

```markdown
# AGENTS.md

## Project Overview
A TypeScript CLI tool for data processing.

## Setup Commands
- Install: `pnpm install`
- Dev: `pnpm dev`
- Build: `pnpm build`

## Testing
- Run tests: `pnpm test`
- Coverage: `pnpm test:coverage`

## Code Style
- TypeScript strict mode
- Single quotes, no semicolons
- Max line length: 100

## PR Guidelines
- Run `pnpm lint` and `pnpm test` before committing
- Use Conventional Commits format

## Security
- Never commit .env files
- Validate all external inputs
```

## Notes

- Do not overwrite existing AGENTS.md without confirmation
- Keep generated content concise and actionable
- Include actual commands the agent can execute
