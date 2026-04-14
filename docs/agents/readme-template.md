# Plugin README Template

All plugin READMEs in this repository follow a unified structure for consistency and discoverability.

## Structure

1. **Features** - List what's included (Skills, Hooks, MCP, Agents as tables)
2. **Examples** - Code samples (optional, if applicable)
3. **Installation** - Requirements + `/plugin install ${plugin-name}@agent-extentions`
4. **Usage** - How to use the plugin
5. **License** - MIT

## Template

```markdown
# plugin-name

Brief description of what the plugin does.

## Features

### Skills
- **skill-name** - Brief description of the skill
- **another-skill** - Another skill description

### Hooks
| Hook | Description |
|------|-------------|
| `HookName` | When it fires and what it does |

## Examples

```bash
# Example usage
/plugin:cmd argument
```

## Installation

### Requirements
- Required tool or dependency
- Another requirement

```bash
/plugin install plugin-name@agent-extentions
```

## Usage

Detailed usage instructions...

### Subsection
More specific guidance...

## License

MIT
```

## Component Tables

Use tables for Hooks, bullet lists for Skills:

**Hooks table:**
```markdown
| Hook | Description |
|------|-------------|
| `HookName` | Description |
```

**Skills list:**
```markdown
- **skill-name** - Description with trigger phrases
```

## Installation Format

Always use:
```bash
/plugin install ${plugin-name}@agent-extentions
```

Do not include restart instructions - Claude Code handles reload automatically.

## License

All plugins in this repository use MIT license.
