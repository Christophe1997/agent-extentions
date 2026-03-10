# llm-doc

Documentation standards for AI coding agents. Provides comprehensive tooling for AGENTS.md lifecycle management and conventional commit messages.

## Skills

### agents-md
Guidance for creating and maintaining AGENTS.md files - the standardized format for AI coding agent context. Includes structure, sections, best practices, and symlink patterns for multi-agent compatibility.

**Resources:**
- `references/lifecycle.md` - AGENTS.md maintenance lifecycle
- `references/validation.md` - Quality checklist and validation patterns
- `references/agent-compatibility.md` - Multi-agent symlink strategies
- `examples/` - Real-world AGENTS.md samples

**Trigger phrases:**
- "create an AGENTS.md"
- "write AGENTS.md"
- "migrate to AGENTS.md"
- "update AGENTS.md"

### conventional-commits
Generate compact, clear commit messages following the Conventional Commits specification. Covers types, scopes, breaking changes, and style guidelines.

**Key principle:** No `Co-Authored-By` footer for AI agents. Human takes full ownership of all commits.

**Trigger phrases:**
- "write a commit message"
- "generate a commit"
- "help me commit"
- "commit these changes"

## Installation

### Via Marketplace

```bash
/plugin install llm-doc@agent-extentions
```

## Commands

### /llm-doc:commit
Generate a commit message from staged changes and create the commit. Analyzes the diff to determine type, scope, and description following Conventional Commits.

```bash
/llm-doc:commit        # Auto-detect scope from changed files
```

### /llm-doc:init-agents-md [path]
Scaffold a compact AGENTS.md file by analyzing project configuration (package.json, Cargo.toml, go.mod, etc.). Detects test commands, build scripts, and code style automatically. Defaults to single-file approach.

```bash
/llm-doc:init-agents-md           # Create ./AGENTS.md
/llm-doc:init-agents-md ./docs/   # Create ./docs/AGENTS.md
```

### /llm-doc:migrate-agents-md [source]
Migrate existing agent documentation (AGENT.md, .cursorrules, .windsurfrules, CLAUDE.md) to the compact AGENTS.md format. Auto-detects source files.

```bash
/llm-doc:migrate-agents-md                    # Auto-detect source
/llm-doc:migrate-agents-md ./AGENT.md         # Migrate specific file
```

### /llm-doc:update-agents-md [path]
Update an existing AGENTS.md to reflect current project state. Use when build commands, dependencies, or conventions change.

```bash
/llm-doc:update-agents-md           # Update ./AGENTS.md
/llm-doc:update-agents-md ./docs/   # Update ./docs/AGENTS.md
```

## Usage

- **For guidance**: Ask questions using the trigger phrases above
- **For action**: Use commands for AGENTS.md lifecycle:
  - New project → `/llm-doc:init-agents-md`
  - Existing docs → `/llm-doc:migrate-agents-md`
  - Project changes → `/llm-doc:update-agents-md`
  - Ready to commit → `/llm-doc:commit`

## License

MIT
