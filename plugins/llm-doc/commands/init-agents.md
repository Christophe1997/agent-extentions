---
name: init-agents
description: Scaffold an AGENTS.md file with project-specific content
argument-hint: optional path (default: ./AGENTS.md)
allowed-tools: [Bash, Read, Write, Glob, Skill]
---

Create an AGENTS.md file tailored to the current project by analyzing its structure and configuration.

## Load Context

Load both skills for comprehensive context:

1. **AGENTS.md format** - Load `agents-md` skill:
   ```
   Use Skill tool with skill="llm-doc:agents-md"
   ```
   Provides: sections, structure, symlink patterns, best practices

2. **Commit format** - Load `commit-message` skill (for PR/Commit Guidelines section):
   ```
   Use Skill tool with skill="llm-doc:commit-message"
   ```
   Provides: Conventional Commits types, style rules, examples

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

4. **Generate AGENTS.md** using the format from the skill:
   - Apply recommended sections from skill knowledge
   - Fill in detected project-specific content
   - Keep content concise and actionable

5. **Write the file** to the specified path (default: `./AGENTS.md`)

6. **Ask about symlinks** (from skill best practices):
   After creating AGENTS.md, ask: "Would you like me to create symlinks for other AI agents? (CLAUDE.md, .cursorrules, .windsurfrules)"

## Template Detection

| Config File | Detected Context |
|-------------|------------------|
| `package.json` | npm/pnpm/yarn commands, scripts |
| `Cargo.toml` | Rust: `cargo build`, `cargo test` |
| `go.mod` | Go: `go build`, `go test ./...` |
| `pyproject.toml` | Python: poetry/pip commands |
| `Makefile` | Make targets |

## Notes

- Do not overwrite existing AGENTS.md without confirmation
- Keep generated content concise and actionable
- Include actual commands the agent can execute
- Follow the format and best practices from the loaded skill
