---
name: add-tool
description: Add a new function tool to an existing ADK-Go agent
argument-hint: "[tool-name] [description]"
allowed-tools: [Read, Write, Edit, Glob, Grep, AskUserQuestion, Skill]
---

# Add Function Tool to ADK Agent

Create a new function tool and add it to an existing agent.

## Steps

1. **Find agent files**: Look for `agent.go` or files with `llmagent.New`

2. **Get tool details**:
   - Tool name (kebab-case, e.g., "get-weather")
   - Description (what the tool does)
   - Parameters (name, type, description for each)

3. **Generate tool code**:
```go
type {{ToolName}}Args struct {
    {{ParamName}} {{ParamType}} `json:"{{paramName}}" jsonschema:"description={{paramDescription}}"`
}

var {{ToolName}}Tool, _ = functiontool.New(functiontool.Config{
    Name:        "{{tool_name}}",
    Description: "{{description}}",
}, func(ctx tool.Context, args {{ToolName}}Args) (map[string]any, error) {
    // TODO: Implement tool logic
    return map[string]any{
        "result": "not implemented",
    }, nil
})
```

4. **Add import if needed**:
```go
import "google.golang.org/adk/tool/functiontool"
```

5. **Register tool in agent config**:
```go
Tools: []tool.Tool{{{ToolName}}Tool},
```

## Parameter Types

| Go Type | JSON Schema Type |
|---------|-----------------|
| `string` | string |
| `int`, `int64` | integer |
| `float64` | number |
| `bool` | boolean |
| `[]string` | array of strings |
| `map[string]any` | object |

## Output

- Show the generated tool code
- Show where it was added
- Remind to implement the tool logic
