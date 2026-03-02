# Agent Design

Guidelines for designing tools and action spaces for AI agents. Covers progressive disclosure, tool design patterns, and lessons from Claude Code development.

## Features

### Skill
Automatically activates when:
- Building agent harnesses
- Designing tool interfaces
- Creating elicitation mechanisms
- Optimizing agent-tool interactions

## Installation

```bash
/plugin install agent-design@agent-extentions
```

## Core Principles

### 1. Claude Must "Like" Calling the Tool
Even the best designed tool doesn't work if Claude doesn't understand how to call it.
- Test if the model naturally uses the tool
- Read outputs to see if it's confused
- Iterate on the interface until it "clicks"

### 2. Tools That Were Necessary Can Become Constraints
As models improve, old workarounds become unnecessary. Constantly revisit assumptions.

### 3. Progressive Disclosure Over Context Bloat
Instead of stuffing everything in the system prompt:
- Give agents tools to discover context themselves
- Let them search, read, and explore recursively

## Usage

Ask questions about agent design:
```
"How should I design tools for my AI agent?"
"What's the best way to structure tool interfaces?"
"How do I implement progressive disclosure?"
"What can I learn from Claude Code's tool design?"
```

## Topics Covered

- Tool design patterns
- Progressive disclosure
- Elicitation mechanisms
- Action space optimization
- Lessons from Claude Code development
