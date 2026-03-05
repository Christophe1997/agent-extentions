# Command Patterns

Guidelines for writing Claude Code slash commands with consistent structure and formatting.

## Command Structure

Every command file should follow this structure:

```yaml
---
name: command-name
description: What the command does (shown in /help)
argument-hint: optional argument description
allowed-tools: [Read, Write, Bash, Skill, AskUserQuestion]
---

# Title

Brief one-line description of what the command accomplishes.

## Load Context (Optional)

If the command needs knowledge from a skill:

```
Use Skill tool with skill="plugin-name:skill-name"
```

This provides:
- Key concept 1
- Key concept 2

## Process

1. **Action Label**: Description of what to do in this step.
   - Sub-detail or example if needed
   - Another sub-detail

2. **Next Action Label**: Continue with clear actions.
   - For interactive steps, specify the tool:

   Call the AskUserQuestion tool:
   ```json
   {
     "questions": [{
       "question": "Question text?",
       "header": "Short",
       "options": [
         {"label": "Option 1", "description": "What happens"},
         {"label": "Option 2", "description": "Alternative"}
       ]
     }]
   }
   ```

3. **Continue Process**: More steps as needed.

## Error Handling (Optional)

- What to do when things go wrong
- Edge cases to handle
- User communication for failures

## Example Usage

```
/plugin-name:command-name argument
/plugin-name:command-name --option value
```

## Tips (Optional)

- Helpful hints for users
- Common pitfalls to avoid
- Related commands or workflows
```

## Process Section Guidelines

### Step Formatting

**Good:**
```markdown
1. **Check git status**:
   ```bash
   git status --short
   ```
   Identify unstaged files (lines where first column is space or `?`).
```

**Good (interactive):**
```markdown
2. **Ask user for confirmation**:

   Call the AskUserQuestion tool:
   ```json
   {
     "questions": [{
       "question": "Ready to proceed?",
       "header": "Confirm",
       "options": [
         {"label": "Yes", "description": "Continue with action"},
         {"label": "No", "description": "Cancel operation"}
       ]
     }]
   }
   ```
```

### When to Use Sub-sections

For very complex commands with distinct phases, you can use `###` headers within Process:

```markdown
## Process

### Phase 1: Setup

1. **Initialize**: First step...

2. **Configure**: Second step...

### Phase 2: Execution

3. **Run**: Third step...
```

However, prefer flat numbered steps when possible. Only use phases when the command has clearly separate stages.

## Tool Usage in Commands

### AskUserQuestion Pattern

Always show the exact JSON structure:

```markdown
Call the AskUserQuestion tool:
```json
{
  "questions": [{
    "question": "Full question text here?",
    "header": "Short Label",
    "options": [
      {"label": "Choice A", "description": "Result of choosing A"},
      {"label": "Choice B", "description": "Result of choosing B"}
    ]
  }]
}
```

After receiving the response:
- "Choice A" → Do X
- "Choice B" → Do Y
```

### Bash Commands

Show the exact command:

```markdown
```bash
git status --short
```
```

### Skill Loading

Reference skills at the start when needed:

```markdown
## Load Context

Load the `skill-name` skill for guidance:
```
Use Skill tool with skill="plugin-name:skill-name"
```

This provides:
- Key information the skill contains
- Why it's needed for this command
```

## Common Sections

| Section | Required? | Purpose |
|---------|-----------|---------|
| `## Load Context` | Optional | Load skills for knowledge |
| `## Process` | Required | Main workflow steps |
| `## Error Handling` | Optional | Edge cases and failures |
| `## Example Usage` | Recommended | Show how to invoke |
| `## Tips` | Optional | Helpful hints |

## Checklist

- [ ] Uses `## Process` section header
- [ ] Numbered steps with **bold action labels**
- [ ] Bash commands shown in code blocks
- [ ] AskUserQuestion shown with full JSON
- [ ] Includes `## Example Usage`
- [ ] Has `## Error Handling` if edge cases exist
- [ ] Loads skills via `## Load Context` when needed
