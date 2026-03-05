# Agent Compatibility and Configuration

Detailed information about AGENTS.md compatibility across AI coding agents and tool-specific configuration.

## Agent Compatibility

AGENTS.md works across many AI coding agents:
- OpenAI Codex
- Cursor
- Claude Code
- Aider
- Google Jules
- Factory

## Tool-Specific Configuration

Some agents require configuration to use AGENTS.md:

### Aider

Create `.aider.conf.yml`:
```yaml
read: AGENTS.md
```

### Gemini CLI

Create `.gemini/settings.json`:
```json
{
  "contextFileName": "AGENTS.md"
}
```

## Agent-Specific Symlinks

Many AI coding agents have their own configuration file names. Instead of maintaining multiple files, create symbolic links to AGENTS.md:

| Agent | File | Symlink Command |
|-------|------|-----------------|
| Claude Code | `CLAUDE.md` | `ln -s AGENTS.md CLAUDE.md` |
| Cursor | `.cursorrules` | `ln -s AGENTS.md .cursorrules` |
| Windsurf | `.windsurfrules` | `ln -s AGENTS.md .windsurfrules` |
| Aider | `AGENTS.md` | Configured in `.aider.conf.yml` |
| Gemini CLI | `AGENTS.md` | Configured in `.gemini/settings.json` |

**Benefits**: Maintain one source of truth while supporting multiple agents.

## Monorepo Support

For large monorepos, use nested AGENTS.md files:

```
my-monorepo/
├── AGENTS.md              # Root-level instructions
├── packages/
│   ├── api/
│   │   └── AGENTS.md      # API-specific instructions
│   └── web/
│       └── AGENTS.md      # Web-specific instructions
```

**Precedence**: The closest AGENTS.md to the edited file wins. Explicit user chat prompts override everything.

## Migration from Other Formats

### From AGENT.md

```bash
# Check for existing file
if [ -f AGENT.md ]; then
  # Review content
  cat AGENT.md
  # Rename to standard
  mv AGENT.md AGENTS.md
  # Create backward-compatible symlink
  ln -s AGENTS.md AGENT.md
fi
```

### From README.md Content

1. Extract developer-focused sections from README.md
2. Remove human-oriented content (screenshots, demos)
3. Keep commands, setup, testing instructions
4. Apply progressive disclosure pattern

### Automated Migration

Use the `/llm-doc:migrate-agents-md` command for automated migration from:
- AGENT.md
- .cursorrules
- .windsurfrules
- CLAUDE.md
- contributing.md
