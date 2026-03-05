---
name: adk-tools
description: ADK-Go tool development including function tools, MCP toolsets, Human-in-the-Loop (HITL) patterns, and artifact/memory loading tools. Use when creating custom tools, integrating MCP servers, or implementing user confirmation flows. Triggers on queries about "functiontool", "mcp toolset", "adk tool", "hitl", "human in the loop", "tool confirmation".
---

# ADK-Go Tools

Tool development patterns for ADK agents.

## Package Map

| Package | Purpose |
|---|---|
| `google.golang.org/adk/tool` | `Tool`, `Toolset`, HITL wrappers |
| `google.golang.org/adk/tool/functiontool` | Go function → ADK tool |
| `google.golang.org/adk/tool/mcptoolset` | MCP server → ADK toolset |
| `google.golang.org/adk/tool/loadartifactstool` | Lazy artifact/skill context loader |
| `google.golang.org/adk/tool/loadmemorytool` | Preloads cross-session memory |
| `google.golang.org/adk/tool/geminitool` | Gemini built-in tools (GoogleSearch etc.) |
| `google.golang.org/adk/tool/toolconfirmation` | HITL confirmation constants |

## Function Tools

Convert Go functions to ADK tools with schema inference:

```go
import "google.golang.org/adk/tool/functiontool"

type WeatherArgs struct {
    City string `json:"city" jsonschema:"description=City name"`
}

weatherTool, _ := functiontool.New(functiontool.Config{
    Name:        "get_weather",
    Description: "Returns current weather for a city",
}, func(ctx tool.Context, args WeatherArgs) (map[string]any, error) {
    return map[string]any{"weather": "sunny in " + args.City}, nil
})

agent, _ := llmagent.New(llmagent.Config{
    Name:  "weather_agent",
    Model: model,
    Tools: []tool.Tool{weatherTool},
})
```

## MCP Tools

### In-Process MCP Server

```go
import (
    "google.golang.org/adk/tool/mcptoolset"
    "github.com/modelcontextprotocol/go-sdk/mcp"
)

clientTransport, serverTransport := mcp.NewInMemoryTransports()
server := mcp.NewServer(&mcp.Implementation{Name: "my_server", Version: "v1"}, nil)
mcp.AddTool(server, &mcp.Tool{Name: "search", Description: "Search the web"}, mySearchFn)
go server.Connect(ctx, serverTransport, nil)

toolSet, _ := mcptoolset.New(mcptoolset.Config{
    Transport: clientTransport,
    ToolFilter: tool.StringPredicate("search", "summarize"), // Optional: filter tools
})
```

### Remote MCP Server

```go
toolSet, _ := mcptoolset.New(mcptoolset.Config{
    Transport: mcp.NewSSEClientTransport("https://my-mcp-server.example.com/mcp/", httpClient),
})

agent, _ := llmagent.New(llmagent.Config{
    Name:     "mcp_agent",
    Model:    model,
    Toolsets: []tool.Toolset{toolSet},  // ← Toolsets, not Tools
})
```

## Human-in-the-Loop (HITL)

### Static Confirmation on MCP Toolsets

```go
mcptoolset.New(mcptoolset.Config{
    Transport:           transport,
    RequireConfirmation: true,  // All tools require approval
})
```

### Dynamic Confirmation

```go
mcptoolset.New(mcptoolset.Config{
    Transport: transport,
    RequireConfirmationProvider: func(toolName string, args any) bool {
        if toolName == "delete_file" { return true }
        if m, ok := args.(map[string]any); ok {
            path, _ := m["path"].(string)
            return strings.HasPrefix(path, "/prod/")
        }
        return false
    },
})
```

### Custom Tool with HITL

```go
func (t *MyTool) Run(ctx tool.Context, args any) (map[string]any, error) {
    if confirmation := ctx.ToolConfirmation(); confirmation != nil {
        if !confirmation.Confirmed {
            return nil, fmt.Errorf("action rejected by user")
        }
        // proceed — user approved
    } else {
        // First pass: ask for confirmation
        ctx.RequestConfirmation("Confirm sending email?", args)
        ctx.Actions().SkipSummarization = true
        return nil, fmt.Errorf("awaiting confirmation")
    }
    return t.doSend(args)
}
```

### Client-Side Protocol

```
ADK emits FunctionCall:
  Name: "adk_request_confirmation"
  Args: {
    "originalFunctionCall": { name: "send_email", args: {...} },
    "toolConfirmation":     { hint: "Confirm sending email?" }
  }

Client replies with FunctionResponse:
  Name: "adk_request_confirmation"
  ID:   <same as received FunctionCall ID>
  Response: { "confirmed": true }   // or false
```

## Built-in Tools

### Load Artifacts Tool

LLM-driven lazy skill loading:

```go
import "google.golang.org/adk/tool/loadartifactstool"

// Pre-save skill docs as artifacts
artifactSvc.Save(ctx, &artifact.SaveRequest{
    AppName: "app", UserID: "u1", SessionID: "s1",
    FileName: "sql_skill.md",
    Part:     genai.NewPartFromText(sqlSkillMarkdown),
})

agent, _ := llmagent.New(llmagent.Config{
    Name:        "skilled_agent",
    Model:       model,
    Instruction: "Load and use relevant skill docs when answering questions.",
    Tools: []tool.Tool{loadartifactstool.New()},
})
// Tool injects: "You have artifacts: [sql_skill.md, ...]
// Call load_artifacts(artifact_names=[...]) to access their content."
```

### Load Memory Tool

```go
import "google.golang.org/adk/tool/loadmemorytool"

Tools: []tool.Tool{loadmemorytool.New()}
```

## Gotchas

### MCP toolsets use `Toolsets`, not `Tools`

```go
// ✅ correct
llmagent.Config{ Toolsets: []tool.Toolset{mcpSet} }
// ❌ won't compile — mcpSet is Toolset, not Tool
llmagent.Config{ Tools: []tool.Tool{mcpSet} }
```

### HITL `WithConfirmation` is EXPERIMENTAL

Prefer `RequireConfirmation`/`RequireConfirmationProvider` on `mcptoolset.Config` for MCP tools.

## See Also

- [adk-basics](../adk-basics) - Core agent setup
- [adk-callbacks](../adk-callbacks) - Callbacks for tool lifecycle
