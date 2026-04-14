# Skill Patterns

Guidelines for writing Claude Code skills with consistent structure and formatting.

## Skill Structure

Every skill file (SKILL.md) should follow this structure:

```yaml
---
name: plugin:skill-name
description: "Trigger phrases that activate this skill. Use when user says X, Y, or Z."
argument-hint: optional argument description
allowed-tools: [Read, Write, Bash, Skill, AskUserQuestion]
disable-model-invocation: true  # optional: for script-like skills invoked by human only
---

# Title

Brief one-line description of what the skill accomplishes.

## Load Context (Optional)

If the skill needs knowledge from another skill:

```
Use Skill tool with skill="plugin-name:other-skill"
```

This provides:
- Key concept 1
- Key concept 2

## Process

1. **Action Label**: Description of what to do in this step.
   - Sub-detail or example if needed

2. **Next Action Label**: Continue with clear actions.
   - For interactive steps, use AskUserQuestion:

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

## Example Usage

```
/plugin-name:skill-name argument
/plugin-name:skill-name --option value
```

## Tips (Optional)

- Helpful hints for users
- Common pitfalls to avoid
- Related skills or workflows
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

For complex skills with distinct phases, use `###` headers within Process:

```markdown
## Process

### Phase 1: Setup

1. **Initialize**: First step...

### Phase 2: Execution

2. **Run**: Second step...
```

Prefer flat numbered steps when possible. Only use phases when the skill has clearly separate stages.

## Tool Usage in Skills

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

Reference other skills at the start when needed:

```markdown
## Load Context

Load the `skill-name` skill for guidance:
```
Use Skill tool with skill="plugin-name:skill-name"
```

This provides:
- Key information the skill contains
- Why it's needed for this skill
```

## Common Sections

| Section | Required? | Purpose |
|---------|-----------|---------|
| `## Load Context` | Optional | Load other skills for knowledge |
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
- [ ] Uses `disable-model-invocation: true` if no LLM reasoning needed
