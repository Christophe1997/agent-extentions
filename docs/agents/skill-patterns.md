# Skill Patterns

Guidelines for writing Claude Code skills in this repository with consistent
structure, naming, and formatting. For the body word-budget and the rationale
behind lean skills, see [progressive-disclosure.md](progressive-disclosure.md).

## Skill Structure

Every skill is a directory containing a required `SKILL.md` plus optional bundled
resources:

```
skills/
└── <skill-dir>/
    ├── SKILL.md            # required: frontmatter + body
    ├── references/         # optional: detail loaded on demand
    ├── examples/           # optional: copyable samples
    └── scripts/            # optional: executables run via Bash
```

`SKILL.md` frontmatter:

```yaml
---
name: <prefix>:<skill>          # see "Naming & Invocation"
description: This skill should be used when the user asks to "<phrase A>", "<phrase B>". <One sentence on what it does.>
argument-hint: "[--flag N] | subcommand"        # optional, display-only
allowed-tools: [Read, Write, Bash, Skill, AskUserQuestion]   # optional
disable-model-invocation: true   # optional; see "Frontmatter Reference"
---
```

## Frontmatter Reference

| Field | Required? | Purpose |
|-------|-----------|---------|
| `name` | **Required** | The skill's identifier — see [Naming & Invocation](#naming--invocation). |
| `description` | **Required** | Triggers model invocation; must carry concrete phrases — see [Description](#description). |
| `argument-hint` | Optional | Display-only usage hint. Mirror the real flags/subcommands. |
| `allowed-tools` | Optional | Restricts the tools the skill may use. **MUST include `Skill`** if it loads other skills. Pure-knowledge skills may omit it. Canonical form is a YAML list (`[Read, Bash]`); a bare comma string also parses. |
| `disable-model-invocation` | Optional | `true` stops the model from auto-triggering the skill, so it runs only when a human invokes the `/command`. Use for deterministic, script-like skills with no reasoning step. |

## Naming & Invocation

A plugin skill is reachable two ways, **both of which resolve at runtime**:

- **`<plugin>:<skill-directory>`** — e.g. `agentic-doc:agd-agents-md`. Claude Code
  derives this canonical id from the `plugin.json` `name` plus the skill folder; it
  is how the skill appears in the skills registry.
- **the frontmatter `name:` value** — e.g. `agd:agents-md`. The Skill tool also
  resolves `skill=` against this (verified: invoking `skill="agd:conventional-commits"`
  loads `agentic-doc/skills/agd-conventional-commits`).

Because both resolve, the in-file `name:` is a **convenience alias**. This repo's
convention:

- Use a **short plugin prefix + skill suffix**: `name: <prefix>:<skill>`
  (`a2a:send`, `agd:commit`, `gpd:search`, `yap:explain`, `smts:export`). The prefix
  is a deliberate shorthand (`agd:` for plugin `agentic-doc`), not the full plugin
  name; keep it consistent across a plugin's skills.
- **Multi-skill plugins** prefix every skill **except** the flagship whose directory
  equals the plugin name, which stays bare: `tdd` (invoked `/tdd:tdd`) alongside
  `tdd:patterns` and `tdd:review`.
- **Single-skill plugins** stay bare: `review-blog`, `zettel-sync`.
- A cross-skill `Skill` reference uses the same short-prefix form:
  `Use Skill tool with skill="agd:conventional-commits"`.

## Description

The `description` is what makes the model load the skill, so it must contain
**concrete trigger phrases** — the literal things a user would say.

- **Required:** quoted trigger phrases.
  `description: This skill should be used when the user asks to "commit these changes", "create a commit".`
- A concise **imperative summary** is acceptable for command skills
  (`Sends a message to an A2A agent by URL or alias…`), but still surface the
  triggers.
- **Avoid** vague openers with no phrases — `Use this skill when working with X`,
  `Provides X guidance`. Anthropic's skill-authoring guidance flags these as wrong:
  no specificity, no triggers.

## Skill Archetypes

Two shapes, with different section expectations:

- **Command / workflow skill** (performs a task): has a `## Process`, usually
  `## Example Usage`, and `allowed-tools`. Examples: `agd:commit`, `a2a:send`,
  `zettel-sync`.
- **Reference / knowledge skill** (informs reasoning): lean prose, often no
  `## Process` and no tools; loaded by other skills or activated by topic.
  Examples: `a2a:protocol`, `tdd:patterns`, `yap:rule-syntax`.

The Required markers and Checklist below apply to **command/workflow** skills.
Reference skills are exempt from `## Process` and `## Example Usage`.

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

Prefer flat numbered steps when possible. Only use phases when the skill has
clearly separate stages.

## Body Writing Style

Write the body in **imperative / verb-first** instructions. Never address the agent
in second person.

- Good: `Check git status before staging.` / `Resolve the alias before sending.`
- Avoid: `You should check git status.` / `You need to resolve the alias.`

## Body Length & Progressive Disclosure

Keep the body lean — ideally **1,500–2,000 words, hard maximum under 5,000**. Push
detail into `references/`. Loading happens in three levels: metadata (always in
context) → `SKILL.md` body (on trigger) → bundled resources (on demand). See
[progressive-disclosure.md](progressive-disclosure.md).

## Bundled Resources

| Directory | Holds | Referenced from SKILL.md as |
|-----------|-------|------------------------------|
| `references/` | detail Claude reads on demand | relative path — `references/cli-reference.md` |
| `examples/` | copyable samples | relative path — `examples/basic.md` |
| `scripts/` | executables run via Bash | `${CLAUDE_PLUGIN_ROOT}/scripts/x.py` |
| `assets/` | files used in output (templates, fonts) | `${CLAUDE_PLUGIN_ROOT}/assets/...` |

Rules:

- Use `${CLAUDE_PLUGIN_ROOT}/...` for anything Bash executes or reads by absolute
  path; use a **relative** path for files Claude opens itself.
- **Mention every bundled resource from `SKILL.md`** so Claude knows it exists.
- **No duplication:** a fact lives in `SKILL.md` *or* a reference file, never both —
  prefer references for depth.

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

Reference other skills with the short-prefix form, and include `Skill` in
`allowed-tools`:

```markdown
## Load Context

Load the `agd:conventional-commits` skill for guidance:
```
Use Skill tool with skill="agd:conventional-commits"
```

This provides:
- Key information the skill contains
- Why it's needed for this skill
```

## Common Sections

| Section | Command skill | Reference skill | Purpose |
|---------|---------------|-----------------|---------|
| `## Load Context` | Optional | Optional | Load other skills for knowledge |
| `## Process` | **Required** | — (n/a) | Main workflow steps |
| `## Error Handling` | Optional | Optional | Edge cases and failures |
| `## Example Usage` | Recommended | Optional | Show how to invoke |
| `## Tips` | Optional | Optional | Helpful hints |

## Checklist

For a **command / workflow** skill:

- [ ] Frontmatter has `name` (short-prefix form) and a `description` with concrete trigger phrases
- [ ] `## Process` with numbered **bold action label** steps
- [ ] Body is imperative / verb-first (no second person)
- [ ] Body is lean (~1,500–2,000 words; detail in `references/`)
- [ ] Bash commands in code blocks; `${CLAUDE_PLUGIN_ROOT}` for scripts
- [ ] `## Example Usage` present (recommended)
- [ ] `allowed-tools` includes `Skill` if it loads other skills
- [ ] `disable-model-invocation: true` if it is a deterministic, human-only runner

For a **reference / knowledge** skill: frontmatter + a lean imperative body;
`## Process`, `## Example Usage`, and `allowed-tools` are optional.
