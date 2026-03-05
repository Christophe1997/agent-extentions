---
name: init-agents-md
description: Scaffold a compact AGENTS.md file with project-specific content. Defaults to simple single-file approach.
argument-hint: optional path (default: ./AGENTS.md)
allowed-tools: [Bash, Read, Write, Glob, Skill, AskUserQuestion]
---

Create a compact, lean AGENTS.md file tailored to the current project. Default to a single file; ask about references folder only if the project is complex.

## Load Context

Load both skills for comprehensive context:

1. **AGENTS.md format** - Load `agents-md` skill:
   ```
   Use Skill tool with skill="llm-doc:agents-md"
   ```
   Provides: sections, structure, best practices

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

4. **Generate compact AGENTS.md** using the format from the skill:
   - Apply recommended sections from skill knowledge
   - Fill in detected project-specific content
   - **Keep content concise and actionable** (target: 50-80 lines)
   - Focus on essential commands and conventions only

5. **Write the file** to the specified path (default: `./AGENTS.md`)

6. **Validate the generated file**:
   - Check all commands are executable
   - Ensure sections are complete and relevant
   - Confirm file is compact (under 100 lines)
   - Verify no placeholder content

7. **Ask about references folder** using AskUserQuestion:
   Ask: "Would you like me to create a references folder for detailed documentation?"

   **Options**:
   - "No, single file is enough" (default) - Simple AGENTS.md satisfies
   - "Yes, create docs/agents/" - Create references folder with detailed docs
   - "Yes, use custom path" - Ask for custom path

   **Only ask if**:
   - Project has complex architecture
   - Many project-specific patterns to document
   - Generated AGENTS.md exceeds 80 lines

8. **Ask about symlinks** (from skill best practices):
   "Would you like me to create symlinks for other AI agents? (CLAUDE.md, .cursorrules, .windsurfrules)"

## Template Detection

| Config File | Detected Context |
|-------------|------------------|
| `package.json` | npm/pnpm/yarn commands, scripts |
| `Cargo.toml` | Rust: `cargo build`, `cargo test` |
| `go.mod` | Go: `go build`, `go test ./...` |
| `pyproject.toml` | Python: poetry/pip commands |
| `Makefile` | Make targets |

## AskUserQuestion Format

Use this format when asking about references folder:

```
questions: [
  {
    "question": "Would you like me to create a references folder for detailed documentation?",
    "header": "References",
    "options": [
      {
        "label": "No, single file is enough",
        "description": "Keep AGENTS.md as a simple, compact file. Recommended for most projects."
      },
      {
        "label": "Yes, create docs/agents/",
        "description": "Create references folder with detailed docs for architecture, patterns, tutorials."
      },
      {
        "label": "Yes, use custom path",
        "description": "Specify a custom path for the references folder."
      }
    ]
  }
]
```

## Notes

- **Default to simple**: Always start with a compact single-file AGENTS.md
- Do not overwrite existing AGENTS.md without confirmation
- Keep generated content concise and actionable
- Include actual commands the agent can execute
- Follow the format and best practices from the loaded skill
- Only create references folder when user explicitly wants it
- Validate generated file before completing
- Always load the agents-md skill first for context
