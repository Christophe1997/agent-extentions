# Progressive Disclosure Pattern

Guidelines for implementing progressive disclosure in Claude Code plugins.

## Core Principle

**Progressive Disclosure Over Context Bloat**: Instead of stuffing everything in system prompts, give agents tools to discover context themselves. Skills should reference other files for nested discovery rather than containing all information inline.

## Patterns

### Skills Referencing Skills

When a skill needs knowledge from another domain, reference the skill instead of duplicating:

```markdown
### PR/Commit Guidelines
Reference the `llm-doc:commit-message` skill for Conventional Commits format.
When generating this section, load the `commit-message` skill for details.
```

### Commands Loading Skills

Commands should load skills for context rather than duplicating content:

```yaml
---
allowed-tools: [Read, Write, Skill]
---

## Load Context
Load the relevant skill for guidance:
Use Skill tool with skill="plugin-name:skill-name"
```

### Cross-Plugin Reference Format

Always use the full format `plugin-name:skill-name` when referencing skills from other plugins.

## Benefits

- Keeps skill bodies lean and focused
- Avoids duplication and stale content
- Agents load only what they need
- Easier to maintain single source of truth

## Implementation Checklist

- [ ] Skill bodies under 2,000 words
- [ ] Detailed content in `references/` or `examples/`
- [ ] Cross-domain knowledge referenced via skill names
- [ ] Commands include `Skill` in `allowed-tools` when loading skills
